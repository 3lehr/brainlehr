import XCTest
@testable import BrainlehrCore

/// ADR-013/ADR-024: Die Domaene BESCHREIBT, das atelier ZEICHNET. Diese Tests
/// pruefen die Uebersetzung von der Beschreibung in ein Anzeigemodell -- also
/// genau die Naht, an der ein zweiter Zeichner (Web) spaeter ansetzt.
///
/// Warum das die richtige Ebene ist: Eine SwiftUI-Ansicht laesst sich nur mit
/// erheblichem Aufwand pruefen, das Modell darunter ohne jeden Mock. Und die
/// Entscheidungen, die schiefgehen koennen -- unbekannte Spaltenart, fehlender
/// Wert, leere Liste -- fallen alle hier und nicht im Zeichnen.
final class DomaenenBildschirmTests: XCTestCase {

    private var beschreibung: [String: Any] {
        [
            "kennung": "euer_zuordnung",
            "art": "tabelle",
            "titel": "Übertragung in die Anlage EÜR",
            "erklaerung": "Jede Zeile zeigt, was woran belegt ist.",
            "spalten": [
                ["name": "groesse", "titel": "Größe", "art": "text"],
                ["name": "betrag_cent", "titel": "Betrag", "art": "betrag"],
                ["name": "fundstelle", "titel": "Belegt durch", "art": "zitat"],
            ],
            "leerfall": "Für dieses Jahr ist noch nichts zugeordnet.",
        ]
    }

    func testBeschreibungWirdGelesen() {
        let b = DomaenenBildschirm(beschreibung: beschreibung)
        XCTAssertNotNil(b)
        XCTAssertEqual(b?.titel, "Übertragung in die Anlage EÜR")
        XCTAssertEqual(b?.spalten.count, 3)
        XCTAssertEqual(b?.spalten.first?.titel, "Größe")
    }

    /// Ohne Titel gibt es keinen Bildschirm -- ein namenloser Reiter ist fuer
    /// den Menschen nicht auffindbar.
    func testOhneTitelKeinBildschirm() {
        var b = beschreibung
        b.removeValue(forKey: "titel")
        XCTAssertNil(DomaenenBildschirm(beschreibung: b))
    }

    func testOhneSpaltenKeinBildschirm() {
        var b = beschreibung
        b["spalten"] = [[String: Any]]()
        XCTAssertNil(DomaenenBildschirm(beschreibung: b))
    }

    /// Der Kern der Plattformblindheit auf der ZEICHNER-Seite: Die Domaene
    /// nennt eine Rolle ("betrag"), nicht eine Bauform. Was daraus wird --
    /// rechtsbuendig, Monospace, mit Waehrungszeichen -- entscheidet das
    /// atelier. Eine unbekannte Rolle wird als Text gezeigt, nicht verworfen:
    /// eine neuere Domaene darf eine aeltere Anwendung nicht sprengen.
    func testUnbekannteSpaltenartWirdText() {
        var b = beschreibung
        b["spalten"] = [["name": "x", "titel": "X", "art": "hologramm"]]
        XCTAssertEqual(DomaenenBildschirm(beschreibung: b)?.spalten.first?.art, .text)
    }

    // MARK: - Werte

    func testBetragWirdAusCentGeformt() {
        let b = DomaenenBildschirm(beschreibung: beschreibung)!
        let zeile = b.zeile(aus: ["groesse": "Ausgaben", "betrag_cent": 123456, "fundstelle": "Betriebsausgaben"])
        XCTAssertEqual(zeile[0], "Ausgaben")
        XCTAssertTrue(zeile[1].contains("1.234"), "aus 123456 Cent werden 1.234,56 -- ist: \(zeile[1])")
        XCTAssertEqual(zeile[2], "Betriebsausgaben")
    }

    /// Ein FEHLENDER Wert ist keine Null. Er wird als Strich gezeigt, nicht als
    /// "0,00 €" -- sonst behauptet der Bildschirm einen Betrag, den niemand
    /// gerechnet hat. Dieselbe Regel wie im Dienst (euer_vorschlag.py).
    func testFehlenderBetragIstKeineNull() {
        let b = DomaenenBildschirm(beschreibung: beschreibung)!
        let zeile = b.zeile(aus: ["groesse": "Ausgaben"])
        XCTAssertFalse(zeile[1].contains("0,00"), "fehlender Wert darf nicht als Null erscheinen")
        XCTAssertEqual(zeile[1], "—")
    }

    func testNullIstNullUndKeinStrich() {
        let b = DomaenenBildschirm(beschreibung: beschreibung)!
        let zeile = b.zeile(aus: ["betrag_cent": 0])
        XCTAssertTrue(zeile[1].contains("0,00"), "eine gerechnete Null ist eine Aussage -- ist: \(zeile[1])")
    }

    func testLeerfallSatzKommtAusDerBeschreibung() {
        XCTAssertEqual(DomaenenBildschirm(beschreibung: beschreibung)?.leerfall,
                       "Für dieses Jahr ist noch nichts zugeordnet.")
    }

    /// Ohne eigenen Satz ein neutraler -- nie eine leere Flaeche, und nie
    /// Entwicklerinformation.
    func testOhneLeerfallGibtEsTrotzdemEinenSatz() {
        var b = beschreibung
        b.removeValue(forKey: "leerfall")
        let s = DomaenenBildschirm(beschreibung: b)?.leerfall
        XCTAssertNotNil(s)
        XCTAssertFalse(s?.isEmpty ?? true)
    }
}
