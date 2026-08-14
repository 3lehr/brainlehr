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
    conn.commit(); conn.close()
    return p


def _norm(db, node_id, rang, titel, wann="2026-08-11T09:00:00+02:00",
          actor=None, bedient_von=None, content=None,
          norm_entschieden_von="test"):
    import sqlite3
    conn = sqlite3.connect(str(db))
    try:
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, parent_path, title, summary, "
            "content, source, norm_rang, gilt_ab, norm_entscheidung, "
            "norm_entschieden_grund, norm_entschieden_von, norm_entschieden_am, "
            "actor, bedient_von, created_at, updated_at) "
            "VALUES (?,?,'/',?,?,?,?,?,'2026-08-11','norm_unbefristet','Testnorm.',"
            "?,'2026-08-11',?,?,?,?)",
            (node_id, f"/probe/{node_id}", titel, "Zusammenfassung.", content,
             "Test test_regelwechsel.py", rang, norm_entschieden_von, actor,
             bedient_von, wann, wann))
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
