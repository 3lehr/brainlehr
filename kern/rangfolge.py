#!/usr/bin/env python3
"""rangfolge.py -- zwei zusaetzliche Rangsignale fuer den Recall (Auftrag
2026-08-08, Knoten /brainlehr/zu-tun-rangfolge-verschraenken-vier).

Der Recall (haken/knowledge_recall_hook.py) rangiert heute Knoten-Kandidaten
nach Stichwort+Bedeutung (RRF) und trust_score. Zwei vorhandene, aber
ungenutzte Signale kommen hier dazu:

  norm_rang   -- knowledge_nodes.norm_rang (1=globale CLAUDE.md, 2=hub-
                 CLAUDE.md, 3=ADR-Bestand, NULL=Fakt, keine Norm). Rang 1
                 zaehlt am meisten.
  hebb_kante  -- Summe der Kantengewichte aus knowledge_relations
                 (relation_type=analogous_to, source=hebb_kanten.py), die
                 diesen Knoten mit irgendeinem anderen verbinden. Ein gut
                 vernetzter Knoten hat sich wiederholt als gemeinsam
                 gebraucht erwiesen.

Zwei GEPRUEFTE Signale bleiben aussen vor (Auftrag, nicht einzubauen):
Wirkung (misst nur Haeufigkeit, 3 Eintraege = 78% aller Einspielungen) und
Konfidenz (misst nur den Importstichtag, 1672/2008 Knoten am selben Tag).

ADDITIV, NIE SUBTRAKTIV: combined = rank_score + NORMRANG_WEIGHT*norm_score
+ HEBB_WEIGHT*hebb_score. rank_score selbst bleibt fuer JEDEN Kandidaten
unveraendert -- ein Knoten ohne Kante und ohne Normrang (norm_score=0,
hebb_score=0) behaelt exakt seinen heutigen rank_score, faellt also nie
zurueck, egal wie stark andere Kandidaten geboostet werden (nur relative
Reihenfolge kann sich verschieben, wenn ANDERE Kandidaten ueberholen).

Abschaltbar wie ZWEITER_KANAL/ENSEMBLE_PFLICHT in knowledge_recall_hook.py:
Modul-Konstante + KNOWLEDGE_<NAME>-Umgebungsvariable ("1"/"0") uebersteuert,
gleiches Muster, keine zweite Bauform.

Aufruf aus dem Hook NUR ueber anwenden() -- die Datei selbst bleibt frei von
Ranglogik jenseits dieser beiden Signale (Monolith-Stopp in
knowledge_recall_hook.py, siehe dortiger Auftrag).

Gemessene Trefferguete vorher/nachher: siehe Bericht im Auftrag (rot-vor-
gruen mit messlauf_abrufguete.py-Bausteinen, tests/test_rangfolge.py).

Selbsttest: python3 rangfolge.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import os
import sqlite3

RELATION_TYPE = "analogous_to"
RELATION_SOURCE = "hebb_kanten.py"

# Auftrag 76: drittes Signal neben norm_rang/Hebb -- Kanten
# 'aehnlich_bedeutung' (kanten_aus_bedeutung.py), aber NUR die, deren
# hinsicht denselben Projektbereich traegt (siehe dortiges
# hinsicht_projektbereich()). Eine bereichsuebergreifende Kante
# ('projektbereich:uebergreifend') ist laut Modul-Docstring dort oft nur
# "irgendein NASA-Verfahren" -- ohne die Hinsicht waeren beide Kantenarten
# im Score ununterscheidbar (das ist die Rot-Probe, siehe
# tests/test_rangfolge.py::test_aehnlich_ohne_hinsicht_ist_blind).
AEHNLICH_RELATION_TYPE = "aehnlich_bedeutung"
AEHNLICH_SOURCE = "kanten_aus_bedeutung.py"

# --- Schalter (Muster: ZWEITER_KANAL/ENSEMBLE_PFLICHT in knowledge_recall_hook.py) ---
# VORGABE AUS, und das ist eine Entscheidung, keine Vorsicht.
#
# Gemessen 2026-08-08 am Pruefstand: kein Effekt, weder besser noch
# schlechter. Der Grund liegt aber nicht am Signal, sondern am Bestand --
# nur 82 von 2019 Knoten (4 Prozent) werden ueberhaupt von einer Kante
# beruehrt, und im Pruefkorpus ist kein einziger Zielknoten darunter. Das
# Hebb-Signal ist auf diesem Bestand also nicht PRUEFBAR, nicht wirkungslos.
#
# Ein Signal einzuschalten, dessen Nutzen man nicht messen konnte, waere
# genau die Behauptung ohne Beleg, gegen die dieses Haus gebaut ist. Also
# liegt es fertig da, abschaltbar, getestet -- und AUS, bis die Kanten aus
# Bedeutung stehen (kanten_aus_bedeutung.py). Dann wird erneut gemessen,
# und die Zahl entscheidet, nicht die Erwartung.
NORMRANG_AKTIV = False
HEBB_AKTIV = False
# Wie HEBB_AKTIV: unmessbar, solange kein Pruefkorpus-Ziel unter den
# aehnlich_bedeutung-verbundenen Knoten liegt (gleicher Befund wie beim
# Hebb-Signal oben). AUS bis zur Messung, nicht wirkungslos -- die Bauform
# selbst ist unten getestet (test_aehnlich_ohne_hinsicht_ist_blind).
AEHNLICH_AKTIV = False


def _normrang_aktiv() -> bool:
    override = os.environ.get("KNOWLEDGE_NORMRANG_AKTIV")
    if override is not None:
        return override == "1"
    return NORMRANG_AKTIV


def _hebb_aktiv() -> bool:
    override = os.environ.get("KNOWLEDGE_HEBB_AKTIV")
    if override is not None:
        return override == "1"
    return HEBB_AKTIV


def _aehnlich_aktiv() -> bool:
    override = os.environ.get("KNOWLEDGE_AEHNLICH_AKTIV")
    if override is not None:
        return override == "1"
    return AEHNLICH_AKTIV


# Gewichte (gemessen, siehe Modul-Docstring/Auftragsbericht -- nicht geraten):
# klein gehalten, weil beide Signale additiv auf rank_score (0..1) draufkommen
# und die bestehende Relevanzordnung fuehrend bleiben soll (gleiches Prinzip
# wie TRUST_WEIGHT < 0.5 im Hook: ein Treffer, der zum Prompt passt, darf
# nicht von einem Nebensignal verdraengt werden).
NORMRANG_WEIGHT = 0.15
HEBB_WEIGHT = 0.15
AEHNLICH_WEIGHT = 0.15


def norm_score(norm_rang: int | None) -> float:
    """Rang 1 (globale CLAUDE.md) -> 1.0, Rang 2 -> 0.667, Rang 3 -> 0.333,
    alles andere (NULL, Rang 4+ ohne heutigen Traeger) -> 0.0 -- neutral,
    nie negativ."""
    if norm_rang in (1, 2, 3):
        return (4 - norm_rang) / 3
    return 0.0


def hebb_gewichte(conn: sqlite3.Connection, paths: list[str]) -> dict[str, float]:
    """Summe der Kantengewichte je Pfad (Quelle+Ziel zusammen) -- eine Abfrage
    fuer die ganze Kandidatenliste, kein Query je Kandidat."""
    if not paths:
        return {}
    platzhalter = ",".join("?" * len(paths))
    rows = conn.execute(
        f"SELECT source_path, target_path, weight FROM knowledge_relations "
        f"WHERE relation_type = ? AND source = ? "
        f"AND (source_path IN ({platzhalter}) OR target_path IN ({platzhalter}))",
        (RELATION_TYPE, RELATION_SOURCE, *paths, *paths),
    ).fetchall()
    summe: dict[str, float] = {p: 0.0 for p in paths}
    for src, tgt, gewicht in rows:
        if src in summe:
            summe[src] += gewicht
        if tgt in summe:
            summe[tgt] += gewicht
    return summe


def aehnlich_gewichte(
    conn: sqlite3.Connection, paths: list[str], *, nur_gleiche_hinsicht: bool = True
) -> dict[str, float]:
    """Wie hebb_gewichte, aber ueber aehnlich_bedeutung-Kanten. Die Kosinus-
    Aehnlichkeit steht dort in `confidence`, nicht in `weight`
    (kanten_aus_bedeutung.py::schreibe_kanten schreibt weight konstant 1.0) --
    darum wird hier confidence summiert. nur_gleiche_hinsicht=True (Vorgabe) zaehlt nur
    Kanten, deren hinsicht denselben Projektbereich traegt -- eine
    bereichsuebergreifende Kante (hinsicht IS NULL oder 'projektbereich:
    uebergreifend') geht NICHT in die Summe ein.

    nur_gleiche_hinsicht=False ignoriert die Hinsicht komplett (zaehlt jede
    aehnlich_bedeutung-Kante gleich) -- existiert nur fuer die Gegenprobe in
    tests/test_rangfolge.py, dass die Hinsicht das Ergebnis tatsaechlich
    aendert und nicht nur mitgefuehrt wird."""
    if not paths:
        return {}
    platzhalter = ",".join("?" * len(paths))
    rows = conn.execute(
        f"SELECT source_path, target_path, confidence, hinsicht FROM knowledge_relations "
        f"WHERE relation_type = ? AND source = ? "
        f"AND (source_path IN ({platzhalter}) OR target_path IN ({platzhalter}))",
        (AEHNLICH_RELATION_TYPE, AEHNLICH_SOURCE, *paths, *paths),
    ).fetchall()
    summe: dict[str, float] = {p: 0.0 for p in paths}
    for src, tgt, gewicht, hinsicht in rows:
        if nur_gleiche_hinsicht and (hinsicht is None or hinsicht == "projektbereich:uebergreifend"):
            continue
        if src in summe:
            summe[src] += gewicht
        if tgt in summe:
            summe[tgt] += gewicht
    return summe


def hebb_score(gewicht: float, max_gewicht: float) -> float:
    """Normiert auf die Kandidatenliste (wie _apply_trust_score im Hook auf
    Rang statt Rohscore geht): 0 ohne Kante, 1.0 fuer den staerksten
    verbundenen Kandidaten in DIESER Liste. max_gewicht<=0 -> alle 0.0."""
    if max_gewicht <= 0:
        return 0.0
    return gewicht / max_gewicht


def anwenden(candidates: list[dict], conn: sqlite3.Connection) -> list[dict]:
    """Reiht `candidates` (bereits relevanzgeordnete Liste von Node-Dicts mit
    Schluessel 'path') anhand von norm_rang + Hebb-Kantengewicht + hinsicht-
    gleiche aehnlich_bedeutung-Kanten um. Wirkungslos (Reihenfolge
    unveraendert), wenn ALLE DREI Schalter aus sind -- Gegenprobe fuer die
    Abschaltbarkeit."""
    normrang_an = _normrang_aktiv()
    hebb_an = _hebb_aktiv()
    aehnlich_an = _aehnlich_aktiv()
    if not normrang_an and not hebb_an and not aehnlich_an:
        return candidates
    n = len(candidates)
    if n <= 1:
        return candidates

    paths = [c["path"] for c in candidates]

    norm_rang_by_path: dict[str, int | None] = {}
    if normrang_an:
        platzhalter = ",".join("?" * len(paths))
        rows = conn.execute(
            f"SELECT path, norm_rang FROM knowledge_nodes WHERE path IN ({platzhalter})",
            paths,
        ).fetchall()
        norm_rang_by_path = {r[0]: r[1] for r in rows}

    gewichte: dict[str, float] = {}
    max_gewicht = 0.0
    if hebb_an:
        gewichte = hebb_gewichte(conn, paths)
        max_gewicht = max(gewichte.values(), default=0.0)

    aehnlich_gewichte_by_path: dict[str, float] = {}
    max_aehnlich = 0.0
    if aehnlich_an:
        aehnlich_gewichte_by_path = aehnlich_gewichte(conn, paths)
        max_aehnlich = max(aehnlich_gewichte_by_path.values(), default=0.0)

    def combined(idx_item: tuple[int, dict]) -> float:
        idx, item = idx_item
        rank_score = 1 - idx / n
        zusatz = 0.0
        if normrang_an:
            zusatz += NORMRANG_WEIGHT * norm_score(norm_rang_by_path.get(item["path"]))
        if hebb_an:
            zusatz += HEBB_WEIGHT * hebb_score(gewichte.get(item["path"], 0.0), max_gewicht)
        if aehnlich_an:
            zusatz += AEHNLICH_WEIGHT * hebb_score(
                aehnlich_gewichte_by_path.get(item["path"], 0.0), max_aehnlich
            )
        return rank_score + zusatz

    geordnet = sorted(enumerate(candidates), key=combined, reverse=True)
    return [item for _, item in geordnet]


# --- Selbsttest -------------------------------------------------------------

def _selftest() -> int:
    import tempfile
    from pathlib import Path

    ok = True

    def check(bedingung: bool, text: str) -> None:
        nonlocal ok
        status = "OK" if bedingung else "FEHLER"
        print(f"  [{status}] {text}")
        if not bedingung:
            ok = False

    # norm_score: Grenzwerte der Skala
    check(norm_score(1) == 1.0, "norm_score(1) == 1.0")
    check(abs(norm_score(2) - 2 / 3) < 1e-9, "norm_score(2) == 2/3")
    check(abs(norm_score(3) - 1 / 3) < 1e-9, "norm_score(3) == 1/3")
    check(norm_score(None) == 0.0, "norm_score(None) == 0.0 (Fakt, neutral)")
    check(norm_score(4) == 0.0, "norm_score(4) == 0.0 (kein heutiger Traeger)")
    check(norm_score(0) == 0.0, "norm_score(0) == 0.0 (ausserhalb der Skala)")

    # hebb_score
    check(hebb_score(0.0, 0.0) == 0.0, "hebb_score ohne jede Kante in der Liste -> 0.0")
    check(hebb_score(2.0, 4.0) == 0.5, "hebb_score normiert auf max_gewicht der Liste")
    check(hebb_score(4.0, 4.0) == 1.0, "hebb_score des staerksten Kandidaten -> 1.0")

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "brainlehr.db"
        schema_sql = (_w / "schema.sql").read_text(encoding="utf-8")
        conn = sqlite3.connect(str(db_path))
        conn.executescript(schema_sql)
        now = "2026-08-08T00:00:00+02:00"

        def insert_node(path: str, rang: int | None, projekt: str = "shared") -> None:
            entscheidung = "keine_norm" if rang is None else "norm_unbefristet"
            gilt_ab = None if rang is None else now
            conn.execute(
                "INSERT INTO knowledge_nodes (id,path,project_id,title,summary,source,created_at,updated_at,"
                "norm_rang,gilt_ab,norm_entscheidung,norm_entschieden_von,norm_entschieden_am,norm_entschieden_grund) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (path, path, projekt, path, "Test", "selftest", now, now, rang, gilt_ab, entscheidung,
                 "skript:rangfolge.py", now, "Testvorrichtung, keine echte Norm-Pruefung"),
            )

        # 8+ Kandidaten, damit der Rangabstand (1/n) unter den vollen
        # Gewichten (je 0.15) liegt -- nur SO kann ein Signal einen NACHBARN
        # ueberholen, ohne die Relevanzfuehrung (/a bleibt immer vorn, Abstand
        # zu jedem Boost-Kandidaten viel zu gross) zu brechen.
        # /a       : kein Rang, keine Kante -- Kontrolle, muss immer vorn bleiben
        # /p1..p3  : Fuellkandidaten, kein Signal
        # /nB, /b  : Nachbarpaar fuer den Normrang-Test (/b hat Rang 1)
        # /nG, /g  : Nachbarpaar fuer den Hebb-Test (/g haengt an /aussen)
        # /nH, /h  : Nachbarpaar fuer den Aehnlich+Hinsicht-Test (/h haengt an
        #            /partner MIT gleichem Projektbereich; /nH haengt an
        #            /woanders mit ANDEREM Projektbereich -- beide Kanten
        #            gleich stark (confidence 0.9), nur die Hinsicht trennt sie)
        for p, r in (("/a", None), ("/p1", None), ("/p2", None), ("/p3", None),
                     ("/nB", None), ("/b", 1), ("/nG", None), ("/g", None), ("/aussen", None),
                     ("/nH", None), ("/h", None)):
            insert_node(p, r)
        insert_node("/partner", None, projekt="shared")     # gleicher Bereich wie /h
        insert_node("/woanders", None, projekt="fremd")     # anderer Bereich als /nH
        conn.execute(
            "INSERT INTO knowledge_relations (id,source_path,target_path,relation_type,weight,source) "
            "VALUES ('R-1','/g','/aussen','analogous_to',5.0,'hebb_kanten.py')"
        )
        conn.execute(
            "INSERT INTO knowledge_relations "
            "(id,source_path,target_path,relation_type,confidence,source,hinsicht) "
            "VALUES ('R-2','/h','/partner','aehnlich_bedeutung',0.9,'kanten_aus_bedeutung.py',"
            "'projektbereich:shared')"
        )
        conn.execute(
            "INSERT INTO knowledge_relations "
            "(id,source_path,target_path,relation_type,confidence,source,hinsicht) "
            "VALUES ('R-3','/nH','/woanders','aehnlich_bedeutung',0.9,'kanten_aus_bedeutung.py',"
            "'projektbereich:uebergreifend')"
        )
        conn.commit()

        namen = ["/a", "/p1", "/p2", "/p3", "/nB", "/b", "/nG", "/g", "/nH", "/h"]
        candidates = [{"path": p} for p in namen]

        def order(env_norm: str, env_hebb: str, env_aehnlich: str = "0") -> list[str]:
            os.environ["KNOWLEDGE_NORMRANG_AKTIV"] = env_norm
            os.environ["KNOWLEDGE_HEBB_AKTIV"] = env_hebb
            os.environ["KNOWLEDGE_AEHNLICH_AKTIV"] = env_aehnlich
            return [c["path"] for c in anwenden(list(candidates), conn)]

        # Alle Schalter aus -> wirkungslos, identische Reihenfolge (Gegenprobe Richtung 1)
        aus = order("0", "0")
        check(aus == namen, f"alle Schalter aus -> Reihenfolge unveraendert, war {aus}")

        # Nur NORMRANG an -> /b (Rang 1) ueberholt seinen unmittelbaren Nachbarn /nB.
        # Nur diesen -- die Fuellkandidaten und die anderen Nachbarpaare bleiben unberuehrt.
        nur_norm = order("1", "0")
        check(nur_norm.index("/b") < nur_norm.index("/nB"),
              f"NORMRANG an: /b (Rang 1) ueberholt /nB (kein Rang), war {nur_norm}")
        check(nur_norm.index("/nG") < nur_norm.index("/g"),
              f"NORMRANG an, HEBB aus: /g (Kante) bleibt WIRKUNGSLOS hinter /nG, war {nur_norm}")
        check(nur_norm[0] == "/a", f"/a bleibt vorn, war {nur_norm}")

        # Nur HEBB an -> /g (Kante nach /aussen) ueberholt seinen Nachbarn /nG,
        # der Normrang-Nachbar bleibt UNBERUEHRT (Gegenprobe fuer den jeweils
        # anderen Schalter).
        nur_hebb = order("0", "1")
        check(nur_hebb.index("/g") < nur_hebb.index("/nG"),
              f"HEBB an: /g (Kante) ueberholt /nG (keine Kante), war {nur_hebb}")
        check(nur_hebb.index("/nB") < nur_hebb.index("/b"),
              f"HEBB an, NORMRANG aus: /b (Rang 1) bleibt WIRKUNGSLOS hinter /nB, war {nur_hebb}")
        check(nur_hebb[0] == "/a", f"/a bleibt vorn, war {nur_hebb}")

        # Nur AEHNLICH an -> /h (Kante MIT gleicher Hinsicht) ueberholt seinen
        # Nachbarn /nH, obwohl dessen Kante (nach /woanders) genau dieselbe
        # Konfidenz traegt -- einziger Unterschied ist die Hinsicht. Das ist
        # die Kernprobe des Auftrags: ohne Hinsicht waeren beide Kanten
        # gleichwertig und /nH/​/h liefen gleichauf (siehe aehnlich_gewichte-
        # Direktprobe unten).
        nur_aehnlich = order("0", "0", "1")
        check(nur_aehnlich.index("/h") < nur_aehnlich.index("/nH"),
              f"AEHNLICH an: /h (Kante MIT gleicher Hinsicht) ueberholt /nH "
              f"(Kante, aber ANDERE Hinsicht), war {nur_aehnlich}")
        check(nur_aehnlich[0] == "/a", f"/a bleibt vorn, war {nur_aehnlich}")

        # Alle drei an -> alle Ueberholungen gleichzeitig; /a (Negativfall: kein
        # Signal) bleibt trotzdem GANZ VORN -- fuer den Kontrollkandidaten
        # aendert sich gegenueber "heute" (alle aus) nichts.
        alle = order("1", "1", "1")
        check(alle.index("/b") < alle.index("/nB"), f"alle an: /b vor /nB, war {alle}")
        check(alle.index("/g") < alle.index("/nG"), f"alle an: /g vor /nG, war {alle}")
        check(alle.index("/h") < alle.index("/nH"), f"alle an: /h vor /nH, war {alle}")
        check(alle[0] == "/a",
              f"Negativfall: /a (kein Signal) faellt gegenueber heute nicht zurueck "
              f"(bleibt vorn), war {alle}")

        # Rot-Probe / Gegenprobe (Auftrag 76, ABNAHME): OHNE die Hinsicht
        # mitzulesen sind eine gleich-projektbereichige und eine
        # projektuebergreifende Kante bei gleicher Konfidenz UNUNTERSCHEIDBAR
        # -- beide addieren sich gleichermassen. Erst mit Hinsicht trennt sich
        # /h (bekommt Gewicht) von /nH (bekommt keins).
        mit_hinsicht = aehnlich_gewichte(conn, ["/h", "/nH"], nur_gleiche_hinsicht=True)
        ohne_hinsicht = aehnlich_gewichte(conn, ["/h", "/nH"], nur_gleiche_hinsicht=False)
        check(mit_hinsicht["/h"] > 0.0 and mit_hinsicht["/nH"] == 0.0,
              f"MIT Hinsicht: /h bekommt Gewicht, /nH (andere Hinsicht) nicht, war {mit_hinsicht}")
        check(ohne_hinsicht["/h"] == ohne_hinsicht["/nH"] > 0.0,
              f"OHNE Hinsicht (Gegenprobe): beide Kanten gleich stark, /h und /nH "
              f"ununterscheidbar, war {ohne_hinsicht}")
        check(mit_hinsicht != ohne_hinsicht,
              "Hinsicht aendert das Ergebnis der Auswertung tatsaechlich (sonst waere sie Zierrat)")

        for k in ("KNOWLEDGE_NORMRANG_AKTIV", "KNOWLEDGE_HEBB_AKTIV", "KNOWLEDGE_AEHNLICH_AKTIV"):
            os.environ.pop(k, None)
        conn.close()

    print("SELFTEST " + ("BESTANDEN" if ok else "FEHLGESCHLAGEN"))
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    print(__doc__)
