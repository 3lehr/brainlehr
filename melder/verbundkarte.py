#!/usr/bin/env python3
"""Schritt 1 aus docs/PLAN_DIAGRAMME_2026-08-16.md -- die Karte des Verbunds:
wer redet hier mit wem, und WORUEBER.

Anlass, woertlich vom Betreiber am 2026-08-16: "Wir haben inzwischen so viel
Code Pfade Apps usw. und selbst keinen Ueberblick mehr!" -- mit der Auflage,
dass die Darstellung "automatisch mit moeglichst wenig ki" entsteht und
aktuell bleibt.

NULL MODELLAUFRUFE, und das ist pruefbar: dieses Modul importiert weder einen
Klienten noch kern/embeddings.py, es liest ausschliesslich Dateien. Das ist
kein Sparzwang, sondern der Grund, warum die Karte nicht altert -- ein
erzeugtes Diagramm ist bei jedem Lauf so aktuell wie der Quelltext, ein
geschriebenes ist ab dem naechsten Commit falsch.

VIER QUELLEN, alle deterministisch:
  Repos          Verzeichnisse mit .git direkt unter der Verbundwurzel
  Datenspeicher  *.db in einer Repo-Wurzel + wer ihren Namen im Quelltext nennt
  Dienste/Ports  wer auf 127.0.0.1:<port> lauscht, und wer ihn anspricht
  Startwege      MCP-Server aus ~/.claude.json, LaunchAgents aus ~/Library

WAS DIE KARTE AUCH ZEIGT, und das ist der Punkt: **was NICHT verbunden ist.**
Ein Datenspeicher ohne Leser, ein Dienst ohne Klienten. Eine Karte, die nur
Vorhandenes zeigt, verschweigt genau den Befund, der dieses Haus seit dem
2026-08-13 beschaeftigt ("gebaut, laufend, meldend, wirkungslos").

KEIN ZEITSTEMPEL IM ERZEUGNIS -- Absicht, keine Nachlaessigkeit. Das
Erzeugnis wird committet, damit der Diff zeigt, was sich an der ARCHITEKTUR
geaendert hat; ein Zeitstempel machte jeden Lauf zu einer Aenderung und den
Diff damit unlesbar. Wann die Karte entstand, beantwortet `git log`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

VERBUND = Path(__file__).resolve().parents[2]

# Verzeichnisse, die beim Absuchen des Quelltextes nie betreten werden.
# .claude/worktrees ist der wichtigste: ein Arbeitsbaum ist eine KOPIE, seine
# Fundstellen wuerden jede Kante mehrfach zaehlen (gemessen: symbolindex.py
# meldet fuer eine einzige Dart-Klasse "+17 weitere Worktrees").
UEBERSPRUNGEN = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "worktrees",
    "_LOCAL_CACHE.nosync", "archive", "build", ".build", "DerivedData",
    "site-packages", ".mypy_cache", ".pytest_cache", "dist",
}

PORT_LAUSCHT = re.compile(r"""(?:HTTPServer|serve_forever|--port|listen)\D{0,40}?(\d{4,5})""")
PORT_RUFT = re.compile(r"""(?:127\.0\.0\.1|localhost)[:/](\d{4,5})""")

# Ein Port, der als NAME statt als Zahl in der Adresse steht:
#   http://127.0.0.1:\(port)/     Swift-Interpolation
#   http://localhost:{PORT}/      Python-f-string
#   http://127.0.0.1:$PORT/       Shell
# Ohne diesen Fall fehlte die erste Kante, an der die Karte gepruefte wurde:
# das atelier ruft 8799 ueber DienstAufsicht.basisURL, und der Regex fand nur
# Ziffern. Eine Karte, die eine bekannte Verbindung nicht zeigt, ist ein Bild
# und keine Karte -- deshalb wird der Name im GLEICHEN Dateitext aufgeloest.
PORT_RUFT_SYMBOLISCH = re.compile(
    r"""(?:127\.0\.0\.1|localhost)[:/][\\({$]{1,2}(\w+)""")


def _symbol_aufloesen(text: str, name: str) -> str | None:
    """`static let port = 8799`, `PORT = 8799`, `port: int = 8799`.
    Nur im selben Dateitext -- eine repoweite Aufloesung waere ein Ratespiel
    mit gleichnamigen Konstanten."""
    m = re.search(rf"\b{re.escape(name)}\b\s*(?::\s*\w+\s*)?=\s*(\d{{4,5}})", text)
    return m.group(1) if m else None

# Erzeugte oder gebuendelte Dateien tragen keine Architekturaussage, sondern
# Zufallszahlen: der erste Lauf meldete "Port 0000, lauscht:
# spikes/univer_i3_min/probe3/bundle.js" -- eine Ziffernfolge aus
# minifiziertem Fremdcode, die durch PORT_LAUSCHT rutschte. Ein Rauschwert in
# einer Uebersichtskarte ist teurer als eine fehlende Kante: er kostet beim
# Lesen jedes Mal die Pruefung, ob er echt ist.
ERZEUGT = re.compile(r"(\.min\.|bundle\.|\.g\.dart$|_pb2\.py$|\.freezed\.)")


def _gueltiger_port(p: str) -> bool:
    """Nur registrierte/dynamische Ports. Sperrt fuehrende Nullen mit ab
    ('0000' war der erste Fehlalarm)."""
    return p.isdigit() and not p.startswith("0") and 1024 <= int(p) <= 65535


def _dateien(wurzel: Path, endungen=(".py", ".swift", ".sh", ".js", ".dart")):
    """Quelltextdateien unterhalb wurzel, sortiert -- die Sortierung ist die
    halbe Determinismus-Zusage (os.walk allein ist es nicht)."""
    treffer = []
    for ordner, unter, dateien in os.walk(wurzel):
        unter[:] = sorted(d for d in unter if d not in UEBERSPRUNGEN and not d.startswith("."))
        for d in sorted(dateien):
            if d.endswith(endungen) and not ERZEUGT.search(d):
                treffer.append(Path(ordner) / d)
    return treffer


def repos(wurzel: Path) -> list[str]:
    return sorted(p.name for p in wurzel.iterdir() if (p / ".git").exists())


def datenspeicher(wurzel: Path, namen: list[str]) -> dict:
    """DB-Datei -> {'repo': wo sie liegt, 'leser': [Repos, die ihren Namen nennen]}.

    Gesucht wird der DATEINAME, nicht der Pfad: brainlehr.db wird ueber
    kern/speicher aufgeloest (Hausregel: Pfade nie fest verdrahten), taucht im
    Quelltext also als blosser Name auf. Ein Pfadvergleich faende null Leser
    und meldete jeden Speicher als verwaist -- ein Fehlalarm, der die
    interessanteste Aussage der Karte entwertet."""
    gefunden = {}
    for repo in namen:
        for db in sorted((wurzel / repo).glob("*.db")):
            gefunden[db.name] = {"repo": repo, "leser": set()}
    if not gefunden:
        return {}
    muster = re.compile("|".join(re.escape(n) for n in sorted(gefunden)))
    for repo in namen:
        for datei in _dateien(wurzel / repo):
            try:
                text = datei.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for name in set(muster.findall(text)):
                gefunden[name]["leser"].add(repo)
    return {k: {"repo": v["repo"], "leser": sorted(v["leser"])} for k, v in sorted(gefunden.items())}


def dienste(wurzel: Path, namen: list[str]) -> dict:
    """Port -> {'lauscht': [repo/datei], 'ruft': [Repos]}.

    Ein Port mit Lauscher und ohne Rufer ist ein Dienst, den niemand nutzt;
    einer mit Rufern und ohne Lauscher ist ein Aufruf ins Leere. Beides sind
    Befunde, deshalb werden die Seiten getrennt gefuehrt statt verschmolzen."""
    gefunden: dict[str, dict] = {}
    for repo in namen:
        for datei in _dateien(wurzel / repo):
            try:
                text = datei.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            rel = f"{repo}/{datei.relative_to(wurzel / repo)}"
            for port in set(PORT_LAUSCHT.findall(text)):
                if _gueltiger_port(port):
                    gefunden.setdefault(port, {"lauscht": set(), "ruft": set()})["lauscht"].add(rel)
            rufe = set(PORT_RUFT.findall(text))
            for name in set(PORT_RUFT_SYMBOLISCH.findall(text)):
                aufgeloest = _symbol_aufloesen(text, name)
                if aufgeloest:
                    rufe.add(aufgeloest)
            for port in rufe:
                if _gueltiger_port(port):
                    gefunden.setdefault(port, {"lauscht": set(), "ruft": set()})["ruft"].add(repo)
    return {p: {"lauscht": sorted(v["lauscht"]), "ruft": sorted(v["ruft"])}
            for p, v in sorted(gefunden.items(), key=lambda t: int(t[0]))}


def startwege(wurzel: Path) -> dict:
    """MCP-Server (~/.claude.json) und LaunchAgents (~/Library/LaunchAgents).

    Beide sind Startwege von AUSSERHALB des Verbunds -- sie stehen in keinem
    Repo und tauchen in keiner Codesuche auf. Genau deshalb gehoeren sie auf
    die Karte: ein Dienst, den nur launchd kennt, ist sonst unsichtbar."""
    mcp, agenten = {}, {}
    konf = Path.home() / ".claude.json"
    if konf.exists():
        try:
            d = json.loads(konf.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            d = {}
        for name, eintrag in sorted((d.get("mcpServers") or {}).items()):
            teile = [str(eintrag.get("command", ""))] + [str(a) for a in eintrag.get("args", [])]
            ziel = next((t for t in teile if str(wurzel) in t), "")
            mcp[name] = {"ziel": ziel.replace(str(wurzel) + "/", ""), "extern": not ziel}
    for plist in sorted((Path.home() / "Library" / "LaunchAgents").glob("*.plist")):
        try:
            text = plist.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if str(wurzel) not in text:
            continue
        treffer = re.findall(rf"{re.escape(str(wurzel))}/(\S+?\.py)", text)
        agenten[plist.stem] = sorted(set(treffer))
    return {"mcp": mcp, "launchagents": agenten}


def _knoten_id(text: str) -> str:
    """Mermaid-Kennung: nur Buchstaben, Ziffern, Unterstrich."""
    return re.sub(r"\W", "_", text)


def _repos_an_port(v: dict) -> set:
    return {x.split("/")[0] for x in v["lauscht"]} | set(v["ruft"])


def als_mermaid(k: dict, alles: bool = False) -> tuple[str, list[str]]:
    """Ein Diagramm, keine Galerie -- und der Unterschied ist gemessen: der
    erste volle Lauf ueber 27 Repos ergab 539 Zeilen Mermaid. Das ist die
    Tapete, vor der der Plan bei den Aehnlichkeitskanten warnt, nur mit Ports
    statt Knoten.

    Der Zuschnitt ist deshalb inhaltlich, nicht heuristisch: **ins Bild kommt,
    was zwei verschiedene Repos verbindet.** Ein Port, den nur fahrtenbuch
    nutzt, ist eine Eigenschaft von fahrtenbuch und keine Aussage ueber den
    VERBUND -- er gehoert in die Codemap dieses Repos (Schritt 3 des Plans),
    nicht hierher. Ein erster Versuch mit einer Zahlenschwelle ("ab 3 Rufern")
    schnitt dieselbe Menge willkuerlich und liess sich nicht begruenden.

    Zwei Ausnahmen bleiben drin, obwohl sie nur EIN Repo beruehren, weil sie
    der eigentliche Ertrag der Karte sind:
      - **Waisen** -- ein Dienst ohne Klienten, ein Speicher ohne Leser.
      - **Startwege von aussen** -- MCP und launchd stehen in keinem Repo.

    Rueckgabe ist ein PAAR: Diagramm und die Liste dessen, was es nicht
    zeigt. Eine stille Kappung liest sich wie Vollstaendigkeit; wer kappt,
    sagt es (Hausregel). `alles=True` hebt den Zuschnitt auf."""
    z = ["```mermaid", "graph LR"]
    weggelassen: list[str] = []
    for port, v in k["dienste"].items():
        if not v["lauscht"] and not v["ruft"]:
            continue
        # Waise heisst hier NUR: im Verbund gebaut, aber von niemandem
        # gerufen -- der Befund "gebaut, laufend, wirkungslos". Der
        # umgekehrte Fall (gerufen, kein Lauscher) ist fast immer ein
        # FREMDdienst: 11434 ist Ollama, 3307 MySQL, 1234 LM Studio. Die als
        # Waisen zu markieren waere ein Fehlalarm in genau der Spalte, auf
        # die es ankommt.
        verwaist = bool(v["lauscht"]) and not v["ruft"]
        extern = not v["lauscht"]
        if not alles and len(_repos_an_port(v)) < 2 and not verwaist:
            weggelassen.append(f"Port {port} (nur {', '.join(sorted(_repos_an_port(v)))})")
            continue
        pid = f"port_{port}"
        z.append(f'  {pid}(["Port {port}{" (fremd)" if extern else ""}"])')
        # Auf REPO-Ebene entdoppelt: vier Dateien desselben Repos an einem
        # Port sind eine Kante, nicht vier (der erste Lauf zeichnete
        # openlehr_legacy viermal an Port 4242).
        for rid in sorted({x.split("/")[0] for x in v["lauscht"]}):
            z.append(f"  {_knoten_id(rid)} -->|lauscht| {pid}")
        for rufer in sorted(set(v["ruft"]) - {x.split("/")[0] for x in v["lauscht"]}):
            z.append(f"  {_knoten_id(rufer)} -->|ruft| {pid}")
        if verwaist:
            z.append(f"  class {pid} waise")
    for db, v in k["datenspeicher"].items():
        if not alles and len(set(v["leser"]) | {v["repo"]}) < 2 and v["leser"]:
            weggelassen.append(f"{db} (nur {v['repo']})")
            continue
        did = f"db_{_knoten_id(db)}"
        z.append(f'  {did}[("{db}")]')
        z.append(f"  {_knoten_id(v['repo'])} -->|liegt| {did}")
        for leser in v["leser"]:
            if leser != v["repo"]:
                z.append(f"  {_knoten_id(leser)} -.->|liest| {did}")
        if not v["leser"]:
            z.append(f"  class {did} waise")
    for name, v in k["startwege"]["mcp"].items():
        mid = f"mcp_{_knoten_id(name)}"
        z.append(f'  {mid}>"MCP {name}"]')
        if v["ziel"]:
            z.append(f"  {mid} -->|startet| {_knoten_id(v['ziel'].split('/')[0])}")
        else:
            z.append(f"  class {mid} waise")
    for name, ziele in k["startwege"]["launchagents"].items():
        aid = f"la_{_knoten_id(name)}"
        z.append(f'  {aid}>"launchd {name}"]')
        for ziel in ziele:
            z.append(f"  {aid} -->|startet| {_knoten_id(ziel.split('/')[0])}")
    z.append("  classDef waise stroke-dasharray: 5 5")
    z.append("```")
    return "\n".join(z), weggelassen


def als_markdown(k: dict, alles: bool = False) -> str:
    bild, weggelassen = als_mermaid(k, alles)
    t = ["# Verbundkarte", "",
         "**Erzeugt von `melder/verbundkarte.py` -- nicht von Hand aendern.**",
         "Kein Zeitstempel: das Erzeugnis soll sich nur aendern, wenn sich die",
         "Architektur aendert. Wann es entstand, sagt `git log -- docs/VERBUNDKARTE.md`.",
         "", bild, "",
         "Gestrichelte Umrandung = **niemand haengt dran**.", ""]
    if weggelassen:
        t += [f"Im Bild weggelassen ({len(weggelassen)}), weil nur EIN Repo daran haengt und "
              "damit keine Verbundaussage -- **in den Tabellen unten vollstaendig**: "
              + "; ".join(weggelassen) + ".", ""]

    t += ["## Datenspeicher", "", "| Datei | liegt in | gelesen von |", "|---|---|---|"]
    for db, v in k["datenspeicher"].items():
        leser = ", ".join(v["leser"]) or "**niemand**"
        t.append(f"| `{db}` | {v['repo']} | {leser} |")

    t += ["", "## Dienste", "", "| Port | lauscht | gerufen von |", "|---|---|---|"]
    for port, v in k["dienste"].items():
        t.append(f"| {port} | {', '.join(f'`{x}`' for x in v['lauscht']) or '**niemand**'} "
                 f"| {', '.join(v['ruft']) or '**niemand**'} |")

    t += ["", "## Startwege von aussen", "",
          "Weder im Quelltext noch in einer Codesuche sichtbar -- deshalb hier.", ""]
    for name, v in k["startwege"]["mcp"].items():
        t.append(f"- MCP `{name}` -> {'`' + v['ziel'] + '`' if v['ziel'] else '**ausserhalb des Verbunds**'}")
    for name, ziele in k["startwege"]["launchagents"].items():
        t.append(f"- launchd `{name}` -> {', '.join(f'`{z}`' for z in ziele) or '**kein Ziel im Verbund**'}")

    t += ["", "## Repos", "", ", ".join(f"`{r}`" for r in k["repos"]), ""]
    return "\n".join(t)


def karte(wurzel: Path = VERBUND, nur: list[str] | None = None) -> dict:
    namen = repos(wurzel)
    if nur:
        namen = [n for n in namen if n in nur]
    return {
        "repos": namen,
        "datenspeicher": datenspeicher(wurzel, namen),
        "dienste": dienste(wurzel, namen),
        "startwege": startwege(wurzel),
    }


def demo() -> None:
    """Selbsttest ohne Dateisystem-Annahmen: prueft die zwei Zusagen, die
    kein Blick auf das Bild bestaetigen kann -- dass Waisen als solche
    markiert werden, und dass die Kennungen mermaid-tauglich sind."""
    k = {
        "repos": ["a", "b"],
        "datenspeicher": {"leer.db": {"repo": "a", "leser": []},
                          "voll.db": {"repo": "a", "leser": ["a", "b"]}},
        "dienste": {"8799": {"lauscht": ["a/dienst.py"], "ruft": ["b"]},
                    "9000": {"lauscht": [], "ruft": ["b"]}},
        "startwege": {"mcp": {"k-1": {"ziel": "a/srv.py", "extern": False},
                              "fremd": {"ziel": "", "extern": True}},
                      "launchagents": {"de.x.y": ["a/dienst.py"]}},
    }
    m, weggelassen = als_mermaid(k, alles=True)
    assert "class db_leer_db waise" in m, "Speicher ohne Leser muss als Waise markiert sein"
    assert "class db_voll_db waise" not in m, "Speicher MIT Lesern darf keine Waise sein"
    assert "class port_9000 waise" not in m, (
        "Port OHNE Lauscher im Verbund ist ein Fremddienst (Ollama, MySQL), keine Waise")
    k2 = dict(k, dienste={"8799": {"lauscht": ["a/d.py", "a/e.py"], "ruft": []}})
    m2, _ = als_mermaid(k2, alles=True)
    assert "class port_8799 waise" in m2, (
        "im Verbund gebaut und von niemandem gerufen -- DAS ist die Waise")
    assert m2.count("a -->|lauscht| port_8799") == 1, (
        "zwei Dateien desselben Repos sind eine Kante, nicht zwei")
    assert "class mcp_fremd waise" in m, "MCP-Server ausserhalb des Verbunds ist eine Waise"
    assert "-" not in m.split("classDef")[0].split("mcp_k")[1][:3], (
        "Bindestrich in einer Mermaid-Kennung -- das Diagramm bricht still")
    assert als_markdown(k) == als_markdown(k), "zweimal erzeugt, zweimal gleich"

    # Symbolischer Port -- die Kante, die beim ersten Lauf gegen den echten
    # Bestand fehlte (atelier -> 8799 ueber `URL(string: "http://127.0.0.1:\(port)/")`).
    swift = 'static let port = 8799\nstatic let basisURL = URL(string: "http://127.0.0.1:\\(port)/")!'
    assert not PORT_RUFT.findall(swift), "Voraussetzung: der Ziffern-Regex findet hier nichts"
    namen = PORT_RUFT_SYMBOLISCH.findall(swift)
    assert namen == ["port"], f"symbolischer Portname nicht erkannt: {namen}"
    assert _symbol_aufloesen(swift, "port") == "8799", "Konstante nicht aufgeloest"
    assert _symbol_aufloesen(swift, "fehlt") is None, "unbekannter Name darf nichts erfinden"
    assert _symbol_aufloesen("port = 80", "port") is None, "zu kurzer Port ist kein Treffer"
    print("demo: ok")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default=None, help="Zieldatei, sonst nach stdout")
    p.add_argument("--json", action="store_true", help="Rohdaten statt Markdown")
    p.add_argument("--nur", nargs="*", default=None, help="nur diese Repos")
    p.add_argument("--alles", action="store_true",
                   help="auch Ports ohne Lauscher ins Bild (Vorgabe: nur in die Tabelle)")
    a = p.parse_args()
    k = karte(nur=a.nur)
    text = json.dumps(k, indent=2, ensure_ascii=False) if a.json else als_markdown(k, a.alles)
    if a.out:
        Path(a.out).write_text(text + "\n", encoding="utf-8")
        print(f"geschrieben: {a.out} ({len(text)} Zeichen)", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    demo()
    main()
