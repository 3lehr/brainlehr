// Rot-vor-Gruen-Beleg fuer die Zustandsuebersetzung, die DienstAufsicht.swift
// seit der Umstellung auf einen eigenstaendigen Dienst benutzt (Auftrag
// 2026-08-14/15). Vor dieser Aenderung gab es den Typ `DienstMeldung` nicht
// -- dieser Test war rot mit "cannot find 'DienstMeldung' in scope", siehe
// Bau-Log im Auftragsbericht.

import XCTest
@testable import BrainlehrCore

final class DienstMeldungTests: XCTestCase {
    // Dienst laeuft -> keine Meldung, die Oberflaeche zeigt den Wissensraum.
    func testLaeuftZeigtKeineMeldung() {
        XCTAssertNil(DienstMeldung.fuer(.laeuft))
    }

    func testStartetGeradeZeigtKeineMeldung() {
        XCTAssertNil(DienstMeldung.fuer(.startetGerade))
    }

    func testAngehaltenZeigtKeineMeldung() {
        XCTAssertNil(DienstMeldung.fuer(.angehalten))
    }

    // Dienst laeuft nicht -> der Satz, den ein Mensch lesen und danach
    // handeln kann. Verboten darin: Port, Pfad, Prozessname, Sprache.
    func testUnerwartetBeendetNenntEinenWeg() {
        let satz = DienstMeldung.fuer(.unerwartetBeendet)
        XCTAssertEqual(satz, DienstMeldung.nichtErreichbar)
        XCTAssertNotNil(satz)
        XCTAssertFalse(satz!.contains("8799"))
        XCTAssertFalse(satz!.lowercased().contains("python"))
        XCTAssertFalse(satz!.lowercased().contains(".py"))
    }
}
