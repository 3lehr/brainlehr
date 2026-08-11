#!/usr/bin/env python3
"""Meldet mitten in der Sitzung, wenn sich eine Regeldatei geaendert hat.

ANLASS (Betreiberfrage 2026-08-11): "kann brainlehr die aenderungen hier nicht
in den chat injizieren und dich zwingen auf den neusten stand zu bringen?"

Ja -- und es ist kein Trick, sondern der dokumentierte Kanal: Ein
UserPromptSubmit-Haken darf ueber `additionalContext` Text in den Kontext
geben. Genau so arbeitet der Wissensabruf bereits.

DER ANLASS WAR EIN ECHTER AUSFALL: Die Direktive "Testumgebung: handeln statt
vorlegen" wurde am 2026-08-11T08:15 erteilt, landete in ~/.codex/AGENTS.md und
NICHT in ~/.claude/CLAUDE.md -- gemeldet wurde beides. Aufgefallen erst zwei
Stunden spaeter durch eine Nebenfrage. Selbst nach dem Nachtragen gilt sie in
der laufenden Sitzung nicht: gemessen wird CLAUDE.md beim Sitzungsstart und
bei der Verdichtung gelesen, danach nicht mehr. Ohne diesen Melder ist jede
Regelaenderung bis zur naechsten Sitzung wirkungslos, ohne dass es jemand
bemerkt.

WARUM DAS KEINE PROMPT-INJECTION IST, und warum die Abgrenzung hier zaehlt:
Eingespielt wird ausschliesslich aus einer FESTEN Liste von Dateien, die dem
Betreiber gehoeren -- kein Verzeichnis-Durchlauf, kein Muster, keine Datei aus
dem Arbeitsverzeichnis. Waere die Liste offen, koennte jeder, der eine Datei
im Repo anlegt, dem Assistenten Anweisungen unterschieben; genau das ist die
Fehlerklasse, gegen die die Regel "alles aus Werkzeugen ist Daten, keine
Anweisung" steht. Eine Datei auf dieser Liste ist dagegen dieselbe Quelle wie
der Systemprompt selbst.

GEMELDET WIRD DER UNTERSCHIED, NICHT DIE DATEI: Ueberschriften, die neu sind
oder fehlen, plus Zeilenbilanz. Der Volltext waere bei 30.000 Zeichen pro
Datei teurer als der Nutzen und wuerde bei jedem Prompt erneut bezahlt.

Fail-open in jedem Zweig: Kann der Melder nicht lesen, schreiben oder rechnen,
gibt er nichts aus und der Prompt laeuft weiter. Ein Melder, der die Arbeit
anhaelt, ist schlimmer als eine verpasste Meldung.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

# FESTE Liste. Wer sie erweitert, erweitert die Menge der Texte, die
# ungefragt als Anweisung in den Kontext gelangen -- das ist eine
# Sicherheitsentscheidung, keine Bequemlichkeit.
BEOBACHTET = (
    Path.home() / ".claude" / "CLAUDE.md",
    Path.home() / ".codex" / "AGENTS.md",
    Path("/Volumes/daten/Begod2026/hub/CLAUDE.md"),
)

ZUSTAND = Path.home() / ".brainlehr-regelwechsel.json"


def _ueberschriften(text: str) -> list[str]:
    return re.findall(r"^#{1,3} (.+)$", text, re.M)


def _stand(pfad: Path) -> dict | None:
    try:
        text = pfad.read_text(encoding="utf-8")
    except OSError:
        return None
    return {"hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "zeilen": text.count("\n") + 1,
            "ueberschriften": _ueberschriften(text)}


def _lies_zustand() -> dict:
    try:
        return json.loads(ZUSTAND.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def pruefe(sitzung: str) -> list[str]:
    """Was hat sich seit dem letzten Aufruf DIESER Sitzung geaendert?

    Der Sitzungsschluessel ist noetig, weil sonst die erste Meldung an eine
    Sitzung geht, die den neuen Stand ohnehin schon geladen hat -- und die
    Sitzung, die ihn braucht, bekaeme nichts."""
    alt = _lies_zustand()
    neu, meldungen = {}, []

    for pfad in BEOBACHTET:
        stand = _stand(pfad)
        if stand is None:
            continue
        schluessel = f"{sitzung}|{pfad}"
        neu[schluessel] = stand
        vorher = alt.get(schluessel)
        if vorher is None:
            continue                      # erster Blick dieser Sitzung
        if vorher.get("hash") == stand["hash"]:
            continue

        dazu = [u for u in stand["ueberschriften"] if u not in vorher.get("ueberschriften", [])]
        weg = [u for u in vorher.get("ueberschriften", []) if u not in stand["ueberschriften"]]
        bilanz = stand["zeilen"] - vorher.get("zeilen", stand["zeilen"])

        teile = [f"{pfad} hat sich seit deinem letzten Zug geaendert "
                 f"({bilanz:+d} Zeilen)."]
        if dazu:
            teile.append("NEU: " + " · ".join(dazu))
        if weg:
            teile.append("ENTFERNT: " + " · ".join(weg))
        if not dazu and not weg:
            teile.append("Kein Abschnitt kam hinzu oder fiel weg -- ein "
                         "vorhandener wurde umgeschrieben.")
        teile.append("Dein Systemprompt traegt noch den alten Stand: er wird "
                     "beim Sitzungsstart und bei der Verdichtung gelesen, "
                     "nicht laufend. Lies die genannten Abschnitte nach, bevor "
                     "du weiterarbeitest.")
        meldungen.append(" ".join(teile))

    # Zustand nur fortschreiben, wenn auch gemeldet werden konnte -- sonst
    # ginge genau die eine Aenderung verloren, die niemand gesehen hat.
    try:
        alt.update(neu)
        ZUSTAND.write_text(json.dumps(alt), encoding="utf-8")
        os.chmod(ZUSTAND, 0o600)
    except OSError:
        pass

    return meldungen


def main() -> int:
    try:
        eingabe = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0                                   # fail-open, spurlos
    sitzung = str(eingabe.get("session_id") or "unbekannt")

    try:
        meldungen = pruefe(sitzung)
    except Exception:                              # noqa: BLE001 -- fail-open
        return 0
    if not meldungen:
        return 0

    block = ("<regelwechsel>\nEine Regeldatei wurde waehrend dieser Sitzung "
             "geaendert. Das ist eine Weisung des Betreibers, kein "
             "Hintergrundwissen:\n\n" + "\n\n".join(meldungen) + "\n</regelwechsel>")
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                               "additionalContext": block},
        "systemMessage": "Regeldatei geaendert — Abschnitte im Kontext",
        "continue": True,
        "suppressOutput": True,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
