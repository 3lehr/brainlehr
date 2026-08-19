#!/usr/bin/env python3
"""risikoeinstufung.py -- eine Einstufung, zwei Wirkungen (E18 + U06).

Eine Risikoeinstufung, zwei Abnehmer:

E18: Regelrang, Export, Connector, Providerwechsel, Ausnahme, Hold sind
VORGANGSARTEN. Die Einstufung entscheidet, ob ein Vorgang ein zweites
Augenpaar braucht (`pruefe_vier_augen`). "Selektiv" heisst: hoch gated,
niedrig nicht -- beides ablesbar in `_VORGANG_STUFE`, nicht verteilt im Code.

U06: Konflikt, Ablauf, Quellenluecke, Policy-Denial sind EREIGNISARTEN. Die-
selbe Einstufung entscheidet den Kanal (`melde`). Ohne Inhaltsleck heisst:
die Meldung traegt WAS und WO, nie den betroffenen Inhalt -- `melde()` nimmt
deshalb nur `objekt_kennung` entgegen, nie den Inhalt selbst.

Kanal ist hier eine benannte Senke (Liste in einem dict), kein Netzzugriff,
kein Versand -- die Auftragszeile verlangt nicht mehr.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Stufe(Enum):
    NIEDRIG = "niedrig"
    HOCH = "hoch"


class VierAugenErforderlich(Exception):
    """Ein hoch eingestufter Vorgang ohne zweites Augenpaar wird abgewiesen."""


# E18: Vorgangsart -> Stufe. Begruendung steht daneben, nicht im Kopf.
_VORGANG_STUFE: dict[str, Stufe] = {
    # aendert Rangfolge/Ausgang kuenftiger Entscheidungen -> hoch
    "regelrang": Stufe.HOCH,
    # verlaesst das System -> hoch
    "export": Stufe.HOCH,
    # neue Aussenverbindung -> hoch
    "connector": Stufe.HOCH,
    # wechselt den Verarbeiter fremder Daten -> hoch
    "providerwechsel": Stufe.HOCH,
    # hebt eine bestehende Regel fuer einen Fall auf -> hoch
    "ausnahme": Stufe.HOCH,
    # HOLD HAT ZWEI RICHTUNGEN, und nur eine davon ist harmlos.
    # Befund 2026-08-19: Hier stand `"hold": Stufe.NIEDRIG` als EINE
    # Vorgangsart. Der Code kennt die Trennung laengst --
    # kern/kundenschluessel.py:128 `rechtssperre_setzen` und :138
    # `rechtssperre_aufheben`. Setzen schuetzt Daten vor Vernichtung und ist
    # folgenlos, wenn es zu Unrecht geschieht. Aufheben gibt sie zur
    # Vernichtung frei -- und `kundenschluessel.widerrufen()` wirft heute
    # NUR, solange die Sperre steht. Wer sie aufhebt, oeffnet damit einen
    # unumkehrbaren Weg.
    #
    # Die grobe Einstufung haette also ausgerechnet die gefaehrliche Richtung
    # ungegatet gelassen, waehrend die harmlose die Einstufung traegt. Das AC
    # verlangt "korrekt gegatet", nicht "eingestuft".
    #
    # Gefunden beim Lesen der Tabelle, nicht durch einen Test: die
    # Klassifikation IST die Zusicherung, gegen die geprueft wird -- kein Test
    # kann sie widerlegen.
    "hold_setzen": Stufe.NIEDRIG,
    "hold_aufheben": Stufe.HOCH,
}

# U06: Ereignisart -> Stufe. Gleiche Tabelle, gleiche Herkunft der Einstufung.
_EREIGNIS_STUFE: dict[str, Stufe] = {
    # zwei Quellen widersprechen sich -> hoch (kann Fehlentscheidung erzeugen)
    "konflikt": Stufe.HOCH,
    # eine Freigabe/Frist ist ausgelaufen -> niedrig (planbar, kein Ueberraschungsmoment)
    "ablauf": Stufe.NIEDRIG,
    # eine erwartete Quelle fehlt -> niedrig (Luecke, kein Fehlverhalten)
    "quellenluecke": Stufe.NIEDRIG,
    # eine Regel hat aktiv verweigert -> hoch (moeglicher Policy-Umgehungsversuch)
    "policy_denial": Stufe.HOCH,
}

# Kanal je Stufe. Eine benannte Senke, keine Infrastruktur.
_KANAL_JE_STUFE: dict[Stufe, str] = {
    Stufe.HOCH: "eskalation",
    Stufe.NIEDRIG: "protokoll",
}


def stufe_vorgang(vorgangsart: str) -> Stufe:
    """E18: Einstufung einer Vorgangsart. KeyError bei unbekannter Art (kein stilles Raten)."""
    return _VORGANG_STUFE[vorgangsart]


def stufe_ereignis(ereignisart: str) -> Stufe:
    """U06: Einstufung einer Ereignisart."""
    return _EREIGNIS_STUFE[ereignisart]


def pruefe_vier_augen(vorgangsart: str, *, zweites_augenpaar: str | None) -> Stufe:
    """E18: gibt die Stufe zurueck, wirft bei hoch ohne zweites Augenpaar.

    `zweites_augenpaar` ist die Kennung der pruefenden Person/Rolle, nicht der
    Vorgang selbst -- None/leer heisst "kein zweites Augenpaar vorhanden".
    """
    stufe = stufe_vorgang(vorgangsart)
    if stufe is Stufe.HOCH and not zweites_augenpaar:
        raise VierAugenErforderlich(
            f"Vorgangsart '{vorgangsart}' ist hoch eingestuft und braucht ein zweites Augenpaar."
        )
    return stufe


@dataclass
class Meldung:
    ereignisart: str
    stufe: Stufe
    kanal: str
    objekt_kennung: str
    text: str


_SENKEN: dict[str, list[Meldung]] = {}


def melde(ereignisart: str, objekt_kennung: str) -> Meldung:
    """U06: routet eine Ereignisart nach Stufe in einen Kanal.

    Nimmt bewusst KEINEN Inhalt/Text des betroffenen Eintrags entgegen --
    nur seine Kennung (z.B. eine ID). Der Meldungstext wird aus Ereignisart
    und Kennung gebaut, nie aus Inhalt.
    """
    stufe = stufe_ereignis(ereignisart)
    kanal = _KANAL_JE_STUFE[stufe]
    text = f"{ereignisart} bei {objekt_kennung}"
    meldung = Meldung(ereignisart, stufe, kanal, objekt_kennung, text)
    _SENKEN.setdefault(kanal, []).append(meldung)
    return meldung


def senke_lesen(kanal: str) -> list[Meldung]:
    """Test-/Betriebszugriff auf eine Senke."""
    return list(_SENKEN.get(kanal, []))


def demo() -> None:
    assert stufe_vorgang("export") is Stufe.HOCH
    assert stufe_vorgang("hold_setzen") is Stufe.NIEDRIG
    # Die riskante Richtung MUSS gegatet sein -- sonst waere die
    # Einstufung wieder so grob wie vor dem 2026-08-19.
    assert stufe_vorgang("hold_aufheben") is Stufe.HOCH
    try:
        pruefe_vier_augen("export", zweites_augenpaar=None)
        raise AssertionError("haette werfen muessen")
    except VierAugenErforderlich:
        pass
    assert pruefe_vier_augen("hold_setzen", zweites_augenpaar=None) is Stufe.NIEDRIG
    try:
        pruefe_vier_augen("hold_aufheben", zweites_augenpaar=None)
        raise AssertionError("hold_aufheben ohne zweites Augenpaar kam durch")
    except VierAugenErforderlich:
        pass
    m = melde("konflikt", "eintrag-123")
    assert "eintrag-123" in m.text
    assert m.kanal == "eskalation"
    print("ok")


if __name__ == "__main__":
    demo()
