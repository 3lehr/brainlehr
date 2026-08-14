// Was die Steuerschnittstelle versteht -- als reine Rechnung, ohne Netzwerk.
//
// ANLASS: Hausregel H6 verlangt fuer native Anwendungen "eine lokale
// Steuerschnittstelle, die ausschliesslich im Debug-Build existiert", damit
// Kernaktionen und Zustandsabfrage ohne Bildschirmabzug pruefbar sind. Der
// Bedienungshilfen-Baum (app/werkzeuge/ax_baum.swift) sagt, WAS auf dem Schirm
// steht; diese Schnittstelle sagt, in welchem ZUSTAND die App ist. Erst beide
// zusammen machen eine Pruefung ohne Auge moeglich.
//
// WARUM DIE LOGIK HIER UND NICHT IM NETZWERKTEIL: dieselbe Trennung wie bei
// DienstZustand gegen DienstAufsicht -- die Entscheidung ist ohne Fenster und
// ohne offenen Port pruefbar, nur das Zustellen braucht die Aussenwelt.
//
// DIE FEHLERKLASSE, gegen die die Antworten gebaut sind: Ein Werkzeug, das bei
// einem unbekannten Befehl still nichts tut oder pauschal "ok" meldet, ist von
// Erfolg nicht unterscheidbar. Jede Ablehnung nennt deshalb den Grund UND die
// Befehle, die es gaebe.

import Foundation

/// Ein verstandener Befehl, oder eine begruendete Ablehnung.
public enum Steuerbefehl: Equatable, Sendable {
    /// Vollstaendiger Zustand als JSON.
    case zustand
    /// Lebenszeichen -- billig, ohne den Zustand einzusammeln.
    case gesundheit
    /// Ansicht umschalten. Der Wert ist bereits als gueltig erkannt.
    case ansichtWaehlen(String)
    /// Blick im Wissensraum umschalten (Baum, Bedeutung, Spuren, Vergleich,
    /// Abrufweg). Eigener Befehl statt eines zweiten Feldes an /ansicht: der
    /// Blick ist NICHT die Ansicht -- er gilt nur innerhalb einer einzigen und
    /// bleibt beim Wechsel in eine andere bestehen.
    case blickWaehlen(String)
}

public struct Steuerantwort: Equatable, Sendable, Error {
    public let code: Int
    public let koerper: String

    public init(code: Int, koerper: String) {
        self.code = code
        self.koerper = koerper
    }
}

public enum Steuerdeutung {
    /// Ansichten, die es gibt. Wird von aussen gesetzt, damit der Kern die
    /// Oberflaechen-Aufzaehlung nicht kennen muss.
    public static let bekanntePfade = ["/zustand", "/gesundheit", "/ansicht", "/blick"]

    /// Deutet eine Anfrage. `erlaubteAnsichten` kommt vom Aufrufer, damit
    /// diese Datei nicht gegen die Seitenleiste gebunden ist.
    ///
    /// Gibt entweder einen Befehl oder eine fertige Ablehnung zurueck -- nie
    /// beides und nie keines von beidem.
    public static func deute(methode: String, pfad: String, koerper: String,
                             erlaubteAnsichten: [String],
                             erlaubteBlicke: [String] = []) -> Result<Steuerbefehl, Steuerantwort> {
        // Abfragezeichen abschneiden: /zustand?hübsch=1 ist derselbe Pfad.
        let reinerPfad = String(pfad.split(separator: "?").first ?? "")

        switch (methode.uppercased(), reinerPfad) {
        case ("GET", "/zustand"):
            return .success(.zustand)
        case ("GET", "/gesundheit"):
            return .success(.gesundheit)
        case ("POST", "/ansicht"):
            guard let name = feldAusJSON(koerper, schluessel: "ansicht") else {
                return .failure(Steuerantwort(code: 400, koerper: fehler(
                    "Feld 'ansicht' fehlt im Rumpf.",
                    hinweis: "Erwartet wird {\"ansicht\":\"…\"} mit einem aus \(erlaubteAnsichten.joined(separator: ", "))")))
            }
            guard erlaubteAnsichten.contains(name) else {
                return .failure(Steuerantwort(code: 400, koerper: fehler(
                    "Unbekannte Ansicht '\(name)'.",
                    hinweis: "Bekannt sind: \(erlaubteAnsichten.joined(separator: ", "))")))
            }
            return .success(.ansichtWaehlen(name))
        case ("POST", "/blick"):
            guard let name = feldAusJSON(koerper, schluessel: "blick") else {
                return .failure(Steuerantwort(code: 400, koerper: fehler(
                    "Feld 'blick' fehlt im Rumpf.",
                    hinweis: "Erwartet wird {\"blick\":\"…\"} mit einem aus \(erlaubteBlicke.joined(separator: ", "))")))
            }
            guard erlaubteBlicke.contains(name) else {
                return .failure(Steuerantwort(code: 400, koerper: fehler(
                    "Unbekannter Blick '\(name)'.",
                    hinweis: "Bekannt sind: \(erlaubteBlicke.joined(separator: ", "))")))
            }
            return .success(.blickWaehlen(name))
        case ("GET", "/blick"):
            return .failure(Steuerantwort(code: 405, koerper: fehler(
                "/blick wird mit POST gesetzt, nicht mit GET.",
                hinweis: "Zum Lesen des aktuellen Blicks: GET /zustand")))
        case ("GET", "/ansicht"):
            // Haeufiger Irrtum, deshalb eigens beantwortet statt als 404.
            return .failure(Steuerantwort(code: 405, koerper: fehler(
                "/ansicht wird mit POST gesetzt, nicht mit GET.",
                hinweis: "Zum Lesen der aktuellen Ansicht: GET /zustand")))
        default:
            return .failure(Steuerantwort(code: 404, koerper: fehler(
                "Unbekannter Pfad '\(reinerPfad)' fuer \(methode.uppercased()).",
                hinweis: "Bekannt sind: \(bekanntePfade.joined(separator: ", "))")))
        }
    }

    /// Erste Zeile einer HTTP-Anfrage zerlegen. `nil`, wenn sie nicht passt --
    /// ein unlesbarer Anfang wird abgelehnt, nicht geraten.
    public static func zerlegeAnfragezeile(_ zeile: String) -> (methode: String, pfad: String)? {
        let teile = zeile.split(separator: " ", omittingEmptySubsequences: true)
        guard teile.count >= 2 else { return nil }
        let pfad = String(teile[1])
        guard pfad.hasPrefix("/") else { return nil }
        return (String(teile[0]), pfad)
    }

    /// Winziger Leser fuer flaches JSON. Absichtlich kein voller Parser: der
    /// Rumpf dieser Schnittstelle ist immer flach, und ein Fremdpaket dafuer
    /// waere teurer als der Nutzen.
    static func feldAusJSON(_ text: String, schluessel: String) -> String? {
        guard let daten = text.data(using: .utf8),
              let objekt = try? JSONSerialization.jsonObject(with: daten) as? [String: Any],
              let wert = objekt[schluessel] as? String,
              !wert.isEmpty
        else { return nil }
        return wert
    }

    static func fehler(_ grund: String, hinweis: String) -> String {
        let g = grund.replacingOccurrences(of: "\"", with: "'")
        let h = hinweis.replacingOccurrences(of: "\"", with: "'")
        return "{\"fehler\":\"\(g)\",\"hinweis\":\"\(h)\"}"
    }

    /// Baut die Zustandsantwort. Reine Zeichenkettenarbeit, damit sie ohne
    /// laufende App pruefbar ist.
    ///
    /// `fenster` ist nicht Schmuck, sondern der Grund fuer diese Signatur:
    /// Beim ersten echten Einsatz dieser Schnittstelle lief die App mit NULL
    /// Fenstern und meldete dabei "ansicht: ausweise, dienst: laeuft" -- ein
    /// vollkommen gesund aussehender Zustand fuer eine Anwendung, die nichts
    /// anzeigt. Genau das verbietet Hausregel H6 ("ehrliche Statusfelder").
    /// Eine Ansicht ohne Fenster ist keine Ansicht, und das muss die Antwort
    /// sagen, nicht der Betrachter erraten.
    public static func zustandJSON(ansicht: String, dienst: String, pid: Int32,
                                   fassung: String, fenster: Int,
                                   ansichten: [String], blick: String = "",
                                   blicke: [String] = []) -> String {
        let liste = ansichten.map { "\"\($0)\"" }.joined(separator: ",")
        let blickListe = blicke.map { "\"\($0)\"" }.joined(separator: ",")
        // Der Blick steht NUR dann im Zustand, wenn es ihn gibt -- ein leeres
        // Feld waere von "Blick unbekannt" nicht zu unterscheiden.
        let blickTeil = blick.isEmpty ? "" : "\"blick\":\"\(blick)\",\"blicke\":[\(blickListe)],"
        // Ein eigenes Feld statt eines Kommentars: ein Programm liest kein
        // "eigentlich sieht man gerade nichts".
        let sichtbar = fenster > 0
        return """
        {"ansicht":"\(ansicht)",\(blickTeil)"sichtbar":\(sichtbar),"fenster":\(fenster),\
        "dienst":"\(dienst)","pid":\(pid),\
        "fassung":"\(fassung)","ansichten":[\(liste)]}
        """
    }
}
