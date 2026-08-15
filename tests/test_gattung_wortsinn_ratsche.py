"""Ratsche: `gattung` traegt zwei Bedeutungen, nur eine darf im Wort `gattung` bleiben.

BEFUND (2026-08-15, Betreiberentscheidung Knoten `00e74420`): `gattung` bezeichnete
bisher zwei verschiedene Dinge -- den Wissensknoten-Typ (`knowledge_nodes.gattung`,
Werte `arbeitsbestand`/`nachschlagewerk`, per Trigger erzwungen, ueber 2200 Knoten
haengen daran) UND die Dokumentart (Rechnung, Brief, Korrekturblatt ... ADR-015).
Letztere hatte im Code null Zeilen (`kern/dokument.py` kennt kein Gattungsfeld) und
wurde deshalb umbenannt in `Dokumentart`. Die Wissensknoten-Bedeutung bleibt
unangetastet -- sie steckt in Schema, Triggern und Bestand und wird hier NICHT
geprueft.

ROT VOR GRUEN, nachgewiesen ueber `git show HEAD:<datei>` statt ueber Ruecknahme
der Aenderung (kein `git stash` verwendet): der Stand vor dieser Aenderung trug
in ADR-015 fuenf, in ADR-019 vier Vorkommen von `gattung` in der Dokument-
Bedeutung -- dieser Test waere gegen jenen Stand rot gewesen.

GEGENPROBE in beide Richtungen: ADR-015/ADR-019 duerfen das Wort `gattung` gar
nicht mehr enthalten (Dokument-Bedeutung, umbenannt). Eine Wissensknoten-Datei
(PLAN_KLIENTENDOKU) MUSS es weiterhin enthalten -- sonst waere die Ratsche blind
und wuerde beim naechsten Schreiber den ganzen Bestand lahmlegen.
"""
from __future__ import annotations

import re
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent

DOCS = _w / "docs"
_GATTUNG = re.compile(r"gattung", re.IGNORECASE)

# Dateien, in denen `gattung` ausschliesslich die DOKUMENTART meinte und deshalb
# vollstaendig auf `Dokumentart` umgestellt wurde. Kein Vorkommen darf hier
# zurueckkehren.
DOKUMENT_BEDEUTUNG_DATEIEN = (
    DOCS / "adr" / "ADR-015-designvorrat-als-daten-und-der-editor-kann-nur-was-der-satz-kann.md",
    DOCS / "adr" / "ADR-019-drei-entscheidungen-vor-dem-ersten-dokument.md",
)

# Datei, in der `gattung` den WISSENSKNOTEN-Typ meint (schema.sql, ueber 2200
# Knoten). Muss unangetastet bleiben -- Positivkontrolle gegen eine blinde Regel.
WISSENSKNOTEN_BEDEUTUNG_DATEI = DOCS / "PLAN_KLIENTENDOKU_2026-08-10.md"


def test_dokumentart_dateien_frei_von_gattung() -> None:
    for pfad in DOKUMENT_BEDEUTUNG_DATEIEN:
        assert pfad.exists(), f"Datei fehlt: {pfad}"
        treffer = _GATTUNG.findall(pfad.read_text(encoding="utf-8"))
        assert not treffer, (
            f"{pfad.name} traegt noch {len(treffer)}x 'gattung' in der "
            "Dokumentbedeutung -- sollte 'Dokumentart' heissen"
        )


def test_wissensknoten_bedeutung_bleibt_unangetastet() -> None:
    """Gegenprobe: die andere Bedeutung von `gattung` darf NICHT verschwinden."""
    text = WISSENSKNOTEN_BEDEUTUNG_DATEI.read_text(encoding="utf-8")
    treffer = _GATTUNG.findall(text)
    assert len(treffer) >= 10, (
        f"{WISSENSKNOTEN_BEDEUTUNG_DATEI.name} sollte die Wissensknoten-Bedeutung "
        f"von 'gattung' mehrfach tragen, fand nur {len(treffer)} -- Ratsche waere "
        "blind fuer den falschen Fall"
    )


if __name__ == "__main__":
    test_dokumentart_dateien_frei_von_gattung()
    test_wissensknoten_bedeutung_bleibt_unangetastet()
    print("gruen: Dokumentart-Umbenennung haelt, Wissensknoten-Bedeutung unberuehrt")
