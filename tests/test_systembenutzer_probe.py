"""Rot-vor-gruen fuer G5 (docs/PLAN_GESAMT Abschnitt G5, Fund O4 in
docs/SICHERHEITSFUNDE_2026-08-14.md).

HEUTE (2026-08-15) ist der echte Bestand noch rot: brainlehr.db und die
Ausweisdatei gehoeren der angemeldeten Kennung. Der erste Test belegt genau
das, live gegen die echten Dateien -- kein Mock. Er wird von selbst gruen,
sobald der Betreiber spaeter den Systembenutzer angelegt und den Bestand
uebertragen hat; bis dahin MUSS er rot bleiben, sonst prueft die Probe nichts.

Der zweite Test zeigt, dass dieselbe Probe im simulierten Erfolgsfall (fremde
UID, kein Schreibzugriff) tatsaechlich gruen wird -- ohne ihn waere nicht
belegt, dass "gilt: false" ueberhaupt umschlagen KANN.
"""
from __future__ import annotations

import os
import stat
import sys
from pathlib import Path
from unittest import mock

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL / "melder"))

import systembenutzer_probe as probe  # noqa: E402


def test_g5_ist_heute_noch_nicht_erfuellt() -> None:
    """Rot-Probe: der reale Bestand gehoert noch der angemeldeten Kennung.

    Diese Aussage ist ZEITLICH -- vor dem Einfuegen des Systembenutzers wahr,
    danach falsch. Genau das ist der Witz: der Test dokumentiert den
    Ausgangszustand, den die Befehlsfolge in docs/G5_SYSTEMBENUTZER.md
    aendern soll."""
    befund = probe.pruefe()
    assert befund["g5_erfuellt"] is False
    assert befund["brainlehr_db"]["fremder_eigner"] is False
    assert befund["brainlehr_db"]["angemeldeter_uid"] == os.getuid()


def test_probe_wird_gruen_wenn_bestand_fremd_und_nicht_beschreibbar(tmp_path, monkeypatch) -> None:
    """Gegenprobe: simuliert den Zustand NACH dem Einfuegen (fremde UID,
    W_OK False) und zeigt, dass g5_erfuellt dann auf True kippt. Ohne diesen
    Test waere 'gilt: False' oben nicht als echte Messung ausgewiesen --
    eine Probe, die niemals gruen werden kann, ist keine Probe.

    BRAINLEHR_AUSWEISE zeigt (wie bei jedem Test, tests/conftest.py) auf ein
    isoliertes Verzeichnis -- hier extra angelegt, weil die Probe das
    Verzeichnis selbst prueft (nicht nur eine Datei darin) und ein fehlender
    Ordner sonst als 'vorhanden: False' und damit 'gilt: False' zaehlt, egal
    was gemockt wird."""
    ausweisordner = tmp_path / "brainlehr-ausweise"
    ausweisordner.mkdir(mode=0o700)
    monkeypatch.setenv("BRAINLEHR_AUSWEISE", str(ausweisordner))

    mit_fremder_uid = mock.patch("os.getuid", return_value=os.getuid() + 1)
    mit_verweigertem_schreibzugriff = mock.patch("os.access", return_value=False)
    with mit_fremder_uid, mit_verweigertem_schreibzugriff:
        befund = probe.pruefe()
    assert befund["g5_erfuellt"] is True
    assert befund["brainlehr_db"]["gilt"] is True
    assert befund["ausweisordner"]["gilt"] is True


def test_fehlende_datei_urteilt_nicht() -> None:
    """Grenzwert: eine nicht vorhandene Datei darf weder als erfuellt noch
    als Verstoss gelten -- sonst meldet die Probe auf einem frisch geklonten
    Arbeitsbaum ohne DB faelschlich 'gilt'."""
    befund = probe._pruefe_datei(WURZEL / "gibt_es_nicht_12345.db", 0o600)
    assert befund["vorhanden"] is False
    assert befund["gilt"] is False


def test_zu_offene_rechte_unter_fremder_uid_gelten_nicht() -> None:
    """Negativfall: fremde UID allein genuegt nicht -- stehen die Rechte
    trotzdem offen (z.B. 0644), bleibt os.access meist True und die Probe
    darf nicht faelschlich 'erfuellt' melden."""
    mit_fremder_uid = mock.patch("os.getuid", return_value=os.getuid() + 1)
    # W_OK bleibt real (nicht gemockt) -- unter der eigenen Testdatei mit
    # 0600 kann der eigene Prozess ohnehin nicht mehr schreiben, sobald die
    # UID im Mock fremd erscheint faellt os.access auf den echten Kernel-Check
    # zurueck und meldet fuer die eigene Testdatei weiterhin beschreibbar,
    # weil das Betriebssystem die echte UID sieht, nicht die gemockte.
    # Deshalb hier NICHT os.access mocken, sondern direkt pruefen, dass
    # 'nicht_beschreibbar' bei einer reell beschreibbaren Datei False bleibt.
    with mit_fremder_uid:
        befund = probe.pruefe()
    assert befund["brainlehr_db"]["nicht_beschreibbar"] is False
    assert befund["brainlehr_db"]["gilt"] is False
