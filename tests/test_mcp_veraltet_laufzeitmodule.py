"""MUST-LAGE-002: Der MCP-Wächter beobachtet geladene Laufzeitmodule.

Rot vor Grün: Vor dem Fix verglich ``haken/mcp_veraltet.py`` ausschließlich
den Wrapper ``knowledge_mcp_server.py``. Ein nach Prozessstart geänderter
Scorer blieb deshalb unsichtbar, obwohl der laufende Prozess dessen alten
Python-Code weiter benutzte.
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


def test_main_meldet_nach_prozessstart_geaenderten_scorer(
    tmp_path, monkeypatch, capsys
):
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
    responses = iter(
        (
            SimpleNamespace(stdout="123\n"),
            SimpleNamespace(
                stdout=datetime.fromtimestamp(200).strftime(
                    mcp_veraltet.LSTART_FMT
                )
                + "\n"
            ),
        )
    )
    monkeypatch.setattr(
        mcp_veraltet.subprocess, "run", lambda *_args, **_kwargs: next(responses)
    )

    mcp_veraltet.main()

    assert "veraltet" in capsys.readouterr().out
