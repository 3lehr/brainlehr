// Die Antwort des Dienstes auf "wo steht das" -- oder auf "ich weiss es nicht".
//
// Gegenstueck zu kern/fundstelle.py, geliefert von POST /api/fundstelle.
// Die App BESTELLT diese Antwort, sie rechnet sie nicht selbst: der Volltext
// liegt als .txt neben den PDFs, das ist Textarbeit, und sie ist ohne gebaute
// App pruefbar (python3 kern/fundstelle.py --quelle 14).
//
// DREI FELDER, DIE NICHT DASSELBE SAGEN -- und ihre Verwechslung ist die
// Fehlerklasse, gegen die das ganze Modul gebaut ist:
//   belegt      Wissen wir ueberhaupt etwas ueber die Stelle?
//   markierbar  Kennen wir den Wortlaut, den wir hervorheben koennten?
//   mehrdeutig  Kommt dieser Wortlaut mehr als einmal vor?
// Quelle 1 des Bestands ist der Beleg: Seite 4 ist gepflegt, ein Suchtext
// nicht. Das Dokument laesst sich richtig aufschlagen, hervorgehoben werden
// darf nichts.

import Foundation

public struct Fundstelle: Decodable, Equatable, Sendable {
    public let belegt: Bool
    public let herkunft: String        // gepflegt | gerechnet | keine
    public let grund: String
    public let datei: String
    public let absolut: String
    public let format: String
    public let seite: Int?
    public let seiten: [Int]
    public let suchtext: String
    public let kurz: String
    public let markierbar: Bool

    /// `nil` heisst UNBEKANNT, nicht "eindeutig".
    ///
    /// 9 der 367 Volltexte tragen keine Seitenmarken; dort ist die Seitenliste
    /// leer, nicht weil der Text einmal vorkommt, sondern weil es sich nicht
    /// ausrechnen laesst. Ein zweiwertiges Feld muesste hier luegen.
    public let mehrdeutig: Bool?

    public init(belegt: Bool, herkunft: String, grund: String = "", datei: String = "",
                absolut: String = "", format: String = "unbekannt", seite: Int? = nil,
                seiten: [Int] = [], suchtext: String = "", kurz: String = "",
                markierbar: Bool = false, mehrdeutig: Bool? = nil) {
        self.belegt = belegt; self.herkunft = herkunft; self.grund = grund
        self.datei = datei; self.absolut = absolut; self.format = format
        self.seite = seite; self.seiten = seiten; self.suchtext = suchtext
        self.kurz = kurz; self.markierbar = markierbar; self.mehrdeutig = mehrdeutig
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        // Fehlende Felder sind keine Ausnahme: Der Dienst ist aelter oder
        // juenger als die App, und eine Antwort ohne `seiten` ist trotzdem
        // eine Antwort. Was fehlt, gilt als "nicht gewusst" -- nie als "nein".
        belegt = try c.decodeIfPresent(Bool.self, forKey: .belegt) ?? false
        herkunft = try c.decodeIfPresent(String.self, forKey: .herkunft) ?? "keine"
        grund = try c.decodeIfPresent(String.self, forKey: .grund) ?? ""
        datei = try c.decodeIfPresent(String.self, forKey: .datei) ?? ""
        absolut = try c.decodeIfPresent(String.self, forKey: .absolut) ?? ""
        format = try c.decodeIfPresent(String.self, forKey: .format) ?? "unbekannt"
        seite = try c.decodeIfPresent(Int.self, forKey: .seite)
        seiten = try c.decodeIfPresent([Int].self, forKey: .seiten) ?? []
        suchtext = try c.decodeIfPresent(String.self, forKey: .suchtext) ?? ""
        kurz = try c.decodeIfPresent(String.self, forKey: .kurz) ?? ""
        markierbar = try c.decodeIfPresent(Bool.self, forKey: .markierbar) ?? !suchtext.isEmpty
        mehrdeutig = try c.decodeIfPresent(Bool.self, forKey: .mehrdeutig)
    }

    enum CodingKeys: String, CodingKey, CaseIterable {
        case belegt, herkunft, grund, datei, absolut, format, seite, seiten
        case suchtext, kurz, markierbar, mehrdeutig
    }

    /// Felder, die der Dienst liefert und die App BEWUSST nicht liest.
    ///
    /// Der Unterschied zu "vergessen" ist der ganze Zweck dieser Menge:
    /// `Decodable` ueberliest unbekannte Schluessel wortlos, ein neues Feld auf
    /// der Python-Seite kaeme hier also nie an und niemand merkte es. Der
    /// Vertragstest vergleicht die Schluessel der echten Antwort gegen
    /// `CodingKeys` PLUS diese Liste -- wer ein Feld ergaenzt, muss es also
    /// entweder lesen oder hier mit Grund eintragen.
    ///
    /// `weitere`: weitere Treffer desselben Wortlauts, ungewichtet. Die Anzeige
    /// zeigt heute genau eine Stelle; `seiten` und `mehrdeutig` sagen bereits,
    /// dass es mehr gibt. Eine ungewichtete Liste waere eine Auswahl ohne
    /// Rangfolge -- also geraten.
    public static let bewusstNichtGelesen: Set<String> = ["weitere"]

    /// Was unter dem Dokument steht -- in der Sprache des Lesers.
    ///
    /// Der Erfolgsfall bekommt AUSDRUECKLICH einen Text, nicht nur der
    /// Fehlerfall. Sonst bedeutet die Abwesenheit einer Beschriftung
    /// "markiert", und das ist dieselbe Fehlerklasse wie Bedeutung ueber
    /// Farbe -- nur ueber Leere statt ueber Farbton.
    public var lage: String {
        if markierbar {
            if mehrdeutig == true {
                return "Stelle markiert – dieser Wortlaut kommt mehrfach vor"
            }
            if let s = seite { return "Stelle markiert · Seite \(s)" }
            return "Stelle markiert"
        }
        if belegt, let s = seite { return "Seite \(s) · keine Stelle markiert" }
        if belegt { return "Ganzes Dokument · keine Stelle markiert" }
        return grund.isEmpty ? "Keine Stelle hinterlegt" : grund
    }

    /// Der Knopf daneben. Ohne ihn muesste der Leser sich eine Handlung
    /// merken statt eine zu sehen.
    public var handlung: String? {
        markierbar ? nil : (absolut.isEmpty ? nil : "Im Dokument suchen")
    }
}
