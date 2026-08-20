#!/usr/bin/env python3
"""Erzeugt docs/WAS_BRAINLEHR_KANN.md aus dem Quellcode.

ANLASS (Betreiberweisung 2026-08-20): *"einzusatzt im fahrtebuch protokolieren
wir mit was jeder screen usw kann?!! das sollten wir auch hier mit brainlehr
machen"* -- fuer die README auf GitHub, eine Bedienanleitung, den Abgleich mit
dem Lastenkatalog und die technische Doku.

VORBILD IST fahrtenbuch_nativ/tool/bildschirmkarte.py, und die Begruendung
dort gilt hier woertlich: eine von Hand gepflegte Liste ist nach zwei
Sitzungen falsch, und dann schlimmer als keine. Der Gegenstand ist hier nur
ein anderer -- brainlehr hat keine Bildschirme, es hat WERKZEUGE.

VIER GEGENSTAENDE, alle aus dem Code gelesen, keiner abgetippt:

  1. MCP-Werkzeuge -- aus der echten TOOLS-Tabelle des Servers IMPORTIERT,
     nicht per Regexp geraten. Damit kann die Karte nicht behaupten, es gebe
     ein Werkzeug, das der Server nicht anbietet.
  2. Melder -- erste Zeile des Modul-Docstrings, plus ob sie VERDRAHTET sind
     (~/.claude/settings.json) und ob sie einen Selbsttest haben. Ein Melder
     ohne Ausloeser zaehlt als keiner; das gehoert in die Karte, nicht in eine
     Fussnote.
  3. Haken -- welches Ereignis sie bedienen, aus derselben Einstellungsdatei.
  4. Katalogzeilen (BDW-/INT-), die eine Datei im Text nennt. Das ist der
     Abgleich mit dem Lastenkatalog, den der Betreiber verlangt hat: welche
     Anforderung hat ueberhaupt Code, der sich auf sie beruft.

`--pruefen` vergleicht die erzeugte Datei mit dem Quellstand und meldet, wenn
sie veraltet ist -- ohne diesen Modus waere die Karte genau die handgepflegte
Liste, gegen die sie gebaut ist.

    tool/faehigkeitskarte.py --bauen
    tool/faehigkeitskarte.py --pruefen
    tool/faehigkeitskarte.py --selbsttest
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
ZIEL = WURZEL / "docs" / "WAS_BRAINLEHR_KANN.md"
EINSTELLUNGEN = Path.home() / ".claude" / "settings.json"
KATALOGZEILE = re.compile(r"\b(BDW-[A-Z]+-?\d+|INT-[A-Z]+-\d+)\b")


def mcp_werkzeuge() -> list[tuple[str, str]]:
    """(Name, Beschreibung) aus der ECHTEN Tabelle des Servers."""
    sys.path[:0] = [str(WURZEL)]
    try:
        import knowledge_mcp_server as kms
    except Exception:
        return []
    return sorted((name, (spec.get("description") or "").strip())
                  for name, spec in kms.TOOLS.items())


def _erster_satz(text: str, hoechstens: int = 190) -> str:
    """Erster Satz, gedeckelt.

    Die Werkzeugbeschreibungen des Servers sind bis zu 2 000 Zeichen lang --
    richtig fuer ein Modell, das entscheiden muss, ob es das Werkzeug ruft,
    unbrauchbar fuer eine Uebersichtstabelle. Der Volltext bleibt dort, wo er
    hingehoert: im Werkzeug selbst."""
    text = " ".join((text or "").split())
    for trenner in (". ", " -- ", " — "):
        if trenner in text[:hoechstens + 60]:
            text = text.split(trenner, 1)[0]
            break
    return text[:hoechstens].rstrip(" ,;:") + ("…" if len(text) > hoechstens else "")


def _erste_zeile(pfad: Path) -> str:
    try:
        text = pfad.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    m = re.search(r'"""(.*?)(?:\n|""")', text, re.S)
    return (m.group(1).strip() if m else "").rstrip(".")


def verdrahtung() -> dict[str, list[str]]:
    """Modulname -> Ereignisse, in denen er haengt."""
    try:
        d = json.loads(EINSTELLUNGEN.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    treffer: dict[str, list[str]] = {}
    for ereignis, gruppen in (d.get("hooks") or {}).items():
        for g in gruppen:
            for h in g.get("hooks", []):
                b = h.get("command", "")
                for teil in re.findall(r"([\w_]+)\.py", b):
                    treffer.setdefault(teil, [])
                    if ereignis not in treffer[teil]:
                        treffer[teil].append(ereignis)
    return treffer


def module(ordner: str) -> list[dict]:
    hooks = verdrahtung()
    out = []
    for p in sorted((WURZEL / ordner).glob("*.py")):
        if p.name.startswith("_"):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        out.append({
            "name": p.stem,
            "pfad": f"{ordner}/{p.name}",
            "zweck": _erste_zeile(p),
            "ereignisse": hooks.get(p.stem, []),
            "selbsttest": "--selftest" in text or "--selbsttest" in text,
            "katalog": sorted(set(KATALOGZEILE.findall(text))),
        })
    return out


def baue() -> str:
    jetzt = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    kopf = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=WURZEL,
                          capture_output=True, text=True).stdout.strip()
    werkzeuge = mcp_werkzeuge()
    melder = module("melder")
    haken = module("haken")
    kern = module("kern")

    z = [f"# Was brainlehr kann",
         "",
         f"Erzeugt aus dem Quellcode am {jetzt} (Stand `{kopf}`) von "
         "`tool/faehigkeitskarte.py`. **Nicht von Hand bearbeiten** — eine "
         "handgepflegte Liste ist nach zwei Sitzungen falsch und dann "
         "schlimmer als keine.",
         "",
         "## Auf einen Blick",
         "",
         f"| | |", "|---|---:|",
         f"| Werkzeuge über MCP | {len(werkzeuge)} |",
         f"| Melder | {len(melder)}, davon verdrahtet "
         f"{sum(1 for m in melder if m['ereignisse'])} |",
         f"| Haken | {len(haken)}, davon verdrahtet "
         f"{sum(1 for h in haken if h['ereignisse'])} |",
         f"| Kernmodule | {len(kern)} |",
         f"| Module mit Selbsttest | "
         f"{sum(1 for m in melder + haken + kern if m['selbsttest'])} von "
         f"{len(melder) + len(haken) + len(kern)} |",
         "",
         "## Werkzeuge — was ein Klient aufrufen kann",
         "",
         "Das ist die Bedienoberfläche von brainlehr. Jede Zeile kommt aus der "
         "Werkzeugtabelle des Servers selbst, nicht aus einer Doku daneben.",
         "", "| Werkzeug | Was es tut |", "|---|---|"]
    for name, beschr in werkzeuge:
        z.append(f"| `{name}` | {_erster_satz(beschr).replace('|', '/')} |")

    for titel, liste, erklaerung in (
        ("Melder — was das System über sich selbst prüft", melder,
         "Ein Melder ohne Auslöser zählt als keiner. Die Spalte **wirkt** sagt, "
         "ob er tatsächlich an einem Ereignis hängt."),
        ("Haken — was bei jedem Prompt und jedem Werkzeugaufruf läuft", haken,
         "Diese Module bestimmen, was ohne Zutun in den Kontext gelangt."),
    ):
        z += ["", f"## {titel}", "", erklaerung, "",
              "| Modul | Zweck | wirkt | Selbsttest | Katalog |", "|---|---|---|---|---|"]
        for m in liste:
            wirkt = ", ".join(m["ereignisse"]) if m["ereignisse"] else "—"
            z.append(f"| `{m['pfad']}` | {_erster_satz(m['zweck'], 100).replace('|', '/')} | "
                     f"{wirkt} | {'ja' if m['selbsttest'] else '—'} | "
                     f"{', '.join(m['katalog'][:3]) or '—'} |")

    z += ["", "## Kern — worauf alles aufsetzt", "",
          "| Modul | Zweck | Selbsttest |", "|---|---|---|"]
    for m in kern:
        z.append(f"| `{m['pfad']}` | {_erster_satz(m['zweck'], 100).replace('|', '/')} | "
                 f"{'ja' if m['selbsttest'] else '—'} |")

    # Abgleich mit dem Lastenkatalog: welche Anforderung hat Code, der sich
    # auf sie beruft? Das ist die Gegenrichtung zur Belegspalte -- dort steht,
    # ob eine Zeile geprueft ist, hier, ob sie ueberhaupt jemanden hat.
    beruft = {}
    for m in melder + haken + kern:
        for k in m["katalog"]:
            beruft.setdefault(k, []).append(m["pfad"])
    z += ["", "## Abgleich mit dem Lastenkatalog", "",
          f"{len(beruft)} Katalogzeilen werden im Code ausdrücklich genannt. "
          "Eine Zeile ohne Nennung hat keinen Code, der sich auf sie beruft — "
          "das ist die Gegenrichtung zur Belegspalte, die sagt, ob geprüft wurde.",
          "", "| Katalogzeile | genannt in |", "|---|---|"]
    for k in sorted(beruft):
        z.append(f"| `{k}` | {', '.join(sorted(beruft[k])[:4])} |")
    return "\n".join(z) + "\n"


def _selbsttest() -> int:
    t = baue()
    assert "# Was brainlehr kann" in t
    # a) Die Werkzeugtabelle kommt aus dem Server -- ein bekanntes Werkzeug
    #    muss drinstehen, sonst wurde sie nicht gelesen.
    assert "`knowledge_add`" in t, "MCP-Werkzeuge fehlen"
    assert "`lesson_record`" in t
    # b) Melder und ihre Verdrahtung.
    assert "melder/gatestand.py" in t
    assert "UserPromptSubmit" in t or "Stop" in t, "keine Verdrahtung erkannt"
    # c) NEGATIVFALL: nichts erfunden -- ein Modul, das es nicht gibt, steht
    #    auch nicht drin.
    assert "melder/gibtsnicht.py" not in t
    # d) Der Abgleich mit dem Lastenkatalog findet echte Kennungen.
    assert re.search(r"\| `BDW-[A-Z]+-?\d+` \|", t), "keine Katalogzeile erkannt"
    print("faehigkeitskarte: Selbsttest gruen (4 Faelle: Werkzeuge aus der "
          "echten Tabelle, Melder samt Verdrahtung, nichts erfunden, "
          "Katalogabgleich traegt Kennungen)")
    return 0


def _pruefen() -> int:
    neu = baue()
    try:
        alt = ZIEL.read_text(encoding="utf-8")
    except OSError:
        print(f"{ZIEL.name} fehlt -- mit --bauen erzeugen", file=sys.stderr)
        return 1
    # Die Kopfzeile traegt Zeitstempel und Commit; sie darf abweichen.
    schnitt = lambda s: "\n".join(z for z in s.splitlines()
                                  if not z.startswith("Erzeugt aus dem Quellcode"))
    if schnitt(neu) != schnitt(alt):
        print(f"{ZIEL.name} ist veraltet -- tool/faehigkeitskarte.py --bauen",
              file=sys.stderr)
        return 1
    print(f"{ZIEL.name} ist aktuell")
    return 0


if __name__ == "__main__":
    if "--selbsttest" in sys.argv or "--selftest" in sys.argv:
        sys.exit(_selbsttest())
    if "--pruefen" in sys.argv:
        sys.exit(_pruefen())
    if "--bauen" in sys.argv:
        ZIEL.parent.mkdir(parents=True, exist_ok=True)
        ZIEL.write_text(baue(), encoding="utf-8")
        print(f"{ZIEL} geschrieben ({len(baue().splitlines())} Zeilen)")
        sys.exit(0)
    print(__doc__.strip().splitlines()[0])
