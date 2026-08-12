#!/usr/bin/env python3
"""MESSAUFTRAG (Betreiber, 2026-08-13), zweite Frage: Wiederholt eine
Assistant-Antwort bereits Text aus den Treffern, die IHR vorausgingen? Wenn
ja, fuettert der Abruf sich selbst -- fuer eine spaetere Antwort-Vektor-Suche
toedlich (sie wuerde nur denselben Fund wiederfinden).

VORBILD: messungen/kontamination.py prueft dieselbe Grundfrage (steht ein
TRAEGER aus zugetragenem Kontext in der spaeteren Aeusserung?) fuer
Subagenten-Protokolle. Hier: recall_log.jsonl (was der Haken eingespielt hat)
gegen das eigene Sitzungsprotokoll (was danach geantwortet wurde).

QUELLE, GRENZE DER MESSUNG: recall_log.jsonl protokolliert Einspielungen aus
VIELEN Sitzungen/Worktrees (cwd-Feld). Nur Zeilen mit cwd der AKTUELLEN
Sitzung (hallo-01e380) werden gezaehlt -- fuer andere Worktrees liegt das
Transcript hier nicht vor, ein Treffer waere nicht nachpruefbar. Das ist eine
bewusste Einschraenkung, kein Uebersehen (siehe ABNAHME im Skriptaufruf).

KRITERIUM (bewusst zweistufig, spiegelt haken/antwort_abruf.py
BEGRIFFLICH_MIN=2 -- dieselbe Abwaegung: ein einzelnes haeufiges Wort waere
ein Fehlalarm):
  WOERTLICH   -- die Kennung (Pfad bzw. L-Id) selbst steht im Antworttext.
  BEGRIFFLICH -- mindestens 2 der markanten Woerter (>=6 Zeichen) aus
                 Titel+Zusammenfassung (Node) bzw. Beschreibung (Lehre)
                 kommen in der Antwort vor.
  KEINS       -- weder noch.

Aufruf:
    python3 messungen/rueckkopplung_antwort.py --out runs/<name>.json
    python3 messungen/rueckkopplung_antwort.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w), str(_w / "kern")]

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pruefkorpus  # kern/pruefkorpus.py -- tokenize() wiederverwendet

WURZEL = _w
RECALL_LOG = WURZEL / "recall_log.jsonl"
TRANSCRIPT = Path(
    "/Users/lehrmacbook/.claude/projects/"
    "-Volumes-daten-Begod2026-brainlehr--claude-worktrees-hallo-01e380/"
    "d695fd29-c21d-485a-b4d0-f73757047a9d.jsonl")
WORKTREE_MARKER = "hallo-01e380"
BEGRIFFLICH_MIN = 2  # gleiche Zahl, gleiche Begruendung wie antwort_abruf.py
FENSTER = timedelta(minutes=30)  # Antwort muss innerhalb dieses Fensters
# nach der Einspielung liegen -- sonst ist ein spaeterer Treffer zufaellig,
# nicht kausal aus dieser Einspielung erklaerbar.


def _parse_ts(s: str) -> datetime | None:
    try:
        s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except (ValueError, AttributeError):
        return None


def lade_recall_zeilen(pfad=RECALL_LOG, marker=WORKTREE_MARKER) -> list[dict]:
    zeilen = []
    with open(pfad, encoding="utf-8", errors="replace") as f:
        for zeile in f:
            try:
                d = json.loads(zeile)
            except json.JSONDecodeError:
                continue
            if marker not in (d.get("cwd") or ""):
                continue
            if not (d.get("nodes") or d.get("lessons")):
                continue
            zeilen.append(d)
    return zeilen


def lade_assistant_texte(transcript=TRANSCRIPT) -> list[tuple[datetime, str]]:
    """Je Assistant-Nachricht mit Textinhalt: (Zeitstempel, Text). Robust
    gegen kaputte Zeilen wie letzte_antwort() in antwort_abruf.py."""
    out = []
    with open(transcript, encoding="utf-8", errors="replace") as f:
        for zeile in f:
            try:
                d = json.loads(zeile)
            except json.JSONDecodeError:
                continue
            if d.get("type") != "assistant":
                continue
            ts = _parse_ts(d.get("timestamp") or "")
            if ts is None:
                continue
            inhalt = (d.get("message") or {}).get("content") or []
            stuecke = [c.get("text", "") for c in inhalt
                       if isinstance(c, dict) and c.get("type") == "text"]
            text = "\n".join(t for t in stuecke if t)
            if text:
                out.append((ts, text))
    out.sort(key=lambda x: x[0])
    return out


def naechste_antwort(ts: datetime, antworten: list[tuple[datetime, str]],
                      fenster: timedelta = FENSTER) -> str | None:
    """Erste Antwort NACH ts, innerhalb fenster. None wenn keine im Fenster."""
    for a_ts, text in antworten:
        if a_ts > ts:
            return text if (a_ts - ts) <= fenster else None
    return None


def lade_bestand_lookup(db_path: str = None) -> tuple[dict, dict]:
    nodes, lessons = pruefkorpus.load_bestand(db_path) if db_path else pruefkorpus.load_bestand()
    nach_pfad = {n["path"]: n for n in nodes}
    nach_id = {l["id"]: l for l in lessons}
    return nach_pfad, nach_id


def markante_begriffe(text: str, min_laenge: int = 6) -> set[str]:
    return {w for w in pruefkorpus.tokenize(text) if len(w) >= min_laenge}


def pruefe_eintrag(kennung: str, inhalt_text: str, antwort: str) -> str:
    """WOERTLICH / BEGRIFFLICH / KEINS."""
    if kennung and kennung in antwort:
        return "woertlich"
    begriffe = markante_begriffe(inhalt_text)
    antwort_begriffe = pruefkorpus.tokenize(antwort)
    if len(begriffe & antwort_begriffe) >= BEGRIFFLICH_MIN:
        return "begrifflich"
    return "keins"


def messen() -> dict:
    zeilen = lade_recall_zeilen()
    antworten = lade_assistant_texte()
    nach_pfad, nach_id = lade_bestand_lookup()

    befunde = []
    ohne_folgeantwort = 0
    ohne_inhalt = 0
    geprueft = 0
    kontaminiert = 0

    for z in zeilen:
        ts = _parse_ts(z.get("ts") or "")
        if ts is None:
            continue
        antwort = naechste_antwort(ts, antworten)
        if antwort is None:
            ohne_folgeantwort += len(z.get("nodes") or []) + len(z.get("lessons") or [])
            continue
        for pfad in (z.get("nodes") or []):
            n = nach_pfad.get(pfad)
            if n is None:
                ohne_inhalt += 1
                continue
            geprueft += 1
            urteil = pruefe_eintrag(pfad, pruefkorpus.node_text(n), antwort)
            if urteil != "keins":
                kontaminiert += 1
            befunde.append({"ts": z["ts"], "kind": "node", "kennung": pfad, "urteil": urteil})
        for lid in (z.get("lessons") or []):
            l = nach_id.get(lid)
            if l is None:
                ohne_inhalt += 1
                continue
            geprueft += 1
            urteil = pruefe_eintrag(lid, pruefkorpus.lesson_text(l), antwort)
            if urteil != "keins":
                kontaminiert += 1
            befunde.append({"ts": z["ts"], "kind": "lesson", "kennung": lid, "urteil": urteil})

    return {
        "worktree_marker": WORKTREE_MARKER,
        "recall_zeilen_im_scope": len(zeilen),
        "assistant_nachrichten_im_transcript": len(antworten),
        "geprueft": geprueft,
        "kontaminiert": kontaminiert,
        "quote": f"{kontaminiert}/{geprueft}" if geprueft else "0/0",
        "ohne_folgeantwort_im_fenster": ohne_folgeantwort,
        "ohne_bestandsinhalt_mehr_vorhanden": ohne_inhalt,
        "befunde": befunde,
        "befund_text": (
            f"{kontaminiert} von {geprueft} eingespielten Eintraegen (Nodes+Lehren) "
            f"kamen in der jeweils naechsten Antwort woertlich oder begrifflich vor -- "
            f"{ohne_folgeantwort} Eintraege hatten keine Folgeantwort im {FENSTER}-Fenster "
            f"und wurden nicht gezaehlt."
        ),
    }


def _selftest() -> None:
    assert pruefe_eintrag("/pfad/x", "Vorhersehbare Titelzeile Zusammenfassung",
                           "Ich nutze die Vorhersehbare Zusammenfassung hier.") == "begrifflich"
    assert pruefe_eintrag("/pfad/x", "kurz", "kein Ueberlapp hier drin") == "keins"
    assert pruefe_eintrag("L-abc123", "irrelevanter Inhalt ganz woanders",
                           "siehe L-abc123 fuer Details") == "woertlich"
    # Negativfall: nur EIN markanter Begriff -> kein Fehlalarm (BEGRIFFLICH_MIN=2)
    assert pruefe_eintrag("/pfad/y", "Einzelbegriff Zusammenfassung",
                           "Nur Einzelbegriff kommt hier vor, sonst nichts Passendes.") == "keins"
    print("selftest ok (3 Faelle + Negativfall)", file=_sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        _selftest()
        return
    ergebnis = messen()
    print(ergebnis["befund_text"])
    if a.out:
        a.out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        print(f"Geschrieben: {a.out}")


if __name__ == "__main__":
    main()
