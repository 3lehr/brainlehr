"""brainlehr als Speicher-Anbieter fuer Hermes (Nous Research, MIT).

WAS DAS IST: Hermes bietet unter Einstellungen einen "Memory Provider" an.
Am 2026-08-20 standen dort acht Anbieter zur Auswahl -- byterover, hindsight,
holographic, honcho, mem0, openviking, retaindb, supermemory -- und brainlehr
nicht. Gemessen ueber `hermes memory status`: sieben der acht brauchen einen
API-Schluessel, nur holographic laeuft rein lokal.

WARUM DAS MEHR IST ALS DER VORHANDENE MCP-ZUGANG: brainlehr ist bei Hermes
laengst als MCP-Server angebunden, das Modell KANN also nachschlagen. Ein
Speicher-Anbieter liefert Kontext AUTOMATISCH vor jedem Zug, ohne dass das
Modell ein Werkzeug ruft. Der Unterschied zwischen "kann nachschlagen" und
"weiss es schon".

GESCHRIEBEN wird hier NICHT automatisch: `sync_turn` ist bewusst nicht
gebaut. brainlehr verlangt an jedem Eintrag eine nachpruefbare Herkunft, und
ein Automat, der Zug fuer Zug mitschreibt, kann keine ehrliche liefern -- er
haette nur "aus einem Gespraech". Eintraege entstehen darum ausschliesslich,
wenn das Modell `brainlehr_merken` ruft und die Herkunft mitgibt.

WO DIESE DATEI INSTALLIERT GEHOERT, und das ist die Falle:
    ~/.hermes/plugins/brainlehr/          RICHTIG (Nutzerbereich)
    ~/.hermes/hermes-agent/plugins/...    FALSCH (wird beim Update ersetzt)
Der zweite Ort ist der naheliegende -- dort liegen die acht mitgelieferten.
Er wird beim naechsten Hermes-Update ueberschrieben. Dieselbe Klasse wie die
MIT-Lizenz am selben Tag: etwas an einen Ort legen, den ein Neuanlegen
zuruecksetzt, und es dann nie wieder ansehen.

UEBERNOMMEN AUS DEM QUELLTEXT DER ACHT, jeweils weil es MEHRFACH vorkam und
damit eher Stand der Technik als Einzelmeinung ist:

  * Abruf im Hintergrund mit kurzer Wartefrist statt blockierend
    (mem0 _PREFETCH_WAIT_SECS=3, retaindb, supermemory). Hier zaehlt es
    doppelt: brainlehrs Abruf kann lokale Einbettungen rechnen, und ein
    langsames Ollama darf nicht die Antwortzeit des Nutzers kosten.
  * Trivialfilter vor Abruf und Schreiben. Die Schnittstelle bringt ihn
    selbst mit (memory_provider.is_trivial_prompt) -- byterover und
    supermemory bauen ihn trotzdem nach. Wir nehmen den vorhandenen.
  * Kein Schreiben aus nebenlaeufigen Kontexten. Die Schnittstelle warnt
    ausdruecklich: Cron-Systemprompts wuerden die Nutzerdarstellung
    verderben. Ein Speicher, der seine eigenen Wartungslaeufe als Wissen
    aufnimmt, vergiftet sich selbst.

BEWUSST NICHT UEBERNOMMEN: honchos Wettlauf aus drei Hintergrund-Threads mit
sieben Zeitfenstern, Rueckfall-Zaehlern und Veraltungswaechter in einer
Methode. Der Agent, der ihn gelesen hat, nennt genau das den Satz, den er
nicht gebaut haette -- und brainlehrs Abruf ist lokal, also ist der Engpass
ein anderer.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

# Die Basisklasse liegt in Hermes. Fehlt sie, laeuft diese Datei trotzdem --
# sie gehoert zu brainlehr und muss in brainlehrs Pruefstand ohne installiertes
# Hermes ladbar sein. Sonst waere sie nur auf genau dem Rechner pruefbar, auf
# dem sie ohnehin laeuft.
try:
    from agent.memory_provider import MemoryProvider, is_trivial_prompt
except ImportError:  # pragma: no cover -- ausserhalb von Hermes
    class MemoryProvider:  # type: ignore[no-redef]
        """Ersatz fuer den Pruefstand."""

    def is_trivial_prompt(text: Optional[str]) -> bool:  # type: ignore[no-redef]
        return not (text or "").strip() or len((text or "").strip()) < 10


WARTEFRIST = 3.0          # Sekunden, die prefetch() hoechstens wartet
TREFFER = 5               # Eintraege je Abruf
ZEICHENDECKEL = 4000      # so viel Kontext geht hoechstens in den Prompt

MERKMAL = "knowledge_mcp_server.py"   # daran wird eine brainlehr-Wurzel erkannt

log = logging.getLogger(__name__)


def _selbstfund() -> Optional[Path]:
    """Von dieser Datei aus nach oben, bis eine brainlehr-Wurzel dasteht.

    `resolve()` folgt dem Symlink, unter dem dieses Plugin installiert gehoert
    (`~/.hermes/plugins/brainlehr` -> `<repo>/integrations/hermes/plugin`), und
    landet damit im echten Repo. Am MERKMAL gesucht statt an einer festen
    Ebenenzahl -- dieselbe Idee wie `haken/ort.py`, das die Wurzel an
    `schema.sql` sucht: eine Ebenenzahl bricht beim naechsten Umzug lautlos.
    Wer statt des Symlinks kopiert, faellt hier durch und braucht die
    Einstellung -- was richtig ist, denn eine Kopie WEISS nicht, wo sie herkam.
    """
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / MERKMAL).is_file():
            return p
        p = p.parent
    return None


def _brainlehr_heim(konfig: Optional[Dict[str, Any]] = None) -> Optional[Path]:
    """Wo brainlehr liegt -- vier Quellen, absteigend nach Ausdruecklichkeit.

    1. `brainlehr_home` aus dem Hermes-Einstellungspanel. Was der Nutzer
       sichtbar eingetragen hat, sticht alles andere. Dieselbe Rangfolge wie
       bei `ausweis` und `embed_service_url` weiter unten.
    2. Umgebungsvariable `BRAINLEHR_HOME` -- fuer Aufrufe ohne Panel
       (Kommandozeile, CI, Pruefstand).
    3. Der eigene Ort (`_selbstfund`). Deckt die empfohlene Symlink-
       Installation ohne jede Einstellung ab: das haeufigste ist das, was
       niemand konfigurieren muss.
    4. `~/brainlehr` -- die Konvention, wenn brainlehr getrennt vom Plugin
       liegt und niemand etwas gesetzt hat.

    Ein absoluter Pfad EINES Rechners steht bewusst nirgends darin: er wuerde
    auf jedem anderen Rechner nur schweigend danebengreifen.
    """
    quellen = [
        (konfig or {}).get("brainlehr_home"),
        os.environ.get("BRAINLEHR_HOME"),
    ]
    for wert in quellen:
        if wert and str(wert).strip():
            p = Path(str(wert)).expanduser()
            # Ausdruecklich gesetzt und falsch ist ein Befund, kein Anlass,
            # heimlich weiterzuraten -- sonst laeuft der Nutzer auf einem
            # Bestand, den er nicht gemeint hat.
            return p if (p / MERKMAL).is_file() else None

    gefunden = _selbstfund()
    if gefunden is not None:
        return gefunden

    konvention = Path.home() / "brainlehr"
    return konvention if (konvention / MERKMAL).is_file() else None


def _server_befehl(konfig: Optional[Dict[str, Any]] = None) -> Optional[List[str]]:
    """Womit brainlehrs MCP-Server gestartet wird.

    `mcp_command` aus den Einstellungen (oder `$BRAINLEHR_MCP_COMMAND`) sticht
    alles. Sonst wird der Befehl aus dem Fundort ABGELEITET -- derselbe
    Interpreter, unter dem dieses Plugin laeuft, plus der Server im
    Arbeitsstand. Abgeleitet, nicht verdrahtet: es steht kein Pfad eines
    bestimmten Rechners darin."""
    roh = ((konfig or {}).get("mcp_command")
           or os.environ.get("BRAINLEHR_MCP_COMMAND") or "").strip()
    if roh:
        import shlex
        return shlex.split(roh)
    heim = _brainlehr_heim(konfig)
    return [sys.executable, str(heim / MERKMAL)] if heim else None


class _MCPKlient:
    """Ein Gespraech mit brainlehr ueber MCP -- stdio, JSON-RPC 2.0, eine
    Zeile je Nachricht (knowledge_mcp_server.py::main).

    WARUM UEBERHAUPT: Bis zum 2026-08-21 importierte dieser Adapter brainlehrs
    Module in den EIGENEN Prozess (`import knowledge_mcp_server`, `import ort`,
    jeweils nach sys.path-Griff). Das ist die engste Kopplung, die es gibt: der
    Adapter kannte die Interna und waere an jeder internen Aenderung
    zerbrochen. Ueber MCP kennt er nur noch die Schnittstelle -- zwei
    Programme, die Nachrichten tauschen. Und genau dafuer ist der Server
    ausdruecklich gebaut (ADR-024, "portabler Kern").

    Jeder Aufruf laeuft mit Frist in einem eigenen Faden. Ein `readline()` auf
    einer Pipe blockiert sonst unbegrenzt, und ein haengender Speicher darf
    die Antwortzeit des Nutzers nicht kosten. Dieselbe Bauform wie die
    Wartefrist in `prefetch()`, nur eine Ebene tiefer."""

    def __init__(self, befehl: List[str], umgebung: Optional[Dict[str, str]] = None):
        self.befehl = befehl
        self.umgebung = umgebung or {}
        self._proc: Optional[Any] = None
        self._zaehler = 0
        self._schloss = threading.Lock()

    # -- Leben ---------------------------------------------------------------

    def _sicherstellen(self) -> bool:
        if self._proc is not None and self._proc.poll() is None:
            return True
        import subprocess
        umwelt = dict(os.environ)
        umwelt.update({k: str(v) for k, v in self.umgebung.items() if v})
        try:
            self._proc = subprocess.Popen(
                self.befehl,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                # stderr verwerfen: der Server schreibt dort Hinweise hin. Eine
                # volle, nie gelesene Pipe wuerde ihn irgendwann blockieren.
                stderr=subprocess.DEVNULL,
                text=True, bufsize=1, env=umwelt)
        except Exception as fehler:
            log.warning("brainlehr MCP server would not start (%s): %s",
                        " ".join(self.befehl), fehler)
            self._proc = None
            return False
        return self._handschlag()

    def _handschlag(self) -> bool:
        antwort = self._roh("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "hermes-brainlehr-plugin", "version": "1.0.0"},
        }, frist=15.0)
        if antwort is None:
            self.stop()
            return False
        self._senden({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return True

    def stop(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            proc.stdin.close()
        except Exception:
            pass
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    # -- Verkehr -------------------------------------------------------------

    def _senden(self, nachricht: Dict[str, Any]) -> None:
        self._proc.stdin.write(json.dumps(nachricht) + "\n")
        self._proc.stdin.flush()

    def _roh(self, methode: str, parameter: Dict[str, Any],
             frist: float) -> Optional[Dict[str, Any]]:
        """Eine Anfrage, eine Antwort, mit Frist. None heisst: nicht
        zustandegekommen -- der Aufrufer entscheidet, was das bedeutet."""
        self._zaehler += 1
        anfrage = {"jsonrpc": "2.0", "id": self._zaehler,
                   "method": methode, "params": parameter}
        eimer: List[Optional[str]] = [None]

        def arbeiten() -> None:
            try:
                self._senden(anfrage)
                eimer[0] = self._proc.stdout.readline()
            except Exception:
                eimer[0] = None

        faden = threading.Thread(target=arbeiten, daemon=True)
        faden.start()
        faden.join(timeout=frist)
        if faden.is_alive():
            log.warning("brainlehr MCP call %s exceeded %.1fs -- restarting the "
                        "server process", methode, frist)
            self.stop()          # der Faden laeuft ins Leere und endet
            return None
        zeile = eimer[0]
        if not zeile:
            self.stop()
            return None
        try:
            return json.loads(zeile)
        except json.JSONDecodeError:
            return None

    def ruf(self, werkzeug: str, argumente: Dict[str, Any],
            frist: float = 20.0) -> Optional[Dict[str, Any]]:
        """Ein Werkzeug aufrufen. Ergebnis ist der ausgepackte Nutzinhalt,
        oder None, wenn der Server nicht antwortete oder abgewiesen hat."""
        with self._schloss:
            if not self._sicherstellen():
                return None
            antwort = self._roh("tools/call",
                                {"name": werkzeug, "arguments": argumente},
                                frist=frist)
        if not antwort or "result" not in antwort:
            return None
        ergebnis = antwort["result"]
        if ergebnis.get("isError"):
            inhalt = (ergebnis.get("content") or [{}])[0].get("text", "")
            log.warning("brainlehr rejected %s: %s", werkzeug, inhalt[:200])
            return None
        try:
            return json.loads((ergebnis.get("content") or [{}])[0].get("text") or "{}")
        except json.JSONDecodeError:
            return None

    def werkzeugnamen(self, frist: float = 15.0) -> Optional[List[str]]:
        with self._schloss:
            if not self._sicherstellen():
                return None
            antwort = self._roh("tools/list", {}, frist=frist)
        if not antwort or "result" not in antwort:
            return None
        return [w.get("name") for w in antwort["result"].get("tools", [])]


def _hermes_konfig() -> Dict[str, Any]:
    """brainlehrs Einstellungsblock im Hermes-Panel --
    $HERMES_HOME/brainlehr/config.json, Hermes' Vorgabespeicherform fuer
    Anbieter ohne eigenes `storage=` (siehe config_schema.py, STORAGE_FLAT_JSON).
    Fehlt Datei oder HERMES_HOME, ist das Ergebnis leer -- kein Grund zu werfen,
    is_available() liest dann nur die Umgebungsvariablen-Rueckfallwerte."""
    basis = os.environ.get("HERMES_HOME")
    heim = Path(basis).expanduser() if basis else Path.home() / ".hermes"
    pfad = heim / "brainlehr" / "config.json"
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
        return daten if isinstance(daten, dict) else {}
    except Exception:
        return {}


def _dienst_erreichbar(url: str, timeout: float = 1.5) -> bool:
    """Kurzer Verbindungsversuch mit knapper Frist -- genau die Pruefung, die
    is_available() bisher NICHT machte. Ein HTTP-Fehlerstatus zaehlt als
    erreichbar (der Dienst hat geantwortet); eine nicht aufloesbare Adresse,
    ein verweigerter Verbindungsaufbau oder eine ueberschrittene Frist nicht.

    Das weicht von der Hermes-Basisklasse ab ('is_available soll keine
    Netzaufrufe machen') -- bewusst, weil genau dieser Dienst am 2026-08-20
    dreizehnmal unbemerkt gefehlt und Eintraege ohne Vektor erzeugt hat. Die
    kurze Frist haelt den Preis dafuer klein."""
    if not url:
        return False
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


class BrainlehrProvider(MemoryProvider):
    """Lokaler Wissensspeicher mit erzwungener Herkunft, Geltung und Freigabe."""

    def __init__(self) -> None:
        self._sitzung = ""
        self.grund = ""       # warum is_available() zuletzt False sagte
        self.darf_schreiben = True
        self._vorrat = ""
        self._faden: Optional[threading.Thread] = None
        self._klient: Optional[_MCPKlient] = None

    def _verbindung(self) -> Optional[_MCPKlient]:
        """Ein Server-Prozess je Anbieter, beim ersten Bedarf gestartet."""
        if self._klient is None:
            konfig = _hermes_konfig()
            befehl = _server_befehl(konfig)
            if befehl is None:
                return None
            self._klient = _MCPKlient(befehl, {
                "BRAINLEHR_DB": konfig.get("db_path") or "",
                "KNOWLEDGE_OLLAMA_URL": konfig.get("embed_service_url") or "",
            })
        return self._klient

    @property
    def name(self) -> str:
        return "brainlehr"

    # -- Pflicht ------------------------------------------------------------

    def is_available(self) -> bool:
        """Nachsehen, ob Code, Bestand UND die zwei still scheiternden
        Pflichtfelder (Ausweis, Einbettungsdienst) da sind.

        Wer hier True meldet und erst beim Benutzen scheitert, steht im Menue
        und enttaeuscht dann -- genau das passierte bisher mit einem fehlenden
        Ausweis (jeder Schreibvorgang vom Trigger abgewiesen, ohne Hinweis im
        Menue) und einem unerreichbaren Einbettungsdienst (Eintraege ohne
        Vektor, am 2026-08-20 dreizehnmal). Gibt diese Methode False zurueck,
        fuegt der MemoryManager den Anbieter gar nicht erst hinzu, statt ihn
        kaputt laufen zu lassen.

        JEDES False nennt seinen Grund im Log. Ein stummes False sieht fuer den
        Nutzer genauso aus wie "brainlehr gibt es hier nicht" -- er weiss
        dann nicht, ob ihm der Bestand, der Ausweis oder nur eine Pfadangabe
        fehlt. `self.grund` traegt denselben Text fuer Aufrufer, die kein Log
        mitlesen."""
        grund = self._grund_fuer_unverfuegbar()
        self.grund = grund
        if grund:
            log.warning("brainlehr memory provider unavailable: %s", grund)
            return False
        return True

    def _grund_fuer_unverfuegbar(self) -> str:
        """Leerer String heisst verfuegbar; sonst der englische Grund."""
        konfig = _hermes_konfig()

        befehl = _server_befehl(konfig)
        if befehl is None:
            return (
                "brainlehr not found. Looked at, in order: the `mcp_command` "
                "setting, $BRAINLEHR_MCP_COMMAND, the `brainlehr_home` setting, "
                "$BRAINLEHR_HOME, the directory this plugin was installed from, "
                f"and ~/brainlehr -- none of them yields {MERKMAL}. Set "
                "`brainlehr_home` in the plugin settings to your brainlehr "
                "checkout, or `mcp_command` to the command that starts its MCP "
                "server.")

        klient = self._verbindung()
        namen = klient.werkzeugnamen() if klient else None
        if namen is None:
            return ("brainlehr's MCP server did not answer. Command tried: "
                    f"{' '.join(befehl)}. Check that it starts and speaks MCP "
                    "over stdio.")
        fehlend = [w for w in ("knowledge_search", "knowledge_add")
                   if w not in namen]
        if fehlend:
            return (f"brainlehr's MCP server answered but does not offer "
                    f"{', '.join(fehlend)}. This plugin needs those two tools; "
                    f"the server offered {len(namen)}. Check that the checkout "
                    "is up to date.")

        stats = klient.ruf("knowledge_stats", {})
        if stats is None or "db_path" not in stats:
            return ("brainlehr's MCP server is running but its store did not "
                    "answer `knowledge_stats`. The database is probably "
                    "missing or unreadable -- point $BRAINLEHR_DB / the "
                    "`db_path` setting at an existing one.")

        ausweis = konfig.get("ausweis") or os.environ.get("BRAINLEHR_AUSWEIS", "")
        if not str(ausweis).strip():
            return ("no `ausweis` (acting identity) configured. Writes are "
                    "attributed to it, so without one every entry lands "
                    "unattributed. Set `ausweis` in the plugin settings or "
                    "$BRAINLEHR_AUSWEIS.")

        dienst = konfig.get("embed_service_url") or os.environ.get(
            "KNOWLEDGE_OLLAMA_URL", "http://127.0.0.1:11434")
        if not _dienst_erreichbar(dienst):
            return (f"the embedding service at {dienst} did not answer. "
                    "Entries would be stored without a vector and be "
                    "unfindable through semantic search, with no error shown. "
                    "Start it, or correct `embed_service_url`.")

        return ""

    def initialize(self, session_id: str, **kwargs) -> None:
        self._sitzung = session_id
        # Nur der Hauptlauf schreibt. Cron und Unteragenten lesen mit,
        # tragen aber nichts ein -- ihre Systemprompts sind kein Wissen.
        self.darf_schreiben = kwargs.get("agent_context", "primary") == "primary"

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "brainlehr_suche",
                "description": (
                    "Search the local brainlehr knowledge base. Returns entries "
                    "with their origin (source) and validity. Every entry states "
                    "where it came from -- an entry without verifiable origin "
                    "cannot exist in this store."),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "frage": {"type": "string",
                                  "description": "What to look for"},
                        "anzahl": {"type": "integer",
                                   "description": f"How many entries (default {TREFFER})"},
                    },
                    "required": ["frage"],
                },
            },
            {
                "name": "brainlehr_merken",
                "description": (
                    "Record a durable fact or decision. Requires `herkunft` "
                    "(where this came from) -- this is enforced by a database "
                    "trigger, not by convention, so an entry without it is "
                    "rejected rather than silently stored."),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "titel": {"type": "string"},
                        "inhalt": {"type": "string"},
                        "herkunft": {"type": "string",
                                     "description": "Origin: what this is derived from, and as of when"},
                    },
                    "required": ["titel", "inhalt", "herkunft"],
                },
            },
        ]

    # -- Abruf --------------------------------------------------------------

    def _suchen(self, frage: str, anzahl: int = TREFFER) -> List[Dict[str, Any]]:
        klient = self._verbindung()
        if klient is None:
            return []
        antwort = klient.ruf("knowledge_search",
                             {"query": frage, "scope": "all",
                              "max_results": anzahl})
        return (antwort or {}).get("results", []) or []

    def _im_hintergrund(self, frage: str) -> None:
        treffer = self._suchen(frage)
        zeilen, zeichen = [], 0
        for t in treffer:
            stueck = (f"- {t.get('title') or t.get('path')}: "
                      f"{(t.get('summary') or '')[:300]}")
            # Herkunft mitliefern -- sie ist der Grund, warum dieser Speicher
            # anders ist als die uebrigen sieben. Ein Eintrag ohne sie kann
            # hier gar nicht entstehen; sie wegzulassen waere, den Unterschied
            # zu verschenken.
            if t.get("source"):
                stueck += f"  [Herkunft: {str(t['source'])[:120]}]"
            if zeichen + len(stueck) > ZEICHENDECKEL:
                break
            zeilen.append(stueck)
            zeichen += len(stueck)
        self._vorrat = ("Aus brainlehr (lokal, jede Zeile mit Herkunft):\n"
                        + "\n".join(zeilen)) if zeilen else ""

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Kontext fuer den kommenden Zug -- im Hintergrund, mit Wartefrist.

        Blockierend waere einfacher, aber brainlehrs Abruf rechnet lokale
        Einbettungen: Ein langsames Ollama duerfte sonst die Antwortzeit des
        Nutzers kosten. Dieselbe Bauform wie mem0, retaindb und supermemory --
        was in drei von vier Anbietern gleich geloest ist, ist eher Stand der
        Technik als Geschmack."""
        if is_trivial_prompt(query):
            return ""
        self._faden = threading.Thread(target=self._im_hintergrund,
                                       args=(query,), daemon=True)
        self._faden.start()
        self._faden.join(timeout=WARTEFRIST)
        return self._vorrat

    def system_prompt_block(self) -> str:
        return (
            "brainlehr is available as your memory: a local knowledge store "
            "whose rules are enforced by database triggers, not by convention. "
            "Every entry carries a verifiable origin (`source`) and states "
            "whether it is still valid. When asked what brainlehr is or "
            "contains, call its tools rather than answering from memory -- the "
            "numbers change, and a remembered figure is a snapshot of an older "
            "system.")

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        if tool_name == "brainlehr_suche":
            treffer = self._suchen(args.get("frage", ""),
                                   int(args.get("anzahl", TREFFER)))
            return json.dumps({"treffer": treffer}, ensure_ascii=False)
        if tool_name == "brainlehr_merken":
            if not self.darf_schreiben:
                return json.dumps({"fehler": "kein Schreibrecht in diesem Kontext"})
            klient = self._verbindung()
            if klient is None:
                return json.dumps({"fehler": "brainlehr nicht erreichbar"})
            ergebnis = klient.ruf("knowledge_add", {
                "parent_path": "/shared",
                "title": args["titel"],
                "summary": args["inhalt"][:400],
                "content": args.get("inhalt"),
                "source": args["herkunft"],
                "norm_entscheidung": "keine_norm",
                "norm_entschieden_grund":
                    "ueber Hermes erfasst, nicht als Regel gemeint",
            })
            if ergebnis is None:
                return json.dumps(
                    {"fehler": "brainlehr hat den Eintrag nicht angenommen -- "
                               "Grund steht im Log"}, ensure_ascii=False)
            return json.dumps(ergebnis, ensure_ascii=False, default=str)
        return json.dumps({"fehler": f"unbekanntes Werkzeug {tool_name}"})

    def shutdown(self) -> None:
        """Den Server-Prozess mitnehmen.

        Erst mit dem Umstieg auf MCP gibt es ueberhaupt etwas aufzuraeumen:
        die importierende Fassung hatte keinen eigenen Prozess. Ohne das hier
        ueberlebt brainlehrs Server jede Hermes-Sitzung, und nach ein paar
        Neustarts haengen mehrere an derselben Datenbank."""
        if self._klient is not None:
            self._klient.stop()
            self._klient = None

    def backup_paths(self) -> List[str]:
        """Den ECHTEN Datenbankort melden, und ihn ERFRAGEN statt zu raten.

        `knowledge_stats` gibt `db_path` zurueck -- die Datei, die der Server
        tatsaechlich offen hat. Geraten waere `<heim>/brainlehr.db` gewesen,
        und das ist regelmaessig falsch: `haken/ort.py` laesst `$BRAINLEHR_DB`
        den Ort stechen und faellt auf den alten Namen `knowledge.db` zurueck,
        wenn `brainlehr.db` fehlt. Ein geratener Name haette hier also eine
        Datei gesichert, die es nicht gibt, und es nicht gemeldet."""
        klient = self._verbindung()
        if klient is None:
            return []
        stats = klient.ruf("knowledge_stats", {})
        pfad = (stats or {}).get("db_path")
        return [str(pfad)] if pfad and Path(str(pfad)).is_file() else []


def register_memory_provider():
    """Einstiegspunkt fuer Hermes."""
    return BrainlehrProvider()
