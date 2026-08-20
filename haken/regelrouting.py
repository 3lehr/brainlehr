#!/usr/bin/env python3
"""Regel-Routing: spielt eine Regel ein, WENN sie gebraucht wird.

ANLASS (Betreiberweisung 2026-08-20): *"meine vermutung, der system prompt ist
einfach viel zu lange, wir brauchen ein systemprompt routing. systemprompt
'regeln' nur dort wo sie gebraucht werden und sortiert nach wichtigkeit?"*

GEMESSEN, bevor gebaut wurde:

  ~/.claude/CLAUDE.md            59 364 Zeichen, 26 Abschnitte
  hub/CLAUDE.md                  29 124 Zeichen
  brainlehr/CLAUDE.md             4 181 Zeichen
                                 -------
  bei JEDEM Sitzungsstart        92 669 Zeichen

Davon sind nach der Frage "haengt die Regel an einem THEMA oder an einer
SITUATION?" rund 23 % (13 123 Zeichen) themengebunden -- sie gelten nur, wenn
jemand eine Oberflaeche baut, ein Dokument setzt, Trainingsdaten anfasst.
77 % sind situationsgebunden (Belegpflicht, Rueckfrage, Committen) und muessen
im Kontext stehen, weil ihr Ausloeser kein Dateityp ist.

DIE BAUFORM WAR SCHON DA, nur einmal angewandt: Der BSI-Abschnitt steht seit
Langem als "nur Trigger, kein Katalog im Kontext" in CLAUDE.md. Dieses Modul
verallgemeinert das.

DER STUMPF BLEIBT, und das ist die Sicherung. In CLAUDE.md steht weiterhin ein
kurzer Abschnitt mit dem Kern und dem Verweis auf die ausgelagerte Datei.
Faellt der Haken aus, degradiert die Regel zu "benannt, aber nicht zitiert" --
nicht zu "existiert nicht". Ein Routing ohne Stumpf waere ein Loeschen mit
Zusatzschritt.

EINMAL JE SITZUNG UND REGEL: Der Zustand liegt je Sitzung. Wer zwanzigmal eine
Swift-Datei anfasst, bekommt die Oberflaechenregel einmal.

    python3 haken/regelrouting.py --selftest
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REGELN = Path.home() / ".claude" / "regeln"
ZUSTAND = Path.home() / ".brainlehr-regelrouting.json"

# Regel -> (Dateiendungen, die sie ausloesen). Absichtlich an der ENDUNG und
# nicht am Inhalt: der Ausloeser muss billig sein, sonst laeuft er nicht bei
# jedem Werkzeugaufruf mit.
ROUTEN: dict[str, tuple[str, ...]] = {
    "wcag": (".swift", ".html", ".css", ".tsx", ".jsx", ".vue", ".dart", ".xaml"),
}

# Werkzeuge, bei denen ein Pfad ueberhaupt eine Absicht verraet. Ein `Read`
# loest NICHT aus -- wer eine Datei liest, baut noch keine Oberflaeche.
WERKZEUGE = ("Edit", "Write", "NotebookEdit", "MultiEdit")


def _aus() -> bool:
    return os.environ.get("BRAINLEHR_REGELROUTING", "").strip().lower() == "aus"


def passende_regel(werkzeug: str, pfad: str) -> str | None:
    if werkzeug not in WERKZEUGE or not pfad:
        return None
    klein = pfad.lower()
    for regel, endungen in ROUTEN.items():
        if klein.endswith(endungen):
            return regel
    return None


def text(regel: str) -> str:
    try:
        return (REGELN / f"{regel}.md").read_text(encoding="utf-8")
    except OSError:
        return ""


def melde(sitzung: str, werkzeug: str, pfad: str,
          zustand: Path | None = None, regeln: Path | None = None) -> str:
    global REGELN
    if regeln is not None:
        REGELN = regeln
    regel = passende_regel(werkzeug, pfad)
    if not regel:
        return ""
    ablage = zustand or ZUSTAND
    try:
        alt = json.loads(ablage.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        alt = {}
    schon = alt.get(sitzung, [])
    if regel in schon:
        return ""
    inhalt = text(regel)
    if not inhalt:
        return ""          # lieber nichts als ein leerer Verweis
    alt[sitzung] = schon + [regel]
    try:
        ablage.write_text(json.dumps(alt)[:200_000], encoding="utf-8")
        os.chmod(ablage, 0o600)
    except OSError:
        pass
    return inhalt


def _selftest() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "wcag.md").write_text("# WCAG\nRegeltext.", encoding="utf-8")
        z = d / "z.json"

        # a) Oberflaechendatei bearbeiten -> Regel kommt.
        erste = melde("s1", "Edit", "/x/AnsichtFoo.swift", z, d)
        assert "Regeltext" in erste, erste
        # b) EINMAL je Sitzung -- die zwanzigste Swift-Datei bekommt nichts.
        assert melde("s1", "Edit", "/x/Bar.swift", z, d) == ""
        # c) Andere Sitzung bekommt sie eigenstaendig.
        assert "Regeltext" in melde("s2", "Write", "/x/seite.html", z, d)
        # d) NEGATIVFALL: LESEN loest nicht aus -- wer liest, baut noch nichts.
        assert melde("s3", "Read", "/x/Ansicht.swift", z, d) == ""
        # e) NEGATIVFALL: eine Datei ohne Oberflaechenendung loest nicht aus.
        assert melde("s3", "Edit", "/x/rechner.py", z, d) == ""
        # f) Fehlende Regeldatei -> nichts, kein halber Verweis.
        assert melde("s4", "Edit", "/x/a.swift", z, d / "leer") == ""
        # g) Schalter wirkt.
        os.environ["BRAINLEHR_REGELROUTING"] = "aus"
        assert _aus() is True
        del os.environ["BRAINLEHR_REGELROUTING"]
        assert _aus() is False
    print("regelrouting: Selbsttest gruen (7 Faelle: Regel kommt, einmal je "
          "Sitzung, zweite Sitzung eigenstaendig, Lesen loest nicht aus, "
          "fremde Endung nicht, fehlende Datei still, Schalter wirkt)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    if _aus():
        return 0
    try:
        eingabe = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    werkzeug = str(eingabe.get("tool_name") or "")
    eingaben = eingabe.get("tool_input") or {}
    pfad = str(eingaben.get("file_path") or eingaben.get("notebook_path") or "")
    try:
        inhalt = melde(str(eingabe.get("session_id") or "unbekannt"), werkzeug, pfad)
    except Exception:
        return 0
    if inhalt:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": str(eingabe.get("hook_event_name") or "PreToolUse"),
            "additionalContext": (
                "<geroutete-regel name='wcag'>\n"
                "Diese Regel wurde eingespielt, WEIL du gerade eine "
                "Oberflaechendatei anfasst. Sie steht nicht dauerhaft im "
                "Systemprompt.\n\n" + inhalt + "\n</geroutete-regel>"),
        }}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
