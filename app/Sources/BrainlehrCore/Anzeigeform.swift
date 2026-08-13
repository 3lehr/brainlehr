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

    /// Punkte einer Ansicht in Millimeter. macOS rechnet in Punkten zu
    /// 1/72 Zoll -- unabhaengig davon, wie viele Bildpunkte darauf liegen.
    /// Ein Netzhautschirm hat mehr Bildpunkte, aber keine groessere Flaeche,
    /// und lesbar wird Text von Flaeche, nicht von Bildpunkten.
    public static func punkteInMm(_ punkte: Double) -> Double {
        punkte * ptInMm
    }
}
