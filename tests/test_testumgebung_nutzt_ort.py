"""Die Testumgebung muss ihren DB-Pfad vom Aufloeser (haken/ort.py) beziehen.

BEFUND 2026-08-11: Beim Umzug von knowledge.db auf brainlehr.db bauten
tests/conftest.py (braucht_bestand) und tests/test_vektorlage.py den Pfad
SELBST zusammen (os.environ.get("BEGOD_KNOWLEDGE_DB") oder .../knowledge.db),
statt haken.ort.DB zu fragen. Ergebnis: neun echte, rote Suchbefunde wurden
zu stillen SKIPPED, weil unter dem alten Namen kein Bestand mehr lag -- eine
Umbenennung sah in der Gesamtzeile wie eine Verbesserung aus.

Dieser Test faengt die Fehlerklasse: kein Testmodul unter tests/ darf
"knowledge.db" als Text tragen, ausser es baut sich (per tmp_path) eine
EIGENE, beliebig benannte Wegwerf-Datenbank oder prueft den Aufloeser selbst.
"""
from __future__ import annotations

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent

# tests/test_ort_env_kompat.py prueft haken.ort._ermittle_db() direkt und
# muss den alten Dateinamen als Text kennen, um dessen Fallback zu belegen --
# das ist keine Umgehung des Aufloesers, sondern ein Test UEBER ihn.
# Diese Datei selbst nennt den Namen nur in der eigenen Beschreibung/Regex.
#
# tests/test_paketbau.py (2026-08-21) nennt "knowledge.db"/"brainlehr.db" in
# VERBOTEN -- einer Liste von Dateinamen-Mustern, die NICHT ins Archiv duerfen.
# Das ist kein DB-Pfad, den irgendein Code zum VERBINDEN zusammenbaut (die
# Datei enthaelt keinen sqlite3.connect/haken.ort-Aufruf ueberhaupt), sondern
# ein Archivinhalts-Check -- die Fehlerklasse dieser Wache (stiller SKIP nach
# einer Umbenennung des Bestands) kann dort gar nicht entstehen.
AUSGENOMMEN = {"test_ort_env_kompat.py", "test_paketbau.py", Path(__file__).name}

# Zeilen, die sich ueber tmp_path (oder einen anderen Wegwerf-Ordner) eine
# EIGENE Datenbank anlegen, sind nicht betroffen -- dort ist der Name
# beliebig, es ist nie der Bestand hinter dem Aufloeser.
UNBEDENKLICH = re.compile(r"tmp_path")

TREFFER = re.compile(r'"knowledge\.db"')


def test_kein_testmodul_baut_den_db_namen_selbst_zusammen():
    verdaechtig = []
    for datei in sorted(TESTS.glob("test_*.py")) + [TESTS / "conftest.py"]:
        if datei.name in AUSGENOMMEN:
            continue
        for zeile_nr, zeile in enumerate(
            datei.read_text(encoding="utf-8").splitlines(), start=1
        ):
            # Kommentare ausnehmen: die Geschwisterwache
            # tests/test_produktivcode_nutzt_ort.py erklaert in einem Kommentar,
            # welche Schreibweisen sie verbietet -- und nennt sie dabei woertlich.
            # Ohne diese Zeile beanstandet eine Wache die andere dafuer, dass sie
            # ihre eigene Regel dokumentiert. Kommentierter Code wird nie
            # ausgefuehrt und kann keinen Pfad bauen.
            if zeile.lstrip().startswith("#"):
                continue
            if TREFFER.search(zeile) and not UNBEDENKLICH.search(zeile):
                verdaechtig.append(f"{datei.name}:{zeile_nr}: {zeile.strip()}")
    assert not verdaechtig, (
        "Testcode baut den DB-Namen selbst zusammen statt haken.ort zu "
        "fragen -- eine Umbenennung der Datei macht solche Tests still "
        "uebersprungen statt rot:\n" + "\n".join(verdaechtig)
    )
