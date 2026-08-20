"""Der brainlehr-Provider fuer Hermes.

DER ANLASS (2026-08-20): Hermes bietet unter Einstellungen einen "Memory
Provider" an -- acht Anbieter zur Auswahl, brainlehr nicht darunter:
byterover, hindsight, holographic, honcho, mem0, openviking, retaindb,
supermemory. Gemessen ueber `hermes memory status`: sieben der acht brauchen
einen API-Schluessel, nur holographic laeuft rein lokal. Genau die Nische, in
der brainlehr steht.

WO DAS PLUGIN LIEGEN MUSS, und das ist die Falle:
`~/.hermes/plugins/<name>/` -- der NUTZERBEREICH. Der naheliegende Ort waere
`hermes-agent/plugins/memory/<name>/` gewesen, wo die acht mitgelieferten
liegen; der wird beim naechsten Hermes-Update ueberschrieben. Dieselbe Klasse
wie die MIT-Lizenz am selben Tag: etwas an einen Ort legen, den ein Neuanlegen
zuruecksetzt, und es dann nie wieder ansehen.

Erkannt wird ein Provider per Textsuche in den ersten 8192 Zeichen seiner
`__init__.py` nach "MemoryProvider" oder "register_memory_provider"
(plugins/memory/__init__.py::_is_memory_provider_dir). Kein Import, kein
Manifest -- ein blosser Textscan. Wer das nicht weiss, baut ein korrektes
Plugin, das nie gefunden wird.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "integrations" / "hermes" / "plugin"))
import brainlehr_provider as bp  # noqa: E402


def test_ohne_hermes_ladbar():
    """Das Plugin liegt in brainlehrs Repo und muss dort pruefbar sein --
    ohne installiertes Hermes. Sonst ist es nur auf genau einem Rechner
    testbar, und das ist derselbe Rechner, auf dem es sowieso laeuft."""
    assert bp.BrainlehrProvider is not None


def test_name_ist_der_ordnername():
    """Hermes leitet den Anbieternamen aus dem Verzeichnis ab -- weicht die
    Eigenschaft davon ab, findet der Nutzer im Menue einen anderen Namen als
    im Dateisystem."""
    assert bp.BrainlehrProvider().name == "brainlehr"


def test_wird_von_hermes_als_memory_provider_erkannt():
    """DIE PROBE, die kein Funktionstest ersetzt: Hermes sucht per TEXTSCAN in
    den ersten 8192 Zeichen. Ein Provider, der alles richtig macht und dieses
    Wort erst in Zeile 300 fuehrt, erscheint nie im Menue."""
    quelle = (REPO / "integrations" / "hermes" / "plugin"
              / "__init__.py").read_text(encoding="utf-8")[:8192]
    assert "MemoryProvider" in quelle or "register_memory_provider" in quelle


def test_manifest_vollstaendig():
    import yaml
    p = REPO / "integrations" / "hermes" / "plugin" / "plugin.yaml"
    meta = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert meta["name"] == "brainlehr"
    assert meta.get("description"), "die Beschreibung steht im Auswahlmenue"


def test_nicht_verfuegbar_ohne_bestand(tmp_path, monkeypatch):
    """NEGATIVFALL: is_available darf keine Netzaufrufe machen und muss bei
    fehlendem Bestand sauber False liefern -- sonst erscheint brainlehr im
    Menue und scheitert erst beim Benutzen."""
    monkeypatch.setenv("BRAINLEHR_HOME", str(tmp_path / "gibtsnicht"))
    assert bp.BrainlehrProvider().is_available() is False


def test_verfuegbar_mit_bestand(monkeypatch):
    monkeypatch.setenv("BRAINLEHR_HOME", str(REPO))
    assert bp.BrainlehrProvider().is_available() is True


def test_werkzeuge_haben_openai_form():
    """Hermes erwartet OpenAI-Function-Calling-Form, nicht MCP-Form."""
    schemas = bp.BrainlehrProvider().get_tool_schemas()
    assert schemas, "ohne Werkzeuge waere brainlehr nur ein Kontextlieferant"
    for s in schemas:
        assert set(s) >= {"name", "description", "parameters"}
        assert s["parameters"]["type"] == "object"


def test_schreibt_nicht_aus_nebenlaeufigen_kontexten():
    """Die Schnittstelle warnt ausdruecklich: 'Providers should skip writes for
    non-primary contexts (cron system prompts would corrupt user
    representations)'. Ein Speicher, der Cron-Systemprompts als Wissen
    aufnimmt, vergiftet sich selbst."""
    p = bp.BrainlehrProvider()
    p.initialize("s1", hermes_home="/tmp", platform="cron", agent_context="cron")
    assert p.darf_schreiben is False
    p2 = bp.BrainlehrProvider()
    p2.initialize("s2", hermes_home="/tmp", platform="cli", agent_context="primary")
    assert p2.darf_schreiben is True
