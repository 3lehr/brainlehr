#!/usr/bin/env python3
"""Meldet zwei Fehlklassen in den Claude-Code-Fertigkeiten unter
~/.claude/skills/*/SKILL.md: Subagenten, die eine Fertigkeit anbietet, die es
nicht gibt -- und Rollennamen aus einem fremden Haus (ChatGPT/Codex), die dort
nicht gelten.

ANLASS, gemessen 2026-08-18: ~/.claude/skills/cavecrew/SKILL.md verspricht
drei Subagenten (cavecrew-investigator, cavecrew-builder, cavecrew-reviewer).
Vorhanden ist unter ~/.claude/agents/ nur compliance.md; ein Aufruf scheitert
mit "Agent type 'cavecrew-investigator' not found". Dieselbe Datei nannte bis
zu einer Korrektur am selben Tag ausserdem Terra/Luna/Sol -- Rollen aus
~/.codex/AGENTS.md, nicht aus diesem System. Jede Sitzung, die die Fertigkeit
laedt, zahlt Token und faellt auf falsche Namen herein.

TEIL 1 -- ERFUNDENE AGENTEN. Erkennungsmuster (zwei, beide auf backtick-
quotierte Einzeltoken beschraenkt -- ein Name mit Leerzeichen wie
"Code Reviewer" faellt durch das Zeichenmuster [A-Za-z][\\w:-]* und wird nicht
erfasst; das ist Absicht, siehe unten):

  (a) LETZTE TABELLENZELLE: eine Markdown-Tabellenzeile, deren letzte Spalte
      einen backtick-Namen enthaelt -- das Muster, in dem cavecrew seine
      Entscheidungstabelle "Task | Use" fuehrt. `\\|[^|\\n]*`NAME`[^|\\n]*\\|\\s*$`
  (b) VERBKONTEXT: ein backtick-Name innerhalb von 40 Zeichen NACH einem der
      Verben spawn / delegate to / route to. Bewusst eng gehalten (NICHT
      "use", NICHT "invoke", NICHT "hand to"): eine erste Fassung mit "use"
      erzeugte einen Fehlalarm auf "use `nit:` instead" in
      caveman-review/SKILL.md -- ein Bezeichner-Etikett, kein Agentenname.

  PREIS BEIDER MUSTER (was sie NICHT finden): ein Agentenname in reinem
  Fliesstext ohne backticks ("ruf den Investigator-Agenten auf") · ein Name in
  YAML/JSON (`subagent_type: "x"`) ausserhalb von SKILL.md-Markdown · ein Name,
  der ueber mehrere Zeilen oder in einem Codeblock mit dreifachen backticks
  steht · ein plugin-qualifizierter Name wie `feature-dev:code-architect`, der
  vielleicht ueber ein installiertes Plugin real existiert -- dieser Melder
  kennt nur ~/.claude/agents/*.md plus die eingebauten Namen und meldet einen
  solchen Namen deshalb IMMER als ungeklaert, auch wenn ein Plugin ihn loest.

TEIL 2 -- FREMDE ROLLEN. Terra/Luna/Sol/Hermes als eigenes Wort (Wortgrenze
\\b...\\b) in SKILL.md-Dateien und in ~/.claude/CLAUDE.md. Wortgrenzen
verhindern, dass "Solidaritaet" oder "Lunartage" treffen.

HINWEISRECHT, KEIN VETO (Vorbild melder/ausloeserlos.py): dieses Skript endet
im normalen Betrieb IMMER mit Code 0. Nur die Betriebsart --streng (fuer einen
pre-push-Hook) liefert bei Funden Code 1.

Aufruf:
    python3 fremdrollen.py --bericht     # alle Funde (Vorgabe)
    python3 fremdrollen.py --melder      # nur sprechen, wenn etwas anschlaegt
    python3 fremdrollen.py --streng      # wie --bericht, aber exit 1 bei Funden
    python3 fremdrollen.py --selftest
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# eingebaute Namen dieses Systems -- werden nie als "erfunden" gemeldet.
BUILTIN_AGENTEN = frozenset({
    "general-purpose", "Explore", "Plan", "statusline-setup",
    "claude", "claude-code-guide",
})

FREMDE_ROLLEN = ("Terra", "Luna", "Sol", "Hermes")

_TABELLENZELLE = re.compile(r"\|[^|\n]*`([A-Za-z][\w:-]*)`[^|\n]*\|\s*$", re.M)
_VERBKONTEXT = re.compile(
    r"\b(?:spawn|delegate\s+to|route\s+to)\b[^`\n]{0,40}`([A-Za-z][\w:-]*)`",
    re.I,
)

_FRONTMATTER_NAME = re.compile(r"(?m)^name:\s*(\S+)\s*$")


def vorhandene_agenten(agenten_ordner: Path) -> set[str]:
    """Namen aus dem `name:`-Frontmatter jeder ~/.claude/agents/*.md, plus
    die eingebauten Konstanten."""
    namen = set(BUILTIN_AGENTEN)
    if agenten_ordner.is_dir():
        for md in agenten_ordner.glob("*.md"):
            try:
                text = md.read_text(errors="replace")
            except OSError:
                continue
            m = _FRONTMATTER_NAME.search(text)
            if m:
                namen.add(m.group(1))
    return namen


def angebotene_agenten(skill_text: str) -> set[str]:
    """Namen, die eine SKILL.md als Subagent anbietet -- Vereinigung der
    beiden Muster (a) und (b), siehe Docstring."""
    treffer = set(_TABELLENZELLE.findall(skill_text))
    treffer |= set(_VERBKONTEXT.findall(skill_text))
    return treffer


def _wortgrenze(rolle: str) -> re.Pattern:
    return re.compile(rf"\b{re.escape(rolle)}\b")


def fremde_rollen_in(text: str) -> set[str]:
    return {r for r in FREMDE_ROLLEN if _wortgrenze(r).search(text)}


def skill_dateien(claude_ordner: Path) -> list[Path]:
    muster = claude_ordner / "skills"
    if not muster.is_dir():
        return []
    return sorted(muster.glob("*/SKILL.md"))


def bericht(claude_ordner: Path) -> dict:
    """claude_ordner ist typischerweise ~/.claude -- als Parameter, damit
    der Selbsttest gegen ein tmp-Verzeichnis laufen kann, nie gegen den
    echten Bestand."""
    agenten = vorhandene_agenten(claude_ordner / "agents")
    erfunden: list[dict] = []
    rollen: list[dict] = []

    for skill in skill_dateien(claude_ordner):
        try:
            text = skill.read_text(errors="replace")
        except OSError:
            continue
        rel = str(skill)
        for name in sorted(angebotene_agenten(text) - agenten):
            erfunden.append({"datei": rel, "name": name})
        for rolle in sorted(fremde_rollen_in(text)):
            rollen.append({"datei": rel, "rolle": rolle})

    claude_md = claude_ordner / "CLAUDE.md"
    if claude_md.is_file():
        try:
            text = claude_md.read_text(errors="replace")
        except OSError:
            text = ""
        for rolle in sorted(fremde_rollen_in(text)):
            rollen.append({"datei": str(claude_md), "rolle": rolle})

    return {"erfunden": erfunden, "rollen": rollen}


def render(funde: dict) -> str:
    erfunden, rollen = funde["erfunden"], funde["rollen"]
    if not erfunden and not rollen:
        return "fremdrollen: keine Funde -- keine erfundenen Agenten, keine fremden Rollennamen."
    zeilen = []
    if erfunden:
        zeilen.append(f"fremdrollen: {len(erfunden)} angebotene(r) Agent(en) ohne Entsprechung:")
        for f in erfunden:
            zeilen.append(f"  - {f['datei']}: `{f['name']}`")
    if rollen:
        zeilen.append(f"fremdrollen: {len(rollen)} Vorkommen fremder Rollennamen (Terra/Luna/Sol/Hermes):")
        for r in rollen:
            zeilen.append(f"  - {r['datei']}: {r['rolle']}")
    zeilen.append("Hinweisrecht, kein Veto: hier nicht entschieden, ob korrigiert oder verworfen wird.")
    return "\n".join(zeilen)


def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "skills" / "sauber").mkdir(parents=True)
        (root / "skills" / "erfunden").mkdir(parents=True)
        (root / "skills" / "fremd").mkdir(parents=True)
        (root / "agents").mkdir(parents=True)

        (root / "agents" / "compliance.md").write_text(
            "---\nname: compliance\ndescription: x\n---\ntut etwas.\n"
        )

        # sauber: nutzt nur einen echten (Datei-)Agenten und einen eingebauten.
        (root / "skills" / "sauber" / "SKILL.md").write_text(
            "---\nname: sauber\ndescription: x\n---\n"
            "| Task | Use |\n|---|---|\n"
            "| lookup | `compliance` |\n"
            "| explore | `Explore` |\n"
            "Kein fremdes Wort, auch nicht 'Solidaritaet' oder 'Lunartage'.\n"
        )

        # erfunden: bietet zwei Namen ohne Agenten-Datei an -- einen ueber die
        # Tabellenzelle, einen ueber "spawn `name`".
        (root / "skills" / "erfunden" / "SKILL.md").write_text(
            "---\nname: erfunden\ndescription: x\n---\n"
            "| Task | Use |\n|---|---|\n"
            "| locate | `cavecrew-investigator` |\n"
            "Tells the thread WHEN to spawn `cavecrew-builder` for edits.\n"
            "use `nit:` instead of a suggestion.\n"
        )

        # fremd: nennt Luna als eigenes Wort.
        (root / "skills" / "fremd" / "SKILL.md").write_text(
            "---\nname: fremd\ndescription: x\n---\n"
            "Global model roles: Terra orchestrates, Luna executes.\n"
        )

        (root / "CLAUDE.md").write_text("Kein Codex-Rollenname hier.\n")

        funde = bericht(root)
        erfunden_namen = {f["name"] for f in funde["erfunden"]}
        rollen_namen = {r["rolle"] for r in funde["rollen"]}

        assert "compliance" not in erfunden_namen, "existierender Agent darf nicht gemeldet werden"
        assert "Explore" not in erfunden_namen, "eingebauter Name darf nicht gemeldet werden"
        print("  (a) vorhandene/eingebaute Agenten -> kein Fund: ok")

        assert "cavecrew-investigator" in erfunden_namen
        assert "cavecrew-builder" in erfunden_namen
        print("  (b) erfundene Agenten aus Tabellenzelle UND Verbkontext gefunden: ok")

        assert "nit" not in erfunden_namen, \
            "'use `nit:`' ist kein Agentenangebot -- 'use' allein darf nicht treffen"
        print("  (c) Fehlalarm 'use `nit:`' bleibt aus (nur spawn/delegate to/route to zaehlen): ok")

        assert "Luna" in rollen_namen and "Terra" in rollen_namen
        print("  (d) fremde Rollen Terra/Luna gefunden: ok")

        # Grenzfall Wortgrenze: 'Solidaritaet'/'Lunartage' duerfen nicht treffen.
        grenzfall = fremde_rollen_in("Wir bauen Solidaritaet fuer Lunartage.")
        assert grenzfall == set(), f"Wortgrenze verletzt: {grenzfall}"
        print("  (e) Wortgrenze -- 'Solidaritaet'/'Lunartage' loesen NICHT aus: ok")

        text = render(funde)
        assert "Hinweisrecht, kein Veto" in text
        assert "`compliance`" not in text and "`Explore`" not in text
        print("  render() zeigt Funde mit Hinweisrecht-Satz: ok")

        leer = render({"erfunden": [], "rollen": []})
        assert "keine Funde" in leer
        print("  render() ohne Funde: eindeutiger Text: ok")

    print("selftest ok (5 Faelle, je mit Gegenprobe)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bericht", action="store_true", help="alle Funde, ausfuehrlich")
    p.add_argument("--melder", action="store_true", help="nur sprechen, wenn etwas anschlaegt")
    p.add_argument("--streng", action="store_true", help="exit 1 bei Funden (fuer pre-push)")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return

    claude_ordner = Path.home() / ".claude"
    funde = bericht(claude_ordner)
    hat_funde = bool(funde["erfunden"] or funde["rollen"])

    if a.melder and not a.streng:
        if hat_funde:
            print(render(funde))
        return

    if not a.melder or a.bericht or a.streng:
        print(render(funde))

    if a.streng and hat_funde:
        sys.exit(1)


if __name__ == "__main__":
    main()
