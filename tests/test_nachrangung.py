"""Nachrangung ordnet um und wirft nie etwas weg."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kern.nachrangung import modell, regel  # noqa: E402

KANDIDATEN = [
    {"title": "Ganz anderes Thema", "summary": "Kessel und Heizung", "path": "/a"},
    {"title": "Vertrauensregler", "summary": "Der Regler steuert die Rückfragepflicht", "path": "/b"},
    {"title": "Kurz", "summary": "", "path": "/c"},
]


def test_regel_zieht_den_passenden_nach_vorn():
    r = regel("Was macht der Vertrauensregler?", KANDIDATEN)
    assert r[0] == 1, r


def test_regel_wirft_nichts_weg_und_bleibt_vollstaendig():
    r = regel("Vertrauensregler", KANDIDATEN)
    assert sorted(r) == list(range(len(KANDIDATEN)))


def test_ohne_brauchbare_anfrage_bleibt_die_reihenfolge():
    # Nur Füllwörter: die Fusion wusste schon etwas, das wird nicht ohne
    # Grund verworfen.
    assert regel("und oder die das", KANDIDATEN) == [0, 1, 2]


def test_modell_faellt_bei_fehlschlag_auf_die_alte_reihenfolge():
    # Kein Dienst an diesem Port -- die Nachrangung darf dann nicht
    # abstürzen und nicht kürzen.
    r = modell("egal", KANDIDATEN, endpunkt="http://127.0.0.1:9/api/generate", zeitgrenze=1)
    assert r == [0, 1, 2]


def test_leere_kandidatenliste_ist_kein_fehlerfall():
    assert regel("x", []) == []
    assert modell("x", []) == []
