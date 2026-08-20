"""brainlehr als Speicher-Anbieter fuer Hermes (Nous Research, MIT).

WAS DAS IST: Hermes bietet unter Einstellungen einen "Memory Provider" an.
Am 2026-08-20 standen dort acht Anbieter zur Auswahl -- byterover, hindsight,
holographic, honcho, mem0, openviking, retaindb, supermemory -- und brainlehr
nicht. Gemessen ueber `hermes memory status`: sieben der acht brauchen einen
API-Schluessel, nur holographic laeuft rein lokal.

WARUM DAS MEHR IST ALS DER VORHANDENE MCP-ZUGANG: brainlehr ist bei Hermes
laengst als MCP-Server angebunden, das Modell KANN also nachschlagen. Ein
Speicher-Anbieter liefert Kontext AUTOMATISCH vor jedem Zug und schreibt
danach zurueck, ohne dass das Modell ein Werkzeug ruft. Der Unterschied
zwischen "kann nachschlagen" und "weiss es schon".

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
  * Schreiben entkoppelt vom Zug (alle vier kleinen Anbieter).
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
import os
import sys
import threading
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


def _brainlehr_heim() -> Optional[Path]:
    """Wo brainlehr liegt. Einstellbar, weil es bei jedem anders liegt."""
    aus_umgebung = os.environ.get("BRAINLEHR_HOME")
    if aus_umgebung:
        p = Path(aus_umgebung).expanduser()
        return p if (p / "knowledge_mcp_server.py").is_file() else None
    for kandidat in (Path.home() / "brainlehr",
                     Path("/Volumes/daten/Begod2026/brainlehr")):
        if (kandidat / "knowledge_mcp_server.py").is_file():
            return kandidat
    return None


class BrainlehrProvider(MemoryProvider):
    """Lokaler Wissensspeicher mit erzwungener Herkunft, Geltung und Freigabe."""

    def __init__(self) -> None:
        self._heim: Optional[Path] = None
        self._sitzung = ""
        self.darf_schreiben = True
        self._vorrat = ""
        self._faden: Optional[threading.Thread] = None

    @property
    def name(self) -> str:
        return "brainlehr"

    # -- Pflicht ------------------------------------------------------------

    def is_available(self) -> bool:
        """Kein Netzaufruf, wie die Schnittstelle es verlangt -- nur nachsehen,
        ob Code und Bestand da sind.

        Wer hier True meldet und erst beim Benutzen scheitert, steht im Menue
        und enttaeuscht dann."""
        heim = _brainlehr_heim()
        if heim is None:
            return False
        try:
            sys.path[:0] = [str(heim), str(heim / "kern"), str(heim / "haken")]
            import ort  # noqa: F401 -- nur die Aufloesung pruefen
            return Path(ort.DB).is_file()
        except Exception:
            return False

    def initialize(self, session_id: str, **kwargs) -> None:
        self._heim = _brainlehr_heim()
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
        if self._heim is None:
            return []
        try:
            sys.path[:0] = [str(self._heim), str(self._heim / "kern"),
                            str(self._heim / "haken")]
            import knowledge_mcp_server as kms
            antwort = kms.knowledge_search(frage, scope="all", max_results=anzahl)
            return antwort.get("results", []) or []
        except Exception:
            return []

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
            if self._heim is None:
                return json.dumps({"fehler": "brainlehr nicht erreichbar"})
            try:
                sys.path[:0] = [str(self._heim), str(self._heim / "kern")]
                import knowledge_mcp_server as kms
                return json.dumps(kms.knowledge_add(
                    parent_path="/shared", title=args["titel"],
                    summary=args["inhalt"][:400], content=args.get("inhalt"),
                    source=args["herkunft"],
                    norm_entscheidung="keine_norm",
                    norm_entschieden_grund="ueber Hermes erfasst, nicht als Regel gemeint",
                ), ensure_ascii=False, default=str)
            except Exception as fehler:
                return json.dumps({"fehler": str(fehler)[:200]}, ensure_ascii=False)
        return json.dumps({"fehler": f"unbekanntes Werkzeug {tool_name}"})

    def backup_paths(self) -> List[str]:
        heim = self._heim or _brainlehr_heim()
        return [str(heim / "brainlehr.db")] if heim else []


def register_memory_provider():
    """Einstiegspunkt fuer Hermes."""
    return BrainlehrProvider()
