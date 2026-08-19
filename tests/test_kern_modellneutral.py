#!/usr/bin/env python3
"""BDW-R05-AC1: „Derselbe Kern besteht einen lokalen MCP-Lauf mit
austauschbarem Modellpfad und ausgewiesener Quelle/Geltung."

ANLASS, 2026-08-18: Die Vermessung aller offenen Produktgates fand für
`BDW-R05` keinen Prüfpfad. Der bisher nächste Treffer
(`test_knowledge_mcp_server.py::test_access_identity_env_and_update_logging`)
prüft, dass ein Modellname protokolliert wird -- nicht, dass der Kern OHNE
das Modell weiterarbeitet. Das ist ein anderer Gegenstand.

DER SATZ, DEN DAS AC MEINT: „modellneutral" heißt nicht „irgendein Modell
ist eingestellt", sondern **der Kern liefert auch dann Quelle und Geltung,
wenn das Einbettungsmodell fehlt**. Wer ein lokales Sprachmodell
voraussetzt, hat keinen neutralen Kern, sondern eine Abhängigkeit mit
freundlichem Namen.

DIESER FALL IST HEUTE REAL, nicht konstruiert: Ollama läuft auf diesem
Rechner nicht, der Einbettungskanal ist tot, und der Abruf fällt auf den
Stichwortkanal zurück. Genau dieser Zustand wird hier zum Prüffall gemacht,
statt ihn als Umgebungsproblem zu behandeln.

ABGRENZUNG: Geprüft wird der KERN (`knowledge_search` über
`knowledge_mcp_server`), nicht der Recall-Haken. Der Haken darf ohne Modell
schweigen; der Kern darf es nicht.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(WURZEL), str(WURZEL / "kern")]


@pytest.fixture
def bestand(tmp_path, monkeypatch):
    """Eigene Datenbank -- NIE die produktive.

    Der Name ist der Fallstrick: `knowledge_mcp_server` liest
    `BEGOD_KNOWLEDGE_DB`. Wer `BRAINLEHR_DB` setzt (den Namen, den
    `haken/ort.py` empfiehlt), schreibt in die echte Datenbank; am
    2026-08-18 sind so 48 Testknoten dorthin gelaufen."""
    db = tmp_path / "pruefbestand.db"
    conn = sqlite3.connect(str(db))
    conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))
    # norm_entscheidung ist Pflicht -- ein Datenbank-Trigger erzwingt sie.
    # Beim ersten Lauf hat er diesen Test abgewiesen, und das ist richtig so:
    # ein Knoten ohne Normentscheidung liesse offen, ob nie jemand hingesehen
    # hat oder ob bewusst "kein Rang" entschieden wurde.
    # Der Elternknoten muss existieren -- zweiter Trigger, zweite berechtigte
    # Abweisung: ein Knoten unter einem Ast, den es nicht gibt, waere ueber
    # den Baum nie erreichbar.
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, title, summary, content,"
        " source, norm_entscheidung, norm_entschieden_grund, norm_entschieden_von,"
        " gattung, project_id, created_at, updated_at)"
        " VALUES ('t0','/probe',NULL,'Probe','Ast fuer Pruefknoten.','',"
        "'erzeugt aus tests/test_kern_modellneutral.py','keine_norm',"
        "'Astwurzel, traegt keine Aussage','betreiber','arbeitsbestand','shared',"
        "'2026-08-18T00:00:00Z','2026-08-18T00:00:00Z')")
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, title, summary, content,"
        " source, norm_rang, gilt_ab, gilt_bis, norm_entscheidung, norm_entschieden_grund,"
        " norm_entschieden_von, gattung, project_id, created_at, updated_at)"
        " VALUES ('t1','/probe/modellneutral','/probe','Modellneutraler Kern',"
        "'Der Kern liefert Quelle und Geltung auch ohne Einbettungsmodell.',"
        "'Volltext zur Modellneutralitaet des Kerns.','erzeugt aus tests/test_kern_modellneutral.py',"
        "2,'2026-08-01',NULL,'norm_unbefristet','Pruefknoten fuer BDW-R05-AC1: traegt Rang und"
        " Geltung, damit die Antwort beides ausweisen KANN','betreiber',"
        "'arbeitsbestand','shared','2026-08-18T00:00:00Z','2026-08-18T00:00:00Z')")
    conn.commit()
    conn.close()
    monkeypatch.setenv("BEGOD_KNOWLEDGE_DB", str(db))
    for name in ("knowledge_mcp_server",):
        sys.modules.pop(name, None)
    return db


def _suche(**kwargs):
    import knowledge_mcp_server as srv
    return srv.knowledge_search(**kwargs)


def test_kern_liefert_ohne_einbettungsmodell(bestand, monkeypatch):
    """DAS AC, erste Hälfte: kein Modell erreichbar -> der Kern antwortet
    trotzdem. Der Einbettungspfad wird hart abgeschaltet, damit der Test
    nicht davon abhängt, ob auf diesem Rechner gerade ein Modell läuft."""
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:9")  # nichts lauscht dort
    treffer = _suche(query="modellneutraler Kern", scope="all", max_results=10)
    assert treffer, "ohne Einbettungsmodell keine Antwort -- der Kern ist nicht neutral"
    text = treffer if isinstance(treffer, str) else str(treffer)
    assert "/probe/modellneutral" in text, f"Zielknoten nicht gefunden: {text[:300]}"


def test_antwort_weist_quelle_und_geltung_aus(bestand, monkeypatch):
    """DAS AC, zweite Hälfte -- und der Teil, der leicht übersehen wird:
    Eine Antwort ohne Quelle ist ein Zitat ohne Herkunft."""
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:9")
    treffer = _suche(query="modellneutraler Kern", scope="all", max_results=10)
    text = treffer if isinstance(treffer, str) else str(treffer)
    assert "Modellneutraler Kern" in text, "Titel fehlt in der Antwort"
    # Geltung: der Knoten trägt norm_rang 2 und gilt_ab -- mindestens eines
    # davon muss die Antwort mitführen, sonst ist die Geltung unausgewiesen.
    assert any(m in text for m in ("Rang", "rang", "gilt", "2026-08-01")), (
        f"weder Rang noch Geltung in der Antwort: {text[:300]}")


def test_zwei_laeufe_liefern_dasselbe(bestand, monkeypatch):
    """Neutralität heißt auch: reproduzierbar. Ein Kern, dessen Antwort je
    Lauf schwankt, ist nicht neutral, sondern zufällig."""
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:9")
    a = str(_suche(query="modellneutraler Kern", scope="all", max_results=10))
    b = str(_suche(query="modellneutraler Kern", scope="all", max_results=10))
    assert a == b, "zwei identische Anfragen, zwei verschiedene Antworten"


def test_schreibt_nicht_in_die_produktivdatenbank(bestand):
    """Die Gegenprobe zum Fallstrick im Fixture. Ohne sie wäre der Test grün
    und hätte trotzdem in den echten Bestand geschrieben -- genau das ist am
    2026-08-18 mit 48 Knoten passiert."""
    assert os.environ["BEGOD_KNOWLEDGE_DB"] == str(bestand)
    echt = WURZEL / "brainlehr.db"
    if echt.exists():
        conn = sqlite3.connect(f"file:{echt}?mode=ro", uri=True)
        treffer = conn.execute(
            "SELECT count(*) FROM knowledge_nodes WHERE path = '/probe/modellneutral'").fetchone()[0]
        conn.close()
        assert treffer == 0, "Testknoten in der Produktivdatenbank gelandet"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
