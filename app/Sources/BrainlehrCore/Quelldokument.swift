// Was die App ueber eine Quelle wissen muss, bevor sie sie anzeigt --
// und was sie dem Menschen sagt, wenn es nicht geht.
//
// Reine Logik, kein PDFKit, kein AppKit: damit ohne Bildschirm pruefbar.
// Die Anzeige selbst haengt darunter und bekommt fertige Entscheidungen.
//
// DIE DREI BEFUNDE DES KONSILS, die diese Datei begruenden -- alle am
// 2026-08-13 auf diesem Rechner gemessen, nicht aus der Doku uebernommen:
//
// 1. Quick Look kann WEDER aufschlagen NOCH hervorheben NOCH einen Fehlschlag
//    melden. Es nimmt eine erfundene Endung ".zzq" an und liefert ein Symbol,
//    das von Erfolg nicht zu unterscheiden ist. Die Apple-Referenz empfiehlt
//    selbst, das Format VORHER zu pruefen -- genau das tut `weg(fuer:)`.
// 2. Ein GESPERRTES PDF ist nicht nil. pageCount stimmt, eine Miniatur
//    entsteht, und die Suche liefert null Treffer. Ohne isLocked-Abfrage wird
//    aus "Passwort noetig" ein stilles "keine Fundstelle" -- der teuerste
//    Fall, weil er wie ein Ergebnis aussieht.
// 3. Ein teilbeschaedigtes PDF oeffnet und liefert Text. CoreGraphics
//    protokolliert einen Fehler auf stderr, ueber die API kommt NICHTS an.
//    Diese Klasse kann das nicht erkennen und behauptet es auch nicht.

import Foundation

/// Womit ein Dokument angezeigt wird. Nach Format entschieden, weil kein
/// einzelner Weg alles kann.
public enum Anzeigeweg: String, Equatable, Sendable {
    /// PDFKit: aufschlagen, suchen, hervorheben -- alles drei gemessen.
    case pdf
    /// NSTextView: html und txt. Kann aufschlagen und hervorheben, mit
    /// Tastatur und zugaenglichem Namen. Quick Look kann hier NICHTS davon.
    case text
    /// Bilder. Nichts zu suchen, nichts hervorzuheben -- ehrlich gesagt statt
    /// eine Markierung vorzutaeuschen.
    case bild
    /// Alles Uebrige. Quick Look als Auffang, aber MIT dieser Vorpruefung,
    /// denn es sagt selbst nie "nein".
    case unbekannt

    public var kannHervorheben: Bool { self == .pdf || self == .text }
    public var kannAufschlagen: Bool { self == .pdf || self == .text }
}

/// Warum ein Dokument (nicht) angezeigt werden kann.
///
/// Die Texte gehen an den Menschen: seine Lage, seine naechste Handlung --
/// nie der Zustand des Quelltexts. Kein Dateipfad, kein Klassenname, keine
/// Fehlernummer.
public enum Dokumentbefund: Equatable, Sendable {
    case bereit
    case passwortNoetig
    case nichtLesbar
    case formatUnbekannt(endung: String)
    case fehlt

    public var istBereit: Bool { self == .bereit }

    public var meldung: String? {
        switch self {
        case .bereit:
            return nil
        case .passwortNoetig:
            return "Dieses Dokument ist mit einem Kennwort geschützt."
        case .nichtLesbar:
            return "Dieses Dokument lässt sich nicht öffnen."
        case .formatUnbekannt(let endung):
            return endung.isEmpty
                ? "Dieses Format kann hier nicht angezeigt werden."
                : "Dateien vom Typ \(endung) können hier nicht angezeigt werden."
        case .fehlt:
            return "Zu dieser Quelle ist keine Datei hinterlegt."
        }
    }

    /// Was der Mensch tun kann. Ohne diesen Satz ist eine Meldung eine
    /// Sackgasse -- und eine Sackgasse mitten in einer Besprechung ist
    /// schlimmer als eine leere Fläche, weil sie zum Suchen einlädt.
    public var handlung: String? {
        switch self {
        case .bereit:
            return nil
        case .passwortNoetig:
            return "Mit dem Kennwort öffnen"
        case .nichtLesbar, .formatUnbekannt:
            return "Mit einem anderen Programm öffnen"
        case .fehlt:
            return nil
        }
    }
}

public enum Quelldokument {
    /// Endungen, die wir NACHWEISLICH beherrschen. Bewusst eine Liste des
    /// Koennens, keine des Ausschliessens: Was nicht daraufsteht, geht an den
    /// Auffangweg und wird als solches benannt -- statt still zu scheitern.
    static let pdfEndungen: Set<String> = ["pdf"]
    static let textEndungen: Set<String> = ["html", "htm", "txt", "md", "xml"]
    static let bildEndungen: Set<String> = ["jpg", "jpeg", "png", "gif", "tiff", "tif", "heic"]

    public static func weg(fuer dateiname: String) -> Anzeigeweg {
        let e = endung(dateiname)
        if pdfEndungen.contains(e) { return .pdf }
        if textEndungen.contains(e) { return .text }
        if bildEndungen.contains(e) { return .bild }
        return .unbekannt
    }

    public static func endung(_ dateiname: String) -> String {
        (dateiname as NSString).pathExtension.lowercased()
    }

    /// Der Befund VOR dem Anzeigen. `istGesperrt` und `istLesbar` kommen von
    /// aussen (PDFKit), damit diese Entscheidung ohne PDFKit pruefbar bleibt
    /// -- dasselbe Muster wie RepoWurzel, das die Existenzpruefung auch von
    /// aussen bekommt.
    public static func befund(dateiname: String,
                              existiert: Bool,
                              istGesperrt: Bool = false,
                              istLesbar: Bool = true) -> Dokumentbefund {
        guard !dateiname.isEmpty, existiert else { return .fehlt }
        let w = weg(fuer: dateiname)
        if w == .unbekannt { return .formatUnbekannt(endung: endung(dateiname)) }
        // Reihenfolge ist bedeutungstragend: gesperrt VOR nicht-lesbar. Ein
        // gesperrtes PDF ist technisch lesbar (Seitenzahl stimmt, Miniatur
        // entsteht) und liefert trotzdem keinen Text -- wer zuerst auf
        // Lesbarkeit prueft, meldet nie das Kennwort.
        if w == .pdf && istGesperrt { return .passwortNoetig }
        if !istLesbar { return .nichtLesbar }
        return .bereit
    }

    /// Darf an dieser Stelle markiert werden?
    ///
    /// Drei Bedingungen, und alle drei muessen stehen: das Format kann es,
    /// das Dokument ist bereit, und es gibt einen Suchtext. Faellt eine weg,
    /// wird NICHT markiert -- eine Markierung ohne Beleg sieht im Raum aus
    /// wie ein Beleg, und dort widerspricht ihr niemand.
    public static func darfMarkieren(dateiname: String,
                                     befund: Dokumentbefund,
                                     suchtext: String?) -> Bool {
        guard befund.istBereit, let s = suchtext, !s.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        else { return false }
        return weg(fuer: dateiname).kannHervorheben
    }
}
