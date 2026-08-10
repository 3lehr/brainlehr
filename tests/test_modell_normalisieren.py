"""Ein Modell, eine Schreibweise -- sonst ist das Feld nicht gruppierbar.

Die Faelle stammen aus dem echten Bestand (gemessen 2026-08-08): fuenf
Schreibweisen fuer zwei Modelle, dazu 95 Prozent NULL. Die NULLs sind eine
andere Baustelle; hier geht es nur darum, dass die gefuellten Werte
zusammenfallen, wenn sie dasselbe meinen.
"""

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from knowledge_mcp_server import modell_normalisieren as n  # noqa: E402


def test_die_fuenf_schreibweisen_aus_dem_bestand_fallen_zusammen():
    opus = {"Anthropic/claude-opus-5", "anthropic/claude-opus-5", "claude-opus-5",
            "Anthropic/Opus 5", "  Opus 5  ", "opus5"}
    assert len({n(v) for v in opus}) == 1, "alle meinen dasselbe Modell"
    assert n("Anthropic/Opus 5") == "claude-opus-5"
    assert n("claude-sonnet-5") == "claude-sonnet-5" != n("claude-opus-5")


def test_unbekanntes_geht_durch_statt_verworfen_zu_werden():
    """Kein geschlossener Wertebereich: ein neues Modell soll eintragbar
    sein. Normalisiert wird die Schreibweise, nicht der Inhalt."""
    assert n("irgendwas-neues-2027") == "irgendwas-neues-2027"
    assert n("Irgendwas-Neues-2027") == "irgendwas-neues-2027"


def test_anbieter_bleibt_wo_er_unterscheidet():
    """Ein lokales gemma3 ist nicht dasselbe wie ein gehostetes."""
    assert n("ollama/gemma3:12b") == "ollama/gemma3:12b"
    assert n("gemma3:12b") == "gemma3:12b"
    assert n("ollama/gemma3:12b") != n("gemma3:12b")


def test_none_und_leer_bleiben_unterscheidbar():
    """Wer bewusst nichts sagt, darf nicht aussehen wie wer nichts uebergab."""
    assert n(None) is None
    assert n("") == ""
    assert n("   ") == ""
