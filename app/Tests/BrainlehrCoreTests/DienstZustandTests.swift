import XCTest
@testable import BrainlehrCore

final class DienstZustandTests: XCTestCase {

    // Aufstart: solange nicht erreichbar, bleibt es "startetGerade" -- das ist
    // KEIN unerwartetes Ende, nur noch nicht fertig hochgefahren.
    func testStartetGeradeBleibtBeimHochfahren() {
        let z = DienstUebergang.naechsterZustand(aktuell: .startetGerade, erreichbar: false, wurdeAngehalten: false)
        XCTAssertEqual(z, .startetGerade)
    }

    func testStartetGeradeWirdLaeuftSobaldErreichbar() {
        let z = DienstUebergang.naechsterZustand(aktuell: .startetGerade, erreichbar: true, wurdeAngehalten: false)
        XCTAssertEqual(z, .laeuft)
    }

    // Der zentrale Fall des Auftrags: laeuft -> nicht mehr erreichbar heisst
    // unerwartetes Ende, und genau das muss die Oberflaeche zeigen.
    func testLaeuftWirdUnerwartetBeendetBeiAusfall() {
        let z = DienstUebergang.naechsterZustand(aktuell: .laeuft, erreichbar: false, wurdeAngehalten: false)
        XCTAssertEqual(z, .unerwartetBeendet)
        XCTAssertTrue(z.istFehler)
    }

    func testLaeuftBleibtLaeuftSolangeErreichbar() {
        let z = DienstUebergang.naechsterZustand(aktuell: .laeuft, erreichbar: true, wurdeAngehalten: false)
        XCTAssertEqual(z, .laeuft)
    }

    // Erholt sich der Dienst von selbst wieder, wird das ohne Zutun erkannt.
    func testUnerwartetBeendetErholtSichZuLaeuft() {
        let z = DienstUebergang.naechsterZustand(aktuell: .unerwartetBeendet, erreichbar: true, wurdeAngehalten: false)
        XCTAssertEqual(z, .laeuft)
    }

    func testUnerwartetBeendetBleibtOhneErreichbarkeit() {
        let z = DienstUebergang.naechsterZustand(aktuell: .unerwartetBeendet, erreichbar: false, wurdeAngehalten: false)
        XCTAssertEqual(z, .unerwartetBeendet)
    }

    // Negativfall: absichtliches Anhalten ist niemals ein Fehlerzustand,
    // unabhaengig vom Ausgangszustand.
    func testAngehaltenUeberschreibtLaeuft() {
        let z = DienstUebergang.naechsterZustand(aktuell: .laeuft, erreichbar: true, wurdeAngehalten: true)
        XCTAssertEqual(z, .angehalten)
        XCTAssertFalse(z.istFehler)
    }

    func testAngehaltenUeberschreibtUnerwartetBeendet() {
        let z = DienstUebergang.naechsterZustand(aktuell: .unerwartetBeendet, erreichbar: true, wurdeAngehalten: true)
        XCTAssertEqual(z, .angehalten)
    }

    func testAngehaltenBleibtOhneNeustart() {
        let z = DienstUebergang.naechsterZustand(aktuell: .angehalten, erreichbar: true, wurdeAngehalten: false)
        XCTAssertEqual(z, .angehalten)
    }
}

final class PythonAuswahlTests: XCTestCase {
    func testErsterFaehigerGewinnt() {
        let ergebnis = PythonAuswahl.waehle(
            kandidaten: ["/a/python3", "/b/python3", "/c/python3"],
            faehig: { $0 == "/b/python3" || $0 == "/c/python3" }
        )
        XCTAssertEqual(ergebnis, "/b/python3")
    }

    func testKeinerFaehigGibtNil() {
        let ergebnis = PythonAuswahl.waehle(kandidaten: ["/a/python3"], faehig: { _ in false })
        XCTAssertNil(ergebnis)
    }

    func testLeereListeGibtNil() {
        let ergebnis = PythonAuswahl.waehle(kandidaten: [], faehig: { _ in true })
        XCTAssertNil(ergebnis)
    }
}
