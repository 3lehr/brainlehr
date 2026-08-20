#!/usr/bin/env python3
"""Die oeffentliche Ausgabe entsteht per Skript, nicht von Hand.

BETREIBERFRAGE 2026-08-20: "die ganzen checks werden per ki gemacht? mit
welcher sonntet? haiku? koennnen wir brainlehr fuer die zukunft so anlegen
das dies per script geht? das war sowieso einmal im plan gestanden, das wir
wissen auch fuer andere exportieren koennen?!"

ANTWORT AUF DEN ERSTEN TEIL: Kein Modell im Spiel. pflege/export_offen.py,
tools/privacy_check.py und tool/aussenabgleich.py sind rein deterministisch
-- SQL, Regex, Dateivergleich. Was ein Modell gemacht hat, waren die
BEURTEILUNGEN (welcher Eintrag beantwortet welche Frage), nicht die
Pruefungen.

ANTWORT AUF DEN ZWEITEN TEIL, und dieses Modul ist sie: Bis heute fehlte
genau ein Stueck -- die AUSWAHL. Der Auszug (Daten) hatte ein Werkzeug, die
Pruefung hatte eins, der Abgleich hatte eins. Welche CODE-Dateien nach
aussen gehoeren, wurde von Hand entschieden; deshalb standen dort 25 statt
438.

DIE AUSWAHLREGEL, gemessen statt gesetzt: Eine Datei geht nach aussen, wenn
der Privacy-Check des Exports sie nicht beanstandet. Kein zweiter Massstab,
keine gepflegte Positivliste -- eine Handliste kennt nur, woran ihr Autor
beim Schreiben dachte (L-0ca81c).

ROT VOR GRUEN: Jeder Fall faellt gegen den Stand davor mit
ModuleNotFoundError -- tool/oeffentliche_ausgabe.py existiert dort nicht.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "tool")]

import pytest  # noqa: E402

import oeffentliche_ausgabe as oa  # noqa: E402


def test_saubere_datei_wird_gewaehlt(tmp_path):
    p = tmp_path / "rein.py"
    p.write_text("# nur Fachtext, keine Pfade, keine Kennungen\nX = 1\n")
    assert oa.beanstandung(p, freigegeben=set()) is None


def test_heimatpfad_wird_abgelehnt(tmp_path):
    p = tmp_path / "pfad.py"
    p.write_text('ZIEL = "/Users/jemand/.claude/x"\n')
    assert oa.beanstandung(p, freigegeben=set()) == "absolute-path"


def test_kennung_mit_freigabe_geht_durch(tmp_path):
    """Der Kern der Entschaerfung: Eine Lehrenkennung ist ein VERWEIS auf
    eine mitgelieferte Lehre, kein privates Artefakt."""
    p = tmp_path / "mit.py"
    p.write_text("# siehe L-abc123 -- deshalb steht die Pruefung hier\n")
    assert oa.beanstandung(p, freigegeben={"L-abc123"}) is None


def test_kennung_ohne_freigabe_verlaesst_das_haus_nicht(tmp_path):
    """Eine Kennung ohne mitgelieferte Lehre zeigt ins Leere -- und verraet
    allein durch ihr Vorhandensein, dass es dort etwas gibt.

    GEAENDERT 2026-08-20: Diese Zeile pruefte bis dahin, dass die DATEI
    abgelehnt wird. Das war zu grob -- 139 Dateien fielen an einzelnen
    Kennungen in Kommentaren, darunter kern/speicher.py an genau einer. Die
    Schutzwirkung ist dieselbe (die Kennung verlaesst das Haus nicht), der
    Preis ist ein Bruchteil. Was die Zeile SICHERSTELLT, hat sich nicht
    geaendert; wo sie es sicherstellt, schon."""
    p = tmp_path / "ohne.py"
    p.write_text("# siehe L-999999\n")
    assert oa.beanstandung(p, freigegeben={"L-abc123"}) is None
    raus = oa._kennungen_neutralisieren(p.read_text(), {"L-abc123"})
    assert "L-999999" not in raus


def test_datenbank_wird_nie_gewaehlt(tmp_path):
    p = tmp_path / "brainlehr.db"
    p.write_bytes(b"SQLite format 3\x00")
    assert oa.beanstandung(p, freigegeben=set()) == "forbidden-file"


def test_auswahl_zaehlt_beide_seiten(tmp_path):
    """Die Ausgabe nennt gewaehlt UND abgelehnt mit Grund. Eine Auswahl, die
    nur das Genommene zeigt, verschweigt ihren eigenen Massstab."""
    (tmp_path / "gut.py").write_text("X = 1\n")
    (tmp_path / "schlecht.py").write_text('P = "/Volumes/daten/x"\n')
    erg = oa.waehle([tmp_path / "gut.py", tmp_path / "schlecht.py"],
                    wurzel=tmp_path, freigegeben=set())
    assert [p.name for p in erg["gewaehlt"]] == ["gut.py"]
    assert erg["abgelehnt"] == {"schlecht.py": "absolute-path"}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


def test_fehlendes_modul_zieht_seinen_nutzer_mit_raus(tmp_path):
    """DER BEFUND VOM 2026-08-20, im echten Export sichtbar geworden:
    438 Dateien waren einzeln sauber -- und die kopierten Tests brachen mit
    79 Sammelfehlern ab, weil sie Module importieren, die die Auswahl
    abgelehnt hatte. Jede Datei fuer sich korrekt, kaputt ist ihre Umgebung.
    Dieselbe Klasse wie beim Klon am selben Tag.

    Regel: Ein Modul, das nicht mitkommt, nimmt jeden mit, der es braucht."""
    (tmp_path / "nutzt.py").write_text("import geheim\nX = 1\n")
    (tmp_path / "geheim.py").write_text('P = "/Users/jemand/x"\n')  # faellt durch
    erg = oa.waehle([tmp_path / "nutzt.py", tmp_path / "geheim.py"],
                    wurzel=tmp_path, freigegeben=set())
    lauffaehig = oa.lauffaehig_machen(erg, wurzel=tmp_path)
    assert [p.name for p in lauffaehig["gewaehlt"]] == []
    assert lauffaehig["abgelehnt"]["nutzt.py"].startswith("import-fehlt")


def test_sauberes_modul_bleibt_drin(tmp_path):
    """NEGATIVFALL: Ist das importierte Modul selbst sauber, bleiben BEIDE.
    Ohne diese Zeile waere aus der Regel ein Kahlschlag geworden."""
    (tmp_path / "nutzt.py").write_text("import hilfe\nX = 1\n")
    (tmp_path / "hilfe.py").write_text("Y = 2\n")
    erg = oa.waehle([tmp_path / "nutzt.py", tmp_path / "hilfe.py"],
                    wurzel=tmp_path, freigegeben=set())
    lauffaehig = oa.lauffaehig_machen(erg, wurzel=tmp_path)
    assert sorted(p.name for p in lauffaehig["gewaehlt"]) == ["hilfe.py", "nutzt.py"]


def test_standardbibliothek_ist_kein_fehlendes_modul(tmp_path):
    """`import json` darf nichts ausloesen -- sonst faellt alles heraus."""
    (tmp_path / "nutzt.py").write_text("import json\nimport pathlib\nX = 1\n")
    erg = oa.waehle([tmp_path / "nutzt.py"], wurzel=tmp_path, freigegeben=set())
    lauffaehig = oa.lauffaehig_machen(erg, wurzel=tmp_path)
    assert [p.name for p in lauffaehig["gewaehlt"]] == ["nutzt.py"]


def test_kette_wird_bis_zum_ende_verfolgt(tmp_path):
    """A braucht B, B braucht C, C faellt durch -- dann fallen alle drei.
    Eine Pruefung, die nur eine Ebene tief geht, laesst A stehen und der
    Export bricht beim zweiten Import."""
    (tmp_path / "a.py").write_text("import b\n")
    (tmp_path / "b.py").write_text("import c\n")
    (tmp_path / "c.py").write_text('P = "/Volumes/platte/x"\n')
    erg = oa.waehle([tmp_path / "a.py", tmp_path / "b.py", tmp_path / "c.py"],
                    wurzel=tmp_path, freigegeben=set())
    lauffaehig = oa.lauffaehig_machen(erg, wurzel=tmp_path)
    assert [p.name for p in lauffaehig["gewaehlt"]] == []


def test_verweis_auf_nicht_geliefertes_wird_beim_kopieren_neutralisiert(tmp_path):
    """Ein Verweis auf eine nicht mitgelieferte Lehre ist kein Grund, die
    DATEI wegzulassen -- er ist ein Grund, den VERWEIS zu ersetzen.

    Gemessen am 2026-08-20: 139 von 731 Dateien fielen allein daran, darunter
    kern/speicher.py wegen EINER Kennung in einem Kommentar. Die Datei
    wegzulassen kostet den Leser das ganze Modul; den Zeiger zu ersetzen
    kostet ihn einen Satz. Dieselbe Entscheidung wie im Auszug
    (pflege/export_offen.verweise_entschaerfen), hier fuer Quelltext."""
    q = tmp_path / "q"; z = tmp_path / "z"; q.mkdir(); z.mkdir()
    (q / "m.py").write_text("# dieselbe Klasse wie L-a69129, siehe L-abc123\nX = 1\n")
    oa.uebernehmen([q / "m.py"], repo=q, ziel=z, freigegeben={"L-abc123"})
    raus = (z / "m.py").read_text()
    assert "L-a69129" not in raus
    assert "L-abc123" in raus, "eine MITGELIEFERTE Lehre bleibt stehen"
    assert "X = 1" in raus, "der Code selbst wird nicht angefasst"


def test_kennung_ist_kein_ablehnungsgrund_mehr(tmp_path):
    """Gegenprobe zur vorigen Zeile: wer den Verweis beim Kopieren repariert,
    darf die Datei nicht trotzdem vorher aussortieren."""
    (tmp_path / "m.py").write_text("# siehe L-999999\n")
    assert oa.beanstandung(tmp_path / "m.py", {"L-abc123"}) is None


def test_modul_ausserhalb_der_quellordner_gilt_als_fehlend(tmp_path):
    """Ein Import auf ein Modul, das die Auswahl GAR NICHT KENNT, muss die
    Datei ebenso herausnehmen wie ein abgelehntes.

    DER BEFUND (2026-08-20): lauffaehig_machen bildete die Menge bekannter
    Modulnamen aus gewaehlten PLUS abgelehnten Dateien -- also aus den
    Kandidaten. Ein Modul in einem Ordner, der nicht in QUELLORDNER steht,
    kam in keiner der beiden Mengen vor und galt damit als Fremdpaket wie
    `json`. Der Import blieb stehen, die Datei wanderte in den Export, und
    dort brach sie mit ModuleNotFoundError ab: 12 Testdateien scheiterten an
    Modulen aus `messungen/`, das schlicht in keiner Liste stand.

    Die Luecke ist gefaehrlicher als eine falsche Ablehnung, weil sie in die
    FALSCHE Richtung irrt: Sie laesst durch statt zu sperren, und der Fehler
    zeigt sich erst beim Empfaenger."""
    (tmp_path / "nutzt.py").write_text("import fremdmodul\n")
    (tmp_path / "woanders").mkdir()
    (tmp_path / "woanders" / "fremdmodul.py").write_text("X = 1\n")
    erg = oa.waehle([tmp_path / "nutzt.py"], wurzel=tmp_path, freigegeben=set())
    lauffaehig = oa.lauffaehig_machen(erg, wurzel=tmp_path)
    assert [p.name for p in lauffaehig["gewaehlt"]] == []
    assert lauffaehig["abgelehnt"]["nutzt.py"] == "import-fehlt:fremdmodul"
