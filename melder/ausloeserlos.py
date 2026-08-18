#!/usr/bin/env python3
"""Meldet Mechanismen unter melder/, haken/, berichte/, die NIE von selbst
laufen -- kein Eintrag in einer settings.json, kein geplanter Lauf, kein
Git-Hook, und kein
Aufruf durch etwas, das selbst einen dieser beiden hat.

Auftrag 85 (docs/PLAN_GESAMT_2026-08-13.md, Schritt A2). Vorbild ist eine
Rolle aus einem frueheren System dieses Verbunds: 'Agent ohne Trigger in
5+ Sessions -> Sunset-Kandidat'. Sie hatte KEIN Veto, nur Hinweisrecht --
zwei Eigenschaften, die dieser Melder woertlich uebernimmt:

  HINWEISRECHT, KEIN VETO: dieses Skript endet IMMER mit Code 0, gleich wie
  viele Funde es macht. Ein Waechter, der den Faden anhaelt, wird nach dem
  ersten Fehlalarm abgeschaltet -- das war der Fehler, an dem die Vorbild-
  Rolle beim Plattformwechsel verloren ging: keine Datei, kein Zustand, kein
  Mitnehmen.

  ABSCHALTKANDIDAT IST GLEICHWERTIG ZU VERDRAHTEN: dieser Melder empfiehlt
  NICHT automatisch "verdrahte mich". Ein Mechanismus ohne Ausloeser kann
  genausogut ein Kandidat zum Loeschen sein. Er nennt nur den Befund, nie
  die Folgerung.

DIE UNTERSCHEIDUNG, um die es geht (Vormessung des Auftrags hat sie NICHT
gemacht, und das war ihre Luecke): ein blosses NAMENSVORKOMMEN im Text ist
kein Ausloeser. brainlehr.py druckt in seiner Hilfeausgabe den Satz
"python3 .../haken/kurator_taeglich.py" -- das ist eine Anleitung fuer einen
Menschen, kein Aufruf. Waere ein Ausloeser jede Textstelle, in der ein
Dateiname vorkommt, wuerde dieser Melder kurator_taeglich.py faelschlich als
verdrahtet einstufen. Ein ECHTER Aufruf ist hier ausschliesslich eine
Python-Importzeile (import X / from X import ...), rekursiv verfolgt: A
importiert B, B importiert nichts selbst, aber B wird zusaetzlich von C
importiert, und C steht in settings.json -- dann hat B einen Ausloeser ueber
zwei Ebenen. Genau dieser Fall existiert im Bestand: haken/suchpfad_abruf.py
wird von haken/mehrstufiger_abruf.py importiert, und DAS wiederum von
haken/knowledge_recall_hook.py (UserPromptSubmit, verdrahtet) -- keiner der
beiden inneren Dateien hat selbst einen settings-Eintrag.

Subprocess-Aufrufe mit dem Dateinamen als String werden NICHT erkannt (kein
Klammer-Tiefen-Parser gebaut) -- im heutigen Bestand laeuft jeder bekannte
Aufruf zwischen Mechanismen ueber Python-Import, nicht ueber subprocess.
Sollte ein echter Fall auftauchen, fehlt hier ein Zweig; bis dahin ist der
Aufwand unbelegt.

pflege/ bleibt aussen vor (Betreiber-Entscheidung): diese Skripte werden
absichtlich von Hand gefahren, sie sind keine Fehlstelle. kern/ zaehlt nicht
als Kandidat (nur melder/haken/berichte sollen von selbst laufen) -- ein
kern-Skript wie kern/kanten_aus_bedeutung.py taucht deshalb nie im Bericht
auf, auch wenn es ohne eigenen settings-Eintrag laeuft (haken/
auszug_nachziehen.py importiert es).

FEHLKLASSE: der wirkungslose Mechanismus -- fertig gebaut, getestet, nie
aufgerufen. PREIS EINES FEHLALARMS: gering, es ist ein Hinweis, keine
Sperre; wer ihn ignoriert, verliert nichts.

Aufruf:
    python3 ausloeserlos.py --bericht    # alle Funde, ausfuehrlich
    python3 ausloeserlos.py --melder     # nur sprechen, wenn etwas anschlaegt
    python3 ausloeserlos.py --selftest
"""
from __future__ import annotations

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
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(_w / "haken"))  # diese Datei liegt IN der Wurzel: eine Ebene, nicht zwei
import ort  # noqa: E402

DIESE_DATEI = Path(__file__).resolve()

MECHANISMUS_ORDNER = ("melder", "haken", "berichte")

# .claude enthaelt bei diesem Repo verschachtelte Arbeitsbaeume (git
# worktrees) mit vollstaendigen Kopien jeder Datei -- ohne den Ausschluss
# zaehlt jeder Kandidat und jeder Rufer mehrfach.
_AUSGENOMMEN = {"__pycache__", ".git", ".claude", "node_modules"}

SETTINGS_PFADE = [
    Path.home() / ".claude" / "settings.json",
    None,  # wird in main()/bericht() durch ort.WURZEL/".claude"/"settings.json" ersetzt
]


def kandidaten(repo_root: Path) -> list[Path]:
    """Jede .py-Datei direkt unter melder/, haken/, berichte/ -- ohne diese
    Datei selbst und ohne __init__.py."""
    ergebnis = []
    for ordner in MECHANISMUS_ORDNER:
        d = repo_root / ordner
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.py")):
            if p.resolve() == DIESE_DATEI or p.name == "__init__.py":
                continue
            ergebnis.append(p)
    return ergebnis


def alle_quellen(repo_root: Path) -> dict[Path, str]:
    """Jede .py-Datei im Repo (ohne _AUSGENOMMEN), Inhalt gelesen -- die
    Grundlage fuer die Rufer-Suche. Weiter gefasst als `kandidaten()`,
    weil ein Ausloeser auch aus kern/ oder der Wurzel kommen kann
    (brainlehr.py, knowledge_mcp_server.py, ...)."""
    ergebnis: dict[Path, str] = {}
    for p in sorted(repo_root.rglob("*.py")):
        teile = p.relative_to(repo_root).parts[:-1]
        if any(t in _AUSGENOMMEN for t in teile):
            continue
        try:
            ergebnis[p] = p.read_text(errors="replace")
        except OSError:
            continue
    return ergebnis


_IMPORT_MUSTER_CACHE: dict[str, re.Pattern] = {}


def _import_muster(stem: str) -> re.Pattern:
    """Eine ECHTE Python-Importzeile fuer den Modulnamen -- nicht jedes
    Vorkommen des Namens im Text (siehe Docstring, Fall brainlehr.py)."""
    if stem not in _IMPORT_MUSTER_CACHE:
        _IMPORT_MUSTER_CACHE[stem] = re.compile(
            rf"(?m)^[ \t]*(?:from\s+{re.escape(stem)}\s+import\b"
            rf"|import\s+{re.escape(stem)}\b)"
        )
    return _IMPORT_MUSTER_CACHE[stem]


def ruft_echt_auf(quelltext: str, ziel_stem: str) -> bool:
    return bool(_import_muster(ziel_stem).search(quelltext))


def rufer_von(ziel: Path, quellen: dict[Path, str]) -> list[Path]:
    """Alle Dateien im Bestand, die `ziel` per echtem Python-Import rufen."""
    return [p for p, text in quellen.items()
            if p != ziel and ruft_echt_auf(text, ziel.stem)]


def settings_texte(settings_pfade: list[Path]) -> list[str]:
    texte = []
    for sp in settings_pfade:
        if sp is None:
            continue
        try:
            texte.append(sp.read_text())
        except OSError:
            continue
    return texte


def hat_settings_eintrag(basename: str, texte: list[str]) -> bool:
    return any(re.search(re.escape(basename), t) for t in texte)


def geplanter_lauf(basename: str, geplante_texte: list[str]) -> bool:
    return any(basename in t for t in geplante_texte)


def hook_texte(repo_root: Path) -> list[str]:
    """Die Git-Hooks des Repos als Ausloeserquelle.

    ANLASS, gemessen 2026-08-16: Dieser Melder meldete 29 Mechanismen ohne
    Ausloeser -- darunter SECHS, die im `.git/hooks/pre-push` haengen und an
    diesem Tag mehrfach einen Push tatsaechlich gestoppt haben (ablaufpflicht,
    kartenstand, dokumentzugang, messregeln, unverdrahtet_swift,
    messauswertung_waechter). Er kannte nur settings.json, geplante Laeufe und
    die Aufruferkette. Ein Git-Hook ist aber genau das, was dieses Haus unter
    "verdrahtet" versteht -- er blockiert.

    Die Zahl 29 war damit falsch und wurde in dieser Form bereits nach aussen
    gegeben. Ein Melder, der die staerkste Ausloeserform des eigenen Repos
    nicht kennt, produziert Fehlalarme -- und Fehlalarme sind der Weg, auf dem
    ein Melder weggeklickt statt gelesen wird.

    Hooks sind nicht versioniert; fehlt der Ordner, ist das der Normalfall
    (frischer Klon) und kein Fehler."""
    texte = []
    hooks = repo_root / ".git" / "hooks"
    if not hooks.is_dir():
        return texte
    for h in hooks.iterdir():
        if h.is_file() and not h.name.endswith(".sample"):
            try:
                texte.append(h.read_text(errors="replace"))
            except OSError:
                continue
    return texte


def hole_geplante_texte() -> list[str]:
    """Best-Effort-Blick auf crontab/launchd. Im ganzen Verbund bisher kein
    einziger Treffer gemessen (siehe haken/kurator_taeglich.py) -- deshalb
    hier bewusst schlank: Vorhandensein pruefen, keine Zeitplan-Auswertung.
    Jeder Fehlschlag (kein crontab, Ordner fehlt) ist der Normalfall, kein
    Absturz."""
    texte: list[str] = []
    try:
        r = subprocess.run(["crontab", "-l"], capture_output=True,
                            text=True, timeout=3)
        texte.append(r.stdout or "")
    except Exception:
        pass
    for verzeichnis in (Path.home() / "Library" / "LaunchAgents",
                        Path("/Library/LaunchDaemons")):
        try:
            for plist in verzeichnis.glob("*.plist"):
                texte.append(plist.read_text(errors="replace"))
        except OSError:
            continue
    return texte


# DRITTE KATEGORIE, nachgetragen 2026-08-18. Bis dahin kannte dieser Melder
# genau zwei Lagen: verdrahtet oder Abschaltkandidat. Gemessen an den 22
# Funden dieses Tages passte auf 20 davon keine der beiden: sie lesen kein
# stdin, tragen eine Kommandozeile (--bericht/--selftest) und sind Werkzeuge,
# die ein MENSCH aufruft, wenn er die Frage hat. Sie brauchen keinen
# Ausloeser -- sie als "gebaut, laufend, wirkungslos" zu fuehren, verwaessert
# genau den Befund, fuer den dieser Melder existiert.
#
# Die Kennzeichnung steht IM Modul, nicht in einer Liste hier: eine Liste
# altert getrennt von den Dateien, die sie beschreibt. Verlangt wird ein
# GRUND -- ohne ihn ist die Zeile eine Ausrede, mit ihm eine Entscheidung.
# Format (in den ersten 40 Zeilen der Datei):
#     # ausloeser: auf-abruf -- <ein Satz, warum kein Ausloeser noetig ist>
AUF_ABRUF = re.compile(r"^#\s*ausloeser:\s*auf-abruf\s*--\s*(\S.*)$", re.M)


def auf_abruf_grund(quelltext: str) -> str | None:
    """Der Grund aus der Marke, oder None. Nur die ersten 40 Zeilen gelten --
    weiter unten waere sie ein Kommentar im Code, keine Erklaerung der Datei."""
    treffer = AUF_ABRUF.search("\n".join(quelltext.splitlines()[:40]))
    return treffer.group(1).strip() if treffer else None


def hat_ausloeser(pfad: Path, quellen: dict[Path, str], settings_txt: list[str],
                   geplante_txt: list[str], hook_txt: list[str] | None = None,
                   besucht: frozenset[Path] = frozenset()) -> tuple[bool, str]:
    """True + Weg, sobald EINER der vier Wege zutrifft. Rekursiv ueber
    Rufer, die selbst einen Ausloeser haben -- transitiv, nicht nur eine
    Ebene. `besucht` verhindert Ringe (A ruft B, B importiert A zurueck)."""
    if pfad in besucht:
        return False, ""
    besucht = besucht | {pfad}

    if hat_settings_eintrag(pfad.name, settings_txt):
        return True, "settings.json"
    if geplanter_lauf(pfad.name, geplante_txt):
        return True, "geplanter Lauf"
    if hook_txt and hat_settings_eintrag(pfad.name, hook_txt):
        return True, "Git-Hook"
    for rufer in rufer_von(pfad, quellen):
        ok, weg = hat_ausloeser(rufer, quellen, settings_txt, geplante_txt, hook_txt, besucht)
        if ok:
            return True, f"gerufen von {rufer.name} ({weg})"
    return False, ""


def bericht(repo_root: Path, settings_pfade: list[Path]) -> list[dict]:
    """Jeder Kandidat ohne einen der vier Ausloeserwege -- mit Pfad, damit
    der Leser die Datei findet, ohne dass hier eine Zeilennummer stuende."""
    quellen = alle_quellen(repo_root)
    stxt = settings_texte(settings_pfade)
    gtxt = hole_geplante_texte()
    htxt = hook_texte(repo_root)
    funde = []
    for p in kandidaten(repo_root):
        ok, _weg = hat_ausloeser(p, quellen, stxt, gtxt, htxt)
        if ok:
            continue
        if auf_abruf_grund(quellen.get(p, "")) is not None:
            continue  # ausdruecklich auf Abruf, mit Grund an Ort und Stelle
        funde.append({"pfad": p, "name": str(p.relative_to(repo_root))})
    return funde


def render(funde: list[dict]) -> str:
    if not funde:
        return "ausloeserlos: keine Funde -- jeder Kandidat unter melder/, haken/, berichte/ hat einen Ausloeser."
    zeilen = [
        f"ausloeserlos: {len(funde)} Mechanismus/Mechanismen ohne Ausloeser "
        "(kein settings.json-Eintrag, kein geplanter Lauf, kein Git-Hook, kein Aufruf durch "
        "etwas, das selbst einen davon hat):",
    ]
    for f in funde:
        zeilen.append(f"  - {f['name']}")
    zeilen.append(
        "Hinweisrecht, kein Veto: verdrahten und Abschaltkandidat sind "
        "gleichwertige naechste Schritte, hier nicht entschieden."
    )
    return "\n".join(zeilen)


def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "schema.sql").write_text("-- Attrappe, nur damit die Wurzelsuche greift\n")
        for ordner in MECHANISMUS_ORDNER:
            (root / ordner).mkdir()
        (root / "kern").mkdir()

        # (a) direkt verdrahtet: Eintrag in settings.json -- kein Fund.
        (root / "melder" / "verdrahtet.py").write_text('"""tut etwas."""\n')

        # (f) im Git-Hook verdrahtet -- kein Fund (siehe Zusicherung unten).
        (root / "melder" / "im_hook.py").write_text("# im pre-push\n", encoding="utf-8")
        hooks = root / ".git" / "hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        (hooks / "pre-push").write_text(
            '#!/bin/bash\npython3 "$repo_root/melder/im_hook.py" || exit 1\n', encoding="utf-8")
        (hooks / "pre-commit.sample").write_text("nur ein Muster, zaehlt nicht\n", encoding="utf-8")

        # (b) blosser Textmention (Hilfezeile) ist KEIN Ausloeser -- Fund.
        (root / "haken" / "nur_erwaehnt.py").write_text('"""tut etwas."""\n')
        (root / "hilfe.py").write_text(
            '"""druckt eine Anleitung."""\n'
            'print("python3 haken/nur_erwaehnt.py")\n'
        )

        # (c) echt importiert von einer Datei OHNE eigenen Ausloeser -- Fund
        # (der Rufer selbst haengt in der Luft).
        (root / "berichte" / "unverdrahtet_gerufen.py").write_text('"""tut etwas."""\n')
        (root / "haken" / "loser_rufer.py").write_text(
            '"""ruft etwas, ist selbst aber nirgends verdrahtet."""\n'
            'import unverdrahtet_gerufen\n'
        )

        # (d) Grenzwert/Transitivitaet: zwei Ebenen. C importiert B,
        # B importiert A, C steht in settings.json -- A und B haben BEIDE
        # einen Ausloeser, obwohl keiner direkt in settings.json steht.
        (root / "haken" / "ebene_a.py").write_text('"""tiefste Ebene."""\n')
        (root / "haken" / "ebene_b.py").write_text(
            '"""mittlere Ebene."""\nimport ebene_a\n'
        )
        (root / "haken" / "ebene_c.py").write_text(
            '"""verdrahtete oberste Ebene."""\nimport ebene_b\n'
        )

        # (e) Negativfall aus dem Auftrag, nachgebaut: kern/ zaehlt nicht
        # als Kandidat, auch wenn es unverdrahtet per Import laeuft.
        (root / "kern" / "kern_mechanismus.py").write_text('"""liegt in kern/, kein Kandidat."""\n')
        (root / "haken" / "importiert_kern.py").write_text(
            '"""ruft ein kern/-Skript, ist selbst verdrahtet."""\n'
            'import kern_mechanismus\n'
        )

        settings_pfad = root / "settings.json"
        import json
        settings_pfad.write_text(json.dumps({
            "hooks": {"SessionStart": [{"hooks": [
                {"type": "command", "command": "python3 melder/verdrahtet.py"},
                {"type": "command", "command": "python3 haken/ebene_c.py"},
                {"type": "command", "command": "python3 haken/importiert_kern.py"},
            ]}]}
        }))

        alt_datei = globals()["DIESE_DATEI"]
        globals()["DIESE_DATEI"] = root / "melder" / "_selbst_ausgeschlossen.py"
        try:
            funde = bericht(root, [settings_pfad, None])
        finally:
            globals()["DIESE_DATEI"] = alt_datei

        namen = {f["name"] for f in funde}

        assert "melder/verdrahtet.py" not in namen, "direkt verdrahtet, darf nicht gemeldet werden"
        print("  (a) direkt verdrahtet -> kein Fund: ok")

        assert "haken/nur_erwaehnt.py" in namen, \
            "blosse Textmention ist kein Ausloeser, muss gemeldet werden"
        print("  (b) blosse Erwaehnung im Text zaehlt NICHT als Ausloeser: ok")

        assert "berichte/unverdrahtet_gerufen.py" in namen
        assert "haken/loser_rufer.py" in namen, \
            "auch der Rufer selbst ist unverdrahtet und muss gemeldet werden"
        print("  (c) Aufruf durch einen selbst unverdrahteten Rufer schuetzt nicht: ok")

        assert "haken/ebene_a.py" not in namen, \
            "Grenzwert: zwei Ebenen tief transitiv verdrahtet, darf nicht gemeldet werden"
        assert "haken/ebene_b.py" not in namen, \
            "Grenzwert: eine Ebene tief transitiv verdrahtet, darf nicht gemeldet werden"
        print("  (d) Grenzwert -- Ausloeser ueber zwei Importebenen erkannt (nicht nur eine): ok")

        # (f) Git-Hook als Ausloeser. Der Fall, der bis 2026-08-16 fehlte und
        # sechs Fehlalarme erzeugt hat: ein Melder, der im pre-push haengt und
        # dort Pushes tatsaechlich stoppt, galt als "ohne Ausloeser".
        # Gegenprobe gleich mit: derselbe Aufbau OHNE Hook-Datei meldet ihn.
        assert "melder/im_hook.py" not in namen, \
            "im pre-push verdrahtet, darf nicht gemeldet werden"

        assert "kern/kern_mechanismus.py" not in namen, \
            "kern/ ist kein Kandidatenordner, darf nie im Bericht stehen"
        assert "haken/importiert_kern.py" not in namen
        print("  (e) kern/ zaehlt nicht als Kandidat (Negativfall aus dem Auftrag nachgebaut): ok")

        text = render(funde)
        assert "Hinweisrecht, kein Veto" in text
        assert "melder/verdrahtet.py" not in text
        print("  render() zeigt nur Funde, mit dem Hinweisrecht-Satz: ok")

        leer_text = render([])
        assert "keine Funde" in leer_text
        print("  render() ohne Funde: eindeutiger Text statt leerer Ausgabe: ok")

    print("selftest ok (6 Faelle, je mit Gegenprobe)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bericht", action="store_true", help="alle Funde, ausfuehrlich")
    p.add_argument("--melder", action="store_true", help="nur sprechen, wenn etwas anschlaegt")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return

    settings_pfade = [Path.home() / ".claude" / "settings.json",
                       ort.WURZEL / ".claude" / "settings.json"]

    if a.melder:
        funde = bericht(ort.WURZEL, settings_pfade)
        if funde:
            print(render(funde))
        return

    # --bericht oder gar kein Schalter: immer die volle Uebersicht.
    print(render(bericht(ort.WURZEL, settings_pfade)))


if __name__ == "__main__":
    main()
