#!/usr/bin/env python3
"""Die drei Achsen der Normordnung — und zwei Melder, damit sie nicht still ausfallen.

Grundlage: Knoten b6305304 (/methodik/normen-ordnen-sich-nach-drei), Rang 1,
Betreiberentscheidung 2026-08-09. Normen ordnen sich nach DREI unabhaengigen
Achsen:

  1. RANG            wer hat es erlassen (1 global, 2 hub, 3 ADR) -- in Benutzung
  2. ART             Sein / Sollen / Duerfen -- gebaut, aber LEER
  3. UNABAENDERLICHKEIT  Naturgesetz > Menschenrecht > zwischenstaatlich >
                     Einzelfall -- bewusst NICHT gebaut

Dieses Modul baut Achse 3 NICHT. Es haelt die zwei Stellen offen, an denen
die Entscheidung sonst lautlos verfaellt.

MELDER 1 -- die stumme Achse. `norm_art` wird von
knowledge_lint.py::_is_spannung ausgewertet: zwei Normen verschiedener Art
konkurrieren nicht, egal welchen Rang sie tragen. Steht die Spalte auf NULL,
faellt diese Unterscheidung aus -- nicht mit einem Fehler, sondern indem
jedes Paar als vergleichbar gilt. Gemessen 2026-08-09: 2022 von 2022 Knoten
NULL. Eine gebaute Regel, die nichts tut, ist schlimmer als eine fehlende:
sie sieht im Quelltext aus wie Schutz.

MELDER 2 -- die Abbruchbedingung der Vertagung. Achse 3 wird faellig, sobald
die erste Norm eintrifft, die NICHT aus diesem Haus stammt (Gesetz,
Gerichtsurteil, Norm einer Normungsstelle). Vorher unterscheidet sich
Unabaenderlichkeit nicht messbar, weil alles vom selben Betreiber stammt und
damit gleich widerrufbar ist. Ohne diesen Melder waere die Vertagung ein
Vielleicht statt einer Frist.

Aufruf:
    python3 normachsen.py            # beide Melder
    python3 normachsen.py --selftest
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

import argparse
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(_w / "haken"))
import ort  # noqa: E402

# Werte der Art-Achse. Bewusst NICHT per CHECK erzwungen -- gleiche Haltung
# wie bei norm_rang: die Menge ist noch nicht abschliessend belegt (siehe
# Spaltenkommentar in schema.sql).
ARTEN = ("sein", "sollen", "duerfen")

# Woran eine FREMDE Norm erkennbar ist. Bewusst eng und an der Quelle, nicht
# am Inhalt: wer den Text beurteilt, raet. Wer die Quelle liest, misst.
FREMDE_QUELLE = re.compile(
    r"\b(gesetz|verordnung|urteil|az\.|aktenzeichen|BGBl|EU-Verordnung|"
    r"Richtlinie|DIN\s|EN\s|ISO\s|IEC\s|BSI\s|WCAG|RFC\s?\d)", re.I
)


def _verbindung(db: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db or ort.DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def stumme_achse(conn: sqlite3.Connection) -> dict:
    """Normen ohne Art. Nur NORMEN -- ein Fakt braucht keine Art, so wie er
    keinen Rang braucht (Spaltenkommentar: 'ein Rang auf einem Fakt waere
    eine Ordnung, die nichts ordnet')."""
    zeilen = conn.execute(
        "SELECT COUNT(*) n, SUM(norm_art IS NULL) ohne FROM knowledge_nodes "
        "WHERE norm_rang IS NOT NULL AND zurueckgezogen = 0"
    ).fetchone()
    n, ohne = zeilen["n"] or 0, zeilen["ohne"] or 0
    return {
        "normen": n,
        "ohne_art": ohne,
        "anteil": round(ohne / n, 3) if n else None,
        "wirkung": ("_is_spannung unterscheidet nicht -- jedes Normpaar gilt als "
                    "vergleichbar, auch Sein gegen Sollen") if ohne == n and n else
                   ("teilweise wirksam" if ohne else "vollstaendig erfasst"),
    }


def fremdnormen(conn: sqlite3.Connection) -> list[dict]:
    """Normen, deren QUELLE auf eine Stelle ausserhalb dieses Hauses zeigt.
    Trifft die Abbruchbedingung der Vertagung von Achse 3."""
    fund = []
    for r in conn.execute(
        "SELECT path, norm_rang, source FROM knowledge_nodes "
        "WHERE norm_rang IS NOT NULL AND zurueckgezogen = 0 AND source IS NOT NULL"
    ):
        treffer = FREMDE_QUELLE.search(r["source"] or "")
        if treffer:
            fund.append({"path": r["path"], "rang": r["norm_rang"],
                         "merkmal": treffer.group(0).strip()})
    return fund


def bericht(conn: sqlite3.Connection) -> dict:
    stumm = stumme_achse(conn)
    fremd = fremdnormen(conn)
    return {
        "achse2_art": stumm,
        "achse3_faellig": bool(fremd),
        "fremdnormen": fremd,
        "hinweis": (
            "Achse 3 (Unabaenderlichkeit) ist FAELLIG -- eine Norm fremder Herkunft "
            "ist im Bestand, damit unterscheidet sich Widerrufbarkeit messbar. "
            "Siehe Knoten b6305304." if fremd else
            "Achse 3 bleibt vertagt -- alle Normen stammen aus diesem Haus und sind "
            "damit gleich widerrufbar. Die Vertagung traegt ihre Abbruchbedingung."
        ),
    }


def _selftest() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE knowledge_nodes (path TEXT, norm_rang INTEGER,
                    norm_art TEXT, source TEXT, zurueckgezogen INTEGER DEFAULT 0)""")

    # Negativfall zuerst: ein FAKT ohne Art darf nicht als Luecke zaehlen.
    conn.execute("INSERT INTO knowledge_nodes VALUES ('/a', NULL, NULL, 'Messung', 0)")
    assert stumme_achse(conn)["normen"] == 0, "Fakten sind keine Normen"

    conn.execute("INSERT INTO knowledge_nodes VALUES ('/n1', 1, NULL, 'Chat', 0)")
    conn.execute("INSERT INTO knowledge_nodes VALUES ('/n2', 2, 'sollen', 'Chat', 0)")
    s = stumme_achse(conn)
    assert s["normen"] == 2 and s["ohne_art"] == 1, s
    assert "teilweise" in s["wirkung"]

    # Zurueckgezogene zaehlen nicht mit -- sonst meldet der Melder Altlasten.
    conn.execute("INSERT INTO knowledge_nodes VALUES ('/alt', 1, NULL, 'Chat', 1)")
    assert stumme_achse(conn)["normen"] == 2, "zurueckgezogene Normen zaehlen nicht"

    # Achse 3: solange alles aus dem Haus stammt, bleibt sie vertagt.
    assert not bericht(conn)["achse3_faellig"], "Hausnormen loesen nichts aus"

    # Grenzfall/Positivfall: eine fremde Quelle macht sie faellig.
    conn.execute("INSERT INTO knowledge_nodes VALUES ('/din', 2, 'sollen', 'DIN 9241-210', 0)")
    b = bericht(conn)
    assert b["achse3_faellig"] and b["fremdnormen"][0]["merkmal"].startswith("DIN")

    # Gegenprobe, dass die Erkennung nicht alles durchlaesst: ein Chatverweis
    # mit dem Wort 'Richtlinie' im FLIESSTEXT der Quelle ist gewollt ein
    # Treffer -- aber ein gewoehnlicher Dateiverweis darf keiner sein.
    conn.execute("INSERT INTO knowledge_nodes VALUES ('/x', 1, NULL, 'erzeugt aus docs/plan.md', 0)")
    assert len(bericht(conn)["fremdnormen"]) == 1, "Dateiverweis ist keine fremde Norm"

    print("selftest ok (7 Faelle)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--melder", action="store_true",
                   help="Nur sprechen, wenn etwas faellig ist -- fuer den Sitzungsstart")
    p.add_argument("--db", type=Path, default=None)
    a = p.parse_args()
    if a.selftest:
        _selftest()
        return
    conn = _verbindung(a.db)
    b = bericht(conn)
    conn.close()
    s = b["achse2_art"]

    if a.melder:
        # Stiller Melder: nur reden, wenn etwas zu tun ist. Ein Melder, der
        # bei jedem Start dasselbe sagt, wird nach drei Tagen ueberlesen --
        # und dann faellt er genauso aus wie einer, den es nicht gibt.
        zeilen = []
        if b["achse3_faellig"]:
            wo = ", ".join(f["path"].rsplit("/", 1)[-1][:40] for f in b["fremdnormen"][:2])
            zeilen.append(f"Normachse 3 (Unabaenderlichkeit) ist FAELLIG: {len(b['fremdnormen'])} "
                          f"Norm(en) fremder Herkunft im Bestand ({wo}). Knoten b6305304.")
        if s["normen"] and s["ohne_art"] == s["normen"]:
            zeilen.append(f"Normachse 2 (Art) ist stumm: {s['ohne_art']} von {s['normen']} Normen "
                          f"ohne Art -- _is_spannung unterscheidet dadurch nichts.")
        if zeilen:
            print("⚠️ " + "\n   ".join(zeilen))
        return

    anteil = s["anteil"]
    quote = "" if anteil is None else f" ({anteil:.0%})"
    print(f"Achse 2 (Art): {s['ohne_art']} von {s['normen']} Normen ohne Art{quote}")
    print(f"  Wirkung: {s['wirkung']}")
    print(f"\nAchse 3 (Unabaenderlichkeit): {'FAELLIG' if b['achse3_faellig'] else 'vertagt'}")
    print(f"  {b['hinweis']}")
    for f in b["fremdnormen"][:5]:
        print(f"  - {f['path']} (Rang {f['rang']}, erkannt an: {f['merkmal']})")


if __name__ == "__main__":
    main()
