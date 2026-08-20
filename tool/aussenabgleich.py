#!/usr/bin/env python3
"""Gleicht den weitergebbaren Klon gegen dieses Repo ab -- Datei fuer Datei.

ANLASS (Betreiber, 2026-08-20): "ausserdem hat sich einiges verbessert seit
dem letzten push zu github? sollten wir github updaten, also das oeffentliche
repo?" Gemessen an diesem Tag: 241 Commits seit dem letzten Aussenstand, 170
davon auf Pfaden, die es im oeffentlichen Baum ueberhaupt gibt.

WARUM ES DIESES WERKZEUG BRAUCHT, obwohl der Auszug laengst eines hat:
pflege/export_offen.py loest die DATENfrage (nur freigabe='offen' verlaesst
das Haus). Die CODEfrage war bis heute unbeantwortet -- der oeffentliche Klon
unter _brainlehr_open ist ein eigenstaendiges Repo mit eigener Historie, und
wer ihn aktualisieren wollte, kopierte von Hand. Die Vorpruefung vom
2026-08-15 haelt das woertlich fest: "Kein Skript erzeugt oder synchronisiert
das oeffentliche Repo automatisch aus diesem Arbeitsbaum."

DIE AUSWAHL WIRD NICHT ERFUNDEN, SONDERN GELESEN. Welche Dateien nach aussen
gehoeren, ist eine Bewertung (Lizenz, Personenbezug, Betriebsgeheimnis) und
steht dem Menschen zu -- genauso wie bei der Freigabe eines Knotens. Dieses
Werkzeug nimmt deshalb `git ls-files` des Zielbaums als die bereits
getroffene Entscheidung und fasst nichts an, was dort nicht schon liegt.
Gemessen 2026-08-20: 12 von 48 Meldern und 53 von 110 Kernmodulen sind
draussen -- eine Auswahl, keine Teilmenge nach Ordner. Wer sie automatisch
erweitert, veroeffentlicht ungeprueft.

DREI BEFUNDARTEN, absichtlich getrennt (dieselbe Bauform wie
melder/quelle_gegen_betrieb.py, aus dem der Nennerfehler dieses Tages stammt):

  abweichung        -- draussen und drinnen, Inhalt verschieden -> uebernehmbar
  fehlt_innen       -- draussen vorhanden, hier geloescht/verschoben -> NIE
                       automatisch geloescht, immer ein Befund fuer den
                       Menschen (eine Loeschung nach aussen ist unumkehrbar,
                       sobald sie gepusht ist)
  kandidat          -- hier neu, draussen nicht -> nur GENANNT, nie kopiert

DER NENNER IST DIE GEPRUEFTE MENGE, nicht die Befundliste. Am 2026-08-20 hat
genau dieser Fehler in einem frischen Melder "0 von 0 (0.0%)" erzeugt -- eine
Zahl, die nicht unterscheidet, ob 280 Dateien geprueft wurden oder keine.

Aufruf:
    python3 tool/aussenabgleich.py                  # nur messen
    python3 tool/aussenabgleich.py --kandidaten     # zusaetzlich die neuen nennen
    python3 tool/aussenabgleich.py --uebernehmen    # abweichende Dateien kopieren
    python3 tool/aussenabgleich.py --selftest
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import subprocess
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w), str(_w / "kern")]

import rueckwirkung as _rw  # noqa: E402 -- gemeinsame Zaehler-Bauform

REPO = _w
# Geschwisterordner, kein Unterordner: der weitergebbare Klon hat eine EIGENE
# Historie und eine EIGENE knowledge.db. Ein Unterordner waere hier falsch --
# er landete sonst irgendwann selbst im Auszug.
AUSSEN = REPO.parent / "_brainlehr_open"

# Was nie abgeglichen wird, egal ob es im Zielbaum liegt. Die Datenbank und
# ihre Sicherungen gehoeren dem Zielbaum allein und werden ueber
# pflege/export_offen.py erneuert -- ein Kopieren von hier truege den ganzen
# internen Bestand nach draussen.
NIE_ABGLEICHEN = (
    "knowledge.db", "knowledge.db-wal", "knowledge.db-shm",
    "auszug-offen/", "zero_hit_log.jsonl", "VERSION",
    "README.md", "README.de.md", "START_HIER.md", "NOTICE", "LICENSE",
    "LICENSE_FAQ.md", "CONTRIBUTING.md", "KNOWLEDGE_CONTRACT.md",
    "BSI_COMPLIANCE_GATE.md",
)


def _ausgeschlossen(rel: str) -> bool:
    return any(rel == m or rel.startswith(m) for m in NIE_ABGLEICHEN
               if not m.endswith("/")) or any(
        rel.startswith(m) for m in NIE_ABGLEICHEN if m.endswith("/"))


def aussenbestand(aussen: Path) -> list[str]:
    """Die getroffene Auswahl: was der Zielbaum versioniert fuehrt."""
    if not (aussen / ".git").exists():
        return []
    roh = subprocess.run(["git", "ls-files"], cwd=aussen,
                         capture_output=True, text=True).stdout.splitlines()
    return [r for r in roh if r and not _ausgeschlossen(r)]


def pruefe(repo: Path = REPO, aussen: Path = AUSSEN) -> dict:
    dateien = aussenbestand(aussen)
    abweichung, fehlt_innen = [], []
    for rel in dateien:
        innen = repo / rel
        if not innen.is_file():
            fehlt_innen.append(rel)
            continue
        if not filecmp.cmp(innen, aussen / rel, shallow=False):
            abweichung.append(rel)
    return {
        "geprueft": dateien,
        "abweichung": abweichung,
        "fehlt_innen": fehlt_innen,
    }


def kandidaten(repo: Path = REPO, aussen: Path = AUSSEN) -> list[str]:
    """Hier vorhanden, draussen nicht -- in denselben Ordnern, die es draussen
    schon gibt. Nur diese Ordner, weil ein neuer Ordner eine Entscheidung ist
    und keine Ergaenzung."""
    draussen = set(aussenbestand(aussen))
    ordner = {r.split("/")[0] for r in draussen if "/" in r}
    if not ordner:
        return []
    roh = subprocess.run(["git", "ls-files", *sorted(ordner)], cwd=repo,
                         capture_output=True, text=True).stdout.splitlines()
    return [r for r in roh if r and r not in draussen and not _ausgeschlossen(r)]


def bericht(ergebnis: dict, neue: list[str] | None = None) -> str:
    geprueft = ergebnis["geprueft"]
    rahmen = f"ueber {len(geprueft)} versionierte Dateien des weitergebbaren Klons"
    abw = set(ergebnis["abweichung"])
    fehlt = set(ergebnis["fehlt_innen"])

    zeilen = [
        _rw.zaehle(geprueft, lambda r: r in abw, str).zeile(
            "Dateien mit abweichendem Inhalt", rahmen),
    ]
    zeilen += [f"    | {r}" for r in ergebnis["abweichung"][:20]]
    if len(ergebnis["abweichung"]) > 20:
        zeilen.append(f"    | ... und {len(ergebnis['abweichung']) - 20} weitere")

    zeilen.append(_rw.zaehle(geprueft, lambda r: r in fehlt, str).zeile(
        "draussen vorhanden, hier nicht mehr", rahmen))
    zeilen += [f"    | {r}" for r in ergebnis["fehlt_innen"]]

    if neue is not None:
        zeilen.append(
            f"Kandidaten (hier neu, draussen nicht): {len(neue)} "
            "-- werden NICHT uebernommen, die Auswahl trifft ein Mensch")
        zeilen += [f"    + {r}" for r in neue[:30]]
        if len(neue) > 30:
            zeilen.append(f"    + ... und {len(neue) - 30} weitere")
    return "\n".join(zeilen)


def uebernehmen(ergebnis: dict, repo: Path = REPO, aussen: Path = AUSSEN) -> int:
    """Kopiert NUR die abweichenden Dateien, die es draussen schon gibt.
    Loescht nie, legt nie an."""
    for rel in ergebnis["abweichung"]:
        shutil.copy2(repo / rel, aussen / rel)
    return len(ergebnis["abweichung"])


def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        wurzel = Path(td)
        innen, aussen = wurzel / "innen", wurzel / "aussen"
        for p in (innen / "kern", aussen / "kern", innen / "melder", aussen / "melder"):
            p.mkdir(parents=True)
        (innen / "kern" / "gleich.py").write_text("a\n")
        (aussen / "kern" / "gleich.py").write_text("a\n")
        (innen / "kern" / "anders.py").write_text("neu\n")
        (aussen / "kern" / "anders.py").write_text("alt\n")
        (aussen / "kern" / "verschwunden.py").write_text("x\n")
        (innen / "kern" / "brandneu.py").write_text("y\n")
        # Und ein Ordner, den es DRAUSSEN gar nicht gibt: er darf keine
        # Kandidaten liefern. Ein neuer Ordner ist eine Entscheidung ueber
        # den Zuschnitt des weitergebbaren Repos, keine Ergaenzung.
        (innen / "melder" / "ganz_neuer_ordner.py").write_text("z\n")
        (aussen / "knowledge.db").write_text("BESTAND")
        (innen / "knowledge.db").write_text("ANDERER BESTAND")
        for baum in (innen, aussen):
            subprocess.run(["git", "init", "-q"], cwd=baum, check=True)
            subprocess.run(["git", "add", "-A"], cwd=baum, check=True)
            subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                            "commit", "-qm", "x"], cwd=baum, check=True)

        e = pruefe(innen, aussen)
        # POSITIV: die geaenderte Datei faellt auf.
        assert e["abweichung"] == ["kern/anders.py"], e
        # POSITIV: die draussen verwaiste Datei faellt auf.
        assert e["fehlt_innen"] == ["kern/verschwunden.py"], e
        # NEGATIV: die identische Datei taucht nirgends auf.
        assert "kern/gleich.py" not in e["abweichung"] + e["fehlt_innen"], e
        # NEGATIV, und das ist der teuerste Fall: die Datenbank steht in
        # BEIDEN Baeumen mit verschiedenem Inhalt und darf trotzdem NIE als
        # Abweichung erscheinen -- sonst kopiert ein --uebernehmen den
        # internen Bestand nach draussen.
        assert "knowledge.db" not in e["abweichung"], e
        assert "knowledge.db" not in e["geprueft"], e

        k = kandidaten(innen, aussen)
        assert k == ["kern/brandneu.py"], k
        assert not any("ganz_neuer_ordner" in r for r in k), k

        # DER NENNER ist die gepruefte Menge, nicht die Befundliste.
        text = bericht(e, k)
        assert f"von {len(e['geprueft'])}" in text, text
        assert len(e["geprueft"]) > len(e["abweichung"]), e
        # Gegenprobe: ohne Befund bleibt der Nenner stehen.
        (innen / "kern" / "anders.py").write_text("alt\n")
        (innen / "kern" / "verschwunden.py").write_text("x\n")
        sauber = pruefe(innen, aussen)
        assert sauber["abweichung"] == [] and sauber["fehlt_innen"] == [], sauber
        assert f"0 von {len(sauber['geprueft'])}" in bericht(sauber), bericht(sauber)

        # Uebernehmen kopiert genau die abweichenden und nichts sonst.
        (innen / "kern" / "anders.py").write_text("neu\n")
        e2 = pruefe(innen, aussen)
        assert uebernehmen(e2, innen, aussen) == 1
        assert (aussen / "kern" / "anders.py").read_text() == "neu\n"
        assert (aussen / "knowledge.db").read_text() == "BESTAND", "Bestand wurde ueberschrieben"
        assert not (aussen / "kern" / "brandneu.py").exists(), "Kandidat wurde ungefragt uebernommen"
        assert (aussen / "kern" / "verschwunden.py").exists(), "draussen geloescht"

    print("aussenabgleich: Selbsttest gruen (10 Faelle: Abweichung, Verwaiste, "
          "Gleichstand, Bestand nie abgeglichen, Kandidat nur genannt, Nenner "
          "in beide Richtungen, Uebernahme kopiert nichts weiter)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--kandidaten", action="store_true")
    p.add_argument("--uebernehmen", action="store_true")
    args = p.parse_args()
    if args.selftest:
        return _selftest()
    if not AUSSEN.exists():
        print(f"aussenabgleich: kein weitergebbarer Klon unter {AUSSEN}")
        return 0
    e = pruefe()
    neue = kandidaten() if (args.kandidaten or args.uebernehmen) else None
    print(bericht(e, neue))
    if args.uebernehmen:
        n = uebernehmen(e)
        print(f"\nuebernommen: {n} Datei(en) nach {AUSSEN}. "
              "Der Auszug wird davon NICHT beruehrt -- pflege/export_offen.py "
              "erneuert ihn getrennt, gegen die Freigabe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
