"""ADR-016 Auflage 1/2, Schritt 2 von PLAN_I3_TABELLE_2026-08-15.md.

Rot vor gruen: vor diesem Auftrag gab es keinen Mechanismus, der Univers
mitgelieferte Verbotsliste (ALL_IMPLEMENTED_FUNCTIONS, wird per .concat()
angehaengt, nie ersetzt) auf eine Positivliste zurechtstutzt. Ohne
spikes/univer_i3_min/probe4/entry_positivliste.js gab es keine Abmeldeschleife
und =WEBSERVICE(...) waere so ausfuehrbar gewesen, wie jede andere Formel.

WARUM DIESE TESTS EINEN ECHTEN BROWSER STARTEN, statt die Positivliste nur
als Python-Menge zu vergleichen: der Praefstand-Befund vom 2026-08-15 (siehe
~/.claude/CLAUDE.md, "Der Pruefstand misst mit") gilt hier direkt -- ein Mock
der Univer-Formel-Engine wuerde genau das Feld (functionService) fest
verdrahten, dessen Verhalten die eigentliche Frage ist. Gemessen wird darum
die TATSAECHLICH VERFUEGBARE Funktionsmenge im laufenden Bundle (per
functionService.hasExecutor je mitgelieferter Funktion), nicht eine Kopie der
erlaubten Liste. Kommt in einer kuenftigen Univer-Fassung eine Funktion dazu,
faellt sie bei "sind die verbotenen weg" nicht auf, bei "ist verfuegbar ==
erlaubt" schon (siehe Kommentar in entry_positivliste.js).

Sieht der Code anders aus als hier beschrieben, halte dich an den Code und
melde die Abweichung.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

SPIKE = Path(__file__).resolve().parent.parent / "spikes" / "univer_i3_min"
PROBE4 = SPIKE / "probe4"
POSITIVLISTE = PROBE4 / "positivliste.mjs"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

pytestmark = pytest.mark.skipif(
    not (SPIKE / "node_modules" / ".bin" / "esbuild").exists() or not Path(CHROME).exists(),
    reason="Spike-Abhaengigkeiten (esbuild in spikes/univer_i3_min/node_modules oder "
    "Google Chrome) fehlen auf diesem Rechner -- nicht mit dem Spike-Ergebnis verwechseln, "
    "das ist ein uebersprungener Test, kein bestandener.",
)


@contextmanager
def _erlaubte_liste(funktionen: list[str]):
    """Tauscht ALLOWED_FUNCTIONS in positivliste.mjs fuer die Dauer des
    Blocks aus -- fuer die Grenzwert- und Mutationsproben. Sicherung per
    Kopie, nicht per git stash (Hausregel), Rueckbau im finally auch bei
    einem fehlschlagenden Test."""
    original = POSITIVLISTE.read_text(encoding="utf-8")
    liste_js = ", ".join(json.dumps(f) for f in funktionen)
    ersetzt = original.replace(
        original[original.index("export const ALLOWED_FUNCTIONS = ["):original.rindex("];") + 2],
        f"export const ALLOWED_FUNCTIONS = [{liste_js}];",
    )
    POSITIVLISTE.write_text(ersetzt, encoding="utf-8")
    try:
        yield
    finally:
        POSITIVLISTE.write_text(original, encoding="utf-8")


def _baue_bundle() -> None:
    subprocess.run(
        [
            str(SPIKE / "node_modules" / ".bin" / "esbuild"),
            "probe4/entry_positivliste.js",
            "--bundle",
            "--outfile=probe4/bundle.js",
            "--format=esm",
            "--loader:.css=css",
        ],
        cwd=SPIKE,
        check=True,
        capture_output=True,
        timeout=30,
    )


def _fuehre_probe_aus() -> dict:
    """Baut das Bundle aus dem aktuellen Stand von entry_positivliste.js +
    positivliste.mjs, startet die Probe unter der Netzwerk-Sandbox (nur
    localhost, ADR-016 Frage 1) in einem echten, headless Chrome, und liefert
    das gemeldete Ergebnis-JSON zurueck. Raeumt Server- und Browserprozess in
    jedem Fall wieder auf (finally), sonst sammeln sich ueber mehrere
    Testlaeufe verwaiste Chrome-Kindprozesse an (ADR-016: "Chrome beendet
    sich unter dieser Sandbox nicht sauber")."""
    _baue_bundle()
    ergebnis_pfad = PROBE4 / "ergebnis.json"
    ergebnis_pfad.unlink(missing_ok=True)

    server = subprocess.Popen(
        ["node", "probe4/serve_and_log.mjs"],
        cwd=SPIKE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    time.sleep(0.5)

    udd = tempfile.mkdtemp(prefix="probe4_udd_")
    chrome = None
    try:
        chrome = subprocess.Popen(
            [
                "sandbox-exec", "-f", "no-network.sb",
                CHROME,
                "--headless=new", "--disable-gpu", "--no-sandbox",
                f"--user-data-dir={udd}",
                "--virtual-time-budget=15000",
                "http://127.0.0.1:8934/index.html",
            ],
            cwd=SPIKE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        frist = time.time() + 20
        while time.time() < frist:
            if ergebnis_pfad.exists() and ergebnis_pfad.stat().st_size > 0:
                break
            time.sleep(0.5)
        else:
            pytest.fail("Probe4 hat innerhalb von 20s kein Ergebnis gemeldet.")
    finally:
        for proc in (chrome, server):
            if proc is None:
                continue
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
        # Chrome faechert unter der Sandbox in weitere Prozesse auf, die nicht
        # in derselben Prozessgruppe haengen (Updater, GPU-Helper) -- gezielt
        # ueber den eindeutigen --user-data-dir-Pfad treffen, NIE per
        # "Google Chrome" pauschal (koennte die echte Sitzung des Betreibers
        # treffen).
        subprocess.run(["pkill", "-f", udd], capture_output=True)
        shutil.rmtree(udd, ignore_errors=True)

    daten = json.loads(ergebnis_pfad.read_text(encoding="utf-8"))
    assert "fehler" not in daten, f"Probe4 meldete einen Laufzeitfehler: {daten.get('fehler')}"
    return daten


# --- Grundzustand: die produktive Positivliste aus positivliste.mjs -------

def test_verfuegbare_menge_ist_gleich_der_erlaubten_menge():
    """Der eigentliche Beleg aus dem Auftrag: NICHT 'die verbotenen sind
    weg', sondern verfuegbar == erlaubt, als Mengen."""
    d = _fuehre_probe_aus()
    assert set(d["verfuegbar"]) == set(d["erlaubt"])
    assert d["verfuegbar_anzahl"] == d["erlaubt_anzahl"]
    assert d["erlaubt_anzahl"] + d["abgemeldet_anzahl"] == d["mitgeliefert_anzahl"]
    # Zahl mit Nenner, wie in der Abnahme verlangt.
    assert d["mitgeliefert_anzahl"] > d["erlaubt_anzahl"] > 0


def test_erlaubte_formel_ueber_benannten_bereich_rechnet_richtig():
    d = _fuehre_probe_aus()
    assert d["c1_summe_ueber_benannten_bereich"] == 350


def test_negativfall_webservice_ergibt_name_fehler():
    d = _fuehre_probe_aus()
    assert d["c2_webservice"] == "#NAME?"


def test_grenzwert_unbekannte_funktion_ergibt_name_fehler():
    d = _fuehre_probe_aus()
    assert d["c3_unbekannte_funktion"] == "#NAME?"


def test_negativfall_abgemeldete_echte_funktion_wird_wirklich_blockiert():
    """Der schaerfere Beleg als der WEBSERVICE-Fall: CONCATENATE ist eine
    ECHTE, mitgelieferte Univer-Funktion (nicht wie WEBSERVICE ohnehin ohne
    Executor) -- sie steht nicht auf der Positivliste und muss trotzdem
    #NAME? ergeben, nicht 'ab'."""
    d = _fuehre_probe_aus()
    assert d["c4_abgemeldete_echte_funktion_concatenate"] == "#NAME?"


# --- Grenzwerte an der Positivliste selbst ---------------------------------

def test_grenzwert_leere_erlaubte_liste():
    with _erlaubte_liste([]):
        d = _fuehre_probe_aus()
    assert d["erlaubt_anzahl"] == 0
    assert d["verfuegbar_anzahl"] == 0
    assert d["abgemeldet_anzahl"] == d["mitgeliefert_anzahl"]


def test_grenzwert_erlaubte_funktion_die_es_nicht_gibt():
    with _erlaubte_liste(["SUM", "DIESEFUNKTIONGIBTESNICHT"]):
        d = _fuehre_probe_aus()
    # Die erfundene Funktion steht auf der erlaubten Liste, kann aber nie
    # verfuegbar werden -- verfuegbar und erlaubt duerfen sich hier NICHT
    # decken. Genau dieses Auseinanderfallen ist der gewuenschte Fehlerfall.
    assert "DIESEFUNKTIONGIBTESNICHT" in d["erlaubt"]
    assert "DIESEFUNKTIONGIBTESNICHT" not in d["verfuegbar"]
    assert d["erlaubt_anzahl"] != d["verfuegbar_anzahl"]
    assert d["c1_summe_ueber_benannten_bereich"] == 350  # SUM bleibt unberuehrt


def test_grenzwert_doppelter_eintrag_wird_dedupliziert():
    with _erlaubte_liste(["SUM", "SUM", "IF"]):
        d = _fuehre_probe_aus()
    assert d["erlaubt_anzahl"] == 2
    assert set(d["verfuegbar"]) == {"SUM", "IF"}


# --- Mutationsproben (ADR-034-Stil: Anmeldung/Abmeldung kaputt machen -----
# muss rot werden). Beide laufen ueber _erlaubte_liste bzw. eine bewusst
# lueckenhafte Liste -- kein Eingriff in entry_positivliste.js noetig, weil
# die Abmeldeschleife selbst (functionService.unregisterExecutors) nur ueber
# die Eingabeliste ansteuerbar ist. Der Rueckbau passiert automatisch durch
# den Context-Manager; git diff nach einem vollen Testlauf zeigt daher keine
# Aenderung an positivliste.mjs.

def test_mutationsprobe_erweiterte_anmeldung_faellt_auf():
    """Wird eine bislang abgemeldete, echte Funktion in die Positivliste
    aufgenommen, MUSS ein Test, der die produktive (enge) Liste erwartet,
    das nicht mehr blind gutheissen -- hier direkt am Ergebnis geprueft,
    ohne den festen 37er-Grundzustandstest zu veraendern."""
    with _erlaubte_liste(["SUM", "IF", "CONCATENATE"]):
        d = _fuehre_probe_aus()
    assert d["c4_abgemeldete_echte_funktion_concatenate"] == "ab"
    assert "CONCATENATE" in d["verfuegbar"]


def test_mutationsprobe_verkuerzte_anmeldung_entzieht_erlaubte_funktion():
    """Gegenprobe: fehlt eine tatsaechlich gebrauchte Funktion (hier SUM) in
    der Liste, wird sie ebenso zuverlaessig abgemeldet wie jede andere --
    die Schleife kennt keine Ausnahme fuer 'eigentlich gewollt'."""
    with _erlaubte_liste(["IF"]):
        d = _fuehre_probe_aus()
    assert d["c1_summe_ueber_benannten_bereich"] == "#NAME?"
    assert "SUM" not in d["verfuegbar"]
