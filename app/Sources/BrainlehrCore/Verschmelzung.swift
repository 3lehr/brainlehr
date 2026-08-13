// Zwei Schreiber auf einem Dokument -- ohne dass etwas verlorengeht.
//
// ANLASS (Betreiber, 2026-08-13): "das warum ist kein grund! ich will das du
// das baust!" -- zur Live-Bearbeitung, die ich im Plan gestrichen hatte.
//
// MEIN EINWAND WAR SACHLICH RICHTIG UND DIE FOLGERUNG FALSCH. Richtig ist:
// Zwei Schreiber auf einem Dokument ohne Konfliktaufloesung verlieren
// Aenderungen, und zwar LEISE -- kein Fehler, keine Meldung, der Text ist
// einfach weg. Falsch war der Schluss "also nicht bauen". Die Aufgabe lautet
// nicht "vermeiden", sondern "so bauen, dass nichts verlorengeht".
//
// DIE BAUFORM: Drei-Wege-Verschmelzung auf Absatzebene, wie bei Git. Beide
// Seiten kennen eine gemeinsame Vorfassung; verglichen wird jede Seite GEGEN
// DIESE, nicht gegeneinander. Damit ist unterscheidbar, wer etwas geaendert
// hat -- und nur wo BEIDE denselben Absatz angefasst haben, entsteht ein
// Konflikt. Alles andere verschmilzt ohne Rueckfrage.
//
// WARUM ABSATZ UND NICHT ZEILE: Ein Rechtstext wird absatzweise umformuliert.
// Zeilenweise verglichen erzeugt jede Umbruchaenderung einen Scheinkonflikt,
// und wer drei Scheinkonflikte gesehen hat, klickt den vierten echten weg.
//
// WAS HIER BEWUSST FEHLT: kein CRDT, keine Zeichen-genaue Verschmelzung, kein
// Sperrprotokoll. Ein CRDT loest gleichzeitiges Tippen im selben Wort -- das
// Problem hat ein Mensch mit einem Modell nicht, weil das Modell in
// Absaetzen schreibt und nicht buchstabenweise mittippt.

import Foundation

/// Ein Absatz nach der Verschmelzung.
public struct Absatz: Equatable, Sendable {
    public enum Herkunft: String, Equatable, Sendable {
        case unveraendert   // niemand hat ihn angefasst
        case vomMenschen    // nur der Mensch
        case vomModell      // nur das Modell
        case konflikt       // BEIDE, und verschieden
    }
    /// Was aktuell gilt.
    public let text: String
    public let herkunft: Herkunft

    /// Die beiden Fassungen, BENANNT statt ueber die Position gemeint.
    ///
    /// Der Vorgaenger hatte ein einzelnes `andereFassung`, dessen Bedeutung
    /// von der Herkunft abhing: bei `.konflikt` war `text` der Mensch und
    /// `andereFassung` das Modell, bei `.vomModell` genau umgekehrt.
    /// `entscheide` konnte beides nicht auseinanderhalten und lieferte bei
    /// "Vorschlag ablehnen" den Vorschlag zurueck. Dieselbe Fehlerklasse, die
    /// heute schon zweimal zugeschlagen hat: nach der FORM gehen statt nach
    /// der Bedeutung.
    public let fassungMensch: String?
    public let fassungModell: String?

    public init(text: String, herkunft: Herkunft,
                fassungMensch: String? = nil, fassungModell: String? = nil) {
        self.text = text; self.herkunft = herkunft
        self.fassungMensch = fassungMensch; self.fassungModell = fassungModell
    }

    /// Die jeweils andere Fassung -- fuer die Anzeige, die beide
    /// nebeneinander stellt, statt eine zu verstecken.
    public var andereFassung: String? {
        switch herkunft {
        case .konflikt:   return fassungModell
        case .vomModell:  return fassungMensch
        case .vomMenschen, .unveraendert: return nil
        }
    }

    /// Gibt es hier etwas zu entscheiden?
    public var offen: Bool { herkunft == .konflikt || herkunft == .vomModell }
}

public struct Verschmelzungsergebnis: Equatable, Sendable {
    public let absaetze: [Absatz]

    public var text: String { absaetze.map(\.text).joined(separator: "\n\n") }
    public var konflikte: Int { absaetze.filter { $0.herkunft == .konflikt }.count }
    public var hatKonflikte: Bool { konflikte > 0 }

    /// Was der Mensch sieht, wenn nichts zu entscheiden ist.
    public var meldung: String? {
        guard hatKonflikte else { return nil }
        return konflikte == 1
            ? "Ein Absatz wurde von beiden Seiten geändert."
            : "\(konflikte) Absätze wurden von beiden Seiten geändert."
    }
}

public enum Verschmelzung {

    /// Zerlegt in Absaetze. Leerzeilen trennen, Leerraum am Rand faellt weg.
    public static func absaetze(_ text: String) -> [String] {
        text.components(separatedBy: "\n\n")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
    }

    /// Ordnet die Absaetze einer geaenderten Fassung denen der Vorfassung zu.
    ///
    /// Rueckgabe je Vorfassungs-Absatz: der Text danach, oder `nil` fuer
    /// geloescht. Dazu getrennt, was hinten neu angehaengt wurde.
    ///
    /// WARUM NICHT UEBER DIE POSITION -- gemessen, nicht vermutet: Loescht
    /// der Mensch Absatz B und aendert das Modell Absatz C, verschiebt sich
    /// beim Menschen alles um eins. Positionsweise verglichen wird C dann
    /// einmal als "Aenderung des Menschen" und einmal als "Aenderung des
    /// Modells" gefuehrt -- der Absatz erscheint ZWEIMAL im Ergebnis. In
    /// einem Rechtstext ist ein verdoppelter Absatz genauso falsch wie ein
    /// verlorener, nur auffaelliger.
    ///
    /// Darum ueber gemeinsame ANKER (laengste gemeinsame Teilfolge): Absaetze,
    /// die woertlich erhalten blieben, sind Fixpunkte; was dazwischen liegt,
    /// gehoert zusammen. Das ist derselbe Ansatz wie bei jedem Diff.
    /// - `zuordnung[i]`: was aus dem i-ten alten Absatz wurde, `nil` = geloescht
    /// - `eingefuegt[i]`: was VOR dem i-ten alten Absatz neu dazukam
    /// - `angehaengt`: was nach dem letzten alten Absatz dazukam
    struct Zuordnung: Equatable {
        var zuordnung: [String?]
        var eingefuegt: [Int: [String]]
        var angehaengt: [String]
    }

    static func ordne(_ alt: [String], _ neu: [String]) -> Zuordnung {
        if alt.isEmpty {
            return Zuordnung(zuordnung: [], eingefuegt: [:], angehaengt: neu)
        }
        // Laengste gemeinsame Teilfolge ueber eine Tabelle.
        var tab = Array(repeating: Array(repeating: 0, count: neu.count + 1), count: alt.count + 1)
        for i in stride(from: alt.count - 1, through: 0, by: -1) {
            for j in stride(from: neu.count - 1, through: 0, by: -1) {
                tab[i][j] = alt[i] == neu[j] ? tab[i+1][j+1] + 1 : max(tab[i+1][j], tab[i][j+1])
            }
        }
        var anker: [(alt: Int, neu: Int)] = []
        var i = 0, j = 0
        while i < alt.count && j < neu.count {
            if alt[i] == neu[j] { anker.append((i, j)); i += 1; j += 1 }
            else if tab[i+1][j] >= tab[i][j+1] { i += 1 } else { j += 1 }
        }

        var erg = Zuordnung(zuordnung: [String?](repeating: nil, count: alt.count),
                            eingefuegt: [:], angehaengt: [])
        var altAb = 0, neuAb = 0

        // Ein Bereich zwischen zwei Ankern: die alten Absaetze darin wurden
        // durch die neuen darin ersetzt. Paarweise zuordnen; was auf einer
        // Seite uebrig bleibt, ist geloescht bzw. eingefuegt -- nie verworfen.
        func bereich(bisAlt: Int, bisNeu: Int) {
            let alte = Array(altAb..<bisAlt)
            let neue = Array(neuAb..<bisNeu)
            for (n, idx) in alte.enumerated() {
                erg.zuordnung[idx] = n < neue.count ? neu[neue[n]] : nil
            }
            if neue.count > alte.count {
                let rest = neue[alte.count...].map { neu[$0] }
                if bisAlt < alt.count {
                    erg.eingefuegt[bisAlt, default: []].append(contentsOf: rest)
                } else {
                    erg.angehaengt.append(contentsOf: rest)
                }
            }
        }

        for a in anker {
            bereich(bisAlt: a.alt, bisNeu: a.neu)
            erg.zuordnung[a.alt] = neu[a.neu]
            altAb = a.alt + 1; neuAb = a.neu + 1
        }
        bereich(bisAlt: alt.count, bisNeu: neu.count)
        return erg
    }

    /// Drei-Wege-Verschmelzung: `vorfassung` ist der letzte Stand, den BEIDE
    /// gesehen haben.
    public static func verschmelze(vorfassung: String,
                                   mensch: String,
                                   modell: String) -> Verschmelzungsergebnis {
        let v = absaetze(vorfassung)
        let m = ordne(v, absaetze(mensch))
        let k = ordne(v, absaetze(modell))
        var ergebnis: [Absatz] = []

        func einfuegungen(vor i: Int) {
            // Was der Mensch eingefuegt hat, steht; was das Modell eingefuegt
            // hat, ist ein VORSCHLAG. Beides kommt durch, nichts wird still
            // verworfen -- auch nicht, wenn beide an derselben Stelle
            // eingefuegt haben.
            for t in m.eingefuegt[i] ?? [] { ergebnis.append(.init(text: t, herkunft: .vomMenschen)) }
            for t in k.eingefuegt[i] ?? [] {
                ergebnis.append(.init(text: t, herkunft: .vomModell,
                                      fassungMensch: nil, fassungModell: t))
            }
        }

        for i in 0..<v.count {
            einfuegungen(vor: i)
            let alt = v[i], mensch = m.zuordnung[i], modell = k.zuordnung[i]

            // Beide haben gestrichen -- weg, und das ist Einigkeit, kein Konflikt.
            if mensch == nil && modell == nil { continue }
            // Nur eine Seite streicht: Loeschen ist eine Aenderung wie jede
            // andere. Hat die andere Seite NICHTS geaendert, gilt die Loeschung.
            if mensch == nil {
                if modell! != alt { ergebnis.append(.init(text: modell!, herkunft: .vomModell)) }
                continue
            }
            if modell == nil {
                if mensch! != alt { ergebnis.append(.init(text: mensch!, herkunft: .vomMenschen)) }
                continue
            }

            switch (mensch! != alt, modell! != alt) {
            case (false, false):
                ergebnis.append(.init(text: mensch!, herkunft: .unveraendert))
            case (true, false):
                ergebnis.append(.init(text: mensch!, herkunft: .vomMenschen))
            case (false, true):
                // Der Regelfall der Live-Bearbeitung: Das Modell schlaegt
                // etwas vor, der Mensch hat den Absatz nicht angefasst.
                ergebnis.append(.init(text: modell!, herkunft: .vomModell,
                                      fassungMensch: alt, fassungModell: modell!))
            case (true, true):
                if mensch! == modell! {
                    ergebnis.append(.init(text: mensch!, herkunft: .unveraendert))
                } else {
                    // DER FALL, UM DEN ES GEHT. Die Fassung des MENSCHEN steht
                    // vorn: Wer selbst getippt hat, soll seinen Text sehen und
                    // nicht suchen muessen. Die andere geht nicht verloren,
                    // sie wird danebengestellt.
                    ergebnis.append(.init(text: mensch!, herkunft: .konflikt,
                                          fassungMensch: mensch!, fassungModell: modell!))
                }
            }
        }
        einfuegungen(vor: v.count)
        for t in m.angehaengt { ergebnis.append(.init(text: t, herkunft: .vomMenschen)) }
        for t in k.angehaengt {
            // Angehaengter Vorschlag: ablehnen heisst hier "weg", nicht
            // "zurueck zur Vorfassung" -- es gab keine.
            ergebnis.append(.init(text: t, herkunft: .vomModell,
                                  fassungMensch: nil, fassungModell: t))
        }
        return Verschmelzungsergebnis(absaetze: ergebnis)
    }

    /// Loest einen Konflikt auf, ohne den Rest anzufassen.
    public enum Wahl: String, Sendable { case mensch, modell, beide }

    public static func entscheide(_ e: Verschmelzungsergebnis,
                                  absatz i: Int, wahl: Wahl) -> Verschmelzungsergebnis {
        // Entschieden werden kann ueber Konflikte UND ueber Vorschlaege des
        // Modells -- das ist der Betreiberauftrag: "ki macht live vorschlaege,
        // mensch darf live korrigieren und schreiben". Ein Vorschlag, den man
        // nur ansehen, aber nicht ablehnen kann, ist keiner.
        guard i >= 0, i < e.absaetze.count,
              e.absaetze[i].herkunft == .konflikt || e.absaetze[i].herkunft == .vomModell
        else { return e }
        var neu = e.absaetze
        let a = neu[i]
        switch wahl {
        case .mensch:
            // Ablehnen. Gab es keine Fassung des Menschen (reiner Einschub des
            // Modells), faellt der Absatz weg -- das ist die Ablehnung.
            if let m = a.fassungMensch {
                neu[i] = .init(text: m, herkunft: .vomMenschen, fassungMensch: m)
            } else {
                neu.remove(at: i)
            }
        case .modell:
            let k = a.fassungModell ?? a.text
            neu[i] = .init(text: k, herkunft: .vomModell, fassungMensch: nil, fassungModell: k)
        case .beide:
            // Beide behalten, in dieser Reihenfolge -- die haeufigste richtige
            // Antwort bei Rechtstexten, weil zwei Formulierungen oft zwei
            // Gedanken sind und nicht zwei Fassungen desselben.
            let zusammen = [a.fassungMensch, a.fassungModell]
                .compactMap { $0 }.joined(separator: "\n\n")
            neu[i] = .init(text: zusammen.isEmpty ? a.text : zusammen, herkunft: .vomMenschen)
        }
        return Verschmelzungsergebnis(absaetze: neu)
    }
}
