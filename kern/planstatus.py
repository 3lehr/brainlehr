#!/usr/bin/env python3
"""Ablage fuer ERLEDIGUNG eines Planabschnitts -- getrennt von der Ablage fuer
ENTSCHEIDUNG, die `planentscheidung.py` schon hat.

Anlass (Auftrag 2026-08-15): `planentscheidung.py` legt aus ENTSCHEIDENDEN
Planabschnitten Knoten an und schreibt eine Kennung zurueck. Das Wort
"erledigt" kommt in seinem Modulkopf genau einmal vor, in einem Kommentar --
kein Feld, kein Uebergang, kein Weg, ihn zu setzen. Folge, am 2026-08-15
gemessen: der Fortschritt wurde aus dem FLIESSTEXT von
docs/PLAN_GESAMT_2026-08-13.md gelesen und aus `git log` geraten. Ergebnis:
fuenf Agenten auf bereits Gebautes angesetzt, `82`/`83`/`87` als
Phantomzeilen gefuehrt, `H2`-`H7` faelschlich als erledigt in STAND.md.

WO DER STATUS LIEGT (Frage 1 des Auftrags, gegen den Bestand gemessen): NICHT
als vierte Spalte an knowledge_nodes -- `abgeleitet_von` (1/2217, 0,0%) und
`norm_entschieden_belegart` (0/2217, 0,0%) sind schon heute faktisch leere
Spalten, siehe schema.sql. Auch NICHT als Kante in knowledge_relations: ein
Status ist keine Beziehung zwischen zwei Knoten, sondern eine Aussage UEBER
einen -- eine Kante als Eigenschlaufe (source_path == target_path) waere eine
Verbiegung des Kantenbegriffs, nur um eine dritte Struktur zu vermeiden.
Gewaehlt: eine eigene Tabelle `plan_status` (schema.sql), 1:1 an einen
Planknoten aus planentscheidung.py gebunden -- Details und die sechs
gemessenen Zustaende (plus 'unbelegt', Antwort auf Frage 3) stehen dort im
Tabellenkommentar, nicht hier verdoppelt.

WORTLISTE FUER DIE ERKENNUNG, gleiche Bauform wie `planentscheidung.
ist_entscheidend()` und aus demselben Grund gegen den Plantext gemessen statt
angenommen: kein Wortkatalog erreicht Praezision und Trefferquote zugleich
(siehe dortiger Modulkopf) -- darum ist `--vorschlag` vor `--schreiben` auch
hier Pflicht, nicht Kuer, und die Erkennung schreibt NIE direkt, nur bis zum
naechsten `--schreiben`-Lauf. Die sechs Muster unten sind woertlich an
docs/PLAN_GESAMT_2026-08-13.md gemessen (nur gelesen, Datei bleibt tabu):
  'phantom'             -- "keine eigene Definition gefunden" (`82`,`83`,`87`,`23`)
  'gebaut_wirkungslos'  -- "gebaut, aber wirkungslos" (`73`,`79`, eigene
                            Kategorie seit der Fortschreibung 13:50 Uhr)
  'nicht_nachgemessen'  -- "nicht nachgemessen" (`G3`,`G6`,`F8`)
  'teilweise'           -- "bleibt teilweise, nicht erledigt" (`73`,`79` vor
                            der eigenen Kategorie)
  'erledigt'            -- "sind erledigt" (`F1`-`F4`), MIT der Verneinung
                            "nicht erledigt" ausdruecklich ausgeschlossen
  'offen'               -- "echt offen, kein Commit-Beleg gefunden" (`H2`-`H7`)

WAS DIE HEURISTIK NICHT KANN, und warum es trotzdem einen manuellen Weg gibt:
`H5` galt am 2026-08-15 als erledigt, obwohl der Fliesstext `H2`-`H7`
kollektiv als offen fuehrt ("Keine neue Schaetzung fuer H2-H7"). Eine
Sammelaussage ueber sieben Kennungen aus einer einzelnen wieder aufzuloesen
ist kein Regex-Problem, sondern eine Frage, die nur ein Mensch beantwortet --
darum gibt es --kennung/--status/--beleg-art/--beleg als expliziten,
menschlich gesetzten Weg NEBEN der Batch-Erkennung, nicht als Ersatz dafuer.
Frage 3 des Auftrags ("wer setzt ihn") hat also zwei Antworten: die
Heuristik SCHLAEGT VOR (nur bis --schreiben), der Mensch UEBERSCHREIBT dort,
wo die Heuristik falsch liegt.

REICHWEITE, NACHTRAG 2026-08-15 (Betreiber: "erzaehl mir nichts von
Einschraenkungen sondern loese diese auf"): Erste Fassung dieses Moduls
erreichte nur die 12 von 39 `source LIKE '%PLAN_%'`-Knoten, die
planentscheidung.py selbst angelegt hatte -- der Batch-Weg brauchte die
`*Kennung: ...*`-Zeile in der Plandatei, um von dort zum Knoten zu finden.
Unnoetige Voraussetzung: **jeder Knoten hat schon eine eigene id und einen
path** -- der Status haengt am Knoten, nicht am Plantext, und die
Kennungszeile existiert nur, damit `planbindung.py` die GEGENRICHTUNG
(Datei -> Knoten) pruefen kann. `verarbeiten_knoten()` unten dreht die
Richtung um: SELECT direkt auf `knowledge_nodes` (`source LIKE '%PLAN_%'`,
ohne planentscheidung.py-Herkunft, ohne Astknoten), Status/Beleg aus
Titel+Summary+Content des KNOTENS SELBST erkannt (dieselben Muster wie
oben -- die Abschnittsprosa ist bei diesen 27 identisch mit dem
Knoteninhalt, es gibt keine zweite Kopie in einer Datei). Woran man erkennt,
WELCHER Abschnitt ein Knoten ist, wenn keine Kennungszeile existiert: der
freie `source`-Text nennt fast immer die Plandatei und haeufig einen
Abschnitts-/Schritt-/Paragraph-/Zeilenverweis (`_quelle_aus_source()`,
gegen alle 27 gemessen: 13 mit Feinverweis, Rest faellt ehrlich auf die
eigene 8-stellige id zurueck -- keine erfundene Praezision). Gemessen am
2026-08-15: von den 39 Knoten werden so 37 vom Batch-Weg erreicht (12 ueber
Abschnitte + 25 ueber Knoten direkt), 2 bleiben aussen vor -- `/plaene` und
`/plaene/plan-destille-2026-08-09`, reine Astknoten ohne eigenen Volltext
(`content=''` bzw. woertlich "ein eigener Volltext liegt nicht vor"), also
strukturell ohne jede Entscheidungsprosa, an der ein Status haengen koennte.

Aufruf:
    python3 planstatus.py --vorschlag DATEI   # Batch-Trockenlauf ueber alle gebundenen Abschnitte EINER Datei
    python3 planstatus.py --schreiben DATEI   # Batch-Schreiblauf, dieselbe Datei
    python3 planstatus.py --vorschlag-bestand   # Batch-Trockenlauf ueber ALLE PLAN_-Knoten der DB (kein Dateizugriff)
    python3 planstatus.py --schreiben-bestand   # Batch-Schreiblauf, DB-weit
    python3 planstatus.py --vorschlag DATEI --kennung S2 --status erledigt \\
        --beleg-art commit --beleg 46d96bc3   # gezielter Trockenlauf auf EINEM Abschnitt
    python3 planstatus.py --schreiben DATEI --kennung S2 --status erledigt \\
        --beleg-art commit --beleg 46d96bc3   # gezielter Schreiblauf
    python3 planstatus.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql, wie alle Geschwister-Skripte hier.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import argparse
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import planbindung     # reuse: _abschnitte(), _existiert(), _vorhandene_ids()
import planentscheidung  # reuse: _abschnitt_positionen(), _bestehende_kennung(), _fremd_gebunden()

WURZEL = _w

STATUS_WERTE = (
    "offen", "teilweise", "gebaut_wirkungslos",
    "nicht_nachgemessen", "phantom", "erledigt", "unbelegt",
)
_BELEGPFLICHTIG = {"erledigt", "gebaut_wirkungslos"}  # schema.sql erzwingt das gleiche am Trigger.

# Reihenfolge ist die Erkennungsreihenfolge -- erster Treffer gewinnt (gleiche
# Bauform wie planentscheidung._ENTSCHEIDEND_RE, siehe dortiger Modulkopf fuer
# die Begruendung, warum ein Wortkatalog priorisiert werden muss). 'phantom'
# und 'gebaut_wirkungslos' zuerst, weil ihre Formulierungen sonst von den
# allgemeineren Mustern ('teilweise', 'erledigt') verschluckt wuerden --
# "gebaut, aber wirkungslos" enthaelt kein Trigger-Wort von 'teilweise', aber
# ein Text, der ZUSAETZLICH "teilweise" nennt, soll trotzdem als das
# praezisere gebaut_wirkungslos gelten.
_STATUS_MUSTER: list[tuple[str, re.Pattern]] = [
    ("phantom", re.compile(
        r"keine eigene Definition gefunden|nur als Sammelnennung|\bphantom\b", re.IGNORECASE)),
    ("gebaut_wirkungslos", re.compile(
        r"gebaut,?\s+(?:aber|und)\s+wirkungslos", re.IGNORECASE)),
    ("nicht_nachgemessen", re.compile(
        r"nicht nachgemessen|nicht erneut gepr[üu]ft|\bungemessen\b", re.IGNORECASE)),
    ("teilweise", re.compile(r"\bteilweise\b", re.IGNORECASE)),
    ("erledigt", re.compile(
        r"(?<!nicht )\berledigt\b|rot[- ]vor[- ]gr[üu]n belegt", re.IGNORECASE)),
    ("offen", re.compile(r"\boffen\b|wartet auf den Betreiber", re.IGNORECASE)),
]

# Belegmuster, absteigend nach Aussagekraft: ein Testname ist der staerkste
# Beleg (rot-vor-gruen selbst), ein zitierter Commit der zweitstaerkste, ein
# runs/-Pfad (Messdatei) der schwaechste, aber noch nachpruefbare. Reine
# Quelldateien (*.py) zaehlen bewusst NICHT als Beleg -- sie nennen, WAS
# geaendert wurde, nicht, dass es WIRKT (siehe `73`: die Datei existiert,
# der Beleg fuer "wirkungslos" ist trotzdem die Zahl der Kanten am echten
# Bestand, hier ueber den zitierten Commit erfasst, nicht ueber den Dateinamen).
_BELEG_TEST_RE = re.compile(r"\b(test_[a-zA-Z0-9_]+)\b")
_BELEG_COMMIT_RE = re.compile(r"`([0-9a-f]{7,8})`")
_BELEG_MESSDATEI_RE = re.compile(r"\bruns/[\w./-]+")


def _erkenne_status(text: str) -> str | None:
    for name, muster in _STATUS_MUSTER:
        if muster.search(text):
            return name
    return None


def _erkenne_beleg(text: str) -> tuple[str | None, str | None]:
    m = _BELEG_TEST_RE.search(text)
    if m:
        return "test", m.group(1)
    m = _BELEG_COMMIT_RE.search(text)
    if m:
        return "commit", m.group(1)
    m = _BELEG_MESSDATEI_RE.search(text)
    if m:
        return "messdatei", m.group(0)
    return None, None


def _node_path(conn, kennung: str) -> str | None:
    row = conn.execute(
        "SELECT path FROM knowledge_nodes WHERE id LIKE ?", (f"{kennung}%",)
    ).fetchone()
    return row[0] if row else None


# Feinverweis innerhalb einer Plandatei, WENN source ihn nennt -- "Abschnitt
# 6", "Schritt 6", "§10", "Zeile 76". Bestmoeglich, nicht erzwungen: fehlt er,
# faellt _quelle_aus_source() auf die Knoten-id zurueck (siehe dort).
_ABSCHNITT_REF_RE = re.compile(
    r"(Abschnitt\s+\S+|Schritt\s+\d+[a-z]?|§\s?\d+[a-z]?|Zeile\s+\d+)", re.IGNORECASE)
_MD_DATEI_RE = re.compile(r"[\w./-]+\.md")


def _quelle_aus_source(source: str, node_id: str) -> tuple[str, str]:
    """(datei, kennung) aus dem freien `source`-Text eines Knotens ohne
    Kennungszeile -- siehe Modulkopf "REICHWEITE, NACHTRAG 2026-08-15". Kein
    Abgleich gegen eine Plandatei (die bleibt tabu/ungelesen fuer diesen
    Pfad) -- nur Text, den der Knoten selbst schon traegt."""
    source = source or ""
    dateien = _MD_DATEI_RE.findall(source)
    datei = next((d for d in dateien if "plan" in d.lower()), dateien[0] if dateien else "unbekannt")
    treffer = _ABSCHNITT_REF_RE.search(source)
    kennung = treffer.group(1) if treffer else node_id[:8]
    return datei, kennung


def _bestehende_kennung(zeilen: list[str], start: int, ende: int, ab_text: str, ids: list[str]) -> str | None:
    block = zeilen[start:ende]
    return planentscheidung._bestehende_kennung(block) or planentscheidung._fremd_gebunden(ab_text, ids)


@dataclass
class Bericht:
    kennung: str
    titel: str
    status: str | None
    beleg_art: str | None
    beleg: str | None
    aktion: str  # "gesetzt"|"fortgeschrieben"|"unveraendert"|"wuerde_setzen"|
                 # "kennung_fehlt"|"phantom_ziel"|"kein_status_erkannt"


def _setzen(conn, kms, node_path: str, datei_name: str, kennung: str,
            status: str, beleg_art: str | None, beleg: str | None) -> str:
    """Upsert -- ein Knoten traegt genau EINE aktuelle Statuszeile (siehe
    schema.sql: node_path UNIQUE). Idempotent wie planentscheidung.py:
    gleicher Inhalt schreibt nicht neu."""
    row = conn.execute(
        "SELECT status, beleg_art, beleg FROM plan_status WHERE node_path = ?", (node_path,)
    ).fetchone()
    akteur = kms._identity()[0]
    jetzt = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    if row is None:
        conn.execute(
            """INSERT INTO plan_status
               (id, node_path, quelle_datei, quelle_kennung, status, beleg_art, beleg, gesetzt_von, gesetzt_am)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (f"PST-{uuid.uuid4().hex[:8]}", node_path, datei_name, kennung, status, beleg_art, beleg, akteur, jetzt),
        )
        conn.commit()
        return "gesetzt"
    if (row["status"], row["beleg_art"], row["beleg"]) == (status, beleg_art, beleg):
        return "unveraendert"
    conn.execute(
        """UPDATE plan_status SET status=?, beleg_art=?, beleg=?, gesetzt_von=?, gesetzt_am=?,
           quelle_datei=?, quelle_kennung=? WHERE node_path=?""",
        (status, beleg_art, beleg, akteur, jetzt, datei_name, kennung, node_path),
    )
    conn.commit()
    return "fortgeschrieben"


def _abgesichert(status: str, beleg_art: str | None, beleg: str | None) -> str:
    """Negativfall des Auftrags: 'erledigt'/'gebaut_wirkungslos' ohne Beleg
    ist 'unbelegt', nicht 'erledigt' -- Python-seitig VOR jedem Schreiben
    entschaerft, der DB-Trigger in schema.sql ist die zweite, unabhaengige
    Schranke fuer einen Schreiber, der diese Funktion nicht durchlaeuft
    (z.B. --kennung-Weg direkt aufgerufen ohne main())."""
    if status in _BELEGPFLICHTIG and not (beleg_art and beleg and beleg.strip()):
        return "unbelegt"
    return status


# ---------------------------------------------------------------------------
# Batch: alle Abschnitte einer Datei, die bereits eine Kennung tragen.
# ---------------------------------------------------------------------------

def verarbeiten(kms, conn, datei: Path, schreiben: bool) -> list[Bericht]:
    zeilen = datei.read_text(encoding="utf-8").splitlines()
    positionen = planentscheidung._abschnitt_positionen(zeilen)
    abschnitte = planbindung._abschnitte(datei)
    assert len(positionen) == len(abschnitte), "Positions- und Textliste muessen 1:1 uebereinstimmen"

    ids = planbindung._vorhandene_ids(conn)
    berichte: list[Bericht] = []

    for (start, ende, kennung, titel), ab in zip(positionen, abschnitte):
        bestehende = _bestehende_kennung(zeilen, start, ende, ab.text, ids)
        if not bestehende:
            # Grenzwert "Abschnitt ohne Kennung": planentscheidung.py laeuft
            # hier noch nicht -- kein Status ohne Knoten.
            berichte.append(Bericht(kennung, titel, None, None, None, "kennung_fehlt"))
            continue
        if not planbindung._existiert(bestehende, ids):
            # Grenzwert "Kennung ohne Abschnitt" (hier umgekehrt: die
            # gebundene Kennung zeigt auf keinen echten Knoten mehr).
            berichte.append(Bericht(kennung, titel, None, None, bestehende, "phantom_ziel"))
            continue

        # OHNE die eigene Kennungszeile: sie traegt selbst eine 8-stellige
        # Hexfolge in Backticks und wuerde sonst von _BELEG_COMMIT_RE als
        # (falscher) Beleg gelesen -- derselbe Grund wie planentscheidung.
        # _ohne_kennungszeile() beim Fortschreibungsvergleich.
        prosa = planentscheidung._ohne_kennungszeile(ab.text)
        status = _erkenne_status(prosa)
        if status is None:
            berichte.append(Bericht(kennung, titel, None, None, bestehende, "kein_status_erkannt"))
            continue
        beleg_art, beleg = _erkenne_beleg(prosa)
        status = _abgesichert(status, beleg_art, beleg)

        node_path = _node_path(conn, bestehende)
        if node_path is None:
            berichte.append(Bericht(kennung, titel, status, beleg_art, bestehende, "phantom_ziel"))
            continue

        if not schreiben:
            berichte.append(Bericht(kennung, titel, status, beleg_art, beleg, "wuerde_setzen"))
            continue
        aktion = _setzen(conn, kms, node_path, datei.name, kennung, status, beleg_art, beleg)
        berichte.append(Bericht(kennung, titel, status, beleg_art, beleg, aktion))

    return berichte


# ---------------------------------------------------------------------------
# Batch, DB-weit: Knoten OHNE Kennungszeile -- siehe Modulkopf "REICHWEITE,
# NACHTRAG 2026-08-15". Kein Dateizugriff, docs/ bleibt unberuehrt.
# ---------------------------------------------------------------------------

# planentscheidung.py-Knoten laufen bereits ueber verarbeiten() (Datei- statt
# DB-Weg) -- ausgeschlossen, damit ein Knoten nicht ueber zwei Wege
# gleichzeitig, mit potenziell widerspruechlicher quelle_kennung, beschrieben
# wird. Astknoten (kms.knowledge_add(neuer_ast=True) erzeugt Platzhalter mit
# der woertlichen Signatur "neuer_ast=True, automatisch erzeugt durch ..." in
# source, siehe knowledge_mcp_server.py) tragen keinen eigenen Volltext --
# generisch ausgeschlossen statt an den zwei heute betroffenen Pfaden
# festgemacht, damit ein spaeterer dritter Astknoten nicht erneut lautlos in
# "kein_status_erkannt" laeuft.
_KNOTEN_BESTAND_SQL = """
    SELECT id, path, title, summary, content, source FROM knowledge_nodes
    WHERE source LIKE :muster
      AND source NOT LIKE '%planentscheidung.py%'
      AND source NOT LIKE 'neuer_ast=True%'
"""


def verarbeiten_knoten(kms, conn, schreiben: bool, muster: str = "%PLAN_%") -> list[Bericht]:
    zeilen = conn.execute(_KNOTEN_BESTAND_SQL, {"muster": muster}).fetchall()
    berichte: list[Bericht] = []
    for row in zeilen:
        text = " ".join(t for t in (row["title"], row["summary"], row["content"]) if t)
        status = _erkenne_status(text)
        datei, kennung = _quelle_aus_source(row["source"], row["id"])
        if status is None:
            berichte.append(Bericht(kennung, row["title"], None, None, None, "kein_status_erkannt"))
            continue
        beleg_art, beleg = _erkenne_beleg(text)
        status = _abgesichert(status, beleg_art, beleg)

        if not schreiben:
            berichte.append(Bericht(kennung, row["title"], status, beleg_art, beleg, "wuerde_setzen"))
            continue
        aktion = _setzen(conn, kms, row["path"], datei, kennung, status, beleg_art, beleg)
        berichte.append(Bericht(kennung, row["title"], status, beleg_art, beleg, aktion))
    return berichte


# ---------------------------------------------------------------------------
# Manuell: EIN Abschnitt, vom Menschen benannt -- fuer die Faelle, die die
# Heuristik nicht (mehr korrekt) lesen kann, siehe Modulkopf ("H5").
# ---------------------------------------------------------------------------

def setzen_manuell(kms, conn, datei: Path, kennung_ziel: str, status: str,
                    beleg_art: str | None, beleg: str | None, schreiben: bool) -> Bericht:
    if status not in STATUS_WERTE:
        raise ValueError(f"unbekannter Status {status!r} -- erlaubt sind {', '.join(STATUS_WERTE)}")

    zeilen = datei.read_text(encoding="utf-8").splitlines()
    positionen = planentscheidung._abschnitt_positionen(zeilen)
    abschnitte = planbindung._abschnitte(datei)
    treffer = [(pos, ab) for pos, ab in zip(positionen, abschnitte) if pos[2] == kennung_ziel]

    if not treffer:
        # Grenzwert "Status auf einen Abschnitt, der gar nicht existiert".
        raise ValueError(f"Kennung {kennung_ziel!r} kommt in {datei.name} nicht vor -- kein Ziel fuer einen Status.")
    if len(treffer) > 1:
        # Grenzwert "zwei Abschnitte mit derselben Kennung" -- lieber
        # ablehnen als raten, welcher der beiden gemeint ist.
        raise ValueError(
            f"Kennung {kennung_ziel!r} kommt {len(treffer)}x in {datei.name} vor -- mehrdeutig, "
            "kein automatisches Ziel (Grenzfall PLAN_DESTILLE_2026-08-09.md: 'S12' zweimal)."
        )

    (start, ende, kennung, titel), ab = treffer[0]
    ids = planbindung._vorhandene_ids(conn)
    bestehende = _bestehende_kennung(zeilen, start, ende, ab.text, ids)
    if not bestehende:
        raise ValueError(f"{kennung_ziel} hat noch keine Kennung -- erst planentscheidung.py --schreiben laufen lassen.")
    if not planbindung._existiert(bestehende, ids):
        raise ValueError(f"{kennung_ziel} nennt Kennung {bestehende}, die es in der DB nicht (mehr) gibt (Phantom).")

    status = _abgesichert(status, beleg_art, beleg)
    node_path = _node_path(conn, bestehende)

    if not schreiben:
        return Bericht(kennung, titel, status, beleg_art, beleg, "wuerde_setzen")
    aktion = _setzen(conn, kms, node_path, datei.name, kennung, status, beleg_art, beleg)
    return Bericht(kennung, titel, status, beleg_art, beleg, aktion)


def _drucken(kopf_name: str, berichte: list[Bericht], schreiben: bool) -> None:
    kopf = "SCHREIBLAUF" if schreiben else "TROCKENLAUF (--vorschlag, nichts geschrieben)"
    print(f"\n== {kopf_name} -- {kopf} ==")
    for b in berichte:
        status = b.status or "-"
        beleg = f" beleg={b.beleg_art}:{b.beleg}" if b.beleg_art else (f" ziel={b.beleg}" if b.beleg else "")
        print(f"  {b.aktion:20} {b.kennung:6} {status:20} {b.titel[:45]}{beleg}")
    zaehl: dict[str, int] = {}
    for b in berichte:
        zaehl[b.aktion] = zaehl.get(b.aktion, 0) + 1
    print("  --")
    print("  " + ", ".join(f"{k}={v}" for k, v in sorted(zaehl.items())))


def _lauf(datei: Path, schreiben: bool, kennung: str | None, status: str | None,
          beleg_art: str | None, beleg: str | None) -> list[Bericht]:
    import knowledge_mcp_server as kms  # lazy: DB_PATH wird erst beim Import fixiert
    conn = kms.get_db()
    try:
        if kennung:
            berichte = [setzen_manuell(kms, conn, datei, kennung, status, beleg_art, beleg, schreiben)]
        else:
            berichte = verarbeiten(kms, conn, datei, schreiben)
    finally:
        conn.close()
    _drucken(datei.name, berichte, schreiben)
    return berichte


def _lauf_bestand(schreiben: bool) -> list[Bericht]:
    import knowledge_mcp_server as kms
    conn = kms.get_db()
    try:
        berichte = verarbeiten_knoten(kms, conn, schreiben)
    finally:
        conn.close()
    _drucken("DB-Bestand (source LIKE '%PLAN_%', ohne planentscheidung.py/Astknoten)", berichte, schreiben)
    return berichte


# ---------------------------------------------------------------------------
# Selbsttest -- eigene Beispieldatei, eigene temporaere DB.
# ---------------------------------------------------------------------------

def _selftest() -> None:
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        plan = tmp / "PLAN_TEST.md"
        plan.write_text(
            "# Testplan\n\n"
            "### S1 · gebaut, aber wirkungslos, mit Beleg\n"
            "Verworfen wurde nichts. Bindend: der Mechanismus (`46d96bc3`) ist gebaut, aber "
            "wirkungslos, weil am echten Bestand 0 Kanten stehen.\n\n"
            "### S2 · Phantom, keine eigene Definition\n"
            "Entscheidung: diese Kennung ist nur als Sammelnennung im Plan genannt, keine eigene "
            "Definition gefunden.\n\n"
            "### S3 · erledigt mit Testbeleg\n"
            "Beschlossen: fertig. Rot-vor-gruen mit test_beispiel_laeuft_durch belegt, sind erledigt.\n\n"
            "### S4 · behauptet erledigt, ohne jeden Beleg\n"
            "Vorgabe ist: dieser Punkt ist erledigt. Bindend so beschlossen.\n\n"
            "### S1 · zweite Ueberschrift mit dem Label S1, echtes Duplikat\n"
            "Verworfen wurde die erste Fassung. Bindend: auch dieser zweite Mechanismus "
            "(`46d96bc3`) ist gebaut, aber wirkungslos.\n",
            encoding="utf-8",
        )

        db_pfad = tmp / "test.db"
        os.environ["BEGOD_KNOWLEDGE_DB"] = str(db_pfad)  # knowledge_mcp_server.DB_PATH liest NUR
                                                          # diesen Namen, siehe planentscheidung.py
                                                          # Selbsttest fuer dieselbe Anmerkung.
        for name in ("knowledge_mcp_server",):
            sys.modules.pop(name, None)
        import knowledge_mcp_server as kms

        conn = kms.get_db()

        # ROT: vor dem Bau existierte plan_status nicht -- ein INSERT waere
        # mit "no such table: plan_status" abgebrochen (woertlich, nicht
        # reproduzierbar ohne den fertigen Code/Schema zu entfernen). Ab hier
        # die GRUEN-Probe.

        # --- Vorbereitung: planentscheidung.py bindet die vier S1..S4-Abschnitte an Knoten ---
        planentscheidung.verarbeiten(kms, conn, plan, schreiben=True)
        # S1 kommt zweimal vor -- planentscheidung.py bindet BEIDE Vorkommen einzeln (verschiedene
        # Titel -> verschiedene Slugs -> verschiedene node_path), das ist die Grundlage fuer den
        # Duplikat-Grenzfall unten.
        s1_knoten = conn.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE path LIKE '/plaene/plan-test/%s1%'").fetchone()[0]
        assert s1_knoten == 2, f"Vorbedingung verletzt: planentscheidung.py haette 2 S1-Knoten binden muessen, hat {s1_knoten}"

        # --- Trockenlauf: nichts geschrieben ------------------------------------------------
        vor = plan.read_text(encoding="utf-8")
        berichte = verarbeiten(kms, conn, plan, schreiben=False)
        nach = plan.read_text(encoding="utf-8")
        assert vor == nach, "Trockenlauf haette die Datei nicht anfassen duerfen"
        arten = {b.kennung + "#" + str(i): b for i, b in enumerate(berichte)}
        anzahl_leer = conn.execute("SELECT COUNT(*) FROM plan_status").fetchone()[0]
        assert anzahl_leer == 0, "Trockenlauf haette keine Statuszeile anlegen duerfen"
        print("Pflichtfall a (Trockenlauf schreibt nichts): bestanden")

        # --- Die drei echten Faelle des Tages: 73/79 (gebaut_wirkungslos+Beleg), 82 (phantom) ---
        s1_bericht = [b for b in berichte if b.kennung == "S1"]
        assert len(s1_bericht) == 2, f"erwartet 2 S1-Berichte (Duplikat), bekommen {len(s1_bericht)}"
        assert all(b.status == "gebaut_wirkungslos" for b in s1_bericht), \
            f"S1 (`73`/`79`-Analogon) haette gebaut_wirkungslos erkennen muessen: {[b.status for b in s1_bericht]}"
        assert all(b.beleg_art == "commit" and b.beleg == "46d96bc3" for b in s1_bericht), \
            f"S1 haette den zitierten Commit als Beleg erkennen muessen: {[(b.beleg_art, b.beleg) for b in s1_bericht]}"

        s2_bericht = next(b for b in berichte if b.kennung == "S2")
        assert s2_bericht.status == "phantom", f"S2 (`82`-Analogon) haette phantom sein muessen, war {s2_bericht.status}"
        print("Pflichtfall b (die drei echten Tagesfaelle: gebaut_wirkungslos+Beleg, phantom): bestanden")

        # --- Negativfall: Status ohne Beleg ist 'unbelegt', nicht 'erledigt' ------------------
        s4_bericht = next(b for b in berichte if b.kennung == "S4")
        assert s4_bericht.status == "unbelegt", \
            f"S4 (erledigt-Behauptung ohne Beleg) haette zu unbelegt herabgestuft werden muessen, war {s4_bericht.status}"
        print("Pflichtfall c (Negativfall: Status ohne Beleg wird unbelegt, nicht erledigt): bestanden")

        # --- Schreiblauf, dann Idempotenz -----------------------------------------------------
        berichte1 = verarbeiten(kms, conn, plan, schreiben=True)
        assert all(b.aktion in ("gesetzt",) for b in berichte1 if b.status is not None), \
            f"erster Schreiblauf haette alles neu setzen muessen: {[(b.kennung, b.aktion) for b in berichte1]}"
        anzahl1 = conn.execute("SELECT COUNT(*) FROM plan_status").fetchone()[0]
        assert anzahl1 == 5, f"erwartet 5 Statuszeilen (S1x2, S2, S3, S4), bekommen {anzahl1}"

        berichte2 = verarbeiten(kms, conn, plan, schreiben=True)
        assert all(b.aktion in ("unveraendert",) for b in berichte2 if b.status is not None), \
            f"zweiter Lauf haette alles unveraendert lassen muessen: {[(b.kennung, b.aktion) for b in berichte2]}"
        anzahl2 = conn.execute("SELECT COUNT(*) FROM plan_status").fetchone()[0]
        assert anzahl2 == 5, f"zweiter Lauf haette KEINE neuen Zeilen anlegen duerfen, hat jetzt {anzahl2}"
        print("Pflichtfall d (Schreiblauf, dann idempotent unveraendert): bestanden")

        # --- DB-Trigger direkt: 'erledigt' ohne Beleg ist an der Datenbank unmoeglich, nicht
        # nur in dieser Funktion (Verteidigungslinie 2, siehe Modulkopf). --------------------
        import sqlite3 as _sqlite3
        try:
            conn.execute(
                """INSERT INTO plan_status (id, node_path, quelle_datei, quelle_kennung, status,
                   beleg_art, beleg, gesetzt_von, gesetzt_am)
                   VALUES ('PST-zzzzzzzz', (SELECT path FROM knowledge_nodes LIMIT 1),
                   'x.md', 'X1', 'erledigt', NULL, NULL, 'test', '2026-01-01T00:00:00+00:00')"""
            )
            conn.rollback()
            raise AssertionError("DB-Trigger haette 'erledigt' ohne Beleg verhindern muessen")
        except _sqlite3.IntegrityError as exc:
            assert "unbelegt" in str(exc)
            conn.rollback()
        print("Pflichtfall e (DB-Trigger blockiert 'erledigt' ohne Beleg direkt am SQL): bestanden")

        # --- Manueller Weg: H5-Analogon -- Heuristik saehe 'S3' als erledigt bereits richtig,
        # hier wird stattdessen S4 (heuristisch 'unbelegt') vom Menschen ausdruecklich auf
        # 'erledigt' mit Beleg gesetzt -- genau der Fall, den die Heuristik nicht mehr korrekt
        # liest (siehe Modulkopf, 'H5'). --------------------------------------------------
        vor_manuell = plan.read_text(encoding="utf-8")
        bericht_manuell = setzen_manuell(kms, conn, plan, "S4", "erledigt", "test", "test_h5_beispiel", schreiben=False)
        assert bericht_manuell.aktion == "wuerde_setzen"
        assert plan.read_text(encoding="utf-8") == vor_manuell, "manueller Trockenlauf haette die Datei nicht anfassen duerfen"

        bericht_manuell2 = setzen_manuell(kms, conn, plan, "S4", "erledigt", "test", "test_h5_beispiel", schreiben=True)
        assert bericht_manuell2.status == "erledigt"
        assert bericht_manuell2.aktion == "fortgeschrieben", \
            f"S4 hatte bereits 'unbelegt' -- der manuelle Weg haette fortschreiben muessen, war {bericht_manuell2.aktion}"
        zeile = conn.execute(
            "SELECT status, beleg_art, beleg FROM plan_status WHERE quelle_kennung='S4'"
        ).fetchone()
        assert tuple(zeile) == ("erledigt", "test", "test_h5_beispiel")
        print("Pflichtfall f (manueller Weg ueberschreibt eine heuristisch falsche Statuszeile, mit Beleg): bestanden")

        # --- Grenzwert: Kennung ohne Abschnitt (Status auf ein Ziel, das nicht existiert) -----
        try:
            setzen_manuell(kms, conn, plan, "S99", "erledigt", "commit", "abc1234", schreiben=False)
            raise AssertionError("S99 haette scheitern muessen -- kein Abschnitt mit dieser Kennung")
        except ValueError as exc:
            assert "kommt in" in str(exc)
        print("Grenzwert (Status auf nicht existierenden Abschnitt, S99): bestanden")

        # --- Grenzwert: zwei Abschnitte mit derselben Kennung (S1 kommt zweimal vor) ---------
        try:
            setzen_manuell(kms, conn, plan, "S1", "erledigt", "commit", "abc1234", schreiben=False)
            raise AssertionError("S1 haette scheitern muessen -- mehrdeutig (zweimal im Plan)")
        except ValueError as exc:
            assert "mehrdeutig" in str(exc)
        print("Grenzwert (zwei Abschnitte mit derselben Kennung, S1): bestanden")

        # --- Grenzwert: Abschnitt ohne Kennung (planentscheidung.py lief hier nie) -----------
        plan_ohne_kennung = tmp / "PLAN_OHNE_KENNUNG.md"
        plan_ohne_kennung.write_text(
            "### S1 · nie an planentscheidung.py uebergeben\nBeschlossen: irgendwas.\n", encoding="utf-8"
        )
        berichte_ohne = verarbeiten(kms, conn, plan_ohne_kennung, schreiben=False)
        assert berichte_ohne[0].aktion == "kennung_fehlt", \
            f"Abschnitt ohne gebundene Kennung haette kennung_fehlt melden muessen, war {berichte_ohne[0].aktion}"
        try:
            setzen_manuell(kms, conn, plan_ohne_kennung, "S1", "erledigt", "commit", "abc1234", schreiben=False)
            raise AssertionError("S1 in plan_ohne_kennung haette scheitern muessen -- keine Kennung gebunden")
        except ValueError as exc:
            assert "noch keine Kennung" in str(exc)
        print("Grenzwert (Abschnitt ohne Kennung): bestanden")

        # --- verarbeiten_knoten(): DB-Weg fuer Knoten OHNE Kennungszeile (Nachtrag 2026-08-15) ---
        # (a) Knoten mit Abschnittsverweis im source-Text -> Feinkennung erkannt, Status samt
        #     Beleg aus dem KNOTENINHALT selbst (nicht aus einer Datei).
        erg_fein = kms.knowledge_add(
            parent_path="/bestand", title="Mit Abschnittsverweis",
            summary="Ein Mechanismus ist gebaut, aber wirkungslos, siehe Beleg.",
            content="Commit `abc1234` zeigt: gebaut, aber wirkungslos, weil die Wirkung am echten Bestand fehlt.",
            neuer_ast=True, tags=["bestand-test"],
            source="erzeugt aus docs/PLAN_BESTANDSWEG_TEST.md Abschnitt 6 (Testfixture)",
            anlass="skript", norm_entscheidung="keine_norm", norm_entschieden_grund="Testfixture.",
        )
        # (b) Knoten OHNE Abschnittsverweis -> Kennung faellt auf die eigene id zurueck.
        erg_grob = kms.knowledge_add(
            parent_path="/bestand", title="Ohne Abschnittsverweis",
            summary="Nur Titel und Datei, kein Feinverweis.",
            content="Beschlossen: dieser Punkt ist erledigt. Beleg test_bestandsweg_beispiel.",
            neuer_ast=True, tags=["bestand-test"],
            source="docs/PLAN_BESTANDSWEG_TEST.md",
            anlass="skript", norm_entscheidung="keine_norm", norm_entschieden_grund="Testfixture.",
        )
        # (c) Astknoten-Platzhalter -- generisch an der source-Signatur erkannt, die
        # kms.knowledge_add(neuer_ast=True) selbst vergibt (siehe _KNOTEN_BESTAND_SQL), NICHT an
        # einem hartcodierten Pfad wie /plaene -- ein dritter, spaeterer Astknoten faellt so
        # automatisch mit heraus, nicht erst nach einer weiteren Fundstelle.
        # "plan-astknoten" statt nur "astknoten" im Pfad -- sonst faellt die Zeile schon am
        # `source LIKE '%PLAN_%'`-Muster heraus, bevor die eigentlich zu pruefende
        # Astknoten-Ausschlussklausel je gebraucht wird (wie die zwei echten Astknoten
        # /plaene/plan-destille-2026-08-09 -- "plan" steckt im Pfadnamen, nicht nur im Astwort).
        kms.knowledge_add(
            parent_path="/bestand/plan-astknoten-test", title="Astknoten",
            summary="Automatisch erzeugter Astknoten.", content="", neuer_ast=True,
            tags=["bestand-test"],
            source="neuer_ast=True, automatisch erzeugt durch /bestand/plan-astknoten-test/irgendwas",
            anlass="skript", norm_entscheidung="keine_norm", norm_entschieden_grund="Testfixture.",
        )

        berichte_bestand = verarbeiten_knoten(kms, conn, schreiben=False)
        kennungen = {b.kennung for b in berichte_bestand}
        assert "Abschnitt 6" in kennungen, f"Feinverweis nicht erkannt: {kennungen}"
        assert erg_grob["id"][:8] in kennungen, f"Fallback auf die eigene id fehlt: {kennungen}"
        assert not any(b.titel == "Astknoten" for b in berichte_bestand), \
            "Astknoten-Platzhalter (/plaene) haette ausgeschlossen bleiben muessen"
        fein_bericht = next(b for b in berichte_bestand if b.kennung == "Abschnitt 6")
        assert fein_bericht.status == "gebaut_wirkungslos" and fein_bericht.beleg == "abc1234", \
            f"Statuserkennung aus dem Knoteninhalt selbst fehlgeschlagen: {fein_bericht}"
        grob_bericht = next(b for b in berichte_bestand if b.kennung == erg_grob["id"][:8])
        assert grob_bericht.status == "erledigt" and grob_bericht.beleg_art == "test", \
            f"Statuserkennung (Fallback-Kennung) fehlgeschlagen: {grob_bericht}"
        print("Nachtrag (verarbeiten_knoten: Feinverweis, id-Fallback, Astknoten ausgeschlossen): bestanden")

        # Schreiblauf + Idempotenz, derselbe Nachweis wie bei verarbeiten() oben.
        verarbeiten_knoten(kms, conn, schreiben=True)
        anzahl_bestand1 = conn.execute("SELECT COUNT(*) FROM plan_status WHERE quelle_datei LIKE 'docs/PLAN_BESTANDSWEG%'").fetchone()[0]
        assert anzahl_bestand1 == 2, f"erwartet 2 Statuszeilen aus dem Bestandsweg, bekommen {anzahl_bestand1}"
        berichte_bestand2 = verarbeiten_knoten(kms, conn, schreiben=True)
        assert all(b.aktion == "unveraendert" for b in berichte_bestand2 if b.status is not None), \
            f"zweiter Bestandslauf haette unveraendert bleiben muessen: {[(b.kennung, b.aktion) for b in berichte_bestand2]}"
        print("Nachtrag (Bestandsweg schreibt, dann idempotent): bestanden")

        conn.close()
        del os.environ["BEGOD_KNOWLEDGE_DB"]
        sys.modules.pop("knowledge_mcp_server", None)

    print("Selbsttest bestanden.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    gruppe = ap.add_mutually_exclusive_group()
    gruppe.add_argument("--vorschlag", type=Path, help="Trockenlauf auf EINER Plandatei (Abschnitts-Weg)")
    gruppe.add_argument("--schreiben", type=Path, help="Statuszeilen anlegen/fortschreiben (Abschnitts-Weg)")
    gruppe.add_argument("--vorschlag-bestand", action="store_true",
                         help="Trockenlauf ueber ALLE PLAN_-Knoten der DB, ohne Dateizugriff")
    gruppe.add_argument("--schreiben-bestand", action="store_true",
                         help="Schreiblauf ueber ALLE PLAN_-Knoten der DB, ohne Dateizugriff")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--kennung", help="gezielter Weg: EINE Abschnittskennung statt der ganzen Datei")
    ap.add_argument("--status", choices=STATUS_WERTE, help="nur mit --kennung")
    ap.add_argument("--beleg-art", dest="beleg_art", choices=("commit", "test", "messdatei"))
    ap.add_argument("--beleg", help="Commit-Hash / Testname / runs/-Pfad, woertlich")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return 0

    if args.vorschlag_bestand or args.schreiben_bestand:
        _lauf_bestand(schreiben=args.schreiben_bestand)
        return 0

    datei = args.schreiben or args.vorschlag
    if not datei:
        ap.print_help()
        return 1
    if args.kennung and not args.status:
        ap.error("--kennung verlangt --status")

    schreiben = args.schreiben is not None
    try:
        _lauf(datei, schreiben, args.kennung, args.status, args.beleg_art, args.beleg)
    except ValueError as exc:
        print(f"FEHLER: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
