// Die Naht zwischen kern/fundstelle.py und der App -- und warum sie einen
// eigenen Test braucht.
//
// DIE FEHLERKLASSE: Python rechnet die Antwort, Swift liest sie. Die Feldnamen
// stehen dabei ZWEIMAL -- einmal als dataclass, einmal als CodingKeys. Wird auf
// der Python-Seite ein Feld umbenannt, liefert Python weiter gueltiges JSON und
// `Decodable` ueberliest den unbekannten Schluessel WORTLOS. Der Nutzer sieht
// dann ein unmarkiertes Dokument, und das sieht aus wie "fuer diese Quelle gibt
// es keine Stelle" -- also wie eine Antwort statt wie ein Fehler.
//
// Gemessen 2026-08-13: Der Vertrag war zu diesem Zeitpunkt bereits gebrochen.
// Python lieferte 13 Felder, das Struct kannte 12; `weitere` kam in der App nie
// an, ohne dass es jemandem aufgefallen waere. Genau dafuer ist
// `bewusstNichtGelesen` da: ein Feld darf ungelesen bleiben, aber nur
// ausdruecklich und mit Grund.
//
// Vorlage erneuern: python3 kern/fundstelle.py --vertrag > app/Resources/fundstelle_vertrag.json

import XCTest
@testable import BrainlehrCore

final class FundstelleVertragTests: XCTestCase {

    /// app/Resources/fundstelle_vertrag.json, gefunden ueber den Ort DIESER
    /// Datei -- nicht ueber das Arbeitsverzeichnis, das je nach Aufrufer
    /// woanders liegt.
    private func vertragsDatei() throws -> Data {
        let hier = URL(fileURLWithPath: #filePath)          // .../app/Tests/BrainlehrCoreTests/<datei>
        let app = hier.deletingLastPathComponent()          // BrainlehrCoreTests
            .deletingLastPathComponent()                    // Tests
            .deletingLastPathComponent()                    // app
        let datei = app.appendingPathComponent("Resources/fundstelle_vertrag.json")
        return try Data(contentsOf: datei)
    }

    /// DER EIGENTLICHE TEST. Jeder Schluessel der echten Antwort muss entweder
    /// gelesen oder ausdruecklich als ungelesen erklaert sein.
    func testJederGelieferteSchluesselIstGelesenOderBegruendetUngelesen() throws {
        let roh = try JSONSerialization.jsonObject(with: try vertragsDatei())
        let objekt = try XCTUnwrap(roh as? [String: Any], "Vertragsmuster ist kein JSON-Objekt")

        let geliefert = Set(objekt.keys)
        let gelesen = Set(Fundstelle.CodingKeys.allCases.map(\.rawValue))
        let erklaert = gelesen.union(Fundstelle.bewusstNichtGelesen)

        let unbemerkt = geliefert.subtracting(erklaert)
        XCTAssertTrue(unbemerkt.isEmpty,
                      "Der Dienst liefert Felder, die weder gelesen noch als ungelesen erklaert "
                      + "sind: \(unbemerkt.sorted()). Entweder in Fundstelle lesen oder mit Grund "
                      + "in bewusstNichtGelesen eintragen -- stillschweigend verschwinden lassen "
                      + "ist die Fehlerklasse, gegen die dieser Test steht.")

        // Gegenrichtung, und sie ist die unbequemere: Das Struct erwartet ein
        // Feld, das der Dienst gar nicht mehr schickt. `decodeIfPresent` faengt
        // das zur Laufzeit ab -- aber als STILLE Voreinstellung, also genau das,
        // was hier laut werden soll.
        let verwaist = gelesen.subtracting(geliefert)
        XCTAssertTrue(verwaist.isEmpty,
                      "Das Struct liest Felder, die der Dienst nicht mehr liefert: "
                      + "\(verwaist.sorted()). Sie kommen zur Laufzeit als Voreinstellung "
                      + "durch, nicht als Fehler.")

        // Und ein Feld, das nur in bewusstNichtGelesen steht, ohne dass der
        // Dienst es liefert, ist eine veraltete Ausnahme -- sie wuerde ein
        // echtes neues Feld gleichen Namens kuenftig stumm durchwinken.
        let veralteteAusnahme = Fundstelle.bewusstNichtGelesen.subtracting(geliefert)
        XCTAssertTrue(veralteteAusnahme.isEmpty,
                      "bewusstNichtGelesen nennt Felder, die es nicht mehr gibt: "
                      + "\(veralteteAusnahme.sorted()).")
    }

    /// Die Vorlage muss auch wirklich dekodierbar sein -- sonst prueft der Test
    /// oben nur Zeichenketten gegen Zeichenketten.
    func testVorlageDekodiertUndTraegtDieDreiAussagen() throws {
        let f = try JSONDecoder().decode(Fundstelle.self, from: try vertragsDatei())

        XCTAssertTrue(f.belegt)
        XCTAssertEqual(f.seite, 8)
        XCTAssertEqual(f.seiten, [4, 5, 8])
        // belegt, markierbar und mehrdeutig sagen drei verschiedene Dinge --
        // die Vorlage traegt deshalb fuer jedes einen von den anderen
        // unabhaengigen Wert.
        XCTAssertTrue(f.markierbar, "Suchtext vorhanden, also markierbar")
        XCTAssertEqual(f.mehrdeutig, true, "drei Seiten, also mehrdeutig")
        XCTAssertEqual(f.lage, "Stelle markiert – dieser Wortlaut kommt mehrfach vor")
    }
}
