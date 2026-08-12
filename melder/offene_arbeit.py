#!/usr/bin/env python3
"""Zeigt beim Sitzungsstart, was offen ist -- aus der Datei, nicht aus dem Kopf.

Anlass 2026-08-12T05:50:00+0200: Der Betreiber fragte, wie viele Sprints offen
sind. Die Frage war aus den Unterlagen nicht zu beantworten -- 21 Abschnitte
ohne Statusfeld. Danach entstand docs/SPRINTS.md, und dann fragte er das
Zweite: sehen die anderen Arbeitsbaeume das auch?

Nein, taten sie nicht. Die Liste lag im Sitzungsspeicher (Aufgabenwerkzeug)
und in einem Wecker, der mit der Sitzung stirbt. Beides ist von der Sorte, die
in dieser Nacht dreimal beanstandet wurde: gebaut und ohne Wirkung.

Darum liest dieser Melder die DATEI. Eine Datei liegt im Verzeichnis, ist
committet, ueberlebt jede Sitzung und ist in jedem Arbeitsbaum dieselbe.

Er ist bewusst projektunabhaengig: er sucht docs/SPRINTS.md relativ zur
Repo-Wurzel des aktuellen Verzeichnisses. Wo es die Datei nicht gibt, schweigt
er -- der vierzehnte Startmelder, der immer redet, waere einer zu viel.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

OFFEN = {"offen", "teilweise", "wartet auf betreiber"}
MAX_ZEILEN = 6


def _wurzel() -> Path | None:
    try:
        aus = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return Path(aus.stdout.strip()) if aus.returncode == 0 and aus.stdout.strip() else None


def zeilen(datei: Path) -> list[tuple[str, str, str]]:
    """(Kennung, Status, Titel) je Sprintzeile der Tabelle."""
    treffer = []
    for zeile in datei.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*(S\d+[a-d]?)\s*\|([^|]*)\|([^|]*)\|", zeile)
        if m:
            treffer.append((m.group(1).strip(), m.group(3).strip().lower(),
                            m.group(2).strip()))
    return treffer


def melde(wurzel: Path | None = None) -> str:
    wurzel = wurzel or _wurzel()
    if wurzel is None:
        return ""
    datei = wurzel / "docs" / "SPRINTS.md"
    if not datei.exists():
        return ""                      # kein Register -- nichts zu sagen
    alle = zeilen(datei)
    if not alle:
        return ""
    offen = [(k, s, t) for k, s, t in alle if s in OFFEN]
    if not offen:
        return f"Alle {len(alle)} Sprints erledigt laut {datei.name}."
    kopf = (f"{len(offen)} von {len(alle)} Sprints offen "
            f"({datei.relative_to(wurzel)}, Status steht dort mit Beleg):")
    zeig = [f"  {k} [{s}] {t[:70]}" for k, s, t in offen[:MAX_ZEILEN]]
    if len(offen) > MAX_ZEILEN:
        zeig.append(f"  ... und {len(offen) - MAX_ZEILEN} weitere")
    return "\n".join([kopf, *zeig])


def _selftest() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        w = Path(d)
        (w / "docs").mkdir()
        (w / "docs" / "SPRINTS.md").write_text(
            "| Sprint | Titel | Status | Beleg |\n"
            "|---|---|---|---|\n"
            "| S1 | Erstes | erledigt | commit abc |\n"
            "| S2 | Zweites | offen | -- |\n"
            "| S3 | Drittes | teilweise | halb |\n", encoding="utf-8")
        aus = melde(w)
        assert "2 von 3" in aus, aus
        assert "S2" in aus and "S3" in aus and "S1" not in aus, aus

        # Negativfall: ohne Register schweigt er, statt etwas zu erfinden.
        leer = Path(d) / "leer"
        leer.mkdir()
        assert melde(leer) == "", melde(leer)

        # Grenzfall: alles erledigt -- eine andere Aussage, kein Schweigen.
        (w / "docs" / "SPRINTS.md").write_text(
            "| Sprint | Titel | Status | Beleg |\n"
            "|---|---|---|---|\n"
            "| S1 | Erstes | erledigt | commit abc |\n", encoding="utf-8")
        assert "Alle 1" in melde(w), melde(w)
    print("offene_arbeit: Selbsttest gruen")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        text = melde()
        if text:
            print(text)
