import SwiftUI
import BrainlehrCore

/// Holt die Bildschirm-BESCHREIBUNG einer importierten Domäne beim Dienst und
/// gibt sie an den Zeichner (`DomaenenAnsicht`).
///
/// WAS SICH HIER GEÄNDERT HAT, und warum es der eigentliche Schritt war: Die
/// erste Fassung suchte die Manifest-DATEI im Dateisystem -- über eine
/// Umgebungsvariable, ersatzweise in der Nachbarschaft der Repo-Wurzel. Das war
/// ausdrücklich als Brücke benannt und trotzdem falsch: Ein Fremder, der die
/// Domäne nach ADR-012 als Paket bekommt (das Wissenspaket reist frei, das
/// Werkzeug wird installiert), hat diese Datei nie. Er hätte das Wissen gehabt
/// und keinen Bildschirm.
///
/// Jetzt ist die Beschreibung Teil dessen, was beim Import in den Bestand
/// wandert (`kern/domaene.py::speichere`), und wird von dort gelesen. Damit
/// hängt der Bildschirm am IMPORT, nicht am Dateisystem des Betreibers.
///
/// DREI LAGEN, die der Mensch unterscheiden können muss -- deshalb drei Sätze
/// statt einer leeren Fläche:
///   nicht importiert       die Domäne ist hier nicht eingebunden
///   ohne Bildschirm        eingebunden, bringt aber nur Wissen mit (ADR-013)
///   Dienst antwortet nicht der Wissensraum läuft nicht
struct DomaenenSeite: View {
    /// Vorerst eine Domäne. Die Stelle, an der die Aufsicht über *n* aufgeht,
    /// ist dieselbe wie in `DienstAufsicht` -- benannt, nicht versteckt.
    static let domaene = "einzelunternehmer"

    @State private var lage: Lage = .laedt

    enum Lage {
        case laedt
        case bildschirm(DomaenenBildschirm)
        case ohneBildschirm
        case nichtImportiert
        case dienstAntwortetNicht
    }

    var body: some View {
        inhalt
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .task { await hole() }
    }

    @ViewBuilder
    private var inhalt: some View {
        switch lage {
        case .laedt:
            ProgressView()
        case .bildschirm(let b):
            // Zeilen kommen, sobald der Fachdienst der Domäne läuft. Bis dahin
            // greift der Leerfall aus der Beschreibung -- ein Satz, kein leeres
            // Feld.
            DomaenenAnsicht(bildschirm: b, zeilen: [])
        case .ohneBildschirm:
            satz("Diese Anwendung bringt kein eigenes Fenster mit.",
                 "Ihr Wissen steht trotzdem zur Verfügung.")
        case .nichtImportiert:
            satz("Diese Anwendung ist hier nicht eingebunden.",
                 "Über „Domäne importieren…\u{201C} lässt sie sich hinzufügen.")
        case .dienstAntwortetNicht:
            satz("Der Wissensraum ist gerade nicht erreichbar.",
                 "Sobald er läuft, erscheint diese Ansicht von selbst.")
        }
    }

    private func satz(_ oben: String, _ unten: String) -> some View {
        VStack(spacing: 6) {
            Spacer()
            Text(oben).foregroundStyle(.secondary)
            Text(unten).font(.callout).foregroundStyle(.secondary)
            Spacer()
        }
        .multilineTextAlignment(.center)
        .padding(.horizontal, 32)
    }

    private func hole() async {
        guard let url = URL(string:
                "http://127.0.0.1:\(DienstAufsicht.port)/api/domaene-oberflaeche?domaene=\(Self.domaene)")
        else {
            lage = .dienstAntwortetNicht
            return
        }
        guard let (daten, _) = try? await URLSession.shared.data(from: url),
              let roh = try? JSONSerialization.jsonObject(with: daten) as? [String: Any]
        else {
            lage = .dienstAntwortetNicht
            return
        }
        guard (roh["importiert"] as? Bool) == true else {
            lage = .nichtImportiert
            return
        }
        guard let bildschirme = roh["bildschirme"] as? [[String: Any]],
              let erster = bildschirme.first,
              let b = DomaenenBildschirm(beschreibung: erster)
        else {
            lage = .ohneBildschirm
            return
        }
        lage = .bildschirm(b)
    }
}
