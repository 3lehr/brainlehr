#!/usr/bin/env python3
"""Sagen, wie belastbar ein Suchergebnis ist -- statt es zu verschweigen.

DAS PROBLEM, gemessen am 2026-08-16 (Knoten cc458fb3): Bei 40 Anfragen, deren
Antwort nachweislich NICHT im Bestand liegt, meldete das System 40 Mal einen
Treffer. Der Zustand "dazu habe ich nichts" war nicht ausdrueckbar -- und
damit ist jede Trefferquote dieses Hauses zweideutig.

WARUM HIER NICHT GEFILTERT WIRD, und das ist die eigentliche Entscheidung:
Dieselbe Messung hat drei Schwellwerte geprueft (bester Kosinuswert, Abstand
zum Zweitbesten, Abstand zum Median). Alle drei ordnen 76 bis 80 Prozent der
Faelle richtig ein -- keiner trennt sauber, die Verteilungen ueberlappen fast
vollstaendig. Ein Filter kauft deshalb weniger Falschmeldungen mit VERLORENEN
Treffern: rund 8 statt 40 Falschmeldungen, aber nur noch rund 32 statt 37
gefundene von 40.

Ein Hinweis kostet das nicht. Er nimmt keinen Treffer weg, macht aber den
Zustand ausdrueckbar, den es bisher nicht gab. Wer spaeter doch filtern will,
hat mit `lage` bereits das Feld dafuer -- und dann eine Zahl, die er begruenden
muss.

REINE RECHNUNG: keine Datenbank, kein Netz, kein Modell. Damit ist die
Bewertung ohne Aufbau testbar -- und genau daran ist die erste Fassung dieser
Messung gescheitert (12 gegen 12 Faelle zeigten eine saubere Trennung, die bei
40 gegen 40 verschwand).
"""
from __future__ import annotations

# Aus der Messung vom 2026-08-16, nicht gesetzt: die besten Schwellen der drei
# Masse lagen bei 0,586 (bester Wert) und 0,043 (Abstand zum Zweitbesten).
# Sie stehen hier als GRENZE ZUR KENNZEICHNUNG, nicht als Filter -- ein
# Unterschied, der bei einer spaeteren Aenderung mitgelesen werden muss.
STARK_AB = 0.586
ABSTAND_AB = 0.043


def beurteile(werte: list[float]) -> dict:
    """`werte` sind die absteigend sortierten Kosinuswerte des Bedeutungskanals.

    Rueckgabe traegt drei Dinge: die Lage als Wort, die beiden Zahlen, aus
    denen sie folgt, und einen Satz FUER DEN NUTZER -- keine Kennzahl, keinen
    Feldnamen, keine Schwelle. Was er nicht in eine Entscheidung uebersetzen
    kann, gehoert ins Protokoll und nicht auf den Bildschirm."""
    if not werte:
        return {"lage": "ohne_bedeutungskanal", "bester": None, "abstand": None,
                "satz": ""}
    bester = float(werte[0])
    abstand = float(werte[0] - werte[1]) if len(werte) > 1 else 0.0

    # Zwei Zeichen muessen zusammenkommen: ein hoher bester Wert UND ein
    # sichtbarer Abstand zum naechsten. Ein hoher Wert allein bedeutet oft nur,
    # dass die Anfrage allgemein formuliert war -- dann aehneln ihr viele
    # Knoten gleich gut, und keiner davon ist die Antwort.
    if bester >= STARK_AB and abstand >= ABSTAND_AB:
        lage = "passend"
        satz = ""
    elif bester >= STARK_AB or abstand >= ABSTAND_AB:
        lage = "schwach"
        satz = "Dazu steht wenig Passendes im Bestand — die Treffer sind eher verwandt als einschlägig."
    else:
        lage = "nichts_passendes"
        satz = "Zu dieser Frage steht vermutlich nichts Passendes im Bestand."
    return {"lage": lage, "bester": round(bester, 4), "abstand": round(abstand, 4),
            "satz": satz}


def demo() -> None:
    """Selbsttest ohne Aufbau. Prueft die drei Lagen und die beiden Faelle,
    an denen die Regel haengt."""
    stark = beurteile([0.70, 0.60, 0.55])
    assert stark["lage"] == "passend" and stark["satz"] == "", stark

    # Hoher Wert, aber alles aehnelt gleich gut -- der Fall, den ein reiner
    # Schwellwert falsch einordnet.
    breit = beurteile([0.70, 0.699, 0.698])
    assert breit["lage"] == "schwach", breit

    # Deutlicher Abstand, aber insgesamt schwach.
    knapp = beurteile([0.50, 0.40, 0.39])
    assert knapp["lage"] == "schwach", knapp

    nichts = beurteile([0.45, 0.44, 0.43])
    assert nichts["lage"] == "nichts_passendes", nichts
    assert "Bestand" in nichts["satz"]

    # Keine Entwicklerinformation im Satz an den Nutzer (Hausregel).
    for lage in (stark, breit, knapp, nichts):
        for verboten in ("Kosinus", "Schwelle", "Embedding", "0.", "lage", "Feld"):
            assert verboten not in lage["satz"], (verboten, lage)

    assert beurteile([])["lage"] == "ohne_bedeutungskanal"
    assert beurteile([0.9])["abstand"] == 0.0, "ein einziger Treffer hat keinen Abstand"
    print("demo: ok")


if __name__ == "__main__":
    demo()
