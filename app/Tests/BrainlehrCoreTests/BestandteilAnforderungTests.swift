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

    // Grenzwert: bekannt, aber Auflage offen -> verweigert.
    //
    // BERICHTIGT 2026-08-16: Dieser Test stand auf "tabellenkalkulation wird
    // verweigert" und war seit be74c1c1 (2026-08-15) ROT -- dort wurde die
    // letzte offene Auflage gemessen und aufgehoben, die Swift-Seite auf
    // true gezogen und die Erwartung hier nicht nachgeholt. Rot war also die
    // veraltete ERWARTUNG, nicht der Code.
    //
    // Geprueft wird jetzt gegen einen EINGESETZTEN Katalog statt gegen den
    // Produktivkatalog: in dem steht seit be74c1c1 kein Eintrag mit
    // unerfuellter Auflage mehr, und ein Negativfall ohne Vertreter prueft
    // nichts. Die Regel bleibt damit pruefbar, auch wenn alle echten
    // Auflagen erfuellt sind.
    func testBestandteilMitUnerfuellterAuflageWirdVerweigert() {
        let g = BestandteilAnforderung.gewaehrt(
            angefordert: ["tabellenkalkulation"],
            katalog: [.tabellenkalkulation: BestandteilEintrag(auflagenErfuellt: false)])
        XCTAssertTrue(g.isEmpty)
    }

    /// Gegenrichtung zum vorigen Fall: derselbe Bestandteil, Auflage erfuellt
    /// -> gewaehrt. Ohne diese Zeile wuerde ein `gewaehrt`, das IMMER leer
    /// zurueckgibt, den Negativfall bestehen.
    func testBestandteilMitErfuellterAuflageWirdGewaehrt() {
        let g = BestandteilAnforderung.gewaehrt(angefordert: ["tabellenkalkulation"])
        XCTAssertEqual(g, [.tabellenkalkulation])
    }

    func testDomaeneOhneAngabeBekommtNichts() {
        let g = BestandteilAnforderung.gewaehrt(angefordert: [])
        XCTAssertTrue(g.isEmpty)
    }

    // BERICHTIGT 2026-08-16, gleiche Ursache: "unbekannt" faellt weiterhin
    // heraus, "tabellenkalkulation" seit be74c1c1 nicht mehr.
    func testGemischteAnforderungNurGueltigerTeilLaedt() {
        let g = BestandteilAnforderung.gewaehrt(
            angefordert: ["dokumentfenster", "tabellenkalkulation", "unbekannt"])
        XCTAssertEqual(g, [.dokumentfenster, .tabellenkalkulation])
    }
}
