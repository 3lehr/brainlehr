#!/usr/bin/env python3
"""Prüft die versionierbare Positivliste auf offensichtliche private Artefakte."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAD_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".log", ".dump", ".bak", ".pem", ".key", ".p12", ".pfx", ".p8"}
BAD_NAMES = {".env", "knowledge.db"}
PATTERNS = {
    "absolute-path": re.compile(r"/(?:Users|Volumes)/"),
    # BEHOBEN 2026-08-23: hier stand \\. in einem Raw-String, also Backslash
    # PLUS Punkt -- die Pruefung hat nie eine einzige Adresse gefunden.
    # Aufgefallen an einer Negativprobe -- eine erfundene Adresse mit echter
    # Domaene ging glatt durch --, nicht im
    # Betrieb: ein Waechter, der nichts findet, sieht wie einer aus, der nichts
    # zu finden hat.
    #
    # example.com/.net/.org sind nach RFC 2606 fuer Dokumentation reserviert
    # und koennen niemandem gehoeren -- sie sind ausgenommen, sonst waere die
    # Pruefung in jedem Testwert rot und wuerde deshalb abgeschaltet.
    "email": re.compile(
        r"[A-Za-z0-9._%+-]+@(?!example\.(?:com|net|org)\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "token": re.compile("(?:gh" + "p_|sk" + "-|AKIA)[A-Za-z0-9_-]{16,}"),
    "key-material": re.compile("-----BEGIN (?:[A-Z ]+" + "KEY)-----"),
    # NACHGESCHAERFT 2026-08-23, vor der Freigabe des Quellcodes. Der Pruefer
    # meldete 173 Treffer, und JEDER EINZELNE war ein Fehlalarm -- nachgesehen,
    # nicht abgewunken. Ein Waechter, der bei nachweislich sauberem Inhalt
    # anschlaegt, ist selbst der Befund; die Behebung gehoert in die Regel und
    # nicht in eine Umformulierung des Inhalts.
    #
    # internal-id: ENTFERNT. Sie traf 96 Lehren-Kennungen, alle in
    # Kommentaren, alle in der Form "L-xxxxxx: <abstrakte Lehre>". Genau die
    # nennt die Veroeffentlichungsregel oeffentlich ("abstrakte Coding-
    # Lehren"). Privat waere eine Kennung mit KONKRETEM Anwendungswissen
    # dahinter -- und diese beiden Faelle haben dieselbe FORM. Ein regulaerer
    # Ausdruck kann sie nicht trennen.
    #
    # Zwei Auswege waeren falsch gewesen: die Kennungen aus den Kommentaren
    # streichen (sie sind die Nachfahrbarkeit, die dieses Haus ausmacht), oder
    # eine Ausnahmeliste mit 96 Eintraegen fuehren (eine Sammelfreigabe, die
    # niemand nachprueft, ist keine Pruefung -- L-95d30e).
    #
    # Der Bestand selbst bleibt geschuetzt, und zwar wirksamer: ueber
    # BAD_SUFFIXES (.db, .sqlite, .dump, .bak) und BAD_NAMES. Was hier
    # verloren geht, ist eine Pruefung, die nie das geprueft hat, wofuer sie
    # gedacht war.
    # operator-text: traf 34-mal den FELDNAMEN betreiber_weisung aus der
    # Schnittstelle. Ein Feldname ist keine Weisung. Gesucht wird jetzt der
    # Feldname MIT einem zugewiesenen Zitat.
    "operator-text": re.compile("betreiber" + "_weisung\\s*=\\s*[\"\u201e]|operator" + " instruction", re.I),
    # private-context: traf 41-mal den Dateinamen CLAUDE.md -- den oeffentlich
    # bekannten Namen der Projektanweisung, den dieser Code als Normquelle
    # LIEST. Null Treffer auf die tatsaechlich privaten Namen. Der Dateiname
    # ist raus, die privaten Namen bleiben.
    "private-context": re.compile("brain" + "lehr-privat|beg" + "od2026", re.I),
}


def files():
    listed = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True, text=True, capture_output=True)
    for name in listed.stdout.splitlines():
        yield ROOT / name


def main():
    findings = []
    for path in files():
        relative = path.relative_to(ROOT)
        if path.name in BAD_NAMES or path.suffix.lower() in BAD_SUFFIXES or ".env" in path.name:
            findings.append(("forbidden-file", relative))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(("binary", relative))
            continue
        for category, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append((category, relative))
    for category, path in findings:
        print(f"{category}: {path}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
