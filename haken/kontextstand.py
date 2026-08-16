#!/usr/bin/env python3
"""Meldet, wenn das Kontextfenster voll laeuft -- bevor die Verdichtung einsetzt.

ANLASS, woertlich vom Betreiber am 2026-08-16: "btw das kontextfenster laeuft
voll, erkennst du das?" -- und auf die Antwort, dass es sich nachlesen laesst:
"also du siehst es, benutzt es aber nicht? das sollten wir aendern?!"

Er hatte in beidem recht. Der Fuellstand steht in JEDER Transcript-Zeile, und
kein Mechanismus las ihn. Gemessen in genau dieser Sitzung: 916.883 Token von
einer Million, also 92 Prozent -- aufgefallen ist es dem BETREIBER, nicht dem
Assistenten, und zwar nach sechzehn Stunden.

WARUM DAS ZAEHLT: Laeuft das Fenster ueber, wird verdichtet. Die Verdichtung
ist verlustbehaftet und trifft zuerst die Belege -- gemessene Zahlen,
Fundstellen, verworfene Wege. Was bleibt, ist die Zusammenfassung, und die
liest sich genauso sicher wie das Original. Wer rechtzeitig uebergibt,
entscheidet SELBST, was in die Uebergabe kommt.

DIE ZAHL IST EIN ZUSTAND, KEINE SUMME. `input_tokens + cache_read +
cache_creation` der LETZTEN Anfrage ist der Fuellstand; die Summe ueber alle
Anfragen der Sitzung ist Durchsatz und waechst auch dann, wenn das Fenster
halbleer bleibt. Wer beides verwechselt, meldet Alarm bei jeder langen
Sitzung.

STDOUT WIRD BEI PostToolUse NICHT ANGEZEIGT (L-9e8832, vier Stunden
Fehlersuche): Die Meldung geht deshalb als JSON mit `systemMessage` heraus,
zusammen mit `continue` und `suppressOutput` -- ein blosses systemMessage
blitzt eine Sekunde auf und verschwindet.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Ab wann gemeldet wird. Zwei Stufen, weil sie verschiedene Handlungen
# ausloesen: bei 75 Prozent lohnt es sich, die Uebergabe zu SCHREIBEN, bei 88
# Prozent sie zu BENUTZEN. Eine einzige Schwelle waere entweder zu frueh
# (nervt und wird ignoriert) oder zu spaet (die Verdichtung war schneller).
WARNUNG = 0.75
DRINGEND = 0.88

# Fenstergroesse. Wird ueberschrieben, wenn die Umgebung sie kennt -- geraten
# wird hier nichts, aber ohne Angabe ist eine Million der belegte Stand fuer
# die Modelle dieses Hauses.
FENSTER_VORGABE = 1_000_000


def fuellstand(transcript: Path) -> tuple[int, int] | None:
    """(Token im Fenster, gelesene Zeilen) oder None.

    Gelesen wird die LETZTE Zeile mit usage-Angabe -- rueckwaerts, damit eine
    lange Sitzung nicht bei jedem Werkzeugaufruf megabyteweise Text durch den
    Speicher zieht."""
    if not transcript.exists():
        return None
    zeilen = transcript.read_text(encoding="utf-8", errors="ignore").splitlines()
    for i, z in enumerate(reversed(zeilen)):
        try:
            d = json.loads(z)
        except ValueError:
            continue
        u = (d.get("message") or {}).get("usage")
        if not u:
            continue
        stand = (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                 + u.get("cache_creation_input_tokens", 0))
        if stand:
            return stand, len(zeilen)
    return None


def satz(stand: int, fenster: int) -> str | None:
    """Der Satz an den Assistenten -- oder None, wenn nichts zu melden ist.

    Er nennt die HANDLUNG, nicht nur den Zustand. Ein Melder, der eine Zahl
    zeigt und offenlaesst, was zu tun ist, wird weggeklickt (L-47a196)."""
    anteil = stand / fenster
    if anteil >= DRINGEND:
        return (f"Kontextfenster zu {anteil:.0%} voll ({stand:,} von {fenster:,}). "
                f"JETZT uebergeben: Startprompt schreiben, offene Belege sichern, "
                f"dann neue Sitzung. Nach der Verdichtung sind die Zahlen weg.")
    if anteil >= WARNUNG:
        return (f"Kontextfenster zu {anteil:.0%} voll ({stand:,} von {fenster:,}). "
                f"Guter Zeitpunkt, die Uebergabe zu schreiben, solange die Belege "
                f"noch vollstaendig im Kontext stehen.")
    return None


def demo() -> None:
    """Selbsttest ohne Transcript: prueft die Schwellen und dass unterhalb
    geschwiegen wird. Ein Melder, der immer redet, ist einer zu viel."""
    assert satz(500_000, 1_000_000) is None, "die Haelfte ist kein Anlass"
    assert satz(740_000, 1_000_000) is None, "knapp unter der Schwelle: still"
    w = satz(760_000, 1_000_000)
    assert w and "Uebergabe zu schreiben" in w, w
    d = satz(920_000, 1_000_000)
    assert d and "JETZT uebergeben" in d, d
    # Der Satz nennt die Handlung, nicht nur die Zahl.
    for m in (w, d):
        assert "uebergeben" in m.lower() or "uebergabe" in m.lower(), m
    print("demo: ok", file=sys.stderr)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--transcript", default=os.environ.get("CLAUDE_TRANSCRIPT_PATH", ""))
    p.add_argument("--fenster", type=int,
                   default=int(os.environ.get("CLAUDE_CONTEXT_WINDOW", FENSTER_VORGABE)))
    p.add_argument("--zeigen", action="store_true", help="Stand immer ausgeben, auch unterhalb der Schwelle")
    a = p.parse_args()

    if not a.transcript:
        # Kein Transcript bekannt -- schweigen statt raten. Ein Haken, der bei
        # fehlender Eingabe Alarm schlaegt, wird abgeschaltet.
        return 0
    ergebnis = fuellstand(Path(a.transcript))
    if not ergebnis:
        return 0
    stand, zeilen = ergebnis
    if a.zeigen:
        print(f"{stand:,} von {a.fenster:,} Token ({stand/a.fenster:.0%}), "
              f"{zeilen} Transcript-Zeilen")
        return 0
    meldung = satz(stand, a.fenster)
    if not meldung:
        return 0
    # PostToolUse zeigt stdout NICHT an (L-9e8832) -- als JSON mit
    # systemMessage, und nur zusammen mit continue+suppressOutput bleibt es
    # stehen statt eine Sekunde aufzublitzen.
    print(json.dumps({"systemMessage": meldung, "continue": True,
                      "suppressOutput": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    demo()
    raise SystemExit(main())
