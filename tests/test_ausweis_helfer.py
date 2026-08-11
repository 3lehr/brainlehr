"""Der Bruecke zwischen Ausweis-App und kern/ausweis.py auf die Finger sehen.

WAS DIESE TESTS ABDECKEN UND WAS NICHT -- ausdruecklich, damit niemand aus
gruenen Tests auf eine geprueffte App schliesst:

  ABGEDECKT   pflege/ausweis_helfer.py: Ausgabeform (JSON statt Fliesstext),
              Geheimnis ausschliesslich ueber STDIN, Fehler im Wortlaut des
              Moduls, Rechtepruefung greift.
  NICHT       Die Dialoge von Ausweisstelle.app. Sie sind AppleScript und nur
              von Hand zu bedienen. `osacompile` bestaetigt die Syntax, mehr
              nicht -- wer die App aendert, prueft sie am Bildschirm.

Der Erfolgsfall laesst sich hier nur pruefen, weil jeder Test seine EIGENE
Ausweisdatei bekommt (BRAINLEHR_AUSWEISE): In eine leere Datei darf der erste
Ausweis ohne Ausstellerrecht -- das ist der Gruendungsakt. Gegen den echten
Bestand ginge das nicht, und genau das ist die Schranke, die am 2026-08-11
gegen den Assistenten selbst gewirkt hat (Knoten 8c81d489).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent

HELFER = _w / "pflege" / "ausweis_helfer.py"


def _ruf(*argumente: str, geheimnis: str | None = None,
         datei: Path | None = None) -> tuple[dict, int]:
    """Ruft den Helfer wie die App es tut: Geheimnis auf STDIN, nie in argv."""
    umgebung = {"PATH": "/usr/bin:/bin", "HOME": str(datei.parent) if datei else "/tmp"}
    if datei is not None:
        umgebung["BRAINLEHR_AUSWEISE"] = str(datei)
    lauf = subprocess.run(
        [sys.executable, str(HELFER), *argumente],
        input=(geheimnis or ""), capture_output=True, text=True,
        timeout=60, env=umgebung, cwd=str(_w),
    )
    try:
        return json.loads(lauf.stdout or "{}"), lauf.returncode
    except json.JSONDecodeError:
        pytest.fail(f"keine JSON-Ausgabe: {lauf.stdout!r} / {lauf.stderr!r}")


@pytest.fixture()
def leere_datei(tmp_path) -> Path:
    """Eigene Ausweisdatei -- der echte Bestand wird nie angefasst."""
    return tmp_path / "ausweise.json"


def test_rollen_kommen_als_json(leere_datei):
    """Die App darf nicht auf Fliesstext angewiesen sein."""
    erg, rc = _ruf("rollen", datei=leere_datei)
    assert rc == 0
    assert "ausweis:ausstellen" in erg["rollen"]["meldeamt"]
    assert erg["rollen"]["betreiber"] == ["*"]


def test_gruendungsakt_legt_den_ersten_an(leere_datei):
    """In eine leere Datei darf der erste Ausweis ohne Ausstellerrecht."""
    erg, rc = _ruf("anlegen", "chef", "mensch", "betreiber", datei=leere_datei)
    assert rc == 0, erg
    assert erg["geheimnis"], "kein Geheimnis zurueckgegeben"
    assert len(erg["geheimnis"]) >= 20, "Geheimnis verdaechtig kurz"
    assert erg["art"] == "mensch"


def test_zweiter_ausweis_braucht_ein_recht(leere_datei):
    """NEGATIVFALL, und er ist der Kern der ganzen Anlage: Ist der Bestand
    nicht leer, ist es kein Gruendungsakt mehr."""
    _ruf("anlegen", "chef", "mensch", "betreiber", datei=leere_datei)
    erg, rc = _ruf("anlegen", "eindringling", "maschine", "betreiber",
                   datei=leere_datei)
    assert rc != 0
    assert "fehler" in erg
    assert "ausweis:ausstellen" in erg["fehler"], \
        "der Grund muss im Wortlaut durchgereicht werden, nicht verallgemeinert"


def test_mit_recht_geht_es(leere_datei):
    """GEGENPROBE zum Negativfall -- sonst prueft der nur, dass gar nichts geht."""
    chef, _ = _ruf("anlegen", "chef", "mensch", "betreiber", datei=leere_datei)
    erg, rc = _ruf("anlegen", "helferlein", "maschine", "schreiber",
                   geheimnis=chef["geheimnis"], datei=leere_datei)
    assert rc == 0, erg
    assert erg["rollen"] == ["schreiber"]


def test_falsches_geheimnis_gibt_nicht_mehr_rechte_als_keines(leere_datei):
    """Ein falsches Geheimnis darf nie mehr ergeben als gar keines -- die
    Zusicherung steht so im Modul und wird hier am Helfer nachgeprueft."""
    _ruf("anlegen", "chef", "mensch", "betreiber", datei=leere_datei)
    erg, rc = _ruf("anlegen", "x", "maschine", "leser",
                   geheimnis="voellig-erfunden", datei=leere_datei)
    assert rc != 0 and "fehler" in erg


def test_einladung_traegt_dauer_und_verantwortlichen(leere_datei):
    chef, _ = _ruf("anlegen", "chef", "mensch", "betreiber", datei=leere_datei)
    erg, rc = _ruf("einladen", "gast-1", "chef", "leser",
                   geheimnis=chef["geheimnis"], datei=leere_datei)
    assert rc == 0, erg
    assert erg["pin"] and erg["fuer"] == "chef"
    assert isinstance(erg["gueltig_minuten"], int) and erg["gueltig_minuten"] > 0


def test_unvollstaendige_eingabe_meldet_statt_abzustuerzen(leere_datei):
    """Die App darf einen Traceback nie zu sehen bekommen -- sie zeigt an, was
    hier herauskommt."""
    erg, rc = _ruf("anlegen", "nur-ein-name", datei=leere_datei)
    assert rc == 2 and "fehler" in erg


def test_unbekannter_befehl_meldet_sauber(leere_datei):
    erg, rc = _ruf("tanzen", datei=leere_datei)
    assert rc == 2 and "unbekannt" in erg["fehler"].lower()


# --- Der Weg, den die App wirklich nimmt ----------------------------------

STARTER = _w / "pflege" / "ausweis_start.sh"


def _ruf_wie_die_app(*argumente: str, geheimnis: str = "",
                     datei: Path) -> tuple[dict, int]:
    """Wie `do shell script`: leere Umgebung, PATH nur /usr/bin:/bin.

    Genau das unterscheidet diesen Test von den obigen -- die rufen den Helfer
    mit sys.executable auf, also mit dem Projekt-Python."""
    lauf = subprocess.run(
        [str(STARTER), *argumente], input=geheimnis,
        capture_output=True, text=True, timeout=60,
        env={"PATH": "/usr/bin:/bin", "HOME": str(datei.parent),
             "BRAINLEHR_AUSWEISE": str(datei)},
    )
    try:
        return json.loads(lauf.stdout or "{}"), lauf.returncode
    except json.JSONDecodeError:
        pytest.fail(f"keine JSON-Ausgabe: {lauf.stdout!r} / {lauf.stderr!r}")


def test_app_weg_funktioniert_mit_eingeschraenktem_pfad(leere_datei):
    """ROT VOR GRUEN, und dieser Test ist der Grund fuer ausweis_start.sh.

    Gemessen 2026-08-11: Unter /usr/bin/python3 (Apple, 3.9.6) fehlt
    hashlib.scrypt -- kern/ausweis.py stuerzt mit AttributeError ab, BEVOR
    eine Zeile Ausgabe entsteht. Alle acht Tests darueber waren gruen, weil
    sie unter sys.executable (3.14) liefen. Die App lief aber unter dem
    eingeschraenkten PATH von `do shell script`, wo /usr/bin/python3 der
    einzige Treffer ist. Gruen im Kopflauf, tot im Feld -- genau die
    Ebenenverwechslung, gegen die die Belegpflicht steht."""
    erg, rc = _ruf_wie_die_app("anlegen", "chef", "mensch", "betreiber",
                               datei=leere_datei)
    assert rc == 0, erg
    assert len(erg.get("geheimnis", "")) >= 20


def test_app_weg_reicht_das_geheimnis_durch(leere_datei):
    """Das Startskript darf STDIN nicht verschlucken -- ohne durchgereichtes
    Geheimnis waere jede Ausstellung eine Ablehnung."""
    chef, _ = _ruf_wie_die_app("anlegen", "chef", "mensch", "betreiber",
                               datei=leere_datei)
    erg, rc = _ruf_wie_die_app("einladen", "gast", "chef", "leser",
                               geheimnis=chef["geheimnis"], datei=leere_datei)
    assert rc == 0, erg
    assert erg["pin"]


def test_app_weg_meldet_fehler_als_json(leere_datei):
    """Auch im Fehlerfall JSON -- die App zeigt an, was hier herauskommt, und
    darf nie einen Traceback oder eine leere Ausgabe zu sehen bekommen."""
    _ruf_wie_die_app("anlegen", "chef", "mensch", "betreiber", datei=leere_datei)
    erg, rc = _ruf_wie_die_app("anlegen", "zweiter", "maschine", "leser",
                               datei=leere_datei)
    assert rc != 0 and "fehler" in erg
