"""brainlehrs deklariertes Einstellungsfeld fuer Hermes' generisches Panel.

WARUM DIESE DATEI FEHLTE: Sechs von acht mitgelieferten Speicher-Anbietern
haben kein `config_schema.py` und zeigen darum kein Einstellungspanel.
`hindsight` und `honcho` haben eins -- deren Bauform ist hier abgeschrieben,
nicht neu erfunden (Hermes, `plugins/memory/{hindsight,honcho}/config_schema.py`).

DER SCHNITT (docs/PLAN_NAECHSTE_STUFE_2026-08-21.md §4b, Betreiberentscheidung
2026-08-21): EINSTELLUNG gegen HANDLUNG. Ein Wert, der bleibt und das
Verhalten praegt, gehoert hierher. Ein einmaliger Vorgang (Katalog-Import,
Lehren-Befoerderung, Ausweis-Widerruf) gehoert in ein MCP-Werkzeug
(`get_tool_schemas()` in `brainlehr_provider.py`), nicht ins Panel.

INLINE (kompaktes Panel) sind genau die sechs Felder, ohne die entweder gar
nichts laeuft oder etwas STILL falsch laeuft: Datenbankpfad, Ausweis,
Betriebsprofil, Mandantenname, Einbettungsdienst, Oberflaechensprache.
Alles andere steht im vollen Dialog.

ZWEISPRACHIGKEIT (ADR-033): Diese Erklaerungen existieren noch nicht, also
entstehen sie zweisprachig -- Deutsch, dann eine mit "English: " markierte
englische Fassung. `_bi()` haelt die Form an einer Stelle fest, damit ein
Test beide Haelften trennen und pruefen kann (keine Uebersetzung ohne
englische Haelfte).

WARUM `description` NIE NUR DEN FELDNAMEN WIEDERHOLT: Ein Feldname sagt WAS
ein Feld ist. Er sagt nicht, was beim Falschsetzen passiert -- und genau das
ist hier die Information, die zaehlt (Ausweis: Trigger weist JEDEN
Schreibvorgang ab; Einbettungsdienst: Eintraege ohne Vektor, ohne Fehler;
`embed_model`: 7409 Vektoren entwertet, ohne dass etwas das meldet).

DAS EINE GEFAEHRLICHE FELD: `embed_model` entwertet bei Aenderung den ganzen
Vektorbestand, ohne dass irgendwo ein Fehler erscheint (Beleg:
`atelier/app/Sources/BrainlehrCore/Modellzugaenge.swift:8-13`, 7409 Vektoren).
Hermes' Schema kennt keine Feldart "anzeigen, nicht aendern" -- der Ausweg
ohne Aenderung an Hermes ist `KIND_SELECT` mit GENAU EINER Option: dem
laufenden Modell. Sichtbar, auf nichts anderes stellbar.

NICHT HIER: die gemessenen Schwellen (MIN_HITS=3, 0,65, 2,0/10%, 84). Sie
sind das Ergebnis einer Messung, keine Einstellung -- anzeigen ja (an anderer
Stelle), bedienbar nein.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# config_schema.py wird von Hermes PER PFAD geladen (importlib, siehe
# get_provider_config_schema in hermes_cli/web_server.py), nicht per
# Paketimport -- deshalb kann sie ausschliesslich das nennen, was Hermes
# selbst mitbringt (`plugins.memory.config_schema`), plus, mit demselben
# Trick wie brainlehr_provider.py, den optionalen Blick in brainlehrs
# eigenen Bestand fuer den EINEN dynamischen Wert (das laufende
# Einbettungsmodell). Schlaegt der fehl, bleibt der belegte Literalwert.
_sys.path[:0] = [str(_Path(__file__).resolve().parent)]

from plugins.memory.config_schema import (  # noqa: E402
    KIND_JSON,
    KIND_SELECT,
    KIND_TEXT,
    ProviderConfigSchema,
    ProviderField,
    ProviderFieldOption,
)


def _bi(de: str, en: str) -> str:
    """Deutsch, dann eine mit 'English: ' markierte englische Fassung
    (ADR-033: jeder neu geschriebene nutzersichtbare Text ist zweisprachig)."""
    return f"{de}\n\nEnglish: {en}"


def _laufendes_embed_model() -> str:
    """Das aktive Einbettungsmodell -- der zuletzt belegte Wert (2026-08-21:
    'bge-m3@ctx2048'), uebersteuerbar ueber `$BRAINLEHR_EMBED_MODEL`.

    BIS 2026-08-21 STAND HIER EIN IMPORT von brainlehrs `embeddings`-Modul in
    DIESEN Prozess, nur um eine Zeichenkette zu lesen. Das ist zugleich die
    engste Kopplung (dieser Adapter kennt dann brainlehrs Interna und bricht
    an jeder internen Umbenennung) und der teuerste Weg zu einem Wort. Der
    Server bietet den Wert nicht ueber MCP an -- solange das so ist, ist ein
    Literal mit Uebersteuerung ehrlicher als ein Import, der so tut, als
    waere der Wert live.

    PREIS, offen benannt: Wird brainlehrs Vorgabemodell gewechselt, ohne dass
    diese Zeile oder die Variable nachgezogen wird, zeigt das Panel ein
    falsches Modell an. Es ist ein Anzeigefehler, kein Datenfehler -- das Feld
    hat ohnehin nur eine Option und aendert nichts."""
    import os as _os

    return _os.environ.get("BRAINLEHR_EMBED_MODEL", "").strip() or "bge-m3@ctx2048"


CONFIG_SCHEMA = ProviderConfigSchema(
    name="brainlehr",
    label="brainlehr — local knowledge store, provenance enforced",
    fields=(
        # ---------------------------------------------------------- inline
        ProviderField(
            key="db_path",
            label="Datenbankpfad / Database path",
            kind=KIND_TEXT,
            aliases=("BRAINLEHR_DB",),
            placeholder="~/brainlehr/brainlehr.db",
            description=_bi(
                "Ohne diesen Pfad findet brainlehr seinen Bestand nicht und "
                "bleibt inaktiv -- kein Fehler, nur eine leere Erweiterung.",
                "Without this path brainlehr cannot find its store and stays "
                "inactive -- no error, just a memory provider that does nothing.",
            ),
            inline=True,
        ),
        ProviderField(
            key="ausweis",
            label="Ausweis / handelnde Kennung",
            kind=KIND_TEXT,
            placeholder="z.B. hermes-nutzer",
            description=_bi(
                "Jeder Eintrag wird ihr zugeschrieben. Ohne sie traegt die "
                "Zuschreibung dauerhaft das Praefix `unbeglaubigt:` -- der "
                "Eintrag entsteht, aber es ist rueckwirkend nicht mehr "
                "feststellbar, wer ihn gemacht hat.",
                "Every entry is attributed to it. Without one the attribution "
                "permanently carries the prefix `unbeglaubigt:` (uncertified) "
                "-- the entry is still created, but who made it can no longer "
                "be established afterwards.",
            ),
            inline=True,
        ),
        ProviderField(
            key="betriebsprofil",
            label="Betriebsprofil / Operating profile",
            kind=KIND_SELECT,
            default="einzelplatz",
            description=_bi(
                "`einzelplatz` ist der Auslieferungszustand. Der Wechsel zu "
                "`unternehmen` ist spaeter moeglich und hat einen Rueckweg -- "
                "beides gefahren und gezaehlt.",
                "`einzelplatz` (single-seat) is the shipped default. Switching "
                "to `unternehmen` (company) later is possible and has a way "
                "back -- both have been run and counted.",
            ),
            options=(
                ProviderFieldOption(
                    "einzelplatz", "Einzelplatz / Single-seat",
                    _bi("Ein Mandant, keine Rollentrennung.",
                        "One tenant, no role separation."),
                ),
                ProviderFieldOption(
                    "unternehmen", "Unternehmen / Company",
                    _bi("Verlangt einen Mandantennamen (siehe unten).",
                        "Requires a tenant name (see below)."),
                ),
            ),
            inline=True,
        ),
        ProviderField(
            key="mandant",
            label="Mandantenname / Tenant name",
            kind=KIND_TEXT,
            description=_bi(
                "Pflicht, sobald das Betriebsprofil auf `unternehmen` steht -- "
                "sonst bleibt der Bestand auf dem verborgenen Mandanten "
                "`lokal` stehen, ohne dass etwas das meldet.",
                "Required as soon as the operating profile is `unternehmen` -- "
                "otherwise the store silently stays on the hidden tenant "
                "`lokal`, with nothing reporting it.",
            ),
            inline=True,
        ),
        ProviderField(
            key="embed_service_url",
            label="Einbettungsdienst-Adresse / Embedding service address",
            kind=KIND_TEXT,
            default="http://127.0.0.1:11434",
            aliases=("KNOWLEDGE_OLLAMA_URL",),
            description=_bi(
                "Ist er nicht erreichbar, entstehen Eintraege OHNE Vektor und "
                "sind ueber die Bedeutungssuche unauffindbar, ohne dass ein "
                "Fehler erscheint -- am 2026-08-20 dreizehnmal passiert.",
                "If unreachable, entries are stored WITHOUT a vector and "
                "become unfindable through semantic search, with no error "
                "shown -- this happened thirteen times on 2026-08-20.",
            ),
            inline=True,
        ),
        ProviderField(
            key="oberflaechensprache",
            label="Sprache der Oberflaeche / Interface language",
            kind=KIND_SELECT,
            default="de",
            description=_bi(
                "Sitzungsstart, Melderausgaben und Werkzeugbeschreibungen "
                "folgen dieser Sprache, nicht der Sprache des einzelnen "
                "Eintrags (`BDW-P19`).",
                "Session start, guard output and tool descriptions follow "
                "this language, not the language of the individual entry "
                "(`BDW-P19`).",
            ),
            options=(
                ProviderFieldOption("de", "Deutsch"),
                ProviderFieldOption("en", "English"),
            ),
            inline=True,
        ),
        # ------------------------------------------------- voller Dialog
        ProviderField(
            key="brainlehr_home",
            label="Fundort von brainlehr / brainlehr checkout",
            kind=KIND_TEXT,
            aliases=("BRAINLEHR_HOME",),
            placeholder="~/brainlehr",
            description=_bi(
                "Nur noetig, wenn dieses Plugin KOPIERT statt verlinkt wurde: "
                "ueber den empfohlenen Symlink findet es brainlehr von sich "
                "aus. Steht hier ein falscher Pfad, bleibt der Anbieter "
                "inaktiv und nennt den Grund im Log.",
                "Only needed if this plugin was COPIED instead of symlinked: "
                "installed via the recommended symlink it finds brainlehr by "
                "itself. A wrong path here leaves the provider inactive and "
                "states the reason in the log.",
            ),
        ),
        ProviderField(
            key="mcp_command",
            label="Startbefehl des MCP-Servers / MCP server command",
            kind=KIND_TEXT,
            aliases=("BRAINLEHR_MCP_COMMAND",),
            placeholder="python3 ~/brainlehr/knowledge_mcp_server.py",
            description=_bi(
                "Nur noetig, wenn brainlehr mit einem eigenen Interpreter oder "
                "Wrapper starten soll. Leer gelassen wird der Befehl aus dem "
                "Fundort abgeleitet. Die Verbindung laeuft ueber MCP (stdio), "
                "nicht ueber einen Bibliotheksimport -- brainlehr laeuft also "
                "als eigener Prozess.",
                "Only needed if brainlehr should start with its own "
                "interpreter or a wrapper. Left empty, the command is derived "
                "from the checkout location. The connection runs over MCP "
                "(stdio), not a library import -- so brainlehr runs as its own "
                "process.",
            ),
        ),
        ProviderField(
            key="sprache_eigenes_material",
            label="Sprache des eigenen Materials / Language of own material",
            kind=KIND_SELECT,
            default="de",
            description=_bi(
                "Nicht dasselbe wie die Oberflaechensprache oben (`BDW-P10`): "
                "hier geht es um die Sprache der eigenen Eintraege, gemessen "
                "3573 deutsch gegen 1609 englisch.",
                "Not the same as the interface language above (`BDW-P10`): "
                "this is the language of your own entries, measured at 3573 "
                "German versus 1609 English.",
            ),
            options=(
                ProviderFieldOption("de", "Deutsch"),
                ProviderFieldOption("en", "English"),
            ),
        ),
        ProviderField(
            key="kataloge_erststart",
            label="Kataloge beim Erststart / Catalogs on first run",
            kind=KIND_JSON,
            placeholder='["bsi", "wcag"]',
            description=_bi(
                "Wird nur beim allerersten Start auf einem LEEREN Bestand "
                "gelesen -- auf einem gewachsenen Bestand hat dieses Feld "
                "keine Wirkung, damit nichts unerwartet nachgeladen wird.",
                "Only read on the very first run against an EMPTY store -- "
                "on a store that already has content this field has no "
                "effect, so nothing gets pulled in unexpectedly.",
            ),
        ),
        ProviderField(
            key="mitschrift",
            label="Zug-Mitschrift / Per-turn transcript",
            kind=KIND_SELECT,
            default="aus",
            description=_bi(
                "Schreibt nach jedem Zug einen Eintrag. AUS ist die Vorgabe, "
                "und das ist eine Entscheidung, keine Traegheit: ein Automat "
                "kann keine QUELLE angeben, nur den WEG. Eingeschaltet traegt "
                "jeder Eintrag darum 'Hermes-Sitzung <id>, Zug <n>, "
                "<Zeitpunkt>' -- nachpruefbar, aber es bezeugt nur, DASS "
                "etwas gesagt wurde, nicht dass es stimmt. Wer den Bestand "
                "als geprueftes Wissen liest, schaltet das besser aus und "
                "laesst das Modell `brainlehr_merken` mit eigener Herkunft "
                "rufen.",
                "Writes one entry after every turn. OFF is the default, and "
                "that is a decision, not laziness: an automaton cannot state "
                "a SOURCE, only the PATH. Switched on, every entry therefore "
                "carries 'Hermes-Sitzung <id>, Zug <n>, <timestamp>' -- "
                "verifiable, but it only attests that something was said, "
                "not that it is true. If you read this store as vetted "
                "knowledge, leave it off and let the model call "
                "`brainlehr_merken` with its own origin instead.",
            ),
            options=(
                ProviderFieldOption("aus", "Aus / Off"),
                ProviderFieldOption("an", "An / On"),
            ),
        ),
        ProviderField(
            key="embed_model",
            label="Einbettungsmodell / Embedding model",
            kind=KIND_SELECT,
            default=_laufendes_embed_model(),
            description=_bi(
                "Eine Aenderung entwertet 7409 vorhandene Vektoren, ohne dass "
                "irgendwo ein Fehler erscheint -- deshalb genau EINE Option: "
                "das Modell, das gerade laeuft. Wer wechseln will, baut das "
                "im Bestand selbst neu auf, nicht hier per Klick.",
                "Changing this silently invalidates 7409 existing vectors "
                "with no error anywhere -- so exactly ONE option is offered: "
                "the model currently in use. Switching means rebuilding the "
                "store itself, not a click here.",
            ),
            options=(
                ProviderFieldOption(
                    _laufendes_embed_model(), _laufendes_embed_model(),
                    _bi("Das laufende Modell -- nicht veraenderbar.",
                        "The model currently in use -- not changeable."),
                ),
            ),
        ),
    ),
)
