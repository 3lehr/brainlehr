"""Rot-vor-gruen fuer B2: das Uebernahmeregister (kern/uebernahmeregister.py).

ANLASS: Rang-1-Weisung `73f8a1c0` -- jede Regel, Schwelle, Formel oder
Verhaltensweise, die aus einem Bestand in einen Neubau wandert, traegt
`status: unbelegt`, bis im Neubau ein eigener Test existiert, der gegen eine
BEWUSST FALSCHE Fassung rot war. 4 575 gruene Tests im Bestand belegen nur,
dass der Code tut, was jemand aufgeschrieben hat.

WARUM DAS EIN MECHANISMUS SEIN MUSS und keine Selbstverpflichtung: Nach dem
Schnitt (B3) liegt der geerbte Code physisch da und sieht dadurch
vertrauenswuerdig aus. Das Register ist dann das einzige, was Blaupause von
Werkbank trennt -- und eine Selbstverpflichtung faellt beim ersten Zeitdruck.

WARUM HIER UND NICHT IM DOMAENEN-REPO (ADR-014): Ob die geerbten Regeln einer
Domaene als belegt gelten, darf diese Domaene nicht ueber sich selbst
entscheiden. Der MECHANISMUS liegt deshalb zentral, die MARKIERUNGEN liegen im
Domaenen-Repo und reisen mit ihm.

VORHER GESUCHT, nicht angenommen (2026-08-16): `kern/herkunft_belegung.py` und
`kern/herkunft_normentscheider.py` betreffen die Herkunftsfelder des
WISSENSBESTANDS, nicht die Uebernahme aus einem Bestandsrepo.
`symbolindex.py unbelegt` meldet keine Treffer, `grep` findet in
fahrtenbuch_nativ -- dem Repo, fuer das `73f8a1c0` zuerst galt -- nur den
PLANTEXT (docs/PLAN_NEUBAU_NATIV_2026-08-16.md §8), kein Verzeichnis
`ios/Tests/Vektoren/` und kein zaehlendes Skript. Es gab nichts zu erben.

ROT-PROBE: siehe runs/rotprobe_b2_2026-08-16.txt.
"""

import json

import pytest

from kern import uebernahmeregister as reg


def _vektor(**zusatz):
    basis = {
        "name": "euer_zuordnung_bewirtung",
        "herkunft": "legacy",
        "status": "unbelegt",
    }
    basis.update(zusatz)
    return basis


# --- Pflichtfelder, ohne Vorgabewert ---------------------------------------

def test_vollstaendiger_vektor_wird_angenommen():
    assert reg.pruefe(_vektor()) is None


@pytest.mark.parametrize("fehlend", ["herkunft", "status"])
def test_fehlendes_pflichtfeld_wird_abgelehnt(fehlend):
    """Kein Vorgabewert: ein fehlendes Feld ist eine Ablehnung, keine stille
    Annahme. Genau hier faellt die Regel sonst um -- ein Vorgabewert
    `unbelegt` waere bequem und wuerde die Frage nie stellen."""
    vektor = _vektor()
    del vektor[fehlend]

    grund = reg.pruefe(vektor)

    assert grund is not None
    assert fehlend in grund


@pytest.mark.parametrize(
    "feld,wert", [("herkunft", "irgendwoher"), ("status", "geprueft"), ("status", "")]
)
def test_unbekannter_wert_wird_abgelehnt(feld, wert):
    grund = reg.pruefe(_vektor(**{feld: wert}))

    assert grund is not None
    assert feld in grund


# --- Der Kern: 'belegt' ist eine Behauptung und braucht einen Beleg --------

def test_belegt_ohne_beleg_wird_abgelehnt():
    """Der teuerste Fall. Ohne diese Pruefung ist `status: belegt` ein Wort,
    das jeder hinschreiben kann -- und die ganze Weisung waere Zierrat."""
    grund = reg.pruefe(_vektor(status="belegt"))

    assert grund is not None
    assert "Beleg" in grund


@pytest.mark.parametrize("fehlend", ["test", "rotprobe"])
def test_belegt_mit_halbem_beleg_wird_abgelehnt(fehlend):
    """Ein Test allein belegt nichts -- er koennte von Anfang an gruen gewesen
    sein. Die Rot-Probe ist der Teil, der die Wirksamkeit zeigt."""
    beleg = {"test": "tests/test_euer.py::test_bewirtung", "rotprobe": "runs/rot.txt"}
    del beleg[fehlend]

    grund = reg.pruefe(_vektor(status="belegt", beleg=beleg))

    assert grund is not None
    assert fehlend in grund


def test_belegt_mit_vollstaendigem_beleg_geht_durch():
    vektor = _vektor(
        status="belegt",
        beleg={"test": "tests/test_euer.py::test_bewirtung", "rotprobe": "runs/rot.txt"},
    )

    assert reg.pruefe(vektor) is None


def test_unbelegt_mit_beleg_ist_ein_widerspruch():
    """Gegenrichtung: wer einen Beleg mitliefert, aber `unbelegt` stehen laesst,
    hat entweder vergessen umzustellen oder den Beleg erfunden. Beides gehoert
    gesagt, statt die guenstigere Lesart zu waehlen."""
    grund = reg.pruefe(
        _vektor(beleg={"test": "tests/test_euer.py::test_bewirtung", "rotprobe": "runs/rot.txt"})
    )

    assert grund is not None


# --- Verzeichnis und Zaehlung ---------------------------------------------

def test_verzeichnis_meldet_die_datei_beim_namen(tmp_path):
    (tmp_path / "gut.json").write_text(json.dumps(_vektor()), encoding="utf-8")
    (tmp_path / "kaputt.json").write_text(json.dumps({"name": "x"}), encoding="utf-8")

    befunde = reg.pruefe_verzeichnis(tmp_path)

    assert len(befunde) == 1
    assert "kaputt.json" in befunde[0]


def test_beschaedigte_datei_ist_ein_befund_kein_absturz(tmp_path):
    (tmp_path / "kaputt.json").write_text("{kein json", encoding="utf-8")

    befunde = reg.pruefe_verzeichnis(tmp_path)

    assert len(befunde) == 1
    assert "kaputt.json" in befunde[0]


def test_zaehlung_trennt_unbelegt_von_belegt(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps(_vektor()), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(_vektor(name="b")), encoding="utf-8")
    (tmp_path / "c.json").write_text(
        json.dumps(
            _vektor(
                name="c",
                herkunft="neu",
                status="belegt",
                beleg={"test": "t::x", "rotprobe": "runs/rot.txt"},
            )
        ),
        encoding="utf-8",
    )

    zahlen = reg.zaehle(tmp_path)

    assert zahlen == {
        "gesamt": 3, "unbelegt": 2, "belegt": 1, "legacy": 2, "neu": 1, "beanstandet": 0,
    }


def test_beanstandeter_vektor_zaehlt_nicht_als_belegt(tmp_path):
    """Die Zahl geht nach STAND.md. Ein Vektor, der `belegt` BEHAUPTET und die
    Pruefung nicht besteht, darf dort nicht als belegt erscheinen -- sonst
    macht die Kennzahl die Schuld kleiner, und das ist die Richtung, gegen die
    der ganze Mechanismus gebaut ist. Gefunden an der AUSGABE des Werkzeugs,
    nicht am Rueckgabewert."""
    (tmp_path / "luegt.json").write_text(
        json.dumps(_vektor(status="belegt")), encoding="utf-8"
    )

    zahlen = reg.zaehle(tmp_path)

    assert zahlen["belegt"] == 0
    assert zahlen["beanstandet"] == 1
    assert zahlen["gesamt"] == 1


def test_leeres_verzeichnis_ist_kein_fehler(tmp_path):
    """Vor der ersten Uebernahme ist das Register leer -- das ist der
    Normalzustand, nicht ein Mangel."""
    assert reg.pruefe_verzeichnis(tmp_path) == []
    assert reg.zaehle(tmp_path)["gesamt"] == 0
