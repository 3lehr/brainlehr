import XCTest
@testable import BrainlehrCore

/// Prueft die Zerlegung des Sitzungsstroms.
///
/// Die Proben sind der ECHTEN Datei nachgebildet (Feldnamen am 2026-08-13
/// gemessen: timestamp, message.role, content-Bloecke thinking/text/tool_use/
/// tool_result). Der wichtigste Test ist nicht, dass Gespraech ankommt,
/// sondern dass SYSTEMTEXT NICHT ankommt -- er steht in denselben Feldern wie
/// eine echte Eingabe.
final class SitzungsstromTests: XCTestCase {

    private func zeile(rolle: String, bloecke: String, zeit: String = "2026-08-13T17:00:00.000Z") -> String {
        """
        {"type":"assistant","timestamp":"\(zeit)","message":{"role":"\(rolle)","content":[\(bloecke)]}}
        """
    }

    // MARK: - Die vier Blockarten

    func testDenkenWirdErkannt() {
        let e = Sitzungsstrom.zerlege(zeile(rolle: "assistant",
                                            bloecke: #"{"type":"thinking","thinking":"Erst messen, dann bauen.","signature":"x"}"#))
        XCTAssertEqual(e.count, 1)
        XCTAssertEqual(e[0].art, .denken)
        XCTAssertEqual(e[0].text, "Erst messen, dann bauen.")
        XCTAssertNotNil(e[0].zeitpunkt)
    }

    func testAntwortUndEingabeWerdenNachRolleGetrennt() {
        let a = Sitzungsstrom.zerlege(zeile(rolle: "assistant", bloecke: #"{"type":"text","text":"Fertig."}"#))
        XCTAssertEqual(a[0].art, .antwort)
        let u = Sitzungsstrom.zerlege(zeile(rolle: "user", bloecke: #"{"type":"text","text":"Bau das."}"#))
        XCTAssertEqual(u[0].art, .eingabe)
    }

    func testWerkzeugTraegtSeinenNamen() {
        let e = Sitzungsstrom.zerlege(zeile(rolle: "assistant",
                                            bloecke: #"{"type":"tool_use","id":"t1","name":"Read","input":{}}"#))
        XCTAssertEqual(e[0].art, .werkzeug)
        XCTAssertEqual(e[0].werkzeug, "Read")
    }

    func testWerkzeugergebnisAlsTextUndAlsBloecke() {
        let alsText = Sitzungsstrom.zerlege(zeile(rolle: "user",
                                                  bloecke: #"{"type":"tool_result","tool_use_id":"t1","content":"48 Quellen"}"#))
        XCTAssertEqual(alsText[0].art, .ergebnis)
        XCTAssertEqual(alsText[0].text, "48 Quellen")
        let alsBloecke = Sitzungsstrom.zerlege(zeile(rolle: "user",
                                                     bloecke: #"{"type":"tool_result","tool_use_id":"t1","content":[{"type":"text","text":"30 markierbar"}]}"#))
        XCTAssertEqual(alsBloecke[0].text, "30 markierbar")
    }

    func testEineZeileKannMehrereEreignisseTragen() {
        // Der Normalfall: Denken, dann Text, dann zwei Werkzeuge.
        let e = Sitzungsstrom.zerlege(zeile(rolle: "assistant", bloecke: """
        {"type":"thinking","thinking":"Nachsehen."},
        {"type":"text","text":"Ich messe das."},
        {"type":"tool_use","id":"a","name":"Bash","input":{}},
        {"type":"tool_use","id":"b","name":"Read","input":{}}
        """))
        XCTAssertEqual(e.map(\.art), [.denken, .antwort, .werkzeug, .werkzeug])
    }

    // MARK: - DER wichtigste Test: Systemtext ist kein Gespraech

    func testSystemtextErscheintNichtAlsEingabe() {
        // Erinnerungen, Haken-Ausgaben und eingespieltes Wissen stehen in
        // DENSELBEN Feldern wie eine echte Eingabe. Wer sie mitzeigt, laesst
        // den Betreiber Saetze lesen, die er nie geschrieben hat -- und vor
        // anderen Menschen sieht das aus, als haette er sie geschrieben.
        for marke in ["<system-reminder>Denk an X</system-reminder>",
                      "<knowledge-recall>Aus dem Speicher</knowledge-recall>",
                      "<persisted-output>zu gross</persisted-output>",
                      "<command-name>caveman</command-name>"] {
            let json = "{\"type\":\"user\",\"message\":{\"role\":\"user\",\"content\":\"\(marke)\"}}"
            XCTAssertTrue(Sitzungsstrom.zerlege(json).isEmpty, "durchgelassen: \(marke)")
        }
    }

    func testEchteEingabeMitSpitzenKlammernBleibt() {
        // Gegenprobe: nicht jede spitze Klammer ist Systemtext.
        let json = #"{"type":"user","message":{"role":"user","content":"nimm <b> raus aus dem HTML"}}"#
        let e = Sitzungsstrom.zerlege(json)
        XCTAssertEqual(e.count, 1)
        XCTAssertEqual(e[0].art, .eingabe)
    }

    // MARK: - Robustheit: die Datei waechst waehrend des Lesens

    func testUnvollstaendigeUndFremdeZeilenErgebenNichts() {
        XCTAssertTrue(Sitzungsstrom.zerlege("").isEmpty)
        XCTAssertTrue(Sitzungsstrom.zerlege("{\"type\":\"assis").isEmpty, "halbe Zeile ist der Normalfall")
        XCTAssertTrue(Sitzungsstrom.zerlege(#"{"type":"queue-operation"}"#).isEmpty)
        XCTAssertTrue(Sitzungsstrom.zerlege(#"{"type":"attachment","message":{}}"#).isEmpty)
        XCTAssertTrue(Sitzungsstrom.zerlege("kein json").isEmpty)
    }

    func testLeereTexteWerdenVerworfen() {
        let e = Sitzungsstrom.zerlege(zeile(rolle: "assistant",
                                            bloecke: #"{"type":"text","text":"   \n  "}"#))
        XCTAssertTrue(e.isEmpty, "Leerraum ist kein Ereignis")
    }

    // MARK: - Ausfuehrlichkeit

    func testStufenZeigenUnterschiedlichViel() {
        let alle: [Sitzungsereignis] = [
            .init(art: .eingabe, text: "bau das"),
            .init(art: .denken, text: "erst messen"),
            .init(art: .werkzeug, text: "Bash", werkzeug: "Bash"),
            .init(art: .ergebnis, text: "48 Quellen"),
            .init(art: .antwort, text: "fertig"),
        ]
        XCTAssertEqual(Sitzungsstrom.gefiltert(alle, .knapp).map(\.art), [.eingabe, .antwort])
        XCTAssertEqual(Sitzungsstrom.gefiltert(alle, .normal).map(\.art),
                       [.eingabe, .denken, .werkzeug, .antwort])
        XCTAssertEqual(Sitzungsstrom.gefiltert(alle, .voll).count, 5)
    }

    func testLangeStroemeWerdenHintenAbgeschnitten() {
        // Juengstes zuletzt -- wer scrollt, will das Neue sehen.
        let viele = (1...500).map { Sitzungsereignis(art: .antwort, text: "\($0)") }
        let g = Sitzungsstrom.gefiltert(viele, .knapp, hoechstens: 10)
        XCTAssertEqual(g.count, 10)
        XCTAssertEqual(g.last?.text, "500")
        XCTAssertEqual(g.first?.text, "491")
    }

    // MARK: - Das Denken-Fenster

    func testAktuellerSchrittIstDasLetzteWerkzeug() {
        let e: [Sitzungsereignis] = [
            .init(art: .eingabe, text: "los"),
            .init(art: .denken, text: "nachsehen"),
            .init(art: .werkzeug, text: "Read", werkzeug: "Read"),
        ]
        XCTAssertEqual(Sitzungsstrom.aktuellerSchritt(e), "Read")
    }

    func testNachEinerAntwortLaeuftNichtsMehr() {
        // Sonst bliebe der letzte Werkzeugname stehen und sae­he aus, als
        // arbeite die App noch -- eine Anzeige, die etwas Falsches behauptet,
        // ist schlechter als eine leere.
        let e: [Sitzungsereignis] = [
            .init(art: .werkzeug, text: "Bash", werkzeug: "Bash"),
            .init(art: .ergebnis, text: "ok"),
            .init(art: .antwort, text: "fertig"),
        ]
        XCTAssertNil(Sitzungsstrom.aktuellerSchritt(e))
    }

    func testErgebnisseUeberspringenBisZumWerkzeug() {
        let e: [Sitzungsereignis] = [
            .init(art: .werkzeug, text: "Grep", werkzeug: "Grep"),
            .init(art: .ergebnis, text: "3 Treffer"),
            .init(art: .ergebnis, text: "noch was"),
        ]
        XCTAssertEqual(Sitzungsstrom.aktuellerSchritt(e), "Grep")
    }

    func testLeererStromZeigtNichts() {
        XCTAssertNil(Sitzungsstrom.aktuellerSchritt([]))
    }
}
