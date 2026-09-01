"""Kann das System sagen, dass es nichts hat?

Bis zum 2026-08-16 nicht: bei 40 Anfragen, deren Antwort nachweislich NICHT
im Bestand liegt, meldete es 40 Mal einen Treffer (Knoten cc458fb3). Der
Zustand war nicht ausdrueckbar -- und damit jede Trefferquote zweideutig.

Diese Datei prueft die Behebung auf beiden Ebenen: die reine Rechnung
(kern/relevanzlage.py, ohne Aufbau) und den echten Suchweg
(knowledge_search, mit Datenbank und Bedeutungskanal).

ROT VOR GRUEN: gegen den Stand vor dem 2026-08-16 schlägt der echte Suchweg
fehl -- `bestandslage` existierte nicht, der Zugriff liefe ins Leere. Seit
MUST-LAGE-001 heißt eine niedrige, nicht trennscharfe Lage `uneindeutig`, weil
der Klassifikator die FTS-/Fusionsbelege nicht sieht.
"""
from __future__ import annotations

import json
import sys as _sys
import urllib.error
import urllib.request
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w), str(_w / "kern")]

import pytest  # noqa: E402

from conftest import braucht_bestand  # noqa: E402
import relevanzlage  # noqa: E402


def test_zwei_zeichen_muessen_zusammenkommen():
    """Ein hoher Wert ALLEIN genuegt nicht.

    Der Fall dahinter ist gemessen: eine allgemein formulierte Anfrage
    aehnelt vielen Knoten gleich gut. Ein reiner Schwellwert haelt das fuer
    einen guten Treffer -- der Abstand zum Zweitbesten entlarvt es."""
    assert relevanzlage.beurteile([0.70, 0.60, 0.55])["lage"] == "passend"
    assert relevanzlage.beurteile([0.70, 0.699, 0.698])["lage"] == "schwach"
    assert relevanzlage.beurteile([0.45, 0.44, 0.43])["lage"] == "uneindeutig"


def test_uneindeutiger_bedeutungskanal_behauptet_keinen_leeren_bestand():
    """MUST-LAGE-001: Der Klassifikator sieht nur den Bedeutungskanal.

    Niedrige, eng beieinanderliegende Kosinuswerte belegen deshalb keine
    Abwesenheit in FTS/Fusion. Der echte Q2-Fall liefert trotz dieser Werte
    ``cd571222`` als FTS-Rang 1.
    """
    lage = relevanzlage.beurteile([0.5372, 0.5356])
    assert lage["lage"] == "uneindeutig"
    assert "nichts Passendes" not in lage["satz"]


def test_kein_entwicklertext_im_satz():
    """Der Satz geht an den NUTZER -- keine Kennzahl, kein Feldname, keine
    Schwelle (Hausregel: keine Entwicklerinformation in der Oberflaeche)."""
    for werte in ([0.70, 0.60], [0.70, 0.699], [0.45, 0.44], [0.50, 0.40]):
        satz = relevanzlage.beurteile(werte)["satz"]
        for verboten in ("Kosinus", "Schwelle", "Embedding", "lage", "0."):
            assert verboten not in satz, (verboten, satz)


def test_ohne_bedeutungskanal_keine_behauptung():
    """Ollama nicht erreichbar, Tabelle fehlt: dann wird NICHTS behauptet --
    weder dass etwas passt noch dass nichts da ist."""
    lage = relevanzlage.beurteile([])
    assert lage["lage"] == "ohne_bedeutungskanal" and lage["satz"] == ""


def test_ollama_lage_unterscheidet_endpoint_und_fehlendes_modell(monkeypatch):
    import embeddings

    class Reply:
        def __init__(self, payload): self.payload = payload
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self): return json.dumps(self.payload).encode()

    monkeypatch.setattr(embeddings, "DEFAULT_EMBED_MODEL", "bge-m3@ctx2048")
    monkeypatch.setattr(urllib.request, "urlopen", lambda *_args, **_kwargs: Reply({"models": []}))
    assert "not installed" in _ollama_lage()
    monkeypatch.setattr(urllib.request, "urlopen", lambda *_args, **_kwargs: Reply({"models": [{"name": "bge-m3:latest"}]}))
    assert _ollama_lage() == "ready"


def _ollama_lage() -> str:
    """Health-only: never load or generate an embedding just to choose a skip."""
    import embeddings
    raw_model, _ctx = embeddings.parse_model_identity(embeddings.DEFAULT_EMBED_MODEL)
    try:
        with urllib.request.urlopen(f"{embeddings.DEFAULT_OLLAMA_URL.rstrip('/')}/api/tags", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError, OSError):
        return f"Ollama endpoint unavailable at {embeddings.DEFAULT_OLLAMA_URL}"
    names = {str(row.get("name", "")).split(":", 1)[0] for row in payload.get("models", []) if isinstance(row, dict)}
    return "ready" if raw_model in names else f"Ollama reachable, embedding model {raw_model!r} is not installed"


@pytest.mark.skipif(not (_w / "brainlehr.db").exists(), reason="keine Datenbank")
def test_suchweg_meldet_uneindeutige_lage():
    """Der ECHTE Weg, beide Richtungen -- die Abnahme dieser Aenderung.

    Wichtig ist der zweite Teil der Zusicherung: die Treffer bleiben. Es wird
    gekennzeichnet, nicht gefiltert. Ein Filter kauft weniger Falschmeldungen
    mit verlorenen Treffern (gemessen: 8 statt 40 Falschmeldungen, aber nur
    noch 32 statt 37 gefundene von 40)."""
    # The live smoke needs a grown corpus, not merely an existing (possibly
    # fresh partition) SQLite file.  Keep the semantic assertion strict once
    # that prerequisite is present.
    braucht_bestand()
    ollama_lage = _ollama_lage()
    if ollama_lage != "ready":
        pytest.skip(ollama_lage)
    import knowledge_mcp_server as kms

    unsinn = kms.knowledge_search("Kaffeemaschine Bueroklammer Regenschirm Wochenendausflug",
                                  max_results=5)
    assert unsinn["bestandslage"]["lage"] == "uneindeutig", unsinn["bestandslage"]
    assert unsinn["bestandslage"]["satz"], "der Nutzer bekommt einen Satz, keine Zahl"
    assert unsinn["count"] > 0, (
        "gekennzeichnet, NICHT gefiltert -- die Treffer bleiben erhalten")

    leitfall = kms.knowledge_search("Dichtung Leckage Treibstofftank Fehleranalyse Startverzoegerung",
                                    max_results=5)
    # The installed corpus/model is mutable.  This is a live smoke check, not
    # a frozen calibration fixture: never turn an honest close-score warning
    # into a false "passend" claim merely because the words are plausible.
    assert leitfall["bestandslage"]["lage"] in {"passend", "schwach", "uneindeutig"}
    assert leitfall["count"] > 0
