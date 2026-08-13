import XCTest
@testable import BrainlehrCore

/// Prueft die Entscheidung "Ausschnitt, ganze Seite oder nebeneinander".
///
/// Der Kern ist nicht, dass die Rechnung stimmt, sondern dass sie an den
/// SPRUENGEN stimmt: Zwischen 55 und 65 Zoll wechselt das Ergebnis von null
/// auf zwei Felder, und genau deshalb darf die Feldzahl nicht fest verdrahtet
/// werden. Ein Test, der nur eine bequeme Groesse prueft, wuerde das nicht
/// bemerken.
final class AnzeigeformTests: XCTestCase {

    /// Breite und Hoehe eines 16:9-Schirms in mm aus der Diagonale in Zoll.
    private func schirm(_ zoll: Double, breit: Double = 16, hoch: Double = 9) -> (Double, Double) {
        let d = zoll * 25.4
        let norm = (breit * breit + hoch * hoch).squareRoot()
        return (d * breit / norm, d * hoch / norm)
    }

    private func form(_ zoll: Double, abstandMm: Double) -> Anzeigeform {
        let (b, h) = schirm(zoll)
        return Lesbarkeit.form(breiteMm: b, hoeheMm: h, abstandMm: abstandMm)
    }

    // MARK: - Die Lagen, die der Betreiber genannt hat

    func testEinzelplatzTraegtNieEineGanzeSeite() {
        // Die haeufigste Lage von allen -- und in ihr ist "eine Seite zeigen"
        // grundsaetzlich das falsche Ziel.
        XCTAssertEqual(form(14, abstandMm: 600), .ausschnitt)
        XCTAssertEqual(form(14, abstandMm: 700), .ausschnitt)
        XCTAssertEqual(form(16, abstandMm: 700), .ausschnitt)
    }

    func testEinzelnerBueroschirmTraegtEbenfallsKeineSeite() {
        XCTAssertEqual(form(27, abstandMm: 700), .ausschnitt)
    }

    func testGrosserFernseherTraegtZweiSeitenNebeneinander() {
        XCTAssertEqual(form(65, abstandMm: 1500), .nebeneinander)
        XCTAssertEqual(form(75, abstandMm: 1500), .nebeneinander)
    }

    /// DER Test dieser Datei: der Sprung, der eine feste Feldzahl unhaltbar
    /// macht. Engpass ist die Hoehe, nicht die Breite.
    func testSprungZwischen55Und65Zoll() {
        XCTAssertEqual(form(55, abstandMm: 1500), .ausschnitt,
                       "55 Zoll traegt bei 1,5 m keine volle Seite -- zu niedrig")
        XCTAssertEqual(form(65, abstandMm: 1500), .nebeneinander,
                       "65 Zoll traegt zwei -- der Sprung ist nicht sanft")
    }

    func testGrosserSchirmAusGrosserEntfernungTraegtWiederNichts() {
        // Ein Vortragsraum ist keine bessere Lage, nur eine andere.
        XCTAssertEqual(form(85, abstandMm: 2500), .ausschnitt)
    }

    // MARK: - Monotonie, in beide Richtungen

    func testMehrFlaecheTraegtNieWeniger() {
        for abstand in [1000.0, 1500.0, 2000.0] {
            var vorher = -1
            for zoll in [14.0, 24.0, 32.0, 43.0, 55.0, 65.0, 75.0, 85.0] {
                let (b, h) = schirm(zoll)
                let n = Lesbarkeit.felder(breiteMm: b, hoeheMm: h, abstandMm: abstand)
                XCTAssertGreaterThanOrEqual(n, vorher,
                    "bei \(abstand) mm faellt die Feldzahl von \(vorher) auf \(n) bei \(zoll)\"")
                vorher = n
            }
        }
    }

    func testMehrAbstandTraegtNieMehr() {
        let (b, h) = schirm(65)
        var vorher = Int.max
        for abstand in [800.0, 1000.0, 1500.0, 2000.0, 3000.0] {
            let n = Lesbarkeit.felder(breiteMm: b, hoeheMm: h, abstandMm: abstand)
            XCTAssertLessThanOrEqual(n, vorher)
            vorher = n
        }
    }

    // MARK: - Negativfaelle: keine Angabe ist nicht dasselbe wie kein Bedarf

    func testUnbrauchbareEingabenErgebenKeineVergroesserung() {
        XCTAssertNil(Lesbarkeit.vergroesserung(abstandMm: 0, werte: .gemessen))
        XCTAssertNil(Lesbarkeit.vergroesserung(abstandMm: -100, werte: .gemessen))
        let ohneSchrift = Lesbarkeitswerte(fliesstextPt: 0, xHoeheAnteil: 0.5,
                                           seiteBreiteMm: 210, seiteHoeheMm: 297,
                                           schwelleGrad: 0.2)
        XCTAssertNil(Lesbarkeit.vergroesserung(abstandMm: 1500, werte: ohneSchrift))
    }

    func testKeineFlaecheErgibtKeineFelderUndDenAusschnitt() {
        XCTAssertEqual(Lesbarkeit.felder(breiteMm: 0, hoeheMm: 0, abstandMm: 1500), 0)
        XCTAssertEqual(Lesbarkeit.form(breiteMm: 0, hoeheMm: 0, abstandMm: 1500), .ausschnitt)
        // Kein Abstand heisst keine Aussage -- und dann lieber Ausschnitt als
        // eine erfundene Feldzahl.
        XCTAssertEqual(Lesbarkeit.form(breiteMm: 1440, hoeheMm: 810, abstandMm: 0), .ausschnitt)
    }

    // MARK: - Die Schwelle ist Modellwissen und darum ein Parameter

    func testLockereSchwelleTraegtMehrFelder() {
        let (b, h) = schirm(27)
        let streng = Lesbarkeit.felder(breiteMm: b, hoeheMm: h, abstandMm: 700, werte: .gemessen)
        let locker = Lesbarkeit.felder(breiteMm: b, hoeheMm: h, abstandMm: 700,
                                       werte: Lesbarkeitswerte(
                                           fliesstextPt: 10.9, xHoeheAnteil: 0.547,
                                           seiteBreiteMm: 210, seiteHoeheMm: 297,
                                           schwelleGrad: 0.14))
        XCTAssertEqual(streng, 0)
        XCTAssertGreaterThan(locker, streng,
            "Die Schwelle entscheidet mehr als die Bauform -- das muss sichtbar bleiben")
    }

    // MARK: - Einheiten

    func testPunkteWerdenZuMillimeter() {
        // 72 Punkte sind ein Zoll.
        XCTAssertEqual(Lesbarkeit.punkteInMm(72), 25.4, accuracy: 0.0001)
        XCTAssertEqual(Lesbarkeit.punkteInMm(0), 0, accuracy: 0.0001)
    }

    func testEinMacBookFensterIstKleinerAlsEinFernseher() {
        // Gegenprobe zur Einheitenrechnung ueber die echte Fenstergroesse:
        // 1440 x 810 Punkte sind rund 508 x 286 mm.
        XCTAssertEqual(Lesbarkeit.punkteInMm(1440), 508, accuracy: 1.0)
    }
}
