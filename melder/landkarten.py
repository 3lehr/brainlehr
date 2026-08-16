#!/usr/bin/env python3
"""Vier Landkarten des brainlehr-Universums, erzeugt statt gepflegt.

Betreiberentscheidung 2026-08-16 (docs/PLAN_DIAGRAMME_2026-08-16.md,
Fortschreibung 07:05): Die Karten beschreiben das SYSTEM, nicht den
Datenbestand -- sie stehen eine Ebene ueber dem Wissensraum und bekommen einen
eigenen Punkt in der Seitenleiste. Ein sechster "Blick" neben Baum und
Bedeutung behauptete eine Gleichrangigkeit, die es nicht gibt.

  verbund       Repos, Datenspeicher, Ports, Startwege  (melder/verbundkarte.py)
  anwendung     Bildschirme und Bedienwege des atelier   (Swift-Quelltext)
  code/<repo>   Modul-Abhaengigkeiten eines Python-Repos (ast, echte Importe)
  bestand       Aeste und Kanten des Wissensbestands     (Datenbank)

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
    karten = [karte_verbund(), karte_anwendung(), karte_bestand()]
    karten += [karte_code(r) for r in repos_fuer_code]
    return karten


def schreiben(karten: list[tuple[str, str, str]]) -> list[Path]:
    ZIEL.mkdir(parents=True, exist_ok=True)
    geschrieben = []
    for kennung, titel, inhalt in karten:
        p = ZIEL / f"{kennung}.md"
        p.write_text(f"# {titel}\n\n**Erzeugt von `melder/landkarten.py` — nicht von Hand "
                     f"ändern.**\n\n{inhalt}", encoding="utf-8")
        geschrieben.append(p)
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
