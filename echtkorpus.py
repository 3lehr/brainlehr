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

# Zweiter Zielkanal: eine Kennung STEHT im Text -- keine Aufloesung noetig,
# nur eine Existenzpruefung gegen die Datenbank. Das macht diese Faelle
# LEICHT (Antwort im Prompt) und darum eine eigene Klasse (siehe Modulkopf).
_LEHRE = re.compile(r"\bL-[0-9a-f]{6}\b")
# Knotenpfad: beginnt mit '/', mindestens zwei Segmente -- ein blosses '/etc'
# waere Rauschen. Die DB-Pruefung filtert den Rest (dieselbe Wirklichkeit-
# statt-Vertrauen-Regel wie in codekanten.aufloesen): ein Kandidat wie
# '/Volumes/daten/...' loest sich hier einfach nicht auf.
_KNOTENPFAD = re.compile(r"(?<!\S)/[a-zA-Z][\w\-]*(?:/[\w\-]+)+")
SITZUNGEN = Path.home() / ".claude" / "projects"


def _ist_echte_frage(text: str) -> bool:
    """Gemeinsamer Filter beider Quellen. '<' am Anfang und Maschinentext
    sind keine Fragen -- eine Frage ist der Gegenstand der Messung."""
    return (len(text) >= MIN_LAENGE and not text.startswith("<")
            and not MASCHINENTEXT.search(text))


def echte_nachrichten(pfad: Path = RECALL_LOG) -> list[str]:
    """Quelle 1: recall_log.jsonl -- nur was den Haltepunkt erreicht hat."""
    if not pfad.exists():
        return []
    raus = []
    for zeile in pfad.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            satz = json.loads(zeile)
        except json.JSONDecodeError:
            continue
        text = (satz.get("prompt") or "").strip()
        if _ist_echte_frage(text):
            raus.append(text)
    return raus


def sitzungs_nachrichten(wurzel: Path = SITZUNGEN) -> list[str]:
    """Quelle 2: Sitzungstranskripte -- auch die Nachrichten, die den
    Haltepunkt nie erreicht haben (gemessen: 18,3 % tun das nicht)."""
    if not wurzel.exists():
        return []
    raus = []
    for pfad in wurzel.glob("*/[0-9a-f-]*.jsonl"):
        try:
            zeilen = pfad.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for zeile in zeilen:
            try:
                satz = json.loads(zeile)
            except json.JSONDecodeError:
                continue
            if satz.get("type") != "user":
                continue
            inhalt = (satz.get("message") or {}).get("content")
            if isinstance(inhalt, str):
                text = inhalt.strip()
            elif isinstance(inhalt, list):
                text = "\n".join(
                    t.get("text", "") for t in inhalt
                    if isinstance(t, dict) and t.get("type") == "text").strip()
            else:
                continue
            if _ist_echte_frage(text):
                raus.append(text)
    return raus


def _ohne_doppelte(nachrichten: list[str]) -> list[str]:
    return list(dict.fromkeys(nachrichten))


def faelle_bilden(nachrichten: list[str], conn) -> list[dict]:
    """Klasse 'pfad': die Zielangabe kommt ueber code_kanten, nicht aus dem
    Text -- der schwere Fall, um den es diesem Korpus eigentlich geht."""
    faelle = []
    for text in nachrichten:
        pfade = sorted(k for k in ck.kandidaten(text) if "/" in k)
        ziele = set()
        for k in pfade:
            for w in ck.wissen_zu(k, conn):
                if not w["mehrdeutig"]:
                    ziele.add((w["quelle_art"], w["quelle_id"]))
        if ziele and len(ziele) <= MAX_ZIELE:
            faelle.append({"prompt": text, "klasse": "pfad", "pfade": pfade,
                            "ziele": [{"art": a, "id": i} for a, i in sorted(ziele)]})
    return faelle


def kennungen(text: str) -> set[str]:
    return set(_LEHRE.findall(text or "")) | set(_KNOTENPFAD.findall(text or ""))


def kennung_pruefen(kandidat: str, conn) -> dict | None:
    """Existenzpruefung -- eine erfundene Kennung ist kein Fall."""
    if _LEHRE.fullmatch(kandidat):
        zeile = conn.execute(
            "SELECT id FROM lessons_learned WHERE id = ?", (kandidat,)).fetchone()
        return {"art": "lehre", "id": zeile["id"]} if zeile else None
    zeile = conn.execute(
        "SELECT path FROM knowledge_nodes WHERE path = ?", (kandidat,)).fetchone()
    return {"art": "knoten", "id": zeile["path"]} if zeile else None


def kennung_faelle_bilden(nachrichten: list[str], conn) -> list[dict]:
    """Klasse 'kennung': die Zielangabe steht wortwoertlich im Text -- der
    LEICHTE Fall, deshalb eigene Klasse statt gemeinsamer Topf mit 'pfad'."""
    faelle = []
    for text in nachrichten:
        ziele = set()
        for k in sorted(kennungen(text)):
            treffer = kennung_pruefen(k, conn)
            if treffer:
                ziele.add((treffer["art"], treffer["id"]))
        if ziele:
            faelle.append({"prompt": text, "klasse": "kennung",
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

    # Klasse 'kennung': existierende Kennung im Text ergibt einen Fall,
    # eine erfundene keinen -- beide Richtungen, wie beim Pfad-Kanal.
    class FakeCursor:
        def __init__(self, treffer): self._treffer = treffer
        def fetchone(self): return self._treffer

    class FakeConn2:
        def __init__(self, echte_lehre_ids, echte_pfade):
            self._lehren = echte_lehre_ids
            self._pfade = echte_pfade

        def execute(self, sql, params):
            wert = params[0]
            if "lessons_learned" in sql:
                return FakeCursor({"id": wert} if wert in self._lehren else None)
            return FakeCursor({"path": wert} if wert in self._pfade else None)

    echte_kennung_text = "Siehe L-0f4036 zur Lesetuer, das war der Befund."
    erfundene_kennung_text = "Siehe L-ffffff, das steht nirgends."
    knotenpfad_text = "Der Knoten /agents/mcp-tools erklaert das genauer."

    conn2 = FakeConn2(echte_lehre_ids={"L-0f4036"}, echte_pfade={"/agents/mcp-tools"})

    kf = kennung_faelle_bilden([echte_kennung_text], conn2)
    assert len(kf) == 1 and kf[0]["klasse"] == "kennung", kf
    assert kf[0]["ziele"] == [{"art": "lehre", "id": "L-0f4036"}]

    assert kennung_faelle_bilden([erfundene_kennung_text], conn2) == [], \
        "eine erfundene Kennung wurde als Fall gezaehlt"

    kf_pfad = kennung_faelle_bilden([knotenpfad_text], conn2)
    assert len(kf_pfad) == 1
    assert kf_pfad[0]["ziele"] == [{"art": "knoten", "id": "/agents/mcp-tools"}]

    # Ein 'pfad'-Fall bleibt Klasse 'pfad', nicht vermischt mit 'kennung'.
    with mock.patch.object(ck, "wissen_zu",
                            lambda pfad, conn: [{"quelle_art": "lehre", "quelle_id": "L-1",
                                                  "mehrdeutig": 0}] if "trip_service" in pfad else []):
        f_pfad = faelle_bilden(n, None)
    assert f_pfad[0]["klasse"] == "pfad", f_pfad

    # Doppelter Text ergibt einen Fall, nicht zwei.
    doppelt = _ohne_doppelte([echte_kennung_text, echte_kennung_text, knotenpfad_text])
    assert doppelt == [echte_kennung_text, knotenpfad_text], doppelt
    assert len(kennung_faelle_bilden(doppelt, conn2)) == 2

    print("selftest ok (Gegenprobe je Klasse in beide Richtungen)", file=sys.stderr)


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

    aus_log = echte_nachrichten()
    aus_sitzungen = sitzungs_nachrichten()
    nachrichten = _ohne_doppelte(aus_log + aus_sitzungen)

    with speicher.lesen() as conn:
        faelle = faelle_bilden(nachrichten, conn) + kennung_faelle_bilden(nachrichten, conn)

    nach_klasse = {k: sum(1 for f in faelle if f["klasse"] == k) for k in ("pfad", "kennung")}
    print(f"{len(aus_log)} aus recall_log + {len(aus_sitzungen)} aus Sitzungen "
          f"-> {len(nachrichten)} eindeutige Nachrichten -> {len(faelle)} Faelle "
          f"(pfad: {nach_klasse['pfad']}, kennung: {nach_klasse['kennung']})")
    if len(faelle) < 20:
        print(f"  ZU WENIG ZUM MESSEN. {len(faelle)} Faelle sind ein Anfang, keine "
              "Grundlage -- die Anforderungen zu senken waere der Rueckweg zum "
              "erfundenen Korpus.")
    for f in faelle[:6]:
        quelle = f.get("pfade", sorted(kennungen(f["prompt"])))[:2]
        print(f"  [{f['klasse']}] {quelle} -> {[z['id'] for z in f['ziele']]}")
    if a.out:
        a.out.write_text(json.dumps(
            {"verfahren": "Aufgabentext aus recall_log + Sitzungstranskripten (echte "
                          "Nachricht), Ziel ueber code_kanten (Pfad) oder Existenzpruefung "
                          "(Kennung) -- getrennte Kanaele, keine Erzeugung",
             "nachrichten": len(nachrichten),
             "nachrichten_aus_log": len(aus_log),
             "nachrichten_aus_sitzungen": len(aus_sitzungen),
             "faelle": faelle},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nGeschrieben: {a.out}")


if __name__ == "__main__":
    main()
