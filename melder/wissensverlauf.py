#!/usr/bin/env python3
"""Wissensverlauf -- Zeitreihe der Knowledge-Lint-Kennzahlen.

knowledge_lint.py rechnet bei jedem Lauf sieben Befundzahlen und drei
Struktur-Kennzahlen, speichert aber keine davon -- keine Reihe, kein
Vergleich, keine Aussage ueber Verbesserung. Dieses Skript haengt jeden
Lauf als eine Zeile an wissensverlauf.jsonl (append-only, nur Zahlen,
keine Fundstellen) und meldet auf Wunsch nur, was sich geaendert hat.

Zwei Unterbefehle:
  aufzeichnen  -- ruft knowledge_lint.run() auf (importiert, nicht
                  nachgebaut), haengt eine Zeile an.
  differenz    -- vergleicht letzten Lauf gegen vorletzten (oder gegen
                  einen per --gegen gewaehlten Zeitpunkt), meldet nur
                  Abweichungen. Bei Gleichstand: keine Ausgabe.

knowledge_lint.py wird importiert, nie geaendert. Rein lesend gegenueber
brainlehr.db (ueber knowledge_lint.run(), Verbindung mode=ro).
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
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SHARED_KNOWLEDGE = _w
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_lint  # noqa: E402

HISTORY_PATH = SHARED_KNOWLEDGE / "wissensverlauf.jsonl"

# Reihenfolge = Meldereihenfolge in differenz(). Label ist deutsch, fuer
# die Satzbildung dort.
FIELDS: list[tuple[str, str]] = [
    ("corpus_size", "Korpusgroesse (Knoten)"),
    ("orphans", "Waisen"),
    ("stale", "Karteileichen"),
    ("never_pulled_nodes", "nie gezogene Knoten"),
    ("never_pulled_lessons", "nie gezogene Lehren"),
    ("vector_gaps", "Vektor-Luecken"),
    ("near_duplicate_lessons", "Beinahe-Dubletten"),
    ("path_hygiene", "Pfad-Hygiene-Funde"),
    ("truncated_embeddings", "abgeschnittene Einbettungen"),
    ("avg_degree", "mittlerer Grad"),
    ("cross_project_lessons", "projektuebergreifende Lessons"),
    ("confidence_default_count", "Knoten auf Konfidenz-Vorgabewert"),
]


def build_record(result: dict, ts: datetime) -> dict:
    """Nur Zahlen + Zeitstempel -- keine Fundstellen, damit die Datei
    ueber Monate klein bleibt. ts wird uebergeben, nicht hier gezogen."""
    perc = result["structure_metrics"]["percolation_distance"]
    fil = result["structure_metrics"]["filaments"]
    conf = result["structure_metrics"]["confidence_default_age"]
    return {
        "ts": ts.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "corpus_size": perc["nodes"],
        "orphans": len(result["orphans"]),
        "stale": len(result["stale"]),
        "never_pulled_nodes": len(result["never_pulled_nodes"]),
        "never_pulled_lessons": len(result["never_pulled_lessons"]),
        "vector_gaps": len(result["vector_gaps"]),
        "near_duplicate_lessons": len(result["near_duplicate_lessons"]),
        "path_hygiene": len(result["path_hygiene"]),
        "truncated_embeddings": len(result["truncated_embeddings"]),
        "avg_degree": perc["avg_degree"],
        "cross_project_lessons": fil["cross_project_lessons"],
        "confidence_default_count": conf["count"],
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def aufzeichnen(db_path: Path, log_path: Path, history_path: Path, ts: datetime) -> dict:
    before = _sha256(db_path) if db_path.exists() else None
    result = knowledge_lint.run(db_path, log_path, ts)
    after = _sha256(db_path) if db_path.exists() else None
    record = build_record(result, ts)
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {
        "record": record,
        "db_sha256_before": before,
        "db_sha256_after": after,
        "db_unchanged": before == after,
    }


def _read_history(history_path: Path) -> list[dict]:
    if not history_path.exists():
        return []
    out = []
    with open(history_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _fmt(v) -> str:
    if isinstance(v, float):
        s = f"{v:.3f}".rstrip("0").rstrip(".")
        return s.replace(".", ",")
    return str(v)


def differenz(history_path: Path, gegen: str | None = None) -> str | None:
    """None = nichts zu melden (Gleichstand). Sonst der Meldetext."""
    rows = _read_history(history_path)
    if not rows:
        return "Kein Lauf aufgezeichnet."

    if gegen is None:
        if len(rows) < 2:
            return "Nur ein Lauf aufgezeichnet -- kein Vergleich moeglich."
        old, new = rows[-2], rows[-1]
    else:
        matches = [r for r in rows if r["ts"] == gegen]
        if not matches:
            return f"Kein Lauf mit Zeitstempel {gegen} gefunden."
        old, new = matches[0], rows[-1]

    lines = []
    for key, label in FIELDS:
        ov, nv = old.get(key), new.get(key)
        if ov is None or nv is None or ov == nv:
            continue
        richtung = "gestiegen" if nv > ov else "gefallen"
        lines.append(f"  {label} von {_fmt(ov)} auf {_fmt(nv)} {richtung}")
    if not lines:
        return None
    return f"Vergleich {old['ts']} -> {new['ts']}:\n" + "\n".join(lines)


# ─── Selftest ─────────────────────────────────────────────────────────────

def _selftest() -> None:
    import tempfile

    now = datetime.now(timezone.utc)

    # A) aufzeichnen() gegen echten knowledge_lint-Lauf (Fixture aus
    #    knowledge_lint._selftest_db wiederverwendet, nicht nachgebaut).
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        db_path = knowledge_lint._selftest_db(tmp, now)
        log_path = tmp / "recall_log.jsonl"
        log_path.write_text(json.dumps({"nodes": ["/shared/kind"], "lessons": []}) + "\n", encoding="utf-8")
        history_path = tmp / "verlauf.jsonl"

        out1 = aufzeichnen(db_path, log_path, history_path, now)
        assert out1["db_unchanged"], "run() darf brainlehr.db nicht veraendern"
        rec1 = out1["record"]
        assert rec1["orphans"] == 1, rec1
        assert rec1["path_hygiene"] == 2, rec1
        assert rec1["cross_project_lessons"] == 2, rec1
        # 11 seit knowledge_lint.py um die beiden Kategorie-10-Fixtures
        # (n_no_source, n_has_source) erweitert wurde -- dort bereits als
        # conf["count"] == 11 dokumentiert, hier nur nachgezogen.
        assert rec1["confidence_default_count"] == 11, rec1

        out2 = aufzeichnen(db_path, log_path, history_path, now)
        rows = _read_history(history_path)
        assert len(rows) == 2, "aufzeichnen haengt an, ueberschreibt nicht"
        assert rows[0] == rows[1] == out2["record"], "identischer Zustand -> identische Zeile"

        zeile = json.dumps(rows[0], ensure_ascii=False)
        assert len(zeile) < 400, f"Verlaufszeile zu lang: {len(zeile)} Zeichen"

        # identische Zahlen -> differenz() meldet nichts. Wichtigster Fall.
        assert differenz(history_path) is None

    # B) differenz()-Logik auf synthetischen Zeilen -- Grenzfaelle isoliert
    #    von einem echten Lint-Lauf pruefen.
    with tempfile.TemporaryDirectory() as td2:
        history_path = Path(td2) / "verlauf.jsonl"

        base = {k: 0 for k, _ in FIELDS}
        base["corpus_size"] = 10
        base["avg_degree"] = 0.059

        def write(ts: str, **overrides) -> dict:
            rec = dict(base, ts=ts, **overrides)
            with open(history_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            return rec

        # Nur ein Lauf -> saubere Meldung, kein Absturz.
        write("2026-08-01T00:00:00+0000")
        msg = differenz(history_path)
        assert msg is not None and "ein Lauf" in msg, msg

        # Zweiter Lauf, eine Zahl geaendert -> genau diese eine gemeldet.
        write("2026-08-02T00:00:00+0000", orphans=4)
        msg = differenz(history_path)
        assert msg is not None
        assert "Waisen von 0 auf 4 gestiegen" in msg, msg
        for _, label in FIELDS:
            if label == "Waisen":
                continue
            assert label not in msg, f"unveraenderte Zahl haette nicht gemeldet werden duerfen: {label}"

        # --gegen mit nicht existierendem Zeitpunkt -> saubere Meldung.
        msg = differenz(history_path, gegen="1999-01-01T00:00:00+0000")
        assert msg is not None and "Kein Lauf" in msg, msg

        # Beidseitige Richtung: eine Zahl steigt, eine faellt, im selben Vergleich.
        write("2026-08-03T00:00:00+0000", orphans=4, stale=4, path_hygiene=0)
        write("2026-08-04T00:00:00+0000", orphans=1, stale=4, path_hygiene=3)
        msg = differenz(history_path)
        assert "Waisen von 4 auf 1 gefallen" in msg, msg
        assert "Pfad-Hygiene-Funde von 0 auf 3 gestiegen" in msg, msg
        assert "Karteileichen" not in msg, msg  # stale unveraendert (4 -> 4)

    print("selftest: aufzeichnen haengt an und veraendert die DB nicht, "
          "differenz meldet nur Abweichungen und schweigt bei Gleichstand. OK")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    sub = parser.add_subparsers(dest="cmd")

    p_auf = sub.add_parser("aufzeichnen", help="Lint-Lauf ausfuehren, Zeile anhaengen")
    p_auf.add_argument("--db", default=str(knowledge_lint.DB_PATH))
    p_auf.add_argument("--log", default=str(knowledge_lint.RECALL_LOG))
    p_auf.add_argument("--history", default=str(HISTORY_PATH))
    p_auf.add_argument("--ts", default=None, help="ISO-Zeitstempel, Default: jetzt (UTC)")

    p_diff = sub.add_parser("differenz", help="Letzten Lauf gegen vorherigen vergleichen")
    p_diff.add_argument("--history", default=str(HISTORY_PATH))
    p_diff.add_argument("--gegen", default=None, help="Zeitstempel des Vergleichslaufs (Default: vorletzter)")

    args = parser.parse_args()

    if args.selftest:
        _selftest()
        return

    if args.cmd == "aufzeichnen":
        ts = datetime.fromisoformat(args.ts) if args.ts else datetime.now(timezone.utc)
        out = aufzeichnen(Path(args.db), Path(args.log), Path(args.history), ts)
        print(f"aufgezeichnet: {out['record']}")
        status = "ja" if out["db_unchanged"] else "NEIN -- SOFORT MELDEN"
        print(f"brainlehr.db unveraendert: {status} "
              f"(sha256 vorher={out['db_sha256_before']} nachher={out['db_sha256_after']})")
    elif args.cmd == "differenz":
        msg = differenz(Path(args.history), args.gegen)
        if msg:
            print(msg)
    else:
        parser.error("cmd erforderlich: aufzeichnen | differenz (oder --selftest)")


if __name__ == "__main__":
    main()
