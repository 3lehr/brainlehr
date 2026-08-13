"""Rot-vor-gruen fuer messungen/modellvergleich.py -- kein Netz, keine DB-
Schreibung. Bauform wie tests/test_naht_ratsche.py: WURZEL per schema.sql
gesucht statt fester Ebenenzahl.
"""
from __future__ import annotations

import sys
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "messungen")]

import embeddings  # noqa: E402
import modellvergleich as mv  # noqa: E402


def test_naechstes_ziel_findet_naeheres():
    ziel_vecs = {"node:/a": [1.0, 0.0], "node:/b": [0.0, 1.0]}
    assert mv.naechstes_ziel([0.9, 0.1], ziel_vecs) == "node:/a"
    assert mv.naechstes_ziel([0.1, 0.9], ziel_vecs) == "node:/b"


def test_naechstes_ziel_ohne_query_vektor():
    # Ein Embed-Fehler der Anfrage darf nie stillschweigend "irgendein Ziel"
    # liefern -- das saehe wie ein Treffer/Fehltreffer aus, ist aber keiner.
    assert mv.naechstes_ziel(None, {"node:/a": [1.0, 0.0]}) is None


def test_naechstes_ziel_leerer_kandidatenpool():
    assert mv.naechstes_ziel([1.0, 0.0], {}) is None


def test_gekappte_ziele_werden_erkannt():
    grenze = embeddings.zeichengrenze()
    assert not embeddings.wird_gekappt("kurzer Text")
    assert embeddings.wird_gekappt("x" * (grenze + 1))


def test_nicht_erreichbares_modell_liefert_keine_0treffer_quote(monkeypatch):
    """Abnahme 5: ein Ausfall des Dienstes darf NICHT wie ein schlechtes
    Modell aussehen (0 Treffer). probe_erreichbar() muss False liefern, wenn
    embed_text() ausnahmslos None liefert."""
    monkeypatch.setattr(embeddings, "embed_text",
                         lambda *a, **k: None)
    assert mv.probe_erreichbar("nicht-vorhandenes-modell") is False


def test_gegenprobe_erreichbares_modell_liefert_true(monkeypatch):
    """Gegenprobe zum vorigen Fall: ein Fake, der Vektoren liefert, gilt als
    erreichbar -- sonst waere probe_erreichbar() nur eine Funktion, die immer
    False sagt, und der Negativfall oben waere kein Test."""
    monkeypatch.setattr(embeddings, "embed_text",
                         lambda *a, **k: [0.1, 0.2, 0.3])
    assert mv.probe_erreichbar("irgendein-modell") is True


def test_fallbestand_form():
    etikettiert, negativ = mv.lade_faelle()
    assert len(etikettiert) == 35, (
        f"erwartet 35 etikettierte Faelle aus {mv.FALLBESTAND.name}, "
        f"gefunden {len(etikettiert)} -- Datei geaendert?")
    assert len(negativ) == 10, len(negativ)
    for f in etikettiert:
        assert f["target_kind"] in ("node", "lesson")
        assert f["target_id"]
    for f in negativ:
        assert not f.get("target_id")


def test_ziel_ids_eindeutig_und_aufloesbar():
    """Jedes der 35 Ziele muss GENAU einmal vorkommen und im heutigen
    Bestand tatsaechlich existieren -- sonst misst die Trefferquote gegen
    ein Ziel, das es gar nicht mehr gibt."""
    import speicher

    etikettiert, _ = mv.lade_faelle()
    ziel_ids = {f"{f['target_kind']}:{f['target_id']}" for f in etikettiert}
    assert len(ziel_ids) == 35, "Ziele nicht eindeutig -- Trefferquote waere verzerrt"
    with speicher.lesen() as conn:
        fehlend = []
        for zid in ziel_ids:
            kind, ref = zid.split(":", 1)
            if mv.ziel_text(conn, kind, ref) is None:
                fehlend.append(zid)
    assert not fehlend, f"Ziele nicht mehr im Bestand: {fehlend}"
