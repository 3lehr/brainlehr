import XCTest
@testable import BrainlehrCore

// I1: rot vor gruen -- vor diesem Auftrag gab es keine Funktion, die eine
// Anforderung gegen einen Katalog entschied; SeitenleistenEintrag.allCases
// zeigte "Dokument" unbedingt, unabhaengig davon, ob irgendeine Domaene ihn
// je angefordert hatte. Diese Tests pruefen die neue Entscheidung.
final class BestandteilAnforderungTests: XCTestCase {

    func testBekannterBestandteilMitErfuellterAuflageWirdGewaehrt() {
        let g = BestandteilAnforderung.gewaehrt(angefordert: ["dokumentfenster"])
        XCTAssertEqual(g, [.dokumentfenster])
    }

    func testUnbekannterBestandteilWirdVerworfen() {
        let g = BestandteilAnforderung.gewaehrt(angefordert: ["nichtdererfundene"])
        XCTAssertTrue(g.isEmpty)
    }

    func testZweimalDerselbeAngefordertWirdDedupliziert() {
        let g = BestandteilAnforderung.gewaehrt(angefordert: ["dokumentfenster", "dokumentfenster"])
        XCTAssertEqual(g, [.dokumentfenster])
    }

    // Grenzwert: bekannt, aber ADR-016 Auflage 3 offen.
    func testBestandteilMitUnerfuellterAuflageWirdVerweigert() {
        let g = BestandteilAnforderung.gewaehrt(angefordert: ["tabellenkalkulation"])
        XCTAssertTrue(g.isEmpty)
    }

    func testDomaeneOhneAngabeBekommtNichts() {
        let g = BestandteilAnforderung.gewaehrt(angefordert: [])
        XCTAssertTrue(g.isEmpty)
    }

    func testGemischteAnforderungNurGueltigerTeilLaedt() {
        let g = BestandteilAnforderung.gewaehrt(
            angefordert: ["dokumentfenster", "tabellenkalkulation", "unbekannt"])
        XCTAssertEqual(g, [.dokumentfenster])
    }
}
