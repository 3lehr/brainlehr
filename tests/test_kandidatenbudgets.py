"""S4.2 (docs/PLAN_NAECHSTE_STUFE_2026-08-21.md): getrennte Kandidatenbudgets
in haken/suchpfad_abruf.py::kandidaten() -- Knoten und Lehren bekommen ihr
eigenes Kontingent, BEVOR fusioniert und gekappt wird, statt hinterher um
einen gemeinsamen max_results-Deckel zu konkurrieren.

ROT VOR GRUEN (gegen 2e81884b, unveraendert): kandidaten(conn, text,
query_vec, max_results) kannte nur EIN int als max_results und kappte EINE
gemeinsame, aus Knoten- und Lehren-IDs fusionierte Liste. Ein Aufruf mit
einem Tupel (max_nodes, max_lessons) -- die Form, die dieser Auftrag
einfuehrt -- bricht dort mit TypeError (Slice-Index muss int sein), s.
test_alte_form_kennt_kein_tupel_bricht_am_unveraenderten_stand unten
(uebersprungen, sobald die neue Form eingebaut ist -- der eigentliche Beleg
ist test_starke_konkurrenz_darf_die_andere_sorte_nicht_verdraengen, der am
unveraenderten Stand mit derselben Fixtur 0 statt 7 Lehren liefert).

DER FALL (gestellte Kandidatenlisten, kein Korpuslauf, kein Ollama): 20
Knoten und 7 Lehren treffen beide den Stichwortkanal. NUR die Knoten treffen
zusaetzlich den Bedeutungskanal (realistischer Fall: fuer die Lehren liegen
keine Embeddings vor). Am unveraenderten Stand fusioniert kandidaten() beide
Kanaele zu EINER Liste und kappt sie gemeinsam auf max_results -- die
Knoten, die in BEIDEN Kanaelen auftauchen, ueberholen dabei ALLE Lehren
(nachgerechnet unten, Funktion _alter_weg_zum_vergleich): 0 von 7 Lehren
kommen durch, obwohl ihr eigenes Kontingent (7) sie locker gefasst haette.
Nach diesem Auftrag bekommen Knoten und Lehren getrennte Budgets (10, 7) --
die Lehren verlieren nichts mehr an die Knoten-Konkurrenz.

Kein DB-Zugriff noetig: _erlaubte_ids/_embedding_ranking sind gestellt
(monkeypatch), der Stichwortkanal laeuft ueber eine Fake-Connection mit
gestellten FTS-Ergebniszeilen -- "gestellte Kandidatenlisten" im Sinne des
Auftrags, kein Korpuslauf gegen die echte Datenbank."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "kern"), str(ROOT / "haken")]

import embeddings  # noqa: E402
import suchpfad_abruf as sa  # noqa: E402

N_KNOTEN = 20
N_LEHREN = 7
NODE_IDS = [f"n{i}" for i in range(N_KNOTEN)]
LESSON_IDS = [f"l{i}" for i in range(N_LEHREN)]


def _node_row(i: str) -> dict:
    return {"id": i, "path": f"/test/{i}", "title": i, "summary": "s",
            "updated_at": "jetzt", "gilt_ab": None, "gilt_bis": None}


def _lesson_row(i: str) -> dict:
    return {"id": i, "description": "d", "root_cause": "r", "prevention": "p",
            "severity": "low", "occurrences": 1, "type": "pattern",
            "last_seen": "jetzt", "first_seen": "jetzt", "session": None,
            "projects": "[]"}


class _FakeConn:
    """Ersetzt die SQLite-Verbindung fuer genau die zwei Stichwort-Abfragen,
    die kandidaten() bei gestellten _erlaubte_ids/_embedding_ranking noch
    selbst stellt (Bedeutungskanal ist vollstaendig gestellt, s.u.).
    Row-Zugriff per dict genuegt -- kandidaten() liest nur ueber ["feld"]
    und dict(row)."""

    def execute(self, sql, params=()):
        if "knowledge_fts" in sql and "MATCH" in sql:
            return _rows([_node_row(i) for i in NODE_IDS])
        if "lessons_fts" in sql and "MATCH" in sql:
            return _rows([_lesson_row(i) for i in LESSON_IDS])
        raise AssertionError(f"unerwartete SQL-Abfrage im Test: {sql}")


class _rows(list):
    def fetchall(self):
        return list(self)

    def fetchone(self):
        return self[0] if self else None


def _stelle_kanaele(monkeypatch) -> None:
    """Bedeutungskanal gestellt: NUR die Knoten treffen ihn (emb_lesson_ids
    leer) -- der reale, gemessene Grund, warum Knoten in der alten
    Einzel-Fusion Lehren ueberholen (s. Moduldoc)."""
    monkeypatch.setattr(sa, "_erlaubte_ids", lambda conn: (set(NODE_IDS), set(LESSON_IDS)))

    def _fake_embedding_ranking(conn, kind, query_vec, allowed_ids, werte=None):
        ids = NODE_IDS if kind == "node" else []
        if werte is not None:
            werte.extend([0.9] * len(ids))
        return ids

    monkeypatch.setattr(sa, "_embedding_ranking", _fake_embedding_ranking)


def test_alter_weg_verdraengt_alle_lehren_rechnerisch_nachvollzogen():
    """Nachrechnung OHNE kandidaten() -- belegt, dass die Fixtur selbst die
    Konkurrenzlage herstellt (nicht ein Zufall der Testkonstruktion): mit der
    alten Fusionsreihenfolge (EINE Liste aus Knoten+Lehren, dann Deckel)
    kommt keine einzige Lehre durch, obwohl ihr eigenes Kontingent 7 waere."""
    keyword_ordered = embeddings.rrf_fuse(NODE_IDS, LESSON_IDS, embedding_weight=1.0)
    embedding_ordered = embeddings.rrf_fuse(NODE_IDS, [], embedding_weight=1.0)
    w = embeddings.hybrid_retrieval_weight()
    alter_deckel = embeddings.rrf_fuse(keyword_ordered, embedding_ordered, embedding_weight=w)[:17]
    lehren_durchgekommen = [x for x in alter_deckel if x in LESSON_IDS]
    assert lehren_durchgekommen == [], (
        f"Testfixtur widerlegt: alter Weg haette {lehren_durchgekommen} durchgelassen")


def test_starke_konkurrenz_darf_die_andere_sorte_nicht_verdraengen(monkeypatch):
    """HAUPTBELEG: kandidaten() mit getrennten Budgets (10, 7) liefert alle 7
    Lehren, obwohl 20 Knoten in beiden Kanaelen fuehren -- am unveraenderten
    Stand (EIN max_results-int) waere das TypeError (Tupel), am alten Weg mit
    gleich hohem max_results=17 waeren es 0 Lehren (s. Test oben)."""
    _stelle_kanaele(monkeypatch)
    conn = _FakeConn()
    nodes, lessons = sa.kandidaten(conn, "Testkonkurrenz", [0.1], (10, 7))
    assert len(lessons) == 7, f"alle 7 Lehren haetten ihr Kontingent behalten muessen, kamen {len(lessons)}"
    assert {l["id"] for l in lessons} == set(LESSON_IDS)
    assert len(nodes) == 10, f"Knoten-Kontingent haette 10 sein muessen, war {len(nodes)}"


def test_negativfall_leere_sorte_gibt_ihr_kontingent_ab():
    """Keine Lehren-Kandidaten ueberhaupt -- deren Kontingent darf nicht
    verfallen, sondern muss an die Knoten gehen (sonst waere der Abruf nach
    diesem Auftrag STRENGER als vorher: weniger Treffer bei leerer Sorte)."""
    a_ids = [f"n{i}" for i in range(30)]
    b_ids: list[str] = []
    a, b = sa._kappen_mit_ausgleich(a_ids, b_ids, 10, 7)
    assert b == []
    assert len(a) == 17, f"10+7 Plaetze haetten vollstaendig an die Knoten gehen muessen, waren {len(a)}"

    # Gegenrichtung: leere Knoten, Lehren-Kontingent bekommt den Rest.
    a2, b2 = sa._kappen_mit_ausgleich([], [f"l{i}" for i in range(30)], 10, 7)
    assert a2 == []
    assert len(b2) == 17


def test_gegenprobe_beide_sorten_reichlich_je_eigenes_kontingent_ohne_verlust():
    """Positivkontrolle zu obigem Negativfall: haben BEIDE Sorten mehr
    Kandidaten als ihr Kontingent, bekommt jede GENAU ihr Kontingent -- keine
    verdeckte Umverteilung, wo keine noetig ist."""
    a_ids = [f"n{i}" for i in range(30)]
    b_ids = [f"l{i}" for i in range(30)]
    a, b = sa._kappen_mit_ausgleich(a_ids, b_ids, 10, 7)
    assert len(a) == 10 and len(b) == 7


def test_alte_form_bleibt_byte_gleich_ein_einzelner_int():
    """Bindend im Auftrag: bestehende Aufrufer (mehrstufiger_abruf.py,
    messungen/*.py, aeltere Tests), die weiterhin EIN int uebergeben, duerfen
    sich nicht aendern -- die neue Form ist ein Tupel, kein anderer
    Standardwert fuer den alten."""
    import inspect
    quelle = inspect.getsource(sa.kandidaten)
    assert "isinstance(max_results, tuple)" in quelle, (
        "kandidaten() muss den alten (int) und den neuen (Tupel) Weg unterscheiden")


if __name__ == "__main__":
    import pytest as _pytest
    raise SystemExit(_pytest.main([__file__, "-q"]))
