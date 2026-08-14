// Zwei Schreiber auf EINEM Dokument -- live nebeneinander, nichts verlorengeht.
//
// Schritt B5 aus docs/PLAN_OBERFLAECHE_2026-08-13.md. Betreiber woertlich:
// "ki macht live vorschlaege, mensch darf live korrigieren und schreiben".
// Die Verschmelzung selbst leistet BrainlehrCore/Verschmelzung.swift (fertig,
// 20 Tests) -- diese Ansicht zeigt nur, was dabei herauskommt, und lenkt
// Entscheidungen an sie zurueck.
//
// DIE BEDIENFLAECHE FUER DEN MENSCHEN IST FLIESSTEXT, KEIN FELD JE ABSATZ:
// Verschmelzung.absaetze() trennt an Leerzeilen -- wer im Fliesstext tippt,
// bearbeitet damit automatisch genau EINEN Absatz, ohne Sperre und ohne
// Umweg ueber eine Zeilennummer, die sich beim naechsten Einfuegen ohnehin
// verschieben wuerde. Das deckt "jederzeit jeden Absatz bearbeiten"
// vollstaendiger ab als ein Feld pro Zeile.
//
// WARUM EINE ENTSCHEIDUNG NICHT DEN QUELLTEXT AENDERT, SONDERN GEMERKT WIRD:
// Verschmelzungsergebnis hat keinen oeffentlichen Konstruktor -- mit Absicht,
// denn ein von aussen zusammengesetztes Ergebnis koennte die Drei-Wege-Logik
// umgehen. Angenommene und abgelehnte Vorschlaege werden darum je Absatzindex
// gemerkt und bei jeder Neuverschmelzung erneut ueber Verschmelzung.entscheide
// angewandt -- absteigend nach Index, weil eine Ablehnung eines reinen
// Einschubs den Absatz ENTFERNT und damit alle folgenden Indizes verschiebt.
//
// ponytail: Entscheidungen sind indexbasiert und gelten fuer den aktuellen
// Diff-Stand. Wer NACH einer Entscheidung den rohen Text so aendert, dass
// sich die Absatzzahl davor verschiebt, kann eine alte Entscheidung auf den
// falschen Absatz treffen lassen. Fuer die drei geforderten Vorfuehrfaelle
// ohne Zwischenschritt ist das kein Problem; ein stabiler Absatz-Anker waere
// der Ausbau, falls freies Nacheinander von Text- UND Entscheidungsaenderung
// noetig wird.

import BrainlehrCore
import SwiftUI

struct BearbeitungsAnsicht: View {
    @State private var vorfassung = Beispiel.vorfassung
    @State private var mensch = Beispiel.mensch
    @State private var modell = Beispiel.modell
    /// Je Absatzindex im JEWEILS AKTUELLEN Ergebnis eine getroffene Wahl.
    @State private var entschieden: [Int: Verschmelzung.Wahl] = [:]

    private var ergebnis: Verschmelzungsergebnis {
        var e = Verschmelzung.verschmelze(vorfassung: vorfassung, mensch: mensch, modell: modell)
        for (i, wahl) in entschieden.sorted(by: { $0.key > $1.key }) {
            e = Verschmelzung.entscheide(e, absatz: i, wahl: wahl)
        }
        return e
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Kopfzeile(ergebnis: ergebnis)
            Divider()
            HStack(spacing: 0) {
                Bearbeitungsfeld(titel: "Ihr Text", text: $mensch)
                Divider()
                Bearbeitungsfeld(titel: "Vorschlag des Modells", text: $modell)
            }
            .frame(height: 160)
            Divider()
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 10) {
                    ForEach(Array(ergebnis.absaetze.enumerated()), id: \.offset) { i, absatz in
                        AbsatzZeile(absatz: absatz) { wahl in entschieden[i] = wahl }
                    }
                }
                .padding(12)
            }
        }
    }
}

// MARK: - Kopf und Bearbeitungsfelder

private struct Kopfzeile: View {
    let ergebnis: Verschmelzungsergebnis

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Bearbeitung").font(.headline).accessibilityAddTraits(.isHeader)
            Text(ergebnis.meldung ?? "Kein Absatz wartet auf eine Entscheidung.")
                .font(.subheadline).foregroundStyle(.secondary)
        }
        .padding(.horizontal).padding(.vertical, 8)
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct Bearbeitungsfeld: View {
    let titel: String
    @Binding var text: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(titel).font(.caption.bold()).foregroundStyle(.secondary)
                .padding(.horizontal, 8).padding(.top, 6)
            TextEditor(text: $text)
                .font(.body)
                .accessibilityLabel(titel)
                .padding(.horizontal, 4)
        }
        .frame(maxWidth: .infinity)
    }
}

// MARK: - Ein Absatz

private struct AbsatzZeile: View {
    let absatz: Absatz
    let entscheiden: (Verschmelzung.Wahl) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Herkunftsmarke(herkunft: absatz.herkunft)
            if absatz.herkunft == .konflikt {
                HStack(alignment: .top, spacing: 12) {
                    Fassungskasten(titel: "Ihre Fassung", text: absatz.fassungMensch ?? absatz.text)
                    Fassungskasten(titel: "Vorschlag des Modells", text: absatz.fassungModell ?? "")
                }
            } else {
                Text(absatz.text)
                    .textSelection(.enabled)
                    .padding(8)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(.quaternary, in: RoundedRectangle(cornerRadius: 6))
            }
            // Entscheiden kann man bei .vomModell (reiner Vorschlag) UND bei
            // .konflikt (beide haben geaendert) -- Absatz.offen fasst das
            // zusammen, siehe BrainlehrCore.
            if absatz.offen {
                HStack(spacing: 8) {
                    Button("Annehmen") { entscheiden(.modell) }
                        .frame(minWidth: 24, minHeight: 24)
                        .accessibilityHint("Übernimmt den Vorschlag des Modells für diesen Absatz.")
                    Button("Ablehnen") { entscheiden(.mensch) }
                        .frame(minWidth: 24, minHeight: 24)
                        .accessibilityHint("Stellt Ihre eigene Fassung dieses Absatzes wieder her, nicht den Vorschlag.")
                }
            }
        }
        .padding(10)
        .background(.background, in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(.separator))
    }
}

/// Herkunft je IMMER als Wort UND Symbol -- nie allein über Farbe erkennbar.
private struct Herkunftsmarke: View {
    let herkunft: Absatz.Herkunft

    private var beschriftung: (text: String, symbol: String) {
        switch herkunft {
        case .unveraendert: return ("Unverändert", "checkmark")
        case .vomMenschen:  return ("Von Ihnen", "pencil")
        case .vomModell:    return ("Vorschlag des Modells", "sparkles")
        case .konflikt:     return ("Von beiden geändert", "arrow.triangle.branch")
        }
    }

    var body: some View {
        Label(beschriftung.text, systemImage: beschriftung.symbol)
            .font(.caption.bold())
            .foregroundStyle(.secondary)
            .accessibilityLabel(beschriftung.text)
    }
}

private struct Fassungskasten: View {
    let titel: String
    let text: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(titel).font(.caption.bold()).foregroundStyle(.secondary)
            Text(text).textSelection(.enabled)
        }
        .padding(8)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.quaternary, in: RoundedRectangle(cornerRadius: 6))
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(titel): \(text)")
    }
}

// MARK: - Beispiel

/// Eingebautes Vorfuehrdokument. EIN Beispiel deckt alle drei Abnahmefaelle
/// ab, ohne Szenario-Umschalter: §1 aendert nur der Mensch, §2 aendert nur
/// das Modell (Vorschlag), §3 aendern beide -- verschieden (Konflikt).
private enum Beispiel {
    static let vorfassung = """
    § 1 Die Eigentümerversammlung wird mindestens einmal im Kalenderjahr durch den Verwalter einberufen.

    § 2 Beschlüsse werden mit einfacher Mehrheit der abgegebenen Stimmen gefasst, soweit das Gesetz oder die Gemeinschaftsordnung nichts anderes bestimmt.

    § 3 Über jede Versammlung ist eine Niederschrift zu fertigen, die vom Verwalter zu unterschreiben ist.
    """

    static let mensch = """
    § 1 Die Eigentümerversammlung wird mindestens einmal jährlich, spätestens jedoch bis zum 30. Juni, durch den Verwalter einberufen.

    § 2 Beschlüsse werden mit einfacher Mehrheit der abgegebenen Stimmen gefasst, soweit das Gesetz oder die Gemeinschaftsordnung nichts anderes bestimmt.

    § 3 Über jede Versammlung ist eine Niederschrift zu fertigen, die vom Verwalter und vom Versammlungsleiter zu unterschreiben ist.
    """

    static let modell = """
    § 1 Die Eigentümerversammlung wird mindestens einmal im Kalenderjahr durch den Verwalter einberufen.

    § 2 Beschlüsse werden mit einfacher Mehrheit der abgegebenen, gültigen Stimmen gefasst, soweit das Gesetz oder die Gemeinschaftsordnung nichts anderes bestimmt.

    § 3 Über jede Versammlung ist eine Niederschrift zu fertigen, die vom Verwalter und einem Eigentümer zu unterschreiben ist.
    """
}
