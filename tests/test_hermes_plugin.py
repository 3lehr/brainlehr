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


# ---------------------------------------------------------------------------
# Hermes' eigene Liste fuer eigenstaendige Plugins (CONTRIBUTING.md 70-104):
# sync_turn / post_setup / register_cli / pip-Eintragspunkt.
# ---------------------------------------------------------------------------

class _FakeKlient:
    """Ein MCP-Klient, der nur mitschreibt, was ihm aufgetragen wurde.

    Kein Prozess, kein stdio -- die Frage dieser Tests ist NICHT, ob brainlehr
    antwortet, sondern OB und MIT WELCHER HERKUNFT geschrieben wird. Ein echter
    Server wuerde genau diese Frage verdecken (die Antwort saehe gleich aus,
    ob geschrieben wurde oder nicht)."""

    def __init__(self):
        self.rufe = []

    def ruf(self, werkzeug, argumente, frist=None):
        self.rufe.append((werkzeug, argumente))
        return {"node_id": "test0000"}

    def werkzeugnamen(self, frist=15.0):
        return ["knowledge_search", "knowledge_add", "knowledge_stats"]

    def stop(self):
        pass


def _provider_mit_fake(mitschrift, sitzung="s-abc", kontext="primary"):
    p = bp.BrainlehrProvider()
    p.initialize(sitzung, hermes_home="/tmp", platform="cli",
                 agent_context=kontext)
    p._klient = _FakeKlient()
    p.mitschrift = mitschrift
    return p


def _schreibrufe(p):
    return [a for (w, a) in p._klient.rufe if w == "knowledge_add"]


# -- 1. sync_turn -----------------------------------------------------------

def test_sync_turn_existiert():
    """VORHER ROT: die Methode fehlte ganz. Hermes' Liste nennt sie neben
    prefetch und shutdown als Pflichtteil des ABC -- ein Plugin ohne sie ist
    kein eigenstaendiges Plugin nach ihrer Anleitung, egal wie gut der Rest
    ist."""
    assert callable(getattr(bp.BrainlehrProvider, "sync_turn", None))


def test_sync_turn_schreibt_per_vorgabe_nichts(caplog):
    """Die Entscheidung, und ihr Negativfall: per Vorgabe entsteht KEIN
    Eintrag. Ein Zug-fuer-Zug-Automat kann keine geprueft
    Aussage liefern -- er kann nur bezeugen, dass etwas gesagt wurde.

    Und der Teil, der diesen Test ueberhaupt noetig macht: stillschweigend
    nichts zu tun waere der schlechtere Zustand. Der Grund muss sichtbar
    werden."""
    import logging
    p = _provider_mit_fake(mitschrift=False)
    with caplog.at_level(logging.INFO):
        p.sync_turn("Wie hoch ist die Schwelle?", "Sie liegt bei 0,65.")
    assert _schreibrufe(p) == [], "per Vorgabe darf nichts entstehen"
    assert p.mitschrift_grund, "ein stummes Nichtstun ist ausdruecklich unzulaessig"
    assert any("mitschrift" in r.getMessage().lower() for r in caplog.records), \
        "der Grund muss im Log stehen, nicht nur in einem Attribut"


def test_sync_turn_schreibt_eingeschaltet_mit_weg_als_herkunft():
    """Eingeschaltet entsteht ein Eintrag -- und seine Herkunft nennt den WEG
    (Sitzung, Zug, Zeitpunkt), nicht eine behauptete Quelle. Dieselbe Trennung
    wie bei Fremdimporten (`BDW-P12`)."""
    p = _provider_mit_fake(mitschrift=True)
    p.sync_turn("Wie hoch ist die Schwelle?", "Sie liegt bei 0,65.")
    rufe = _schreibrufe(p)
    assert len(rufe) == 1, "genau ein Eintrag je Zug"
    quelle = rufe[0]["source"]
    assert bp._ist_weg_herkunft(quelle), quelle
    assert "s-abc" in quelle and "Zug 1" in quelle


def test_behauptete_quelle_wird_abgewiesen():
    """NEGATIVTEST: eine Herkunft, die eine QUELLE behauptet ('laut dem
    Betreiber'), ist keine Weg-Herkunft und darf nicht durchgehen. Ohne diese
    Probe waere die Weg-Form eine Absicht und keine Schranke."""
    assert not bp._ist_weg_herkunft("laut dem Betreiber")
    assert not bp._ist_weg_herkunft("aus einem Gespraech")
    assert not bp._ist_weg_herkunft("")
    p = _provider_mit_fake(mitschrift=True)
    p._herkunft_bauer = lambda *a, **k: "laut dem Betreiber"
    p.sync_turn("Frage", "Antwort")
    assert _schreibrufe(p) == [], \
        "eine behauptete Quelle muss den Schreibvorgang verhindern"


def test_sync_turn_schweigt_in_nebenlaeufigen_kontexten():
    """Auch eingeschaltet schreibt ein Cron-Lauf nicht -- dieselbe Schranke,
    die schon fuer brainlehr_merken gilt."""
    p = _provider_mit_fake(mitschrift=True, kontext="cron")
    p.sync_turn("Frage", "Antwort")
    assert _schreibrufe(p) == []


# -- 2. post_setup ----------------------------------------------------------

def test_post_setup_existiert():
    """VORHER ROT. `hermes memory setup` uebergibt ab hier vollstaendig an den
    Anbieter (hermes_cli/memory_setup.py:325-329: 'delegate entirely to it')
    -- ohne die Methode laeuft nur der allgemeine Weg."""
    assert callable(getattr(bp.BrainlehrProvider, "post_setup", None))


def test_post_setup_schreibt_konfig_und_aktiviert(tmp_path, monkeypatch):
    """Die vier Dinge des Einrichtungsassistenten landen in
    $HERMES_HOME/brainlehr/config.json, und der Anbieter wird aktiviert --
    genau das, was der allgemeine Weg sonst tut und was post_setup uebernimmt,
    wenn es existiert."""
    import json as _json
    antworten = iter(["/pfad/zur/brainlehr.db", "hermes-nutzer",
                      "http://127.0.0.1:11434", "einzelplatz"])
    monkeypatch.setattr(bp, "_frage", lambda *a, **k: next(antworten))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    konfig = {}
    bp.BrainlehrProvider().post_setup(str(tmp_path), konfig)

    geschrieben = _json.loads(
        (tmp_path / "brainlehr" / "config.json").read_text(encoding="utf-8"))
    assert geschrieben["db_path"] == "/pfad/zur/brainlehr.db"
    assert geschrieben["ausweis"] == "hermes-nutzer"
    assert geschrieben["embed_service_url"] == "http://127.0.0.1:11434"
    assert geschrieben["betriebsprofil"] == "einzelplatz"
    assert konfig["memory"]["provider"] == "brainlehr", \
        "post_setup uebernimmt die Aktivierung -- sonst tut sie niemand"


# -- 3. cli.py --------------------------------------------------------------

def _lade_cli():
    import importlib.util
    pfad = REPO / "integrations" / "hermes" / "plugin" / "cli.py"
    if not pfad.is_file():
        raise AssertionError(f"{pfad} fehlt")
    spec = importlib.util.spec_from_file_location("_test_brainlehr_cli", pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def test_cli_bietet_register_cli():
    """VORHER ROT: cli.py existierte nicht. discover_plugin_cli_commands()
    sucht genau diesen Namen."""
    assert callable(getattr(_lade_cli(), "register_cli", None))


def test_cli_handler_heisst_wie_hermes_ihn_sucht():
    """DIE FALLE: Hermes holt den Handler ueber
    `getattr(cli_mod, f"{provider}_command")` -- also `brainlehr_command`.
    Ein anders benannter Handler wird still nicht gefunden, und der Befehl
    steht dann ohne Wirkung im Menue."""
    assert callable(getattr(_lade_cli(), "brainlehr_command", None))


def test_cli_pruefen_meldet_grund_statt_abzustuerzen(tmp_path, monkeypatch, capsys):
    """DIE HAERTEPROBE, jetzt ueber die Kommandozeile: ohne erreichbaren
    Server ein sauberer Grund, kein Absturz. Das ist die Diagnose, die ein
    fremder Nutzer bei Problemen zuerst braucht."""
    import argparse
    monkeypatch.setenv("BRAINLEHR_HOME", str(tmp_path))   # leer, kein MERKMAL
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    cli = _lade_cli()
    rc = cli.brainlehr_command(argparse.Namespace(brainlehr_befehl="pruefen"))
    ausgabe = capsys.readouterr().out
    assert rc != 0, "unbrauchbar muss sich auch am Rueckgabewert zeigen"
    assert "brainlehr" in ausgabe.lower() and len(ausgabe.strip()) > 40, ausgabe


# -- 4. pip-Eintragspunkt ---------------------------------------------------

def test_pip_eintragspunkt_in_hermes_gruppe():
    """VORHER ROT: es gab keine Paketdatei. Die Gruppe heisst
    `hermes_agent.plugins` (hermes_cli/plugins.py::ENTRY_POINTS_GROUP) -- der
    einzige Gruppenname, den Hermes ueberhaupt liest."""
    import tomllib
    pfad = REPO / "integrations" / "hermes" / "plugin" / "pyproject.toml"
    assert pfad.is_file(), f"{pfad} fehlt"
    daten = tomllib.loads(pfad.read_text(encoding="utf-8"))
    eintraege = daten["project"]["entry-points"]["hermes_agent.plugins"]
    assert "brainlehr" in eintraege, eintraege


def test_mitschrift_ist_im_panel_schaltbar():
    """Die Einstellung, ueber die sync_turn eingeschaltet wird, muss im Panel
    stehen -- sonst ist 'einschaltbar' eine Behauptung ueber eine Variable,
    die niemand findet."""
    schema = _lade_config_schema()
    schluessel = {f.key for f in schema.fields}
    assert "mitschrift" in schluessel, sorted(schluessel)


def test_cli_pruefen_nennt_die_zahl_die_der_server_wirklich_liefert(monkeypatch, capsys):
    """VORHER ROT und am laufenden Server GEMESSEN, nicht vermutet: die
    Diagnose las `total_nodes`, `knowledge_stats` liefert aber `nodes_total`
    (5251 Knoten am 2026-08-21). Das ist die stille Sorte -- kein Fehler, nur
    ein '?' an der Stelle, an der die Zahl stehen sollte. Ein Schluesselname
    ist nichts, was man aus dem Kopf schreibt."""
    import argparse
    cli = _lade_cli()
    fake = _FakeKlient()
    fake.ruf = lambda w, a, frist=None: {"db_path": "/x/brainlehr.db",
                                         "nodes_total": 5251}
    p = bp.BrainlehrProvider()
    p._klient = fake
    monkeypatch.setattr(p, "_grund_fuer_unverfuegbar", lambda: "")
    monkeypatch.setattr(cli, "_provider", lambda: p)
    rc = cli.brainlehr_command(argparse.Namespace(brainlehr_befehl="pruefen"))
    ausgabe = capsys.readouterr().out
    assert rc == 0
    assert "5251" in ausgabe, ausgabe


def test_frage_passt_auf_hermes_echtes_prompt():
    """POSITIVKONTROLLE gegen den eigenen Pruefstand: die post_setup-Tests
    ersetzen `_frage` vollstaendig -- der Weg, den Hermes wirklich nimmt
    (`hermes_cli.memory_setup._prompt`), wird darin also NIE ausgefuehrt. Ein
    Signaturwechsel bliebe dort unsichtbar und faende erst der Nutzer beim
    Einrichten. Hier wird die echte Signatur geprueft, nicht die des Doubles."""
    import inspect
    import os as _os
    hermes_agent = Path(_os.environ.get(
        "HERMES_AGENT_HOME", str(Path.home() / ".hermes" / "hermes-agent")))
    if not (hermes_agent / "hermes_cli" / "memory_setup.py").is_file():
        import pytest
        pytest.skip("Hermes nicht installiert")
    sys.path.insert(0, str(hermes_agent))
    from hermes_cli.memory_setup import _prompt
    # _frage ruft _prompt(text, vorgabe) -- zwei Stellungsargumente.
    inspect.signature(_prompt).bind("label", "vorgabe")


def test_beide_schreibwege_haengen_an_denselben_vorhandenen_elternknoten():
    """VORHER ROT, und der Fund ist der Grund fuer diesen Test: sync_turn
    hing an "/shared/hermes-mitschrift". Ein Trigger bricht jeden Eintrag ab,
    dessen `parent_path` auf keinen vorhandenen Knoten zeigt
    (knowledge_mcp_server.py:303-313) -- am laufenden Bestand nachgesehen gibt
    es "/shared", den Unterzweig nicht. Jeder mitgeschriebene Zug waere im
    Hintergrundfaden abgewiesen worden, ohne Spur an der Oberflaeche.

    Geprueft wird die GLEICHHEIT beider Wege, nicht der Wert: der eine Weg
    (`brainlehr_merken`) ist im Betrieb belegt, und solange der andere
    denselben nimmt, kann er nicht einzeln abdriften."""
    p = _provider_mit_fake(mitschrift=True)
    p.handle_tool_call("brainlehr_merken",
                       {"titel": "t", "inhalt": "i", "herkunft": "h"})
    p.sync_turn("Eine Frage von ausreichender Laenge?", "Eine Antwort.")
    if p._faden is not None:
        p._faden.join(timeout=2)
    import time
    for _ in range(40):
        if len(_schreibrufe(p)) >= 2:
            break
        time.sleep(0.05)
    eltern = {a["parent_path"] for a in _schreibrufe(p)}
    assert len(_schreibrufe(p)) == 2, _schreibrufe(p)
    assert eltern == {bp.ELTERNPFAD}, eltern
    assert "/" == bp.ELTERNPFAD[0] and bp.ELTERNPFAD.count("/") == 1, \
        "ein Unterzweig muesste erst angelegt werden -- der Trigger bricht sonst ab"


def test_beide_schreibwege_haengen_an_denselben_vorhandenen_elternknoten():
    """VORHER ROT, und der Fund ist der Grund fuer diesen Test: sync_turn hing
    an "/shared/hermes-mitschrift". Ein Trigger bricht jeden Eintrag ab, dessen
    `parent_path` auf keinen vorhandenen Knoten zeigt
    (knowledge_mcp_server.py:303-313) -- am laufenden Bestand nachgesehen gibt
    es "/shared", einen Unterzweig darunter nicht. Jeder mitgeschriebene Zug
    waere im Hintergrundfaden abgewiesen worden, ohne Spur an der Oberflaeche.

    Geprueft wird die GLEICHHEIT beider Wege, nicht der Wert: der eine Weg
    (`brainlehr_merken`) ist im Betrieb belegt, und solange der andere denselben
    nimmt, kann er nicht einzeln abdriften."""
    import time
    p = _provider_mit_fake(mitschrift=True)
    p.handle_tool_call("brainlehr_merken",
                       {"titel": "t", "inhalt": "i", "herkunft": "h"})
    p.sync_turn("Eine Frage von ausreichender Laenge?", "Eine Antwort.")
    for _ in range(40):                      # der Schreibvorgang laeuft nebenher
        if len(_schreibrufe(p)) >= 2:
            break
        time.sleep(0.05)
    assert len(_schreibrufe(p)) == 2, _schreibrufe(p)
    assert {a["parent_path"] for a in _schreibrufe(p)} == {bp.ELTERNPFAD}
    assert bp.ELTERNPFAD.count("/") == 1, \
        "ein Unterzweig muesste erst angelegt werden -- sonst bricht der Trigger ab"
