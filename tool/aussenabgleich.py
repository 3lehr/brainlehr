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
import re
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
    # Eigenleben des Zielrepos: GitHub-Vorlagen ergeben nur DORT einen Sinn
    # und haben hier bewusst kein Gegenstueck. Ohne diese Zeile meldet der
    # Abgleich sie dauerhaft als "draussen vorhanden, hier nicht mehr" --
    # ein Befund, der nie verschwindet, und der naechste Leser lernt, die
    # ganze Liste zu ueberspringen.
    ".github/",
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


def _umzug(repo: Path, rel: str) -> str | None:
    """Dieselbe Datei unter einem anderen Ordner -- ein Umzug, keine Loeschung.

    Gemessen 2026-08-20: alle 8 vermeintlich geloeschten Dateien des
    weitergebbaren Klons lagen hier weiterhin, nur unter `berichte/` statt
    `melder/` bzw. `messungen/`. Wer das nicht unterscheidet, meldet acht
    Loeschungen, die keine sind -- und eine Loeschung nach aussen ist nach
    dem Push nicht mehr zurueckzuholen."""
    name = Path(rel).name
    for kandidat in repo.glob(f"*/{name}"):
        if kandidat.is_file():
            return str(kandidat.relative_to(repo))
    return None


def pruefe(repo: Path = REPO, aussen: Path = AUSSEN) -> dict:
    dateien = aussenbestand(aussen)
    abweichung, fehlt_innen, umgezogen = [], [], {}
    for rel in dateien:
        innen = repo / rel
        if not innen.is_file():
            ziel = _umzug(repo, rel)
            if ziel:
                umgezogen[rel] = ziel
            else:
                fehlt_innen.append(rel)
            continue
        if not filecmp.cmp(innen, aussen / rel, shallow=False):
            abweichung.append(rel)
    return {
        "geprueft": dateien,
        "abweichung": abweichung,
        "fehlt_innen": fehlt_innen,
        "umgezogen": umgezogen,
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


_IMPORT = re.compile(r"^\s*(?:from\s+([A-Za-z_][\w]*)\s+import|import\s+([A-Za-z_][\w]*))", re.M)


def _lokale_module(baum: Path, ordner: set[str]) -> set[str]:
    """Modulnamen, die in diesem Baum als Datei liegen -- nur flach, weil die
    Suchpfade der Module genau so gesetzt sind (sys.path[:0] = [wurzel, kern,
    haken, ...]), nicht als Paket."""
    namen = set()
    for o in ordner | {""}:
        d = baum / o if o else baum
        if d.is_dir():
            namen |= {f.stem for f in d.glob("*.py")}
    return namen


def importluecken(ergebnis: dict, repo: Path = REPO, aussen: Path = AUSSEN) -> dict:
    """Welche lokalen Module wuerden nach einer Uebernahme FEHLEN.

    Der Anlass ist ein selbst gebauter Schaden, 2026-08-20: Die erste
    Uebernahme kopierte 152 Dateien und machte den weitergebbaren Baum
    kaputt -- kern/ausweis.py importiert `geheimnis`, knowledge_mcp_server.py
    importiert `relevanzlage`, beide liegen draussen nicht. Vorher startete
    brainlehr.py dort, danach brach es mit ModuleNotFoundError. Ein Abgleich,
    der eine Datei einzeln vergleicht, sieht das nie: jede einzelne Datei ist
    fuer sich korrekt, kaputt ist erst ihre Umgebung.

    Transitiv, weil ein fehlendes Modul selbst wieder importiert."""
    draussen_dateien = set(aussenbestand(aussen))
    ordner = {r.split("/")[0] for r in draussen_dateien if "/" in r}
    vorhanden = _lokale_module(aussen, ordner)
    hier = _lokale_module(repo, ordner)

    # Startmenge: die Dateien, die uebernommen wuerden, in ihrer INNEN-Fassung.
    offen = [repo / r for r in ergebnis["abweichung"]]
    gesehen: set[str] = set()
    luecken: dict[str, list[str]] = {}
    while offen:
        datei = offen.pop()
        try:
            text = datei.read_text(errors="replace")
        except OSError:
            continue
        for m in _IMPORT.finditer(text):
            name = m.group(1) or m.group(2)
            if name in vorhanden or name not in hier or name in gesehen:
                continue
            gesehen.add(name)
            luecken.setdefault(name, []).append(
                str(datei.relative_to(repo)))
            # Das fehlende Modul zieht seine eigenen Importe nach.
            for o in sorted(ordner) + [""]:
                kandidat = (repo / o / f"{name}.py") if o else (repo / f"{name}.py")
                if kandidat.is_file():
                    offen.append(kandidat)
                    break
    return luecken


def bericht(ergebnis: dict, neue: list[str] | None = None,
            luecken: dict | None = None) -> str:
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
        "draussen vorhanden, hier weder noch umgezogen", rahmen))
    zeilen += [f"    | {r}" for r in ergebnis["fehlt_innen"]]

    umg = ergebnis.get("umgezogen") or {}
    zeilen.append(_rw.zaehle(geprueft, lambda r: r in umg, str).zeile(
        "hier UMGEZOGEN, draussen am alten Ort", rahmen))
    zeilen += [f"    > {alt} -> {neu_}" for alt, neu_ in sorted(umg.items())]

    if neue is not None:
        zeilen.append(
            f"Kandidaten (hier neu, draussen nicht): {len(neue)} "
            "-- werden NICHT uebernommen, die Auswahl trifft ein Mensch")
        zeilen += [f"    + {r}" for r in neue[:30]]
        if len(neue) > 30:
            zeilen.append(f"    + ... und {len(neue) - 30} weitere")

    if luecken:
        zeilen.append(
            f"IMPORTLUECKEN nach einer Uebernahme: {len(luecken)} Modul(e) "
            "fehlen draussen -- der Baum waere danach nicht lauffaehig")
        for name in sorted(luecken):
            zeilen.append(f"    ! {name} (gebraucht von {luecken[name][0]})")
    return "\n".join(zeilen)


def luecken_schliessen(luecken: dict, repo: Path = REPO,
                       aussen: Path = AUSSEN) -> list[str]:
    """Kopiert genau die Module, ohne die der Zielbaum nach einer Uebernahme
    nicht mehr laeuft -- und NUR die.

    Das ist die eine Ausnahme von "Kandidaten werden nur genannt": ein Modul,
    das ein bereits freigegebenes Modul importiert, ist keine Erweiterung des
    Zuschnitts, sondern die fehlende Haelfte einer bereits getroffenen
    Entscheidung. Wer kern/ausweis.py freigibt und `geheimnis` zurueckhaelt,
    hat nichts zurueckgehalten -- er hat den Baum kaputt gemacht.

    Die Freigabefrage bleibt trotzdem eine: DATEN entscheidet die Spalte
    `freigabe`, CODE entscheidet ein Mensch. Darum liefert diese Funktion die
    Liste dessen zurueck, was sie kopiert hat -- sie ist zum Vorlegen da, nicht
    zum Wegsehen."""
    kopiert = []
    for name in sorted(luecken):
        for ordner in ("kern", "melder", "haken", "berichte", "messungen", ""):
            quelle = (repo / ordner / f"{name}.py") if ordner else (repo / f"{name}.py")
            if quelle.is_file():
                ziel = aussen / ordner / f"{name}.py" if ordner else aussen / f"{name}.py"
                ziel.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(quelle, ziel)
                kopiert.append(str(quelle.relative_to(repo)))
                break
    return kopiert


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
        # NEGATIV, hier und nicht spaeter: solange es den Ordner `melder`
        # DRAUSSEN nicht gibt, darf er keine Kandidaten liefern -- ein neuer
        # Ordner ist eine Entscheidung ueber den Zuschnitt. (Der Umzugsfall
        # unten legt melder/ draussen an und hebt diese Lage auf.)
        assert kandidaten(innen, aussen) == ["kern/brandneu.py"], kandidaten(innen, aussen)

        # UMZUG: dieselbe Datei liegt hier in einem ANDEREN Ordner -- das ist
        # keine Loeschung. Rot vor gruen: gegen die Fassung ohne _umzug()
        # stand sie unter "fehlt_innen" und waere als Loeschkandidat nach
        # aussen gegangen.
        (aussen / "melder").mkdir(exist_ok=True)
        (aussen / "melder" / "umgezogen.py").write_text("u\n")
        (innen / "berichte").mkdir(exist_ok=True)
        (innen / "berichte" / "umgezogen.py").write_text("u\n")
        subprocess.run(["git", "add", "-A"], cwd=aussen, check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-qm", "umzug"], cwd=aussen, check=True)
        e_u = pruefe(innen, aussen)
        assert e_u["umgezogen"] == {"melder/umgezogen.py": "berichte/umgezogen.py"}, e_u
        assert "melder/umgezogen.py" not in e_u["fehlt_innen"], e_u
        # NEGATIV: die echte Verwaiste bleibt eine Verwaiste -- sonst
        # verschluckt die Umzugserkennung jede echte Loeschung.
        assert "kern/verschwunden.py" in e_u["fehlt_innen"], e_u

        # NEGATIV: die identische Datei taucht nirgends auf.
        assert "kern/gleich.py" not in e["abweichung"] + e["fehlt_innen"], e
        # NEGATIV, und das ist der teuerste Fall: die Datenbank steht in
        # BEIDEN Baeumen mit verschiedenem Inhalt und darf trotzdem NIE als
        # Abweichung erscheinen -- sonst kopiert ein --uebernehmen den
        # internen Bestand nach draussen.
        assert "knowledge.db" not in e["abweichung"], e
        assert "knowledge.db" not in e["geprueft"], e

        # IMPORTLUECKE: die uebernommene Datei zieht ein Modul nach, das
        # draussen fehlt -- und dieses wiederum ein zweites (transitiv).
        (innen / "kern" / "anders.py").write_text("import geheimnis\nneu\n")
        (innen / "kern" / "geheimnis.py").write_text("import tiefer\n")
        (innen / "kern" / "tiefer.py").write_text("x\n")
        e_l = pruefe(innen, aussen)
        luecken = importluecken(e_l, innen, aussen)
        assert set(luecken) == {"geheimnis", "tiefer"}, luecken
        assert "kern/anders.py" in luecken["geheimnis"], luecken
        assert "IMPORTLUECKEN" in bericht(e_l, None, luecken)
        # NEGATIV: ein Modul, das draussen SCHON liegt, ist keine Luecke --
        # sonst meldet der Abgleich bei jeder Datei die halbe Standardlage.
        (innen / "kern" / "anders.py").write_text("import gleich\nneu\n")
        assert importluecken(pruefe(innen, aussen), innen, aussen) == {}, "gleich.py liegt draussen"
        # NEGATIV: die Standardbibliothek ist nie eine Luecke.
        (innen / "kern" / "anders.py").write_text("import json\nimport pathlib\nneu\n")
        assert importluecken(pruefe(innen, aussen), innen, aussen) == {}, "stdlib gemeldet"
        (innen / "kern" / "anders.py").write_text("neu\n")
        for weg in ("geheimnis.py", "tiefer.py"):
            (innen / "kern" / weg).unlink()

        # Jetzt gibt es melder/ auch draussen -- also ist die dortige neue
        # Datei folgerichtig ein Kandidat. Der Zuschnitt hat sich geaendert,
        # nicht die Regel.
        k = kandidaten(innen, aussen)
        assert k == ["kern/brandneu.py", "melder/ganz_neuer_ordner.py"], k

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

    print("aussenabgleich: Selbsttest gruen (14 Faelle: Abweichung, Verwaiste, "
          "Gleichstand, Bestand nie abgeglichen, Kandidat nur genannt, neuer "
          "Ordner liefert keine Kandidaten, Nenner in beide Richtungen, "
          "Uebernahme kopiert nichts weiter, Importluecke transitiv, "
          "vorhandenes Modul und Standardbibliothek sind keine Luecke, "
          "Umzug ist keine Loeschung und verschluckt keine echte)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--kandidaten", action="store_true")
    p.add_argument("--uebernehmen", action="store_true")
    p.add_argument("--luecken-schliessen", action="store_true",
                   help="kopiert die fehlenden Module mit und legt sie vor")
    p.add_argument("--trotz-luecken", action="store_true",
                   help="kopiert auch dann, wenn danach Module fehlen")
    args = p.parse_args()
    if args.selftest:
        return _selftest()
    if not AUSSEN.exists():
        print(f"aussenabgleich: kein weitergebbarer Klon unter {AUSSEN}")
        return 0
    e = pruefe()
    neue = kandidaten() if (args.kandidaten or args.uebernehmen) else None
    luecken = importluecken(e)
    print(bericht(e, neue, luecken))
    if args.uebernehmen and luecken and args.luecken_schliessen:
        neu_dazu = luecken_schliessen(luecken)
        print(f"\nLuecken geschlossen: {len(neu_dazu)} Modul(e) zusaetzlich "
              "kopiert -- das ist eine FREIGABE von Code und gehoert vorgelegt:")
        for r in neu_dazu:
            print(f"    + {r}")
        luecken = importluecken(e)
        if luecken:
            print(f"\nes fehlen weiterhin {len(luecken)}: {', '.join(sorted(luecken))}")
            return 1
    if args.uebernehmen and luecken and not args.trotz_luecken:
        print(f"\nABGEBROCHEN, nichts kopiert: {len(luecken)} Modul(e) fehlen "
              "im weitergebbaren Baum. Eine Uebernahme wuerde ihn kaputt "
              "machen -- am 2026-08-20 genau so passiert (brainlehr.py startete "
              "vorher, danach ModuleNotFoundError). Die fehlenden Module sind "
              "Freigabe-KANDIDATEN, keine Ergaenzung: erst entscheiden, ob sie "
              "nach aussen duerfen, dann hier erneut. Wer weiss was er tut: "
              "--trotz-luecken.")
        return 1
    if args.uebernehmen:
        n = uebernehmen(e)
        print(f"\nuebernommen: {n} Datei(en) nach {AUSSEN}. "
              "Der Auszug wird davon NICHT beruehrt -- pflege/export_offen.py "
              "erneuert ihn getrennt, gegen die Freigabe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
