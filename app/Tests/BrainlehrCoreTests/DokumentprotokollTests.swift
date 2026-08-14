// Prueft das Protokoll des Dokumentdienstes.
//
// Die teure Fehlerklasse ist hier nicht "Nachricht wird abgelehnt", sondern
// "Nachricht wird angenommen, obwohl sie Schaden anrichtet": eine
// Teilnehmerkennung ueber der 32-Bit-Schranke laesst Text sich STILL
// verdoppeln -- kein Absturz, keine Meldung, nur ein Absatz, der zweimal
// dasteht. Darum steht der Grenzwert hier dreifach.

import XCTest
@testable import BrainlehrCore

final class DokumentprotokollTests: XCTestCase {

    // MARK: Willkommen und die Kennungsschranke

    func testWillkommenMitTragbarerKennung() {
        let roh = #"{"art":"willkommen","kennung":42,"stand":"AAA="}"#
        guard case .success(.willkommen(let kennung, let stand)) = Dokumentprotokoll.deute(roh)
        else { return XCTFail("haette gedeutet werden muessen") }
        XCTAssertEqual(kennung, 42)
        XCTAssertEqual(stand, Data(base64Encoded: "AAA="))
    }

    func testKennungGrenzwertDreifach() {
        // Genau an der Schranke: traegt.
        let anDerGrenze = #"{"art":"willkommen","kennung":4294967295,"stand":""}"#
        guard case .success(.willkommen(let k, _)) = Dokumentprotokoll.deute(anDerGrenze)
        else { return XCTFail("2^32-1 muss getragen werden") }
        XCTAssertEqual(k, Dokumentprotokoll.groessteKennung)

        // Eins darueber: abgelehnt, und der Grund nennt die Folge.
        let darueber = #"{"art":"willkommen","kennung":4294967296,"stand":""}"#
        guard case .failure(let fehler) = Dokumentprotokoll.deute(darueber)
        else { return XCTFail("2^32 haette abgelehnt werden muessen") }
        XCTAssertEqual(fehler, .kennungAusserhalb(4_294_967_296))
        XCTAssertTrue("\(fehler)".contains("verdoppeln"),
                      "der Grund muss die Folge nennen, nicht nur die Zahl: \(fehler)")

        // Null: sieht aus wie "keine Angabe" und wird darum abgelehnt.
        let null = #"{"art":"willkommen","kennung":0,"stand":""}"#
        guard case .failure(.kennungAusserhalb(0)) = Dokumentprotokoll.deute(null)
        else { return XCTFail("Kennung 0 haette abgelehnt werden muessen") }
    }

    func testWillkommenOhneStandIstGueltig() {
        // Ein frischer Raum hat noch keinen Stand -- das ist kein Fehler.
        let roh = #"{"art":"willkommen","kennung":7}"#
        guard case .success(.willkommen(_, let stand)) = Dokumentprotokoll.deute(roh)
        else { return XCTFail("fehlender Stand darf nicht scheitern") }
        XCTAssertTrue(stand.isEmpty)
    }

    // MARK: Update und Fehler

    func testUpdateWirdEntschluesselt() {
        let nutz = Data([1, 2, 3, 255])
        let roh = #"{"art":"update","daten":"\#(nutz.base64EncodedString())"}"#
        guard case .success(.update(let daten)) = Dokumentprotokoll.deute(roh)
        else { return XCTFail("Update haette gedeutet werden muessen") }
        XCTAssertEqual(daten, nutz)
    }

    func testFehlerVomDienstKommtDurch() {
        let roh = #"{"art":"fehler","grund":"kein beglaubigter Ausweis"}"#
        guard case .success(.fehler(let grund)) = Dokumentprotokoll.deute(roh)
        else { return XCTFail("Fehler haette gedeutet werden muessen") }
        XCTAssertEqual(grund, "kein beglaubigter Ausweis")
    }

    // MARK: Negativfaelle -- was NICHT durchkommen darf

    func testUnbekannteArtWirdBenanntStattVerschluckt() {
        guard case .failure(.unbekannteArt("quatsch")) = Dokumentprotokoll.deute(#"{"art":"quatsch"}"#)
        else { return XCTFail("unbekannte Art haette benannt werden muessen") }
    }

    func testFehlendeFelderFallenEinzeln() {
        guard case .failure(.feldFehlt("art")) = Dokumentprotokoll.deute(#"{"kennung":1}"#)
        else { return XCTFail("fehlendes 'art'") }
        guard case .failure(.feldFehlt("kennung")) = Dokumentprotokoll.deute(#"{"art":"willkommen"}"#)
        else { return XCTFail("fehlendes 'kennung'") }
        guard case .failure(.feldFehlt("daten")) = Dokumentprotokoll.deute(#"{"art":"update"}"#)
        else { return XCTFail("fehlendes 'daten'") }
    }

    func testUnlesbaresWirdAbgelehntStattGeraten() {
        guard case .failure(.unlesbar) = Dokumentprotokoll.deute("das ist kein JSON")
        else { return XCTFail("Unlesbares haette abgelehnt werden muessen") }
        // Auch gueltiges JSON, das kein Objekt ist.
        guard case .failure(.unlesbar) = Dokumentprotokoll.deute("[1,2,3]")
        else { return XCTFail("JSON-Liste ist keine Nachricht") }
        // Base64, das keines ist.
        guard case .failure(.unlesbar("daten")) = Dokumentprotokoll.deute(#"{"art":"update","daten":"!!!"}"#)
        else { return XCTFail("kaputtes Base64 haette abgelehnt werden muessen") }
    }

    // MARK: Was der Klient sendet

    func testGesendeteRahmenSindGueltigesJSON() {
        for text in [Dokumentprotokoll.anmeldung(geheimnis: "wort\"mit'zeichen\\"),
                     Dokumentprotokoll.update(Data([0, 1, 2]))] {
            let daten = text.data(using: .utf8)!
            XCTAssertNoThrow(try JSONSerialization.jsonObject(with: daten),
                             "kein gueltiges JSON: \(text)")
        }
    }

    func testAnmeldungTraegtDasGeheimnisUnveraendert() {
        // Ein Geheimnis mit Sonderzeichen darf nicht stillschweigend
        // verstuemmelt werden -- sonst schlaegt die Anmeldung fehl und niemand
        // weiss warum.
        let geheim = "a\"b'c\\d\ne"
        let roh = Dokumentprotokoll.anmeldung(geheimnis: geheim)
        let objekt = try! JSONSerialization.jsonObject(with: roh.data(using: .utf8)!) as! [String: Any]
        XCTAssertEqual(objekt["geheimnis"] as? String, geheim)
        XCTAssertEqual(objekt["art"] as? String, "anmelden")
    }

    func testUpdateRundlauf() {
        let nutz = Data((0...255).map(UInt8.init))
        guard case .success(.update(let zurueck)) =
                Dokumentprotokoll.deute(Dokumentprotokoll.update(nutz))
        else { return XCTFail("eigener Rahmen muss sich selbst deuten lassen") }
        XCTAssertEqual(zurueck, nutz)
    }
}
