"""Rot-vor-gruen fuer den inkrementellen Umbau von build_embeddings.py
(Auftrag 2026-08-07): der Lauf schrieb bisher per INSERT OR REPLACE ueber
ALLE Knoten/Lehren, egal ob sich am Text etwas geaendert hatte -- gemessen
453,8s fuer einen Lauf ohne jede Aenderung am Bestand. Fix: text_checksum-
Spalte (sha256 ueber den eingebetteten Text), ueberspringt eine Zeile, wenn
Modell UND Pruefsumme zur vorhandenen knowledge_embeddings-Zeile passen.

Diese Tests nutzen eine synthetische tmp-DB (schema.sql + Fixture-Zeilen)
statt der echten ~3000-Zeilen-DB -- deterministisch und schnell, misst
dieselbe Logik wie ein echter Lauf. Der reale Laufzeit-Beleg (rot: 453,8s-
Klasse, gruen: kurzer Folgelauf) steht in der Commit-Nachricht/STAND.md,
nicht hier -- ein Test darf nicht 8 Minuten dauern.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))
sys.path.insert(0, str(SHARED_KNOWLEDGE / "kern"))

import build_embeddings as be  # noqa: E402


FAKE_VEC = [0.1, 0.2, 0.3]


@pytest.fixture()
def db_path(tmp_path, monkeypatch):
    """Frische DB aus schema.sql (Trigger + embed_model-Seed 'bge-m3' aktiv),
    ein Knoten + eine Lehre. schema.sql traegt (noch) keine text_checksum-
    Spalte -- genau der Bestandsfall, den die Selbstheilung in main()
    abdecken muss."""
    path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(path))
    conn.executescript(schema)
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, source, level, norm_entscheidung, "
        "norm_entschieden_von, norm_entschieden_grund) "
        "VALUES ('n1', '/n1', 'shared', 'Titel', 'Zusammenfassung', 'Inhalt', 'test', 0, 'keine_norm', 'skript:test', 'Testvorrichtung')"
    )
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description, projects, status) "
        "VALUES ('l1', 'insight', 'Beschreibung', '[\"shared\"]', 'active')"
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(be, "DB_PATH", path)
    monkeypatch.setattr(be, "FORCE", False)
    monkeypatch.setattr(be.embeddings, "embed_text", lambda text, **kw: list(FAKE_VEC))
    monkeypatch.setattr(be, "_embed_batch", lambda texts, **kw: [list(FAKE_VEC) for _ in texts])
    return path


def _run():
    return be.main()


def _emb_rows(path):
    conn = sqlite3.connect(str(path))
    rows = conn.execute(
        "SELECT kind, ref_id, project_id, model, text_checksum, updated_at FROM knowledge_embeddings ORDER BY kind, ref_id"
    ).fetchall()
    conn.close()
    return rows


# --- Punkt 3: zweiter Lauf ohne Aenderung -> beide uebersprungen -----------

def test_zweiter_lauf_ohne_aenderung_ueberspringt_beide(db_path, capsys):
    assert _run() == 0
    out1 = capsys.readouterr().out
    assert "Neu gerechnet: 2, uebersprungen (unveraendert): 0" in out1
    rows_after_first = _emb_rows(db_path)
    assert len(rows_after_first) == 2
    assert all(r[4] for r in rows_after_first), "text_checksum haette gesetzt sein muessen"

    assert _run() == 0
    out2 = capsys.readouterr().out
    assert "Neu gerechnet: 0, uebersprungen (unveraendert): 2" in out2
    assert _emb_rows(db_path) == rows_after_first, "unveraenderter Lauf darf keine Zeile anfassen"


# --- Punkt 3b: EINEN Eintrag aendern -> genau dieser wird neu gerechnet ----

def test_ein_geaenderter_eintrag_nur_dieser_wird_neu_gerechnet(db_path, capsys):
    _run()
    capsys.readouterr()
    before = {(r[0], r[1]): r for r in _emb_rows(db_path)}

    conn = sqlite3.connect(str(db_path))
    conn.execute("UPDATE knowledge_nodes SET summary = 'Geaenderte Zusammenfassung' WHERE id='n1'")
    conn.commit()
    conn.close()

    assert _run() == 0
    out = capsys.readouterr().out
    assert "Neu gerechnet: 1, uebersprungen (unveraendert): 1" in out

    after = {(r[0], r[1]): r for r in _emb_rows(db_path)}
    assert after[("node", "n1")] != before[("node", "n1")], "geaenderter Knoten haette neu gerechnet werden muessen"
    assert after[("lesson", "l1")] == before[("lesson", "l1")], "unveraenderte Lehre wurde faelschlich angefasst"


# --- Punkt 4: Modellwechsel in knowledge_config -> alles neu rechnen -------

def test_modellwechsel_erzwingt_volle_neuberechnung(db_path, monkeypatch, capsys):
    _run()
    capsys.readouterr()

    conn = sqlite3.connect(str(db_path))
    conn.execute("UPDATE knowledge_config SET value='ein-neues-modell' WHERE key='embed_model'")
    conn.commit()
    conn.close()
    monkeypatch.setattr(be.embeddings, "DEFAULT_EMBED_MODEL", "ein-neues-modell")

    assert _run() == 0
    out = capsys.readouterr().out
    assert "Neu gerechnet: 2, uebersprungen (unveraendert): 0" in out
    rows = _emb_rows(db_path)
    assert all(r[3] == "ein-neues-modell" for r in rows)


# --- Punkt: --force rechnet trotz passender Pruefsumme neu -----------------

def test_force_flag_rechnet_trotz_unveraendertem_text_neu(db_path, monkeypatch, capsys):
    _run()
    capsys.readouterr()
    monkeypatch.setattr(be, "FORCE", True)

    assert _run() == 0
    out = capsys.readouterr().out
    assert "Neu gerechnet: 2, uebersprungen (unveraendert): 0" in out


# --- Punkt 5: Modellsperre-Trigger weist Fremdmodell weiterhin ab ----------

def test_modell_trigger_weist_fremdmodell_weiterhin_ab(db_path):
    _run()  # legt text_checksum-Spalte selbstheilend an
    conn = sqlite3.connect(str(db_path))
    with pytest.raises(sqlite3.IntegrityError, match="weicht vom gueltigen Modell"):
        conn.execute(
            "INSERT INTO knowledge_embeddings (kind, ref_id, project_id, model, dim, vector, updated_at, text_checksum) "
            "VALUES ('node', 'fremd', 'shared', 'altes-modell', 3, X'000000', '2026-08-07T00:00:00+02:00', 'x')"
        )
    conn.close()


# --- Stapel-Einbettung: ein HTTP-Aufruf statt einem je Text ---------------

def test_batch_wird_in_einem_aufruf_mit_allen_pending_texten_aufgerufen(db_path, monkeypatch, capsys):
    calls: list[list[str]] = []

    def spy(texts, **kw):
        calls.append(list(texts))
        return [list(FAKE_VEC) for _ in texts]

    monkeypatch.setattr(be, "_embed_batch", spy)
    assert _run() == 0
    capsys.readouterr()
    # 1 Knoten + 1 Lehre, beide unter BATCH_SIZE -> je Kategorie EIN Aufruf
    # mit allen ihren pending Texten, nicht einer je Text.
    assert len(calls) == 2, calls
    assert all(len(c) == 1 for c in calls), calls


# --- Stapel-Ausfall: kein stiller Vektorverlust, Fallback auf Einzelpfad ---

def test_batch_ausfall_verliert_keine_vektoren_faellt_auf_einzelpfad_zurueck(monkeypatch):
    """_embed_batch() selbst (nicht gemockt) gegen eine urlopen-Attrappe, die
    den GANZEN Stapel scheitern laesst (liefert weniger Vektoren als
    gesendet) -- Fallback muss jeden Text einzeln ueber embeddings.embed_text
    nachfahren, damit kein Vektor still verlorengeht."""
    texts = ["a", "b", "c"]
    single_calls: list[str] = []

    def fake_embed_text(text, **kw):
        single_calls.append(text)
        return [0.9, 0.9]

    def fake_urlopen(req, timeout=None):
        raise be.urllib.error.URLError("Stapel kaputt, absichtlich")

    monkeypatch.setattr(be.embeddings, "embed_text", fake_embed_text)
    monkeypatch.setattr(be.urllib.request, "urlopen", fake_urlopen)

    result = be._embed_batch(texts, timeout=5.0)

    assert result == [[0.9, 0.9]] * 3, "Fallback haette jeden Text einzeln liefern muessen, kein Verlust"
    assert single_calls == texts, "jeder Text des kaputten Stapels muss einzeln nachgefahren werden"


# --- Selbstheilung: text_checksum-Spalte fehlt vorher, existiert danach ---

def test_text_checksum_spalte_wird_selbstheilend_angelegt(db_path):
    # Vorbedingung SELBST herstellen statt sie von schema.sql zu erben:
    # Seit dem 2026-08-14 (Aufgabe 110) fuehrt schema.sql text_checksum, weil
    # eine unvollstaendige SOLL-Datei den Schemamelder mit einer Abweichung
    # beschaeftigte, die keine war. Die Selbstheilung bleibt trotzdem noetig --
    # sie gilt gewachsenen Bestaenden aus der Zeit davor, und genau die sind
    # der Fall, den eine Erstinstallation NIE zeigt.
    conn = sqlite3.connect(str(db_path))
    if "text_checksum" in {r[1] for r in conn.execute("PRAGMA table_info(knowledge_embeddings)")}:
        conn.execute("ALTER TABLE knowledge_embeddings DROP COLUMN text_checksum")
        conn.commit()
    cols_before = {r[1] for r in conn.execute("PRAGMA table_info(knowledge_embeddings)")}
    conn.close()
    assert "text_checksum" not in cols_before, "Testaufbau: alter Bestand ohne die Spalte"

    _run()

    conn = sqlite3.connect(str(db_path))
    cols_after = {r[1] for r in conn.execute("PRAGMA table_info(knowledge_embeddings)")}
    conn.close()
    assert "text_checksum" in cols_after
