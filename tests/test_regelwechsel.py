"""Der Regelwechsel-Melder muss melden -- und nur, was er darf.

ANLASS (Betreiberfrage 2026-08-11): "kann brainlehr die aenderungen hier nicht
in den chat injizieren und dich zwingen auf den neusten stand zu bringen?"

Der teuerste Fall, gegen den hier geprueft wird, ist nicht das Ausbleiben
einer Meldung, sondern die OFFENE QUELLE: Duerfte der Melder beliebige Dateien
einspielen, koennte jeder, der eine Datei im Repo anlegt, dem Assistenten
Anweisungen unterschieben. Die feste Liste ist deshalb Gegenstand eines
eigenen Tests.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path.insert(0, str(_w / "haken"))

import regelwechsel  # noqa: E402


def _lauf(sitzung: str) -> dict:
    lauf = subprocess.run(
        [sys.executable, str(_w / "haken" / "regelwechsel.py")],
        input=json.dumps({"session_id": sitzung}),
        capture_output=True, text=True, timeout=60,
    )
    assert lauf.returncode == 0, lauf.stderr[-400:]
    return json.loads(lauf.stdout) if lauf.stdout.strip() else {}


def test_erster_blick_meldet_nichts(tmp_path, monkeypatch):
    """Sonst bekaeme jede Sitzung beim ersten Prompt eine Meldung ueber einen
    Stand, den sie ohnehin geladen hat."""
    datei = tmp_path / "regeln.md"
    datei.write_text("# Eins\ntext\n", encoding="utf-8")
    monkeypatch.setattr(regelwechsel, "BEOBACHTET", (datei,))
    monkeypatch.setattr(regelwechsel, "ZUSTAND", tmp_path / "zustand.json")
    assert regelwechsel.pruefe("s1") == []


def test_aenderung_wird_gemeldet(tmp_path, monkeypatch):
    datei = tmp_path / "regeln.md"
    datei.write_text("# Eins\ntext\n", encoding="utf-8")
    monkeypatch.setattr(regelwechsel, "BEOBACHTET", (datei,))
    monkeypatch.setattr(regelwechsel, "ZUSTAND", tmp_path / "zustand.json")
    regelwechsel.pruefe("s1")
    datei.write_text("# Eins\ntext\n\n## Zwei\nneu\n", encoding="utf-8")
    meldungen = regelwechsel.pruefe("s1")
    assert len(meldungen) == 1
    assert "Zwei" in meldungen[0], "der neue Abschnitt muss benannt sein"
    assert "+3" in meldungen[0], "die Zeilenbilanz fehlt"


def test_jede_sitzung_wird_einzeln_gezaehlt(tmp_path, monkeypatch):
    """GRENZFALL: Eine zweite Sitzung darf die Meldung der ersten nicht
    verbrauchen -- sonst bekommt genau die Sitzung nichts, die sie braucht."""
    datei = tmp_path / "regeln.md"
    datei.write_text("# Eins\n", encoding="utf-8")
    monkeypatch.setattr(regelwechsel, "BEOBACHTET", (datei,))
    monkeypatch.setattr(regelwechsel, "ZUSTAND", tmp_path / "zustand.json")
    regelwechsel.pruefe("s1")
    regelwechsel.pruefe("s2")
    datei.write_text("# Eins\n## Zwei\n", encoding="utf-8")
    assert regelwechsel.pruefe("s1"), "Sitzung 1 bekam keine Meldung"
    assert regelwechsel.pruefe("s2"), "Sitzung 2 bekam keine Meldung"


def test_entfernter_abschnitt_wird_gemeldet(tmp_path, monkeypatch):
    """NEGATIVFALL: Eine gestrichene Regel ist so folgenreich wie eine neue."""
    datei = tmp_path / "regeln.md"
    datei.write_text("# Eins\n## Zwei\n", encoding="utf-8")
    monkeypatch.setattr(regelwechsel, "BEOBACHTET", (datei,))
    monkeypatch.setattr(regelwechsel, "ZUSTAND", tmp_path / "zustand.json")
    regelwechsel.pruefe("s1")
    datei.write_text("# Eins\n", encoding="utf-8")
    m = regelwechsel.pruefe("s1")
    assert m and "ENTFERNT" in m[0] and "Zwei" in m[0]


def test_die_quelle_ist_geschlossen():
    """DER SICHERHEITSTEST. Eine offene Liste waere ein Einfallstor: wer eine
    Datei anlegen kann, koennte dem Assistenten Anweisungen unterschieben."""
    for pfad in regelwechsel.BEOBACHTET:
        assert isinstance(pfad, Path), "nur feste Pfade, keine Muster"
        text = str(pfad)
        assert "*" not in text and "?" not in text, f"Platzhalter in {text}"
        assert text.endswith((".md",)), f"nur Regeldateien: {text}"
    assert len(regelwechsel.BEOBACHTET) <= 5, \
        "die Liste waechst -- jede Datei darf ungefragt Anweisungen einspielen"


def test_fehlende_datei_bricht_nicht(tmp_path, monkeypatch):
    """Fail-open: ein Melder, der die Arbeit anhaelt, ist schlimmer als eine
    verpasste Meldung."""
    monkeypatch.setattr(regelwechsel, "BEOBACHTET", (tmp_path / "gibtsnicht.md",))
    monkeypatch.setattr(regelwechsel, "ZUSTAND", tmp_path / "zustand.json")
    assert regelwechsel.pruefe("s1") == []


def test_haken_gibt_gueltiges_json_und_endet_mit_null():
    """Der Weg, den der Klient nimmt -- als eigener Prozess."""
    erg = _lauf("test-sitzung-ohne-aenderung")
    assert erg == {} or "hookSpecificOutput" in erg


# --- Normen im Speicher, nicht nur Dateien ---------------------------------

def _db(tmp_path):
    """Eine Datenbank mit dem echten Schema -- Normen haben Pflichtfelder und
    Trigger, ein nachgebautes CREATE TABLE wuerde daran vorbeimessen."""
    import sqlite3
    p = tmp_path / "knowledge.db"
    conn = sqlite3.connect(str(p))
    conn.executescript((_w / "schema.sql").read_text(encoding="utf-8"))
    # KEIN ALTER TABLE: schema.sql traegt `project_id` bereits. Der erste
    # Anlauf legte hier eine eigene Spalte `project` an -- gemessen am
    # 2026-08-18 gegen brainlehr.db gibt es die dort NICHT, und der Melder
    # waere gegen die echte Datenbank in seinen fail-open-Zweig gelaufen:
    # der ganze Normwechsel-Zweig still leer, nicht nur der Zusatz. Ein
    # Testschema, das mehr kann als das echte, prueft sich selbst.
    conn.commit(); conn.close()
    return p


def _norm(db, node_id, rang, titel, wann="2026-08-11T09:00:00+02:00",
          actor=None, bedient_von=None, content=None,
          norm_entschieden_von="test", project="shared"):
    import sqlite3
    conn = sqlite3.connect(str(db))
    try:
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, parent_path, title, summary, "
            "content, source, norm_rang, gilt_ab, norm_entscheidung, "
            "norm_entschieden_grund, norm_entschieden_von, norm_entschieden_am, "
            "actor, bedient_von, project_id, created_at, updated_at) "
            "VALUES (?,?,'/',?,?,?,?,?,'2026-08-11','norm_unbefristet','Testnorm.',"
            "?,'2026-08-11',?,?,?,?,?)",
            (node_id, f"/probe/{node_id}", titel, "Zusammenfassung.", content,
             "Test test_regelwechsel.py", rang, norm_entschieden_von, actor,
             bedient_von, project, wann, wann))
        conn.commit()
    finally:
        conn.close()


def _update_norm(db, node_id, wann, actor=None, bedient_von=None, content=None,
                  titel=None, norm_entschieden_von=None):
    """Schreibt eine bestehende Norm um -- loest den Fassungs-Trigger aus wie
    eine echte Aenderung, damit knowledge_fassungen die Vorfassung traegt.

    norm_entschieden_von bleibt standardmaessig unveraendert (COALESCE), nur
    wer ihn ausdruecklich mitgibt, schreibt ihn um."""
    import sqlite3
    conn = sqlite3.connect(str(db))
    try:
        conn.execute(
            "UPDATE knowledge_nodes SET updated_at=?, actor=?, bedient_von=?, "
            "content=?, title=COALESCE(?, title), "
            "norm_entschieden_von=COALESCE(?, norm_entschieden_von) WHERE id=?",
            (wann, actor, bedient_von, content, titel, norm_entschieden_von,
             node_id))
        conn.commit()
    finally:
        conn.close()


def test_neue_bindende_norm_wird_gemeldet(tmp_path, monkeypatch):
    """ROT VOR GRUEN, und der Anlass ist ein echter Ausfall: c14adcfe (Rang 2)
    wurde am 2026-08-11 um 08:39 gesetzt und verlangt die autonome Pflege des
    Lageknotens. Sie lag den ganzen Vormittag im passiven Recall und wurde
    nicht gelesen -- die Regel sagt in Punkt 5 selbst, dass passiver Recall
    kein Handoff ist."""
    db = _db(tmp_path)
    monkeypatch.setattr(regelwechsel, "BEOBACHTET", ())
    monkeypatch.setattr(regelwechsel, "ZUSTAND", tmp_path / "z.json")
    monkeypatch.setattr(regelwechsel, "DB", db)
    regelwechsel.pruefe("s1")                       # erster Blick: still
    _norm(db, "neu00001", 2, "Schichtbetrieb: Lageknoten pflegen")
    meldungen = regelwechsel.pruefe("s1")
    assert meldungen, "eine neue Rang-2-Norm blieb stumm"
    assert "neu00001" in meldungen[0], "die Kennung fehlt -- ohne sie kein Nachlesen"


def test_rang_drei_und_tiefer_meldet_nicht(tmp_path, monkeypatch):
    """GRENZWERT. Rang 1 und 2 sind Direktiven, ab Rang 3 sind es ADRs und
    Fakten. Meldete der Haken alles, waere er nach einer Woche Rauschen --
    und wer Rauschen abschaltet, schaltet auch die Direktiven ab."""
    db = _db(tmp_path)
    monkeypatch.setattr(regelwechsel, "BEOBACHTET", ())
    monkeypatch.setattr(regelwechsel, "ZUSTAND", tmp_path / "z.json")
    monkeypatch.setattr(regelwechsel, "DB", db)
    regelwechsel.pruefe("s1")
    _norm(db, "adr00001", 3, "Irgendeine ADR")
    assert regelwechsel.pruefe("s1") == []


def test_fehlende_datenbank_bricht_nicht(tmp_path, monkeypatch):
    """Fail-open wie der Rest des Melders."""
    monkeypatch.setattr(regelwechsel, "BEOBACHTET", ())
    monkeypatch.setattr(regelwechsel, "ZUSTAND", tmp_path / "z.json")
    monkeypatch.setattr(regelwechsel, "DB", tmp_path / "gibtsnicht.db")
    assert regelwechsel.pruefe("s1") == []


# --- Urheber: Betreiber, Werkzeug, unbekannt (Auftrag 107, 2026-08-13) -----
#
# ANLASS: Das S12-Umschriftwerkzeug schrieb 07fb68aa um -- der Melder feuerte
# "Das ist eine Weisung des Betreibers", obwohl der Betreiber nichts
# geaendert hatte. Dieselbe falsche Behauptung ein zweites Mal, als
# kern/sicherung_s12.py --zurueck den Knoten WORTGLEICH auf die Urfassung
# zurücksetzte -- eine Reparatur, keine Weisung.

def test_werkzeug_urheber_loest_keine_weisung_aus(tmp_path, monkeypatch):
    """ROT VOR GRUEN: die alte Fassung des Melders meldete jede Aenderung,
    unabhaengig vom actor -- dieser Test waere dort rot gewesen. Wird die
    Unterscheidung in _urheber()/pruefe() entfernt, wird er wieder rot."""
    db = _db(tmp_path)
    monkeypatch.setattr(regelwechsel, "BEOBACHTET", ())
    monkeypatch.setattr(regelwechsel, "ZUSTAND", tmp_path / "z.json")
    monkeypatch.setattr(regelwechsel, "DB", db)
    _norm(db, "07fb68aa", 2, "Testnorm", actor="betreiber", content="Urtext")
    regelwechsel.pruefe("s1")                       # erster Blick: still
    _update_norm(db, "07fb68aa", "2026-08-13T09:00:00+02:00",
                 actor="s12-umschriftwerkzeug", content="Umgeschriebener Text")
    meldungen = regelwechsel.pruefe("s1")
    assert meldungen == [], (
        "ein Werkzeug-Urheber darf keine Weisungsmeldung ausloesen: " + repr(meldungen))


def test_wiederherstellung_meldet_nicht_auch_bei_betreiber_actor(tmp_path, monkeypatch):
    """Der robustere Griff: WORTGLEICH mit einer Vorfassung heisst Reparatur,
    unabhaengig davon, wer sie ausgefuehrt hat. Der zweite S12-Vorfall --
    kern/sicherung_s12.py --zurueck lief unter einem Werkzeug-actor, hier wird
    zusaetzlich geprueft, dass selbst ein Betreiber-actor keine Meldung
    ausloest, wenn der Text nur wiederhergestellt wurde."""
    db = _db(tmp_path)
    monkeypatch.setattr(regelwechsel, "BEOBACHTET", ())
    monkeypatch.setattr(regelwechsel, "ZUSTAND", tmp_path / "z.json")
    monkeypatch.setattr(regelwechsel, "DB", db)
    _norm(db, "07fb68aa", 2, "Testnorm", actor="betreiber", content="Urtext")
    regelwechsel.pruefe("s1")                       # erster Blick: still
    _update_norm(db, "07fb68aa", "2026-08-13T09:00:00+02:00",
                 actor="s12-umschriftwerkzeug", content="Umgeschriebener Text")
    regelwechsel.pruefe("s1")                       # Zwischenschritt konsumieren
    _update_norm(db, "07fb68aa", "2026-08-13T09:05:00+02:00",
                 actor="betreiber", content="Urtext")     # WORTGLEICH zur Urfassung
    meldungen = regelwechsel.pruefe("s1")
    assert meldungen == [], (
        "wortgleiche Wiederherstellung ist keine Weisung, auch nicht mit "
        "Betreiber-actor: " + repr(meldungen))


def test_betreiber_urheber_loest_weisung_weiterhin_aus(tmp_path, monkeypatch):
    """NEGATIVFALL zu den beiden Tests oben: ohne ihn koennte ein Melder, der
    ueberhaupt nichts mehr meldet, dieselben Tests bestehen."""
    db = _db(tmp_path)
    monkeypatch.setattr(regelwechsel, "BEOBACHTET", ())
    monkeypatch.setattr(regelwechsel, "ZUSTAND", tmp_path / "z.json")
    monkeypatch.setattr(regelwechsel, "DB", db)
    _norm(db, "07fb68aa", 2, "Testnorm", actor="betreiber", content="Urtext")
    regelwechsel.pruefe("s1")
    _update_norm(db, "07fb68aa", "2026-08-13T09:00:00+02:00",
                 actor="betreiber", content="Echte Aenderung durch den Betreiber")
    meldungen = regelwechsel.pruefe("s1")
    assert meldungen and "Weisung des Betreibers" in meldungen[0]
    assert "07fb68aa" in meldungen[0]


def test_bedient_von_zaehlt_als_betreiber(tmp_path, monkeypatch):
    """bedient_von ist der beglaubigte Beleg, dass ein Mensch die Maschine
    fuehrt (kern/ausweis.py) -- das zaehlt wie eine direkte Betreiberaenderung,
    auch wenn actor der Name eines Agenten ist."""
    db = _db(tmp_path)
    monkeypatch.setattr(regelwechsel, "BEOBACHTET", ())
    monkeypatch.setattr(regelwechsel, "ZUSTAND", tmp_path / "z.json")
    monkeypatch.setattr(regelwechsel, "DB", db)
    # bedient_von ist ab dem Schreiben unveraenderlich (Trigger
    # knowledge_nodes_bedient_von_unveraenderlich_bu) -- darum von Anfang an
    # gesetzt, nur der Inhalt aendert sich.
    _norm(db, "07fb68aa", 2, "Testnorm", actor="chatgpt", bedient_von="markus",
          content="Urtext")
    regelwechsel.pruefe("s1")
    _update_norm(db, "07fb68aa", "2026-08-13T09:00:00+02:00",
                 actor="chatgpt", bedient_von="markus", content="Neuer Text")
    meldungen = regelwechsel.pruefe("s1")
    assert meldungen and "Das ist eine Weisung des Betreibers" in meldungen[0]


def test_actor_leer_meldet_offenen_urheber_statt_zu_schweigen(tmp_path, monkeypatch):
    """GRENZWERT: actor NULL/leer darf weder als Betreiber behauptet noch
    stillschweigend uebergangen werden -- der Meldetext muss die offene
    Herkunft selbst benennen."""
    db = _db(tmp_path)
    monkeypatch.setattr(regelwechsel, "BEOBACHTET", ())
    monkeypatch.setattr(regelwechsel, "ZUSTAND", tmp_path / "z.json")
    monkeypatch.setattr(regelwechsel, "DB", db)
    _norm(db, "07fb68aa", 2, "Testnorm", actor="betreiber", content="Urtext")
    regelwechsel.pruefe("s1")
    _update_norm(db, "07fb68aa", "2026-08-13T09:00:00+02:00",
                 actor=None, content="Text ohne erkennbaren Schreiber")
    meldungen = regelwechsel.pruefe("s1")
    assert meldungen, "actor leer darf nicht stillschweigend uebergangen werden"
    assert "URHEBER OFFEN" in meldungen[0]
    assert "Das ist eine Weisung des Betreibers" not in meldungen[0], (
        "eine offene Herkunft ist keine Behauptung, wer es war")


# --- norm_entschieden_von als zweitstaerkstes Merkmal (Auftrag: 15 von 23 --
# Rang-1-Normen meldeten "URHEBER OFFEN", obwohl norm_entschieden_von='betreiber'
# in der Datenbank steht -- der Melder fragte das Feld bislang gar nicht ab)

def test_norm_entschieden_von_betreiber_gilt_als_betreiber(tmp_path, monkeypatch):
    """ROT VOR GRUEN, stellt Knoten 222acfea nach: actor=None, bedient_von=None,
    norm_entschieden_von='betreiber'. Vor dem Fix meldete das 'URHEBER OFFEN',
    obwohl die Herkunft in der Datenbank eindeutig steht."""
    db = _db(tmp_path)
    monkeypatch.setattr(regelwechsel, "BEOBACHTET", ())
    monkeypatch.setattr(regelwechsel, "ZUSTAND", tmp_path / "z.json")
    monkeypatch.setattr(regelwechsel, "DB", db)
    _norm(db, "07fb68aa", 2, "Testnorm", actor="betreiber",
          norm_entschieden_von="betreiber", content="Urtext")
    regelwechsel.pruefe("s1")                       # erster Blick: still
    _update_norm(db, "07fb68aa", "2026-08-14T09:00:00+02:00",
                 actor=None, bedient_von=None, norm_entschieden_von="betreiber",
                 content="Neuer Text ohne actor, mit norm_entschieden_von")
    meldungen = regelwechsel.pruefe("s1")
    assert meldungen, "eine echte Aenderung darf nicht stumm bleiben"
    assert "Das ist eine Weisung des Betreibers" in meldungen[0], (
        "norm_entschieden_von='betreiber' muss wie actor='betreiber' zaehlen: "
        + repr(meldungen))
    assert "URHEBER OFFEN" not in meldungen[0]


def test_beides_leer_bleibt_unbekannt():
    """NEGATIVFALL, auf Funktionsebene: fehlen actor UND norm_entschieden_von,
    bleibt es 'unbekannt' -- der Fix darf nicht stillschweigend zu 'betreiber'
    kippen. Ueber die DB laesst sich dieser Zustand nicht nachstellen, weil
    das Schema norm_entschieden_von fuer jede entschiedene Norm erzwingt
    (knowledge_nodes_norm_entscheidung_wer_bi/bu) -- das ist genau der Beleg
    aus dem Auftrag, dass norm_entschieden_von bei ALLEN 23 Rang-1-Normen
    gesetzt ist."""
    assert regelwechsel._urheber(None, None, None) == "unbekannt"
    assert regelwechsel._urheber(None, None, "") == "unbekannt"
    assert regelwechsel._urheber("unbekannt", None, None) == "unbekannt"


# --- Herkunftswert fuer Fremdnormen (Auftrag 2026-08-14, Normachse 3) ------
#
# ANLASS: Ohne eigenen Zweig fuer den neuen Wert norm_entschieden_von=
# 'gesetzgeber' (kern/normachsen.py::HERKUNFT_FREMD) waeren die drei echten
# Fremdnormen im Bestand auf 'unbekannt' gefallen und haetten ab dem naechsten
# Sitzungsstart "URHEBER OFFEN -- ungeklaerte Herkunft" gemeldet, obwohl die
# Herkunft geklaert ist: sie ist nur nicht der Betreiber.

def test_urheber_fremd_direkt():
    """ROT VOR GRUEN auf Funktionsebene: vor dem Fix kannte _urheber() nur
    'betreiber'/'werkzeug'/'unbekannt' -- 'gesetzgeber' fiel mangels Treffer
    auf 'unbekannt'."""
    assert regelwechsel._urheber(None, None, "gesetzgeber") == "fremd"
    # bedient_von schlaegt weiterhin alles -- auch eine Fremdnorm kann ein
    # Mensch mit beglaubigtem Ausweis eintragen.
    assert regelwechsel._urheber(None, "markus", "gesetzgeber") == "betreiber"


def test_norm_entschieden_von_gesetzgeber_meldet_fremd_statt_offen(tmp_path, monkeypatch):
    """ROT VOR GRUEN: stellt eine der drei echten Fremdnormen nach (source
    nennt ein Gesetz, norm_entschieden_von='gesetzgeber' nach der Migration).
    Vor dem Fix waere die Meldung 'URHEBER OFFEN -- ungeklaerte Herkunft'
    gewesen -- falsch, denn die Herkunft ist geklaert."""
    db = _db(tmp_path)
    monkeypatch.setattr(regelwechsel, "BEOBACHTET", ())
    monkeypatch.setattr(regelwechsel, "ZUSTAND", tmp_path / "z.json")
    monkeypatch.setattr(regelwechsel, "DB", db)
    _norm(db, "07fb68aa", 1, "GEG heisst seit 29.07.2026 GMoDG",
          norm_entschieden_von="gesetzgeber", content="Urtext")
    regelwechsel.pruefe("s1")                       # erster Blick: still
    _update_norm(db, "07fb68aa", "2026-08-14T09:00:00+02:00",
                 actor=None, bedient_von=None, norm_entschieden_von="gesetzgeber",
                 content="Text nach Aktualisierung durch das Gesetz")
    meldungen = regelwechsel.pruefe("s1")
    assert meldungen, "eine echte Aenderung darf nicht stumm bleiben"
    assert "URHEBER OFFEN" not in meldungen[0], (
        "eine Fremdnorm mit Herkunftswert ist keine ungeklaerte Herkunft: "
        + repr(meldungen))
    assert "Weisung des Betreibers" not in meldungen[0], (
        "eine Fremdnorm ist keine Betreiberweisung: " + repr(meldungen))
    assert "NICHT widerrufbar" in meldungen[0]
    assert "07fb68aa" in meldungen[0]


def test_norm_entschieden_von_anderer_wert_wird_nicht_zu_betreiber(tmp_path, monkeypatch):
    """NEGATIVFALL: ein von 'betreiber' abweichender Wert (z.B. eine externe
    Quelle wie 'Gesetz' oder ein Testwert) darf nicht zu 'betreiber' fuehren."""
    db = _db(tmp_path)
    monkeypatch.setattr(regelwechsel, "BEOBACHTET", ())
    monkeypatch.setattr(regelwechsel, "ZUSTAND", tmp_path / "z.json")
    monkeypatch.setattr(regelwechsel, "DB", db)
    _norm(db, "07fb68aa", 2, "Testnorm", actor="betreiber",
          norm_entschieden_von="betreiber", content="Urtext")
    regelwechsel.pruefe("s1")
    _update_norm(db, "07fb68aa", "2026-08-14T09:00:00+02:00",
                 actor=None, bedient_von=None, norm_entschieden_von="jemand-anders",
                 content="Text mit fremdem norm_entschieden_von")
    meldungen = regelwechsel.pruefe("s1")
    assert meldungen and "URHEBER OFFEN" in meldungen[0], (
        "ein abweichender Wert ist keine Betreiber-Selbstauskunft: " + repr(meldungen))


def test_herkunftswert_steht_wortgleich_in_beiden_dateien():
    """Der Wert 'gesetzgeber' steht doppelt: als _HERKUNFT_FREMD in
    haken/regelwechsel.py und als HERKUNFT_FREMD in kern/normachsen.py.
    Die Verdopplung ist Absicht -- regelwechsel laeuft bei JEDEM Prompt und
    soll dafuer nicht normachsen samt Regex importieren muessen.

    Der Preis der Verdopplung ist stilles Auseinanderlaufen: aendert jemand
    einen der beiden Werte, meldet regelwechsel jede Fremdnorm wieder als
    'URHEBER OFFEN', ohne dass irgendetwas rot wird. Genau das faengt dieser
    Test -- er ist der Grund, warum die Verdopplung tragbar ist.

    Rot-Probe: einen der beiden Werte aendern, dann faellt er."""
    import sys as _s
    from pathlib import Path as _P
    _w = _P(__file__).resolve().parent.parent
    _s.path[:0] = [str(_w / "kern"), str(_w / "haken")]
    import normachsen
    import regelwechsel
    assert regelwechsel._HERKUNFT_FREMD == normachsen.HERKUNFT_FREMD, (
        regelwechsel._HERKUNFT_FREMD, normachsen.HERKUNFT_FREMD,
        "die beiden Fassungen des Herkunftswerts sind auseinandergelaufen -- "
        "regelwechsel meldet ab jetzt jede Fremdnorm wieder als ungeklaert")


# ---------------------------------------------------------------------------
# ROT VOR GRUEN, gemessen am 2026-08-18: Waehrend einer Sitzung am Fahrtenbuch
# spielte der Melder die Norm f6db5670 ein -- "Der Python-Rechenkern ist die
# Quelle, der JavaScript-Kern zieht nach". Die gehoert zu buckeberg und hat mit
# dem Fahrtenbuch nichts zu tun; sie kam trotzdem als "gilt fuer diese Sitzung".
#
# Der Melder ist damit nicht falsch verdrahtet, sondern zu weit: Rang 1 heisst
# "global", aber der Knoten trug zugleich project='buckeberg'. Beides zusammen
# ist ein Widerspruch, den nur der Leser aufloesen kann -- und genau das kann er
# nur, wenn er ihn SIEHT.
#
# Nicht unterdrueckt wird die Meldung: Eine Weisung wegzufiltern, weil ein Feld
# nicht passt, waere der teurere Fehler. Gekennzeichnet wird sie.

def test_norm_mit_fremdem_projekt_wird_als_solche_gekennzeichnet(tmp_path, monkeypatch):
    db = _db(tmp_path)
    monkeypatch.setattr(regelwechsel, "BEOBACHTET", ())
    monkeypatch.setattr(regelwechsel, "ZUSTAND", tmp_path / "z.json")
    monkeypatch.setattr(regelwechsel, "DB", db)
    regelwechsel.pruefe("s1", projekt="fahrtenbuch")
    _norm(db, "fremd001", 1, "Der Python-Rechenkern ist die Quelle",
          norm_entschieden_von="betreiber", project="buckeberg")
    meldungen = regelwechsel.pruefe("s1", projekt="fahrtenbuch")
    assert meldungen, "die Norm blieb stumm -- sie soll gemeldet, nicht verschluckt werden"
    text = " ".join(meldungen)
    assert "buckeberg" in text, (
        "das fremde Projekt fehlt in der Meldung -- ohne es liest der Leser sie "
        "als Weisung fuer seine eigene Arbeit, genau wie am 2026-08-18 geschehen")
    assert "gilt fuer diese Sitzung" not in text, (
        "der Satz widerspricht dem Zusatz, und der Leser glaubt dem ersten")


def test_norm_mit_projekt_shared_bleibt_unveraendert(tmp_path, monkeypatch):
    """GEGENPROBE. Eine echte globale Norm darf keinen Projekt-Zusatz bekommen
    -- sonst wirkt jede Direktive wie eine fremde.

    `project_id` ist im echten Schema NOT NULL: Es gibt keine Norm OHNE
    Projekt. Der Wert fuer "gilt ueberall" heisst `shared` -- gemessen am
    2026-08-18 im Bestand, wo die Beta-Direktive und die Klientvorgaben-Regel
    genau so eingetragen sind."""
    db = _db(tmp_path)
    monkeypatch.setattr(regelwechsel, "BEOBACHTET", ())
    monkeypatch.setattr(regelwechsel, "ZUSTAND", tmp_path / "z.json")
    monkeypatch.setattr(regelwechsel, "DB", db)
    regelwechsel.pruefe("s1", projekt="fahrtenbuch")
    _norm(db, "global01", 1, "Caveman mode always on",
          norm_entschieden_von="betreiber", project="shared")
    text = " ".join(regelwechsel.pruefe("s1", projekt="fahrtenbuch"))
    assert "global01" in text
    assert "Eingetragen fuer" not in text


def test_norm_des_eigenen_projekts_bekommt_keinen_zusatz(tmp_path, monkeypatch):
    """GEGENPROBE zweite Richtung: Wer am Fahrtenbuch arbeitet, soll eine
    Fahrtenbuch-Norm ohne Beiwerk bekommen."""
    db = _db(tmp_path)
    monkeypatch.setattr(regelwechsel, "BEOBACHTET", ())
    monkeypatch.setattr(regelwechsel, "ZUSTAND", tmp_path / "z.json")
    monkeypatch.setattr(regelwechsel, "DB", db)
    regelwechsel.pruefe("s1", projekt="fahrtenbuch")
    _norm(db, "eigen001", 1, "Legacy gilt als ungeprueft",
          norm_entschieden_von="betreiber", project="fahrtenbuch")
    text = " ".join(regelwechsel.pruefe("s1", projekt="fahrtenbuch"))
    assert "eigen001" in text
    assert "Eingetragen fuer" not in text


def test_ohne_bekanntes_projekt_wird_nichts_behauptet(tmp_path, monkeypatch):
    """Kennt der Melder das eigene Projekt nicht, sagt er nichts darueber --
    eine geratene Zuordnung waere schlimmer als keine."""
    db = _db(tmp_path)
    monkeypatch.setattr(regelwechsel, "BEOBACHTET", ())
    monkeypatch.setattr(regelwechsel, "ZUSTAND", tmp_path / "z.json")
    monkeypatch.setattr(regelwechsel, "DB", db)
    regelwechsel.pruefe("s1")
    _norm(db, "fremd002", 1, "Irgendeine Norm",
          norm_entschieden_von="betreiber", project="buckeberg")
    text = " ".join(regelwechsel.pruefe("s1"))
    assert "fremd002" in text
    assert "Eingetragen fuer" not in text
