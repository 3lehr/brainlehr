// Entscheidet, WIE eine Quelle gezeigt wird -- Ausschnitt, ganze Seite oder
// mehrere nebeneinander. Reine Rechnung, kein SwiftUI, kein AppKit: damit
// ohne gebaute App und ohne Bildschirm pruefbar, wie DienstZustand und
// RepoWurzel es vormachen.
//
// ANLASS (ADR-004, Betreiber 2026-08-13): "die app muss alle scenarien tragen
// nicht nur das morgige!" Die Lagen reichen vom Einzelplatz am 14-Zoll-Laptop
// ueber zwei Bildschirme im Buero bis zum 4K-Fernseher bei 1,5 m.
//
// DER GRUND, WARUM DIE FELDZAHL NICHT IN DIE KONFIGURATION GEHOERT: Die
// Spruenge sind nicht sanft. Gemessen bei 1,5 m traegt ein 55-Zoll-Schirm
// NULL volle A4-Seiten, ein 65-Zoll-Schirm ZWEI -- Engpass ist die Hoehe
// (eine Seite braucht dort rund 739 mm, ein 55er ist 685 mm hoch). Eine fest
// verdrahtete Zahl waere in fast jeder Lage falsch, und zwar nicht knapp.
//
// Die gemessenen Werte kommen aus app/Resources/lesbarkeit.json -- dieselbe
// Datei, die app/werkzeuge/lesbarkeit.py liest. Die Formel steht zweimal, die
// Zahlen einmal.

import Foundation

/// Was auf der verfuegbaren Flaeche sinnvoll darstellbar ist.
public enum Anzeigeform: String, Equatable, Sendable {
    /// Weniger als eine Seite lesbar: die Fundstelle gross, mit Kontextsatz
    /// davor und dahinter, dazu ein bewusst unlesbares Seitenbild mit
    /// Positionsbalken. Haeufigste Lage -- weder 14 Zoll bei Armlaenge noch
    /// ein einzelner 27-Zoeller tragen eine volle Seite.
    case ausschnitt
    /// Genau eine Seite, an der Stelle aufgeschlagen und markiert.
    case ganzeSeite
    /// Zwei oder mehr nebeneinander. Erst hier traegt der Vorschaumonitor,
    /// und erst hier laesst sich "im Vertrag steht A, im Protokoll B" als EIN
    /// Bild zeigen -- bei WEG-Fragen der halbe Streit.
    case nebeneinander

    public var titel: String {
        switch self {
        case .ausschnitt: return "Fundstelle"
        case .ganzeSeite: return "Ganze Seite"
        case .nebeneinander: return "Nebeneinander"
        }
    }
}

/// Die gemessenen Eigenschaften des Dokumentenbestands.
public struct Lesbarkeitswerte: Equatable, Sendable {
    public let fliesstextPt: Double
    public let xHoeheAnteil: Double
    public let seiteBreiteMm: Double
    public let seiteHoeheMm: Double
    public let schwelleGrad: Double

    public init(fliesstextPt: Double, xHoeheAnteil: Double,
                seiteBreiteMm: Double, seiteHoeheMm: Double, schwelleGrad: Double) {
        self.fliesstextPt = fliesstextPt
        self.xHoeheAnteil = xHoeheAnteil
        self.seiteBreiteMm = seiteBreiteMm
        self.seiteHoeheMm = seiteHoeheMm
        self.schwelleGrad = schwelleGrad
    }

    /// Rueckfall, falls die Datei fehlt -- die Werte vom 2026-08-13. Bewusst
    /// hier und nicht in der Rechnung: Eine App, die ohne ihre Beidatei gar
    /// nichts anzeigt, ist schlechter als eine, die mit dem letzten bekannten
    /// Stand rechnet und das sagt.
    public static let gemessen = Lesbarkeitswerte(
        fliesstextPt: 10.9, xHoeheAnteil: 0.547,
        seiteBreiteMm: 210.0, seiteHoeheMm: 297.0, schwelleGrad: 0.20)
}

public enum Lesbarkeit {
    static let ptInMm = 25.4 / 72.0

    /// Wie gross die x-Hoehe auf dem Schirm sein muss, um lesbar zu sein.
    public static func noetigeXHoeheMm(abstandMm: Double, schwelleGrad: Double) -> Double {
        abstandMm * tan(schwelleGrad * .pi / 180.0)
    }

    /// Faktor, um den eine Seite ueber ihre Originalgroesse hinaus muss.
    /// `nil` bei unbrauchbaren Eingaben -- nicht 1.0, denn "keine Angabe" und
    /// "keine Vergroesserung noetig" sind verschiedene Aussagen.
    public static func vergroesserung(abstandMm: Double, werte: Lesbarkeitswerte) -> Double? {
        guard abstandMm > 0, werte.fliesstextPt > 0, werte.xHoeheAnteil > 0,
              werte.schwelleGrad > 0 else { return nil }
        let vorhanden = werte.fliesstextPt * werte.xHoeheAnteil * ptInMm
        return noetigeXHoeheMm(abstandMm: abstandMm, schwelleGrad: werte.schwelleGrad) / vorhanden
    }

    /// Wie viele ganze Seiten die Flaeche traegt -- Spalten mal Zeilen.
    ///
    /// GANZE Felder, nicht Flaechenanteile: Ein halbes Feld traegt keine halbe
    /// Seite, es traegt gar keine. Wer die Flaeche teilt statt die Felder zu
    /// zaehlen, bekommt "2,7" und baut daraus drei.
    public static func felder(breiteMm: Double, hoeheMm: Double, abstandMm: Double,
                              werte: Lesbarkeitswerte = .gemessen) -> Int {
        guard let f = vergroesserung(abstandMm: abstandMm, werte: werte), f > 0,
              breiteMm > 0, hoeheMm > 0 else { return 0 }
        let spalten = Int(breiteMm / (werte.seiteBreiteMm * f))
        let zeilen = Int(hoeheMm / (werte.seiteHoeheMm * f))
        return spalten * zeilen
    }

    /// Die Entscheidung, um die es geht.
    public static func form(breiteMm: Double, hoeheMm: Double, abstandMm: Double,
                            werte: Lesbarkeitswerte = .gemessen) -> Anzeigeform {
        switch felder(breiteMm: breiteMm, hoeheMm: hoeheMm, abstandMm: abstandMm, werte: werte) {
        case 0: return .ausschnitt
        case 1: return .ganzeSeite
        default: return .nebeneinander
        }
    }

    /// Millimeter je Punkt auf EINEM bestimmten Schirm.
    ///
    /// ES GIBT KEINE ALLGEMEINE UMRECHNUNG, und das ist der ganze Punkt
    /// dieser Funktion. Sie war hier zuerst als `punkteInMm(_:)` mit dem
    /// Faktor 1/72 Zoll notiert -- die Annahme stimmt fuer PDF und ist fuer
    /// Bildschirme falsch. Gemessen am 2026-08-13 an zwei angeschlossenen
    /// Geraeten:
    ///
    ///   EIZO CG2700X          echt 27,1"  angenommen 40,8"  Faktor 1,50
    ///   Built-in Retina       echt 16,1"  angenommen 28,6"  Faktor 1,77
    ///
    /// Die Fehlfaktoren sind VERSCHIEDEN -- es gibt also nicht einmal eine
    /// konstante Korrektur. Ein Punkt misst hier 0,2341 mm, dort 0,1992 mm,
    /// weil ein Punkt eine logische Einheit ist und seine physische Groesse
    /// von der Dichte des Geraets abhaengt.
    ///
    /// Die physische Groesse muss deshalb von aussen kommen; auf macOS
    /// liefert sie `CGDisplayScreenSize`. Diese Schicht rechnet nur.
    public static func mmJePunkt(physischMm: Double, punkte: Double) -> Double? {
        guard physischMm > 0, punkte > 0 else { return nil }
        return physischMm / punkte
    }
}

/// Ein Schirm oder ein Fenster darauf -- mit seiner ECHTEN Flaeche.
///
/// Traegt beides, weil beides gebraucht wird: Punkte fuer das Zeichnen,
/// Millimeter fuer die Frage, ob ein Mensch das lesen kann. Wer nur Punkte
/// hat, kann die zweite Frage nicht beantworten, egal wie er rechnet.
public struct Anzeigeflaeche: Equatable, Sendable {
    public let breiteMm: Double
    public let hoeheMm: Double

    public init(breiteMm: Double, hoeheMm: Double) {
        self.breiteMm = breiteMm
        self.hoeheMm = hoeheMm
    }

    /// Aus der physischen Schirmgroesse und dem Anteil, den ein Fenster davon
    /// einnimmt. Ein Fenster auf halber Schirmbreite hat halb so viel Flaeche
    /// -- und traegt darum weniger, was die Feldrechnung selbst merkt.
    public init?(schirmMm: (breite: Double, hoehe: Double),
                 schirmPunkte: (breite: Double, hoehe: Double),
                 fensterPunkte: (breite: Double, hoehe: Double)) {
        guard let mmProPunktB = Lesbarkeit.mmJePunkt(physischMm: schirmMm.breite,
                                                     punkte: schirmPunkte.breite),
              let mmProPunktH = Lesbarkeit.mmJePunkt(physischMm: schirmMm.hoehe,
                                                     punkte: schirmPunkte.hoehe),
              fensterPunkte.breite > 0, fensterPunkte.hoehe > 0
        else { return nil }
        self.breiteMm = fensterPunkte.breite * mmProPunktB
        self.hoeheMm = fensterPunkte.hoehe * mmProPunktH
    }

    public var diagonaleZoll: Double {
        (breiteMm * breiteMm + hoeheMm * hoeheMm).squareRoot() / 25.4
    }

    public func felder(abstandMm: Double, werte: Lesbarkeitswerte = .gemessen) -> Int {
        Lesbarkeit.felder(breiteMm: breiteMm, hoeheMm: hoeheMm,
                          abstandMm: abstandMm, werte: werte)
    }

    public func form(abstandMm: Double, werte: Lesbarkeitswerte = .gemessen) -> Anzeigeform {
        Lesbarkeit.form(breiteMm: breiteMm, hoeheMm: hoeheMm,
                        abstandMm: abstandMm, werte: werte)
    }
}
