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

    // MARK: - Einheiten: es gibt KEINE allgemeine Punkt-zu-Millimeter-Rechnung

    /// Die Zahlen stammen aus einer Messung an zwei angeschlossenen Geraeten
    /// am 2026-08-13 (CGDisplayScreenSize gegen NSScreen.frame). Vorher stand
    /// hier ein Test, der die FALSCHE Annahme festschrieb, ein Punkt sei
    /// 1/72 Zoll -- die schlimmste Sorte Test, weil sein Gruen einen Fehler
    /// zementiert. Aufgefallen erst, als ein zweiter Schirm angeschlossen war.
    func testMillimeterJePunktIstGeraeteabhaengig() {
        let eizo = Lesbarkeit.mmJePunkt(physischMm: 599, punkte: 2560)
        let intern = Lesbarkeit.mmJePunkt(physischMm: 344, punkte: 1728)
        XCTAssertEqual(eizo!, 0.2341, accuracy: 0.001)
        XCTAssertEqual(intern!, 0.1992, accuracy: 0.001)
        XCTAssertNotEqual(eizo!, intern!, accuracy: 0.01,
            "Zwei Geraete, zwei Werte -- es gibt nicht einmal eine konstante Korrektur")
        // Die alte Annahme 1/72 Zoll = 0,3528 mm liegt bei BEIDEN daneben,
        // und zwar unterschiedlich weit.
        XCTAssertLessThan(eizo!, 0.3528)
        XCTAssertLessThan(intern!, 0.3528)
    }

    func testOhneAngabeKeineUmrechnung() {
        XCTAssertNil(Lesbarkeit.mmJePunkt(physischMm: 0, punkte: 2560))
        XCTAssertNil(Lesbarkeit.mmJePunkt(physischMm: 599, punkte: 0))
        XCTAssertNil(Lesbarkeit.mmJePunkt(physischMm: -1, punkte: 2560))
    }

    // MARK: - Die beiden echten Schirme des Betreibers

    /// Rot vor gruen an echter Hardware: Mit der alten Punkt-Annahme meldete
    /// der EIZO 40,8 Zoll statt 27,1 und der eingebaute 28,6 statt 16,1.
    func testEchteSchirmeWerdenRichtigVermessen() {
        let eizo = Anzeigeflaeche(schirmMm: (599, 340), schirmPunkte: (2560, 1440),
                                  fensterPunkte: (2560, 1440))!
        XCTAssertEqual(eizo.diagonaleZoll, 27.1, accuracy: 0.2)

        let intern = Anzeigeflaeche(schirmMm: (344, 222), schirmPunkte: (1728, 1117),
                                    fensterPunkte: (1728, 1117))!
        XCTAssertEqual(intern.diagonaleZoll, 16.1, accuracy: 0.2)
    }

    func testEinFensterAufHalberBreiteTraegtWeniger() {
        let voll = Anzeigeflaeche(schirmMm: (599, 340), schirmPunkte: (2560, 1440),
                                  fensterPunkte: (2560, 1440))!
        let halb = Anzeigeflaeche(schirmMm: (599, 340), schirmPunkte: (2560, 1440),
                                  fensterPunkte: (1280, 1440))!
        XCTAssertLessThanOrEqual(halb.felder(abstandMm: 700), voll.felder(abstandMm: 700))
        XCTAssertEqual(halb.breiteMm, voll.breiteMm / 2, accuracy: 0.1)
    }

    func testUnbrauchbareSchirmangabenErgebenKeineFlaeche() {
        XCTAssertNil(Anzeigeflaeche(schirmMm: (0, 340), schirmPunkte: (2560, 1440),
                                    fensterPunkte: (2560, 1440)))
        XCTAssertNil(Anzeigeflaeche(schirmMm: (599, 340), schirmPunkte: (2560, 1440),
                                    fensterPunkte: (0, 1440)))
    }
}
