"""Schritt 1 + Schritt 2 aus docs/PLAN_KANALGUETE_2026-08-15.md, isoliert
gegen kern/embeddings.py -- OHNE DB/Ollama, damit die Mutationsprobe schnell
und ohne Netz laeuft (der volle Weg gegen den echten Bestand steht in
runs/kanalguete_*.json, erzeugt von kern/kanalguete_messung.py).

Schritt 1 (filter_whole_word_hits): der Stichwortkanal ist trigram-
tokenisiert -- ein Fragmenttreffer ('ver' aus 'Startverzoegerung' matcht
'Verdichtung') darf nicht mehr in die Fusion.

Schritt 2 (channel_discrimination -> rrf_fuse(fts_scores=, embedding_scores=)):
ein Kanal ohne Punktwert-Spanne (bester Treffer == mittlerer) traegt kein
volles Ranggewicht mehr. Explizit GEGENGEPRUEFT: der am 2026-08-12 verworfene
Ansatz (harter Schwellwert, Kanal komplett stumm) haette die treffsichere
Einwort-Anfrage ('reachability', 1 Treffer) bestraft -- hier bleibt ein
Kanal mit nur einem Treffer bei voller Wirkung (channel_discrimination
gibt 1.0 zurueck, kein Schwellwert, keine Stummschaltung).
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w), str(_w / "kern")]

import embeddings  # noqa: E402


# ---------- channel_discrimination (Schritt 2, Baustein) ----------

def test_discrimination_identische_punktwerte_ist_null():
    """Grenzwert: keine Trennschaerfe -- alle Punktwerte gleich."""
    assert embeddings.channel_discrimination([0.4, 0.4, 0.4]) == 0.0


def test_discrimination_einzelner_treffer_ist_voll():
    """Der 'reachability'-Gegenbeweis zum verworfenen Schwellwert-Ansatz:
    EIN Treffer hat nichts, wogegen er verglichen wird -- volle Wirkung,
    keine Bestrafung fuer Praezision."""
    assert embeddings.channel_discrimination([0.9]) == 1.0


def test_discrimination_leere_liste_ist_voll():
    assert embeddings.channel_discrimination([]) == 1.0


def test_discrimination_scharfe_spitze_nahe_eins():
    """Bester Treffer weit ueber dem Median -> nahe 1.0."""
    d = embeddings.channel_discrimination([0.9, 0.1, 0.1, 0.1, 0.1])
    assert d > 0.9


def test_discrimination_flacher_kanal_nahe_null():
    """Bester Treffer kaum ueber dem Median -> nahe 0.0 (sieben eng
    beieinanderliegende Trigramm-Zufallstreffer, einer minimal darueber,
    wie im belegten Befund -- die Masse der Punktwerte liegt am oberen
    Rand, der Median fast auf Hoehe des Maximums)."""
    d = embeddings.channel_discrimination([0.31, 0.305, 0.30, 0.30, 0.30, 0.30, 0.30, 0.24])
    assert d < 0.2


# ---------- filter_whole_word_hits (Schritt 1) ----------

TEXTE = {
    "verdichtung": "Die Verdichtung des Bodens war ungenuegend.",
    "startverzoegerung": "Eine Startverzoegerung trat beim Test auf.",
    "treffer": "Dichtung und Leckage am Treibstofftank, Fehleranalyse noetig.",
}


def test_schritt1_verwirft_reinen_fragmenttreffer():
    """'ver' aus 'Startverzoegerung' matcht 'Verdichtung' nur als Trigramm-
    Fragment -- kein GANZES Anfragewort steht im Text -> raus."""
    ergebnis = embeddings.filter_whole_word_hits(
        "Startverzoegerung", ["verdichtung", "startverzoegerung"], TEXTE)
    assert ergebnis == ["startverzoegerung"]


def test_schritt1_behaelt_ganzwort_treffer():
    ergebnis = embeddings.filter_whole_word_hits(
        "Dichtung Leckage", ["treffer"], TEXTE)
    assert ergebnis == ["treffer"]


def test_schritt1_fehlender_text_bleibt_drin():
    """Kein Text geladen -> konservativ behalten, nicht verwerfen."""
    ergebnis = embeddings.filter_whole_word_hits("irgendwas", ["unbekannt-id"], {})
    assert ergebnis == ["unbekannt-id"]


def test_schritt1_kurze_anfrageworte_filtern_nicht():
    """Woerter < 3 Zeichen erzeugen im Trigramm-Index ohnehin kein Fragment
    (_stichwortkanal_blind in knowledge_mcp_server.py) -- hier: keine
    filterfaehigen Woerter -> alles bleibt drin, unveraendert."""
    ergebnis = embeddings.filter_whole_word_hits("zu an", ["verdichtung", "treffer"], TEXTE)
    assert ergebnis == ["verdichtung", "treffer"]


def test_schritt1_reihenfolge_bleibt_erhalten():
    ergebnis = embeddings.filter_whole_word_hits(
        "Verdichtung Dichtung", ["treffer", "verdichtung"], TEXTE)
    assert ergebnis == ["treffer", "verdichtung"]


# ---------- rrf_fuse mit Schritt 2 (Rueckwaertskompatibilitaet + Wirkung) ----------

def test_rrf_fuse_ohne_scores_unveraendert():
    """Kein score-Argument -> byte-identisch zur alten Formel (Vorgabe
    fts_disc=emb_disc=1.0). Belegt Rueckwaertskompatibilitaet fuer jeden
    bestehenden Aufrufer, der keine Scores uebergibt."""
    kw = ["a", "b", "c"]
    emb = ["c", "a", "d"]
    alt = sorted(
        {doc_id: sum(1.0 / (60 + p + 1) for lst in (kw, emb) for p, i in enumerate(lst) if i == doc_id)
         for doc_id in set(kw) | set(emb)}.items(),
        key=lambda kv: kv[1], reverse=True)
    alt_ids = [k for k, _ in alt]
    assert embeddings.rrf_fuse(kw, emb) == alt_ids


def test_rrf_fuse_flacher_stichwortkanal_verliert_gewicht_gegen_scharfen_bedeutungskanal():
    """Leitfall nachgebaut (synthetisch, wie tests/test_kanalguete_flooranalyse.py):
    5 gleich schwache Stichworttreffer (Trigramm-Rauschen) vs. ein Bedeutungs-
    kanal mit einem klar fuehrenden Treffer. OHNE Schritt 2 (Rangaddition
    allein) kann Rauschen auf Rang 1 gewinnen; MIT channel_discrimination
    verliert der flache Kanal Gewicht.

    MUTATIONSPROBE: rrf_fuse(..., fts_scores=..., embedding_scores=...) durch
    rrf_fuse(...) OHNE Scores ersetzen -> dieser Test wird ROT (siehe
    Kommentar unten)."""
    kw = ["noise-1", "noise-2", "noise-3", "noise-4", "noise-5"]
    kw_scores = {i: 0.30 for i in kw}  # voellig flach -- keine Trennschaerfe
    emb = ["target", "noise-2", "noise-4"]
    emb_scores = {"target": 0.90, "noise-2": 0.20, "noise-4": 0.15}  # scharfe Spitze

    ergebnis = embeddings.rrf_fuse(
        kw, emb, fts_scores=kw_scores, embedding_scores=emb_scores)
    ohne_schritt2 = embeddings.rrf_fuse(kw, emb)  # alte Formel, zum Kontrast

    assert ergebnis.index("target") < ohne_schritt2.index("target"), (
        "Schritt 2 sollte 'target' (scharfer Bedeutungstreffer) gegenueber "
        "dem flachen Rauschkanal nach vorn ziehen -- vorher lag es weiter "
        "hinten. Rot bei rrf_fuse(kw, emb) ohne Scores: das IST die "
        "Mutationsprobe (siehe Docstring)."
    )


def test_rrf_fuse_grenzwert_ein_kanal_leer():
    assert embeddings.rrf_fuse([], ["x", "y"]) == ["x", "y"]
    assert embeddings.rrf_fuse(["x", "y"], []) == ["x", "y"]


def test_rrf_fuse_grenzwert_leere_anfrage_beide_kanaele_leer():
    assert embeddings.rrf_fuse([], []) == []


if __name__ == "__main__":
    import inspect
    modul_funktionen = [f for name, f in list(globals().items())
                         if name.startswith("test_") and inspect.isfunction(f)]
    for f in modul_funktionen:
        f()
        print(f"{f.__name__}: ok")
