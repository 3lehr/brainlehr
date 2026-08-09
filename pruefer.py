#!/usr/bin/env python3
"""Der erste Melder, der URTEILT statt zaehlt.

Anlass: Der Betreiber vermisste am 2026-08-09, dass sich Pruefer von selbst
melden -- frueher habe ein Skeptiker-Agent auf Dogmen hingewiesen. Die
Recherche ergab (L-479171): er hat NIE autonom gefeuert. Er war Schritt 3
einer von Hand gestarteten Pipeline, und die "ACTIVATION: proaktiv"-Zeilen
im Frontmatter waren Prosa fuer ein Modell, kein Mechanismus.

Die Lage ist trotzdem besser als damals: heute feuern 23 Haken autonom. Es
fehlt nicht an Autonomie, sondern daran, dass einer ein URTEIL faellt.

DER UNTERSCHIED, auf den es ankommt: Ein Melder vergleicht eine Schwelle
("18 Tage alt", "12 ohne Vermerk"). Ein Pruefer sagt, dass etwas SCHIEF
STEHT, obwohl keine Zahl ueberschritten ist. Das ist heikler, weil es
Fehlalarme gibt -- darum drei Auflagen fuer jede Pruefung hier:

  1. Sie muss sich aus dem Bestand MESSEN lassen, nicht aus Stimmung.
  2. Sie nennt, welcher Fehlklasse sie nachgeht -- ein Befund ohne
     Fehlklasse ist eine Meinung.
  3. Sie nennt den Preis eines Fehlalarms. Wer den nicht beziffern kann,
     hat die Pruefung nicht zu Ende gedacht.

Und sie schweigt, solange nichts anschlaegt. Ein Pruefer, der bei jedem
Start dasselbe sagt, wird ueberlesen -- dann faellt er genauso aus wie
einer, den es nicht gibt.

Aufruf:
    python3 pruefer.py             # alle Pruefungen, ausfuehrlich
    python3 pruefer.py --melder    # nur sprechen, wenn etwas anschlaegt
    python3 pruefer.py --selftest
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "haken"))
import ort  # noqa: E402

# Woran ein KI-Entscheider erkennbar ist. Gleiche Liste wie in der
# Herkunftsschranke (schema.sql) -- bewusst hier wiederholt und nicht
# importiert, weil dieses Modul ohne Server und ohne Schemazugriff laufen
# koennen muss (Regel aus S7: jeder Lesepfad ohne den Server).
KI_MARKER = ("claude", "gpt", "gemini", "anthropic", "opus", "sonnet", "haiku")

# Ab wann eine Quote ueberhaupt etwas bedeutet. Unter dieser Zahl ist jede
# Prozentangabe Rauschen -- 2 von 3 sind 67 Prozent und sagen nichts.
MINDESTZAHL = 20


def _verbindung(db: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db or ort.DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def selbstzuschreibung(conn: sqlite3.Connection) -> dict | None:
    """Wieviele Normentscheidungen hat sich die Maschine selbst gegeben?

    FEHLKLASSE: stille Selbstermaechtigung. Eine Maschine, die ihre eigenen
    Aussagen fuer verbindlich erklaert, erzeugt eine Geltung ohne
    Gegenueber -- und niemandem faellt es auf, weil jede einzelne
    Entscheidung fuer sich plausibel aussieht.

    PREIS EINES FEHLALARMS: gering. Der Befund fordert kein Handeln, er
    macht eine Verteilung sichtbar. Wer ihn ignoriert, verliert nichts;
    wer ihm folgt, sieht sich 33 Zeilen an.

    Gemessen 2026-08-09 vor dem Bau: 62 von 72. Heute haette kein Melder
    das gesagt -- der Betreiber hat es selbst gefunden."""
    zeilen = conn.execute(
        "SELECT norm_entschieden_von FROM knowledge_nodes "
        "WHERE norm_rang IS NOT NULL AND zurueckgezogen = 0"
    ).fetchall()
    n = len(zeilen)
    if n < MINDESTZAHL:
        return None
    ki = sum(1 for z in zeilen
             if any(m in (z["norm_entschieden_von"] or "").lower() for m in KI_MARKER))
    anteil = ki / n
    if anteil < 0.5:
        return None
    return {
        "pruefung": "selbstzuschreibung",
        "befund": f"{ki} von {n} Normentscheidungen ({anteil:.0%}) hat ein KI-Akteur sich selbst gegeben",
        "fehlklasse": "stille Selbstermaechtigung -- Geltung ohne Gegenueber",
        "fehlalarm_kostet": "gering: der Befund fordert kein Handeln, er macht eine Verteilung sichtbar",
    }


def stumme_spalte(conn: sqlite3.Connection, spalte: str, zweck: str,
                  nur_normen: bool = True) -> dict | None:
    """Eine Spalte mit definiertem Zweck, die zu 100 Prozent leer steht.

    FEHLKLASSE: gebaute Regel ohne Wirkung. Sie sieht im Quelltext aus wie
    Schutz und unterscheidet nichts -- dieselbe Signatur wie ein Schema
    ohne Schreiber (vier Tokenspalten ueber 2167 Zeilen NULL) und wie der
    Skeptiker, dessen Ausloeser Prosa war (L-479171).

    PREIS EINES FEHLALARMS: gering, aber nicht null -- eine Spalte kann
    absichtlich leer sein (Altbestand, der nie geraten werden soll). Darum
    nennt der Befund den ZWECK mit, damit sich das beurteilen laesst.

    Nur bei 100 Prozent, nicht bei 90: eine teilweise gefuellte Spalte
    wirkt wenigstens dort, wo sie gefuellt ist. Der Sprung von 'wirkt nie'
    auf 'wirkt manchmal' ist der Unterschied, um den es geht."""
    wo = "WHERE norm_rang IS NOT NULL AND zurueckgezogen = 0" if nur_normen else "WHERE zurueckgezogen = 0"
    r = conn.execute(
        f"SELECT COUNT(*) n, SUM({spalte} IS NULL OR TRIM({spalte})='') leer "
        f"FROM knowledge_nodes {wo}"
    ).fetchone()
    n, leer = r["n"] or 0, r["leer"] or 0
    if n < MINDESTZAHL or leer != n:
        return None
    return {
        "pruefung": f"stumme_spalte:{spalte}",
        "befund": f"{spalte} ist bei allen {n} betroffenen Zeilen leer",
        "fehlklasse": f"gebaute Regel ohne Wirkung -- Zweck laut Schema: {zweck}",
        "fehlalarm_kostet": "gering: eine Spalte darf absichtlich leer sein, der Zweck steht daneben",
    }


def alle(conn: sqlite3.Connection) -> list[dict]:
    funde = [
        selbstzuschreibung(conn),
        stumme_spalte(conn, "norm_art",
                      "Sein/Sollen/Duerfen -- zwei Normen verschiedener Art konkurrieren nicht"),
    ]
    return [f for f in funde if f]


def _selftest() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE knowledge_nodes (norm_rang INTEGER, norm_art TEXT,
                    norm_entschieden_von TEXT, zurueckgezogen INTEGER DEFAULT 0)""")

    def fuelle(n, wer, art=None, rang=1, zurueck=0):
        for _ in range(n):
            conn.execute("INSERT INTO knowledge_nodes VALUES (?,?,?,?)", (rang, art, wer, zurueck))

    # Negativfall zuerst und er ist der wichtigste: unter der Mindestzahl
    # schweigt die Pruefung, auch bei 100 Prozent. Sonst meldet sie bei
    # zwei Zeilen einen Missstand.
    fuelle(3, "claude-code/opus-5")
    assert selbstzuschreibung(conn) is None, "unter der Mindestzahl wird nicht geurteilt"

    fuelle(30, "claude-code/opus-5")
    f = selbstzuschreibung(conn)
    assert f and "33 von 33" in f["befund"], f
    assert f["fehlklasse"] and f["fehlalarm_kostet"], "Fehlklasse und Preis sind Pflicht"

    # Gegenprobe: kippt die Mehrheit auf Menschen, schweigt die Pruefung.
    fuelle(40, "markus")
    assert selbstzuschreibung(conn) is None, "bei menschlicher Mehrheit kein Befund"

    # Zurueckgezogene zaehlen nicht mit.
    fuelle(100, "claude-code/opus-5", zurueck=1)
    assert selbstzuschreibung(conn) is None, "zurueckgezogene Zeilen duerfen nicht kippen"

    # Stumme Spalte: 100 Prozent meldet, 99 Prozent nicht.
    conn2 = sqlite3.connect(":memory:"); conn2.row_factory = sqlite3.Row
    conn2.execute("""CREATE TABLE knowledge_nodes (norm_rang INTEGER, norm_art TEXT,
                     norm_entschieden_von TEXT, zurueckgezogen INTEGER DEFAULT 0)""")
    for _ in range(25):
        conn2.execute("INSERT INTO knowledge_nodes VALUES (1, NULL, 'x', 0)")
    assert stumme_spalte(conn2, "norm_art", "z") is not None
    conn2.execute("INSERT INTO knowledge_nodes VALUES (1, 'sollen', 'x', 0)")
    assert stumme_spalte(conn2, "norm_art", "z") is None, "teilweise gefuellt ist kein Befund"

    print("selftest ok (7 Faelle)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--melder", action="store_true", help="nur sprechen, wenn etwas anschlaegt")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--db", type=Path, default=None)
    a = p.parse_args()
    if a.selftest:
        _selftest()
        return
    conn = _verbindung(a.db)
    funde = alle(conn)
    conn.close()

    if a.melder:
        if funde:
            zeilen = [f"{f['befund']} ({f['fehlklasse']})" for f in funde]
            print("⚠️ Pruefer: " + "\n   ".join(zeilen))
        return

    if not funde:
        print("Pruefer: nichts anzumerken.")
        return
    for f in funde:
        print(f"[{f['pruefung']}] {f['befund']}")
        print(f"   Fehlklasse:  {f['fehlklasse']}")
        print(f"   Fehlalarm:   {f['fehlalarm_kostet']}")


if __name__ == "__main__":
    main()
