// Prueft die Bedienung des Wissensraums als Fachlogik -- die Einteilung nach
// Zweck, die Sichtbarkeit je Blick, das Klemmen und die Zahlform.
//
// Die teure Fehlerklasse hier ist nicht "Regler fehlt", sondern "Regler ist da
// und bewirkt nichts": ein Schieberegler, der in diesem Blick keine Wirkung
// hat, behauptet eine Einstellmoeglichkeit, die es nicht gibt. Darum prueft
// jeder Positivfall unten seinen Negativfall mit.

import XCTest
@testable import BrainlehrCore

final class WissensraumreglerTests: XCTestCase {

    // MARK: Einteilung nach Zweck

    func testJederReglerHatGenauEinenZweck() {
        for regler in Wissensraumregler.alle {
            XCTAssertTrue(Wissensraumregler.Zweck.allCases.contains(regler.zweck),
                          "\(regler.id) traegt keinen bekannten Zweck")
        }
        // Beide Seiten sind besetzt -- waere eine leer, waere die Trennung
        // Papier.
        XCTAssertFalse(Wissensraumregler.fuer(blick: Wissensraumregler.abrufweg,
                                              zweck: .gegenstand).isEmpty)
        XCTAssertFalse(Wissensraumregler.fuer(blick: Wissensraumregler.abrufweg,
                                              zweck: .darstellung).isEmpty)
    }

    func testKennungenSindEindeutig() {
        let ids = Wissensraumregler.alle.map(\.id)
        XCTAssertEqual(Set(ids).count, ids.count, "doppelte Regler-Kennung: \(ids)")
    }

    // MARK: Sichtbarkeit je Blick -- Positiv- und Negativfall

    func testZeitleisteFehltBeimAbrufweg() {
        let imBaum = Wissensraumregler.fuer(blick: Wissensraumregler.baum).map(\.id)
        XCTAssertTrue(imBaum.contains("zeit"), "Zeit gehoert in den Baum-Blick")

        let imAbrufweg = Wissensraumregler.fuer(blick: Wissensraumregler.abrufweg).map(\.id)
        XCTAssertFalse(imAbrufweg.contains("zeit"),
                       "die Seite zeigt beim Abrufweg keine Zeitleiste -- ein Regler ohne "
                       + "Wirkung behauptet eine Einstellmoeglichkeit, die es nicht gibt")
    }

    func testTaktungNurBeimAbrufweg() {
        XCTAssertTrue(Wissensraumregler.fuer(blick: Wissensraumregler.abrufweg)
            .map(\.id).contains("reglerTaktung"))
        for blick in [Wissensraumregler.baum, .init(1), 2, 3] {
            XCTAssertFalse(Wissensraumregler.fuer(blick: blick).map(\.id).contains("reglerTaktung"),
                           "Taktung darf in Blick \(blick) nicht auftauchen")
        }
    }

    func testDarstellungNurDortWoEsWelcheGibt() {
        XCTAssertTrue(Wissensraumregler.hatDarstellung(blick: Wissensraumregler.abrufweg))
        // Negativfall: in den vier anderen Blicken gibt es nichts aufzuklappen,
        // also darf auch kein leeres Aufklappelement erscheinen.
        for blick in [0, 1, 2, 3] {
            XCTAssertFalse(Wissensraumregler.hatDarstellung(blick: blick),
                           "Blick \(blick) haette ein leeres Aufklappelement")
        }
    }

    // MARK: Klemmen -- Grenzwerte beidseitig

    func testKlemmeAnDenGrenzen() {
        guard let helligkeit = Wissensraumregler.alle.first(where: { $0.id == "reglerHelligkeit" })
        else { return XCTFail("Regler reglerHelligkeit fehlt") }

        XCTAssertEqual(helligkeit.klemme(0.4), 0.4, accuracy: 1e-9)   // genau an der Grenze
        XCTAssertEqual(helligkeit.klemme(1.0), 1.0, accuracy: 1e-9)
        XCTAssertEqual(helligkeit.klemme(0.39), 0.4, accuracy: 1e-9)  // darunter
        XCTAssertEqual(helligkeit.klemme(1.01), 1.0, accuracy: 1e-9)  // darueber
        XCTAssertEqual(helligkeit.klemme(-99), 0.4, accuracy: 1e-9)
    }

    func testVorgabeLiegtImmerInDenGrenzen() {
        for regler in Wissensraumregler.alle {
            XCTAssertEqual(regler.klemme(regler.vorgabe), regler.vorgabe, accuracy: 1e-9,
                           "Vorgabe von \(regler.id) liegt ausserhalb der eigenen Grenzen")
            XCTAssertLessThan(regler.von, regler.bis, "\(regler.id): leere Spanne")
        }
    }

    // MARK: Das erzeugte Skript

    func testSkriptSchreibtGeklemmtenWertUndLoestInputAus() {
        guard let puls = Wissensraumregler.alle.first(where: { $0.id == "reglerPulsstaerke" })
        else { return XCTFail("Regler reglerPulsstaerke fehlt") }

        let skript = Wissensraumregler.skript(fuer: puls, wert: 99)
        XCTAssertTrue(skript.contains("getElementById('reglerPulsstaerke')"))
        XCTAssertTrue(skript.contains("new Event('input'"),
                      "ohne input-Ereignis rechnet die Seite nicht neu")
        XCTAssertTrue(skript.contains("e.value = '0.3500'"),
                      "der Wert muss VOR dem Schreiben geklemmt sein, sonst stehen native "
                      + "und Web-Seite danach auf verschiedenen Zahlen: \(skript)")
        XCTAssertFalse(skript.contains("99"), "ungeklemmter Wert im Skript: \(skript)")
    }

    func testZahlformOhneKommaUndOhneExponent() {
        // Ein deutsches Dezimalkomma waere im DOM ungueltig und faellt dort
        // stumm auf den alten Wert zurueck -- der Regler saehe bewegt aus und
        // waere es nicht.
        XCTAssertEqual(Wissensraumregler.zahl(0.83), "0.8300")
        XCTAssertEqual(Wissensraumregler.zahl(3200), "3200")
        XCTAssertEqual(Wissensraumregler.zahl(0), "0")
        XCTAssertFalse(Wissensraumregler.zahl(0.0001).contains("e"))
    }

    func testFehlendesElementWirdGemeldetStattStillZuScheitern() {
        guard let zeit = Wissensraumregler.alle.first(where: { $0.id == "zeit" })
        else { return XCTFail("Regler zeit fehlt") }
        XCTAssertTrue(Wissensraumregler.skript(fuer: zeit, wert: 50).contains("return 'fehlt'"),
                      "ein fehlendes Element muss sich melden -- sonst sieht ein stiller "
                      + "Fehlschlag wie eine wirkungslose Einstellung aus")
    }

    // MARK: Beschriftung

    func testBeschriftungTraegtDieEinheit() {
        let erwartet: [String: String] = [
            "zeit": "100 %",
            "reglerTaktung": "15 s",
            "reglerHelligkeit": "0.83",
            "reglerPulsstaerke": "0.13",
            "reglerPulsdauer": "3200 ms",
            "reglerNachleuchten": "4.0 s",
        ]
        for regler in Wissensraumregler.alle {
            XCTAssertEqual(regler.beschriftung(regler.vorgabe), erwartet[regler.id],
                           "Beschriftung von \(regler.id)")
        }
    }

    // MARK: Ausblenden der Web-Leiste

    func testWebleisteAusblendenTrifftTafelUndKlappknopf() {
        let skript = Wissensraumregler.webleisteAusblenden
        XCTAssertTrue(skript.contains("'tafel'"))
        XCTAssertTrue(skript.contains("'klapper'"),
                      "der Klappknopf blendet eine Leiste ein, die es nicht mehr gibt")
    }

    // MARK: Eingabe und Aktionen

    func testAblaufWirktUeberallVorfuehrenNurBeimAbrufweg() {
        for blick in [0, 1, 2, 3, 4] {
            XCTAssertTrue(Wissensraumregler.schalter(blick: blick).map(\.id).contains("lauf"),
                          "Ablauf fehlt in Blick \(blick)")
        }
        XCTAssertTrue(Wissensraumregler.schalter(blick: Wissensraumregler.abrufweg)
            .map(\.id).contains("abrufwegVorfuehren"))
        for blick in [0, 1, 2, 3] {
            XCTAssertFalse(Wissensraumregler.schalter(blick: blick).map(\.id).contains("abrufwegVorfuehren"),
                           "Vorfuehren darf in Blick \(blick) nicht auftauchen -- die Seite blendet "
                           + "seine Leiste dort aus")
        }
    }

    func testAnfrageNurBeimAbrufweg() {
        XCTAssertTrue(Wissensraumregler.hatAnfrage(blick: Wissensraumregler.abrufweg))
        for blick in [0, 1, 2, 3] {
            XCTAssertFalse(Wissensraumregler.hatAnfrage(blick: blick))
        }
    }

    func testSchalterSkriptGibtDenErreichtenZustandZurueck() {
        let skript = Wissensraumregler.skript(fuerSchalter: "lauf")
        XCTAssertTrue(skript.contains("e.click()"))
        XCTAssertTrue(skript.contains("aria-pressed"),
                      "ohne den erreichten Zustand ist ein wirkungsloser Klick von einem "
                      + "wirksamen nicht zu unterscheiden")
        XCTAssertTrue(skript.contains("return 'fehlt'"))
    }

    func testAnfrageMitApostrophBleibtHeil() {
        // Eine Anfrage mit Apostroph ist zulaessig. Wer sie stillschweigend
        // verstuemmelt, erzeugt ein Ergebnis zur falschen Frage -- und wer sie
        // roh einsetzt, baut eine Skriptluecke.
        let skript = Wissensraumregler.skript(fuerAnfrage: "Dichtung's \"Leck\" \\ Ende")
        XCTAssertTrue(skript.contains("requestSubmit"))
        XCTAssertFalse(skript.contains("feld.value = 'Dichtung's"),
                       "roh eingesetzter Apostroph bricht das Skript: \(skript)")
        XCTAssertTrue(skript.contains("\\\"Leck\\\""), skript)
    }

    func testLeereAnfrageErzeugtGueltigesSkript() {
        // Grenzwert: leerer Text. Muss ein gueltiges Skript ergeben, nicht
        // eines, das im Browser mit einem Syntaxfehler stirbt.
        let skript = Wissensraumregler.skript(fuerAnfrage: "")
        XCTAssertTrue(skript.contains("feld.value = \"\""), skript)
    }
}
