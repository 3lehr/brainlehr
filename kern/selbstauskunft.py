#!/usr/bin/env python3
"""Was brainlehr ueber sich selbst sagt -- erhoben, nicht gepflegt.

DER ANLASS, und er ist genauer als jede Absichtserklaerung: Am 2026-08-20
fragte der Betreiber einen fremden Klienten (Hermes), ob er brainlehr kenne.
Die Antwort war inhaltlich sehr gut -- die vier Kerndisziplinen, der Zweck,
die Zwei-Schichten-Architektur, sogar der Zeitpunkt der letzten Sicherung auf
die Minute. Und JEDE gepflegte Zahl war falsch, alle in dieselbe Richtung:

    "20 Tabellen"                   gemessen 35
    "31 Trigger"                    gemessen 63
    "~20 Werkzeuge"                 gemessen 30
    "keine externen Pakete"         gemessen fuenf

Kein Halluzinieren, sondern ein Schnappschuss von frueher: brainlehr, wie es
einmal war. Genau die Fehlerklasse, fuer die brainlehr ueberhaupt gebaut
wurde -- ein Befund von gestern ist keine Tatsache von heute.

DIE TRENNLINIE, die das erklaert: Prinzipien altern langsam, Zahlen schnell.
Hermes hatte die Prinzipien richtig und jede Zahl falsch. Deshalb steht in
CLAUDE.md der Satz "Zahlen gehoeren dorthin, wo sie berechnet werden", und
deshalb erhebt dieses Modul jede Angabe zur Laufzeit aus der Quelle:

    Tabellen und Trigger  aus sqlite_master des laufenden Bestands
    Werkzeuge             aus der Registrierung TOOLS, nicht aus einer Liste
    Abhaengigkeiten       aus requirements.txt
    Faehigkeiten          aus dem Bestand (melder/selbstbeschreibung.py)

Eine Zahl, die hier als Literal stuende, waere gepflegt -- und damit wieder
das Problem statt der Loesung. tests/test_selbstauskunft.py prueft genau das
und faellt rot, sobald jemand eine hinschreibt.

Aufruf:
    python3 kern/selbstauskunft.py           # Text
    python3 kern/selbstauskunft.py --json
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

_w = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken")]

REPO = _w


def _zaehle(db: Path | None, art: str) -> int | None:
    """Anzahl aus sqlite_master -- None, wenn kein Bestand erreichbar ist.

    Ein fremder Klient hat moeglicherweise gar keine Datenbank. Der bekommt
    dann eine Auskunft ueber den CODE statt einer Ausnahme: Die Haelfte einer
    Antwort ist mehr wert als ein Absturz, solange sie sagt, welche Haelfte
    fehlt."""
    if db is None or not Path(db).is_file():
        return None
    try:
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            return c.execute(
                "SELECT count(*) FROM sqlite_master WHERE type = ?", (art,)
            ).fetchone()[0]
        finally:
            c.close()
    except sqlite3.Error:
        return None


def _werkzeuge() -> dict:
    """Aus der Registrierung, nicht aus einer Liste daneben.

    Zwei Quellen fuer dieselbe Menge gehen auseinander -- die Liste altert,
    waehrend die Registrierung waechst. Genau so entsteht "~20 Werkzeuge"."""
    try:
        import knowledge_mcp_server as kms
        namen = sorted(kms.TOOLS)
        return {"anzahl": len(namen), "namen": namen}
    except Exception as fehler:  # noqa: BLE001 -- Auskunft, kein Betriebsweg
        return {"anzahl": 0, "namen": [], "fehler": str(fehler)[:120]}


def _abhaengigkeiten() -> list:
    """Aus requirements.txt.

    "Reines Python 3, keine externen Pakete" war der teuerste Einzelfehler in
    Hermes' Beschreibung -- er klingt nach einer dauerhaften EIGENSCHAFT und
    ist eine Momentaufnahme. Solche Saetze altern unbemerkt, weil niemand
    nachsieht, ob aus "keine" inzwischen fuenf geworden sind."""
    p = REPO / "requirements.txt"
    if not p.is_file():
        return []
    raus = []
    for zeile in p.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#"):
            continue
        for trenner in (">=", "==", "~=", ">", "<", "["):
            if trenner in zeile:
                zeile = zeile.split(trenner)[0]
                break
        raus.append(zeile.split("#")[0].strip())
    return raus


def _bestandsort():
    try:
        import ort
        return Path(ort.DB)
    except Exception:  # noqa: BLE001
        return None


def erhebe(db: Path | None = ...) -> dict:
    """Alles, was ein fremder Klient wissen will -- zum Zeitpunkt des Aufrufs.

    `db` weglassen nimmt den Bestand des laufenden Systems; None oder ein
    nicht vorhandener Pfad liefert die Auskunft ohne Bestandszahlen."""
    if db is ...:
        db = _bestandsort()
    werkzeuge = _werkzeuge()
    return {
        "erhoben": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bestand": {
            "ort": str(db) if db else None,
            "tabellen": _zaehle(db, "table"),
            "trigger": _zaehle(db, "trigger"),
            "knoten": _menge(db, "knowledge_nodes"),
            "lehren": _menge(db, "lessons_learned"),
        },
        "werkzeuge": werkzeuge,
        "abhaengigkeiten": _abhaengigkeiten(),
    }


def _menge(db: Path | None, tabelle: str) -> int | None:
    if db is None or not Path(db).is_file():
        return None
    try:
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            return c.execute(f"SELECT count(*) FROM {tabelle}").fetchone()[0]
        finally:
            c.close()
    except sqlite3.Error:
        return None


def als_text(daten: dict) -> str:
    """Fuer den Menschen und fuer fremde Klienten.

    Jede Zahl traegt ihren Erhebungszeitpunkt mit. Eine Zahl ohne Zeitpunkt
    ist genau das, was hier weitergegeben wurde und veraltete."""
    b = daten["bestand"]
    z = [
        "brainlehr -- Selbstauskunft",
        f"erhoben: {daten['erhoben']} (jede Zahl unten gilt fuer diesen Zeitpunkt)",
        "",
        "Was es ist: ein Wissensspeicher, dessen Regeln als Datenbank-Trigger",
        "erzwungen sind statt als Konvention -- ein Eintrag ohne nachpruefbare",
        "Herkunft entsteht gar nicht erst. Die Zahlen unten sind erhoben, nicht",
        "gepflegt; eine gepflegte Beschreibung altert.",
        "",
    ]
    if b["ort"]:
        z += [f"Bestand: {b['ort']}",
              f"  Tabellen: {b['tabellen']}   Trigger: {b['trigger']}",
              f"  Knoten:   {b['knoten']}   Lehren: {b['lehren']}"]
    else:
        z += ["Bestand: nicht erreichbar -- die Angaben unten betreffen nur den Code."]
    w = daten["werkzeuge"]
    z += ["", f"Werkzeuge ueber MCP: {w['anzahl']}"]
    if w["namen"]:
        z += ["  " + ", ".join(w["namen"])]
    a = daten["abhaengigkeiten"]
    z += ["", f"Externe Pakete: {len(a) or 'keine'}"]
    if a:
        z += ["  " + ", ".join(a)]
    z += ["",
          "Was diese Auskunft NICHT sagt: ob der Bestand INHALTLICH stimmt.",
          "Sie zaehlt, was da ist. Ob ein Eintrag heute noch gilt, steht an ihm",
          "selbst (Geltung, Rang, Freigabe) -- nicht in dieser Uebersicht."]
    return "\n".join(z)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    daten = erhebe()
    print(json.dumps(daten, ensure_ascii=False, indent=2) if args.json
          else als_text(daten))
    return 0


if __name__ == "__main__":
    sys.exit(main())
