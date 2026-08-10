#!/usr/bin/env python3
"""abrufversagen.py -- rueckblickende Pruefung: wurde eine Lehre neu

geschrieben, obwohl eine aehnliche schon im Bestand lag UND der
automatische Abruf DIESER Sitzung sie geliefert hatte, aber ignoriert
wurde (a) -- oder lag sie im Bestand, wurde aber vom Abruf gar nicht
geliefert (b, BELEGTER FEHLSCHLAG)?

Anlassfall (Auftrag 2026-08-09): fahrtenbuch-Sitzung 2026-08-08, fuenf von
sechs neu erarbeiteten Befunden lagen als Lehre bereits vor (L-aa4995,
L-8b4799, L-cbb443, L-319e01, L-05e18b, L-4750fc). Bisher fiel so etwas nur
auf, wenn ein Mensch zufaellig nachfragte.

Nur LESEN -- kein Eingriff in knowledge_mcp_server.py oder den Recall-Haken
(beide tabu laut Auftrag). Aehnlichkeitsmass wird von dort *wiederverwendet*
(_tokenize/SIMILARITY_THRESHOLD), nicht neu gebaut -- zwei Mass e nebeneinander
liefen sonst garantiert auseinander.

Vier Ausgaenge je Lehre mit Sitzungskennung:
  a) aehnliche Lehre existierte VOR ihrer Erfassung UND wurde vom Abruf
     dieser Sitzung geliefert -> jemand hat trotzdem neu geschrieben.
     Anderes Problem, nicht das des Abrufs.
  b) aehnliche Lehre existierte VOR ihrer Erfassung, wurde aber vom Abruf
     dieser Sitzung NICHT geliefert -> BELEGTER FEHLSCHLAG des Abrufs.
  c) keine aehnliche Lehre existierte vorher -> echtes neues Wissen.
  d) keine Abruf-Protokollzeile fuer diese Sitzung gefunden -> unbekannt,
     NICHT b) (der Haken protokolliert nur bei Treffern; eine fehlende
     Zeile heisst "nichts protokolliert", nicht "nichts geliefert").

Nenner werden immer mitgesprochen (Auftrag, Auflage 3): "X von Y Lehren mit
Sitzungskennung, davon Z mit Abrufprotokoll" -- nie eine nackte Zahl.

Recall-Log liegt PRO ARBEITSBAUM (haken/ort.py: RECALL_LOG = WURZEL /
"recall_log.jsonl", nicht ueber BEGOD_KNOWLEDGE_DB steuerbar) -- eine Sitzung
kann in einem anderen Arbeitsbaum geloggt haben als dem, in dem dieses
Modul laeuft. Darum werden alle recall_log.jsonl unter dem Projekt-Wurzel-
verzeichnis (Hauptcheckout + .claude/worktrees/*) zusammengefuehrt, per
Zeileninhalt dedupliziert (Arbeitsbaeume werden beim Anlegen mit der bis
dahin gewachsenen Datei "gestartet", die Praefixe sind sonst mehrfach).

Aufruf:
    .venv/bin/python abrufversagen.py            # Lauf gegen den echten Bestand
    .venv/bin/python abrufversagen.py --selftest  # kuenstlicher Bestand, alle 4 Ausgaenge
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "haken"))
sys.path.insert(0, str(HERE))
import ort  # noqa: E402 -- haken/ort.py, liefert DB/WURZEL
import knowledge_mcp_server as kms  # noqa: E402 -- NUR _tokenize/SIMILARITY_THRESHOLD, kein Serveraufruf

A_GELIEFERT_TROTZDEM_NEU = "a_geliefert_trotzdem_neu_geschrieben"
B_BELEGTER_FEHLSCHLAG = "b_belegter_fehlschlag_des_abrufs"
C_ECHTES_NEUES_WISSEN = "c_echtes_neues_wissen"
D_SITZUNG_OHNE_PROTOKOLL = "d_sitzung_ohne_abrufprotokoll"


def _projekt_wurzel(start: Path) -> Path:
    """Hauptcheckout, auch wenn `start` selbst schon ein Arbeitsbaum ist
    (.claude/worktrees/<name>) -- dort liegen die GESCHWISTER-Arbeitsbaeume,
    deren recall_log.jsonl sonst uebersehen wird."""
    teile = start.resolve().parts
    if ".claude" in teile and "worktrees" in teile:
        i = teile.index(".claude")
        return Path(*teile[:i])
    return start.resolve()


def _recall_logs(projekt_wurzel: Path) -> list[Path]:
    kandidaten = [projekt_wurzel / "recall_log.jsonl"]
    kandidaten += sorted((projekt_wurzel / ".claude" / "worktrees").glob("*/recall_log.jsonl"))
    return [p for p in kandidaten if p.is_file()]


def _lade_recall_zeilen(pfade: list[Path]) -> list[dict]:
    """Alle Zeilen aus allen gefundenen recall_log.jsonl, per Rohzeile
    dedupliziert (Arbeitsbaeume teilen eine gemeinsame Vorgeschichte)."""
    gesehen: set[str] = set()
    zeilen: list[dict] = []
    for pfad in pfade:
        for rohzeile in pfad.read_text(encoding="utf-8").splitlines():
            rohzeile = rohzeile.strip()
            if not rohzeile or rohzeile in gesehen:
                continue
            gesehen.add(rohzeile)
            try:
                zeilen.append(json.loads(rohzeile))
            except json.JSONDecodeError:
                continue
    return zeilen


def _sitzung_lieferungen(zeilen: list[dict]) -> dict[str, set[str]]:
    """session -> Menge aller je in dieser Sitzung gelieferten Lehren-IDs
    (ueber alle Protokollzeilen dieser Sitzung hinweg)."""
    out: dict[str, set[str]] = {}
    for z in zeilen:
        session = z.get("session")
        if not session:
            continue
        out.setdefault(session, set()).update(z.get("lessons") or [])
    return out


def _hat_sitzung_protokoll(zeilen: list[dict]) -> set[str]:
    """Sitzungen, fuer die UEBERHAUPT eine recall_log-Zeile existiert --
    unabhaengig davon, ob dabei Lehren geliefert wurden. Trennt Auflage 2
    (kein Protokoll != nichts geliefert) sauber von b)."""
    return {z["session"] for z in zeilen if z.get("session")}


def _parse_zeit(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _aehnlichste_vorherige_lehre(conn: sqlite3.Connection, neue_zeile: sqlite3.Row) -> dict | None:
    """Wie kms._find_similar_lesson, aber zusaetzlich zeitlich eingeschraenkt:
    nur Lehren, deren first_seen VOR der first_seen der neuen Lehre liegt
    (Auftrag Auflage 1 -- sonst zaehlt jede spaetere Doppelung rueckwirkend).
    Gleicher Typ, gleiche Tokenisierung/Schwelle wie im Server -- absichtlich
    dieselbe Funktion (_tokenize/SIMILARITY_THRESHOLD), keine zweite Messung."""
    neue_zeit = _parse_zeit(neue_zeile["first_seen"])
    needle = kms._tokenize(neue_zeile["description"])
    if not needle:
        return None
    best = None
    for row in conn.execute(
        "SELECT id, first_seen, description FROM lessons_learned WHERE type = ? AND id != ?",
        (neue_zeile["type"], neue_zeile["id"]),
    ):
        vorherige_zeit = _parse_zeit(row["first_seen"])
        if neue_zeit is not None and vorherige_zeit is not None and vorherige_zeit >= neue_zeit:
            continue  # Auflage 1: nur echt aeltere Lehren zaehlen
        hay = kms._tokenize(row["description"])
        if not hay:
            continue
        score = len(needle & hay) / len(needle | hay)
        if score >= kms.SIMILARITY_THRESHOLD and (best is None or score > best["score"]):
            best = {"id": row["id"], "first_seen": row["first_seen"], "score": round(score, 2)}
    return best


def pruefe(conn: sqlite3.Connection, recall_zeilen: list[dict]) -> dict:
    lieferungen = _sitzung_lieferungen(recall_zeilen)
    protokolliert = _hat_sitzung_protokoll(recall_zeilen)

    neue_lehren = conn.execute(
        "SELECT id, session, first_seen, type, description FROM lessons_learned "
        "WHERE session IS NOT NULL AND session != '' ORDER BY first_seen"
    ).fetchall()

    faelle = {A_GELIEFERT_TROTZDEM_NEU: [], B_BELEGTER_FEHLSCHLAG: [],
              C_ECHTES_NEUES_WISSEN: [], D_SITZUNG_OHNE_PROTOKOLL: []}

    for lehre in neue_lehren:
        aehnlich = _aehnlichste_vorherige_lehre(conn, lehre)
        if aehnlich is None:
            faelle[C_ECHTES_NEUES_WISSEN].append({"lehre": lehre["id"], "session": lehre["session"]})
            continue

        eintrag = {
            "neue_lehre": lehre["id"], "session": lehre["session"],
            "first_seen": lehre["first_seen"], "aehnliche_lehre": aehnlich["id"],
            "aehnliche_lehre_first_seen": aehnlich["first_seen"], "score": aehnlich["score"],
        }

        if lehre["session"] not in protokolliert:
            faelle[D_SITZUNG_OHNE_PROTOKOLL].append(eintrag)
            continue

        geliefert = aehnlich["id"] in lieferungen.get(lehre["session"], set())
        if geliefert:
            faelle[A_GELIEFERT_TROTZDEM_NEU].append(eintrag)
        else:
            faelle[B_BELEGTER_FEHLSCHLAG].append(eintrag)

    return {
        "nenner_lehren_mit_sitzung": len(neue_lehren),
        "nenner_sitzungen_mit_protokoll": len({l["session"] for l in neue_lehren if l["session"] in protokolliert}),
        "faelle": faelle,
    }


def bericht(ergebnis: dict) -> str:
    n = ergebnis["nenner_lehren_mit_sitzung"]
    m = ergebnis["nenner_sitzungen_mit_protokoll"]
    f = ergebnis["faelle"]
    zeilen = [
        f"{n} Lehren mit Sitzungskennung, davon {m} mit Abrufprotokoll fuer ihre Sitzung.",
        f"a) geliefert, trotzdem neu geschrieben: {len(f[A_GELIEFERT_TROTZDEM_NEU])}",
        f"b) BELEGTER FEHLSCHLAG des Abrufs:      {len(f[B_BELEGTER_FEHLSCHLAG])}",
        f"c) echtes neues Wissen:                 {len(f[C_ECHTES_NEUES_WISSEN])}",
        f"d) Sitzung ohne Abrufprotokoll (unbekannt): {len(f[D_SITZUNG_OHNE_PROTOKOLL])}",
    ]
    if f[B_BELEGTER_FEHLSCHLAG]:
        zeilen.append("Faelle b) im Einzelnen:")
        for e in f[B_BELEGTER_FEHLSCHLAG]:
            zeilen.append(
                f"  {e['neue_lehre']} (Sitzung {e['session']}, {e['first_seen']}) "
                f"wiederholt {e['aehnliche_lehre']} ({e['aehnliche_lehre_first_seen']}, score {e['score']})"
            )
    return "\n".join(zeilen)


def _selftest() -> None:
    """Kuenstlicher Bestand mit allen vier Ausgaengen + den zwei Negativfaellen
    aus dem Auftrag (Zeitpunkt, Kategorie)."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE lessons_learned (
        id TEXT PRIMARY KEY, session TEXT, first_seen TEXT, type TEXT, description TEXT)""")

    def einfuegen(id_, session, first_seen, typ, beschreibung):
        conn.execute("INSERT INTO lessons_learned VALUES (?,?,?,?,?)",
                     (id_, session, first_seen, typ, beschreibung))

    # Fall a): aehnliche Lehre existiert vorher, Abruf lieferte sie, trotzdem neu geschrieben.
    einfuegen("L-alt-a", None, "2026-01-01T00:00:00+00:00", "antipattern",
              "async dispose ohne await verliert Fehler beim Aufraeumen")
    einfuegen("L-neu-a", "sitzung-a", "2026-01-05T00:00:00+00:00", "antipattern",
              "async dispose ohne await verliert Fehler beim Aufraeumen")

    # Fall b): aehnliche Lehre existiert vorher, Abruf-Protokoll fuer die Sitzung
    # existiert, lieferte sie aber NICHT -> belegter Fehlschlag.
    einfuegen("L-alt-b", None, "2026-01-01T00:00:00+00:00", "error",
              "Silent-Buffering vor Fahrt-Bestaetigung verliert Vorlauf-Kilometer")
    einfuegen("L-neu-b", "sitzung-b", "2026-01-05T00:00:00+00:00", "error",
              "Silent-Buffering vor Fahrt-Bestaetigung verliert Vorlauf-Kilometer")

    # Fall c): keine aehnliche Lehre vorher -> echtes neues Wissen.
    einfuegen("L-neu-c", "sitzung-c", "2026-01-05T00:00:00+00:00", "insight",
              "voellig anderes Thema, Kanuverleih-Oeffnungszeiten am Fluss")

    # Fall d): aehnliche Lehre existiert vorher, aber KEIN Protokoll fuer die
    # Sitzung -> unbekannt, nicht b).
    einfuegen("L-alt-d", None, "2026-01-01T00:00:00+00:00", "pattern",
              "Retry mit exponentiellem Backoff bei Netzwerkfehlern einbauen")
    einfuegen("L-neu-d", "sitzung-d", "2026-01-05T00:00:00+00:00", "pattern",
              "Retry mit exponentiellem Backoff bei Netzwerkfehlern einbauen")

    # Negativfall Zeitpunkt: L-spaeter existiert erst NACH L-neu-a2 -- darf
    # bei L-neu-a2 nicht als "vorherige aehnliche Lehre" zaehlen.
    einfuegen("L-neu-a2", "sitzung-a2", "2026-01-05T00:00:00+00:00", "insight",
              "Kontrastwert wird aus Tokens berechnet, nie als Zahl fest verdrahtet")
    einfuegen("L-spaeter", None, "2026-01-06T00:00:00+00:00", "insight",
              "Kontrastwert wird aus Tokens berechnet, nie als Zahl fest verdrahtet")

    recall_zeilen = [
        {"session": "sitzung-a", "lessons": ["L-alt-a"]},
        {"session": "sitzung-b", "lessons": ["L-irgendwas-anderes"]},  # protokolliert, liefert L-alt-b NICHT
        {"session": "sitzung-c", "lessons": []},
        # sitzung-d: KEINE Zeile -> Kategorie d).
        {"session": "sitzung-a2", "lessons": []},
    ]

    ergebnis = pruefe(conn, recall_zeilen)
    f = ergebnis["faelle"]

    def enthaelt(kategorie, lehre_id):
        return any(e["neue_lehre"] == lehre_id for e in f[kategorie])

    assert enthaelt(A_GELIEFERT_TROTZDEM_NEU, "L-neu-a"), "Fall a) nicht erkannt"
    assert enthaelt(B_BELEGTER_FEHLSCHLAG, "L-neu-b"), "Fall b) nicht erkannt"
    assert any(e["lehre"] == "L-neu-c" for e in f[C_ECHTES_NEUES_WISSEN]), "Fall c) nicht erkannt"
    assert enthaelt(D_SITZUNG_OHNE_PROTOKOLL, "L-neu-d"), "Fall d) nicht erkannt"
    # Negativfall Zeitpunkt: L-neu-a2 darf NICHT als Wiederholung erkannt werden
    # (die aehnliche Lehre L-spaeter kam erst danach) -> muss c) sein.
    assert any(e["lehre"] == "L-neu-a2" for e in f[C_ECHTES_NEUES_WISSEN]), \
        "Zeitpunkt-Negativfall verletzt: spaetere Lehre zaehlte rueckwirkend"
    # Kategorie-Negativfall: sitzung-d hat kein Protokoll -> NICHT in b).
    assert not enthaelt(B_BELEGTER_FEHLSCHLAG, "L-neu-d"), \
        "Kategorie-Negativfall verletzt: fehlendes Protokoll als Fehlschlag gezaehlt"

    assert ergebnis["nenner_lehren_mit_sitzung"] == 5

    print("Selbsttest ok: alle vier Ausgaenge + beide Negativfaelle bestehen.")


def main() -> None:
    if "--selftest" in sys.argv:
        _selftest()
        return

    projekt_wurzel = _projekt_wurzel(HERE)
    recall_pfade = _recall_logs(projekt_wurzel)
    recall_zeilen = _lade_recall_zeilen(recall_pfade)

    conn = sqlite3.connect(f"file:{ort.DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    ergebnis = pruefe(conn, recall_zeilen)
    print(f"Bestand: {ort.DB}")
    print(f"Recall-Protokolle: {', '.join(str(p) for p in recall_pfade) or '(keine gefunden)'}")
    print()
    print(bericht(ergebnis))


if __name__ == "__main__":
    main()
