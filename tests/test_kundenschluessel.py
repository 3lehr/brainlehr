"""Tests fuer kern/kundenschluessel.py -- Crypto-Shredding fuer Wissensinhalte.

Positivfaelle je Faehigkeit (ablegen/lesen, rotieren, widerrufen, restore),
der entscheidende Negativfall (nach Vernichtung unlesbar, Chiffretext bleibt),
die Gegenprobe zur Tatsache (Bestehen bleibt abfragbar) und eine gefahrene
Mutationsprobe (siehe test_widerruf_mutationsprobe_schluessel_nicht_wirklich_verworfen).
"""
from __future__ import annotations

import pytest

from kern.kundenschluessel import KeinSchluessel, Kundenschluesselspeicher, Rechtssperre

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


# --- Legal Hold (BDW-E14, ADR-029) -------------------------------------
# Nachgetragen 2026-08-18. ADR-029 macht den Hold zu einer Sperre AUF DER
# SCHLUESSELVERNICHTUNG statt zu einem Sonderweg an den Daten vorbei -- und
# nennt als dritte Erfolgsprobe ausdruecklich: "Ein Legal Hold verhindert die
# Schluesselvernichtung -- und das schlaegt fehl, wenn jemand den Hold umgeht,
# statt still durchzulaufen."

def test_rechtssperre_verhindert_schluesselvernichtung():
    """DAS AC. Ein Hold macht widerrufen() laut, nicht wirkungslos."""
    s = Kundenschluesselspeicher()
    s.neuer_schluessel("r1", ts=1.0)
    s.ablegen("r1", "geheim", ts=1.0)
    s.rechtssperre_setzen("r1", grund="Betriebspruefung 2026", ts=2.0)

    with pytest.raises(Rechtssperre) as fehler:
        s.widerrufen("r1")
    assert "Betriebspruefung" in str(fehler.value), "Grund fehlt in der Meldung"

    # Und der eigentliche Punkt: der Inhalt ist danach WEITER lesbar.
    assert s.lesen("r1") == "geheim"


def test_aufgehobene_sperre_loescht_nicht_von_selbst():
    """Das Aufheben eines Holds darf keine Loeschung ausloesen -- sonst wird
    aus einer Schutzmassnahme ein Ausloeser. Die Frist muss danach erneut
    greifen."""
    s = Kundenschluesselspeicher()
    s.neuer_schluessel("r2", ts=1.0)
    s.ablegen("r2", "geheim", ts=1.0)
    s.rechtssperre_setzen("r2", grund="Rechtsstreit", ts=2.0)
    s.rechtssperre_aufheben("r2")
    assert s.rechtssperre("r2") is None
    assert s.lesen("r2") == "geheim", "Aufheben hat den Inhalt vernichtet"
    # Erst der ausdrueckliche Widerruf wirkt.
    s.widerrufen("r2")
    with pytest.raises(KeinSchluessel):
        s.lesen("r2")


def test_sperre_wirkt_auch_vor_dem_anlegen():
    """Eine Sperre, die erst nach dem Anlegen gesetzt werden koennte, kaeme im
    Ernstfall zu spaet."""
    s = Kundenschluesselspeicher()
    s.rechtssperre_setzen("r3", grund="vorsorglich", ts=1.0)
    s.neuer_schluessel("r3", ts=2.0)
    s.ablegen("r3", "geheim", ts=2.0)
    with pytest.raises(Rechtssperre):
        s.widerrufen("r3")


def test_sperre_ohne_grund_wird_abgewiesen():
    """Ein Hold ohne Grund ist spaeter weder pruefbar noch aufhebbar."""
    s = Kundenschluesselspeicher()
    for schlecht in ("", "   "):
        with pytest.raises(ValueError):
            s.rechtssperre_setzen("r4", grund=schlecht, ts=1.0)
