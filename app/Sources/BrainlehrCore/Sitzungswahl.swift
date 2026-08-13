// Welcher Chat ist gerade der spannende?
//
// ANLASS (Betreiber, 2026-08-13): "sollte ich in der app oberflaeche nicht
// einstellen koennen welcher chat gerade der spannende ist? weil ich habe oft
// mehrere chats gleichzeitig auf, du verstehst?"
//
// ER HAT EINEN DENKFEHLER IN MEINEM BAU GEFUNDEN: Die App ist selbst kein
// Chat. Sie hat keine "eigene" Sitzung, aus der sich der Strom ableiten
// liesse. Der erste Bau nahm darum "die zuletzt geaenderte Datei im Ordner
// der Repo-Wurzel" -- eine Heuristik, die genau dann versagt, wenn sie
// gebraucht wird.
//
// GEMESSEN am 2026-08-13, 19:40: Im Ordner
// `-Volumes-daten-Begod2026-brainlehr--claude-worktrees` schrieben ZWEI
// Sitzungen gleichzeitig (6,2 MB vor 0,2 Minuten und 32,5 MB vor 5,6
// Minuten). "Die zuletzt geaenderte" springt zwischen beiden hin und her --
// das Fenster haette abwechselnd die Arbeit der einen und der anderen
// gezeigt, ohne dass irgendetwas darauf hinweist. Insgesamt lagen 3467
// Sitzungsdateien vor, 37 davon aus den letzten drei Stunden.
//
// DIE ANTWORT IST KEINE BESSERE HEURISTIK, SONDERN EIN SCHALTER. Welcher
// Chat zaehlt, weiss nur der Mensch -- und eine Anzeige, die es errät und
// dabei falsch liegt, ist schlimmer als eine, die fragt.
//
// Reine Zerlegung, kein Dateizugriff: eine Zeile rein, eine Teilerkenntnis
// raus. Das Sammeln der Dateien liegt eine Schicht hoeher.

import Foundation

/// Eine laufende oder zurueckliegende Sitzung, wie die Auswahl sie zeigt.
public struct Sitzungskennung: Equatable, Identifiable, Sendable {
    public let pfad: String
    /// Vom Menschen vergebener Titel, sonst leer.
    public let titel: String
    /// Die juengste echte Eingabe -- oft aussagekraeftiger als der Titel,
    /// weil sie sagt, WORAN gerade gearbeitet wird.
    public let letzteEingabe: String
    public let zuletztAktiv: Date
    /// Lesbar gemachter Projektordner.
    public let projekt: String

    public var id: String { pfad }

    public init(pfad: String, titel: String, letzteEingabe: String,
                zuletztAktiv: Date, projekt: String) {
        self.pfad = pfad; self.titel = titel; self.letzteEingabe = letzteEingabe
        self.zuletztAktiv = zuletztAktiv; self.projekt = projekt
    }

    /// Was in der Auswahl steht. Nie leer -- eine namenlose Zeile waere
    /// nicht auswaehlbar, und mehrere namenlose waeren nicht unterscheidbar.
    ///
    /// DIE EINGABE DES MENSCHEN STEHT HIER AUSDRUECKLICH NICHT, obwohl sie
    /// der beste Hinweis waere. Gemessen am 2026-08-13: 15 von 15 Sitzungen
    /// der letzten 24 Stunden trugen keinen Titel, und die Liste zeigt Chats
    /// ALLER Projekte -- darunter buckeberg mit Namen Dritter. Eine Auswahl,
    /// in der fremde Namen offen stehen, ist ein Leck, das niemand als
    /// solches erkennt, weil es wie eine Hilfe aussieht.
    ///
    /// Ohne Titel unterscheidet Projekt plus Uhrzeit ausreichend, und beides
    /// stammt nicht aus dem Gespraech.
    public var beschriftung: String {
        if !titel.isEmpty { return titel }
        if !projekt.isEmpty { return "\(projekt) — ohne Titel" }
        return "Sitzung ohne Titel"
    }

    /// Die zweite Zeile: Projekt und wie lange es her ist.
    public func lage(jetzt: Date = Date()) -> String {
        let min = Int(jetzt.timeIntervalSince(zuletztAktiv) / 60)
        let zeit: String
        switch min {
        case ..<1: zeit = "gerade eben"
        case ..<60: zeit = "vor \(min) Min"
        case ..<1440: zeit = "vor \(min / 60) Std"
        default: zeit = "vor \(min / 1440) Tagen"
        }
        return projekt.isEmpty ? zeit : "\(projekt) · \(zeit)"
    }
}

public enum Sitzungswahl {

    /// Titel und Eingabe aus EINER Zeile, soweit sie welche traegt.
    ///
    /// Beides kann mehrfach vorkommen; wer die Datei durchlaeuft, behaelt den
    /// jeweils juengsten Wert -- ein Titel wird umbenannt, eine Eingabe folgt
    /// der naechsten.
    public static func deute(_ zeile: String) -> (titel: String?, eingabe: String?) {
        guard let daten = zeile.data(using: .utf8),
              let roh = try? JSONSerialization.jsonObject(with: daten) as? [String: Any]
        else { return (nil, nil) }

        if roh["type"] as? String == "custom-title" {
            let t = (roh["title"] as? String ?? roh["customTitle"] as? String ?? "")
                .trimmingCharacters(in: .whitespacesAndNewlines)
            return (t.isEmpty ? nil : t, nil)
        }
        guard roh["type"] as? String == "user",
              let nachricht = roh["message"] as? [String: Any] else { return (nil, nil) }

        var text = nachricht["content"] as? String ?? ""
        if let bloecke = nachricht["content"] as? [[String: Any]] {
            text = bloecke.compactMap { $0["type"] as? String == "text" ? $0["text"] as? String : nil }
                .joined(separator: " ")
        }
        text = text.trimmingCharacters(in: .whitespacesAndNewlines)
        // Systemtext ist keine Eingabe des Menschen -- und als Beschriftung
        // waere er irrefuehrend: Der Betreiber saehe eine Sitzung, benannt
        // nach einem Satz, den er nie geschrieben hat.
        guard !text.isEmpty, !Sitzungsstrom.istSystemtext(text) else { return (nil, nil) }
        return (nil, text.replacingOccurrences(of: "\n", with: " "))
    }

    /// Lesbarer Projektname aus dem Ordnernamen.
    ///
    /// Aus `-Volumes-daten-Begod2026-brainlehr--claude-worktrees-hallo-01e380`
    /// wird `brainlehr · hallo`. Der Pfad selbst gehoert nicht auf den
    /// Bildschirm -- er sagt dem Menschen nichts, was er nicht schon weiss.
    public static func projektname(_ ordner: String) -> String {
        var t = ordner
        for vor in ["-Volumes-daten-Begod2026-", "-Users-", "-Volumes-"] {
            if t.hasPrefix(vor) { t = String(t.dropFirst(vor.count)); break }
        }
        // Der Arbeitsbaum-Teil steht hinter dem doppelten Trenner.
        let teile = t.components(separatedBy: "--claude-worktrees")
        let projekt = teile[0]
        guard teile.count > 1 else { return projekt }
        let baum = teile[1].trimmingCharacters(in: CharacterSet(charactersIn: "-"))
        if baum.isEmpty { return projekt }
        // Die angehaengte Kennung (sechs Zeichen hinter dem letzten Strich)
        // sagt nichts -- weg damit.
        let stuecke = baum.components(separatedBy: "-")
        let ohneKennung = (stuecke.count > 1 && stuecke.last!.count == 6)
            ? stuecke.dropLast().joined(separator: "-") : baum
        return "\(projekt) · \(ohneKennung)"
    }

    /// Sortiert: was zuletzt lief, steht oben.
    ///
    /// KEINE automatische Vorauswahl der juengsten -- das war der Fehler.
    /// Die Reihenfolge ist ein Vorschlag, die Wahl trifft der Mensch.
    public static func sortiert(_ sitzungen: [Sitzungskennung]) -> [Sitzungskennung] {
        sitzungen.sorted { $0.zuletztAktiv > $1.zuletztAktiv }
    }
}
