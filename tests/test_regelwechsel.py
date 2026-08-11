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


def _norm(db, node_id, rang, titel, wann="2026-08-11T09:00:00+02:00"):
    import sqlite3
    conn = sqlite3.connect(str(db))
    try:
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, parent_path, title, summary, "
            "source, norm_rang, gilt_ab, norm_entscheidung, norm_entschieden_grund, "
            "norm_entschieden_von, norm_entschieden_am, created_at, updated_at) "
            "VALUES (?,?,'/',?,?,?,?,'2026-08-11','norm_unbefristet','Testnorm.',"
            "'test','2026-08-11',?,?)",
            (node_id, f"/probe/{node_id}", titel, "Zusammenfassung.",
             "Test test_regelwechsel.py", rang, wann, wann))
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
