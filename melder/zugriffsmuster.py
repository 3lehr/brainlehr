#!/usr/bin/env python3
"""Ungewoehnliche Zugriffsmuster auf den Wissensbestand -- BDW-E25.

DIE SACHE (Auftrag D, docs/PLAN_BETRIEBSPROFILE_2026-08-20.md): Gegen den,
der eine rohe Kopie der Datenbankdatei zieht, hilft keine Verschluesselung --
er umgeht jede Schnittstelle. Was bleibt, ist, es zu BEMERKEN. `access_log`
(actor, session, node_path, action, timestamp) traegt die noetigen Daten
bereits, es muss nichts Neues gesammelt werden.

GEMESSEN, bevor gebaut wurde -- und das Ergebnis widerlegt das naheliegende
Signal. Menge (viele Zeilen) taugt NICHT: die auffaelligste Sitzung im
Bestand (`d695fd29`, 5024 Zeilen) ist die harmloseste -- sie hat dieselben
~215 Knoten immer wieder gelesen (23,4 Zeilen je Knoten). Ein Melder auf
"viele Zugriffe" haette den Falschen erwischt.

ZWEI MERKMALE TRENNEN, beide aus access_log, gemeinsam gebraucht:
  * Zugriffe je Knoten (`zeilen(session) / verschiedene_knoten(session)`).
    Normale Arbeit wiederholt sich (gemessen 5,5 bis 23,4). Ein Abzug liest
    jeden Eintrag EINMAL -- Faktor nahe 1. Das ist die UMKEHRUNG des naiven
    Signals: ein NIEDRIGER Wert ist der Verdacht, kein hoher.
  * Abdeckung (`verschiedene_knoten(session) / knowledge_nodes gesamt`).
    Die breiteste Sitzung im Bestand beruehrte 214 von 5240 Knoten = 4,1 %.
    In 20 Tagen Betrieb kam niemand auch nur in die Naehe von 10 %.

Erst BEIDE Merkmale gemeinsam -- niedriger Faktor UND hohe Abdeckung --
sind der Befund. Je einzeln genommen waere jedes fuer sich zu grob: ein
Skript, das dieselben zehn Knoten hundertmal abfragt, hat einen hohen
Faktor trotz Wiederholung; ein Mensch, der an einem Tag zufaellig viele
verschiedene, aber nur einmal beruehrte Knoten liest, haette sonst einen
niedrigen Faktor ohne Abzugsabsicht.

VERWORFEN, weil gemessen unbrauchbar: "Lesevorgaenge je Suche" -- `search`
wird ohne `node_path` protokolliert, das Verhaeltnis liegt bei fast allen
Sitzungen bei 0,0 und waere im Melder stilles Rauschen.

DEFINITION "Zugriffe je Knoten" -- ABWEICHUNG VOM AUFTRAGSTEXT, siehe
Meldung: nachgerechnet mit ALLEN Aktionen der Sitzung (jede `action`,
geteilt durch verschiedene `node_path`) kommt man auf 23,4/7,1/5,5 -- nahe an
den im Auftrag genannten 24,2/7,9/5,1 (Rest ist rund 1 Tag Bestandswachstum
seit der Planmessung vom 2026-08-20). ABER: diese Rechnung zaehlt `update`
und `add` mit -- also SCHREIBENDE Aktionen -- in den Nenner der
"Lese"-Kennzahl. Beim Bau gefunden: Sitzung `d40bc0e8` (754 `update`-Zeilen
einer Massenmigration in 38 Minuten, 380 Knoten) landet damit bei Faktor 2,04
und Abdeckung 7,3 % -- der naechste Fehlalarm-Kandidat ueberhaupt, obwohl sie
keine einzige `read`-Zeile enthaelt. Ein Angreifer, der ueber die
Schnittstelle LIEST, erzeugt keine `update`-Zeilen; eine Migration erzeugt
keine Leseabsicht. Beide in einen Topf zu werfen waere die Fehlerklasse aus
CLAUDE.md ("Der Pruefstand misst mit") in neu: eine Zahl, die gut aussieht,
weil sie zufaellig ein falsches Merkmal einschliesst.

Gezaehlt wird deshalb NUR `action IN ('read','browse','search')` UND
`node_path IS NOT NULL` (eine `search`-Zeile ohne `node_path` sagt nicht,
WELCHEN Knoten jemand gesehen hat, und bleibt darum aussen vor -- siehe
"verworfen" oben). Damit sinkt `d40bc0e8` auf 2 Lesezeilen/1 Knoten und faellt
weit unter jede Schwelle. Die drei Auftrags-Beispiele liegen mit dieser
Definition bei 12,1/4,1/2,7 (Faktor) und 3,8/4,1/2,6 % (Abdeckung, gerundet)
statt bei 24,2/7,9/5,1 -- die groessere Abweichung vom Auftragstext, gemeldet
wie verlangt: sie kommt daher, dass der Auftragstext schreibende Aktionen
mitzaehlt, dieser Melder bewusst nicht.

SCHWELLEN, gewaehlt mit grossem Abstand zum gemessenen Rand (kein Aufwand,
sondern siehe unten -- eine spaetere Nachmessung darf sie verschieben).
Gemessen ueber ALLE 97 Sitzungen mit mindestens einer Lesezeile (nicht nur
die drei Beispiele), mit der Lese-Definition oben:
  JE_KNOTEN_SCHWELLE = 2.0   -- Sitzungen mit Faktor nahe 1,0 im echten
                                Bestand sind ausnahmslos winzig (2-11
                                Lesezeilen, Abdeckung < 0,3 %) -- die
                                Abdeckungsschwelle faengt sie ohnehin ab.
                                Ein Abzug traegt exakt Faktor 1,0.
  ABDECKUNG_SCHWELLE = 0.10  -- gemessener Rand des Bestands: 4,1 % (Faktor
                                2,4 drunter). Ein Abzug ueber 500 von 5240
                                Knoten traegt 9,5 %.
Beide Schwellen sind SCHAETZUNGEN mit Sicherheitsabstand, keine Messung wie
der 0,65-Wert aus CLAUDE.md -- es gibt (gemaess Auftrag) im Bestand keinen
einzigen Positivfall, an dem sich eine echte Schwelle kalibrieren liesse.
Das ist die Luecke aus AC1: ohne eine HERGESTELLTE Positivkontrolle waere
dieser Melder von einem kaputten nicht zu unterscheiden.

HINWEISRECHT, KEIN VETO: dieses Skript endet immer mit Code 0 bei `--pruefen`
ohne Befund und mit Code 1, sobald mindestens eine Sitzung beide Schwellen
reisst -- der Rueckgabewert ist die Abnahmeform (`AC1: MUSS anschlagen`),
kein Abbruch fuer den Aufrufer.

WO DIESER MELDER HAENGEN MUESSTE (noch NICHT verdrahtet -- siehe
`melder/ausloeserlos.py`, der genau das meldet): Er passt zu keinem der
etablierten Ausloeser. "auf-abruf" waere falsch -- eine Auslesung braucht
niemanden, der zufaellig fragt. Kandidaten:
  1. `melder/bewegungsmelder.py`: LAEUFER-Eintrag ergaenzen (Parser fuer
     "N Sitzung(en) ueber der Schwelle"), dann faellt eine neu auftauchende
     Verdachtssitzung als "neu erschienen" auf -- passt zur bestehenden
     taeglichen Lauf-Form.
  2. Ein eigener LaunchAgent wie `de.brainlehr.tagessicherung`
     (kern/sicherungen.py) -- taeglicher Lauf, eigenes Log.
Diese Datei entscheidet das nicht selbst und traegt sich in keine
settings.json/plist ein.

Aufruf:
    python3 melder/zugriffsmuster.py --pruefen [--db DATEIPFAD]
    python3 melder/zugriffsmuster.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import argparse
import sqlite3
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

import speicher  # noqa: E402 -- Tuer statt eigener Verbindung, siehe CLAUDE.md

JE_KNOTEN_SCHWELLE = 2.0
ABDECKUNG_SCHWELLE = 0.10


@dataclass
class Treffer:
    session: str
    zugriffe: int
    knoten: int
    je_knoten: float
    gesamt_knoten: int
    abdeckung: float

    def zeile(self) -> str:
        return (f"{self.session}: {self.zugriffe} Zugriffe auf {self.knoten} "
                f"verschiedene Knoten (je Knoten {self.je_knoten:.1f}, "
                f"Abdeckung {self.abdeckung * 100:.1f} % von {self.gesamt_knoten})")


def gesamt_knoten(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]


def kennzahlen_je_sitzung(conn: sqlite3.Connection) -> dict[str, tuple[int, int]]:
    """session -> (Lesezeilen, verschiedene node_path). NUR lesende Aktionen
    (read/browse/search) mit gesetztem node_path -- siehe Modulkopf, warum
    schreibende Aktionen (update/add/...) hier NICHT mitzaehlen. Sitzungen
    ohne jede solche Zeile liefern knoten=0 und werden von `beurteilen`
    uebersprungen -- ein Faktor durch 0 waere kein Befund, sondern ein
    Absturz."""
    ergebnis: dict[str, tuple[int, int]] = {}
    for row in conn.execute(
        """
        SELECT session, COUNT(*) AS zugriffe,
               COUNT(DISTINCT node_path) AS knoten
        FROM access_log
        WHERE session IS NOT NULL
          AND action IN ('read', 'browse', 'search')
          AND node_path IS NOT NULL
        GROUP BY session
        """
    ):
        ergebnis[row[0]] = (row[1], row[2])
    return ergebnis


def beurteilen(
    kennzahlen: dict[str, tuple[int, int]],
    gesamt: int,
    je_knoten_schwelle: float = JE_KNOTEN_SCHWELLE,
    abdeckung_schwelle: float = ABDECKUNG_SCHWELLE,
) -> list[Treffer]:
    """Reine Funktion: beide Schwellen muessen GLEICHZEITIG gerissen sein --
    niedriger Faktor (>=1, <=Schwelle) UND hohe Abdeckung (>=Schwelle)."""
    treffer: list[Treffer] = []
    if gesamt <= 0:
        return treffer
    for session, (zugriffe, knoten) in sorted(kennzahlen.items()):
        if knoten <= 0:
            continue
        je_knoten = zugriffe / knoten
        abdeckung = knoten / gesamt
        if je_knoten <= je_knoten_schwelle and abdeckung >= abdeckung_schwelle:
            treffer.append(Treffer(session, zugriffe, knoten, je_knoten, gesamt, abdeckung))
    return treffer


def pruefen(conn: sqlite3.Connection) -> list[Treffer]:
    return beurteilen(kennzahlen_je_sitzung(conn), gesamt_knoten(conn))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pruefen", action="store_true")
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--selftest", action="store_true")
    # Am Sitzungsstart schweigt der Melder, wenn nichts vorliegt -- ein
    # Mechanismus, der bei jedem Start eine Zeile 'nichts gefunden' schreibt,
    # wird nach zwei Tagen ueberlesen, und dann ueberliest man auch die Zeile,
    # die etwas sagt. --laut fuer den Handlauf, wo die Nullmeldung der Beleg
    # ist, dass ueberhaupt gemessen wurde.
    parser.add_argument("--laut", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return _selftest()

    with speicher.lesen(args.db) as conn:
        treffer = pruefen(conn)

    if not treffer:
        if args.laut:
            print("zugriffsmuster: keine Sitzung ueber beiden Schwellen "
                  f"(je Knoten <= {JE_KNOTEN_SCHWELLE}, Abdeckung >= {ABDECKUNG_SCHWELLE * 100:.0f} %).")
        return 0

    print(f"{len(treffer)} Sitzung(en) ueber beiden Schwellen:")
    for t in treffer:
        print("  " + t.zeile())
    return 1


# ─── Selftest ─────────────────────────────────────────────────────────────
# ":memory:" wie kantenstillstand.py -- eine Testkulisse ist keine Tuer zum
# Bestand, der Naht-Waechter zaehlt sie bewusst nicht mit.

def _fixture_db() -> sqlite3.Connection:
    schema = (_w / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(":memory:")
    conn.executescript(schema)
    return conn


def _insert_node(conn: sqlite3.Connection, path: str) -> None:
    conn.execute(
        """
        INSERT INTO knowledge_nodes
        (id, path, parent_path, project_id, title, summary, source, anlass,
         norm_entscheidung, norm_entschieden_von, norm_entschieden_am, norm_entschieden_grund)
        VALUES (?, ?, NULL, 'shared', ?, 'Testknoten', 'test', 'skript',
                'keine_norm', 'test', '2026-08-21T00:00:00+02:00',
                'Testvorrichtung, keine echte Norm-Pruefung')
        """,
        (str(uuid.uuid4()), path, path),
    )


def _insert_zugriffe(conn: sqlite3.Connection, session: str, node_paths: list[str | None]) -> None:
    for p in node_paths:
        conn.execute(
            "INSERT INTO access_log (node_path, action, session) VALUES (?, 'read', ?)",
            (p, session),
        )


def _bauen(gesamt_knoten_zahl: int, sitzungen: dict[str, list[str | None]]) -> sqlite3.Connection:
    conn = _fixture_db()
    for i in range(gesamt_knoten_zahl):
        _insert_node(conn, f"/n{i}")
    for session, pfade in sitzungen.items():
        _insert_zugriffe(conn, session, pfade)
    conn.commit()
    return conn


def _selftest() -> int:
    # AC1 -- POSITIVKONTROLLE: ein hergestellter Lauf ueber 500 verschiedene
    # Knoten, je EINMAL gelesen (Faktor 1,0), in einem Bestand von 520 Knoten
    # (Abdeckung 96,2 %) MUSS anschlagen.
    pfade_abzug = [f"/n{i}" for i in range(500)]
    conn = _bauen(520, {"abzug": pfade_abzug})
    treffer = pruefen(conn)
    assert len(treffer) == 1 and treffer[0].session == "abzug", treffer
    assert treffer[0].je_knoten == 1.0
    assert abs(treffer[0].abdeckung - 500 / 520) < 1e-9
    conn.close()

    # NEGATIV -- normale Arbeit: hohe Wiederholung (Faktor 24), niedrige
    # Abdeckung (10 von 520 Knoten) darf NICHT anschlagen.
    pfade_normal = [f"/n{i}" for i in range(10)] * 24
    conn = _bauen(520, {"normal": pfade_normal})
    assert pruefen(conn) == []
    conn.close()

    # NEGATIV -- die drei ECHTEN Beispielsitzungen aus dem Auftrag, mit den
    # gegen die Lese-Definition dieses Moduls nachgerechneten Kennzahlen
    # (siehe Modulkopf: 12,1/201, 4,1/214, 2,7/134 -- nicht die 24,2/7,9/5,1
    # aus dem Auftragstext, der schreibende Aktionen mitzaehlt). Hohe
    # Wiederholung, Abdeckung weit unter der Schwelle. Duerfen NICHT
    # anschlagen -- das ist AC2 im Kleinen, vor dem echten Lauf.
    for zugriffe, knoten in ((2437, 201), (888, 214), (359, 134)):
        conn = _bauen(5240, {"echt": [f"/n{i}" for i in range(knoten)] * (zugriffe // knoten)
                              + [f"/n{i}" for i in range(zugriffe % knoten)]})
        treffer = pruefen(conn)
        assert treffer == [], (zugriffe, knoten, treffer)
        conn.close()

    # GRENZWERTE Abdeckung (Schwelle 0.10, Gesamt 1000 Knoten -> Grenze bei
    # 100 Knoten). je_knoten wird bei 1.0 (weit unter seiner Schwelle)
    # gehalten, damit ausschliesslich die Abdeckung geprueft wird.
    conn = _bauen(1000, {
        "unter": [f"/n{i}" for i in range(99)],    # 9,9 % -- darf NICHT
        "genau": [f"/n{i}" for i in range(100)],   # 10,0 % -- MUSS (>=)
        "ueber": [f"/n{i}" for i in range(101)],   # 10,1 % -- MUSS
    })
    treffer = {t.session for t in pruefen(conn)}
    assert treffer == {"genau", "ueber"}, treffer
    conn.close()

    # GRENZWERTE je Knoten (Schwelle 2.0). Abdeckung wird bei 50 % (weit
    # ueber ihrer Schwelle) gehalten, damit ausschliesslich der Faktor
    # geprueft wird. 100 Knoten von insgesamt 200.
    def _sitzung(faktor: float) -> list[str]:
        n = 100
        gesamt_zeilen = round(n * faktor)
        basis = [f"/n{i}" for i in range(n)]
        return (basis * (gesamt_zeilen // n)) + basis[: gesamt_zeilen % n]

    conn = _bauen(200, {
        "drueber": _sitzung(2.1),   # Faktor 2,1 -- darf NICHT (> Schwelle)
        "genau": _sitzung(2.0),     # Faktor 2,0 -- MUSS (<=)
        "drunter": _sitzung(1.9),   # Faktor 1,9 -- MUSS
    })
    treffer = {t.session for t in pruefen(conn)}
    assert treffer == {"genau", "drunter"}, treffer
    conn.close()

    # Sitzung ganz ohne node_path (reine Suche) -- kein Absturz, kein Befund.
    conn = _bauen(100, {"nur_suche": [None, None, None]})
    assert pruefen(conn) == []
    conn.close()

    # NEGATIV -- der beim Bau gefundene Fehlalarm-Kandidat: eine
    # Massenmigration (viele 'update'-Zeilen ueber viele Knoten in kurzer
    # Zeit) sieht mit ALLEN Aktionen gezaehlt aus wie ein Abzug (Faktor 2,0,
    # Abdeckung 7,3 % im echten Fund `d40bc0e8`). Mit der Lese-Definition
    # dieses Moduls (nur read/browse/search) darf sie NICHT anschlagen, weil
    # sie keine einzige Lesezeile traegt.
    conn = _bauen(520, {"migration": []})
    for i in range(380):
        conn.execute(
            "INSERT INTO access_log (node_path, action, session) VALUES (?, 'update', ?)",
            (f"/n{i}", "migration"),
        )
    conn.commit()
    assert pruefen(conn) == []
    conn.close()

    # Leerer Bestand -- kein Absturz.
    conn = _fixture_db()
    assert pruefen(conn) == []
    conn.close()

    print("zugriffsmuster: Selbsttest gruen (Positivkontrolle 500/520 schlaegt an, "
          "normale Arbeit und die drei nachgerechneten echten Sitzungen schweigen, "
          "beide Schwellen je auf Schwelle-1/Schwelle/Schwelle+1 geprueft, "
          "sitzungslose node_path-Zeilen und leerer Bestand stuerzen nicht ab)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
