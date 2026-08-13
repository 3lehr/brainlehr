import XCTest
@testable import BrainlehrCore

/// Prueft die Drei-Wege-Verschmelzung.
///
/// Der Kern ist nicht, dass Text ankommt, sondern dass NICHTS VERSCHWINDET.
/// Genau das ist die Fehlerklasse bei zwei Schreibern: kein Absturz, keine
/// Meldung, der Absatz ist einfach weg. Jeder Test hier prueft deshalb auch,
/// dass die jeweils andere Fassung noch erreichbar ist.
final class VerschmelzungTests: XCTestCase {

    private let vor = "Erster Absatz.\n\nZweiter Absatz.\n\nDritter Absatz."

    // MARK: - Die vier Grundfaelle

    func testNiemandAendertEtwas() {
        let e = Verschmelzung.verschmelze(vorfassung: vor, mensch: vor, modell: vor)
        XCTAssertFalse(e.hatKonflikte)
        XCTAssertEqual(e.absaetze.map(\.herkunft), [.unveraendert, .unveraendert, .unveraendert])
        XCTAssertEqual(e.text, vor)
        XCTAssertNil(e.meldung, "Wo nichts zu entscheiden ist, wird nichts gemeldet")
    }

    func testNurDerMenschAendert() {
        let m = "Erster Absatz.\n\nZweiter Absatz, vom Menschen.\n\nDritter Absatz."
        let e = Verschmelzung.verschmelze(vorfassung: vor, mensch: m, modell: vor)
        XCTAssertFalse(e.hatKonflikte)
        XCTAssertEqual(e.absaetze[1].herkunft, .vomMenschen)
        XCTAssertEqual(e.text, m)
    }

    func testNurDasModellAendert() {
        let k = "Erster Absatz.\n\nZweiter Absatz, vom Modell.\n\nDritter Absatz."
        let e = Verschmelzung.verschmelze(vorfassung: vor, mensch: vor, modell: k)
        XCTAssertFalse(e.hatKonflikte)
        XCTAssertEqual(e.absaetze[1].herkunft, .vomModell)
        XCTAssertEqual(e.text, k)
    }

    /// DER Fall, um den es geht: beide gleichzeitig, verschiedene Absaetze.
    /// Ohne Verschmelzung wuerde eine der beiden Aenderungen still
    /// ueberschrieben -- je nachdem, wer zuletzt speichert.
    func testBeideAendernVerschiedeneAbsaetzeOhneKonflikt() {
        let m = "Erster Absatz, vom Menschen.\n\nZweiter Absatz.\n\nDritter Absatz."
        let k = "Erster Absatz.\n\nZweiter Absatz.\n\nDritter Absatz, vom Modell."
        let e = Verschmelzung.verschmelze(vorfassung: vor, mensch: m, modell: k)
        XCTAssertFalse(e.hatKonflikte, "Verschiedene Absaetze sind kein Konflikt")
        XCTAssertEqual(e.absaetze.map(\.herkunft), [.vomMenschen, .unveraendert, .vomModell])
        XCTAssertTrue(e.text.contains("vom Menschen"))
        XCTAssertTrue(e.text.contains("vom Modell"), "Die Aenderung des Modells darf nicht verschwinden")
    }

    // MARK: - Konflikt: beide, derselbe Absatz

    func testBeideAendernDenselbenAbsatz() {
        let m = "Erster Absatz.\n\nFassung des Menschen.\n\nDritter Absatz."
        let k = "Erster Absatz.\n\nFassung des Modells.\n\nDritter Absatz."
        let e = Verschmelzung.verschmelze(vorfassung: vor, mensch: m, modell: k)
        XCTAssertTrue(e.hatKonflikte)
        XCTAssertEqual(e.konflikte, 1)
        XCTAssertEqual(e.absaetze[1].herkunft, .konflikt)
        // Die Fassung des Menschen steht vorn -- wer selbst getippt hat, soll
        // seinen Text sehen und nicht suchen muessen.
        XCTAssertEqual(e.absaetze[1].text, "Fassung des Menschen.")
        // UND die andere ist noch da. Das ist der ganze Punkt.
        XCTAssertEqual(e.absaetze[1].andereFassung, "Fassung des Modells.")
        XCTAssertEqual(e.meldung, "Ein Absatz wurde von beiden Seiten geändert.")
    }

    func testGleicheAenderungIstKeinKonflikt() {
        let gleich = "Erster Absatz.\n\nBeide schreiben dasselbe.\n\nDritter Absatz."
        let e = Verschmelzung.verschmelze(vorfassung: vor, mensch: gleich, modell: gleich)
        XCTAssertFalse(e.hatKonflikte, "Einigkeit ist kein Konflikt")
        XCTAssertEqual(e.absaetze[1].herkunft, .unveraendert)
    }

    func testMehrereKonflikteWerdenGezaehlt() {
        let m = "A vom Menschen.\n\nB vom Menschen.\n\nDritter Absatz."
        let k = "A vom Modell.\n\nB vom Modell.\n\nDritter Absatz."
        let e = Verschmelzung.verschmelze(vorfassung: vor, mensch: m, modell: k)
        XCTAssertEqual(e.konflikte, 2)
        XCTAssertEqual(e.meldung, "2 Absätze wurden von beiden Seiten geändert.")
    }

    // MARK: - Loeschen und Anhaengen: nichts faellt hinten runter

    func testAngehaengterAbsatzGehtNichtVerloren() {
        let m = vor + "\n\nVierter Absatz, vom Menschen."
        let e = Verschmelzung.verschmelze(vorfassung: vor, mensch: m, modell: vor)
        XCTAssertEqual(e.absaetze.count, 4)
        XCTAssertEqual(e.absaetze[3].herkunft, .vomMenschen)
    }

    /// Beide haengen hinten etwas an -- das sind ZWEI BEITRAEGE, nicht zwei
    /// Fassungen desselben. Ohne Beleg fuer das Gegenteil gilt die
    /// informationserhaltende Lesart: beide bleiben (Lehre L-014f8f, dort an
    /// zwei Vertragsentwuerfen desselben Absenders gemessen -- die Lesart
    /// "der neue ersetzt den alten" vernichtete eine Wahlmoeglichkeit, die
    /// dem Gremium zustand).
    func testBeideHaengenAnUndBeidesBleibt() {
        let m = vor + "\n\nVierter, vom Menschen."
        let k = vor + "\n\nVierter, vom Modell."
        let e = Verschmelzung.verschmelze(vorfassung: vor, mensch: m, modell: k)
        let texte = e.absaetze.map(\.text)
        XCTAssertTrue(texte.contains("Vierter, vom Menschen."))
        XCTAssertTrue(texte.contains("Vierter, vom Modell."), "nichts darf verschwinden")
        XCTAssertFalse(e.hatKonflikte, "zwei Beitraege sind kein Konflikt")
        // Der Vorschlag des Modells bleibt aber als solcher erkennbar und
        // damit ablehnbar.
        XCTAssertEqual(e.absaetze.last?.herkunft, .vomModell)
    }

    // MARK: - Live-Vorschlaege: das Modell schlaegt vor, der Mensch entscheidet

    /// Der Regelfall der Live-Bearbeitung, wie der Betreiber ihn beschrieben
    /// hat: "ki macht live vorschlaege, mensch darf live korrigieren und
    /// schreiben". Ein Vorschlag, den man nur ansehen, aber nicht ablehnen
    /// kann, ist keiner.
    func testVorschlagDesModellsIstAblehnbar() {
        let k = "Erster Absatz.\n\nZweiter Absatz, besser formuliert.\n\nDritter Absatz."
        let e = Verschmelzung.verschmelze(vorfassung: vor, mensch: vor, modell: k)
        XCTAssertEqual(e.absaetze[1].herkunft, .vomModell)
        XCTAssertEqual(e.absaetze[1].andereFassung, "Zweiter Absatz.",
                       "die Vorfassung muss erreichbar bleiben, sonst ist Ablehnen unmoeglich")

        let abgelehnt = Verschmelzung.entscheide(e, absatz: 1, wahl: .mensch)
        XCTAssertEqual(abgelehnt.absaetze[1].text, "Zweiter Absatz.")
        XCTAssertEqual(abgelehnt.absaetze[1].herkunft, .vomMenschen)

        let angenommen = Verschmelzung.entscheide(e, absatz: 1, wahl: .modell)
        XCTAssertEqual(angenommen.absaetze[1].text, "Zweiter Absatz, besser formuliert.")
    }

    func testMenschSchreibtWaehrendDasModellAnAndererStelleVorschlaegt() {
        // Beide gleichzeitig, verschiedene Absaetze -- niemand wird gebremst,
        // niemand verliert etwas, keine Rueckfrage.
        let m = "Erster Absatz, vom Menschen getippt.\n\nZweiter Absatz.\n\nDritter Absatz."
        let k = "Erster Absatz.\n\nZweiter Absatz, Vorschlag.\n\nDritter Absatz."
        let e = Verschmelzung.verschmelze(vorfassung: vor, mensch: m, modell: k)
        XCTAssertFalse(e.hatKonflikte)
        XCTAssertEqual(e.absaetze[0].herkunft, .vomMenschen)
        XCTAssertEqual(e.absaetze[1].herkunft, .vomModell)
        XCTAssertTrue(e.text.contains("vom Menschen getippt"))
        XCTAssertTrue(e.text.contains("Vorschlag"))
    }

    func testEinseitigesLoeschenWirdUebernommen() {
        let m = "Erster Absatz.\n\nDritter Absatz."   // zweiter gestrichen
        let e = Verschmelzung.verschmelze(vorfassung: vor, mensch: m, modell: vor)
        XCTAssertEqual(e.absaetze.map(\.text), ["Erster Absatz.", "Dritter Absatz."])
        XCTAssertFalse(e.hatKonflikte)
    }

    /// DER Fall, der die positionsbasierte Zuordnung erledigt hat -- gemessen,
    /// nicht vermutet: Loescht der Mensch B und aendert das Modell C, dann
    /// verschiebt sich beim Menschen alles um eins. Ueber die Position
    /// verglichen wird C einmal als Aenderung des Menschen und einmal als
    /// Aenderung des Modells gefuehrt: der Absatz erscheint ZWEIMAL.
    ///
    /// In einem Rechtstext ist ein verdoppelter Absatz genauso falsch wie ein
    /// verlorener, nur auffaelliger.
    func testLoeschenAufDerEinenUndAendernAufDerAnderenSeiteVerdoppeltNichts() {
        let m = "Erster Absatz.\n\nDritter Absatz."                       // B weg
        let k = "Erster Absatz.\n\nZweiter Absatz.\n\nDritter, geaendert." // C geaendert
        let e = Verschmelzung.verschmelze(vorfassung: vor, mensch: m, modell: k)

        let texte = e.absaetze.map(\.text)
        XCTAssertEqual(Set(texte).count, texte.count, "kein Absatz darf doppelt vorkommen: \(texte)")
        XCTAssertFalse(texte.contains("Dritter Absatz."),
                       "die unveraenderte Fassung von C darf nicht neben der geaenderten stehen")
        XCTAssertTrue(texte.contains("Dritter, geaendert."),
                      "die Aenderung des Modells darf nicht verlorengehen")
    }

    func testVerschobeneAbsaetzeBleibenErkennbar() {
        // Der Mensch haengt vorn etwas an -- alles rutscht, nichts aendert sich.
        let m = "Null.\n\n" + vor
        let e = Verschmelzung.verschmelze(vorfassung: vor, mensch: m, modell: vor)
        XCTAssertFalse(e.hatKonflikte, "Ein Einschub ist keine Aenderung der uebrigen Absaetze")
        XCTAssertTrue(e.text.contains("Null."))
        XCTAssertTrue(e.text.contains("Dritter Absatz."))
    }

    func testBeidseitigesLoeschenLaesstNichtsUebrig() {
        let e = Verschmelzung.verschmelze(vorfassung: vor, mensch: "", modell: "")
        XCTAssertTrue(e.absaetze.isEmpty)
        XCTAssertFalse(e.hatKonflikte, "Einigkeit ueber das Loeschen ist kein Konflikt")
    }

    // MARK: - Entscheiden

    func testKonfliktLaesstSichZugunstenJederSeiteAufloesen() {
        let m = "Erster Absatz.\n\nMensch.\n\nDritter Absatz."
        let k = "Erster Absatz.\n\nModell.\n\nDritter Absatz."
        let e = Verschmelzung.verschmelze(vorfassung: vor, mensch: m, modell: k)

        let fuerMensch = Verschmelzung.entscheide(e, absatz: 1, wahl: .mensch)
        XCTAssertFalse(fuerMensch.hatKonflikte)
        XCTAssertEqual(fuerMensch.absaetze[1].text, "Mensch.")

        let fuerModell = Verschmelzung.entscheide(e, absatz: 1, wahl: .modell)
        XCTAssertFalse(fuerModell.hatKonflikte)
        XCTAssertEqual(fuerModell.absaetze[1].text, "Modell.")

        let beide = Verschmelzung.entscheide(e, absatz: 1, wahl: .beide)
        XCTAssertFalse(beide.hatKonflikte)
        XCTAssertTrue(beide.absaetze[1].text.contains("Mensch."))
        XCTAssertTrue(beide.absaetze[1].text.contains("Modell."))
    }

    func testEntscheidenLaesstAndereAbsaetzeUnberuehrt() {
        let m = "A vom Menschen.\n\nB vom Menschen.\n\nDritter Absatz."
        let k = "A vom Modell.\n\nB vom Modell.\n\nDritter Absatz."
        let e = Verschmelzung.verschmelze(vorfassung: vor, mensch: m, modell: k)
        let nach = Verschmelzung.entscheide(e, absatz: 0, wahl: .modell)
        XCTAssertEqual(nach.konflikte, 1, "Der zweite Konflikt bleibt offen")
        XCTAssertEqual(nach.absaetze[1].herkunft, .konflikt)
    }

    func testUnsinnigeEntscheidungAendertNichts() {
        let e = Verschmelzung.verschmelze(vorfassung: vor, mensch: vor, modell: vor)
        XCTAssertEqual(Verschmelzung.entscheide(e, absatz: 99, wahl: .mensch), e)
        XCTAssertEqual(Verschmelzung.entscheide(e, absatz: -1, wahl: .mensch), e)
        // Auf einem konfliktfreien Absatz gibt es nichts zu entscheiden.
        XCTAssertEqual(Verschmelzung.entscheide(e, absatz: 0, wahl: .modell), e)
    }

    // MARK: - Absatzzerlegung

    func testLeerraumUndLeerzeilenStoerenNicht() {
        XCTAssertEqual(Verschmelzung.absaetze("  A  \n\n\n\n  B  "), ["A", "B"])
        XCTAssertEqual(Verschmelzung.absaetze(""), [])
        XCTAssertEqual(Verschmelzung.absaetze("\n\n\n"), [])
    }

    /// Der Grund fuer Absatz statt Zeile: Ein Rechtstext wird absatzweise
    /// umformuliert. Zeilenweise verglichen erzeugt jede Umbruchaenderung
    /// einen Scheinkonflikt -- und wer drei davon weggeklickt hat, klickt den
    /// vierten echten mit weg.
    func testUmbruchInnerhalbEinesAbsatzesIstKeinKonflikt() {
        let alt = "Ein Satz.\nEine zweite Zeile.\n\nZweiter Absatz."
        let neu = "Ein Satz. Eine zweite Zeile.\n\nZweiter Absatz."
        let e = Verschmelzung.verschmelze(vorfassung: alt, mensch: neu, modell: alt)
        XCTAssertFalse(e.hatKonflikte)
        XCTAssertEqual(e.absaetze.count, 2)
    }
}
