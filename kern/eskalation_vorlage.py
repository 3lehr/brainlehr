#!/usr/bin/env python3
"""
eskalation_vorlage.py — Ziel fuer den Weg C->A bei lessons_learned.

Vorgeschichte (Lehre L-86e92d): eine Lehre mit occurrences>=3 wird von
knowledge_mcp_server auf status='escalated_to_rule' gesetzt und meldet
"Should become a rule in .instructions.md!" -- diese Datei existiert nirgends,
der Weg endete im Nichts.

Dieses Skript gibt der Eskalation ein Ziel: hub/CLAUDE.md, Abschnitt
"Eskalierte Lehren (Stufe A)". Diese Datei ist ueber @-Import in JEDER
Projekt-CLAUDE.md eingebunden und damit bei jeder Sitzung geladen (A-Stufe).
Kein neuer Ladeweg -- der vorhandene wird benutzt.

Der Vorgang, nicht die Benachrichtigung:
  - Adressat: der Betreiber. Nur er befoerdert/stuft zurueck.
  - Antwort-Ort: `python3 eskalation_vorlage.py befoerdern <id>` bzw.
    `zurueckstufen <id>`, von Hand ausgefuehrt.
  - Ohne Antwort: die Lehre bleibt in der Vorlage (status='escalated_to_rule'),
    taucht bei jedem `vorlage`-Lauf wieder auf. Kein Automatismus befoerdert.

Rueckstufungs-Kriterium (in den CLAUDE.md-Abschnitt geschrieben, hier nur
Kurzfassung): eine A-Lehre gehoert zurueck, wenn sie seit Befoerderung nicht
wieder aufgetreten ist, eine allgemeinere Regel sie abdeckt, oder der
Fehlerfall technisch nicht mehr moeglich ist.

Usage:
    python3 eskalation_vorlage.py vorlage
    python3 eskalation_vorlage.py befoerdern <lesson_id>
    python3 eskalation_vorlage.py zurueckstufen <lesson_id>
    python3 eskalation_vorlage.py selftest
"""

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
import re
import sqlite3
import sys
from pathlib import Path

import speicher  # noqa: E402 -- nur verbinde_bestand() fuer get_db()

DB_PATH = _w / "brainlehr.db"
CLAUDE_MD_PATH = _w.parent / "CLAUDE.md"

MARK_START = "<!-- ESKALATION:START -->"
MARK_END = "<!-- ESKALATION:END -->"
SECTION_HEADER = f"""## Eskalierte Lehren (Stufe A) — vom Betreiber befoerdert

Jede Zeile hier kostet Tokens bei JEDEM Prompt, in jedem Projekt. Befoerdert
wird ausschliesslich von Hand: `shared-knowledge/eskalation_vorlage.py
befoerdern <id>` nach Betreiber-Entscheidung — Vorlage der Kandidaten via
`... vorlage`. Voller Text je Lehre: `lesson_query` / Knowledge-DB, id s.u.

Rueckstufung (`... zurueckstufen <id>`) wenn: die Lehre seit Befoerderung
nicht wieder aufgetreten ist, ODER eine allgemeinere Regel sie abdeckt,
ODER der Fehlerfall technisch nicht mehr moeglich ist.

{MARK_START}
{MARK_END}
"""

RULE_CAP = 220  # Zeichen je beforderter Zeile -- A-Stufe traegt den Trigger, C traegt die Langfassung.

STATUS_POOL = "escalated_to_rule"
STATUS_PROMOTED = "in_claude_md"


def get_db():
    # verbinde_bestand statt sqlite3.connect: dieser Bestand muss schon
    # existieren (Eskalation ergaenzt Zeilen, legt keinen an) -- siehe
    # kern/speicher.py::verbinde_bestand.
    conn = speicher.verbinde_bestand(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _cap(text: str, n: int = RULE_CAP) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def cmd_vorlage(_args):
    conn = get_db()
    rows = conn.execute(
        "SELECT id, occurrences, type, description, prevention FROM lessons_learned "
        "WHERE status = ? ORDER BY occurrences DESC, id",
        (STATUS_POOL,),
    ).fetchall()
    conn.close()
    if not rows:
        return  # Kein Platzhalter, kein Rauschen -- liegt nichts vor, schweigt der Vorgang.
    total_full = sum(len(r["prevention"] or "") for r in rows)
    total_capped = sum(len(_cap(r["prevention"])) for r in rows)
    print(f"=== {len(rows)} Kandidaten fuer Stufe A (status='{STATUS_POOL}') ===\n")
    for r in rows:
        print(f"[{r['id']}] x{r['occurrences']} {r['type']}: {r['description'][:80]}")
        print(f"  -> als A-Zeile ({len(_cap(r['prevention']))} Zeichen): {_cap(r['prevention'])}")
        print()
    print(f"Summe Praeventionstext voll: {total_full} Zeichen.")
    print(f"Summe als A-Zeilen (Deckel {RULE_CAP}): {total_capped} Zeichen.")
    print(f"hub/CLAUDE.md aktuell: {len(CLAUDE_MD_PATH.read_text(encoding='utf-8'))} Zeichen.")
    print("Entscheidung beim Betreiber: befoerdern <id> / nichts tun (bleibt in der Vorlage).")
    return rows


def _read_claude_md(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _ensure_section(text: str) -> str:
    if MARK_START in text:
        return text
    sep = "\n\n" if text and not text.endswith("\n\n") else ""
    return text + sep + SECTION_HEADER


def _promote_line(text: str, lesson_id: str, rule_text: str) -> str:
    text = _ensure_section(text)
    line = f"- [{lesson_id}] {rule_text}"
    return re.sub(
        re.escape(MARK_START),
        MARK_START + "\n" + line,
        text,
        count=1,
    )


def _demote_line(text: str, lesson_id: str) -> tuple[str, bool]:
    pattern = re.compile(rf"\n- \[{re.escape(lesson_id)}\].*")
    new_text, n = pattern.subn("", text, count=1)
    return new_text, n > 0


def cmd_befoerdern(args, db_path=None, claude_md_path=None):
    db_path = db_path or DB_PATH
    claude_md_path = claude_md_path or CLAUDE_MD_PATH
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, prevention, description FROM lessons_learned WHERE id = ? AND status = ?",
        (args.lesson_id, STATUS_POOL),
    ).fetchone()
    if not row:
        print(f"[{args.lesson_id}] nicht in der Vorlage (status != '{STATUS_POOL}' oder unbekannt) -- keine Aktion.")
        conn.close()
        return False
    rule_text = _cap(row["prevention"] or row["description"])
    text = _read_claude_md(claude_md_path)
    new_text = _promote_line(text, row["id"], rule_text)
    claude_md_path.write_text(new_text, encoding="utf-8")
    conn.execute("UPDATE lessons_learned SET status = ? WHERE id = ?", (STATUS_PROMOTED, row["id"]))
    conn.commit()
    conn.close()
    print(f"[{row['id']}] befoerdert -> {claude_md_path}")
    return True


def cmd_zurueckstufen(args, db_path=None, claude_md_path=None):
    db_path = db_path or DB_PATH
    claude_md_path = claude_md_path or CLAUDE_MD_PATH
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id FROM lessons_learned WHERE id = ? AND status = ?",
        (args.lesson_id, STATUS_PROMOTED),
    ).fetchone()
    if not row:
        print(f"[{args.lesson_id}] nicht auf Stufe A (status != '{STATUS_PROMOTED}') -- keine Aktion.")
        conn.close()
        return False
    text = _read_claude_md(claude_md_path)
    new_text, found = _demote_line(text, args.lesson_id)
    if not found:
        print(f"[{args.lesson_id}] Zeile nicht in {claude_md_path} gefunden -- DB trotzdem nicht geaendert (Inkonsistenz melden statt raten).")
        conn.close()
        return False
    claude_md_path.write_text(new_text, encoding="utf-8")
    conn.execute("UPDATE lessons_learned SET status = ? WHERE id = ?", (STATUS_POOL, row["id"]))
    conn.commit()
    conn.close()
    print(f"[{row['id']}] zurueckgestuft -> zurueck in die Vorlage.")
    return True


def cmd_selftest(_args):
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        db_copy = tmp / "brainlehr.db"
        md_copy = tmp / "CLAUDE.md"
        shutil.copy(DB_PATH, db_copy)
        md_copy.write_text("# Testkopf\n", encoding="utf-8")

        class NS:
            lesson_id = "L-b9d1f3"

        # Vorher: Kandidat ist in der Vorlage.
        conn = sqlite3.connect(str(db_copy))
        before = conn.execute("SELECT status FROM lessons_learned WHERE id='L-b9d1f3'").fetchone()[0]
        conn.close()
        assert before == STATUS_POOL, f"Testvoraussetzung verletzt: {before}"

        ok = cmd_befoerdern(NS(), db_path=db_copy, claude_md_path=md_copy)
        assert ok is True
        text_after_promote = md_copy.read_text(encoding="utf-8")
        assert "[L-b9d1f3]" in text_after_promote, "Befoerderung: Zeile fehlt in CLAUDE.md-Kopie"
        conn = sqlite3.connect(str(db_copy))
        conn.row_factory = sqlite3.Row
        status_after = conn.execute("SELECT status FROM lessons_learned WHERE id='L-b9d1f3'").fetchone()["status"]
        conn.close()
        assert status_after == STATUS_PROMOTED

        # Vorlage danach: L-b9d1f3 taucht nicht mehr auf.
        conn = sqlite3.connect(str(db_copy))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id FROM lessons_learned WHERE status = ?", (STATUS_POOL,)).fetchall()
        conn.close()
        assert "L-b9d1f3" not in [r["id"] for r in rows], "Vorlage zeigt befoerderte Lehre noch an"

        ok = cmd_zurueckstufen(NS(), db_path=db_copy, claude_md_path=md_copy)
        assert ok is True
        text_after_demote = md_copy.read_text(encoding="utf-8")
        assert "[L-b9d1f3]" not in text_after_demote, "Ruecksstufung: Zeile steht noch in CLAUDE.md-Kopie"
        conn = sqlite3.connect(str(db_copy))
        conn.row_factory = sqlite3.Row
        status_final = conn.execute("SELECT status FROM lessons_learned WHERE id='L-b9d1f3'").fetchone()["status"]
        conn.close()
        assert status_final == STATUS_POOL

        # Unbekannte / falsch-stufige ID: keine Aktion, kein Crash.
        class NS2:
            lesson_id = "L-does-not-exist"

        assert cmd_befoerdern(NS2(), db_path=db_copy, claude_md_path=md_copy) is False
        assert cmd_zurueckstufen(NS2(), db_path=db_copy, claude_md_path=md_copy) is False

    print("Selbsttest gruen: befoerdern setzt Zeile+Status, zurueckstufen nimmt beides zurueck, unbekannte ID -> keine Aktion.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("vorlage", help="Kandidaten (status=escalated_to_rule) anzeigen")
    p_b = sub.add_parser("befoerdern", help="Lehre nach hub/CLAUDE.md befoerdern")
    p_b.add_argument("lesson_id")
    p_z = sub.add_parser("zurueckstufen", help="Lehre aus hub/CLAUDE.md zurueckstufen")
    p_z.add_argument("lesson_id")
    sub.add_parser("selftest", help="Rundlauf gegen Kopien, keine echten Dateien")

    args = p.parse_args()
    if args.cmd == "vorlage":
        cmd_vorlage(args)
    elif args.cmd == "befoerdern":
        cmd_befoerdern(args)
    elif args.cmd == "zurueckstufen":
        cmd_zurueckstufen(args)
    elif args.cmd == "selftest":
        cmd_selftest(args)


if __name__ == "__main__":
    main()
