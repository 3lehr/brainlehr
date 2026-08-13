// Der Quellenbereich: links die Liste, rechts das aufgeschlagene Dokument.
//
// Schritt B1 aus docs/PLAN_OBERFLAECHE_2026-08-13.md, Anschluss an die
// Seitenleiste. Die Liste ist vorerst schlicht -- der thematische Browser mit
// Live-Rangfolge ist B2 und ersetzt sie.
//
// DIE QUELLEN KOMMEN AUS DEM DIENST, nicht aus einem eigenen Leser:
// POST /api/fundstelle loest auf, GET /api/quellenbestand liefert den Nenner.
// Die App BESTELLT -- so steht es im Gesamtplan, und es hat einen Grund:
// dieselbe Aufloesung ohne gebaute App pruefbar zu halten
// (python3 kern/fundstelle.py --quelle 14).

import BrainlehrCore
import SwiftUI

struct QuellenBereich: View {
    @State private var nummern: [String] = []
    @State private var gewaehlt: String?
    @State private var fundstelle: Fundstelle?
    @State private var laedt = false
    @State private var meldung: String?

    /// Wer gerade zusieht. Vorgabe ist der ENGSTE Zustand -- am
    /// Besprechungstisch sitzen Menschen ohne Ausweis.
    private let betrachter: Betrachter = .unangemeldet

    var body: some View {
        HSplitView {
            liste.frame(minWidth: 220, idealWidth: 260, maxWidth: 380)
            anzeige.frame(minWidth: 420, maxWidth: .infinity, maxHeight: .infinity)
        }
        .task { await ladeBestand() }
    }

    private var liste: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Quellen").font(.headline).accessibilityAddTraits(.isHeader)
                Spacer()
                if !nummern.isEmpty {
                    Text("\(nummern.count)")
                        .font(.caption).foregroundStyle(.secondary)
                        .accessibilityLabel("\(nummern.count) Quellen")
                }
            }
            .padding(.horizontal).padding(.vertical, 8)

            if let m = meldung {
                // Nutzersprache, keine Entwicklerinformation: kein Port, kein
                // Pfad, kein Fehlertext des Dienstes.
                Text(m).font(.callout).foregroundStyle(.secondary)
                    .padding(.horizontal).padding(.bottom, 8)
            }

            List(nummern, id: \.self, selection: $gewaehlt) { nr in
                Text("Quelle \(nr)").tag(nr)
                    .accessibilityLabel("Quelle \(nr)")
            }
            .onChange(of: gewaehlt) { _, neu in
                guard let n = neu else { return }
                Task { await loese(n) }
            }
        }
    }

    @ViewBuilder private var anzeige: some View {
        if laedt {
            VStack { Spacer(); ProgressView("Quelle wird geöffnet …"); Spacer() }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if let f = fundstelle {
            QuellenAnsicht(fundstelle: f, betrachter: betrachter)
        } else {
            VStack(spacing: 8) {
                Spacer()
                Text("Wählen Sie links eine Quelle.")
                    .font(.title3).foregroundStyle(.secondary)
                Spacer()
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    // MARK: - Dienst

    private func ladeBestand() async {
        guard let url = URL(string: "http://127.0.0.1:\(DienstAufsicht.port)/api/quellenbestand"),
              let (daten, _) = try? await URLSession.shared.data(from: url),
              let roh = try? JSONSerialization.jsonObject(with: daten) as? [String: Any]
        else {
            meldung = "Die Quellenliste ist gerade nicht verfügbar."
            return
        }
        let anzahl = roh["quellen"] as? Int ?? 0
        guard anzahl > 0 else {
            meldung = "Es sind keine Quellen hinterlegt."
            return
        }
        nummern = (1...anzahl).map(String.init)
        meldung = nil
    }

    private func loese(_ nummer: String) async {
        laedt = true
        defer { laedt = false }
        guard let url = URL(string: "http://127.0.0.1:\(DienstAufsicht.port)/api/fundstelle")
        else { return }
        var anfrage = URLRequest(url: url)
        anfrage.httpMethod = "POST"
        anfrage.setValue("application/json", forHTTPHeaderField: "Content-Type")
        anfrage.httpBody = try? JSONSerialization.data(withJSONObject: ["quelle": nummer])

        guard let (daten, _) = try? await URLSession.shared.data(for: anfrage),
              let f = try? JSONDecoder().decode(Fundstelle.self, from: daten)
        else {
            meldung = "Diese Quelle lässt sich gerade nicht öffnen."
            fundstelle = nil
            return
        }
        // Was der Betrachter nicht sehen darf, wird gar nicht erst angezeigt --
        // und die Meldung ist DIESELBE wie fuer "gibt es nicht". Sonst laesst
        // sich aus dem Unterschied schliessen, dass es etwas gibt.
        guard Sichtbarkeit.darfSehen(rohFreigabe: "offen", betrachter) else {
            meldung = Sichtbarkeit.nichtVorhanden
            fundstelle = nil
            return
        }
        meldung = nil
        fundstelle = f
    }
}
