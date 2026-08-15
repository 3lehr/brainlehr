"""ROT VOR DEM FIX (runs/vektorstand_2026-08-15T111334+0200.json): zwei Vektoren
ungleicher Laenge lieferten 0.0 -- ununterscheidbar von "voellig unaehnlich".
Entscheidung: Rueckgabewert bleibt 0.0 (Aufrufer sortieren/schwellenvergleichen
ihn direkt, siehe knowledge_mcp_server.py:1985/3208), aber der Fall wird
geloggt statt lautlos zu verschwinden."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "kern"))
import embeddings  # noqa: E402


def test_dimension_mismatch_bleibt_0_aber_wird_geloggt(caplog):
    with caplog.at_level(logging.WARNING, logger="embeddings"):
        ergebnis = embeddings.cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0])
    assert ergebnis == 0.0
    assert any("Dimension ungleich" in r.message for r in caplog.records)


def test_echte_unaehnlichkeit_loggt_nicht():
    logger = logging.getLogger("embeddings")
    geloggt = []
    handler = logging.Handler()
    handler.emit = lambda record: geloggt.append(record)
    logger.addHandler(handler)
    try:
        ergebnis = embeddings.cosine_similarity([1.0, 0.0], [0.0, 1.0])
    finally:
        logger.removeHandler(handler)
    assert ergebnis == 0.0
    assert geloggt == []


def test_gleich_lange_vektoren_unveraendert():
    assert embeddings.cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert embeddings.cosine_similarity([1.0, 2.0, 3.0], [4.0, 5.0, 6.0]) == 1.0 * (
        (1 * 4 + 2 * 5 + 3 * 6) / ((14 ** 0.5) * (77 ** 0.5))
    )


def test_grenzwerte():
    assert embeddings.cosine_similarity([], []) == 0.0
    assert embeddings.cosine_similarity([1.0], [1.0]) == 1.0
    assert embeddings.cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0  # Nullvektor, keine Division durch 0
