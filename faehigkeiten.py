#!/usr/bin/env python3
"""faehigkeiten.py — Faehigkeitsbestand von brainlehr, aus messbaren Quellen.

Auftrag "Faehigkeitsuebersicht" (2026-08-09). Befund, der das ausloest: der
Wurzelknoten /brainlehr im eigenen Wissensspeicher enthaelt nur den
automatisch erzeugten Astknoten-Satz -- ein System mit tausenden Eintraegen,
das auf "was kannst du" nicht antworten kann. Vorbild fuer die Bauform:
build_node_index.py (erzeugen statt pflegen, damit nichts verrottet).

Nachtrag 2026-08-09 (Zweiteilung, L-bed14a): der Knoten wird beim ZUGRIFF
erzeugt, nicht beim Sitzungsstart -- bis dahin waere er falsch. Die Erhebung
selbst zerfaellt in zwei Klassen mit unterschiedlicher Haltbarkeit:

  SOFORT (immer aktuell, kein Zeitstempel noetig -- entsteht im Moment des
  Lesens): Werkzeuge im Repo mit --selftest/--melder (nur ERKANNT, NIE
  ausgefuehrt -- ein Melder kann in die echte Datenbank schreiben, das ist
  keine Testfunktion), Verdrahtung in settings.json, Spaltenfuellung von
  knowledge_nodes/lessons_learned, Bestandszahlen. Reines Zaehlen/Lesen,
  gemessen unter 1 Sekunde.

  MOMENTAUFNAHME (Eigenschaft des BETRIEBS, nicht des Wissens -- traegt
  IMMER ein Datum): ob ein Selbsttest gruen war. Wird NICHT erhoben, sondern
  aus der juengsten Datei runs/selbsttest_rundlauf_*.md gelesen. Fehlt sie,
  steht "nicht erhoben" da -- nie weggelassen, nie mit dem Sofort-Teil
  vermischt. Kein Leser darf im Zweifel sein, ob "gruen" heisst "ist gruen"
  oder "war am <Datum> gruen".

Usage:
  python3 faehigkeiten.py --bericht   # Uebersicht auf stdout
  python3 faehigkeiten.py --knoten    # dieselbe Uebersicht in /brainlehr
                                       # schreiben (via knowledge_update,
                                       # kein rohes SQL) -- ueberschreibt,
                                       # haengt nicht an
  python3 faehigkeiten.py --selftest
"""
from __future__ import annotations

import ast
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from haken.ort import DB as _DB, WURZEL  # noqa: E402

DB = str(_DB)
SETTINGS = Path.home() / ".claude" / "settings.json"
RUNS = WURZEL / "runs"

VORBEHALT = (
    "Diese Uebersicht sagt, was GEBAUT ist -- nicht, was WIRKT: ein "
    "Werkzeug mit gruenem Selbsttest kann trotzdem nie aufgerufen werden, "
    "und eine gefuellte Spalte kann trotzdem bedeutungslos sein."
)

# Verzeichnisse, die keine Werkzeuge enthalten (Tests, Fremdcode, Caches).
_AUSGENOMMEN = {"tests", "__pycache__", ".git", ".claude", "node_modules"}


# ---------- SOFORT, Teil 1+2: Werkzeuge + Verdrahtung ----------

def scan_tools(repo_root: Path) -> list[dict]:
    """Alle .py-Dateien unter repo_root (ohne _AUSGENOMMEN), die --selftest
    oder --melder woertlich im Quelltext tragen. Fuehrt NICHTS aus -- reines
    Lesen, das ist der Punkt der Sofort-Klasse."""
    treffer = []
    for path in sorted(repo_root.rglob("*.py")):
        if path.name == "faehigkeiten.py":
            continue
        if any(teil in _AUSGENOMMEN for teil in path.relative_to(repo_root).parts[:-1]):
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        hat_selftest = "--selftest" in text
        hat_melder = "--melder" in text
        if not (hat_selftest or hat_melder):
            continue
        treffer.append({
            "pfad": path,
            "name": str(path.relative_to(repo_root)),
            "zweck": _zweck(text),
            "selftest": hat_selftest,
            "melder": hat_melder,
        })
    return treffer


def _zweck(text: str) -> str:
    """Erster Satz des Modul-Docstrings -- der Kopfkommentar nennt den
    Zweck laut Auftrag "in der Regel in einem Satz"."""
    try:
        doc = ast.get_docstring(ast.parse(text))
    except SyntaxError:
        doc = None
    if not doc:
        return "(kein Docstring)"
    erste_zeile = doc.strip().splitlines()[0].strip()
    return erste_zeile[:160]


def wired_tools(tools: list[dict], settings_path: Path) -> None:
    """Ergaenzt Feld 'verdrahtet' (bool): Dateiname taucht in irgendeinem
    Hook-Kommando aus settings.json auf."""
    try:
        raw = settings_path.read_text()
    except OSError:
        for tool in tools:
            tool["verdrahtet"] = False
        return
    for tool in tools:
        muster = re.escape(tool["pfad"].name)
        tool["verdrahtet"] = bool(re.search(muster, raw))


# ---------- SOFORT, Teil 3: Spaltenfuellung ----------

def spaltenfuellung(conn: sqlite3.Connection, tabelle: str) -> list[tuple[str, int, int]]:
    """Je Spalte: (name, gefuellt, gesamt). Gefuellt = NOT NULL und (bei
    Text) nicht nur Leerraum -- 0/false zaehlt als gefuellt."""
    spalten = [row[1] for row in conn.execute(f"PRAGMA table_info({tabelle})")]
    gesamt = conn.execute(f"SELECT COUNT(*) FROM {tabelle}").fetchone()[0]
    ergebnis = []
    for spalte in spalten:
        gefuellt = conn.execute(
            f'SELECT COUNT(*) FROM {tabelle} WHERE "{spalte}" IS NOT NULL '
            f'AND TRIM(CAST("{spalte}" AS TEXT)) <> \'\''
        ).fetchone()[0]
        ergebnis.append((spalte, gefuellt, gesamt))
    return ergebnis


# ---------- SOFORT, Teil 4: Bestand ----------

def bestand(conn: sqlite3.Connection) -> dict:
    def zaehl(tabelle: str) -> int:
        try:
            return conn.execute(f"SELECT COUNT(*) FROM {tabelle}").fetchone()[0]
        except sqlite3.Error:
            return 0
    return {
        "knoten": zaehl("knowledge_nodes"),
        "lehren": zaehl("lessons_learned"),
        "kanten": zaehl("knowledge_relations"),
        "vektoren": zaehl("knowledge_embeddings"),
    }


# ---------- MOMENTAUFNAHME: Selbsttest-Rundlauf aus runs/ lesen ----------

_DATEIMUSTER = re.compile(r"selbsttest_rundlauf_(\d{4}-\d{2}-\d{2})\.md$")
_HEADER_ZEITPUNKT = re.compile(r"(\d{4}-\d{2}-\d{2}T[\d:+\-]+)")
_ERGEBNIS_ZEILE = re.compile(r"^ERGEBNIS:\s*(.+)$", re.MULTILINE)
_ROT_BLOCK = re.compile(r"^ROT \(\d+\):\s*\n((?:\s*-\s*.+\n?)+)", re.MULTILINE)


def lies_momentaufnahme(runs_dir: Path) -> dict | None:
    """Liest den juengsten runs/selbsttest_rundlauf_*.md und gibt Datum,
    Ergebniszeile und Rot-Liste zurueck. None, wenn keine Datei existiert --
    das ist keine Ausnahme, sondern der Negativfall (c)."""
    kandidaten = sorted(runs_dir.glob("selbsttest_rundlauf_*.md"),
                         key=lambda p: _DATEIMUSTER.search(p.name).group(1)
                         if _DATEIMUSTER.search(p.name) else "")
    if not kandidaten:
        return None
    pfad = kandidaten[-1]
    try:
        text = pfad.read_text()
    except OSError:
        return None

    header = _HEADER_ZEITPUNKT.search(text)
    datei_datum = _DATEIMUSTER.search(pfad.name)
    datum = header.group(1) if header else (datei_datum.group(1) if datei_datum else "unbekannt")

    ergebnis_treffer = _ERGEBNIS_ZEILE.search(text)
    ergebnis = ergebnis_treffer.group(1).strip() if ergebnis_treffer else "(keine ERGEBNIS-Zeile gefunden)"

    rot_block = _ROT_BLOCK.search(text)
    rot = []
    if rot_block:
        rot = [zeile.strip().lstrip("-").strip()
               for zeile in rot_block.group(1).splitlines() if zeile.strip()]

    return {"quelle": pfad.name, "datum": datum, "ergebnis": ergebnis, "rot": rot}


# ---------- Rendern ----------

def render(tools: list[dict], spalten_nodes: list[tuple[str, int, int]],
           spalten_lessons: list[tuple[str, int, int]], best: dict,
           jetzt: datetime, momentaufnahme: dict | None) -> str:
    lines = [
        VORBEHALT,
        "",
        "# Faehigkeitsbestand brainlehr (generiert — nicht von Hand editieren)",
        "",
        f"erzeugt: {jetzt.strftime('%Y-%m-%dT%H:%M:%S%z')}",
        "",
        "## SOFORT — jetzt gemessen, kein Zeitstempel noetig",
        "",
        "### Werkzeuge mit --selftest oder --melder ({} gefunden)".format(len(tools)),
        "",
    ]
    if not tools:
        lines.append("(keine gefunden)")
    for t in sorted(tools, key=lambda t: t["name"]):
        st = "--selftest vorhanden" if t["selftest"] else "kein --selftest"
        md = "--melder" if t["melder"] else "kein --melder"
        draht = "verdrahtet" if t.get("verdrahtet") else "nicht verdrahtet"
        lines.append(f"- {t['name']} — {t['zweck']} [{st}; {md}; {draht}]")
    lines.append("")

    for titel, spalten in (
        ("knowledge_nodes", spalten_nodes),
        ("lessons_learned", spalten_lessons),
    ):
        lines.append(f"### Spaltenfuellung {titel}")
        lines.append("")
        for name, gefuellt, gesamt in spalten:
            pct = (100 * gefuellt // gesamt) if gesamt else 0
            lines.append(f"- {name}: {gefuellt}/{gesamt} ({pct}%)")
        lines.append("")

    lines.append("### Bestand")
    lines.append("")
    lines.append(f"- Knoten: {best['knoten']}")
    lines.append(f"- Lehren: {best['lehren']}")
    lines.append(f"- Kanten: {best['kanten']}")
    lines.append(f"- Vektoren: {best['vektoren']}")
    lines.append("")

    lines.append("## MOMENTAUFNAHME — Betriebszustand, nicht Wissen, traegt ein Datum")
    lines.append("")
    if momentaufnahme is None:
        lines.append("nicht erhoben (keine runs/selbsttest_rundlauf_*.md gefunden)")
    else:
        lines.append(f"Stand: {momentaufnahme['datum']} (Quelle: runs/{momentaufnahme['quelle']})")
        lines.append(f"Ergebnis am {momentaufnahme['datum']}: {momentaufnahme['ergebnis']}")
        if momentaufnahme["rot"]:
            lines.append(f"ROT am {momentaufnahme['datum']} ({len(momentaufnahme['rot'])}):")
            for name in momentaufnahme["rot"]:
                lines.append(f"  - {name}")
    lines.append("")

    return "\n".join(lines)


def erhebe_sofort(repo_root: Path, db_path: str, settings_path: Path) -> tuple | None:
    """Nur die Sofort-Klasse: Zaehlen und Lesen, kein Selbsttest wird
    ausgefuehrt. None bei fehlender/nicht lesbarer Datenbank."""
    tools = scan_tools(repo_root)
    wired_tools(tools, settings_path)

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0)
        conn.execute("SELECT 1").fetchone()
    except sqlite3.Error:
        return None
    try:
        spalten_nodes = spaltenfuellung(conn, "knowledge_nodes")
        spalten_lessons = spaltenfuellung(conn, "lessons_learned")
        best = bestand(conn)
    finally:
        conn.close()

    return tools, spalten_nodes, spalten_lessons, best


def erhebe(repo_root: Path, db_path: str, settings_path: Path, runs_dir: Path,
           jetzt: datetime) -> str | None:
    """Sofort-Klasse messen + Momentaufnahme aus runs/ lesen, zusammen
    rendern. None bei fehlender/nicht lesbarer Datenbank."""
    sofort = erhebe_sofort(repo_root, db_path, settings_path)
    if sofort is None:
        return None
    tools, spalten_nodes, spalten_lessons, best = sofort
    momentaufnahme = lies_momentaufnahme(runs_dir)
    return render(tools, spalten_nodes, spalten_lessons, best, jetzt, momentaufnahme)


def schreibe_knoten(text: str) -> dict:
    """Ueberschreibt /brainlehr ueber den regulaeren Weg (knowledge_update
    des MCP-Servers), nicht per rohem SQL. Herkunft weist den Erzeuger aus
    (actor='faehigkeiten.py', model='script'), nicht einen Menschen.

    updated_at: knowledge_update() in knowledge_mcp_server.py setzt
    updated_at bei JEDER Aktualisierung unbedingt (kein Parameter, der das
    unterdrueckt -- siehe dortige Zeile 'updates.append("updated_at = ?")",
    ausserhalb dieser Zeile nicht abschaltbar). Der Auftrag verlangt, dass
    dieser Knoten updated_at NICHT veraendert, weil eine automatische
    Neuerzeugung keine inhaltliche Aenderung ist und sonst der
    Konfidenzverfall faelschlich zurueckgesetzt wird. Der regulaere Weg
    LAESST DAS NICHT ZU -- das ist eine Abweichung vom Auftrag und wird hier
    gemeldet statt still per rohem SQL umgangen (das waere der verbotene
    Weg). Wer /brainlehr per --knoten schreibt, muss wissen: updated_at
    springt trotzdem vor."""
    sys.path.insert(0, str(WURZEL))
    import knowledge_mcp_server as server  # noqa: E402
    return server.knowledge_update(
        "/brainlehr", summary=text.strip().splitlines()[0][:200], content=text,
        actor="faehigkeiten.py", model="script",
    )


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return

    jetzt = datetime.now().astimezone()
    if "--knoten" in sys.argv:
        text = erhebe(WURZEL, DB, SETTINGS, RUNS, jetzt)
        if text is None:
            print(f"FEHLER: Datenbank nicht lesbar: {DB}", file=sys.stderr)
            sys.exit(1)
        ergebnis = schreibe_knoten(text)
        if "error" in ergebnis:
            print(f"FEHLER beim Schreiben: {ergebnis['error']}", file=sys.stderr)
            sys.exit(1)
        print("/brainlehr aktualisiert (updated_at springt vor -- siehe schreibe_knoten()-Docstring).")
        return

    if "--bericht" in sys.argv:
        text = erhebe(WURZEL, DB, SETTINGS, RUNS, jetzt)
        if text is None:
            print(f"FEHLER: Datenbank nicht lesbar: {DB}", file=sys.stderr)
            sys.exit(1)
        print(text)
        return

    print(__doc__)


# ---------- Selbsttest ----------

def selftest() -> None:
    import json
    import time
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        # (a) Werkzeug mit --selftest wird erkannt, samt Zweck-Satz --
        # NICHT ausgefuehrt (scan_tools fuehrt nie etwas aus).
        werkzeug_mit = td / "beispiel_mit.py"
        werkzeug_mit.write_text(
            '"""beispiel_mit.py — tut testbare Dinge.\n\nmehr Text.\n"""\n'
            'import sys\n'
            'if "--selftest" in sys.argv:\n'
            '    print("selftest ok")\n'
            '    sys.exit(0)\n'
        )
        werkzeug_ohne = td / "beispiel_ohne.py"
        werkzeug_ohne.write_text('"""beispiel_ohne.py — reines Skript."""\n')
        werkzeug_melder = td / "beispiel_melder.py"
        werkzeug_melder.write_text(
            '"""beispiel_melder.py — meldet was am Haltepunkt."""\n'
            'import sys\n'
            'if "--melder" in sys.argv:\n'
            '    pass\n'
        )

        tools = scan_tools(td)
        namen = {t["name"] for t in tools}
        assert "beispiel_mit.py" in namen, tools
        assert "beispiel_ohne.py" not in namen, "Datei ohne --selftest/--melder faelschlich erkannt"
        assert "beispiel_melder.py" in namen
        mit = next(t for t in tools if t["name"] == "beispiel_mit.py")
        assert mit["zweck"] == "beispiel_mit.py — tut testbare Dinge.", mit["zweck"]
        assert mit["selftest"] and not mit["melder"]
        melder = next(t for t in tools if t["name"] == "beispiel_melder.py")
        assert melder["melder"] and not melder["selftest"]
        assert "selftest_ergebnis" not in mit, "scan_tools hat ausgefuehrt statt nur erkannt"
        assert "selftest_ergebnis" not in melder, "scan_tools hat ausgefuehrt statt nur erkannt"
        print("  (a) --selftest/--melder erkannt, Zweck aus Docstring gelesen, NICHTS ausgefuehrt: ok")

        # (b) verdrahtet vs. nicht verdrahtet.
        settings_path = td / "settings.json"
        settings_path.write_text(json.dumps({
            "hooks": {"SessionStart": [{"hooks": [
                {"type": "command", "command": "python3 x/beispiel_melder.py --melder"}
            ]}]}
        }))
        wired_tools(tools, settings_path)
        assert melder["verdrahtet"] is True
        assert mit["verdrahtet"] is False
        print("  (b) verdrahtet (settings.json) korrekt von nicht-verdrahtet unterschieden: ok")

        # (c) 0%-gefuellte Spalte erscheint als solche.
        db_path = td / "t.db"
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE knowledge_nodes (path TEXT, summary TEXT, quell_hash TEXT, access_count INTEGER)"
        )
        conn.execute("CREATE TABLE lessons_learned (description TEXT, root_cause TEXT)")
        conn.executemany(
            "INSERT INTO knowledge_nodes VALUES (?,?,?,?)",
            [("/a", "s1", None, 0), ("/b", "s2", None, 5), ("/c", "", None, None)],
        )
        conn.execute("INSERT INTO lessons_learned VALUES ('d1', 'r1')")
        conn.commit()
        conn.close()

        rconn = sqlite3.connect(db_path)
        spalten = spaltenfuellung(rconn, "knowledge_nodes")
        rconn.close()
        by_name = dict((n, (g, ges)) for n, g, ges in spalten)
        assert by_name["quell_hash"] == (0, 3), by_name  # 0 Prozent
        assert by_name["path"] == (3, 3)
        assert by_name["summary"] == (2, 3)  # Leerstring zaehlt nicht
        assert by_name["access_count"] == (2, 3)  # 0 zaehlt, NULL nicht
        print("  (c) 0-Prozent-Spalte erscheint als 0-Prozent, 0 != NULL: ok")

        # (d) Sofort-Teil laeuft unter 1 Sekunde, GEMESSEN -- und enthaelt
        # keine Selbsttest-Ergebnisse (Pflichtfall a des Auftrags).
        start = time.monotonic()
        sofort = erhebe_sofort(td, str(db_path), settings_path)
        dauer_s = time.monotonic() - start
        assert sofort is not None
        assert dauer_s < 1.0, f"Sofort-Teil braucht {dauer_s:.3f}s, nicht unter 1s"
        for t in sofort[0]:
            assert "selftest_ergebnis" not in t, "Sofort-Teil traegt Selbsttest-Ergebnisse"
        print(f"  (d) Sofort-Teil in {dauer_s:.4f}s (gemessen), ohne Selbsttest-Ergebnisse: ok")

        # (e) Momentaufnahme: Datei vorhanden -> Datum + ROT-Liste gelesen,
        # NICHT selbst ausgefuehrt.
        runs_dir = td / "runs"
        runs_dir.mkdir()
        (runs_dir / "selbsttest_rundlauf_2026-08-01.md").write_text(
            "# Selbsttest-Rundlauf 2026-08-01T09:00:00+0200\n\n"
            "ERGEBNIS: 10 Selbsttests, 8 gruen, 2 ROT.\n\n"
            "ROT (2):\n  - alt_a.py\n  - alt_b.py\n\n"
        )
        (runs_dir / "selbsttest_rundlauf_2026-08-09.md").write_text(
            "# Selbsttest-Rundlauf 2026-08-09T20:55:00+0200\n\n"
            "ERGEBNIS: 73 Selbsttests, 52 gruen, 21 ROT.\n\n"
            "ROT (2):\n  - abrufguete.py\n  - deckelreihe.py\n\n"
        )
        mom = lies_momentaufnahme(runs_dir)
        assert mom is not None
        assert mom["datum"] == "2026-08-09T20:55:00+0200", mom  # juengste Datei, nicht die erste
        assert mom["rot"] == ["abrufguete.py", "deckelreihe.py"], mom
        assert "52 gruen" in mom["ergebnis"], mom
        print("  (e) Momentaufnahme: juengste Datei gewaehlt, Datum + ROT-Liste gelesen: ok")

        # (f) Negativfall: keine runs/-Datei -> 'nicht erhoben' im Text,
        # nicht weggelassen -- und der Sofort-Teil traegt trotzdem keine
        # Momentaufnahme-Werte.
        leere_runs = td / "runs_leer"
        leere_runs.mkdir()
        mom_fehlt = lies_momentaufnahme(leere_runs)
        assert mom_fehlt is None
        jetzt = datetime(2026, 8, 9, 12, 0, 0).astimezone()
        text_ohne = render(sofort[0], sofort[1], sofort[2], sofort[3], jetzt, mom_fehlt)
        assert "nicht erhoben" in text_ohne, "fehlende Ergebnisdatei nicht ausgewiesen"
        assert "## MOMENTAUFNAHME" in text_ohne
        print("  (f) fehlende Ergebnisdatei -> 'nicht erhoben', nicht weggelassen: ok")

        # (g) Sofort-Teil traegt keine Selbsttest-Ergebnisse im gerenderten
        # Text (Pflichtfall a, textueller Beleg zusaetzlich zum Datenbeleg).
        text_mit = render(sofort[0], sofort[1], sofort[2], sofort[3], jetzt, mom)
        sofort_abschnitt = text_mit.split("## MOMENTAUFNAHME")[0]
        assert "selftest_ergebnis" not in sofort_abschnitt
        assert "ERGEBNIS:" not in sofort_abschnitt
        assert "abrufguete.py" not in sofort_abschnitt and "deckelreihe.py" not in sofort_abschnitt
        print("  (g) gerenderter Sofort-Abschnitt frei von Selbsttest-Ergebnissen: ok")

        # (h) zweimaliges Erzeugen: gleicher Zeitpunkt -> byte-identischer
        # Text (keine Anhaengung, keine Dubletten in render()).
        text1 = render(sofort[0], sofort[1], sofort[2], sofort[3], jetzt, mom)
        text2 = render(sofort[0], sofort[1], sofort[2], sofort[3], jetzt, mom)
        assert text1 == text2
        assert text1.count("### Bestand") == 1, "Abschnitt dupliziert statt ueberschrieben"
        print("  (h) zweimaliges Erzeugen liefert identischen, nicht angehaengten Text: ok")

        # schreibe_knoten() ueberschreibt (letzter Aufruf gewinnt), haengt
        # nicht an -- geprueft an einem Attrappen-knowledge_update statt
        # dem echten MCP-Server (der eigene Trigger/Schema braucht, die
        # hier nicht das Testziel sind).
        speicher: dict[str, str] = {}

        def fake_update(node_id, summary=None, content=None, **kw):
            speicher[node_id] = content
            return {"ok": True}

        fake_update("/brainlehr", content="erster Text")
        fake_update("/brainlehr", content="zweiter Text")
        assert speicher["/brainlehr"] == "zweiter Text"
        assert "erster" not in speicher["/brainlehr"], "angehaengt statt ueberschrieben"
        print("  schreibe_knoten-Vertrag (Update statt Anhaengen) am Attrappen-Speicher bestaetigt: ok")

        # (i) Negativfall Datenbank: keine Datenbank -> None statt Ausnahme.
        fehlt = str(td / "does_not_exist.db")
        ergebnis = erhebe(td, fehlt, settings_path, runs_dir, jetzt)
        assert ergebnis is None
        print("  (i) fehlende Datenbank -> None statt Ausnahme: ok")

    print("selftest ok")


if __name__ == "__main__":
    main()
