import XCTest
@testable import BrainlehrCore

/// ADR-023: Voreinstellung AUS, und der Schluessel kollidiert nicht.
final class MitstartTests: XCTestCase {

    func testVoreinstellungIstAus() {
        XCTAssertFalse(Mitstart.istEingeschaltet("einzelunternehmer", speicher: [:]))
    }

    func testEingeschaltetWirdGelesen() {
        let s = [Mitstart.schluessel(fuer: "einzelunternehmer"): true]
        XCTAssertTrue(Mitstart.istEingeschaltet("einzelunternehmer", speicher: s))
    }

    func testAusdruecklichAusBleibtAus() {
        let s = [Mitstart.schluessel(fuer: "einzelunternehmer"): false]
        XCTAssertFalse(Mitstart.istEingeschaltet("einzelunternehmer", speicher: s))
    }

    /// Der Fall, den ein nackter Domaenenname kaputt macht: eine fremde
    /// Einstellung mit demselben Namen wuerde den Schalter stellen.
    func testFremderSchluesselStelltDenSchalterNicht() {
        XCTAssertFalse(Mitstart.istEingeschaltet("einzelunternehmer",
                                                 speicher: ["einzelunternehmer": true]))
    }

    /// Zwei Domaenen teilen sich den Speicher und duerfen sich nicht stellen.
    func testZweiDomaenenStoerenEinanderNicht() {
        let s = [Mitstart.schluessel(fuer: "einzelunternehmer"): true]
        XCTAssertTrue(Mitstart.istEingeschaltet("einzelunternehmer", speicher: s))
        XCTAssertFalse(Mitstart.istEingeschaltet("schulkorrektor", speicher: s))
    }
}
