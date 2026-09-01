"""Tests fuer melder/abrufwirkung.py -- Auftrag 2026-08-15 (dauerhafter
Verlauf statt einmaliger Messung, siehe runs/abrufwirkung_2026-08-15T131451+0200.json).

Deckt die drei Auflagen des Auftrags:
  1. roh vs. normiert (L-8b377b) -- test_bericht_roh_und_normiert_weichen_ab.
  2. Signal in BEIDE Richtungen, echter Bestand (L-f61f86) --
     test_positivkontrolle_und_negativkontrolle_echter_bestand.
  3. keine Selbstauskunft (L-79ec88) -- das Modul liest ausschliesslich
     Transkript und git log, nirgends wird das Modell nach einer Einschaetzung
     gefragt (strukturell durch die Funktionssignaturen erzwungen, kein
     eigener Test noetig).

Und die zwei FALLEN, je mit einem Test, der ROT ist, solange die Falle nicht
abgefangen wird -- beide gegen echte Daten dieses Repos (git log von heute
bzw. das reale Sitzungsprotokoll):
  - test_falle_zeitrichtung_ohne_filter_zaehlt_scheintreffer
  - test_falle_wortgrenzen_ohne_schutz_zaehlt_pfad_praefix_falsch
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pathlib import Path as _Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "melder"), str(ROOT / "kern")]

import abrufwirkung  # noqa: E402
import zeitmarke  # noqa: E402

JETZT = "2026-08-15T12:00:00Z"

# Das reale Sitzungsprotokoll, aus dem runs/abrufwirkung_2026-08-15T131451+0200.json
# entstand (siehe dessen Feld quelle_protokoll). Ausserhalb des Repos, nur
# gelesen (Auftragsgrenze), waechst weiter (laufende Sitzung) -- deshalb
# werden Zahlen daraus NICHT hart erwartet, sondern nur als unterer Schrank
# geprueft, und der Test wird uebersprungen, wenn die Datei fehlt (anderer
# Rechner, rotiert).
ECHTES_PROTOKOLL = Path(
    str(_Path.home() / ".claude" / "projects") + "/"
    "-Volumes-daten-Begod2026-brainlehr--claude-worktrees-baum-20260815T054407-65075/"
    "01c01c7f-2c38-4eff-96e5-2e3d8e4d9677.jsonl"
)


def _mini_transkript(tmp_path: Path, name: str, zeilen: list[dict]) -> Path:
    pfad = tmp_path / name
    with open(pfad, "w", encoding="utf-8") as f:
        for z in zeilen:
            f.write(json.dumps(z, ensure_ascii=False) + "\n")
    return pfad


# --- Grundfunktionen ---------------------------------------------------

def test_kennungen_aus_block_beide_formen():
    text = "<knowledge-recall>\n- [/tools/beispiel-pfad] ...\n(error, 1x, L-abcdef, ...)"
    assert abrufwirkung.kennungen_aus_block(text) == {
        "/tools/beispiel-pfad": "knoten",
        "L-abcdef": "lehre",
    }


def test_git_commits_reads_log_and_patch_in_one_process(monkeypatch, tmp_path):
    """Large histories must not spawn three Git processes per commit."""
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if "--patch" in command:
            return subprocess.CompletedProcess(command, 0,
                "\x1eabc\x1f2026-08-15T08:16:52+02:00\x1fsubject\n\ndiff --git a/x b/x\n", "")
        if "--format=%H" in command:
            return subprocess.CompletedProcess(command, 0, "abc\n", "")
        if "--format=%aI%x1f%B" in command:
            return subprocess.CompletedProcess(command, 0, "2026-08-15T08:16:52+02:00\x1fsubject", "")
        return subprocess.CompletedProcess(command, 0, "diff --git a/x b/x\n", "")

    monkeypatch.setattr(abrufwirkung.subprocess, "run", fake_run)
    assert abrufwirkung._git_commits(tmp_path, "2026-08-14") == [
        ("abc", "2026-08-15T06:16:52Z", "subject\n\ndiff --git a/x b/x\n")]
    assert len(calls) == 1


def test_verlauf_aktualisieren_ergaenzt_denselben_eintrag_statt_neuen():
    """Kern der Bauform (kern/baustein.py::herkunftsverlauf uebernommen):
    zwei Aufrufe fuer dieselbe Kennung duerfen NICHT zwei Eintraege ergeben."""
    bestand: dict = {}
    abrufwirkung.verlauf_aktualisieren(
        bestand, "L-x", "lehre",
        [{"ereignis": "eingespielt", "ts": "2026-08-15T10:00:00Z", "seq": 1, "quelle": "a"}])
    abrufwirkung.verlauf_aktualisieren(
        bestand, "L-x", "lehre",
        [{"ereignis": "unbeachtet", "ts": "2026-08-15T10:01:00Z", "seq": None, "quelle": "lauf"}])
    abrufwirkung.verlauf_aktualisieren(
        bestand, "L-x", "lehre",
        [{"ereignis": "eingespielt", "ts": "2026-08-15T10:02:00Z", "seq": 5, "quelle": "b"},
         {"ereignis": "benutzt", "ts": "2026-08-15T10:03:00Z", "seq": 6, "quelle": "b"}])
    assert list(bestand.keys()) == ["L-x"]
    arten = [e["ereignis"] for e in bestand["L-x"]["ereignisse"]]
    assert arten == ["eingespielt", "unbeachtet", "eingespielt", "benutzt"], arten


def test_verwendung_reiner_fliesstext_zaehlt_nicht(tmp_path):
    """Ein Assistenten-Textbaustein, der die Kennung nur ERWAEHNT (kein
    Werkzeugaufruf), darf keine Verwendung ausloesen -- L-79ec88 (keine
    Selbstauskunft): nur beobachtbare Werkzeugaufrufe zaehlen."""
    transkript = _mini_transkript(tmp_path, "t.jsonl", [
        {"attachment": {"type": "hook_additional_context",
                         "content": ["<knowledge-recall>\n(error, 1x, L-aaaaaa, ...)"]},
         "timestamp": "2026-08-15T10:00:00.000Z"},
        {"message": {"content": [{"type": "text", "text": "Ich erwaehne L-aaaaaa hier nur."}]},
         "timestamp": "2026-08-15T10:01:00.000Z"},
    ])
    gefunden = abrufwirkung.verwendungen_aus_transkript(
        transkript, {"L-aaaaaa": "lehre"}, {"L-aaaaaa": 1})
    assert gefunden == {}


# --- FALLE 1: Zeitrichtung (echte Commits von heute) --------------------

# Aus runs/abrufwirkung_2026-08-15T131451+0200.json,
# "abgelehnte_scheintreffer_falsche_zeitreihenfolge": Commit 30ed7737
# (2026-08-15T08:16:52+02:00 = 06:16:52Z) nennt L-d34412 in seiner
# Commit-Nachricht -- der Commit hat den Eintrag ERZEUGT, nicht auf eine
# Einspielung reagiert. Verifiziert unten per git show, dass beides (Hash,
# Text) auch heute noch zutrifft -- keine erfundene Fixture.
_ZEITRICHTUNG_HASH_PRAEFIX = "30ed7737"
_ZEITRICHTUNG_KENNUNG = "L-d34412"


def _hole_realen_commit(hash_praefix: str) -> tuple[str, str, str]:
    voll = subprocess.run(["git", "-C", str(ROOT), "rev-parse", hash_praefix],
                           capture_output=True, text=True, check=True).stdout.strip()
    treffer = [c for c in abrufwirkung._git_commits(ROOT, "2026-08-14 00:00") if c[0] == voll]
    assert treffer, f"Commit {hash_praefix} nicht im git log --since 2026-08-14 gefunden"
    return treffer[0]


def test_zeitrichtung_commit_traegt_die_kennung_wirklich():
    """Voraussetzung des Falle-Tests unten: der reale Commit muss die
    Kennung tatsaechlich enthalten, sonst waere der Test wirkungslos."""
    _, ts_utc, text = _hole_realen_commit(_ZEITRICHTUNG_HASH_PRAEFIX)
    assert ts_utc == "2026-08-15T06:16:52Z", ts_utc
    assert abrufwirkung.wortgrenzen_treffer(text, _ZEITRICHTUNG_KENNUNG, ist_pfad=False)


def test_falle_zeitrichtung_ohne_filter_zaehlt_scheintreffer(monkeypatch):
    """ROT VOR GRUEN: eine Fassung OHNE Zeitstempelvergleich (ts_utc <=
    grenze uebersprungen) zaehlt den realen Commit 30ed7737 mit -- die
    korrekte Fassung (git_verwendungen) NICHT, weil der Commit VOR der
    (hier gesetzten) Einspielungsgrenze liegt."""
    einziger_commit = _hole_realen_commit(_ZEITRICHTUNG_HASH_PRAEFIX)
    commit_hash, commit_ts, _ = einziger_commit
    monkeypatch.setattr(abrufwirkung, "_git_commits",
                         lambda wurzel, seit: [einziger_commit])

    grenze_nach_commit = {_ZEITRICHTUNG_KENNUNG: "2026-08-15T08:41:51Z"}  # NACH dem Commit
    korrekt = abrufwirkung.git_verwendungen(
        ROOT, {_ZEITRICHTUNG_KENNUNG: "lehre"}, grenze_nach_commit, "2026-08-14 00:00")
    assert korrekt == {}, "der Commit liegt VOR der Einspielung -- darf nicht zaehlen (ROT waere ein Treffer hier)"

    # Naive Fassung: derselbe Ablauf, aber OHNE den Zeitstempelvergleich
    # (Falle rekonstruiert) -- muss den Scheintreffer liefern, sonst waere
    # der obige Test nicht aussagekraeftig (er koennte auch aus einem
    # anderen Grund leer sein, z.B. Wortgrenzen).
    def _naiv_ohne_zeitfilter(wurzel, gesuchte, grenze_ts, seit):
        commits = abrufwirkung._git_commits(wurzel, seit)
        gefunden = {}
        for kennung, art in gesuchte.items():
            for h, ts_utc, text in commits:
                if abrufwirkung.wortgrenzen_treffer(text, kennung, art == "knoten"):
                    gefunden[kennung] = {"ts": ts_utc, "quelle": f"git:{h[:8]}"}
                    break
        return gefunden

    naiv = _naiv_ohne_zeitfilter(ROOT, {_ZEITRICHTUNG_KENNUNG: "lehre"}, grenze_nach_commit, "2026-08-14 00:00")
    assert naiv == {_ZEITRICHTUNG_KENNUNG: {"ts": commit_ts, "quelle": f"git:{commit_hash[:8]}"}}, (
        "die naive Fassung (Falle) MUSS den Scheintreffer liefern -- sonst belegt "
        "der Test oben nichts")


# --- FALLE 2: Wortgrenzen (echte Fundstuecke aus git log -p heute) ------

# Aus `git log --since '2026-08-15 00:00' -p -- .` in diesem Repo: '/brainlehr'
# ist Praefix von laengeren Pfaden -- kein Zitat der Kennung, nur ihr
# Ablageort. Woertlich uebernommen, nicht erfunden.
_ECHTE_FUNDSTUECKE_PRAEFIX = [
    "+ neuer Knoten unter /brainlehr/betreiberentscheidung-adr-020 angelegt",
    "Sicherung liegt jetzt unter /brainlehr-ausweise/2026-08-15/",
]


def test_falle_wortgrenzen_ohne_schutz_zaehlt_pfad_praefix_falsch():
    """ROT VOR GRUEN: ein naiver Substring-Test ('/brainlehr' in text) zaehlt
    beide echten Fundstuecke als Treffer -- wortgrenzen_treffer (die
    tatsaechlich verwendete Pruefung) verwirft beide."""
    for text in _ECHTE_FUNDSTUECKE_PRAEFIX:
        assert "/brainlehr" in text, text  # Voraussetzung: naiver Test waere rot (Falle vorhanden)
        assert abrufwirkung.wortgrenzen_treffer(text, "/brainlehr", ist_pfad=True) is False, text

    # Gegenprobe (L-f61f86, Signal in beide Richtungen): eine ECHTE, klar
    # abgegrenzte Nennung muss weiterhin treffen.
    klarer_treffer = "Astknoten liegt direkt unter /brainlehr, sonst nirgends"
    assert abrufwirkung.wortgrenzen_treffer(klarer_treffer, "/brainlehr", ist_pfad=True) is True


# --- Positiv-/Negativkontrolle am echten Bestand (Auflage 2, L-f61f86) --

pytestmark_echt = pytest.mark.skipif(
    not ECHTES_PROTOKOLL.exists(),
    reason="reales Sitzungsprotokoll nicht auf diesem Rechner vorhanden")


@pytest.mark.skipif(not ECHTES_PROTOKOLL.exists(), reason="reales Sitzungsprotokoll fehlt")
def test_positivkontrolle_und_negativkontrolle_echter_bestand(tmp_path):
    """L-c9f9e9 MUSS als benutzt gefunden werden (woertlich in einen
    Agentenauftrag uebernommen, siehe runs/abrufwirkung_2026-08-15T131451+0200.json
    'positivkontrolle'). L-d07097 MUSS als Spaetwirkung erkannt werden
    (zweimal eingespielt, wirkungslos, erst beim dritten Antreffen benutzt).
    Negativkontrolle (L-f61f86, Signal in beide Richtungen): eine frei
    erfundene Kennung, die nirgends im Protokoll vorkommt, darf NICHT als
    benutzt gelten."""
    bericht = abrufwirkung.lauf(ECHTES_PROTOKOLL, ROOT, JETZT,
                                 verlauf_pfad=tmp_path / "verlauf.json",
                                 git_seit="2026-08-15 00:00")

    assert "L-c9f9e9" in bericht["benutzt_kennungen"], bericht["benutzt_kennungen"]
    assert "L-d07097" in bericht["spaetwirkung_kennungen"], bericht["spaetwirkung_kennungen"]

    frei_erfunden = {"L-000000": "lehre"}
    negativ = abrufwirkung.verwendungen_aus_transkript(ECHTES_PROTOKOLL, frei_erfunden, {"L-000000": 0})
    assert negativ == {}, "eine nirgends vorkommende Kennung darf nie als benutzt gelten"

    # Lauf gegen die heutige Sitzung (Abnahme: 334/37 aus der einmaligen
    # Messung). WEICHT AB, ERKLAERT statt kalibriert: das Protokoll ist eine
    # LAUFENDE Sitzung, die seit der Messung (13:14:51+0200) weitergewachsen
    # ist -- mehr Zeilen, mehr echte Agentenauftraege, mehr Einspielungen.
    # Ausserdem deckt dieses Modul bewusst NICHT den in der Messung
    # zusaetzlich gezeigten 'schritt_4' (Gegenrichtung: neu geschriebenes
    # Wissen) ab -- das war nicht Teil des Auftrags. Die Zahlen hier sind
    # deshalb ein UNTERER Schrank (mindestens so viele wie damals bekannt),
    # keine exakte Reproduktion.
    assert bericht["kennungen_gesamt"] >= 334, bericht["kennungen_gesamt"]
    assert bericht["anzahl_benutzt"] >= 37, bericht["anzahl_benutzt"]


# --- Bericht: roh vs. normiert weichen tatsaechlich ab (Auflage 1) -----

def test_bericht_roh_und_normiert_weichen_ab_bei_schiefer_verteilung(tmp_path):
    """L-8b377b: eine schief verteilte Einspielhaeufigkeit darf die
    normierte Quote NICHT verzerren -- roh und normiert muessen dann
    auseinanderfallen. Fixture: eine Kennung 10x eingespielt und 1x benutzt,
    drei andere je 1x eingespielt und nie benutzt."""
    zeilen = []
    ts = "2026-08-15T10:00:00.000Z"
    for i in range(10):
        zeilen.append({"attachment": {"type": "hook_additional_context",
                                       "content": ["<knowledge-recall>\n(error, 1x, L-cafe01, ...)"]},
                        "timestamp": ts})
    for k in ("L-facade", "L-decade", "L-beaded"):
        zeilen.append({"attachment": {"type": "hook_additional_context",
                                       "content": [f"<knowledge-recall>\n(error, 1x, {k}, ...)"]},
                        "timestamp": ts})
    zeilen.append({"message": {"content": [{"type": "tool_use", "name": "Agent",
                                             "input": {"prompt": "nutze L-cafe01 jetzt"}}]},
                   "timestamp": "2026-08-15T10:05:00.000Z"})
    transkript = _mini_transkript(tmp_path, "schief.jsonl", zeilen)

    bericht = abrufwirkung.lauf(transkript, ROOT, JETZT, verlauf_pfad=tmp_path / "verlauf.json")
    assert bericht["kennungen_gesamt"] == 4, bericht
    assert bericht["einspielungen_roh"] == 13, bericht
    assert bericht["anzahl_benutzt"] == 1, bericht
    # normiert: 1 von 4 Kennungen -> 25%. roh: 10 von 13 Einspielungen -> 76,9%.
    assert bericht["quote_normiert_prozent"] == 25.0, bericht
    assert bericht["quote_roh_prozent"] == pytest.approx(76.9, abs=0.1), bericht
    assert bericht["quote_roh_prozent"] > bericht["quote_normiert_prozent"], (
        "roh ueberschaetzt hier per Konstruktion -- sonst waere die Auflage nicht erfuellt")
    assert bericht["top3_anteil_prozent"] > 50, (
        "Verteilungs-Gegenprobe: die drei haeufigsten Kennungen dominieren die "
        "Einspielungen in dieser Fixture, wie in L-8b377b beschrieben")
