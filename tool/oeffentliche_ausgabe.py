#!/usr/bin/env python3
"""Erzeugt die oeffentliche Ausgabe -- per Skript, nicht von Hand.

BETREIBERFRAGE 2026-08-20: "koennnen wir brainlehr fuer die zukunft so
anlegen das dies per script geht? das war sowieso einmal im plan gestanden,
das wir wissen auch fuer andere exportieren koennen?!"

UND DIE VORFRAGE, weil sie eine Fehlannahme ausraeumt: "die ganzen checks
werden per ki gemacht? mit welcher sonntet? haiku?" -- NEIN. Kein Modell im
Spiel, an keiner Stelle dieses Weges. pflege/export_offen.py ist SQL plus
Freigabefeld, tools/privacy_check.py ist Regex plus ein Abgleich gegen den
Auszug, tool/aussenabgleich.py ist ein Dateivergleich. Was am 2026-08-20 ein
Modell gemacht hat, waren die BEURTEILUNGEN (welcher Eintrag beantwortet
welche Frage, taugt er als Zweitziel) -- Urteile ueber Inhalt, nie die
Pruefungen selbst.

WAS BIS HEUTE FEHLTE, und es war genau ein Stueck: die AUSWAHL. Drei
Werkzeuge gab es schon --

    pflege/export_offen.py      welche DATEN gehen raus   (freigabe='offen')
    tools/privacy_check.py      ist eine Datei sauber      (im Export)
    tool/aussenabgleich.py      was weicht ab              (Klon gegen Repo)

-- aber welche CODE-Dateien nach aussen gehoeren, entschied ein Mensch. Das
Ergebnis war ein oeffentlicher Stand mit 25 Dateien, waehrend die
Betreiberentscheidung "vollstaendiger Brainlehr-Code, sichere Tests und
abstrakte Coding-Lehren" lautet. Gemessen am 2026-08-20: 438 Dateien
bestehen die Pruefung.

DIE AUSWAHLREGEL IST GEMESSEN, NICHT GESETZT: Eine Datei geht nach aussen,
wenn der Privacy-Check des Exports sie nicht beanstandet -- kein zweiter
Massstab und ausdruecklich KEINE gepflegte Positivliste. Eine Handliste
kennt nur, woran ihr Autor beim Schreiben dachte (L-0ca81c), und altert
gegen den Bestand.

WAS DIESES SKRIPT NICHT TUT: Es entscheidet nicht, WAS freigegeben ist --
das ist eine Bewertung (Lizenz, Personenbezug, Betriebsgeheimnis) und bleibt
beim Menschen. Es pusht nicht. Und es loescht im Ziel nichts, was es nicht
selbst geschrieben hat.

Aufruf:
    python3 tool/oeffentliche_ausgabe.py                # nur messen
    python3 tool/oeffentliche_ausgabe.py --uebernehmen  # Dateien kopieren
    python3 tool/oeffentliche_ausgabe.py --selftest
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w), str(_w / "kern")]

import rueckwirkung as _rw  # noqa: E402

REPO = _w
ZIEL = REPO.parent / "_brainlehr_public"

# Die Ordner, aus denen ueberhaupt etwas nach aussen gehen kann. Bewusst eine
# Liste von ORDNERN und keine Dateiliste: eine Datei kommt kuenftig von selbst
# dazu, wenn sie die Pruefung besteht -- eine Dateiliste muesste gepflegt
# werden und waere binnen Wochen unvollstaendig.
QUELLORDNER = ("kern/", "melder/", "haken/", "tests/", "tool/", "pflege/",
               "berichte/", "migrationen/", "schreibpruefstand/", "docs/",
               # Seit 2026-08-20: Die Messlaeufe belegen die Zahlen, mit denen
               # brainlehr ueber sich selbst spricht -- eine Schwelle von 0,65
               # ohne die Erhebung dahinter ist eine Behauptung. Aufgefallen
               # ist der fehlende Ordner nicht durch diese Ueberlegung, sondern
               # weil 12 mitgelieferte Testdateien im Export an Modulen aus
               # `messungen/` abbrachen: Die Tests waren da, ihr Gegenstand
               # nicht.
               "messungen/",
               # Seit 2026-08-20: Der Lizenzwaechter muss MIT DEM REPO wandern.
               # Ein Hook unter .git/hooks/ waere der falsche Ort -- er ist
               # nicht versioniert und haette genau das Neuanlegen des
               # Export-Verzeichnisses nicht ueberlebt, also den Vorgang, der
               # den MIT-Fehler ueberhaupt erzeugt hat.
               #
               # Gezielt nur workflows/, nicht .github/ insgesamt: dort liegt
               # auch eine Copilot-Anweisungsdatei, die nichts im oeffentlichen
               # Repo zu suchen hat.
               ".github/workflows/")
QUELLDATEIEN = ("schema.sql", "brainlehr.py", "knowledge_mcp_server.py",
                "requirements.txt",
                # Seit 2026-08-20 ausdruecklich MITGELIEFERT statt dem Ziel
                # ueberlassen -- die Lizenz gehoert dem Werk, nicht dem Export.
                "LICENSE", "CONTRIBUTING.md", "LICENSE_FAQ.md")

# Was im Ziel dem Ziel gehoert und nie ueberschrieben wird: seine eigene
# Beschreibung, seine Lizenz, sein Pruefwerkzeug, sein Auszug.
NIE_UEBERSCHREIBEN = (
    "README.md", "README.de.md", "NOTICE", "SECURITY.md",
    "PUBLICATION_POLICY.md", "RELEASE_NOTES.md", "AI_HANDOFF.md",
    ".gitignore", "tools/privacy_check.py", "auszug-offen/",
    "integrations/", "docs/FEATURE_MATRIX.json", "docs/AI_DECISIONS.md",
)

# LICENSE, CONTRIBUTING.md und LICENSE_FAQ.md standen bis 2026-08-20 unter
# NIE_UEBERSCHREIBEN -- als "gehoert dem Ziel" gedacht. Genau daran lag es:
# Der Export wurde neu angelegt, bekam eine MIT-Datei als VORGABEWERT, und
# das Werkzeug fasste sie danach nie wieder an. Drei Tage stand das
# oeffentliche Repo unter MIT, waehrend AGPL-3.0 plus CLA beschlossen war.
#
# Die Lizenz gehoert nicht dem Export, sondern dem Werk. Sie kommt jetzt aus
# dem Arbeitsrepo wie jede andere Datei -- und tests/test_lizenz.py faellt
# rot, wenn sie es nicht tut.


def _pruefer():
    """Der Privacy-Check des ZIELS, nicht eine Kopie davon.

    Bewusst importiert statt nachgebaut: Zwei Kopien einer Pruefung driften
    auseinander, und dann misst diese Auswahl etwas anderes als das, was im
    Ziel spaeter anschlaegt -- genau die Klasse aus L-600726 (das wirksame
    Artefakt ist nicht das, das im Quelltext steht)."""
    pfad = ZIEL / "tools" / "privacy_check.py"
    if not pfad.is_file():
        return None
    spec = importlib.util.spec_from_file_location("_pc", pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_KENNUNG = re.compile(r"\bL-[0-9a-f]{6}\b")
_MUSTER = {
    "absolute-path": re.compile(r"/(?:Users|Volumes)/"),
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "token": re.compile("(?:gh" + "p_|sk" + "-|AKIA)[A-Za-z0-9_-]{16,}"),
    "key-material": re.compile("-----BEGIN (?:[A-Z ]+" + "KEY)-----"),
    "operator-text": re.compile("betreiber" + "_weisung|operator" + " instruction", re.I),
    "private-context": re.compile("brain" + "lehr-privat|beg" + "od2026|cla" + "ude" + chr(92) + ".md", re.I),
}
_VERBOTENE_ENDUNGEN = {".db", ".sqlite", ".sqlite3", ".log", ".dump", ".bak",
                       ".pem", ".key", ".p12", ".pfx", ".p8"}


def beanstandung(pfad: Path, freigegeben: set) -> str | None:
    """Warum diese Datei NICHT nach aussen darf -- oder None.

    Nutzt die Muster des Ziel-Pruefers, wenn er erreichbar ist, sonst die
    hier hinterlegte Fassung. Beide Wege liefern dieselben Kategorienamen,
    damit ein Bericht in jedem Fall lesbar bleibt."""
    if pfad.suffix.lower() in _VERBOTENE_ENDUNGEN or pfad.name.startswith(".env"):
        return "forbidden-file"
    try:
        text = pfad.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return "binary"
    pc = _pruefer()
    muster = pc.PATTERNS if pc else _MUSTER
    for name, m in muster.items():
        if m.search(text):
            return name
    # Eine Lehrenkennung ohne Freigabe ist KEIN Grund, die Datei wegzulassen
    # -- sie wird beim Kopieren ersetzt (siehe _kennungen_neutralisieren).
    # Bis 2026-08-20 war sie einer, und das kostete 139 Dateien wegen
    # einzelner Kennungen in Kommentaren.
    return None


def freigegebene_kennungen(auszug: Path) -> set:
    """Lehrenkennungen aus dem Auszug -- das ist per Bauart genau das, was
    der Leser bekommt.

    Der Auszug ist verschachtelt ({"tabelle": ..., "zeile": {...}}). Eine
    Ebene zu hoch zu greifen liefert 0 Kennungen und damit ein falsches
    Ergebnis: am 2026-08-20 galten dadurch 274 Dateien als beanstandet."""
    if not auszug.is_file():
        return set()
    raus = set()
    for zeile in auszug.read_text(encoding="utf-8", errors="replace").splitlines():
        if not zeile.strip():
            continue
        try:
            satz = json.loads(zeile)
        except ValueError:
            continue
        inhalt = satz.get("zeile") if isinstance(satz.get("zeile"), dict) else satz
        kennung = str(inhalt.get("id") or "")
        if kennung.startswith("L-"):
            raus.add(kennung)
    return raus


_IMPORT = re.compile(r"^\s*(?:from\s+([A-Za-z_]\w*)\s+import|import\s+([A-Za-z_]\w*))", re.M)


def _lokale_module(wurzel: Path, pfade) -> dict:
    """Modulname -> Datei, fuer alle Dateien im Suchraum.

    Flach je Ordner, weil die Module dieses Repos so importiert werden
    (sys.path[:0] = [wurzel, kern, haken, ...]) und nicht als Paket."""
    return {Path(p).stem: Path(p) for p in pfade}


def lauffaehig_machen(auswahl: dict, wurzel: Path) -> dict:
    """Entfernt jede Datei, deren Importe im Export fehlen wuerden.

    DER BEFUND, der diese Funktion verlangt (2026-08-20): Die Auswahl nach
    Privacy lieferte 438 einzeln saubere Dateien -- und `pytest` brach im
    Export mit 79 SAMMELFEHLERN ab, weil Tests Module importieren, die die
    Auswahl abgelehnt hatte (speicher, knowledge_lint, konfidenz und
    weitere). Jede Datei fuer sich korrekt, kaputt ist ihre Umgebung.
    Dieselbe Klasse wie beim weitergebbaren Klon am selben Tag.

    BIS ZUM FIXPUNKT, nicht eine Ebene tief: Faellt C heraus, faellt auch B,
    das C importiert, und dann A, das B importiert. Wer nur eine Ebene
    prueft, laesst A stehen und der Export bricht beim zweiten Import.

    Was NICHT geprueft wird: Standardbibliothek und fremde Pakete -- alles,
    was kein Modul dieses Repos ist, muss der Empfaenger ohnehin selbst
    haben. `import json` darf nichts ausloesen, sonst faellt alles heraus."""
    drin = {Path(p) for p in auswahl["gewaehlt"]}
    abgelehnt = dict(auswahl["abgelehnt"])
    # Alle Modulnamen, die dieses Repo ueberhaupt kennt -- nur sie koennen
    # fehlen. Gebildet ueber das GANZE Repo, nicht ueber die Kandidaten:
    # Bis 2026-08-20 stand hier "gewaehlt plus abgelehnt", also die
    # Kandidatenmenge. Ein Modul in einem Ordner, der nicht in QUELLORDNER
    # steht, kam in keiner der beiden Mengen vor und galt damit als
    # Fremdpaket wie `json` -- der Import blieb stehen, die Datei wanderte in
    # den Export, und dort brach sie ab. 12 Testdateien scheiterten an
    # Modulen aus `messungen/`, das schlicht in keiner Liste stand.
    #
    # Die Luecke irrte in die FALSCHE Richtung: durchlassen statt sperren,
    # und der Fehler zeigte sich erst beim Empfaenger.
    alle_namen = {d.stem for d in wurzel.rglob("*.py")
                  if ".git" not in d.parts and "node_modules" not in d.parts}

    while True:
        vorhanden = {p.stem for p in drin}
        raus = {}
        for p in sorted(drin):
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for m in _IMPORT.finditer(text):
                name = m.group(1) or m.group(2)
                if name in vorhanden or name not in alle_namen:
                    continue
                raus[p] = f"import-fehlt:{name}"
                break
        if not raus:
            return {"gewaehlt": sorted(drin), "abgelehnt": abgelehnt}
        for p, grund in raus.items():
            drin.discard(p)
            abgelehnt[str(p.relative_to(wurzel))] = grund


def kandidaten(repo: Path = REPO) -> list[Path]:
    roh = subprocess.run(["git", "ls-files"], cwd=repo, capture_output=True,
                         text=True).stdout.splitlines()
    return [repo / r for r in roh
            if r.startswith(QUELLORDNER) or r in QUELLDATEIEN]


def _geschuetzt(rel: str) -> bool:
    return any(rel == n or rel.startswith(n) for n in NIE_UEBERSCHREIBEN)


def waehle(pfade: list, wurzel: Path, freigegeben: set) -> dict:
    gewaehlt, abgelehnt = [], {}
    for p in pfade:
        rel = str(Path(p).relative_to(wurzel))
        grund = beanstandung(Path(p), freigegeben)
        if grund:
            abgelehnt[rel] = grund
        else:
            gewaehlt.append(Path(p))
    return {"gewaehlt": gewaehlt, "abgelehnt": abgelehnt}


PLATZHALTER = "<nicht oeffentliche Lehre>"
_TEXTENDUNGEN = {".py", ".md", ".sql", ".txt", ".json", ".sh", ".toml", ".yaml", ".yml"}


def _kennungen_neutralisieren(text: str, freigegeben: set) -> str:
    """Ersetzt Verweise auf Lehren, die der Leser nicht bekommt.

    Ein Zeiger ins Leere ist fuer ihn wertlos und verraet allein durch sein
    Vorhandensein, dass es dort etwas gibt. Ersetzt statt geloescht: der Satz
    bleibt lesbar ("dieselbe Klasse wie <nicht oeffentliche Lehre>"), und der
    Leser sieht, DASS dort etwas fehlt, statt einen unerklaerten Bruch zu
    finden. Dieselbe Entscheidung wie im Auszug, hier fuer Quelltext.

    Angefasst wird ausschliesslich das KOPIERTE Exemplar -- der Arbeitsstand
    bleibt unberuehrt. Und ausschliesslich die Kennung: eine Kennung ist nie
    ein Bezeichner, nie ein Schluesselwort, nie Teil einer Zeichenkette, die
    das Programm auswertet. Deshalb ist diese Ersetzung die einzige, die
    beim Kopieren stattfindet -- ein Heimatpfad im Code wird NICHT
    wegretuschiert, sondern bleibt ein Befund und faellt heraus."""
    return _KENNUNG.sub(
        lambda m: m.group(0) if m.group(0) in freigegeben else PLATZHALTER, text)


def uebernehmen(gewaehlt: list, repo: Path = REPO, ziel: Path = ZIEL,
                freigegeben: set | None = None) -> dict:
    kopiert, uebersprungen = [], []
    for p in gewaehlt:
        rel = str(p.relative_to(repo))
        if _geschuetzt(rel):
            uebersprungen.append(rel)
            continue
        z = ziel / rel
        z.parent.mkdir(parents=True, exist_ok=True)
        if freigegeben is not None and p.suffix.lower() in _TEXTENDUNGEN:
            roh = p.read_text(encoding="utf-8", errors="strict")
            z.write_text(_kennungen_neutralisieren(roh, freigegeben), encoding="utf-8")
        else:
            shutil.copy2(p, z)
        kopiert.append(rel)
    return {"kopiert": kopiert, "uebersprungen_weil_dem_ziel_gehoerend": uebersprungen}


def aufraeumen(gewaehlt: list, repo: Path = REPO, ziel: Path = ZIEL) -> list:
    """Entfernt im Ziel, was ein frueherer Lauf kopiert hat und die Auswahl
    heute nicht mehr traegt.

    Ohne diesen Schritt bleibt eine einmal kopierte Datei fuer immer liegen --
    auch wenn sie inzwischen beanstandet wird oder ihre Importe fehlen. Der
    Export waere dann eine Ansammlung aller je bestandenen Pruefungen statt
    des heutigen Ergebnisses.

    Angefasst wird ausschliesslich, was aus den QUELLORDNERN stammt und dem
    Ziel nicht selbst gehoert -- README, Lizenz, Pruefwerkzeug und Auszug
    bleiben unberuehrt."""
    behalten = {str(Path(p).relative_to(repo)) for p in gewaehlt}
    weg = []
    for ordner in QUELLORDNER:
        wurzel = ziel / ordner
        if not wurzel.is_dir():
            continue
        for datei in sorted(wurzel.rglob("*")):
            if not datei.is_file():
                continue
            rel = str(datei.relative_to(ziel))
            if rel in behalten or _geschuetzt(rel):
                continue
            if not (repo / rel).exists():
                continue  # gehoert dem Ziel, kam nie von hier
            datei.unlink()
            weg.append(rel)
    return weg


def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        (t / "rein.py").write_text("X = 1\n")
        (t / "pfad.py").write_text('P = "/Users/jemand/x"\n')
        (t / "mit.py").write_text("# siehe L-abc123\n")
        (t / "ohne.py").write_text("# siehe L-999999\n")
        (t / "b.db").write_bytes(b"SQLite format 3\x00")
        assert beanstandung(t / "rein.py", set()) is None
        assert beanstandung(t / "pfad.py", set()) == "absolute-path"
        assert beanstandung(t / "mit.py", {"L-abc123"}) is None
        assert beanstandung(t / "ohne.py", {"L-abc123"}) is None
        assert _kennungen_neutralisieren("L-abc123 L-999999", {"L-abc123"}) == \
            f"L-abc123 {PLATZHALTER}"
        assert beanstandung(t / "b.db", set()) == "forbidden-file"
        erg = waehle([t / "rein.py", t / "pfad.py"], t, set())
        assert [p.name for p in erg["gewaehlt"]] == ["rein.py"]
        assert erg["abgelehnt"] == {"pfad.py": "absolute-path"}
    print("oeffentliche_ausgabe: Selbsttest gruen (7 Faelle: sauber, "
          "Heimatpfad, Kennung mit und ohne Freigabe (ersetzt, nicht "
          "abgelehnt), Datenbank nie, "
          "Auswahl nennt beide Seiten)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--uebernehmen", action="store_true")
    args = p.parse_args()
    if args.selftest:
        return _selftest()
    if not ZIEL.exists():
        print(f"kein Export-Arbeitsbereich unter {ZIEL}")
        return 1

    frei = freigegebene_kennungen(ZIEL / "auszug-offen" / "bestand.jsonl")
    if not frei:
        print("ABBRUCH: keine freigegebenen Lehrenkennungen im Auszug gefunden.\n"
              "Erst pflege/export_offen.py laufen lassen -- ohne Auszug waere "
              "JEDE Kennung im Code eine Beanstandung, und die Auswahl misst "
              "dann ihre eigene fehlende Grundlage.")
        return 2

    alle = kandidaten()
    roh = waehle(alle, REPO, frei)
    vor = len(roh["gewaehlt"])
    erg = lauffaehig_machen(roh, wurzel=REPO)
    if vor != len(erg["gewaehlt"]):
        print(f"nach Importpruefung: {vor} -> {len(erg['gewaehlt'])} "
              f"({vor - len(erg['gewaehlt'])} Datei(en) haetten im Export "
              f"nicht importiert werden koennen)")
    b = _rw.zaehle(alle, lambda p: Path(p) in erg["gewaehlt"], str)
    print(b.zeile("Dateien, die die Pruefung bestehen",
                  f"ueber {len(alle)} versionierte Dateien in {len(QUELLORDNER)} Quellordnern"))
    print(f"freigegebene Lehrenkennungen im Auszug: {len(frei)}")
    print("\nabgelehnt, nach Grund:")
    from collections import Counter
    for grund, k in Counter(erg["abgelehnt"].values()).most_common():
        print(f"  {grund:<24} {k:>5}")

    if args.uebernehmen:
        weg = aufraeumen(erg["gewaehlt"])
        if weg:
            print(f"\nim Ziel entfernt, weil nicht mehr gewaehlt: {len(weg)}")
        u = uebernehmen(erg["gewaehlt"], freigegeben=frei)
        print(f"\nkopiert: {len(u['kopiert'])} Datei(en) nach {ZIEL}")
        if u["uebersprungen_weil_dem_ziel_gehoerend"]:
            print(f"uebersprungen (gehoeren dem Ziel): "
                  f"{len(u['uebersprungen_weil_dem_ziel_gehoerend'])}")
        print("\nNICHT gepusht -- das entscheidet ein Mensch. Vorher im Ziel:"
              "\n  python3 tools/privacy_check.py"
              "\n  python3 -m pytest -q tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
