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

GESCHRIEBEN wird hier per Vorgabe NICHT: `sync_turn` ist gebaut (Hermes'
Anleitung fuer eigenstaendige Plugins verlangt die Methode), schreibt aber nur,
wenn `mitschrift` im Panel eingeschaltet wird -- und sagt beim ersten Zug im
Log, dass und warum es schweigt. Ein Automat kann keine QUELLE liefern; er
kann nur den WEG bezeugen. Eingeschaltet traegt jeder Eintrag darum
"Hermes-Sitzung <id>, Zug <n>, <Zeitpunkt>" als Herkunft und behauptet nichts
darueber hinaus -- dieselbe Trennung, die hier fuer Fremdimporte gilt
(`BDW-P12`: der Import traegt seinen Weg ein und behauptet keine Quelle). Eine
Herkunft, die stattdessen eine Quelle behauptet, verhindert den Schreibvorgang
(`_ist_weg_herkunft`) statt ihn zu schoenen.

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
import re
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime
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

# Wohin Eintraege dieses Plugins gehaengt werden.
# EIN Wert fuer beide Schreibwege (`brainlehr_merken` und `sync_turn`), weil
# der Preis fuer einen zweiten hoch und lautlos ist: ein Datenbanktrigger
# bricht jeden Eintrag ab, dessen `parent_path` auf keinen VORHANDENEN Knoten
# zeigt (knowledge_mcp_server.py:303-313). Ein huebscherer eigener Unterzweig
# fuer die Mitschrift existiert nicht -- am 2026-08-21 am laufenden Bestand
# nachgesehen: "/shared" ja, ein Unterzweig darunter nein. Jeder Zug waere
# abgewiesen worden, im Hintergrundfaden, ohne dass es jemand sieht.
ELTERNPFAD = "/shared"

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

    # EIN Prozess je Aufrufkennung, nicht je Instanz -- mit Zaehlwerk.
    #
    # ANLASS, gemessen 2026-08-23: Hermes baut im Gateway-Betrieb je Nachricht
    # einen frischen AIAgent (so ausdruecklich in agent/agent_init.py:1883),
    # und plugins/memory/__init__.py::load_memory_provider haelt keinen
    # Zwischenspeicher -- also entsteht je Nachricht ein neuer Anbieter.
    # `shutdown_all()` laeuft bewusst NICHT je Zug (agent/turn_finalizer.py:806
    # nennt den Grund: es wuerde den Anbieter vor der zweiten Nachricht toeten),
    # sondern erst bei Sitzungsablauf. Dazwischen haeuft sich also je Nachricht
    # ein Serverprozess an. Belegt: drei Instanzen -> drei gleichzeitige
    # Prozesse auf derselben SQLite-Datei.
    #
    # Es ist unsere Sache, nicht Hermes' -- deren Lebenszyklus ist stimmig, nur
    # passt "ein Prozess je Instanz" nicht dazu. Die eigene shutdown()-
    # Beschreibung warnte woertlich davor ("nach ein paar Neustarts haengen
    # mehrere an derselben Datenbank"); die Warnung stand da und der Fall trat
    # trotzdem ein.
    #
    # Der Zaehler ist der Kern und nicht die Zwischenspeicherung: Ohne ihn
    # wuerde die erste Instanz, die shutdown() ruft, den Prozess unter allen
    # anderen wegziehen -- aus einem Leck ein Absturz, was schlechter ist.
    _GETEILT: Dict[str, "_MCPKlient"] = {}
    _GETEILT_SCHLOSS = threading.Lock()

    @classmethod
    def geteilt(cls, befehl: List[str],
                umgebung: Optional[Dict[str, str]] = None) -> "_MCPKlient":
        """Holt den Klienten fuer diese Aufrufkennung, oder legt ihn an.

        Die Kennung umfasst Befehl UND Umgebung: zwei Anbieter mit
        verschiedenem BRAINLEHR_DB sind verschiedene Speicher und duerfen sich
        keinen Prozess teilen -- sonst schriebe der eine in die Datenbank des
        anderen. Das waere ein schlimmerer Fehler als der, den diese
        Aenderung behebt."""
        kennung = repr((tuple(befehl), tuple(sorted((umgebung or {}).items()))))
        with cls._GETEILT_SCHLOSS:
            klient = cls._GETEILT.get(kennung)
            if klient is None:
                klient = cls(befehl, umgebung)
                klient._kennung = kennung
                cls._GETEILT[kennung] = klient
            klient._nutzer += 1
            return klient

    def __init__(self, befehl: List[str], umgebung: Optional[Dict[str, str]] = None):
        self.befehl = befehl
        self.umgebung = umgebung or {}
        self._proc: Optional[Any] = None
        self._zaehler = 0
        self._schloss = threading.Lock()
        self._nutzer = 0
        self._kennung: Optional[str] = None

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
        """Beendet den Prozess -- aber erst, wenn der LETZTE Nutzer geht.

        Ein geteilter Klient, den der erste Aufrufer beendet, ist schlimmer
        als gar kein Teilen: die uebrigen Anbieter haetten dann einen toten
        Prozess in der Hand und wuerden ihn beim naechsten Zug stumm neu
        starten -- das Leck waere weg und ein Wackelkontakt daefuer da."""
        if self._kennung is not None:
            with type(self)._GETEILT_SCHLOSS:
                self._nutzer -= 1
                if self._nutzer > 0:
                    return
                type(self)._GETEILT.pop(self._kennung, None)
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


# Die WEG-Herkunft. Sie nennt, wie ein Eintrag entstanden ist (welche Sitzung,
# welcher Zug, wann) -- und ausdruecklich NICHT, woraus er inhaltlich stammt.
# Das ist der ganze Unterschied: "Hermes-Sitzung s7, Zug 4, 2026-08-21T14:02:11+0200"
# ist nachpruefbar, "laut dem Betreiber" waere erfunden.
_WEG_MUSTER = re.compile(
    r"^Hermes-Sitzung \S[^,]*, Zug \d+, "
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4}$")


def _weg_herkunft(sitzung: str, zug: int,
                  zeitpunkt: Optional[str] = None) -> str:
    """Der Weg als Zeichenkette -- die einzige Herkunft, die ein Automat
    ehrlich vergeben kann."""
    z = zeitpunkt or datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    return f"Hermes-Sitzung {sitzung or 'ohne-Kennung'}, Zug {zug}, {z}"


def _ist_weg_herkunft(text: Optional[str]) -> bool:
    """Die Schranke davor. Ohne sie waere die Weg-Form eine Absicht: jeder
    spaetere Umbau koennte eine behauptete Quelle einsetzen, und nichts
    wuerde es merken."""
    return bool(_WEG_MUSTER.match((text or "").strip()))


def _frage(text: str, vorgabe: str = "") -> str:
    """Eine Zeile vom Nutzer holen. Hermes' eigenes `_prompt` wird benutzt,
    wenn es da ist -- es kennt Abbruch, Vorgabewerte und die Darstellung des
    Assistenten. Nur wenn Hermes fehlt (Pruefstand), wird `input` genommen;
    dann ist diese Funktion zugleich die Stelle, die ein Test uebernimmt."""
    try:
        from hermes_cli.memory_setup import _prompt  # type: ignore
    except Exception:
        _prompt = None  # type: ignore

    # Nur der IMPORT darf scheitern. Waere der AUFRUF mit im try, wuerde eine
    # geaenderte Signatur bei Hermes lautlos auf `input` zurueckfallen -- die
    # Einrichtung liefe weiter und saehe nur ein bisschen anders aus. Genau
    # die Sorte Fehler, die man erst Monate spaeter findet.
    if _prompt is not None:
        return _prompt(text, vorgabe)
    antwort = input(f"  {text}" + (f" [{vorgabe}]" if vorgabe else "") + ": ")
    return antwort.strip() or vorgabe


class BrainlehrProvider(MemoryProvider):
    """Lokaler Wissensspeicher mit erzwungener Herkunft, Geltung und Freigabe."""

    def __init__(self) -> None:
        self._sitzung = ""
        self.grund = ""       # warum is_available() zuletzt False sagte
        self.darf_schreiben = True
        self._vorrat = ""
        self._faden: Optional[threading.Thread] = None
        self._klient: Optional[_MCPKlient] = None
        self.mitschrift = False      # sync_turn schreibt nur, wenn eingeschaltet
        self.mitschrift_grund = ""   # warum sync_turn zuletzt nichts schrieb
        self._zug = 0
        self._gemeldet = False
        self._herkunft_bauer = _weg_herkunft
        # Nur bei platform == "cli" uebergibt Hermes diese zwei Rueckrufe
        # (agent_init.py:1735-1737) -- Gateway/Telegram/Discord kennen sie
        # nicht. Ohne sie bleibt prefetch() stumm wie bisher; das ist kein
        # Fehlerfall, nur der Betrieb ohne CLI.
        self._status_melden: Optional[Any] = None
        self._warnung_melden: Optional[Any] = None
        self._absturz: Optional[Exception] = None

    def _verbindung(self) -> Optional[_MCPKlient]:
        """Ein Server-Prozess je Anbieter, beim ersten Bedarf gestartet."""
        if self._klient is None:
            konfig = _hermes_konfig()
            befehl = _server_befehl(konfig)
            if befehl is None:
                return None
            self._klient = _MCPKlient.geteilt(befehl, {
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
        self._zug = 0
        self._gemeldet = False
        # Einmal je Sitzung gelesen, nicht je Zug: sync_turn laeuft nach JEDEM
        # Zug, und ein Dateizugriff pro Zug waere ein Preis fuer nichts.
        self.mitschrift = str(
            _hermes_konfig().get("mitschrift", "")).strip().lower() in (
                "1", "true", "ja", "yes", "an", "on")
        self._status_melden = kwargs.get("status_callback")
        self._warnung_melden = kwargs.get("warning_callback")

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
        self._absturz = None
        try:
            self._im_hintergrund_kern(frage)
        except Exception as fehler:  # der Faden darf nicht stumm sterben
            self._absturz = fehler

    def _im_hintergrund_kern(self, frage: str) -> None:
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
        Technik als Geschmack.

        WARUM HIER EINE ZEILE ANS CLI GEHT: `memory_manager.py:542` faengt
        jeden Fehler eines Fremdanbieters ab und schreibt ihn nach
        logger.debug -- der Nutzer sieht das nie, weder den leeren Treffer
        noch den Absturz noch die gerissene 8s-Frist. Genau diese drei Lagen
        werden hier unterscheidbar gemacht, ueber die Rueckrufe, die Hermes
        bei platform == 'cli' ohnehin uebergibt (agent_init.py:1735-1737).
        Fehlen sie (Gateway/Telegram/Discord), bleibt prefetch() stumm wie
        bisher -- kein print, das dort im Log landete."""
        if is_trivial_prompt(query):
            return ""
        self._faden = threading.Thread(target=self._im_hintergrund,
                                       args=(query,), daemon=True)
        self._faden.start()
        self._faden.join(timeout=WARTEFRIST)
        if self._faden.is_alive():
            if self._warnung_melden is not None:
                self._warnung_melden(
                    f"brainlehr: Abruf ueberschritt {WARTEFRIST:.0f}s, ohne "
                    f"Treffer / brainlehr: lookup exceeded {WARTEFRIST:.0f}s, "
                    "no results")
            return self._vorrat
        if self._absturz is not None:
            if self._warnung_melden is not None:
                self._warnung_melden(
                    f"brainlehr: Abruf abgestuerzt ({self._absturz}) / "
                    f"brainlehr: lookup crashed ({self._absturz})")
            return self._vorrat
        anzahl = self._vorrat.count("\n- ") if self._vorrat else 0
        if self._status_melden is not None:
            if anzahl:
                self._status_melden(
                    f"brainlehr: {anzahl} Treffer eingespielt / "
                    f"brainlehr: {anzahl} results injected")
            else:
                self._status_melden(
                    "brainlehr: keine Treffer / brainlehr: no results")
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
                "parent_path": ELTERNPFAD,
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

    # -- Mitschrift ---------------------------------------------------------

    def sync_turn(self, user_content: str, assistant_content: str, *,
                  session_id: str = "",
                  messages: Optional[List[Dict[str, Any]]] = None) -> None:
        """Nach jedem Zug. Per Vorgabe entsteht hier KEIN Eintrag.

        DIE ENTSCHEIDUNG, und warum sie nicht "Methode weglassen" lautet:
        Hermes' Anleitung fuer eigenstaendige Plugins nennt `sync_turn` neben
        `prefetch` und `shutdown` als Pflichtteil des ABC. Sie zu streichen
        hiesse, ihre Anleitung nicht zu erfuellen. Sie zu bauen und stumm
        nichts tun zu lassen waere schlimmer als beides -- dann sieht der
        Nutzer eine Mitschrift, die es nicht gibt.

        DER AUSWEG: Sie ist da, sie schweigt per Vorgabe, und sie SAGT beim
        ersten Zug einer Sitzung, dass sie schweigt und wie man das aendert.
        Eingeschaltet (`mitschrift` im Panel) schreibt sie mit der WEG-Herkunft
        -- Sitzung, Zug, Zeitpunkt. Das ist nachpruefbar. "Aus einem
        Gespraech" waere es nicht, und genau daran scheiterte der Automat
        bisher.

        Nicht blockierend: der Schreibvorgang laeuft im Hintergrund, wie schon
        der Abruf. Die Schnittstelle verlangt das ausdruecklich."""
        self._zug += 1

        if not self.darf_schreiben:
            self.mitschrift_grund = (
                "kein Schreibrecht in diesem Kontext (Cron/Unteragent) -- "
                "deren Systemprompts sind kein Wissen")
            return

        if not self.mitschrift:
            self.mitschrift_grund = (
                "mitschrift ist ausgeschaltet (Vorgabe): brainlehr verlangt an "
                "jedem Eintrag eine nachpruefbare Herkunft, und ein Automat "
                "kann nur den Weg bezeugen, nicht die Quelle. Einschalten "
                "ueber `mitschrift` in den Plugin-Einstellungen; Eintraege "
                "tragen dann 'Hermes-Sitzung <id>, Zug <n>, <Zeitpunkt>'.")
            if not self._gemeldet:
                self._gemeldet = True
                log.info("brainlehr sync_turn: %s", self.mitschrift_grund)
            return

        if is_trivial_prompt(user_content) or not (assistant_content or "").strip():
            self.mitschrift_grund = "Zug ohne Gehalt (Trivialfilter)"
            return

        herkunft = self._herkunft_bauer(session_id or self._sitzung, self._zug)
        if not _ist_weg_herkunft(herkunft):
            # Kein Schoenschreiben: lieber kein Eintrag als einer, dessen
            # Herkunft etwas behauptet. Der Fall ist heute unerreichbar --
            # er wird es beim naechsten Umbau nicht mehr sein.
            self.mitschrift_grund = (
                f"Herkunft nennt nicht den Weg, sondern behauptet eine "
                f"Quelle: {herkunft!r} -- nicht geschrieben")
            log.warning("brainlehr sync_turn: %s", self.mitschrift_grund)
            return

        self.mitschrift_grund = ""
        threading.Thread(target=self._mitschreiben,
                         args=(user_content, assistant_content, herkunft),
                         daemon=True).start()

    def _mitschreiben(self, frage: str, antwort: str, herkunft: str) -> None:
        klient = self._verbindung()
        if klient is None:
            return
        klient.ruf("knowledge_add", {
            "parent_path": ELTERNPFAD,
            "title": frage.strip().splitlines()[0][:120],
            "summary": antwort.strip()[:400],
            "content": f"Frage:\n{frage}\n\nAntwort:\n{antwort}",
            "source": herkunft,
            "norm_entscheidung": "keine_norm",
            "norm_entschieden_grund":
                "Zug-Mitschrift aus Hermes -- bezeugt den Verlauf, nicht "
                "seine Richtigkeit",
        })

    # -- Einrichtung --------------------------------------------------------

    def post_setup(self, hermes_home: str, config: dict) -> None:
        """`hermes memory setup` uebergibt hier VOLLSTAENDIG (memory_setup.py:
        'delegate entirely to it') -- also gehoert auch die Aktivierung hierher.

        Gefragt werden genau die vier Dinge, ohne die der Anbieter still
        nutzlos ist und die `is_available()` sonst einzeln beanstandet:
        Datenbankpfad, Ausweis, Einbettungsdienst, Betriebsprofil. Der Rest
        des Panels hat brauchbare Vorgaben.

        Und dann wird GEMESSEN statt gemeldet: zum Schluss laeuft dieselbe
        Diagnose wie `hermes brainlehr pruefen`. Eine Einrichtung, die 'fertig'
        sagt, ohne einmal verbunden zu haben, verschiebt den Fehler nur auf
        den ersten echten Zug."""
        heim = Path(hermes_home).expanduser()
        vorher = _hermes_konfig()

        print("\n  brainlehr einrichten / configuring brainlehr:\n")
        werte = dict(vorher)
        werte["db_path"] = _frage(
            "Datenbankpfad / database path", vorher.get("db_path", ""))
        werte["ausweis"] = _frage(
            "Ausweis (handelnde Kennung) / acting identity",
            vorher.get("ausweis", ""))
        werte["embed_service_url"] = _frage(
            "Einbettungsdienst / embedding service",
            vorher.get("embed_service_url", "") or "http://127.0.0.1:11434")
        werte["betriebsprofil"] = _frage(
            "Betriebsprofil (einzelplatz/mandant) / operating profile",
            vorher.get("betriebsprofil", "") or "einzelplatz")

        # Fuenfte Frage: welche Kataloge liegen bereit, und sollen sie JETZT
        # geholt und eingelesen werden? Vorgabe NEIN -- ein Katalog ist ein
        # fremder Bestand mit eigener Lizenz, kein stiller Standardschritt.
        # Nur MCP, kein Import von kern/einrichtung: der Adapter spricht mit
        # brainlehr als eigenem Prozess (42c32f7d), nicht ueber sys.path.
        klient = self._verbindung()
        kataloge_liste = []
        if klient is not None:
            stand = klient.ruf("einrichtung_starten", {}) or {}
            kataloge_liste = (stand.get("lage") or {}).get("kataloge") or []
        if kataloge_liste:
            print("\n  Verfuegbare Kataloge / available catalogs:\n")
            for k in kataloge_liste:
                umfang = k.get("umfang")
                lizenz = (k.get("quelle") or {}).get("lizenz", "ungeprueft")
                print(f"    - {k.get('titel', k.get('name'))}: "
                      f"{umfang if umfang is not None else 'Umfang unbekannt'}, "
                      f"Lizenz: {lizenz}")
            holen = _frage(
                "Diese Kataloge jetzt holen und einlesen? (ja/nein) / "
                "fetch and import these catalogs now?", "nein")
            if holen.strip().lower() in ("ja", "j", "yes", "y"):
                for k in kataloge_liste:
                    if (k.get("quelle") or {}).get("art") != "keine":
                        klient.ruf("katalog_holen", {"name": k["name"]})
                klient.ruf("einrichtung_starten",
                          {"kataloge": [k["name"] for k in kataloge_liste],
                           "bestaetigt": True})

        ziel = heim / "brainlehr" / "config.json"
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(json.dumps(werte, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        print(f"\n  Gespeichert / saved: {ziel}")

        if not isinstance(config.get("memory"), dict):
            config["memory"] = {}
        config["memory"]["provider"] = "brainlehr"
        try:
            from hermes_cli.config import save_config  # type: ignore
            save_config(config)
        except Exception:
            # Ohne Hermes (Pruefstand) gibt es keine config.yaml. Der Aufrufer
            # haelt das Ergebnis dann im uebergebenen dict -- gepruefft wird
            # genau das.
            pass

        grund = self._grund_fuer_unverfuegbar()
        if grund:
            print(f"  ⚠ Noch nicht einsatzbereit / not ready yet: {grund}\n")
        else:
            print("  ✓ brainlehr ist erreichbar und einsatzbereit / ready\n")

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
