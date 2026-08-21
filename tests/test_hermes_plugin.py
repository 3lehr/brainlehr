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
    """Positivkontrolle ueber den vollen Weg: Bestand da, Ausweis gesetzt,
    Einbettungsdienst erreichbar (ein lokaler Dummy-Server genuegt -- es geht
    um Erreichbarkeit, nicht um eine echte Ollama-Antwort)."""
    import http.server
    import threading as _threading

    server = http.server.HTTPServer(("127.0.0.1", 0), http.server.BaseHTTPRequestHandler)
    faden = _threading.Thread(target=server.serve_forever, daemon=True)
    faden.start()
    try:
        monkeypatch.setenv("BRAINLEHR_HOME", str(REPO))
        monkeypatch.setenv("BRAINLEHR_AUSWEIS", "test-ausweis")
        monkeypatch.setenv("KNOWLEDGE_OLLAMA_URL", f"http://127.0.0.1:{server.server_port}")
        assert bp.BrainlehrProvider().is_available() is True
    finally:
        server.shutdown()


def test_nicht_verfuegbar_ohne_ausweis(monkeypatch):
    """NEGATIVFALL (B4/Ausweis): Bestand und Dienst da, aber kein Ausweis --
    genau der Fall, der bisher STILL scheiterte (jeder Schreibvorgang vom
    Trigger abgewiesen, ohne dass das Menue etwas davon zeigte)."""
    import http.server
    import threading as _threading

    server = http.server.HTTPServer(("127.0.0.1", 0), http.server.BaseHTTPRequestHandler)
    faden = _threading.Thread(target=server.serve_forever, daemon=True)
    faden.start()
    try:
        monkeypatch.setenv("BRAINLEHR_HOME", str(REPO))
        monkeypatch.delenv("BRAINLEHR_AUSWEIS", raising=False)
        monkeypatch.setenv("KNOWLEDGE_OLLAMA_URL", f"http://127.0.0.1:{server.server_port}")
        assert bp.BrainlehrProvider().is_available() is False
    finally:
        server.shutdown()


def test_nicht_verfuegbar_ohne_einbettungsdienst(monkeypatch):
    """NEGATIVFALL (Einbettungsdienst): Bestand und Ausweis da, aber die
    Adresse ist unerreichbar -- eine unbenutzte Portnummer auf localhost
    genuegt, kein echtes Netz noetig. Ohne diese Pruefung entstehen Eintraege
    ohne Vektor, ohne dass ein Fehler erscheint (2026-08-20, dreizehnmal)."""
    monkeypatch.setenv("BRAINLEHR_HOME", str(REPO))
    monkeypatch.setenv("BRAINLEHR_AUSWEIS", "test-ausweis")
    monkeypatch.setenv("KNOWLEDGE_OLLAMA_URL", "http://127.0.0.1:1")
    assert bp.BrainlehrProvider().is_available() is False


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


def _lade_config_schema():
    """Laedt config_schema.py GENAU WIE HERMES ES TUT: per Dateipfad via
    importlib, nicht per Paketimport (siehe get_provider_config_schema in
    hermes_cli/web_server.py). Das ist der einzige Weg, der auch eine Datei
    findet, deren einzige Importquelle `plugins.memory.config_schema` ist --
    ein Paketimport aus brainlehrs eigenem Repo koennte diesen Pfad gar nicht
    aufloesen."""
    import importlib.util
    import os as _os

    hermes_agent = Path(_os.environ.get(
        "HERMES_AGENT_HOME", str(Path.home() / ".hermes" / "hermes-agent")))
    if not (hermes_agent / "plugins" / "memory" / "config_schema.py").is_file():
        import pytest
        pytest.skip("Hermes nicht installiert -- config_schema.py braucht "
                     "plugins.memory.config_schema aus dem echten Hermes")
    sys.path.insert(0, str(hermes_agent))

    pfad = REPO / "integrations" / "hermes" / "plugin" / "config_schema.py"
    spec = importlib.util.spec_from_file_location("_test_brainlehr_config_schema", pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul.CONFIG_SCHEMA


def test_config_schema_laedt_wie_hermes():
    """VORHER ROT: die Datei existierte nicht. Laedt per Pfad, wie Hermes'
    eigener `get_provider_config_schema()` es tut."""
    schema = _lade_config_schema()
    assert schema.name == "brainlehr"
    assert len(schema.fields) > 0


def test_sechs_felder_inline():
    """Der Schnitt aus PLAN_NAECHSTE_STUFE_2026-08-21.md §4b: genau sechs
    Felder im kompakten Panel, der Rest im vollen Dialog."""
    schema = _lade_config_schema()
    inline = schema.inline_fields()
    assert len(inline) == 6
    assert {f.key for f in inline} == {
        "db_path", "ausweis", "betriebsprofil", "mandant",
        "embed_service_url", "oberflaechensprache",
    }


def test_jedes_feld_hat_beide_sprachen():
    """ADR-033: jeder NEU geschriebene nutzersichtbare Text entsteht
    zweisprachig. NEGATIVTEST: eine deutsche Beschreibung ohne die mit
    'English: ' markierte englische Haelfte faellt durch."""
    schema = _lade_config_schema()
    for feld in schema.fields:
        assert feld.description, f"{feld.key} hat keine Beschreibung"
        assert "English: " in feld.description, (
            f"{feld.key} hat keine englische Fassung")
        de, _, en = feld.description.partition("English: ")
        assert de.strip() and en.strip(), f"{feld.key}: eine Haelfte ist leer"
        for option in feld.options:
            if option.description:
                assert "English: " in option.description, (
                    f"{feld.key}/{option.value} hat keine englische Fassung")


def test_embed_model_hat_genau_eine_option():
    """Das gefaehrliche Feld: eine Aenderung entwertet 7409 Vektoren, ohne
    dass ein Fehler erscheint. Ausweg ohne Aenderung an Hermes: KIND_SELECT
    mit GENAU EINER Option. NEGATIVTEST: mehr als eine Option ist ein Fehler."""
    schema = _lade_config_schema()
    embed_model = next(f for f in schema.fields if f.key == "embed_model")
    assert embed_model.kind == "select"
    assert len(embed_model.options) == 1


# ── Proben, die OHNE brainlehr-Bestand laufen ────────────────────────────────
# Alles darueber setzt eine vorhandene Datenbank voraus und ist damit nur auf
# einem eingerichteten Rechner aussagekraeftig. Ein fremder Pruefer -- etwa
# jemand, der diesen Beitrag bei Hermes durchsieht -- hat die nicht. Was hier
# folgt, belegt trotzdem etwas und braucht nichts als das Plugin selbst.

PLUGIN = REPO / "integrations" / "hermes" / "plugin"


def test_kein_pfad_dieses_rechners():
    """Ein absoluter Pfad EINES Rechners im Plugin ist auf jedem anderen
    Rechner ein stiller Fehlgriff: nichts stuerzt ab, es wird nur nichts
    gefunden. VORHER ROT -- `brainlehr_provider.py` trug
    `/Volumes/daten/...` als Rueckfall, die README als Installationszeile."""
    verdaechtig = ("/Volumes/daten", "/Users/lehrmacbook", "/home/")
    for datei in sorted(PLUGIN.glob("*.py")) + sorted(PLUGIN.glob("*.md")):
        text = datei.read_text(encoding="utf-8")
        for zeile_nr, zeile in enumerate(text.splitlines(), 1):
            for muster in verdaechtig:
                assert muster not in zeile, (
                    f"{datei.name}:{zeile_nr} nennt einen Pfad dieses "
                    f"Rechners: {zeile.strip()[:100]}")


def test_kein_bibliotheksimport_von_brainlehr():
    """Der Adapter spricht brainlehr ueber MCP an, nicht als Bibliothek.

    Das ist zuerst eine BAUFRAGE: wer `knowledge_mcp_server` importiert, kennt
    die Interna und bricht an jeder internen Aenderung; ueber die Schnittstelle
    bricht er nicht. VORHER ROT -- es gab drei solche Importstellen in
    `brainlehr_provider.py` plus eine in `config_schema.py`.

    Geprueft wird am SYNTAXBAUM, nicht am Text. Ein Textmuster faende auch
    jede Erwaehnung in einem Kommentar -- und genau das ist hier haeufig, weil
    die Docstrings den alten Bau erklaeren. Ein Waechter, der seine eigene
    Begruendung beanstandet, wird umformuliert statt befolgt."""
    import ast

    fremd = {"knowledge_mcp_server", "ort", "embeddings", "kern", "haken",
             "werkzeugrechte", "trennung", "ausweis"}
    for datei in sorted(PLUGIN.glob("*.py")):
        baum = ast.parse(datei.read_text(encoding="utf-8"), filename=str(datei))
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.Import):
                namen = [a.name.split(".")[0] for a in knoten.names]
            elif isinstance(knoten, ast.ImportFrom):
                namen = [(knoten.module or "").split(".")[0]]
            else:
                continue
            for name in namen:
                assert name not in fremd, (
                    f"{datei.name}:{knoten.lineno} laedt brainlehrs `{name}` in "
                    "den eigenen Prozess, statt ueber MCP zu sprechen")


def test_syntaxbaum_waechter_wuerde_anschlagen():
    """POSITIVKONTROLLE zum Waechter darueber. Ohne sie belegt ein gruener
    Lauf nur, dass nichts gefunden WURDE -- nicht, dass etwas gefunden
    WUERDE. Genau die Klasse, in der ein Test gruen steht, weil der gepruefte
    Fall gar nicht eintreten kann."""
    import ast

    fremd = {"knowledge_mcp_server", "ort", "embeddings"}
    getroffen = []
    for knoten in ast.walk(ast.parse(
            "import json\nimport knowledge_mcp_server as kms\n"
            "from ort import DB\n")):
        if isinstance(knoten, ast.Import):
            getroffen += [a.name.split(".")[0] for a in knoten.names]
        elif isinstance(knoten, ast.ImportFrom):
            getroffen.append((knoten.module or "").split(".")[0])
    assert set(getroffen) & fremd == {"knowledge_mcp_server", "ort"}
    assert "json" not in fremd, "die Stdlib darf der Waechter nie beanstanden"


def test_ohne_brainlehr_sauber_nicht_verfuegbar(tmp_path, monkeypatch, caplog):
    """DIE PROBE FUER DEN FREMDEN RECHNER: nichts eingerichtet, nichts
    erreichbar. Erwartet wird sauberes False MIT Grund -- kein Absturz und
    kein stilles False, das fuer den Nutzer wie 'gibt es hier nicht' aussieht.

    VORHER ROT in beide Richtungen: ohne gesetzte Variablen griff der alte
    Stand auf den fest verdrahteten Pfad DIESES Rechners zurueck, und sein
    False nannte nie einen Grund."""
    import logging

    monkeypatch.setenv("BRAINLEHR_HOME", str(tmp_path / "gibtsnicht"))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "kein-hermes"))
    monkeypatch.delenv("BRAINLEHR_MCP_COMMAND", raising=False)

    p = bp.BrainlehrProvider()
    with caplog.at_level(logging.WARNING):
        assert p.is_available() is False
    assert p.grund, "ein False ohne Grund ist fuer den Nutzer nicht auswertbar"
    assert "brainlehr" in caplog.text.lower(), "der Grund fehlt im Log"
    # Der Grund muss SAGEN, wo gesucht wurde -- sonst weiss der Nutzer nicht,
    # welche Einstellung ihm fehlt.
    assert "brainlehr_home" in p.grund and "mcp_command" in p.grund
    # ... und darf danach nicht doch noch abstuerzen.
    assert p.backup_paths() == []
    assert p._suchen("irgendwas") == []


def test_startbefehl_wird_abgeleitet_nicht_verdrahtet(tmp_path, monkeypatch):
    """Ohne Fundort gibt es keinen Befehl -- statt heimlich auf einen
    Vorgabepfad zu raten. Und ein gesetzter `mcp_command` sticht alles."""
    monkeypatch.setenv("BRAINLEHR_HOME", str(tmp_path / "gibtsnicht"))
    monkeypatch.delenv("BRAINLEHR_MCP_COMMAND", raising=False)
    assert bp._server_befehl({}) is None

    monkeypatch.setenv("BRAINLEHR_MCP_COMMAND", "python3 -u /anderswo/server.py")
    assert bp._server_befehl({}) == ["python3", "-u", "/anderswo/server.py"]


def test_alle_feldbeschreibungen_zweisprachig_ohne_hermes():
    """Wie `test_jedes_feld_hat_beide_sprachen`, aber am QUELLTEXT statt am
    geladenen Schema -- denn das Laden braucht ein installiertes Hermes, und
    genau daran scheitert ein fremder Pruefer, der nur dieses Repo hat.
    ADR-033: jeder neu geschriebene nutzersichtbare Text ist zweisprachig."""
    import re

    quelle = (PLUGIN / "config_schema.py").read_text(encoding="utf-8")
    aufrufe = re.findall(r"_bi\(\s*(.*?)\s*\)\s*,\n", quelle, re.S)
    assert len(aufrufe) >= 10, f"nur {len(aufrufe)} zweisprachige Texte gefunden"
    for text in aufrufe:
        assert '"' in text, "ein _bi()-Aufruf ohne Zeichenketten"
    # NEGATIVPROBE: jedes Feld mit `description=` geht durch _bi(), keines
    # traegt eine nackte Zeichenkette.
    for treffer in re.finditer(r"description=(.{0,12})", quelle):
        assert treffer.group(1).lstrip().startswith("_bi("), (
            f"eine Beschreibung umgeht _bi(): {treffer.group(0)!r}")
