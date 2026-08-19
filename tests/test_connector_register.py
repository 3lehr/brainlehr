#!/usr/bin/env python3
"""Belegt BDW-F08-AC1 (Referenz/Pruefsumme/Provenienz/Claims statt Kopie,
Abweichung ist Befund) und BDW-U04-AC1 (Allowlist wirkt bei Aktivierung UND
Direktaufruf, ein gelisteter Connector laeuft unveraendert durch).

Rot-Probe: `git stash` auf diesen Test gegen Commit vor der Aenderung faellt
weg, weil connector_register.py in demselben Commit entsteht wie der Test --
Rot vor gruen wird stattdessen ueber einen FESTEN Vergleichs-Commit-Hash
gefahren (siehe Auftrag), nicht ueber diese Datei selbst.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "kern"))

from connector_register import (  # noqa: E402
    AbweichendePruefsumme,
    ConnectorNichtErlaubt,
    ConnectorRegister,
)


def _reg() -> ConnectorRegister:
    r = ConnectorRegister()
    r.zulassen("pdf")
    return r


# --- F08: je Eigenschaft ein Fall ---

def test_f08_referenz():
    r = _reg()
    a = r.aufnehmen("pdf", "doc://1", b"Inhalt", "quelle-x", 100.0, "alice", ())
    assert a.referenz == "doc://1"


def test_f08_pruefsumme():
    import hashlib

    r = _reg()
    a = r.aufnehmen("pdf", "doc://1", b"Inhalt", "quelle-x", 100.0, "alice", ())
    assert a.pruefsumme == hashlib.sha256(b"Inhalt").hexdigest()


def test_f08_provenienz():
    r = _reg()
    a = r.aufnehmen("pdf", "doc://1", b"Inhalt", "quelle-x", 100.0, "alice", ())
    assert (a.quelle, a.ts, a.wer) == ("quelle-x", 100.0, "alice")


def test_f08_claims():
    r = _reg()
    a = r.aufnehmen("pdf", "doc://1", b"Inhalt", "quelle-x", 100.0, "alice", ("satz-1", "satz-2"))
    assert a.claims == ("satz-1", "satz-2")


def test_f08_inhalt_nicht_kopiert():
    """Das Dokument selbst ist nirgends abgelegt: der Aufnahme-Datensatz
    traegt kein Feld mit dem Originalinhalt, und die interne Ablage des
    Registers enthaelt den Bytestring an keiner Stelle."""
    r = _reg()
    geheim = b"NUR-EINMAL-VORHANDENER-INHALT-42"
    a = r.aufnehmen("pdf", "doc://1", geheim, "quelle-x", 100.0, "alice", ())
    assert not any(isinstance(v, bytes) for v in vars(a).values())
    assert geheim.decode() not in repr(r._aufnahmen)


def test_f08_gegenprobe_abweichung_ist_befund():
    """Gleiche Referenz, anderer Inhalt: BEFUND, kein stilles Ueberschreiben
    -- der alte Eintrag bleibt stehen."""
    r = _reg()
    alt = r.aufnehmen("pdf", "doc://1", b"Version A", "quelle-x", 100.0, "alice", ())
    try:
        r.aufnehmen("pdf", "doc://1", b"Version B", "quelle-x", 200.0, "alice", ())
        assert False, "haette AbweichendePruefsumme werfen muessen"
    except AbweichendePruefsumme:
        pass
    assert r.gelesen("doc://1").pruefsumme == alt.pruefsumme


def test_f08_gleicher_inhalt_kein_befund():
    """Grenzwert der Gegenprobe: identischer Inhalt erneut aufgenommen loest
    KEINEN Befund aus."""
    r = _reg()
    r.aufnehmen("pdf", "doc://1", b"gleich", "quelle-x", 100.0, "alice", ())
    r.aufnehmen("pdf", "doc://1", b"gleich", "quelle-y", 200.0, "bob", ())


# --- U04: beide Wege, plus Gegenprobe ---

def test_u04_aktivieren_scheitert_bei_nicht_gelistet():
    r = ConnectorRegister()
    try:
        r.aktivieren("unbekannt")
        assert False, "haette ConnectorNichtErlaubt werfen muessen"
    except ConnectorNichtErlaubt:
        pass


def test_u04_direktaufruf_scheitert_bei_nicht_gelistet():
    """Der Kern von U04: aufnehmen() OHNE vorherige Aktivierung, mit nicht
    gelistetem Connector-Namen -- der Umgehungsweg."""
    r = ConnectorRegister()
    try:
        r.aufnehmen("unbekannt", "doc://1", b"x", "quelle-x", 100.0, "alice", ())
        assert False, "haette ConnectorNichtErlaubt werfen muessen"
    except ConnectorNichtErlaubt:
        pass
    assert r.gelesen("doc://1") is None


def test_u04_gegenprobe_gelisteter_connector_laeuft_durch():
    """Eine Allowlist, die alles blockiert, bestuende den Test oben ebenso --
    dieser Fall zeigt, dass ein gelisteter Connector unveraendert arbeitet."""
    r = _reg()
    a = r.aufnehmen("pdf", "doc://1", b"x", "quelle-x", 100.0, "alice", ())
    assert a.referenz == "doc://1"


if __name__ == "__main__":
    import inspect

    ok = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and inspect.isfunction(fn):
            fn()
            ok += 1
    print(f"{ok} Tests gruen")
