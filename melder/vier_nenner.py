#!/usr/bin/env python3
"""vier_nenner.py -- Aufgabe 62 (docs/PLAN_PARALLEL_2026-08-13.md): vier
Zahlen mit Nenner statt einer Zahl ohne Kontext.

A  Wie viele menschliche Nachrichten gab es in dieser Sitzung, und bei wie
   vielen LIEF ueberhaupt ein Abruf (query() wurde aufgerufen)? NENNER AUS
   DEM TRANSKRIPT, nicht aus recall_log.jsonl -- recall_log fuehrt nur
   Zeilen, die main() (haken/knowledge_recall_hook.py) ueberhaupt schreibt.
   Nachrichten, die den UserPromptSubmit-Haltepunkt NIE erreichen (Klient
   liefert sie als Attachment waehrend laufender Arbeit), fehlen dort
   komplett -- ein Nenner aus recall_log wuerde nur die Ueberlebenden
   zaehlen, exakt der Fehler von L-bd4e5f (2026-08-09, schon einmal
   passiert). messungen/ausloeser.py hat das Problem bereits geloest
   (scan() liest die Warteschlangen-Ereignisse (queue-operation/enqueue)
   direkt aus den Transcript-Dateien und gleicht sie gegen die
   promptSource-Zeilen ab, die den Haltepunkt markieren) -- hier nur
   IMPORTIERT (reine Funktionen, keine Seiteneffekte, kein Schreiben nach
   runs/), nicht verandert: fremde Datei laut Dateiplan.
B  Wie viele der GELAUFENEN Abrufe (aus A) fanden nichts (leer)? B ist
   AUSDRUECKLICH KEINE Fehlerquote -- manchmal liegt nichts Passendes vor,
   und Schweigen ist dann richtig (Auftrag). B wird durch den Kanarienvogel
   (Aufgabe 63, kern/kanarienvogel.py) weiter zerlegbar in 'ehrlich leer'
   und 'stumm ausgefallen' -- diese Aufteilung braucht aber eine LIVE-Sonde
   je Abruf (noch nicht verdrahtet, siehe dortiger Moduldoc) und steht hier
   darum nicht als Zahl, nur als Verweis.
C  Wo ein Ziel bekannt ist (runs/pruefkorpus.jsonl, target_kind gesetzt):
   wie viele Abrufe trafen es? Wiederverwendet kern/abrufguete.py
   (lade_korpus/messe) -- ruft den ECHTEN Abrufweg (rh.query()), kein
   zweiter, selbstgebauter Suchpfad.
D  Aufgabe 42 (Trichterfragen/Satzart-Erkennung, Auftrag C in
   docs/PLAN_PARALLEL_2026-08-13.md) -- eigener Auftrag, hier bewusst NICHT
   gemessen, nur als Luecke ausgewiesen statt stillschweigend wegzulassen.

TABU BEACHTET: haken/knowledge_recall_hook.py und haken/antwort_abruf.py
werden nur GELESEN (importiert), nie veraendert -- waehrend dieser Arbeit
laeuft eine Nullmessung (Okkultation) des Abrufwegs, ein Fremdeingriff
waere darin nicht mehr von einer echten Verschiebung zu unterscheiden.

Aufruf:
    python3 melder/vier_nenner.py            # Bericht auf stdout
    python3 melder/vier_nenner.py --selftest  # rot-vor-gruen, kein Ollama noetig
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

WURZEL = _w
sys.path.insert(0, str(WURZEL / "messungen"))
sys.path.insert(0, str(WURZEL / "kern"))
import ausloeser  # noqa: E402 -- messungen/ausloeser.py, nur GELESEN/importiert
import abrufguete  # noqa: E402 -- kern/abrufguete.py, nur GELESEN/importiert
import speicher  # noqa: E402 -- die Naht (kern/speicher.py): lesen() statt eigener Verbindung

RECALL_LOG = WURZEL / "recall_log.jsonl"


def _zeit(s: str):
    return ausloeser._zeit(s)


def _protokoll_fenster() -> tuple[datetime, datetime, list[dict]]:
    if not RECALL_LOG.exists():
        raise SystemExit("recall_log.jsonl fehlt -- Nenner A/B nicht messbar")
    protokoll = [json.loads(z) for z in RECALL_LOG.read_text(encoding="utf-8").splitlines() if z.strip()]
    if not protokoll:
        raise SystemExit("recall_log.jsonl leer -- Nenner A/B nicht messbar")
    ab = max(_zeit(protokoll[0]["ts"]), _zeit(ausloeser.LEERPROTOKOLL_AB))
    bis = _zeit(protokoll[-1]["ts"]) + timedelta(seconds=ausloeser.ZEITFENSTER_S)
    return ab, bis, protokoll


def nenner_a_b() -> dict:
    """A/B aus dem TRANSKRIPT -- ruft dieselben reinen Funktionen wie
    messungen/ausloeser.py::main() (scan/stufe1_haltepunkt/grund), schreibt
    aber keine runs/-Datei (das ist Aufgabe 46, Auftrag D) und liefert nur
    die Aggregation, die dieser Melder braucht."""
    ab, bis, protokoll = _protokoll_fenster()
    nach_text: dict = defaultdict(list)
    nach_sitzung: dict = defaultdict(list)
    for p in protokoll:
        p["_t"] = _zeit(p["ts"])
        nach_sitzung[p["session"]].append(p)
        if p.get("prompt"):
            nach_text[(p["session"], p["prompt"].strip())].append(p)

    promptsource_evs, enqueue_evs, _dateien = ausloeser.scan(ab, bis)
    menschen = ausloeser.stufe1_haltepunkt(
        [e for e in enqueue_evs if e["kind"] == "mensch"], promptsource_evs
    )

    verbraucht: set = set()
    for e in menschen:
        if not e["erreicht"]:
            e["gelaufen"] = False
            e["leer"] = None
            continue
        ps = e["_ps"]
        zeile = None
        for k in nach_text.get((ps["session"], ps["text"]), []):
            if id(k) not in verbraucht:
                zeile = k
                break
        if zeile is None:  # Rueckfall ueber die Zeit, wie ausloeser.main()
            for k in nach_sitzung.get(ps["session"], []):
                if id(k) in verbraucht or k.get("prompt"):
                    continue
                d = (k["_t"] - ps["ts"]).total_seconds()
                if 0 <= d <= ausloeser.ZEITFENSTER_S:
                    zeile = k
                    break
        if zeile is not None:
            verbraucht.add(id(zeile))
            e["gelaufen"] = True
            e["leer"] = not zeile["nodes"] and not zeile["lessons"]
        else:
            grund = ausloeser.grund(ps["text"])
            # min_hits/schraegstrich/kein_prompt: query() wurde in main()
            # NIE aufgerufen (fruehe Sperren, siehe dortige Reihenfolge) --
            # kein Abruf gelaufen. 'unerklaert': Haltepunkt erreicht, keine
            # Sperre greift, trotzdem keine recall_log-Zeile -- log_recall()
            # ist reines Beiwerk (jeder Fehler wird verschluckt, siehe
            # dessen Docstring), darum zaehlt das hier als 'gelaufen, aber
            # unprotokolliert' statt als 'sicher nicht gelaufen'.
            e["gelaufen"] = grund == "unerklaert"
            e["leer"] = None

    a_gesamt = len(menschen)
    a_gelaufen = sum(1 for e in menschen if e["gelaufen"])
    b_leer = sum(1 for e in menschen if e.get("leer") is True)
    return {"a_nachrichten": a_gesamt, "a_abruf_gelaufen": a_gelaufen, "b_leer": b_leer}


def nenner_c(korpus_pfade: list[Path] | None = None) -> dict:
    """Wiederverwendet kern/abrufguete.py: echter Abrufweg (rh.query()),
    Faelle mit bekanntem Ziel (target_kind gesetzt), Treffer ja/nein. RO-
    Zugang ueber die Naht (kern/speicher.py::lesen()) statt einer eigenen
    Verbindung."""
    faelle, _dubletten = abrufguete.lade_korpus(korpus_pfade)
    with speicher.lesen() as conn:
        ergebnis = abrufguete.messe(faelle, conn)
    # ergebnis[g] ist (treffer_n, gesamt_n) je Gruppe -- KEINE Liste von
    # Booleans (Fund beim ersten Anlauf: sum(v)/len(v) auf dem Tupel zaehlte
    # falsch, weil ein 2er-Tupel immer len==2 hat). LESSON+NODE zusammen
    # ergeben alle Faelle MIT target_kind (MIT_KANTE/OHNE_KANTE sind
    # dieselben Faelle noch einmal, anders gruppiert -- nicht mitzaehlen,
    # sonst doppelt).
    n = sum(ergebnis[g][1] for g in ("LESSON", "NODE"))
    treffer = sum(ergebnis[g][0] for g in ("LESSON", "NODE"))
    return {"c_ziele_bekannt": n, "c_getroffen": treffer}


def melden(mit_c: bool = True) -> dict:
    ab = nenner_a_b()
    c = {"c_ziele_bekannt": None, "c_getroffen": None}
    if mit_c:
        c = nenner_c()
    befund = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "A": f"{ab['a_abruf_gelaufen']}/{ab['a_nachrichten']} menschliche Nachrichten loesten "
             f"ueberhaupt einen Abruf aus (Nenner aus dem Transkript)",
        "B": (f"{ab['b_leer']}/{ab['a_abruf_gelaufen']} gelaufene Abrufe fanden nichts -- "
              f"KEINE Fehlerquote, manchmal ist Schweigen richtig"
              if ab["a_abruf_gelaufen"] else "0/0 -- kein Abruf lief"),
        "C": (f"{c['c_getroffen']}/{c['c_ziele_bekannt']} Faelle mit bekanntem Ziel trafen es"
              if mit_c else "nicht gemessen (--ohne-c)"),
        "D": "nicht gemessen (Aufgabe 42, eigener Auftrag)",
        "zahlen": {**ab, **c},
    }
    return befund


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--ohne-c", action="store_true",
                     help="C ueberspringen (spart 45 echte Abrufe/Ollama-Aufrufe)")
    args = ap.parse_args()
    if args.selftest:
        _selftest()
        return
    befund = melden(mit_c=not args.ohne_c)
    for k in ("A", "B", "C", "D"):
        print(f"{k}: {befund[k]}")


# --- Selbsttest (rot vor gruen) ---------------------------------------------

def _selftest() -> None:
    """Rot-Probe: ein Fall, in dem die vier Zahlen falsch waeren, und Beleg,
    dass diese Aggregation es zeigt. Konstruiert ein Mini-Transkript +
    Mini-recall_log mit bekanntem Soll (3 Nachrichten: eine erreicht den
    Haltepunkt nie, eine loest einen leeren Abruf aus, eine einen mit
    Treffer) und prueft die Zahlen gegen dieses Soll -- ein falscher Nenner
    (z.B. aus recall_log statt aus dem Transkript gezaehlt) wuerde hier 2/2
    statt 2/3 fuer A liefern, das schlaegt die Probe fehl."""
    import tempfile
    from unittest import mock

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        projekte = tmp_path / "projects" / "testsitzung"
        projekte.mkdir(parents=True)
        transcript = projekte / "sitzung.jsonl"
        recall_log = tmp_path / "recall_log.jsonl"

        basis = datetime(2026, 8, 12, 10, 0, 0, tzinfo=timezone.utc)

        def ts(n_sek: int) -> str:
            return (basis + timedelta(seconds=n_sek)).isoformat().replace("+00:00", "Z")

        # Drei menschliche enqueue-Ereignisse (Nenner A). Reihenfolge bewusst
        # so, dass 'hallo' INNERHALB des Messfensters liegt -- ausloeser.py
        # spannt das Fenster [erste recall_log-ts, letzte recall_log-ts +
        # ZEITFENSTER_S] auf, OHNE Rueckwaerts-Puffer vor die erste Zeile (so
        # arbeitet das wiederverwendete Original: ab = max(erste Protokoll-
        # Zeile, LEERPROTOKOLL_AB)). Die erste enqueue-Zeile faellt darum nur
        # dann nicht aus dem Fenster, wenn ihr Zeitstempel NICHT vor dem
        # ihrer eigenen promptSource-/recall_log-Zeile liegt -- hier auf
        # dieselbe Sekunde gelegt (reale Logs koennen das, Klient und Haken
        # sind schneller als eine Sekunde):
        #   1) "frage ohne treffer im speicher heute" -- erreicht den Halte-
        #      punkt UND loest einen leeren Abruf aus (recall_log-Zeile mit
        #      leeren Listen) -- setzt den Fensterbeginn (ab).
        #   2) "hallo" -- erreicht den Haltepunkt NIE (kein promptSource-
        #      Partner), liegt zeitlich NACH (1) und VOR (3).
        #   3) "frage mit einem echten treffer im speicher" -- erreicht ihn
        #      UND liefert einen Treffer -- setzt das Fensterende (bis).
        zeilen = [
            {"type": "queue-operation", "operation": "enqueue", "sessionId": "abcd1234",
             "content": "frage ohne treffer im speicher heute", "timestamp": ts(0)},
            {"type": "user", "promptSource": True, "sessionId": "abcd1234",
             "origin": {"kind": "human"},
             "message": {"content": "frage ohne treffer im speicher heute"},
             "timestamp": ts(0)},
            {"type": "queue-operation", "operation": "enqueue", "sessionId": "abcd1234",
             "content": "hallo", "timestamp": ts(5)},
            {"type": "queue-operation", "operation": "enqueue", "sessionId": "abcd1234",
             "content": "frage mit einem echten treffer im speicher", "timestamp": ts(10)},
            {"type": "user", "promptSource": True, "sessionId": "abcd1234",
             "origin": {"kind": "human"},
             "message": {"content": "frage mit einem echten treffer im speicher"},
             "timestamp": ts(10)},
        ]
        with transcript.open("w", encoding="utf-8") as f:
            for z in zeilen:
                f.write(json.dumps(z) + "\n")

        recall_zeilen = [
            {"ts": ts(0).replace("Z", "+00:00"), "nodes": [], "lessons": [],
             "session": "abcd1234", "prompt": "frage ohne treffer im speicher heute"},
            {"ts": ts(10).replace("Z", "+00:00"), "nodes": ["/x/y"], "lessons": [],
             "session": "abcd1234", "prompt": "frage mit einem echten treffer im speicher"},
        ]
        with recall_log.open("w", encoding="utf-8") as f:
            for z in recall_zeilen:
                f.write(json.dumps(z) + "\n")

        with mock.patch.object(ausloeser, "PROJEKTE", tmp_path / "projects"), \
             mock.patch(f"{__name__}.RECALL_LOG", recall_log):
            ergebnis = nenner_a_b()

        # SOLL: 3 Nachrichten gesamt, 2 davon lösten einen Abruf aus (die
        # dritte erreicht den Haltepunkt nie), davon 1 leer.
        assert ergebnis["a_nachrichten"] == 3, ergebnis
        assert ergebnis["a_abruf_gelaufen"] == 2, ergebnis
        assert ergebnis["b_leer"] == 1, ergebnis

        # GEGENPROBE (falscher Nenner): wer A aus recall_log.jsonl zaehlt
        # (2 Zeilen) statt aus dem Transkript (3 Nachrichten), bekommt einen
        # zu kleinen Nenner -- genau der Fehler, den dieser Melder vermeiden
        # soll. Die Probe zeigt den Unterschied ausdruecklich.
        recall_nenner = sum(1 for _ in recall_log.read_text(encoding="utf-8").splitlines())
        assert recall_nenner != ergebnis["a_nachrichten"], (
            "Testaufbau untauglich: recall_log-Nenner und Transkript-Nenner "
            "duerfen sich fuer diese Probe nicht zufaellig gleichen"
        )

    # nenner_c(): ergebnis[g] ist ein (treffer_n, gesamt_n)-TUPEL je Gruppe,
    # keine Liste -- die Probe belegt genau die Verwechslung, die beim
    # ersten Anlauf dieses Melders durchrutschte (52/4 statt eines
    # sinnvollen Bruchs, weil sum(v)/len(v) auf dem Tupel selbst gerechnet
    # wurde statt auf den ersten/zweiten Eintrag). Faelschlicher Code haette
    # hier c_ziele_bekannt=8 (4 Gruppen * len==2) und c_getroffen>gesamt
    # geliefert -- die Asserts unten schlagen genau darauf an.
    fake_ergebnis = {"LESSON": (3, 5), "NODE": (7, 10), "MIT_KANTE": (4, 6), "OHNE_KANTE": (6, 9)}
    with mock.patch.object(abrufguete, "lade_korpus", return_value=([{"target_kind": "node"}] * 15, 0)), \
         mock.patch.object(abrufguete, "messe", return_value=fake_ergebnis), \
         mock.patch.object(speicher, "lesen"):
        c = nenner_c()
        assert c == {"c_ziele_bekannt": 15, "c_getroffen": 10}, c  # 5+10 gesamt, 3+7 treffer
        assert c["c_getroffen"] <= c["c_ziele_bekannt"], c  # Grenzwert: nie mehr Treffer als Faelle

    # Struktur von melden() ohne C (kein echter Abrufweg im Selbsttest --
    # kein Ollama-Netzwerkaufruf noetig, Walkthrough-Doktrin).
    with mock.patch(f"{__name__}.nenner_a_b", return_value={
            "a_nachrichten": 3, "a_abruf_gelaufen": 2, "b_leer": 1}):
        befund = melden(mit_c=False)
        assert befund["A"].startswith("2/3")
        assert befund["B"].startswith("1/2")
        assert befund["D"] == "nicht gemessen (Aufgabe 42, eigener Auftrag)"

        # Grenzwert: kein Abruf gelaufen -> B darf nicht durch 0 teilen.
        with mock.patch(f"{__name__}.nenner_a_b", return_value={
                "a_nachrichten": 5, "a_abruf_gelaufen": 0, "b_leer": 0}):
            befund0 = melden(mit_c=False)
            assert befund0["B"] == "0/0 -- kein Abruf lief", befund0

    print("SELFTEST OK: vier_nenner")


if __name__ == "__main__":
    main()
