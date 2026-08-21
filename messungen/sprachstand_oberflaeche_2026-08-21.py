"""Zaehlskript zu Auftrag 'Sprachstand der Oberflaeche', 2026-08-21.

ERHEBUNG, kein Bau. Zaehlt nutzersichtbare Textstellen im Repo und klassifiziert
sie mit kern/spracherkennung.py. Nur Lesen -- schreibt ausschliesslich die
Ergebnisdatei runs/sprachstand_oberflaeche_2026-08-21.json.

NUTZERSICHTBAR (Abgrenzung laut Auftrag):
  - print()-Literale in haken/*.py, melder/*.py, berichte/*.py und den drei
    ueber settings.json verdrahteten kern/-Skripten (build_node_index.py,
    normachsen.py, planbindung.py) -- Hook-/Melder-Ausgabe.
  - TOOLS-Dict in knowledge_mcp_server.py: "description"-Werte je Werkzeug
    und je Parameter -- MCP-Werkzeugbeschreibung.
  - raise ValueError/RuntimeError/... mit Literaltext INNERHALB der
    TOOLS[...]["handler"]-Aufrufkette -- die erreichen den Klienten ueber das
    generische `except Exception as e: {"error": str(e)}` in handle_request()
    (Beleg: knowledge_mcp_server.py:7332-7338). MCP-Rueckgabetext.
  - dict-Literale mit Schluessel error/message/hinweis/warnung/grund im
    Quelltext von knowledge_mcp_server.py -- MCP-Rueckgabetext.
  - RAISE(ABORT|FAIL|ROLLBACK, '...') in schema.sql -- Trigger-Fehlertext,
    auf eindeutige Texte verdichtet (INSERT- und UPDATE-Trigger tragen meist
    denselben Text doppelt).

NICHT SICHTBAR (nicht gezaehlt): Docstrings, Kommentare, Testnamen,
Assertion-Texte, Variablennamen -- laut Auftrag nur von jemandem gelesen,
der den Quelltext oeffnet.

GRENZE der Sprachklassifikation (siehe Bericht): kern/spracherkennung.py
braucht >=2 Treffer aus 18 Stoppwoertern je Sprache. Kurze, fachwortdichte
Texte (viele Fundstellen hier: 40-90 Zeichen) unterschreiten das haeufig und
fallen auf None, obwohl sie beim Lesen erkennbar deutsch sind. Das ist im
Ergebnis als eigener Befund ausgewiesen, nicht stillschweigend interpoliert.
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kern.spracherkennung import erkenne, DE, EN, _WORT, _falte  # noqa: E402


# ---------- Literaltext aus AST ----------

def literal_text(node: ast.AST) -> str | None:
    """Konkatenierten Literaltext eines Constant/JoinedStr/BinOp(+)-Knotens,
    oder None, wenn er nicht vollstaendig aus Literalen besteht. Platzhalter
    in f-Strings (FormattedValue) werden durch '{}' ersetzt -- der Rahmentext
    bleibt fuer die Sprachprobe erhalten, der eingesetzte Wert nicht."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(v.value)
            elif isinstance(v, ast.FormattedValue):
                parts.append("{}")
            else:
                return None
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        l = literal_text(node.left)
        r = literal_text(node.right)
        if l is not None and r is not None:
            return l + r
    return None


def find_print_literals(pyfile: Path) -> tuple[list[dict], str | None]:
    try:
        tree = ast.parse(pyfile.read_text(encoding="utf-8"), filename=str(pyfile))
    except Exception as e:  # pragma: no cover - Befund, kein Normalfall
        return [], f"PARSE_ERROR: {e}"
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            if not node.args:
                continue
            txt = literal_text(node.args[0])
            if txt is not None and txt.strip():
                out.append({"line": node.lineno, "text": txt})
    return out, None


def scan_dir_prints(dirname: str) -> dict:
    results: dict = {}
    for pyfile in sorted((ROOT / dirname).glob("*.py")):
        items, err = find_print_literals(pyfile)
        if items:
            results[f"{dirname}/{pyfile.name}"] = items
        if err:
            results.setdefault("__errors__", []).append((pyfile.name, err))
    return results


# ---------- knowledge_mcp_server.py: TOOLS-Beschreibungen + Rueckgabetexte ----------

def extract_mcp_texts(server_file: Path) -> dict:
    src = server_file.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(server_file))

    tool_descs: list[dict] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "TOOLS" for t in node.targets
        ):
            def walk_dict(d: ast.Dict, toolname: str | None):
                for k, v in zip(d.keys, d.values):
                    keytxt = literal_text(k) if k is not None else None
                    if keytxt == "description":
                        txt = literal_text(v)
                        if txt is not None:
                            tool_descs.append({"tool": toolname, "line": v.lineno, "text": txt})
                    elif isinstance(v, ast.Dict):
                        walk_dict(v, toolname)

            for k, v in zip(node.value.keys, node.value.values):
                tname = literal_text(k)
                if isinstance(v, ast.Dict):
                    walk_dict(v, tname)

    raises: list[dict] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            fn = node.exc.func
            fname = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else None)
            if fname in ("ValueError", "RuntimeError", "Exception", "PermissionError", "LookupError", "KeyError"):
                if node.exc.args:
                    txt = literal_text(node.exc.args[0])
                    if txt is not None and txt.strip():
                        raises.append({"line": node.lineno, "exc": fname, "text": txt})

    keys = {"error", "message", "hinweis", "warnung", "grund", "status_text"}
    seen_lines: set[int] = set()
    dict_returns: list[dict] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                keytxt = literal_text(k) if k is not None else None
                if keytxt in keys:
                    txt = literal_text(v)
                    if txt is not None and txt.strip() and v.lineno not in seen_lines:
                        seen_lines.add(v.lineno)
                        dict_returns.append({"line": v.lineno, "key": keytxt, "text": txt})

    return {"tool_param_descriptions": tool_descs, "raises": raises, "dict_returns": dict_returns}


# ---------- schema.sql: RAISE-Texte ----------

def extract_schema_raises(schema_file: Path) -> dict:
    src = schema_file.read_text(encoding="utf-8")
    pat = re.compile(r"RAISE\((?:ABORT|FAIL|ROLLBACK),\s*'((?:[^'\\]|\\.)*)'\)")
    matches = pat.findall(src)
    return {"orte_gesamt": len(matches), "eindeutige_texte": sorted(set(matches))}


# ---------- Sprachklassifikation ----------

def scores(text: str) -> tuple[int, int]:
    if not text:
        return 0, 0
    woerter = _WORT.findall(_falte(text.lower()))
    return sum(1 for w in woerter if w in DE), sum(1 for w in woerter if w in EN)


def klass(text: str) -> dict:
    lang = erkenne(text)
    de, en = scores(text)
    return {
        "sprache": lang,
        "de_score": de,
        "en_score": en,
        "beide_nichtnull": de > 0 and en > 0,
        "zeichen": len(text),
    }


def add_group(groups: dict, name: str, art: str, items: list[dict]) -> None:
    entries = [{**it, **klass(it["text"])} for it in items]
    groups[name] = {
        "art": art,
        "anzahl": len(entries),
        "zeichen_gesamt": sum(e["zeichen"] for e in entries),
        "eintraege": entries,
    }


def main() -> None:
    groups: dict = {}

    haken = scan_dir_prints("haken")
    items = [
        {"ort": f, "line": it["line"], "text": it["text"]}
        for f, its in haken.items() if f != "__errors__" for it in its
    ]
    add_group(groups, "haken_print", "Hook-Meldung", items)

    melder = scan_dir_prints("melder")
    items = [
        {"ort": f, "line": it["line"], "text": it["text"]}
        for f, its in melder.items() if f != "__errors__" for it in its
    ]
    add_group(groups, "melder_print", "Melder-Ausgabe", items)

    berichte = scan_dir_prints("berichte")
    items = [
        {"ort": f, "line": it["line"], "text": it["text"]}
        for f, its in berichte.items() if f != "__errors__" for it in its
    ]
    add_group(groups, "berichte_print_manuell",
              "Melder-Ausgabe (berichte/, manuell aufgerufen -- kein Hook-Ausloeser)", items)

    kern_items = []
    for f in ("kern/build_node_index.py", "kern/normachsen.py", "kern/planbindung.py"):
        its, _ = find_print_literals(ROOT / f)
        kern_items.extend({"ort": f, "line": it["line"], "text": it["text"]} for it in its)
    add_group(groups, "kern_wired_print",
              "Hook-Meldung (kern, ueber settings.json verdrahtet)", kern_items)

    mcp = extract_mcp_texts(ROOT / "knowledge_mcp_server.py")
    add_group(groups, "mcp_tool_beschreibung", "MCP-Werkzeugbeschreibung",
              [{"ort": f"knowledge_mcp_server.py:{it['line']}", "tool": it["tool"], "text": it["text"]}
               for it in mcp["tool_param_descriptions"]])
    add_group(groups, "mcp_raise_rueckgabe", "MCP-Rueckgabetext (raise -> str(e) an Klienten)",
              [{"ort": f"knowledge_mcp_server.py:{it['line']}", "exc": it["exc"], "text": it["text"]}
               for it in mcp["raises"]])
    add_group(groups, "mcp_dict_rueckgabe", "MCP-Rueckgabetext (dict-Literal error/message/...)",
              [{"ort": f"knowledge_mcp_server.py:{it['line']}", "key": it["key"], "text": it["text"]}
               for it in mcp["dict_returns"]])

    schema = extract_schema_raises(ROOT / "schema.sql")
    add_group(groups, "schema_trigger",
              "Trigger-Fehlertext (schema.sql, auf eindeutige Texte verdichtet)",
              [{"ort": "schema.sql", "text": t} for t in schema["eindeutige_texte"]])

    gesamt_anzahl = sum(g["anzahl"] for g in groups.values())
    gesamt_zeichen = sum(g["zeichen_gesamt"] for g in groups.values())

    # ---------- Punkt 4: was ein Nutzer wirklich sieht ----------
    # melder/ausloeserlos.py selbst ausfuehren, nicht seinen letzten Stand zitieren.
    ausloeserlos_proc = subprocess.run(
        [sys.executable, str(ROOT / "melder" / "ausloeserlos.py")],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    ausloeserlos_ausgabe = (ausloeserlos_proc.stdout or "") + (ausloeserlos_proc.stderr or "")
    orphan_dateien = set(re.findall(r"^\s*-\s+(melder/\S+\.py)\s*$", ausloeserlos_ausgabe, re.M))

    orphan_items = [e for e in groups["melder_print"]["eintraege"] if e["ort"] in orphan_dateien]
    erreicht_gesamt = gesamt_anzahl - len(orphan_items)
    erreicht_zeichen = gesamt_zeichen - sum(e["zeichen"] for e in orphan_items)

    verteilung = {"de": [0, 0], "en": [0, 0], "none_unklar": [0, 0]}
    beide_nichtnull = 0
    for g in groups.values():
        for e in g["eintraege"]:
            key = e["sprache"] if e["sprache"] in ("de", "en") else "none_unklar"
            verteilung[key][0] += 1
            verteilung[key][1] += e["zeichen"]
            if e["beide_nichtnull"]:
                beide_nichtnull += 1

    result = {
        "auftrag": "Sprachstand der Oberflaeche, ERHEBUNG",
        "stand": "1354e4db",
        "zeitpunkt": "2026-08-21",
        "gesamt_anzahl_textstellen": gesamt_anzahl,
        "gesamt_zeichen": gesamt_zeichen,
        "sprachverteilung": {
            "de": {"anzahl": verteilung["de"][0], "zeichen": verteilung["de"][1]},
            "en": {"anzahl": verteilung["en"][0], "zeichen": verteilung["en"][1]},
            "none_unklar": {"anzahl": verteilung["none_unklar"][0], "zeichen": verteilung["none_unklar"][1]},
            "davon_beide_stoppwortlisten_treffen_nichtnull": beide_nichtnull,
        },
        "spracherkennung_eignung_kurztexte": (
            "kern/spracherkennung.py verlangt >=2 Stoppworttreffer je Sprache (MINDEST=2). "
            "Bei den hier gezaehlten Textstellen (Median-Laenge deutlich unter 100 Zeichen, "
            "viele Fachbegriffe) faellt der Median-Fall auf None, obwohl von Hand gelesen "
            "eindeutig Deutsch erkennbar ist -- Beispiel: schema.sql-Trigger 'source fehlt: "
            "Herkunft des Knotens angeben (aus welcher Datei/welchem Lauf er stammt)' hat 0 "
            "Treffer in beiden Listen. Das Verfahren ist fuer Fliesstext gebaut (Selbsttest "
            "in kern/spracherkennung.py verwendet ganze Saetze) und fuer kurze, dichte "
            "Textstellen wie hier NICHT geeignet -- die None-Quote je Gruppe ist deshalb "
            "kein Beleg fuer Englisch/unklar, sondern ueberwiegend ein Werkzeuggrenzfall."
        ),
        "je_gruppe": {name: {"art": g["art"], "anzahl": g["anzahl"], "zeichen_gesamt": g["zeichen_gesamt"]}
                      for name, g in groups.items()},
        "schema_sql_rohzahl_vor_verdichtung": schema["orte_gesamt"],
        "punkt4_was_ein_nutzer_wirklich_sieht": {
            "melder_ausloeserlos_lauf": ausloeserlos_ausgabe.strip(),
            "melder_ohne_ausloeser": sorted(orphan_dateien),
            "davon_print_textstellen_unerreichbar": len(orphan_items),
            "davon_zeichen_unerreichbar": sum(e["zeichen"] for e in orphan_items),
            "erreicht_textstellen": erreicht_gesamt,
            "erreicht_zeichen": erreicht_zeichen,
            "einordnung": (
                "melder/ausloeserlos.py prueft settings.json (Projekt UND global "
                "~/.claude/settings.json), geplante Laeufe, Git-Hooks und Aufrufketten. "
                "Alle print()-Textstellen in haken/, kern_wired und knowledge_mcp_server.py "
                "sind darueber erreichbar. berichte/ (41 Textstellen) haengt an KEINEM "
                "Hook -- wird nur erreicht, wenn ein Mensch das Skript manuell aufruft "
                "(so in CLAUDE.md dokumentiert), zaehlt hier NICHT zu 'unerreichbar', weil "
                "es einen benannten Aufrufweg hat, aber auch nicht automatisch zu "
                "'erreicht' im Sinne von Sitzungsstart."
            ),
        },
        "punkt5_nicht_uebersetzbar_ohne_bruch": [
            {
                "fundstelle": "schema.sql (33 eindeutige RAISE-Texte, 58 Fundstellen)",
                "grund": (
                    "Aenderung an der Datei erreicht eine bereits angelegte Datenbank nicht "
                    "von selbst -- CREATE TRIGGER IF NOT EXISTS ergaenzt, ersetzt nicht "
                    "(L-55075a). Nach jeder Aenderung muesste die INSTALLIERTE Fassung "
                    "(select sql from sqlite_master) neu geschrieben werden, nicht nur die "
                    "Datei -- sonst zeigen neue und alte Datenbanken unterschiedliche "
                    "Fehlertexte fuer dieselbe Regel."
                ),
            },
            {
                "fundstelle": "melder/rueckfrageschleife.py:66-134 (FRAGE, STOPP, VORHABEN)",
                "grund": (
                    "Regulaere Ausdruecke pruefen die vom ASSISTENTEN SELBST erzeugte "
                    "Antwort auf deutsche (und seit 2026-08-20 zusaetzlich englische) "
                    "Formulierungsmuster ('soll ich', 'moechtest du', 'wartet auf dich' "
                    "u.a.). Das ist kein print()-Text dieses Auftrags, sondern Vokabular, "
                    "das gegen die Sprache der Modellantwort laeuft -- eine Uebersetzung "
                    "der Oberflaeche aendert nicht diesen Text, wohl aber (mittelbar) die "
                    "Sprache der Antworten, gegen die er prueft."
                ),
            },
            {
                "fundstelle": "melder/korrekturlehre.py:41-51 (KORREKTUR)",
                "grund": (
                    "Regex ausschliesslich auf deutsche Tadel-Formulierungen des "
                    "Betreibers ('warum hast', 'wie oft noch', 'haettest du' u.a.), "
                    "laut Kommentar Zeile fuer Zeile aus echten Nachrichten entnommen. "
                    "Nicht Teil der Oberflaechen-Textmenge, aber vom selben Grundproblem "
                    "betroffen: englische Nachrichten des Betreibers wuerden diesen "
                    "Waechter nicht erreichen."
                ),
            },
            {
                "fundstelle": "melder/nulllinie.py:52-64 (_LEERE, _KONTROLLE)",
                "grund": (
                    "_KONTROLLE prueft auf das Vokabular der Gegenprobe-Pflicht selbst "
                    "('Nulllinie', 'Positivkontrolle', 'Gegenprobe', 'Baseline') in Text, "
                    "den ein Zug oder Bericht erzeugt. Eine Uebersetzung dieser Begriffe an "
                    "anderer Stelle (Berichte, Melderausgaben) liesse den Waechter blind "
                    "werden, ohne dass er selbst geaendert wurde -- exakt die Klasse aus "
                    "L-8fce9c (Waechter prueft Woerter, nicht die Sache)."
                ),
            },
            {
                "fundstelle": "melder/vermutungswaechter.py:210-220 (SPRACHPROBE)",
                "grund": (
                    "Eigene, von kern/spracherkennung.py UNABHAENGIGE Sprachheuristik "
                    "(je 14 Stoppwoerter de/en, Schwelle 3 Treffer/400 Zeichen) zur "
                    "Erkennung der Antwortsprache selbst -- SPRACHPROBE zu uebersetzen "
                    "waere widersinnig, das Woerterbuch IST das Messinstrument."
                ),
            },
            {
                "fundstelle": "In Lehren/Knoten woertlich zitierte Fehlertexte",
                "grund": (
                    "Nicht einzeln nachgezaehlt (ausserhalb des Lese-Auftrags: erfordert "
                    "DB-Zugriff auf hub/shared-knowledge/knowledge.db), aber laut "
                    "CLAUDE.md-Vorgabe (~/.claude/CLAUDE.md) mehrfach belegtes Muster: "
                    "L-55075a, L-8fce9c, L-dfdb00, L-0e0ab6, L-b034c4 zitieren Trigger- "
                    "bzw. Waechtertexte woertlich als Beleg. Wird der zitierte Text "
                    "spaeter uebersetzt, zeigt die Lehre einen Text, der im Code nicht "
                    "mehr vorkommt -- Befund, kein gezaehlter Fund dieser Erhebung."
                ),
            },
        ],
        "punkt6_vorhandene_uebersetzungsschicht": {
            "gefunden": False,
            "wege_geprueft": [
                "grep -rniE gettext|i18n|locale|translations (Repo, ohne node_modules/worktrees): 0 Treffer",
                "find *.po *.mo: 0 Treffer",
                "python3 hub/scripts/symbolindex.py uebersetzung: kein Treffer in brainlehr "
                "(einzige Treffer ausserhalb: openlehr-Steuerformular, hub-Desktop-App)",
                "python3 hub/scripts/symbolindex.py mehrsprachigkeit: kein Treffer in brainlehr "
                "(Treffer nur in hub/begod/desktop)",
            ],
            "verwandter_aber_anderer_befund": (
                "BDW-P10 (docs/REQUIREMENTS_BRAINLEHR.md) legt fest, dass jeder "
                "Wissenseintrag seine Sprache traegt und der Speicher AUSDRUECKLICH kein "
                "Uebersetzungssystem ist ('Uebersetzung ist ein Problem der Ausgabe, "
                "nicht des Speichers'). Das betrifft die Sprache gespeicherter Wissens- "
                "INHALTE, nicht die Oberflaechen-Texte aus diesem Auftrag -- keine "
                "Ueberschneidung mit der hier gezaehlten Menge, aber dieselbe Systemachse."
            ),
        },
        "gruppen_detail": groups,
    }

    out = ROOT / "runs" / "sprachstand_oberflaeche_2026-08-21.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"geschrieben: {out}")
    print(f"gesamt_anzahl_textstellen={gesamt_anzahl} gesamt_zeichen={gesamt_zeichen}")
    print(json.dumps(result["sprachverteilung"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
