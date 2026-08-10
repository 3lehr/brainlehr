#!/usr/bin/env python3
"""normkraft.py -- Auftrag docs/PLAN_NORMSCHICHT_2026-08-05.md, letztes Glied.

N1..N4 liefern Rang (normrang.py), Widerspruchskandidaten (knowledge_lint.py)
und Geltungsbereich (geltungsbereich.py) -- aber nichts kann `gilt_bis`
tatsaechlich setzen. Gemessen 2026-08-06: kein Schreibvorgang in
shared-knowledge/*.py trifft die Spalte, sie ist so tot wie `confidence`
(183/237 auf dem eingefrorenen Vorgabewert) und `access_count` (19/237 ueber
Null) vor ihr. Dieses Skript ist das fehlende Verb: eine Norm ausser Kraft
setzen, mit Pflichtgrund, und die Gegenprobe dazu (welche Normen galten an
einem Stichtag).

Kein Ermessen ueber WELCHE Norm abgeloest ist -- das entscheidet der
Betreiber aus den Lint-Kandidaten. Dieses Skript wendet nur an.

Grund-Ablage: content-Feld des Knotens (angehaengt, nicht ueberschrieben) UND
access_log-Zeile (action='ausser_kraft', query=Grund, node_path=Pfad). Zwei
Orte, nicht einer: content ist da, wo jeder Leser des Knotens ihn sofort
sieht (kein zweiter Lookup noetig); access_log ist die bereits vorhandene
Auditspur der DB (schema.sql-Kommentar: "wer hat wann was abgefragt/
geaendert"), dort gehoert jede schreibende Aktion hin, unabhaengig davon,
ob sie zusaetzlich im Content sichtbar ist. Kein neues Feld, keine
Schemaaenderung. zeilen_hash/ketten_hash bleiben NULL: die Kettenberechnung
lebt in knowledge_mcp_server.py::log_access() (tabu fuer diesen Auftrag),
direkte SQL-Skripte (normrang.py, migrate_normfelder.py) gehen grundsaetzlich
an dieser Funktion vorbei -- gleiches Muster wie migrate_auditkette.py es
fuer Bestandszeilen vor der Migration beschreibt: NULL ist ein gueltiger
Zustand, keine spaeter nachgetragene Kette waere ein Beweis.

Backup-Muster identisch zu normrang.py::_backup() / build_embeddings.py
(WAL-Checkpoint vor dem Kopieren, Abbruch bei parallelem Schreiber -- Fund
aus 2cb22705f: eine Kopie ohne Checkpoint kann committete, aber noch nicht
zurueckgeschriebene WAL-Aenderungen verlieren).

Usage:
    .venv/bin/python shared-knowledge/normkraft.py ausser_kraft <pfad> --ab <ISO> --wegen <text> [--abgeloest-durch <pfad>] [--apply]
    .venv/bin/python shared-knowledge/normkraft.py in_kraft [--stichtag <ISO>]
    .venv/bin/python shared-knowledge/normkraft.py --selftest
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
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = _w
DB_PATH = HERE / "knowledge.db"
CET = timezone(timedelta(hours=1))


def _backup(db_path: Path) -> Path:
    """Identisch zu normrang.py::_backup() -- WAL-Checkpoint vor dem
    Kopieren, sonst fehlen committete, aber noch nicht zurueckgeschriebene
    Aenderungen in der Sicherung (Fund 2cb22705f)."""
    conn = sqlite3.connect(str(db_path))
    try:
        busy, _frames, _checkpointed = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if busy:
            raise RuntimeError(
                "WAL-Checkpoint blockiert -- ein anderer Prozess schreibt gerade. Abbruch."
            )
    finally:
        conn.close()
    stamp = datetime.now(CET).strftime("%Y%m%dT%H%M%S")
    dest = db_path.parent / f"knowledge.db.bak-{stamp}"
    shutil.copy2(db_path, dest)
    return dest


def now_iso() -> str:
    return datetime.now(CET).strftime("%Y-%m-%dT%H:%M:%S%z")


class Ablehnung(Exception):
    """Eine der geschuetzten Ablehnungen -- kein Programmierfehler, ein
    gewolltes Nein. main() faengt sie ab und druckt die Meldung."""


def _lade_norm(conn: sqlite3.Connection, pfad: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT id, path, title, content, norm_rang, gilt_ab, gilt_bis FROM knowledge_nodes WHERE path = ?",
        (pfad,),
    ).fetchone()
    if row is None:
        raise Ablehnung(f"Pfad nicht gefunden: {pfad}")
    if row["norm_rang"] is None:
        raise Ablehnung(f"{pfad} ist keine Norm (norm_rang IS NULL) -- kein Traeger fuer gilt_bis.")
    return row


def plan_ausser_kraft(db_path: Path, pfad: str, ab: str, wegen: str,
                       abgeloest_durch: str | None) -> dict:
    """Berechnet den Zielzustand, schreibt nichts. Wirft Ablehnung bei jedem
    der vier geschuetzten Faelle."""
    if not wegen or not wegen.strip():
        raise Ablehnung("--wegen ist Pflicht -- eine Norm ohne Grund ausser Kraft zu setzen ist spaeter nicht nachvollziehbar.")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        row = _lade_norm(conn, pfad)

        if row["gilt_bis"] is not None:
            raise Ablehnung(
                f"{pfad} ist bereits ausser Kraft seit {row['gilt_bis']}."
            )

        gilt_ab = row["gilt_ab"]
        if gilt_ab is not None and ab < gilt_ab:
            raise Ablehnung(
                f"--ab {ab} liegt vor gilt_ab ({gilt_ab}) von {pfad} -- eine Norm kann nicht vor ihrem Inkrafttreten ausser Kraft treten."
            )

        ziel_row = None
        if abgeloest_durch is not None:
            ziel_row = conn.execute(
                "SELECT path, norm_rang FROM knowledge_nodes WHERE path = ?",
                (abgeloest_durch,),
            ).fetchone()
            if ziel_row is None:
                raise Ablehnung(f"--abgeloest-durch Pfad nicht gefunden: {abgeloest_durch}")
            if ziel_row["norm_rang"] is None:
                raise Ablehnung(
                    f"--abgeloest-durch {abgeloest_durch} ist keine Norm (norm_rang IS NULL) -- Abloesung durch einen Fakt ist kein gueltiger Vorgang."
                )

        notiz = f"\n\n[ausser Kraft ab {ab}: {wegen.strip()}"
        if abgeloest_durch:
            notiz += f" -- abgeloest durch {abgeloest_durch}"
        notiz += "]"

        return {
            "pfad": pfad,
            "id": row["id"],
            "vorher_gilt_bis": row["gilt_bis"],
            "nachher_gilt_bis": ab,
            "content_anhang": notiz,
            "wegen": wegen.strip(),
            "abgeloest_durch": abgeloest_durch,
        }
    finally:
        conn.close()


def ausser_kraft(db_path: Path, pfad: str, ab: str, wegen: str,
                  abgeloest_durch: str | None, apply: bool) -> dict:
    result = plan_ausser_kraft(db_path, pfad, ab, wegen, abgeloest_durch)
    result["backup"] = None
    if not apply:
        return result

    result["backup"] = str(_backup(db_path))
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT content FROM knowledge_nodes WHERE id = ?", (result["id"],)
        ).fetchone()
        neuer_content = (row[0] or "") + result["content_anhang"]
        # norm_entscheidung (Nachtrag 2026-08-08): ein gesetztes gilt_bis
        # macht aus einer norm_unbefristet-en Norm eine norm_befristet-e --
        # dieselbe Aenderung wie knowledge_update() sie fuer diesen Fall
        # verlangt. wegen ist bereits eine Pflichtangabe des Aufrufers
        # (siehe unten), wird hier fuer norm_entschieden_grund wiederverwendet
        # statt eine zweite Begruendung zu verlangen.
        jetzt = now_iso()
        conn.execute(
            "UPDATE knowledge_nodes SET gilt_bis = ?, content = ?, updated_at = ?, "
            "norm_entscheidung = 'norm_befristet', norm_entschieden_von = ?, "
            "norm_entschieden_am = ?, norm_entschieden_grund = ? WHERE id = ?",
            (ab, neuer_content, jetzt, "skript:normkraft.py", jetzt, wegen.strip(), result["id"]),
        )
        conn.execute(
            """INSERT INTO access_log (node_path, action, query, status, timestamp)
               VALUES (?, 'ausser_kraft', ?, 'completed', ?)""",
            (pfad, wegen.strip(), now_iso()),
        )
        conn.commit()
    finally:
        conn.close()
    return result


def in_kraft(db_path: Path, stichtag: str | None = None) -> list[dict]:
    """Normen, die zum Stichtag (Vorgabe: jetzt) in Kraft waren.

    KANONISCHE BEDEUTUNG von gilt_bis, hier und nirgends sonst festgelegt --
    jeder weitere Auswerter (z.B. knowledge_mcp_server.py::_geltung_status)
    verweist hierher statt die Regel erneut zu formulieren: gilt_bis ist
    INKLUSIV, der letzte Tag, an dem die Norm noch gilt. Entscheidung
    2026-08-06 (Auftrag): das Feld traegt in der Praxis Datumsangaben, und
    "gilt bis 31.12." heisst umgangssprachlich wie juristisch einschliesslich
    des 31.12. Formel: gilt_ab <= stichtag AND (gilt_bis IS NULL OR gilt_bis
    >= stichtag)."""
    stichtag = stichtag or now_iso()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT path, title, norm_rang, gilt_ab, gilt_bis FROM knowledge_nodes
               WHERE norm_rang IS NOT NULL
                 AND gilt_ab IS NOT NULL AND gilt_ab <= ?
                 AND (gilt_bis IS NULL OR gilt_bis >= ?)
               ORDER BY norm_rang, path""",
            (stichtag, stichtag),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


# --- CLI ---------------------------------------------------------------

def _print_ausser_kraft(result: dict, mode: str) -> None:
    print(f"=== normkraft ausser_kraft ({mode}) ===")
    print(f"Pfad: {result['pfad']}")
    print(f"gilt_bis: {result['vorher_gilt_bis']!r} -> {result['nachher_gilt_bis']!r}")
    print(f"wegen: {result['wegen']}")
    if result["abgeloest_durch"]:
        print(f"abgeloest durch: {result['abgeloest_durch']}")
    if result.get("backup"):
        print(f"Sicherung: {result['backup']}")


def _print_in_kraft(rows: list[dict], stichtag: str) -> None:
    print(f"=== normkraft in_kraft (Stichtag {stichtag}) ===")
    print(f"Normen in Kraft: {len(rows)}")
    for r in rows:
        print(f"  Rang {r['norm_rang']}  {r['path']}  ({r['title']})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--selftest", action="store_true")
    sub = parser.add_subparsers(dest="cmd")

    p_ak = sub.add_parser("ausser_kraft")
    p_ak.add_argument("pfad")
    p_ak.add_argument("--ab", required=True, help="ISO-Zeitpunkt, ab dem die Norm ausser Kraft ist")
    p_ak.add_argument("--wegen", required=True, help="Pflicht: Grund fuer die Ausserkraftsetzung")
    p_ak.add_argument("--abgeloest-durch", default=None, help="optional: Pfad der ablösenden Norm")
    p_ak.add_argument("--apply", action="store_true", help="tatsaechlich schreiben (Vorgabe: --dry-run)")
    p_ak.add_argument("--dry-run", action="store_true", help="Vorgabe, nur zur Klarheit explizit angebbar")

    p_ik = sub.add_parser("in_kraft")
    p_ik.add_argument("--stichtag", default=None, help="ISO-Zeitpunkt, Vorgabe: jetzt")

    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()

    if args.cmd is None:
        parser.print_help()
        return 1

    if not DB_PATH.exists():
        print(f"FEHLER: {DB_PATH} nicht gefunden.")
        return 1

    if args.cmd == "ausser_kraft":
        try:
            result = ausser_kraft(DB_PATH, args.pfad, args.ab, args.wegen,
                                   getattr(args, "abgeloest_durch"), apply=args.apply)
        except Ablehnung as exc:
            print(f"ABGELEHNT: {exc}")
            return 1
        _print_ausser_kraft(result, "APPLY" if args.apply else "DRY-RUN (kein --apply)")
        return 0

    if args.cmd == "in_kraft":
        stichtag = args.stichtag or now_iso()
        rows = in_kraft(DB_PATH, args.stichtag)
        _print_in_kraft(rows, stichtag)
        return 0

    parser.print_help()
    return 1


# --- Selbsttest ----------------------------------------------------------

def _init_temp_db(path: Path) -> None:
    schema_sql = (HERE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(path))
    conn.executescript(schema_sql)
    conn.close()


def _insert_node(conn: sqlite3.Connection, node_id: str, path: str, *, norm_rang: int | None,
                  gilt_ab: str | None, gilt_bis: str | None = None, content: str = "") -> None:
    # norm_entscheidung (Auftrag 2026-08-08): dieses Modul PRUEFT Normkraft
    # (Ausserkraftsetzung), norm_rang=None steht hier ausdruecklich fuer
    # "kein Normtraeger" (test_ablehnung_kein_norm_traeger) -- keine_norm.
    # Sonst Norm: befristet, wenn der Aufrufer ein gilt_bis mitgibt, sonst
    # unbefristet. Folgt direkt aus den Aufrufer-Parametern, kein Raten.
    norm_entscheidung = "keine_norm" if norm_rang is None else (
        "norm_befristet" if gilt_bis is not None else "norm_unbefristet")
    # norm_entschieden_* (Nachtrag 2026-08-08): dieser Helfer selbst ist der
    # Entscheider, Begruendung folgt aus demselben Parameter wie oben.
    grund = ("Testvorrichtung ohne Rang -- kein Normtraeger" if norm_rang is None
             else "Testvorrichtung: Normkraft-Test braucht einen echten Normtraeger")
    zeitpunkt = gilt_ab or "2026-01-01T00:00:00+01:00"
    conn.execute(
        """INSERT INTO knowledge_nodes
           (id, path, parent_path, project_id, title, summary, content, level, tags,
            created_at, updated_at, norm_rang, gilt_ab, gilt_bis, norm_entscheidung,
            norm_entschieden_von, norm_entschieden_am, norm_entschieden_grund, source)
           VALUES (?, ?, '/', 'shared', ?, 'summary', ?, 1, '[]', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'selftest')""",
        (node_id, path, node_id, content, zeitpunkt, zeitpunkt, norm_rang, gilt_ab, gilt_bis,
         norm_entscheidung, "skript:normkraft.py", zeitpunkt, grund),
    )


def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "knowledge.db"
        _init_temp_db(db_path)

        conn = sqlite3.connect(str(db_path))
        try:
            _insert_node(conn, "n-adr", "/adr/x", norm_rang=3, gilt_ab="2026-01-01T00:00:00+01:00")
            _insert_node(conn, "n-adr2", "/adr/y", norm_rang=3, gilt_ab="2026-01-01T00:00:00+01:00")
            _insert_node(conn, "n-fakt", "/fakt/x", norm_rang=None, gilt_ab=None)
            _insert_node(conn, "n-schon-tot", "/adr/z", norm_rang=3, gilt_ab="2026-01-01T00:00:00+01:00",
                         gilt_bis="2026-02-01T00:00:00+01:00")
            conn.commit()
        finally:
            conn.close()

        # --- Rot vor gruen: vor jedem Schreiben ist gilt_bis fuer /adr/x NULL,
        # und nichts in diesem Skript konnte es bisher setzen (das Skript
        # selbst existierte nicht -- der Import oben waere rot gewesen).
        conn = sqlite3.connect(str(db_path))
        vorher = conn.execute("SELECT gilt_bis FROM knowledge_nodes WHERE path='/adr/x'").fetchone()[0]
        conn.close()
        assert vorher is None, "rot-Fall verletzt: gilt_bis war schon vor dem Verb gesetzt"

        # --- Ablehnung 1: Pfad existiert nicht.
        try:
            plan_ausser_kraft(db_path, "/nirgends", "2026-03-01T00:00:00+01:00", "Test", None)
            assert False, "haette ablehnen muessen (Pfad fehlt)"
        except Ablehnung as e:
            assert "nicht gefunden" in str(e)

        # --- Ablehnung 2: kein Norm-Knoten (norm_rang IS NULL).
        try:
            plan_ausser_kraft(db_path, "/fakt/x", "2026-03-01T00:00:00+01:00", "Test", None)
            assert False, "haette ablehnen muessen (kein Norm-Traeger)"
        except Ablehnung as e:
            assert "keine Norm" in str(e)

        # --- Ablehnung 3: gilt_bis vor gilt_ab.
        try:
            plan_ausser_kraft(db_path, "/adr/x", "2025-01-01T00:00:00+01:00", "Test", None)
            assert False, "haette ablehnen muessen (--ab vor gilt_ab)"
        except Ablehnung as e:
            assert "vor gilt_ab" in str(e)

        # --- Ablehnung 4: bereits ausser Kraft.
        try:
            plan_ausser_kraft(db_path, "/adr/z", "2026-03-01T00:00:00+01:00", "Test", None)
            assert False, "haette ablehnen muessen (schon ausser Kraft)"
        except Ablehnung as e:
            assert "bereits ausser Kraft" in str(e) and "2026-02-01" in str(e)

        # --- Ablehnung 5 (Pflichtgrund fehlt).
        try:
            plan_ausser_kraft(db_path, "/adr/x", "2026-03-01T00:00:00+01:00", "", None)
            assert False, "haette ablehnen muessen (--wegen fehlt)"
        except Ablehnung as e:
            assert "Pflicht" in str(e)

        # --- Ablehnung 6 (abgeloest-durch ist ein Fakt, kein Norm).
        try:
            plan_ausser_kraft(db_path, "/adr/x", "2026-03-01T00:00:00+01:00", "Test", "/fakt/x")
            assert False, "haette ablehnen muessen (Abloesung durch Fakt)"
        except Ablehnung as e:
            assert "kein gueltiger Vorgang" in str(e)

        # --- Ablehnung 7 (abgeloest-durch existiert nicht).
        try:
            plan_ausser_kraft(db_path, "/adr/x", "2026-03-01T00:00:00+01:00", "Test", "/nirgends")
            assert False, "haette ablehnen muessen (Zielpfad fehlt)"
        except Ablehnung as e:
            assert "nicht gefunden" in str(e)

        # --- dry-run: nichts geschrieben.
        dry = ausser_kraft(db_path, "/adr/x", "2026-03-01T00:00:00+01:00", "Testgrund", "/adr/y", apply=False)
        assert dry["backup"] is None
        conn = sqlite3.connect(str(db_path))
        zwischen = conn.execute("SELECT gilt_bis FROM knowledge_nodes WHERE path='/adr/x'").fetchone()[0]
        conn.close()
        assert zwischen is None, "dry-run darf nichts schreiben"

        # --- Erfolgsfall: gruen. gilt_bis gesetzt, Backup da, Grund im Content
        # UND in access_log.
        ok = ausser_kraft(db_path, "/adr/x", "2026-03-01T00:00:00+01:00", "Testgrund", "/adr/y", apply=True)
        assert ok["backup"] and Path(ok["backup"]).exists()
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute("SELECT gilt_bis, content FROM knowledge_nodes WHERE path='/adr/x'").fetchone()
            assert row["gilt_bis"] == "2026-03-01T00:00:00+01:00"
            assert "Testgrund" in row["content"]
            assert "/adr/y" in row["content"]
            log_row = conn.execute(
                "SELECT action, query, node_path FROM access_log WHERE action='ausser_kraft' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            assert log_row["query"] == "Testgrund"
            assert log_row["node_path"] == "/adr/x"
        finally:
            conn.close()

        # --- Idempotenz: zweiter Versuch auf derselbe Norm lehnt ab (schon
        # ausser Kraft), Bestand aendert sich nicht dabei.
        try:
            ausser_kraft(db_path, "/adr/x", "2026-04-01T00:00:00+01:00", "Nochmal", None, apply=True)
            assert False, "zweite Ausserkraftsetzung haette ablehnen muessen"
        except Ablehnung as e:
            assert "bereits ausser Kraft" in str(e)
        conn = sqlite3.connect(str(db_path))
        gilt_bis_final = conn.execute("SELECT gilt_bis FROM knowledge_nodes WHERE path='/adr/x'").fetchone()[0]
        conn.close()
        assert gilt_bis_final == "2026-03-01T00:00:00+01:00", "Idempotenz verletzt: zweiter Lauf haette nichts aendern duerfen"

        # --- Gegenprobe in_kraft: vor und nach dem Stichtag.
        vor = in_kraft(db_path, "2026-02-01T00:00:00+01:00")
        vor_pfade = {r["path"] for r in vor}
        assert "/adr/x" in vor_pfade, "vor dem Ausserkrafttreten muss /adr/x in Kraft sein"

        # --- Grenzwert: gilt_bis ist inklusiv -- am Tag von gilt_bis selbst
        # gilt die Norm noch (letzter Tag), erst danach nicht mehr.
        am_stichtag = in_kraft(db_path, "2026-03-01T00:00:00+01:00")
        assert "/adr/x" in {r["path"] for r in am_stichtag}, "gilt_bis inklusiv: am Stichtag == gilt_bis muss /adr/x noch in Kraft sein"

        nach = in_kraft(db_path, "2026-04-01T00:00:00+01:00")
        nach_pfade = {r["path"] for r in nach}
        assert "/adr/x" not in nach_pfade, "nach dem Ausserkrafttreten darf /adr/x nicht mehr in Kraft sein"
        assert "/adr/y" in nach_pfade, "unbefristete Norm /adr/y muss weiter in Kraft sein"
        assert "/fakt/x" not in nach_pfade and "/fakt/x" not in vor_pfade, "Fakt darf nie in in_kraft auftauchen"

    print("SELFTEST OK: 7 Ablehnungen, dry-run, Erfolgsfall (Content+access_log), Idempotenz, in_kraft vor/Stichtag/nach (gilt_bis inklusiv).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
