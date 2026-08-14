// Das Protokoll des Dokumentdienstes -- als pruefbare Fachlogik, nicht als
// Zeichenketten mitten in einer Netzwerkschleife.
//
// Gegenstueck: `kern/dokumentdienst.py`. Vier Nachrichten, mehr nicht:
//
//     Klient -> Dienst  {"art": "anmelden", "geheimnis": <str>}   (nur wenn noetig)
//     Dienst -> Klient  {"art": "willkommen", "kennung": <int>, "stand": <base64>}
//     Klient -> Dienst  {"art": "update", "daten": <base64>}
//     Dienst -> Klient  {"art": "update", "daten": <base64>} | {"art": "fehler", "grund": <str>}
//
// DIE KENNUNG WIRD GEPRUEFT, NICHT GEGLAUBT. `yswift` schneidet sie auf 32 Bit
// ab, `pycrdt` wuerfelt bis 2^53 -- darueber kommt der eigene Beitrag als
// FREMDER zurueck und der Text verdoppelt sich still (ADR-010, `L-44dc9f`).
// Der Dienst haelt sich daran; ein Klient, der das nur voraussetzt, merkt den
// Tag nicht, an dem sich das aendert. Darum lehnt `Willkommen` eine Kennung
// ausserhalb der Schranke ab, statt sie zu uebernehmen.
//
// WARUM HIER UND NICHT IN DER ANSICHT: `Sources/Atelier` hat keine Tests,
// `BrainlehrCore` hat sie. Ob eine Nachricht gueltig ist, ist pruefbar; ein
// `URLSessionWebSocketTask` ist es nicht.

import Foundation

public enum Dokumentprotokoll {

    /// Groesste Teilnehmerkennung, die beide Seiten unbeschaedigt tragen.
    /// Gemessen an der Schwelle: 2^32-1 traegt, 2^32 nicht.
    public static let groessteKennung: UInt64 = 4_294_967_295

    public enum Fehler: Error, Equatable, CustomStringConvertible {
        case unlesbar(String)
        case unbekannteArt(String)
        case feldFehlt(String)
        case kennungAusserhalb(UInt64)
        case vomDienst(String)

        public var description: String {
            switch self {
            case .unlesbar(let was): return "unlesbare Nachricht: \(was)"
            case .unbekannteArt(let art): return "unbekannte Art '\(art)'"
            case .feldFehlt(let feld): return "Feld '\(feld)' fehlt"
            case .kennungAusserhalb(let k):
                return "Kennung \(k) liegt ueber \(groessteKennung) -- Text wuerde sich still verdoppeln"
            case .vomDienst(let grund): return grund
            }
        }
    }

    /// Was der Dienst schickt.
    public enum Eingang: Equatable {
        case willkommen(kennung: UInt64, stand: Data)
        case update(Data)
        case fehler(String)
    }

    public static func deute(_ roh: String) -> Result<Eingang, Fehler> {
        guard let daten = roh.data(using: .utf8),
              let objekt = try? JSONSerialization.jsonObject(with: daten) as? [String: Any]
        else { return .failure(.unlesbar(String(roh.prefix(80)))) }

        guard let art = objekt["art"] as? String else { return .failure(.feldFehlt("art")) }

        switch art {
        case "willkommen":
            // `as? UInt64` scheitert bei JSON-Zahlen (NSNumber) -- ueber
            // NSNumber gehen, sonst faellt jede gueltige Nachricht durch.
            guard let zahl = objekt["kennung"] as? NSNumber else { return .failure(.feldFehlt("kennung")) }
            let kennung = zahl.uint64Value
            guard kennung >= 1, kennung <= groessteKennung else {
                return .failure(.kennungAusserhalb(kennung))
            }
            let stand = (objekt["stand"] as? String).flatMap { Data(base64Encoded: $0) } ?? Data()
            return .success(.willkommen(kennung: kennung, stand: stand))

        case "update":
            guard let text = objekt["daten"] as? String else { return .failure(.feldFehlt("daten")) }
            guard let daten = Data(base64Encoded: text) else { return .failure(.unlesbar("daten")) }
            return .success(.update(daten))

        case "fehler":
            return .success(.fehler((objekt["grund"] as? String) ?? "ohne Grund"))

        default:
            return .failure(.unbekannteArt(art))
        }
    }

    /// Was der Klient schickt. Base64, damit ein Rahmen mit blossem Auge
    /// lesbar bleibt -- dieselbe Entscheidung wie auf der Dienstseite.
    public static func anmeldung(geheimnis: String) -> String {
        rahmen(["art": "anmelden", "geheimnis": geheimnis])
    }

    public static func update(_ daten: Data) -> String {
        rahmen(["art": "update", "daten": daten.base64EncodedString()])
    }

    static func rahmen(_ felder: [String: String]) -> String {
        guard let daten = try? JSONSerialization.data(withJSONObject: felder),
              let text = String(data: daten, encoding: .utf8)
        else { return "{}" }
        return text
    }
}
