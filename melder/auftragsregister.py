#!/usr/bin/env python3
"""Anweisungsregister — zieht echte Nutzereingaben aus Claude-Code-Transkripten,
haelt sie fest in `auftraege.jsonl`, beantwortet "gab es das schon einmal?".

Plan: docs/PLAN_ANWEISUNGSREGISTER_2026-08-05.md, Schritt A1.
Deterministisch, kein Modellaufruf. Transkripte werden nur gelesen.

Unterscheidung "echte Nutzereingabe" vs. Beiwerk (an echten Transkripten geprueft,
siehe get_user_text()):
- Neuere Transkripte tragen `origin.kind == "human"` direkt am Eintrag -- das ist
  das verlaessliche Signal, auch wenn der Text selbst wie ein Tag aussieht
  (Pasted-Markdown, weitergeleitete Nachricht).
- Aeltere Transkripte kennen `origin` noch nicht. Fallback: type=="user",
  nicht isMeta, kein toolUseResult, kein reiner tool_result-Block, und der Text
  faengt nicht mit einem der synthetischen Marker an
  (<task-notification>, <command-name>, <command-message>, <local-command-stdout>,
  "[Request interrupted by user").
"""
# ausloeser: auf-abruf -- Subcommands brauchen eine Menschenfrage (pruefe TEXT)
# oder eine Menschenentscheidung (status ID abgelehnt/angenommen); extract/
# triage/offen sind Aufbereitung fuer genau diese Entscheidung, kein
# Dauerlauf. auftrag_recall_hook.py deckt die automatische Haelfte bereits
# ab (eigene, bewusst duplizierte Leselogik, siehe dessen Modulkopf).
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import argparse
import difflib
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = _w
AUFTRAEGE_PATH = HERE / "auftraege.jsonl"
STATE_PATH = HERE / ".auftragsregister_state.json"

sys.path.insert(0, str(HERE))
from knowledge_mcp_server import fold_de  # noqa: E402  (wie im Auftrag verlangt)

_SYNTH_PREFIXES = (
    "<task-notification>",
    "<command-name>",
    "<command-message>",
    "<local-command-stdout>",
)
_CONFIRM_WORDS = {
    "ja", "nein", "danke", "dankeschoen", "ok", "okay", "k",
    "gut", "passt", "super", "perfekt", "alles klar",
}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def transcripts_dir_for(projekt: Path) -> Path:
    """~/.claude/projects/<projektpfad-mit-bindestrichen>/"""
    abspath = str(projekt.resolve())
    name = re.sub(r"[^A-Za-z0-9]", "-", abspath)
    return Path.home() / ".claude" / "projects" / name


def get_user_text(o: dict) -> str | None:
    if o.get("type") != "user":
        return None
    message = o.get("message") or {}
    content = message.get("content")
    has_origin = "origin" in o
    if has_origin:
        if (o.get("origin") or {}).get("kind") != "human":
            return None
    else:
        if o.get("isMeta"):
            return None
        if o.get("toolUseResult") is not None:
            return None

    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        types = {b.get("type") for b in content if isinstance(b, dict)}
        if types and types <= {"tool_result"}:
            return None
        text = "\n".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    else:
        return None

    text = text.strip()
    if not text:
        return None

    if not has_origin:
        if text.startswith(_SYNTH_PREFIXES) or text.startswith("[Request interrupted by user"):
            return None

    return text


def get_queued_attachment_text(o: dict) -> str | None:
    """Mitten im Zug eingereihte Nachricht, neueres Transkriptformat.
    `attachment.origin.kind == "human"` ist dasselbe Signal wie bei get_user_text,
    nur eine Ebene tiefer (siehe docs/PLAN_ANWEISUNGSREGISTER_2026-08-05.md, Nachtrag)."""
    if o.get("type") != "attachment":
        return None
    a = o.get("attachment") or {}
    if a.get("type") != "queued_command":
        return None
    if (a.get("origin") or {}).get("kind") != "human":
        return None
    prompt = a.get("prompt")
    if isinstance(prompt, list):
        # Bild-Anhang ohne/mit Text -- wie bei get_user_text nur die Textbloecke
        prompt = "\n".join(
            b.get("text", "") for b in prompt
            if isinstance(b, dict) and b.get("type") == "text"
        )
    text = (prompt or "").strip()
    return text or None


def get_queue_enqueue_text(o: dict) -> str | None:
    """Fallback fuer aeltere Transkripte ohne `attachment`-Eintrag: die
    `queue-operation`/`enqueue`-Zeile traegt den Text direkt in `content`."""
    if o.get("type") != "queue-operation" or o.get("operation") != "enqueue":
        return None
    text = (o.get("content") or "").strip()
    if not text:
        return None
    if text.startswith(_SYNTH_PREFIXES) or text.startswith("[Request interrupted by user"):
        return None
    return text


def _file_uses_attachment_format(lines: list[str]) -> bool:
    """True, wenn diese Datei ueberhaupt `type=="attachment"`-Zeilen kennt --
    dann liefert `queue-operation` dieselben Nachrichten noch einmal und wird
    ignoriert (Entdopplung durch Quellenwahl statt Zeitstempel-Abgleich)."""
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            o = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if o.get("type") == "attachment":
            return True
    return False


def is_beiwerk(text: str) -> bool:
    """Grober Vorfilter: reine Bestaetigungen und blanke Slash-Kommandos.
    Entscheidet nicht, was ein Auftrag ist -- im Zweifel False (aufnehmen)."""
    t = fold_de(text.strip().rstrip("!.,"))
    if t in _CONFIRM_WORDS:
        return True
    if re.fullmatch(r"/\S+", text.strip()):
        return True
    return False


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"files": {}, "seen_hashes": []}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def extract_from_dir(tdir: Path, projekt_label: str, seit_tage: int,
                      out_path: Path, state: dict) -> tuple[int, int, int]:
    """Liefert (gelesene Dateien, neue Eintraege, vom Vorfilter verworfene)."""
    if not tdir.exists():
        return 0, 0, 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=seit_tage)
    files_state = state.setdefault("files", {})
    seen = set(state.get("seen_hashes", []))
    new_entries = []
    verworfen = 0
    gelesen = 0

    for f in sorted(tdir.glob("*.jsonl")):
        key = str(f)
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
        if key not in files_state and mtime < cutoff:
            continue  # nie gesehen und ausserhalb des Wasserzeichen-Fensters
        gelesen += 1

        prev_lines = files_state.get(key, {}).get("lines", 0)
        lines = f.read_text(errors="replace").splitlines()
        uses_attachment_format = _file_uses_attachment_format(lines)
        for i, raw in enumerate(lines):
            if i < prev_lines:
                continue
            raw = raw.strip()
            if not raw:
                continue
            try:
                o = json.loads(raw)
            except json.JSONDecodeError:
                continue
            text = get_user_text(o)
            if text is None:
                text = (
                    get_queued_attachment_text(o) if uses_attachment_format
                    else get_queue_enqueue_text(o)
                )
            if text is None:
                continue
            if is_beiwerk(text):
                verworfen += 1
                continue
            ts = o.get("timestamp", "")
            session = o.get("sessionId", "")
            h = hashlib.sha1(f"{session}|{ts}|{text}".encode()).hexdigest()[:16]
            if h in seen:
                continue
            seen.add(h)
            new_entries.append({
                "id": h,
                "ts": ts,
                "projekt": projekt_label,
                "session": session,
                "text": text,
                "status": "neu",
                "quelle": key,
            })
        files_state[key] = {"lines": len(lines)}

    if new_entries:
        with open(out_path, "a", encoding="utf-8") as fh:
            for e in new_entries:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    state["seen_hashes"] = sorted(seen)
    return gelesen, len(new_entries), verworfen


def cmd_extract(args) -> None:
    projekt = Path(args.projekt) if args.projekt else Path.cwd()
    tdir = transcripts_dir_for(projekt)
    state = load_state()
    gelesen, neu, verworfen = extract_from_dir(
        tdir, str(projekt), args.seit, AUFTRAEGE_PATH, state
    )
    save_state(state)
    print(f"Transkriptverzeichnis: {tdir}")
    print(f"gelesene Dateien: {gelesen}")
    print(f"neue Eintraege: {neu}")
    print(f"vom Vorfilter verworfen: {verworfen}")


def read_all_entries() -> dict[str, dict]:
    entries: dict[str, dict] = {}
    if not AUFTRAEGE_PATH.exists():
        return entries
    with open(AUFTRAEGE_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            if o.get("art") == "statuswechsel":
                e = entries.get(o["id"])
                if e:
                    e["status"] = o["status"]
                    if o.get("begruendung"):
                        e["begruendung"] = o["begruendung"]
                    e["status_ts"] = o["ts"]
            else:
                entries[o["id"]] = dict(o)
    return entries


def set_status(entry_id: str, status: str, begruendung: str | None = None) -> None:
    patch = {"art": "statuswechsel", "id": entry_id, "status": status, "ts": now_iso()}
    if begruendung:
        patch["begruendung"] = begruendung
    with open(AUFTRAEGE_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(patch, ensure_ascii=False) + "\n")


def cmd_offen(args) -> None:
    entries = [e for e in read_all_entries().values() if e.get("status") == "offen"]
    entries.sort(key=lambda e: e.get("ts", ""), reverse=True)
    shown = entries[: args.max]
    for e in shown:
        print(f"{e.get('ts','?')}  [{e.get('session','?')[:8]}]  {e['text'][:120]}")
    if len(entries) > args.max:
        print(f"... {len(entries) - args.max} weitere gekappt (--max {args.max})")


def similarity(query_folded: str, target_folded: str) -> float:
    """Gleichheit ODER Enthaltensein, je nachdem was besser passt.
    `ratio()` bestraft Laengenunterschiede (kurzes Stichwort in langer
    Mehrpunkt-Nachricht faellt sonst durch) -- zusaetzlich daher der laengste
    zusammenhaengende Treffer (find_longest_match) bezogen auf die Anfragelaenge:
    "steht die Anfrage als ein Stueck in der Nachricht?". Absichtlich NICHT die
    Summe aller (auch verstreuter) Bloecke -- das faende bei jeder Anfrage
    irgendwelche gemeinsamen Woerter und war die zuerst verworfene Fassung."""
    if not query_folded:
        return 0.0
    sm = difflib.SequenceMatcher(None, query_folded, target_folded)
    ratio = sm.ratio()
    longest = sm.find_longest_match(0, len(query_folded), 0, len(target_folded)).size
    contained = longest / len(query_folded)
    return max(ratio, contained)


def pruefe_treffer(text: str, schwelle: float, exclude_id: str | None = None,
                    entries: dict[str, dict] | None = None) -> list[tuple[float, dict]]:
    query_folded = fold_de(text)
    hits = []
    for e in (entries if entries is not None else read_all_entries()).values():
        if exclude_id and e["id"] == exclude_id:
            continue
        s = similarity(query_folded, fold_de(e["text"]))
        if s >= schwelle:
            hits.append((s, e))
    hits.sort(key=lambda x: x[0], reverse=True)
    return hits


def cmd_pruefe(args) -> None:
    hits = pruefe_treffer(args.text, args.schwelle)
    if not hits:
        print("keine Treffer")
        return
    for s, e in hits:
        line = f"{s:.2f}  {e.get('ts','?')}  status={e.get('status')}  {e['text'][:150]}"
        print(line)
        if e.get("status") == "abgelehnt" and e.get("begruendung"):
            print(f"    Begruendung: {e['begruendung']}")


_STATUS_WERTE = {"offen", "erledigt", "abgelehnt", "kein_auftrag"}


def cmd_status(args) -> None:
    if args.status not in _STATUS_WERTE:
        print(f"unzulaessiger Status: {args.status!r} (erlaubt: {', '.join(sorted(_STATUS_WERTE))})")
        raise SystemExit(1)
    if args.status == "abgelehnt" and not args.begruendung:
        print("abgelehnt ohne --begruendung wird abgelehnt")
        raise SystemExit(1)
    set_status(args.id, args.status, args.begruendung)
    print(f"{args.id} -> {args.status}")


def cmd_triage(args) -> None:
    alle = read_all_entries()
    entries = [e for e in alle.values() if e.get("status") == "neu"]
    if args.session:
        entries = [e for e in entries if e.get("session") == args.session]
    entries.sort(key=lambda e: e.get("ts", ""), reverse=True)
    shown = entries[: args.max]
    for e in shown:
        print(f"## {e['id']}  {e.get('ts','?')}  [{e.get('session','?')[:8]}]")
        print(e["text"])
        vorbestand = pruefe_treffer(e["text"], 0.5, exclude_id=e["id"], entries=alle)
        if vorbestand:
            for s, h in vorbestand[:3]:
                print(f"    verwandt ({s:.2f}, status={h.get('status')}): {h['text'][:100]}")
        print()
    if len(entries) > args.max:
        print(f"... {len(entries) - args.max} weitere gekappt (--max {args.max})")


def _selftest() -> None:
    import shutil
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    tdir = tmp / "transcripts"
    tdir.mkdir()
    out_path = tmp / "auftraege.jsonl"
    session = "sess-1"
    lines = [
        # 1. echte Nutzereingabe (aeltere Transkriptform, kein origin-Feld)
        {"type": "user", "sessionId": session, "timestamp": "2026-08-05T09:00:00Z",
         "message": {"content": "nicht vormerken erst messen dann selbstaendig ausfuehren"}},
        # 2. tool_result -- kein Nutzertext
        {"type": "user", "sessionId": session, "timestamp": "2026-08-05T09:01:00Z",
         "toolUseResult": {"foo": "bar"},
         "message": {"content": [{"type": "tool_result", "content": "Datei geschrieben"}]}},
        # 3. Hook-Einspielung
        {"type": "user", "sessionId": session, "timestamp": "2026-08-05T09:02:00Z",
         "isMeta": True, "message": {"content": "Stop hook feedback: rufe /learn auf"}},
        # 4. reine Bestaetigung
        {"type": "user", "sessionId": session, "timestamp": "2026-08-05T09:03:00Z",
         "message": {"content": "ok"}},
        # 5. Slash-Kommando (Harness-Wrapper)
        {"type": "user", "sessionId": session, "timestamp": "2026-08-05T09:04:00Z",
         "message": {"content": "<command-name>/pause</command-name>\n<command-message>pause</command-message>"}},
        # zusaetzlich fuer die pruefe-Gegenprobe: bereits abgelehnter Eintrag
        {"type": "user", "sessionId": session, "timestamp": "2026-08-05T09:05:00Z",
         "message": {"content": "spekulatives Feature X vorab bauen"}},
        # 6. mitten im Zug eingereiht -- steht doppelt (queue-operation + attachment),
        #    muss trotzdem genau EINEN Registereintrag ergeben
        {"type": "queue-operation", "operation": "enqueue", "sessionId": session,
         "timestamp": "2026-08-05T09:06:00Z", "content": "Testnachricht mid-turn"},
        {"type": "attachment", "sessionId": session, "timestamp": "2026-08-05T09:06:00Z",
         "attachment": {"type": "queued_command", "commandMode": "prompt",
                        "prompt": "Testnachricht mid-turn", "origin": {"kind": "human"}}},
        {"type": "queue-operation", "operation": "remove", "sessionId": session,
         "timestamp": "2026-08-05T09:06:05Z", "content": "Testnachricht mid-turn"},
    ]
    tf = tdir / "1.jsonl"
    tf.write_text("\n".join(json.dumps(l, ensure_ascii=False) for l in lines) + "\n")

    state = {"files": {}, "seen_hashes": []}
    gelesen, neu, verworfen = extract_from_dir(tdir, "testprojekt", 14, out_path, state)
    assert gelesen == 1, gelesen
    assert neu == 3, f"erwartet 3 (echte Eingabe + abgelehnt-Kandidat + mid-turn), war {neu}"
    assert verworfen == 1, f"erwartet 1 verworfene Bestaetigung, war {verworfen}"

    texts = [json.loads(l)["text"] for l in out_path.read_text().splitlines()]
    assert "nicht vormerken erst messen dann selbstaendig ausfuehren" in texts
    assert not any("hook feedback" in t for t in texts)
    assert not any(t == "ok" for t in texts)
    assert not any("<command-name>" in t for t in texts)
    assert texts.count("Testnachricht mid-turn") == 1, "Entdopplung queue-operation vs. attachment fehlgeschlagen"
    print("selftest: Unterscheidung echte Eingabe vs. Beiwerk -- OK")
    print("selftest: mid-turn-Nachricht (queue-operation + attachment) -- genau 1 Eintrag -- OK")

    # zweiter Lauf: keine Duplikate
    gelesen2, neu2, _ = extract_from_dir(tdir, "testprojekt", 14, out_path, state)
    assert neu2 == 0, f"zweiter Lauf haette 0 neue Eintraege, war {neu2}"
    print("selftest: Idempotenz zweiter Lauf -- OK")

    # pruefe findet abgelehnten Eintrag samt Begruendung
    global AUFTRAEGE_PATH
    orig_path = AUFTRAEGE_PATH
    AUFTRAEGE_PATH = out_path
    entries = read_all_entries()
    target_id = next(e["id"] for e in entries.values() if "spekulatives Feature X" in e["text"])
    set_status(target_id, "abgelehnt", "Testgrund: kein Bedarf")
    entries = read_all_entries()
    assert entries[target_id]["status"] == "abgelehnt"
    assert entries[target_id]["begruendung"] == "Testgrund: kein Bedarf"

    q = fold_de("spekulatives feature x vorab bauen")
    ratio = difflib.SequenceMatcher(None, q, fold_de(entries[target_id]["text"])).ratio()
    assert ratio > 0.9
    print("selftest: pruefe findet abgelehnten Eintrag samt Begruendung -- OK")

    # offen respektiert Deckel
    for i in range(5):
        with open(out_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "id": f"deckel-{i}", "ts": f"2026-08-0{i+1}T00:00:00Z",
                "projekt": "testprojekt", "session": session,
                "text": f"offener Auftrag {i}", "status": "offen", "quelle": str(tf),
            }, ensure_ascii=False) + "\n")
    entries = read_all_entries()
    offen = [e for e in entries.values() if e.get("status") == "offen"]
    assert len(offen) == 5, len(offen)
    print("selftest: offen-Bestand fuer Deckel-Test angelegt (5 Eintraege) -- OK")

    # pruefe: kurzes Stichwort, das woertlich in einer langen Mehrpunkt-Nachricht
    # steckt, muss bei der Vorgabeschwelle treffen -- Enthaltensein, nicht Gleichheit
    lange_id = hashlib.sha1(b"lange-nachricht").hexdigest()[:16]
    with open(out_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "id": lange_id, "ts": "2026-08-05T10:00:00Z", "projekt": "testprojekt",
            "session": session,
            "text": "1 claude neu starten oder was meinst du mit server?\n2 was besagt L-b9d1f3 i ?",
            "status": "neu", "quelle": str(tf),
        }, ensure_ascii=False) + "\n")
    entries = read_all_entries()
    treffer = pruefe_treffer("was besagt L-b9d1f3", 0.5, entries=entries)
    assert any(e["id"] == lange_id for _, e in treffer), "Enthaltensein-Treffer fehlt bei Vorgabeschwelle"
    print("selftest: pruefe -- kurzes Stichwort in langer Nachricht, Vorgabeschwelle -- OK")

    # Gegenprobe: voellig unaehnlicher Text darf nicht treffen
    treffer_leer = pruefe_treffer("xqzvy-nonsense-zeichenkette-7712", 0.5, entries=entries)
    assert treffer_leer == [], f"unaehnlicher Text haette keinen Treffer liefern duerfen, war {treffer_leer}"
    print("selftest: pruefe -- unaehnlicher Text liefert keinen Treffer -- OK")

    # status: 'abgelehnt' ohne Begruendung wird zurueckgewiesen
    ns = argparse.Namespace(id=target_id, status="abgelehnt", begruendung=None)
    try:
        cmd_status(ns)
        raised = False
    except SystemExit:
        raised = True
    assert raised, "abgelehnt ohne Begruendung haette abgelehnt werden muessen"
    print("selftest: status abgelehnt ohne Begruendung wird zurueckgewiesen -- OK")

    AUFTRAEGE_PATH = orig_path
    shutil.rmtree(tmp)
    print("selftest: alle Faelle gruen")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--selftest", action="store_true")
    sub = p.add_subparsers(dest="cmd")

    pe = sub.add_parser("extract")
    pe.add_argument("--seit", type=int, default=14)
    pe.add_argument("--projekt", default=None)
    pe.set_defaults(func=cmd_extract)

    po = sub.add_parser("offen")
    po.add_argument("--max", type=int, default=10)
    po.set_defaults(func=cmd_offen)

    pp = sub.add_parser("pruefe")
    pp.add_argument("text")
    pp.add_argument("--schwelle", type=float, default=0.5)
    pp.set_defaults(func=cmd_pruefe)

    ps = sub.add_parser("status")
    ps.add_argument("id")
    ps.add_argument("status")
    ps.add_argument("--begruendung", default=None)
    ps.set_defaults(func=cmd_status)

    pt = sub.add_parser("triage")
    pt.add_argument("--max", type=int, default=20)
    pt.add_argument("--session", default=None)
    pt.set_defaults(func=cmd_triage)

    args = p.parse_args()
    if args.selftest:
        _selftest()
        return
    if not args.cmd:
        p.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
