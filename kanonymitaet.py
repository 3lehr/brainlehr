#!/usr/bin/env python3
"""
k-Anonymitaet-Messwerkzeug fuer die Knowledge-DB.

Misst pro Merkmal bzw. Merkmalskombination, wie viele Personen (k) eine
Auspraegung teilen. Liest Knoten unter einem Pfad-Praefix, extrahiert
Merkmale per Regex aus title/summary/content und zaehlt.

WAS DIESES WERKZEUG NICHT SAGT:
Es nennt nur die Zahl k je Auspraegung und die Faelle unter einer Schwelle.
Es verwendet nie die Woerter "anonym" oder "Anonymisierung moeglich" — das
waere eine Rechtsaussage (z.B. nach DSGVO Erwaegungsgrund 26), und die trifft
kein Programm. Ob ein gemessenes k ausreicht, haengt von Kontextwissen ab,
das diese DB nicht enthaelt (wer sonst noch Zugriff hat, was oeffentlich
bekannt ist, Verkettung mit anderen Quellen) — das kann nur ein Mensch
beurteilen. Das Werkzeug liefert die Zahl, der Schluss bleibt beim Menschen.

Nur lesend: oeffnet die DB mit mode=ro (uri=True), schreibt nichts.

Nutzung:
    python3 kanonymitaet.py --pfad /organisational/hr_confidential \
        --merkmal abteilung --merkmal zeitraum --schwelle 2

    Als Bibliothek:
    from kanonymitaet import lade_personen, k_werte
    personen = lade_personen(db_pfad, "/organisational/hr_confidential")
    k_werte(personen, ["abteilung", "zeitraum"])

Selbsttest: python3 kanonymitaet.py --selbsttest
"""

import argparse
import os
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

# Gleiche Bauform wie knowledge_mcp_server.py: BEGOD_KNOWLEDGE_DB
# ueberschreibt den Pfad, sonst brainlehr.db neben dieser Datei.
DB_PATH = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (Path(__file__).parent / "brainlehr.db"))

_RE_NAME = re.compile(r"Abwesenheit: (.+?) \(")
_RE_SUMMARY = re.compile(
    r"^(.+?) \((.+?)\) ist vom (\d{4}-\d{2}-\d{2}) bis (\d{4}-\d{2}-\d{2}) abwesend\.$"
)
_RE_GRUND = re.compile(r"Grund: (.+)")
_RE_BUERO = re.compile(r"Büro: (.+)")


def lade_personen(db_pfad, pfad_praefix):
    """Liest Knoten unter pfad_praefix, extrahiert Merkmale je Person.

    Gibt Liste von dicts zurueck: name, abteilung, buero, beginn, ende, grund.
    Was nicht sicher extrahierbar ist, bleibt None (kein Raten).
    """
    uri = f"file:{db_pfad}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    cur = con.cursor()
    cur.execute(
        "select title, summary, content from knowledge_nodes "
        "where path like ? and title != ? order by path",
        (pfad_praefix.rstrip("/") + "/%", pfad_praefix.rsplit("/", 1)[-1]),
    )
    rows = cur.fetchall()
    con.close()

    personen = []
    for title, summary, content in rows:
        summary = summary or ""
        content = content or ""
        m_name = _RE_NAME.search(title or "")
        m_sum = _RE_SUMMARY.search(summary)
        m_grund = _RE_GRUND.search(content)
        m_buero = _RE_BUERO.search(content)

        name = m_name.group(1) if m_name else None
        if m_sum:
            _, abteilung, beginn, ende = m_sum.groups()
        else:
            abteilung = beginn = ende = None

        personen.append(
            dict(
                name=name,
                abteilung=abteilung,
                buero=m_buero.group(1).strip() if m_buero else None,
                beginn=beginn,
                ende=ende,
                grund=m_grund.group(1).strip() if m_grund else None,
            )
        )
    return personen


_MERKMAL_FUNKTIONEN = {
    "abteilung": lambda p: p["abteilung"],
    "raum": lambda p: p["buero"],
    "zeitraum": lambda p: (p["beginn"], p["ende"]),
    "grund": lambda p: p["grund"],
}


def k_werte(personen, merkmale):
    """k je Auspraegung fuer eine Merkmalskombination (Liste von Namen aus
    _MERKMAL_FUNKTIONEN). Gibt dict {Auspraegung: [Personennamen]} zurueck.
    """
    gruppen = defaultdict(list)
    for p in personen:
        schluessel = tuple(_MERKMAL_FUNKTIONEN[m](p) for m in merkmale)
        if len(schluessel) == 1:
            schluessel = schluessel[0]
        gruppen[schluessel].append(p["name"])
    return dict(gruppen)


def unter_schwelle(gruppen, schwelle):
    """Auspraegungen mit k < schwelle. Liste von (Auspraegung, k, Namen)."""
    return [(val, len(names), names) for val, names in gruppen.items() if len(names) < schwelle]


def _selbsttest():
    personen = [
        dict(name="A", abteilung="IT", buero="R1", beginn="2026-01-01", ende="2026-01-05", grund="Urlaub"),
        dict(name="B", abteilung="IT", buero="R2", beginn="2026-03-01", ende="2026-03-05", grund="Reha"),
        dict(name="C", abteilung="HR", buero="R3", beginn="2026-02-01", ende="2026-02-05", grund="Schulung"),
    ]
    g_abteilung = k_werte(personen, ["abteilung"])
    assert len(g_abteilung["IT"]) == 2, g_abteilung
    assert len(g_abteilung["HR"]) == 1, g_abteilung

    g_kombi = k_werte(personen, ["abteilung", "zeitraum"])
    for val, names in g_kombi.items():
        assert len(names) == 1, f"Kombination haette k=1 ergeben muessen: {val} -> {names}"

    unter2 = unter_schwelle(g_abteilung, 2)
    assert len(unter2) == 1 and unter2[0][0] == "HR", unter2

    print("Selbsttest OK: k=2 fuer geteiltes Merkmal, k=1 nach Kombination, Schwellenfilter korrekt.")


def main():
    ap = argparse.ArgumentParser(description="k-Anonymitaet messen (nur lesend)")
    ap.add_argument("--db", default=str(DB_PATH), help="Pfad zur DB (Default: BEGOD_KNOWLEDGE_DB oder brainlehr.db)")
    ap.add_argument("--pfad", help="Pfad-Praefix, z.B. /organisational/hr_confidential")
    ap.add_argument(
        "--merkmal",
        action="append",
        default=[],
        choices=list(_MERKMAL_FUNKTIONEN),
        help="Merkmal (mehrfach fuer Kombination): abteilung, raum, zeitraum, grund",
    )
    ap.add_argument("--schwelle", type=int, default=2, help="k < Schwelle wird gesondert aufgelistet")
    ap.add_argument("--selbsttest", action="store_true")
    args = ap.parse_args()

    if args.selbsttest:
        _selbsttest()
        return

    if not args.pfad or not args.merkmal:
        ap.error("--pfad und mindestens ein --merkmal sind erforderlich (oder --selbsttest)")

    personen = lade_personen(args.db, args.pfad)
    print(f"{len(personen)} Personen geladen unter {args.pfad}")

    gruppen = k_werte(personen, args.merkmal)
    print(f"\nk je Auspraegung von {'+'.join(args.merkmal)}:")
    for val, names in gruppen.items():
        print(f"  {val!r}: k={len(names)} {names}")

    faelle = unter_schwelle(gruppen, args.schwelle)
    print(f"\nAuspraegungen mit k < {args.schwelle}: {len(faelle)}")
    for val, k, names in faelle:
        print(f"  {val!r}: k={k} {names}")


if __name__ == "__main__":
    main()
