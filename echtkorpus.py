#!/usr/bin/env python3
"""Ein Pruefkorpus, der nicht erfunden wird, sondern anfaellt.

ANLASS (2026-08-11, zwei Befunde desselben Tages): Der bisherige Pruefkorpus
wurde AUS den Eintraegen erzeugt, die er finden soll -- im Handel heisst das
data snooping bias, und es macht jede Abrufzahl daraus wertlos (Lopez de Prado
2017, Recherche im Pruefspruch #6). Der zweite Befund kam vom Messaufbau
selbst: drei Subagenten bekamen die Loesung durch den Abruf-Haken eingespielt,
bevor sie die Aufgabe lasen.

Beide Fehler haben dieselbe Wurzel: Aufgabentext und Zielangabe stammten aus
DERSELBEN Quelle. Dieses Modul trennt die Kanaele:

  Aufgabentext  eine ECHTE Nachricht aus recall_log.jsonl -- so gestellt, wie
                sie gestellt wurde, ohne Kenntnis eines Ziels
  Zielangabe    ueber code_kanten, also ueber den DATEIPFAD -- ein Kanal, der
                mit dem Wortlaut der Nachricht nichts zu tun hat

Ein Fall entsteht nur, wenn eine echte Nachricht einen spezifischen Pfad nennt
UND an diesem Pfad Wissen haengt. Niemand formuliert dafuer etwas.

WARUM SAMMLER UND NICHT KORPUS: Der erste Lauf am 2026-08-11 ergab aus 299
menschlichen Nachrichten genau VIER brauchbare Faelle. Das misst nichts. Die
ehrliche Antwort darauf ist nicht, die Anforderungen zu senken, bis genug
zusammenkommt -- dann waere man wieder beim erfundenen Korpus. Die ehrliche
Antwort ist, zu warten: jede kuenftige Nachricht, die eine Datei nennt, legt
einen Fall dazu, ohne dass jemand etwas tut.

DREI FILTER, jeder gegen einen beobachteten Fehlerweg:
  1. Systemmeldungen raus (<task-notification> und Verwandte). Ohne diesen
     Filter waren 38 von 38 Kandidaten zur Haelfte Maschinentext.
  2. Nur SPEZIFISCHE Pfade (mit Verzeichnisteil). 'settings.json' ist keine
     Adresse, sondern ein Wort.
  3. Nur eindeutige Kanten und hoechstens drei Ziele. Ein Fall mit zwanzig
     richtigen Antworten prueft nichts.

Aufruf:
    python3 echtkorpus.py --sammeln --out runs/echtkorpus.json
    python3 echtkorpus.py --selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "haken"))

import codekanten as ck  # noqa: E402
import ort  # noqa: E402
import speicher  # noqa: E402

# Das Protokoll liegt NEBEN der Datenbank, nicht neben dem Quelltext.
# ort.RECALL_LOG leitet den Pfad aus der Wurzel des Arbeitsbaums ab -- und ein
# Arbeitsbaum traegt keine Daten (heute schon einmal erlebt, L-0f4036: eine
# leere Datenbank statt einer fehlenden Datei). Deshalb wird der Ort aus dem
# tatsaechlich benutzten Datenbankpfad abgeleitet; nur wenn dort nichts liegt,
# bleibt es bei der Ableitung aus dem Quelltextort.
_NEBEN_DER_DB = Path(ort.DB).parent / "recall_log.jsonl"
RECALL_LOG = _NEBEN_DER_DB if _NEBEN_DER_DB.exists() else ort.RECALL_LOG
MASCHINENTEXT = re.compile(
    r"<task-notification>|<system-reminder>|<knowledge-recall>|tool-use-id|"
    r"<antwort-recall>|<persisted-output>")
MIN_LAENGE = 25
MAX_ZIELE = 3


def echte_nachrichten(pfad: Path = RECALL_LOG) -> list[str]:
    """Nur was ein Mensch geschrieben hat. Maschinentext traegt zwar Pfade,
    aber keine Frage -- und eine Frage ist der Gegenstand der Messung."""
    if not pfad.exists():
        return []
    raus = []
    for zeile in pfad.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            satz = json.loads(zeile)
        except json.JSONDecodeError:
            continue
        text = (satz.get("prompt") or "").strip()
        if len(text) >= MIN_LAENGE and not MASCHINENTEXT.search(text):
            raus.append(text)
    return raus


def faelle_bilden(nachrichten: list[str], conn) -> list[dict]:
    faelle = []
    for text in nachrichten:
        pfade = sorted(k for k in ck.kandidaten(text) if "/" in k)
        ziele = set()
        for k in pfade:
            for w in ck.wissen_zu(k, conn):
                if not w["mehrdeutig"]:
                    ziele.add((w["quelle_art"], w["quelle_id"]))
        if ziele and len(ziele) <= MAX_ZIELE:
            faelle.append({"prompt": text, "pfade": pfade,
                            "ziele": [{"art": a, "id": i} for a, i in sorted(ziele)]})
    return faelle


def _selftest() -> None:
    import tempfile

    log = Path(tempfile.mkdtemp()) / "recall.jsonl"
    log.write_text("\n".join(json.dumps(z) for z in [
        {"prompt": "Sieh dir bitte lib/trip_service.dart an, da stimmt etwas nicht."},
        {"prompt": "<task-notification>lib/trip_service.dart ist fertig</task-notification>"},
        {"prompt": "kurz"},
        {"prompt": "Was ist mit settings.json?"},
    ]) + "\n")

    n = echte_nachrichten(log)
    assert len(n) == 2, n                      # Maschinentext und zu Kurzes raus
    assert all("task-notification" not in x for x in n)

    class FakeConn:
        def __init__(self, treffer): self.treffer = treffer
        def execute(self, *a, **k): raise AssertionError("nicht benutzt")

    # Kanal-Trennung: die Ziele kommen NICHT aus dem Text, sondern aus der
    # Kantenabfrage -- hier gestellt.
    import unittest.mock as mock
    with mock.patch.object(ck, "wissen_zu",
                            lambda pfad, conn: [{"quelle_art": "lehre", "quelle_id": "L-1",
                                                  "mehrdeutig": 0}] if "trip_service" in pfad else []):
        f = faelle_bilden(n, None)
    assert len(f) == 1, f                      # nur die Nachricht mit spezifischem Pfad
    assert f[0]["ziele"] == [{"art": "lehre", "id": "L-1"}]
    assert "settings.json" not in json.dumps(f), "unspezifischer Name wurde als Adresse genommen"

    # Gegenprobe: zu viele Ziele -> kein Fall. Ein Fall mit zwanzig richtigen
    # Antworten prueft nichts.
    with mock.patch.object(ck, "wissen_zu",
                            lambda pfad, conn: [{"quelle_art": "lehre", "quelle_id": f"L-{i}",
                                                  "mehrdeutig": 0} for i in range(MAX_ZIELE + 1)]):
        assert faelle_bilden(n, None) == []

    # Gegenprobe: mehrdeutige Kante zaehlt nicht.
    with mock.patch.object(ck, "wissen_zu",
                            lambda pfad, conn: [{"quelle_art": "lehre", "quelle_id": "L-1",
                                                  "mehrdeutig": 1}]):
        assert faelle_bilden(n, None) == []

    print("selftest ok (4 Faelle, Gegenprobe in beide Richtungen)", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sammeln", action="store_true")
    p.add_argument("--out", type=Path)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return

    nachrichten = echte_nachrichten()
    with speicher.lesen() as conn:
        faelle = faelle_bilden(nachrichten, conn)

    print(f"{len(nachrichten)} echte Nachrichten -> {len(faelle)} Faelle")
    if len(faelle) < 20:
        print(f"  ZU WENIG ZUM MESSEN. {len(faelle)} Faelle sind ein Anfang, keine "
              "Grundlage -- die Anforderungen zu senken waere der Rueckweg zum "
              "erfundenen Korpus.")
    for f in faelle[:6]:
        print(f"  {f['pfade'][:2]} -> {[z['id'] for z in f['ziele']]}")
    if a.out:
        a.out.write_text(json.dumps(
            {"verfahren": "Aufgabentext aus recall_log (echte Nachricht), Ziel ueber "
                          "code_kanten (Dateipfad) -- getrennte Kanaele, keine Erzeugung",
             "nachrichten": len(nachrichten), "faelle": faelle},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nGeschrieben: {a.out}")


if __name__ == "__main__":
    main()
