#!/usr/bin/env python3
"""konfidenz.py -- ADR-026, Z3 letztes Stueck: Konfidenzverfall.

Alter und Herkunft sind erfuellt (Alter im Recall, `source` Pflicht,
`quell_hash`), Rang/Geltung sind erfuellt (normrang.py/normkraft.py). Was
fehlt: die confidence-Spalte hat sich seit Bestehen nie veraendert (183 von
237 auf dem Schema-Vorgabewert 0.8, siehe knowledge_lint.py::
find_confidence_default_age, K3). Dieses Skript liefert das fehlende Verb.

Zwei Dinge, die NICHT vermischt werden duerfen (ADR-024, Gespraech
2026-08-05):
  - FAKTEN (norm_rang IS NULL) verfallen: ohne Bestaetigung sinkt die
    gerechnete Konfidenz mit der Zeit, Kalman-artig (Zustand + wachsende
    Unsicherheit ohne neue Messung).
  - NORMEN (norm_rang IS NOT NULL) verfallen NICHT. Sie gelten oder gelten
    nicht (gilt_ab/gilt_bis, normkraft.py) -- eine Direktive wird nicht
    unsicherer, sie tritt ausser Kraft. gerechnete_konfidenz() gibt fuer
    Normen daher IMMER den unveraenderten Ausgangswert zurueck, unabhaengig
    vom Alter.

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

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from normkraft import Ablehnung, _backup, now_iso, CET  # noqa: E402

DB_PATH = HERE / "knowledge.db"

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


def gerechnete_konfidenz(confidence: float, updated_at: str | None, norm_rang: int | None,
                          path: str, source: str | None, now: datetime) -> float:
    """Kern der ganzen Datei. Normen (norm_rang IS NOT NULL) verfallen NIE
    -- unveraenderter Ausgangswert, unabhaengig von Alter oder updated_at.
    Fakten verfallen exponentiell mit Halbwertszeit je Wissensart:
        aktuell = ausgangswert * 0.5 ** (alter_tage / halbwertszeit_tage)
    Bei alter_tage=0 -> ausgangswert. Bei alter_tage=halbwertszeit ->
    die Haelfte. Bei 2x Halbwertszeit -> ein Viertel."""
    if norm_rang is not None:
        return confidence
    if not updated_at:
        return confidence
    hwz = HALBWERTSZEIT_TAGE[wissensart(path, source)]
    tage = alter_tage(updated_at, now)
    return confidence * (0.5 ** (tage / hwz))


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
        g = gerechnete_konfidenz(r["confidence"], r["updated_at"], r["norm_rang"], r["path"], r["source"], now)
        werte.append({"path": r["path"], "title": r["title"], "ausgangswert": r["confidence"],
                      "gerechnet": round(g, 4), "alter_tage": round(alter_tage(r["updated_at"], now), 1)
                      if r["updated_at"] else None})
    unter_schwelle = [w for w in werte if w["gerechnet"] < KONFIDENZ_SCHWELLE]
    aeltester = max((w for w in werte if w["alter_tage"] is not None), key=lambda w: w["alter_tage"], default=None)
    buckets = {"1.0-0.8": 0, "0.8-0.6": 0, "0.6-0.4": 0, "0.4-0.2": 0, "0.2-0.0": 0}
    for w in werte:
        g = w["gerechnet"]
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
    return {
        "gesamt": len(werte),
        "buckets": buckets,
        "schwelle": KONFIDENZ_SCHWELLE,
        "unter_schwelle_anzahl": len(unter_schwelle),
        "aeltester": aeltester,
    }


# ─── Lint-Integration: Kategorie 14 ─────────────────────────────────────────

def find_confidence_decay(conn: sqlite3.Connection, now: datetime | None = None,
                           schwelle: float = KONFIDENZ_SCHWELLE) -> list[dict]:
    """Fuer knowledge_lint.py: Fakten (norm_rang IS NULL), deren gerechnete
    Konfidenz unter die Schwelle gefallen ist. conn darf read-only sein --
    diese Funktion schreibt nichts."""
    now = now or datetime.now(CET)
    rows = conn.execute(
        "SELECT path, title, confidence, norm_rang, updated_at, source "
        "FROM knowledge_nodes WHERE norm_rang IS NULL"
    ).fetchall()
    out = []
    for r in rows:
        g = gerechnete_konfidenz(r["confidence"], r["updated_at"], r["norm_rang"], r["path"], r["source"], now)
        if g < schwelle:
            out.append({
                "path": r["path"], "title": r["title"], "ausgangswert": r["confidence"],
                "gerechnet": round(g, 4),
                "alter_tage": round(alter_tage(r["updated_at"], now), 1) if r["updated_at"] else None,
            })
    out.sort(key=lambda i: i["gerechnet"])
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
    art = wissensart(row["path"], row["source"])
    hwz = HALBWERTSZEIT_TAGE[art]
    g = gerechnete_konfidenz(row["confidence"], row["updated_at"], row["norm_rang"], row["path"], row["source"], now)
    print(f"Pfad: {row['path']}")
    print(f"norm_rang: {row['norm_rang']!r}")
    print(f"Ausgangswert (confidence-Spalte): {row['confidence']}")
    if row["norm_rang"] is not None:
        print("Norm -- verfaellt nicht, gerechnete Konfidenz == Ausgangswert.")
        return
    alter = alter_tage(row["updated_at"], now) if row["updated_at"] else None
    print(f"Wissensart: {art} (Halbwertszeit {hwz} Tage, geraten)")
    print(f"Alter seit updated_at: {alter} Tage" if alter is not None else "Alter: unbekannt (updated_at leer)")
    print(f"gerechnete Konfidenz: {round(g, 4)}")


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
        for bucket, n in v["buckets"].items():
            print(f"  {bucket}: {n}")
        print(f"Unter Schwelle: {v['unter_schwelle_anzahl']}")
        if v["aeltester"]:
            a = v["aeltester"]
            print(f"Aeltester Fakt: {a['path']} ({a['alter_tage']} Tage, gerechnet {a['gerechnet']})")
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
    conn.execute(
        """INSERT INTO knowledge_nodes
           (id, path, parent_path, project_id, title, summary, content, level, tags,
            created_at, updated_at, confidence, norm_rang, source)
           VALUES (?, ?, '/', 'shared', ?, 'summary', ?, 1, '[]', ?, ?, ?, ?, ?)""",
        (node_id, path, node_id, content, updated_at, updated_at, confidence, norm_rang, source),
    )


def _selftest() -> int:
    import tempfile

    # --- Reine Formel, von Hand nachgerechnet (Abnahme 1) --------------------
    _now = datetime.fromisoformat("2026-04-11T00:00:00+01:00")  # beliebiger fixer Referenzpunkt

    def _mk_ts(tage_zurueck: float) -> str:
        from datetime import timedelta
        return (_now - timedelta(days=tage_zurueck)).isoformat()

    # Null Alter -> voller Ausgangswert.
    g0 = gerechnete_konfidenz(0.8, _mk_ts(0), None, "/standard/x", None, _now)
    assert abs(g0 - 0.8) < 1e-9, g0

    # Genau eine Halbwertszeit (WISSENSART_STANDARD=120 Tage) -> exakt die Haelfte.
    g_half = gerechnete_konfidenz(0.8, _mk_ts(HALBWERTSZEIT_TAGE[WISSENSART_STANDARD]), None, "/standard/x", None, _now)
    assert abs(g_half - 0.4) < 1e-9, g_half  # 0.8 * 0.5**1 = 0.4, von Hand nachgerechnet

    # Zwei Halbwertszeiten -> ein Viertel.
    g_quarter = gerechnete_konfidenz(
        0.8, _mk_ts(2 * HALBWERTSZEIT_TAGE[WISSENSART_STANDARD]), None, "/standard/x", None, _now
    )
    assert abs(g_quarter - 0.2) < 1e-9, g_quarter  # 0.8 * 0.5**2 = 0.2, von Hand nachgerechnet

    # --- Gegenprobe, die den Kern schuetzt: Norm verfaellt NIE ---------------
    g_norm_jung = gerechnete_konfidenz(0.9, _mk_ts(0), 1, "/adr/x", "ADR", _now)
    g_norm_uralt = gerechnete_konfidenz(0.9, _mk_ts(20000), 1, "/adr/x", "ADR", _now)  # ~55 Jahre
    assert g_norm_jung == 0.9 and g_norm_uralt == 0.9, (g_norm_jung, g_norm_uralt)

    # --- Wissensart-Klassifikation, deterministisch -----------------------
    assert wissensart("/arch/mcp", None) == WISSENSART_ARCHITEKTUR
    assert wissensart("/shared/irgendwas", "Konsil 2026-08-05") == WISSENSART_ARCHITEKTUR
    assert wissensart("/shared/irgendwas", "docs/adr/ADR-026.md") == WISSENSART_ARCHITEKTUR
    assert wissensart("/testing/pytest", None) == WISSENSART_BETRIEB
    assert wissensart("/ops/appstoreconnect", None) == WISSENSART_BETRIEB
    assert wissensart("/lessons", None) == WISSENSART_STANDARD

    print("SELFTEST Formel OK: alter=0 -> voll, alter=1xHWZ -> Haelfte, alter=2xHWZ -> Viertel, "
          "Norm unveraendert bei jedem Alter, Wissensart-Klassifikation deterministisch.")

    # --- bestaetigen(): DB-Rundfahrt -----------------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "knowledge.db"
        _init_temp_db(db_path)

        conn = sqlite3.connect(str(db_path))
        try:
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

        # Erfolgsfall: Konfidenz vor der Bestaetigung ist verfallen (Halbwertszeit
        # alt -> ~0.4), danach zurueck auf den Ausgangswert 0.8. Bezugszeitpunkt
        # neu, Grund im Content UND im access_log.
        ok = bestaetigen(db_path, "/standard/alt", "Testgrund fuer Bestaetigung", apply=True, now=_now)
        assert abs(ok["vorher_gerechnet"] - 0.4) < 1e-6, ok["vorher_gerechnet"]
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

        # find_confidence_decay(): der frisch bestaetigte Knoten liegt ueber der
        # Schwelle, ein zusaetzlich sehr alter Knoten darunter, die Norm nie dabei.
        conn = sqlite3.connect(str(db_path))
        _insert_node(conn, "n-verfallen", "/standard/verfallen", confidence=0.8,
                     updated_at=_mk_ts(5 * HALBWERTSZEIT_TAGE[WISSENSART_STANDARD]))
        conn.commit()
        conn.row_factory = sqlite3.Row
        try:
            decay = find_confidence_decay(conn, now=_now)
        finally:
            conn.close()
        decay_paths = {d["path"] for d in decay}
        assert "/standard/verfallen" in decay_paths, decay_paths
        assert "/standard/alt" not in decay_paths, decay_paths  # frisch bestaetigt bzw. nur Alt-Fixture vor Reset
        assert "/adr/x" not in decay_paths, "Norm darf nie im Konfidenzverfall auftauchen"

    print("SELFTEST bestaetigen OK: 4 Ablehnungen, dry-run, Erfolgsfall (Content+access_log+Reset), "
          "find_confidence_decay() findet Verfallene, nie Normen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
