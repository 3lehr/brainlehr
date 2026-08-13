// Welche Quelle steht oben -- thematisch oder nach dem, was gerade zaehlt.
//
// ANLASS (Betreiber, 2026-08-13): "was noch toll waere ist ein art
// dateibrowser, aber nicht einfach so wie im dateisystem abgelegt, sondern
// einmal thematisch sortiert und zum umschalten live ranking durch die ki was
// gerade am wichtigsten ist!"
//
// ZWEI ORDNUNGEN, und die zweite ist die eigentliche Arbeit:
//   thematisch  Nach Gattung und Nummer. STABIL -- wer eine Quelle zweimal
//               sucht, findet sie am selben Platz. Das ist keine Schwaeche,
//               sondern der Zweck: ein Verzeichnis, das bei jeder Frage
//               umsortiert, ist kein Verzeichnis.
//   nach Lage   Was zur laufenden Arbeit passt, steht oben.
//
// WORAUS "WAS GERADE ZAEHLT" BERECHNET WIRD -- kein Modellaufruf, sondern
// vorhandene Signale:
//   1. Woerter aus dem Sitzungsstrom (was gerade besprochen wird)
//   2. Ob die Quelle ueberhaupt eine markierbare Stelle hat
//   3. Ihr gepflegter Rang im Quellenverzeichnis
// Ein Modell zu fragen waere teurer, langsamer und nicht nachvollziehbar --
// und die Rangfolge muss erklaerbar sein, sonst ist sie am Besprechungstisch
// wertlos ("warum steht das oben?").
//
// DIE HARTE REGEL, die ueber allem steht:
//
//   WAS DER BETRACHTER NICHT SEHEN DARF, TAUCHT IN KEINER RANGLISTE AUF --
//   UND WIRD AUCH NICHT MITGEZAEHLT.
//
// Gefiltert wird VOR dem Sortieren. Wer danach filtert, verraet ueber Luecken
// in der Nummerierung oder ueber eine Gesamtzahl, DASS es etwas gibt. Bei
// WEG-Rechtsfaellen mit Namen Dritter ist schon das eine Aussage.

import Foundation

/// Eine Quelle, so wie die Rangfolge sie braucht.
public struct Quellenzeile: Equatable, Sendable {
    public let nummer: String
    public let kurz: String
    /// Gattung aus dem Quellenverzeichnis: gesetz, vertrag, urteil, ...
    public let art: String
    public let freigabe: String?
    public let markierbar: Bool
    /// Gepflegter Rang, kleiner ist wichtiger. 0 = ohne Angabe.
    public let rang: Int

    public init(nummer: String, kurz: String, art: String = "",
                freigabe: String? = "offen", markierbar: Bool = false, rang: Int = 0) {
        self.nummer = nummer; self.kurz = kurz; self.art = art
        self.freigabe = freigabe; self.markierbar = markierbar; self.rang = rang
    }
}

public enum Ordnung: String, Sendable, CaseIterable {
    case thematisch
    case nachLage

    public var titel: String {
        switch self {
        case .thematisch: return "Nach Thema"
        case .nachLage: return "Was gerade zählt"
        }
    }
}

/// Eine Quelle mit ihrem Platz und der BEGRUENDUNG dafuer.
///
/// Die Begruendung ist kein Beiwerk: Eine Rangfolge, die niemand erklaeren
/// kann, ist am Besprechungstisch wertlos. Wer fragt "warum steht das oben",
/// bekommt eine Antwort statt eines Achselzuckens.
public struct Rangplatz: Equatable, Sendable {
    public let zeile: Quellenzeile
    public let punkte: Double
    public let begruendung: String
}

public enum Rangfolge {

    /// Reihenfolge der Gattungen. Recht vor Vertrag vor Beleg -- bei einer
    /// Rechtsfrage ist die Norm die Grundlage, nicht das Angebot.
    /// Am echten Bestand abgeglichen (2026-08-13, 49 Quellen): "rechtsprechung"
    /// stand nicht drin und waere auf den Sammelplatz 8 gefallen -- hinter
    /// Rechnungen. Bei einer WEG-Frage ist ein BGH-Urteil aber Grundlage,
    /// nicht Beiwerk. Eine Rangliste, die den eigenen Bestand nicht kennt,
    /// sortiert die wichtigsten Quellen nach unten.
    static let gattungsrang = [
        // Recht zuerst -- bei einer WEG-Frage ist die Norm die Grundlage.
        "gesetz": 0, "gesetzestext": 0, "verordnung": 0,
        "urteil": 1, "rechtsprechung": 1,
        "richtlinie": 2, "merkblatt": 2,
        // Was die Gemeinschaft selbst bindet.
        "urkunde": 3, "vertrag": 3, "bescheid": 3,
        "angebot": 4, "protokoll": 5,
        "schriftverkehr": 6, "rechnung": 6, "auswertung": 7,
    ]

    static func gattung(_ a: String) -> Int { gattungsrang[a.lowercased()] ?? 8 }

    /// Woerter, die nichts ueber das Thema sagen. Ohne sie wuerde jede Quelle
    /// zu jeder Frage passen -- und eine Rangfolge, die immer alles nach oben
    /// holt, ist keine.
    static let fuellwoerter: Set<String> = [
        "der", "die", "das", "und", "oder", "ist", "sind", "war", "waren",
        "ein", "eine", "einer", "eines", "einem", "einen", "den", "dem", "des",
        "für", "fuer", "mit", "von", "vom", "zum", "zur", "auf", "aus", "bei",
        "nicht", "auch", "noch", "nur", "dann", "wenn", "aber", "wie", "was",
        "wir", "ich", "sie", "man", "sich", "kann", "muss", "soll", "wird",
        "haben", "hat", "hatte", "dass", "dann", "also", "sehr", "mehr",
    ]

    /// Bedeutungstragende Woerter eines Textes.
    public static func stichwoerter(_ text: String) -> Set<String> {
        let teile = text.lowercased()
            .components(separatedBy: CharacterSet.alphanumerics.inverted)
            .filter { $0.count >= 4 && !fuellwoerter.contains($0) }
        return Set(teile)
    }

    /// Thematisch: Gattung, dann gepflegter Rang, dann Nummer.
    ///
    /// STABIL und ohne Bezug zur laufenden Arbeit -- genau das ist der Zweck.
    public static func thematisch(_ zeilen: [Quellenzeile]) -> [Quellenzeile] {
        zeilen.sorted { a, b in
            let (ga, gb) = (gattung(a.art), gattung(b.art))
            if ga != gb { return ga < gb }
            let (ra, rb) = (a.rang == 0 ? Int.max : a.rang, b.rang == 0 ? Int.max : b.rang)
            if ra != rb { return ra < rb }
            return (Int(a.nummer) ?? 0) < (Int(b.nummer) ?? 0)
        }
    }

    /// Nach Lage: was zur laufenden Arbeit passt, steht oben.
    ///
    /// `lagewoerter` kommt aus dem Sitzungsstrom. Ist es leer, faellt die
    /// Ordnung auf die thematische zurueck -- ohne Bezug gibt es nichts zu
    /// gewichten, und dann eine Reihenfolge zu erfinden waere Rauschen.
    public static func nachLage(_ zeilen: [Quellenzeile],
                                lagewoerter: Set<String>) -> [Rangplatz] {
        zeilen.map { z in
            var punkte = 0.0
            var gruende: [String] = []

            let eigene = stichwoerter(z.kurz)
            let treffer = eigene.intersection(lagewoerter)
            if !treffer.isEmpty {
                // Jedes gemeinsame Wort zaehlt, aber mit abnehmendem Gewicht:
                // Der Sprung von null auf ein Wort ist die eigentliche
                // Aussage, der von acht auf neun sagt fast nichts mehr.
                punkte += 3.0 * (1.0 + log(Double(treffer.count)))
                gruende.append("passt zu \(treffer.sorted().prefix(3).joined(separator: ", "))")
            }
            if z.markierbar {
                // Eine Quelle, deren Stelle bekannt ist, laesst sich SOFORT
                // zeigen. Am Besprechungstisch ist das der Unterschied
                // zwischen Beleg und Suche.
                punkte += 1.5
                gruende.append("Stelle bekannt")
            }
            if z.rang > 0 {
                punkte += max(0.0, 1.0 - Double(z.rang) / 10.0)
            }
            return Rangplatz(zeile: z, punkte: punkte,
                             begruendung: gruende.isEmpty ? "kein Bezug zur laufenden Arbeit"
                                                          : gruende.joined(separator: " · "))
        }
        .sorted { a, b in
            if a.punkte != b.punkte { return a.punkte > b.punkte }
            // Bei Gleichstand die thematische Ordnung -- nie zufaellig, sonst
            // springt die Liste bei jedem Neuzeichnen.
            let (ga, gb) = (gattung(a.zeile.art), gattung(b.zeile.art))
            if ga != gb { return ga < gb }
            return (Int(a.zeile.nummer) ?? 0) < (Int(b.zeile.nummer) ?? 0)
        }
    }

    /// Die eine Tuer: filtert, ordnet, begruendet.
    ///
    /// GEFILTERT WIRD ZUERST. Wer nach dem Sortieren filtert, verraet ueber
    /// Luecken in der Reihenfolge, dass es mehr gibt -- und schon das ist bei
    /// Namen Dritter eine Aussage.
    public static func liste(_ zeilen: [Quellenzeile],
                             ordnung: Ordnung,
                             betrachter: Betrachter,
                             lagewoerter: Set<String> = []) -> [Rangplatz] {
        let sichtbar = Sichtbarkeit.sichtbar(zeilen, betrachter) { $0.freigabe }
        switch ordnung {
        case .thematisch:
            return thematisch(sichtbar).map {
                Rangplatz(zeile: $0, punkte: 0, begruendung: $0.art.isEmpty ? "" : $0.art)
            }
        case .nachLage:
            guard !lagewoerter.isEmpty else {
                return thematisch(sichtbar).map {
                    Rangplatz(zeile: $0, punkte: 0,
                              begruendung: "noch kein Bezug zur laufenden Arbeit")
                }
            }
            return nachLage(sichtbar, lagewoerter: lagewoerter)
        }
    }

    /// Die Stichwoerter der laufenden Arbeit aus dem Sitzungsstrom.
    ///
    /// Nur die juengsten Ereignisse: Was vor einer Stunde besprochen wurde,
    /// ist fuer "was gerade zaehlt" kein Bezug mehr. Werkzeugnamen und
    /// Rueckgaben bleiben draussen -- "Bash" und "48 Quellen" sagen nichts
    /// ueber das Thema.
    public static func lageAus(_ ereignisse: [Sitzungsereignis],
                               juengste: Int = 12) -> Set<String> {
        let bedeutsam = ereignisse.filter {
            $0.art == .eingabe || $0.art == .antwort || $0.art == .denken
        }
        return Set(bedeutsam.suffix(juengste).flatMap { stichwoerter($0.text) })
    }
}
