// Aus zwei Textfassungen die kleinste Aenderung machen -- der Kern des
// Dokumentfensters (F5).
//
// WARUM DAS NOETIG IST, und es ist der ganze Punkt von "Zeichen fuer Zeichen":
// Ein Textfeld meldet bei jedem Tastendruck den GANZEN neuen Text. Wer den
// einfach in das gemeinsame Dokument schreibt, loescht dort alles und fuegt
// alles neu ein. Fuer den Bildschirm sieht das gleich aus -- fuer ein CRDT
// nicht: die Aenderung des anderen wird dabei mitgeloescht und danach als
// Konflikt wieder eingefuegt oder ist schlicht weg. Aus "beide tippen im selben
// Satz" wird "der Schnellere gewinnt".
//
// Deshalb wird die Differenz gebildet: gemeinsames Praefix, gemeinsames Suffix,
// und dazwischen genau eine Loeschung und eine Einfuegung. Das ist keine
// vollstaendige Differenzrechnung (kein Myers-Algorithmus) und muss es nicht
// sein: eine Tastatureingabe aendert eine zusammenhaengende Stelle. Wer den
// ganzen Text auf einmal ersetzt (Einfuegen aus der Zwischenablage), bekommt
// eine grosse Aenderung -- richtig, nur eben nicht klein.
//
// EINHEIT IST DAS UTF-8-BYTE, nicht das Zeichen: `yswift` und `pycrdt` zaehlen
// Positionen in der UTF-8-Sicht (YText.insert(_:at:) nimmt "die Position
// innerhalb des UTF-8-Puffers"). Wer hier in Swift-Characters rechnet, trifft
// bei jedem Umlaut daneben -- und zwar still, weil der Text danach nur
// verschoben ist, nicht kaputt.

import Foundation

public enum Textabgleich {

    /// Eine zusammenhaengende Aenderung, in UTF-8-Bytes gemessen.
    public struct Aenderung: Equatable, Sendable {
        /// Wo die Aenderung ansetzt (UTF-8-Bytes vom Anfang).
        public let bei: UInt32
        /// Wie viele Bytes dort entfallen.
        public let geloescht: UInt32
        /// Was dort eingefuegt wird.
        public let eingefuegt: String

        public var istLeer: Bool { geloescht == 0 && eingefuegt.isEmpty }

        public init(bei: UInt32, geloescht: UInt32, eingefuegt: String) {
            self.bei = bei
            self.geloescht = geloescht
            self.eingefuegt = eingefuegt
        }
    }

    /// Die kleinste zusammenhaengende Aenderung von `alt` nach `neu`.
    ///
    /// Gibt eine leere Aenderung zurueck, wenn beide gleich sind -- der
    /// Aufrufer muss dann nichts senden. Das ist nicht Sparsamkeit: ein
    /// Update ohne Inhalt weckt bei jedem anderen Teilnehmer eine Neuzeichnung.
    public static func aenderung(von alt: String, nach neu: String) -> Aenderung {
        let a = Array(alt.utf8)
        let n = Array(neu.utf8)
        if a == n { return Aenderung(bei: 0, geloescht: 0, eingefuegt: "") }

        // Gemeinsames Praefix -- aber nur bis zu einer Zeichengrenze, sonst
        // entsteht eine Position mitten in einem Mehrbyte-Zeichen und die
        // eingefuegte Zeichenkette ist danach ungueltiges UTF-8.
        var vorne = 0
        while vorne < a.count && vorne < n.count && a[vorne] == n[vorne] { vorne += 1 }
        // Zurueck auf die naechste Zeichengrenze. Geprueft wird an BEIDEN
        // Fassungen: `vorne` kann das Ende der einen erreicht haben und
        // trotzdem mitten in einem Zeichen der anderen liegen -- und ein Index
        // gleich der Laenge ist kein gueltiger Zugriff (hier zuerst als
        // Absturz aufgefallen, nicht als falsches Ergebnis).
        while vorne > 0 && (istFolgebyteAn(a, vorne) || istFolgebyteAn(n, vorne)) { vorne -= 1 }

        // Gemeinsames Suffix, ebenfalls auf Zeichengrenze zurueckgesetzt.
        var hinten = 0
        while hinten < (a.count - vorne) && hinten < (n.count - vorne)
                && a[a.count - 1 - hinten] == n[n.count - 1 - hinten] {
            hinten += 1
        }
        while hinten > 0 && (istFolgebyteAn(a, a.count - hinten)
                             || istFolgebyteAn(n, n.count - hinten)) {
            hinten -= 1
        }

        let entfallen = a.count - vorne - hinten
        let neueBytes = Array(n[vorne..<(n.count - hinten)])
        return Aenderung(bei: UInt32(vorne),
                         geloescht: UInt32(max(0, entfallen)),
                         eingefuegt: String(decoding: neueBytes, as: UTF8.self))
    }

    /// Ein UTF-8-Folgebyte (10xxxxxx) -- an dieser Stelle darf nicht getrennt
    /// werden.
    static func istFolgebyte(_ byte: UInt8) -> Bool {
        byte & 0b1100_0000 == 0b1000_0000
    }

    /// Wie `istFolgebyte`, aber ein Index am Ende ist keine Trennstelle mitten
    /// im Zeichen, sondern schlicht das Ende -- und kein gueltiger Zugriff.
    static func istFolgebyteAn(_ bytes: [UInt8], _ index: Int) -> Bool {
        index >= 0 && index < bytes.count && istFolgebyte(bytes[index])
    }

    /// Wendet eine Aenderung an -- nur fuer Proben. Im Betrieb tut das die
    /// CRDT-Bibliothek; diese Funktion belegt, dass die Rechnung stimmt.
    public static func wendeAn(_ aenderung: Aenderung, auf text: String) -> String {
        var bytes = Array(text.utf8)
        let bei = Int(aenderung.bei)
        guard bei <= bytes.count else { return text }
        let bis = min(bytes.count, bei + Int(aenderung.geloescht))
        bytes.replaceSubrange(bei..<bis, with: Array(aenderung.eingefuegt.utf8))
        return String(decoding: bytes, as: UTF8.self)
    }
}
