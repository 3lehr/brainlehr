"""Beweis, WARUM eine Aenderung an kern/embeddings.py::rrf_fuse() die
deutsch/englisch-Asymmetrie aus Knoten d84b6b64 NICHT beheben kann.

AUFTRAG 2026-08-15: rrf_fuse() gewichte den Rang im Kanal statt seine Guete
-- Befund vom 2026-08-12. Vor jeder Aenderung wurde der ECHTE Suchpfad
(knowledge_mcp_server.knowledge_search) mit dem Leitfall nachgefahren:

  DE "Dichtung Leckage Treibstofftank Fehleranalyse Startverzoegerung"
     -> 0 von 5 Treffern aus /nasa-llis (reproduziert, siehe Bericht)
  EN "seal leakage propellant tank failure analysis launch delay"
     -> mind. 3 von 5 Treffern aus /nasa-llis (reproduziert)

STRUKTURELLER BEFUND (dieser Datei): knowledge_search() ruft NICHT direkt
rrf_fuse() fuer das Endergebnis -- es ruft
knowledge_mcp_server._fuse_with_keyword_floor(), die NACH rrf_fuse() einen
unbedingten Stichwort-Sockel voranstellt:

    floor = keyword_ordered_ids[:max_results]
    return list(dict.fromkeys(floor + fused))[:max(max_results, len(floor))]

keyword_ordered_ids traegt NUR Stichworttreffer (FTS5-Rang von Knoten+
Lehren, embedding_weight dort fest 1.0 zwischen zwei Stichwort-Ranglisten --
der Bedeutungskanal ist an dieser Stelle nicht beteiligt). Hat der
Stichwortkanal allein schon >= max_results Treffer (Leitfall: 6 Knoten + 6
Lehren = 12 >= 5), ist floor VOLLSTAENDIG gefuellt, rein aus Stichwort-
Treffern -- unabhaengig davon, was rrf_fuse() intern berechnet, denn floor
wird direkt aus keyword_ordered_ids geschnitten, nicht aus dem Ergebnis von
rrf_fuse() zwischen Stichwort- und Bedeutungskanal.

test_floor_gesaettigt_verdraengt_embedding_treffer beweist das MATHEMATISCH,
ohne DB/Netzwerk: selbst wenn rrf_fuse() DURCH DIE EXTREMSTMOEGLICHE
Bedeutungs-fuehrt-Variante ersetzt wird (monkeypatch: liefert exakt die
Embedding-Rangliste, Stichwortkanal komplett ignoriert), bleibt der
embedding-only-Treffer draussen -- weil _fuse_with_keyword_floor() das
Ergebnis von rrf_fuse() gar nicht befragt, solange floor allein schon
max_results Plaetze fuellt.

FOLGERUNG: die Behebung des Leitfalls braucht eine Aenderung an
knowledge_mcp_server.py::_fuse_with_keyword_floor() (z.B. Ersatz durch
kern/embeddings.py::fuse_semantic_led(), die genau diesen Sockel-Fehler
behebt -- s. deren Docstring). Diese Datei liegt aber auf der TABU-Liste
des Auftrags 2026-08-15 -- die Behebung ist deshalb NICHT Teil dieser
Aenderung, siehe Bericht im Auftrag.

test_floor_nicht_gesaettigt_laesst_embedding_treffer_durch ist die
Gegenprobe: hat der Stichwortkanal WENIGER Treffer als max_results, bleiben
freie Plaetze fuer den fusionierten (Stichwort+Bedeutung) Rang -- dort WIRKT
eine rrf_fuse-Aenderung. Dieser Fall ist NICHT der Leitfall (dort hat der
Stichwortkanal genug Treffer, um den Sockel zu fuellen), zeigt aber, dass
_fuse_with_keyword_floor() nicht in jedem Fall taub fuer den Bedeutungskanal
ist -- nur wenn der Stichwortkanal saettigt.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w), str(_w / "kern")]

import knowledge_mcp_server as kms  # noqa: E402


def test_floor_gesaettigt_verdraengt_embedding_treffer(monkeypatch):
    """Leitfall nachgebaut, synthetisch: 5 reine Stichworttreffer (kein
    Bezug zum Ziel), das Ziel liegt NUR im Bedeutungskanal, dort auf Rang 0
    (bestmoeglich). max_results=5 -- wie der Leitfall (0 von 5)."""
    kw_ids = ["noise-1", "noise-2", "noise-3", "noise-4", "noise-5"]
    emb_ids = ["target", "noise-1", "noise-3", "noise-5", "noise-2"]

    # Extremstmoegliche Bedeutungs-fuehrt-Variante: rrf_fuse() ignoriert den
    # Stichwortkanal komplett und liefert reine Embedding-Reihenfolge --
    # staerker als jede in kern/embeddings.py denkbare Gewichtung.
    monkeypatch.setattr(kms.embeddings, "rrf_fuse", lambda kw, emb, **_: list(emb))

    ergebnis = kms._fuse_with_keyword_floor(kw_ids, emb_ids, max_results=5)

    assert "target" not in ergebnis, (
        "Der Sockel (floor = keyword_ordered_ids[:max_results]) haette bei "
        "5 Stichworttreffern und max_results=5 ALLE Plaetze aus dem "
        "Stichwortkanal gefuellt, bevor rrf_fuse() ueberhaupt gefragt wird -- "
        "'target' haette draussen bleiben MUESSEN, selbst mit der "
        "staerksten denkbaren Bedeutungs-Gewichtung. Ist es doch drin, hat "
        "sich die Sockel-Logik in _fuse_with_keyword_floor() geaendert und "
        "dieser Befund ist zu pruefen."
    )
    assert ergebnis == kw_ids, "Sockel haette bei Saettigung 1:1 die Stichwortliste sein muessen"


def test_floor_nicht_gesaettigt_laesst_embedding_treffer_durch():
    """Gegenprobe: nur 2 Stichworttreffer bei max_results=5 -- der Sockel
    lässt 3 freie Plaetze, die der fusionierten (Stichwort+Bedeutung)
    Rangliste zufallen. Echtes rrf_fuse(), keine Mutation -- zeigt den
    Normalfall, in dem eine rrf_fuse-Aenderung sehr wohl wirkt."""
    kw_ids = ["noise-1", "noise-2"]
    emb_ids = ["target", "noise-1", "andere-1", "andere-2"]

    ergebnis = kms._fuse_with_keyword_floor(kw_ids, emb_ids, max_results=5)

    assert "target" in ergebnis, (
        "Bei nicht-gesaettigtem Sockel sollte ein embedding-only-Treffer "
        "einen freien Platz bekommen -- Messwerkzeug oder Sockel-Logik "
        "hat sich geaendert, neu pruefen."
    )


if __name__ == "__main__":
    test_floor_gesaettigt_verdraengt_embedding_treffer_ctx = None
    import types

    class _Ctx:
        def setattr(self, obj, name, value):
            setattr(obj, name, value)

    test_floor_gesaettigt_verdraengt_embedding_treffer(_Ctx())
    print("test_floor_gesaettigt_verdraengt_embedding_treffer: ok")
    test_floor_nicht_gesaettigt_laesst_embedding_treffer_durch()
    print("test_floor_nicht_gesaettigt_laesst_embedding_treffer_durch: ok")
