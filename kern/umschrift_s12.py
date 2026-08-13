#!/usr/bin/env python3
"""S12 Schritt 3: die behandelte Haelfte nach drei Schreibregeln umschreiben.

ZWEI-SCHRITT-WERKZEUG nach dem Vorbild von messungen/okkultation.py
(--aufgaben/--auswerten): dieses Modul ruft selbst KEIN Modell auf.

    1. --lose            Kandidaten + fertigen Auftrag ausgeben (dieses Skript)
    2. Hauptfaden         die Knoten tatsaechlich umschreiben (Agent/Mensch)
    3. --zurueckschreiben die neuen Fassungen pruefen und schreiben (dieses Skript)

Die drei Regeln (Knoten b4238789), woertlich in jedem Auftrag:
    1. Der Titel benennt die Sache, nicht ihre Herkunft.
    2. Die Zusammenfassung traegt in ein bis drei Saetzen die Kernaussage,
       verstaendlich ohne Vorwissen. Keine Verwaltungsformeln, kein Verweis
       auf Dateien oder Sitzungen als Ersatz fuer Inhalt.
    3. Der Volltext nennt die Begriffe mehrfach und unterschiedlich.

VOR JEDEM SCHREIBEN, ohne Ausnahme (kein stiller Fall):
    - kein Knoten ohne Zeile in s12_urfassungen (kern/sicherung_s12.py sichert sie)
    - kein Knoten der UNBEHANDELTEN Haelfte (Kontrollgruppe, kern/teilung_s12.py)
    - kein Knoten, den kern/umschrift_pruefstein.py beanstandet (Sachverlust)
    - kein Knoten, dessen neuer Volltext den alten Volltext WOERTLICH UND
      VOLLSTAENDIG enthaelt (Kontrollarm-Verdopplung statt Umschrift,
      Vorfall 2026-08-13, Lehre L-a4f6dd -- siehe ist_blosse_verdopplung()).
      Der Pruefstein oben sieht das NICHT: die alte Fassung ist Teilmenge
      der neuen, also fehlt nichts, also 0 Beanstandungen.

"Noch unbehandelt" (Auswahl fuer --lose) heisst: Titel UND Zusammenfassung
stimmen noch mit der Urfassung ueberein. Ein bereits umgeschriebener Knoten
weicht ab und faellt darum von selbst aus der naechsten Auswahl -- ein
Wiederaufnehmen nach Abbruch braucht keine Zusatzdatei.

Zugriff auf die Datenbank ausschliesslich ueber kern/speicher.py
(speicher.lesen()/speicher.schreiben()) -- keine eigene Verbindung am
Speicher vorbei (tests/test_naht_ratsche.py haelt das fest).

Aufruf:
    python3 umschrift_s12.py --lose runs/s12_lose_01.json --n 20
    python3 umschrift_s12.py --lose runs/s12_lose_02.json --n 20 --ab 20
    python3 umschrift_s12.py --zurueckschreiben runs/s12_lose_01.json runs/s12_neu_01.json
    python3 umschrift_s12.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import json
import sqlite3
from pathlib import Path

import speicher
import teilung_s12
import umschrift_pruefstein as pruefstein
from knowledge_mcp_server import now_iso  # noqa: E402 -- kanonisches Zeitstempelformat

WURZEL = _w

REGELN = (
    "1. Der Titel benennt die Sache, nicht ihre Herkunft.\n"
    "2. Die Zusammenfassung traegt in ein bis drei Saetzen die Kernaussage, "
    "verstaendlich ohne Vorwissen. Keine Verwaltungsformeln, kein Verweis auf "
    "Dateien oder Sitzungen als Ersatz fuer Inhalt.\n"
    "3. Der Volltext nennt die Begriffe mehrfach und unterschiedlich."
)


def _normalisiert(text: str) -> str:
    """Leerraum glaetten, damit reine Zeilenumbruch-/Einrueckungsunterschiede
    keinen falschen Treffer noch verhindern -- nicht mehr."""
    return " ".join((text or "").split())


def ist_blosse_verdopplung(alt_co: str, neu_co: str) -> bool:
    """Vierte Schranke: haengt der neue Volltext den KOMPLETTEN alten Volltext
    unveraendert an (Kontrollarm statt Umschrift), statt ihn umzuschreiben?

    VORFALL 2026-08-13 (L-a4f6dd): ein Agent sollte 20 Knoten umschreiben und
    haengte je Knoten den vollstaendigen alten Text unveraendert an eine neue
    Einleitung. Der Pruefstein (Sachverlust-Sieb) meldete 0 Beanstandungen --
    er KANN das nicht sehen, weil die alte Fassung Teilmenge der neuen ist:
    es fehlt ja nichts.

    MASS, mit Begruendung: woertliche Teilmenge des VOLLSTAENDIGEN alten
    Volltexts (nach Glaetten von Leerraum), nicht ein Anteilsmass (z.B. eine
    Aehnlichkeitsquote ueber Woerter/Zeichen). Grund: die Regeln erlauben und
    verlangen sogar, dass viele Saetze, Zitate, Zahlenreihen und Eigennamen
    woertlich stehen bleiben (Regel 3, Pruefstein-Zweck) -- ein Anteilsmass
    muesste dann eine Schwelle X% finden, die "viel woertlich uebernommen,
    aber umgeschrieben" von "alles woertlich angehaengt" trennt, und jede
    Schwelle < 100% laesst sich mit einem echten Umschreib-Los widerlegen,
    das zufaellig druebersteht. Die Teilmengenpruefung braucht keine Schwelle:
    sie fragt nur, ob der gesamte alte Text als zusammenhaengender Block noch
    irgendwo im neuen steckt.

    SCHWELLE = 100% des alten Volltexts, LUECKENLOS und AM STUECK.
    DURCHGELASSEN wird ausdruecklich: jede Umschrift, die den alten Text an
    irgendeiner Stelle unterbricht -- ein geloeschtes oder eingefuegtes Wort
    mitten im uebernommenen Absatz, eine andere Reihenfolge der Absaetze,
    ein einzelner veraenderter Traeger. Das ist gewollt: eine echte Umschrift,
    die ganze Saetze/Traeger unveraendert laesst (siehe negativfall unten),
    muss durchgehen -- nur die luecken- und ordnungslose Volltext-Kopie nicht.
    """
    alt_norm = _normalisiert(alt_co)
    neu_norm = _normalisiert(neu_co)
    if not alt_norm:
        return False
    return alt_norm in neu_norm


def auftrag_text(node_id: str, path: str) -> str:
    return (
        f"Schreibe Titel, Zusammenfassung und Volltext (Feld 'co') von Knoten "
        f"{node_id} ({path}) nach diesen drei Regeln neu:\n{REGELN}\n"
        "Erhalte dabei jede Zahl, jedes Datum, jede Kennung, jeden Pfad und "
        "jeden Eigennamen aus der Urfassung -- kern/umschrift_pruefstein.py "
        "prueft das maschinell und lehnt Verlust ab. Gib id unveraendert, "
        "title, summary und co zurueck."
    )


# --------------------------------------------------------------- Schritt 1
def kandidaten_unbehandelt(conn: sqlite3.Connection) -> list[str]:
    """Behandelte Knoten mit Urfassung, deren Titel UND Zusammenfassung noch
    wortgleich mit der Urfassung sind -- also noch nicht umgeschrieben.
    Sortiert nach id (stabile Reihenfolge, damit --ab reproduzierbar ist)."""
    ids = teilung_s12.bestand(conn)["knoten"]
    behandelt = sorted(i for i in ids if teilung_s12.haelfte("knoten", i) == teilung_s12.BEHANDELT)
    raus = []
    for node_id in behandelt:
        row = conn.execute(
            "SELECT title, summary FROM knowledge_nodes WHERE id = ?", (node_id,)
        ).fetchone()
        urf = conn.execute(
            "SELECT title, summary FROM s12_urfassungen WHERE node_id = ?", (node_id,)
        ).fetchone()
        if row is None or urf is None:
            continue  # ohne Urfassung nicht anbietbar -- s12_urfassungen-Wache meldet das separat
        if row["title"] == urf["title"] and row["summary"] == urf["summary"]:
            raus.append(node_id)
    return raus


def lose_erzeugen(conn: sqlite3.Connection, n: int, ab: int = 0) -> list[dict]:
    """Schritt 1: n noch unbehandelte Knoten (ab Position `ab`) samt fertigem
    Umschreibauftrag. n=0 liefert [] ohne Fehler."""
    kandidaten = kandidaten_unbehandelt(conn)[ab:ab + max(n, 0)]
    los = []
    for node_id in kandidaten:
        row = conn.execute(
            "SELECT path, title, summary, content FROM knowledge_nodes WHERE id = ?",
            (node_id,)).fetchone()
        los.append({
            "id": node_id, "path": row["path"], "title": row["title"],
            "summary": row["summary"], "co": row["content"],
            "auftrag": auftrag_text(node_id, row["path"]),
        })
    return los


# --------------------------------------------------------------- Schritt 3
def zurueckschreiben_alle(conn: sqlite3.Connection, alt_liste: list[dict],
                           neu_liste: list[dict], jetzt: str | None = None) -> dict:
    """Prueft jeden Knoten aus alt_liste gegen die vier Schranken und schreibt
    nur, was alle vier besteht. Meldet jede Ablehnung namentlich, in fuenf
    getrennten Zaehlern -- keiner darf stillschweigend verschwinden."""
    jetzt = jetzt or now_iso()
    neu_je_id = {r["id"]: r for r in neu_liste}
    ergebnis = {"geschrieben": [], "ohne_urfassung": [], "falsche_haelfte": [],
                "verdopplung_abgelehnt": [], "pruefstein_abgelehnt": []}

    for alt in alt_liste:
        node_id = alt["id"]

        if teilung_s12.haelfte("knoten", node_id) != teilung_s12.BEHANDELT:
            ergebnis["falsche_haelfte"].append(node_id)
            continue

        hat_urfassung = conn.execute(
            "SELECT 1 FROM s12_urfassungen WHERE node_id = ?", (node_id,)
        ).fetchone()
        if hat_urfassung is None:
            ergebnis["ohne_urfassung"].append(node_id)
            continue

        neu = neu_je_id.get(node_id)
        if neu is None:
            ergebnis["pruefstein_abgelehnt"].append(node_id)
            continue
        if ist_blosse_verdopplung(alt.get("co", ""), neu.get("co", "")):
            ergebnis["verdopplung_abgelehnt"].append(node_id)
            continue
        befund = pruefstein.pruefe_knoten(alt, neu)
        if not befund["ok"]:
            ergebnis["pruefstein_abgelehnt"].append(node_id)
            continue

        conn.execute(
            "UPDATE knowledge_nodes SET title = ?, summary = ?, content = ?, updated_at = ? "
            "WHERE id = ?",
            (neu["title"], neu["summary"], neu.get("co"), jetzt, node_id))
        ergebnis["geschrieben"].append(node_id)

    return ergebnis


# ---------------------------------------------------------------------- CLI
def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lose", metavar="AUS_DATEI")
    p.add_argument("--n", type=int, default=None)
    p.add_argument("--ab", type=int, default=0)
    p.add_argument("--zurueckschreiben", nargs=2, metavar=("ALT", "NEU"))
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return

    if a.lose:
        if a.n is None:
            p.error("--lose braucht --n")
        with speicher.lesen() as conn:
            los = lose_erzeugen(conn, a.n, a.ab)
        ziel = Path(a.lose)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(json.dumps(los, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Los: {len(los)} Knoten (n={a.n}, ab={a.ab}) -> {ziel}")
        return

    if a.zurueckschreiben:
        alt_pfad, neu_pfad = a.zurueckschreiben
        alt = json.loads(Path(alt_pfad).read_text(encoding="utf-8"))
        neu = json.loads(Path(neu_pfad).read_text(encoding="utf-8"))
        with speicher.schreiben() as conn:
            e = zurueckschreiben_alle(conn, alt, neu)
        print(f"geschrieben: {len(e['geschrieben'])}")
        print(f"abgelehnt ohne Urfassung: {len(e['ohne_urfassung'])} {e['ohne_urfassung']}")
        print(f"abgelehnt falsche Haelfte: {len(e['falsche_haelfte'])} {e['falsche_haelfte']}")
        print(f"abgelehnt Verdopplung: {len(e['verdopplung_abgelehnt'])} {e['verdopplung_abgelehnt']}")
        print(f"abgelehnt vom Pruefstein: {len(e['pruefstein_abgelehnt'])} {e['pruefstein_abgelehnt']}")
        return

    p.print_help()


# ------------------------------------------------------------------- Tests
def _insert_node(conn: sqlite3.Connection, node_id: str, path: str,
                  title: str, summary: str, content: str, jetzt: str) -> None:
    conn.execute(
        """INSERT INTO knowledge_nodes
           (id, path, parent_path, project_id, title, summary, content, level, tags, source,
            created_at, updated_at, norm_entscheidung,
            norm_entschieden_von, norm_entschieden_am, norm_entschieden_grund)
           VALUES (?, ?, '/', 'shared', ?, ?, ?, 1, '[]', ?, ?, ?, 'keine_norm', ?, ?, ?)""",
        (node_id, path, title, summary, content, node_id, jetzt, jetzt,
         "skript:umschrift_s12.py", jetzt, "Testvorrichtung fuer die Umschrift"),
    )


def _selftest() -> None:
    """Rot-vor-gruen auf einer tmp-Datenbank, keine echte Datei angefasst."""
    import tempfile
    import sicherung_s12

    tmp = _Path(tempfile.mkdtemp())
    db = tmp / "probe.db"
    schema_sql = (WURZEL / "schema.sql").read_text(encoding="utf-8")
    jetzt = "2026-08-13T08:00:00+02:00"

    kandidaten = [f"n-{i}" for i in range(60)]
    behandelt_ids = [k for k in kandidaten if teilung_s12.haelfte("knoten", k) == teilung_s12.BEHANDELT]
    unbehandelt_id = next(k for k in kandidaten if teilung_s12.haelfte("knoten", k) == teilung_s12.UNBEHANDELT)
    sauber_id, ohne_urf_id, defekt_id = behandelt_ids[0], behandelt_ids[1], behandelt_ids[2]

    with speicher.schreiben(db) as conn:
        conn.executescript(schema_sql)
        _insert_node(conn, sauber_id, "/x/sauber", "Alter Titel",
                     "Alte Zusammenfassung mit 8,50 USD.", "Volltext 8,50 USD.", jetzt)
        _insert_node(conn, ohne_urf_id, "/x/ohne-urfassung", "Titel B",
                     "Zusammenfassung B.", "Text B.", jetzt)
        _insert_node(conn, defekt_id, "/x/defekt", "Titel C",
                     "Zusammenfassung C mit 47 Prozent.", "Text C mit 47 Prozent.", jetzt)
        _insert_node(conn, unbehandelt_id, "/x/unbehandelt", "Titel D",
                     "Zusammenfassung D.", "Text D.", jetzt)
        # Urfassungen: sauber_id und defekt_id gesichert, ohne_urf_id absichtlich NICHT.
        conn.executescript(sicherung_s12.SCHEMA)
        for nid, path_, title, summary, content in (
            (sauber_id, "/x/sauber", "Alter Titel", "Alte Zusammenfassung mit 8,50 USD.", "Volltext 8,50 USD."),
            (defekt_id, "/x/defekt", "Titel C", "Zusammenfassung C mit 47 Prozent.", "Text C mit 47 Prozent."),
        ):
            conn.execute(
                "INSERT INTO s12_urfassungen (node_id, path, title, summary, content, gesichert_am) "
                "VALUES (?,?,?,?,?,?)", (nid, path_, title, summary, content, jetzt))

    # --- Schritt 1: --lose findet nur behandelte Knoten mit Urfassung, die
    # noch wortgleich mit ihr sind. ohne_urf_id fehlt (keine Urfassung),
    # unbehandelt_id fehlt (falsche Haelfte).
    with speicher.lesen(db) as conn:
        kand = kandidaten_unbehandelt(conn)
    assert set(kand) == {sauber_id, defekt_id}, kand
    with speicher.lesen(db) as conn:
        los_1 = lose_erzeugen(conn, 1, 0)
        los_0 = lose_erzeugen(conn, 0, 0)
    assert len(los_1) == 1, "Grenzwert --n 1 muss genau einen Knoten liefern"
    assert los_0 == [], "Grenzwert --n 0 muss leer sein, kein Fehler"
    for eintrag in los_1:
        assert "1. Der Titel benennt die Sache" in eintrag["auftrag"]
        assert "2. Die Zusammenfassung traegt" in eintrag["auftrag"]
        assert "3. Der Volltext nennt" in eintrag["auftrag"]

    with speicher.lesen(db) as conn:
        alt_liste = lose_erzeugen(conn, 10, 0)
    alt_je_id = {r["id"]: r for r in alt_liste}

    # --- Schritt 3, vier Faelle -----------------------------------------
    # 1) sauber_id: hat Urfassung, ist behandelt, Pruefstein besteht -> geschrieben.
    neu_sauber = dict(alt_je_id[sauber_id],
                       title="Wer 8,50 USD zahlt (neu formuliert)",
                       summary="Alte Zusammenfassung mit 8,50 USD, neu formuliert.",
                       co="Volltext 8,50 USD, neu formuliert.")
    # 2) ohne_urf_id: KEINE Urfassung -> abgelehnt, obwohl der Rest sauber waere.
    neu_ohne_urf = {"id": ohne_urf_id, "title": "Neuer Titel B",
                     "summary": "Neue Zusammenfassung B.", "co": "Neuer Text B."}
    # 3) unbehandelt_id: falsche Haelfte -> abgelehnt.
    neu_unbehandelt = {"id": unbehandelt_id, "title": "Neuer Titel D",
                        "summary": "Neue Zusammenfassung D.", "co": "Neuer Text D."}
    # 4) defekt_id: eine Zahl (47 Prozent) verschwindet -> Pruefstein lehnt ab.
    neu_defekt = dict(alt_je_id[defekt_id], summary="Zusammenfassung C.", co="Text C.")

    alt_input = [alt_je_id[sauber_id], {"id": ohne_urf_id}, {"id": unbehandelt_id}, alt_je_id[defekt_id]]
    neu_input = [neu_sauber, neu_ohne_urf, neu_unbehandelt, neu_defekt]

    with speicher.schreiben(db) as conn:
        e = zurueckschreiben_alle(conn, alt_input, neu_input, jetzt)

    assert e["geschrieben"] == [sauber_id], e["geschrieben"]
    assert e["ohne_urfassung"] == [ohne_urf_id], e["ohne_urfassung"]
    assert e["falsche_haelfte"] == [unbehandelt_id], e["falsche_haelfte"]
    assert e["pruefstein_abgelehnt"] == [defekt_id], e["pruefstein_abgelehnt"]

    # Negativfall gegen alle drei Schranken zugleich: nur der eine saubere
    # Knoten wurde tatsaechlich in der DB veraendert.
    with speicher.lesen(db) as conn:
        row = conn.execute("SELECT title FROM knowledge_nodes WHERE id=?", (sauber_id,)).fetchone()
        row_c = conn.execute("SELECT title FROM knowledge_nodes WHERE id=?", (ohne_urf_id,)).fetchone()
        row_d = conn.execute("SELECT title FROM knowledge_nodes WHERE id=?", (defekt_id,)).fetchone()
    assert row["title"] == "Wer 8,50 USD zahlt (neu formuliert)"
    assert row_c["title"] == "Titel B", "abgelehnter Knoten (ohne Urfassung) wurde trotzdem geschrieben"
    assert row_d["title"] == "Titel C", "abgelehnter Knoten (Pruefstein) wurde trotzdem geschrieben"

    # --- Wiederaufnahme: sauber_id ist jetzt umgeschrieben (Titel/Summary
    # weichen von der Urfassung ab) und darf in einem zweiten --lose-Aufruf
    # nicht mehr auftauchen. defekt_id blieb unveraendert (abgelehnt) und
    # taucht darum weiter auf.
    with speicher.lesen(db) as conn:
        kand_2 = kandidaten_unbehandelt(conn)
    assert sauber_id not in kand_2, "umgeschriebener Knoten taucht erneut auf"
    assert defekt_id in kand_2, "abgelehnter (unveraenderter) Knoten fehlt zu Unrecht"

    print("selftest ok (Grenzwerte, fuenf Ablehnungsklassen, Negativfall, "
          "Wiederaufnahme ohne Zusatzdatei)", file=_sys.stderr)


if __name__ == "__main__":
    main()
