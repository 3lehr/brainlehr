"""Belegt, dass messungen/kandidatendiagnose.py den AKTIVEN Abrufweg
(haken/suchpfad_abruf.kandidaten) misst, statt ihn mit
knowledge_mcp_server._fuse_with_keyword_floor() nachzubauen.

Befund vor dieser Datei: final_ids/in_kandidatenliste kamen aus dem alten,
am 2026-08-09 in suchpfad_abruf ausdruecklich abgeschafften Stichwort-Sockel
(_fuse_with_keyword_floor) -- einer anderen Formel als der Betriebsweg.
Fall 8dc84938 zeigte die Folge: rang_verschmolzen 1, in_kandidatenliste
False, weil der Sockel diesen Platz nicht vergab.

Drei Tests:
1) test_diagnose_liefert_dieselbe_liste_wie_der_echte_abrufweg -- Rot-Probe:
   wird final_ids wie vor der Reparatur ueber _fuse_with_keyword_floor
   berechnet, weicht die Liste vom echten Weg ab UND der Test nennt die
   abweichenden IDs (nicht nur "ungleich").
2) test_fall_8dc84938_jetzt_in_liste -- der belegte Einzelfall.
3) test_negativfall_bleibt_nicht_in_liste -- ohne ihn wuerde auch eine
   Diagnose bestehen, die immer True meldet.
"""
from __future__ import annotations

import sqlite3
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen", "messungen")]

import pytest  # noqa: E402

import embeddings  # noqa: E402
import ort  # noqa: E402
import suchpfad_abruf  # noqa: E402
from kandidatendiagnose import MAX_RESULTS, diagnose, ziel_ref  # noqa: E402
from knowledge_mcp_server import _fuse_with_keyword_floor  # noqa: E402

ZIEL_PFAD = "/methodik/direktiven/keine-entwicklerinformation-in-der-oberflaeche-systemweit"
ZIEL_TASK = (
    "Ein Kunde möchte seine persönlichen Informationen im Profil aktualisieren, doch der "
    "Vorgang wird abgebrochen. Die Meldung auf dem Display darf keine Details zu den "
    "technischen Hintergründen preisgeben und sollte den Nutzer stattdessen lediglich dazu "
    "anweisen, die Eingabe in einigen Minuten erneut zu versuchen."
)


def _ollama_erreichbar() -> bool:
    try:
        return bool(embeddings.embed_text("Erreichbarkeitspruefung"))
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _Path(ort.DB).exists(), reason="brainlehr.db fehlt auf diesem Rechner")


@pytest.fixture(scope="module")
def conn():
    c = sqlite3.connect(f"file:{ort.DB}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


@pytest.fixture(scope="module")
def vec():
    if not _ollama_erreichbar():
        pytest.skip("Ollama nicht erreichbar -- Bedeutungskanal nicht pruefbar")
    return embeddings.embed_text(ZIEL_TASK)


# Beide folgenden Faelle haengen daran, dass der Zielknoten 8dc84938 unter den
# ersten MAX_RESULTS=5 steht. Am 2026-08-14 gemessen: Rang 21,
# in_kandidatenliste False. Das ist KEIN Testfehler und keine Bestandsdrift zum
# Wegwischen, sondern ein Abrufbefund -- ausgerechnet der Knoten, an dem die
# Reparatur vom 2026-08-09 belegt wurde, wird heute nicht mehr gefunden
# (Bestand seither auf 2197 Knoten gewachsen). Der Wert wird deshalb NICHT
# nachgezogen: ein auf Rang 21 umgeschriebener Test waere gruen und wertlos.
# Gehoert zur Abrufguete (S12, groesserer Korpus, Knoten 0e6adb6c), nicht zur
# Testpflege. strict=True, damit es auffaellt, sobald der Abruf ihn wiederfindet.
# NACHTRAG 2026-08-16, nach der Umstellung von _fuse_with_keyword_floor() auf
# embeddings.fuse_semantic_led(): Der Zielknoten steht jetzt auf Rang 23 (vorher
# 21), in_kandidatenliste weiterhin False -- dieser Einzelfall ist NICHT geheilt.
# Im Mittel wirkt die Umstellung dagegen deutlich: 37/40 statt 34/40, einsprachig
# 5/35 statt 0/35, Leitfall trifft wieder
# (runs/kanalguete_nach_verdrahtung_2026-08-16.json). Der Marker bleibt deshalb
# an test_fall_8dc84938_jetzt_in_liste. Er faellt nur bei
# test_diagnose_liefert_dieselbe_liste_wie_der_echte_abrufweg weg: dieser Test
# hing an der falschen Bedingung -- er prueft, ob Diagnose und echter Abrufweg
# DIESELBE Liste liefern, nicht ob das Ziel darin steht. Seit der Umstellung tun
# sie das, und weil der Marker strict war, ist es aufgefallen statt still zu
# bleiben.
#
# NACHTRAG 2026-08-21: genau das ist eingetreten, wofuer strict=True gesetzt
# wurde ("damit es auffaellt, sobald der Abruf ihn wiederfindet"). Gemessen
# gegen den echten Bestand (kein Codepfad in kandidatendiagnose.py/
# suchpfad_abruf.py/embeddings.py/knowledge_mcp_server.py in dieser Sitzung
# geaendert -- diff gegen 42c32f7d leer): Zielknoten 8dc84938 steht auf
# Rang 1, in_kandidatenliste True. Ursache ist Bestandswachstum, nicht ein
# Commit dieser Sitzung: eine kleine Test-DB (372 KB, ohne den echten Bestand)
# zeigt weiterhin das alte Bild, die echte brainlehr.db (177 MB) nicht mehr.
# Der xfail-Marker ist damit erledigt und wird entfernt, statt ihn XPASS
# melden zu lassen -- ein weiterhin xfail-markierter, tatsaechlich
# bestehender Fall waere die stille Variante desselben Fehlers.
# Marker entfernt (s. Nachtrag 2026-08-21) -- der Fall ist geheilt, kein
# xfail mehr noetig.


def test_diagnose_liefert_dieselbe_liste_wie_der_echte_abrufweg(conn, vec):
    ref = ziel_ref(conn, "node", ZIEL_PFAD)
    assert ref is not None, "Fixtur fehlt: Ziel-Knoten nicht im Bestand"

    node_rows, lesson_rows = suchpfad_abruf.kandidaten(conn, ZIEL_TASK, vec, MAX_RESULTS)
    echt = [r["id"] for r in node_rows] + [r["id"] for r in lesson_rows]

    d = diagnose(conn, ZIEL_TASK, "node", ref, vec)
    assert d["final_ids"] == echt, (
        f"Diagnose weicht vom echten Abrufweg ab: echt={echt} diagnose={d['final_ids']}")

    # Rot-Probe: der Weg vor der Reparatur (_fuse_with_keyword_floor) haette
    # eine ANDERE Liste geliefert -- namentlich verschieden, nicht nur ungleich.
    from knowledge_mcp_server import _embedding_ranking, _or_query
    from gattung_filter import SQL_ARBEITSBESTAND_NUR

    fts_query = _or_query(ZIEL_TASK)
    node_ids = [r["id"] for r in conn.execute(
        "SELECT n.id FROM knowledge_fts f JOIN knowledge_nodes n ON n.rowid = f.rowid "
        f"WHERE knowledge_fts MATCH ? AND n.zurueckgezogen = 0 {SQL_ARBEITSBESTAND_NUR} "
        "ORDER BY rank", (fts_query,))]
    lesson_ids = [r["id"] for r in conn.execute(
        "SELECT l.id FROM lessons_fts f JOIN lessons_learned l ON l.rowid = f.rowid "
        "WHERE lessons_fts MATCH ? AND l.status != 'resolved' ORDER BY rank", (fts_query,))]
    keyword_ordered = embeddings.rrf_fuse(node_ids, lesson_ids, embedding_weight=1.0)
    emb_node_ids = _embedding_ranking(conn, "node", vec, None)
    emb_lesson_ids = _embedding_ranking(conn, "lesson", vec, None)
    embedding_ordered = embeddings.rrf_fuse(emb_node_ids, emb_lesson_ids, embedding_weight=1.0)
    alt_final_ids = _fuse_with_keyword_floor(keyword_ordered, embedding_ordered, MAX_RESULTS)

    assert alt_final_ids != echt, (
        "Rot-Probe wirkungslos: der alte Sockel-Pfad liefert zufaellig dieselbe Liste "
        f"wie der echte Weg ({echt}) -- Testfall taugt nicht als Regressionswaechter"
    )
    abweichung = set(alt_final_ids) ^ set(echt)
    assert ref in abweichung, (
        f"Rot-Probe soll gerade am Ziel {ref} abweichen: alt={alt_final_ids} echt={echt}"
    )


def test_fall_8dc84938_jetzt_in_liste(conn, vec):
    ref = ziel_ref(conn, "node", ZIEL_PFAD)
    assert ref == "8dc84938"
    d = diagnose(conn, ZIEL_TASK, "node", ref, vec)
    assert d["rang_verschmolzen"] == 1, f"erwartet Rang 1, war {d['rang_verschmolzen']}"
    assert d["in_kandidatenliste"] is True, (
        "Fall 8dc84938 muss nach der Reparatur in der Kandidatenliste stehen")


def test_negativfall_bleibt_nicht_in_liste(conn):
    ref = ziel_ref(conn, "node", ZIEL_PFAD)
    nonsens = "qwfpqwfpblorx zvxjkq wibbnfrx yprxxq"
    d = diagnose(conn, nonsens, "node", ref, None)
    assert d["in_kandidatenliste"] is False, "Nonsens-Anfrage darf das Ziel nicht finden"
    assert d["fts_treffer_knoten"] == 0
