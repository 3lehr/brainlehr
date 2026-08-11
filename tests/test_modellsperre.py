"""Pruefstein zu L-a69129 (drei Vorkommen am 2026-08-09, zur Regel eskaliert).

Der Betreiber hat am 2026-08-07 entschieden: Haiku fuer die Prueflaeufe.
Dreimal lief an einem Tag trotzdem ein Prueflauf gegen ein lokales
Erzeugungsmodell, jedes Mal vom Betreiber bemerkt, nie vom Assistenten:
pruefkorpus.py mit seinem Vorgabewert (gemma4:12b, 45 Faelle in 30 Minuten
statt 55 in 2,6 Minuten) und wissensnutzen_blind.py, dessen Ergebnis
dadurch unbrauchbar war.

Gemeinsame Engstelle aller drei Faelle: schreiblauf._call_with_retry --
der einzige Erzeugungsaufruf, den die Messwerkzeuge teilen. Er geht
ausschliesslich gegen das lokale Ollama; ein Modellname taucht in keiner
Kommandozeile auf, sondern steht als Vorgabewert im Modul. Darum greift
die Sperre dort und nicht in einem Melder auf geaenderten Code (Fall 2/3
aenderten keine Zeile) und nicht in einem Haltepunkt vor dem Start (der
Modellname steht nicht im Aufruf). Herleitung der Ortswahl: L-358e31.

Zwei Siebe, beide hier geprueft: die ROLLE am Aufrufort (was ist dieser
Aufruf) und die LAUFZEIT-FREIGABE BRAINLEHR_LOKAL fuer 'erzeugen'. Die
Rolle 'beantworten' ist auch mit Freigabe gesperrt -- das ist die
Verschaerfung gegenueber dem Entwurf vom 2026-08-09.

Nichts hier ruft Ollama an: _call_ollama wird gestubbt, die Sperre sitzt
davor.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))
sys.path.insert(0, str(SHARED_KNOWLEDGE / "schreibpruefstand"))

import embeddings  # noqa: E402
import schreiblauf as sl  # noqa: E402


@pytest.fixture(autouse=True)
def _kein_netz_und_keine_freigabe(monkeypatch):
    monkeypatch.delenv("BRAINLEHR_LOKAL", raising=False)
    monkeypatch.setattr(sl, "_call_ollama", lambda prompt, **kw: ("42", None))


def _wissensnutzen_blind():
    sys.path.insert(0, str(SHARED_KNOWLEDGE / "haken"))
    import wissensnutzen_blind
    return wissensnutzen_blind


# --- rot vor gruen: die gemessenen Faelle ----------------------------------

def test_guetemessung_gegen_lokales_modell_schlaegt_an():
    """wissensnutzen_blind.run_cell ist die zentrale Nutzenmessung des
    2026-08-09. Sie lief gegen gemma4:12b/gemma4:e4b und war unbrauchbar."""
    wnb = _wissensnutzen_blind()
    with pytest.raises(RuntimeError) as exc:
        wnb.run_cell("Wie viele Zacken haben drei Glimberge?", "gemma4:12b")
    assert "gemma4:12b" in str(exc.value)


def test_korpuslauf_mit_vorgabemodell_schlaegt_an():
    """Fall 2: pruefkorpus.py mit seinem Vorgabewert MODEL = sl.DEFAULT_MODEL."""
    import pruefkorpus
    assert pruefkorpus.MODEL == sl.DEFAULT_MODEL == "gemma4:12b"
    with pytest.raises(RuntimeError):
        pruefkorpus._generate("Formuliere eine Aufgabe.")


# --- Negativfall: absichtlich lokal darf NICHT anschlagen -------------------

def test_ausdruecklich_beauftragter_lokaler_lauf_schlaegt_nicht_an(monkeypatch):
    """'Korpus-Erzeugung, wenn sie ausdruecklich so beauftragt wird' --
    ausdruecklich heisst zur Laufzeit, nicht als Zeile im Quelltext."""
    monkeypatch.setenv("BRAINLEHR_LOKAL", "1")
    import pruefkorpus
    raw, err, _ = pruefkorpus._generate("Formuliere eine Aufgabe.")
    assert (raw, err) == ("42", None)


def test_lokales_modell_als_gegenstand_schlaegt_nicht_an():
    """Der Schreibpruefstand misst das lokale Modell selbst -- dort ist es
    das Messobjekt, nicht das Messgeraet."""
    raw, err, retries = sl._call_with_retry(
        "x", model=sl.DEFAULT_MODEL, base_url=sl.DEFAULT_OLLAMA_URL,
        timeout=1.0, rolle="messobjekt")
    assert (raw, err, retries) == ("42", None, 0)


def test_einbettung_schlaegt_nicht_an(monkeypatch):
    """bge-m3 laeuft absichtlich lokal und nimmt einen anderen Weg
    (/api/embed statt /api/generate) -- die Sperre darf ihn nicht sehen."""
    class _Antwort:
        def read(self):
            return b'{"embeddings": [[0.1, 0.2]]}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(embeddings.urllib.request, "urlopen", lambda req, timeout=5.0: _Antwort())
    assert embeddings.embed_text("Glimberg", model="bge-m3") == pytest.approx([0.1, 0.2])


# --- Grenzwert: was ist ueberhaupt ein lokales Erzeugungsmodell -------------

def test_nichtlokale_gegenstelle_schlaegt_nicht_an():
    raw, err, _ = sl._call_with_retry(
        "x", model="claude-haiku-4-5", base_url="https://api.example.invalid",
        timeout=1.0, rolle="erzeugen")
    assert (raw, err) == ("42", None)


# --- Gegenprobe: Zusicherung entwerten -------------------------------------

def test_gegenprobe_entwertete_zusicherung_schlaegt_an():
    """Dieselbe Stelle wie test_lokales_modell_als_gegenstand..., nur ohne
    die Zusicherung: dann muss es anschlagen."""
    with pytest.raises(RuntimeError):
        sl._call_with_retry(
            "x", model=sl.DEFAULT_MODEL, base_url=sl.DEFAULT_OLLAMA_URL,
            timeout=1.0, rolle="erzeugen")


def test_gegenprobe_schreiblauf_ohne_zusicherung_schlaegt_an(monkeypatch):
    """Und ueber den echten Aufrufweg: nimmt man schreiblauf.run() seine
    Zusicherung weg, faellt der Schreibpruefstand in die Sperre."""
    monkeypatch.setattr(sl, "LOKAL_IST_MESSOBJEKT", False)
    with pytest.raises(RuntimeError):
        sl.run(pieces=["Ein Glimberg hat 7 Zacken."])


# --- Die Verschaerfung: 'beantworten' ist nicht freigebbar -----------------

def test_antwortlauf_bleibt_auch_mit_freigabe_gesperrt(monkeypatch):
    """Die Umgebungsvariable oeffnet die Korpus-Erzeugung, nicht das
    Beantworten. Sonst waere sie nach drei Vorkommen genau die Hintertuer,
    die man sich angewoehnt -- und der dritte Fall lief ueber einen
    Antwortpfad."""
    monkeypatch.setenv("BRAINLEHR_LOKAL", "1")
    with pytest.raises(RuntimeError) as exc:
        sl._call_with_retry(
            "x", model=sl.DEFAULT_MODEL, base_url=sl.DEFAULT_OLLAMA_URL,
            timeout=1.0, rolle="beantworten")
    assert "BRAINLEHR_LOKAL" in str(exc.value)


def test_unbekannte_rolle_wird_abgewiesen():
    """Ein Schreibfehler in der Rolle waere sonst ein stilles Loch."""
    with pytest.raises(ValueError):
        sl._call_with_retry(
            "x", model=sl.DEFAULT_MODEL, base_url=sl.DEFAULT_OLLAMA_URL,
            timeout=1.0, rolle="Beantworten")
