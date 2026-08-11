"""Lokale Embeddings via Ollama + Brute-Force-Cosine-Fusion mit FTS5/LIKE.

Herkunft: reine Funktionen (embed_text, pack/unpack_embedding, cosine_similarity,
rrf_fuse, hybrid_retrieval_weight) 1:1 uebernommen aus
openlehr/apps/openlehr/daemon/embeddings.py, Commit 34bcb2af
(2026-07-29T14:40:11+0200). Nur die ENV-Variablen-Namen sind hub-spezifisch
umbenannt (KNOWLEDGE_* statt OPENLEHR_*); Logik unveraendert.

Ponytail: bei Einzelnutzer-Volumen (Grössenordnung Hunderte Nodes/Lessons)
reicht Brute-Force-Cosine-Similarity in reinem Python -- kein sqlite-vec,
keine neue Dependency (numpy ist nicht installiert und wird hierfuer nicht
gebraucht).

Embedding-Erzeugung ist IMMER best-effort: `embed_text()` gibt bei jedem
Fehler (Ollama nicht erreichbar, Modell fehlt, Timeout) `None` zurueck statt
zu werfen -- ein Ausfall darf NIE die Wissenssuche blockieren, die bisher
ohne Netzwerk-Abhaengigkeit (reines FTS5/LIKE) funktioniert.
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

import json
import math
import os
import struct
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_OLLAMA_URL = os.environ.get("KNOWLEDGE_OLLAMA_URL", "http://127.0.0.1:11434")
# bge-m3 statt nomic-embed-text (Auftrag 2026-08-07, Messung
# docs/PRUEFKORPORA_UND_SPRACHE_2026-08-07.md): nomic-embed-text trennt auf
# deutschem Fachtext nicht (passend Median 0,531 vs. fachfremd 0,527,
# Fachfremd-Minimum ueber Passend-Minimum) -- bge-m3 trennt (Median-Abstand
# 0,106). KNOWLEDGE_OLLAMA_EMBED_MODEL ueberschreibt weiterhin.
DEFAULT_EMBED_MODEL = os.environ.get("KNOWLEDGE_OLLAMA_EMBED_MODEL", "bge-m3")

# Warmhaltung und Timeout gehoeren zusammen -- getrennt loest keines das
# Problem. Gemessen 2026-08-11: Kaltstart von bge-m3 11,5 s, warmer Aufruf
# 0,12 s, Vorgabe-Timeout war 5,0 s. Jeder Versuch lief damit in den Timeout
# und gab still None zurueck; weil er abbrach, wurde das Modell nie warm, und
# der naechste Versuch fand denselben Kaltstart vor. Ein Teufelskreis, der im
# Bestand ein Datum hinterlassen hat: juengster Vektor 2026-08-10T12:26.
#
# EINHEIT NICHT VERGESSEN: Ollama lehnt keep_alive ohne Zeiteinheit mit
# HTTP 400 ab ("time: missing unit in duration") -- auch die naheliegende
# "-1" fuer unbegrenzt. Belegt in L-ce7310.
DEFAULT_KEEP_ALIVE = os.environ.get("KNOWLEDGE_OLLAMA_KEEP_ALIVE", "30m")

# Deckt den gemessenen Kaltstart mit Reserve. Der Preis ist eine laengere
# Wartezeit im echten Ausfall (Dienst tot) -- aber genau EINMAL je Prozess,
# weil der Rueckfall auf Stichwortsuche danach still weiterlaeuft.
DEFAULT_TIMEOUT = float(os.environ.get("KNOWLEDGE_OLLAMA_TIMEOUT", "20"))


def hybrid_retrieval_weight() -> float:
    """Fusion-Gewicht Embedding=0 -> reines Stichwortmatching (heutiger Zustand,
    Rollback-Schalter)."""
    raw = os.environ.get("KNOWLEDGE_HYBRID_EMBEDDING_WEIGHT", "1.0")
    try:
        weight = float(raw)
    except ValueError:
        return 1.0
    return max(0.0, weight)


def embed_text(text: str, *, base_url: str = "", model: str = "",
               timeout: float | None = None) -> list[float] | None:
    """Best-effort Embedding ueber Ollamas `/api/embed`. None bei jedem
    Netzwerk-/Modell-Fehler (Ollama nicht erreichbar, Modell fehlt, Timeout).
    AUSNAHME bewusst laut: Nicht-Loopback-URL wirft weiterhin ValueError,
    statt still zu degradieren -- ein Versuch, Embedding-Text an einen
    Nicht-Loopback-Host zu schicken, ist ein Konfigurationsfehler, der
    auffallen MUSS, nicht endlos still auf Stichwort-only zurueckfallen darf."""
    cleaned = (text or "").strip()
    if not cleaned:
        return None
    url = (base_url or DEFAULT_OLLAMA_URL).rstrip("/")
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Ollama-Embeddings duerfen nur Loopback-URLs nutzen")
    payload = {"model": model or DEFAULT_EMBED_MODEL, "input": cleaned,
               "keep_alive": DEFAULT_KEEP_ALIVE}
    req = urllib.request.Request(
        f"{url}/api/embed",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(
                req, timeout=DEFAULT_TIMEOUT if timeout is None else timeout) as response:
            raw_body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None
    vectors = raw_body.get("embeddings")
    if not isinstance(vectors, list) or not vectors or not isinstance(vectors[0], list):
        return None
    try:
        return [float(x) for x in vectors[0]]
    except (TypeError, ValueError):
        return None


def pack_embedding(vector: list[float]) -> bytes:
    return struct.pack(f"<{len(vector)}f", *vector)


def unpack_embedding(blob: bytes) -> list[float]:
    count = len(blob) // 4
    return list(struct.unpack(f"<{count}f", blob))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def rrf_fuse(
    fts_ordered_ids: list[Any],
    embedding_ordered_ids: list[Any],
    *,
    embedding_weight: float = 1.0,
    k: int = 60,
) -> list[Any]:
    """Reciprocal-Rank-Fusion: kombiniert zwei bereits sortierte ID-Listen zu
    einer, ohne die (unterschiedlich skalierten) Rohscores normalisieren zu
    muessen. embedding_weight=0 reproduziert exakt die Stichwort-Reihenfolge
    (Rollback)."""
    scores: dict[Any, float] = {}
    for position, doc_id in enumerate(fts_ordered_ids):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + position + 1)
    if embedding_weight > 0.0:
        for position, doc_id in enumerate(embedding_ordered_ids):
            scores[doc_id] = scores.get(doc_id, 0.0) + embedding_weight / (k + position + 1)
    return sorted(scores.keys(), key=lambda doc_id: scores[doc_id], reverse=True)


__all__ = [
    "cosine_similarity",
    "embed_text",
    "hybrid_retrieval_weight",
    "pack_embedding",
    "rrf_fuse",
    "unpack_embedding",
]
