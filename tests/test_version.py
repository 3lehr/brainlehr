"""Die Fassung steht an EINER Stelle — und alle nennen dieselbe.

Bis 2026-08-10 meldete der MCP-Server fest "1.0.0", waehrend es weder einen
git-Tag noch eine Versionsdatei gab. Eine Stabilitaetszusage ohne Deckung, die
jeder Klient beim Verbinden liest.

Diese Probe faengt die Fehlklasse, die dabei entsteht: eine Zahl im Quelltext
neben einer Zahl in der README neben einem Tag. Sie laufen auseinander, und
hinterher weiss niemand, welche stimmt (vgl. L-c33fbb: eine Korrektur, die
nicht alle Ausgabekanaele erreicht).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

import knowledge_mcp_server as kms  # noqa: E402


def _datei() -> str:
    return (WURZEL / "VERSION").read_text(encoding="utf-8").strip()


def test_versionsdatei_ist_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", _datei()), _datei()


def test_server_meldet_die_datei():
    antwort = kms.handle_request(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    gemeldet = antwort["result"]["serverInfo"]["version"]
    assert gemeldet == _datei(), (
        f"Server meldet {gemeldet!r}, die Datei sagt {_datei()!r}")


def test_readme_nennt_dieselbe_fassung():
    text = (WURZEL / "README.md").read_text(encoding="utf-8")
    assert _datei() in text, (
        f"README nennt die Fassung {_datei()} nicht — dann steht sie an zwei "
        f"Orten verschieden")


def test_keine_stabilitaetszusage_solange_null():
    """Solange die fuehrende Ziffer 0 ist, darf nirgends 'stabil' zugesagt
    werden. Die Probe ist billig und faengt genau den Satz, der beim
    Marketing-Schreiben durchrutscht."""
    if not _datei().startswith("0."):
        return
    text = (WURZEL / "README.md").read_text(encoding="utf-8").lower()
    for wort in ("produktionsreif", "production-ready", "stabile api",
                 "stable api"):
        assert wort not in text, f"README sagt {wort!r} bei Fassung {_datei()}"
