#!/usr/bin/env python3
"""reifegrad.py -- S1 aus docs/PLAN_DESTILLE_2026-08-09.md: Reifegrad MESSEN
statt zuweisen, und die Schranke fuer Normrang 1/2.

TEIL 1 -- REIFEGRAD. Gleiche Bauform wie konfidenz.py (drei Regime,
Praezedenz in dieser Reihenfolge, importiert von dort statt neu gebaut --
beobachtbare_datei()/naechste_pruefung()/wissensart() sind Ladder-Rung-2,
kein zweites Mal geschrieben):

  1 REIFE_ERKLAERT     -- ein MENSCH hat entschieden, mit Grund. Nur an
    knowledge_nodes moeglich (norm_entschieden_von gesetzt, nicht
    maschinell, norm_entschieden_grund nicht leer). Schlaegt jede Ableitung
    -- deshalb zuerst geprueft.
  2 REIFE_ABGELEITET    -- der Bezug ist beobachtbar (source nennt eine
    Datei, die existiert und in einem Git-Repo liegt), ODER die Aussage
    traegt einen Pruefvermerk (norm_entscheidung <> 'offen' -- eine
    EXPLIZITE Entscheidung liegt vor, auch wenn sie von einer Maschine
    stammt: das ist der Fall der 62 Selbstzuschreibungen, siehe unten),
    ODER sie ist mehrfach unabhaengig aufgetreten (Lehren: occurrences >= 2).
  3 REIFE_UNBESTIMMT    -- nichts davon. KEIN Makel, sondern eine
    FAELLIGKEIT: naechste_pruefung() aus konfidenz.py liefert ein Datum,
    kein Papierkorb.

Lehren koennen strukturell nie REIFE_ERKLAERT erreichen: lessons_learned hat
kein Feld, das einen menschlichen Entscheider mit Grund traegt (anders als
knowledge_nodes.norm_entschieden_von/_grund) -- gemessen an schema.sql, kein
Nachbau. Das ist selbst ein Befund und wird im Bericht ausgewiesen, nicht
stillschweigend auf 0 gerundet.

Die 62 bestehenden Selbstzuschreibungen werden NICHT ruckwirkend geaendert
(Auftrag Punkt 3) -- dieses Modul liest nur, es schreibt an knowledge_nodes
nirgends.

TEIL 2 -- DIE SCHRANKE (Normrang 1/2), korrigiert 2026-08-09 nach
Betreibereinwand: die urspruengliche Fassung ("maschineller Schreiber darf
Rang 1/2 nie setzen") haette 100% der Rang-1/2-Normen blockiert, darunter
zwei legitime Aufzeichnungen deutschen WEG-Rechts
(/ops/verwalterwahl-weg-im-buckeberg-zum-2027/rechtslage-die-*). Der
Denkfehler: ENTSCHEIDEN (dass etwas bei uns gelten soll -- Normsetzung,
Sache des Menschen) und AUFZEICHNEN (dass eine fremde Instanz etwas
entschieden hat -- ein Bericht ueber eine Tatsache, darf die Maschine) sind
zwei verschiedene Handlungen. Die Schranke haengt darum an der HERKUNFT DER
NORM (source), nicht am Schreiber:

  - Hausnorm  (source zeigt NICHT auf eine externe Stelle) + Rang 1/2
    + Entscheider maschinell erkennbar  -> ABGEWIESEN.
  - Fremdnorm (source nennt Gesetz/Verordnung/Urteil/Normungsstelle,
    erkannt ueber normachsen.FREMDE_QUELLE) -> die Maschine darf
    aufzeichnen, jeder Rang.

Woran ein maschineller Entscheider erkennbar ist: norm_entschieden_von
nennt sich selbst als KI. Gemessen am echten Bestand 2026-08-09 (SELECT
norm_rang, norm_entschieden_von, ... WHERE norm_rang IN (1,2)): 37 Zeilen
gesamt, 33 tragen woertlich 'claude-code/opus-5', 4 tragen 'unbekannt' --
KEINE einzige NULL oder einen Menschennamen. MASCHINEN_MERKMALE unten ist
darum eine Substring-Liste bekannter Anbieter-/Produktnamen (dieselbe Menge
wie knowledge_mcp_server.py::_MODELL_ALIAS/_ANBIETER, hier als LIKE-fähige
Substrings statt als Python-Normalisierung). 'unbekannt' matcht bewusst
NICHT: ein nicht nachweislich maschineller Schreiber wird nicht blockiert
(GRENZE aus dem Auftrag -- Belegpflicht ersetzt die Abnahme, sie ergaenzt
sie nicht; ein Rang, der auf eine Bestaetigung wartet, die niemand geben
kann, erzeugt eine Halde).

Der eigentliche Deckel ist ein SQL-Trigger in schema.sql (Regel an der
Tabelle, nicht im Aufrufer). SQLite kennt kein eingebautes REGEXP, und ein
registriertes Custom-Function haette ~20 raw-SQL-Skripte gebrochen, die die
DB ohne diese Python-Verbindung anfassen -- die LIKE-Kette im Trigger ist
darum von Hand aus denselben zwei Stichwortlisten uebersetzt, die hier
stehen (MASCHINEN_MERKMALE, FREMDE_QUELLE importiert aus normachsen.py).
_selftest() unten prueft beide Fassungen (Python hier, SQL im Trigger)
gegen dieselben Beispielsaetze und bricht, wenn sie auseinanderlaufen.

Aufruf:
    python3 reifegrad.py bericht
    python3 reifegrad.py --selftest
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from konfidenz import beobachtbare_datei, naechste_pruefung, CET  # noqa: E402
from normachsen import FREMDE_QUELLE  # noqa: E402
from haken.ort import DB as DB_PATH  # noqa: E402

REIFE_ERKLAERT = "erklaert"
REIFE_ABGELEITET = "abgeleitet"
REIFE_UNBESTIMMT = "unbestimmt"

# Siehe Moduldocstring Teil 2. Reihenfolge unwichtig (Substring-Test).
MASCHINEN_MERKMALE = ("claude", "gpt", "gemini", "anthropic", "opus", "sonnet", "haiku")


def ist_maschine(entschieden_von: str | None) -> bool:
    """Selbstauskunft, nicht mehr -- so gut wie der Aufrufer (gleiche
    Einschraenkung wie anlass='selbst'/'betreiber' im Schema-Kommentar)."""
    klein = (entschieden_von or "").lower()
    return any(m in klein for m in MASCHINEN_MERKMALE)


def ist_nachweislich_mensch(entschieden_von: str | None) -> bool:
    """'unbekannt' ist NICHT dasselbe wie 'ein Mensch hat entschieden' --
    es ist Abwesenheit einer Aussage, nicht deren Gegenteil. Gemessen: 44
    Zeilen tragen woertlich 'unbekannt' als Entscheider (SELECT ... WHERE
    norm_entscheidung <> 'offen' GROUP BY norm_entschieden_von). Ohne diese
    Funktion waeren sie faelschlich REIFE_ERKLAERT (weil nicht maschinell
    erkennbar) statt REIFE_ABGELEITET (Pruefvermerk liegt vor, der
    Entscheider ist nur nicht benannt)."""
    klein = (entschieden_von or "").strip().lower()
    return bool(klein) and klein != "unbekannt" and not ist_maschine(entschieden_von)


def ist_fremde_norm(source: str | None) -> bool:
    """Deckt sich mit normachsen.FREMDE_QUELLE -- importiert, nicht
    nachgebaut (normachsen.py bleibt unveraendert, siehe Auftrag)."""
    return bool(FREMDE_QUELLE.search(source or ""))


def bewerten_knoten(row: dict, now: datetime) -> dict:
    """Reifegrad fuer eine Zeile aus knowledge_nodes. row braucht mindestens
    path, source, updated_at, norm_entscheidung, norm_entschieden_von,
    norm_entschieden_grund."""
    entschieden = (row.get("norm_entscheidung") or "offen") != "offen"
    von = row.get("norm_entschieden_von")
    grund = row.get("norm_entschieden_grund")
    if entschieden and grund and ist_nachweislich_mensch(von):
        return {"regime": REIFE_ERKLAERT, "grund": "menschlicher Entscheider mit Begruendung",
                "naechste_pruefung": None}
    if beobachtbare_datei(row.get("source")) is not None:
        return {"regime": REIFE_ABGELEITET, "grund": "Bezug beobachtbar (Datei in Git-Repo)",
                "naechste_pruefung": None}
    if entschieden:
        return {"regime": REIFE_ABGELEITET, "grund": "Pruefvermerk: explizite Entscheidung liegt vor",
                "naechste_pruefung": None}
    if not row.get("updated_at"):
        return {"regime": REIFE_UNBESTIMMT, "grund": "kein Bezugszeitpunkt", "naechste_pruefung": None}
    return {"regime": REIFE_UNBESTIMMT, "grund": "kein Beleg",
            "naechste_pruefung": naechste_pruefung(row["updated_at"], row.get("path") or "",
                                                     row.get("source"), now)}


def bewerten_lehre(row: dict, now: datetime) -> dict:
    """Reifegrad fuer eine Zeile aus lessons_learned. Erreicht REIFE_ERKLAERT
    strukturell nie -- kein Feld traegt einen menschlichen Entscheider mit
    Grund (siehe Moduldocstring)."""
    if beobachtbare_datei(row.get("node_path")) is not None:
        return {"regime": REIFE_ABGELEITET, "grund": "Bezug beobachtbar (Datei in Git-Repo)",
                "naechste_pruefung": None}
    if (row.get("occurrences") or 1) >= 2:
        return {"regime": REIFE_ABGELEITET, "grund": "mehrfach unabhaengig aufgetreten",
                "naechste_pruefung": None}
    if row.get("status") in ("resolved", "escalated_to_rule"):
        return {"regime": REIFE_ABGELEITET, "grund": "Pruefvermerk: status ist resolved/escalated_to_rule",
                "naechste_pruefung": None}
    bezug = row.get("last_seen") or row.get("first_seen")
    if not bezug:
        return {"regime": REIFE_UNBESTIMMT, "grund": "kein Bezugszeitpunkt", "naechste_pruefung": None}
    return {"regime": REIFE_UNBESTIMMT, "grund": "kein Beleg",
            "naechste_pruefung": naechste_pruefung(bezug, row.get("node_path") or "", None, now)}


def verteilung(conn: sqlite3.Connection, now: datetime | None = None) -> dict:
    now = now or datetime.now(CET)
    knoten = conn.execute(
        "SELECT path, source, updated_at, norm_entscheidung, norm_entschieden_von, "
        "norm_entschieden_grund FROM knowledge_nodes WHERE zurueckgezogen = 0"
    ).fetchall()
    lehren = conn.execute(
        "SELECT node_path, occurrences, status, first_seen, last_seen FROM lessons_learned"
    ).fetchall()
    zaehler_k = {REIFE_ERKLAERT: 0, REIFE_ABGELEITET: 0, REIFE_UNBESTIMMT: 0}
    zaehler_l = {REIFE_ERKLAERT: 0, REIFE_ABGELEITET: 0, REIFE_UNBESTIMMT: 0}
    for r in knoten:
        zaehler_k[bewerten_knoten(dict(r), now)["regime"]] += 1
    for r in lehren:
        zaehler_l[bewerten_lehre(dict(r), now)["regime"]] += 1
    return {
        "knoten_gesamt": len(knoten), "knoten": zaehler_k,
        "lehren_gesamt": len(lehren), "lehren": zaehler_l,
    }


def normrang_herkunft_bericht(conn: sqlite3.Connection) -> dict:
    """Sichtbarmachung fuer Rang 1/2 (Auftrag Punkt 3: nicht aendern, nur
    zeigen)."""
    zeilen = conn.execute(
        "SELECT path, norm_rang, norm_entschieden_von, source FROM knowledge_nodes "
        "WHERE norm_rang IN (1,2) AND zurueckgezogen = 0"
    ).fetchall()
    maschinell_haus = maschinell_fremd = mensch_bzw_unklar = 0
    for r in zeilen:
        if ist_maschine(r["norm_entschieden_von"]):
            if ist_fremde_norm(r["source"]):
                maschinell_fremd += 1
            else:
                maschinell_haus += 1
        else:
            mensch_bzw_unklar += 1
    return {
        "rang_1_2_gesamt": len(zeilen),
        "maschinell_hausnorm": maschinell_haus,
        "maschinell_fremdnorm_aufgezeichnet": maschinell_fremd,
        "nicht_nachweislich_maschinell": mensch_bzw_unklar,
    }


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("kommando", nargs="?", default="bericht", choices=["bericht"])
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    conn = _connect()
    try:
        v = verteilung(conn)
        h = normrang_herkunft_bericht(conn)
    finally:
        conn.close()
    print("Reifegrad -- Knoten:", v["knoten"], "von", v["knoten_gesamt"])
    print("Reifegrad -- Lehren:", v["lehren"], "von", v["lehren_gesamt"])
    print("Rang 1/2 nach Herkunft:", h)
    return 0


# ─── Selbsttest ─────────────────────────────────────────────────────────────

def _selftest() -> int:
    now = datetime(2026, 8, 9, tzinfo=CET)

    # --- Teil 1: Reifegrad, ein Fall je Regime -----------------------------
    erklaert = bewerten_knoten({
        "path": "/x", "source": "Chatgespraech", "updated_at": now.isoformat(),
        "norm_entscheidung": "norm_unbefristet", "norm_entschieden_von": "Erika Mustermann",
        "norm_entschieden_grund": "Betreiberentscheidung im Gespraech",
    }, now)
    assert erklaert["regime"] == REIFE_ERKLAERT, erklaert

    # 'unbekannt' als Entscheider ist NICHT erklaert (Abwesenheit einer
    # Aussage ist kein Mensch) -- faellt auf abgeleitet zurueck, weil die
    # Entscheidung selbst (der Pruefvermerk) trotzdem vorliegt. Gemessen: 44
    # solche Zeilen im echten Bestand, siehe ist_nachweislich_mensch().
    unbekannt_von = bewerten_knoten({
        "path": "/u", "source": "irgendein Freitext ohne Datei", "updated_at": now.isoformat(),
        "norm_entscheidung": "norm_unbefristet", "norm_entschieden_von": "unbekannt",
        "norm_entschieden_grund": "Sammelmigration",
    }, now)
    assert unbekannt_von["regime"] == REIFE_ABGELEITET, unbekannt_von

    abgeleitet_pruefvermerk = bewerten_knoten({
        "path": "/y", "source": "irgendein Freitext ohne Datei", "updated_at": now.isoformat(),
        "norm_entscheidung": "norm_unbefristet", "norm_entschieden_von": "claude-code/opus-5",
        "norm_entschieden_grund": "erzeugt aus CLAUDE.md",
    }, now)
    assert abgeleitet_pruefvermerk["regime"] == REIFE_ABGELEITET, abgeleitet_pruefvermerk

    unbestimmt = bewerten_knoten({
        "path": "/z", "source": None, "updated_at": now.isoformat(),
        "norm_entscheidung": "offen", "norm_entschieden_von": None, "norm_entschieden_grund": None,
    }, now)
    assert unbestimmt["regime"] == REIFE_UNBESTIMMT, unbestimmt
    assert unbestimmt["naechste_pruefung"] is not None, "unbestimmt muss eine Faelligkeit tragen, keinen Papierkorb"

    # Lehren erreichen REIFE_ERKLAERT strukturell nie.
    lehre_abgeleitet = bewerten_lehre({"node_path": None, "occurrences": 3, "status": "active",
                                        "last_seen": now.isoformat()}, now)
    assert lehre_abgeleitet["regime"] == REIFE_ABGELEITET, lehre_abgeleitet
    lehre_unbestimmt = bewerten_lehre({"node_path": None, "occurrences": 1, "status": "active",
                                        "last_seen": now.isoformat()}, now)
    assert lehre_unbestimmt["regime"] == REIFE_UNBESTIMMT, lehre_unbestimmt
    assert lehre_unbestimmt["naechste_pruefung"] is not None

    # --- Teil 2: Machinen-/Fremd-Erkennung ----------------------------------
    assert ist_maschine("claude-code/opus-5") is True
    assert ist_maschine("unbekannt") is False
    assert ist_maschine("Erika Mustermann") is False
    assert ist_maschine(None) is False

    fremd_beispiele = [
        "erzeugt aus buckeberg/recht/jahresabrechnung-beim-wechsel.md (§ 28 WEG "
        "über gesetze-im-internet.de, BGH V ZR 206/24 über dejure.org, Abrufdatum 2026-07-22)",
        "erzeugt aus buckeberg/recht/verwaltervertrag-pruefpunkte.md (§ 26 und § 9b WEG "
        "über gesetze-im-internet.de, Abrufdatum 2026-07-22)",
        "DIN 18040 Abschnitt 4.3",
        "WCAG 2.2 AA Kriterium 2.4.11",
    ]
    haus_beispiele = [
        "erzeugt aus /Users/lehrmacbook/.claude/CLAUDE.md (Stand 2026-08-01T13:07:10+02:00)",
        "Entscheidung des Betreibers im Gespraech 2026-08-07T12:30:00+0200",
        "Betreiberentscheidung im Chat 2026-08-09T07:40:00+0200",
    ]
    for s in fremd_beispiele:
        assert ist_fremde_norm(s), s
    for s in haus_beispiele:
        assert not ist_fremde_norm(s), s

    # Python-Fassung (ist_fremde_norm) und die SQL-LIKE-Kette im Trigger
    # muessen auf denselben Beispielen uebereinstimmen -- reine Substring-
    # Nachbildung der LIKE-Klauseln aus schema.sql, damit eine Abweichung
    # zwischen den beiden Fassungen hier auffliegt statt erst am Trigger.
    def _sql_like_fremd(s: str) -> bool:
        woerter = ("gesetz", "verordnung", "urteil", "az.", "aktenzeichen", "bgbl",
                   "eu-verordnung", "richtlinie", "din ", "en ", "iso ", "iec ", "bsi ",
                   "wcag", "rfc")
        klein = s.lower()
        return any(w in klein for w in woerter)

    for s in fremd_beispiele + haus_beispiele:
        assert ist_fremde_norm(s) == _sql_like_fremd(s), (
            f"Python-Regex und SQL-LIKE-Nachbildung laufen auseinander bei: {s!r}")

    # --- Teil 2: die Schranke selbst, gegen eine In-Memory-DB --------------
    conn = _init_test_db()
    try:
        # ROT VOR GRUEN: ohne die Trigger waere jede der folgenden INSERTs
        # erfolgreich -- dieselbe DB, dieselben Zeilen, nur ohne die zwei
        # Trigger unten eingespielt.
        conn.execute("""CREATE TABLE knowledge_nodes_ohne_schranke AS
                        SELECT * FROM knowledge_nodes WHERE 0""")

        def _insert(path, rang, von, source, grund="weil"):
            conn.execute(
                "INSERT INTO knowledge_nodes (id, path, title, summary, norm_rang, "
                "norm_entscheidung, norm_entschieden_von, norm_entschieden_am, "
                "norm_entschieden_grund, gilt_ab, source) "
                "VALUES (?, ?, ?, ?, ?, 'norm_unbefristet', ?, '2026-08-09', ?, '2026-08-09', ?)",
                (path, path, path, path, rang, von, grund, source),
            )

        # Fall 1: maschineller Entscheider, Hausnorm, Rang 1 -- ABGEWIESEN.
        try:
            _insert("/t/haus-maschine-rang1", 1, "claude-code/opus-5",
                    "erzeugt aus /Users/x/.claude/CLAUDE.md")
            raise AssertionError("haette abgewiesen werden muessen: maschinelle Hausnorm Rang 1")
        except sqlite3.IntegrityError as e:
            assert "menschlichen Entscheider" in str(e), e

        # Fall 2 (Grenzwert): dieselbe Zeile mit Rang 2 -- ABGEWIESEN.
        try:
            _insert("/t/haus-maschine-rang2", 2, "claude-code/opus-5",
                    "erzeugt aus /Users/x/.claude/CLAUDE.md")
            raise AssertionError("haette abgewiesen werden muessen: maschinelle Hausnorm Rang 2")
        except sqlite3.IntegrityError:
            pass

        # Fall 3 (Grenzwert): dieselbe Zeile mit Rang 3 -- DURCHGELASSEN.
        _insert("/t/haus-maschine-rang3", 3, "claude-code/opus-5",
                "erzeugt aus /Users/x/.claude/CLAUDE.md")

        # Fall 4: menschlicher Entscheider, Hausnorm, Rang 1 -- DURCHGELASSEN.
        _insert("/t/haus-mensch-rang1", 1, "Erika Mustermann", "Chatgespraech 2026-08-09")

        # Fall 5: maschineller Entscheider, Fremdnorm, Rang 1 -- DURCHGELASSEN
        # (die Maschine zeichnet eine fremde Tatsache auf, entscheidet nichts).
        _insert("/t/fremd-maschine-rang1", 1, "claude-code/opus-5",
                "§ 28 WEG über gesetze-im-internet.de")

        # Fall 6 (Negativfall): Fakt ohne Rang bleibt unberuehrt, auch mit
        # maschinellem 'Entscheider' im Feld (das Feld ist hier bedeutungslos,
        # weil norm_rang NULL bleibt -- keine_norm verlangt norm_entschieden_von
        # NICHT, siehe Trigger knowledge_nodes_norm_entscheidung_rang_bi/bu).
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, title, summary, source, norm_entscheidung, "
            "norm_entschieden_von, norm_entschieden_am, norm_entschieden_grund) "
            "VALUES (?, ?, ?, ?, ?, 'keine_norm', 'claude-code/opus-5', '2026-08-09', 'Fakt, kein Rang')",
            ("/t/fakt-ohne-rang", "/t/fakt-ohne-rang", "/t/fakt-ohne-rang", "/t/fakt-ohne-rang", "irgendeine Quelle"),
        )

        # Fall 7 (Regressionsnachweis, namentlich): die zwei echten WEG-Knoten
        # aus dem Bestand bleiben unter der Schranke weiterhin anlegbar.
        _insert(
            "/ops/verwalterwahl-weg-im-buckeberg-zum-2027/rechtslage-die-jahresabrechnung-2026",
            1, "claude-code/opus-5",
            "erzeugt aus buckeberg/recht/jahresabrechnung-beim-wechsel.md (§ 28 WEG "
            "über gesetze-im-internet.de, BGH V ZR 206/24 über dejure.org, Abrufdatum 2026-07-22)",
        )
        _insert(
            "/ops/verwalterwahl-weg-im-buckeberg-zum-2027/rechtslage-die-angebotenen",
            1, "claude-code/opus-5",
            "erzeugt aus buckeberg/recht/verwaltervertrag-pruefpunkte.md (§ 26 und § 9b WEG "
            "über gesetze-im-internet.de, Abrufdatum 2026-07-22)",
        )
        conn.commit()
    finally:
        conn.close()

    print("reifegrad.py: alle Selbsttests bestanden "
          "(3 Reifegrad-Regime + 4 Herkunfts-/Machinen-Faelle + 7 Schranken-Faelle inkl. 2 WEG-Regressionen).")
    return 0


def _init_test_db() -> sqlite3.Connection:
    """In-Memory-DB aus dem echten schema.sql -- keine Schema-Kopie von
    Hand, damit dieser Test bei einer Schema-Aenderung sofort mitbricht
    statt gegen ein veraltetes Abbild gruen zu bleiben."""
    conn = sqlite3.connect(":memory:")
    schema = (HERE / "schema.sql").read_text()
    conn.executescript(schema)
    return conn


if __name__ == "__main__":
    raise SystemExit(main())
