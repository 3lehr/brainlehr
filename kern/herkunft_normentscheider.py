#!/usr/bin/env python3
"""Wer hat entschieden -- der Urheber oder der Abschreiber?

BEFUND, gemessen 2026-08-09: 31 der 37 hoechstrangigen Normen trugen
`norm_entschieden_von = 'claude-code/opus-5'`. Der Pruefer meldete das seit
Tagen als "stille Selbstermaechtigung: 86 Prozent der Normentscheidungen hat
ein KI-Akteur sich selbst gegeben". Das war zu einem grossen Teil falsch --
niemand hat sich etwas angemasst. Die Knoten sind aus den CLAUDE.md-Dateien
des Betreibers importiert worden, und der Import trug den SCHREIBER ins
Entscheiderfeld statt den URHEBER.

Die Unterscheidung ist nicht kosmetisch: `norm_entschieden_von` beantwortet
die Frage, wer dafuer einsteht, dass ein Satz bei uns gelten soll. Steht dort
eine Maschine, ist die Norm nach unseren eigenen Regeln nicht legitimiert --
und der Reifegrad kann 'erklaert' nie erreichen (reifegrad.py).

DREI GRUPPEN, und nur die ersten beiden werden korrigiert:

1 URHEBER BELEGT -- `source` nennt eine CLAUDE.md des Betreibers. Diese
  Dateien schreibt er selbst; der Text im Knoten steht dort woertlich. Der
  Entscheider ist er.
2 URHEBER IM QUELLTEXT GENANNT -- `source` sagt ausdruecklich
  "Betreiber-Entscheidung" oder "Entscheidung des Betreibers".
3 FREMDNORM, NICHT KORRIGIEREN -- `source` nennt Gesetz, Urteil, WEG-Recht
  oder eine Normungsstelle. Hier hat der Betreiber NICHTS entschieden, die
  Maschine hat eine fremde Regel AUFGEZEICHNET. 'betreiber' einzutragen waere
  eine Falschaussage in die andere Richtung -- und genau die Verwechslung,
  wegen der reifegrad.py zwischen Hausnorm und aufgezeichneter Fremdnorm
  unterscheidet.

Eingetragen wird die ROLLE 'betreiber', nicht der Name. Es gibt genau einen,
und die offene Annahme A-d93330 haelt fest, dass diese Spalten teurer werden,
sobald der erste menschliche Name darin steht.

Aufruf:
  python3 herkunft_normentscheider.py            zeigt, was sich aendern wuerde
  python3 herkunft_normentscheider.py --apply    schreibt
  python3 herkunft_normentscheider.py --selftest
"""
from __future__ import annotations

import os
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

import sqlite3
import sys
from pathlib import Path

WURZEL = _w
sys.path.insert(0, str(WURZEL / "haken"))
import ort  # noqa: E402
import speicher  # noqa: E402 -- nur verbinde_bestand() fuer main()

BETREIBER = "betreiber"

# Quellen, die den Betreiber als Urheber belegen.
URHEBER_MERKMALE = (
    # Die globalen Arbeitsanweisungen des Betreibers. Der Benutzername stand
    # bis 2026-08-10 hier im Klartext -- in einem weitergebbaren Repo ist das
    # ein Personenbezug, und bei jedem anderen Nutzer waere das Muster obendrein
    # falsch. Aus dem Heimatverzeichnis abgeleitet, per BEGOD_BETREIBER_MERKMAL
    # ueberschreibbar.
    os.environ.get("BEGOD_BETREIBER_MERKMAL")
    or str(Path.home() / ".claude" / "CLAUDE.md").lower(),
    "/begod2026/hub/claude.md",
    "betreiber-entscheidung",
    "entscheidung des betreibers",
    "betreiberentscheidung",
)

# Quellen, bei denen die Maschine eine FREMDE Regel aufgezeichnet hat. Diese
# Liste sticht die obere -- im Zweifel nicht korrigieren.
FREMDNORM_MERKMALE = (
    "gesetz", "urteil", "weg-recht", "buckeberg/recht", "verordnung",
    "din ", "iso ", "bsi ", "wcag", "richtlinie",
)


def ist_urheber_betreiber(source: str | None) -> bool:
    s = (source or "").lower()
    if any(f in s for f in FREMDNORM_MERKMALE):
        return False
    return any(m in s for m in URHEBER_MERKMALE)


def kandidaten(conn: sqlite3.Connection) -> list[dict]:
    conn.row_factory = sqlite3.Row
    return [dict(r) for r in conn.execute(
        "SELECT id, path, source, norm_rang, norm_entschieden_von FROM knowledge_nodes "
        "WHERE norm_rang IN (1, 2) AND zurueckgezogen = 0 "
        "AND COALESCE(norm_entschieden_von, '') <> ?", (BETREIBER,))
        if ist_urheber_betreiber(r["source"])]


def anwenden(conn: sqlite3.Connection, ids: list[str]) -> int:
    if not ids:
        return 0
    q = ",".join("?" for _ in ids)
    cur = conn.execute(
        f"UPDATE knowledge_nodes SET norm_entschieden_von = ? WHERE id IN ({q})",
        [BETREIBER] + ids)
    conn.commit()
    return cur.rowcount


def main(argv: list[str]) -> int:
    # verbinde_bestand statt sqlite3.connect: liest/korrigiert einen
    # bestehenden Bestand, legt keinen an -- siehe
    # kern/speicher.py::verbinde_bestand.
    conn = speicher.verbinde_bestand(ort.DB)
    k = kandidaten(conn)
    print(f"Ziel: {ort.DB}")
    print(f"Rang-1/2-Knoten mit belegtem Urheber Betreiber: {len(k)}\n")
    for x in k[:40]:
        print(f"  Rang {x['norm_rang']}  {x['norm_entschieden_von'] or '(leer)'} -> {BETREIBER}"
              f"   {x['path'][:56]}")
    if "--apply" not in argv:
        print(f"\nZum Schreiben: python3 {Path(argv[0]).name} --apply")
        conn.close()
        return 0
    n = anwenden(conn, [x["id"] for x in k])
    print(f"\ngeaendert: {n}")
    conn.close()
    return 0


def demo() -> None:
    """Gegenprobe in beide Richtungen plus der Negativfall, der hier der
    wichtigste ist: eine aufgezeichnete Fremdnorm darf NICHT dem Betreiber
    zugeschrieben werden."""
    # Aus dem Heimatverzeichnis DIESES Rechners gebaut statt fest getippt --
    # ein hartkodierter Benutzername macht die Probe bei jedem anderen Nutzer
    # rot, und zwar ohne dass an der Sache etwas falsch waere.
    eigen = f"erzeugt aus {Path.home()}/.claude/CLAUDE.md (Stand ...)"
    assert ist_urheber_betreiber(eigen), eigen
    assert ist_urheber_betreiber("erzeugt aus /Volumes/daten/Begod2026/hub/CLAUDE.md")
    assert ist_urheber_betreiber("Betreiber-Entscheidung im Chat 2026-08-08T18:40")
    assert ist_urheber_betreiber("Entscheidung des Betreibers im Gespraech 2026-08-07")

    # Negativfall: Fremdnorm sticht, auch wenn 'Betreiber' im Text steht.
    assert not ist_urheber_betreiber("erzeugt aus buckeberg/recht/jahresabrechnung-BGH-Urteil")
    assert not ist_urheber_betreiber("Betreiber nennt das Urteil des BGH vom ...")
    assert not ist_urheber_betreiber("WCAG 2.2 AA, W3C-Empfehlung")
    assert not ist_urheber_betreiber("erzeugt aus docs/openlehr/UX_WALKTHROUGH_TIEF.md")
    assert not ist_urheber_betreiber(None) and not ist_urheber_betreiber("")

    # Und die Wirkung auf den Reifegrad, in beide Richtungen.
    import reifegrad
    assert reifegrad.ist_nachweislich_mensch(BETREIBER), "'betreiber' muss als Mensch gelten"
    assert not reifegrad.ist_nachweislich_mensch("claude-code/opus-5")
    print("herkunft_normentscheider.demo ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        demo()
    else:
        raise SystemExit(main(sys.argv))
