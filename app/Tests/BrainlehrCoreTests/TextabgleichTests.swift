// Prueft die Differenzrechnung des Dokumentfensters.
//
// Die teure Fehlerklasse ist hier eine STILLE: eine Position, die um ein paar
// Bytes danebenliegt, macht den Text nicht kaputt -- sie verschiebt ihn. Beim
// Tippen faellt das kaum auf, bei gleichzeitiger Bearbeitung wird daraus ein
// Zeichensalat, den niemand mehr einer Ursache zuordnen kann. Darum steht
// jeder Fall hier zusaetzlich als Rundlauf: Aenderung anwenden muss `neu`
// ergeben.

import XCTest
@testable import BrainlehrCore

final class TextabgleichTests: XCTestCase {

    /// Jeder Fall wird zweimal geprueft: die erwartete Aenderung UND dass ihre
    /// Anwendung tatsaechlich beim Ziel landet.
    private func pruefe(_ alt: String, _ neu: String,
                        bei: UInt32, geloescht: UInt32, eingefuegt: String,
                        datei: StaticString = #filePath, zeile: UInt = #line) {
        let a = Textabgleich.aenderung(von: alt, nach: neu)
        XCTAssertEqual(a, Textabgleich.Aenderung(bei: bei, geloescht: geloescht, eingefuegt: eingefuegt),
                       "Aenderung \(alt.debugDescription) -> \(neu.debugDescription)",
                       file: datei, line: zeile)
        XCTAssertEqual(Textabgleich.wendeAn(a, auf: alt), neu,
                       "Rundlauf misslungen", file: datei, line: zeile)
    }

    // MARK: Die alltaeglichen Faelle

    func testEinfuegenAmEnde() {
        pruefe("Hallo", "Hallo Welt", bei: 5, geloescht: 0, eingefuegt: " Welt")
    }

    func testEinfuegenInDerMitte() {
        pruefe("Hallo Welt", "Hallo schoene Welt", bei: 6, geloescht: 0, eingefuegt: "schoene ")
    }

    func testEinfuegenAmAnfang() {
        pruefe("Welt", ">> Welt", bei: 0, geloescht: 0, eingefuegt: ">> ")
    }

    func testLoeschenEinesZeichens() {
        pruefe("Hallo", "Hall", bei: 4, geloescht: 1, eingefuegt: "")
    }

    func testErsetzen() {
        pruefe("Hallo Welt", "Hallo Erde", bei: 6, geloescht: 4, eingefuegt: "Erde")
    }

    // MARK: Grenzwerte

    func testGleicherTextErzeugtKeineAenderung() {
        let a = Textabgleich.aenderung(von: "unveraendert", nach: "unveraendert")
        XCTAssertTrue(a.istLeer,
                      "ein Update ohne Inhalt weckt bei jedem anderen Teilnehmer eine Neuzeichnung")
    }

    func testVonLeerNachVoll() {
        pruefe("", "Erster Satz.", bei: 0, geloescht: 0, eingefuegt: "Erster Satz.")
    }

    func testVonVollNachLeer() {
        pruefe("alles weg", "", bei: 0, geloescht: 9, eingefuegt: "")
    }

    func testGanzErsetzt() {
        pruefe("abc", "xyz", bei: 0, geloescht: 3, eingefuegt: "xyz")
    }

    // MARK: Mehrbyte -- der stille Fehler

    func testUmlautWirdInBytesGezaehltNichtInZeichen() {
        // "Grüße" ist 5 Zeichen, aber 7 UTF-8-Bytes. Wer in Zeichen rechnet,
        // setzt hier um zwei Stellen daneben -- und der Text ist danach nur
        // verschoben, nicht kaputt, also faellt es nicht auf.
        let a = Textabgleich.aenderung(von: "Grüße", nach: "Grüße!")
        XCTAssertEqual(a.bei, 7, "Position muss in UTF-8-Bytes zaehlen, nicht in Zeichen")
        XCTAssertEqual(Textabgleich.wendeAn(a, auf: "Grüße"), "Grüße!")
    }

    func testAenderungMittenImMehrbytezeichenTrenntNichtFalsch() {
        // ä (C3 A4) -> ö (C3 B6): das erste Byte ist gleich. Wuerde dort
        // getrennt, entstuende ungueltiges UTF-8.
        let a = Textabgleich.aenderung(von: "Bär", nach: "Bör")
        XCTAssertEqual(Textabgleich.wendeAn(a, auf: "Bär"), "Bör")
        XCTAssertFalse(a.eingefuegt.isEmpty)
        // Die eingefuegte Zeichenkette muss fuer sich gueltig sein.
        XCTAssertEqual(a.eingefuegt.utf8.count, Array(a.eingefuegt.utf8).count)
    }

    func testEmojiUeberlebt() {
        let a = Textabgleich.aenderung(von: "Fertig", nach: "Fertig 🎉")
        XCTAssertEqual(Textabgleich.wendeAn(a, auf: "Fertig"), "Fertig 🎉")
    }

    func testEmojiInDerMitteEntfernt() {
        pruefeRundlauf("vor 🎉 nach", "vor  nach")
    }

    // MARK: Zufaellige Faelle -- der Rundlauf muss immer halten

    func testRundlaufUeberVieleFaelle() {
        let stuecke = ["a", "ä", "🎉", " ", "Satz", "\n", "ß"]
        var zaehler = 0
        for i in 0..<stuecke.count {
            for j in 0..<stuecke.count {
                for k in 0..<stuecke.count {
                    let alt = stuecke[i] + stuecke[j]
                    let neu = stuecke[i] + stuecke[k] + stuecke[j]
                    pruefeRundlauf(alt, neu)
                    pruefeRundlauf(neu, alt)
                    zaehler += 2
                }
            }
        }
        XCTAssertGreaterThan(zaehler, 600, "zu wenige Faelle geprueft")
    }

    private func pruefeRundlauf(_ alt: String, _ neu: String,
                                datei: StaticString = #filePath, zeile: UInt = #line) {
        let a = Textabgleich.aenderung(von: alt, nach: neu)
        XCTAssertEqual(Textabgleich.wendeAn(a, auf: alt), neu,
                       "Rundlauf \(alt.debugDescription) -> \(neu.debugDescription)",
                       file: datei, line: zeile)
    }
}
