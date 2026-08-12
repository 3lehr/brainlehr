#!/usr/bin/env python3
"""Wo gehen Fragen verloren? Trichter vom Rohbestand bis zum Fall.

ANLASS (Auftrag 2026-08-12): runs/echtkorpus_2026-08-12T1000.json zeigt 89
Faelle, davon 76 auftrag / 13 frage -- rund 85 Prozent Auftraege, obwohl bei
Anlage der Aufgabe das Verhaeltnis noch 72 zu 6 war. Bevor irgendetwas gebaut
wird: an welcher Stelle der Kette (roh -> echte Nachricht -> eindeutig ->
Kandidat -> Fall) sterben Fragen ueberproportional? Nicht raten, zaehlen.

QUELLE FUER "ROH": Sitzungstranskripte (type == 'user'), NICHT recall_log --
recall_log ist bereits ein Hook-Ausschnitt (18,3 % der Nachrichten erreichen
den Haltepunkt nie, siehe echtkorpus.py Docstring zu sitzungs_nachrichten).
Wer von recall_log aus zaehlt, zaehlt einen bereits gefilterten Bestand als
Nenner und misst den Hook, nicht die Kette. Satzart wird auf dem UNGEFILTERTEN
Text bestimmt -- satzart() braucht kein vorheriges Filtern.

KETTE, gemeinsam fuer 'pfad' und 'kennung' (beide gehen vom selben
Nachrichtentext aus):
  roh              jede Nutzer-Turn im Transkript, auch Rauschen
  echte_nachricht  ueberlebt echtkorpus._ist_echte_frage (Laenge, kein
                   Maschinentext, kein Fertigkeits-Vorspann)
  eindeutig        nach globalem Dedup (echtkorpus._ohne_doppelte)
  kandidat_pfad    hat mindestens einen Pfadkandidaten (ck.kandidaten, "/"
                   im Kandidaten)
  fall_pfad        der Kandidat loest zu <= MAX_ZIELE eindeutigem Wissen auf
  kandidat_kennung hat mindestens eine Kennung (L-xxxxxx oder /knoten/pfad)
  fall_kennung     die Kennung existiert in der DB

Der 'lese'-Kanal haengt NICHT am Nachrichtentext, sondern an session+ts aus
recall_log und an access_log -- eigene Kette, eigener Nenner:
  eingespielt   echte recall_log-Zeile mit Sitzung+Zeitstempel (echtkorpus.
                _einspielungen)
  gelesen       mindestens ein access_log-read im Nachrichtenfenster
  unabhaengig   davon mindestens ein Ziel, das nicht schon eingespielt war
  fall_lese     unabhaengig und <= MAX_ZIELE Ziele

Aufruf:
    python3 trichter_fragen.py --out runs/trichter_fragen_<datum>.json
    python3 trichter_fragen.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "haken"))
sys.path.insert(0, str(WURZEL / "kern"))

import codekanten as ck  # noqa: E402
import speicher  # noqa: E402
import echtkorpus as ek  # noqa: E402

SATZARTEN = ("frage", "auftrag")


def _leere_stufen() -> dict:
    return {s: {a: 0 for a in SATZARTEN} for s in (
        "roh", "echte_nachricht", "eindeutig",
        "kandidat_pfad", "fall_pfad",
        "kandidat_kennung", "fall_kennung")}


def roh_nachrichten_je_satzart(wurzel: Path = ek.SITZUNGEN) -> list[tuple[str, str]]:
    """Wie echtkorpus.sitzungs_nachrichten, aber OHNE den _ist_echte_frage-
    Filter -- das ist hier der erste Trichterschritt, kein Vorfilter."""
    raus = []
    if not wurzel.exists():
        return raus
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
            if not text:
                continue
            raus.append((text, ek.satzart(text)))
    return raus


def trichter(roh: list[tuple[str, str]], conn) -> dict:
    stufen = _leere_stufen()
    for art in SATZARTEN:
        stufen["roh"][art] = sum(1 for _, a in roh if a == art)

    echte = [(t, a) for t, a in roh if ek._ist_echte_frage(t)]
    for art in SATZARTEN:
        stufen["echte_nachricht"][art] = sum(1 for _, a in echte if a == art)

    gesehen = set()
    eindeutig = []
    for t, a in echte:
        if t in gesehen:
            continue
        gesehen.add(t)
        eindeutig.append((t, a))
    for art in SATZARTEN:
        stufen["eindeutig"][art] = sum(1 for _, a in eindeutig if a == art)

    for t, a in eindeutig:
        pfade = sorted(k for k in ck.kandidaten(t) if "/" in k)
        if pfade:
            stufen["kandidat_pfad"][a] += 1
            ziele = set()
            for k in pfade:
                for w in ck.wissen_zu(k, conn):
                    if not w["mehrdeutig"]:
                        ziele.add((w["quelle_art"], w["quelle_id"]))
            if ziele and len(ziele) <= ek.MAX_ZIELE:
                stufen["fall_pfad"][a] += 1

        kennungen = sorted(ek.kennungen(t))
        if kennungen:
            stufen["kandidat_kennung"][a] += 1
            ziele = set()
            for k in kennungen:
                treffer = ek.kennung_pruefen(k, conn)
                if treffer:
                    ziele.add((treffer["art"], treffer["id"]))
            if ziele:
                stufen["fall_kennung"][a] += 1
    return stufen


def lese_trichter(conn, pfad: Path = ek.RECALL_LOG) -> dict:
    """Eigene Kette fuer den 'lese'-Kanal, siehe Modulkopf."""
    stufen = {s: {a: 0 for a in SATZARTEN} for s in (
        "eingespielt", "gelesen", "unabhaengig", "fall_lese")}
    nach_sitzung: dict[str, list[dict]] = {}
    for e in ek._einspielungen(pfad):
        nach_sitzung.setdefault(e["session"], []).append(e)

    for session, eintraege in nach_sitzung.items():
        for i, e in enumerate(eintraege):
            art = ek.satzart(e["prompt"])
            stufen["eingespielt"][art] += 1
            fenster_ende = eintraege[i + 1]["ts"] if i + 1 < len(eintraege) else None
            sql = ("SELECT DISTINCT node_path FROM access_log WHERE action = 'read' "
                   "AND status = 'completed' AND client = 'claude-code' "
                   "AND node_path IS NOT NULL AND session LIKE ? AND timestamp > ?")
            params = [f"{session}%", ek.wirkung._fmt_ts(e["ts"])]
            if fenster_ende is not None:
                sql += " AND timestamp <= ?"
                params.append(ek.wirkung._fmt_ts(fenster_ende))
            gelesen = {r[0] for r in conn.execute(sql, params)}
            if not gelesen:
                continue
            stufen["gelesen"][art] += 1
            unabhaengig = gelesen - e["eingespielt"]
            if not unabhaengig:
                continue
            stufen["unabhaengig"][art] += 1
            if len(unabhaengig) <= ek.MAX_ZIELE:
                stufen["fall_lese"][art] += 1
    return stufen


def _groesster_abfall(stufen: dict, reihenfolge: list[str], art: str) -> tuple[str, str, int]:
    """Zwischen welchen zwei benachbarten Stufen faellt 'art' am staerksten
    (absolut), und wie viele gehen dort verloren?"""
    schlimmster = (None, None, -1)
    for a, b in zip(reihenfolge, reihenfolge[1:]):
        verlust = stufen[a][art] - stufen[b][art]
        if verlust > schlimmster[2]:
            schlimmster = (a, b, verlust)
    return schlimmster


def _selftest() -> None:
    import sqlite3
    import tempfile
    import unittest.mock as mock

    roh = [
        ("Was ist mit lib/trip_service.dart los?", "frage"),        # -> kandidat+fall pfad
        ("kurz", "frage"),                                          # zu kurz, stirbt bei echte_nachricht
        ("<task-notification>Maschinentext</task-notification>", "frage"),  # stirbt bei echte_nachricht
        ("Was ist mit lib/trip_service.dart los?", "frage"),        # Duplikat, stirbt bei eindeutig
        ("Siehe L-abc123 dazu, das ist eine sehr lange Zeile Text.", "frage"),  # kandidat+fall kennung
        ("Erstelle ein neues Modul fuer die Auswertung bitte jetzt.", "auftrag"),  # kein Kandidat
    ]

    with mock.patch.object(ek, "kennungen",
                            lambda t: ({"L-abc123"} if "L-abc123" in t else set())):
        class FakeConn:
            def execute(self, *a, **k):
                raise AssertionError("nicht benutzt in diesem Zweig")

        with mock.patch.object(ck, "kandidaten",
                                lambda t: {"lib/trip_service.dart"} if "trip_service" in t else set()), \
             mock.patch.object(ck, "wissen_zu",
                                lambda pfad, conn: [{"quelle_art": "lehre", "quelle_id": "L-1",
                                                      "mehrdeutig": 0}]), \
             mock.patch.object(ek, "kennung_pruefen",
                                lambda k, conn: {"art": "lehre", "id": k} if k == "L-abc123" else None):
            stufen = trichter(roh, conn=None)

    assert stufen["roh"]["frage"] == 5 and stufen["roh"]["auftrag"] == 1, stufen
    assert stufen["echte_nachricht"]["frage"] == 3, stufen   # 'kurz' und Maschinentext raus
    assert stufen["eindeutig"]["frage"] == 2, stufen         # Duplikat raus
    assert stufen["kandidat_pfad"]["frage"] == 1, stufen
    assert stufen["fall_pfad"]["frage"] == 1, stufen
    assert stufen["kandidat_kennung"]["frage"] == 1, stufen
    assert stufen["fall_kennung"]["frage"] == 1, stufen
    assert stufen["kandidat_pfad"]["auftrag"] == 0, stufen   # der Auftrag hat keinen Pfad -> 0, nicht geraten

    # Groesster Abfall bei 'frage' liegt zwischen roh und echte_nachricht (5 -> 3 -> 2 -> 1 -> 1).
    reihenfolge = ["roh", "echte_nachricht", "eindeutig", "kandidat_pfad", "fall_pfad"]
    a, b, verlust = _groesster_abfall(stufen, reihenfolge, "frage")
    assert (a, b, verlust) == ("roh", "echte_nachricht", 2), (a, b, verlust)

    # lese_trichter: eigener Nenner, Gegenprobe Kontamination + Fenstergrenze wie in echtkorpus.
    log = Path(tempfile.mkdtemp()) / "recall.jsonl"
    log.write_text("\n".join(json.dumps(z) for z in [
        {"session": "aaaa1111", "ts": "2026-08-12T10:00:00+00:00",
         "prompt": "Wo steht die Regel zur Fenstergroesse genau?", "nodes": []},
        {"session": "bbbb2222", "ts": "2026-08-12T10:00:00+00:00",
         "prompt": "Erledige jetzt bitte die Migration fuer diese Tabelle vollstaendig.", "nodes": []},
    ]) + "\n", encoding="utf-8")
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE access_log (node_path TEXT, action TEXT, status TEXT, "
                  "client TEXT, session TEXT, timestamp TEXT)")
    conn.execute("INSERT INTO access_log VALUES ('/x/echt','read','completed',"
                  "'claude-code','aaaa1111','2026-08-12T10:00:05Z')")
    conn.commit()
    lstufen = lese_trichter(conn, log)
    assert lstufen["eingespielt"]["frage"] == 1 and lstufen["eingespielt"]["auftrag"] == 1, lstufen
    assert lstufen["gelesen"]["frage"] == 1 and lstufen["gelesen"]["auftrag"] == 0, lstufen
    assert lstufen["fall_lese"]["frage"] == 1, lstufen

    print("selftest ok (Kette + groesster Abfall + lese-Trichter je Satzart)", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return

    roh = roh_nachrichten_je_satzart()
    with speicher.lesen() as conn:
        stufen = trichter(roh, conn)
        lstufen = lese_trichter(conn)

    print(f"Rohbestand: {len(roh)} Nutzer-Turns aus Sitzungstranskripten")
    for art in SATZARTEN:
        print(f"\n-- {art} --")
        reihenfolge = ["roh", "echte_nachricht", "eindeutig", "kandidat_pfad", "fall_pfad"]
        for s in reihenfolge:
            print(f"  {s}: {stufen[s][art]}")
        a2, b2, verlust = _groesster_abfall(stufen, reihenfolge, art)
        print(f"  groesster Abfall (pfad-Kette): {a2} -> {b2}, -{verlust}")
        print(f"  kandidat_kennung: {stufen['kandidat_kennung'][art]}, "
              f"fall_kennung: {stufen['fall_kennung'][art]}")
        print(f"  lese: eingespielt {lstufen['eingespielt'][art]}, "
              f"gelesen {lstufen['gelesen'][art]}, "
              f"unabhaengig {lstufen['unabhaengig'][art]}, "
              f"fall_lese {lstufen['fall_lese'][art]}")

    if a.out:
        a.out.write_text(json.dumps(
            {"rohbestand_turns": len(roh), "kette": stufen, "lese_kette": lstufen},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nGeschrieben: {a.out}")


if __name__ == "__main__":
    main()
