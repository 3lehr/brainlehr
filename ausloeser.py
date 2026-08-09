#!/usr/bin/env python3
"""ausloeser.py — misst den AUSLOESER des Auto-Recalls, nicht die Suche.

Die Trefferquote des Abrufs (16/35, gemessen 2026-08-09) sagt nichts darueber,
wie oft der Haken ueberhaupt gefragt wird. Eine Suche, die nicht gefragt wird,
hat keine Trefferquote.

Zaehler und Nenner:

  Nenner — jede Eingabe, die den UserPromptSubmit-Haltepunkt erreicht hat.
           Quelle sind die Sitzungsprotokolle des Klienten unter
           ~/.claude/projects/**/*.jsonl: Zeilen mit type=user UND
           promptSource. Ihr Feld origin.kind trennt die Herkunft
           ('human' gegen 'task-notification' u.a.) -- genau die
           Unterscheidung, um die es im Feldbericht (Knoten 1d2e6458) geht.

  Zaehler — jede Zeile in recall_log.jsonl. Leere Abrufe stehen dort seit
            2026-08-09 ebenfalls drin (leere Listen), sind also von
            "gar kein Abruf" unterscheidbar.

Fuer jede Eingabe OHNE Protokollzeile wird der Grund nachgespielt, statt ihn
zu vermuten: dieselben Sperren, die main() der Reihe nach zieht.

  kein_prompt   leerer Text
  schraegstrich Text beginnt mit '/' (Klientenbefehl)
  min_hits      keywords(text) < MIN_HITS -- der Haken fragt die DB gar nicht
  unerklaert    keine der Sperren greift und trotzdem keine Zeile

Ausgabe: runs/ausloeser_<datum>.json, mit Rastervermerk (welche Dateien,
welches Fenster, welcher Bestand) -- ein Ergebnis ohne Raster ist nicht
wiederholbar, sondern nur wiederholbar von vorn.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "haken"))
from knowledge_recall_hook import MIN_HITS, keywords  # noqa: E402

PROJEKTE = Path.home() / ".claude" / "projects"
RECALL_LOG = Path(os.environ.get("BEGOD_RECALL_LOG", REPO / "recall_log.jsonl"))
# Zuordnung ueber die Zeit ist die Rueckfalloption, wenn der Text fehlt
# (Zeilen vor dem 2026-08-09 tragen kein prompt-Feld). Der Haken schreibt
# seine Zeile Sekundenbruchteile nach der Eingabe; 15 s sind grosszuegig
# und immer noch enger als der Abstand zweier Eingaben.
ZEITFENSTER_S = 15


def _zeit(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def eingaben(ab: datetime, bis: datetime) -> tuple[list[dict], list[str]]:
    """Alle Eingaben im Fenster, plus die Liste der abgesuchten Dateien."""
    treffer, dateien = [], []
    for pfad in sorted(PROJEKTE.glob("*/*.jsonl")):
        dateien.append(str(pfad.relative_to(PROJEKTE)))
        with pfad.open(encoding="utf-8", errors="replace") as fh:
            for zeile in fh:
                if '"promptSource"' not in zeile:
                    continue
                try:
                    r = json.loads(zeile)
                except Exception:
                    continue
                if r.get("type") != "user" or not r.get("promptSource"):
                    continue
                ts = r.get("timestamp")
                if not ts:
                    continue
                t = _zeit(ts)
                if not (ab <= t <= bis):
                    continue
                inhalt = r.get("message", {}).get("content")
                if not isinstance(inhalt, str):
                    continue  # Werkzeugergebnisse, keine Eingabe
                herkunft = r.get("origin") or {}
                treffer.append({
                    "ts": t,
                    "session": (r.get("sessionId") or "")[:8],
                    "kind": herkunft.get("kind") or "unbekannt",
                    "text": inhalt.strip(),
                    "cwd": r.get("cwd") or "",
                    "datei": str(pfad.relative_to(PROJEKTE)),
                })
    treffer.sort(key=lambda e: e["ts"])
    return treffer, dateien


def grund(text: str) -> str:
    """Die Sperren aus main(), in derselben Reihenfolge."""
    if not text:
        return "kein_prompt"
    if text.startswith("/"):
        return "schraegstrich"
    if len(keywords(text)) < MIN_HITS:
        return "min_hits"
    return "unerklaert"


def main() -> None:
    protokoll = [json.loads(z) for z in RECALL_LOG.read_text(encoding="utf-8").splitlines() if z.strip()]
    if not protokoll:
        print("recall_log.jsonl leer -- nichts zu messen", file=sys.stderr)
        raise SystemExit(1)
    ab = _zeit(protokoll[0]["ts"])
    bis = _zeit(protokoll[-1]["ts"]) + timedelta(seconds=ZEITFENSTER_S)

    nach_text: dict[tuple[str, str], list[dict]] = defaultdict(list)
    nach_sitzung: dict[str, list[dict]] = defaultdict(list)
    for p in protokoll:
        p["_t"] = _zeit(p["ts"])
        nach_sitzung[p["session"]].append(p)
        if p.get("prompt"):
            nach_text[(p["session"], p["prompt"].strip())].append(p)

    evs, dateien = eingaben(ab, bis)
    verbraucht: set[int] = set()
    for e in evs:
        zeile = None
        kandidaten = nach_text.get((e["session"], e["text"]))
        if kandidaten:
            for k in kandidaten:
                if id(k) not in verbraucht:
                    zeile = k
                    break
        if zeile is None:  # Rueckfall ueber die Zeit
            for k in nach_sitzung.get(e["session"], []):
                if id(k) in verbraucht or k.get("prompt"):
                    continue
                d = (k["_t"] - e["ts"]).total_seconds()
                if 0 <= d <= ZEITFENSTER_S:
                    zeile = k
                    break
        if zeile is not None:
            verbraucht.add(id(zeile))
            e["gefeuert"] = True
            e["leer"] = not zeile["nodes"] and not zeile["lessons"]
            e["grund"] = "leer" if e["leer"] else "eingespielt"
        else:
            e["gefeuert"] = False
            e["leer"] = None
            e["grund"] = grund(e["text"])

    je_kind: dict[str, Counter] = defaultdict(Counter)
    for e in evs:
        je_kind[e["kind"]][e["grund"]] += 1

    beispiele = defaultdict(list)
    for e in evs:
        if len(beispiele[e["grund"]]) < 5:
            beispiele[e["grund"]].append({
                "ts": e["ts"].isoformat(),
                "kind": e["kind"],
                "stichworte": len(keywords(e["text"])),
                "zeichen": len(e["text"]),
                "text": e["text"][:160],
            })

    ergebnis = {
        "raster": {
            "erzeugt": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "fenster_von": ab.isoformat(),
            "fenster_bis": bis.isoformat(),
            "abgesuchte_dateien": dateien,
            "dateien_gesamt": len(dateien),
            "protokollzeilen": len(protokoll),
            "min_hits": MIN_HITS,
            "zeitfenster_s": ZEITFENSTER_S,
            "nicht_abgesucht": "Eingaben ausserhalb ~/.claude/projects (andere Klienten) "
                               "und Sitzungen, deren Protokoll geloescht wurde",
        },
        "eingaben_gesamt": len(evs),
        "gefeuert": sum(1 for e in evs if e["gefeuert"]),
        "still": sum(1 for e in evs if not e["gefeuert"]),
        "protokollzeilen_ohne_eingabe": len(protokoll) - len(verbraucht),
        "je_herkunft": {k: dict(v) for k, v in sorted(je_kind.items())},
        "je_grund": dict(Counter(e["grund"] for e in evs)),
        "beispiele": dict(beispiele),
    }

    ziel = REPO / "runs" / f"ausloeser_{datetime.now().strftime('%Y-%m-%d')}.json"
    ziel.parent.mkdir(exist_ok=True)
    ziel.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Fenster {ab.isoformat()} .. {bis.isoformat()}")
    print(f"Eingaben {len(evs)} · gefeuert {ergebnis['gefeuert']} · still {ergebnis['still']}")
    print(f"Protokollzeilen ohne zugeordnete Eingabe: {ergebnis['protokollzeilen_ohne_eingabe']}/{len(protokoll)}")
    for kind, c in sorted(je_kind.items()):
        ges = sum(c.values())
        print(f"  {kind:20s} {ges:4d}  " + " ".join(f"{k}={v}" for k, v in c.most_common()))
    print(f"-> {ziel}")


def selftest() -> None:
    """Negativfall zuerst: eine Eingabe, die die Sperre reisst, darf NICHT
    als 'min_hits' erklaert werden -- sonst erklaert die Klassifikation alles."""
    assert grund("") == "kein_prompt"
    assert grund("/pause") == "schraegstrich"
    assert grund("ja") == "min_hits", grund("ja")
    lang = "Der Abruf trifft die Rangfolge der Kandidatenliste im Bedeutungskanal nicht"
    assert len(keywords(lang)) >= MIN_HITS
    assert grund(lang) == "unerklaert", grund(lang)
    # Grenzwert: genau MIN_HITS Stichworte reissen die Sperre nicht mehr.
    knapp = None
    for n in range(1, 40):
        probe = " ".join(f"Bedeutungskanal{i} Rangfolge{i}"[: 8 + i] for i in range(n))
        if len(keywords(probe)) == MIN_HITS:
            knapp = probe
            break
    assert knapp is not None, "kein Text mit genau MIN_HITS Stichworten gefunden"
    assert grund(knapp) == "unerklaert"
    unter = " ".join(knapp.split()[:-1])
    assert len(keywords(unter)) < MIN_HITS
    assert grund(unter) == "min_hits"
    print(f"selftest ok (MIN_HITS={MIN_HITS})")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        main()
