"""Die Wache gegen lautlos alternde Derivate -- und ihre gemessenen Grenzen.

Anlass: Eilmeldung 2dd8a01d (2026-08-19, aus buckeberg). Ein Handout, dessen
Zitat STIMMTE und das trotzdem irrefuehrte: 26 Tage alt ohne es zu zeigen,
eine bestrittene Zeile ohne Vermerk, und die wichtigere Klausel verschwiegen.

DER TEST, auf den es ankommt, ist der NEGATIVFALL. Der erste Anlauf nahm
jeden Dateinamen im Text als Quelle und meldete 635 Befunde in buckeberg --
fast alle unsinnig, weil eine Erwaehnung keine Berufung ist. Eine Wache mit
dieser Fehlalarmquote wird binnen einer Woche ignoriert. Nach der
Einschraenkung auf Linkziele und Dokumente mit erklaertem Stand: 15.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "melder"))

import derivatfrische as df  # noqa: E402


def _repo(tmp_path: Path, dateien: dict[str, str], wann: str = "2026-07-23T00:55:46+02:00") -> Path:
    """Der Commit-Zeitpunkt wird GESETZT, nicht dem Zufall des Testlaufs
    ueberlassen.

    Sonst liegt die Quelle im Pruefstand immer in der Gegenwart und ist damit
    zwangslaeufig juenger als jeder erklaerte Stand -- die Frischeprobe
    schluege in jedem Test an, und der Pruefstand haette eine Eigenschaft
    gemessen, die nur er hat. Der Vorgabewert ist der echte: `swb.pdf` wurde
    zuletzt am 2026-07-23 committet.
    """
    umgebung = {**os.environ, "GIT_AUTHOR_DATE": wann, "GIT_COMMITTER_DATE": wann}
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    for name, inhalt in dateien.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(inhalt, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "erst"], cwd=tmp_path, env=umgebung, check=True)
    return tmp_path


DERIVAT = (
    "# Handout\n\n"
    "**Stand:** 2026-07-24T05:54:16+0200\n\n"
    "Der Preis steht im Vertrag. "
    "[Quelle: Vertragsentwurf](https://x/viewer.html?file=%2Fquellen%2Fswb.pdf#page=2)\n"
)


def test_ein_ueberholtes_derivat_wird_gemeldet(tmp_path):
    # Genau der Anlassfall: 26 Tage alt am Tag des Vorfalls.
    w = _repo(tmp_path, {"handout.md": DERIVAT, "quellen/swb.pdf": "x"})
    e = df.pruefe(w, frist_tage=21, jetzt="2026-08-19T08:00:00+02:00")
    assert [v["derivat"] for v in e["veraltet"]] == ["handout.md"], e
    assert e["veraltet"][0]["tage"] == 26


def test_dasselbe_derivat_ist_kurz_nach_dem_stand_kein_befund(tmp_path):
    # Gegenprobe in die andere Richtung: ohne sie belegt der Test oben nur,
    # dass die Wache ueberhaupt etwas meldet, nicht dass sie unterscheidet.
    w = _repo(tmp_path, {"handout.md": DERIVAT, "quellen/swb.pdf": "x"})
    e = df.pruefe(w, frist_tage=21, jetzt="2026-07-30T08:00:00+02:00")
    assert e["veraltet"] == []


def test_grenzwert_genau_auf_der_frist_meldet_nicht(tmp_path):
    w = _repo(tmp_path, {"handout.md": DERIVAT, "quellen/swb.pdf": "x"})
    e = df.pruefe(w, frist_tage=21, jetzt="2026-08-14T05:54:16+02:00")
    assert e["veraltet"] == [], "21 Tage sind die Frist, nicht ihre Ueberschreitung"
    e2 = df.pruefe(w, frist_tage=21, jetzt="2026-08-15T05:54:17+02:00")
    assert e2["veraltet"], "22 Tage muessen melden"


def test_eine_blosse_erwaehnung_ist_keine_berufung():
    # DER Fall, der 635 Fehlalarme erzeugt hat.
    assert df._genannte_dateien("der Stand steht in STAND.md, siehe daten/kosten.json") == set()


def test_ein_linkziel_ist_eine_berufung_auch_prozentkodiert():
    text = "[Q](https://x/viewer.html?file=%2Fquellen%2Fswb.pdf#page=2)"
    assert df._genannte_dateien(text) == {"swb.pdf"}


def test_ohne_erklaerten_stand_wird_nichts_gemeldet(tmp_path):
    # Eine Momentaufnahme (Plan, Uebergabe) DARF aelter sein als das, was
    # danach kam -- sie behauptet keine Aktualitaet.
    ohne = DERIVAT.replace("**Stand:** 2026-07-24T05:54:16+0200\n\n", "")
    w = _repo(tmp_path, {"plan.md": ohne, "quellen/swb.pdf": "x"})
    e = df.pruefe(w, frist_tage=1, jetzt="2027-01-01T00:00:00+01:00")
    assert e["veraltet"] == [] and e["befunde"] == []


def test_die_frischeprobe_faengt_den_anlassfall_NICHT(tmp_path):
    """Festgehalten, nicht behoben -- und deshalb ein Test.

    Die Eilmeldung schlug als Bauform (a) einen Frischevergleich vor. Am
    echten Fall gemessen greift er nicht: `swb.pdf` wurde zuletzt am
    2026-07-23 geaendert, das Handout trug Stand 2026-07-24 -- das Derivat
    war JUENGER als seine Quelle und trotzdem 26 Tage ueberholt. Ein
    Vertragstext aendert sich nicht; was altert, ist das Verstaendnis davon.
    """
    w = _repo(tmp_path, {"handout.md": DERIVAT, "quellen/swb.pdf": "x"})
    e = df.pruefe(w, frist_tage=21, jetzt="2026-08-19T08:00:00+02:00")
    assert e["befunde"] == [], "die Quelle ist unveraendert, die Frischeprobe schweigt zu Recht"
    assert e["veraltet"], "gefangen wird der Fall allein ueber das ALTER"


def test_die_frischeprobe_schlaegt_an_wenn_die_quelle_nachtraeglich_kam(tmp_path):
    # Positivkontrolle: ohne sie belegt der Test darueber nur, dass die
    # Frischeprobe schweigt -- nicht, dass sie ueberhaupt funktioniert.
    w = _repo(tmp_path, {"handout.md": DERIVAT, "quellen/swb.pdf": "x"},
              wann="2026-08-01T12:00:00+02:00")
    e = df.pruefe(w, frist_tage=21, jetzt="2026-08-05T08:00:00+02:00")
    assert [b["quelle"] for b in e["befunde"]] == ["quellen/swb.pdf"], e
    assert e["veraltet"] == [], "12 Tage alt -- das Alter allein meldet hier nichts"


def test_zeitzonen_werden_umgerechnet():
    # 08:00+0200 ist 06:00Z und damit FRUEHER als 07:00Z.
    assert df._juenger("2026-08-19T07:00:00+00:00", "2026-08-19T08:00:00+0200")
    assert not df._juenger("2026-08-19T05:00:00+00:00", "2026-08-19T08:00:00+0200")


def test_selftest_laeuft_durch():
    assert df._selftest() == 0
