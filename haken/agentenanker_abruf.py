#!/usr/bin/env python3
"""agentenanker_abruf.py -- PreToolUse-Haken (Matcher: Agent), Teil 1 des
verengten Abrufs fuer Subagenten (ADR-022, Entscheidung 1 + 3).

ABWEICHUNG VOM AUFTRAG, GEMESSEN, NICHT VERMUTET: Der Auftrag verlangt einen
Haken an `SubagentStart`, der aus dem Auftragstext Anker zieht. Das
SubagentStart-Ereignis traegt den Auftragstext aber NICHT -- geprueft am
gebauten Client (2.1.207, Funktion jzr): sein hookInput ist
`{session_id, transcript_path, cwd, prompt_id, permission_mode, agent_id,
agent_type, effort}`. Kein `prompt`, keine `description`. Dieselbe Luecke
dokumentiert bereits `hub/scripts/agent_model_guard.py` ("SubagentStart
liefert weder `model` noch `task` verlaesslich") -- und loest sie mit
genau der Bauform, die dieses Modul hier uebernimmt: der Text steht nur EINEN
Schritt frueher zur Verfuegung, im `tool_input` des PreToolUse-Aufrufs auf
das Agent-Werkzeug selbst (`tool_input.prompt`), BEVOR der Subagent entsteht.
Zwei Haken statt einem: dieser hier LIEST den Text und RECHNET, sein
Gegenstueck `agentenanker_einspielung.py` (SubagentStart) SPIELT NUR EIN, was
hier schon feststeht -- Bruecke ueber eine eigene, kleine Pending-Datei in
/tmp (FIFO je Sitzung, dieselbe Naeherung wie
`hub/scripts/agent_model_guard.py`/`agent_register_hook.py::_pop_pending`
fuer Modell+Aufgabe: bei mehreren gleichzeitig gestarteten Agenten ist die
Zuordnung best-effort in Aufrufreihenfolge, nicht ID-exakt -- derselbe
akzeptierte Kompromiss wie beim Vorbild).

WAS "VERENGT" HEISST, UND WORAN ES SICH MISST: Der volle Abruf
(`knowledge_recall_hook.py`) sucht ueber den GANZEN Prompt, mit
Embedding+FTS+RRF-Fusion, gemessen 6,0s. Dieser Haken zieht zuerst die
HARTEN ANKER aus dem Auftragstext -- Dateipfade, `.py`-Modulnamen,
`L-xxxxxx`, Plan-Kennungen (`H4`, `G3`, `B4`, `S12`, ...), `ADR-nnn`,
Hex-Kennungen (Commit/Knoten, 7-40 Zeichen) -- und fragt NUR danach, mit
einer einzigen gebuendelten Anfrage (nicht je Anker einzeln). Ohne Anker:
sofort still, keine Anfrage. Das ist die Verengung, und sie ist messbar:
Eingabegroesse (Ankerliste statt Volltext) und Anfrage-Anzahl (1 statt
mehrfach) sind beide kleiner, unabhaengig vom gemessenen Zeitwert.

DIE EXISTENZPROBE (ADR-022, Entscheidung 1) haengt hier MIT DRAN, nicht
daneben: `git log --all --grep=<anker>` und
`hub/scripts/symbolindex.py <anker>` laufen fuer dieselben Anker, die auch
den Wissens-Abruf speisen -- beide unter 50ms gemessen (siehe
`runs/agentenanker_messung_*.json`), kein zusaetzliches Kostenrisiko.

FAIL-OPEN, IMMER: jeder Fehler (Timeout, fehlende Datenbank, kaputtes JSON)
wird verschluckt, der PreToolUse-Aufruf gibt NIE eine `permissionDecision`
zurueck und blockiert nie den Werkzeugaufruf. Dieser Haken ist reine
Nebenwirkung (Pending-Datei schreiben), kein Gate.

Selbsttest: python3 agentenanker_abruf.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ort  # noqa: E402

SYMBOLINDEX = Path("/Volumes/daten/Begod2026/hub/scripts/symbolindex.py")
PENDING = Path(tempfile.gettempdir()) / "claude-agentenanker-pending.jsonl"
MAX_ANKER = 8          # Deckel gegen "50 Dateinamen im Auftrag"
MAX_BYTES = 2_000_000  # gegen Endloswachstum, wie beim Vorbild in hub/
GIT_TIMEOUT = 1.5
SYMBOL_TIMEOUT = 2.0
WISSEN_TIMEOUT = 3.0

# Reihenfolge zaehlt: laengere/spezifischere Muster zuerst, damit ein Pfad
# nicht zusaetzlich als bloßer Modulname doppelt in die Ankerliste faellt
# (die Menge dedupliziert ohnehin per dict.fromkeys, aber so bleibt die
# Herkunft im Test nachvollziehbar).
# Satzende-Punkt darf einen Pfad abschliessen (".md." am Satzende ist der
# Regelfall in deutscher Prosa) -- deshalb NICHT '.' im hinteren Ausschluss,
# nur im vorderen (sonst faengt der Treffer erst nach einem Trennzeichen an).
_RE_PFAD = re.compile(r'(?<![\w.-])(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.[A-Za-z0-9]{1,6}(?![\w-])')
_RE_MODUL = re.compile(r'\b[A-Za-z_][A-Za-z0-9_]*\.py\b')
_RE_LEHRE = re.compile(r'\bL-[0-9a-f]{6}\b')
_RE_ADR = re.compile(r'\bADR-\d{3}\b')
_RE_HEX = re.compile(r'\b[0-9a-f]{7,40}\b')
# Plan-Kennungen dieses Hauses: ein Grossbuchstabe + 1-3 Ziffern (H4, G3, S12,
# B4, I3, ...). Bewusst OHNE reine Zahlen ("97" allein): eine nackte Zahl ist
# von gewoehnlicher Prosa nicht unterscheidbar und waere Rauschen, kein Anker
# -- siehe Docstring-Abschnitt "WAS AUSDRUECKLICH NICHT GEHT" unten.
_RE_PLANID = re.compile(r'\b[A-Z]\d{1,3}\b')

# Bau-Signal (ADR-022, Entscheidung 1: "Vor jedem Auftrag, der etwas BAUEN
# soll"). OHNE dieses Gate feuert der Haken bei jedem Anker, auch wenn der
# Anker nur die Datei ist, die ein reiner Lese-/Review-/Persona-Auftrag
# ohnehin nennt -- git/symbolindex finden sie dann IMMER (es ist ja die
# eigene Datei), das ist kein Existenzbeleg, nur Rauschen. GEMESSEN gegen 120
# echte Auftragstexte des Tages (siehe Auftragsbericht): ohne Gate 102/120
# Treffer (85%, ueberwiegend Rauschen -- Review-, Persona- und reine
# Lese-Auftraege trafen genauso wie echte Bauauftraege). Das Gate ist die
# Lehre aus dieser Messung, nicht eine Vorab-Annahme.
_RE_BAUSIGNAL = re.compile(
    r'\b(bau(e|en|t)?|erstell(e|t|en)?|implementier(e|t|en)?|schreib(e|t|en)?|'
    r'anleg(e|t|en)?|entwickl(e|t|en)?|erzeug(e|t|en)?|verdrahte(n|t)?|'
    r'programmier(e|t|en)?|f[uü]g(e|t|en)? .{0,20}hinzu|richte .{0,20}ein)\b',
    re.IGNORECASE)


def _liegt_vor(anker: str, cwd: str) -> str:
    """Liegt die genannte Datei bereits auf der Platte?

    Exakt und rauschfrei, im Gegensatz zu `git log --grep=<dateiname>`: dort
    trifft jeder Commit, der die Datei je beruehrt hat, und das sagt ueber ein
    VORHABEN nichts. Hier ist der Fund die Sache selbst.

    Ein Modulname ohne Pfad (`speicher.py`) wird flach unter den bekannten
    Verzeichnissen gesucht -- absichtlich nicht rekursiv ueber den ganzen Baum,
    weil ein Allerweltsname sonst wieder Rauschen erzeugt."""
    p = Path(cwd) / anker
    if p.exists():
        return anker
    if "/" not in anker:
        for ordner in ("kern", "haken", "melder", "berichte", "tests", "pflege"):
            k = Path(cwd) / ordner / anker
            if k.exists():
                return f"{ordner}/{anker}"
    return ""


def _ist_praeziser_anker(anker: str) -> bool:
    """Traegt der Anker eine Kennung, die jemand BEWUSST in eine
    Commit-Nachricht schreibt?

    Nur fuer diese Sorte ist ein Treffer in `git log --grep` eine Aussage
    ueber ein VORHABEN. Ein Dateiname trifft dort auch dann, wenn die Datei
    nur beilaeufig beruehrt wurde -- das ist die gemessene Rauschquelle
    (91 von 120 Auftraegen, 2026-08-15)."""
    return bool(
        _RE_LEHRE.fullmatch(anker)
        or _RE_ADR.fullmatch(anker)
        or _RE_PLANID.fullmatch(anker)
        or _RE_HEX.fullmatch(anker)
    )


def anker_ziehen(text: str, hoechstens: int = MAX_ANKER) -> list[str]:
    """Harte Anker aus dem Auftragstext -- keine Woerter, nur Kennungen.

    WAS AUSDRUECKLICH NICHT GEHT: informelle Planlabel wie "Dienststart"
    (ein deutsches Wort, kein Muster) oder eine nackte Zeilennummer wie "97"
    werden NICHT erkannt -- jedes Muster dafuer waere entweder zu eng (nur
    dieser eine Fall) oder zu weit (jede Zahl im Text). Das ist eine
    Grenzentscheidung, kein Versehen: von den fuenf Faellen aus L-229bb2
    treffen H4/H5/H7 auf _RE_PLANID, "97" und "Dienststart" nicht -- siehe
    Positivkontrolle im Auftragsbericht."""
    if not text:
        return []
    gefunden: list[str] = []
    for muster in (_RE_PFAD, _RE_MODUL, _RE_LEHRE, _RE_ADR, _RE_PLANID, _RE_HEX):
        for m in muster.findall(text):
            if m not in gefunden:
                gefunden.append(m)
    return gefunden[:hoechstens]


def git_treffer(anker: str, cwd: str, timeout: float = GIT_TIMEOUT) -> list[str]:
    try:
        r = subprocess.run(
            ["git", "log", "--all", "--oneline", "--grep=" + anker, "-i", "-n", "2"],
            cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return [z for z in r.stdout.splitlines() if z.strip()]
    except Exception:
        return []


def symbolindex_treffer(anker: str, timeout: float = SYMBOL_TIMEOUT) -> list[str]:
    if not SYMBOLINDEX.exists():
        return []
    try:
        r = subprocess.run(["python3", str(SYMBOLINDEX), anker],
                            capture_output=True, text=True, timeout=timeout)
        out = r.stdout.strip()
        if not out or "keine Treffer" in out:
            return []
        return out.splitlines()[:3]
    except Exception:
        return []


_WISSEN_CODE = """
import sys, json
sys.path.insert(0, {wurzel!r})
try:
    import knowledge_mcp_server as kms
    r = kms.knowledge_search({anfrage!r}, max_results=3)
    treffer = [(t.get("path") or t.get("id",""), t.get("title") or t.get("summary","")) for t in r.get("results", [])]
except Exception:
    treffer = []
print(json.dumps(treffer))
"""


def wissen_treffer(anfrage: str, timeout: float = WISSEN_TIMEOUT) -> list[tuple[str, str]]:
    """Eigener Unterprozess statt In-Prozess-Import: begrenzt das Zeitrisiko
    hart (subprocess.timeout schlaegt zuverlaessig zu, ein haengender
    In-Prozess-Aufruf in einem PreToolUse-Haken wuerde JEDE Agenten-
    Delegation anhalten -- genau die Bremse, vor der ADR-022 warnt)."""
    if not anfrage.strip():
        return []
    code = _WISSEN_CODE.format(wurzel=str(ort.WURZEL), anfrage=anfrage)
    try:
        r = subprocess.run(["python3", "-c", code], capture_output=True, text=True,
                            timeout=timeout, cwd=str(ort.WURZEL))
        if not r.stdout.strip():
            return []
        return [tuple(x) for x in json.loads(r.stdout)]
    except Exception:
        return []


def existenzprobe(anker_liste: list[str], cwd: str) -> dict[str, list[str]]:
    """Git+Symbolindex je Anker -- die MITGELIEFERTE Antwort auf 'gibt es
    das schon', nicht nur eine Mahnung zur Sorgfalt."""
    treffer: dict[str, list[str]] = {}
    for anker in anker_liste:
        # Gemessen 2026-08-15 gegen 120 echte Auftraege: 91 Treffer (76 %),
        # ueberwiegend Rauschen. Ursache benannt vom bauenden Agenten selbst --
        # "Datei existiert" ist NICHT dasselbe wie "Vorhaben existiert schon".
        # Ein `git log --grep=<dateiname>` trifft jeden Commit, der die Datei je
        # beruehrt hat, und das sagt ueber ein VORHABEN nichts.
        #
        # Deshalb: der Commit-Weg gilt nur fuer PRAEZISE Anker -- Kennungen, die
        # jemand bewusst in eine Commit-Nachricht schreibt (L-xxxxxx, ADR-nnn,
        # Planzeile, Hex-Kennung). Datei- und Modulanker laufen ausschliesslich
        # ueber den Symbolindex, der nach TAETIGKEIT sucht (Docstring, Kommentar)
        # statt nach Namen -- er beantwortet "gibt es so etwas schon", waehrend
        # git log nur "gibt es diese Datei" beantwortet.
        #
        # Ein Waechter mit drei belanglosen Einspielungen je Auftrag wird
        # ueberlesen und ist dann schlechter als keiner (L-7bc26e).
        fund = [f"symbol: {z}" for z in symbolindex_treffer(anker)]
        if _ist_praeziser_anker(anker):
            fund = git_treffer(anker, cwd) + fund
        else:
            # Datei- und Modulanker: die EXISTENZ auf der Platte ist die
            # Aussage, nicht die Erwaehnung in einer Commit-Nachricht.
            # "Lege haken/existenzpruefung.py an" + die Datei liegt da = Fund.
            # "Aendere haken/x.py" + git log nennt sie = nichts.
            liegt = _liegt_vor(anker, cwd)
            if liegt:
                fund = [f"liegt bereits: {liegt}"] + fund
        if fund:
            treffer[anker] = fund
    return treffer


def baue_block(anker_liste: list[str], probe: dict[str, list[str]],
               wissen: list[tuple[str, str]]) -> str | None:
    if not probe and not wissen:
        return None
    zeilen = ["<agentenanker-abruf>",
              "Existenzprobe und Wissensabruf zu den Kennungen aus diesem "
              "Auftrag, VOR der Arbeit gepruefte Treffer -- ein Treffer heisst "
              "'schon vorhanden', keine Bewertung des Auftrags:"]
    for anker, fund in probe.items():
        zeilen.append(f"- {anker}:")
        zeilen.extend(f"    {z}" for z in fund[:3])
    if wissen:
        zeilen.append("- Wissensspeicher:")
        zeilen.extend(f"    {p} · {t[:70]}" for p, t in wissen)
    zeilen.append("</agentenanker-abruf>")
    return "\n".join(zeilen)


def _pending_append(session: str, block: str) -> None:
    try:
        if PENDING.exists() and PENDING.stat().st_size > MAX_BYTES:
            PENDING.unlink()
        with open(PENDING, "a", encoding="utf-8") as f:
            f.write(json.dumps({"session": session, "ts": time.time(), "block": block}) + "\n")
    except OSError:
        pass


def main() -> int:
    try:
        daten = json.load(sys.stdin)
    except Exception:
        return 0
    tool_input = daten.get("tool_input") or {}
    prompt = str(tool_input.get("prompt") or tool_input.get("description") or "")
    session = str(daten.get("session_id") or "")
    cwd = str(daten.get("cwd") or os.getcwd())
    if not prompt or not session:
        return 0

    if not _RE_BAUSIGNAL.search(prompt):  # kein Bau-Auftrag -> Existenzprobe passt nicht
        return 0
    anker = anker_ziehen(prompt)
    if not anker:  # Gegenprobe: kein Anker -> nichts einspielen, nichts rechnen
        return 0

    try:
        probe = existenzprobe(anker, cwd)
        wissen = wissen_treffer(" ".join(anker[:5]))
        block = baue_block(anker, probe, wissen)
    except Exception:
        return 0

    if block:
        _pending_append(session, block)
    return 0


def _selftest() -> int:
    ok = True

    faelle = [
        ("Fund in haken/knowledge_recall_hook.py pruefen (L-229bb2), siehe ADR-022.",
         ["haken/knowledge_recall_hook.py", "L-229bb2", "ADR-022"]),
        ("Baue H4 und G3 fertig, orientiere dich an docs/PLAN_GESAMT_2026-08-13.md.",
         ["docs/PLAN_GESAMT_2026-08-13.md", "H4", "G3"]),
        ("Ganz gewoehnlicher Satz ohne jede Kennung oder Datei.", []),
        ("", []),
    ]
    for text, erwartet in faelle:
        gefunden = anker_ziehen(text)
        okk = set(erwartet) <= set(gefunden) if erwartet else gefunden == []
        ok &= okk
        print(f"  Anker aus {text!r}: {gefunden} -- {'OK' if okk else 'FEHLER (erwartet mind. ' + str(erwartet) + ')'}")

    # Grenzwert: 50 Dateinamen im Auftrag -> Deckel MAX_ANKER greift
    viele = " ".join(f"kern/modul{i}.py" for i in range(50))
    gedeckelt = anker_ziehen(viele)
    okk = len(gedeckelt) == MAX_ANKER
    ok &= okk
    print(f"  Deckel bei 50 Dateinamen: {len(gedeckelt)} von {MAX_ANKER} -- {'OK' if okk else 'FEHLER'}")

    # Grenzwert: Kennung, die es nicht gibt -> git/symbolindex liefern leer, kein Absturz
    probe = existenzprobe(["ZZZ999NICHTVORHANDEN"], str(ort.WURZEL))
    okk = probe == {}
    ok &= okk
    print(f"  Erfundene Kennung ohne Treffer: {probe} -- {'OK' if okk else 'FEHLER'}")

    # Grenzwert: Datenbank nicht erreichbar (Pfad zeigt ins Leere)
    import contextlib, io
    alt_wurzel = ort.WURZEL
    try:
        ort.WURZEL = Path("/nicht/vorhanden/xyz")
        r = wissen_treffer("irgendwas")
        okk2 = r == []
        ok &= okk2
        print(f"  Datenbank unerreichbar -> leere Liste: {'OK' if okk2 else 'FEHLER'}")
    finally:
        ort.WURZEL = alt_wurzel

    # main() Gegenprobe: kein Anker im Prompt -> keine Pending-Zeile
    with tempfile.TemporaryDirectory() as td:
        global PENDING
        alt_pending = PENDING
        PENDING = Path(td) / "pending.jsonl"
        try:
            eingabe = {"tool_input": {"prompt": "einfach nur Prosa, keine Kennung hier"},
                       "session_id": "sess-test", "cwd": str(ort.WURZEL)}
            alt_stdin = sys.stdin
            sys.stdin = io.StringIO(json.dumps(eingabe))
            main()
            sys.stdin = alt_stdin
            okk3 = not PENDING.exists()
            ok &= okk3
            print(f"  Gegenprobe ohne Anker -> keine Pending-Datei: {'OK' if okk3 else 'FEHLER'}")

            # leerer Auftragstext -> ebenfalls still
            sys.stdin = io.StringIO(json.dumps({"tool_input": {"prompt": ""}, "session_id": "s2"}))
            main()
            sys.stdin = alt_stdin
            okk4 = not PENDING.exists()
            ok &= okk4
            print(f"  Leerer Auftragstext -> still: {'OK' if okk4 else 'FEHLER'}")
        finally:
            PENDING = alt_pending

    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
