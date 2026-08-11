#!/usr/bin/env python3
"""lehren_verdichten.py -- Auftrag 2026-08-08 (Zweig hub/subagent-bericht-caveman).

Anlass: eine Lehre hat vier Textfelder (description/root_cause/resolution/
prevention, gemessener Median 560+364+308+460 Zeichen) fuer DREI verschiedene
Zwecke, die sich EIN Feld teilen -- den Volltext. Der bei jedem lesson_query-
Treffer eingespielte Block ist median ~3600 Zeichen gross, weil es ausser dem
Volltext nichts gibt: keine Kurzform fuers Einspielen, kein Regelsatz fuer die
Befoerderung in eine immer geladene Datei. Dieses Skript erzeugt beide Texte
je Lehre und schreibt sie in zwei NEUE Spalten (kurzform, regelsatz) auf
lessons_learned -- additiv, der Volltext (description/root_cause/resolution/
prevention) bleibt UNVERAENDERT.

WAS NIE VERDICHTET WERDEN DARF (Betreiber-Hausregel, Prompt UND Nachpruefung):
Zahlen, Dateinamen, Funktionsnamen, Fehlertexte, Commit-Kennungen; Zuschreibung
("gemessen" vs. "abgeleitet", "vorbestehend, nicht von mir verursacht",
"Gegenprobe gefahren"). NACHTRAG des Betreibers (Praezisierung, siehe unten):
nicht die Zahlen sind die Hauptgefahr, sondern die VERHAELTNISWOERTER
zwischen ihnen -- "obwohl", "weil", "statt", "trotz", "ohne dass", "bevor",
"nachdem", "im Gegensatz zu". Wer sie streichen laesst, macht aus einem
Befund ("3720 Tests gruen, OBWOHL das Merkmal tot war") eine Aufzaehlung
("3720 Tests gruen, Merkmal tot") -- gleiche Zahlen, keine Aussage mehr. Der
Prompt (siehe KURZFORM_PROMPT) verlangt diese Woerter ausdruecklich, UND
_treue_warnungen() prueft nach Erzeugung, ob sie beim Uebersetzen verloren
gingen (Befund, kein Blocker -- gemeldet, nicht stillschweigend verworfen).

KURZFORM: fuer JEDE Lehre, deren Volltext laenger als KURZ_SCHWELLE Zeichen
ist -- eigenstaendig verstaendlicher Kern, nicht der gekuerzte Volltext.
Ist der Volltext schon kurz (<= KURZ_SCHWELLE, gemessen: 4 von 622 Lehren),
entsteht KEINE Kurzform (Spalte bleibt leerer String '' als Markierung
"geprueft, nicht noetig" -- unterscheidbar von NULL="noch nicht geprueft",
das macht den Lauf ohne externen Fortschrittszaehler abschnittsweise
fortsetzbar: WHERE kurzform IS NULL waehlt automatisch den Rest).

REGELSATZ: nur fuer status='escalated_to_rule' (Kandidatenzustand fuer die
immer geladene Datei, gemessen: 4 Lehren). EIN Satz, ohne Vorwissen
verstaendlich, kein Rueckverweis wie "Zwei Befunde" am Satzanfang.

Modell: gemma4:12b ueber lokales Ollama (127.0.0.1:11434) -- DEFAULT_MODEL/
DEFAULT_OLLAMA_URL/CALL_TIMEOUT/KEEP_ALIVE UND die Aufruf-/Retry-Funktionen
(_call_ollama/_call_with_retry) aus schreibpruefstand/schreiblauf.py
importiert, nicht kopiert (identisches Muster wie fenstergroesse.py in
diesem Verzeichnis). Die Sicherungslogik vor einem ALTER TABLE (WAL-
Checkpoint + Dateikopie, Lehre L-218f1e) kommt aus migrate_schreiber._backup,
ebenfalls nur importiert.

Geaenderte Dateien ausserhalb dieser einen: KEINE. Alle anderen *.py und die
Weboberflaeche in diesem Verzeichnis werden nur gelesen/importiert.

Usage:
    .venv/bin/python shared-knowledge/lehren_verdichten.py                 # Trockenlauf, 5 Lehren
    .venv/bin/python shared-knowledge/lehren_verdichten.py --limit 50 --apply
    .venv/bin/python shared-knowledge/lehren_verdichten.py --nur-regelsatz --apply
    .venv/bin/python shared-knowledge/lehren_verdichten.py --selftest
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "schreibpruefstand"))

from migrate_schreiber import _backup  # noqa: E402 -- nur gelesen/importiert
import schreiblauf as sl  # noqa: E402 -- nur gelesen/importiert (_call_ollama, _call_with_retry, Konstanten)

DB_PATH = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (HERE / "brainlehr.db"))
MODEL = sl.DEFAULT_MODEL
OLLAMA_URL = sl.DEFAULT_OLLAMA_URL
TIMEOUT = sl.CALL_TIMEOUT

NEW_COLUMNS = ("kurzform", "regelsatz")
VOLLTEXT_FELDER = ("description", "root_cause", "resolution", "prevention")

# Gemessen (622 Lehren, 2026-08-08): min 198, p10 1060, median 1767, p90 2837,
# max 5949 Zeichen Volltext. Nur 4 Lehren liegen <=400 -- das ist die Menge,
# fuer die "schon kurz genug" tatsaechlich zutrifft, kein willkuerlicher Schnitt
# in der Masse der Verteilung.
KURZ_SCHWELLE = 400

DEFAULT_LIMIT = 50  # eine Sektion; mehrere Laeufe hintereinander decken den Bestand ab

REL_WOERTER = (
    "obwohl", "weil", "statt", "anstatt", "trotz", "ohne dass",
    "bevor", "nachdem", "im gegensatz zu", "waehrend", "während",
)
ZUSCHREIBUNGS_PHRASEN = (
    "gemessen", "abgeleitet", "vorbestehend", "nicht von mir verursacht",
    "gegenprobe gefahren", "nicht verifiziert", "unverifiziert",
)
# Verbotene Regelsatz-Anfaenge: Rueckverweis auf "wie viele Befunde", ohne
# dass der Satz fuer sich steht (Auftrag: "beginnt nicht mit 'Zwei Befunde'").
_RUECKVERWEIS_ANFANG = re.compile(
    r"^(ein|eine|zwei|drei|vier|fuenf|fünf|mehrere|beide|alle)\s+(befund|fund|fall|faelle|fälle|mal|vorkommen|wiederholung)",
    re.IGNORECASE,
)

KURZFORM_PROMPT = """Du verdichtest eine Lehre aus einer Fehler-Wissensdatenbank auf ihren \
handlungsleitenden Kern -- fuer eine Kurzform, die bei JEDEM Treffer sofort mitgelesen wird, \
von einem Leser OHNE Vorwissen ueber diesen Fall. Nicht Zusammenfassung, sondern Antwort auf: \
"was macht der Leser jetzt anders?"

Volltext:
\"\"\"{volltext}\"\"\"

Regeln, alle verbindlich:
1. Erst streichen, was zwischen den Feldern doppelt steht (Beschreibung wiederholt oft die \
Ursache, Behebung oft den Vorfall) -- dann erst kuerzen.
2. Die Handlung zuerst: der erste Satz sagt, was zu tun oder zu lassen ist. Danach nur so \
viel Beleg, dass man es glaubt (eine Zahl, ein Ort, ein Datum) -- nicht die ganze Geschichte.
3. Kein Rueckverweis wie "Zwei Befunde, der zweite ist der schwerere" oder "Dritter Fall" -- \
wertlos ohne den Volltext, den die Kurzform gerade ersetzt.
4. Zahlen, Dateinamen, Funktionsnamen, Fehlertexte, Commit-Kennungen woertlich uebernehmen, \
niemals runden oder umformulieren.
5. Zuschreibungen woertlich erhalten, wo vorhanden: "gemessen" vs. "abgeleitet", \
"vorbestehend, nicht von mir verursacht", "Gegenprobe gefahren", "nicht verifiziert".
6. WICHTIGSTE REGEL: Verhaeltniswoerter zwischen den Tatsachen erhalten -- obwohl, weil, \
statt, trotz, ohne dass, bevor, nachdem, im Gegensatz zu. Kein Aufzaehlungsstil. \
"3720 Tests gruen, OBWOHL das Merkmal tot war" ist ein Befund; "3720 Tests gruen, Merkmal \
tot" ist keiner mehr -- dieselben Zahlen, aber der Zusammenhang fehlt. Erhalte den Zusammenhang.
7. Wenige Zeilen, kuerzer als der Volltext. Im Zweifel laenger statt missverstaendlich -- \
die Kurzform wird viele Male gelesen.

Antworte NUR mit der Kurzform, kein Fliesstext davor oder danach, keine Ueberschrift."""

REGELSATZ_PROMPT = """Aus dieser Lehre wird EIN Satz fuer eine immer geladene Regel-Datei \
gebraucht -- Kandidat fuer eine dauerhafte Regel, kein Lehrtext.

Lehre:
\"\"\"{volltext}\"\"\"

Regeln, alle verbindlich:
1. GENAU EIN Satz.
2. Ohne Vorwissen ueber diese Lehre verstaendlich -- sagt, was zu TUN ist, nicht was \
passiert ist.
3. Nennt den Ausloeser, an dem man merkt, dass die Regel gerade greift (z.B. "vor jeder \
Aussage ueber X", "sobald Y fehlt") -- sonst ist der Satz wahr, aber nicht anwendbar.
4. Beginnt NICHT mit einem Rueckverweis wie "Zwei Befunde" oder "Ein Fall" -- der Satz \
steht fuer sich, er verweist nicht auf eine Zaehlung vorheriger Vorkommen.
5. Zahlen/Dateinamen/Funktionsnamen woertlich, wo fachlich noetig.

Gutes Beispiel: "Vor jeder Aussage ueber eine Quelle pruefen, ob man die Quelle gesehen hat \
oder ihren Stellvertreter."
Schlechtes Beispiel: "Zwei Befunde, der zweite ist der schwerere. ERSTENS: ..."

Antworte NUR mit dem einen Satz, kein Fliesstext davor oder danach."""


def volltext(row: dict) -> str:
    parts = [row.get(f) for f in VOLLTEXT_FELDER if row.get(f)]
    return "\n\n".join(parts)


def _treue_warnungen(vt: str, kurz: str) -> list[str]:
    """Nachpruefung, kein Blocker -- meldet, was beim Verdichten verloren ging.
    Drei Kategorien: Zahlen (>=2-stellig, sonst zu viel Rauschen von Aufzaehl-
    zeichen/Einzelziffern), Zuschreibungsphrasen, Verhaeltniswoerter."""
    warnungen = []
    kurz_fold = kurz.lower()

    zahlen = set(re.findall(r"\b\d{2,}\b", vt))
    fehlende_zahlen = sorted(z for z in zahlen if z not in kurz)
    if fehlende_zahlen:
        warnungen.append(f"Zahlen fehlen in Kurzform: {', '.join(fehlende_zahlen)}")

    vt_fold = vt.lower()
    for phrase in ZUSCHREIBUNGS_PHRASEN:
        if phrase in vt_fold and phrase not in kurz_fold:
            warnungen.append(f"Zuschreibung '{phrase}' fehlt in Kurzform")

    vt_hat_rel = any(w in vt_fold for w in REL_WOERTER)
    kurz_hat_rel = any(w in kurz_fold for w in REL_WOERTER)
    if vt_hat_rel and not kurz_hat_rel:
        warnungen.append(
            "Verhaeltniswoerter (obwohl/weil/statt/trotz/...) im Volltext vorhanden, "
            "in Kurzform keins -- moeglich, dass aus Befund Aufzaehlung wurde"
        )
    return warnungen


def _ensure_columns(conn: sqlite3.Connection, apply: bool) -> dict:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(lessons_learned)")}
    missing = [c for c in NEW_COLUMNS if c not in existing]
    result = {"fehlende_spalten": missing, "backup": None}
    if not missing or not apply:
        return result
    backup_path = _backup(DB_PATH)
    result["backup"] = str(backup_path)
    for name in missing:
        conn.execute(f"ALTER TABLE lessons_learned ADD COLUMN {name} TEXT")
    conn.commit()
    return result


def _integrity_check(conn: sqlite3.Connection) -> str:
    return conn.execute("PRAGMA integrity_check").fetchone()[0]


def _andere_laeufe(eigene_pid: int) -> list[str]:
    """pgrep nach anderen Instanzen DIESES Skripts (Auftrag: pruefen, ob ein
    anderer Lauf schreibt). Der WAL-Checkpoint in migrate_schreiber._backup
    faengt fremde Schreiber auf der DB-Ebene zusaetzlich ab (busy!=0 ->
    RuntimeError) -- das hier ist die vom Auftrag verlangte pgrep-Vorpruefung,
    kein Ersatz dafuer."""
    try:
        out = subprocess.run(
            ["pgrep", "-f", "lehren_verdichten.py"],
            capture_output=True, text=True, timeout=5,
        ).stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    pids = [p for p in out.split() if p.isdigit() and int(p) != eigene_pid]
    return pids


def _call_model(prompt: str) -> tuple[str | None, str | None]:
    # erzeugen: verdichtet Bestandstext, beantwortet keine Pruefaufgabe --
    # lokal zulaessig, aber nur mit ausdruecklicher Freigabe BRAINLEHR_LOKAL=1.
    raw, err, _retries = sl._call_with_retry(prompt, model=MODEL, base_url=OLLAMA_URL,
                                              timeout=TIMEOUT, rolle="erzeugen")
    if err:
        return None, err
    return (raw or "").strip(), None


def generate_kurzform(row: dict, call_model=_call_model) -> tuple[str | None, str | None, list[str]]:
    """Gibt (kurzform, fehler, treue_warnungen) zurueck. kurzform=='' heisst
    'geprueft, Volltext schon kurz genug'. kurzform is None heisst Fehlschlag
    (nicht kuerzer als Volltext oder Modellfehler) -- Zeile bleibt NULL, naechster
    Lauf versucht erneut."""
    vt = volltext(row)
    if len(vt) <= KURZ_SCHWELLE:
        return "", None, []
    raw, err = call_model(KURZFORM_PROMPT.format(volltext=vt))
    if err:
        return None, err, []
    if not raw or len(raw) >= len(vt):
        return None, f"Kurzform nicht kuerzer als Volltext ({len(raw or '')} >= {len(vt)} Zeichen)", []
    return raw, None, _treue_warnungen(vt, raw)


def generate_regelsatz(row: dict, call_model=_call_model) -> tuple[str | None, str | None]:
    vt = volltext(row)
    raw, err = call_model(REGELSATZ_PROMPT.format(volltext=vt))
    if err:
        return None, err
    satz = (raw or "").strip()
    if not satz:
        return None, "leere Modellantwort"
    if _RUECKVERWEIS_ANFANG.match(satz):
        return None, f"Regelsatz beginnt mit Rueckverweis: '{satz[:40]}...'"
    return satz, None


def process_kurzformen(conn: sqlite3.Connection, limit: int, apply: bool, call_model=_call_model,
                        has_column: bool = True, zeige_volltext: bool = False) -> dict:
    where = "WHERE kurzform IS NULL " if has_column else ""  # Spalte fehlt im Trockenlauf ohne --apply
    rows = [dict(r) for r in conn.execute(
        f"SELECT id, description, root_cause, resolution, prevention "
        f"FROM lessons_learned {where}ORDER BY id LIMIT ?", (limit,)
    )]
    stats = {"geprueft": 0, "kurzform_erzeugt": 0, "schon_kurz": 0, "fehlgeschlagen": 0, "warnungen": []}
    for row in rows:
        stats["geprueft"] += 1
        kurz, err, warnungen = generate_kurzform(row, call_model=call_model)
        vt_len = len(volltext(row))
        if err:
            stats["fehlgeschlagen"] += 1
            print(f"  {row['id']}: FEHLER -- {err}")
            continue
        if kurz == "":
            stats["schon_kurz"] += 1
            print(f"  {row['id']}: schon kurz genug (Volltext {vt_len} Zeichen) -- keine Kurzform")
        else:
            stats["kurzform_erzeugt"] += 1
            print(f"  {row['id']}: Volltext {vt_len} -> Kurzform {len(kurz)} Zeichen")
            if zeige_volltext:
                print(f"    VOLLTEXT: {volltext(row)!r}")
                print(f"    KURZFORM: {kurz!r}")
            if warnungen:
                for w in warnungen:
                    print(f"    WARNUNG: {w}")
                stats["warnungen"].append({"id": row["id"], "warnungen": warnungen})
        if apply:
            conn.execute("UPDATE lessons_learned SET kurzform = ? WHERE id = ?", (kurz, row["id"]))
    if apply and rows:
        conn.commit()
    return stats


def process_regelsaetze(conn: sqlite3.Connection, apply: bool, call_model=_call_model,
                         has_column: bool = True) -> dict:
    regelsatz_filter = "AND regelsatz IS NULL " if has_column else ""
    rows = [dict(r) for r in conn.execute(
        f"SELECT id, description, root_cause, resolution, prevention "
        f"FROM lessons_learned WHERE status = 'escalated_to_rule' {regelsatz_filter}ORDER BY id"
    )]
    stats = {"geprueft": 0, "erzeugt": 0, "fehlgeschlagen": 0}
    for row in rows:
        stats["geprueft"] += 1
        satz, err = generate_regelsatz(row, call_model=call_model)
        if err:
            stats["fehlgeschlagen"] += 1
            print(f"  {row['id']}: FEHLER -- {err}")
            continue
        stats["erzeugt"] += 1
        print(f"  {row['id']}: {satz}")
        if apply:
            conn.execute("UPDATE lessons_learned SET regelsatz = ? WHERE id = ?", (satz, row["id"]))
    if apply and rows:
        conn.commit()
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="schreibt (Vorgabe: Trockenlauf)")
    ap.add_argument("--limit", type=int, default=None,
                     help=f"Sektionsgroesse Kurzform (Vorgabe: {DEFAULT_LIMIT} bei --apply, 5 im Trockenlauf)")
    ap.add_argument("--nur-kurzform", action="store_true")
    ap.add_argument("--nur-regelsatz", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    limit = args.limit if args.limit is not None else (DEFAULT_LIMIT if args.apply else 5)

    if not DB_PATH.exists():
        print(f"FEHLER: {DB_PATH} nicht gefunden.")
        return 1

    fremde = _andere_laeufe(os.getpid())
    if fremde:
        print(f"ABBRUCH: anderer Lauf von lehren_verdichten.py aktiv (PID {', '.join(fremde)}).")
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        vor = _integrity_check(conn)
        if vor != "ok":
            print(f"ABBRUCH: PRAGMA integrity_check vor Lauf meldet '{vor}', nicht 'ok'.")
            return 1

        vorher_gesamt = conn.execute("SELECT COUNT(*) FROM lessons_learned").fetchone()[0]
        col_result = _ensure_columns(conn, args.apply)
        mode = "APPLY" if args.apply else "TROCKENLAUF"
        print(f"=== lehren_verdichten ({mode}, Sektion {limit}) ===")
        print(f"Bestand: {vorher_gesamt} Lehren. Fehlende Spalten: {col_result['fehlende_spalten']}")
        if col_result["backup"]:
            print(f"Sicherung vor ALTER TABLE: {col_result['backup']}")
        # Ohne --apply existieren die Spalten evtl. noch nicht (werden nur bei --apply
        # angelegt) -- WHERE kurzform IS NULL entfaellt dann, Vorschau nimmt die
        # ersten `limit` Lehren ungefiltert. Zeigt trotzdem echte Modellausgabe.
        has_column = "kurzform" not in col_result["fehlende_spalten"]
        if not args.apply and col_result["fehlende_spalten"]:
            print("Spalten kurzform/regelsatz noch nicht angelegt (nur --apply legt sie an) -- "
                  "Vorschau unten zeigt Modellausgabe ungefiltert, schreibt nichts.")

        if not args.nur_regelsatz:
            print("\n-- Kurzform --")
            k_stats = process_kurzformen(conn, limit, args.apply, has_column=has_column,
                                         zeige_volltext=not args.apply)
            print(f"geprueft={k_stats['geprueft']} erzeugt={k_stats['kurzform_erzeugt']} "
                  f"schon_kurz={k_stats['schon_kurz']} fehlgeschlagen={k_stats['fehlgeschlagen']} "
                  f"treue_warnungen={len(k_stats['warnungen'])}")

        if not args.nur_kurzform:
            print("\n-- Regelsatz (nur status=escalated_to_rule) --")
            r_stats = process_regelsaetze(conn, args.apply, has_column=has_column)
            print(f"geprueft={r_stats['geprueft']} erzeugt={r_stats['erzeugt']} "
                  f"fehlgeschlagen={r_stats['fehlgeschlagen']}")

        if args.apply:
            nach = _integrity_check(conn)
            print(f"\nPRAGMA integrity_check nach Lauf: {nach}")
            if nach != "ok":
                print("WARNUNG: integrity_check nach dem Lauf nicht 'ok' -- Sicherung pruefen.")
        nachher_gesamt = conn.execute("SELECT COUNT(*) FROM lessons_learned").fetchone()[0]
        print(f"Zeilen vorher={vorher_gesamt} nachher={nachher_gesamt} (Zeilenzahl darf sich nie aendern)")
    finally:
        conn.close()
    return 0


def _selftest() -> int:
    """Netzlos -- ersetzt call_model durch eine feste Fake-Funktion, prueft
    Skip-Schwelle, Laengenpruefung, Treue-Warnungen, Rueckverweis-Erkennung
    und die additive Spalten-Migration gegen eine Tempkopie der DB."""
    import shutil
    import tempfile
    global DB_PATH

    # 1) Skip-Schwelle: kurzer Volltext -> keine Kurzform, kein Modellaufruf.
    kurze_zeile = {"description": "Kurzer Fehler.", "root_cause": None, "resolution": None, "prevention": None}
    assert len(volltext(kurze_zeile)) <= KURZ_SCHWELLE

    def _sollte_nicht_rufen(_prompt):
        raise AssertionError("Modell haette bei kurzem Volltext nicht gerufen werden duerfen")

    kurz, err, warn = generate_kurzform(kurze_zeile, call_model=_sollte_nicht_rufen)
    assert kurz == "" and err is None and warn == []

    # 2) Laengenpruefung: Modellantwort nicht kuerzer als Volltext -> Fehlschlag, kein Schreiben.
    lange_zeile = {"description": "X " * 300, "root_cause": None, "resolution": None, "prevention": None}
    kurz2, err2, _ = generate_kurzform(lange_zeile, call_model=lambda p: (p, None))
    assert kurz2 is None and "nicht kuerzer" in err2

    # 3) Treue-Warnung: Zahl + Zuschreibung + Verhaeltniswort im Volltext, in der
    #    (absichtlich zu stark gekuerzten) Kurzform keins davon -> drei Warnungen.
    vt = "Am 2026-08-01 fielen 3720 Tests gruen aus, OBWOHL das Merkmal tot war. Gemessen, nicht geraten."
    kurz3 = "Tests gruen, Merkmal tot."
    warnungen = _treue_warnungen(vt, kurz3)
    assert any("Zahlen" in w for w in warnungen), warnungen
    assert any("Zuschreibung" in w for w in warnungen), warnungen
    assert any("Verhaeltniswoerter" in w for w in warnungen), warnungen
    # Gegenprobe: bleibt "obwohl" erhalten, keine Verhaeltnis-Warnung mehr.
    kurz3b = "3720 Tests gruen, obwohl Merkmal tot. Gemessen."
    warnungen_b = _treue_warnungen(vt, kurz3b)
    assert not any("Verhaeltniswoerter" in w for w in warnungen_b), warnungen_b

    # 4) Rueckverweis-Erkennung fuer Regelsatz.
    zeile = {"description": "irrelevant", "root_cause": None, "resolution": None, "prevention": None}
    satz, err4 = generate_regelsatz(zeile, call_model=lambda p: ("Zwei Befunde zeigen das Muster.", None))
    assert satz is None and "Rueckverweis" in err4
    satz2, err5 = generate_regelsatz(zeile, call_model=lambda p: ("Vor jeder Aussage die Fehlerausgabe lesen.", None))
    assert satz2 == "Vor jeder Aussage die Fehlerausgabe lesen." and err5 is None

    # 5) Additive Migration gegen Tempkopie, idempotent, Zeilenzahl unveraendert.
    with tempfile.TemporaryDirectory() as tmp:
        tmp_db = Path(tmp) / "brainlehr.db"
        shutil.copy2(DB_PATH, tmp_db)
        orig_db_path = DB_PATH
        DB_PATH = tmp_db
        try:
            conn = sqlite3.connect(str(tmp_db))
            conn.row_factory = sqlite3.Row
            vorher = conn.execute("SELECT COUNT(*) FROM lessons_learned").fetchone()[0]
            res1 = _ensure_columns(conn, apply=True)
            assert set(res1["fehlende_spalten"]) <= set(NEW_COLUMNS)
            assert res1["backup"] and Path(res1["backup"]).exists()
            existing = {row[1] for row in conn.execute("PRAGMA table_info(lessons_learned)")}
            assert {"kurzform", "regelsatz"} <= existing
            nachher = conn.execute("SELECT COUNT(*) FROM lessons_learned").fetchone()[0]
            assert vorher == nachher
            res2 = _ensure_columns(conn, apply=True)
            assert res2["fehlende_spalten"] == [] and res2["backup"] is None
            conn.close()
        finally:
            DB_PATH = orig_db_path

    print("SELFTEST OK: Skip-Schwelle, Laengenpruefung, Treue-Warnungen (Zahlen/Zuschreibung/"
          "Verhaeltniswoerter), Rueckverweis-Erkennung, additive Migration idempotent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
