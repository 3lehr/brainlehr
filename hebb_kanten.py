#!/usr/bin/env python3
"""Hebbsche Kanten: recall_log.jsonl -> knowledge_relations.

Zwei Knoten, die wiederholt im selben Recall-Abruf gemeinsam auftauchen,
bekommen eine abgeleitete Kante (relation_type=analogous_to, source="hebb_kanten.py").
Ein einmaliges Zusammentreffen ist blosse Stichwortueberschneidung (BM25 zieht
beide fuer dieselben Woerter); erst ein wiederholtes Zusammentreffen ueber
verschiedene Abrufe hinweg ist ein Hinweis auf Verwandtschaft -- daher
Schwelle 2, nicht 1.

ZERFALL (Konsil 2026-08-08, Korrektur 2026-08-08): Ohne Zerfall addierte jeder
Lauf nur, nie Dekrement -- ein Matthaeus-Effekt, wer frueh Treffer bekam,
behielt sie fuer immer. Das GEWICHT wird darum bei JEDEM Lauf komplett aus dem
Protokoll neu berechnet (kein Aufaddieren mehr auf den gespeicherten Wert),
jedes einzelne Zusammentreffen zaehlt mit exponentiellem Abstand zum Ende des
Protokolls:

    gewicht = sum(exp(-ln2 * alter_in_ereignissen / HALF_LIFE_EVENTS))

Ereignisbasiert wie begod/scripts/trust_factor.py (DR-22: event-based >
time-based, dort HALF_LIFE_INTERACTIONS=30 pro Agent). Hier ist der Takt
der globale Abruf-Strom, nicht ein Pro-Paar-Strom -- wie beim Ameisen-
Pheromon verdunstet JEDER Pfad mit jedem Tick, nicht nur der eigene: ein
Thema, das niemand mehr anfragt, verblasst auch dann, wenn es frueher stark
war. HALF_LIFE_EVENTS=200 aus den Daten (789 Abrufe/6,67 Tage = ~118/Tag,
Median-Abstand zwischen zwei Bestaetigungen desselben Paares = 1 Ereignis,
p90 = 6 -- fast alle Bestaetigungen liegen Minuten bis Stunden auseinander).

WICHTIG -- Zerfall betrifft nur das GEWICHT, nie die EXISTENZ: bei Ameisen
verdunstet das Pheromon, aber der Weg bleibt begehbar, verdunstet ist nur der
Hinweis, dass ihn viele gegangen sind. Eine Kante, die einmal die
Anlage-Schwelle erreicht hat, bleibt bestehen, auch wenn ihr Gewicht spaeter
unter die Schwelle faellt (eine Woche Pause darf keine Verwandtschaft
loeschen). Wer nur starke Kanten sehen will, filtert beim LESEN -- das ist
Aufgabe der Ansicht, nicht des Speichers. Loeschen bleibt einem ausdruecklichen
Aufraeumlauf vorbehalten (--delete, loescht ALLE eigenen Kanten, nicht
selektiv nach Gewicht).

Weil das Gewicht bei jedem Lauf aus dem VOLLEN Protokoll neu gerechnet wird
(nicht auf den letzten gespeicherten Wert aufaddiert), ist ein Lauf ohne neue
Abrufe zwischen zwei Aufrufen von Natur aus wiederholungsfest (idempotent) --
keine gesonderte "wurde dieser Abruf schon gezaehlt"-Buchhaltung noetig.

Schreibt ausschliesslich ueber knowledge_mcp_server.knowledge_relation_add()
/ _update() / _remove() (Wissensvertrag: kein direktes INSERT/UPDATE/DELETE).
Kanten zwischen/mit Lessons entfallen: knowledge_relations hat FOREIGN KEY
auf knowledge_nodes.path fuer beide Enden (schema.sql:152-153), lessons_learned
ist kein gueltiges Ende.

Nutzung:
    python3 hebb_kanten.py --dry-run          # Vorgabe, schreibt nichts
    python3 hebb_kanten.py --apply            # schreibt, legt vorher Sicherung an
    python3 hebb_kanten.py --schwelle 3 --dry-run
    python3 hebb_kanten.py --halbwertszeit 100 --dry-run
    python3 hebb_kanten.py --selftest
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import shutil
import sqlite3
import sys
import tempfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
import knowledge_mcp_server as kms  # nur ueber diese Funktion schreiben

HERE = Path(__file__).parent
RECALL_LOG = HERE / "recall_log.jsonl"
BERLIN = ZoneInfo("Europe/Berlin")

# Schwelle: 1 gemeinsamer Abruf = geteilte BM25-Suchworte, kein Hinweis.
# Ab 2 (nach Zerfall gerechnet) ist es ein wiederholtes Muster -> Kante.
SCHWELLE_DEFAULT = 2

# Siehe Modulkommentar oben fuer die Herleitung aus den echten Protokolldaten.
HALF_LIFE_EVENTS_DEFAULT = 200
LN2 = math.log(2)
GEWICHT_EPSILON = 1e-6  # Toleranz gegen Gleitkomma-Rauschen an der Schwelle (exp() ist nie exakt 1.0)

RELATION_TYPE = "analogous_to"  # naechstliegender Typ fuer eine unbelegte, undirektionale Assoziation
SOURCE_TAG = "hebb_kanten.py"    # macht die Kante als abgeleitet erkennbar (Feld "source" in knowledge_relations)


def _backup(db_path: Path) -> Path:
    """Checkpoint vor dem Kopieren, Befund 2026-08-05: die Live-DB laeuft im
    WAL-Modus, ein reiner shutil.copy2 der Hauptdatei laesst committete, aber
    noch nicht zurueckgeschriebene Aenderungen im WAL-Journal zurueck --
    beobachtet an drei .bak-Dateien vom selben Tag, in denen die neu
    angelegte Spalte norm_rang fehlte, obwohl die Live-DB sie laengst hatte
    (eine davon entstand sogar NACH der Migration). TRUNCATE checkpointed
    und leert die WAL-Datei; ist ein anderer Prozess busy und der Checkpoint
    bleibt unvollstaendig, wird abgebrochen statt eine unvollstaendige Kopie
    anzulegen (siehe RuntimeError unten)."""
    conn = sqlite3.connect(str(db_path))
    try:
        busy, log_frames, checkpointed = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if busy:
            raise RuntimeError(
                f"WAL-Checkpoint blockiert (busy={busy}, log={log_frames} Frames, "
                f"{checkpointed} checkpointed) -- ein anderer Prozess schreibt gerade. "
                "Sicherung abgebrochen statt unvollstaendig angelegt."
            )
    finally:
        conn.close()
    stamp = datetime.now(BERLIN).strftime("%Y%m%dT%H%M%S")
    dest = db_path.parent / f"knowledge.db.bak-{stamp}"
    shutil.copy2(db_path, dest)
    return dest


def paar_zaehlung(log_path: Path) -> tuple[dict[tuple[str, str], list[int]], dict[tuple[str, str], list[int]], int]:
    """Sammelt je Paar (ueber Knoten UND Lessons gemeinsam, wie im Protokoll)
    die Ereignis-Indizes (0-basiert, nur ueber nicht-leere Zeilen gezaehlt),
    zu denen es gemeinsam auftrat -- Grundlage sowohl fuer die rohe Zaehlung
    als auch fuer den Zerfall (Alter = zeilen_gesamt - 1 - index).

    Ein Paar zaehlt pro Zeile hoechstens einmal, auch wenn 3+ Eintraege in
    derselben Zeile stehen (sonst wuerden grosse Abrufe ueberproportional
    gewichten). Getrennt zurueckgegeben: reine Knoten-Knoten-Paare (koennen
    zu Kanten werden) und Paare, an denen mindestens eine Lesson beteiligt
    ist (schema-bedingt nie eine Kante, siehe Modulkommentar).

    Gibt (knoten_paare, lesson_beteiligte_paare, Zeilenzahl) zurueck.
    """
    knoten_paare: dict[tuple[str, str], list[int]] = defaultdict(list)
    lesson_paare: dict[tuple[str, str], list[int]] = defaultdict(list)
    zeilen = 0
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            idx = zeilen  # 0-basierter Ereignisindex dieser (nicht-leeren) Zeile
            zeilen += 1
            eintrag = json.loads(line)
            nodes = set(eintrag.get("nodes") or [])
            lessons = set(eintrag.get("lessons") or [])
            for a, b in itertools.combinations(sorted(nodes | lessons), 2):
                if a in lessons or b in lessons:
                    lesson_paare[(a, b)].append(idx)
                else:
                    knoten_paare[(a, b)].append(idx)
    return knoten_paare, lesson_paare, zeilen


def gewicht_mit_zerfall(idxs: list[int], zeilen_gesamt: int, halbwertszeit: float) -> float:
    """Summe der Einzelbeitraege, jeder exponentiell nach Alter in Ereignissen
    seit dem Ende des Protokolls verjuengt. Ein Zusammentreffen in der
    letzten Zeile hat Alter 0 (Beitrag ~1), eines am Anfang des Protokolls
    hat Alter zeilen_gesamt-1 (Beitrag entsprechend klein)."""
    return sum(
        math.exp(-LN2 * (zeilen_gesamt - 1 - i) / halbwertszeit)
        for i in idxs
    )


def existierende_pfade(conn: sqlite3.Connection) -> set[str]:
    return {row[0] for row in conn.execute("SELECT path FROM knowledge_nodes")}


def bestehende_kanten(conn: sqlite3.Connection) -> dict[tuple[str, str], tuple[str, float]]:
    """Pfad-Paar -> (relation_id, aktuelles Gewicht), nur eigener Kantentyp+Quelle."""
    rows = conn.execute(
        "SELECT id, source_path, target_path, weight FROM knowledge_relations WHERE relation_type=? AND source=?",
        (RELATION_TYPE, SOURCE_TAG),
    ).fetchall()
    return {(r[1], r[2]): (r[0], r[3]) for r in rows}


def plane(zaehler: dict[tuple[str, str], list[int]], schwelle: int, gueltige_pfade: set[str],
          vorhandene_kanten: dict[tuple[str, str], tuple[str, float]],
          zeilen_gesamt: int, halbwertszeit: float,
          ) -> tuple[list[tuple[str, str, int, float]],
                     list[tuple[str, str, int, float, str, float]],
                     int]:
    """Liefert (neue Kanten [a,b,n,gewicht], zu aktualisierende [a,b,n,gewicht,relation_id,altes_gewicht],
    Zahl uebersprungener Paare wegen fehlendem Knoten).

    Gewicht wird bei jedem Lauf komplett neu aus dem Protokoll berechnet (nicht auf den alten Wert
    aufaddiert) -- macht den Lauf von selbst wiederholungsfest und bildet den Zerfall ab. Zerfall
    betrifft nur das GEWICHT: eine einmal angelegte Kante wird IMMER aktualisiert, nie geloescht,
    auch wenn ihr neues Gewicht unter die Schwelle faellt (Anlage-Schwelle != Existenzbedingung,
    siehe Modulkommentar). Nur eine Kante, die NIE angelegt wurde, bleibt unterhalb der Schwelle
    ungeschrieben."""
    anzulegen = []
    zu_aktualisieren = []
    uebersprungen_fehlend = 0
    for (a, b), idxs in zaehler.items():
        n = len(idxs)
        bestehend = vorhandene_kanten.get((a, b)) or vorhandene_kanten.get((b, a))
        if n < schwelle and not bestehend:
            continue  # roh schon unter Schwelle, nie angelegt -- Zerfall macht es nur noch kleiner
        if a not in gueltige_pfade or b not in gueltige_pfade:
            uebersprungen_fehlend += 1
            continue
        gewicht = gewicht_mit_zerfall(idxs, zeilen_gesamt, halbwertszeit)
        if bestehend:
            relation_id, altes_gewicht = bestehend
            zu_aktualisieren.append((a, b, n, gewicht, relation_id, altes_gewicht))
        elif gewicht >= schwelle - GEWICHT_EPSILON:
            anzulegen.append((a, b, n, gewicht))
        # sonst: roh >= Schwelle, aber nach Zerfall (noch) nicht -- keine Neuanlage, keine Loeschung noetig (gab es nie)
    return anzulegen, zu_aktualisieren, uebersprungen_fehlend


def wende_an(neu: list[tuple[str, str, int, float]],
             aktualisierungen: list[tuple[str, str, int, float, str, float]],
             halbwertszeit: float) -> tuple[int, int]:
    angelegt = 0
    for a, b, n, gewicht in neu:
        kms.knowledge_relation_add(
            source_node=a, target_node=b, relation_type=RELATION_TYPE,
            confidence=0.5,  # abgeleitet, nicht belegt -- bewusst unter dem Default 0.8
            weight=gewicht,
            evidence=f"{n} gemeinsame Abrufe insgesamt in recall_log.jsonl, {gewicht:.3f} nach "
                     f"Zerfall (Halbwertszeit {halbwertszeit:.0f} Ereignisse)",
            source=SOURCE_TAG,
            creator=SOURCE_TAG,
        )
        angelegt += 1
    aktualisiert = 0
    for a, b, n, gewicht, relation_id, altes_gewicht in aktualisierungen:
        kms.knowledge_relation_update(
            relation_id=relation_id,
            weight=gewicht,
            evidence=f"{n} gemeinsame Abrufe insgesamt in recall_log.jsonl, {gewicht:.3f} nach "
                     f"Zerfall (Halbwertszeit {halbwertszeit:.0f} Ereignisse, war {altes_gewicht:.3f})",
            creator=SOURCE_TAG,
        )
        aktualisiert += 1
    return angelegt, aktualisiert


def loesche_eigene_kanten(conn: sqlite3.Connection) -> list[str]:
    """IDs aller Kanten dieses Typs+Quelle. Nur lesend -- Loeschen macht der Aufrufer
    ueber kms.knowledge_relation_remove(), damit auch das Loeschen den Wissensvertrag
    (audited Zugriff statt direktem DELETE) einhaelt."""
    rows = conn.execute(
        "SELECT id FROM knowledge_relations WHERE relation_type=? AND source=?",
        (RELATION_TYPE, SOURCE_TAG),
    ).fetchall()
    return [r[0] for r in rows]


def verteilung(gewichte: list[float]) -> tuple[int, float, float, float]:
    """(Anzahl, Minimum, Maximum, Median) -- Abnahme 6: entsteht nach dem Zerfall
    ueberhaupt eine Rangfolge, oder liegt alles nahe an derselben Zahl?"""
    if not gewichte:
        return 0, 0.0, 0.0, 0.0
    s = sorted(gewichte)
    n = len(s)
    median = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    return n, s[0], s[-1], median


def bericht(knoten_paare: dict[tuple[str, str], list[int]], lesson_paare: dict[tuple[str, str], list[int]],
            zeilen: int, schwelle: int, halbwertszeit: float,
            kanten: list[tuple[str, str, int, float]],
            aktualisierungen: list[tuple[str, str, int, float, str, float]],
            uebersprungen: int) -> None:
    gesamt_counts: dict[tuple[str, str], int] = {k: len(v) for k, v in knoten_paare.items()}
    gesamt_counts.update({k: len(v) for k, v in lesson_paare.items()})
    print(f"recall_log.jsonl: {zeilen} Zeilen, {len(gesamt_counts)} verschiedene Ko-Abruf-Paare insgesamt "
          f"(Knoten+Lessons zusammen, wie im Protokoll)")
    for s in (1, 2):
        n = sum(1 for c in gesamt_counts.values() if c >= s)
        print(f"  Paare mit >= {s} gemeinsamen Abrufen (roh, vor Zerfall): {n}")
    roh_ab_schwelle = sum(1 for idxs in knoten_paare.values() if len(idxs) >= schwelle)
    print(f"  davon reine Knoten-Knoten-Paare (einzige moegliche Kanten): "
          f"{len(knoten_paare)} insgesamt, {roh_ab_schwelle} roh ab Schwelle {schwelle}")
    print(f"  davon Paare mit Lesson-Beteiligung (nie eine Kante -- knowledge_relations.source_path/"
          f"target_path referenziert nur knowledge_nodes, siehe schema.sql): {len(lesson_paare)}")
    print(f"Schwelle={schwelle} (nur Anlage-Bedingung), Halbwertszeit={halbwertszeit:.0f} Ereignisse -> "
          f"{len(kanten)} neue Kanten, {len(aktualisierungen)} bestehende mit neuem Gewicht "
          f"(Zerfall loescht nie, nur --delete tut das)")
    print(f"  uebersprungen (Knoten-Knoten-Paar relevant, aber ein Pfad existiert nicht mehr): {uebersprungen}")
    alle_gewichte = [g for _, _, _, g in kanten] + [g for _, _, _, g, _, _ in aktualisierungen]
    n, lo, hi, med = verteilung(alle_gewichte)
    print(f"  Gewichtsverteilung nach Zerfall: n={n}, Spanne=[{lo:.3f}, {hi:.3f}], Median={med:.3f}")


def lauf(log_path: Path, db_path: Path, schwelle: int, apply: bool,
         halbwertszeit: float = HALF_LIFE_EVENTS_DEFAULT) -> dict:
    knoten_paare, lesson_paare, zeilen = paar_zaehlung(log_path)
    conn = sqlite3.connect(str(db_path))
    gueltige_pfade = existierende_pfade(conn)
    vorhandene = bestehende_kanten(conn)
    kanten, aktualisierungen, uebersprungen = plane(
        knoten_paare, schwelle, gueltige_pfade, vorhandene, zeilen, halbwertszeit,
    )
    conn.close()
    bericht(knoten_paare, lesson_paare, zeilen, schwelle, halbwertszeit,
            kanten, aktualisierungen, uebersprungen)

    if not apply:
        print("(--dry-run, nichts geschrieben. --apply zum Schreiben.)")
        return {"geplant": len(kanten), "aktualisierungen": len(aktualisierungen),
                "uebersprungen": uebersprungen}

    sicherung = _backup(db_path)
    print(f"Sicherung: {sicherung}")
    kms.DB_PATH = db_path  # knowledge_relation_add/_update oeffnen ueber kms.get_db() -> DB_PATH
    angelegt, aktualisiert = wende_an(kanten, aktualisierungen, halbwertszeit)
    print(f"Angelegt: {angelegt} Kanten. Neu berechnet: {aktualisiert} Kanten.")
    return {"angelegt": angelegt, "aktualisiert": aktualisiert, "sicherung": str(sicherung)}


def loesche(db_path: Path, apply: bool) -> dict:
    conn = sqlite3.connect(str(db_path))
    ids = loesche_eigene_kanten(conn)
    conn.close()
    print(f"Kanten relation_type={RELATION_TYPE!r} source={SOURCE_TAG!r}: {len(ids)} gefunden.")
    if not apply:
        print("(--dry-run, nichts geloescht. --delete --apply zum Loeschen.)")
        return {"gefunden": len(ids)}
    sicherung = _backup(db_path)
    print(f"Sicherung: {sicherung}")
    kms.DB_PATH = db_path
    for relation_id in ids:
        kms.knowledge_relation_remove(relation_id=relation_id, actor=SOURCE_TAG)
    print(f"Geloescht: {len(ids)} Kanten.")
    return {"geloescht": len(ids), "sicherung": str(sicherung)}


# ─── Selbsttest ──────────────────────────────────────────────────────────

def _selftest() -> int:
    tmp_dir = Path(tempfile.mkdtemp(prefix="hebb_selftest_"))
    db_path = tmp_dir / "knowledge.db"
    log_path = tmp_dir / "recall_log.jsonl"

    conn = sqlite3.connect(str(db_path))
    conn.executescript(Path(HERE / "schema.sql").read_text(encoding="utf-8"))
    now = datetime.now(BERLIN).isoformat(timespec="seconds")
    knoten = ["/a", "/b", "/c", "/d", "/e", "/f"]
    for i, p in enumerate(knoten):
        conn.execute(
            "INSERT INTO knowledge_nodes (id,path,title,summary,source,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
            (f"N-{i}", p, p, "Test", "selftest", now, now),
        )
    conn.commit()
    conn.close()

    # Kernfaelle (kurzes Protokoll, riesige Halbwertszeit -> Zerfall vernachlaessigbar,
    # damit die reine Schwellenlogik wie bisher pruefbar bleibt):
    # /a-/b: 1x gemeinsam -> darf NICHT angelegt werden
    # /b-/c: 2x gemeinsam -> muss angelegt werden
    # /c-/d: 3x gemeinsam -> muss angelegt werden, hoeheres Gewicht
    # /a-/fehlt: nicht-existenter Knoten -> uebersprungen, gezaehlt
    # /a-/a (Selbstpaar, gleicher Pfad zweimal in einer Zeile) -> nie (combinations auf set liefert kein Selbstpaar)
    kernzeilen = [
        {"nodes": ["/a", "/b"], "lessons": []},
        {"nodes": ["/b", "/c"], "lessons": []},
        {"nodes": ["/b", "/c"], "lessons": []},
        {"nodes": ["/c", "/d"], "lessons": []},
        {"nodes": ["/c", "/d"], "lessons": []},
        {"nodes": ["/c", "/d"], "lessons": []},
        {"nodes": ["/a", "/fehlt-nicht-vorhanden"], "lessons": []},
        {"nodes": ["/a", "/fehlt-nicht-vorhanden"], "lessons": []},  # 2x, sonst faellt Paar schon an der Schwelle raus
        {"nodes": ["/a", "/a"], "lessons": []},  # Selbstpaar in einer Zeile
        {"nodes": [], "lessons": ["L-1", "L-2"]},  # Lesson-Paar, muss uebersprungen werden
    ]
    with open(log_path, "w", encoding="utf-8") as f:
        for z in kernzeilen:
            f.write(json.dumps(z) + "\n")

    kms.DB_PATH = db_path  # knowledge_relation_add nutzt kms.get_db() -> DB_PATH
    RIESIG = 1e9  # macht exp(-ln2*age/RIESIG) ~ 1.0 fuer diese wenigen Zeilen -> Zerfall irrelevant

    ok = True

    def check(bedingung: bool, text: str) -> None:
        nonlocal ok
        status = "OK" if bedingung else "FEHLER"
        print(f"  [{status}] {text}")
        if not bedingung:
            ok = False

    def nahe(x: float, ziel: float, tol: float = 0.01) -> bool:
        return abs(x - ziel) <= tol

    # Lauf 1: dry-run darf nichts schreiben
    ergebnis = lauf(log_path, db_path, SCHWELLE_DEFAULT, apply=False, halbwertszeit=RIESIG)
    conn = sqlite3.connect(str(db_path))
    n_vor = conn.execute("SELECT COUNT(*) FROM knowledge_relations").fetchone()[0]
    conn.close()
    check(n_vor == 0, "dry-run schreibt nichts")
    check(ergebnis["geplant"] == 2, f"2 Kanten geplant (b-c, c-d), war {ergebnis['geplant']}")
    check(ergebnis["uebersprungen"] == 1, f"1 Paar wegen fehlendem Knoten uebersprungen, war {ergebnis['uebersprungen']}")

    # Lauf 2: apply
    ergebnis2 = lauf(log_path, db_path, SCHWELLE_DEFAULT, apply=True, halbwertszeit=RIESIG)
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        "SELECT source_path,target_path,weight FROM knowledge_relations ORDER BY source_path"
    ).fetchall()
    conn.close()
    check(len(rows) == 2, f"2 Kanten in DB nach apply, war {len(rows)}")
    gewicht_bc = next((r[2] for r in rows if {r[0], r[1]} == {"/b", "/c"}), None)
    gewicht_cd = next((r[2] for r in rows if {r[0], r[1]} == {"/c", "/d"}), None)
    check(nahe(gewicht_bc, 2.0), f"/b-/c Gewicht ~2 (Zerfall vernachlaessigbar), war {gewicht_bc}")
    check(nahe(gewicht_cd, 3.0), f"/c-/d Gewicht ~3 (haeufiger), war {gewicht_cd}")
    check(not any({r[0], r[1]} == {"/a", "/b"} for r in rows), "/a-/b (nur 1x) wurde NICHT angelegt")

    # Lauf 3 (Abnahme 4, Wiederholungsfestigkeit): zweiter apply-Lauf OHNE neue Zeilen
    # darf das Gewicht NICHT veraendern (nicht verdoppeln) -- das Gewicht wird aus dem
    # vollen Protokoll neu berechnet, nicht auf den alten Wert aufaddiert.
    ergebnis3 = lauf(log_path, db_path, SCHWELLE_DEFAULT, apply=True, halbwertszeit=RIESIG)
    conn = sqlite3.connect(str(db_path))
    rows_nach = conn.execute(
        "SELECT source_path,target_path,weight FROM knowledge_relations ORDER BY source_path"
    ).fetchall()
    conn.close()
    check(len(rows_nach) == 2, f"zweiter Lauf ohne neue Zeilen legt nichts doppelt an, weiter 2 Kanten, war {len(rows_nach)}")
    check(ergebnis3["angelegt"] == 0, f"zweiter Lauf legt 0 neue Kanten an, war {ergebnis3['angelegt']}")
    gewicht_bc_2 = next((r[2] for r in rows_nach if {r[0], r[1]} == {"/b", "/c"}), None)
    gewicht_cd_2 = next((r[2] for r in rows_nach if {r[0], r[1]} == {"/c", "/d"}), None)
    check(nahe(gewicht_bc_2, gewicht_bc), f"/b-/c Gewicht unveraendert nach Wiederholungslauf, war {gewicht_bc} -> {gewicht_bc_2}")
    check(nahe(gewicht_cd_2, gewicht_cd), f"/c-/d Gewicht unveraendert nach Wiederholungslauf, war {gewicht_cd} -> {gewicht_cd_2}")

    # Lauf 4 (Abnahme 1+2, rot-vor-gruen + Alter darf nicht mehr gleich zaehlen):
    # /e-/f: 5x GANZ AM ANFANG eines langen Protokolls, seither nie bestaetigt ("alt").
    # /c-/d: 3x GANZ AM ENDE ("frisch"). Halbwertszeit 300, dazwischen 300 Fuellzeilen.
    # ROT (Stand vor diesem Fix -- Gewicht = rohe Zaehlung, kein Alter): /e-/f haette
    # Gewicht 5, /c-/d Gewicht 3 -- rein nach roher Haeufigkeit, das Alter zaehlt nicht.
    # GRUEN (mit Zerfall, hier numerisch vorab ermittelt ueber gewicht_mit_zerfall):
    # /e-/f faellt trotz mehr rohen Treffern unter /c-/d, weil es alt ist.
    HALBWERTSZEIT_TEST = 300
    n_alt = 5
    luecke = 300
    lange_zeilen = [{"nodes": ["/e", "/f"], "lessons": []} for _ in range(n_alt)]
    lange_zeilen += [{"nodes": [], "lessons": ["L-fuell"]} for _ in range(luecke)]
    lange_zeilen += [{"nodes": ["/c", "/d"], "lessons": []} for _ in range(3)]  # frisch am Ende
    log_path2 = tmp_dir / "recall_log2.jsonl"
    with open(log_path2, "w", encoding="utf-8") as f:
        for z in lange_zeilen:
            f.write(json.dumps(z) + "\n")

    db_path2 = tmp_dir / "knowledge2.db"
    conn = sqlite3.connect(str(db_path2))
    conn.executescript(Path(HERE / "schema.sql").read_text(encoding="utf-8"))
    for i, p in enumerate(["/c", "/d", "/e", "/f"]):
        conn.execute(
            "INSERT INTO knowledge_nodes (id,path,title,summary,source,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
            (f"M-{i}", p, p, "Test", "selftest", now, now),
        )
    conn.commit()
    conn.close()

    kms.DB_PATH = db_path2
    gewicht_roh_ef = float(n_alt)  # ROT: Stand vor dem Fix (Gewicht == rohe Zaehlung, kein Alter)
    gewicht_roh_cd = 3.0
    check(gewicht_roh_ef > gewicht_roh_cd,
          f"ROT (Stand vor dem Fix): /e-/f (alt, {n_alt}x) haette MEHR Gewicht als /c-/d (frisch, 3x) -- "
          f"reine Haeufigkeit ignoriert das Alter komplett")

    ergebnis4 = lauf(log_path2, db_path2, SCHWELLE_DEFAULT, apply=True, halbwertszeit=HALBWERTSZEIT_TEST)
    conn = sqlite3.connect(str(db_path2))
    rows4 = conn.execute(
        "SELECT source_path,target_path,weight FROM knowledge_relations ORDER BY source_path"
    ).fetchall()
    conn.close()
    gewicht_neu_ef = next((r[2] for r in rows4 if {r[0], r[1]} == {"/e", "/f"}), None)
    gewicht_neu_cd = next((r[2] for r in rows4 if {r[0], r[1]} == {"/c", "/d"}), None)
    check(gewicht_neu_ef is not None, "/e-/f (alt, trotz Zerfall noch ueber Schwelle) angelegt")
    check(gewicht_neu_cd is not None, "/c-/d (frisch) angelegt")
    if gewicht_neu_ef is not None and gewicht_neu_cd is not None:
        check(gewicht_neu_ef < gewicht_neu_cd,
              f"GRUEN: trotz 5x vs 3x roh hat das ALTE Paar jetzt WENIGER Gewicht als das frische "
              f"(war {gewicht_neu_ef:.3f} vs {gewicht_neu_cd:.3f})")

    # Lauf 5 (Abnahme 3+Konsil-Korrektur, Grenzwert -- Gewicht faellt unter die Schwelle,
    # die KANTE BLEIBT): 100 weitere Ereignisse anhaengen, OHNE dass /e-/f nochmal vorkommt
    # -> Alter waechst weiter (numerisch vorab ermittelt: Gewicht faellt von ~2.47 auf ~1.96,
    # unter Schwelle 2) -- Arbeitspause darf die Kante NICHT loeschen (Ameisen-Pheromon:
    # der Weg bleibt begehbar, nur der Hinweis verblasst).
    with open(log_path2, "a", encoding="utf-8") as f:
        for _ in range(100):
            f.write(json.dumps({"nodes": [], "lessons": ["L-fuell2"]}) + "\n")
    ergebnis5 = lauf(log_path2, db_path2, SCHWELLE_DEFAULT, apply=True, halbwertszeit=HALBWERTSZEIT_TEST)
    conn = sqlite3.connect(str(db_path2))
    rows5 = conn.execute(
        "SELECT source_path,target_path,weight FROM knowledge_relations ORDER BY source_path"
    ).fetchall()
    conn.close()
    gewicht_ef_nach_pause = next((r[2] for r in rows5 if {r[0], r[1]} == {"/e", "/f"}), None)
    check(ergebnis5["angelegt"] == 0, f"Lauf legt nichts neu an (Kante existiert schon), war {ergebnis5['angelegt']}")
    check(gewicht_ef_nach_pause is not None,
          "/e-/f (kein neues Zusammentreffen, Alter waechst weiter) bleibt BESTEHEN trotz Gewicht < Schwelle")
    if gewicht_ef_nach_pause is not None:
        check(gewicht_ef_nach_pause < SCHWELLE_DEFAULT,
              f"/e-/f Gewicht ist jetzt unter Schwelle {SCHWELLE_DEFAULT} gefallen (war {gewicht_ef_nach_pause:.3f}), "
              f"trotzdem noch in der DB (Existenz != Schwelle)")
        check(gewicht_ef_nach_pause < gewicht_neu_ef,
              f"/e-/f Gewicht ist gegenueber Lauf 4 weiter gesunken ({gewicht_neu_ef:.3f} -> {gewicht_ef_nach_pause:.3f})")
    check(any({r[0], r[1]} == {"/c", "/d"} for r in rows5), "/c-/d bleibt (kuerzlich bestaetigt, noch ueber Schwelle)")

    # Lauf 6 (Gegenrichtung -- neue Bestaetigung hebt das Gewicht einer laengst bestehenden,
    # unter die Schwelle gesunkenen Kante wieder an; es ist eine Aktualisierung, keine Neuanlage):
    with open(log_path2, "a", encoding="utf-8") as f:
        f.write(json.dumps({"nodes": ["/e", "/f"], "lessons": []}) + "\n")
        f.write(json.dumps({"nodes": ["/e", "/f"], "lessons": []}) + "\n")
    ergebnis6 = lauf(log_path2, db_path2, SCHWELLE_DEFAULT, apply=True, halbwertszeit=HALBWERTSZEIT_TEST)
    conn = sqlite3.connect(str(db_path2))
    rows6 = conn.execute(
        "SELECT source_path,target_path,weight FROM knowledge_relations ORDER BY source_path"
    ).fetchall()
    conn.close()
    gewicht_ef_zurueck = next((r[2] for r in rows6 if {r[0], r[1]} == {"/e", "/f"}), None)
    check(ergebnis6["angelegt"] == 0, f"Rueckkehr ist eine Aktualisierung, keine Neuanlage, war angelegt={ergebnis6['angelegt']}")
    check(gewicht_ef_zurueck is not None and gewicht_ef_zurueck > gewicht_ef_nach_pause,
          f"/e-/f Gewicht steigt nach zwei frischen Bestaetigungen wieder ({gewicht_ef_nach_pause} -> {gewicht_ef_zurueck})")

    # Lauf 7: Loeschbefehl trifft nur den eigenen Typ, eine fremde Kante bleibt
    conn = sqlite3.connect(str(db_path))
    fremd_now = now
    conn.execute(
        """INSERT INTO knowledge_relations
           (id,source_path,target_path,relation_type,confidence,weight,evidence,source,
            creator,model,session,created_at,updated_at)
           VALUES ('R-fremd','/a','/d','constrains',0.8,1.0,'von Hand','betreiber',
                   'betreiber',NULL,NULL,?,?)""",
        (fremd_now, fremd_now),
    )
    conn.commit()
    conn.close()

    kms.DB_PATH = db_path
    loesch_dry = loesche(db_path, apply=False)
    conn = sqlite3.connect(str(db_path))
    n_dry = conn.execute("SELECT COUNT(*) FROM knowledge_relations").fetchone()[0]
    conn.close()
    check(loesch_dry["gefunden"] == 2, f"Loesch-Trockenlauf findet 2 eigene Kanten, war {loesch_dry['gefunden']}")
    check(n_dry == 3, f"Loesch-Trockenlauf loescht nichts, weiter 3 Kanten (2 eigene+1 fremd), war {n_dry}")

    loesch_apply = loesche(db_path, apply=True)
    conn = sqlite3.connect(str(db_path))
    rest = conn.execute("SELECT relation_type,source FROM knowledge_relations").fetchall()
    conn.close()
    check(loesch_apply["geloescht"] == 2, f"Loeschung entfernt 2 eigene Kanten, war {loesch_apply['geloescht']}")
    check(len(rest) == 1 and rest[0] == ("constrains", "betreiber"),
          f"nur die fremde Kante bleibt, war {rest}")

    shutil.rmtree(tmp_dir, ignore_errors=True)
    print("SELFTEST " + ("BESTANDEN" if ok else "FEHLGESCHLAGEN"))
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--schwelle", type=int, default=SCHWELLE_DEFAULT,
                   help=f"Mindestgewicht nach Zerfall (Vorgabe {SCHWELLE_DEFAULT})")
    p.add_argument("--halbwertszeit", type=float, default=HALF_LIFE_EVENTS_DEFAULT,
                   help=f"Halbwertszeit des Zerfalls in Ereignissen (Vorgabe {HALF_LIFE_EVENTS_DEFAULT})")
    p.add_argument("--apply", action="store_true", help="Schreibt Kanten (Vorgabe: nur --dry-run)")
    p.add_argument("--dry-run", action="store_true", help="Nur planen, nichts schreiben (Vorgabe)")
    p.add_argument("--delete", action="store_true",
                   help="Loescht nur eigene Kanten (relation_type=analogous_to, source=hebb_kanten.py). "
                        "Ohne --apply nur Anzahl anzeigen.")
    p.add_argument("--selftest", action="store_true", help="Selbsttest mit temporaerer DB/Log")
    p.add_argument("--log", type=Path, default=RECALL_LOG)
    p.add_argument("--db", type=Path, default=kms.DB_PATH)
    args = p.parse_args()

    if args.selftest:
        return _selftest()

    apply = args.apply and not args.dry_run
    if not args.db.exists():
        print(f"FEHLER: {args.db} nicht gefunden.")
        return 1

    if args.delete:
        loesche(args.db, apply)
        return 0

    if not args.log.exists():
        print(f"FEHLER: {args.log} nicht gefunden.")
        return 1

    lauf(args.log, args.db, args.schwelle, apply, args.halbwertszeit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
