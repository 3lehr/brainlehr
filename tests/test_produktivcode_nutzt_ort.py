"""Produktivcode muss seinen DB-Pfad vom Aufloeser (haken/ort.py) beziehen.

BEFUND (Auftrag 2026-08-12, Knoten 3bd128cc): Beim Umzug von knowledge.db auf
brainlehr.db bauten sechs Produktivdateien den Pfad SELBST zusammen statt
haken.ort zu fragen -- teils mit eigener Auswertung von BEGOD_KNOWLEDGE_DB,
teils als nackter String. kern/normbezug.py::belegt() meldete dadurch JEDES
Normzitat als unbelegt, ohne die Datenbank je zu oeffnen: der alte, selbst
gebaute Pfad existierte nach der Umbenennung nicht mehr.

Dieser Test faengt die Fehlerklasse fuer den Produktivbaum (Pendant zu
tests/test_testumgebung_nutzt_ort.py, das dasselbe fuer tests/ prueft).

ERWEITERT (Auftrag 2026-08-12, Naht kern/teilung_s12.py): die urspruengliche
Fassung verbot NUR den alten Namen 'knowledge.db' als Text -- eine Wache
gegen den Fehler von GESTERN. kern/teilung_s12.py verdrahtete den AKTUELLEN
Namen 'brainlehr.db' fest und kam trotzdem durch. TREFFER faengt jetzt JEDEN
hartcodierten .db-Dateinamen, nicht nur den alten.

RATSCHE STATT VERBOT (dieselbe Bauform wie tests/naht_ratsche.py /
naht_basis.json, aus demselben Grund): die breitere Suche foerderte beim
Durchsehen des vollen Baums (ausserhalb migrationen/tests/__pycache__/.claude)
37 laenger bestehende Dateien zutage, die denselben Aufloeser-Bedarf wie
haken/ort.py EIGENSTAENDIG loesen -- ueberwiegend
`DB_PATH = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (... / "brainlehr.db"))`,
vereinzelt ohne die Umgebungsvariable. Ein Verbot haette alle 37 auf einen
Schlag rot gemacht, obwohl keine davon Teil dieses Auftrags ist (der ist auf
die Naht in kern/teilung_s12.py begrenzt) -- dieselbe Fehlerklasse "blockierende
Wache, die eine unerfuellbare Regel durchsetzt", die naht_ratsche.py schon
einmal umgangen hat. tests/produktivcode_basis.json haelt den Bestand fest;
er darf nur SINKEN. kern/teilung_s12.py stand dort nicht drin und ist darum
die einzige neue Datei, die dieser Test vor der Reparatur meldet.

UNBEDENKLICH ist ebenfalls erweitert: die urspruengliche Fassung erkannte nur
das woertliche Fixture-Wort 'tmp_path'. Der Baum benutzt fuer denselben Zweck
auch tmp/tmpdir/td/_td/_TMP_DIR und tempfile.mkdtemp() -- ohne die zaehlten
Dutzende echte Wegwerf-Datenbanken in Test-/Demo-Funktionen als Treffer und
waeren in die Basis gewandert, obwohl sie nie den gemeinsamen Bestand meinen.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
BASIS = WURZEL / "tests" / "produktivcode_basis.json"

# haken/ort.py traegt hartcodierte Namen BERECHTIGT: dort stehen die
# Rueckfallpfade fuer Installationen ohne gesetzte Umgebungsvariable und ohne
# migrierte Datei -- das ist der Aufloeser selbst, keine Umgehung von ihm.
#
# migrationen/ ist ausgenommen: Migrationsskripte sind Momentaufnahmen eines
# einmaligen Laufs zu einem bestimmten Datum (hier: 2026-08-08, DREI TAGE VOR
# der Umbenennung auf brainlehr.db) und laufen nicht erneut -- ein alter
# Dateiname darin ist ein historischer Fakt, kein Bug. Ausserdem GRENZEN
# dieses Auftrags: migrationen/lauf_titelverteidiger_2026-08-08.py ist fremde,
# laufende Sitzung und darf nicht angefasst werden.
AUSGENOMMENE_ORDNER = ("migrationen", "tests", "__pycache__", ".claude")
AUSGENOMMENE_DATEIEN = {WURZEL / "haken" / "ort.py"}

# Zeilen, die sich ueber ein Wegwerf-Verzeichnis (Fixture oder
# tempfile.mkdtemp()) eine EIGENE Datenbank anlegen, sind unbedenklich --
# dort ist der Name beliebig, es ist nie der gemeinsame Bestand hinter dem
# Aufloeser. Die Namen sind die im Baum tatsaechlich verwendeten
# Wegwerf-Variablen (siehe Modul-Docstring), keine erschoepfende Liste.
UNBEDENKLICH = re.compile(
    r"\btmp_path\b|\btmpdir\b|\btmp_dir\b|\btmp\b|\btd2?\b|\b_td\b|"
    r"\b_TMP_DIR\b|tempfile\.mkdtemp"
)

# Jeder hartcodierte .db-Dateiname, nicht nur der alte 'knowledge.db' --
# kern/teilung_s12.py verdrahtete den AKTUELLEN Namen 'brainlehr.db' fest und
# kam an der alten, engeren Fassung vorbei. Einfach- wie doppelt-quotiert,
# damit `WURZEL / 'brainlehr.db'` genauso faellt wie `"knowledge.db"`.
TREFFER = re.compile(r'''['"][A-Za-z0-9_.\-]*\.db['"]''')


def _produktivdateien():
    for pfad in WURZEL.rglob("*.py"):
        if pfad in AUSGENOMMENE_DATEIEN:
            continue
        if any(teil in AUSGENOMMENE_ORDNER for teil in pfad.relative_to(WURZEL).parts):
            continue
        yield pfad


def dateien_mit_hartcodiertem_db_namen() -> list[str]:
    """Produktivdateien (ohne Tests/Migrationen/Ausnahmen), die irgendwo
    einen .db-Dateinamen woertlich tragen, statt haken.ort zu fragen --
    Wegwerf-Datenbanken in Test-/Demo-Funktionen ausgenommen (UNBEDENKLICH)."""
    treffer = set()
    for datei in _produktivdateien():
        for zeile in datei.read_text(encoding="utf-8").splitlines():
            if TREFFER.search(zeile) and not UNBEDENKLICH.search(zeile):
                treffer.add(f"./{datei.relative_to(WURZEL)}")
                break
    return sorted(treffer)


def test_kein_produktivmodul_baut_den_db_namen_selbst_zusammen():
    ist = set(dateien_mit_hartcodiertem_db_namen())
    basis = set(json.loads(BASIS.read_text(encoding="utf-8"))["dauerhaft"])

    neu = sorted(ist - basis)
    assert not neu, (
        "Neue Datei(en), die den DB-Namen selbst zusammenbauen statt "
        "haken.ort zu fragen: " + ", ".join(neu) +
        " -- stattdessen haken.ort.DB (oder kern/speicher.py) verwenden. "
        "Ist der hartcodierte Name hier wirklich noetig, gehoert er mit "
        "Begruendung in tests/produktivcode_basis.json."
    )


def test_basis_bleibt_ehrlich():
    """Gegenprobe wie in test_naht_ratsche.py: Dateien, die inzwischen auf
    haken.ort umgestellt wurden, muessen aus der Basis verschwinden -- sonst
    waechst der Spielraum still mit jeder Umstellung."""
    ist = set(dateien_mit_hartcodiertem_db_namen())
    basis = set(json.loads(BASIS.read_text(encoding="utf-8"))["dauerhaft"])

    erledigt = sorted(basis - ist)
    assert not erledigt, (
        "Diese Dateien stehen noch in der Basis, tragen aber keinen "
        "hartcodierten DB-Namen mehr: " + ", ".join(erledigt) +
        " -- aus tests/produktivcode_basis.json streichen."
    )
