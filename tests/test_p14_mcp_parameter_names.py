#!/usr/bin/env python3
"""Test P14-AC2: Deutsche MCP-Parameter identifizieren und übersetzen.

Der Befund sagt '10 von 94 MCP-Parametern noch deutsch'.
Dieser Test dient als Inventur: Welche Parameter sind noch deutsch,
und welche Übersetzung ist vorgesehen?
"""
import sys
from pathlib import Path

w = Path(__file__).resolve().parent
while not (w / "schema.sql").exists() and w != w.parent:
    w = w.parent
sys.path[:0] = [str(w)] + [str(w / o) for o in ("kern", "haken")]

import knowledge_mcp_server as kms  # noqa

# Bekannte deutsche Parameter und ihre englischen Entsprechungen
# Die Liste ist absichtlich explizit, um keine Überraschungen zu haben.
DEUTSCH_NACH_ENGLISCH = {
    "profil": "profile",
    "sprache": "language",
    "kataloge": "catalogs",
    "bestaetigt": "confirmed",
    "mandant": "tenant",
    "anlass": "occasion",
    "gattung": "kind",
    "beinahefehler": "near_miss",
    "bemerkt_woran": "caught_by",
    "gedaechtnisart": "memory_kind",
}


def _alle_parameter():
    """Alle Parameternamen aus allen TOOLS sammeln."""
    params = set()
    for spec in kms.TOOLS.values():
        props = spec.get("inputSchema", {}).get("properties", {})
        params.update(props.keys())
    return params


def test_keine_deutschen_parameter_mehr():
    """P14-AC2: Alle MCP-Parameter müssen englisch sein.

    Rot-Probe: Wenn dieser Test fehlschlägt, gibt es Parameter,
    die noch nicht übersetzt wurden.
    """
    alle = _alle_parameter()
    noch_deutsch = sorted(alle & set(DEUTSCH_NACH_ENGLISCH))
    assert not noch_deutsch, (
        f"Noch {len(noch_deutsch)} deutsche Parameter: {noch_deutsch}. "
        f"Übersetzung: {[(d, DEUTSCH_NACH_ENGLISCH[d]) for d in noch_deutsch]}"
    )
