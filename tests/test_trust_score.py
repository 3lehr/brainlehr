"""Tests fuer knowledge_trust_score() (Auftrag 2026-08-07, Vergleich mit
Hermes Agent). Deckt die drei Rot-Befunde aus der Konsil-Review ab, die den
urspruenglichen Entwurf korrigierten:
  1. Sitzungs-Dedup in _recall_sessions war wirkungslos fuer Altzeilen ohne
     "session"-Feld (Fallback auf sekundengenaue ts -> keine Dedup).
  2. Der Ablehnungs-Pfad fuer Lehren feuert nie (query traegt den GRUND,
     nie die Lehren-ID) -- muss immer 0 liefern, nicht nur meist.
  3. Ein rejizierter Lehren-Schreibversuch darf nicht den verknuepften
     Knoten treffen (node_path-Fehlzuschreibung).
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


def _db(tmp_path, monkeypatch):
    db_path = tmp_path / "trust_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    monkeypatch.setattr(kms, "RECALL_LOG_PATH", tmp_path / "recall_log.jsonl")
    return db_path


def _add_node(db_path, node_id, path):
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, title, summary, source, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) VALUES (?, ?, 't', 's', 'test', 'keine_norm', 'skript:test', 'Testvorrichtung')",
        (node_id, path),
    )
    conn.commit()
    conn.close()


def _add_lesson(db_path, lesson_id, occurrences=1):
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description, occurrences) VALUES (?, 'insight', 'd', ?)",
        (lesson_id, occurrences),
    )
    conn.commit()
    conn.close()


def test_default_score_ohne_jedes_signal(tmp_path, monkeypatch):
    db_path = _db(tmp_path, monkeypatch)
    _add_node(db_path, "n1", "/x")
    r = kms.knowledge_trust_score("node", "n1")
    assert r["trust_score"] == 0.5
    assert r["exists"] is True


def test_unbekannte_ref_liefert_exists_false(tmp_path, monkeypatch):
    _db(tmp_path, monkeypatch)
    r = kms.knowledge_trust_score("node", "existiert-nicht")
    assert r["exists"] is False
    assert r["trust_score"] == 0.5  # Vorgabewert, aber unterscheidbar ueber "exists"


def test_bewusstes_lesen_hebt_score_ueber_lesion(tmp_path, monkeypatch):
    """Gegenprobe b): nie gezogener vs. oft bewusst gelesener Knoten."""
    db_path = _db(tmp_path, monkeypatch)
    _add_node(db_path, "n1", "/nie-gezogen")
    _add_node(db_path, "n2", "/oft-gelesen")
    conn = sqlite3.connect(str(db_path))
    for _ in range(8):
        conn.execute(
            "INSERT INTO access_log (node_path, action, status, timestamp) VALUES (?, 'read', 'completed', datetime('now'))",
            ("/oft-gelesen",),
        )
    conn.commit()
    conn.close()
    nie = kms.knowledge_trust_score("node", "/nie-gezogen")
    oft = kms.knowledge_trust_score("node", "/oft-gelesen")
    assert oft["trust_score"] > nie["trust_score"]
    assert nie["trust_score"] == 0.5


def test_rot_vor_fix_session_dedup_war_wirkungslos_fuer_altzeilen(tmp_path, monkeypatch):
    """Rot-Probe fuer den Konsil-Befund: 10 recall_log-Zeilen OHNE
    "session"-Feld, aber verschiedenen Sekunden-Timestamps, muessen sich auf
    EINEN Tag reduzieren (Tagesbucket-Fallback), nicht auf 10 "Sitzungen"."""
    db_path = _db(tmp_path, monkeypatch)
    _add_node(db_path, "n1", "/vielgezogen")
    log_path = tmp_path / "recall_log.jsonl"
    with open(log_path, "w", encoding="utf-8") as f:
        for i in range(10):
            f.write(json.dumps({
                "ts": f"2026-08-06T12:00:{i:02d}+00:00",
                "nodes": ["/vielgezogen"], "lessons": [],
            }) + "\n")
    sessions = kms._recall_sessions("node", "/vielgezogen", log_path)
    assert sessions == 1, f"10 Zeilen desselben Tages ohne session-Feld muessen zu 1 Sitzung werden, nicht {sessions}"


def test_lehren_ablehnungspfad_liefert_immer_null(tmp_path, monkeypatch):
    """Rot-Probe: der urspruengliche Entwurf las die Lehren-ID aus
    access_log.query bei status='rejected' -- dieser Pfad existiert im
    Code nicht (query traegt dort den Ablehnungsgrund). Muss 0 bleiben,
    auch wenn zufaellig eine Zeile mit query=<lesson_id> und
    status='rejected' existiert (kann uebers Werkzeug nie entstehen, hier
    trotzdem als Grenzfall gesetzt)."""
    db_path = _db(tmp_path, monkeypatch)
    _add_lesson(db_path, "L-abc123")
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO access_log (query, action, status, timestamp) VALUES (?, 'lesson_delete', 'rejected', datetime('now'))",
        ("L-abc123",),
    )
    conn.commit()
    conn.close()
    r = kms.knowledge_trust_score("lesson", "L-abc123")
    assert r["inputs"]["ablehnungen"] == 0


def test_rejizierter_lehren_schreibversuch_trifft_nicht_den_verknuepften_knoten(tmp_path, monkeypatch):
    """Rot-Probe: lesson_record()-Ablehnungen schreiben node_path des
    VERKNUEPFTEN Knotens -- der darf dadurch keinen Punktabzug bekommen."""
    db_path = _db(tmp_path, monkeypatch)
    _add_node(db_path, "n1", "/unbeteiligter-knoten")
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO access_log (node_path, action, status, timestamp) VALUES (?, 'lesson', 'rejected', datetime('now'))",
        ("/unbeteiligter-knoten",),
    )
    conn.commit()
    conn.close()
    r = kms.knowledge_trust_score("node", "/unbeteiligter-knoten")
    assert r["inputs"]["ablehnungen"] == 0
    assert r["trust_score"] == 0.5


def test_unabhaengige_wiederholung_hebt_lehren_score(tmp_path, monkeypatch):
    db_path = _db(tmp_path, monkeypatch)
    _add_lesson(db_path, "L-einmal", occurrences=1)
    _add_lesson(db_path, "L-mehrfach", occurrences=4)
    einmal = kms.knowledge_trust_score("lesson", "L-einmal")
    mehrfach = kms.knowledge_trust_score("lesson", "L-mehrfach")
    assert einmal["trust_score"] == 0.5
    assert mehrfach["trust_score"] > einmal["trust_score"]


def test_unbekanntes_kind_wird_abgelehnt(tmp_path, monkeypatch):
    _db(tmp_path, monkeypatch)
    r = kms.knowledge_trust_score("unsinn", "x")
    assert "error" in r


# --- Wirkungssignal (Plan_SELBSTLERNEN_2026-08-07 Schritt 2) ---------------

def _recall_line(tmp_path, session, ts, node=None, lesson=None):
    log_path = tmp_path / "recall_log.jsonl"
    entry = {"ts": ts, "session": session,
             "nodes": [node] if node else [], "lessons": [lesson] if lesson else []}
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _access(db_path, node_path, action, session, ts, status="completed"):
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO access_log (node_path, action, status, session, timestamp) "
        "VALUES (?, ?, ?, ?, ?)",
        (node_path, action, status, session, ts),
    )
    conn.commit()
    conn.close()


def test_wirkung_ignoriert_ohne_bestandsweites_genutzt_senkt_score_nicht(tmp_path, monkeypatch):
    """Auftrag 2026-08-07 (Nachtrag): solange 'genutzt' im GESAMTEN Bestand
    kein einziges Mal beobachtet wurde, ist 'ignoriert' kein Signal, sondern
    eine Strafe fuer alle (das Tor war zuvor faktisch immer zu, weil der
    Session-Formatfehler 'genutzt' strukturell unerreichbar machte -- siehe
    wirkung.py). Score bleibt beim Vorgabewert."""
    db_path = _db(tmp_path, monkeypatch)
    _add_node(db_path, "n1", "/x/ignoriert")
    vorher = kms.knowledge_trust_score("node", "/x/ignoriert")["trust_score"]
    assert vorher == 0.5, f"rot-Ausgangswert: {vorher}"
    for i, s in enumerate(("s1", "s2", "s3")):
        _recall_line(tmp_path, s, f"2026-08-07T10:0{i}:00+00:00", node="/x/ignoriert")
    nachher = kms.knowledge_trust_score("node", "/x/ignoriert")
    assert nachher["inputs"]["wirkung_ignoriert"] == 3, nachher
    # >= statt ==: die 3 Recall-Zeilen zaehlen auch als recall_sessions
    # (eigener, unabhaengiger Bonus-Term) -- der hebt den Score unabhaengig
    # vom ignoriert-Abzug. Entscheidend ist nur, dass der ignoriert-Abzug
    # selbst nicht mehr greift (siehe Gegenprobe unten: mit bestandsweitem
    # genutzt sinkt derselbe Aufbau UNTER vorher, trotz desselben Bonus).
    assert nachher["trust_score"] >= vorher, (
        f"kein genutzt im Bestand -> ignoriert darf nicht senken: "
        f"vorher={vorher} nachher={nachher['trust_score']}"
    )


def test_wirkung_ignoriert_senkt_score_wenn_bestandsweit_genutzt_existiert(tmp_path, monkeypatch):
    """ROT VOR GRUEN (Gegenrichtung): sobald IRGENDWO im Bestand ein
    'genutzt' existiert -- hier bei einem ANDEREN Knoten --, oeffnet sich
    das Tor, und 'ignoriert' senkt wieder, wie vor dem Nachtrag."""
    db_path = _db(tmp_path, monkeypatch)
    _add_node(db_path, "n1", "/x/genutzt-anderswo")
    _add_node(db_path, "n2", "/x/ignoriert-hier")
    _recall_line(tmp_path, "sg", "2026-08-07T09:00:00+00:00", node="/x/genutzt-anderswo")
    _access(db_path, "/x/genutzt-anderswo", "read", "sg", "2026-08-07T09:00:05Z")

    vorher = kms.knowledge_trust_score("node", "/x/ignoriert-hier")["trust_score"]
    assert vorher == 0.5, f"rot-Ausgangswert: {vorher}"
    for i, s in enumerate(("s1", "s2", "s3")):
        _recall_line(tmp_path, s, f"2026-08-07T10:0{i}:00+00:00", node="/x/ignoriert-hier")
    nachher = kms.knowledge_trust_score("node", "/x/ignoriert-hier")
    assert nachher["inputs"]["wirkung_ignoriert"] == 3, nachher
    assert nachher["trust_score"] < vorher, (
        f"genutzt existiert bestandsweit (anderer Knoten) -> ignoriert muss hier senken: "
        f"vorher={vorher} nachher={nachher['trust_score']}"
    )
    print(f"rot={vorher} gruen={nachher['trust_score']}")


def test_wirkung_genutzt_hebt_score_gegenprobe(tmp_path, monkeypatch):
    """GEGENPROBE: dreimal eingespielt, dreimal danach gelesen -- muss
    steigen (Gegenrichtung zum Ignoriert-Fall)."""
    db_path = _db(tmp_path, monkeypatch)
    _add_node(db_path, "n1", "/x/genutzt")
    vorher = kms.knowledge_trust_score("node", "/x/genutzt")["trust_score"]
    for i, s in enumerate(("s1", "s2", "s3")):
        recall_ts = f"2026-08-07T10:0{i}:00+00:00"
        _recall_line(tmp_path, s, recall_ts, node="/x/genutzt")
        _access(db_path, "/x/genutzt", "read", s, f"2026-08-07T10:0{i}:05Z")
    nachher = kms.knowledge_trust_score("node", "/x/genutzt")
    assert nachher["inputs"]["wirkung_genutzt"] == 3, nachher
    assert nachher["trust_score"] > vorher, (
        f"3x genutzt muss steigen: vorher={vorher} nachher={nachher['trust_score']}"
    )


def test_wirkung_negativfall_ohne_daten_weder_bonus_noch_strafe(tmp_path, monkeypatch):
    """NEGATIVFALL: kein Recall-Log/keine Wirkungsdaten -> Score identisch
    zu einem Eintrag mit denselben Alt-Signalen (bewusstes Lesen), aber vor
    Einfuehrung des Wirkungssignals. Rueckwirkungs-Grenze aus dem Auftrag:
    ein Eintrag ohne jede Wirkungsmessung darf nicht schlechter dastehen."""
    db_path = _db(tmp_path, monkeypatch)
    _add_node(db_path, "n1", "/x/unbewertet")
    _access(db_path, "/x/unbewertet", "read", None, "2026-08-01T00:00:00Z")
    r = kms.knowledge_trust_score("node", "/x/unbewertet")
    assert r["inputs"]["wirkung_genutzt"] == 0
    assert r["inputs"]["wirkung_ignoriert"] == 0
    assert r["inputs"]["wirkung_widerlegt"] == 0
    # Score = Vorgabewert 0.5 + reiner Signal-1-Term, exakt wie vor diesem
    # Auftrag (Wirkungsterme tragen bei 0 nichts bei, tanh(0)=0).
    import math
    erwartet = round(0.5 + 0.30 * math.tanh(1 / 5), 4)
    assert r["trust_score"] == erwartet, r


def test_wirkung_widerlegt_schlaegt_genutzt_grenzwert(tmp_path, monkeypatch):
    """GRENZWERT: widerlegt muss genutzt in derselben Sitzung schlagen --
    Vorrang steckt bereits in wirkung.outcome() (widerlegt zuerst geprueft),
    hier belegt, dass sich das auch im trust_score-Wert fortsetzt: ein
    Knoten, der in derselben Sitzung gelesen UND zurueckgezogen wurde,
    muss als widerlegt zaehlen (score sinkt), nicht als genutzt (score
    steigt)."""
    db_path = _db(tmp_path, monkeypatch)
    _add_node(db_path, "n1", "/x/beides")
    vorher = kms.knowledge_trust_score("node", "/x/beides")["trust_score"]
    _recall_line(tmp_path, "s1", "2026-08-07T10:00:00+00:00", node="/x/beides")
    _access(db_path, "/x/beides", "read", "s1", "2026-08-07T10:00:05Z")
    _access(db_path, "/x/beides", "zurueckziehen", "s1", "2026-08-07T10:00:06Z")
    nachher = kms.knowledge_trust_score("node", "/x/beides")
    assert nachher["inputs"]["wirkung_widerlegt"] == 1, nachher
    assert nachher["inputs"]["wirkung_genutzt"] == 0, nachher
    assert nachher["trust_score"] < vorher, nachher
