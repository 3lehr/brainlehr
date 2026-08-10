#!/usr/bin/env python3
"""ausloeser.py — misst den AUSLOESER des Auto-Recalls, nicht die Suche.

Fassung 2: der Nenner "type=user + promptSource" war nachweislich zu klein.
Gemessen im Fenster ab 2026-08-09T07:52:53+00:00 stehen 94 menschliche
Nachrichten in der Warteschlange (queue-operation, enqueue), aber nur 66
davon haben je eine promptSource-Zeile -- 28 erreichen den
UserPromptSubmit-Haltepunkt nie (Grund unbekannt: Warteschlange verworfen,
Sitzung anders beendet o.ae.) und fielen im alten Nenner unter den Tisch.

Zaehler und Nenner jetzt:

  Nenner  — jede queue-operation/enqueue-Zeile im Fenster, deren content
            NICHT mit '<' beginnt (das sind Agentenmeldungen, z.B.
            "<task-notification>...").
  Stufe 1 — erreichte die Nachricht den Haltepunkt? Abgleich ueber
            sessionId-Praefix + gestripptem Text gegen die
            type=user/promptSource-Zeilen. Kein Treffer -> "nie_am_haltepunkt".
  Stufe 2 — nur fuer das, was den Haltepunkt erreicht hat: Abgleich gegen
            recall_log.jsonl (Text zuerst, Zeit als Rueckfall, bestehende
            Logik unveraendert).

Fuer alles, was den Haltepunkt erreicht hat, aber keine recall_log-Zeile
hat, wird der Grund nachgespielt, statt ihn zu vermuten: dieselben Sperren,
die main() der Reihe nach zieht.

  kein_prompt       leerer Text
  schraegstrich     Text beginnt mit '/' (Klientenbefehl)
  min_hits          keywords(text) < MIN_HITS -- der Haken fragt die DB gar nicht
  unerklaert        keine der Sperren greift und trotzdem keine Zeile
  nie_am_haltepunkt Haltepunkt selbst nie erreicht (Stufe 1 negativ)

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
# Commit e3ef28f -- davor ist 'leerer Abruf' von 'gar kein Abruf' nicht unterscheidbar (L-cb3f28)
LEERPROTOKOLL_AB = "2026-08-09T07:52:53+00:00"


def _zeit(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def scan(ab: datetime, bis: datetime) -> tuple[list[dict], list[dict], list[str]]:
    """Ein Durchlauf durch alle Transkripte: promptSource-Zeilen (Haltepunkt
    erreicht) und queue-operation/enqueue-Zeilen (Warteschlange), beide im
    Fenster [ab, bis]. 'remove'-Zeilen werden nicht ausgewertet."""
    promptsource, enqueue, dateien = [], [], []
    for pfad in sorted(PROJEKTE.glob("*/*.jsonl")):
        dateien.append(str(pfad.relative_to(PROJEKTE)))
        with pfad.open(encoding="utf-8", errors="replace") as fh:
            for zeile in fh:
                if '"promptSource"' in zeile:
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
                    promptsource.append({
                        "ts": t,
                        "session": (r.get("sessionId") or "")[:8],
                        "kind": herkunft.get("kind") or "unbekannt",
                        "text": inhalt.strip(),
                        "datei": str(pfad.relative_to(PROJEKTE)),
                    })
                    continue
                if '"queue-operation"' in zeile and '"enqueue"' in zeile:
                    try:
                        r = json.loads(zeile)
                    except Exception:
                        continue
                    if r.get("type") != "queue-operation" or r.get("operation") != "enqueue":
                        continue
                    ts = r.get("timestamp")
                    if not ts:
                        continue
                    t = _zeit(ts)
                    if not (ab <= t <= bis):
                        continue
                    text = (r.get("content") or "").strip()
                    enqueue.append({
                        "ts": t,
                        "session": (r.get("sessionId") or "")[:8],
                        "text": text,
                        "kind": "maschine" if text.startswith("<") else "mensch",
                        "datei": str(pfad.relative_to(PROJEKTE)),
                    })
    promptsource.sort(key=lambda e: e["ts"])
    enqueue.sort(key=lambda e: e["ts"])
    return promptsource, enqueue, dateien


def stufe1_haltepunkt(enqueue_evs: list[dict], promptsource_evs: list[dict]) -> list[dict]:
    """Stufe 1: erreichte die enqueue-Nachricht den UserPromptSubmit-
    Haltepunkt? Abgleich ueber (session-Praefix, gestrippter Text)."""
    index: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for p in promptsource_evs:
        index[(p["session"], p["text"])].append(p)
    verbraucht: set[int] = set()
    ergebnis = []
    for e in enqueue_evs:
        treffer = None
        for k in index.get((e["session"], e["text"]), []):
            if id(k) not in verbraucht:
                treffer = k
                break
        if treffer is not None:
            verbraucht.add(id(treffer))
        neu = dict(e)
        neu["erreicht"] = treffer is not None
        neu["_ps"] = treffer
        ergebnis.append(neu)
    return ergebnis


def grund(text: str) -> str:
    """Die Sperren aus main(), in derselben Reihenfolge -- nur fuer
    Nachrichten, die den Haltepunkt bereits erreicht haben."""
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
    ab = max(_zeit(protokoll[0]["ts"]), _zeit(LEERPROTOKOLL_AB))
    bis = _zeit(protokoll[-1]["ts"]) + timedelta(seconds=ZEITFENSTER_S)

    nach_text: dict[tuple[str, str], list[dict]] = defaultdict(list)
    nach_sitzung: dict[str, list[dict]] = defaultdict(list)
    for p in protokoll:
        p["_t"] = _zeit(p["ts"])
        nach_sitzung[p["session"]].append(p)
        if p.get("prompt"):
            nach_text[(p["session"], p["prompt"].strip())].append(p)

    promptsource_evs, enqueue_evs, dateien = scan(ab, bis)
    maschinen_anzahl = sum(1 for e in enqueue_evs if e["kind"] == "maschine")
    menschen = stufe1_haltepunkt(
        [e for e in enqueue_evs if e["kind"] == "mensch"], promptsource_evs
    )

    verbraucht_recall: set[int] = set()
    for e in menschen:
        if not e["erreicht"]:
            e["gefeuert"] = False
            e["leer"] = None
            e["grund"] = "nie_am_haltepunkt"
            continue
        ps = e["_ps"]
        zeile = None
        for k in nach_text.get((ps["session"], ps["text"]), []):
            if id(k) not in verbraucht_recall:
                zeile = k
                break
        if zeile is None:  # Rueckfall ueber die Zeit
            for k in nach_sitzung.get(ps["session"], []):
                if id(k) in verbraucht_recall or k.get("prompt"):
                    continue
                d = (k["_t"] - ps["ts"]).total_seconds()
                if 0 <= d <= ZEITFENSTER_S:
                    zeile = k
                    break
        if zeile is not None:
            verbraucht_recall.add(id(zeile))
            e["gefeuert"] = True
            e["leer"] = not zeile["nodes"] and not zeile["lessons"]
            e["grund"] = "leer" if e["leer"] else "eingespielt"
        else:
            e["gefeuert"] = False
            e["leer"] = None
            e["grund"] = grund(ps["text"])

    beispiele = defaultdict(list)
    for e in menschen:
        if len(beispiele[e["grund"]]) < 5:
            beispiele[e["grund"]].append({
                "ts": e["ts"].isoformat(),
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
            "leerprotokoll_ab": LEERPROTOKOLL_AB,
            "enqueue_zeilen": len(enqueue_evs),
            "maschinenmeldungen": maschinen_anzahl,
            "remove_hinweis": "'remove'-Zeilen (Dequeue) werden nicht ausgewertet.",
            "nicht_abgesucht": "Eingaben ausserhalb ~/.claude/projects (andere Klienten) "
                               "und Sitzungen, deren Protokoll geloescht wurde",
        },
        "eingaben_gesamt": len(menschen),
        "am_haltepunkt": sum(1 for e in menschen if e["erreicht"]),
        "nie_am_haltepunkt": sum(1 for e in menschen if not e["erreicht"]),
        "gefeuert": sum(1 for e in menschen if e["gefeuert"]),
        "still": sum(1 for e in menschen if e["erreicht"] and not e["gefeuert"]),
        "protokollzeilen_ohne_eingabe": len(protokoll) - len(verbraucht_recall),
        "je_grund": dict(Counter(e["grund"] for e in menschen)),
        "beispiele": dict(beispiele),
    }

    ziel = REPO / "runs" / f"ausloeser_{datetime.now().strftime('%Y-%m-%d')}.json"
    ziel.parent.mkdir(exist_ok=True)
    ziel.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Fenster {ab.isoformat()} .. {bis.isoformat()}")
    print(f"enqueue-Zeilen {len(enqueue_evs)} (davon Maschinenmeldungen {maschinen_anzahl})")
    print(f"Menschliche Nachrichten {len(menschen)}")
    print(f"  am Haltepunkt {ergebnis['am_haltepunkt']} · nie_am_haltepunkt {ergebnis['nie_am_haltepunkt']}")
    print(f"  gefeuert {ergebnis['gefeuert']} · still {ergebnis['still']}")
    print(f"Protokollzeilen ohne zugeordnete Eingabe: {ergebnis['protokollzeilen_ohne_eingabe']}/{len(protokoll)}")
    for g, n in sorted(ergebnis["je_grund"].items(), key=lambda kv: -kv[1]):
        print(f"  {g:20s} {n}")
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

    # Stufe 1: enqueue OHNE promptSource-Zeile -> nie_am_haltepunkt.
    enq = [{"ts": None, "session": "abcd1234", "text": "hallo welt", "kind": "mensch", "datei": "x"}]
    r = stufe1_haltepunkt(enq, [])
    assert r[0]["erreicht"] is False, r[0]
    # Negativfall: dieselbe Nachricht MIT promptSource-Zeile -> erreicht.
    ps = [{"ts": None, "session": "abcd1234", "text": "hallo welt", "kind": "human", "datei": "y"}]
    r2 = stufe1_haltepunkt(enq, ps)
    assert r2[0]["erreicht"] is True, r2[0]

    print(f"selftest ok (MIN_HITS={MIN_HITS})")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        main()
