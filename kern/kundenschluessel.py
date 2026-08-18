#!/usr/bin/env python3
"""kundenschluessel.py -- Crypto-Shredding fuer Wissensinhalte.

Der SCHLUESSEL entscheidet ueber Loeschung, nicht der Datensatz. Ablage und
Schluessel liegen getrennt (zwei dicts hier -- in Produktion zwei Tabellen).
Wird ein Schluessel vernichtet, ist der Inhalt unlesbar; die TATSACHE, dass es
ihn gab (Kennung, Anlage-Zeitpunkt), bleibt in der Metadatenablage stehen und
wird nie geloescht. Das ist der Unterschied zu einem Loesch-Flag auf dem
Datensatz: dort verschwindet mit dem Inhalt auch der Beleg, dass er je da war.

Vorlage: tests/test_enigma_crypto_shredding_spike.py (AESGCM, Nonce voran den
Chiffretext, subject als AAD). Dieses Modul ist keine Kopie des Spikes,
sondern eine Produktionsform desselben Prinzips fuer echte Ablage.

Zeit kommt IMMER als Parameter `ts` herein (Walkthrough-Doktrin) -- nirgends
ein eigenes `now()`/`datetime.now()` im Kern.

Ein erzeugter Schluessel wird NIE ausgegeben (kein Log, kein print, keine
Rueckgabe an eine Anzeige) -- `sichern()` liefert ihn als Bytes an den
Aufrufer zurueck, der ihn ausserhalb dieses Prozesses verwahrt (Backup); das
ist der einzige Weg, wie ein spaeteres `wiederherstellen()` ueberhaupt einen
Schluessel bekommen kann.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass, field

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class KeinSchluessel(Exception):
    """Kein Schluessel vorhanden (nie angelegt, widerrufen oder falsch)."""


@dataclass
class _Eintrag:
    angelegt_ts: float
    blob: bytes | None = None  # nonce + ciphertext; None solange kein Inhalt abgelegt


@dataclass
class Kundenschluesselspeicher:
    """In-Prozess-Ablage. _schluessel und _inhalte sind absichtlich getrennte
    dicts -- Vernichtung trifft nur _schluessel, _metadaten bleibt immer."""

    _schluessel: dict[str, bytes] = field(default_factory=dict)
    _inhalte: dict[str, _Eintrag] = field(default_factory=dict)
    _metadaten: dict[str, float] = field(default_factory=dict)  # ref -> angelegt_ts, NIE geloescht

    def neuer_schluessel(self, ref: str, ts: float) -> None:
        """Legt ref an bzw. rotiert: neuer Schluessel ersetzt einen etwaigen
        alten. Bestehender Inhalt wird mit dem alten Schluessel entschluesselt
        und unter dem neuen wieder abgelegt (Rotation ohne Datenverlust)."""
        alt_blob = self._inhalte.get(ref)
        klartext = None
        if alt_blob is not None and alt_blob.blob is not None and ref in self._schluessel:
            klartext = self._entschluesseln(self._schluessel[ref], ref, alt_blob.blob)
        self._schluessel[ref] = AESGCM.generate_key(bit_length=256)
        if ref not in self._metadaten:
            self._metadaten[ref] = ts
        if ref not in self._inhalte:
            self._inhalte[ref] = _Eintrag(angelegt_ts=ts)
        if klartext is not None:
            self.ablegen(ref, klartext, ts)

    def ablegen(self, ref: str, klartext: str, ts: float) -> None:
        """Verschluesselt klartext unter dem Schluessel von ref. ref muss
        einen Schluessel haben (neuer_schluessel zuvor)."""
        schluessel = self._schluessel.get(ref)
        if schluessel is None:
            raise KeinSchluessel(ref)
        nonce = secrets.token_bytes(12)
        blob = nonce + AESGCM(schluessel).encrypt(nonce, klartext.encode(), ref.encode())
        eintrag = self._inhalte.setdefault(ref, _Eintrag(angelegt_ts=ts))
        eintrag.blob = blob
        self._metadaten.setdefault(ref, ts)

    def lesen(self, ref: str) -> str:
        """Wirft KeinSchluessel, wenn der Schluessel widerrufen/nie angelegt
        wurde -- unabhaengig davon, ob der Chiffretext noch existiert."""
        if ref not in self._schluessel:
            raise KeinSchluessel(ref)
        eintrag = self._inhalte.get(ref)
        if eintrag is None or eintrag.blob is None:
            raise KeinSchluessel(ref)
        return self._entschluesseln(self._schluessel[ref], ref, eintrag.blob)

    @staticmethod
    def _entschluesseln(schluessel: bytes, ref: str, blob: bytes) -> str:
        return AESGCM(schluessel).decrypt(blob[:12], blob[12:], ref.encode()).decode()

    def rotieren(self, ref: str, ts: float) -> None:
        """Neuer Schluessel, alter unbrauchbar, Inhalt bleibt lesbar."""
        if ref not in self._schluessel:
            raise KeinSchluessel(ref)
        self.neuer_schluessel(ref, ts)

    def widerrufen(self, ref: str) -> None:
        """Vernichtet NUR den Schluessel. Chiffretext und Metadaten (Kennung,
        Anlage-Zeitpunkt) bleiben unangetastet -- das ist Crypto-Shredding,
        kein Loeschen des Datensatzes."""
        self._schluessel.pop(ref, None)

    def sichern(self, ref: str) -> bytes:
        """Liefert den aktuellen Schluessel als Bytes an den Aufrufer, damit
        er ausserhalb dieses Speichers verwahrt werden kann (Backup fuer
        spaeteres wiederherstellen). Der Aufrufer gibt diesen Wert nie aus."""
        if ref not in self._schluessel:
            raise KeinSchluessel(ref)
        return self._schluessel[ref]

    def wiederherstellen(self, ref: str, schluessel: bytes, ts: float) -> None:
        """Setzt einen gesicherten Schluessel zurueck -- macht einen zuvor
        (durch widerrufen) unlesbaren Inhalt wieder lesbar, ohne den
        Chiffretext angefasst zu haben."""
        if ref not in self._inhalte:
            raise KeinSchluessel(ref)
        self._schluessel[ref] = schluessel
        self._metadaten.setdefault(ref, ts)

    def hat_bestanden(self, ref: str) -> bool:
        """Die Tatsache, dass es ref je gab -- unabhaengig vom Schluessel."""
        return ref in self._metadaten

    def angelegt_ts(self, ref: str) -> float:
        return self._metadaten[ref]

    def chiffretext_vorhanden(self, ref: str) -> bool:
        eintrag = self._inhalte.get(ref)
        return eintrag is not None and eintrag.blob is not None

    def chiffretext(self, ref: str) -> bytes | None:
        """Nur fuer Gegenproben (z. B. dass Vernichtung nicht heimlich auch
        den Chiffretext geloescht hat) -- kein Klartext, kein Schluessel."""
        eintrag = self._inhalte.get(ref)
        return eintrag.blob if eintrag else None


def _selftest() -> None:
    speicher = Kundenschluesselspeicher()
    ts0 = 1_000_000.0

    speicher.neuer_schluessel("K1", ts0)
    speicher.ablegen("K1", "geheimer Inhalt", ts0)
    assert speicher.lesen("K1") == "geheimer Inhalt"

    ct_vor_rotation = speicher.chiffretext("K1")
    speicher.rotieren("K1", ts0 + 1)
    assert speicher.lesen("K1") == "geheimer Inhalt", "Rotation darf Inhalt nicht verlieren"
    assert speicher.chiffretext("K1") != ct_vor_rotation, "Rotation muss neu verschluesseln"

    sicherung = speicher.sichern("K1")
    speicher.widerrufen("K1")
    try:
        speicher.lesen("K1")
        raise AssertionError("nach Widerruf haette lesen() scheitern muessen")
    except KeinSchluessel:
        pass
    assert speicher.chiffretext_vorhanden("K1"), "Widerruf darf den Chiffretext nicht loeschen"
    assert speicher.hat_bestanden("K1"), "Tatsache des Bestehens muss bleiben"

    speicher.wiederherstellen("K1", sicherung, ts0 + 2)
    assert speicher.lesen("K1") == "geheimer Inhalt", "Restore mit gesichertem Schluessel muss lesbar machen"

    print("kundenschluessel.py: Selbsttest gruen")


if __name__ == "__main__":
    import sys

    if "--selftest" in sys.argv:
        _selftest()
    else:
        print("Nutzung: python3 kern/kundenschluessel.py --selftest", file=sys.stderr)
        raise SystemExit(1)
