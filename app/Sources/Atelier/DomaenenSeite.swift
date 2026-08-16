import SwiftUI
import BrainlehrCore

/// Holt die Bildschirm-BESCHREIBUNG einer Domaene aus ihrem Manifest und gibt
/// sie an den Zeichner (`DomaenenAnsicht`).
///
/// WARUM DIESE DATEI UEBERHAUPT EXISTIERT: `DomaenenAnsicht` war nach dem Bau
/// von KEINER Stelle aufgerufen -- gebaut, uebersetzbar, getestet und
/// wirkungslos. Genau die Fehlerklasse, die brainlehr an anderen verfolgt und
/// die hier am eigenen Code passiert ist. Diese Datei ist der Aufruf.
///
/// WAS SIE NOCH NICHT KANN, ausdruecklich: Sie sucht das Manifest an den
/// Orten, an denen ein importiertes Domaenen-Repo liegen KANN, und faellt
/// sonst auf einen erklaerten Leerzustand zurueck. Der richtige Weg ist der
/// Import (`DomaeneImportDienst`), der das Manifest in den Bestand legt --
/// solange der nicht damit verbunden ist, ist dies eine Bruecke und wird als
/// solche benannt, nicht als Loesung ausgegeben.
struct DomaenenSeite: View {
    /// Ohne festen Pfad (ADR-023 §3): Umgebung zuerst, dann Nachbarschaft.
    private static func manifestPfad() -> URL? {
        let fm = FileManager.default
        if let ort = ProcessInfo.processInfo.environment["DOMAENE_MANIFEST"] {
            let u = URL(fileURLWithPath: ort)
            if fm.fileExists(atPath: u.path) { return u }
        }
        guard let wurzel = DienstAufsicht.findeRepoWurzel(zusatzStart: URL(fileURLWithPath: fm.currentDirectoryPath))
        else { return nil }
        let kandidat = wurzel
            .deletingLastPathComponent()
            .appendingPathComponent("openlehr_einzelunternehmer/wissen/einzelunternehmer.domaene.json")
        return fm.fileExists(atPath: kandidat.path) ? kandidat : nil
    }

    private var bildschirm: DomaenenBildschirm? {
        guard let pfad = Self.manifestPfad(),
              let daten = try? Data(contentsOf: pfad),
              let paket = try? JSONSerialization.jsonObject(with: daten) as? [String: Any],
              let oberflaeche = paket["oberflaeche"] as? [String: Any],
              let bildschirme = oberflaeche["bildschirme"] as? [[String: Any]],
              let erster = bildschirme.first
        else { return nil }
        return DomaenenBildschirm(beschreibung: erster)
    }

    var body: some View {
        if let bildschirm {
            // Zeilen kommen spaeter vom Dienst der Domaene. Bis dahin greift
            // der Leerfall aus der Beschreibung -- ein Satz, kein leeres Feld.
            DomaenenAnsicht(bildschirm: bildschirm, zeilen: [])
        } else {
            VStack(spacing: 8) {
                Spacer()
                Text("Für diese Anwendung ist noch keine Ansicht eingerichtet.")
                    .foregroundStyle(.secondary)
                Text("Sie erscheint hier, sobald die Anwendung eingebunden ist.")
                    .font(.callout).foregroundStyle(.secondary)
                Spacer()
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }
}
