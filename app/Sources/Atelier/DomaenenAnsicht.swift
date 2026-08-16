import SwiftUI
import BrainlehrCore

/// Zeichnet einen Bildschirm, den eine Domaene BESCHRIEBEN hat -- mit den
/// Bausteinen des atelier, nicht mit ihren.
///
/// ADR-024: V1 ist nativ. Die Domaene sagt WAS (Titel, Spalten, Rollen,
/// Leerfall), diese Ansicht entscheidet WIE (Ausrichtung, Schrift, Abstaende).
/// Deshalb steht hier kein einziger Wert, den das Manifest vorgibt: keine
/// Breite, keine Farbe, keine Schriftgroesse. Genau das haelt die Zusage, dass
/// ein zweiter Zeichner (Web) spaeter ein Schritt bleibt und kein zweiter Bau.
///
/// Die Uebersetzung selbst liegt in BrainlehrCore.DomaenenBildschirm und ist
/// dort ohne Mock geprueft (9 Tests, Mutationsprobe gefahren). Hier steht nur
/// das Zeichnen -- bewusst duenn, damit wenig Ungeprueftes uebrig bleibt.
struct DomaenenAnsicht: View {
    let bildschirm: DomaenenBildschirm
    /// Die Zeilen kommen vom Dienst der Domaene. Leer ist ein normaler
    /// Zustand, kein Fehler.
    let zeilen: [[String: Any]]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(bildschirm.titel)
                .font(.title2)
                .accessibilityAddTraits(.isHeader)

            if let erklaerung = bildschirm.erklaerung {
                Text(erklaerung)
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            if zeilen.isEmpty {
                // Nie eine leere Flaeche: der Satz kommt aus der Beschreibung,
                // ersatzweise aus der Vorgabe. Ein Mensch soll wissen, ob hier
                // nichts IST oder nichts GELADEN wurde.
                Text(bildschirm.leerfall)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .padding(.vertical, 24)
            } else {
                tabelle
            }
            Spacer()
        }
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var tabelle: some View {
        Grid(alignment: .leading, horizontalSpacing: 16, verticalSpacing: 6) {
            GridRow {
                ForEach(bildschirm.spalten, id: \.name) { spalte in
                    Text(spalte.titel)
                        .font(.headline)
                        .gridColumnAlignment(ausrichtung(spalte.art))
                }
            }
            Divider()
            ForEach(Array(zeilen.enumerated()), id: \.offset) { _, daten in
                GridRow {
                    ForEach(Array(bildschirm.zeile(aus: daten).enumerated()), id: \.offset) { i, text in
                        zelle(text, art: bildschirm.spalten[i].art)
                    }
                }
            }
        }
    }

    /// Die Rolle entscheidet die Darstellung -- hier, nicht in der Domaene.
    @ViewBuilder
    private func zelle(_ text: String, art: DomaenenBildschirm.Spaltenart) -> some View {
        switch art {
        case .betrag:
            Text(text).monospacedDigit()
        case .zitat:
            // Ein Zitat wird als solches kenntlich, weil es der BELEG ist --
            // die Fundstelle, die woertlich im amtlichen Text steht. Nicht
            // ueber Farbe allein (WCAG 1.4.1), sondern ueber Anfuehrungszeichen.
            Text("\u{201E}\(text)\u{201C}").italic()
        case .text:
            Text(text)
        }
    }

    private func ausrichtung(_ art: DomaenenBildschirm.Spaltenart) -> HorizontalAlignment {
        art == .betrag ? .trailing : .leading
    }
}
