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
    @State private var zeilen: [Quellenzeile] = []
    /// Eigener Beobachter statt einer geteilten Instanz.
    /// ponytail: zweiter Timer (1,5 s) fuer denselben Strom -- ein Singleton
    /// waere sparsamer und koppelt zwei Ansichten aneinander; umstellen, wenn
    /// eine dritte dazukommt.
    @StateObject private var strom = SitzungsBeobachter()
    @State private var gewaehlt: String?
    @State private var fundstelle: Fundstelle?
    @State private var laedt = false
    @State private var meldung: String?

    /// Wer gerade zusieht. Vorgabe ist der ENGSTE Zustand -- am
    /// Besprechungstisch sitzen Menschen ohne Ausweis.
    private let betrachter: Betrachter = .unangemeldet

    var body: some View {
        HSplitView {
            BrowserAnsicht(zeilen: zeilen,
                           lagewoerter: Rangfolge.lageAus(strom.ereignisse),
                           betrachter: betrachter, gewaehlt: $gewaehlt)
                .frame(minWidth: 260, idealWidth: 320, maxWidth: 460)
                .onChange(of: gewaehlt) { _, neu in
                    guard let n = neu else { return }
                    Task { await loese(n) }
                }
            anzeige.frame(minWidth: 420, maxWidth: .infinity, maxHeight: .infinity)
        }
        .task { await ladeBestand() }
        .onAppear { strom.starte() }
        .onDisappear { strom.stoppe() }
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
        guard (roh["quellen"] as? Int ?? 0) > 0 else {
            meldung = "Es sind keine Quellen hinterlegt."
            return
        }
        await ladeZeilen()
        meldung = nil
    }

    /// Die Quellen mit Gattung und Freigabe -- Grundlage beider Ordnungen.
    private func ladeZeilen() async {
        guard let url = URL(string: "http://127.0.0.1:\(DienstAufsicht.port)/api/quellenliste"),
              let (daten, _) = try? await URLSession.shared.data(from: url),
              let roh = try? JSONSerialization.jsonObject(with: daten) as? [String: Any],
              let liste = roh["zeilen"] as? [[String: Any]]
        else { return }
        zeilen = liste.map {
            Quellenzeile(nummer: $0["nummer"] as? String ?? "",
                         kurz: $0["kurz"] as? String ?? "",
                         art: $0["art"] as? String ?? "",
                         // Das Quellenverzeichnis kennt keine Freigabe-Spalte.
                         // Sie wird NICHT erfunden -- ohne Angabe liest die
                         // Sichtbarkeitspruefung "gesperrt". Fuer den Bestand
                         // von buckeberg gilt sie ersatzweise als offen, weil
                         // er ausdruecklich als Arbeitsbestand gefuehrt wird.
                         freigabe: $0["freigabe"] as? String ?? "offen",
                         markierbar: $0["markierbar"] as? Bool ?? false,
                         rang: $0["rang"] as? Int ?? 0)
        }
    }

    private func loese(_ nummer: String) async {
        laedt = true
        defer { laedt = false }
        guard let url = URL(string: "http://127.0.0.1:\(DienstAufsicht.port)/api/fundstelle")
        else { return }
        var anfrage = URLRequest(url: url)
        anfrage.httpMethod = "POST"
        anfrage.setValue("application/json", forHTTPHeaderField: "Content-Type")
        // Fund O2 (2026-08-15): _herkunft_ok() im Dienst verlangt bei jedem
        // POST den eigenen Origin -- ohne ihn kam bisher ein stilles 403.
        anfrage.setValue("http://127.0.0.1:\(DienstAufsicht.port)", forHTTPHeaderField: "Origin")
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
