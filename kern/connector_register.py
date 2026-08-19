#!/usr/bin/env python3
"""connector_register.py -- Registriert AUFNAHMEN fremder Dokumente, nie das
Dokument selbst (BDW-F08-AC1), und laesst nur zugelassene Connectoren ran
(BDW-U04-AC1).

F08: Zu jeder Referenz stehen PRUEFSUMME (sha256 ueber den gelesenen Inhalt),
PROVENIENZ (Quelle, Zeitpunkt, wer) und CLAIMS (die daraus entstandenen
Aussagen). Der Inhalt selbst wird nirgends abgelegt -- `aufnehmen()` nimmt ihn
nur entgegen, um die Pruefsumme zu bilden, und haelt ihn danach nicht mehr.
Kommt dieselbe Referenz mit ANDERER Pruefsumme wieder, ist das ein Befund
(`AbweichendePruefsumme`), kein stilles Ueberschreiben -- der alte Eintrag
bleibt unangetastet stehen.

U04: Die Allowlist entscheidet, welcher Connector-Name benutzbar ist. Die
Pruefung sitzt in `aufnehmen()` selbst -- der Funktion, die die Arbeit tut --
nicht nur in `aktivieren()`. Wer `aufnehmen()` direkt mit einem nicht
gelisteten Namen aufruft, scheitert genauso wie ueber `aktivieren()`.

WO DIE ALLOWLIST LIEGT: im Register-Objekt selbst (`_erlaubt`), nicht in der
Wissens-DB und nicht unter runs/ -- sie ist Betriebszustand (welcher
Connector-Name heute zugelassen ist), kein Wissen, und dieses Modul darf laut
Auftrag keine weitere Datei anlegen.

Zeit kommt als Parameter `ts` herein (Walkthrough-Doktrin) -- kein eigenes
`now()` im Kern.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


class ConnectorNichtErlaubt(Exception):
    """Der Connector-Name steht nicht auf der Allowlist."""


class AbweichendePruefsumme(Exception):
    """Dieselbe Referenz wurde mit anderem Inhalt erneut aufgenommen."""


@dataclass
class Aufnahme:
    referenz: str
    pruefsumme: str
    quelle: str
    ts: float
    wer: str
    claims: tuple[str, ...]


@dataclass
class ConnectorRegister:
    """`_erlaubt`: Allowlist. `_aufnahmen`: referenz -> Aufnahme, NIE Inhalt."""

    _erlaubt: set[str] = field(default_factory=set)
    _aufnahmen: dict[str, Aufnahme] = field(default_factory=dict)

    def zulassen(self, connector: str) -> None:
        """Pflegt die Allowlist. Getrennte Handlung von aufnehmen(), damit
        eine Pruefung von zulassen() unabhaengig ausfallen kann."""
        self._erlaubt.add(connector)

    def ist_erlaubt(self, connector: str) -> bool:
        return connector in self._erlaubt

    def aktivieren(self, connector: str) -> None:
        """Oberflaechen-Gate. Nicht der eigentliche Schutz -- der sitzt in
        aufnehmen() -- aber ein fruehes, sprechendes Scheitern fuer den
        ueblichen Weg."""
        if not self.ist_erlaubt(connector):
            raise ConnectorNichtErlaubt(connector)

    def aufnehmen(
        self,
        connector: str,
        referenz: str,
        inhalt: bytes,
        quelle: str,
        ts: float,
        wer: str,
        claims: tuple[str, ...],
    ) -> Aufnahme:
        """Legt Referenz, Pruefsumme, Provenienz und Claims ab. `inhalt`
        verlaesst diese Funktion nur als Hash -- es wird nirgends zugewiesen
        oder zurueckgegeben. Prueft die Allowlist SELBST (U04): ein
        Direktaufruf mit nicht gelistetem Connector scheitert genauso wie
        aktivieren()."""
        if not self.ist_erlaubt(connector):
            raise ConnectorNichtErlaubt(connector)
        pruefsumme = hashlib.sha256(inhalt).hexdigest()
        bisherige = self._aufnahmen.get(referenz)
        if bisherige is not None and bisherige.pruefsumme != pruefsumme:
            raise AbweichendePruefsumme(
                f"{referenz}: alt={bisherige.pruefsumme} neu={pruefsumme}"
            )
        aufnahme = Aufnahme(
            referenz=referenz,
            pruefsumme=pruefsumme,
            quelle=quelle,
            ts=ts,
            wer=wer,
            claims=tuple(claims),
        )
        self._aufnahmen[referenz] = aufnahme
        return aufnahme

    def gelesen(self, referenz: str) -> Aufnahme | None:
        return self._aufnahmen.get(referenz)


def _demo() -> None:
    reg = ConnectorRegister()
    reg.zulassen("pdf")
    a = reg.aufnehmen("pdf", "doc://1", b"Inhalt A", "quelle-x", 1000.0, "tester", ("claim-1",))
    assert a.pruefsumme == hashlib.sha256(b"Inhalt A").hexdigest()
    assert "inhalt" not in vars(a)
    try:
        reg.aufnehmen("pdf", "doc://1", b"Inhalt B", "quelle-x", 1001.0, "tester", ())
        raise AssertionError("haette AbweichendePruefsumme werfen muessen")
    except AbweichendePruefsumme:
        pass
    try:
        reg.aufnehmen("unbekannt", "doc://2", b"x", "quelle-x", 1000.0, "tester", ())
        raise AssertionError("haette ConnectorNichtErlaubt werfen muessen")
    except ConnectorNichtErlaubt:
        pass
    print("connector_register: selftest ok")


if __name__ == "__main__":
    _demo()
