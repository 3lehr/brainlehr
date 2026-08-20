""".claude/launch.json darf keinen Skriptpfad nennen, den es nicht gibt.

ANLASS, gemessen 2026-08-12: der Eintrag 'entscheidungen' startete
<ablage>/<arbeitsbereich>/brainlehr/entscheidungen_server.py -- diese Datei
existiert nicht, der Server liegt unter berichte/entscheidungen_server.py.
Ein Start ueber .claude/launch.json waere sofort und laut mit
'python3: can't open file ... No such file or directory' gescheitert -- aber
nur, wenn ihn je jemand von Hand ausprobiert. Ohne Probe faellt das nicht auf.

Geprueft wird der erste .py-Pfad in jeder runtimeArgs-Liste (das aufzurufende
Skript selbst; --port & Co. sind keine Pfade). Kein Python-Import, keine
Ausfuehrung -- reiner Dateisystem-Check, damit der Test nichts startet.
"""
from __future__ import annotations

import json
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
LAUNCH_JSON = WURZEL / ".claude" / "launch.json"


def skriptpfade() -> list[tuple[str, str]]:
    """[(konfigurationsname, skriptpfad), ...] -- ein Paar je Eintrag mit
    einem .py-Pfad in runtimeArgs. Eintraege ohne .py-Argument (z. B. reine
    URL-Konfigurationen) liefern kein Paar."""
    daten = json.loads(LAUNCH_JSON.read_text(encoding="utf-8"))
    paare = []
    for konf in daten.get("configurations", []):
        for arg in konf.get("runtimeArgs", []):
            if arg.endswith(".py"):
                paare.append((konf.get("name", "?"), arg))
                break
    return paare


def pruefe() -> tuple[int, int, list[str]]:
    """(Eintraege gesamt, davon mit .py-Pfad geprueft, beanstandete Pfade)."""
    daten = json.loads(LAUNCH_JSON.read_text(encoding="utf-8"))
    gesamt = len(daten.get("configurations", []))
    paare = skriptpfade()
    beanstandet = [f"{name}: {pfad}" for name, pfad in paare if not Path(pfad).exists()]
    return gesamt, len(paare), beanstandet


def test_jeder_launch_pfad_existiert():
    gesamt, geprueft, beanstandet = pruefe()
    assert not beanstandet, (
        f"{gesamt} Eintraege, {geprueft} mit Skriptpfad geprueft, "
        f"{len(beanstandet)} beanstandet: " + "; ".join(beanstandet)
    )


def pruefe_repo_zugehoerigkeit() -> tuple[int, int, list[str]]:
    """(Eintraege gesamt, davon mit .py-Pfad geprueft, beanstandete Pfade
    ausserhalb dieses Repos). Ein Skript aus einem fremden Repo (z. B. hub/)
    ist ein Befund: genau so ist eine zweite, unbemerkt tote Oberflaeche
    entstanden (wissensgraph -> hub/tools/knowledge-viz/server.py,
    2026-08-12)."""
    daten = json.loads(LAUNCH_JSON.read_text(encoding="utf-8"))
    gesamt = len(daten.get("configurations", []))
    paare = skriptpfade()
    beanstandet = [
        f"{name}: {pfad}" for name, pfad in paare
        if not Path(pfad).resolve().is_relative_to(WURZEL)
    ]
    return gesamt, len(paare), beanstandet


def test_jeder_launch_pfad_liegt_im_repo():
    gesamt, geprueft, beanstandet = pruefe_repo_zugehoerigkeit()
    assert not beanstandet, (
        f"{gesamt} Eintraege, {geprueft} mit Skriptpfad geprueft, "
        f"{len(beanstandet)} beanstandet (ausserhalb des Repos): "
        + "; ".join(beanstandet)
    )


def test_selftest_erkennt_einen_fehlenden_pfad(tmp_path):
    """Gegenprobe zur Probe selbst: ein falscher Pfad muss auffallen. Ohne
    diesen Fall koennte pruefe() durch einen leeren skriptpfade()-Rueckgabewert
    immer gruen sein, ohne je etwas zu pruefen."""
    kaputt = tmp_path / "launch.json"
    kaputt.write_text(json.dumps({
        "configurations": [
            {"name": "x", "runtimeArgs": [str(tmp_path / "gibt_es_nicht.py"), "--port", "1"]},
        ]
    }), encoding="utf-8")
    daten = json.loads(kaputt.read_text(encoding="utf-8"))
    paare = [(k.get("name"), a) for k in daten["configurations"]
             for a in k.get("runtimeArgs", []) if a.endswith(".py")]
    beanstandet = [f"{n}: {p}" for n, p in paare if not Path(p).exists()]
    assert beanstandet == ["x: " + str(tmp_path / "gibt_es_nicht.py")]


def test_selftest_erkennt_einen_repo_fremden_pfad(tmp_path):
    """Gegenprobe: ein existierender, aber repo-fremder Pfad muss auffallen --
    genau das war der wissensgraph-Eintrag (hub/tools/knowledge-viz/server.py)."""
    fremd = tmp_path / "fremd.py"
    fremd.write_text("", encoding="utf-8")
    daten = {"configurations": [
        {"name": "x", "runtimeArgs": [str(fremd), "--port", "1"]},
    ]}
    paare = [(k.get("name"), a) for k in daten["configurations"]
             for a in k.get("runtimeArgs", []) if a.endswith(".py")]
    beanstandet = [f"{n}: {p}" for n, p in paare
                   if not Path(p).resolve().is_relative_to(WURZEL)]
    assert beanstandet == ["x: " + str(fremd)]


if __name__ == "__main__":
    gesamt, geprueft, beanstandet = pruefe()
    print(f"{gesamt} Eintraege, {geprueft} mit Skriptpfad geprueft, "
          f"{len(beanstandet)} beanstandet.")
    for b in beanstandet:
        print(f"  FEHLT: {b}")
