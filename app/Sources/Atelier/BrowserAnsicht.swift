// Der Dateibrowser -- thematisch oder nach dem, was gerade zaehlt.
//
// Schritt B2 aus docs/PLAN_OBERFLAECHE_2026-08-13.md. Betreiberauftrag:
// "nicht einfach so wie im dateisystem abgelegt, sondern einmal thematisch
// sortiert und zum umschalten live ranking durch die ki was gerade am
// wichtigsten ist!"
//
// WARUM NICHT DER VERZEICHNISBAUM: Er ordnet nach dem Ort, an dem eine Datei
// zufaellig liegt. Am Besprechungstisch braucht niemand den Ort -- gesucht
// wird die Gattung ("was sagt das Gesetz dazu") oder der Bezug zur laufenden
// Frage. Beides steht im Quellenverzeichnis bzw. im Sitzungsstrom.
//
// JEDER PLATZ TRAEGT SEINE BEGRUENDUNG. Eine Rangfolge, die niemand erklaeren
// kann, ist am Tisch wertlos: Wer fragt "warum steht das oben", bekommt eine
// Antwort statt eines Achselzuckens.

import BrainlehrCore
import SwiftUI

struct BrowserAnsicht: View {
    /// Die Quellen kommen von aussen -- diese Ansicht laedt nicht selbst.
    let zeilen: [Quellenzeile]
    /// Woran gerade gearbeitet wird, aus dem Sitzungsstrom.
    let lagewoerter: Set<String>
    let betrachter: Betrachter
    @Binding var gewaehlt: String?

    @State private var ordnung: Ordnung = .thematisch
    @State private var suche: String = ""

    private var liste: [Rangplatz] {
        let alle = Rangfolge.liste(zeilen, ordnung: ordnung, betrachter: betrachter,
                                   lagewoerter: lagewoerter)
        let wort = suche.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard !wort.isEmpty else { return alle }
        return alle.filter {
            $0.zeile.kurz.lowercased().contains(wort) || $0.zeile.nummer == wort
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            kopf
            Divider()
            if liste.isEmpty {
                // DERSELBE Satz wie fuer "gibt es nicht". Sonst laesst sich aus
                // dem Unterschied schliessen, dass es etwas gibt, das man nicht
                // sehen darf -- und bei Namen Dritter ist schon das eine Aussage.
                VStack {
                    Spacer()
                    Text(Sichtbarkeit.nichtVorhanden)
                        .font(.callout).foregroundStyle(.secondary)
                        .multilineTextAlignment(.center).padding()
                    Spacer()
                }
                .frame(maxWidth: .infinity)
            } else {
                List(liste, id: \.zeile.nummer, selection: $gewaehlt) { platz in
                    Zeile(platz: platz, ordnung: ordnung).tag(platz.zeile.nummer)
                }
                .listStyle(.inset)
            }
        }
    }

    private var kopf: some View {
        VStack(alignment: .leading, spacing: 8) {
            Picker("Ordnung", selection: $ordnung) {
                ForEach(Ordnung.allCases, id: \.self) { Text($0.titel).tag($0) }
            }
            .pickerStyle(.segmented)
            .accessibilityLabel("Reihenfolge der Quellen")

            HStack(spacing: 6) {
                Image(systemName: "magnifyingglass").accessibilityHidden(true)
                TextField("Quelle suchen", text: $suche)
                    .textFieldStyle(.roundedBorder)
                    .accessibilityLabel("Quelle suchen")
            }

            if ordnung == .nachLage && lagewoerter.isEmpty {
                // Ehrlich statt still: Ohne Bezug wird nicht gewichtet, und
                // das steht da, statt eine erfundene Reihenfolge zu zeigen.
                Text("Noch kein Bezug zur laufenden Arbeit — die Reihenfolge bleibt thematisch.")
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
        .padding(.horizontal).padding(.vertical, 8)
    }
}

private struct Zeile: View {
    let platz: Rangplatz
    let ordnung: Ordnung

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack(spacing: 6) {
                Text(platz.zeile.nummer)
                    .font(.caption).monospacedDigit()
                    .foregroundStyle(.secondary)
                    .frame(minWidth: 22, alignment: .trailing)
                // Ein Zeichen, kein Farbpunkt: Bedeutung nie allein ueber Farbe.
                Image(systemName: platz.zeile.markierbar ? "text.viewfinder" : "doc")
                    .accessibilityHidden(true)
                Text(platz.zeile.kurz)
                    .lineLimit(2)
            }
            if !platz.begruendung.isEmpty {
                Text(platz.begruendung)
                    .font(.caption2).foregroundStyle(.secondary)
                    .padding(.leading, 28)
            }
        }
        .padding(.vertical, 2)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Quelle \(platz.zeile.nummer), \(platz.zeile.kurz)")
        .accessibilityValue(platz.zeile.markierbar
                            ? "Stelle bekannt. \(platz.begruendung)"
                            : "Keine Stelle hinterlegt. \(platz.begruendung)")
    }
}
