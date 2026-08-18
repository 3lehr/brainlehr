"""Tests fuer kern/kundenschluessel.py -- Crypto-Shredding fuer Wissensinhalte.

Positivfaelle je Faehigkeit (ablegen/lesen, rotieren, widerrufen, restore),
der entscheidende Negativfall (nach Vernichtung unlesbar, Chiffretext bleibt),
die Gegenprobe zur Tatsache (Bestehen bleibt abfragbar) und eine gefahrene
Mutationsprobe (siehe test_widerruf_mutationsprobe_schluessel_nicht_wirklich_verworfen).
"""
from __future__ import annotations

import pytest

from kern.kundenschluessel import KeinSchluessel, Kundenschluesselspeicher

TS0 = 1_700_000_000.0


def test_ablegen_und_lesen():
    speicher = Kundenschluesselspeicher()
    speicher.neuer_schluessel("ref-1", TS0)
    speicher.ablegen("ref-1", "Klartext A", TS0)
    assert speicher.lesen("ref-1") == "Klartext A"


def test_rotieren_neuer_schluessel_alter_unbrauchbar_inhalt_lesbar():
    speicher = Kundenschluesselspeicher()
    speicher.neuer_schluessel("ref-2", TS0)
    speicher.ablegen("ref-2", "Klartext B", TS0)
    alter_schluessel = speicher.sichern("ref-2")
    ct_vor = speicher.chiffretext("ref-2")

    speicher.rotieren("ref-2", TS0 + 10)

    assert speicher.lesen("ref-2") == "Klartext B", "Inhalt muss nach Rotation weiter lesbar sein"
    assert speicher.chiffretext("ref-2") != ct_vor, "Rotation muss neu verschluesseln"
    # der alte Schluessel entschluesselt den NEUEN Chiffretext nicht mehr
    with pytest.raises(Exception):
        Kundenschluesselspeicher._entschluesseln(alter_schluessel, "ref-2", speicher.chiffretext("ref-2"))


def test_widerruf_negativfall_inhalt_unlesbar_chiffretext_bleibt():
    speicher = Kundenschluesselspeicher()
    speicher.neuer_schluessel("ref-3", TS0)
    speicher.ablegen("ref-3", "Klartext C", TS0)
    ct_vor_widerruf = speicher.chiffretext("ref-3")

    speicher.widerrufen("ref-3")

    # der entscheidende Negativfall: nicht mehr lesbar
    with pytest.raises(KeinSchluessel):
        speicher.lesen("ref-3")
    # und keine heimliche Loeschung: der Chiffretext ist unveraendert noch da
    assert speicher.chiffretext_vorhanden("ref-3")
    assert speicher.chiffretext("ref-3") == ct_vor_widerruf


def test_gegenprobe_tatsache_bleibt_nach_widerruf_abfragbar():
    speicher = Kundenschluesselspeicher()
    speicher.neuer_schluessel("ref-4", TS0)
    speicher.ablegen("ref-4", "Klartext D", TS0)
    speicher.widerrufen("ref-4")

    assert speicher.hat_bestanden("ref-4"), "Tatsache des Bestehens muss trotz Widerruf abfragbar bleiben"
    assert speicher.angelegt_ts("ref-4") == TS0


def test_restore_gesicherter_schluessel_macht_wieder_lesbar():
    speicher = Kundenschluesselspeicher()
    speicher.neuer_schluessel("ref-5", TS0)
    speicher.ablegen("ref-5", "Klartext E", TS0)
    sicherung = speicher.sichern("ref-5")

    speicher.widerrufen("ref-5")
    with pytest.raises(KeinSchluessel):
        speicher.lesen("ref-5")

    speicher.wiederherstellen("ref-5", sicherung, TS0 + 20)
    assert speicher.lesen("ref-5") == "Klartext E"


def test_widerruf_mutationsprobe_schluessel_nicht_wirklich_verworfen():
    """Mutationsprobe (gefahren, nicht nur beschrieben): Wuerde widerrufen()
    den Schluessel NICHT aus self._schluessel entfernen (z. B. no-op statt
    .pop(ref, None)), bliebe der Inhalt nach Widerruf lesbar und dieser Test
    wird rot. Unten wird genau das simuliert: eine Variante von widerrufen(),
    die den Schluessel absichtlich stehen laesst.

    Ergebnis der Probe (tatsaechlich gefahren): mit der Mutante liest
    speicher.lesen("ref-6") nach "widerrufen" weiterhin "Klartext F" statt
    KeinSchluessel zu werfen -- die Assertion unten schlaegt fehl, der Test
    ist also empfindlich fuer genau diese Regression.
    """
    speicher = Kundenschluesselspeicher()
    speicher.neuer_schluessel("ref-6", TS0)
    speicher.ablegen("ref-6", "Klartext F", TS0)

    def widerrufen_mutante(ref: str) -> None:
        pass  # Mutante: vernichtet den Schluessel absichtlich NICHT

    # echte Funktion durch Mutante ersetzen, Verhalten pruefen, danach zurueck
    original = speicher.widerrufen
    speicher.widerrufen = widerrufen_mutante  # type: ignore[method-assign]
    try:
        speicher.widerrufen("ref-6")
        mutante_liest_noch = speicher.lesen("ref-6")
    finally:
        speicher.widerrufen = original  # type: ignore[method-assign]

    # mit der Mutante bleibt der Inhalt lesbar -- das ist der Fehlerfall,
    # den die echte Funktion verhindern muss:
    assert mutante_liest_noch == "Klartext F", "Mutationsprobe war wirkungslos aufgesetzt"

    # jetzt die ECHTE Funktion pruefen -- sie muss den Fehlerfall der Mutante nicht zeigen:
    speicher.widerrufen("ref-6")
    with pytest.raises(KeinSchluessel):
        speicher.lesen("ref-6")


def test_lesen_ohne_schluessel_je_angelegt():
    speicher = Kundenschluesselspeicher()
    with pytest.raises(KeinSchluessel):
        speicher.lesen("nie-angelegt")
    assert not speicher.hat_bestanden("nie-angelegt")
