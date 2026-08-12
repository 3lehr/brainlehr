"""Die Zahl der Dateien mit eigener DB-Verbindung darf nur SINKEN.

ANLASS: Am 2026-08-11 hielt eine einzige Verbindung stundenlang die
Schreibsperre, und der Umzugspreis auf eine andere Datenbank steht in
derselben Zahl -- 100 Produktivdateien oeffnen ihre Verbindung selbst, keine
Stelle kapselt den Zugriff. speicher.py ist die Naht; diese Ratsche haelt sie.

WARUM RATSCHE UND NICHT VERBOT: Ein Verbot haette die 100 Bestandsdateien
sofort rot gemacht und waere binnen eines Tages abgeschaltet worden -- die
Fehlerklasse "blockierende Wache, die eine unerfuellbare Regel durchsetzt"
ist hier schon gemessen worden. Die Ratsche laesst den Bestand in Ruhe und
verhindert nur das Wachsen. Wer eine Datei umstellt, senkt die Zahl; wer eine
neue Tuer aufmacht, faellt auf.

WAS SIE NICHT KANN: Sie zaehlt DATEIEN, nicht Aufrufe. Eine Datei, die von
drei auf eine Verbindung geht, bewegt die Zahl nicht. Und sie sieht nur
`sqlite3.connect` -- wer die Verbindung anders beschafft, kommt vorbei.
Beides bewusst: die Zahl soll die Naht messen, nicht die Sorgfalt.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
BASIS = WURZEL / "tests" / "naht_basis.json"


def dateien_mit_eigener_verbindung() -> dict[str, list[str]]:
    """Produktivdateien (ohne Tests, ohne fremde Arbeitsbaeume), die selbst
    eine SQLite-Verbindung oeffnen. Migrationsskripte getrennt gefuehrt: sie
    laufen einmal und wandern bei einem Umzug nicht mit."""
    roh = subprocess.run(
        ["grep", "-rn", "sqlite3.connect", "--include=*.py", "."],
        cwd=WURZEL, capture_output=True, text=True,
    ).stdout.splitlines()
    # ':memory:' zaehlt nicht: das ist eine Testkulisse, keine Tuer zum
    # Bestand. Ohne diese Unterscheidung bliebe eine Datei in der Liste
    # stehen, die laengst umgestellt ist -- und die Ratsche wuerde eine
    # erledigte Umstellung als offen fuehren.
    # Kommentarzeilen zaehlen nicht. Eine Datei, die erklaert, warum hier
    # frueher eine eigene Verbindung stand, nennt die verbotene Zeichenfolge
    # zwangslaeufig -- und wuerde sich damit selbst anzeigen. Genau das ist am
    # 2026-08-12 zweimal passiert: erst zwischen den beiden Namenswachen
    # (tests/test_testumgebung_nutzt_ort.py, dort schon behoben), dann hier
    # bei messungen/kalibrierbremse_wirkung.py. Kommentierter Code wird nie
    # ausgefuehrt und oeffnet keine Verbindung.
    def _ist_kommentar(zeile: str) -> bool:
        teile = zeile.split(":", 2)
        return len(teile) == 3 and teile[2].lstrip().startswith("#")

    treffer = sorted({
        zeile.split(":", 1)[0] for zeile in roh
        if ":memory:" not in zeile
        and "/worktrees/" not in zeile and "/tests/" not in zeile
        and not _ist_kommentar(zeile)
        and Path(zeile.split(":", 1)[0]).name != "speicher.py"
    })
    return {
        "dauerhaft": sorted(f for f in treffer if "migrat" not in f),
        "migrationen": sorted(f for f in treffer if "migrat" in f),
    }


def test_naht_waechst_nicht():
    ist = dateien_mit_eigener_verbindung()
    basis = json.loads(BASIS.read_text(encoding="utf-8"))

    neu = sorted(set(ist["dauerhaft"]) - set(basis["dauerhaft"]))
    assert not neu, (
        "Neue Datei(en) mit eigener DB-Verbindung: " + ", ".join(neu) +
        " -- stattdessen speicher.lesen() / speicher.schreiben() verwenden. "
        "Ist die eigene Verbindung hier wirklich noetig, gehoert sie mit "
        "Begruendung in tests/naht_basis.json."
    )


def test_basis_bleibt_ehrlich():
    """Gegenprobe: Dateien, die inzwischen umgestellt wurden, muessen aus der
    Basis verschwinden -- sonst waechst der Spielraum still mit jeder
    Umstellung, und die Ratsche haelt nichts mehr fest."""
    ist = dateien_mit_eigener_verbindung()
    basis = json.loads(BASIS.read_text(encoding="utf-8"))

    erledigt = sorted(set(basis["dauerhaft"]) - set(ist["dauerhaft"]))
    assert not erledigt, (
        "Diese Dateien stehen noch in der Basis, oeffnen aber keine eigene "
        "Verbindung mehr: " + ", ".join(erledigt) +
        " -- aus tests/naht_basis.json streichen, damit die Ratsche greift."
    )
