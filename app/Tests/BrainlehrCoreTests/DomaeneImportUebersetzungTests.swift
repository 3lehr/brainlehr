import XCTest
@testable import BrainlehrCore

// H8b: die Uebersetzung "Ergebnis von unten -> angezeigter Satz" -- beide
// Faelle, wie im Auftrag verlangt. Die Pruefung selbst (kern/domaene.py)
// wird hier NICHT nachgebaut, nur ihre Antwort uebersetzt.
final class DomaeneImportUebersetzungTests: XCTestCase {

    func testAngenommenNenntBezeichnungUndAnzahl() {
        let antwort: [String: Any] = ["angenommen": true, "bezeichnung": "Steuer und Belege", "anzahl_regeln": 3]
        let e = DomaeneImportUebersetzung.uebersetze(antwort)
        XCTAssertEqual(e.titel, "Übernommen")
        XCTAssertEqual(e.text, "„Steuer und Belege“ gilt jetzt. 3 Regeln wurden übernommen.")
    }

    func testAngenommenEineRegelSingular() {
        let antwort: [String: Any] = ["angenommen": true, "bezeichnung": "Steuer", "anzahl_regeln": 1]
        let e = DomaeneImportUebersetzung.uebersetze(antwort)
        XCTAssertEqual(e.text, "„Steuer“ gilt jetzt. Eine Regel wurde übernommen.")
    }

    // INT-UPD-001: rot vor gruen -- vor dieser Unterscheidung sah der
    // Bildschirm nur 'gespeichert' und meldete bei einem reinen
    // Aktualisierungs-Import "enthielt nichts Neues".
    func testAktualisierungIstNichtNichtsNeues() {
        XCTAssertEqual(DomaeneImportUebersetzung.wirkung(["gespeichert": 0, "aktualisiert": 3]), .aktualisiert)
        XCTAssertEqual(DomaeneImportUebersetzung.wirkung(["gespeichert": 2, "aktualisiert": 0]), .angelegt)
        XCTAssertEqual(DomaeneImportUebersetzung.wirkung(["gespeichert": 0, "aktualisiert": 0]), .unveraendert)
        // Alte Antwort ohne den neuen Schluessel darf nicht als Aenderung gelten.
        XCTAssertEqual(DomaeneImportUebersetzung.wirkung(["gespeichert": 0]), .unveraendert)
    }

    // Negativfall: der fachliche Grund aus kern/domaene.py wird woertlich
    // gezeigt -- kein Rohfehler, kein Dateiname, keine Zeilennummer.
    func testAbgelehntZeigtFachlichenGrund() {
        let antwort: [String: Any] = ["angenommen": false, "grund": "Die Regel 'Bewirtung' nennt keine Quelle."]
        let e = DomaeneImportUebersetzung.uebersetze(antwort)
        XCTAssertEqual(e.titel, "Nicht übernommen")
        XCTAssertEqual(e.text, "Die Regel 'Bewirtung' nennt keine Quelle.")
    }

    // H8a (kern/domaene.py) noch nicht vorhanden -- Server antwortet mit
    // "verfuegbar": false statt eines Absturzes.
    func testNochNichtVerfuegbar() {
        let antwort: [String: Any] = ["verfuegbar": false]
        let e = DomaeneImportUebersetzung.uebersetze(antwort)
        XCTAssertEqual(e.titel, "Noch nicht möglich")
        XCTAssertFalse(e.text.contains("kern"))
        XCTAssertFalse(e.text.contains("domaene.py"))
    }

    // Grenzfall: kaputte/unerwartete Antwort ohne "angenommen" -- kein Absturz,
    // kein Rohfehler, ein lesbarer Ersatzsatz.
    func testUnbekannteAntwortformOhneAngenommen() {
        let antwort: [String: Any] = ["irgendwas": 1]
        let e = DomaeneImportUebersetzung.uebersetze(antwort)
        XCTAssertEqual(e.titel, "Nicht übernommen")
        XCTAssertEqual(e.text, "Aus der Datei ließ sich kein Ergebnis lesen.")
    }
}
