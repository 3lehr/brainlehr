"""Rot-vor-gruen fuer B1: das Manifest traegt jetzt DREI Teile, nicht einen.

ANLASS: ADR-013 teilt eine Domaene in Wissen, Dienst und Oberflaeche.
Gemessen am 2026-08-16 deckte `pakete/steuer.domaene.json` mit seinen sechs
Feldern nur *Wissen* ab -- fuer *Dienst* und *Oberflaeche* gab es keinen Platz
im Format. ADR-013 sagt zugleich, warum das kein Nachzuegler sein darf: ein
Format nachtraeglich um ein PFLICHTFELD zu erweitern macht jedes bereits
verteilte Repo ungueltig. Also stehen die Felder VOR dem ersten fremden Import.

ZWEI SCHRANKEN, und beide sind Reihenfolge-Argumente, keine Mengenargumente:

1. KEIN ABSOLUTER PFAD im Dienst-Teil (ADR-023 §3). Die beiden vorhandenen
   Startbeschreibungen im Haus unterscheiden sich genau hier: `de.brainlehr.dienst`
   benutzt den Platzhalter `__REPO_PFAD__`, die openlehr-Legacy-Fassung verdrahtet
   `/Volumes/daten/Begod2026/openlehr` fest. Die erste ueberlebt einen Import auf
   einen fremden Rechner, die zweite nicht.

2. KEINE BAUFORM in der Oberflaechen-Beschreibung (ADR-024). Die Beschreibung
   sagt WAS, nie WIE. Der Betreiber hat zugesagt bekommen, dass eine spaetere
   Weboberflaeche ein weiterer SCHRITT bleibt und kein zweiter Bau -- das gilt nur,
   solange kein Feld ein Bedienelement benennt. Die Gefahr ist die Reihenfolge:
   solange nur EIN Zeichner existiert (nativ, Swift), zieht nichts in die andere
   Richtung, und die Beschreibung nimmt zwangslaeufig seine Form an.

ROT-PROBE, gefahren am 2026-08-16 VOR der Umsetzung: 11 failed, 2 passed.
`pruefe()` kannte weder `dienst` noch `oberflaeche` und nahm jedes Paket an --
auch das mit `/Volumes/...` im Startbefehl und `NSTableView` im Bildschirm. Die
zwei gruenen waren die Positivkontrollen, und sie waren aus genau demselben
Grund gruen: es wurde nichts geprueft. Nachweis: runs/rotprobe_b1_2026-08-16.txt.
"""

import pytest

from kern.domaene import pruefe


def _paket(**zusatz):
    """Ein Paket, das ohne den jeweiligen Zusatz durchlaeuft -- damit ein
    Fehlschlag eindeutig am geprueften Feld liegt und nicht am Rest."""
    basis = {
        "domaene": "probe",
        "bezeichnung": "Probe",
        "herkunft": "test",
        "stand": "2026-08-16T13:00:00+0200",
        "quellen": {"q1": {"bezeichnung": "Q", "hinweistext": "Belegtext"}},
        "regeln": [{"id": "r1", "ziel_id": "q1", "fundstelle": "Belegtext"}],
        "contract_version": 1,
        "dienst": {
            "start": ["__REPO_PFAD__/.venv/bin/python", "-m", "dienst"],
            "horcht_auf": 8811,
            "lebenszeichen": "/gesundheit",
        },
        "oberflaeche": {"fassung": 1, "bildschirme": []},
    }
    basis.update(zusatz)
    return basis


def test_vollstaendiges_paket_wird_angenommen():
    """Gegenprobe in die andere Richtung: die neuen Schranken duerfen ein
    korrektes Paket nicht abweisen, sonst misst der Rest nichts."""
    ergebnis = pruefe(_paket())
    assert ergebnis["angenommen"] is True, ergebnis["grund"]


@pytest.mark.parametrize("fehlend", ["dienst", "oberflaeche"])
def test_paket_ohne_neuen_pflichtteil_wird_abgewiesen(fehlend):
    paket = _paket()
    del paket[fehlend]

    ergebnis = pruefe(paket)

    assert ergebnis["angenommen"] is False
    assert fehlend in ergebnis["grund"]


@pytest.mark.parametrize(
    "start",
    [
        ["/Volumes/daten/Begod2026/openlehr/.venv/bin/python", "-m", "dienst"],
        ["/Users/lehrmacbook/.venv/bin/python"],
        ["~/openlehr/.venv/bin/python"],
    ],
)
def test_absoluter_pfad_im_dienst_wird_abgewiesen(start):
    """Genau die drei Formen, die in der Schnittgrenzen-Messung vom 2026-08-14
    unter apps/openlehr gefunden wurden (24 Dateien)."""
    ergebnis = pruefe(_paket(dienst={"start": start, "horcht_auf": 8811, "lebenszeichen": "/gesundheit"}))

    assert ergebnis["angenommen"] is False
    assert "Pfad" in ergebnis["grund"]


@pytest.mark.parametrize(
    "bildschirm",
    [
        {"art": "NSTableView", "titel": "Belege"},
        {"art": "liste", "darstellung": "sidebar"},
        {"art": "liste", "verhalten": "modal"},
    ],
)
def test_bauform_in_der_oberflaeche_wird_abgewiesen(bildschirm):
    ergebnis = pruefe(_paket(oberflaeche={"fassung": 1, "bildschirme": [bildschirm]}))

    assert ergebnis["angenommen"] is False
    assert "Bauform" in ergebnis["grund"]


@pytest.mark.parametrize(
    "bildschirm",
    [
        {"art": "liste", "titel": "Belege", "farbe": "#2b7de9"},
        {"art": "liste", "breite_px": 320},
    ],
)
def test_aussehen_in_der_oberflaeche_wird_abgewiesen(bildschirm):
    """Getrennt von der Bauform, weil es ein anderer Befund ist und der Mensch
    einen anderen Satz braucht: eine Bauform ist die falsche EBENE, ein
    Farbwert die falsche ZUSTAENDIGKEIT. Der erste Anlauf warf beides in einen
    Topf -- der Prueferspruch war praeziser als der Test."""
    ergebnis = pruefe(_paket(oberflaeche={"fassung": 1, "bildschirme": [bildschirm]}))

    assert ergebnis["angenommen"] is False
    assert "Aussehen" in ergebnis["grund"]


def test_beschreibung_ohne_bauform_bleibt_erlaubt():
    """Die Gegenrichtung, ohne die die Schranke nur alles ablehnen koennte:
    was WAS sagt statt WIE, laeuft durch -- auch das Wort 'tabelle', denn es
    benennt eine Rolle (ADR-010 Bausteintyp), keine Bauform."""
    bildschirm = {
        "art": "tabelle",
        "titel": "Belege",
        "felder": [{"name": "betrag", "pflicht": True}, {"name": "datum"}],
    }

    ergebnis = pruefe(_paket(oberflaeche={"fassung": 1, "bildschirme": [bildschirm]}))

    assert ergebnis["angenommen"] is True, ergebnis["grund"]


def test_grund_nennt_das_wort_das_gestolpert_ist():
    """Ein Grund ohne das konkrete Wort zwingt den Menschen zum Suchen --
    dieselbe Regel wie ueberall im Haus: sag, was zu tun ist."""
    ergebnis = pruefe(
        _paket(oberflaeche={"fassung": 1, "bildschirme": [{"art": "liste", "x": "popover"}]})
    )

    assert "popover" in ergebnis["grund"]
