#!/usr/bin/env python3
"""Fuenf Landkarten des brainlehr-Universums, erzeugt statt gepflegt.

Betreiberentscheidung 2026-08-16 (docs/PLAN_DIAGRAMME_2026-08-16.md,
Fortschreibung 07:05): Die Karten beschreiben das SYSTEM, nicht den
Datenbestand -- sie stehen eine Ebene ueber dem Wissensraum und bekommen einen
eigenen Punkt in der Seitenleiste. Ein sechster "Blick" neben Baum und
Bedeutung behauptete eine Gleichrangigkeit, die es nicht gibt.

  verbund       Repos, Datenspeicher, Ports, Startwege  (melder/verbundkarte.py)
  anwendung     Bildschirme und Bedienwege des atelier   (Swift-Quelltext)
  code/<repo>   Modul-Abhaengigkeiten eines Python-Repos (ast, echte Importe)
  bestand       Aeste und Kanten des Wissensbestands     (Datenbank)
  agenten       Ereignis -> Haken -> Skript              (beide settings.json)

NULL MODELLAUFRUFE, pruefbar an den Importen: nur Standardbibliothek plus
verbundkarte. Kein Klient, kein embeddings. Eine erzeugte Karte ist bei jedem
Lauf so aktuell wie ihre Quelle; eine geschriebene ist ab dem naechsten Commit
falsch.

KEIN ZEITSTEMPEL in den Erzeugnissen -- sie werden committet, damit der Diff
zeigt, was sich an der ARCHITEKTUR geaendert hat. Ein Zeitstempel machte jeden
Lauf zu einer Aenderung und den Diff unlesbar. Wann etwas entstand, sagt
`git log`.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sqlite3
import sys
from pathlib import Path

_w = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_w), str(_w / "melder"), str(_w / "kern")]

import verbundkarte  # noqa: E402

VERBUND = _w.parent
ZIEL = _w / "docs" / "karten"


def _id(text: str) -> str:
    return re.sub(r"\W", "_", text)


# Erklaerungen je Knoten, von den Erzeugern gefuellt und in die .json
# gelegt. Ohne sie ist die Karte ein Bild: "chronist.py" sagt niemandem
# etwas, der ihn nicht ohnehin kennt.
ERKLAERUNGEN: dict = {}


# Woran man erkennt, dass ein Haken ENTSCHEIDET statt nur zu melden: er gibt
# eine Entscheidung an den Aufrufer zurueck (`permissionDecision`/`decision`)
# oder bricht mit dem Code ab, der die Handlung blockiert (2). Alles andere
# schreibt bestenfalls eine Zeile, die niemand liest -- der Unterschied ist
# die Frage des Betreibers "wo werden Entscheidungen getroffen".
_ENTSCHEIDET = re.compile(r"permissionDecision|[\"']decision[\"']|exit\(2\)|sys\.exit\(2\)")


def _kurz(pfad: Path) -> str:
    """Pfad relativ zum Verbund, sonst relativ zum Benutzerverzeichnis mit ~.
    Ein Haken aus ~/.claude/skills/ gehoert NICHT zu diesem Verbund und wird
    von hier aus nicht mitgepflegt -- das soll man an der Angabe sehen."""
    for wurzel, praefix in ((VERBUND, ""), (Path.home(), "~/")):
        try:
            return praefix + str(pfad.relative_to(wurzel))
        except ValueError:
            continue
    return str(pfad)


def _zweck(pfad: Path) -> str:
    """Die erste Zeile des Docstrings -- die einzige Beschreibung, die mit dem
    Code zusammen gepflegt wird. Fehlt sie, wird das GESAGT statt geraten:
    ein Baustein ohne ein Wort zu seinem Zweck ist selbst ein Befund."""
    try:
        baum = ast.parse(pfad.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, SyntaxError, ValueError):
        return ""
    d = ast.get_docstring(baum)
    return (d or "").strip().split("\n")[0][:160]


def _entscheidet(pfad: Path) -> bool:
    try:
        return bool(_ENTSCHEIDET.search(pfad.read_text(encoding="utf-8", errors="ignore")))
    except OSError:
        return False


# ── Karte 1: der Verbund ──────────────────────────────────────────────────

def karte_verbund() -> tuple[str, str, str]:
    k = verbundkarte.karte()
    bild, weggelassen = verbundkarte.als_mermaid(k)
    hinweis = ""
    if weggelassen:
        hinweis = (f"\n{len(weggelassen)} Verbindungen sind im Bild weggelassen, weil nur EIN "
                   "Repo daran haengt und sie damit keine Verbundaussage sind: "
                   + "; ".join(weggelassen) + ".\n")
    return ("verbund", "Der Verbund — wer redet mit wem",
            bild + "\n" + hinweis)


# ── Karte 2: Aufbau der Anwendung ─────────────────────────────────────────

def karte_anwendung() -> tuple[str, str, str]:
    """Bildschirme und Bedienwege des atelier, aus dem Swift-Quelltext.

    Gelesen wird, was die Oberflaeche TATSAECHLICH anbietet: die Faelle von
    SeitenleistenEintrag und WissensraumBlick sowie die Pfade der
    Steuerschnittstelle. Eine von Hand gepflegte Bildschirmliste waere schon
    heute falsch -- genau diese Karte entstand, weil ein Eintrag hinzukam und
    niemand ausser dem Quelltext davon wusste."""
    quelle = _w / "app" / "Sources" / "Atelier"
    haupt = (quelle / "HauptFenster.swift").read_text(encoding="utf-8", errors="ignore")
    web = (quelle / "WissensraumWebView.swift").read_text(encoding="utf-8", errors="ignore")
    steuer = (quelle / "Steuerschnittstelle.swift").read_text(encoding="utf-8", errors="ignore")

    def titel_aus(text: str, enumname: str) -> list[str]:
        """NUR die `titel`-Eigenschaft, nicht der ganze enum-Rumpf: der erste
        Versuch am 2026-08-16 fing die `symbol`-Eigenschaft mit und zeichnete
        `doc.text.magnifyingglass` als Bildschirm neben `Quellen`. Beide Bloecke
        haben dieselbe Form `case .x: return "..."` -- unterscheidbar sind sie
        nur an der Eigenschaft, in der sie stehen."""
        block = re.search(rf"enum {enumname}\b.*?\n\}}", text, re.S)
        if not block:
            return []
        titelblock = re.search(r"var titel: String \{.*?\n    \}", block.group(0), re.S)
        if not titelblock:
            return []
        return re.findall(r'case \.\w+: return "([^"]+)"', titelblock.group(0))

    eintraege = titel_aus(haupt, "SeitenleistenEintrag")
    blicke = titel_aus(web, "WissensraumBlick")
    pfade = sorted(set(re.findall(r'case (?:GET|POST) "(/\w[\w/-]*)"', steuer))
                   or set(re.findall(r'"(/(?:zustand|blick|ansicht|gesundheit)[\w/-]*)"', steuer)))

    z = ["```mermaid", "graph LR", '  app(["atelier"])']
    for e in eintraege:
        z.append(f'  {_id(e)}["{e}"]')
        z.append(f"  app --> {_id(e)}")
    for b in blicke:
        z.append(f'  blick_{_id(b)}("{b}")')
        z.append(f"  {_id('Wissensraum')} --> blick_{_id(b)}")
    if pfade:
        z.append('  steuerung>"Steuerschnittstelle (nur Debug)"]')
        z.append("  steuerung -.->|steuert| app")
    z.append("```")
    text = "\n".join(z)
    if pfade:
        text += "\n\nWege der Steuerschnittstelle: " + ", ".join(f"`{p}`" for p in pfade) + "\n"
    return ("anwendung", "Aufbau der Anwendung — Bildschirme und Bedienwege", text)


# ── Karte 5: Agenten und ihre Auslöser ────────────────────────────────────

def karte_agenten() -> tuple[str, str, str]:
    """Wer laeuft hier eigentlich los, und woran haengt er?

    Betreiberwunsch 2026-08-16 nach dem Morpheus-Video ueber Agenten-Workflows:
    "wir sollten unsere agenten workflows auch zeichnen!" Gezeichnet wird
    nicht, was ein Ablaufplan VORSIEHT, sondern was tatsaechlich verdrahtet
    ist: Ereignis -> Haken -> Skript, dazu die Agententypen.

    ZWEI Einstellungsdateien werden gelesen, und das ist der Punkt: die
    globale (~/.claude/settings.json) UND die repo-eigene. Wer nur eine
    liest, misst falsch -- an einem Tag in beide Richtungen passiert
    (L-ca836f). Die Karte zeigt deshalb je Haken, aus WELCHER Datei er
    stammt.

    Ein Haken ohne Ereignis kann nicht feuern -- solche Skripte erscheinen
    als Waise (`melder/ausloeserlos.py` prueft dieselbe Frage in Textform)."""
    quellen = [(Path.home() / ".claude" / "settings.json", "global"),
               (_w / ".claude" / "settings.json", "repo")]
    z = ["```mermaid", "graph LR"]

    # DER LAUF SELBST, als Rueckgrat. Ohne ihn zeigt die Karte nur
    # "Ereignis -> Skript" und damit NIE einen Kreis -- der Betreiber hat
    # genau das bemerkt ("ich sehe nirgends loops!"). Der Kreis ist aber echt
    # und belegt:
    #
    #   * Nach jedem Werkzeugaufruf geht es zurueck zum Modell, das den
    #     naechsten waehlt (PostToolUse -> Modell -> PreToolUse -> ...).
    #   * Und der Haltepunkt ist kein Ende: haken/knowledge_capture_hook.py
    #     gibt in Zeile 121 `{"decision": "block"}` zurueck und schickt den
    #     Lauf zurueck in die Schleife. Ein Stop, der nicht stoppt.
    #
    # Beides steht im Quelltext, nicht in einer Vorstellung davon, wie
    # Agenten arbeiten.
    z += [
        '  subgraph lauf["Der Lauf eines Agenten"]',
        '    modell(["Modell entscheidet"])',
        '    werkzeug["Werkzeug laeuft"]',
        '    halt(["Haltepunkt"])',
        '    modell -->|waehlt| werkzeug',
        '    werkzeug -->|Ergebnis| modell',
        '    modell -->|fertig?| halt',
        '    halt -->|decision: block| modell',
        "  end",
    ]
    # Die Ereignisse haengen an ihren Stationen des Laufs -- damit sieht man,
    # WO ein Haken in die Schleife greift, nicht nur DASS er existiert.
    station = {"UserPromptSubmit": "modell", "PreToolUse": "werkzeug",
               "PostToolUse": "werkzeug", "Stop": "halt",
               "SubagentStart": "modell", "SubagentStop": "halt",
               "SessionStart": "modell", "WorktreeCreate": "werkzeug"}
    gesehen: set[str] = set()
    zahl = 0
    for pfad, herkunft in quellen:
        if not pfad.exists():
            continue
        try:
            daten = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for ereignis, eintraege in sorted((daten.get("hooks") or {}).items()):
            eid = f"ev_{_id(ereignis)}"
            if eid not in gesehen:
                z.append(f'  {eid}(["{ereignis}"])')
                if ereignis in station:
                    z.append(f"  {station[ereignis]} -.->|loest aus| {eid}")
                gesehen.add(eid)
            for eintrag in eintraege:
                for haken in eintrag.get("hooks", []):
                    befehl = str(haken.get("command", ""))
                    # Nur der Skriptname, nicht die ganze Befehlszeile: die
                    # traegt Pfade, Umleitungen und Argumente und macht jeden
                    # Kasten unlesbar.
                    treffer = re.findall(r"([\w./-]+\.(?:py|sh))", befehl)
                    name = Path(treffer[0]).name if treffer else (befehl.split()[0] if befehl else "?")
                    sid = f"s_{_id(name)}"
                    if sid not in gesehen:
                        z.append(f'  {sid}["{name}"]')
                        gesehen.add(sid)
                        # Der Pfad steht in der Befehlszeile -- daraus Zweck
                        # und Entscheidungsbefugnis lesen.
                        kandidat = Path(treffer[0]) if treffer else None
                        if kandidat and not kandidat.is_absolute():
                            kandidat = VERBUND / kandidat
                        zweck = _zweck(kandidat) if kandidat and kandidat.exists() else ""
                        trifft = _entscheidet(kandidat) if kandidat and kandidat.exists() else False
                        ERKLAERUNGEN[sid] = {
                            "zweck": zweck or "Keine Beschreibung im Quelltext.",
                            "entscheidet": trifft,
                            # Haken liegen nicht alle im Verbund -- einige stammen aus
                            # ~/.claude/skills/. Ein relative_to() darauf wirft, und
                            # die Herkunft AUSSERHALB ist gerade die interessante
                            # Information: dieser Baustein wird von hier aus nicht
                            # mitgepflegt.
                            "quelle": _kurz(kandidat) if kandidat and kandidat.exists() else "",
                        }
                        if trifft:
                            z.append(f"  class {sid} entscheidet")
                    z.append(f"  {eid} -->|{herkunft}| {sid}")
                    zahl += 1
    agenten = sorted((Path.home() / ".claude" / "agents").glob("*.md")) if \
        (Path.home() / ".claude" / "agents").exists() else []
    for a in agenten:
        aid = f"ag_{_id(a.stem)}"
        z.append(f'  {aid}>"Agent {a.stem}"]')
    z.append("  classDef waise stroke-dasharray: 5 5")
    # Entscheider werden im Bild dicker umrandet -- die Antwort auf "wo
    # werden Entscheidungen getroffen" soll man sehen, nicht nachschlagen.
    z.append("  classDef entscheidet stroke-width:4px")
    z.append("```")
    return ("agenten", "Agenten und ihre Auslöser — was wirklich verdrahtet ist",
            "\n".join(z) + f"\n\n{zahl} Verdrahtungen aus zwei Einstellungsdateien "
                           f"(global und repo-eigen — wer nur eine liest, misst falsch), "
                           f"{len(agenten)} Agententypen. Ein Ereignis, an dem nichts "
                           f"hängt, kann nichts auslösen.\n")


# ── Karte 3: Code-Struktur je Repo ────────────────────────────────────────

def _modul(pfad: Path, wurzel: Path) -> str:
    """Erste Verzeichnisebene unter der Repo-Wurzel, sonst der Dateiname --
    dieselbe Kornung wie hub/scripts/codemap.py sie fuer Dart waehlt. Eine
    Karte je EINZELNER Datei waere kein Ueberblick, sondern das Verzeichnis
    noch einmal."""
    rel = pfad.relative_to(wurzel)
    return rel.parts[0] if len(rel.parts) > 1 else rel.stem


def _kanten_sammeln(wurzel: Path, fein: bool) -> tuple[dict, set]:
    """fein=False: Modul == erste Verzeichnisebene. fein=True: Modul == Datei.

    Beides wird gebraucht, weil die Repos verschieden gebaut sind: brainlehr
    hat kern/, melder/, haken/ und ergibt grob 22 Kanten; hub legt alles flach
    in scripts/, wo die grobe Koernung ALLE Kanten zu Selbstbezuegen macht --
    gemessen 2026-08-16: "12 Module, 0 Verbindungen". Eine leere Karte ist dort
    keine Aussage ueber das Repo, sondern ueber die gewaehlte Koernung."""
    kanten: dict[tuple[str, str], int] = {}
    module: set[str] = set()

    def name(p: Path) -> str:
        return p.stem if fein else _modul(p, wurzel)

    for datei in verbundkarte._dateien(wurzel, endungen=(".py",)):
        quelle = name(datei)
        module.add(quelle)
        try:
            baum = ast.parse(datei.read_text(encoding="utf-8", errors="ignore"))
        except (SyntaxError, ValueError, OSError):
            continue
        for knoten in ast.walk(baum):
            namen = []
            if isinstance(knoten, ast.Import):
                namen = [a.name.split(".")[0] for a in knoten.names]
            elif isinstance(knoten, ast.ImportFrom) and knoten.module and knoten.level == 0:
                namen = [knoten.module.split(".")[0]]
            for n in namen:
                # Nur repo-eigene Ziele: ein Pfeil auf `json` oder `numpy` sagt
                # nichts ueber den Aufbau DIESES Repos. Gesucht wird an zwei
                # Orten -- Repo-Wurzel und Verzeichnis der importierenden Datei,
                # genau wie der Suchpfad zur Laufzeit.
                ziel = None
                for ort in (wurzel, datei.parent):
                    if (ort / f"{n}.py").exists():
                        ziel = name(ort / f"{n}.py")
                        break
                    if (ort / n).is_dir():
                        ziel = n if fein else _modul(ort / n / "__init__.py", wurzel)
                        break
                if ziel and ziel != quelle:
                    kanten[(quelle, ziel)] = kanten.get((quelle, ziel), 0) + 1
                    module.add(ziel)
    return kanten, module


def karte_code(repo: str) -> tuple[str, str, str]:
    """Modul-Abhaengigkeiten eines Python-Repos, ueber `ast` statt Regex.

    `hub/scripts/codemap.py` kann das seit langem -- aber nur fuer Dart. Ein
    zweites kleines Lesegeraet fuer Python ist billiger als eine Abstraktion
    ueber zwei Sprachen (Plan, "Was NICHT getan wird")."""
    wurzel = VERBUND / repo
    kanten, module = _kanten_sammeln(wurzel, fein=False)
    koernung = "Verzeichnis"
    if not kanten and len(module) > 1:
        # Alles liegt in EINEM Verzeichnis -- grob betrachtet ist jede Kante
        # ein Selbstbezug. Dann eine Ebene feiner, statt eine leere Karte
        # auszuliefern, die wie "keine Abhaengigkeiten" aussieht.
        kanten, module = _kanten_sammeln(wurzel, fein=True)
        koernung = "Datei"
    z = ["```mermaid", "graph LR"]
    for m in sorted(module):
        z.append(f'  {_id(m)}["{m}"]')
    for (a, b), n in sorted(kanten.items()):
        z.append(f"  {_id(a)} -->|{n}| {_id(b)}")
    z.append("```")
    return (f"code-{repo}", f"Code-Struktur: {repo}",
            "\n".join(z) + f"\n\nEin Kasten ist {'ein Verzeichnis' if koernung == 'Verzeichnis' else 'eine Datei'}, "
                           f"die Zahl an der Kante sagt, wie viele Dateien diesen Weg gehen. "
                           f"{len(module)} Module, {len(kanten)} Verbindungen.\n")


# ── Karte 4: der Wissensbestand ───────────────────────────────────────────

def karte_bestand() -> tuple[str, str, str]:
    """Aeste des Bestands und die Kanten ZWISCHEN ihnen.

    Bewusst nicht die 9495 Aehnlichkeitskanten einzeln (Plan, "Was NICHT getan
    wird"): ein Graph, in dem fast jeder Knoten mit fast jedem verbunden ist,
    zeigt nichts. Auf Astebene verdichtet ist dieselbe Information lesbar --
    und beantwortet die Frage, die man wirklich hat: welche Gebiete haengen
    zusammen."""
    db = _w / "brainlehr.db"
    if not db.exists():
        return ("bestand", "Der Wissensbestand", "_Keine Datenbank gefunden._\n")
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    aeste = c.execute(
        "SELECT substr(path, 2, instr(substr(path,2)||'/', '/')-1) AS ast, COUNT(*) "
        "FROM knowledge_nodes WHERE zurueckgezogen = 0 GROUP BY ast ORDER BY 2 DESC").fetchall()
    # knowledge_relations traegt PFADE, nicht Knoten-IDs (gemessen am
    # 2026-08-16, nachdem ein JOIN ueber from_id/to_id an genau dieser
    # Annahme scheiterte). Damit faellt der Verbund mit knowledge_nodes weg --
    # der Ast steht schon im Pfad.
    kanten = c.execute("""
        SELECT substr(source_path, 2, instr(substr(source_path,2)||'/', '/')-1),
               substr(target_path, 2, instr(substr(target_path,2)||'/', '/')-1),
               COUNT(*)
        FROM knowledge_relations
        GROUP BY 1, 2 HAVING COUNT(*) >= 20 ORDER BY 3 DESC LIMIT 40""").fetchall()
    c.close()
    z = ["```mermaid", "graph LR"]
    for ast_, n in aeste:
        z.append(f'  {_id(ast_)}["{ast_}<br/>{n}"]')
    gezeigt = 0
    for a, b, n in kanten:
        if a and b and a != b:
            z.append(f"  {_id(a)} ---|{n}| {_id(b)}")
            gezeigt += 1
    z.append("```")
    return ("bestand", "Der Wissensbestand — Äste und ihre Verbindungen",
            "\n".join(z) + f"\n\nZahl im Kasten = Knoten im Ast, Zahl an der Kante = "
                           f"Verbindungen zwischen zwei Ästen (ab 20, hoechstens 40 "
                           f"staerkste; {gezeigt} gezeigt).\n")


# ── Ablage ────────────────────────────────────────────────────────────────

def alle(repos_fuer_code: list[str]) -> list[tuple[str, str, str]]:
    karten = [karte_verbund(), karte_anwendung(), karte_agenten(), karte_bestand()]
    karten += [karte_code(r) for r in repos_fuer_code]
    return karten


# Knotenformen, die die Karten benutzen -- die Klammern tragen Bedeutung:
# [] Repo/Modul, ([]) Port, [()] Datenspeicher, >] Startweg von aussen, () Blick.
# Einrueckung ist BELIEBIG, nicht genau zwei: in einem `subgraph` sind es
# vier, und mit `^\s{2}` fielen genau die Kanten des Agenten-Laufs heraus --
# die Karte meldete dann "0 Kreise" fuer einen Graphen, der sichtbar einen
# enthielt.
_KNOTEN = re.compile(r'^\s+(\w+)(\[\(|\(\[|\[|\(|>)"?([^"\]\)]*)"?')
_KANTE = re.compile(r"^\s+(\w+)\s+(-{2,3}>|-\.->|-{3})(?:\|([^|]*)\|)?\s+(\w+)")
_KLASSE = re.compile(r"^\s+class (\w+) (\w+)")


def graph_aus_mermaid(mermaid: str) -> dict:
    """Knoten und Kanten AUS dem erzeugten Bild lesen, statt sie ein zweites
    Mal zu erheben.

    Der Umweg ist Absicht: Filter und Wegsuche brauchen den Graphen als Daten
    (ein Bild kennt keine Wege), und zwei getrennte Erhebungen desselben
    Sachverhalts laufen frueher oder spaeter auseinander -- eine Fehlerklasse,
    die dieses Haus zur Genuege kennt. Kommen die Daten aus dem Bild, koennen
    sie ihm per Konstruktion nicht widersprechen. Die Kennungen sind dieselben,
    die Mermaid in das SVG schreibt; darum laesst sich ein gefundener Weg
    danach direkt im Bild einfaerben."""
    knoten: dict[str, dict] = {}
    kanten: list[dict] = []
    formen = {"[": "kasten", "([": "port", "[(": "speicher", ">": "startweg", "(": "blick"}
    for zeile in mermaid.splitlines():
        m = _KANTE.match(zeile)
        if m:
            von, pfeil, text, nach = m.groups()
            kanten.append({"von": von, "nach": nach, "text": (text or "").strip(),
                           "art": "gestrichelt" if pfeil == "-.->" else
                                  ("ungerichtet" if pfeil == "---" else "gerichtet")})
            for i in (von, nach):
                knoten.setdefault(i, {"id": i, "text": i, "form": "kasten", "waise": False})
            continue
        m = _KNOTEN.match(zeile)
        if m:
            kennung, klammer, text = m.groups()
            eintrag = knoten.setdefault(kennung, {"id": kennung, "text": text or kennung,
                                                  "form": "kasten", "waise": False})
            eintrag["text"] = (text or kennung).replace("<br/>", " · ")
            eintrag["form"] = formen.get(klammer, "kasten")
            continue
        m = _KLASSE.match(zeile)
        if m and m.group(2) == "waise":
            knoten.setdefault(m.group(1), {"id": m.group(1), "text": m.group(1),
                                           "form": "kasten", "waise": False})["waise"] = True
    return {"knoten": sorted(knoten.values(), key=lambda k: k["id"]), "kanten": kanten}


def schreiben(karten: list[tuple[str, str, str]]) -> list[Path]:
    """Je Karte ZWEI Dateien aus EINEM Lauf: das Bild fuer Auge, GitHub und
    Diff, die Daten fuer Filter und Wegsuche."""
    ZIEL.mkdir(parents=True, exist_ok=True)
    geschrieben = []
    for kennung, titel, inhalt in karten:
        p = ZIEL / f"{kennung}.md"
        p.write_text(f"# {titel}\n\n**Erzeugt von `melder/landkarten.py` — nicht von Hand "
                     f"ändern.**\n\n{inhalt}", encoding="utf-8")
        geschrieben.append(p)

        anfang, ende = inhalt.find("```mermaid"), inhalt.find("```", inhalt.find("```mermaid") + 10)
        mermaid = inhalt[anfang + len("```mermaid"):ende] if ende > anfang >= 0 else ""
        d = ZIEL / f"{kennung}.json"
        graph = graph_aus_mermaid(mermaid)
        for k in graph["knoten"]:
            if k["id"] in ERKLAERUNGEN:
                k.update(ERKLAERUNGEN[k["id"]])
        d.write_text(json.dumps({"kennung": kennung, "titel": titel, **graph},
                                indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        geschrieben.append(d)
    return geschrieben


def demo() -> None:
    """Selbsttest ohne Datenbank und ohne Dateisystem-Annahmen: prueft die
    Zusagen, die man dem fertigen Bild nicht ansieht."""
    assert _id("code-brainlehr") == "code_brainlehr"
    assert _id("/nasa-llis") == "_nasa_llis"

    kennung, titel, inhalt = karte_anwendung()
    assert kennung == "anwendung"
    assert "Wissensraum" in inhalt, "die Seitenleiste muss aus dem Quelltext gelesen sein"
    assert inhalt.count("```mermaid") == 1, "genau ein Diagramm je Karte"

    # Der Rueckbau ist Teil der Entscheidung: 'Verbund' darf NICHT mehr als
    # Blick des Wissensraums auftauchen, sonst behauptet die Karte wieder eine
    # Gleichrangigkeit mit Baum und Bedeutung.
    assert 'blick_Verbund("Verbund")' not in inhalt, (
        "Verbund ist kein Blick des Wissensraums mehr, sondern eine eigene Sicht")
    # Der Graph muss aus dem Bild lesbar sein -- sonst haben Filter und
    # Wegsuche eine andere Wahrheit als die Zeichnung.
    probe = """
  hub["hub"]
  port_8799(["Port 8799"])
  db_x[("x.db")]
  mcp_k>"MCP k"]
  hub -->|lauscht| port_8799
  hub -.->|liest| db_x
  mcp_k -->|startet| hub
  class db_x waise
"""
    g = graph_aus_mermaid(probe)
    formen = {k["id"]: k["form"] for k in g["knoten"]}
    assert formen == {"hub": "kasten", "port_8799": "port", "db_x": "speicher",
                      "mcp_k": "startweg"}, formen
    assert [k["waise"] for k in g["knoten"] if k["id"] == "db_x"] == [True]
    assert len(g["kanten"]) == 3, g["kanten"]
    assert {"von": "hub", "nach": "db_x", "text": "liest", "art": "gestrichelt"} in g["kanten"]
    assert next(k for k in g["knoten"] if k["id"] == "port_8799")["text"] == "Port 8799"
    print("demo: ok")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--code", nargs="*", default=["brainlehr"],
                   help="Repos fuer die Code-Karte (Vorgabe: brainlehr)")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    karten = alle(a.code)
    if a.json:
        print(json.dumps([{"kennung": k, "titel": t} for k, t, _ in karten],
                         indent=2, ensure_ascii=False))
        return
    for pfad in schreiben(karten):
        print(f"geschrieben: {pfad.relative_to(_w)}", file=sys.stderr)


if __name__ == "__main__":
    demo()
    main()
