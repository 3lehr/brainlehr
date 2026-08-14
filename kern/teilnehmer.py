#!/usr/bin/env python3
"""Teilnehmerkennungen fuer das gemeinsame Dokument -- die Auflage aus ADR-010,
an einer Stelle durchgesetzt statt in jeder Klientenzeile wiederholt.

DER GRUND, und er ist gemessen: `yswift` schneidet die Teilnehmerkennung
(client id) auf 32 Bit ab, `pycrdt` wuerfelt sie standardmaessig bis etwa 2^53.
Liegt sie darueber, kommt der eigene Beitrag als FREMDER zurueck und wird
pflichtgemaess danebengestellt statt zusammengefuehrt -- der Text verdoppelt
sich STILL. Kein Absturz, keine Meldung. Scharf gemessen am 2026-08-14:
2^32-1 traegt, 2^32 nicht (`L-44dc9f`, Probe in `spikes/crdt_pyswift/`).

WARUM DAS EINE EIGENE DATEI IST: Eine Auflage, die in einem ADR steht und
nirgends im Code, ist eine Absicht. Sie muss an der Stelle sitzen, an der sie
gebrochen wuerde -- also dort, wo eine Kennung entsteht. Wer hier vorbeigeht
und `Doc()` ohne Kennung anlegt, hat den Fehler wieder; deshalb gibt es
`neues_dokument()`, das beides zusammen tut.

WAS HIER BEWUSST NICHT DRIN IST: keine Vergabe ueber das Netz, kein Register,
keine Kollisionspruefung gegen andere Teilnehmer. Der Zufallsraum unter 2^32
ist gross genug, dass zwei Teilnehmer im selben Raum praktisch nie kollidieren
(bei 10 Teilnehmern etwa 1 zu 10^8) -- und ein Register waere ein Dienst, den
es noch nicht gibt. Kollidieren sie doch, faellt es auf: zwei Teilnehmer mit
derselben Kennung erzeugen widerspruechliche Eintraege, und genau dafuer ist
`pruefe()` da, sobald der Dienst die Kennungen kennt.

Aufruf:  python3 kern/teilnehmer.py --selftest
"""

from __future__ import annotations

import argparse
import secrets

# Groesste Kennung, die die Swift-Seite unbeschaedigt zurueckgibt.
# Kein Schaetzwert -- an der Schwelle, darueber und darunter gemessen.
GRENZE = 2**32 - 1


class KennungsFehler(ValueError):
    """Eine Kennung verletzt die Auflage -- laut, nicht still."""


def neue_kennung() -> int:
    """Eine Kennung, die beide Seiten unbeschaedigt tragen.

    Nicht 0: yrs verwendet 0 an manchen Stellen als 'keine Angabe', und eine
    Kennung, die wie eine Abwesenheit aussieht, ist die naechste stille Falle.
    """
    return secrets.randbelow(GRENZE) + 1


def pruefe(kennung: int) -> int:
    """Gibt die Kennung zurueck -- oder wirft. Nie stillschweigend zurechtstutzen.

    Ein Kappen waere hier besonders verlockend (`kennung & 0xFFFFFFFF`) und
    genau falsch: es erzeugt aus zwei verschiedenen Teilnehmern einen, und der
    Schaden traegt keinen Namen mehr.
    """
    if not isinstance(kennung, int) or isinstance(kennung, bool):
        raise KennungsFehler(f"Kennung muss eine ganze Zahl sein, nicht {type(kennung).__name__}")
    if kennung < 1:
        raise KennungsFehler(f"Kennung {kennung} ist kleiner als 1 -- 0 sieht aus wie 'keine Angabe'")
    if kennung > GRENZE:
        raise KennungsFehler(
            f"Kennung {kennung} liegt ueber {GRENZE} (2^32-1). Die Swift-Seite schneidet "
            "auf 32 Bit ab; der eigene Beitrag kaeme als fremder zurueck und der Text "
            "wuerde sich still verdoppeln (ADR-010, L-44dc9f)"
        )
    return kennung


def neues_dokument(kennung: int | None = None):
    """Ein pycrdt-Dokument mit tragbarer Kennung. Der Weg, der nicht vorbeigeht.

    Der Import steht absichtlich hier drin und nicht oben: `pruefe()` und
    `neue_kennung()` sollen auch auf einem Rechner ohne pycrdt laufen -- sonst
    haengt die Durchsetzung der Auflage an einer Abhaengigkeit.
    """
    from pycrdt import Doc

    return Doc(client_id=pruefe(kennung if kennung is not None else neue_kennung()))


def _selftest() -> int:
    # Grenzwert beidseitig, an der Schwelle.
    assert pruefe(1) == 1
    assert pruefe(GRENZE) == GRENZE
    for kaputt in (0, -1, GRENZE + 1, 2**53, True, 1.0, "7"):
        try:
            pruefe(kaputt)
        except KennungsFehler:
            pass
        else:
            raise AssertionError(f"haette fallen muessen: {kaputt!r}")

    # Vergabe bleibt im erlaubten Bereich -- und ist nicht konstant.
    gezogen = {neue_kennung() for _ in range(200)}
    assert all(1 <= k <= GRENZE for k in gezogen)
    assert len(gezogen) > 190, "Vergabe wiederholt sich zu oft -- kein Zufall?"

    # Der bequeme Weg traegt die Auflage mit.
    try:
        from pycrdt import Doc  # noqa: F401
    except ImportError:
        print("teilnehmer: Selbsttest bestanden (ohne pycrdt -- neues_dokument uebersprungen)")
        return 0

    d = neues_dokument()
    assert 1 <= d.client_id <= GRENZE
    assert neues_dokument(4242).client_id == 4242
    try:
        neues_dokument(2**32)
    except KennungsFehler:
        pass
    else:
        raise AssertionError("neues_dokument haette die Kennung ablehnen muessen")

    print("teilnehmer: Selbsttest bestanden")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--neu", action="store_true", help="eine tragbare Kennung ausgeben")
    a = p.parse_args()
    if a.selftest:
        return _selftest()
    if a.neu:
        print(neue_kennung())
        return 0
    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
