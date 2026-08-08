#!/usr/bin/env python3
"""normbestand.py -- N1 aus docs/PLAN_NORMSCHICHT_2026-08-05.md.

Erfasst den Regelbestand (globale CLAUDE.md, hub-CLAUDE.md, docs/adr/*.md)
und gleicht ihn gegen knowledge_nodes ab. Kein Rang, keine Gueltigkeit --
das ist N2/N3. Hier wird nur festgestellt, was von den 54 regeltragenden
Artefakten im Speicher liegt und was fehlt.

Ablageort der neu angelegten Knoten (Kommentar statt Ermessen im Code):
- Globale CLAUDE.md liegt schon unter /methodik/direktiven (14 von 15
  Abschnitten, vor diesem Lauf angelegt) -- wird unveraendert weiterverwendet.
- hub-CLAUDE.md bekommt einen eigenen Ast /methodik/direktiven-hub. Beide
  Dateien heissen "CLAUDE.md" und ueberschneiden sich inhaltlich (der hub
  importiert die globale) -- ohne getrennten Pfad waeren die Herkuenfte
  nicht mehr auseinanderzuhalten, und genau die Trennung braucht der
  spaetere Rang (global schlaegt Projekt/hub, siehe Plan Kapitel 3).
- ADRs bekommen /methodik/adr, getrennt von den vorhandenen 6 ADR-Knoten,
  die organisch unter /apps/fahrtenbuch, /arch, /openlehr/... liegen --
  jene sind App-ADRs aus fremden docs/adr/-Unterordnern (fahrtenbuch,
  schwarmwacht), nicht die hier erfassten hub-weiten docs/adr/*.md.

Abgleich (Auftrag: "ueber die Herkunft (source) und den Titel, nicht ueber
den Pfad") -- ein Artefakt gilt als vorhanden, wenn ein Knoten mit exakt
gleichem (normalisiertem) Titel existiert ODER dessen source-Feld die
Quelldatei referenziert. Pfade sind aus Titeln erzeugt und damit ohnehin
von den Titeln abhaengig; ein reiner Pfadabgleich wuerde nur verunglueckte
Slugs verstecken.

Usage:
    .venv/bin/python shared-knowledge/normbestand.py pruefe [--json]
    .venv/bin/python shared-knowledge/normbestand.py erfasse [--dry-run|--apply]
    .venv/bin/python shared-knowledge/normbestand.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
HUB_ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import knowledge_mcp_server as kms  # noqa: E402  (nur importiert, nicht geaendert)

GLOBAL_CLAUDE_MD = Path.home() / ".claude" / "CLAUDE.md"
HUB_CLAUDE_MD = HUB_ROOT / "CLAUDE.md"
ADR_DIR = HUB_ROOT / "docs" / "adr"

DIREKTIVEN_GLOBAL_PARENT = "/methodik/direktiven"
DIREKTIVEN_HUB_TITLE = "Direktiven (hub-CLAUDE.md)"
ADR_TITLE = "ADR-Bestand (hub/docs/adr)"

ACTOR = "normbestand.py"


# --- Quellen zerlegen ---------------------------------------------------

@dataclass
class Artefakt:
    title: str
    body: str          # voller Abschnitts-/Dateitext (-> content)
    source_needle: str  # Substring, an dem source-Felder erkannt werden


def parse_sections(text: str) -> list[tuple[str, str]]:
    """Zerlegt an Zeilen, die mit '## ' beginnen (Level-2-Ueberschriften).
    Jeder Abschnitt ist ein Artefakt. Datei ohne solche Ueberschriften ->
    leere Liste (kein Crash, siehe Selbsttest-Fall 4)."""
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current: list[str] | None = None
    title = ""
    for line in lines:
        if line.startswith("## "):
            if current is not None:
                sections.append((title, current))
            title = line[3:].strip()
            current = [line]
        elif current is not None:
            current.append(line)
    if current is not None:
        sections.append((title, current))
    return [(t, "\n".join(ls)) for t, ls in sections]


# --- Quellhash (Auftrag 2026-08-06) -------------------------------------
# Zentrale, einmal implementierte Verfahren -- migrate_quellhash.py
# (Rueckfuellung) UND knowledge_lint.py (Kategorie 11 "Quelle veraltet")
# rufen beide diese Funktionen auf, keine zweite Fassung.

SOURCE_RE = re.compile(r"^erzeugt aus (.+) \(Stand (.+)\)$")


def parse_source(source: str | None) -> tuple[Path, str] | None:
    """Zerlegt eine source-Zeile im von diesem Skript erzeugten Format
    ('erzeugt aus <Datei> (Stand <ISO>)') in Dateipfad und Stand. None, wenn
    das Muster nicht passt (Knoten aus anderer Herkunft, z.B. Konsil) --
    solche Knoten sind hier nicht pruefbar UND das ist kein Fehler.
    ADR-Quellen tragen einen relativen Pfad (siehe load_adr_artefakte:
    "docs/adr/<datei>.md") -- gegen HUB_ROOT aufgeloest, CLAUDE.md-Quellen
    sind schon absolut."""
    if not source:
        return None
    m = SOURCE_RE.match(source.strip())
    if not m:
        return None
    raw_path, stand = m.group(1), m.group(2)
    path = Path(raw_path)
    if not path.is_absolute():
        path = HUB_ROOT / path
    return path, stand


def abschnitt_hash(body: str) -> str:
    """Hash des Abschnitts-/Dateitexts, aus dem ein Knoten erzeugt wurde --
    NICHT der ganzen Datei. Grund (gemessen 2026-08-06): 14 von 87 Knoten
    mit Datei-Herkunft teilten sich EINE Bearbeitung der globalen CLAUDE.md
    und waeren bei dateiweitem Hash alle gleichzeitig als veraltet
    gemeldet worden, obwohl vermutlich nur ein Abschnitt betroffen war."""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def current_section_body(path: Path, title: str) -> str | None:
    """Sucht im JETZIGEN Dateiinhalt denselben Ausschnitt, aus dem ein
    Knoten mit gegebenem Titel erzeugt worden waere. Muss wissen, WELCHE
    Zerlegung der Erzeuger fuer diese Datei benutzt hat -- eine ADR-Datei
    hat oft eigene '## '-Zwischenueberschriften (Kontext/Entscheidung/...),
    aber load_adr_artefakte() nimmt trotzdem die GANZE Datei als Artefakt.
    Ein blosses "hat die Datei irgendwo '## '?" wuerde bei ADRs also die
    falsche (interne) Ueberschrift suchen und faelschlich 'nicht gefunden'
    melden -- deshalb Pfadidentitaet statt Heuristik ueber den Inhalt.

    Fuer Dateien ausserhalb der drei von normbestand.py erfassten Quellen
    (GLOBAL_CLAUDE_MD, HUB_CLAUDE_MD, ADR_DIR) ist die Zerlegung eines
    fremden Erzeugers hier unbekannt -- bester Versuch per Titel-Match,
    sonst ganze Datei. Liefert bewusst auch dann etwas, das NICHT passt,
    wenn der Titel nicht gefunden wird: None, was oben als 'nicht pruefbar'
    gilt, niemals als 'ok'."""
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    try:
        is_adr = path.parent.samefile(ADR_DIR)
    except (OSError, FileNotFoundError):
        is_adr = path.parent == ADR_DIR
    if is_adr:
        return text  # ganze Datei ist das Artefakt, wie load_adr_artefakte()
    sections = parse_sections(text)
    if not sections:
        return text  # keine '## '-Abschnitte -> Volltext ist das Artefakt
    norm_t = _norm_title(title)
    for t, body in sections:
        if _norm_title(t) == norm_t:
            return body
    return None


def quellstatus(source: str | None, title: str, stored_hash: str | None) -> dict:
    """Vergleicht den gespeicherten quell_hash mit dem JETZT aus der Quelle
    berechenbaren Hash. Status: 'kein_verweis' (source zeigt nicht auf eine
    Datei -- z.B. Konsil-Herkunft), 'verschwunden' (Datei existiert nicht
    mehr), 'nicht_pruefbar' (kein Hash gespeichert ODER Abschnitt in der
    Datei nicht mehr auffindbar -- beides macht einen Vergleich unmoeglich,
    nicht nur den ersten Fall), 'geaendert' (Hash weicht ab), 'ok' (Hash
    stimmt)."""
    ref = parse_source(source)
    if ref is None:
        return {"status": "kein_verweis"}
    path, stand = ref
    if not path.exists():
        return {"status": "verschwunden", "quelle": str(path)}
    if stored_hash is None:
        return {"status": "nicht_pruefbar", "quelle": str(path)}
    body = current_section_body(path, title)
    if body is None:
        return {"status": "nicht_pruefbar", "quelle": str(path),
                "grund": "Abschnitt nicht mehr in der Datei gefunden"}
    if abschnitt_hash(body) != stored_hash:
        return {"status": "geaendert", "quelle": str(path)}
    return {"status": "ok", "quelle": str(path)}


# knowledge_lint.py::find_truncated_embeddings warnt ab ~2048 geschaetzten
# Tokens (path+title+summary+content, 3.5 Zeichen/Token -> 7168 Zeichen
# Budget). Mehrere ADR-Dateien ueberschreiten das im Volltext (z.B.
# 002-json-data-layer.md mit 12689 Zeichen) -- ungekuerzt haette dieser Lauf
# den Lint-Befund "Einbettung abgeschnitten" von 3 auf über 10 hochgezogen,
# obwohl Abnahmepunkt 6 genau diese Kategorie unveraendert verlangt. Der
# Volltext bleibt in der Quelldatei (source-Feld verweist darauf) --
# gekuerzt wird nur, was zusaetzlich im Knoten gespeichert wuerde.
CONTENT_BUDGET_CHARS = 6500


def cap_content(body: str, path_hint: str, title: str, summary: str) -> str:
    reserved = len(path_hint) + len(title) + len(summary) + 32
    budget = max(500, CONTENT_BUDGET_CHARS - reserved)
    if len(body) <= budget:
        return body
    cut = body.rfind("\n", 0, budget)
    if cut < budget // 2:
        cut = budget
    return body[:cut].rstrip() + "\n\n… (gekuerzt von normbestand.py, Volltext in der Quelldatei)"


def make_summary(body: str, fallback: str) -> str:
    lines = [
        l.strip() for l in body.splitlines()
        if l.strip() and not l.strip().startswith("#")
    ]
    text = " ".join(lines)
    text = re.sub(r"[*_`]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return fallback
    if len(text) > 280:
        text = text[:277].rsplit(" ", 1)[0].rstrip(",.;: ") + "…"
    return text


def load_claude_md_artefakte(path: Path, stand: str) -> list[Artefakt]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    out = []
    for title, body in parse_sections(text):
        out.append(Artefakt(
            title=title,
            body=body,
            source_needle=f"erzeugt aus {path} (Stand {stand})",
        ))
    return out


def load_adr_artefakte(adr_dir: Path, stand: str) -> list[Artefakt]:
    if not adr_dir.exists():
        return []
    out = []
    for f in sorted(adr_dir.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        title = None
        for line in text.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        title = title or f.stem
        rel = f"docs/adr/{f.name}"
        out.append(Artefakt(
            title=title,
            body=text,
            source_needle=f"erzeugt aus {rel} (Stand {stand})",
        ))
    return out


# --- Abgleich gegen den Speicher -----------------------------------------

def _norm_title(t: str) -> str:
    return re.sub(r"\s+", " ", t.strip()).casefold()


def load_nodes(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT id, path, parent_path, title, source FROM knowledge_nodes"
    ).fetchall()


def find_match(nodes: list[sqlite3.Row], artefakt: Artefakt, category_parent: str) -> sqlite3.Row | None:
    """Titel ist die Identitaet (siehe die 14 realen Direktiven-Knoten: alle
    ueber Titelgleichheit gefunden, nicht ueber den vom Titel abgeleiteten
    Pfad -- Slugs koennen verunglueckt sein). Ein reiner Dateiname-in-
    source-Abgleich waere keine echte Zweitpruefung, sondern eine
    Fehlerquelle: alle Abschnitte einer Datei teilen dieselbe source-Zeile
    ("erzeugt aus <Datei> (Stand ...)"), also traefe er jeden Abschnitt
    derselben Datei gleichermassen.

    Titelgleichheit ALLEIN reicht aber nicht: live gemessen traf die
    hub-CLAUDE.md-Abschnittsueberschrift 'Arbeitsweise' zufaellig einen
    voellig unverwandten Knoten /methodik/arbeitsweise (source:
    scripts/methodik_export.py, anderer Erzeuger, andere Quelle). Deshalb
    zusaetzlich Scope-Pflicht: der Treffer muss unter dem fuer diese Quelle
    vorgesehenen Sammelknoten (category_parent) liegen -- das ist der
    stabile, von uns gewaehlte Container-Pfad, nicht der fragile
    artefakteigene Slug-Pfad, und darum kein Verstoss gegen 'nicht ueber
    den Pfad'."""
    norm_t = _norm_title(artefakt.title)
    for n in nodes:
        if n["parent_path"] == category_parent and _norm_title(n["title"]) == norm_t:
            return n
    return None


def category_slug(title: str) -> str:
    return kms._slugify(title)  # gleiche Ableitung wie knowledge_add selbst


@dataclass
class Abgleich:
    quelle: str
    parent_path: str
    gefunden: list[str] = field(default_factory=list)
    fehlend: list[Artefakt] = field(default_factory=list)
    verwaist: list[str] = field(default_factory=list)
    veraltet: list[str] = field(default_factory=list)  # gefunden, aber Quelle seither geaendert


def pruefe_quelle(conn: sqlite3.Connection, quelle: str, parent_path: str,
                   artefakte: list[Artefakt]) -> Abgleich:
    nodes = load_nodes(conn)
    result = Abgleich(quelle=quelle, parent_path=parent_path)
    matched_paths: set[str] = set()
    for a in artefakte:
        hit = find_match(nodes, a, parent_path)
        if hit:
            result.gefunden.append(a.title)
            matched_paths.add(hit["path"])
            # Abgleich des Quellhashs (Auftrag 2026-08-06) -- derselbe
            # quellstatus() wie migrate_quellhash.py/knowledge_lint.py.
            row = conn.execute(
                "SELECT source, quell_hash FROM knowledge_nodes WHERE path = ?", (hit["path"],)
            ).fetchone()
            if row and quellstatus(row["source"], hit["title"], row["quell_hash"])["status"] == "geaendert":
                result.veraltet.append(hit["path"])
        else:
            result.fehlend.append(a)
    # Verwaiste Knoten: direkte Kinder des Zielpfads ohne Entsprechung im
    # aktuellen Artefaktbestand dieser Quelle.
    for n in nodes:
        if n["parent_path"] == parent_path and n["path"] not in matched_paths:
            result.verwaist.append(n["title"])
    return result


def pruefe(db_path: Path, global_md: Path = GLOBAL_CLAUDE_MD,
           hub_md: Path = HUB_CLAUDE_MD, adr_dir: Path = ADR_DIR,
           stand: str | None = None) -> dict[str, Abgleich]:
    stand = stand or datetime.now().astimezone().isoformat()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        global_arts = load_claude_md_artefakte(global_md, stand)
        hub_arts = load_claude_md_artefakte(hub_md, stand)
        adr_arts = load_adr_artefakte(adr_dir, stand)
        hub_parent = "/methodik/" + category_slug(DIREKTIVEN_HUB_TITLE)
        adr_parent = "/methodik/" + category_slug(ADR_TITLE)
        return {
            "global": pruefe_quelle(conn, str(global_md), DIREKTIVEN_GLOBAL_PARENT, global_arts),
            "hub": pruefe_quelle(conn, str(hub_md), hub_parent, hub_arts),
            "adr": pruefe_quelle(conn, str(adr_dir), adr_parent, adr_arts),
        }
    finally:
        conn.close()


def print_pruefe(results: dict[str, Abgleich], as_json: bool) -> None:
    if as_json:
        out = {
            k: {
                "quelle": v.quelle,
                "parent_path": v.parent_path,
                "gefunden": v.gefunden,
                "fehlend": [a.title for a in v.fehlend],
                "verwaist": v.verwaist,
                "veraltet": v.veraltet,
            }
            for k, v in results.items()
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    for key, v in results.items():
        print(f"\n=== {key}: {v.quelle} -> {v.parent_path} ===")
        print(f"gefunden: {len(v.gefunden)}  fehlend: {len(v.fehlend)}  "
              f"verwaist: {len(v.verwaist)}  veraltet: {len(v.veraltet)}")
        for a in v.fehlend:
            print(f"  fehlt: {a.title}")
        for t in v.verwaist:
            print(f"  verwaist: {t}")
        for t in v.veraltet:
            print(f"  veraltet: {t}")


# --- Schreiben -------------------------------------------------------------

def ensure_category(db_path: Path, title: str, apply: bool) -> str:
    """Legt den Sammelknoten unter /methodik an, falls er fehlt. Gibt den
    (tatsaechlichen oder vorausberechneten) Pfad zurueck. Idempotent ueber
    denselben Titel -> denselben Slug (siehe category_slug)."""
    slug_path = "/methodik/" + category_slug(title)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        exists = conn.execute(
            "SELECT 1 FROM knowledge_nodes WHERE path = ?", (slug_path,)
        ).fetchone()
    finally:
        conn.close()
    if exists or not apply:
        return slug_path
    prev_db_path = kms.DB_PATH
    kms.DB_PATH = db_path
    try:
        res = kms.knowledge_add(
            parent_path="/methodik", title=title,
            summary=f"Sammelknoten, angelegt von normbestand.py (N1, {datetime.now().astimezone().isoformat()}).",
            content="", project_id="shared", tags=["methodik"],
            source="normbestand.py::ensure_category", actor=ACTOR,
        )
    finally:
        kms.DB_PATH = prev_db_path
    if "error" in res:
        raise RuntimeError(f"Sammelknoten {title!r} konnte nicht angelegt werden: {res['error']}")
    return res["path"]


def erfasse(db_path: Path, apply: bool, global_md: Path = GLOBAL_CLAUDE_MD,
            hub_md: Path = HUB_CLAUDE_MD, adr_dir: Path = ADR_DIR) -> dict:
    stand = datetime.now().astimezone().isoformat()
    backup_path = None
    if apply:
        backup_path = db_path.parent / f"knowledge.db.bak-{datetime.now().strftime('%Y%m%dT%H%M%S')}"
        shutil.copy2(db_path, backup_path)

    # Sammelknoten fuer hub-CLAUDE.md und ADRs zuerst -- Kinder brauchen den
    # Elternpfad als Voraussetzung (knowledge_add lehnt unbekannte
    # parent_path sonst ab, siehe P1 im MCP-Server-Docstring).
    hub_parent = ensure_category(db_path, DIREKTIVEN_HUB_TITLE, apply)
    adr_parent = ensure_category(db_path, ADR_TITLE, apply)

    results = pruefe(db_path, global_md, hub_md, adr_dir, stand=stand)
    # ensure_category kann im dry-run einen provisorischen Pfad liefern, der
    # mit dem in pruefe() berechneten uebereinstimmt (gleiche Slug-Ableitung) --
    # zur Sicherheit trotzdem den tatsaechlich verwendeten Pfad einsetzen.
    results["hub"].parent_path = hub_parent
    results["adr"].parent_path = adr_parent

    created = {"global": [], "hub": [], "adr": []}
    if apply:
        for key, target_parent in (("global", DIREKTIVEN_GLOBAL_PARENT),
                                    ("hub", hub_parent), ("adr", adr_parent)):
            prev_db_path = kms.DB_PATH
            kms.DB_PATH = db_path
            try:
                for a in results[key].fehlend:
                    tags = ["methodik", "direktiven"] if key != "adr" else ["methodik", "adr"]
                    if key == "hub":
                        tags = tags + ["hub"]
                    summary = make_summary(a.body, a.title)
                    path_hint = f"{target_parent}/{kms._slugify(a.title)}"
                    res = kms.knowledge_add(
                        parent_path=target_parent, title=a.title,
                        summary=summary,
                        content=cap_content(a.body, path_hint, a.title, summary),
                        project_id="shared", tags=tags,
                        source=a.source_needle, actor=ACTOR,
                    )
                    if "error" in res:
                        raise RuntimeError(f"{key}/{a.title!r}: {res['error']}")
                    created[key].append(res["path"])
                    # quell_hash mitschreiben (Auftrag 2026-08-06) -- kein
                    # Feld in knowledge_add()'s INSERT (tabu, nicht
                    # angefasst), darum Nachtrag per direktem UPDATE. Hash
                    # aus a.body: exakt der Abschnittstext, den
                    # current_section_body() bei einer spaeteren Pruefung
                    # aus derselben Datei wieder herausschneiden wuerde.
                    write_conn = sqlite3.connect(str(db_path))
                    try:
                        write_conn.execute(
                            "UPDATE knowledge_nodes SET quell_hash = ? WHERE path = ?",
                            (abschnitt_hash(a.body), res["path"]),
                        )
                        write_conn.commit()
                    finally:
                        write_conn.close()
            finally:
                kms.DB_PATH = prev_db_path

    return {
        "backup": str(backup_path) if backup_path else None,
        "geplant": {k: [a.title for a in v.fehlend] for k, v in results.items()},
        "angelegt": created,
    }


# --- CLI ---------------------------------------------------------------

def cmd_pruefe(args: argparse.Namespace) -> int:
    results = pruefe(kms.DB_PATH)
    print_pruefe(results, args.json)
    return 0


def cmd_erfasse(args: argparse.Namespace) -> int:
    apply = args.apply  # --dry-run ist nur die Vorgabe, kein zusaetzliches Gate
    out = erfasse(kms.DB_PATH, apply=apply)
    mode = "APPLY" if apply else "DRY-RUN"
    print(f"=== erfasse ({mode}) ===")
    if out["backup"]:
        print(f"Sicherung: {out['backup']}")
    for key in ("global", "hub", "adr"):
        n = len(out["geplant"][key])
        print(f"{key}: {n} anzulegen" + (f", {len(out['angelegt'][key])} angelegt" if apply else ""))
        for t in out["geplant"][key]:
            print(f"  - {t}")
    return 0


# --- Selbsttest ----------------------------------------------------------

def _init_temp_db(path: Path) -> None:
    schema_sql = (HERE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(path))
    conn.executescript(schema_sql)
    now = kms.now_iso()
    conn.execute(
        """INSERT INTO knowledge_nodes
           (id, path, parent_path, project_id, title, summary, content, level, tags, source, created_at, updated_at,
            norm_entscheidung, norm_entschieden_von, norm_entschieden_grund)
           VALUES ('root0001', '/', NULL, 'shared', 'root', 'root', '', 0, '[]', '', ?, ?, 'keine_norm', 'skript:normbestand.py', 'Testvorrichtung: Wurzelknoten')""",
        (now, now),
    )
    conn.execute(
        """INSERT INTO knowledge_nodes
           (id, path, parent_path, project_id, title, summary, content, level, tags, source, created_at, updated_at,
            norm_entscheidung, norm_entschieden_von, norm_entschieden_grund)
           VALUES ('meth0001', '/methodik', '/', 'shared', 'methodik', 'methodik', '', 1, '[]', '', ?, ?, 'keine_norm', 'skript:normbestand.py', 'Testvorrichtung: Sammelknoten')""",
        (now, now),
    )
    conn.commit()
    conn.close()


def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "knowledge.db"
        _init_temp_db(db_path)

        global_md = tmp_path / "global.md"
        global_md.write_text(
            "# Global\n\n"
            "## Vorhanden\n\nDieser Abschnitt existiert schon als Knoten.\n\n"
            "## Fehlend\n\nDieser Abschnitt fehlt noch im Speicher.\n",
            encoding="utf-8",
        )
        # Datei ohne '## '-Ueberschriften (Fall 4)
        hub_md = tmp_path / "hub.md"
        hub_md.write_text("# Hub\n\nNur Fliesstext, keine Abschnitte.\n", encoding="utf-8")
        adr_dir = tmp_path / "adr"
        adr_dir.mkdir()

        stand = "2026-08-05T22:00:00+02:00"

        # Fall 1: "Vorhanden"-Abschnitt vorab als Knoten anlegen (matched
        # per Titel) + ein verwaister Knoten (Fall 3) im selben Ast, der zu
        # keinem aktuellen Abschnitt mehr passt.
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        now = kms.now_iso()
        conn.execute(
            """INSERT INTO knowledge_nodes
               (id, path, parent_path, project_id, title, summary, content, level, tags, source, created_at, updated_at,
                norm_entscheidung, norm_entschieden_von, norm_entschieden_grund)
               VALUES ('dir00001', '/methodik/direktiven', '/methodik', 'shared', 'direktiven', 'x', '', 2, '[]', '', ?, ?, 'keine_norm', 'skript:normbestand.py', 'Testvorrichtung: Sammelknoten')""",
            (now, now),
        )
        conn.execute(
            """INSERT INTO knowledge_nodes
               (id, path, parent_path, project_id, title, summary, content, level, tags, source, created_at, updated_at,
                norm_entscheidung, norm_entschieden_von, norm_entschieden_grund)
               VALUES ('dir00002', '/methodik/direktiven/vorhanden', '/methodik/direktiven', 'shared', 'Vorhanden', 'x', 'x', 3, '[]', ?, ?, ?, 'keine_norm', 'skript:normbestand.py', 'Testvorrichtung: simuliert vorhandenen Direktiven-Knoten')""",
            (f"erzeugt aus {global_md} (Stand {stand})", now, now),
        )
        conn.execute(
            """INSERT INTO knowledge_nodes
               (id, path, parent_path, project_id, title, summary, content, level, tags, source, created_at, updated_at,
                norm_entscheidung, norm_entschieden_von, norm_entschieden_grund)
               VALUES ('dir00003', '/methodik/direktiven/verwaist', '/methodik/direktiven', 'shared', 'Nicht mehr in der Quelle', 'x', 'x', 3, '[]', '', ?, ?, 'keine_norm', 'skript:normbestand.py', 'Testvorrichtung: simuliert verwaisten Knoten')""",
            (now, now),
        )
        conn.commit()
        conn.close()

        results = pruefe(db_path, global_md, hub_md, adr_dir, stand=stand)

        # Fall 1: gefunden
        assert "Vorhanden" in results["global"].gefunden, results["global"].gefunden
        # Fall 2: fehlend
        fehlend_titles = [a.title for a in results["global"].fehlend]
        assert fehlend_titles == ["Fehlend"], fehlend_titles
        # Fall 3: verwaist
        assert results["global"].verwaist == ["Nicht mehr in der Quelle"], results["global"].verwaist
        # Fall 4: Datei ohne Ueberschriften -> keine Artefakte, kein Crash
        assert results["hub"].gefunden == [] and results["hub"].fehlend == [] and results["hub"].verwaist == []

        # erfasse --dry-run legt nichts an
        out_dry = erfasse(db_path, apply=False, global_md=global_md, hub_md=hub_md, adr_dir=adr_dir)
        conn = sqlite3.connect(str(db_path))
        count_before = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        conn.close()
        assert count_before == 5, count_before  # root, methodik, direktiven, vorhanden, verwaist
        assert out_dry["geplant"]["global"] == ["Fehlend"]

        # Fall 5: erfasse --apply, dann zweiter Lauf legt nichts doppelt an
        out_apply1 = erfasse(db_path, apply=True, global_md=global_md, hub_md=hub_md, adr_dir=adr_dir)
        assert out_apply1["backup"] and Path(out_apply1["backup"]).exists()
        assert out_apply1["angelegt"]["global"] == ["/methodik/direktiven/fehlend"], out_apply1["angelegt"]

        conn = sqlite3.connect(str(db_path))
        count_after1 = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        conn.close()

        out_apply2 = erfasse(db_path, apply=True, global_md=global_md, hub_md=hub_md, adr_dir=adr_dir)
        assert out_apply2["angelegt"] == {"global": [], "hub": [], "adr": []}, out_apply2["angelegt"]

        conn = sqlite3.connect(str(db_path))
        count_after2 = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        conn.close()
        assert count_after1 == count_after2, (count_after1, count_after2)

        # Nach dem Apply: pruefe zeigt "Fehlend" jetzt als gefunden
        results2 = pruefe(db_path, global_md, hub_md, adr_dir, stand=stand)
        assert set(results2["global"].gefunden) == {"Vorhanden", "Fehlend"}, results2["global"].gefunden
        assert results2["global"].fehlend == []

    print("SELFTEST OK: alle 5 Faelle gruen (vorhanden, fehlend, verwaist, keine Ueberschriften, idempotent).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    sub = parser.add_subparsers(dest="command")

    p_pruefe = sub.add_parser("pruefe")
    p_pruefe.add_argument("--json", action="store_true")
    p_pruefe.set_defaults(func=cmd_pruefe)

    p_erfasse = sub.add_parser("erfasse")
    grp = p_erfasse.add_mutually_exclusive_group()
    grp.add_argument("--dry-run", action="store_true", default=True)
    grp.add_argument("--apply", action="store_true")
    p_erfasse.set_defaults(func=cmd_erfasse)

    args = parser.parse_args()
    if args.selftest:
        return _selftest()
    if not args.command:
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
