// Prueft die Deutung der Steuerbefehle -- ohne Fenster, ohne offenen Port.
//
// Der Schwerpunkt liegt auf den ABLEHNUNGEN, nicht auf den Erfolgen. Ein
// Steuerwerkzeug, das Richtiges annimmt, ist billig; eines, das Falsches
// erkennbar ablehnt, ist der Zweck. Genau daran scheiterten die sechs
// Werkzeuge, die den Grundgedanken des Betreibers ausgeloest haben: sie
// meldeten ihren Fehlschlag nicht.

import XCTest
@testable import BrainlehrCore

final class SteuerbefehlTests: XCTestCase {

    let ansichten = ["quellen", "raster", "bearbeitung", "sitzung", "wissensraum", "ausweise"]

    // ── Was gelingen muss ────────────────────────────────────────────────

    func testZustandUndGesundheitWerdenVerstanden() {
        XCTAssertEqual(try? deute("GET", "/zustand").get(), .zustand)
        XCTAssertEqual(try? deute("GET", "/gesundheit").get(), .gesundheit)
    }

    func testAbfragezeichenAendertDenPfadNicht() {
        XCTAssertEqual(try? deute("GET", "/zustand?huebsch=1").get(), .zustand)
    }

    func testAnsichtWirdGesetzt() {
        let r = deute("POST", "/ansicht", koerper: #"{"ansicht":"raster"}"#)
        XCTAssertEqual(try? r.get(), .ansichtWaehlen("raster"))
    }

    func testMethodeIstUnabhaengigVonDerSchreibweise() {
        XCTAssertEqual(try? deute("get", "/zustand").get(), .zustand)
    }

    // ── Was fehlschlagen MUSS, und zwar sprechend ────────────────────────

    func testUnbekannterPfadNennt404UndDieBekanntenPfade() {
        let antwort = ablehnung(deute("GET", "/gibtsnicht"))
        XCTAssertEqual(antwort.code, 404)
        XCTAssertTrue(antwort.koerper.contains("/zustand"),
                      "Eine Ablehnung ohne die bekannten Pfade zwingt zum Raten: \(antwort.koerper)")
    }

    func testUnbekannteAnsichtWirdAbgelehntUndNenntDieBekannten() {
        let antwort = ablehnung(deute("POST", "/ansicht", koerper: #"{"ansicht":"mondschein"}"#))
        XCTAssertEqual(antwort.code, 400)
        XCTAssertTrue(antwort.koerper.contains("mondschein"), "Der abgelehnte Wert gehoert in die Meldung")
        XCTAssertTrue(antwort.koerper.contains("wissensraum"), "Die gueltigen Werte auch")
    }

    func testFehlendesFeldWirdAbgelehnt() {
        XCTAssertEqual(ablehnung(deute("POST", "/ansicht", koerper: #"{}"#)).code, 400)
    }

    func testKaputterRumpfWirdAbgelehntStattGeraten() {
        XCTAssertEqual(ablehnung(deute("POST", "/ansicht", koerper: "das ist kein JSON")).code, 400)
    }

    func testLeererWertZaehltNichtAlsAngabe() {
        // Sonst waere "" eine gueltige Ansicht und die App spraenge ins Leere.
        XCTAssertEqual(ablehnung(deute("POST", "/ansicht", koerper: #"{"ansicht":""}"#)).code, 400)
    }

    func testFalscheMethodeSagtWelcheRichtigWaere() {
        let antwort = ablehnung(deute("GET", "/ansicht"))
        XCTAssertEqual(antwort.code, 405)
        XCTAssertTrue(antwort.koerper.contains("POST"))
        XCTAssertTrue(antwort.koerper.contains("/zustand"), "Der Weg zum Lesen gehoert in die Ablehnung")
    }

    // ── Anfragezeile: Grenzwerte ─────────────────────────────────────────

    func testAnfragezeileWirdZerlegt() {
        let z = Steuerdeutung.zerlegeAnfragezeile("GET /zustand HTTP/1.1")
        XCTAssertEqual(z?.methode, "GET")
        XCTAssertEqual(z?.pfad, "/zustand")
    }

    func testUnbrauchbareAnfragezeilenWerdenAbgewiesen() {
        // Jede davon wuerde beim Raten einen falschen Befehl erzeugen.
        XCTAssertNil(Steuerdeutung.zerlegeAnfragezeile(""))
        XCTAssertNil(Steuerdeutung.zerlegeAnfragezeile("GET"))
        XCTAssertNil(Steuerdeutung.zerlegeAnfragezeile("GET zustand HTTP/1.1"), "Pfad ohne fuehrenden Schraegstrich")
        XCTAssertNil(Steuerdeutung.zerlegeAnfragezeile("\u{0}\u{1}binaermuell"))
    }

    // ── Zustandsantwort ──────────────────────────────────────────────────

    func testZustandJSONIstLesbarUndTraegtDieAnsichten() throws {
        let objekt = try zustand(fenster: 1)
        XCTAssertEqual(objekt["ansicht"] as? String, "quellen")
        XCTAssertEqual(objekt["pid"] as? Int, 4711)
        XCTAssertEqual((objekt["ansichten"] as? [String])?.count, 6)
        XCTAssertEqual(objekt["sichtbar"] as? Bool, true)
    }

    /// DER TEST, DER DEN GEFUNDENEN FEHLER FESTHAELT.
    ///
    /// Beim ersten echten Einsatz lief die App mit null Fenstern und meldete
    /// dabei "ansicht: ausweise, dienst: laeuft" -- ein gesund aussehender
    /// Zustand fuer eine Anwendung, die nichts anzeigt. Vor dieser Aenderung
    /// gab es kein Feld, an dem das aufgefallen waere.
    func testOhneFensterIstNichtsSichtbarUndDieAntwortSagtEs() throws {
        let objekt = try zustand(fenster: 0)
        XCTAssertEqual(objekt["fenster"] as? Int, 0)
        XCTAssertEqual(objekt["sichtbar"] as? Bool, false,
                       "Eine Ansicht ohne Fenster ist keine Ansicht -- das muss die Antwort sagen")
        // Die Ansicht bleibt trotzdem gemeldet: sie ist der Zustand, zu dem
        // ein wiedergeoeffnetes Fenster zurueckkehrt. Verschweigen waere die
        // andere Sorte Unehrlichkeit.
        XCTAssertEqual(objekt["ansicht"] as? String, "quellen")
    }

    func testGrenzwertGenauEinFenster() throws {
        XCTAssertEqual(try zustand(fenster: 1)["sichtbar"] as? Bool, true)
        XCTAssertEqual(try zustand(fenster: 3)["sichtbar"] as? Bool, true)
    }

    private func zustand(fenster: Int) throws -> [String: Any] {
        let text = Steuerdeutung.zustandJSON(ansicht: "quellen", dienst: "laeuft",
                                             pid: 4711, fassung: "0.1.0",
                                             fenster: fenster, ansichten: ansichten)
        return try XCTUnwrap(
            try JSONSerialization.jsonObject(with: XCTUnwrap(text.data(using: .utf8))) as? [String: Any],
            "Die Zustandsantwort muss maschinell lesbar sein -- sonst prueft sie niemand")
    }

    // ── Dokument verbinden: nur ws(s)://127.0.0.1|localhost|::1 (Fund O2) ──
    //
    // docs/SICHERHEITSFUNDE_2026-08-14.md, Fund O2: der Befehl zum Verbinden
    // pruefte nur `scheme?.hasPrefix("ws")` -- jede fremde Adresse wurde
    // angenommen, und die App synchronisierte das Dokument dorthin.

    func testEigeneAdresseWirdAngenommen() {
        let r = deute("POST", "/dokument", koerper: #"{"adresse":"ws://127.0.0.1:4599"}"#)
        XCTAssertEqual(try? r.get(), .dokumentVerbinden(adresse: "ws://127.0.0.1:4599", geheimnis: ""))
    }

    func testLocalhostUndWssWerdenAngenommen() {
        XCTAssertNoThrow(try deute("POST", "/dokument", koerper: #"{"adresse":"wss://localhost:4599"}"#).get())
        XCTAssertNoThrow(try deute("POST", "/dokument", koerper: #"{"adresse":"ws://[::1]:4599"}"#).get())
    }

    func testFremdeAdresseWirdAbgelehnt() {
        let antwort = ablehnung(deute("POST", "/dokument", koerper: #"{"adresse":"wss://boese.example/ws"}"#))
        XCTAssertEqual(antwort.code, 400)
    }

    func testAdresseOhneSchemaWirdAbgelehnt() {
        XCTAssertEqual(ablehnung(deute("POST", "/dokument", koerper: #"{"adresse":"127.0.0.1:4599"}"#)).code, 400)
    }

    func testAdresseMitEingebettetemZeilenumbruchWirdAbgelehnt() {
        XCTAssertEqual(ablehnung(deute("POST", "/dokument",
            koerper: #"{"adresse":"ws://127.0.0.1:4599\nHost: boese.example"}"#)).code, 400)
    }

    func testNichtWsSchemaWirdAbgelehnt() {
        XCTAssertEqual(ablehnung(deute("POST", "/dokument", koerper: #"{"adresse":"http://127.0.0.1:4599"}"#)).code, 400)
    }

    func testIstLoopbackWebsocketAdresseGrenzwerte() {
        XCTAssertTrue(Steuerdeutung.istLoopbackWebsocketAdresse("ws://127.0.0.1:4599"))
        XCTAssertTrue(Steuerdeutung.istLoopbackWebsocketAdresse("wss://localhost:1"))
        XCTAssertFalse(Steuerdeutung.istLoopbackWebsocketAdresse("wss://boese.example/ws"))
        XCTAssertFalse(Steuerdeutung.istLoopbackWebsocketAdresse("127.0.0.1:4599"))
        XCTAssertFalse(Steuerdeutung.istLoopbackWebsocketAdresse("ws://127.0.0.1:4599\nX-Evil: 1"))
        XCTAssertFalse(Steuerdeutung.istLoopbackWebsocketAdresse(""))
    }

    // ── Hilfen ───────────────────────────────────────────────────────────

    private func deute(_ methode: String, _ pfad: String,
                       koerper: String = "") -> Result<Steuerbefehl, Steuerantwort> {
        Steuerdeutung.deute(methode: methode, pfad: pfad, koerper: koerper,
                            erlaubteAnsichten: ansichten)
    }

    private func ablehnung(_ r: Result<Steuerbefehl, Steuerantwort>) -> Steuerantwort {
        switch r {
        case .success(let b):
            XCTFail("Erwartet war eine Ablehnung, bekommen: \(b)")
            return Steuerantwort(code: 0, koerper: "")
        case .failure(let a):
            return a
        }
    }
}
