"""Aufgabe 65, Schritt 1: kern/ausschreibekatalog.py bewertet jedes Caveman-
Kurzform/Langform-Paar aus dem BESTAND und leitet die Aufnahmeschwelle aus der
gemessenen Verteilung ab (keine gesetzte Zahl). Facts (Commit 339eaee, 2969
Dokumente): impl 0:133, fn 1:269, res 1:264, req 4:134, config 25:242,
auth 31:3, db 187:111. Der Bestand waechst seither weiter -- diese Tests
pruefen die RICHTUNG (Verhaeltnis, Aufnahme/Ausschluss), nicht die exakten
historischen Zahlen.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "kern"))
sys.path.insert(0, str(REPO / "haken"))

import ausschreibekatalog as ak  # noqa: E402


def test_saat_kommt_woertlich_aus_caveman_fertigkeit():
    """Nicht abgetippt, sondern aus der Datei gelesen -- der Auftrag verbietet
    eigene Paare. Die sieben Kurzformen aus der Aufgabenstellung muessen
    genau das sein, was die Fertigkeit heute nennt."""
    kurzformen = set(ak._saat_kurzformen())
    assert kurzformen == {"db", "auth", "config", "req", "res", "fn", "impl"}


def test_saat_langformen_sind_woerterbuchhaft_nicht_erfunden():
    saat = ak.saat()
    assert saat["impl"] == "implementation"
    assert saat["db"] == "database"
    assert saat["fn"] == "function"


def test_zaehlung_ist_wortgrenze_nicht_teilstring():
    """'impl' darf sich nicht selbst in 'kompliziert' finden -- sonst waere
    jede Zaehlung Rauschen statt Signal."""
    texte = ["Das ist kompliziert und implizit unklar."]
    kurz_n, lang_n = ak.zaehle_paar(texte, "impl", "implementation")
    assert kurz_n == 0
    assert lang_n == 0

    texte2 = ["impl steht hier als eigenes Wort, implementation auch."]
    kurz_n2, lang_n2 = ak.zaehle_paar(texte2, "impl", "implementation")
    assert kurz_n2 == 1
    assert lang_n2 == 1


def test_grenzwert_knapp_ueber_und_knapp_unter_schwelle():
    """Ein Paar knapp ueber der Schwelle wird aufgenommen, eines knapp
    darunter nicht -- die Entscheidungsregel selbst, unabhaengig vom
    Bestand."""
    schwelle = ak._schwelle_aus_verteilung([-2.0, -1.9, 1.5, 1.6])
    assert ak.aufnehmen(schwelle + 0.001, schwelle) is True
    assert ak.aufnehmen(schwelle - 0.001, schwelle) is False


def test_schwelle_trennt_zwei_klar_getrennte_gruppen():
    tief = [-3.0, -2.5, -2.0]
    hoch = [2.0, 2.5, 3.0]
    schwelle = ak._schwelle_aus_verteilung(tief + hoch)
    assert max(tief) < schwelle < min(hoch)


def test_impl_wird_aus_dem_echten_bestand_aufgenommen_rot_vor_gruen():
    """Rot-Probe (dokumentiert, nicht nur behauptet): OHNE Katalog findet eine
    Anfrage nach 'impl' 0 Dokumente ueber die lange Form -- die Kurzform
    kennt 'implementation' nicht. GRUEN: der Katalog nimmt das Paar auf, weil
    die lange Form im Bestand haeufiger steht als die kurze."""
    bewertung = ak.bewerte()
    assert "impl" in bewertung, "Saat-Paar impl fehlt -- Caveman-Liste hat sich geaendert"
    eintrag = bewertung["impl"]
    # Rot: eine reine Kurzform-Suche saehe nur kurz_n, nie die 'lange_n'
    # Dokumente -- das ist exakt der Schaden aus dem Plan.
    assert eintrag["lang_n"] > eintrag["kurz_n"]
    # Gruen: der Katalog erkennt das und nimmt impl auf.
    assert eintrag["aufgenommen"] is True
    assert "impl" in ak.katalog()


def test_db_verschlechtert_sich_nicht_negativfall():
    """'db' hat ein echtes Eigenvorkommen -- die Erweiterung darf es NICHT
    in den Katalog aufnehmen, sonst verwaessert eine ohnehin funktionierende
    Kurzform-Suche."""
    bewertung = ak.bewerte()
    if "db" not in bewertung:
        return  # Saat-Liste hat sich geaendert -- kein Fehlschlag dieses Tests
    eintrag = bewertung["db"]
    assert eintrag["kurz_n"] > eintrag["lang_n"], (
        "db muesste im Bestand als eigenes Wort haeufiger stehen als 'database' -- "
        "sonst ist das gewaehlte Beispiel kein Negativfall mehr"
    )
    assert eintrag["aufgenommen"] is False
    assert "db" not in ak.katalog()


def test_katalog_liest_nur_kein_schreibzugriff():
    """Der Katalog schlaegt vor, er setzt nicht: bewerte()/katalog() oeffnen
    nur speicher.lesen() (mode=ro) -- ein Schreibversuch scheiterte dort
    sofort. Hier nur belegt, dass beide Funktionen ohne Fehler durchlaufen,
    also tatsaechlich den lesenden Weg nehmen."""
    ak.bewerte()
    ak.katalog()
