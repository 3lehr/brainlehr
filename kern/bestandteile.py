"""kern/bestandteile.py -- Registrierung anforderbarer Bestandteile (I1,
PLAN_GESAMT_2026-08-13.md, ADR-014/016).

Bestandteil: gemeinsam gebaut, aber nicht jede Domaene braucht ihn
(ADR-014, Nachtrag "gemeinsam ist nicht dasselbe wie immer da"). Eine Domaene
fordert per eigenem Paket an, das atelier entscheidet: laden oder verweigern.

ENTWURFSFRAGE 1 -- WER FORDERT AN: die Domaene, im eigenen Paket. Optionales
Feld "bestandteile" (Liste von Namen) neben den Pflichtfeldern
"domaene"/"quellen"/"regeln" aus kern/domaene.py (TABU hier, nur gelesen:
pruefe() dort weist nur fehlende Pflichtfelder ab, ein unbekanntes Zusatzfeld
stoert die Pruefung nicht). kern/domaene.py bekommt dieses Feld absichtlich
NICHT beigebracht -- Bestandteile sind eine Darstellungsfrage (ADR-014), kein
Wissensvertrag, und die Pruefung dort ist bereits ein gepruefter Vertrag mit
dem atelier (siehe Kommentar "test_vertrag_gegen_das_atelier_haelt" dort).
Das atelier liest "bestandteile" darum LOKAL aus dem ohnehin schon geparsten
Paket (app/Sources/Atelier/DomaeneImportDienst.swift) -- kein zweiter Umweg
ueber den Dienst.

ENTWURFSFRAGE 2 -- UNBEKANNT ODER NICHT DA: verweigern, ohne laden. Kein
Fehler, keine Entwicklerinformation. Ein Bestandteil, den der Katalog nicht
fuehrt, existiert fuer die Anforderung schlicht nicht -- dieselbe Haltung wie
kern/domaene.py bei einer beschaedigten Paketdatei (_abgelehnt(), nie ein
geworfener Fehler).

ENTWURFSFRAGE 3 -- AUFLAGEN (ADR-016): sie sind eine Eigenschaft des
BESTANDTEILS, nicht der anfordernden Domaene, und stehen deshalb hier im
Katalog, fest verdrahtet -- nicht im Domaenenpaket, wo eine Domaene sie sich
selbst haette guenstig setzen koennen. Geprueft wird beim GEWAEHREN
(gewaehrt() unten), also bevor irgendetwas laedt -- nicht erst beim
tatsaechlichen Laden. Ein Bestandteil mit unerfuellter Auflage kommt so nie
bis zur Ladestelle, es gibt dort nichts mehr zu pruefen und nichts zu
vergessen.

ENTWURFSFRAGE 4 -- RECHTEFRAGE: eine Domaene kann sich damit KEINE Rechte
selbst geben. Sie waehlt nur Namen aus einem geschlossenen, hier fest
verdrahteten Katalog; die Auflage jedes Eintrags ist Code, nicht Eingabe.
Anfordern schaltet die Sichtbarkeit einer bereits vorhandenen, bereits
geprueften Faehigkeit frei -- es parametrisiert und erweitert sie nicht.
Gepruefte Gegenprobe: wuerde der Auflagenstatus aus dem Domaenenpaket
gelesen statt aus KATALOG, koennte jede Domaene ihn faelschen. Er wird
absichtlich NICHT von dort gelesen.

Vertrag mit app/Sources/BrainlehrCore/BestandteilRegistry.swift: dieselben
Namen, dieselbe Auflagen-Entscheidung. tests/test_bestandteile.py::
test_namen_stimmen_mit_swift_ueberein haelt beide Fassungen zusammen, damit
sie nicht wie zwei getrennte Wahrheiten auseinanderlaufen.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BestandteilEintrag:
    auflagen_erfuellt: bool
    grund: str  # nur fuers Protokoll -- nie woertlich an den Nutzer


KATALOG: dict[str, BestandteilEintrag] = {
    "dokumentfenster": BestandteilEintrag(
        auflagen_erfuellt=True,
        grund="ADR-010, gebaut (F1-F5), keine offene Auflage.",
    ),
    "tabellenkalkulation": BestandteilEintrag(
        auflagen_erfuellt=True,
        grund=(
            "ADR-016 Auflage 3 gemessen+aufgehoben (2026-08-15T14:10:23+0200) "
            "und Auflage 1/2 (Positivliste) im Spike gebaut und belegt "
            "(spikes/univer_i3_min/probe4, tests/test_univer_positivliste.py: "
            "verfuegbare Funktionsmenge == erlaubte Menge, WEBSERVICE und eine "
            "abgemeldete echte Funktion ergeben #NAME?). Auflage 4 (benannte "
            "Bereiche) ist eine Bauvorschrift fuer den kommenden Bildschirm, "
            "keine Ladebedingung -- sie steht unveraendert in ADR-016."
        ),
    ),
}


def gewaehrt(angefordert: list[str]) -> list[str]:
    """Aus einer Anforderungsliste die Namen, die laden DUERFEN --
    dedupliziert, in Katalogreihenfolge. Unbekannte Namen und Eintraege mit
    unerfuellter Auflage werden stillschweigend verworfen (siehe Moduldoc,
    Entwurfsfrage 2)."""
    angefordert_menge = set(angefordert)
    return [
        name
        for name, eintrag in KATALOG.items()
        if name in angefordert_menge and eintrag.auflagen_erfuellt
    ]


__all__ = ["BestandteilEintrag", "KATALOG", "gewaehrt"]
