import XCTest
@testable import BrainlehrCore

final class AusweisProtokollTests: XCTestCase {
    func testArgumenteAnlegenReihenfolge() {
        let argv = argumenteAnlegen(name: "codex", art: .maschine, rollen: [.schreiber, .leser])
        XCTAssertEqual(argv, ["anlegen", "codex", "maschine", "schreiber,leser"])
    }

    func testArgumenteEinladenReihenfolge() {
        let argv = argumenteEinladen(name: "claude-code", fuer: "markus", rollen: [.schreiber])
        XCTAssertEqual(argv, ["einladen", "claude-code", "markus", "schreiber"])
    }

    // Negativfall: keine Rolle gewaehlt -> leerer Text, kein Absturz.
    func testRollenTextLeereListe() {
        XCTAssertEqual(rollenText([]), "")
    }

    func testGefundenerFehlerErkenntFehlerJSON() {
        let daten = "{\"fehler\": \"Ohne Geheimnis geht es nicht weiter.\"}".data(using: .utf8)!
        XCTAssertEqual(gefundenerFehler(in: daten), "Ohne Geheimnis geht es nicht weiter.")
    }

    // Negativfall: eine Erfolgsantwort ohne "fehler"-Feld darf nicht
    // faelschlich als Fehler gedeutet werden.
    func testGefundenerFehlerNilBeiErfolgsantwort() {
        let daten = "{\"name\": \"codex\", \"art\": \"maschine\", \"rollen\": [], \"geheimnis\": \"abc\"}".data(using: .utf8)!
        XCTAssertNil(gefundenerFehler(in: daten))
    }

    func testAusweisListeAntwortDekodiert() throws {
        let json = """
        {"datei": "/tmp/ausweise.json", "ausweise": [{"name": "markus", "art": "mensch", "rollen": ["betreiber"]}]}
        """.data(using: .utf8)!
        let antwort = try JSONDecoder().decode(AusweisListeAntwort.self, from: json)
        XCTAssertEqual(antwort.datei, "/tmp/ausweise.json")
        XCTAssertEqual(antwort.ausweise.first?.name, "markus")
        XCTAssertEqual(antwort.ausweise.first?.id, "markus")
    }

    func testAusweisEinladenAntwortDekodiert() throws {
        let json = """
        {"name": "claude-code", "fuer": "markus", "pin": "123456", "gueltig_minuten": 15}
        """.data(using: .utf8)!
        let antwort = try JSONDecoder().decode(AusweisEinladenAntwort.self, from: json)
        XCTAssertEqual(antwort.pin, "123456")
        XCTAssertEqual(antwort.gueltig_minuten, 15)
    }
}

final class RepoWurzelTests: XCTestCase {
    func testFindetWurzelBeimStartpunkt() {
        let fund = RepoWurzel.suche(ab: "/repo/app/Sources", istWurzel: { $0 == "/repo/app/Sources" })
        XCTAssertEqual(fund, "/repo/app/Sources")
    }

    func testSteigtBisZurWurzelAuf() {
        let fund = RepoWurzel.suche(ab: "/repo/app/Sources/BrainlehrApp", istWurzel: { $0 == "/repo" })
        XCTAssertEqual(fund, "/repo")
    }

    // Negativfall: kein Kennzeichen irgendwo auf dem Weg -> nil, kein Absturz
    // an der Dateisystemwurzel.
    func testGibtNilOhneKennzeichen() {
        let fund = RepoWurzel.suche(ab: "/eins/zwei/drei", istWurzel: { _ in false })
        XCTAssertNil(fund)
    }

    // Grenzwert: maximalTiefe erschoepft, bevor das Kennzeichen erreicht wird.
    func testGibtNilBeiErschoepfterTiefe() {
        let fund = RepoWurzel.suche(ab: "/a/b/c/d/e", istWurzel: { $0 == "/" }, maximalTiefe: 2)
        XCTAssertNil(fund)
    }
}
