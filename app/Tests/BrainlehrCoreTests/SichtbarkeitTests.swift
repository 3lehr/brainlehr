import XCTest
@testable import BrainlehrCore

/// Prueft die Zugriffsschranke.
///
/// Der Kern ist nicht "erlaubt das Richtige", sondern "verweigert im Zweifel"
/// -- und "verraet nicht, DASS es etwas gibt". Bei WEG-Rechtsfaellen mit
/// Namen Dritter ist schon die Trefferzahl eine Aussage.
final class SichtbarkeitTests: XCTestCase {

    private let gast = Betrachter(name: "Gast", rollen: [], stufe: .oeffentlich)
    private let mitarbeit = Betrachter(name: "M", rollen: ["schreiber"], stufe: .intern)
    private let betreiber = Betrachter(name: "B", rollen: ["betreiber"], stufe: .vollstaendig)

    // MARK: - Die Schranke selbst

    func testJedeStufeSiehtWasIhrZusteht() {
        XCTAssertTrue(Sichtbarkeit.darfSehen(.offen, gast))
        XCTAssertFalse(Sichtbarkeit.darfSehen(.intern, gast))
        XCTAssertFalse(Sichtbarkeit.darfSehen(.gesperrt, gast))

        XCTAssertTrue(Sichtbarkeit.darfSehen(.offen, mitarbeit))
        XCTAssertTrue(Sichtbarkeit.darfSehen(.intern, mitarbeit))
        XCTAssertFalse(Sichtbarkeit.darfSehen(.gesperrt, mitarbeit))

        for f in Freigabe.allCases { XCTAssertTrue(Sichtbarkeit.darfSehen(f, betreiber)) }
    }

    /// DER Test der Schranke: Unbekanntes ist GESPERRT, nicht offen.
    /// Wer "im Zweifel offen" baut, hat eine Schranke, die sich durch einen
    /// Tippfehler oeffnen laesst.
    func testUnbekannteFreigabeGiltAlsGesperrt() {
        for roh in ["", "  ", "OFFEN_NEU", "public", "tippfehlar", "null"] {
            XCTAssertEqual(Freigabe.aus(roh), .gesperrt, "durchgelassen: \(roh)")
            XCTAssertFalse(Sichtbarkeit.darfSehen(rohFreigabe: roh, gast))
            XCTAssertFalse(Sichtbarkeit.darfSehen(rohFreigabe: roh, mitarbeit))
        }
        XCTAssertEqual(Freigabe.aus(nil), .gesperrt)
        // Gegenprobe: die echten Werte kommen weiterhin durch, auch mit
        // Leerraum und Grossschreibung.
        XCTAssertEqual(Freigabe.aus(" Offen "), .offen)
        XCTAssertEqual(Freigabe.aus("INTERN"), .intern)
    }

    func testUnangemeldetSiehtNurFreigegebenes() {
        // Am Besprechungstisch sitzen Menschen ohne Ausweis. Der ungefragte
        // Zustand muss der engste sein.
        XCTAssertEqual(Betrachter.unangemeldet.stufe, .oeffentlich)
        XCTAssertFalse(Sichtbarkeit.darfSehen(.intern, .unangemeldet))
    }

    func testStufeFolgtAusDenRollen() {
        XCTAssertEqual(Betrachter.ausRollen("x", ["betreiber"]).stufe, .vollstaendig)
        XCTAssertEqual(Betrachter.ausRollen("x", ["schreiber"]).stufe, .intern)
        XCTAssertEqual(Betrachter.ausRollen("x", ["fachkundig"]).stufe, .intern)
        XCTAssertEqual(Betrachter.ausRollen("x", ["leser"]).stufe, .oeffentlich)
        XCTAssertEqual(Betrachter.ausRollen("x", []).stufe, .oeffentlich)
        // Eine unbekannte Rolle hebt niemanden hoch.
        XCTAssertEqual(Betrachter.ausRollen("x", ["superadmin"]).stufe, .oeffentlich)
    }

    // MARK: - Schwaerzen heisst ENTFERNEN

    private let vertrag = """
    Die Verwaltung wird an Diana Kunzmann übertragen. \
    Die Vergütung beträgt 50,00 € je Wohneinheit. \
    Widerspruch kam von Rolf Göring.
    """

    /// DER Test dieses Moduls. Nicht "nicht sichtbar" -- NICHT AUFFINDBAR.
    ///
    /// PDFMarkupType.redact setzt nur eine Anmerkung: ein schwarzes Rechteck
    /// ueber weiterhin vorhandenem Text. Wer das fuer Schwaerzung haelt,
    /// verteilt die Daten trotzdem.
    func testGeschwaerzterWortlautIstNichtMehrAuffindbar() {
        let s = [Schwaerzung(wortlaut: "Diana Kunzmann", sichtbarAb: .intern),
                 Schwaerzung(wortlaut: "Rolf Göring", sichtbarAb: .intern)]
        let fuerGast = Sichtbarkeit.schwaerze(vertrag, s, fuer: gast)

        XCTAssertFalse(fuerGast.contains("Diana Kunzmann"))
        XCTAssertFalse(fuerGast.contains("Rolf Göring"))
        // Auch nicht in Teilen -- ein Nachname allein ist auch ein Name.
        XCTAssertFalse(fuerGast.contains("Kunzmann"))
        XCTAssertFalse(fuerGast.contains("Göring"))
        // Der Rest bleibt lesbar, sonst ist das Dokument wertlos.
        XCTAssertTrue(fuerGast.contains("50,00 €"))
        XCTAssertTrue(fuerGast.contains("Wohneinheit"))
    }

    func testDieSchwaerzungIstSichtbarUndVerfaelschtNichtStill() {
        // Eine unsichtbare Schwaerzung macht aus dem Satz eine andere Aussage.
        // Wer einen Vertrag liest, muss erkennen, dass eine Stelle fehlt.
        let s = [Schwaerzung(wortlaut: "Diana Kunzmann", sichtbarAb: .intern)]
        let t = Sichtbarkeit.schwaerze(vertrag, s, fuer: gast)
        XCTAssertTrue(t.contains("[geschwärzt]"))
    }

    func testWerDarfSiehtDenVollenText() {
        let s = [Schwaerzung(wortlaut: "Diana Kunzmann", sichtbarAb: .intern)]
        XCTAssertEqual(Sichtbarkeit.schwaerze(vertrag, s, fuer: mitarbeit), vertrag)
        XCTAssertEqual(Sichtbarkeit.schwaerze(vertrag, s, fuer: betreiber), vertrag)
    }

    func testVerschiedeneStufenSehenVerschiedeneStellen() {
        // Die Eskalationsstufe, die der Betreiber genannt hat: je nach
        // Betrachter andere Stellen.
        let s = [Schwaerzung(wortlaut: "Diana Kunzmann", sichtbarAb: .intern),
                 Schwaerzung(wortlaut: "50,00 €", sichtbarAb: .vollstaendig)]
        let g = Sichtbarkeit.schwaerze(vertrag, s, fuer: gast)
        let m = Sichtbarkeit.schwaerze(vertrag, s, fuer: mitarbeit)
        let b = Sichtbarkeit.schwaerze(vertrag, s, fuer: betreiber)

        XCTAssertFalse(g.contains("Kunzmann")); XCTAssertFalse(g.contains("50,00 €"))
        XCTAssertTrue(m.contains("Kunzmann"));  XCTAssertFalse(m.contains("50,00 €"))
        XCTAssertTrue(b.contains("Kunzmann"));  XCTAssertTrue(b.contains("50,00 €"))
    }

    func testLeererWortlautSchwaerztNichtAlles() {
        // Negativfall: Ein leerer Suchtext wuerde sonst zwischen JEDES Zeichen
        // eine Marke setzen und das Dokument zerstoeren.
        let s = [Schwaerzung(wortlaut: "", sichtbarAb: .vollstaendig)]
        XCTAssertEqual(Sichtbarkeit.schwaerze(vertrag, s, fuer: gast), vertrag)
    }

    // MARK: - Auch das Verweigern leckt

    func testGefiltertWirdVORDerAuswertung() {
        struct Q { let nr: String; let freigabe: String? }
        let alle = [Q(nr: "1", freigabe: "offen"), Q(nr: "2", freigabe: "intern"),
                    Q(nr: "3", freigabe: "gesperrt"), Q(nr: "4", freigabe: nil)]

        let fuerGast = Sichtbarkeit.sichtbar(alle, gast) { $0.freigabe }
        XCTAssertEqual(fuerGast.map(\.nr), ["1"])
        let fuerM = Sichtbarkeit.sichtbar(alle, mitarbeit) { $0.freigabe }
        XCTAssertEqual(fuerM.map(\.nr), ["1", "2"])
        let fuerB = Sichtbarkeit.sichtbar(alle, betreiber) { $0.freigabe }
        XCTAssertEqual(fuerB.count, 4)
    }

    /// Der Satz fuer "nichts da" muss DERSELBE sein wie fuer "gibt es nicht".
    /// Sonst laesst sich aus dem Unterschied schliessen, dass es etwas gibt --
    /// und bei Rechtsfaellen mit Namen Dritter ist schon das eine Aussage.
    func testDieMeldungVerraetNichtDassEsEtwasGibt() {
        let m = Sichtbarkeit.nichtVorhanden
        for verraeterisch in ["gesperrt", "Berechtigung", "keine Rechte", "intern",
                              "verborgen", "Zugriff", "darf"] {
            XCTAssertFalse(m.lowercased().contains(verraeterisch.lowercased()),
                           "Meldung verrät zu viel: enthält '\(verraeterisch)'")
        }
        // Und sie nennt keine Zahl.
        XCTAssertNil(m.rangeOfCharacter(from: .decimalDigits))
    }
}
