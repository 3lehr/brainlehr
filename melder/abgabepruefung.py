#!/usr/bin/env python3
# ausloeser: Stop -- meldet, wenn eine Antwort eine Pruefung an den Betreiber abgibt, ohne einen Testaufbau versucht zu haben
"""Ein Stopp-Punkt beendet die Pruefung nicht, er verlegt sie.

ANLASS ist Knoten 4164a6c4 (Rang 2, 2026-08-19), ausdruecklich an brainlehr
adressiert. Dort wurde dreimal gemeldet „Wirkung ungeprueft, verlangt den
Ausweis des Betreibers", ohne einen einzigen Versuch. Der Betreiber woertlich:

    „und da hast du es dir zu einfach gemacht, wir haetten auch einen
     testausweis bauen koenne, oder ausweise mit ablaufdatem!"

`kern/ausweis.py::anlegen()` nimmt seit Langem `gilt_bis` -- das Mittel lag
offen. Der nachgeholte Versuch scheiterte dann an einer echten Schranke, und
GENAU DAS ist der Punkt: aus „braucht seinen Ausweis" wurde
„claude-code hat Rolle `schreiber`, noetig ist `ausweis:ausstellen`" -- aus
einer Vermutung ein Fehlertext mit Rolle und Fundstelle, aus einem Endzustand
eine Entscheidungsvorlage.

WAS DIESER MELDER FAENGT, und es ist eine andere Klasse als der
Rueckfrage-Waechter daneben: Der faengt FRAGEN im Antworttext. Diese hier ist
keine Frage, sondern eine FESTSTELLUNG, die eine Pruefung an den Menschen
abgibt -- „wartet auf dich", „verlangt deinen Ausweis", „nur du kannst".

DIE GEGENPROBE GEGEN FEHLALARM ist der eigentliche Entwurf. Kennwoerter,
Geld, Aussenwirkung und Unumkehrbares sind ECHTE Halter; dort ist Abgeben
richtig und wird nicht gemeldet. Gemeldet wird nur, wo der genannte Grund
KEINER der vier Stopp-Punkte ist -- „ich brauche ein Kennwort, um MEINE
eigene Arbeit zu pruefen" gehoert nicht dazu, dafuer gibt es Testausweise.

HINWEISRECHT: Wir blockieren hier NICHT. Der Rueckfrage-Waechter blockt, weil
eine unausgefuehrte Ankuendigung immer falsch ist. Eine Abgabe kann richtig
sein -- deshalb nur ein Hinweis, und immer exit 0.

Aufruf:
    python3 melder/abgabepruefung.py --selftest
    (als Stop-Hook: liest das Hook-JSON auf stdin)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Eine ABGABE: die Antwort verlegt eine Pruefung an den Betreiber.
ABGABE = re.compile(
    r"(wartet\s+auf\s+(dich|sie)|verlangt\s+dein|braucht\s+dein"
    r"|braucht\s+den\s+betreiber|nur\s+du\s+kannst|kannst\s+nur\s+du"
    r"|musst\s+du\s+selbst|liegt\s+bei\s+dir|ueberlasse\s+ich\s+dir|überlasse\s+ich\s+dir"
    r"|lege\s+ich\s+dir\s+vor|vorlegen\s+statt)",
    re.I,
)

# Die VIER echten Stopp-Punkte. Steht einer davon im selben Satz, ist die
# Abgabe richtig und wird nicht gemeldet.
ECHTER_HALTER = re.compile(
    r"(kennwort|passwort|password|zugangsdaten|secret|api[- ]?key"
    r"|push|veroeffentlich|veröffentlich|publizier|nach\s+aussen|nach\s+außen"
    r"|pull\s*request|dritte[nr]?\b|empfaenger|empfänger|versend"
    r"|unumkehrbar|unwiderruflich|endgueltig|endgültig"
    r"|geld|kosten|bezahl|rechnung|preis|vertrag)",
    re.I,
)

# Wortmarken eines VERSUCHTEN Testaufbaus -- steht so etwas im Zug, wurde
# nicht blind abgegeben.
VERSUCH = re.compile(
    r"(testausweis|testkonto|fixture|wegwerf|schnappschuss|gilt_bis"
    r"|versucht|nachgeholt|PermissionError|fehlertext|rolle\s|probe\s)",
    re.I,
)


def beurteile(text: str, *, hat_werkzeug: bool | None = None) -> str | None:
    """Grund als Text, oder None wenn nichts zu melden ist.

    `hat_werkzeug=False` heisst: im ganzen Zug kein Werkzeugaufruf. Wer ohne
    einen einzigen Aufruf abgibt, hat sicher nichts versucht."""
    for satz in re.split(r"(?<=[.!?\n])\s+", text or ""):
        if not ABGABE.search(satz):
            continue
        if ECHTER_HALTER.search(satz):
            continue  # einer der vier Stopp-Punkte -- Abgabe ist richtig
        if VERSUCH.search(satz):
            continue  # ein Versuch ist benannt
        if hat_werkzeug:
            continue  # im Zug wurde etwas ausgefuehrt -- kein Blindfall
        return (
            "Diese Antwort gibt eine Pruefung an den Betreiber ab, ohne dass im Zug ein "
            "Testaufbau versucht wurde:\n\n"
            f"  {satz.strip()[:160]}\n\n"
            "Norm 4164a6c4 (Rang 2): Ein Stopp-Punkt beendet die Pruefung nicht, er verlegt "
            "sie. Vorher zu versuchen: Testausweis (kern/ausweis.py::anlegen nimmt "
            "gilt_bis), Testkonto, Fixture, Wegwerf-Bestand, Umgebungsschalter -- die "
            "Beta-Direktive erlaubt das ohne Rueckfrage.\n"
            "Scheitert der Versuch, ist der FEHLERTEXT der Befund (Rolle, Fundstelle, was "
            "fehlt) -- nicht 'geht nicht'. Danach als FRAGE vorlegen.\n\n"
            "Gehoert der Halter zu den vier echten Stopp-Punkten (Kennwort, Aussenwirkung, "
            "Unumkehrbares, Geld), ist die Abgabe richtig -- dann benenne ihn im selben Satz, "
            "und dieser Hinweis bleibt aus."
        )
    return None


def _selftest() -> int:
    # FAENGT: Abgabe ohne Versuch, ohne echten Halter, ohne Werkzeug im Zug.
    for satz in ("Die Wirkung wartet auf dich.",
                 "Das verlangt deinen Ausweis.",
                 "Den Rollenwechsel kann nur du kannst ausloesen."):
        assert beurteile(satz, hat_werkzeug=False), f"nicht gefangen: {satz!r}"

    # FAENGT NICHT, und diese vier sind der eigentliche Entwurf:
    # (1) echter Stopp-Punkt im selben Satz
    assert beurteile("Der Push wartet auf dich.", hat_werkzeug=False) is None
    assert beurteile("Das Kennwort musst du selbst eintippen.", hat_werkzeug=False) is None
    # (2) ein Versuch ist benannt
    assert beurteile("Ich habe einen Testausweis versucht, es wartet auf dich.",
                     hat_werkzeug=False) is None
    # (3) im Zug wurde gearbeitet
    assert beurteile("Die Wirkung wartet auf dich.", hat_werkzeug=True) is None
    # (4) gar keine Abgabe
    assert beurteile("Alles erledigt, 28 von 56 belegt.", hat_werkzeug=False) is None

    # Der Fehlertext-Fall aus der Norm: wer die Rolle NENNT, hat gemessen.
    assert beurteile("claude-code hat Rolle schreiber, noetig ist ausweis:ausstellen -- "
                     "das liegt bei dir.", hat_werkzeug=False) is None

    print("abgabepruefung: Selbsttest gruen (3 gefangen, 6 Gegenproben: echter Halter, "
          "benannter Versuch, Werkzeug im Zug, keine Abgabe, Fehlertext)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    try:
        eingabe = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if eingabe.get("stop_hook_active"):
        return 0
    pfad = eingabe.get("transcript_path")
    if not pfad or not Path(pfad).expanduser().exists():
        return 0
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from rueckfrageschleife import _letzte_antwort  # eine Quelle fuer beides
    except Exception:
        return 0
    text, werkzeug = _letzte_antwort(Path(pfad).expanduser())
    grund = beurteile(text, hat_werkzeug=werkzeug)
    if grund:
        print(grund, file=sys.stderr)   # Hinweis, KEIN block
    return 0


if __name__ == "__main__":
    sys.exit(main())
