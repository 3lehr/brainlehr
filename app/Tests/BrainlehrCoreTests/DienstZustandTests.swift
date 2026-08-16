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

    // ----------------------------------------------------------------------
    // B5 / ADR-023: der Mensch entscheidet per Schalter, ob eine Domaene
    // mitstartet -- und er muss VIER Zustaende unterscheiden koennen, nicht
    // zwei. Die ADR nennt den Grund woertlich: "aus" (Schalter steht aus --
    // kein Defekt, eine Entscheidung) und "startet" sind heute nicht
    // unterscheidbar, und genau diese Verwechslung hat sie ausgeloest.
    // ----------------------------------------------------------------------

    // Schalter aus: kein Defekt, eine Entscheidung. Unabhaengig davon, ob
    // zufaellig etwas auf dem Port antwortet -- sonst wuerde ein fremder
    // Prozess den Zustand der eigenen Domaene bestimmen.
    func testSchalterAusErgibtAusUnabhaengigVonErreichbarkeit() {
        for erreichbar in [true, false] {
            let z = DienstUebergang.naechsterZustand(
                aktuell: .aus, erreichbar: erreichbar, wurdeAngehalten: false, eingeschaltet: false)
            XCTAssertEqual(z, .aus)
            XCTAssertFalse(z.istFehler, "aus ist kein Fehler, sondern eine Entscheidung")
        }
    }

    // Aus jedem Zustand heraus schaltet der Mensch ab -- auch mitten im Lauf.
    func testAusschaltenWirktAusJedemZustand() {
        for aktuell: DienstZustand in [.startetGerade, .laeuft, .unerwartetBeendet, .kommtNichtHoch, .angehalten] {
            let z = DienstUebergang.naechsterZustand(
                aktuell: aktuell, erreichbar: true, wurdeAngehalten: false, eingeschaltet: false)
            XCTAssertEqual(z, .aus, "aus \(aktuell) muss Ausschalten nach .aus fuehren")
        }
    }

    func testEinschaltenAusDemAusZustandBeginntDenStart() {
        let z = DienstUebergang.naechsterZustand(
            aktuell: .aus, erreichbar: false, wurdeAngehalten: false, eingeschaltet: true)
        XCTAssertEqual(z, .startetGerade)
    }

    // DER Fall, den ADR-023 verlangt und den es bisher nicht gab: eingeschaltet,
    // aber kommt nach der Geduldsspanne nicht hoch. Ohne ihn bleibt der Dienst
    // ewig in "startet" -- und "startet fuer immer" liest sich wie ein Defekt,
    // ohne einen zu benennen.
    func testStartetOhneErfolgWirdNachGeduldsspanneKommtNichtHoch() {
        let z = DienstUebergang.naechsterZustand(
            aktuell: .startetGerade, erreichbar: false, wurdeAngehalten: false,
            eingeschaltet: true, versucheSeit: DienstUebergang.geduldsspanne)
        XCTAssertEqual(z, .kommtNichtHoch)
        XCTAssertTrue(z.istFehler)
    }

    // Grenzwert, beide Seiten: eine Sekunde vor Ablauf noch startend.
    func testEineSekundeVorAblaufNochStartend() {
        let z = DienstUebergang.naechsterZustand(
            aktuell: .startetGerade, erreichbar: false, wurdeAngehalten: false,
            eingeschaltet: true, versucheSeit: DienstUebergang.geduldsspanne - 1)
        XCTAssertEqual(z, .startetGerade)
    }

    // Ein spaeter Erfolg schlaegt die Geduldsspanne -- wer hochkommt, laeuft,
    // auch wenn er lange gebraucht hat.
    func testSpaeterErfolgSchlaegtDieGeduldsspanne() {
        let z = DienstUebergang.naechsterZustand(
            aktuell: .startetGerade, erreichbar: true, wurdeAngehalten: false,
            eingeschaltet: true, versucheSeit: DienstUebergang.geduldsspanne * 10)
        XCTAssertEqual(z, .laeuft)
    }

    // Erholt sich der Dienst doch noch, verschwindet der Fehler von selbst --
    // dieselbe Haltung wie bei unerwartetBeendet.
    func testKommtNichtHochErholtSich() {
        let z = DienstUebergang.naechsterZustand(
            aktuell: .kommtNichtHoch, erreichbar: true, wurdeAngehalten: false, eingeschaltet: true)
        XCTAssertEqual(z, .laeuft)
    }

    // Jeder Zustand hat einen Satz fuer den Menschen -- ausser denen, die
    // nichts zu erklaeren haben. "aus" MUSS einen haben, sonst steht der
    // Mensch wieder vor einem stummen Bildschirm.
    func testAusHatEinenSatzUndErKlingtNichtNachDefekt() {
        let satz = DienstMeldung.fuer(.aus)
        XCTAssertNotNil(satz)
        XCTAssertFalse(satz!.isEmpty)
    }

    func testKommtNichtHochSagtWasZuTunIst() {
        let satz = DienstMeldung.fuer(.kommtNichtHoch)
        XCTAssertNotNil(satz)
    }

    // Kein sichtbarer Satz nennt Port, Pfad, Prozess oder Programmiersprache
    // (Hausregel: keine Entwicklerinformation in der Oberflaeche).
    func testKeineEntwicklerinformationInDenSaetzen() {
        let verboten = ["8799", "127.0.0.1", "http", "Port", "Prozess", "Swift", "Python", "PID"]
        for zustand: DienstZustand in [.aus, .startetGerade, .laeuft, .unerwartetBeendet, .kommtNichtHoch, .angehalten] {
            guard let satz = DienstMeldung.fuer(zustand) else { continue }
            for wort in verboten {
                XCTAssertFalse(satz.contains(wort), "\(zustand): Satz nennt \(wort)")
            }
        }
    }
}
