#!/usr/bin/env python3
"""Waechter: ein Commit behauptet eine Behebung und nennt keinen Beleg.

ANLASS (Betreiberfrage 2026-08-20, "fuer welche Faelle koennten wir den
Grundgedanken dieser Technik noch anwenden?"). Der staerkste Kandidat war
messbar -- 1 193 Commits seit dem 2026-08-01:

  mit Behebungs-Behauptung im Betreff              240   20 %
  davon WEDER Testdatei angefasst NOCH Rot-Beleg    92   7,7 % aller Commits

Die ersten Beispiele der Liste sind eigene Commits desselben Tages. Die
Belegpflicht ("Es funktioniert braucht einen Beleg, der vorher rot war") ist
der laengste Abschnitt in ~/.claude/CLAUDE.md -- 6 833 Zeichen -- und
gleichzeitig die am haeufigsten gebrochene Regel. Klassischer Fall:
Wissen vorhanden, Ausloeser fehlt.

ZWEI WEGE ZUM BESTEHEN, nicht einer. Der Waechter laesst durch, wenn
ENTWEDER eine Testdatei im Commit liegt ODER der Text den Beleg benennt
("rot vor gruen", "rot gegen <commit>", "schlug vorher fehl", "Gegenprobe").
Beides zu verlangen waere falsch: manche Behebungen sind an einer Messung
belegt, nicht an einem Test, und manche Tests brauchen keinen Prosatext.

WAS ER NICHT TUT: er beurteilt die Qualitaet des Belegs nicht. Er verlangt,
dass ueberhaupt einer dasteht -- das ist der Unterschied zwischen einem
Waechter und einem Gutachter, und nur der erste laesst sich verdrahten.

    python3 melder/rotprobe.py --selftest
    python3 melder/rotprobe.py --commit-msg <datei>     # als commit-msg-Hook
    python3 melder/rotprobe.py --pruefe-verlauf 30      # Nachschau ueber N Tage
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

# Nur Formen, die eine BEHEBUNG behaupten. "feat" und "docs" nicht -- ein
# neues Merkmal behauptet nichts ueber einen vorherigen Fehlzustand.
BEHAUPTUNG = re.compile(
    r"^(fix|bugfix)\b"
    r"|\b(behoben|behebt|repariert|funktioniert wieder|geht wieder|gel(ö|oe)st)\b",
    re.I)

# Der Beleg, in beiden Sprachen. Absichtlich weit: wer einen Beleg NENNT,
# soll nicht an der Formulierung scheitern.
BELEG = re.compile(
    r"rot vor gr(ü|ue)n|rot-probe|rot gegen|rot vorher|war rot"
    r"|schlug (vorher )?fehl|gegenprobe|durchgerutscht"
    r"|red before green|failed before|was red|counter-?check"
    # NACHGETRAGEN 2026-08-20, wenige Stunden nach dem Bau: Dieser Waechter
    # hielt einen Commit an, dessen Nachricht "Gemessen ueber 1 204 Commits"
    # sagte -- und widersprach damit seinem EIGENEN Docstring drei Absaetze
    # weiter oben ("manche Behebungen sind an einer MESSUNG belegt, nicht an
    # einem Test"). Die Absicht stand in der Doku, das Muster kannte sie nicht.
    #
    # Dazu die zweite Haelfte desselben Befunds: melder/ablaufpflicht.py prueft
    # dieselbe Frage mit einem ANDEREN Vokabular. Zwei Waechter fuer eine
    # Frage, zwei Wortlisten -- wer beiden genuegen will, muss beide auswendig
    # kennen. Beide sind jetzt auf denselben Stand gebracht; sie
    # zusammenzulegen ist der naechste Schritt, nicht dieser.
    r"|\bgemessen\b|\bselbsttest\b|\bselftest\b"
    r"|\d+ (xctest-)?f[aä]lle gr[uü]n|\btests? gr[uü]n\b|\d+ passed",
    re.I)


def _aus() -> bool:
    return os.environ.get("BRAINLEHR_ROTPROBE", "").strip().lower() == "aus"


def beurteile(nachricht: str, dateien: list[str]) -> str | None:
    kopf = nachricht.splitlines()[0] if nachricht.strip() else ""
    if not BEHAUPTUNG.search(kopf):
        return None
    if any("test" in d.lower() for d in dateien):
        return None
    if BELEG.search(nachricht):
        return None
    return (
        f'Dieser Commit behauptet eine Behebung ("{kopf[:60]}") und nennt '
        "weder eine angefasste Testdatei noch einen Beleg im Text.\n\n"
        "Gemessen ueber 1 193 Commits seit dem 2026-08-01: 240 behaupten eine "
        "Behebung, 92 davon ohne beides -- 7,7 % aller Commits. Die "
        "Belegpflicht ist der laengste Abschnitt der Hausregeln und die am "
        "haeufigsten gebrochene Regel.\n\n"
        "Zwei Wege bestehen: eine Testdatei im Commit, ODER der Beleg im Text "
        '-- "rot gegen <commit>", "schlug vorher fehl", "Gegenprobe in beide '
        'Richtungen". Wer keinen hat, schreibt es hin ("geaendert, nicht '
        'verifiziert") und formuliert den Betreff entsprechend.'
    )


def _verlauf(tage: int) -> int:
    roh = subprocess.run(
        ["git", "log", f"--since={tage} days ago", "--pretty=%x01%s%x01%b%x02", "--name-only"],
        capture_output=True, text=True).stdout
    n = beanstandet = 0
    for c in roh.split("\x02"):
        if not c.strip():
            continue
        t = c.split("\x01")
        if len(t) < 3:
            continue
        dateien = [z for z in t[2].splitlines() if z and ("/" in z or "." in z)]
        n += 1
        if beurteile(t[1] + "\n" + t[2], dateien):
            beanstandet += 1
    print(f"{n} Commits der letzten {tage} Tage, {beanstandet} ohne Beleg "
          f"({beanstandet/max(n,1):.1%})")
    return 0


def _selftest() -> int:
    # a) Behauptung ohne alles -> Beanstandung.
    assert beurteile("fix(melder): Zaehler korrigiert", ["melder/x.py"])
    assert beurteile("behebt den Absturz beim Start", ["kern/a.py"])

    # b) Testdatei im Commit -> durch.
    assert beurteile("fix(melder): Zaehler korrigiert",
                     ["melder/x.py", "tests/test_x.py"]) is None
    # c) Beleg im Text -> durch, auch ohne Testdatei (eine Messung ist ein Beleg).
    assert beurteile("fix(sicherungen): 96 % unerreichbar\n\nRot gegen 858c82c4: "
                     "fand 0 statt 1.", ["kern/s.py"]) is None
    assert beurteile("fix: parser\n\nred before green against HEAD", ["a.py"]) is None
    # EINE MESSUNG IST EIN BELEG -- nachgetragen am 2026-08-20, nachdem dieser
    # Waechter einen Commit anhielt, der genau das sagte, und damit seinem
    # eigenen Docstring widersprach.
    assert beurteile("fix(x): Vokabular ergaenzt\n\nGemessen ueber 1 204 Commits: "
                     "285 vorher, 246 nachher.", ["melder/x.py"]) is None
    assert beurteile("fix(y): Zaehler\n\nSelbsttest 7 Faelle gruen.", ["melder/y.py"]) is None
    # NEGATIVFALL bleibt: eine Behauptung ohne beides wird weiterhin gefangen.
    assert beurteile("fix(z): laeuft jetzt wieder", ["melder/z.py"])

    # d) NEGATIVFALL: ein Merkmal behauptet keine Behebung.
    assert beurteile("feat(melder): neuer Waechter", ["melder/y.py"]) is None
    assert beurteile("docs(STAND): Lage nachgetragen", ["STAND.md"]) is None
    # e) NEGATIVFALL: leere Nachricht.
    assert beurteile("", []) is None
    # f) Der Schalter wirkt.
    os.environ["BRAINLEHR_ROTPROBE"] = "aus"
    assert _aus() is True
    del os.environ["BRAINLEHR_ROTPROBE"]
    assert _aus() is False

    print("rotprobe: Selbsttest gruen (2 Beanstandungen, Testdatei deckt, "
          "Beleg im Text deckt in zwei Sprachen, feat/docs/leer still, "
          "Schalter wirkt)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    if "--pruefe-verlauf" in sys.argv:
        i = sys.argv.index("--pruefe-verlauf")
        return _verlauf(int(sys.argv[i + 1]) if len(sys.argv) > i + 1 else 30)
    if _aus():
        return 0
    if "--commit-msg" not in sys.argv:
        print(__doc__.strip().splitlines()[-3].strip(), file=sys.stderr)
        return 0
    i = sys.argv.index("--commit-msg")
    if len(sys.argv) <= i + 1:
        return 0
    try:
        nachricht = Path(sys.argv[i + 1]).read_text(encoding="utf-8")
    except OSError:
        return 0
    dateien = subprocess.run(["git", "diff", "--cached", "--name-only"],
                             capture_output=True, text=True).stdout.split()
    grund = beurteile(nachricht, dateien)
    if grund:
        print("\nrotprobe: " + grund + "\n", file=sys.stderr)
        return 1          # Commit anhalten
    return 0


if __name__ == "__main__":
    sys.exit(main())
