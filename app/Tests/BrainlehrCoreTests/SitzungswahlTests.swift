import XCTest
@testable import BrainlehrCore

/// Prueft die Erkennung und Benennung paralleler Sitzungen.
///
/// ANLASS: Gemessen am 2026-08-13 schrieben in EINEM Projektordner zwei
/// Sitzungen gleichzeitig (6,2 MB vor 0,2 Minuten, 32,5 MB vor 5,6 Minuten).
/// "Die zuletzt geaenderte" springt zwischen beiden hin und her.
final class SitzungswahlTests: XCTestCase {

    // MARK: - Deuten einer Zeile

    func testTitelWirdErkannt() {
        let (t, e) = Sitzungswahl.deute(#"{"type":"custom-title","title":"Multiview plan review"}"#)
        XCTAssertEqual(t, "Multiview plan review")
        XCTAssertNil(e)
    }

    func testEingabeWirdErkannt() {
        let (t, e) = Sitzungswahl.deute(
            #"{"type":"user","message":{"role":"user","content":"bau mir den browser"}}"#)
        XCTAssertNil(t)
        XCTAssertEqual(e, "bau mir den browser")
    }

    func testEingabeAusBloeckenWirdErkannt() {
        let (_, e) = Sitzungswahl.deute(
            #"{"type":"user","message":{"role":"user","content":[{"type":"text","text":"zwei Teile"}]}}"#)
        XCTAssertEqual(e, "zwei Teile")
    }

    /// Eine Sitzung, benannt nach einem Satz, den der Betreiber nie
    /// geschrieben hat, waere schlimmer als eine namenlose.
    func testSystemtextWirdNichtZurBeschriftung() {
        for marke in ["<system-reminder>Denk dran</system-reminder>",
                      "<knowledge-recall>Aus dem Speicher</knowledge-recall>"] {
            let json = "{\"type\":\"user\",\"message\":{\"role\":\"user\",\"content\":\"\(marke)\"}}"
            let (_, e) = Sitzungswahl.deute(json)
            XCTAssertNil(e, "durchgelassen: \(marke)")
        }
    }

    func testWeitereSystemmarkenWerdenErkannt() {
        // Am echten Strom nachgezogen: <task-notification> erschien als
        // Eingabe und wurde in der Auswahl zur Beschriftung einer Sitzung.
        for marke in ["<task-notification>Agent fertig</task-notification>",
                      "<cross-session-message>von der anderen Sitzung</cross-session-message>",
                      "<regelwechsel>Neue Norm</regelwechsel>"] {
            let json = "{\"type\":\"user\",\"message\":{\"role\":\"user\",\"content\":\"\(marke)\"}}"
            XCTAssertNil(Sitzungswahl.deute(json).eingabe, "durchgelassen: \(marke)")
            XCTAssertTrue(Sitzungsstrom.zerlege(json).isEmpty, "im Strom durchgelassen: \(marke)")
        }
    }

    func testFremdeUndHalbeZeilenErgebenNichts() {
        for z in ["", "{halb", "kein json", #"{"type":"assistant"}"#,
                  #"{"type":"queue-operation"}"#] {
            let (t, e) = Sitzungswahl.deute(z)
            XCTAssertNil(t); XCTAssertNil(e)
        }
    }

    func testZeilenumbruecheInEinerEingabeWerdenGeglaettet() {
        let (_, e) = Sitzungswahl.deute(
            #"{"type":"user","message":{"role":"user","content":"erste Zeile\nzweite Zeile"}}"#)
        XCTAssertEqual(e, "erste Zeile zweite Zeile")
    }

    // MARK: - Projektname

    func testProjektnameWirdLesbar() {
        XCTAssertEqual(
            Sitzungswahl.projektname("-Volumes-daten-Begod2026-brainlehr--claude-worktrees"),
            "brainlehr")
        XCTAssertEqual(
            Sitzungswahl.projektname("-Volumes-daten-Begod2026-brainlehr--claude-worktrees-hallo-01e380"),
            "brainlehr · hallo")
        XCTAssertEqual(
            Sitzungswahl.projektname("-Volumes-daten-Begod2026-hub--claude-worktrees-testaufbau-fo1a2b"),
            "hub · testaufbau-fo1a2b".replacingOccurrences(of: "-fo1a2b", with: ""))
    }

    func testUnbekannteFormeStuerzenNichtAb() {
        XCTAssertEqual(Sitzungswahl.projektname(""), "")
        XCTAssertEqual(Sitzungswahl.projektname("irgendwas"), "irgendwas")
    }

    // MARK: - Beschriftung: nie leer, nie mehrdeutig

    func testBeschriftungFaelltSinnvollZurueck() {
        let mitTitel = Sitzungskennung(pfad: "/a", titel: "BRAINLEHR", letzteEingabe: "egal",
                                       zuletztAktiv: Date(), projekt: "brainlehr")
        XCTAssertEqual(mitTitel.beschriftung, "BRAINLEHR")

        // DIE EINGABE DES MENSCHEN DARF NIE ZUR BESCHRIFTUNG WERDEN: Die
        // Auswahl zeigt Chats ALLER Projekte, darunter buckeberg mit Namen
        // Dritter. Gemessen trugen 15 von 15 Sitzungen der letzten 24 Stunden
        // keinen Titel -- der Fall ist also der Regelfall, nicht die Ausnahme.
        let ohneTitel = Sitzungskennung(pfad: "/b", titel: "",
                                        letzteEingabe: "diana kunzmann, michael weier",
                                        zuletztAktiv: Date(), projekt: "buckeberg")
        XCTAssertFalse(ohneTitel.beschriftung.lowercased().contains("kunzmann"),
                       "Namen Dritter dürfen nicht in der Auswahlliste stehen")
        XCTAssertEqual(ohneTitel.beschriftung, "buckeberg — ohne Titel")

        let nackt = Sitzungskennung(pfad: "/c", titel: "", letzteEingabe: "",
                                    zuletztAktiv: Date(), projekt: "hub")
        XCTAssertEqual(nackt.beschriftung, "hub — ohne Titel")

        let ganzNackt = Sitzungskennung(pfad: "/d", titel: "", letzteEingabe: "",
                                        zuletztAktiv: Date(), projekt: "")
        XCTAssertFalse(ganzNackt.beschriftung.isEmpty,
                       "eine namenlose Zeile waere nicht auswählbar")
    }

    func testLageNenntProjektUndAlter() {
        let jetzt = Date()
        let s = Sitzungskennung(pfad: "/a", titel: "T", letzteEingabe: "",
                                zuletztAktiv: jetzt.addingTimeInterval(-300),
                                projekt: "brainlehr")
        XCTAssertEqual(s.lage(jetzt: jetzt), "brainlehr · vor 5 Min")

        let frisch = Sitzungskennung(pfad: "/b", titel: "T", letzteEingabe: "",
                                     zuletztAktiv: jetzt, projekt: "hub")
        XCTAssertEqual(frisch.lage(jetzt: jetzt), "hub · gerade eben")

        let alt = Sitzungskennung(pfad: "/c", titel: "T", letzteEingabe: "",
                                  zuletztAktiv: jetzt.addingTimeInterval(-7200), projekt: "")
        XCTAssertEqual(alt.lage(jetzt: jetzt), "vor 2 Std")
    }

    // MARK: - Sortierung

    func testJuengsteStehtObenAberWirdNichtGewaehlt() {
        let jetzt = Date()
        let liste = [
            Sitzungskennung(pfad: "/alt", titel: "alt", letzteEingabe: "",
                            zuletztAktiv: jetzt.addingTimeInterval(-600), projekt: "p"),
            Sitzungskennung(pfad: "/neu", titel: "neu", letzteEingabe: "",
                            zuletztAktiv: jetzt, projekt: "p"),
        ]
        let s = Sitzungswahl.sortiert(liste)
        XCTAssertEqual(s.map(\.titel), ["neu", "alt"])
        // Die Reihenfolge ist ein VORSCHLAG. Dass hier nichts automatisch
        // gewaehlt wird, ist der ganze Punkt: Welcher Chat zaehlt, weiss nur
        // der Mensch -- und eine Anzeige, die es errät und falsch liegt, ist
        // schlimmer als eine, die fragt.
        XCTAssertEqual(s.count, liste.count, "sortieren darf nichts wegfiltern")
    }
}
