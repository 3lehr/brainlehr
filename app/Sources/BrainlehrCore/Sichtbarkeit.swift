// Wer darf was sehen -- und was heisst "schwaerzen" wirklich.
//
// ANLASS (Betreiber, 2026-08-13): "haben wir auch bedacht das nicht jeder
// alles sehen darf? eskalationsstufe waere dann sogar je nach user andere
// stellen im dokument zu schwaerzen"
//
// GEMESSEN, bevor gebaut wurde: Der Speicher fuehrt die Achse `freigabe`
// (1888 offen, 290 intern, 0 gesperrt) und der Ausweis kennt Rollen mit
// Rechten. Die APP kannte davon nichts -- keine einzige Zugriffspruefung.
//
// DIE HARTE REGEL, die dieses Modul traegt:
//
//   SCHWAERZEN HEISST ENTFERNEN, NICHT UEBERDECKEN.
//
// Sie ist nicht theoretisch. `PDFMarkupType.redact` setzt eine ANMERKUNG --
// ein schwarzes Rechteck ueber weiterhin vorhandenem Text. Wer das fuer
// Schwaerzung haelt, verteilt die Daten trotzdem; sie stehen in der
// Textebene und lassen sich mit jedem Werkzeug herausziehen. Ein Anstrich,
// der wie Schutz aussieht, ist schlechter als gar keiner, weil er Vertrauen
// erzeugt, das er nicht traegt.
//
// Darum arbeitet dieses Modul auf dem TEXT, nicht auf der Darstellung, und
// die Abnahme lautet: Der geschwaerzte Wortlaut ist danach nicht mehr
// auffindbar. Nicht "nicht sichtbar" -- nicht auffindbar.
//
// DIE ZWEITE REGEL, die leicht uebersehen wird:
//
//   AUCH DAS VERWEIGERN LECKT.
//
// "Zu dieser Frage gibt es 7 Treffer, die Sie nicht sehen duerfen" verraet,
// dass es sie gibt. Bei WEG-Rechtsfaellen mit Namen Dritter ist schon die
// ANZAHL eine Aussage. Deshalb filtert dieses Modul VOR der Suche, nicht
// danach, und Zaehlungen laufen ueber die bereits gefilterte Menge.

import Foundation

/// Wie weit jemand sehen darf. Aufsteigend: jede Stufe schliesst die
/// darunter ein.
public enum Sichtstufe: Int, Comparable, Sendable, CaseIterable {
    case oeffentlich = 0   // nur, was ausdruecklich freigegeben ist
    case intern = 1        // der Arbeitsbestand
    case vollstaendig = 2  // alles, auch Gesperrtes

    public static func < (a: Sichtstufe, b: Sichtstufe) -> Bool { a.rawValue < b.rawValue }

    public var titel: String {
        switch self {
        case .oeffentlich: return "Freigegebenes"
        case .intern: return "Arbeitsbestand"
        case .vollstaendig: return "Vollständig"
        }
    }
}

/// Die Freigabe eines Eintrags -- dieselben Werte wie in der Spalte
/// `freigabe` des Speichers.
public enum Freigabe: String, Sendable, CaseIterable {
    case offen, intern, gesperrt

    /// Unbekannte Werte gelten als GESPERRT, nicht als offen.
    ///
    /// Das ist die einzige sichere Richtung: Ein Tippfehler, eine neue Stufe
    /// oder ein alter Datensatz darf niemals dazu fuehren, dass etwas
    /// SICHTBAR wird. Wer hier "im Zweifel offen" baut, hat eine Schranke
    /// gebaut, die sich durch einen Schreibfehler oeffnen laesst.
    public static func aus(_ roh: String?) -> Freigabe {
        guard let r = roh?.trimmingCharacters(in: .whitespaces).lowercased(),
              let f = Freigabe(rawValue: r) else { return .gesperrt }
        return f
    }

    var noetigeStufe: Sichtstufe {
        switch self {
        case .offen: return .oeffentlich
        case .intern: return .intern
        case .gesperrt: return .vollstaendig
        }
    }
}

/// Wer gerade zusieht.
public struct Betrachter: Equatable, Sendable {
    public let name: String
    public let rollen: Set<String>
    public let stufe: Sichtstufe

    public init(name: String, rollen: Set<String>, stufe: Sichtstufe) {
        self.name = name; self.rollen = rollen; self.stufe = stufe
    }

    /// Der Vorgabewert, wenn niemand angemeldet ist.
    ///
    /// `oeffentlich`, nicht `intern`: Am Besprechungstisch sitzen Menschen,
    /// die keinen Ausweis haben. Der ungefragte Zustand muss der engste sein.
    public static let unangemeldet = Betrachter(name: "", rollen: [], stufe: .oeffentlich)

    /// Aus Rollen abgeleitet -- der Betreiber sieht alles, wer schreiben darf
    /// sieht den Arbeitsbestand, alle anderen nur Freigegebenes.
    public static func ausRollen(_ name: String, _ rollen: Set<String>) -> Betrachter {
        let stufe: Sichtstufe = rollen.contains("betreiber") ? .vollstaendig
            : (rollen.contains("schreiber") || rollen.contains("fachkundig") ? .intern
               : .oeffentlich)
        return Betrachter(name: name, rollen: rollen, stufe: stufe)
    }
}

/// Womit eine geschwaerzte Stelle ersetzt wird -- und was das kostet.
///
/// GEMESSEN am 2026-08-13 an einer echten Vertragstabelle (volksbank.pdf
/// Seite 2, mit -layout ausgelesen): Die Zeile ist 78 Zeichen lang. Ersetzt
/// man "50,00" durch "[geschwärzt]", wird sie 85 Zeichen lang -- alles rechts
/// davon verrutscht, und in einer Spaltentabelle ist das Dokument damit
/// unlesbar. Mit Blockzeichen bleibt sie bei 78.
///
/// DER ABWAEGUNGSPUNKT, offen benannt statt versteckt: Blockzeichen halten
/// das Layout und verraten die LAENGE des Entfernten. Bei einem Namen ist
/// das ein schwaches Leck, bei einem Betrag ein staerkeres ("███" ist
/// dreistellig). Wer die Laenge verbergen muss, nimmt `.text` und nimmt in
/// Kauf, dass sich die Zeile verschiebt.
public enum Marke: Equatable, Sendable {
    /// Blockzeichen in der Laenge des Entfernten. Layout bleibt, Laenge sichtbar.
    case blockGleicherLaenge
    /// Fester Text. Laenge verborgen, Zeile kann verrutschen.
    case text(String)
    /// Feste Zahl Blockzeichen -- verbirgt die Laenge UND haelt eine feste
    /// Breite. Verschiebt, wo das Entfernte laenger oder kuerzer war.
    case blockFesterLaenge(Int)

    func fuer(_ wortlaut: String) -> String {
        switch self {
        case .blockGleicherLaenge: return String(repeating: "█", count: wortlaut.count)
        case .text(let t): return t
        case .blockFesterLaenge(let n): return String(repeating: "█", count: max(1, n))
        }
    }

    /// Bleibt die Zeilenbreite erhalten?
    public var haeltLayout: Bool {
        if case .blockGleicherLaenge = self { return true }
        return false
    }
}

/// Eine Stelle im Text, die fuer bestimmte Betrachter verschwindet.
///
/// WICHTIG, und der Betreiber hat es praezisiert: Das ORIGINAL wird nie
/// angefasst. Geschwaerzt wird die PROJEKTION -- das, was dieser eine
/// Betrachter zu sehen bekommt. Die Quelldatei bleibt byte-gleich; war sie
/// schon bei Anlieferung zensiert, ist das der Ausgangszustand und die App
/// weiss nichts davon.
public struct Schwaerzung: Equatable, Sendable {
    /// Der genaue Wortlaut, der entfernt wird.
    public let wortlaut: String
    /// Ab welcher Stufe er sichtbar bleibt.
    public let sichtbarAb: Sichtstufe
    /// Was stattdessen dasteht. Sichtbar, weil eine unsichtbare Schwaerzung
    /// den Text unbemerkt verfaelscht -- wer einen Vertrag liest, muss
    /// erkennen koennen, dass eine Stelle fehlt.
    public let marke: Marke

    public init(wortlaut: String, sichtbarAb: Sichtstufe,
                marke: Marke = .blockGleicherLaenge) {
        self.wortlaut = wortlaut; self.sichtbarAb = sichtbarAb; self.marke = marke
    }
}

public enum Sichtbarkeit {

    /// Darf dieser Betrachter das sehen?
    public static func darfSehen(_ freigabe: Freigabe, _ b: Betrachter) -> Bool {
        b.stufe >= freigabe.noetigeStufe
    }

    public static func darfSehen(rohFreigabe: String?, _ b: Betrachter) -> Bool {
        darfSehen(Freigabe.aus(rohFreigabe), b)
    }

    /// Entfernt alle Stellen, die dieser Betrachter nicht sehen darf.
    ///
    /// ENTFERNT, nicht ueberdeckt: Der Rueckgabetext enthaelt den Wortlaut
    /// nicht mehr. Genau das ist der Unterschied zwischen Schwaerzung und
    /// Anstrich, und er wird als Test gefuehrt, nicht als Zusicherung.
    public static func schwaerze(_ text: String,
                                 _ schwaerzungen: [Schwaerzung],
                                 fuer b: Betrachter) -> String {
        var ergebnis = text
        for s in schwaerzungen where b.stufe < s.sichtbarAb {
            guard !s.wortlaut.isEmpty else { continue }
            ergebnis = ergebnis.replacingOccurrences(of: s.wortlaut,
                                                     with: s.marke.fuer(s.wortlaut))
        }
        return ergebnis
    }

    /// Bleibt bei dieser Schwaerzung die Zeilenbreite erhalten?
    ///
    /// Fuer die Anzeige, damit sie warnen kann, statt eine zerrissene Tabelle
    /// wortlos zu zeigen. Gemessen: "[geschwärzt]" statt "50,00" macht aus
    /// einer 78 Zeichen langen Vertragszeile eine mit 85.
    public static func haeltLayout(_ schwaerzungen: [Schwaerzung]) -> Bool {
        schwaerzungen.allSatisfy { $0.marke.haeltLayout }
    }

    /// Filtert eine Menge VOR der Auswertung.
    ///
    /// Der Rueckgabewert traegt keine Zahl darueber, wie viel weggefallen ist
    /// -- siehe Modulkopf: Auch das Verweigern leckt. Wer wissen will, wie
    /// viel er nicht sieht, muss dafuer eine eigene Berechtigung haben.
    public static func sichtbar<T>(_ menge: [T], _ b: Betrachter,
                                   freigabe: (T) -> String?) -> [T] {
        menge.filter { darfSehen(rohFreigabe: freigabe($0), b) }
    }

    /// Was der Betrachter erfaehrt, wenn eine Quelle fuer ihn nicht existiert.
    ///
    /// KEIN "gesperrt", KEIN "Sie haben keine Berechtigung", KEINE Anzahl.
    /// Diese Saetze verraten, DASS es etwas gibt -- und bei Rechtsfaellen mit
    /// Namen Dritter ist schon das eine Aussage. Der Satz ist derselbe wie
    /// bei einer Quelle, die es wirklich nicht gibt: Nur dann kann aus dem
    /// Unterschied nichts geschlossen werden.
    public static let nichtVorhanden = "Zu dieser Frage ist hier nichts hinterlegt."
}
