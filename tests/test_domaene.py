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

from kern.domaene import exportiere, herkunft_uebersicht, importiere, pruefe, setze_in_kraft, speichere
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
        # Pflicht seit B1 (ADR-013: drei Teile). Leer, aber da --
        # Anwesenheit ist der Vertrag, nicht Inhalt.
        "dienst": {},
        "oberflaeche": {"fassung": 1, "bildschirme": []},
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

    abgelehnt = domaene.pruefe({"domaene": "x", "quellen": {}, "regeln": [{"id": "Bewirtung", "ziel_id": "fehlt", "fundstelle": "nichts"}],
                                "dienst": {}, "oberflaeche": {"fassung": 1, "bildschirme": []}})
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
    assert ergebnis["gespeichert"] == 4  # Wurzel + 1 Quelle + 1 Regel + Oberflaeche
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
    assert ergebnis["gespeichert"] == 4  # +Oberflaeche

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
    assert ergebnis["gespeichert"] == 2  # Wurzel + Oberflaeche (leer, aber vorhanden)
    assert ergebnis["uebersprungen"] == 0


def test_doppelter_import_ist_idempotent_und_ueberschreibt_inkraftgesetzte_regel_nicht(frische_db):
    regeln = [{"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"}]
    paket = _paket(regeln)

    erster = speichere(paket, db=frische_db)
    assert erster["gespeichert"] == 4 and erster["uebersprungen"] == 0

    geaendert = setze_in_kraft("steuer", "Betreiber", "von Hand geprueft", norm_rang=3, db=frische_db)
    assert geaendert == 1

    zweiter = speichere(paket, db=frische_db)
    assert zweiter["gespeichert"] == 0
    assert zweiter["uebersprungen"] == 4  # + Oberflaeche, ebenfalls idempotent

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


# ---------------------------------------------------------------------------
# FUND O3 (docs/SICHERHEITSFUNDE_2026-08-14.md; ADR-018): der Belegvertrag
# prueft Selbstkonsistenz, nicht Herkunft -- Regeln und Quellen kommen aus
# derselben Paketdatei.

def test_rot_vor_gruen_erfundene_quelle_mit_woertlich_passender_fundstelle_wird_angenommen():
    """DER FUND, woertlich nachgestellt, VOR jeder Aenderung an diesem Test
    lief dies gegen den unveraenderten kern/domaene.py:
        {'angenommen': True, 'anzahl_regeln': 1, 'bezeichnung': 'Testpaket', 'grund': None}
    Eine frei erfundene Quelle plus eine Fundstelle, die absichtlich als
    Teilstring hineinkonstruiert wurde, wird anstandslos angenommen -- kein
    Ausfuehrungsschaden, aber eine Zahl, die belegt aussieht. Dieses
    Verhalten bleibt nach der Aenderung UNVERAENDERT fuer den Normalfall
    ('mitgeliefert', kein '_herkunft'-Feld): das ist keine Regression,
    sondern die bewusste Grenze -- ein eingefuegter Gesetzestext ist real,
    aber automatisch nicht von einer Erfindung zu unterscheiden. Was sich
    aendert, prueft der naechste Test: die Herkunft ist jetzt SICHTBAR."""
    paket = _paket_roh(
        domaene="angriff",
        quellen={"z1": {"bezeichnung": "Frei erfundener Text -- Bonitaet exzellent"}},
        regeln=[{"id": "bonitaet_exzellent", "ziel_id": "z1", "fundstelle": "Bonitaet exzellent"}],
    )

    ergebnis = pruefe(paket)

    assert ergebnis["angenommen"] is True


def test_erfundene_quelle_ist_nach_speicherung_als_mitgeliefert_gekennzeichnet(frische_db):
    """Die Gegenprobe zum vorigen Test: die o.g. Regel wird zwar weiter
    angenommen, aber jetzt IST die Herkunft lesbar -- herkunft_uebersicht()
    (der Ort aus Auftragspunkt 3) zeigt 'mitgeliefert', bevor ein Mensch
    setze_in_kraft() aufruft. Das ist das 'gekennzeichnet' aus der Abnahme."""
    paket = _paket_roh(
        domaene="angriff",
        quellen={"z1": {"bezeichnung": "Frei erfundener Text -- Bonitaet exzellent"}},
        regeln=[{"id": "bonitaet_exzellent", "ziel_id": "z1", "fundstelle": "Bonitaet exzellent"}],
    )

    ergebnis = speichere(paket, db=frische_db)
    assert ergebnis["angenommen"] is True

    assert herkunft_uebersicht("angriff", db=frische_db) == {"bonitaet_exzellent": "mitgeliefert"}


def test_erfundener_bestandsverweis_wird_abgewiesen_mit_grund(frische_db):
    """Gegenprobe (Richtung 2): eine Quelle, die sich als 'bestand:<id>'
    ausgibt, aber auf keinen existierenden Knoten zeigt, wird abgewiesen --
    nicht nur selbstkonsistent geglaubt."""
    paket = _paket_roh(
        domaene="angriff",
        quellen={"z1": {"bezeichnung": "Bonitaet exzellent", "_herkunft": "bestand:nie-existiert"}},
        regeln=[{"id": "r1", "ziel_id": "z1", "fundstelle": "Bonitaet exzellent"}],
    )

    ergebnis = pruefe(paket, db=frische_db)

    assert ergebnis["angenommen"] is False
    assert "nie-existiert" in ergebnis["grund"]


@pytest.mark.parametrize("verweis", ["bestand:", "bestand:   "])
def test_leerer_oder_reiner_leerraum_bestandsverweis_wird_abgewiesen(frische_db, verweis):
    """Grenzwert: eine leere bzw. nur aus Leerraum bestehende Kennung ist
    kein Verweis -- `"" in text` waere sonst wieder die Falle aus O2."""
    paket = _paket_roh(
        domaene="angriff",
        quellen={"z1": {"bezeichnung": "Bonitaet exzellent", "_herkunft": verweis}},
        regeln=[{"id": "r1", "ziel_id": "z1", "fundstelle": "Bonitaet exzellent"}],
    )

    ergebnis = pruefe(paket, db=frische_db)

    assert ergebnis["angenommen"] is False
    assert "leer" in ergebnis["grund"]


def test_bestandsverweis_auf_sich_selbst_wird_abgewiesen(frische_db):
    """Grenzwert: die Quelle verweist auf einen Knoten, den DIESES Paket
    selbst gerade erst anlegen wuerde -- kein unabhaengiger Anker, nur ein
    Kreis im selben Paket."""
    paket = _paket_roh(
        domaene="angriff",
        quellen={"z1": {"bezeichnung": "x", "_herkunft": "bestand:domaenenquelle-angriff-z1"}},
        regeln=[{"id": "r1", "ziel_id": "z1", "fundstelle": "x"}],
    )

    ergebnis = pruefe(paket, db=frische_db)

    assert ergebnis["angenommen"] is False
    assert "selbst anlegt" in ergebnis["grund"]


def test_echte_auffindbare_bestandsquelle_geht_durch_und_ist_gekennzeichnet(frische_db):
    """Gegenprobe (Richtung 1): eine Quelle, die auf einen WIRKLICH
    vorhandenen, unabhaengig VOR diesem Paket angelegten Bestandsknoten
    zeigt, wird angenommen -- und herkunft_uebersicht() zeigt 'bestand',
    nicht 'mitgeliefert'."""
    vorwissen = _paket_roh(
        domaene="vorwissen",
        quellen={"z1": {"bezeichnung": "Bestehender, unabhaengiger Bestandstext"}},
        regeln=[{"id": "r1", "ziel_id": "z1", "fundstelle": "Bestand"}],
    )
    vorab = speichere(vorwissen, db=frische_db)
    assert vorab["angenommen"] is True

    paket = _paket_roh(
        domaene="angriff",
        quellen={"z1": {
            "bezeichnung": "Bonitaet exzellent",
            "_herkunft": "bestand:domaenenquelle-vorwissen-z1",
        }},
        regeln=[{"id": "r1", "ziel_id": "z1", "fundstelle": "Bonitaet exzellent"}],
    )

    ergebnis = speichere(paket, db=frische_db)

    assert ergebnis["angenommen"] is True
    assert herkunft_uebersicht("angriff", db=frische_db) == {"r1": "bestand"}


def test_zwei_regeln_mit_derselben_quelle_bleiben_erlaubt(frische_db):
    """Grenzwert, negativ formuliert: derselbe Beleg fuer zwei Regeln ist
    KEIN Herkunftsproblem und wird nicht neuerdings abgewiesen."""
    paket = _paket_roh(
        domaene="steuer2",
        quellen=_QUELLEN,
        regeln=[
            {"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"},
            {"id": "r2", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"},
        ],
    )

    ergebnis = speichere(paket, db=frische_db)

    assert ergebnis["angenommen"] is True
    assert ergebnis["gespeichert"] == 5  # Wurzel + 1 Quelle + 2 Regeln + Oberflaeche


def test_mutationsprobe_bestandspruefung_von_hand_gefahren(tmp_path, frische_db):
    """MUTATIONSPROBE (L-da6eb5) auf einer KOPIE, das Original bleibt
    unangetastet: kern/domaene.py in tmp_path kopiert, darin den Aufruf
        fehler = _pruefe_bestandsquellen(paket["domaene"], quellen, regeln, db)
        if fehler:
            return _abgelehnt(fehler)
    durch ein no-op ersetzt (die Bestandspruefung damit ausgeschaltet), das
    Modul unter neuem Namen geladen und test_erfundener_bestandsverweis_wird_
    abgewiesen_mit_grund nachgestellt: die erfundene Quelle 'bestand:nie-
    existiert' wurde OHNE die Pruefung anstandslos angenommen (angenommen=
    True) -- der Test waere an dieser Stelle rot gegangen. Mit der Pruefung
    (dieser Test hier, gegen das unveraenderte Original) ist sie es nicht."""
    import importlib.util
    import shutil

    kopie = tmp_path / "domaene_mutiert.py"
    shutil.copy(_WURZEL / "kern" / "domaene.py", kopie)
    text = kopie.read_text(encoding="utf-8")
    ziel = (
        'fehler = _pruefe_bestandsquellen(paket["domaene"], quellen, regeln, db)\n'
        '    if fehler:\n'
        '        return _abgelehnt(fehler)'
    )
    assert ziel in text, "die erwartete Stelle fehlt -- Mutationsprobe waere gegenstandslos"
    mutiert = text.replace(ziel, "pass  # Bestandspruefung mutiert weg")
    kopie.write_text(mutiert, encoding="utf-8")

    spec = importlib.util.spec_from_file_location("domaene_mutiert", kopie)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)

    paket = _paket_roh(
        domaene="angriff",
        quellen={"z1": {"bezeichnung": "Bonitaet exzellent", "_herkunft": "bestand:nie-existiert"}},
        regeln=[{"id": "r1", "ziel_id": "z1", "fundstelle": "Bonitaet exzellent"}],
    )
    ergebnis_mutiert = modul.pruefe(paket, db=frische_db)
    assert ergebnis_mutiert["angenommen"] is True, (
        "die Mutation haette die Bestandspruefung ausschalten muessen -- "
        "ohne rote Gegenprobe waere dieser Test blind"
    )

    ergebnis_original = pruefe(paket, db=frische_db)
    assert ergebnis_original["angenommen"] is False


# ---------------------------------------------------------------------------
# H10 -- exportiere() ist der Zwilling von importiere()/pruefe(). Gate ist
# freigabe='offen' je Knoten (schema.sql-Default 'intern' -- ein importierter
# Knoten reist nie von selbst weiter).

def _freigeben(db, *node_ids):
    conn = sqlite3.connect(str(db))
    conn.executemany(
        "UPDATE knowledge_nodes SET freigabe='offen' WHERE id=?",
        [(i,) for i in node_ids],
    )
    conn.commit()
    conn.close()


def test_export_domaene_die_es_nicht_gibt_liefert_none(frische_db):
    """Grenzwert: eine Kennung, fuer die nie importiert wurde."""
    assert exportiere("nie-existiert", db=frische_db) is None


def test_export_leere_domaene_liefert_leeres_paket(frische_db):
    """Grenzwert: Wurzel existiert (leeres Paket importiert), aber es gibt
    nichts, das exportiert werden koennte -- kein Fehler, leeres Paket."""
    speichere(_paket([], quellen={}), db=frische_db)

    paket = exportiere("steuer", db=frische_db)

    assert paket["domaene"] == "steuer"
    assert paket["quellen"] == {}
    assert paket["regeln"] == []


def test_export_nur_gesperrte_knoten_liefert_leeres_paket(frische_db):
    """Grenzwert: Domaene mit Regeln, aber KEINE davon ist freigegeben --
    Vorgabewert nach dem Import ist ueberall 'intern' (schema.sql-Default),
    kein einziger Aufruf in speichere() setzt freigabe='offen'."""
    regeln = [{"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"}]
    speichere(_paket(regeln), db=frische_db)

    paket = exportiere("steuer", db=frische_db)

    assert paket["quellen"] == {}
    assert paket["regeln"] == []


def test_gegenprobe_freigabe_interner_knoten_landet_nicht_im_export(frische_db):
    """ROT-VOR-GRUEN fuer die Freigabe-Schranke: zwei Regeln, nur EINE
    Quelle+Regel wird auf 'offen' gesetzt. Die interne muss draussen bleiben
    -- kein 'wahrscheinlich', ein konkreter Fall."""
    regeln = [
        {"id": "offen1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"},
        {"id": "intern1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"},
    ]
    speichere(_paket(regeln), db=frische_db)
    _freigeben(frische_db, "domaenenquelle-steuer-z1", "domaenenregel-steuer-offen1")
    # domaenenregel-steuer-intern1 bleibt bewusst 'intern'.

    paket = exportiere("steuer", db=frische_db)

    ids = {r["id"] for r in paket["regeln"]}
    assert ids == {"offen1"}, "die intern gebliebene Regel ist mit exportiert worden"
    assert "z1" in paket["quellen"]


def test_offene_regel_ohne_offene_quelle_bleibt_draussen(frische_db):
    """Eine Regel kann nicht ohne ihre Quelle reisen -- sonst waere das
    Paket am Zielort kein gueltiger Belegvertrag mehr (pruefe_regeln findet
    das ziel_id nicht)."""
    regeln = [{"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"}]
    speichere(_paket(regeln), db=frische_db)
    _freigeben(frische_db, "domaenenregel-steuer-r1")  # Quelle bleibt intern

    paket = exportiere("steuer", db=frische_db)

    assert paket["regeln"] == []
    assert paket["quellen"] == {}


def test_gegenprobe_rang_norm_rang_feld_reist_nie_mit(frische_db):
    """Meine Vermutung (norm_rang gilt nicht am Zielort) geprueft an zwei
    Stellen: (1) ein Paket, das absichtlich ein 'norm_rang'-Feld IM CONTENT
    einer Regel mitschickt (wie test_paket_norm_rang_feld_wird_nie_gelesen),
    darf es nicht ungefiltert in den Export tragen. (2) setze_in_kraft()
    setzt den echten DB-Rang -- der lebt NUR als Spalte, nie im 'content',
    das exportiere() liest, also kann er gar nicht mitreisen."""
    regeln = [{
        "id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben",
        "norm_rang": 1, "norm_entscheidung": "norm_unbefristet",
    }]
    speichere(_paket(regeln), db=frische_db)
    setze_in_kraft("steuer", "Betreiber", "von Hand geprueft", norm_rang=3, db=frische_db)
    _freigeben(frische_db, "domaenenquelle-steuer-z1", "domaenenregel-steuer-r1")

    paket = exportiere("steuer", db=frische_db)

    regel = paket["regeln"][0]
    assert "norm_rang" not in regel, "das Paket-Feld norm_rang ist in den Export durchgesickert"


def test_rundlauf_export_import_auf_leerer_instanz_ergibt_dasselbe(tmp_path, frische_db):
    """Hauptbeleg (Abnahme): Export -> Import in eine FRISCHE, leere
    Datenbank -> derselbe Belegvertrag gilt dort. Vorbedingung: die Regel
    wurde am Quellort bereits in Kraft gesetzt (Rang 3) -- am Zielort greift
    trotzdem wieder Wirkung Null, weil setze_in_kraft() dort nie lief."""
    regeln = [{"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"}]
    speichere(_paket(regeln), db=frische_db)
    setze_in_kraft("steuer", "Betreiber", "von Hand geprueft", norm_rang=3, db=frische_db)
    _freigeben(frische_db, "domaenenquelle-steuer-z1", "domaenenregel-steuer-r1")

    paket = exportiere("steuer", db=frische_db)
    assert paket["regeln"] and paket["quellen"], "Export war leer -- Rundlauf gegenstandslos"

    # Zielort: eine zweite, frische, LEERE Datenbank (nicht dieselbe Datei).
    ziel_db = tmp_path / "ziel.db"
    zconn = sqlite3.connect(str(ziel_db))
    zconn.executescript((_WURZEL / "schema.sql").read_text(encoding="utf-8"))
    zconn.close()

    ergebnis = speichere(paket, db=ziel_db)

    assert ergebnis["angenommen"] is True
    assert ergebnis["anzahl_regeln"] == 1
    assert ergebnis["gespeichert"] == 4  # Wurzel + 1 Quelle + 1 Regel + Oberflaeche

    zconn = sqlite3.connect(str(ziel_db))
    zconn.row_factory = sqlite3.Row
    regel = zconn.execute(
        "SELECT norm_rang, norm_entscheidung FROM knowledge_nodes WHERE id='domaenenregel-steuer-r1'"
    ).fetchone()
    zconn.close()

    # Gegenprobe Rang: NICHT 3 (der Wert am Quellort), sondern wieder NULL --
    # Wirkung Null gilt am Zielort neu, unabhaengig vom Quellort.
    assert regel["norm_rang"] is None
    assert regel["norm_entscheidung"] == "keine_norm"


def test_export_zweimal_hintereinander_ist_bis_auf_stand_identisch(frische_db):
    """Grenzwert: zwei Exporte ohne Bestandsaenderung dazwischen liefern
    dieselben Regeln/Quellen -- nur 'stand' (Erzeugungszeitpunkt) darf, muss
    aber nicht, sich unterscheiden."""
    regeln = [{"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"}]
    speichere(_paket(regeln), db=frische_db)
    _freigeben(frische_db, "domaenenquelle-steuer-z1", "domaenenregel-steuer-r1")

    erster = exportiere("steuer", db=frische_db)
    zweiter = exportiere("steuer", db=frische_db)

    assert erster["quellen"] == zweiter["quellen"]
    assert erster["regeln"] == zweiter["regeln"]
    assert erster["domaene"] == zweiter["domaene"] == "steuer"


def test_export_gibt_paket_zurueck_das_pruefe_akzeptiert(frische_db):
    """Positivkontrolle gegen den echten Bestand (Pruefstand-Regel): das von
    exportiere() gebaute Paket ist kein Fantasie-Objekt, sondern besteht die
    ECHTE Pruefung aus pruefe() -- derselbe Belegvertrag, den auch das
    atelier beim Import durchlaeuft."""
    regeln = [{"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"}]
    speichere(_paket(regeln), db=frische_db)
    _freigeben(frische_db, "domaenenquelle-steuer-z1", "domaenenregel-steuer-r1")

    paket = exportiere("steuer", db=frische_db)

    ergebnis = pruefe(paket)
    assert ergebnis["angenommen"] is True
    assert ergebnis["anzahl_regeln"] == 1


def _paket_roh(domaene, quellen, regeln, **zusatz):
    basis = {
        "domaene": domaene,
        "bezeichnung": "t",
        "herkunft": "test",
        "stand": "2026-08-15T00:00:00+0200",
        "quellen": quellen,
        "regeln": regeln,
        # Pflicht seit B1 (ADR-013: drei Teile). Leer, aber da --
        # Anwesenheit ist der Vertrag, nicht Inhalt.
        "dienst": {},
        "oberflaeche": {"fassung": 1, "bildschirme": []},
    }
    basis.update(zusatz)
    return basis
