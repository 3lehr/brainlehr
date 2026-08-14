#!/usr/bin/env python3
"""kanten_herkunft_rueckwirkend.py -- rueckwirkend Kanten 'abgeleitet_von'
aus woertlichen Verweisen im Knotentext.

AUFTRAG 73 Schritt 1 (docs/PLAN_HERKUNFTSKETTE_2026-08-13.md). Im Plan
entschieden, nicht hier neu zu entscheiden: Herkunft wird als KANTENTYP in
knowledge_relations gefuehrt, nicht als Spalte -- die Spalte
knowledge_nodes.abgeleitet_von traegt nur EINEN Vorgaenger, abgeleitetes
Wissen hat fast immer mehrere, und sie ist ein zweiter Ort fuer eine
Tatsache, fuer die es mit knowledge_relations bereits eine Tabelle gibt.

WAS DIESES WERKZEUG TUT: den Bestand nach woertlichen Verweisen absuchen --
eine Zeichenkette im Format L-xxxxxx (Lehre) oder acht Hex-Zeichen (Knoten-
ID) im Titel/Summary/Content eines Knotens -- und daraus eine Kante
'abgeleitet_von' machen: Quelle ist der zitierende Knoten, Ziel die
zitierte Lehre oder der zitierte Knoten (der zitierende Knoten ist DARAUS
abgeleitet). Gemessen 2026-08-13: 83 Knoten nennen eine existierende Lehre,
56 einen existierenden Knoten, 14 beides -- 125 von 2165. Das ist die
POSITIVKONTROLLE dieses Werkzeugs, nicht sein Ziel.

WAS ES NICHT TUT: die uebrigen rund 2040 Knoten ueber Sitzungsnaehe oder
Bedeutungsaehnlichkeit "auffuellen". Eine geratene Herkunft ist schlechter
als eine leere: ein leeres Feld sagt "unbekannt", ein falsch gefuelltes
sagt "belegt". Nur der woertliche Verweis zaehlt.

UNBELEGT vs. ERFUNDEN (dieselbe Unterscheidung wie in kern/normbezug.py,
dort fuer Normzitate): Eine Zeichenkette im Format L-xxxxxx, die es im
Bestand nicht gibt, ist keine bloss fehlende Quelle, sondern ein
Fehltreffer -- sie wird gemeldet, nicht in eine Kante verwandelt und nicht
stillschweigend uebergangen.

WARUM NICHT ueber kern/speicher.schreiben(): dessen Transaktion schaltet
PRAGMA foreign_keys=ON. knowledge_relations.source_path/target_path
referenzieren per FK knowledge_nodes.path -- eine Lehre hat aber keinen
Knotenpfad, nur eine eigene ID (L-xxxxxx). Genau dieselbe Lage besteht
bereits bei relation_type='lesson_mentions_file' (source_path dort eine
Lehren-ID, kein Knotenpfad) und wird dort ebenso mit einer schlichten
sqlite3-Verbindung ohne FK-Durchsetzung geschrieben (kern/kanten_aus_lehren.py).
Dieses Werkzeug folgt derselben, bereits etablierten Konvention -- der
Datenbankpfad kommt trotzdem ausschliesslich aus kern/speicher (ort.DB),
nie fest verdrahtet.

Aufruf:
    python3 kern/kanten_herkunft_rueckwirkend.py            # Trockenlauf
    python3 kern/kanten_herkunft_rueckwirkend.py --write     # schreibt Kanten
    python3 kern/kanten_herkunft_rueckwirkend.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import argparse
import re
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path

import speicher  # noqa: E402 -- liefert den DB-Pfad (speicher.ort.DB), siehe Modulkopf
import zeitmarke  # noqa: E402

RELATION_TYPE = "abgeleitet_von"

# 8 Hex-Zeichen, wie kern/ausweis.py & Co. Knoten-IDs vergeben.
_NODE_ID = re.compile(r"\b[0-9a-f]{8}\b")
# Lehren-Kennung, dieselbe Bauform wie in kern/normbezug.py::_HAUSNORM.
_LESSON_ID = re.compile(r"\bL-[0-9a-fA-F]{6}\b")


@dataclass(frozen=True)
class Kandidat:
    source_path: str   # Pfad des zitierenden Knotens
    target: str         # Pfad des zitierten Knotens ODER Lehren-ID
    ziel_art: str        # "lehre" | "knoten"
    roh: str


def _text(row: sqlite3.Row) -> str:
    return " ".join(str(row[f] or "") for f in ("title", "summary", "content"))


def sammle(conn: sqlite3.Connection) -> tuple[list[Kandidat], list[dict]]:
    """Durchsucht alle Knoten nach woertlichen Verweisen.

    Rueckgabe (Kandidaten, Erfundene). Erfundene sind Zeichenketten im
    Format L-xxxxxx, die im Text stehen, aber im Bestand keine Lehre
    treffen -- siehe Modulkopf, UNBELEGT vs. ERFUNDEN.
    """
    knoten = conn.execute(
        "SELECT id, path, title, summary, content FROM knowledge_nodes"
    ).fetchall()
    id_zu_path = {r["id"]: r["path"] for r in knoten}
    lehren_ids = {r[0] for r in conn.execute("SELECT id FROM lessons_learned")}

    kandidaten: list[Kandidat] = []
    erfunden: list[dict] = []
    gesehen_erfunden: set[tuple[str, str]] = set()

    for row in knoten:
        text = _text(row)
        eigene_id = row["id"]
        # set() dedupliziert je Knoten: derselbe Verweis zweimal im Text
        # erzeugt nicht zweimal dieselbe Kante (UNIQUE(source,target,typ)
        # wuerde das ohnehin auffangen, hier zusaetzlich fuer die Zaehlung).
        ziele: set[tuple[str, str, str]] = set()

        for m in _LESSON_ID.finditer(text):
            kennung = m.group(0)
            if kennung in lehren_ids:
                ziele.add((kennung, "lehre", kennung))
            else:
                schluessel = (row["id"], kennung)
                if schluessel not in gesehen_erfunden:
                    gesehen_erfunden.add(schluessel)
                    erfunden.append({"knoten_id": row["id"],
                                      "knoten_path": row["path"],
                                      "kennung": kennung})

        for m in _NODE_ID.finditer(text):
            kennung = m.group(0)
            if kennung == eigene_id:
                continue  # Selbstbezug -- keine Kante auf sich selbst (siehe Modulkopf)
            ziel_path = id_zu_path.get(kennung)
            if ziel_path is not None and ziel_path != row["path"]:
                ziele.add((ziel_path, "knoten", kennung))

        for target, ziel_art, roh in ziele:
            kandidaten.append(Kandidat(row["path"], target, ziel_art, roh))

    return kandidaten, erfunden


def schreibe(conn: sqlite3.Connection, kandidaten: list[Kandidat]) -> int:
    """Legt Kanten an (INSERT OR IGNORE -- UNIQUE(source,target,typ) macht
    einen zweiten Lauf wirkungslos, nicht doppelt). Gibt die Zahl der neu
    angelegten Kanten zurueck."""
    jetzt = zeitmarke.jetzt()
    neu = 0
    for k in kandidaten:
        cur = conn.execute(
            "INSERT OR IGNORE INTO knowledge_relations "
            "(id, source_path, target_path, relation_type, confidence, weight, "
            " evidence, source, creator, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), k.source_path, k.target, RELATION_TYPE,
             0.9, 1.0, f"woertlicher Verweis im Knotentext: {k.roh}",
             "kanten_herkunft_rueckwirkend.py", "mechanik", jetzt, jetzt))
        neu += cur.rowcount
    return neu


def _db_pfad() -> Path:
    return speicher.ort.DB


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--write", action="store_true",
                    help="Kanten tatsaechlich anlegen (sonst Trockenlauf)")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()

    if args.selftest:
        _selftest()
        return 0

    pfad = _db_pfad()
    with speicher.lesen(pfad) as conn:
        kandidaten, erfunden = sammle(conn)
        vorher = conn.execute(
            "SELECT COUNT(*) FROM knowledge_relations WHERE relation_type = ?",
            (RELATION_TYPE,)).fetchone()[0]

    print(f"gefundene Verweise: {len(kandidaten)} "
          f"(Lehre: {sum(1 for k in kandidaten if k.ziel_art == 'lehre')}, "
          f"Knoten: {sum(1 for k in kandidaten if k.ziel_art == 'knoten')})")
    print(f"Kanten '{RELATION_TYPE}' vorher: {vorher}")

    if erfunden:
        print(f"ERFUNDEN -- {len(erfunden)} Zeichenkette(n) im Format L-xxxxxx "
              f"ohne Treffer im Bestand, keine Kante erzeugt:")
        for e in erfunden:
            print(f"  {e['knoten_path']} ({e['knoten_id']}) nennt {e['kennung']}")

    if not args.write:
        print(f"Trockenlauf -- kein Schreibvorgang. --write zum Anlegen.")
        return 0

    conn = sqlite3.connect(str(pfad))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN IMMEDIATE")
        neu = schreibe(conn, kandidaten)
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()

    with speicher.lesen(pfad) as conn:
        nachher = conn.execute(
            "SELECT COUNT(*) FROM knowledge_relations WHERE relation_type = ?",
            (RELATION_TYPE,)).fetchone()[0]
    print(f"neu angelegt: {neu}. Kanten '{RELATION_TYPE}' nachher: {nachher}")
    return 0


# --- Selbsttest --------------------------------------------------------------

def _bauvorrichtung(conn: sqlite3.Connection) -> None:
    schema = (_w / "schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.commit()


def _knoten(conn: sqlite3.Connection, id_: str, path: str, title: str,
            summary: str = "", content: str | None = None) -> None:
    jetzt = zeitmarke.jetzt()
    conn.execute(
        """INSERT INTO knowledge_nodes
           (id, path, parent_path, project_id, title, summary, content, source,
            anlass, norm_entscheidung, norm_entschieden_von, norm_entschieden_am,
            norm_entschieden_grund, created_at, updated_at)
           VALUES (?, ?, NULL, 'shared', ?, ?, ?, 'test', 'skript',
                   'keine_norm', 'test', ?, 'Testvorrichtung, keine echte Norm-Pruefung',
                   ?, ?)""",
        (id_, path, title, summary, content, jetzt, jetzt, jetzt))


def _lehre(conn: sqlite3.Connection, id_: str, description: str) -> None:
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description) VALUES (?, 'insight', ?)",
        (id_, description))


def _selftest() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _bauvorrichtung(conn)

    _lehre(conn, "L-abc123", "Testlehre")
    _knoten(conn, "aaaaaaaa", "/test/vorgaenger", "Vorgaenger", "Ausgangsknoten")
    # zitiert die Lehre UND den Vorgaenger-Knoten -- der Fall "beides" (14 von 125)
    _knoten(conn, "bbbbbbbb", "/test/nachfolger", "Nachfolger",
            "Baut auf L-abc123 und Knoten aaaaaaaa auf")
    # Selbstbezug: nennt die EIGENE ID -- darf keine Kante auf sich selbst erzeugen
    _knoten(conn, "cccccccc", "/test/selbstbezug", "Selbstbezug",
            "Verweist versehentlich auf cccccccc")
    # ohne jeden Verweis -- der Negativfall
    _knoten(conn, "dddddddd", "/test/ohne_verweis", "Ohne Verweis",
            "Ganz normaler Text ohne Kennung")
    # erfundene Lehre -- Grenzwert: gemeldet, keine Kante
    _knoten(conn, "eeeeeeee", "/test/erfunden", "Erfunden",
            "Beruft sich auf L-ffffff, die es nicht gibt")
    conn.commit()

    kandidaten, erfunden = sammle(conn)
    by_source = {}
    for k in kandidaten:
        by_source.setdefault(k.source_path, []).append(k)

    # --- Positivfall: Lehre und Knoten, beides an einem Knoten -------------
    ziele_nachfolger = {(k.target, k.ziel_art) for k in by_source["/test/nachfolger"]}
    assert ziele_nachfolger == {("L-abc123", "lehre"), ("/test/vorgaenger", "knoten")}, \
        ziele_nachfolger

    # --- Selbstbezug erzeugt KEINE Kante ------------------------------------
    assert "/test/selbstbezug" not in by_source, \
        "Selbstbezug hat eine Kante erzeugt -- das darf nicht sein"

    # --- Negativfall: kein Verweis, keine Kante -----------------------------
    assert "/test/ohne_verweis" not in by_source, \
        "ein Verfahren, das ueberall etwas findet, findet nichts"

    # --- Grenzwert: erfundene Lehre wird gemeldet, nicht verschluckt -------
    assert "/test/erfunden" not in by_source, "erfundene Lehre wurde als Kante uebernommen"
    assert any(e["kennung"] == "L-ffffff" and e["knoten_path"] == "/test/erfunden"
               for e in erfunden), erfunden

    # --- Schreiben: Kanten landen in knowledge_relations, zweiter Lauf 0 ---
    vorher = conn.execute(
        "SELECT COUNT(*) FROM knowledge_relations WHERE relation_type = ?",
        (RELATION_TYPE,)).fetchone()[0]
    assert vorher == 0
    neu = schreibe(conn, kandidaten)
    assert neu == len(kandidaten) == 2, (neu, kandidaten)
    nachher = conn.execute(
        "SELECT COUNT(*) FROM knowledge_relations WHERE relation_type = ?",
        (RELATION_TYPE,)).fetchone()[0]
    assert nachher == 2, nachher

    neu2 = schreibe(conn, kandidaten)
    assert neu2 == 0, "zweiter Lauf hat erneut Kanten angelegt"
    nachher2 = conn.execute(
        "SELECT COUNT(*) FROM knowledge_relations WHERE relation_type = ?",
        (RELATION_TYPE,)).fetchone()[0]
    assert nachher2 == 2, nachher2

    conn.close()
    print("kanten_herkunft_rueckwirkend.py: Selbsttest gruen")


if __name__ == "__main__":
    raise SystemExit(main())
