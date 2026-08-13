import XCTest
@testable import BrainlehrCore

/// Prueft die beiden Ordnungen des Dateibrowsers.
///
/// Der wichtigste Test ist nicht "sortiert richtig", sondern: **Was der
/// Betrachter nicht sehen darf, taucht nirgends auf -- auch nicht als Luecke
/// und auch nicht in einer Zahl.**
final class RangfolgeTests: XCTestCase {

    private let gast = Betrachter(name: "G", rollen: [], stufe: .oeffentlich)
    private let betreiber = Betrachter(name: "B", rollen: ["betreiber"], stufe: .vollstaendig)

    private var bestand: [Quellenzeile] {
        [
            .init(nummer: "1", kurz: "Teilungserklärung 1982, Aufteilung in Wohneinheiten",
                  art: "vertrag", freigabe: "offen", markierbar: false, rang: 1),
            .init(nummer: "2", kurz: "Volksbank Verwaltervertrag Grundvergütung 50,00 Euro",
                  art: "vertrag", freigabe: "offen", markierbar: true, rang: 3),
            .init(nummer: "12", kurz: "§ 16 WEG abweichende Kostenverteilung Beschluss",
                  art: "gesetz", freigabe: "offen", markierbar: true, rang: 2),
            .init(nummer: "20", kurz: "Protokoll Eigentümerversammlung Heizung",
                  art: "protokoll", freigabe: "intern", markierbar: true, rang: 5),
            .init(nummer: "42", kurz: "Rechtsfall mit Namen Dritter",
                  art: "urteil", freigabe: "gesperrt", markierbar: true, rang: 1),
        ]
    }

    // MARK: - Die harte Regel

    /// Gefiltert wird VOR dem Sortieren. Wer danach filtert, verraet ueber
    /// Luecken in der Reihenfolge oder ueber eine Gesamtzahl, DASS es etwas
    /// gibt -- und bei Namen Dritter ist schon das eine Aussage.
    func testWasNichtSichtbarIstTauchtInKEINERListeAuf() {
        for ordnung in Ordnung.allCases {
            let liste = Rangfolge.liste(bestand, ordnung: ordnung, betrachter: gast,
                                        lagewoerter: ["kosten", "beschluss"])
            let nummern = liste.map(\.zeile.nummer)
            XCTAssertFalse(nummern.contains("20"), "\(ordnung): internes durchgelassen")
            XCTAssertFalse(nummern.contains("42"), "\(ordnung): gesperrtes durchgelassen")
            XCTAssertEqual(liste.count, 3, "\(ordnung): Anzahl verraet die verborgenen")
            // Und in keiner Begruendung darf der verborgene Titel auftauchen.
            for p in liste {
                XCTAssertFalse(p.begruendung.contains("Dritter"))
            }
        }
    }

    func testDerBetreiberSiehtAlles() {
        let liste = Rangfolge.liste(bestand, ordnung: .thematisch, betrachter: betreiber)
        XCTAssertEqual(liste.count, 5)
    }

    // MARK: - Thematisch: stabil

    func testThematischIstStabilUndUnabhaengigVonDerLage() {
        let a = Rangfolge.liste(bestand, ordnung: .thematisch, betrachter: betreiber,
                                lagewoerter: ["heizung"])
        let b = Rangfolge.liste(bestand, ordnung: .thematisch, betrachter: betreiber,
                                lagewoerter: ["kosten", "vergütung"])
        XCTAssertEqual(a.map(\.zeile.nummer), b.map(\.zeile.nummer),
                       "Die thematische Ordnung darf sich durch die Lage NIE ändern")
    }

    func testRechtStehtVorVertragUndVertragVorProtokoll() {
        let n = Rangfolge.liste(bestand, ordnung: .thematisch, betrachter: betreiber)
            .map(\.zeile.art)
        XCTAssertEqual(n.first, "gesetz", "Bei einer Rechtsfrage ist die Norm die Grundlage")
        XCTAssertEqual(n.last, "protokoll")
    }

    // MARK: - Nach Lage: was gerade zaehlt

    func testPassendeQuelleSteigtNachOben() {
        let lage: Set<String> = ["kostenverteilung", "beschluss", "abweichende"]
        let liste = Rangfolge.liste(bestand, ordnung: .nachLage, betrachter: betreiber,
                                    lagewoerter: lage)
        XCTAssertEqual(liste.first?.zeile.nummer, "12",
                       "die zum Thema passende Quelle gehört nach oben")
        XCTAssertTrue(liste.first!.begruendung.contains("passt zu"))
    }

    func testEineAndereLageErgibtEineAndereReihenfolge() {
        let a = Rangfolge.liste(bestand, ordnung: .nachLage, betrachter: betreiber,
                                lagewoerter: ["kostenverteilung", "beschluss"])
        let b = Rangfolge.liste(bestand, ordnung: .nachLage, betrachter: betreiber,
                                lagewoerter: ["grundvergütung", "volksbank"])
        XCTAssertNotEqual(a.map(\.zeile.nummer), b.map(\.zeile.nummer),
                          "sonst wäre die Lage wirkungslos")
        XCTAssertEqual(b.first?.zeile.nummer, "2")
    }

    /// Ohne Bezug wird keine Reihenfolge erfunden -- das waere Rauschen, das
    /// wie ein Urteil aussieht.
    func testOhneLageFaelltEsAufDieThematischeOrdnungZurueck() {
        let ohne = Rangfolge.liste(bestand, ordnung: .nachLage, betrachter: betreiber,
                                   lagewoerter: [])
        let thema = Rangfolge.liste(bestand, ordnung: .thematisch, betrachter: betreiber)
        XCTAssertEqual(ohne.map(\.zeile.nummer), thema.map(\.zeile.nummer))
        XCTAssertTrue(ohne.first!.begruendung.contains("kein Bezug"))
    }

    func testJederPlatzTraegtEineBegruendung() {
        // Eine Rangfolge, die niemand erklären kann, ist am Tisch wertlos.
        for p in Rangfolge.liste(bestand, ordnung: .nachLage, betrachter: betreiber,
                                 lagewoerter: ["heizung"]) {
            XCTAssertFalse(p.begruendung.isEmpty, "Quelle \(p.zeile.nummer) ohne Begründung")
        }
    }

    func testBekannteStelleGibtEinenVorsprung() {
        // Gleiche Gattung, gleicher Bezug -- die mit bekannter Stelle gewinnt,
        // weil sie sich sofort zeigen laesst.
        let zwei: [Quellenzeile] = [
            .init(nummer: "1", kurz: "Heizung Kessel Austausch", art: "angebot", markierbar: false),
            .init(nummer: "2", kurz: "Heizung Kessel Austausch", art: "angebot", markierbar: true),
        ]
        let liste = Rangfolge.nachLage(zwei, lagewoerter: ["heizung", "kessel"])
        XCTAssertEqual(liste.first?.zeile.nummer, "2")
        XCTAssertTrue(liste.first!.begruendung.contains("Stelle bekannt"))
    }

    func testGleichstandBleibtStabilStattZuSpringen() {
        let gleich: [Quellenzeile] = [
            .init(nummer: "7", kurz: "ohne Bezug", art: "vertrag"),
            .init(nummer: "3", kurz: "ohne Bezug", art: "vertrag"),
            .init(nummer: "5", kurz: "ohne Bezug", art: "gesetz"),
        ]
        let a = Rangfolge.nachLage(gleich, lagewoerter: ["heizung"]).map(\.zeile.nummer)
        let b = Rangfolge.nachLage(gleich.reversed(), lagewoerter: ["heizung"]).map(\.zeile.nummer)
        XCTAssertEqual(a, b, "bei Gleichstand darf die Liste nicht springen")
        XCTAssertEqual(a, ["5", "3", "7"])
    }

    // MARK: - Stichwoerter

    func testFuellwoerterZaehlenNicht() {
        let w = Rangfolge.stichwoerter("Der Verwalter ist für die Kosten und das Protokoll da")
        XCTAssertTrue(w.contains("verwalter") && w.contains("protokoll") && w.contains("kosten"))
        for f in ["der", "ist", "für", "und", "das"] { XCTAssertFalse(w.contains(f)) }
        // Kurze Wörter fliegen ebenfalls raus -- "da" trägt nichts.
        XCTAssertFalse(w.contains("da"))
    }

    func testLageKommtNurAusGespraechUndDenken() {
        // Werkzeugnamen und Rückgaben sagen nichts über das Thema:
        // "Bash" und "48 Quellen" sind kein Bezug.
        let strom: [Sitzungsereignis] = [
            .init(art: .eingabe, text: "Wie ist die Kostenverteilung geregelt?"),
            .init(art: .werkzeug, text: "Bash", werkzeug: "Bash"),
            .init(art: .ergebnis, text: "Heizungsanlage Kesseltausch Angebot"),
            .init(art: .denken, text: "Der Beschluss braucht Mehrheit"),
        ]
        let lage = Rangfolge.lageAus(strom)
        XCTAssertTrue(lage.contains("kostenverteilung"))
        XCTAssertTrue(lage.contains("beschluss"))
        XCTAssertFalse(lage.contains("bash"))
        XCTAssertFalse(lage.contains("heizungsanlage"), "Werkzeug-Rückgaben sind kein Thema")
    }

    func testNurDieJuengstenEreignisseZaehlen() {
        var strom: [Sitzungsereignis] = (1...30).map {
            .init(art: .antwort, text: "altthema\($0) Verwaltung")
        }
        strom.append(.init(art: .eingabe, text: "neuthema Kostenverteilung"))
        let lage = Rangfolge.lageAus(strom, juengste: 3)
        XCTAssertTrue(lage.contains("neuthema"))
        XCTAssertFalse(lage.contains("altthema1"),
                       "was vor einer Stunde besprochen wurde, ist kein Bezug mehr")
    }

    func testLeererStromErgibtKeineLage() {
        XCTAssertTrue(Rangfolge.lageAus([]).isEmpty)
    }
}
