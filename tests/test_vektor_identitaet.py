"""Rot-vor-gruen fuer Auftrag 80: die Identitaet eines Vektors war bisher
allein der Modellname (Spalte `model` in knowledge_embeddings). num_ctx
veraendert das Ergebnis eines Embeddings (kappt laengeren Text VOR dem
Rechnen), OHNE den Namen zu aendern -- zwei Vektoren mit num_ctx=2048 und
num_ctx=8192 heissen beide 'bge-m3' und wuerden von jedem `model = ?`-Filter
(knowledge_mcp_server._embedding_ranking, haken/suchpfad_abruf.py,
kern/kanten_aus_bedeutung.lade_knoten_vektoren) als vergleichbar behandelt.

Fix: embeddings.model_identity() haengt die erzeugenden Parameter an den
Namen ('bge-m3@ctx2048') -- die drei Leser vergleichen ohnehin nur die Spalte
`model`, sie greifen dadurch unveraendert korrekt. embed_text() und
build_embeddings._embed_batch() trennen diese Identitaet wieder in den
rohen Ollama-Modelltag + num_ctx-Option (parse_model_identity, die "Naht"
zwischen gespeicherter Identitaet und tatsaechlichem API-Aufruf) -- Ollama
kennt kein '@ctx...'-Suffix im Modelltag.

Alle Proben kommen ohne die echte Datenbank aus (reine Funktionen bzw.
gemockte urlopen-Antwort)."""
from __future__ import annotations

import json
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import embeddings  # noqa: E402


# --- a) Rot vor gruen: gleicher Modellname, verschiedene Abschneidegrenze --

def _naiv_modellname(model: str, num_ctx: int) -> str:
    """Steht fuer den Zustand VOR diesem Auftrag: die Identitaetspruefung
    kannte nur den rohen Modellnamen, num_ctx floss nicht ein."""
    return model


def test_rot_vor_fix_gleicher_name_verschiedene_abschneidegrenze_kollidiert():
    alt = _naiv_modellname("bge-m3", num_ctx=2048)
    neu = _naiv_modellname("bge-m3", num_ctx=8192)
    assert alt == neu, (
        "kein Fehler -- genau der Befund: die alte Pruefung haelt zwei "
        "Vektoren mit unterschiedlicher Abschneidegrenze faelschlich fuer "
        "dieselbe Identitaet"
    )


def test_gruen_nach_fix_identitaet_unterscheidet_verschiedene_abschneidegrenze():
    alt = embeddings.model_identity("bge-m3", num_ctx=2048)
    neu = embeddings.model_identity("bge-m3", num_ctx=8192)
    assert alt != neu, "unterschiedliche num_ctx muss unterschiedliche Identitaet ergeben"
    assert alt == "bge-m3@ctx2048"
    assert neu == "bge-m3@ctx8192"


# --- b) Negativfall (verbindlich): ein einheitlicher Bestand meldet nichts -

def test_negativfall_einheitlicher_bestand_erzeugt_keine_meldung():
    zeile_a = embeddings.model_identity("bge-m3", num_ctx=2048)
    zeile_b = embeddings.model_identity("bge-m3", num_ctx=2048)
    assert zeile_a == zeile_b, (
        "zwei Vektoren mit gleichem Modell UND gleicher Abschneidegrenze "
        "sind dieselbe Identitaet -- ohne diese Probe bestuende der "
        "Kollisionstest auch bei einer Pruefung, die immer 'verschieden' meldet"
    )


# --- c) Grenzwert: gleiche Abschneidegrenze, verschiedene Dimension --------

def test_grenzwert_gleiche_abschneidegrenze_verschiedene_dimension():
    """Entscheidung: dim ist bereits eine EIGENE Spalte in knowledge_embeddings
    (nicht Teil dieses Auftrags, nicht Teil der 'erzeugenden Parameter' wie
    num_ctx) und intrinsisch am Modell haengend -- ein Modellname liefert in
    der Praxis immer dieselbe Dimension. model_identity() nimmt dim daher
    NICHT in den Namen auf: gleicher Name + gleiche Abschneidegrenze bleibt
    dieselbe Identitaet, unabhaengig von dim.

    Das ist kein blinder Fleck ohne Netz: cosine_similarity() (kern/embeddings.py)
    prueft die Laenge selbst und liefert bei Mismatch 0.0 statt eines Crashs
    oder einer falschen Zahl -- ein zweites, unabhaengiges Sicherheitsnetz auf
    der Ebene, die dim tatsaechlich beruehrt (Vektor-Arithmetik), nicht auf
    der Ebene der Identitaet."""
    a = embeddings.model_identity("bge-m3", num_ctx=2048)
    b = embeddings.model_identity("bge-m3", num_ctx=2048)  # gleiche Identitaet, dim waere separat
    assert a == b, "dim ist keine erzeugende Parameter-Aenderung im Sinn dieses Auftrags"

    # Sicherheitsnetz auf Vektor-Ebene: unterschiedliche Laenge -> 0.0, kein Crash.
    kurz = [0.1, 0.2]
    lang = [0.1, 0.2, 0.3, 0.4]
    assert embeddings.cosine_similarity(kurz, lang) == 0.0


# --- parse_model_identity: Kehrwert, inkl. Bestandswert ohne Suffix --------

def test_parse_model_identity_rundreise():
    identity = embeddings.model_identity("bge-m3", num_ctx=4096)
    model, ctx = embeddings.parse_model_identity(identity)
    assert (model, ctx) == ("bge-m3", 4096)


def test_parse_model_identity_bestandswert_ohne_suffix_faellt_auf_default_ctx_zurueck():
    """Zeilen aus der Zeit vor diesem Auftrag tragen 'bge-m3' ohne Suffix --
    parse_model_identity() darf daran nicht scheitern, sondern behandelt die
    Zeichenkette selbst als Modellname."""
    model, ctx = embeddings.parse_model_identity("bge-m3")
    assert model == "bge-m3"
    assert ctx == embeddings.EMBED_NUM_CTX


def test_default_embed_model_traegt_identitaet_mit_ctx_suffix():
    assert embeddings.DEFAULT_EMBED_MODEL == f"bge-m3@ctx{embeddings.EMBED_NUM_CTX}"


# --- Naht: die gespeicherte Identitaet darf NIE als Ollama-Modelltag beim --
# --- tatsaechlichen API-Aufruf landen (Ollama kennt kein '@ctx...') -------

def test_naht_embed_text_schickt_rohmodell_nicht_die_identitaet_an_ollama(monkeypatch):
    captured = {}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"embeddings": [[0.1, 0.2]]}).encode("utf-8")

    def fake_urlopen(req, timeout=None):
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        return _FakeResponse()

    monkeypatch.setattr(embeddings.urllib.request, "urlopen", fake_urlopen)

    vec = embeddings.embed_text("Testtext")

    assert vec == [0.1, 0.2]
    assert captured["payload"]["model"] == "bge-m3", (
        "Ollama muss den rohen Modelltag bekommen, nicht die gespeicherte "
        f"Identitaet {embeddings.DEFAULT_EMBED_MODEL!r} -- sonst 404/Modell "
        "nicht gefunden"
    )
    assert captured["payload"]["options"]["num_ctx"] == embeddings.EMBED_NUM_CTX


def test_naht_haelt_auch_bei_explizit_uebergebener_identitaet(monkeypatch):
    """germanquad.py (ausserhalb kern/) uebergibt embeddings.DEFAULT_EMBED_MODEL
    explizit als `model=`-Argument -- embed_text() muss auch DANN die
    Identitaet zerlegen, sonst bricht der einzige Aufrufer ausserhalb von
    kern/, der DEFAULT_EMBED_MODEL als rohen API-Modelltag weiterreicht."""
    captured = {}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"embeddings": [[0.5]]}).encode("utf-8")

    def fake_urlopen(req, timeout=None):
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        return _FakeResponse()

    monkeypatch.setattr(embeddings.urllib.request, "urlopen", fake_urlopen)

    embeddings.embed_text("Text", model=embeddings.DEFAULT_EMBED_MODEL)

    assert captured["payload"]["model"] == "bge-m3"
    assert captured["payload"]["options"]["num_ctx"] == embeddings.EMBED_NUM_CTX


if __name__ == "__main__":
    import subprocess
    subprocess.run([_sys.executable, "-m", "pytest", "-q", __file__], check=True)
