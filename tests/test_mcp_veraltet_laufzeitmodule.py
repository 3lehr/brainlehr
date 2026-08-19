"""MUST-LAGE-002: Der MCP-Wächter beobachtet geladene Laufzeitmodule.

Rot vor Grün: Vor dem ersten Fix verglich ``haken/mcp_veraltet.py``
ausschließlich den Wrapper ``knowledge_mcp_server.py``. Ein nach
Prozessstart geänderter Scorer blieb deshalb unsichtbar, obwohl der
laufende Prozess dessen alten Python-Code weiter benutzte.

L-47a196 (2026-08-14): die Meldung nannte weder PID noch Elternprozess und
band die Empfehlung "Sitzung neu starten" nicht an den Halter -- ein Fund
unter fremdem Halter (anderer MCP-Klient) blieb dadurch unerreichbar,
obwohl die Meldung genau das nahelegte. Die Tests unten prüfen die reine
Auswertungsfunktion mit erfundenen Prozesslisten (nicht gegen echte
``ps``-Ausgabe) und den ``--erneut``-Schalter gegen den Sitzungsmarker.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "haken")]

from haken import mcp_veraltet  # noqa: E402


def test_neuestes_laufzeitmodul_bestimmt_veraltungsgrenze(tmp_path, monkeypatch):
    wrapper = tmp_path / "knowledge_mcp_server.py"
    scorer = tmp_path / "relevanzlage.py"
    wrapper.write_text("# wrapper\n", encoding="utf-8")
    scorer.write_text("# scorer\n", encoding="utf-8")

    os.utime(wrapper, (100, 100))
    os.utime(scorer, (300, 300))
    monkeypatch.setattr(mcp_veraltet, "RUNTIME_FILES", (wrapper, scorer))

    assert mcp_veraltet.latest_runtime_mtime() == 300


# -- auswerten(): reine Funktion, erfundene Prozesslisten, kein echtes ps ---

CLAUDE_ELTERN = (
    "/Users/lehrmacbook/Library/Application Support/Claude/claude-code/"
    "2.1.229/claude.app/Contents/MacOS/claude --resume=xyz"
)
FREMDER_ELTERN = (
    "/Users/lehrmacbook/.hermes/hermes-agent/venv/bin/python "
    "/Users/lehrmacbook/.hermes/hermes-agent/tools/mcp_stdio_watchdog.py "
    "--ppid 1323 -- /opt/homebrew/bin/python3 "
    "/Volumes/daten/Begod2026/brainlehr/knowledge_mcp_server.py"
)


def test_fund_unter_claude_fenster_empfiehlt_sitzungsneustart():
    prozesse = [("5680", "5679", 100.0)]
    eltern = {"5679": CLAUDE_ELTERN}
    zeilen = mcp_veraltet.auswerten(prozesse, eltern, mtime=200.0)
    assert len(zeilen) == 1
    assert "PID 5680" in zeilen[0]
    assert "eigenes Claude-Fenster" in zeilen[0]
    assert "neu starten" in zeilen[0]
    assert "erreicht diesen Fund nicht" not in zeilen[0]


def test_fund_unter_fremdem_halter_nennt_halter_statt_sitzungsneustart():
    prozesse = [("5680", "5679", 100.0)]
    eltern = {"5679": FREMDER_ELTERN}
    zeilen = mcp_veraltet.auswerten(prozesse, eltern, mtime=200.0)
    assert len(zeilen) == 1
    assert "PID 5680" in zeilen[0]
    assert "PID 5679" in zeilen[0]
    assert "mcp_stdio_watchdog.py" in zeilen[0]
    assert "gehalten von" in zeilen[0]
    assert "erreicht diesen Fund nicht" in zeilen[0]


def test_neuerer_prozess_als_datei_wird_nicht_gemeldet():
    """Negativfall: Prozessstart nach der letzten Dateiänderung -> kein Fund."""
    prozesse = [("999", "1", 500.0)]
    eltern = {"1": CLAUDE_ELTERN}
    zeilen = mcp_veraltet.auswerten(prozesse, eltern, mtime=200.0)
    assert zeilen == []


def test_grenzwert_startzeit_exakt_gleich_dateistand_gewinnt_der_prozess():
    """Bei Gleichstand (mtime == started) ist NICHT 'mtime > started' -> kein Fund.

    Der Prozess gewinnt den Grenzfall: eine Reparatur, die exakt beim
    Prozessstart geschrieben wurde, gilt als geladen, nicht als verpasst.
    """
    prozesse = [("999", "1", 200.0)]
    eltern = {"1": CLAUDE_ELTERN}
    zeilen = mcp_veraltet.auswerten(prozesse, eltern, mtime=200.0)
    assert zeilen == []

    # Eine Nanosekunde jünger als der Dateistand -> doch ein Fund.
    zeilen_knapp_aelter = mcp_veraltet.auswerten(prozesse, eltern, mtime=200.000001)
    assert len(zeilen_knapp_aelter) == 1


def test_main_meldet_pid_und_halter_bei_fremdem_prozess(tmp_path, monkeypatch, capsys):
    wrapper = tmp_path / "knowledge_mcp_server.py"
    scorer = tmp_path / "relevanzlage.py"
    wrapper.write_text("# wrapper\n", encoding="utf-8")
    scorer.write_text("# scorer\n", encoding="utf-8")
    os.utime(wrapper, (100, 100))
    os.utime(scorer, (300, 300))

    monkeypatch.setattr(mcp_veraltet, "SERVER_FILE", str(wrapper))
    monkeypatch.setattr(mcp_veraltet, "RUNTIME_FILES", (wrapper, scorer))
    monkeypatch.setattr(
        mcp_veraltet, "state_path", lambda _session: str(tmp_path / "marker")
    )
    monkeypatch.setattr(mcp_veraltet.sys, "stdin", StringIO("{}"))
    monkeypatch.setattr(mcp_veraltet.sys, "argv", ["mcp_veraltet.py"])

    lstart = datetime.fromtimestamp(200).strftime(mcp_veraltet.LSTART_FMT)
    responses = iter(
        (
            SimpleNamespace(stdout="5680\n"),  # pgrep
            SimpleNamespace(stdout=f"5680 5679 {lstart} /usr/bin/python3 {wrapper}\n"),
            # pid,ppid,lstart,command -- das Kommando kam 2026-08-19 dazu:
            # prozessliste() sortiert damit blosse Textreffer aus (pgrep -f
            # findet auch Prozesse, die den Serverpfad nur in einem
            # --mcp-config-JSON mit sich tragen).
            SimpleNamespace(stdout=f"5679 {FREMDER_ELTERN}\n"),  # ppid,command
        )
    )
    monkeypatch.setattr(
        mcp_veraltet.subprocess, "run", lambda *_args, **_kwargs: next(responses)
    )

    mcp_veraltet.main()

    out = capsys.readouterr().out
    assert "veraltet" in out
    assert "PID 5680" in out
    assert "gehalten von" in out


def test_textreffer_im_mcp_config_zaehlt_nicht_als_serverinstanz():
    """ROT VOR GRUEN (2026-08-19): `pgrep -f` findet auch Prozesse, die den
    Serverpfad nur als TEXT tragen -- das Claude-Programm fuehrt ihn in
    seinem --mcp-config-JSON mit. Gemessen an dem Tag: 4 von 14 gemeldeten
    Funden waren solche Textreffer (PID 10662, 10663, 63304, 63305), und die
    Gesamtzahl stimmte trotzdem, weil zufaellig vier echte Instanzen zu Recht
    fehlten. Vor dieser Aenderung gab es die Funktion nicht."""
    echt = f"/opt/homebrew/bin/python3 {mcp_veraltet.SERVER_FILE}"
    assert mcp_veraltet.ist_serverinstanz(echt) is True

    textreffer = (
        '/Applications/Claude.app/Contents/MacOS/claude --mcp-config '
        '{"mcpServers":{"knowledge":{"command":"/opt/homebrew/bin/python3",'
        f'"args":["{mcp_veraltet.SERVER_FILE}"]}}}}}}'
    )
    assert mcp_veraltet.ist_serverinstanz(textreffer) is False

    # Gegenprobe, damit die Unterscheidung nicht bloss auf Anfuehrungszeichen
    # beruht: ein Wrapper, der den Pfad NACH `--` als eigenes Argument
    # weiterreicht, IST eine Serverinstanz und muss weiter gemeldet werden.
    wrapper = f"/usr/bin/python3 watchdog.py --ppid 1323 -- /usr/bin/python3 {mcp_veraltet.SERVER_FILE}"
    assert mcp_veraltet.ist_serverinstanz(wrapper) is True


def test_marker_greift_nicht_bei_erneut(tmp_path, monkeypatch, capsys):
    """L-47a196: der 1x-pro-Sitzung-Marker darf --erneut nicht schlucken."""
    wrapper = tmp_path / "knowledge_mcp_server.py"
    scorer = tmp_path / "relevanzlage.py"
    wrapper.write_text("# wrapper\n", encoding="utf-8")
    scorer.write_text("# scorer\n", encoding="utf-8")
    os.utime(wrapper, (100, 100))
    os.utime(scorer, (300, 300))

    marker = tmp_path / "marker"
    marker.write_text("1")  # Marker existiert bereits -- Sitzung schon gemeldet.

    monkeypatch.setattr(mcp_veraltet, "SERVER_FILE", str(wrapper))
    monkeypatch.setattr(mcp_veraltet, "RUNTIME_FILES", (wrapper, scorer))
    monkeypatch.setattr(mcp_veraltet, "state_path", lambda _session: str(marker))
    monkeypatch.setattr(mcp_veraltet.sys, "stdin", StringIO("{}"))

    lstart = datetime.fromtimestamp(200).strftime(mcp_veraltet.LSTART_FMT)
    responses = iter(
        (
            SimpleNamespace(stdout="5680\n"),
            SimpleNamespace(stdout=f"5680 5679 {lstart} /usr/bin/python3 {wrapper}\n"),
            SimpleNamespace(stdout=f"5679 {CLAUDE_ELTERN}\n"),
        )
    )
    monkeypatch.setattr(
        mcp_veraltet.subprocess, "run", lambda *_args, **_kwargs: next(responses)
    )

    # Ohne --erneut: Marker greift, keine Ausgabe.
    monkeypatch.setattr(mcp_veraltet.sys, "argv", ["mcp_veraltet.py"])
    mcp_veraltet.main()
    assert capsys.readouterr().out == ""

    # Mit --erneut: Marker wird ignoriert, Meldung erscheint trotzdem.
    monkeypatch.setattr(mcp_veraltet.sys, "argv", ["mcp_veraltet.py", "--erneut"])
    mcp_veraltet.main()
    assert "veraltet" in capsys.readouterr().out
