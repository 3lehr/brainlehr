import XCTest
@testable import BrainlehrCore

/// Prueft die Entscheidungen VOR der Anzeige -- die vier Negativfaelle des
/// Konsils, jeder als eigener Test.
///
/// Der Kern: Nicht "wird angezeigt", sondern "wird das Richtige GESAGT, wenn
/// es nicht geht". Ein stiller Fehlschlag mitten in einer Besprechung ist
/// teurer als eine Fehlermeldung, weil er wie ein Ergebnis aussieht.
final class QuelldokumentTests: XCTestCase {

    // MARK: - Anzeigeweg nach Format

    func testFormateWerdenIhremKoennenNachZugeordnet() {
        XCTAssertEqual(Quelldokument.weg(fuer: "volksbank.pdf"), .pdf)
        XCTAssertEqual(Quelldokument.weg(fuer: "weg-16.html"), .text)
        XCTAssertEqual(Quelldokument.weg(fuer: "protokoll.txt"), .text)
        XCTAssertEqual(Quelldokument.weg(fuer: "screenshot.jpg"), .bild)
        // Grossschreibung darf nichts aendern -- Dateinamen kommen von aussen.
        XCTAssertEqual(Quelldokument.weg(fuer: "VOLKSBANK.PDF"), .pdf)
    }

    func testUnbekanntesFormatWirdBenanntStattStillAngenommen() {
        // Der gemessene Fall: Quick Look nimmt ".zzq" an und liefert ein
        // Symbol, das von Erfolg nicht zu unterscheiden ist. Darum die
        // Vorpruefung -- eine Liste des KOENNENS, keine des Ausschliessens.
        XCTAssertEqual(Quelldokument.weg(fuer: "unbekannt.zzq"), .unbekannt)
        XCTAssertEqual(Quelldokument.weg(fuer: "ohneendung"), .unbekannt)
        XCTAssertEqual(Quelldokument.weg(fuer: "vertrag.docx"), .unbekannt)
    }

    func testNurPdfUndTextKoennenHervorheben() {
        XCTAssertTrue(Anzeigeweg.pdf.kannHervorheben)
        XCTAssertTrue(Anzeigeweg.text.kannHervorheben)
        // Ein Bild traegt keinen Text -- ehrlich gesagt statt vorgetaeuscht.
        XCTAssertFalse(Anzeigeweg.bild.kannHervorheben)
        XCTAssertFalse(Anzeigeweg.unbekannt.kannHervorheben)
    }

    // MARK: - Die vier Negativfaelle

    func testGesperrtesPdfMeldetKennwortUndNichtKeineFundstelle() {
        // DER teuerste Fall, gemessen: Ein gesperrtes PDF ist nicht nil.
        // pageCount stimmt, eine Miniatur entsteht, die Suche liefert null
        // Treffer. Ohne diese Reihenfolge wird daraus stillschweigend
        // "keine Fundstelle".
        let b = Quelldokument.befund(dateiname: "geschuetzt.pdf", existiert: true,
                                     istGesperrt: true, istLesbar: false)
        XCTAssertEqual(b, .passwortNoetig)
        XCTAssertEqual(b.meldung, "Dieses Dokument ist mit einem Kennwort geschützt.")
        XCTAssertNotNil(b.handlung, "Eine Meldung ohne Handlung ist eine Sackgasse")
    }

    func testBeschaedigtesDokumentMeldetStattStillZuScheitern() {
        let b = Quelldokument.befund(dateiname: "kaputt.pdf", existiert: true,
                                     istGesperrt: false, istLesbar: false)
        XCTAssertEqual(b, .nichtLesbar)
        XCTAssertNotNil(b.meldung)
    }

    func testUnbekanntesFormatMeldetMitTypangabe() {
        let b = Quelldokument.befund(dateiname: "vertrag.docx", existiert: true)
        XCTAssertEqual(b, .formatUnbekannt(endung: "docx"))
        XCTAssertEqual(b.meldung, "Dateien vom Typ docx können hier nicht angezeigt werden.")
    }

    func testFehlendeDateiIstEinEigenerFall() {
        XCTAssertEqual(Quelldokument.befund(dateiname: "weg.pdf", existiert: false), .fehlt)
        XCTAssertEqual(Quelldokument.befund(dateiname: "", existiert: true), .fehlt)
        // Hier gibt es nichts zu tun -- also wird auch nichts angeboten.
        XCTAssertNil(Dokumentbefund.fehlt.handlung)
    }

    func testBereitesDokumentSchweigt() {
        let b = Quelldokument.befund(dateiname: "volksbank.pdf", existiert: true)
        XCTAssertEqual(b, .bereit)
        XCTAssertNil(b.meldung, "Wo nichts zu melden ist, wird nichts gemeldet")
        XCTAssertNil(b.handlung)
    }

    /// Die Reihenfolge ist bedeutungstragend, nicht Geschmack.
    func testGesperrtSchlaegtNichtLesbar() {
        let b = Quelldokument.befund(dateiname: "x.pdf", existiert: true,
                                     istGesperrt: true, istLesbar: true)
        XCTAssertEqual(b, .passwortNoetig,
                       "Wer zuerst auf Lesbarkeit prueft, meldet nie das Kennwort")
    }

    // MARK: - Markieren: drei Bedingungen, alle noetig

    func testMarkiertWirdNurMitFormatBefundUndSuchtext() {
        XCTAssertTrue(Quelldokument.darfMarkieren(
            dateiname: "a.pdf", befund: .bereit, suchtext: "50,00"))
        XCTAssertTrue(Quelldokument.darfMarkieren(
            dateiname: "a.html", befund: .bereit, suchtext: "Die Wohnungseigentümer"))
    }

    func testOhneSuchtextWirdNichtMarkiert() {
        // Quelle 1 des echten Bestands: Seite gepflegt, Suchtext nicht.
        XCTAssertFalse(Quelldokument.darfMarkieren(
            dateiname: "a.pdf", befund: .bereit, suchtext: nil))
        XCTAssertFalse(Quelldokument.darfMarkieren(
            dateiname: "a.pdf", befund: .bereit, suchtext: ""))
        // Auch Leerraum ist kein Suchtext.
        XCTAssertFalse(Quelldokument.darfMarkieren(
            dateiname: "a.pdf", befund: .bereit, suchtext: "   \n "))
    }

    func testAufEinemNichtBereitenDokumentWirdNichtMarkiert() {
        XCTAssertFalse(Quelldokument.darfMarkieren(
            dateiname: "a.pdf", befund: .passwortNoetig, suchtext: "50,00"))
        XCTAssertFalse(Quelldokument.darfMarkieren(
            dateiname: "a.pdf", befund: .nichtLesbar, suchtext: "50,00"))
    }

    func testAufEinemBildWirdNichtMarkiert() {
        XCTAssertFalse(Quelldokument.darfMarkieren(
            dateiname: "beleg.jpg", befund: .bereit, suchtext: "50,00"))
    }
}

/// Prueft das Modell der Dienst-Antwort -- vor allem, dass fehlende Felder
/// nicht als "nein" gelesen werden.
final class FundstelleTests: XCTestCase {

    private func lese(_ json: String) throws -> Fundstelle {
        try JSONDecoder().decode(Fundstelle.self, from: Data(json.utf8))
    }

    func testVolleAntwortWirdGelesen() throws {
        let f = try lese("""
        {"belegt": true, "herkunft": "gepflegt", "grund": "", "datei": "quellen/volksbank.pdf",
         "absolut": "/pfad/volksbank.pdf", "format": "pdf", "seite": 2, "seiten": [2],
         "suchtext": "50,00", "kurz": "Verwaltervertrag", "markierbar": true, "mehrdeutig": false}
        """)
        XCTAssertTrue(f.belegt)
        XCTAssertEqual(f.seite, 2)
        XCTAssertTrue(f.markierbar)
        XCTAssertEqual(f.mehrdeutig, false)
        XCTAssertEqual(f.lage, "Stelle markiert · Seite 2")
        XCTAssertNil(f.handlung, "Wo markiert ist, braucht es keinen Suchknopf")
    }

    func testUnbekannteMehrdeutigkeitBleibtUnbekannt() throws {
        // 9 von 367 Volltexten tragen keine Seitenmarken. Fehlt das Feld,
        // heisst das NICHT "eindeutig".
        let f = try lese("""
        {"belegt": true, "herkunft": "gerechnet", "suchtext": "x", "markierbar": true}
        """)
        XCTAssertNil(f.mehrdeutig)
        XCTAssertEqual(f.lage, "Stelle markiert")
    }

    func testMehrdeutigeStelleSagtEsDazu() throws {
        let f = try lese("""
        {"belegt": true, "herkunft": "gepflegt", "seite": 8, "seiten": [4,5,6,8],
         "suchtext": "75,00", "markierbar": true, "mehrdeutig": true}
        """)
        XCTAssertEqual(f.lage, "Stelle markiert – dieser Wortlaut kommt mehrfach vor")
    }

    func testAufschlagbarAberNichtMarkierbarBekommtEigenenText() throws {
        // Quelle 1: Seite 4 gepflegt, kein Suchtext.
        let f = try lese("""
        {"belegt": true, "herkunft": "gepflegt", "grund": "Seite bekannt, die Stelle auf der Seite ist nicht erfasst.",
         "absolut": "/pfad/teilung.pdf", "seite": 4, "markierbar": false}
        """)
        XCTAssertEqual(f.lage, "Seite 4 · keine Stelle markiert")
        XCTAssertEqual(f.handlung, "Im Dokument suchen")
    }

    func testKeineStelleNenntDenGrundDesDienstes() throws {
        let f = try lese("""
        {"belegt": false, "herkunft": "keine",
         "grund": "Dieser Wortlaut steht in 7 Dokumenten und grenzt die Stelle nicht ein."}
        """)
        XCTAssertFalse(f.markierbar)
        XCTAssertEqual(f.lage, "Dieser Wortlaut steht in 7 Dokumenten und grenzt die Stelle nicht ein.")
    }

    func testLeereAntwortStuerztNichtAbUndBehauptetNichts() throws {
        let f = try lese("{}")
        XCTAssertFalse(f.belegt)
        XCTAssertFalse(f.markierbar)
        XCTAssertNil(f.seite)
        XCTAssertNil(f.mehrdeutig)
        XCTAssertEqual(f.lage, "Keine Stelle hinterlegt")
    }

    func testMarkierbarWirdAusDemSuchtextAbgeleitetWennEsFehlt() throws {
        // Aeltere Dienstfassung ohne das Feld: Ein vorhandener Suchtext ist
        // der bessere Schluss als ein pauschales "nein".
        let f = try lese("""
        {"belegt": true, "herkunft": "gepflegt", "suchtext": "50,00", "seite": 2}
        """)
        XCTAssertTrue(f.markierbar)
    }
}
