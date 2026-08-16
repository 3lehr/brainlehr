import Foundation

/// Ein Bildschirm, den eine Domaene BESCHRIEBEN hat -- uebersetzt in ein
/// Anzeigemodell, das das atelier mit SEINEN Bausteinen zeichnet.
///
/// ADR-013 (Hauptentscheidung) und ADR-024: „Die Domaene sagt, WAS zu sehen
/// sein soll; das atelier zeichnet es mit seinen eigenen Bausteinen." Diese
/// Datei ist die Naht dazwischen -- und damit die Stelle, an der ein zweiter
/// Zeichner (Web) spaeter ansetzt, ohne dass ein Feld des Manifests sich
/// aendert. Genau das war die Zusage an den Betreiber.
///
/// WARUM HIER UND NICHT IN DER ANSICHT: Eine SwiftUI-Ansicht ist nur mit
/// erheblichem Aufwand pruefbar, dieses Modell ohne jeden Mock. Und die
/// Entscheidungen, die schiefgehen koennen -- unbekannte Spaltenart,
/// fehlender Wert, leere Liste -- fallen alle hier.
public struct DomaenenBildschirm: Sendable {

    /// Die ROLLE einer Spalte, nie ihre Bauform. Was daraus wird --
    /// rechtsbuendig, Monospace, mit Waehrungszeichen -- entscheidet der
    /// Zeichner, nicht die Domaene.
    public enum Spaltenart: String, Sendable {
        case text
        case betrag
        case zitat
    }

    public struct Spalte: Sendable {
        public let name: String
        public let titel: String
        public let art: Spaltenart
    }

    public let kennung: String
    public let titel: String
    public let erklaerung: String?
    public let spalten: [Spalte]
    public let leerfall: String

    /// Der Satz, wenn die Domaene keinen eigenen mitgibt. Nie eine leere
    /// Flaeche, nie Entwicklerinformation.
    public static let leerfallVorgabe = "Hier ist noch nichts eingetragen."

    /// Nil, wenn die Beschreibung nicht zeichenbar ist. Abgelehnt wird
    /// frueh und ganz, statt einen halben Bildschirm zu zeigen: ein
    /// namenloser Reiter ist nicht auffindbar, und eine Tabelle ohne Spalten
    /// ist keine.
    public init?(beschreibung: [String: Any]) {
        guard let titel = beschreibung["titel"] as? String, !titel.isEmpty else { return nil }
        let rohSpalten = beschreibung["spalten"] as? [[String: Any]] ?? []
        let spalten: [Spalte] = rohSpalten.compactMap { s in
            guard let name = s["name"] as? String,
                  let titel = s["titel"] as? String else { return nil }
            // Eine unbekannte Rolle wird TEXT, nicht verworfen: eine neuere
            // Domaene darf eine aeltere Anwendung nicht sprengen. Sie zeigt
            // dann weniger, aber sie zeigt.
            let art = Spaltenart(rawValue: s["art"] as? String ?? "") ?? .text
            return Spalte(name: name, titel: titel, art: art)
        }
        guard !spalten.isEmpty else { return nil }

        self.kennung = beschreibung["kennung"] as? String ?? titel
        self.titel = titel
        self.erklaerung = beschreibung["erklaerung"] as? String
        self.spalten = spalten
        self.leerfall = (beschreibung["leerfall"] as? String).flatMap { $0.isEmpty ? nil : $0 }
            ?? Self.leerfallVorgabe
    }

    /// Eine Datenzeile in Anzeigetexte, in der Reihenfolge der Spalten.
    ///
    /// DER FALL, DER HIER ENTSCHIEDEN WIRD: Ein FEHLENDER Wert ist keine Null.
    /// Er wird als Strich gezeigt, nie als "0,00 €" -- sonst behauptet der
    /// Bildschirm einen Betrag, den niemand gerechnet hat. Eine gerechnete
    /// Null dagegen ist eine Aussage und wird als solche gezeigt. Dieselbe
    /// Unterscheidung trifft der Dienst (euer_vorschlag.py: eine Groesse ohne
    /// Wert erzeugt keinen Vorschlag).
    public func zeile(aus daten: [String: Any]) -> [String] {
        spalten.map { spalte in
            guard let wert = daten[spalte.name] else { return "—" }
            switch spalte.art {
            case .betrag:
                guard let cent = wert as? Int else { return "—" }
                return Self.betrag(cent)
            case .text, .zitat:
                return String(describing: wert)
            }
        }
    }

    /// Cent in einen lesbaren Betrag. Die Form entscheidet der Zeichner --
    /// die Domaene liefert nur die Zahl und die Rolle.
    public static func betrag(_ cent: Int) -> String {
        let f = NumberFormatter()
        f.numberStyle = .decimal
        f.minimumFractionDigits = 2
        f.maximumFractionDigits = 2
        f.locale = Locale(identifier: "de_DE")
        let wert = Double(cent) / 100.0
        return f.string(from: NSNumber(value: wert)) ?? String(format: "%.2f", wert)
    }
}
