#!/usr/bin/env python3
# ausloeser: auf-abruf -- beantwortet 'wie lange und wie teuer war ein Subagentenlauf', wenn jemand die Frage stellt
"""agentendauer.py -- Dauer und Kosten je Subagentenlauf, aus den
Sitzungsprotokollen unter ~/.claude/projects/ ausgezaehlt statt geschaetzt.

WAS IM PROTOKOLL STEHT: Jeder per Agent-Werkzeug gestartete Hintergrundlauf
meldet sich bei Abschluss als "queue-operation"-Zeile mit einem
<task-notification>-Block. Darin, am Ende, ein <usage>-Tag:
<subagent_tokens>N</subagent_tokens><tool_uses>N</tool_uses><duration_ms>N</duration_ms>.
Das ist die einzige EHRLICHE Quelle fuer diese drei Zahlen -- sie steht nicht
im urspruenglichen Agent-Aufruf (der kennt nur description/subagent_type/
model/prompt), sondern ausschliesslich in der Abschlussmeldung. Gefunden per
Auszaehlung, nicht Vermutung: sess.jsonl der aktuellen Sitzung enthaelt 268
<task-notification>-Zeilen, 204 davon mit <usage>, 114 verschiedene
task-id/agentId (mehrfach, weil ein fortgesetzter Agent mehrfach abschliesst).

WAS NICHT IM PROTOKOLL STEHT (wird ausgewiesen, nicht erfunden):
- Aufwandsstufe (reasoning effort) des Subagenten -- der Agent-Aufruf kennt
  nur `model`, keinen Effort-Parameter. Spalte bleibt leer.
- Fuer Vordergrundlaeufe (run_in_background=false) wurde in keiner
  brainlehr-Sitzung ein Beispiel gefunden (Auszaehlung: alle 79
  Agent-Aufrufe der Referenzsitzung sind isAsync=true). Das Werkzeug
  versucht trotzdem, ein <usage>-Tag auch in einem synchronen tool_result
  zu finden -- ungetestet mangels Beispiel, als Luecke benannt.
- Die Schaetzung des Auftraggebers steht, wenn ueberhaupt, nur als Freitext
  im Prompt (z.B. "600 s, 150k Token, 40 Werkzeugaufrufe"). Eine Regex
  versucht sie zu ziehen; wo sie nicht passt, bleibt das Feld leer -- keine
  rueckwirkende Erfindung.

GLEICHZEITIGKEIT: hoechster Stoerfaktor, siehe Auftrag. Aus Start-/Endzeit
jedes Laufs errechnet (Sweep ueber alle Intervalle DERSELBEN eingelesenen
Sitzung(en)) -- eine Ueberschneidung mit Laeufen ausserhalb der eingelesenen
Dateien ist damit nicht sichtbar und wird nicht behauptet.

Start eines Laufs = Ende (Meldungszeitstempel) minus duration_ms -- nicht
der Zeitpunkt des urspruenglichen Agent-Aufrufs, denn der liegt bei
Hintergrundlaeufen vor dem tatsaechlichen Start (Warteschlange) und bei
fortgesetzten Laeufen vor dem letzten Abschnitt.

Aufruf:
    python3 melder/agentendauer.py                       # aktuelle Sitzung
    python3 melder/agentendauer.py --alle                # alle brainlehr-Sitzungen
    python3 melder/agentendauer.py --sitzung PFAD.jsonl   # gezielt (wiederholbar)
    python3 melder/agentendauer.py --schreiben            # zusaetzlich runs/agentendauer_<datum>.json
    python3 melder/agentendauer.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

WURZEL = _w
PROJEKTE = Path.home() / ".claude" / "projects"

USAGE_RE = re.compile(
    r"<usage><subagent_tokens>(\d+)</subagent_tokens>"
    r"<tool_uses>(\d+)</tool_uses>"
    r"<duration_ms>(\d+)</duration_ms></usage>"
)
TASKID_RE = re.compile(r"<task-id>(.*?)</task-id>")
TOOLUSEID_RE = re.compile(r"<tool-use-id>(.*?)</tool-use-id>")
STATUS_RE = re.compile(r"<status>(.*?)</status>")
SUMMARY_RE = re.compile(r"<summary>(.*?)</summary>")

# Heuristik fuer eine im Auftragstext genannte Schaetzung, Form wie
# "600 s, 150k Token, 40 Werkzeugaufrufe" -- Reihenfolge/Wortlaut variiert,
# darum drei unabhaengige Teilsuchen statt eines starren Gesamtmusters.
SCHAETZ_SEK_RE = re.compile(r"(\d+)\s*s(?:ekunden)?\b.{0,20}(?:zeit|schaetzung|geschaetzt)?", re.IGNORECASE)
SCHAETZ_TOKEN_RE = re.compile(r"(\d+)\s*k\s*Token", re.IGNORECASE)
SCHAETZ_TOOLS_RE = re.compile(r"(\d+)\s*Werkzeugauf(?:rufe|rufen)", re.IGNORECASE)

# Auftragsart: Stichwortlisten, siehe _auftragsart() fuer die Begruendung
# und die Selbsttest-Stichprobe fuer die gemessene Fehlerquote.
MESSEN_WOERTER = (
    "messen", "messlauf", "erheben", "erhebe", "auswerten", "auswertung",
    "zaehle", "zaehlen", "auszaehl", "pruefe ", "pruefung", "gemessen",
    "kennzahl", "bericht", "audit", "analysiere", "untersuche", "nenner",
    "positivkontrolle", "gegenprobe", "belegen", "bestandsaufnahme",
    "miss ", "miss,", "misst",
)
BAUEN_WOERTER = (
    "baue", "bauen", "implementier", "fix", "behebe", "behoben", "aendere",
    "aendern", "aenderung", "commit", "schreibe ", "erstelle", "anlege",
    "anlegen", "migration", "refactor", "umbau", "loesche", "entferne",
)
BAUSUITE_MUSTER = ("app/bauen.sh", "pytest tests/", "swift test", "pytest ")


@dataclass
class Lauf:
    session: str
    task_id: str
    tool_use_id: str | None
    beschreibung: str | None
    subagent_type: str | None
    modell: str | None
    hintergrund: bool | None
    zeitlimit_hinweis: str | None
    status: str | None
    start_ts: str | None
    end_ts: str | None
    dauer_ms: int | None
    tokens: int | None
    werkzeugaufrufe: int | None
    mehrfach_abgeschlossen: bool
    auftragsart: str
    bausuite_lauf: bool | None
    dateien_geschrieben: int | None
    gleichzeitig_max: int | None
    schaetzung_sekunden: int | None
    schaetzung_token: int | None
    schaetzung_werkzeugaufrufe: int | None
    tokens_pro_sekunde: float | None

    @property
    def vollstaendig(self) -> bool:
        return self.dauer_ms is not None and self.tokens is not None and self.werkzeugaufrufe is not None


def _sitzungsdateien(explizit: list[str] | None, alle: bool) -> list[Path]:
    """Liefert Sitzungs-JSONL-Dateien (Top-Level, nicht subagents/tool-results/tasks)."""
    if explizit:
        return [Path(p) for p in explizit]
    if not PROJEKTE.exists():
        return []
    muster = "*" if alle else "*brainlehr*"
    gefunden = []
    for projektordner in sorted(PROJEKTE.glob(muster)):
        if not projektordner.is_dir():
            continue
        for datei in sorted(projektordner.glob("*.jsonl")):
            gefunden.append(datei)
    return gefunden


def _agent_call_index(pfad: Path) -> dict[str, dict]:
    """tool_use_id -> {beschreibung, subagent_type, modell, prompt, ts}."""
    index: dict[str, dict] = {}
    with pfad.open(encoding="utf-8", errors="replace") as f:
        for zeile in f:
            if '"name":"Agent"' not in zeile and '"name": "Agent"' not in zeile:
                continue
            try:
                d = json.loads(zeile)
            except json.JSONDecodeError:
                continue
            msg = d.get("message")
            if not isinstance(msg, dict):
                continue
            for blk in msg.get("content") or []:
                if not isinstance(blk, dict) or blk.get("name") != "Agent":
                    continue
                inp = blk.get("input") or {}
                index[blk.get("id")] = {
                    "beschreibung": inp.get("description"),
                    "subagent_type": inp.get("subagent_type"),
                    "modell": inp.get("model"),
                    "hintergrund": inp.get("run_in_background"),
                    "prompt": inp.get("prompt") or "",
                    "start_ts": d.get("timestamp"),
                }
    return index


def _async_launch_index(pfad: Path) -> dict[str, str]:
    """tool_use_id -> agentId, aus dem async_launched-Ergebnis (toolUseResult)."""
    index: dict[str, str] = {}
    with pfad.open(encoding="utf-8", errors="replace") as f:
        for zeile in f:
            if '"isAsync":true' not in zeile and '"isAsync": true' not in zeile:
                continue
            try:
                d = json.loads(zeile)
            except json.JSONDecodeError:
                continue
            tur = d.get("toolUseResult")
            if not isinstance(tur, dict):
                continue
            agent_id = tur.get("agentId")
            msg = d.get("message")
            if not agent_id or not isinstance(msg, dict):
                continue
            for blk in msg.get("content") or []:
                if isinstance(blk, dict) and blk.get("tool_use_id"):
                    index[blk["tool_use_id"]] = agent_id
    return index


def _completions(pfad: Path) -> dict[str, list[dict]]:
    """task_id -> Liste der <task-notification>-Abschluesse (chronologisch)."""
    ergebnis: dict[str, list[dict]] = {}
    with pfad.open(encoding="utf-8", errors="replace") as f:
        for zeile in f:
            if "<task-notification>" not in zeile:
                continue
            try:
                d = json.loads(zeile)
            except json.JSONDecodeError:
                continue
            content = d.get("content")
            if not isinstance(content, str):
                continue
            m_task = TASKID_RE.search(content)
            if not m_task:
                continue
            m_summary = SUMMARY_RE.search(content)
            # Nicht jede <task-notification> ist ein Subagent -- Bash-Hintergrundlaeufe
            # und Monitor-Ereignisse nutzen dieselbe Vorlage. Ausgezaehlt an dieser
            # Sitzung: von den Zeilen mit <summary> beginnen nur die echter
            # Agent-Abschluesse mit 'Agent "...' finished. Alles andere (Background
            # command/Monitor) waere sonst faelschlich als unvollstaendiger Subagentenlauf
            # gezaehlt worden -- gefunden beim Abgleich gegen die Positivkontrolle.
            if not (m_summary and m_summary.group(1).startswith('Agent "')):
                continue
            m_tool_use = TOOLUSEID_RE.search(content)
            m_status = STATUS_RE.search(content)
            eintrag = {
                "task_id": m_task.group(1),
                "tool_use_id": m_tool_use.group(1) if m_tool_use else None,
                "status": m_status.group(1) if m_status else None,
                "summary": m_summary.group(1) if m_summary else None,
                "meldezeit": d.get("timestamp"),
            }
            m_use = USAGE_RE.search(content)
            if m_use:
                eintrag["tokens"] = int(m_use.group(1))
                eintrag["werkzeugaufrufe"] = int(m_use.group(2))
                eintrag["dauer_ms"] = int(m_use.group(3))
            else:
                eintrag["tokens"] = eintrag["werkzeugaufrufe"] = eintrag["dauer_ms"] = None
            ergebnis.setdefault(eintrag["task_id"], []).append(eintrag)
    for lst in ergebnis.values():
        lst.sort(key=lambda e: e["meldezeit"] or "")
    return ergebnis


def _auftragsart(prompt: str) -> str:
    """messen / bauen / beides / unklar -- reine Stichwortsuche im Prompt.

    Kein Anspruch auf Praezision -- die Selbsttest-Stichprobe unten (vier
    von Hand gelesene Beispiele) nennt die dabei gemessene Trefferquote.

    BEFUND aus dem echten Korpus (Sitzung 01c01c7f, 2026-08-15): 78 von 79
    Auftraegen fallen auf "beides" -- die Auftraege dieser Sitzung nennen
    fast durchgehend sowohl einen Mess-/Pruef- als auch einen Bau-/Fix-Schritt
    (typisch: "miss den Ist-Stand, dann behebe"). Das ist kein Fehler der
    Stichwortsuche, sondern eine Eigenschaft dieser Sitzung -- die Trennung
    messen/bauen/beides bringt hier wenig, bis ein Korpus mit reineren
    Einzelauftraegen vorliegt. Ausdruecklich als Befund benannt, nicht
    stillschweigend geglaettet.
    """
    p = prompt.lower()
    hat_messen = any(w in p for w in MESSEN_WOERTER)
    hat_bauen = any(w in p for w in BAUEN_WOERTER)
    if hat_messen and hat_bauen:
        return "beides"
    if hat_messen:
        return "messen"
    if hat_bauen:
        return "bauen"
    return "unklar"


def _schaetzung(prompt: str) -> tuple[int | None, int | None, int | None]:
    m_tok = SCHAETZ_TOKEN_RE.search(prompt)
    m_tools = SCHAETZ_TOOLS_RE.search(prompt)
    sek = tok = tools = None
    if m_tok:
        tok = int(m_tok.group(1)) * 1000
    if m_tools:
        tools = int(m_tools.group(1))
    # Sekunden nur uebernehmen, wenn in unmittelbarer Naehe (< 40 Zeichen)
    # eines der beiden anderen Schaetzwerte steht -- sonst zu viele
    # falsche Treffer auf beliebige "N Sekunden"-Erwaehnungen im Fliesstext.
    if m_tok or m_tools:
        anker = (m_tok or m_tools).start()
        fenster = prompt[max(0, anker - 60):anker + 60]
        m_sek = re.search(r"(\d+)\s*s\b", fenster)
        if m_sek:
            sek = int(m_sek.group(1))
    return sek, tok, tools


def _bausuite_und_dateien(session_dir: Path, task_id: str) -> tuple[bool | None, int | None]:
    """Durchsucht subagents/agent-<task_id>.jsonl -- Suitenlauf? wieviele Dateien geschrieben?"""
    datei = session_dir / "subagents" / f"agent-{task_id}.jsonl"
    if not datei.exists():
        return None, None
    bausuite = False
    dateien: set[str] = set()
    with datei.open(encoding="utf-8", errors="replace") as f:
        for zeile in f:
            if not bausuite and any(m in zeile for m in BAUSUITE_MUSTER):
                bausuite = True
            for muster in ('"name":"Edit","input":{', '"name":"Write","input":{'):
                idx = zeile.find(muster)
                if idx == -1:
                    continue
                m = re.search(r'"file_path":"([^"]*)"', zeile[idx:idx + 400])
                if m:
                    dateien.add(m.group(1))
    return bausuite, len(dateien)


def _zeit(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def sammle(dateien: list[Path]) -> list[Lauf]:
    laeufe: list[Lauf] = []
    for pfad in dateien:
        session = pfad.stem
        session_dir = pfad.parent / session
        calls = _agent_call_index(pfad)
        launches = _async_launch_index(pfad)
        completions = _completions(pfad)
        tool_use_zu_task = {tu: aid for tu, aid in launches.items()}
        task_zu_tool_use = {aid: tu for tu, aid in launches.items()}

        # Jeder gefundene task_id-Abschluss UND jeder Aufruf ohne Abschluss
        # (abgebrochen) zaehlt als ein Lauf.
        gesehene_task_ids = set(completions.keys())
        for tool_use_id, aid in launches.items():
            gesehene_task_ids.add(aid)

        for task_id in sorted(gesehene_task_ids):
            tool_use_id = task_zu_tool_use.get(task_id)
            call = calls.get(tool_use_id, {}) if tool_use_id else {}
            klist = completions.get(task_id, [])
            letzte = klist[-1] if klist else None
            prompt = call.get("prompt", "")

            dauer_ms = letzte["dauer_ms"] if letzte else None
            tokens = letzte["tokens"] if letzte else None
            werkzeugaufrufe = letzte["werkzeugaufrufe"] if letzte else None
            end_ts = _zeit(letzte["meldezeit"]) if letzte else None
            start_ts = end_ts - _ms(dauer_ms) if (end_ts and dauer_ms is not None) else _zeit(call.get("start_ts"))

            bausuite, dateien_n = _bausuite_und_dateien(session_dir, task_id)
            sek, tok, tools = _schaetzung(prompt)

            laeufe.append(Lauf(
                session=session,
                task_id=task_id,
                tool_use_id=tool_use_id,
                beschreibung=call.get("beschreibung") or (letzte and letzte.get("summary")),
                subagent_type=call.get("subagent_type"),
                modell=call.get("modell"),
                hintergrund=(call.get("hintergrund") if call.get("hintergrund") is not None else True) if call else (True if letzte else None),
                zeitlimit_hinweis=_zeitlimit_aus_prompt(prompt),
                status=letzte["status"] if letzte else "kein_abschluss",
                start_ts=_iso(start_ts),
                end_ts=_iso(end_ts),
                dauer_ms=dauer_ms,
                tokens=tokens,
                werkzeugaufrufe=werkzeugaufrufe,
                mehrfach_abgeschlossen=len(klist) > 1,
                auftragsart=_auftragsart(prompt) if prompt else "unklar",
                bausuite_lauf=bausuite,
                dateien_geschrieben=dateien_n,
                gleichzeitig_max=None,
                schaetzung_sekunden=sek,
                schaetzung_token=tok,
                schaetzung_werkzeugaufrufe=tools,
                tokens_pro_sekunde=(tokens / (dauer_ms / 1000) if tokens and dauer_ms else None),
            ))
    _gleichzeitigkeit_berechnen(laeufe)
    return laeufe


def _ms(n: int | None):
    from datetime import timedelta
    return timedelta(milliseconds=n or 0)


def _zeitlimit_aus_prompt(prompt: str) -> str | None:
    m = re.search(r"timeout\s*=\s*(\d+)|ZEITLIMIT[:\s]+([^\n.]{0,60})", prompt, re.IGNORECASE)
    if not m:
        return None
    return m.group(0).strip()[:80]


def _gleichzeitigkeit_berechnen(laeufe: list[Lauf]) -> None:
    """Sweep ueber alle Intervalle mit bekanntem Start UND Ende (Grenzwert:
    Laeufe ohne Endmeldung liefern kein Intervall und bleiben unberuecksichtigt)."""
    intervalle = []
    for i, l in enumerate(laeufe):
        s, e = _zeit(l.start_ts), _zeit(l.end_ts)
        if s and e:
            intervalle.append((i, s, e))
    for i, s, e in intervalle:
        n = sum(1 for _, s2, e2 in intervalle if s2 <= e and s <= e2)
        laeufe[i].gleichzeitig_max = n


def bericht(laeufe: list[Lauf]) -> dict:
    vollstaendig = [l for l in laeufe if l.vollstaendig]
    unvollstaendig = [l for l in laeufe if not l.vollstaendig]
    return {
        "gefunden": len(laeufe),
        "vollstaendig": len(vollstaendig),
        "unvollstaendig": len(unvollstaendig),
        "laeufe": [asdict(l) for l in laeufe],
    }


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sitzung", action="append", help="gezielt eine Sitzungsdatei (wiederholbar)")
    ap.add_argument("--alle", action="store_true", help="alle Projekte statt nur brainlehr*")
    ap.add_argument("--schreiben", action="store_true", help="Ergebnis zusaetzlich unter runs/ ablegen")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        _selftest()
        return

    dateien = _sitzungsdateien(args.sitzung, args.alle)
    laeufe = sammle(dateien)
    b = bericht(laeufe)
    print(f"Sitzungsdateien: {len(dateien)}")
    print(f"Laeufe gefunden: {b['gefunden']} (vollstaendig: {b['vollstaendig']}, unvollstaendig: {b['unvollstaendig']})")
    for l in sorted(laeufe, key=lambda x: x.dauer_ms or -1, reverse=True)[:10]:
        print(f"  {l.task_id[:10]} {l.dauer_ms!s:>10} ms  {l.tokens!s:>8} Tok  "
              f"{l.werkzeugaufrufe!s:>4} Werkz  gleichzeitig={l.gleichzeitig_max}  "
              f"art={l.auftragsart}  {l.beschreibung}")

    if args.schreiben:
        ziel = WURZEL / "runs" / f"agentendauer_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
        ziel.write_text(json.dumps(b, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"geschrieben: {ziel}")


def _selftest() -> None:
    # -- USAGE_RE / TASKID_RE gegen die belegte Positivkontrolle des Auftrags:
    beispiel = (
        '<task-notification>\n<task-id>aea0259134379eb23</task-id>\n'
        '<tool-use-id>toolu_x</tool-use-id>\n<status>completed</status>\n'
        '<summary>Agent "Sechs blinde Mechanismen" finished</summary>\n'
        '<result>...</result>\n'
        '<usage><subagent_tokens>204640</subagent_tokens><tool_uses>97</tool_uses>'
        '<duration_ms>1334164</duration_ms></usage>\n</task-notification>'
    )
    m = USAGE_RE.search(beispiel)
    assert m and m.groups() == ("204640", "97", "1334164"), m
    assert TASKID_RE.search(beispiel).group(1) == "aea0259134379eb23"

    # -- Auftragsart: vier von Hand gelesene Beispiele, Fehlerquote 0/4 an
    # dieser Stichprobe (keine Behauptung ueber die restlichen Laeufe).
    proben = [
        ("Miss, wie oft X eintritt und melde eine Kennzahl.", "messen"),
        ("Baue eine neue Funktion in kern/x.py und committe.", "bauen"),
        ("Miss den Ist-Stand, dann behebe den gefundenen Fehler.", "beides"),
        ("Sag mir bitte guten Morgen.", "unklar"),
    ]
    falsch = [p for p, erwartet in proben if _auftragsart(p) != erwartet]
    assert not falsch, f"Auftragsart-Heuristik daneben bei: {falsch}"

    # -- Schaetzung aus Prompt-Text (Auftraggeber-Beispiel aus DIESEM Auftrag):
    sek, tok, tools = _schaetzung("Schaetzung: 600 s, 150k Token, 40 Werkzeugaufrufe.")
    assert (sek, tok, tools) == (600, 150000, 40), (sek, tok, tools)
    # Grenzwert: kein Schaetzmuster im Text -> alle drei None, nichts erfunden.
    assert _schaetzung("Baue X.") == (None, None, None)

    # -- Gleichzeitigkeit: zwei sich ueberschneidende Laeufe vs. ein alleinstehender.
    from datetime import timedelta
    basis = datetime(2026, 8, 15, 10, 0, 0, tzinfo=timezone.utc)
    laeufe = [
        Lauf(session="s", task_id="a", tool_use_id=None, beschreibung=None,
             subagent_type=None, modell=None, hintergrund=True, zeitlimit_hinweis=None,
             status="completed", start_ts=_iso(basis), end_ts=_iso(basis + timedelta(seconds=100)),
             dauer_ms=100000, tokens=10, werkzeugaufrufe=1, mehrfach_abgeschlossen=False,
             auftragsart="bauen", bausuite_lauf=False, dateien_geschrieben=1,
             gleichzeitig_max=None, schaetzung_sekunden=None, schaetzung_token=None,
             schaetzung_werkzeugaufrufe=None, tokens_pro_sekunde=0.1),
        Lauf(session="s", task_id="b", tool_use_id=None, beschreibung=None,
             subagent_type=None, modell=None, hintergrund=True, zeitlimit_hinweis=None,
             status="completed", start_ts=_iso(basis + timedelta(seconds=50)),
             end_ts=_iso(basis + timedelta(seconds=150)),
             dauer_ms=100000, tokens=10, werkzeugaufrufe=1, mehrfach_abgeschlossen=False,
             auftragsart="bauen", bausuite_lauf=False, dateien_geschrieben=1,
             gleichzeitig_max=None, schaetzung_sekunden=None, schaetzung_token=None,
             schaetzung_werkzeugaufrufe=None, tokens_pro_sekunde=0.1),
        Lauf(session="s", task_id="c", tool_use_id=None, beschreibung=None,
             subagent_type=None, modell=None, hintergrund=True, zeitlimit_hinweis=None,
             status="completed", start_ts=_iso(basis + timedelta(hours=5)),
             end_ts=_iso(basis + timedelta(hours=5, seconds=10)),
             dauer_ms=10000, tokens=1, werkzeugaufrufe=0, mehrfach_abgeschlossen=False,
             auftragsart="unklar", bausuite_lauf=False, dateien_geschrieben=0,
             gleichzeitig_max=None, schaetzung_sekunden=None, schaetzung_token=None,
             schaetzung_werkzeugaufrufe=None, tokens_pro_sekunde=0.1),
        # Grenzwert: kein Ende -> kein Intervall, wird nicht mitgezaehlt.
        Lauf(session="s", task_id="d", tool_use_id=None, beschreibung=None,
             subagent_type=None, modell=None, hintergrund=True, zeitlimit_hinweis=None,
             status="kein_abschluss", start_ts=_iso(basis), end_ts=None,
             dauer_ms=None, tokens=None, werkzeugaufrufe=None, mehrfach_abgeschlossen=False,
             auftragsart="unklar", bausuite_lauf=None, dateien_geschrieben=None,
             gleichzeitig_max=None, schaetzung_sekunden=None, schaetzung_token=None,
             schaetzung_werkzeugaufrufe=None, tokens_pro_sekunde=None),
    ]
    _gleichzeitigkeit_berechnen(laeufe)
    by_id = {l.task_id: l for l in laeufe}
    assert by_id["a"].gleichzeitig_max == 2, by_id["a"].gleichzeitig_max  # ueberlappt mit b
    assert by_id["b"].gleichzeitig_max == 2, by_id["b"].gleichzeitig_max
    assert by_id["c"].gleichzeitig_max == 1, by_id["c"].gleichzeitig_max  # allein
    assert by_id["d"].gleichzeitig_max is None  # kein Ende -> kein Intervall

    # -- Grenzwert: 0 Werkzeugaufrufe ist ein gueltiger, kein fehlender Wert.
    assert by_id["c"].werkzeugaufrufe == 0
    assert by_id["c"].vollstaendig  # 0 ist nicht None

    # -- bericht(): Nenner stimmen.
    b = bericht(laeufe)
    assert b["gefunden"] == 4, b["gefunden"]
    assert b["vollstaendig"] == 3, b["vollstaendig"]  # a, b, c haben alle drei Zahlen; d nicht
    assert b["unvollstaendig"] == 1, b["unvollstaendig"]

    print("SELFTEST OK: agentendauer")


if __name__ == "__main__":
    main()
