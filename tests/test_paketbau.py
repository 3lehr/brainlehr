"""Der Paketbau: was ins Archiv gehoert -- und vor allem, was nicht.

ROT VOR GRUEN: An 85c84fda gibt es kein pyproject.toml in der Wurzel; jeder
Test hier faellt dort auf die fehlende Datei.

DER NEGATIVTEST IST DER WICHTIGERE, und er ist keine Theorie: Der erste
Bauversuch am 2026-08-21 erzeugte ein sdist von 500 826 349 Bytes --
hatchling legt ohne ausdrueckliche Auswahl ALLES hinein, was nicht in
.gitignore steht, also brainlehr.db samt aller Sicherungen. Genau dagegen
steht `only-include` im sdist-Ziel, und genau dagegen steht dieser Test.
"""
from __future__ import annotations

import pathlib
import sys
import tarfile
import tomllib
import zipfile

import pytest

WURZEL = pathlib.Path(__file__).resolve().parent.parent
PYPROJECT = WURZEL / "pyproject.toml"

# Was niemals in ein Archiv darf. brainlehr.db traegt Daten Dritter (230 MB),
# der Rest ist Messwerk und Historie -- kein Nutzer eines Pakets braucht das.
VERBOTEN = ("brainlehr.db", "knowledge.db", "runs/", "messungen/", "spikes/",
            "backups/", "sicherungen/", "docs/", "auszug/", ".claude/",
            "korpora/", "snapshots/", "rohdaten/")

# Ohne die laeuft der Server nicht -- gemessen, nicht geraten (siehe
# runs/paketbau_2026-08-21.json).
PFLICHT = ("knowledge_mcp_server.py", "schema.sql", "herkunft_unveraenderlich.sql",
           "kern/embeddings.py", "kern/ausweis.py", "haken/ort.py")


def _konfig() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def test_lizenz_ist_agpl_und_kern_ohne_abhaengigkeiten():
    p = _konfig()["project"]
    assert "AGPL" in p["license"], "Der Kern ist AGPL -- MIT gilt nur fuer den Hermes-Adapter."
    assert p["dependencies"] == [], "Der Kern laeuft auf Stdlib + SQLite; Fremdpakete gehoeren in den Zusatz."
    zusatz = p["optional-dependencies"]
    assert zusatz, "Die drei Pakete aus requirements.txt brauchen einen ausdruecklichen Zusatz."
    alle = " ".join(x for werte in zusatz.values() for x in werte)
    for paket in ("numpy", "scikit-learn", "cryptography"):
        assert paket in alle


def test_einstiegspunkt_zeigt_auf_den_server():
    skripte = _konfig()["project"]["scripts"]
    assert skripte, "Ohne Einstiegspunkt muss ein Klient wieder einen Dateipfad eintragen."
    ziel = next(iter(skripte.values()))
    assert ziel.endswith("knowledge_mcp_server:main")


def test_dateiliste_ist_eng_und_zeigt_auf_vorhandene_dateien():
    bau = _konfig()["tool"]["hatch"]["build"]
    wheel = bau["targets"]["wheel"]["force-include"]
    sdist = bau["targets"]["sdist"]["only-include"]
    assert sorted(wheel) == sorted(sdist), "wheel und sdist muessen dieselbe Liste tragen."
    for quelle, ziel in wheel.items():
        assert (WURZEL / quelle).is_file(), f"{quelle} steht in pyproject.toml, existiert aber nicht"
        assert ziel.startswith("brainlehr_kern/")
        for schlecht in VERBOTEN:
            assert schlecht not in quelle, f"{quelle} gehoert nicht ins Paket"
    for pflicht in PFLICHT:
        assert pflicht in wheel, f"{pflicht} fehlt -- ohne sie startet der Server nicht"
    summe = sum((WURZEL / q).stat().st_size for q in wheel)
    assert summe < 2_000_000, f"{summe} Bytes Rohgroesse -- da ist etwas drin, was nicht hineingehoert"


@pytest.mark.skipif(
    __import__("importlib.util", fromlist=["util"]).find_spec("hatchling") is None,
    reason="hatchling nicht installiert -- der Archivtest braucht das Bauwerkzeug",
)
def test_archiv_enthaelt_die_kernmodule_und_keine_datenbank(tmp_path):
    from hatchling.builders.sdist import SdistBuilder
    from hatchling.builders.wheel import WheelBuilder

    namen: dict[str, list[str]] = {}
    rad = next(iter(WheelBuilder(str(WURZEL)).build(directory=str(tmp_path))))
    namen["wheel"] = zipfile.ZipFile(rad).namelist()
    quelle = next(iter(SdistBuilder(str(WURZEL)).build(directory=str(tmp_path))))
    with tarfile.open(quelle) as t:
        namen["sdist"] = t.getnames()

    for art, liste in namen.items():
        text = "\n".join(liste)
        for schlecht in VERBOTEN:
            assert schlecht not in text, f"{art}: {schlecht} liegt im Archiv"
        for pflicht in PFLICHT:
            assert any(n.endswith(pflicht) for n in liste), f"{art}: {pflicht} fehlt"
    for archiv in (rad, quelle):
        groesse = pathlib.Path(archiv).stat().st_size
        assert groesse < 1_000_000, f"{archiv}: {groesse} Bytes -- zu gross fuer den Kern"
