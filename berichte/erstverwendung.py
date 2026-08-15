#!/usr/bin/env python3
"""erstverwendung.py -- Auftrag 2026-08-09 (Betreiber-Freigabe): Entscheidung
bei der ERSTEN VERWENDUNG statt beim Import.

Fremdbestand (z.B. die 1638 NASA-LLIS-Knoten, migrate_gattung.py) kommt mit
norm_entscheidung='offen' herein -- 1638 Entscheidungen fuer historisch 3
Abrufe waeren Verschwendung. Dieses Werkzeug beantwortet fuer EINEN Knoten
(oder, im Bericht, fuer den ganzen offenen Bestand): was laesst sich
ableiten, was muss ein Mensch setzen. Es SCHREIBT NICHTS -- reiner Vorschlag,
lesend gegen die DB (SQLite-URI mode=ro erzwingt das zusaetzlich zur reinen
Programmlogik).

SELBSTLAUF-VERMERK (Aufgabe wirkkette-6, 2026-08-15): Zwei getrennte
Rollen, beide ohne eigene Ereignis-Verdrahtung noetig. (1) Als CLI
(--bericht/--vorschlag) ist es ein von Hand aufgerufenes Berichtswerkzeug --
sein Ergebnis ist eine Terminal-Ausgabe zum Lesen, kein Abruf, der irgendwo
im Hintergrund haengt; ein Selbstlauf ruft kein Berichtswerkzeug von sich aus
auf, das waere Vortaeuschung einer Automatisierung, die niemand verlangt hat.
(2) Als Bibliothek (`norm_ableiten` importiert von
haken/knowledge_recall_hook.py) gilt derselbe Befund wie bei
haken/suchpfad_abruf.py: die Ereignisse erbt es vom Aufrufer, eine eigene
Verdrahtung waere doppelt gemoppelt.

ZWEI ABLEITUNGEN, BEIDE DETERMINISTISCH AUS EINEM MERKMAL:

1. gattung <- source (Herkunft, nicht Inhalt). Eine externe URL in source
   heisst: das Werk existierte, bevor es hier abgelegt wurde -- Nachschlage-
   werk, bis widersprochen wird (gleiche Haltung wie migrate_gattung.py fuer
   die NASA-Sammlung, hier aber herkunftsgetrieben statt eine feste Liste
   bekannter Quellen). Kein Nachschlagewerk-Signal -> Vorgabe der Spalte
   selbst greift (arbeitsbestand), keine Aenderung noetig.

2. norm_entscheidung <- Satzbau von title+summary+content. Zwei Merkmale,
   je fuer sich klar zu pruefen:
     - Modalverb (muss/soll/darf/kann/...): Anzeichen von SOLLEN/DUERFEN,
       nicht von SEIN.
     - Geltungsangabe (gilt ab/bis, in Kraft, verbindlich, ...): Anzeichen,
       dass der Satz ueber seine eigene Bindungsdauer spricht.
   Nur wenn BEIDES fehlt, ist der Satz rein beschreibend -> keine_norm.

FEHLURTEIL-PREIS, beide Richtungen (das ist der Grund fuer die UND-Schranke
oben, nicht Bequemlichkeit):
  - Norm faelschlich als 'keine_norm' abgelegt: die Bindungswirkung geht
    STILL verloren -- der Satz faellt aus jeder Widerspruchs-/Konfliktpruefung
    (knowledge_lint.py) heraus, ohne dass es auffaellt. Bemerkt wird es erst,
    wenn die Norm gebraucht und nicht gefunden wird -- der teure Fall.
  - Tatsache faelschlich NICHT abgeleitet (als Vorschlag an den Menschen
    ausgewiesen, obwohl es eigentlich ein Fakt ist): kostet eine unnoetige
    Rueckfrage bei der ersten Verwendung. Sichtbar, billig, eine Sekunde
    Lesezeit.
  Die Erkennung ist darum zweiseitig vorsichtig: im Zweifel (Modalverb ODER
  Geltungsangabe vorhanden) wird NICHT abgeleitet, sondern an den Menschen
  gegeben.

norm_rang faellt nie unter Punkt 1: er beantwortet WER etwas erlassen hat,
das steht in keinem der beiden Merkmale und nicht im Text ueberhaupt.

Betriebsarten:
    python3 erstverwendung.py --vorschlag <id-oder-pfad> [--db PFAD]
    python3 erstverwendung.py --bericht [--db PFAD]
    python3 erstverwendung.py --selftest
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

# Liegt eine Ebene unter der Wurzel: die Wurzel muss auf den Suchpfad,
# sonst findet `import knowledge_mcp_server` nichts. Muster aus haken/.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).parent.parent  # eine Ebene tiefer seit dem Umzug 2026-08-10
DEFAULT_DB = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (HERE / "brainlehr.db"))

# Wortgrenzen-Suche, Kleinschreibung -- ein Treffer als Teilstring reicht,
# keine Grammatikanalyse (waere Ermessen, nicht Ableitung).
MODALVERBEN = (
    "muss", "müssen", "muß", "soll", "sollen", "darf", "dürfen",
    "kann", "können", "hat zu", "haben zu", "ist verpflichtet",
    "sind verpflichtet", "wird verpflichtet", "ist untersagt",
    "sind untersagt",
)
GELTUNGS_MARKER = (
    "gilt ab", "gilt bis", "gültig ab", "gültig bis", "in kraft",
    "tritt in kraft", "verbindlich", "ab dem", "bis zum",
)
_WORT = lambda m: re.compile(r"(?<![\wäöüß])" + re.escape(m) + r"(?![\wäöüß])")

URL_MUSTER = re.compile(r"https?://", re.IGNORECASE)


def get_conn(db_path: Path) -> sqlite3.Connection:
    """Nur-lesend: SQLite-URI mode=ro verweigert jeden Schreibversuch auf
    DB-Ebene, nicht nur weil dieses Skript keine INSERT/UPDATE-Aufrufe
    enthaelt."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _treffer(text: str, kandidaten: tuple[str, ...]) -> list[str]:
    text_l = text.lower()
    return [k for k in kandidaten if _WORT(k).search(text_l)]


def textmerkmale(title: str, summary: str, content: str | None) -> dict:
    text = " ".join(t for t in (title, summary, content) if t)
    modal = _treffer(text, MODALVERBEN)
    geltung = _treffer(text, GELTUNGS_MARKER)
    return {"modalverb_treffer": modal, "geltung_treffer": geltung}


def gattung_ableiten(source: str | None) -> tuple[str, str]:
    """(vorschlag, begruendung). Haengt ausschliesslich an source, s.
    Moduldoc Punkt 1 -- der Inhalt des Knotens spielt keine Rolle."""
    if source and URL_MUSTER.search(source):
        return "nachschlagewerk", f"source nennt eine externe URL ({source!r}) -- Fremdbestand"
    return "arbeitsbestand", "keine externe URL in source -- Spaltenvorgabe bleibt gueltig"


def norm_ableiten(title: str, summary: str, content: str | None) -> dict:
    """Liefert entweder eine Ableitung (norm_entscheidung='keine_norm') oder
    einen Vorschlag mit Grund, was der Mensch setzen muesste. Nie beides."""
    merkmale = textmerkmale(title, summary, content)
    modal, geltung = merkmale["modalverb_treffer"], merkmale["geltung_treffer"]

    if not modal and not geltung:
        return {
            "ableitbar": True,
            "norm_entscheidung": "keine_norm",
            "begruendung": "kein Modalverb, keine Geltungsangabe -- rein beschreibender Satz",
            "stuetzt_sich_auf": "keine_merkmale",
        }
    if modal:
        return {
            "ableitbar": False,
            "grund": "Modalverb gefunden (%s) -- moegliche Norm, kein Fakt" % ", ".join(modal),
            "mensch_muss_setzen": [
                "norm_entscheidung (norm_befristet/norm_unbefristet)",
                "norm_rang (WER hat es erlassen -- steht nicht im Text)",
                "gilt_ab/gilt_bis",
            ],
            "stuetzt_sich_auf": "modalverb",
        }
    # geltung ohne modal: widerspruechlich, nicht rein beschreibend, aber
    # auch kein eindeutiges Normsignal -- an den Menschen.
    return {
        "ableitbar": False,
        "grund": "Geltungsangabe (%s) ohne Modalverb -- widerspruechliches Muster" % ", ".join(geltung),
        "mensch_muss_setzen": [
            "norm_entscheidung -- pruefen, ob tatsaechlich eine Norm gemeint ist",
            "norm_rang, falls ja",
        ],
        "stuetzt_sich_auf": "geltung_ohne_modal",
    }


def analysiere(row: sqlite3.Row) -> dict:
    if row["norm_entscheidung"] != "offen":
        return {"bereits_eingeordnet": True, "norm_entscheidung": row["norm_entscheidung"]}

    gattung_vorschlag, gattung_grund = gattung_ableiten(row["source"])
    norm = norm_ableiten(row["title"], row["summary"], row["content"])
    return {
        "bereits_eingeordnet": False,
        "id": row["id"],
        "path": row["path"],
        "gattung": {"vorschlag": gattung_vorschlag, "begruendung": gattung_grund},
        "norm": norm,
    }


# --- Betriebsarten ----------------------------------------------------------

def _fetch(conn: sqlite3.Connection, kennung: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, path, title, summary, content, source, gattung, norm_entscheidung "
        "FROM knowledge_nodes WHERE id = ? OR path = ?",
        (kennung, kennung),
    ).fetchone()


def cmd_vorschlag(db_path: Path, kennung: str) -> int:
    conn = get_conn(db_path)
    row = _fetch(conn, kennung)
    conn.close()
    if row is None:
        print(f"FEHLER: Knoten nicht gefunden: {kennung}")
        return 1

    ergebnis = analysiere(row)
    if ergebnis["bereits_eingeordnet"]:
        print(f"{kennung}: bereits eingeordnet (norm_entscheidung={ergebnis['norm_entscheidung']!r}) -- nichts zu tun.")
        return 0

    print(f"Knoten {ergebnis['id']} ({ergebnis['path']})")
    print(f"  gattung -> {ergebnis['gattung']['vorschlag']}  ({ergebnis['gattung']['begruendung']})")
    norm = ergebnis["norm"]
    if norm["ableitbar"]:
        print(f"  norm_entscheidung -> {norm['norm_entscheidung']}  ({norm['begruendung']}) [ableitbar]")
    else:
        print(f"  norm_entscheidung -> NICHT ableitbar: {norm['grund']}")
        print("  der Mensch muss setzen:")
        for feld in norm["mensch_muss_setzen"]:
            print(f"    - {feld}")
    return 0


def cmd_bericht(db_path: Path) -> int:
    conn = get_conn(db_path)
    rows = conn.execute(
        "SELECT id, path, title, summary, content, source, gattung, norm_entscheidung "
        "FROM knowledge_nodes WHERE norm_entscheidung = 'offen'"
    ).fetchall()
    conn.close()

    gesamt = len(rows)
    ableitbar = 0
    gruende: dict[str, int] = {}
    gattung_extern = 0
    for row in rows:
        norm = norm_ableiten(row["title"], row["summary"], row["content"])
        if norm["ableitbar"]:
            ableitbar += 1
            gruende["keine_merkmale (keine_norm ableitbar)"] = gruende.get(
                "keine_merkmale (keine_norm ableitbar)", 0) + 1
        else:
            key = norm["stuetzt_sich_auf"]
            gruende[key] = gruende.get(key, 0) + 1
        if gattung_ableiten(row["source"])[0] == "nachschlagewerk":
            gattung_extern += 1

    print(f"=== erstverwendung --bericht ({db_path}) ===")
    print(f"offene Knoten gesamt: {gesamt}")
    print(f"davon maschinell ableitbar (keine_norm): {ableitbar}")
    print(f"davon brauchen einen Menschen: {gesamt - ableitbar}")
    print("aufgeschluesselt nach Grund:")
    for grund, n in sorted(gruende.items(), key=lambda kv: -kv[1]):
        print(f"  {grund}: {n}")
    print(f"gattung-Ableitung nennt 'nachschlagewerk' (externe URL in source) bei: {gattung_extern}")
    return 0


# --- Selbsttest --------------------------------------------------------------

def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        # ponytail: keine volle schema.sql-Nachbildung (Trigger dort blockieren
        # sogar das gezielte Anlegen von 'offen'-Zeilen fuer den Testfall, s.
        # schema.sql-Kommentar an norm_entscheidung -- Altbestand entsteht nur
        # per ALTER TABLE, nicht per INSERT). Dieses Skript liest nur acht
        # Spalten; eine Schattentabelle mit genau diesen Spalten reicht, um
        # SEINE Logik zu pruefen, nicht die des Schemas selbst (die deckt
        # migrate_gattung.py/schema.sql bereits ab).
        db_path = Path(tmp) / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE knowledge_nodes (id TEXT, path TEXT, title TEXT, summary TEXT, "
            "content TEXT, source TEXT, gattung TEXT, norm_entscheidung TEXT)"
        )
        conn.executemany(
            "INSERT INTO knowledge_nodes VALUES (?,?,?,?,?,?,?,?)",
            [
                # (a) beschreibender Satz ohne Modalverb -> ableitbar keine_norm.
                ("a", "/t/a", "Messung", "Der Sensor lieferte 23 Grad.", None,
                 "eigene Beobachtung", "arbeitsbestand", "offen"),
                # (b) Satz mit Modalverb -> NICHT ableitbar, Mensch entscheidet.
                ("b", "/t/b", "Regel", "Jede Aenderung muss protokolliert werden.", None,
                 "eigene Beobachtung", "arbeitsbestand", "offen"),
                # (c) Fremdherkunft (URL) -> gattung nachschlagewerk.
                ("c", "/t/c", "LLIS-Eintrag", "Beschreibung eines NASA-Vorfalls.", None,
                 "https://nen.nasa.gov/web/11/viewall/1", "arbeitsbestand", "offen"),
                # (d) widerspruechlich: Geltungsangabe ohne Modalverb -> Vorschlag.
                ("d", "/t/d", "Frist", "Diese Regelung gilt ab dem 1. Januar.", None,
                 "eigene Beobachtung", "arbeitsbestand", "offen"),
                # (e) bereits eingeordnet -> wird nicht angefasst.
                ("e", "/t/e", "Erledigt", "Ein Fakt.", None,
                 "eigene Beobachtung", "arbeitsbestand", "keine_norm"),
            ],
        )
        conn.commit()
        conn.close()

        conn = get_conn(db_path)

        row_a = _fetch(conn, "a")
        erg_a = analysiere(row_a)
        assert erg_a["norm"]["ableitbar"] is True, erg_a
        assert erg_a["norm"]["norm_entscheidung"] == "keine_norm", erg_a
        print("Fall (a) OK: beschreibender Satz -> keine_norm ableitbar.")

        row_b = _fetch(conn, "b")
        erg_b = analysiere(row_b)
        assert erg_b["norm"]["ableitbar"] is False, erg_b
        assert "norm_rang" in " ".join(erg_b["norm"]["mensch_muss_setzen"])
        print("Fall (b) OK: Modalverb -> menschliche Entscheidung, nicht abgeleitet.")

        row_c = _fetch(conn, "c")
        erg_c = analysiere(row_c)
        assert erg_c["gattung"]["vorschlag"] == "nachschlagewerk", erg_c
        print("Fall (c) OK: Fremdherkunft (URL) -> gattung nachschlagewerk.")

        row_d = _fetch(conn, "d")
        erg_d = analysiere(row_d)
        assert erg_d["norm"]["ableitbar"] is False, erg_d
        assert erg_d["norm"]["stuetzt_sich_auf"] == "geltung_ohne_modal", erg_d
        print("Fall (d) OK: widerspruechliche Merkmale -> Vorschlag statt Ableitung.")

        row_e = _fetch(conn, "e")
        erg_e = analysiere(row_e)
        assert erg_e["bereits_eingeordnet"] is True, erg_e
        print("Fall (e) OK: bereits eingeordneter Knoten wird nicht angefasst.")

        conn.close()

    print("SELFTEST OK: alle fuenf Pflichtfaelle bestanden.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--vorschlag", metavar="ID-ODER-PFAD")
    parser.add_argument("--bericht", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return _selftest()
    if args.vorschlag:
        return cmd_vorschlag(args.db, args.vorschlag)
    if args.bericht:
        if not args.db.exists():
            print(f"FEHLER: {args.db} nicht gefunden.")
            return 1
        return cmd_bericht(args.db)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
