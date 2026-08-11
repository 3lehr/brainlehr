#!/usr/bin/env python3
"""konfidenz.py -- ADR-026, Z3 letztes Stueck: Konfidenzverfall.

Alter und Herkunft sind erfuellt (Alter im Recall, `source` Pflicht,
`quell_hash`), Rang/Geltung sind erfuellt (normrang.py/normkraft.py). Was
fehlt: die confidence-Spalte hat sich seit Bestehen nie veraendert (183 von
237 auf dem Schema-Vorgabewert 0.8, siehe knowledge_lint.py::
find_confidence_default_age, K3). Dieses Skript liefert das fehlende Verb.

Nachtrag 2026-08-06: der urspruengliche Entwurf rechnete den Verfall nach
KALENDERTAGEN -- ein ruhendes Projekt verlor Konfidenz, obwohl sich nichts
geaendert hat. Falscher Massstab: bestraft war unveraenderter Bestand statt
tatsaechlicher Unsicherheit. Ersetzt durch DREI REGIME (Praezedenz in dieser
Reihenfolge):

  1 REGIME_BEOBACHTBAR -- `source` nennt eine Datei, die existiert UND in
    einem Git-Repo liegt (git log kann darauf laufen). Verfall nach ANZAHL
    COMMITS seit updated_at, nicht nach Tagen:
        gerechnet = ausgangswert * 0.5 ** (commits_seit_updated_at / hwz)
    Ruht die Datei, ruht der Verfall -- richtig so.
  2 REGIME_DEKLARIERT -- norm_rang gesetzt. KEIN Verfall, gilt_bis
    entscheidet (normkraft.py). Unveraendert wie zuvor.
  3 REGIME_UNBEOBACHTBAR -- kein beobachtbarer Dateibezug (Gesetzestext,
    fremde Schnittstelle, Marktlage, oder der git-Aufruf faellt aus). KEIN
    Verfallswert -- eine Kurve waere vorgetaeuschte Genauigkeit. Stattdessen
    Faelligkeit (naechste_pruefung(), aus updated_at + Halbwertszeit
    abgeleitet, keine neue Spalte -- reine Ableitung aus Bestehendem).

bewerten() liefert alle drei Regime UNTERSCHEIDBAR (Feld "regime" plus
"gerechnet" ODER "naechste_pruefung", nie beides zugleich).
gerechnete_konfidenz() bleibt als duenner Float-Wrapper fuer Aufrufer, die
nur eine Zahl brauchen (bestaetigen()).

Frage 1 (Auftrag): traegt `confidence` weiterhin den Ausgangswert, oder
etwas anderes? Antwort: den AUSGANGSWERT, unveraendert. Begruendung: der
Verfall wird bei jedem Abruf aus (confidence, updated_at) BERECHNET, nie in
die Spalte zurueckgeschrieben -- sonst muesste ein Cronjob taeglich laufen,
damit die Zahl stimmt, und eine Zahl, die nur nach einem Lauf stimmt, ist
schlimmer als gar keine (Auftragstext). `updated_at` ist bereits der
Bezugszeitpunkt der letzten Aenderung/Bestaetigung -- kein neues Feld noetig
(Grenze: keine Schemaaenderung). bestaetigen() setzt NUR updated_at neu
(setzt das Alter auf 0, die gerechnete Konfidenz springt zurueck auf den
Ausgangswert), nie die Spalte confidence selbst.

Kein Ermessen darueber, WELCHER Fakt bestaetigt wird -- das entscheidet der
Betreiber. Dieses Skript wendet nur an. Bauform (Ablehnung, _backup, CLI,
Pflichtgrund, access_log) identisch zu normkraft.py::ausser_kraft -- wird
von dort importiert statt dupliziert (normkraft.py ist tabu zum AENDERN,
nicht zum IMPORTIEREN; gleiches Muster wie knowledge_lint.py, das
ankerverfahren.rueckstand()/normbestand.quellstatus() importiert statt neu
zu schreiben).

Usage:
    .venv/bin/python shared-knowledge/konfidenz.py aktuell <pfad>
    .venv/bin/python shared-knowledge/konfidenz.py bestaetigen <pfad> --wegen <text> [--apply]
    .venv/bin/python shared-knowledge/konfidenz.py verteilung
    .venv/bin/python shared-knowledge/konfidenz.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import argparse
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = _w
sys.path.insert(0, str(HERE))

from normkraft import Ablehnung, _backup, now_iso, CET  # noqa: E402

DB_PATH = HERE / "brainlehr.db"
# Verbund-Wurzel: mehrere eigene Git-Repos nebeneinander (hub/, fahrtenbuch/,
# setfunk/ ...) -- relative Pfade in `source` sind dagegen aufzuloesen, siehe
# beobachtbare_datei(). Kommt aus haken/ort.py, weil "zwei Ebenen ueber mir"
# seit dem Umzug in .claude/ landet statt in Begod2026.
from haken.ort import VERBUND as BEGOD_ROOT  # noqa: E402

# ─── Wissensart: Halbwertszeit je Art, deterministisch aus Bestand ─────────
#
# Erkennungsmerkmal ist `path` (immer gesetzt, strukturiert) und `source`
# (Freitext, aber "ADR"/"Konsil" kommen darin vor -- siehe Stichprobe
# 2026-08-06 ueber den echten Bestand). `tags` wurde geprueft und verworfen:
# von 225 Fakten tragen nur ~55 ueberhaupt Tags, und die Werte sind zu
# uneinheitlich (Freitext-Schlagworte je Sitzung) fuer eine verlaessliche
# Dreiteilung -- ein Merkmal, das bei 3/4 der Zeilen fehlt, kann keine
# deterministische Klassifikation tragen.
#
# Reihenfolge der Pruefung ist die Praezedenz: eine Quelle, die "ADR" oder
# "Konsil" nennt, ist eine bewusste Entscheidung, auch wenn der Pfad
# zufaellig unter /testing oder /ops liegt -- das Quellenmerkmal ist
# spezifischer als der Pfad und gewinnt daher zuerst.
WISSENSART_ARCHITEKTUR = "architektur"
WISSENSART_BETRIEB = "betrieb"
WISSENSART_STANDARD = "standard"

# Alle drei Werte GERATEN -- keine Messung, keine Kalibrierung gegen echte
# Korrektur-/Widerspruchsraten (die gaebe es erst nach Wochen Betrieb mit
# bestaetigen()/ausser_kraft()). Groessenordnung, kein Messwert:
HALBWERTSZEIT_TAGE: dict[str, float] = {
    # geraten: eine Architekturentscheidung/ADR ist ein bewusster, seltener
    # Beschluss -- sie soll nicht schon nach ein paar Wochen "unsicher"
    # wirken, nur weil niemand sie erneut bestaetigt hat. Groessenordnung
    # "ein Jahr", angelehnt an die Lebensdauer der ADRs im Repo bisher.
    WISSENSART_ARCHITEKTUR: 365.0,
    # geraten: CI-Ergebnisse, Deploy-/Ops-Zustaende sind Momentaufnahmen
    # eines sich staendig aendernden Systems -- ein Monat als grobe
    # Orientierung, bewusst kurz.
    WISSENSART_BETRIEB: 30.0,
    # geraten: Zwischenwert (ca. ein Quartal) fuer generisches Fachwissen
    # ohne staerkeres Signal in path/source.
    WISSENSART_STANDARD: 120.0,
}

# geraten: unterhalb dieser gerechneten Konfidenz gilt ein Fakt als
# "deutlich verfallen" und wird im Lint gemeldet. Willkuerlicher Bruch
# (weniger als 3/8 des ueblichen Ausgangswerts 0.8), keine gemessene
# Fehlalarmrate dahinter.
KONFIDENZ_SCHWELLE = 0.3

# ─── Regime-Kennzeichnung (Auftrag 2026-08-06) ─────────────────────────────
REGIME_BEOBACHTBAR = "bezug_beobachtbar"    # Verfall nach Commits
REGIME_DEKLARIERT = "geltung_deklariert"    # norm_rang, kein Verfall
REGIME_UNBEOBACHTBAR = "bezug_unbeobachtbar"  # kein Verfallswert, nur Faelligkeit

# Kandidat: ein Pfadstueck mit Dateiendung, absolut (~/... oder /...) oder
# relativ (a/b/c.ext). Freitext-Quellen ("erzeugt aus <pfad> (Stand ...)",
# "docs/adr/X.md, Session ...") tragen oft mehrere Kandidaten und Beiwerk --
# beobachtbare_datei() probiert sie der Reihe nach, nimmt den ersten
# treffenden.
_PFAD_KANDIDAT_RE = re.compile(r'[~/][\w./\- ]*?\.\w{1,5}\b|(?:[\w.\-]+/)+[\w.\-]+\.\w{1,5}')


def wissensart(path: str, source: str | None) -> str:
    src = (source or "").lower()
    if "adr" in src or "konsil" in src:
        return WISSENSART_ARCHITEKTUR
    if (path or "").startswith("/arch"):
        return WISSENSART_ARCHITEKTUR
    if (path or "").startswith("/testing") or (path or "").startswith("/ops"):
        return WISSENSART_BETRIEB
    return WISSENSART_STANDARD


def _parse_ts(ts: str) -> datetime:
    d = datetime.fromisoformat(ts)
    if d.tzinfo is None:
        d = d.replace(tzinfo=CET)
    return d


def alter_tage(updated_at: str, now: datetime) -> float:
    """Alter seit dem Bezugszeitpunkt in Tagen, nie negativ (ein
    Zeitstempel in der Zukunft -- Uhrendrift, Testfixture -- zaehlt als
    Alter 0, nicht als Bonus)."""
    delta = (now - _parse_ts(updated_at)).total_seconds() / 86400
    return max(0.0, delta)


def _kandidaten_pfade(source: str | None) -> list[str]:
    if not source:
        return []
    return [m.group(0).strip().rstrip(",;)") for m in _PFAD_KANDIDAT_RE.finditer(source)]


def _git_toplevel(datei: Path) -> str | None:
    try:
        r = subprocess.run(
            ["git", "-C", str(datei.parent), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
    except OSError:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def beobachtbare_datei(source: str | None) -> Path | None:
    """Erster Kandidat aus `source`, der existiert UND in einem Git-Repo
    liegt (Voraussetzung dafuer, dass commits_seit() ueberhaupt laufen
    kann). None -- kein Kandidat traegt, der Bezug ist unbeobachtbar
    (Regime 3). Relative Kandidaten werden gegen BEGOD_ROOT aufgeloest, ~
    gegen HOME."""
    for kandidat in _kandidaten_pfade(source):
        p = Path(os.path.expanduser(kandidat))
        if not p.is_absolute():
            p = BEGOD_ROOT / kandidat
        if p.exists() and _git_toplevel(p):
            return p
    return None


def commits_seit(datei: Path, seit_iso: str) -> int | None:
    """Anzahl Commits, die `datei` seit `seit_iso` veraendert haben. None
    bei ausgefallenem git-Aufruf (Repo verschwunden, Datei geloescht
    zwischen beobachtbare_datei() und hier) -- der Aufrufer darf das NIE
    still als 0 lesen, sondern muss auf Regime 3 zurueckfallen."""
    try:
        r = subprocess.run(
            ["git", "-C", str(datei.parent), "log", "--oneline", f"--since={seit_iso}", "--", datei.name],
            capture_output=True, text=True, timeout=5,
        )
    except OSError:
        return None
    if r.returncode != 0:
        return None
    return len([z for z in r.stdout.splitlines() if z.strip()])


def naechste_pruefung(updated_at: str, path: str, source: str | None, now: datetime) -> dict:
    """Nur Regime 3: keine Verfallszahl, sondern Faelligkeit. Wiederverwendet
    dieselben geratenen HALBWERTSZEIT-Werte, hier als Pruefintervall
    gelesen statt als Verfallskurve -- keine neue Konstante, keine neue
    Bedeutung, nur eine andere Ableitung aus updated_at."""
    hwz = HALBWERTSZEIT_TAGE[wissensart(path, source)]
    faellig = _parse_ts(updated_at) + timedelta(days=hwz)
    return {
        "faellig_am": faellig.isoformat(),
        "ueberfaellig": faellig < now,
        "tage_bis_faellig": round((faellig - now).total_seconds() / 86400, 1),
    }


def bewerten(confidence: float, updated_at: str | None, norm_rang: int | None,
             path: str, source: str | None, now: datetime) -> dict:
    """Kern der ganzen Datei. Macht die drei Regime UNTERSCHEIDBAR --
    'gerechnet' und 'naechste_pruefung' schliessen sich gegenseitig aus,
    nie beide None, nie beide gesetzt:
      Regime 1 (beobachtbar):    gerechnet=float,  naechste_pruefung=None
      Regime 2 (deklariert):     gerechnet=float (Ausgangswert), naechste_pruefung=None
      Regime 3 (unbeobachtbar):  gerechnet=None,   naechste_pruefung=dict
    """
    if norm_rang is not None:
        return {"regime": REGIME_DEKLARIERT, "gerechnet": confidence,
                "commits_seit": None, "naechste_pruefung": None}
    if not updated_at:
        return {"regime": REGIME_UNBEOBACHTBAR, "gerechnet": None,
                "commits_seit": None, "naechste_pruefung": None}
    datei = beobachtbare_datei(source)
    if datei is not None:
        commits = commits_seit(datei, updated_at)
        if commits is not None:
            hwz = HALBWERTSZEIT_TAGE[wissensart(path, source)]
            gerechnet = confidence * (0.5 ** (commits / hwz))
            return {"regime": REGIME_BEOBACHTBAR, "gerechnet": round(gerechnet, 4),
                    "commits_seit": commits, "naechste_pruefung": None}
        # git-Aufruf fehlgeschlagen: Repo/Datei zwischen beobachtbare_datei()
        # und commits_seit() verschwunden -- NICHT still als 0 Commits lesen.
        # Faellt durch auf Regime 3.
    return {"regime": REGIME_UNBEOBACHTBAR, "gerechnet": None, "commits_seit": None,
            "naechste_pruefung": naechste_pruefung(updated_at, path, source, now)}


def gerechnete_konfidenz(confidence: float, updated_at: str | None, norm_rang: int | None,
                          path: str, source: str | None, now: datetime) -> float:
    """Duenner Float-Wrapper um bewerten() fuer Aufrufer, die nur eine Zahl
    brauchen (bestaetigen(): Anzeige vorher/nachher -- der Reset betrifft
    ohnehin nur updated_at, unabhaengig vom Regime). Regime 3 hat KEINEN
    Verfallswert; hier faellt das auf den unveraenderten Ausgangswert
    zurueck. Wer die drei Regime unterscheiden muss, ruft bewerten()."""
    r = bewerten(confidence, updated_at, norm_rang, path, source, now)
    return r["gerechnet"] if r["gerechnet"] is not None else confidence


# ─── Bestaetigen ────────────────────────────────────────────────────────────
# Bauform identisch zu normkraft.py::ausser_kraft/plan_ausser_kraft: erst
# planen (nichts schreiben, kann werfen), dann anwenden (Backup + Schreiben +
# access_log), CLI mit --apply/--dry-run, Pflichtgrund.

def _lade_fakt(conn: sqlite3.Connection, pfad: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT id, path, title, content, confidence, norm_rang, updated_at, source "
        "FROM knowledge_nodes WHERE path = ?",
        (pfad,),
    ).fetchone()
    if row is None:
        raise Ablehnung(f"Pfad nicht gefunden: {pfad}")
    if row["norm_rang"] is not None:
        raise Ablehnung(
            f"{pfad} ist eine Norm (norm_rang={row['norm_rang']}) -- Normen verfallen nicht, "
            "keine Bestaetigung noetig."
        )
    return row


def plan_bestaetigen(db_path: Path, pfad: str, wegen: str, now: datetime | None = None) -> dict:
    if not wegen or not wegen.strip():
        raise Ablehnung("--wegen ist Pflicht -- eine Bestaetigung ohne Grund ist spaeter nicht nachvollziehbar.")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        row = _lade_fakt(conn, pfad)
        now = now or datetime.now(CET)
        vorher = gerechnete_konfidenz(
            row["confidence"], row["updated_at"], row["norm_rang"], row["path"], row["source"], now
        )
        nachher_ts = now_iso()
        # nach dem Reset ist alter_tage=0 -> gerechnete Konfidenz == Ausgangswert.
        nachher = row["confidence"]
        notiz = f"\n\n[bestaetigt am {nachher_ts}: {wegen.strip()}]"
        return {
            "pfad": pfad,
            "id": row["id"],
            "ausgangswert": row["confidence"],
            "vorher_gerechnet": round(vorher, 4),
            "nachher_gerechnet": round(nachher, 4),
            "vorher_updated_at": row["updated_at"],
            "nachher_updated_at": nachher_ts,
            "content_anhang": notiz,
            "wegen": wegen.strip(),
        }
    finally:
        conn.close()


def bestaetigen(db_path: Path, pfad: str, wegen: str, apply: bool, now: datetime | None = None) -> dict:
    result = plan_bestaetigen(db_path, pfad, wegen, now=now)
    result["backup"] = None
    if not apply:
        return result

    result["backup"] = str(_backup(db_path))
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute("SELECT content FROM knowledge_nodes WHERE id = ?", (result["id"],)).fetchone()
        neuer_content = (row[0] or "") + result["content_anhang"]
        conn.execute(
            "UPDATE knowledge_nodes SET updated_at = ?, content = ? WHERE id = ?",
            (result["nachher_updated_at"], neuer_content, result["id"]),
        )
        conn.execute(
            """INSERT INTO access_log (node_path, action, query, status, timestamp)
               VALUES (?, 'bestaetigt', ?, 'completed', ?)""",
            (pfad, result["wegen"], result["nachher_updated_at"]),
        )
        conn.commit()
    finally:
        conn.close()
    return result


# ─── Verteilung gegen den Echtbestand (rein lesend) ────────────────────────

def verteilung(db_path: Path, now: datetime | None = None) -> dict:
    now = now or datetime.now(CET)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT path, title, confidence, norm_rang, updated_at, source "
            "FROM knowledge_nodes WHERE norm_rang IS NULL"
        ).fetchall()
    finally:
        conn.close()
    werte = []
    for r in rows:
        b = bewerten(r["confidence"], r["updated_at"], r["norm_rang"], r["path"], r["source"], now)
        werte.append({"path": r["path"], "title": r["title"], "ausgangswert": r["confidence"],
                      "regime": b["regime"], "gerechnet": b["gerechnet"],
                      "naechste_pruefung": b["naechste_pruefung"],
                      "alter_tage": round(alter_tage(r["updated_at"], now), 1) if r["updated_at"] else None})
    je_regime = {REGIME_BEOBACHTBAR: 0, REGIME_UNBEOBACHTBAR: 0}
    unter_schwelle_je_regime = {REGIME_BEOBACHTBAR: 0}
    buckets = {"1.0-0.8": 0, "0.8-0.6": 0, "0.6-0.4": 0, "0.4-0.2": 0, "0.2-0.0": 0}
    for w in werte:
        je_regime[w["regime"]] = je_regime.get(w["regime"], 0) + 1
        g = w["gerechnet"]
        if g is None:
            continue  # Regime 3: keine Zahl, taucht in Buckets/Schwelle nicht auf
        if g < KONFIDENZ_SCHWELLE:
            unter_schwelle_je_regime[w["regime"]] = unter_schwelle_je_regime.get(w["regime"], 0) + 1
        if g >= 0.8:
            buckets["1.0-0.8"] += 1
        elif g >= 0.6:
            buckets["0.8-0.6"] += 1
        elif g >= 0.4:
            buckets["0.6-0.4"] += 1
        elif g >= 0.2:
            buckets["0.4-0.2"] += 1
        else:
            buckets["0.2-0.0"] += 1
    aeltester = max((w for w in werte if w["alter_tage"] is not None), key=lambda w: w["alter_tage"], default=None)
    return {
        "gesamt": len(werte),
        "je_regime": je_regime,
        "buckets": buckets,
        "schwelle": KONFIDENZ_SCHWELLE,
        "unter_schwelle_je_regime": unter_schwelle_je_regime,
        "unter_schwelle_anzahl": sum(unter_schwelle_je_regime.values()),
        "aeltester": aeltester,
    }


# ─── Lint-Integration: Kategorie 14 ─────────────────────────────────────────

def find_confidence_decay(conn: sqlite3.Connection, now: datetime | None = None,
                           schwelle: float = KONFIDENZ_SCHWELLE) -> list[dict]:
    """Fuer knowledge_lint.py: Fakten (norm_rang IS NULL) mit Regime 1
    (beobachtbarer Dateibezug), deren gerechnete Konfidenz unter die
    Schwelle gefallen ist. Regime 3 hat KEINEN Verfallswert -- kann diese
    Schwelle also nie unter- oder ueberschreiten und taucht hier nie auf
    (siehe find_pruefung_ueberfaellig() fuer das Regime-3-Gegenstueck).
    conn darf read-only sein -- diese Funktion schreibt nichts."""
    now = now or datetime.now(CET)
    rows = conn.execute(
        "SELECT path, title, confidence, norm_rang, updated_at, source "
        "FROM knowledge_nodes WHERE norm_rang IS NULL"
    ).fetchall()
    out = []
    for r in rows:
        b = bewerten(r["confidence"], r["updated_at"], r["norm_rang"], r["path"], r["source"], now)
        if b["gerechnet"] is not None and b["gerechnet"] < schwelle:
            out.append({
                "path": r["path"], "title": r["title"], "ausgangswert": r["confidence"],
                "regime": b["regime"], "gerechnet": b["gerechnet"], "commits_seit": b["commits_seit"],
                "alter_tage": round(alter_tage(r["updated_at"], now), 1) if r["updated_at"] else None,
            })
    out.sort(key=lambda i: i["gerechnet"])
    return out


def find_pruefung_ueberfaellig(conn: sqlite3.Connection, now: datetime | None = None) -> list[dict]:
    """Regime-3-Gegenstueck zu find_confidence_decay(): Fakten ohne
    beobachtbaren Bezug, deren Faelligkeit (naechste_pruefung) verstrichen
    ist. Nicht in find_confidence_decay() gemischt -- 'ueberfaellig' und
    'gerechnet < Schwelle' sind verschiedene Aussagen (Auftrag 2026-08-06,
    Punkt 3: die drei Regime bleiben unterscheidbar, auch im Lint)."""
    now = now or datetime.now(CET)
    rows = conn.execute(
        "SELECT path, title, confidence, norm_rang, updated_at, source "
        "FROM knowledge_nodes WHERE norm_rang IS NULL"
    ).fetchall()
    out = []
    for r in rows:
        b = bewerten(r["confidence"], r["updated_at"], r["norm_rang"], r["path"], r["source"], now)
        if b["regime"] == REGIME_UNBEOBACHTBAR and b["naechste_pruefung"] and b["naechste_pruefung"]["ueberfaellig"]:
            out.append({"path": r["path"], "title": r["title"], **b["naechste_pruefung"]})
    out.sort(key=lambda i: i["faellig_am"])
    return out


# ─── CLI ────────────────────────────────────────────────────────────────────

def _print_bestaetigen(result: dict, mode: str) -> None:
    print(f"=== konfidenz bestaetigen ({mode}) ===")
    print(f"Pfad: {result['pfad']}")
    print(f"Ausgangswert: {result['ausgangswert']}")
    print(f"gerechnete Konfidenz: {result['vorher_gerechnet']} -> {result['nachher_gerechnet']}")
    print(f"Bezugszeitpunkt (updated_at): {result['vorher_updated_at']!r} -> {result['nachher_updated_at']!r}")
    print(f"wegen: {result['wegen']}")
    if result.get("backup"):
        print(f"Sicherung: {result['backup']}")


def _print_aktuell(row: sqlite3.Row, now: datetime) -> None:
    b = bewerten(row["confidence"], row["updated_at"], row["norm_rang"], row["path"], row["source"], now)
    print(f"Pfad: {row['path']}")
    print(f"norm_rang: {row['norm_rang']!r}")
    print(f"Ausgangswert (confidence-Spalte): {row['confidence']}")
    print(f"Regime: {b['regime']}")
    if b["regime"] == REGIME_DEKLARIERT:
        print("Norm -- verfaellt nicht, gerechnete Konfidenz == Ausgangswert.")
        return
    if b["regime"] == REGIME_UNBEOBACHTBAR:
        if b["naechste_pruefung"] is None:
            print("kein Bezugszeitpunkt (updated_at leer) -- nicht messbar.")
        else:
            np = b["naechste_pruefung"]
            print("kein beobachtbarer Bezug -- nicht messbar, kein Verfallswert.")
            print(f"Faellig: {np['faellig_am']} ({'UEBERFAELLIG' if np['ueberfaellig'] else 'noch offen'}, "
                  f"{np['tage_bis_faellig']} Tage)")
        return
    # REGIME_BEOBACHTBAR
    art = wissensart(row["path"], row["source"])
    hwz = HALBWERTSZEIT_TAGE[art]
    alter = alter_tage(row["updated_at"], now)
    print(f"Wissensart: {art} (Halbwertszeit {hwz} Commits, geraten)")
    print(f"Alter seit updated_at: {alter} Tage (informativ, nicht Bezugsgroesse des Verfalls)")
    print(f"Commits seit updated_at: {b['commits_seit']}"
          + (" -- kein Verfall, weil nichts passiert ist" if b["commits_seit"] == 0 else ""))
    print(f"gerechnete Konfidenz: {b['gerechnet']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--selftest", action="store_true")
    sub = parser.add_subparsers(dest="cmd")

    p_akt = sub.add_parser("aktuell")
    p_akt.add_argument("pfad")

    p_best = sub.add_parser("bestaetigen")
    p_best.add_argument("pfad")
    p_best.add_argument("--wegen", required=True, help="Pflicht: Grund fuer die Bestaetigung")
    p_best.add_argument("--apply", action="store_true", help="tatsaechlich schreiben (Vorgabe: --dry-run)")
    p_best.add_argument("--dry-run", action="store_true", help="Vorgabe, nur zur Klarheit explizit angebbar")

    sub.add_parser("verteilung")

    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()

    if args.cmd is None:
        parser.print_help()
        return 1

    if not DB_PATH.exists():
        print(f"FEHLER: {DB_PATH} nicht gefunden.")
        return 1

    if args.cmd == "aktuell":
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=2.0)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT path, title, confidence, norm_rang, updated_at, source "
                "FROM knowledge_nodes WHERE path = ?", (args.pfad,)
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            print(f"Pfad nicht gefunden: {args.pfad}")
            return 1
        _print_aktuell(row, datetime.now(CET))
        return 0

    if args.cmd == "bestaetigen":
        try:
            result = bestaetigen(DB_PATH, args.pfad, args.wegen, apply=args.apply)
        except Ablehnung as exc:
            print(f"ABGELEHNT: {exc}")
            return 1
        _print_bestaetigen(result, "APPLY" if args.apply else "DRY-RUN (kein --apply)")
        return 0

    if args.cmd == "verteilung":
        v = verteilung(DB_PATH)
        print(f"=== konfidenz verteilung (Schwelle {v['schwelle']}) ===")
        print(f"Gesamt (Fakten, norm_rang IS NULL): {v['gesamt']}")
        print(f"  je Regime: beobachtbar={v['je_regime'].get(REGIME_BEOBACHTBAR, 0)} "
              f"unbeobachtbar={v['je_regime'].get(REGIME_UNBEOBACHTBAR, 0)}")
        print("Buckets (nur Regime beobachtbar -- Regime unbeobachtbar hat keine Zahl):")
        for bucket, n in v["buckets"].items():
            print(f"  {bucket}: {n}")
        print(f"Unter Schwelle: {v['unter_schwelle_anzahl']} "
              f"(je Regime: {v['unter_schwelle_je_regime']})")
        if v["aeltester"]:
            a = v["aeltester"]
            print(f"Aeltester Fakt (Kalenderalter, informativ): {a['path']} ({a['alter_tage']} Tage, "
                  f"Regime {a['regime']}, gerechnet {a['gerechnet']})")
        return 0

    parser.print_help()
    return 1


# ─── Selbsttest ────────────────────────────────────────────────────────────

def _init_temp_db(path: Path) -> None:
    schema_sql = (HERE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(path))
    conn.executescript(schema_sql)
    conn.close()


def _insert_node(conn: sqlite3.Connection, node_id: str, path: str, *, confidence: float = 0.8,
                  norm_rang: int | None = None, updated_at: str | None = None,
                  source: str | None = None, content: str = "") -> None:
    updated_at = updated_at or "2026-01-01T00:00:00+01:00"
    # source darf seit dem DB-Trigger (Auftrag 2026-08-06) nicht leer sein --
    # Selbsttest-Platzhalter statt None, wenn der Aufrufer keinen echten Wert
    # mitgibt.
    source = source or "selftest"
    # norm_entscheidung (Auftrag 2026-08-08): dieser Helfer erzeugt reine
    # Testvorrichtungen -- ein gesetzter norm_rang macht sie zur (unbefristet
    # gueltigen, gilt_ab = updated_at als belegbarer Zeitpunkt) Norm, sonst
    # bleiben sie Fakt (keine_norm). Kein Vorgabewert, der raet: die
    # Entscheidung folgt direkt aus dem Aufrufer-Parameter norm_rang.
    norm_entscheidung = "keine_norm" if norm_rang is None else "norm_unbefristet"
    gilt_ab = updated_at if norm_rang is not None else None
    # norm_entschieden_* (Nachtrag 2026-08-08): Entscheider ist dieser
    # Testvorrichtungs-Helfer selbst, Begruendung folgt direkt aus
    # norm_entscheidung oben.
    grund = ("Testvorrichtung ohne Rang -- Fakt" if norm_rang is None
             else "Testvorrichtung mit vorgegebenem norm_rang -- Norm ohne Enddatum")
    conn.execute(
        """INSERT INTO knowledge_nodes
           (id, path, parent_path, project_id, title, summary, content, level, tags,
            created_at, updated_at, confidence, norm_rang, gilt_ab, norm_entscheidung,
            norm_entschieden_von, norm_entschieden_am, norm_entschieden_grund, source)
           VALUES (?, ?, '/', 'shared', ?, 'summary', ?, 1, '[]', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (node_id, path, node_id, content, updated_at, updated_at, confidence, norm_rang,
         gilt_ab, norm_entscheidung, "skript:konfidenz.py", updated_at, grund, source),
    )


def _mk_git_repo(tmp_path: Path, dateiname: str, commit_iso_zeiten: list[str]) -> Path:
    """Testfixture: temp Git-Repo mit einer Datei, committed zu genau den
    gegebenen Zeitpunkten. GIT_AUTHOR/COMMITTER_DATE gesetzt -- ein echtes
    `git commit` ohne das haette den Wall-Clock-Zeitpunkt des Testlaufs,
    nicht den fuer die Pruefung gebrauchten festen Zeitpunkt."""
    repo = tmp_path / f"repo-{dateiname.replace('.', '_')}"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    datei = repo / dateiname
    for i, iso in enumerate(commit_iso_zeiten):
        datei.write_text(f"Inhalt {i}\n")
        env = {**os.environ, "GIT_AUTHOR_DATE": iso, "GIT_COMMITTER_DATE": iso}
        subprocess.run(["git", "add", dateiname], cwd=repo, check=True, env=env)
        subprocess.run(["git", "commit", "-q", "-m", f"c{i}"], cwd=repo, check=True, env=env)
    return datei


def _selftest() -> int:
    import tempfile

    _now = datetime.fromisoformat("2026-04-11T00:00:00+01:00")  # beliebiger fixer Referenzpunkt

    def _mk_ts(tage_zurueck: float) -> str:
        return (_now - timedelta(days=tage_zurueck)).isoformat()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # --- Regime 1 (beobachtbar): Verfall nach COMMITS, nicht nach Tagen ---
        # Datei mit drei Commits bei Tag -40, -20, -5 (relativ zu _now).
        datei = _mk_git_repo(tmp_path, "quelle.md", [
            _mk_ts(40), _mk_ts(20), _mk_ts(5),
        ])
        src = f"erzeugt aus {datei}"

        assert beobachtbare_datei(src) == datei
        assert beobachtbare_datei("Gesetzestext ohne Dateibezug") is None
        assert beobachtbare_datei(None) is None

        # updated_at zwischen c1(-40) und c2(-20) -> 2 Commits seither (c2, c3).
        assert commits_seit(datei, _mk_ts(30)) == 2
        # updated_at zwischen c2(-20) und c3(-5) -> 1 Commit seither (c3).
        assert commits_seit(datei, _mk_ts(10)) == 1
        # updated_at nach c3(-5) -> kein Commit seither.
        assert commits_seit(datei, _mk_ts(1)) == 0

        b1 = bewerten(0.8, _mk_ts(30), None, "/standard/x", src, _now)
        assert b1["regime"] == REGIME_BEOBACHTBAR, b1
        assert b1["commits_seit"] == 2, b1
        hwz_standard = HALBWERTSZEIT_TAGE[WISSENSART_STANDARD]
        erwartet = round(0.8 * 0.5 ** (2 / hwz_standard), 4)
        assert b1["gerechnet"] == erwartet, (b1, erwartet)
        assert b1["naechste_pruefung"] is None

        print("SELFTEST Regime 1 OK: beobachtbare_datei() findet/verwirft Kandidaten, "
              f"commits_seit() zaehlt richtig (2/1/0), gerechnet={erwartet} nach Formel.")

        # --- Rot-vor-gruen (Abnahme b): Datei ohne Aenderung seit 120 Tagen ---
        # EINE Datei, EIN Commit, updated_at kurz danach, jetzt 130 Tage
        # spaeter -- Kalenderalter gross, aber KEIN neuer Commit.
        ruhig = _mk_git_repo(tmp_path, "ruhig.md", [_mk_ts(130)])
        updated_ruhig = (datetime.fromisoformat(_mk_ts(130)) + timedelta(seconds=1)).isoformat()
        alter_ruhig = alter_tage(updated_ruhig, _now)
        assert alter_ruhig > HALBWERTSZEIT_TAGE[WISSENSART_STANDARD], alter_ruhig  # > 120 Tage, deutlich "alt"

        # VORHER (alte Formel, Kalendertage -- so rechnete der Code vor diesem
        # Auftrag): waere deutlich gefallen.
        vorher_kalenderformel = round(0.8 * 0.5 ** (alter_ruhig / HALBWERTSZEIT_TAGE[WISSENSART_STANDARD]), 4)
        assert vorher_kalenderformel < 0.5, vorher_kalenderformel  # "vorher deutlich gefallen"

        # NACHHER (dieser Auftrag): 0 Commits seit updated_at -> unveraendert.
        b_ruhig = bewerten(0.8, updated_ruhig, None, "/standard/ruhig",
                            f"erzeugt aus {ruhig}", _now)
        assert b_ruhig["regime"] == REGIME_BEOBACHTBAR
        assert b_ruhig["commits_seit"] == 0, b_ruhig
        assert b_ruhig["gerechnet"] == 0.8, b_ruhig  # unveraendert -- "nachher"

        print(f"ABNAHME b) rot-vor-gruen: Kalenderalter {alter_ruhig} Tage (>120). "
              f"VORHER (Kalenderformel): {vorher_kalenderformel} (deutlich gefallen). "
              f"NACHHER (Commit-Formel, 0 Commits seither): {b_ruhig['gerechnet']} (unveraendert).")

        # --- Gegenprobe (Abnahme c, wichtigster Punkt): 30 Commits -> MUSS fallen ---
        # 31 Commits im Abstand von je 2 Tagen, updated_at knapp nach dem
        # ersten -> 30 Commits seither.
        aktiv_zeiten = [_mk_ts(62 - 2 * i) for i in range(31)]  # Tag -62 .. -2
        aktiv = _mk_git_repo(tmp_path, "aktiv.md", aktiv_zeiten)
        updated_aktiv = (datetime.fromisoformat(aktiv_zeiten[0]) + timedelta(seconds=1)).isoformat()
        commits_aktiv = commits_seit(aktiv, updated_aktiv)
        assert commits_aktiv == 30, commits_aktiv
        b_aktiv = bewerten(0.8, updated_aktiv, None, "/standard/aktiv", f"erzeugt aus {aktiv}", _now)
        assert b_aktiv["regime"] == REGIME_BEOBACHTBAR
        assert b_aktiv["gerechnet"] < 0.8, b_aktiv  # MUSS fallen -- sonst waere Verfall nur abgeschaltet
        print(f"ABNAHME c) GEGENPROBE: 30 Commits seit updated_at -> gerechnet={b_aktiv['gerechnet']} "
              f"< Ausgangswert 0.8 (Verfall wirkt weiterhin, nur nach Commits statt Kalendertagen).")

        # --- git-Aufruf ausgefallen (Datei existiert, aber KEIN Git-Repo) ---
        # NICHT still als 0 Commits/Regime 1 lesen -- faellt auf Regime 3.
        nicht_git = tmp_path / "kein_repo.md"
        nicht_git.write_text("kein Repo hier\n")
        assert beobachtbare_datei(f"erzeugt aus {nicht_git}") is None
        b_ausserhalb = bewerten(0.8, _mk_ts(200), None, "/standard/y", f"erzeugt aus {nicht_git}", _now)
        assert b_ausserhalb["regime"] == REGIME_UNBEOBACHTBAR, b_ausserhalb
        assert b_ausserhalb["gerechnet"] is None, b_ausserhalb

        # --- Regime 3 (unbeobachtbar): Gesetzestext ohne Dateibezug ---------
        b3 = bewerten(0.85, _mk_ts(200), None, "/recht/urhg-87a", "§87a UrhG, geprueft 2026-01-01", _now)
        assert b3["regime"] == REGIME_UNBEOBACHTBAR, b3
        assert b3["gerechnet"] is None, "Regime 3 darf KEINEN Verfallswert liefern -- vorgetaeuschte Genauigkeit"
        assert b3["naechste_pruefung"] is not None
        assert set(b3["naechste_pruefung"]) == {"faellig_am", "ueberfaellig", "tage_bis_faellig"}
        assert b3["naechste_pruefung"]["ueberfaellig"] is True  # 200 Tage > 120 Tage Pruefintervall (Standard)
        print(f"ABNAHME d) Regime 3, woertliche Ausgabe: {b3}")

        # --- Alle drei Regime nicht verwechselbar (Abnahme 3) ----------------
        b_norm = bewerten(0.9, _mk_ts(0), 1, "/adr/x", "ADR", _now)
        assert b_norm["regime"] == REGIME_DEKLARIERT and b_norm["gerechnet"] == 0.9
        assert {b1["regime"], b_ruhig["regime"], b_norm["regime"], b3["regime"]} == {
            REGIME_BEOBACHTBAR, REGIME_DEKLARIERT, REGIME_UNBEOBACHTBAR,
        }
        # "kein Verfall, weil Norm" (Regime 2) vs. "kein Verfall, weil nichts
        # passiert ist" (Regime 1, 0 Commits) vs. "nicht messbar" (Regime 3) --
        # gleicher gerechnet-Wert (0.9 vs 0.8 vs None) waere hier gerade NICHT
        # verwechselbar, weil "regime" jedes Mal unterschiedlich ist:
        assert b_norm["regime"] != b_ruhig["regime"] != b3["regime"] != b_norm["regime"]

        # --- gerechnete_konfidenz(): Float-Wrapper bleibt fuer alte Aufrufer ---
        assert gerechnete_konfidenz(0.8, _mk_ts(30), None, "/standard/x", src, _now) == erwartet
        assert gerechnete_konfidenz(0.9, _mk_ts(0), 1, "/adr/x", "ADR", _now) == 0.9
        assert gerechnete_konfidenz(0.85, _mk_ts(200), None, "/recht/x", "§87a UrhG", _now) == 0.85  # Regime 3 -> Ausgangswert

        # --- Wissensart-Klassifikation, deterministisch -----------------------
        assert wissensart("/arch/mcp", None) == WISSENSART_ARCHITEKTUR
        assert wissensart("/shared/irgendwas", "Konsil 2026-08-05") == WISSENSART_ARCHITEKTUR
        assert wissensart("/shared/irgendwas", "docs/adr/ADR-026.md") == WISSENSART_ARCHITEKTUR
        assert wissensart("/testing/pytest", None) == WISSENSART_BETRIEB
        assert wissensart("/ops/appstoreconnect", None) == WISSENSART_BETRIEB
        assert wissensart("/lessons", None) == WISSENSART_STANDARD

        print("SELFTEST Regime-Unterscheidung + Wissensart OK.")

        # --- bestaetigen(): DB-Rundfahrt -----------------------------------------
        db_path = tmp_path / "brainlehr.db"
        _init_temp_db(db_path)

        conn = sqlite3.connect(str(db_path))
        try:
            # "n-alt" traegt Freitext-Source ohne Dateibezug -> Regime 3.
            _insert_node(conn, "n-alt", "/standard/alt", confidence=0.8,
                         updated_at=_mk_ts(HALBWERTSZEIT_TAGE[WISSENSART_STANDARD]))
            _insert_node(conn, "n-norm", "/adr/x", confidence=0.9, norm_rang=1, source="ADR")
            conn.commit()
        finally:
            conn.close()

        # Ablehnung 1: Pfad existiert nicht.
        try:
            plan_bestaetigen(db_path, "/nirgends", "Test")
            assert False, "haette ablehnen muessen (Pfad fehlt)"
        except Ablehnung as e:
            assert "nicht gefunden" in str(e)

        # Ablehnung 2: Norm -- keine Bestaetigung noetig.
        try:
            plan_bestaetigen(db_path, "/adr/x", "Test")
            assert False, "haette ablehnen muessen (Norm)"
        except Ablehnung as e:
            assert "Normen verfallen nicht" in str(e)

        # Ablehnung 3: kein Grund.
        try:
            plan_bestaetigen(db_path, "/standard/alt", "")
            assert False, "haette ablehnen muessen (--wegen fehlt)"
        except Ablehnung as e:
            assert "Pflicht" in str(e)

        # dry-run: nichts geschrieben.
        dry = bestaetigen(db_path, "/standard/alt", "Testgrund", apply=False, now=_now)
        assert dry["backup"] is None
        conn = sqlite3.connect(str(db_path))
        zwischen = conn.execute("SELECT updated_at FROM knowledge_nodes WHERE path='/standard/alt'").fetchone()[0]
        conn.close()
        assert zwischen != dry["nachher_updated_at"], "dry-run darf nichts schreiben"

        # Erfolgsfall: "n-alt" ist Regime 3 (kein Dateibezug) -- kein
        # Verfallswert, gerechnete_konfidenz() zeigt daher unveraendert den
        # Ausgangswert, vor UND nach der Bestaetigung. bestaetigen() setzt
        # trotzdem den Bezugszeitpunkt zurueck (fuer die naechste_pruefung-
        # Faelligkeit relevant) -- das ist unabhaengig vom Regime.
        ok = bestaetigen(db_path, "/standard/alt", "Testgrund fuer Bestaetigung", apply=True, now=_now)
        assert ok["vorher_gerechnet"] == 0.8, ok["vorher_gerechnet"]
        assert ok["nachher_gerechnet"] == 0.8, ok["nachher_gerechnet"]
        assert ok["backup"] and Path(ok["backup"]).exists()
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute("SELECT updated_at, content, confidence FROM knowledge_nodes WHERE path='/standard/alt'").fetchone()
            assert row["updated_at"] == ok["nachher_updated_at"]
            assert row["confidence"] == 0.8, "confidence-Spalte bleibt der Ausgangswert, wird nie ueberschrieben"
            assert "Testgrund fuer Bestaetigung" in row["content"]
            log_row = conn.execute(
                "SELECT action, query, node_path FROM access_log WHERE action='bestaetigt' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            assert log_row["query"] == "Testgrund fuer Bestaetigung"
            assert log_row["node_path"] == "/standard/alt"
        finally:
            conn.close()

        # Ablehnung ohne Begruendung ueber die oeffentliche Funktion (nicht
        # nur plan_bestaetigen direkt) -- apply=True darf trotzdem nichts
        # schreiben, wenn die Ablehnung VOR dem Schreiben greift.
        try:
            bestaetigen(db_path, "/standard/alt", "   ", apply=True, now=_now)
            assert False, "haette ablehnen muessen (--wegen nur Leerzeichen)"
        except Ablehnung:
            pass

        # find_confidence_decay(): braucht Regime 1 (Dateibezug), Regime 3 kann
        # NIE darin auftauchen (kein Verfallswert -> keine Zahl unter der
        # Schwelle). Fixture: Datei mit vielen Commits seit updated_at.
        verfallen_zeiten = [_mk_ts(200 - 2 * i) for i in range(50)]  # 50 Commits, Tag -200..-102
        verfallen_datei = _mk_git_repo(tmp_path, "verfallen.md", verfallen_zeiten)
        updated_verfallen = (datetime.fromisoformat(verfallen_zeiten[0]) + timedelta(seconds=1)).isoformat()
        conn = sqlite3.connect(str(db_path))
        _insert_node(conn, "n-verfallen", "/testing/verfallen", confidence=0.8,
                     updated_at=updated_verfallen, source=f"erzeugt aus {verfallen_datei}")
        conn.commit()
        conn.row_factory = sqlite3.Row
        try:
            decay = find_confidence_decay(conn, now=_now)
            ueberfaellig = find_pruefung_ueberfaellig(conn, now=_now)
        finally:
            conn.close()
        decay_paths = {d["path"] for d in decay}
        assert "/testing/verfallen" in decay_paths, decay_paths
        assert decay_paths <= {"/testing/verfallen"}, decay_paths  # weder n-alt (Regime 3) noch die Norm
        assert "/adr/x" not in decay_paths, "Norm darf nie im Konfidenzverfall auftauchen"
        # find_pruefung_ueberfaellig(): das Gegenstueck fuer Regime 3 -- n-alt
        # wurde gerade erst bestaetigt (updated_at=jetzt), also NICHT ueberfaellig.
        ueberfaellig_paths = {u["path"] for u in ueberfaellig}
        assert "/standard/alt" not in ueberfaellig_paths, ueberfaellig_paths
        assert "/testing/verfallen" not in ueberfaellig_paths, "Regime 1 gehoert nicht ins Regime-3-Gegenstueck"

    print("SELFTEST bestaetigen OK: 4 Ablehnungen, dry-run, Erfolgsfall (Content+access_log+Reset), "
          "find_confidence_decay() findet nur Regime-1-Verfallene, find_pruefung_ueberfaellig() "
          "das Regime-3-Gegenstueck, nie Normen in beiden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
