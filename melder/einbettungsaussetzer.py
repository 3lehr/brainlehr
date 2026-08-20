#!/usr/bin/env python3
"""Meldet beim Sitzungsstart, wenn die Aussetzer-Sicherung juengst pausiert hat.

AUFTRAG A3 (docs/PLAN_BETRIEBSPROFILE_2026-08-20.md). ANLASS: der
Einbettungsdienst (Ollama) war am 2026-08-20 zweimal weg, und niemand merkte
es -- 13 Eintraege entstanden ohne Vektor, ohne dass irgendwo ein Fehler
erschien. kern/embeddings.py pausiert seither nach 5 Fehlern in Folge fuer
120s (Vorbild mem0) und schreibt DABEI eine Zeile nach ort.AUSSETZER_LOG.

DER KERN IST NICHT DAS PAUSIEREN, SONDERN DAS MERKEN: eine Pause, die
niemand sieht, macht den stillen Ausfall nur billiger. Weil jede MCP-Sitzung
ihren eigenen Prozess startet (siehe CLAUDE.md), setzt ein Neustart den
Aussetzer-Zaehler zurueck -- das Protokoll ist die einzige Stelle, die ueber
die Prozessgrenze hinweg traegt. Dieser Melder liest es beim naechsten
Sitzungsstart, denselben Kanal wie eilmeldung_faellig.py.

FENSTER statt aller Zeilen fuer immer: ein Aussetzer von letzter Woche, der
laengst repariert ist (naechster build_embeddings.py-Lauf traegt die Luecke
nach), muss nicht jeden kuenftigen Sitzungsstart stoeren -- sonst wird der
Melder mit der Zeit ignoriert (siehe eilmeldung_faellig.py, gleiches
Prinzip in die andere Richtung). SICHTBARKEIT_STUNDEN ist bewusst grosszuegig
(24h): der Betreiber soll den Vorfall in JEDER Sitzung sehen, die er nach
dem Ausfall noch am selben Tag beginnt, nicht nur in der naechsten.

Schweigt, wenn die Protokolldatei fehlt oder leer ist -- das ist der
Normalfall (Dienst laeuft durchgehend).

Aufruf:
    python3 melder/einbettungsaussetzer.py            # meldet oder schweigt
    python3 melder/einbettungsaussetzer.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken")]

sys.path.insert(0, str(_w / "haken"))
import ort  # noqa: E402 -- liefert AUSSETZER_LOG (kein fest verdrahteter Dateiname hier)

SICHTBARKEIT_STUNDEN = 24


def _zeilen(pfad: Path) -> list[dict]:
    try:
        roh = pfad.read_text(encoding="utf-8")
    except OSError:
        return []
    aus = []
    for zeile in roh.splitlines():
        if not zeile.strip():
            continue
        try:
            aus.append(json.loads(zeile))
        except ValueError:
            continue
    return aus


def _juengere_als(eintraege: list[dict], grenze: datetime) -> list[dict]:
    aus = []
    for e in eintraege:
        try:
            ts = datetime.fromisoformat(e.get("ts", ""))
        except (TypeError, ValueError):
            continue
        if ts >= grenze:
            aus.append(e)
    return aus


def melde(pfad: Path | None = None, jetzt: datetime | None = None) -> str:
    jetzt = jetzt or datetime.now(timezone.utc)
    grenze = jetzt - timedelta(hours=SICHTBARKEIT_STUNDEN)
    aktuell = _juengere_als(_zeilen(pfad or ort.AUSSETZER_LOG), grenze)
    if not aktuell:
        return ""
    letzter = aktuell[-1]
    kopf = (
        f"⚠ Einbettungsdienst {len(aktuell)}x in den letzten "
        f"{SICHTBARKEIT_STUNDEN}h pausiert (Aussetzer-Sicherung, "
        f"kern/embeddings.py) -- zuletzt um {letzter.get('ts', '?')} nach "
        f"{letzter.get('fehler_in_folge', '?')} Fehlern in Folge gegen "
        f"{letzter.get('url', '?')}:"
    )
    return (
        kopf + "\n"
        "  Neue Eintraege bekamen in diesem Zeitraum vermutlich keinen "
        "Vektor und sind ueber die Bedeutungssuche unauffindbar, bis "
        "build_embeddings.py sie nachtraegt. Dienst pruefen (melder/"
        "modellwege.py) und den Nachlauf anstossen."
    )


def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "einbettungsausfaelle.jsonl"
        jetzt = datetime(2026, 8, 21, 9, 0, tzinfo=timezone.utc)

        # A) Keine Datei -> Stille, kein Absturz (Normalfall).
        assert melde(log, jetzt) == "", "fehlende Datei muss still bleiben"

        # B) ROT (Anlassfall nachgestellt): ein Aussetzer vor zwei Stunden --
        #    muss anschlagen.
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": "2026-08-21T07:00:00+00:00", "fehler_in_folge": 5,
                "pause_sekunden": 120.0, "url": "http://127.0.0.1:11434",
            }) + "\n")
        aus = melde(log, jetzt)
        assert aus != "", "ein juengster Aussetzer darf nicht schweigen"
        assert "1x" in aus and "07:00:00" in aus, aus

        # C) Zwei Aussetzer im Fenster -> beide gezaehlt, der juengste steht
        #    im Kopf (genau der 2026-08-20-Fall: zweimal am selben Tag).
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": "2026-08-21T08:30:00+00:00", "fehler_in_folge": 5,
                "pause_sekunden": 120.0, "url": "http://127.0.0.1:11434",
            }) + "\n")
        aus = melde(log, jetzt)
        assert "2x" in aus, aus
        assert "08:30:00" in aus, "der juengste Eintrag muss im Kopf stehen"

        # D) NEGATIVFALL: derselbe Eintrag, aber ausserhalb des Sichtbarkeits-
        #    fensters (vor mehr als 24h) -- muss verstummen.
        alt_log = Path(tmp) / "alt.jsonl"
        with open(alt_log, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": "2026-08-18T09:00:00+00:00", "fehler_in_folge": 5,
                "pause_sekunden": 120.0, "url": "http://127.0.0.1:11434",
            }) + "\n")
        assert melde(alt_log, jetzt) == "", "ein alter Aussetzer darf nicht mehr melden"

        # E) Kaputte Zeile stoert nicht, wird uebersprungen.
        kaputt_log = Path(tmp) / "kaputt.jsonl"
        with open(kaputt_log, "a", encoding="utf-8") as f:
            f.write("kein json\n")
            f.write(json.dumps({
                "ts": "2026-08-21T08:00:00+00:00", "fehler_in_folge": 5,
                "pause_sekunden": 120.0, "url": "x",
            }) + "\n")
        assert melde(kaputt_log, jetzt) != ""

    print("einbettungsaussetzer: Selbsttest gruen")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        _selftest()
        return
    text = melde()
    if text:
        print(text)


if __name__ == "__main__":
    main()
