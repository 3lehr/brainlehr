"""Produktivcode muss seinen DB-Pfad vom Aufloeser (haken/ort.py) beziehen.

BEFUND (Auftrag 2026-08-12, Knoten 3bd128cc): Beim Umzug von knowledge.db auf
brainlehr.db bauten sechs Produktivdateien den Pfad SELBST zusammen statt
haken.ort zu fragen -- teils mit eigener Auswertung von BEGOD_KNOWLEDGE_DB,
teils als nackter String. kern/normbezug.py::belegt() meldete dadurch JEDES
Normzitat als unbelegt, ohne die Datenbank je zu oeffnen: der alte, selbst
gebaute Pfad existierte nach der Umbenennung nicht mehr.

Dieser Test faengt die Fehlerklasse fuer den Produktivbaum (Pendant zu
tests/test_testumgebung_nutzt_ort.py, das dasselbe fuer tests/ prueft): kein
Modul ausserhalb von tests/ darf den alten Dateinamen (siehe TREFFER unten,
bewusst nicht woertlich in diesem Text, sonst meldet sich dieser Test selbst)
als Text tragen, ausser es baut sich (per tmp_path) eine EIGENE
Wegwerf-Datenbank oder ist ausdruecklich ausgenommen.
"""
from __future__ import annotations

import re
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent

# haken/ort.py traegt den alten Namen BERECHTIGT: dort steht der Rueckfallpfad
# fuer Installationen ohne gesetzte Umgebungsvariable und ohne migrierte Datei
# -- das ist der Aufloeser selbst, keine Umgehung von ihm.
#
# migrationen/ ist ausgenommen: Migrationsskripte sind Momentaufnahmen eines
# einmaligen Laufs zu einem bestimmten Datum (hier: 2026-08-08, DREI TAGE VOR
# der Umbenennung auf brainlehr.db) und laufen nicht erneut -- ein alter
# Dateiname darin ist ein historischer Fakt, kein Bug. Ausserdem GRENZEN
# dieses Auftrags: migrationen/lauf_titelverteidiger_2026-08-08.py ist fremde,
# laufende Sitzung und darf nicht angefasst werden.
AUSGENOMMENE_ORDNER = ("migrationen", "tests", "__pycache__", ".claude")
AUSGENOMMENE_DATEIEN = {WURZEL / "haken" / "ort.py"}

# Zeilen, die sich ueber tmp_path (oder einen anderen Wegwerf-Ordner) eine
# EIGENE Datenbank anlegen, sind unbedenklich -- dort ist der Name beliebig,
# es ist nie der gemeinsame Bestand hinter dem Aufloeser.
UNBEDENKLICH = re.compile(r"tmp_path")

TREFFER = re.compile(r'"knowledge\.db"')


def _produktivdateien():
    for pfad in WURZEL.rglob("*.py"):
        if pfad in AUSGENOMMENE_DATEIEN:
            continue
        if any(teil in AUSGENOMMENE_ORDNER for teil in pfad.relative_to(WURZEL).parts):
            continue
        yield pfad


def test_kein_produktivmodul_baut_den_db_namen_selbst_zusammen():
    verdaechtig = []
    for datei in sorted(_produktivdateien()):
        for zeile_nr, zeile in enumerate(
            datei.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if TREFFER.search(zeile) and not UNBEDENKLICH.search(zeile):
                verdaechtig.append(
                    f"{datei.relative_to(WURZEL)}:{zeile_nr}: {zeile.strip()}")
    assert not verdaechtig, (
        "Produktivcode baut den DB-Namen selbst zusammen statt haken.ort zu "
        "fragen -- eine Umbenennung der Datei macht eine solche Pruefung "
        "still falsch statt rot:\n" + "\n".join(verdaechtig)
    )
