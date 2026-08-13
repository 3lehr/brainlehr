"""Lokale Embeddings via Ollama + Brute-Force-Cosine-Fusion mit FTS5/LIKE.

Herkunft: reine Funktionen (embed_text, pack/unpack_embedding, cosine_similarity,
rrf_fuse, hybrid_retrieval_weight) 1:1 uebernommen aus
openlehr/apps/openlehr/daemon/embeddings.py, Commit 34bcb2af
(2026-07-29T14:40:11+0200). Nur die ENV-Variablen-Namen sind hub-spezifisch
umbenannt (KNOWLEDGE_* statt OPENLEHR_*); Logik unveraendert.

Ponytail: bei Einzelnutzer-Volumen (Grössenordnung Hunderte Nodes/Lessons)
reicht Brute-Force-Cosine-Similarity in reinem Python -- kein sqlite-vec,
keine neue Dependency. Stand 2026-08-13 richtiggestellt: numpy (2.4.2) IST
inzwischen installiert, wird aber HIER (cosine_similarity dieses Moduls)
weiterhin nicht gebraucht -- das Volumen bleibt klein genug fuer reines
Python. Bei groesserem Volumen (Kantenberechnung ueber alle Knoten-Paare,
Groessenordnung Tausende) nutzt kern/kanten_aus_bedeutung.py numpy, wenn
vorhanden, mit reinem Python als Rueckfall.

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
import re
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
# 0,106). KNOWLEDGE_OLLAMA_EMBED_MODEL ueberschreibt weiterhin -- reiner
# Ollama-Modellname, OHNE @ctx-Anhang (siehe DEFAULT_EMBED_MODEL unten).
_EMBED_MODEL_NAME = os.environ.get("KNOWLEDGE_OLLAMA_EMBED_MODEL", "bge-m3")

# Auftrag 80: die Identitaet eines Vektors ist nicht allein der Modellname.
# num_ctx aendert das Ergebnis (kappt laengeren Text VOR dem Embedden), ohne
# den Namen zu aendern -- heute 2048, ungesetzt in der Ollama-Anfrage und
# damit Ollamas eigener Vorgabewert fuer bge-m3 (siehe kern/knowledge_lint.py
# EMBED_CONTEXT_TOKENS-Kommentar und Aufgabe 69). KNOWLEDGE_OLLAMA_EMBED_NUM_CTX
# ueberschreibt.
EMBED_NUM_CTX = int(os.environ.get("KNOWLEDGE_OLLAMA_EMBED_NUM_CTX", "2048"))

# Aufgabe 69. GEMESSEN, nicht geschaetzt: runs/abschneidegrenze_bge_m3_2026-08-13.json,
# Commit 0b1ab4c. Verfahren war nicht der Konsekutiv-Kosinus (der zeigt nur
# Konvergenz), sondern gleicher Praefix mit VERSCHIEDENEM Suffix -- ab 8000
# Zeichen ist der Vektor EXAKT gleich, unabhaengig vom Suffix. Gleichheit
# statt blosser Aehnlichkeit ist der Beweis fuers Abschneiden. Ollama meldete
# fuer diese 8000 Zeichen 2048 Token (prompt_eval_count), also rund 3,9
# Zeichen je Token auf deutschem Fachtext.
#
# Als QUOTIENT hinterlegt, nicht als Zahl 8000: Wer num_ctx anhebt, bekommt
# die neue Grenze ohne Suchen-und-Ersetzen. Eine festgeschriebene 8000 waere
# ab der ersten Aenderung falsch und wuerde trotzdem geglaubt.
ZEICHEN_JE_TOKEN = 8000 / 2048


def zeichengrenze(num_ctx: int | None = None) -> int:
    """Ab wie vielen Zeichen ein Text VOR dem Einbetten gekappt wird.

    Der Wert ist eine SCHAETZUNG aus einem gemessenen Quotienten, kein
    harter Schnitt: Wie viele Zeichen in ein Token passen, haengt am Text.
    Deutsche Komposita brauchen mehr Token je Zeichen als englische Prosa,
    ein Text voller Kennungen und Pfade noch mehr. Wer knapp darunter liegt,
    ist also nicht sicher -- nur wer deutlich darunter liegt."""
    return int((EMBED_NUM_CTX if num_ctx is None else num_ctx) * ZEICHEN_JE_TOKEN)


def wird_gekappt(text: str, num_ctx: int | None = None) -> bool:
    """Verliert dieser Text beim Einbetten seinen hinteren Teil?

    WOZU: Ein gekappter Knoten ist mit seinem hinteren Teil im
    Bedeutungskanal unauffindbar, und zwar STILL -- eine Abrufzahl kann
    daran scheitern, ohne dass jemand die Ursache sieht. Diese Funktion
    macht die Grenze abfragbar, statt sie in einem Messprotokoll liegen zu
    lassen."""
    return len(text or "") > zeichengrenze(num_ctx)


_IDENTITY_RE = re.compile(r"^(?P<model>.+)@ctx(?P<ctx>\d+)$")


def model_identity(model: str | None = None, num_ctx: int | None = None) -> str:
    """Baut die gespeicherte/verglichene Modell-Identitaet aus Rohname +
    erzeugenden Parametern (Bauform (a), Auftrag 80: Parameter IM Namen statt
    eigener Spalte -- die drei bestehenden Leser vergleichen ohnehin nur die
    Spalte `model`, damit greifen sie unveraendert). Zwei Vektoren mit
    gleichem Rueckgabewert sind vergleichbar; unterscheidet sich num_ctx,
    unterscheidet sich der Rueckgabewert."""
    base = model or _EMBED_MODEL_NAME
    ctx = EMBED_NUM_CTX if num_ctx is None else num_ctx
    return f"{base}@ctx{ctx}"


def parse_model_identity(identity: str) -> tuple[str, int]:
    """Kehrwert zu model_identity(): trennt den rohen Ollama-Modellnamen (fuer
    den tatsaechlichen API-Aufruf -- Ollama kennt kein '@ctx...'-Suffix im
    Modelltag) von num_ctx. Ohne erkennbares Suffix (Bestandswert vor diesem
    Auftrag, oder ein Aufrufer, der einen rohen Namen uebergibt) gilt die
    Zeichenkette selbst als Modellname und EMBED_NUM_CTX als num_ctx."""
    match = _IDENTITY_RE.match(identity or "")
    if not match:
        return identity, EMBED_NUM_CTX
    return match.group("model"), int(match.group("ctx"))


# Identitaet statt Rohname: ALLE bestehenden Leser/Schreiber, die
# embeddings.DEFAULT_EMBED_MODEL referenzieren, vergleichen/speichern damit
# automatisch die volle Identitaet inklusive num_ctx -- ohne dass diese
# Dateien selbst angefasst werden muessen (siehe Auftragsbericht).
DEFAULT_EMBED_MODEL = model_identity()

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
    # model/DEFAULT_EMBED_MODEL traegt die volle Identitaet ('bge-m3@ctx2048')
    # -- Ollama kennt dieses Tag nicht, darum hier in Rohname + num_ctx
    # zerlegt (parse_model_identity ist der Kehrwert zu model_identity()).
    raw_model, ctx = parse_model_identity(model or DEFAULT_EMBED_MODEL)
    payload = {"model": raw_model, "input": cleaned,
               "keep_alive": DEFAULT_KEEP_ALIVE, "options": {"num_ctx": ctx}}
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


def keyword_floor_size() -> int:
    """Wie hybrid_retrieval_weight(): Modul-Konstante + Env-Uebersteuerung,
    Rueckweg kostenlos. KNOWLEDGE_KEYWORD_FLOOR ueberschreibt."""
    raw = os.environ.get("KNOWLEDGE_KEYWORD_FLOOR", "1")
    try:
        n = int(raw)
    except ValueError:
        return 1
    return max(0, n)


def fuse_semantic_led(
    keyword_ordered_ids: list[Any],
    embedding_ordered_ids: list[Any],
    max_results: int,
    *,
    embedding_weight: float = 1.0,
    floor: int | None = None,
) -> list[Any]:
    """Ersetzt die symmetrische RRF-Verschmelzung an der Stelle, wo ein
    Stichwort- und ein Bedeutungskanal zusammentreffen (Auftrag 2026-08-12,
    Knoten d84b6b64: rrf_fuse gewichtet den RANG im Kanal, nicht seine
    GUETE -- ein Kanal mit wenigen, aber durchweg irrelevanten Treffern
    verdraengt per Rangaddition einen einzelnen starken Treffer im anderen
    Kanal).

    GEPRUEFT UND VERWORFEN, 2026-08-12: ein numerischer Kanal-Guete-
    Schwellwert (Trefferzahl, Abstand Rang1-zu-Median, absoluter bm25-Wert),
    unter dem ein Kanal ganz stumm bleibt. Alle drei korrelieren mit der
    SPEZIFITAET einer Anfrage, nicht mit ihrer Richtigkeit: eine treffsichere
    Einwort-Anfrage ('reachability', 1 Treffer, bm25 -8.05) sieht in allen
    drei Massen genauso schwach aus wie die acht themenfremden
    Trigramm-Zufallstreffer der Anfrage, die den Fehler zeigte. Ein
    Schwellwert haette die kurze richtige Anfrage stummgeschaltet oder die
    falsche durchgelassen.

    Stattdessen (Vorlage: eugeniughelbur/obsidian-second-brain, MIT-Lizenz --
    dort fuehrt die Bedeutungssuche das Ranking, die Stichwortsuche ist nur
    Stichentscheid): die Bedeutungsrangliste fuehrt, der Stichwortkanal
    garantiert nur seinen EINEN besten Treffer einen Platz (der bisherige
    Sockel reservierte bis zu max_results Plaetze -- genau der Mechanismus,
    der bei einem grossen, aber irrelevanten Stichwortkanal ALLE Plaetze
    fuer sich beanspruchte und den Bedeutungskanal vollstaendig verdraengte).
    Weitere Stichworttreffer sind Nachtrag: sie fuellen nur, was nach der
    Bedeutungsrangliste noch frei ist -- nichts geht verloren, nichts
    verdraengt mehr die Bedeutungssuche.

    embedding_weight<=0 oder kein Bedeutungskanal: reines Stichwortmatching,
    unveraendert (Rueckweg wie bisher)."""
    if embedding_weight <= 0.0 or not embedding_ordered_ids:
        return list(keyword_ordered_ids)[:max_results]
    floor_n = keyword_floor_size() if floor is None else max(0, floor)
    kw_floor = list(keyword_ordered_ids)[:floor_n]
    kw_floor_set = set(kw_floor)
    ordered = kw_floor + [i for i in embedding_ordered_ids if i not in kw_floor_set]
    ordered_set = set(ordered)
    ordered += [i for i in keyword_ordered_ids[floor_n:] if i not in ordered_set]
    return ordered[:max_results]


__all__ = [
    "cosine_similarity",
    "embed_text",
    "fuse_semantic_led",
    "hybrid_retrieval_weight",
    "keyword_floor_size",
    "model_identity",
    "pack_embedding",
    "parse_model_identity",
    "rrf_fuse",
    "unpack_embedding",
]
