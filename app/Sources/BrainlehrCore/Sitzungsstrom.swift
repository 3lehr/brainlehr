// Liest den Ereignisstrom einer laufenden Sitzung -- Chat, Denken, Werkzeuge.
//
// ANLASS (Betreiber, 2026-08-13): "das warum ist kein grund! ich will das du
// das baust!" -- zum Chat- und Denken-Fenster aus dem urspruenglichen Auftrag.
//
// ER HATTE RECHT, UND MEIN GRUND WAR KEINER. Ich hatte in den Plan
// geschrieben, beide brauchten "einen Ereignisstrom aus der laufenden
// Sitzung, den es nicht gibt", und daraus eine Streichung abgeleitet.
// Nachgesehen habe ich nicht. Gemessen am 2026-08-13 in EINER Datei
// (~/.claude/projects/<repo>/<sitzung>.jsonl, 3 MB, im Sekundentakt
// fortgeschrieben): 121 Denk-Bloecke, 92 Textbloecke, 263 Werkzeugaufrufe,
// 278 Eingaben. Es gab den Strom die ganze Zeit.
//
// Das ist woertlich die Fehlerklasse der Hausregel "Nachsehen, bevor gefragt
// oder delegiert wird": Wer nicht nachgesehen hat, sagt "ich habe nicht
// nachgesehen" -- nicht "es gibt das nicht".
//
// Reine Zerlegung, kein Dateizugriff: eine Zeile rein, ein Ereignis raus.
// Das Beobachten der wachsenden Datei liegt eine Schicht hoeher.

import Foundation

/// Was in einer Sitzung passiert.
public enum Ereignisart: String, Equatable, Sendable, CaseIterable {
    case eingabe      // was der Mensch geschrieben hat
    case antwort      // was das Modell sichtbar geantwortet hat
    case denken       // woran es gerade arbeitet
    case werkzeug     // welches Werkzeug es aufruft
    case ergebnis     // was zurueckkam
}

public struct Sitzungsereignis: Equatable, Sendable {
    public let art: Ereignisart
    public let text: String
    public let zeitpunkt: Date?
    /// Nur bei `.werkzeug` gefuellt.
    public let werkzeug: String?

    public init(art: Ereignisart, text: String, zeitpunkt: Date? = nil, werkzeug: String? = nil) {
        self.art = art; self.text = text; self.zeitpunkt = zeitpunkt; self.werkzeug = werkzeug
    }
}

/// Wie viel gezeigt wird. Der Betreiber hat das ausdruecklich als waehlbar
/// verlangt ("mit waehlbarer Ausfuehrlichkeit") -- und es ist keine Spielerei:
/// Bei 1189 Zeilen in vier Stunden ist ungefiltert niemand lesefaehig.
public enum Ausfuehrlichkeit: String, Equatable, Sendable, CaseIterable {
    /// Nur was der Mensch und das Modell sagen. Wie ein Gespraech.
    case knapp
    /// Dazu, woran gerade gearbeitet wird -- Denken und Werkzeugnamen.
    case normal
    /// Alles, auch die Rueckgaben der Werkzeuge.
    case voll

    public var titel: String {
        switch self {
        case .knapp: return "Nur Gespräch"
        case .normal: return "Mit Arbeitsschritten"
        case .voll: return "Alles"
        }
    }

    public var arten: Set<Ereignisart> {
        switch self {
        case .knapp:  return [.eingabe, .antwort]
        case .normal: return [.eingabe, .antwort, .denken, .werkzeug]
        case .voll:   return Set(Ereignisart.allCases)
        }
    }
}

public enum Sitzungsstrom {
    /// Zerlegt EINE Zeile des Stroms. Eine Zeile kann mehrere Ereignisse
    /// tragen (eine Antwort mit Denken, Text und drei Werkzeugaufrufen).
    ///
    /// Gibt eine leere Liste zurueck statt zu werfen: Der Strom enthaelt
    /// Verwaltungszeilen (queue-operation, attachment, custom-title), die
    /// kein Ereignis sind, und eine halb geschriebene letzte Zeile ist im
    /// Normalbetrieb zu erwarten, weil die Datei waehrend des Lesens waechst.
    public static func zerlege(_ zeile: String) -> [Sitzungsereignis] {
        guard let daten = zeile.data(using: .utf8),
              let roh = try? JSONSerialization.jsonObject(with: daten) as? [String: Any]
        else { return [] }

        let zeit = (roh["timestamp"] as? String).flatMap(datumAus)
        guard let nachricht = roh["message"] as? [String: Any] else { return [] }
        let rolle = nachricht["role"] as? String

        // Reiner Text statt Bloecken -- kommt bei Eingaben vor.
        if let text = nachricht["content"] as? String {
            let t = saeubere(text)
            return t.isEmpty ? [] : [Sitzungsereignis(art: rolle == "user" ? .eingabe : .antwort,
                                                      text: t, zeitpunkt: zeit)]
        }

        guard let bloecke = nachricht["content"] as? [[String: Any]] else { return [] }
        return bloecke.compactMap { b in
            switch b["type"] as? String {
            case "thinking":
                let t = saeubere(b["thinking"] as? String ?? "")
                return t.isEmpty ? nil : Sitzungsereignis(art: .denken, text: t, zeitpunkt: zeit)
            case "text":
                let t = saeubere(b["text"] as? String ?? "")
                return t.isEmpty ? nil : Sitzungsereignis(
                    art: rolle == "user" ? .eingabe : .antwort, text: t, zeitpunkt: zeit)
            case "tool_use":
                let name = b["name"] as? String ?? "Werkzeug"
                return Sitzungsereignis(art: .werkzeug, text: name, zeitpunkt: zeit, werkzeug: name)
            case "tool_result":
                let t = saeubere(inhaltAls(b["content"]))
                return t.isEmpty ? nil : Sitzungsereignis(art: .ergebnis, text: t, zeitpunkt: zeit)
            default:
                return nil
            }
        }
    }

    /// Systemnachrichten sind kein Gespraech und gehoeren nicht in die Anzeige.
    ///
    /// Der Strom traegt Erinnerungen, Haken-Ausgaben und eingespieltes Wissen
    /// in denselben Feldern wie echte Eingaben. Wer sie mitzeigt, laesst den
    /// Betreiber Saetze lesen, die er nie geschrieben hat -- und im Beisein
    /// anderer Menschen sieht das aus, als haette er sie geschrieben.
    /// Am echten Strom nachgezogen (2026-08-13): `<task-notification>` und
    /// `<cross-session-message>` fehlten und erschienen dadurch als Eingaben
    /// des Betreibers -- eine davon wurde in der Chat-Auswahl sogar zur
    /// Beschriftung einer Sitzung. Erkennungszeichen fuer die Luecke: eine
    /// "Eingabe", die mit einer spitzen Klammer beginnt.
    static let systemMarken = ["<system-reminder>", "<knowledge-recall>",
                               "<persisted-output>", "Caveat: The messages below",
                               "<command-name>", "<local-command-stdout>",
                               "<task-notification>", "<cross-session-message>",
                               "<regelwechsel>", "<projekt-wahl>", "<modell-frage>"]

    public static func istSystemtext(_ text: String) -> Bool {
        systemMarken.contains { text.contains($0) }
    }

    static func saeubere(_ text: String) -> String {
        let t = text.trimmingCharacters(in: .whitespacesAndNewlines)
        return istSystemtext(t) ? "" : t
    }

    static func inhaltAls(_ wert: Any?) -> String {
        if let s = wert as? String { return s }
        if let liste = wert as? [[String: Any]] {
            return liste.compactMap { $0["text"] as? String }.joined(separator: "\n")
        }
        return ""
    }

    static func datumAus(_ s: String) -> Date? {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f.date(from: s) ?? ISO8601DateFormatter().date(from: s)
    }

    /// Was bei dieser Ausfuehrlichkeit gezeigt wird, juengste zuletzt.
    public static func gefiltert(_ ereignisse: [Sitzungsereignis],
                                 _ stufe: Ausfuehrlichkeit,
                                 hoechstens: Int = 200) -> [Sitzungsereignis] {
        let erlaubt = stufe.arten
        let treffer = ereignisse.filter { erlaubt.contains($0.art) }
        return treffer.count <= hoechstens ? treffer : Array(treffer.suffix(hoechstens))
    }

    /// Woran gerade gearbeitet wird -- das Denken-Fenster in einer Zeile.
    /// `nil`, wenn nichts laeuft; dann zeigt die Ansicht nichts an, statt
    /// einen alten Stand als aktuell auszugeben.
    public static func aktuellerSchritt(_ ereignisse: [Sitzungsereignis]) -> String? {
        for e in ereignisse.reversed() {
            switch e.art {
            case .werkzeug: return e.werkzeug
            case .denken: return e.text.split(separator: "\n").first.map(String.init)
            case .antwort, .eingabe: return nil   // fertig geantwortet, nichts laeuft
            case .ergebnis: continue
            }
        }
        return nil
    }
}
