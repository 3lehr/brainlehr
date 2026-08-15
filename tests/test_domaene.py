"""Rot-vor-gruen fuer kern/domaene.py (PLAN_OPENLEHR_2026-08-14.md H8a).
Rot-Beleg fuer den Hauptfall steht als Kommentar bei der Funktion, die ihn
erzeugt hat -- siehe test_regel_ohne_beleg_wird_abgelehnt_mit_grund.

WIRKUNG NULL (ADR-018): die Tests ab test_gespeicherte_regel_traegt_wirkung_null
belegen die Sperre aus docs/PLAN_GESAMT_2026-08-13.md ("Wirkung Null steht,
BEVOR kern/domaene.py das erste Mal speichert"). MUTATIONSPROBE von Hand
gefahren (L-da6eb5): kern/domaene.py auf eine Kopie kopiert, in der Kopie
_INSERT_SQL['keine_norm'] durch 'norm_unbefristet' ersetzt (die Regel wuerde
sofort wirken statt Wirkung Null zu tragen), Kopie geloescht nach dem Lauf.
Ergebnis: die Schreibung schlug bereits an der DB-Schranke fehl --
    sqlite3.IntegrityError: knowledge_nodes.norm_entscheidung widerspricht
    norm_rang/gilt_ab: keine_norm verlangt norm_rang und gilt_ab NULL,
    norm_befristet/norm_unbefristet verlangen norm_rang gesetzt
-- die hier folgenden Tests (die norm_entscheidung=='keine_norm' PRUEFEN,
nicht nur hoffen) waeren an derselben Stelle rot gegangen, haette die
DB-Schranke nicht schon vorher abgebrochen. Beide Ebenen (Python-Test +
DB-Trigger) sind damit als wirksam belegt, nicht nur behauptet."""

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from kern.domaene import importiere, pruefe, setze_in_kraft, speichere
from kern import rangfolge

_QUELLEN = {"z1": {"bezeichnung": "Betriebsausgaben (netto)"}}
_WURZEL = Path(__file__).resolve().parent.parent


@pytest.fixture
def frische_db(tmp_path):
    """Ein Bestand mit dem echten Schema, leer -- Erstanlage, kein Bestand
    (siehe Hausregel 'Zwei Ausgangszustaende, und geprueft wird meist der
    falsche')."""
    db = tmp_path / "wirkung_null.db"
    conn = sqlite3.connect(str(db))
    conn.executescript((_WURZEL / "schema.sql").read_text(encoding="utf-8"))
    conn.close()
    return db


def _paket(regeln, quellen=None, **zusatz):
    basis = {
        "domaene": "steuer",
        "bezeichnung": "Steuer und Belege",
        "herkunft": "test",
        "stand": "2026-08-14T00:00:00+0200",
        "quellen": quellen if quellen is not None else _QUELLEN,
        "regeln": regeln,
    }
    basis.update(zusatz)
    return basis


def _schreibe(tmp_path, inhalt: dict | str):
    pfad = tmp_path / "paket.json"
    if isinstance(inhalt, str):
        pfad.write_text(inhalt, encoding="utf-8")
    else:
        pfad.write_text(json.dumps(inhalt), encoding="utf-8")
    return pfad


def test_paket_mit_belegter_regel_wird_angenommen(tmp_path):
    regeln = [{"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"}]
    pfad = _schreibe(tmp_path, _paket(regeln))

    ergebnis = importiere(pfad)

    assert ergebnis == {"angenommen": True, "anzahl_regeln": 1, "bezeichnung": "Steuer und Belege", "grund": None}


def test_regel_ohne_beleg_wird_abgelehnt_mit_grund(tmp_path):
    """ROT-VOR-GRUEN (H8a): Paket mit einer Regel ohne belegte Fundstelle.

    Rot-Probe von Hand gefahren -- in kern/domaene.py den Aufruf
    `pruefe_regeln(regeln, quellen)` durch ein no-op ersetzt (Pruefung kurz
    entfernt) und diesen Test allein laufen lassen:
        FAILED tests/test_domaene.py::test_regel_ohne_beleg_wird_abgelehnt_mit_grund
        AssertionError: assert {'angenommen': True, 'anzahl_regeln': 1, 'grund': None} == {'angenommen': False, ...}
    Ohne die Pruefung waere eine unbelegte Regel klaglos uebernommen worden.
    Pruefung zurueckgesetzt, danach:
        1 passed in 0.02s
    """
    regeln = [{"id": "Bewirtung", "ziel_id": "z1", "fundstelle": "Erfundener Text"}]
    pfad = _schreibe(tmp_path, _paket(regeln))

    ergebnis = importiere(pfad)

    assert ergebnis["angenommen"] is False
    assert ergebnis["anzahl_regeln"] is None
    assert ergebnis["grund"] == "Die Regel 'Bewirtung' nennt keine Quelle, die zu ihrer Fundstelle passt."


def test_kaputtes_json_wird_abgelehnt_mit_grund(tmp_path):
    pfad = _schreibe(tmp_path, "{das ist kein json")

    ergebnis = importiere(pfad)

    assert ergebnis["angenommen"] is False
    assert ergebnis["anzahl_regeln"] is None
    assert ergebnis["grund"]


def test_fehlende_datei_wird_abgelehnt_mit_grund(tmp_path):
    ergebnis = importiere(tmp_path / "existiert-nicht.json")

    assert ergebnis["angenommen"] is False
    assert ergebnis["grund"]


def test_fehlender_pflichtschluessel_wird_abgelehnt_mit_grund(tmp_path):
    paket = _paket([])
    del paket["quellen"]
    pfad = _schreibe(tmp_path, paket)

    ergebnis = importiere(pfad)

    assert ergebnis["angenommen"] is False
    assert "quellen" in ergebnis["grund"]


def test_leere_regelmenge_wird_angenommen_mit_null_regeln(tmp_path):
    # Entscheidung: eine Domaene ohne Regeln behauptet nichts Unbelegtes und
    # wird angenommen (0 Regeln) -- der Vertrag verweigert nur eine Regel,
    # die ihre Fundstelle nicht zeigen kann, nicht das Fehlen von Regeln.
    pfad = _schreibe(tmp_path, _paket([]))

    ergebnis = importiere(pfad)

    assert ergebnis == {"angenommen": True, "anzahl_regeln": 0, "bezeichnung": "Steuer und Belege", "grund": None}


def test_vertrag_gegen_das_atelier_haelt():
    """Die Naht, an der H8b geraten hat: das atelier liest genau diese drei
    Schluessel aus der Antwort. Aendert einer seinen Namen, zeigt der
    Bildschirm still nichts mehr an -- kein Fehler, nur ein leerer Satz.
    Deshalb steht der Vertrag hier als Test und nicht als Kommentar."""
    from kern import domaene

    ergebnis = domaene.importiere("pakete/steuer.domaene.json")
    assert set(ergebnis) == {"angenommen", "anzahl_regeln", "bezeichnung", "grund"}
    assert ergebnis["angenommen"] is True
    assert ergebnis["anzahl_regeln"] == 4
    assert ergebnis["bezeichnung"]

    # Derselbe Inhalt ueber den Weg, den das atelier wirklich nimmt: Datei
    # ausgewaehlt, Inhalt geschickt -- der Dienst liest nichts selbst.
    import json
    with open("pakete/steuer.domaene.json", encoding="utf-8") as f:
        gleich = domaene.pruefe(json.load(f))
    assert gleich == ergebnis

    abgelehnt = domaene.pruefe({"domaene": "x", "quellen": {}, "regeln": [{"id": "Bewirtung", "ziel_id": "fehlt", "fundstelle": "nichts"}]})
    assert set(abgelehnt) == {"angenommen", "anzahl_regeln", "bezeichnung", "grund"}
    assert abgelehnt["angenommen"] is False
    assert "Bewirtung" in abgelehnt["grund"]


# ---------------------------------------------------------------------------
# WIRKUNG NULL (ADR-018) -- speichere() ist die erste Schreibung dieser Datei.

def test_gespeicherte_regel_traegt_wirkung_null(frische_db):
    regeln = [{"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"}]
    paket = _paket(regeln)

    ergebnis = speichere(paket, db=frische_db)

    assert ergebnis["angenommen"] is True
    assert ergebnis["gespeichert"] == 3  # Wurzel + 1 Quelle + 1 Regel
    assert ergebnis["uebersprungen"] == 0

    conn = sqlite3.connect(str(frische_db))
    conn.row_factory = sqlite3.Row
    regel = conn.execute(
        "SELECT norm_rang, norm_entscheidung, gilt_ab FROM knowledge_nodes WHERE id='domaenenregel-steuer-r1'"
    ).fetchone()
    quelle = conn.execute(
        "SELECT norm_rang, norm_entscheidung FROM knowledge_nodes WHERE id='domaenenquelle-steuer-z1'"
    ).fetchone()
    conn.close()

    # Negativfall: frisch importiert wirkt NICHT.
    assert regel["norm_rang"] is None
    assert regel["norm_entscheidung"] == "keine_norm"
    assert regel["gilt_ab"] is None
    assert rangfolge.norm_score(regel["norm_rang"]) == 0.0
    # Quellen sind Belege, keine Normen -- dieselbe Wirkung Null.
    assert quelle["norm_rang"] is None
    assert quelle["norm_entscheidung"] == "keine_norm"


def test_paket_norm_rang_feld_wird_nie_gelesen(frische_db):
    """Grenzwert: ein Paket, das (unzulaessig) selbst einen Rang behauptet,
    darf ihn nicht in den Bestand tragen -- kein Feld im INSERT liest ihn."""
    regeln = [{
        "id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben",
        "norm_rang": 1, "norm_entscheidung": "norm_unbefristet",
    }]
    paket = _paket(regeln)

    ergebnis = speichere(paket, db=frische_db)
    assert ergebnis["gespeichert"] == 3

    conn = sqlite3.connect(str(frische_db))
    row = conn.execute(
        "SELECT norm_rang, norm_entscheidung FROM knowledge_nodes WHERE id='domaenenregel-steuer-r1'"
    ).fetchone()
    conn.close()
    assert row == (None, "keine_norm"), "das Paket-Feld norm_rang ist in den Bestand durchgesickert"


def test_abgelehntes_paket_schreibt_nichts(frische_db):
    regeln = [{"id": "Bewirtung", "ziel_id": "z1", "fundstelle": "Erfundener Text"}]
    paket = _paket(regeln)

    ergebnis = speichere(paket, db=frische_db)

    assert ergebnis["angenommen"] is False
    assert ergebnis["gespeichert"] == 0
    assert ergebnis["uebersprungen"] == 0
    conn = sqlite3.connect(str(frische_db))
    n = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    conn.close()
    assert n == 0


def test_leeres_paket_wird_ohne_regeln_gespeichert(frische_db):
    paket = _paket([], quellen={})

    ergebnis = speichere(paket, db=frische_db)

    assert ergebnis["angenommen"] is True
    assert ergebnis["gespeichert"] == 1  # nur die Wurzel der Domaene
    assert ergebnis["uebersprungen"] == 0


def test_doppelter_import_ist_idempotent_und_ueberschreibt_inkraftgesetzte_regel_nicht(frische_db):
    regeln = [{"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"}]
    paket = _paket(regeln)

    erster = speichere(paket, db=frische_db)
    assert erster["gespeichert"] == 3 and erster["uebersprungen"] == 0

    geaendert = setze_in_kraft("steuer", "Betreiber", "von Hand geprueft", norm_rang=3, db=frische_db)
    assert geaendert == 1

    zweiter = speichere(paket, db=frische_db)
    assert zweiter["gespeichert"] == 0
    assert zweiter["uebersprungen"] == 3

    conn = sqlite3.connect(str(frische_db))
    row = conn.execute(
        "SELECT norm_rang, norm_entscheidung FROM knowledge_nodes WHERE id='domaenenregel-steuer-r1'"
    ).fetchone()
    conn.close()
    assert row == (3, "norm_unbefristet"), "ein zweiter Import hat die bereits in Kraft gesetzte Regel zurueckgesetzt"


def test_setze_in_kraft_ist_der_weg_heraus_gegenprobe(frische_db):
    """Gegenprobe zur Wirkung Null: ausdruecklich in Kraft gesetzt WIRKT."""
    regeln = [{"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"}]
    speichere(_paket(regeln), db=frische_db)

    geaendert = setze_in_kraft("steuer", "Betreiber", "von Hand geprueft und uebernommen", norm_rang=3, db=frische_db)
    assert geaendert == 1

    conn = sqlite3.connect(str(frische_db))
    conn.row_factory = sqlite3.Row
    regel = conn.execute(
        "SELECT norm_rang, norm_entscheidung, gilt_ab, gilt_bis, norm_entschieden_von, norm_entschieden_grund "
        "FROM knowledge_nodes WHERE id='domaenenregel-steuer-r1'"
    ).fetchone()
    quelle = conn.execute("SELECT norm_rang FROM knowledge_nodes WHERE id='domaenenquelle-steuer-z1'").fetchone()
    conn.close()

    assert regel["norm_rang"] == 3
    assert regel["norm_entscheidung"] == "norm_unbefristet"
    assert regel["gilt_ab"] is not None
    assert regel["gilt_bis"] is None
    assert regel["norm_entschieden_von"] == "Betreiber"
    assert regel["norm_entschieden_grund"] == "von Hand geprueft und uebernommen"
    assert rangfolge.norm_score(regel["norm_rang"]) > 0.0
    # Quellen bleiben Wirkung Null -- setze_in_kraft betrifft nur Regeln.
    assert quelle["norm_rang"] is None


def test_maschine_darf_rang_1_oder_2_nicht_selbst_setzen(frische_db):
    """Dieselbe Schranke wie in kern/regelpaket.py TEIL 3 (Trigger
    knowledge_nodes_normrang_herkunft_bi/_bu): eine Maschine darf einer
    importierten Regel nie Rang 1/2 geben."""
    regeln = [{"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"}]
    speichere(_paket(regeln), db=frische_db)

    with pytest.raises(sqlite3.IntegrityError, match="menschlichen Entscheider"):
        setze_in_kraft("steuer", "claude-opus-5", "Selbstermaechtigung, darf nicht durchgehen", norm_rang=1, db=frische_db)


def test_mensch_darf_rang_1_setzen(frische_db):
    regeln = [{"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"}]
    speichere(_paket(regeln), db=frische_db)

    geaendert = setze_in_kraft("steuer", "Betreiber", "von Hand geprueft", norm_rang=1, db=frische_db)
    assert geaendert == 1


def test_setze_in_kraft_ohne_rang_wirft_sprechenden_fehler(frische_db):
    with pytest.raises(ValueError, match="Rang"):
        setze_in_kraft("steuer", "Betreiber", "Grund", norm_rang=None, db=frische_db)


def test_inkraftsetzung_domaene_ohne_regeln_ist_leeres_ergebnis_kein_fehler(frische_db):
    """Grenzwert: Inkraftsetzung von etwas, das es nicht gibt -- kein Fehler,
    nur 0 geaenderte Zeilen."""
    geaendert = setze_in_kraft("nie-importiert", "Betreiber", "Grund", norm_rang=1, db=frische_db)
    assert geaendert == 0


def test_mutationsprobe_json_dokumentiert_von_hand_gefahren():
    """Kein automatischer Lauf (die Mutation aendert Quelltext) -- der Beleg
    steht als woertliches Fehlerprotokoll im Moduldocstring dieser Datei und
    im Bericht. Dieser Test haelt nur fest, WAS mutiert wurde, damit die
    Probe reproduzierbar bleibt, statt nur behauptet zu sein."""
    quelle = (_WURZEL / "kern" / "domaene.py").read_text(encoding="utf-8")
    assert "'keine_norm','skript:domaene.py'" in quelle, (
        "die Wirkung-Null-Setzung fehlt an der erwarteten Stelle -- Mutationsprobe waere gegenstandslos"
    )
