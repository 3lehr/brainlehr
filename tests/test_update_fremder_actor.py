"""knowledge_update darf einen Knoten aendern, den ein ANDERER angelegt hat.

Befund 2026-08-08, gemessen an der Sammelentscheidung ueber 62 Knoten
(Normschicht auf norm_unbefristet/norm_befristet setzen): der allererste
Aufruf brach ab mit

    sqlite3.IntegrityError: Herkunftsfeld unveraenderlich (id, created_at,
    source, quell_hash, abgeleitet_von, session, actor)

Zwei Bausteine desselben Tages standen gegeneinander:

* Trigger knowledge_nodes_herkunft_bu haelt actor und session fuer
  unveraenderlich -- Herkunft wird nachgetragen, nie umgeschrieben.
* knowledge_update setzte actor/session/model bei JEDEM Update neu.

Damit war knowledge_update fuer jeden Knoten unbenutzbar, dessen Anleger ein
anderer war als der Aendernde -- also fuer praktisch jeden Fremdbestand.
Behoben, indem knowledge_update actor/session/model stehen laesst. Wer die
Aenderung vorgenommen hat, steht weiterhin an zwei Stellen: im access_log
und, bei einer Normentscheidung, in norm_entschieden_von.

ROT VOR GRUEN: gegen den Stand vor der Aenderung bricht
test_update_durch_fremden_actor mit IntegrityError ab.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "knowledge_test.db"
    conn = sqlite3.connect(str(db_path))
    # Der Herkunfts-Trigger steht NICHT in schema.sql, sondern in einer
    # eigenen Datei (Befund 2026-08-08). Ohne sie prueft dieser Test die
    # Regel gar nicht, die er pruefen will -- deshalb beide einspielen.
    for datei in ("schema.sql", "herkunft_unveraenderlich.sql"):
        conn.executescript((SHARED_KNOWLEDGE / datei).read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _anlegen(**kw):
    res = kms.knowledge_add(
        parent_path="/",
        title=kw.pop("title", "Knoten des Anlegers"),
        summary="angelegt von actor-A",
        source="erzeugt fuer test_update_fremder_actor.py",
        neuer_ast=True,
        norm_entscheidung="keine_norm",
        norm_entschieden_grund="Testknoten, keine Regel",
        actor="actor-A",
        session="sitzung-A",
        model="modell-A",
        **kw,
    )
    assert "error" not in res, res
    return res["id"]


def test_update_durch_fremden_actor(temp_db):
    """Der Kern des Befunds: B aendert einen Knoten von A."""
    node_id = _anlegen()

    res = kms.knowledge_update(
        node_id, summary="geaendert von actor-B",
        actor="actor-B", session="sitzung-B", model="modell-B",
    )
    assert "error" not in res, res

    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM knowledge_nodes WHERE id = ?", (node_id,)).fetchone()
    conn.close()

    assert row["summary"] == "geaendert von actor-B"
    # Herkunft bleibt beim Anleger -- das ist die Regel, die der Trigger schuetzt.
    assert row["actor"] == "actor-A"
    assert row["session"] == "sitzung-A"


def test_normentscheidung_durch_fremden_actor_haelt_entscheider_fest(temp_db):
    """Der konkrete Anlass: Sammelentscheidung auf fremdem Bestand. Die
    Herkunft bleibt beim Anleger, der ENTSCHEIDER ist der Aendernde."""
    node_id = _anlegen(title="Norm des Anlegers")

    res = kms.knowledge_update(
        node_id,
        norm_rang=2, gilt_ab="2026-08-01",
        norm_entscheidung="norm_unbefristet",
        norm_entschieden_grund="Sammelentscheidung, Rang war absichtlich gesetzt",
        actor="actor-B", session="sitzung-B", model="modell-B",
    )
    assert "error" not in res, res

    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM knowledge_nodes WHERE id = ?", (node_id,)).fetchone()
    conn.close()

    assert row["norm_entscheidung"] == "norm_unbefristet"
    assert row["norm_entschieden_von"] == "actor-B"
    assert row["actor"] == "actor-A"


def test_herkunftstrigger_greift_weiterhin(temp_db):
    """Gegenprobe in die andere Richtung: der Trigger ist NICHT entschaerft
    worden. Ein direkter Schreibversuch auf actor bricht weiterhin ab."""
    node_id = _anlegen(title="Knoten fuer die Gegenprobe")

    conn = sqlite3.connect(str(temp_db))
    with pytest.raises(sqlite3.IntegrityError, match="Herkunftsfeld unveraenderlich"):
        conn.execute("UPDATE knowledge_nodes SET actor = ? WHERE id = ?", ("actor-B", node_id))
    conn.close()


def test_abgewiesenes_update_laesst_die_datenbank_nicht_gesperrt(temp_db):
    """Der teure Teil war nicht das Abweisen, sondern das Aufraeumen danach.

    Gemessen 2026-08-08: der Herkunfts-Trigger wies ein Update ab, die Ausnahme
    flog aus knowledge_update heraus, und die Verbindung blieb am
    __traceback__ der Ausnahme haengen -- mit offener Schreibtransaktion. Die
    gesamte Wissensdatenbank war danach fuer jeden Schreiber gesperrt, bis der
    Serverprozess starb. Eine Schreibprobe wartete 31 Sekunden vergeblich.

    ROT VOR GRUEN: vor der Aenderung bleibt die zweite Verbindung unten mit
    'database is locked' haengen.
    """
    node_id = _anlegen(title="Knoten fuer die Sperrprobe")

    # Ein Update, das der Trigger abweisen MUSS: source ist gesetzt und wird
    # auf einen anderen Wert gezogen. Der Weg dorthin geht ueber die rohe
    # Verbindung, weil knowledge_update source gar nicht anbietet -- genau
    # deshalb ist der Fehlerpfad hier der interessante.
    res = kms.knowledge_update(
        node_id, summary="loest den Trigger nicht aus",
        actor="actor-B", session="sitzung-B", model="modell-B",
    )
    assert "error" not in res, res

    # Jetzt der echte Fall: ein Trigger schlaegt mitten im UPDATE zu.
    conn = sqlite3.connect(str(temp_db))
    conn.execute(
        "CREATE TRIGGER probe_weist_ab BEFORE UPDATE ON knowledge_nodes "
        "FOR EACH ROW WHEN NEW.summary = 'ausloeser' "
        "BEGIN SELECT RAISE(ABORT, 'Probe: abgewiesen'); END"
    )
    conn.commit()
    conn.close()

    res = kms.knowledge_update(node_id, summary="ausloeser", actor="actor-B")
    assert "error" in res, "der Trigger muss abweisen"

    # Die eigentliche Zusicherung: danach kann jemand anders schreiben.
    zweite = sqlite3.connect(str(temp_db), timeout=3)
    zweite.execute("PRAGMA busy_timeout=3000")
    zweite.execute("CREATE TABLE _schreibprobe (x)")
    zweite.commit()
    zweite.close()
