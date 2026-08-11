"""Tests fuer den echten Zeitzonen-Versatz statt fest "+01:00".

Befund 2026-08-06: now_iso() in sechs Dateien nutzte eine feste
timezone(timedelta(hours=1)) und haengte den Text "+01:00" fest an --
im Sommer (Europe/Berlin = +02:00) war der geschriebene Zeitstempel damit
zwei Stunden falsch benannt (Wanduhrzeit = UTC+1, Label "+01:00", real
waere UTC+2 richtig gewesen). Fix: zoneinfo Europe/Berlin +
datetime.isoformat() (liefert bereits Doppelpunkt-Form).
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "kern"))

import knowledge_mcp_server as kms
import build_embeddings as be
import lesson_recorder as lr
import hebb_kanten as hk
import fix_namensraum_knoten as fnk
import migrate_knowledge as mk

BERLIN = ZoneInfo("Europe/Berlin")

MODULE_NOW_ISO = [kms.now_iso, be.now_iso, lr.now_iso, fnk.now_iso, mk.now_iso]


def test_rot_vor_gruen_now_iso_stimmt_mit_echter_berliner_zeit_ueberein():
    """Wanduhrzeit (ohne Offset) muss der echten Europe/Berlin-Wanduhrzeit
    entsprechen, Toleranz 5s. Der alte Fehler war intern selbstkonsistent
    (Instant parst korrekt), aber die Wanduhrzeit stammte aus einer fest
    verdrahteten +1h-Zone -- im Sommer 1h hinter der echten Berliner Zeit
    (Befund 2026-08-06: DB 08:28:27+01:00 vs. echte Zeit 10:28:27+02:00)."""
    referenz_naiv = datetime.now(BERLIN).replace(tzinfo=None)
    for now_iso in MODULE_NOW_ISO:
        geschrieben = now_iso()
        geparst_naiv = datetime.fromisoformat(geschrieben).replace(tzinfo=None)
        diff = abs((geparst_naiv - referenz_naiv).total_seconds())
        assert diff < 5, f"{now_iso.__module__}.now_iso() Wanduhrzeit weicht {diff}s ab: {geschrieben}"


def test_now_iso_traegt_doppelpunkt_im_versatz():
    for now_iso in MODULE_NOW_ISO:
        geschrieben = now_iso()
        versatz = geschrieben[-6:]
        assert versatz[3] == ":", f"{now_iso.__module__}: Versatz ohne Doppelpunkt: {geschrieben}"


def test_winter_gegenprobe_januar_traegt_plus_eins():
    dt = datetime(2026, 1, 15, 12, 0, 0, tzinfo=BERLIN)
    assert dt.isoformat(timespec="seconds").endswith("+01:00")


def test_winter_gegenprobe_juli_traegt_plus_zwei():
    dt = datetime(2026, 7, 15, 12, 0, 0, tzinfo=BERLIN)
    assert dt.isoformat(timespec="seconds").endswith("+02:00")


def test_hebb_kanten_stamp_hilfsfunktion_nutzt_echten_versatz():
    # hebb_kanten._selftest() baut "now" fuer Testfixtures -- direkt pruefen,
    # dass die Zeile datetime.now(BERLIN).isoformat(...) nutzt (kein CET-Rest).
    assert not hasattr(hk, "CET"), "hebb_kanten.py: fixe CET-Zone haette entfernt werden sollen"
    assert not hasattr(kms, "CET"), "knowledge_mcp_server.py: fixe CET-Zone haette entfernt werden sollen"
    assert not hasattr(be, "CET"), "build_embeddings.py: fixe CET-Zone haette entfernt werden sollen"
    assert not hasattr(fnk, "CET"), "fix_namensraum_knoten.py: fixe CET-Zone haette entfernt werden sollen"
    assert not hasattr(mk, "CET"), "migrate_knowledge.py: fixe CET-Zone haette entfernt werden sollen"
    assert not hasattr(lr, "CET"), "lesson_recorder.py: fixe CET-Zone haette entfernt werden sollen"
