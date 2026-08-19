#!/usr/bin/env python3
# ausloeser: Stop -- meldet einmal je Sitzung, wenn der Hauptfaden lange mechanisch arbeitet, ohne zu delegieren
"""Wie lange arbeitet der teuerste Faden mechanisch weiter, ohne zu delegieren?

ANLASS: Norm 75ef2145 (Rang 2, Kaskadenregel) verlangt, mechanische Arbeit an
Sonnet zu geben. Sie ist am 2026-08-08, 08-11, 08-18 und 08-19 gebrochen
worden -- VIERMAL, und jedes Mal hat es der Betreiber bemerkt, nie ich
(L-53eeda, bei 3 Vorkommen auf Regelrang eskaliert).

Die drei bisherigen Vorbeugungen waren Vorsaetze ("Norm beim Start lesen",
"die ranghoehere gewinnt", "pruefe, welche bequemer ist"). Ein Vorsatz hat
keinen Ausloeser. Dieser Melder ist der Ausloeser, und er ist absichtlich
stumpf: er zaehlt.

GEMESSEN am eigenen Protokoll der Sitzung vom 2026-08-19, in der die Norm zum
vierten Mal brach: 807 Bash-Aufrufe im Opus-Hauptfaden, 1.680.313
Ausgabe-Token, 39 Agent-Aufrufe ueber die ganze Sitzung -- nach der
Verdichtung genau EINER.

WARUM DIE STRECKE UND NICHT DAS VERHAELTNIS: Ein Gesamtverhaeltnis
(Agent-Aufrufe zu Werkzeugaufrufen) ist am Ende der Sitzung richtig und
waehrend ihrer ganzen Dauer unbrauchbar -- es sagt nichts darueber, ob GERADE
delegiert werden muesste. Die Strecke seit der letzten Delegation sagt genau
das, und sie ist in dem Moment ablesbar, in dem sie zu lang wird.

DIE SCHWELLE IST GEMESSEN, NICHT GESETZT. Verteilung der 30 Strecken
derselben Sitzung: Median 17, 90. Perzentil 84, Maximum 114. Bei 84 schlaegt
der Melder also auf den obersten Zehnteln an -- den Strecken, in denen
tatsaechlich am Stueck durchgearbeitet wurde -- und schweigt bei der
gewoehnlichen Mischung aus Nachsehen und Handgriffen. Waere die Schwelle auf
den Median gelegt, meldete er in der Haelfte aller Faelle und wuerde
weggeklickt (L-528f0c: ein Signal, das fast immer anschlaegt, wird
weggeklickt).

WAS ER AUSDRUECKLICH NICHT TUT: Er verbietet nichts und weiss nicht, ob
Delegation im Einzelfall richtig gewesen waere -- eine Fehlersuche im eigenen
Kontext ist oft billiger als drei Auftraege. Er stellt nur die Zahl hin, die
sonst nie erhoben wird. Hinweisrecht, kein Veto: immer exit 0.

Aufruf:
    python3 melder/kaskadenanteil.py --selbsttest
    (als Stop-Hook: liest das Hook-JSON auf stdin)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MECHANISCH = {"Bash", "Edit", "Write", "NotebookEdit"}
# 90. Perzentil der gemessenen Verteilung, siehe Modulkopf.
SCHWELLE = 84
# Nur EINMAL je Sitzung, sonst meldet er ab der Schwelle bei jedem Zug.
MARKE = Path("/tmp") / "kaskadenanteil-gemeldet"


def strecke_seit_delegation(zeilen) -> tuple[int, int]:
    """(Strecke seit der letzten Delegation, Agent-Aufrufe gesamt).

    Gezaehlt werden nur Aufrufe des HAUPTFADENS -- Werkzeugaufrufe eines
    Subagenten stehen in dessen eigenem Protokoll, nicht in diesem."""
    lauf = 0
    agenten = 0
    for d in zeilen:
        if d.get("type") != "assistant":
            continue
        for c in ((d.get("message") or {}).get("content") or []):
            if not (isinstance(c, dict) and c.get("type") == "tool_use"):
                continue
            name = c.get("name")
            if name == "Agent":
                agenten += 1
                lauf = 0
            elif name in MECHANISCH:
                lauf += 1
    return lauf, agenten


def meldung(lauf: int, agenten: int) -> str:
    return (
        f"{lauf} mechanische Werkzeugaufrufe im Hauptfaden seit der letzten Delegation "
        f"(Schwelle {SCHWELLE}, gemessenes 90. Perzentil). Agent-Aufrufe bisher: {agenten}.\n"
        "\n"
        "Norm 75ef2145 (Rang 2): mechanische Arbeit -- Messlaeufe, Rot-Proben, Testlaeufe, "
        "umschriebene Code-Aenderungen -- gehoert an einen Sonnet-Subagenten. Die Norm "
        "gewinnt ausdruecklich auch gegen eine Sitzungsanweisung, das Agent-Werkzeug nur "
        "auf Wunsch zu rufen.\n"
        "\n"
        "Das ist ein HINWEIS, kein Verbot: eine Fehlersuche im eigenen Kontext ist oft "
        "billiger als drei Auftraege. Wer weiterarbeitet, tut das mit der Zahl vor Augen "
        "statt ohne."
    )


def _lies_protokoll(pfad: Path):
    for zeile in pfad.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            yield json.loads(zeile)
        except Exception:
            continue


def _selbsttest() -> int:
    def zug(*namen):
        return {"type": "assistant", "message": {"content":
                [{"type": "tool_use", "name": n} for n in namen]}}

    # Strecke wird von einer Delegation zurueckgesetzt.
    z = [zug("Bash", "Bash"), zug("Agent"), zug("Bash", "Edit")]
    assert strecke_seit_delegation(z) == (2, 1), strecke_seit_delegation(z)

    # Ohne jede Delegation laeuft sie durch.
    assert strecke_seit_delegation([zug(*(["Bash"] * 5))]) == (5, 0)

    # NEGATIVFALL, und er ist der wichtigere: nicht-mechanische Aufrufe zaehlen
    # NICHT. Wer den Speicher liest oder eine Lehre schreibt, arbeitet nicht
    # mechanisch -- zaehlte das mit, meldete der Melder genau die Arbeit, die
    # im Hauptfaden richtig aufgehoben ist.
    z = [zug("mcp__knowledge__knowledge_add", "ToolSearch", "WebFetch", "Read")]
    assert strecke_seit_delegation(z) == (0, 0), strecke_seit_delegation(z)

    # Zuege ohne Werkzeug (reiner Text) aendern nichts.
    assert strecke_seit_delegation([{"type": "assistant", "message": {"content": []}}]) == (0, 0)
    # Fremde Zeilen (user, summary) werden nicht gezaehlt.
    assert strecke_seit_delegation([{"type": "user", "message": {"content":
        [{"type": "tool_use", "name": "Bash"}]}}]) == (0, 0)

    m = meldung(84, 1)
    assert "75ef2145" in m and "HINWEIS" in m, m
    print("kaskadenanteil: Selbsttest gruen (Ruecksetzung durch Delegation, Durchlauf ohne, "
          "nicht-mechanische Aufrufe zaehlen nicht, leere und fremde Zeilen stumm)")
    return 0


def main() -> int:
    if "--selbsttest" in sys.argv:
        return _selbsttest()
    try:
        eingabe = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    if eingabe.get("stop_hook_active"):
        return 0
    pfad = eingabe.get("transcript_path")
    if not pfad or not Path(pfad).exists():
        return 0
    marke = MARKE.with_name(MARKE.name + "-" + Path(pfad).stem)
    if marke.exists():
        return 0
    lauf, agenten = strecke_seit_delegation(_lies_protokoll(Path(pfad)))
    if lauf >= SCHWELLE:
        marke.write_text(str(lauf), encoding="utf-8")
        print(meldung(lauf, agenten), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
