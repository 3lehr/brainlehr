// Schritt 3 des Plans (docs/PLAN_MACAPP_2026-08-12.md): die drei Ablaeufe aus
// pflege/brainlehr.applescript (anlegenFluss, einladenFluss, "Ausweise
// anzeigen") als SwiftUI-Formulare. "Rollen erklaeren" ist keiner der drei
// verlangten Ablaeufe -- sein Text lebt stattdessen als Accessibility-Hinweis
// an jeder Rollen-Auswahl, wo er tatsaechlich gebraucht wird.

import SwiftUI
import AppKit
import BrainlehrCore

struct AusweisAnsicht: View {
    @State private var eintraege: [AusweisEintrag] = []
    @State private var datei = ""
    @State private var ladeFehler: String?
    @State private var laedt = false
    @State private var zeigeAnlegen = false
    @State private var zeigeEinladen = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Ausweise und Einladungen")
                    .font(.title2)
                    .accessibilityAddTraits(.isHeader)
                Spacer()
                Button("Ausweis anlegen …") { zeigeAnlegen = true }
                    .accessibilityLabel("Ausweis anlegen")
                    .accessibilityHint("Legt einen neuen Ausweis fuer einen Menschen oder ein Programm an.")
                Button("Einladung erzeugen …") { zeigeEinladen = true }
                    .accessibilityLabel("Einladung erzeugen")
                    .accessibilityHint("Erzeugt eine PIN, mit der sich jemand selbst anmelden kann.")
            }
            .padding()

            if let ladeFehler {
                HStack(spacing: 12) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundStyle(.red)
                        .accessibilityHidden(true)
                    Text(ladeFehler)
                        .accessibilityLabel("Hinweis: \(ladeFehler)")
                    Spacer()
                    Button("Erneut versuchen") { Task { await lade() } }
                        .accessibilityLabel("Erneut versuchen")
                }
                .padding()
                .background(.red.opacity(0.12))
            }

            if eintraege.isEmpty && !laedt && ladeFehler == nil {
                Spacer()
                Text("Noch kein Ausweis angelegt.")
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity)
                Spacer()
            } else {
                List(eintraege) { eintrag in
                    HStack {
                        VStack(alignment: .leading) {
                            Text(eintrag.name).font(.headline)
                            Text(eintrag.rollen.joined(separator: ", "))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        Text(eintrag.art == "mensch" ? "Mensch" : "Programm")
                            .foregroundStyle(.secondary)
                    }
                    .accessibilityElement(children: .combine)
                    .accessibilityLabel(
                        "\(eintrag.name), \(eintrag.art == "mensch" ? "Mensch" : "Programm"), Rollen: \(eintrag.rollen.joined(separator: ", "))"
                    )
                }
            }

            if !datei.isEmpty {
                Text("Datei: \(datei)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .padding([.horizontal, .bottom])
            }
        }
        .task { await lade() }
        .sheet(isPresented: $zeigeAnlegen) {
            AusweisAnlegenSheet(onFertig: { Task { await lade() } })
        }
        .sheet(isPresented: $zeigeEinladen) {
            AusweisEinladenSheet(onFertig: { Task { await lade() } })
        }
    }

    private func lade() async {
        laedt = true
        defer { laedt = false }
        do {
            let antwort = try await AusweisDienst.liste()
            eintraege = antwort.ausweise
            datei = antwort.datei
            ladeFehler = nil
        } catch {
            ladeFehler = (error as? AusweisDienstFehler)?.nachricht ?? "Die Ausweisliste konnte nicht geladen werden."
        }
    }
}

/// Mehrfachauswahl der Rollen, mit demselben erklaerenden Text, den
/// pflege/brainlehr.applescript::rollenZeigen() als eigenen Dialog zeigt --
/// hier als Hinweis direkt an der Auswahl, statt als vierter Ablauf.
private struct RollenAuswahl: View {
    @Binding var auswahl: Set<AusweisRolle>

    var body: some View {
        ForEach(AusweisRolle.allCases) { rolle in
            Toggle(isOn: Binding(
                get: { auswahl.contains(rolle) },
                set: { istAn in
                    if istAn { auswahl.insert(rolle) } else { auswahl.remove(rolle) }
                }
            )) {
                Text(rolle.rawValue)
            }
            .accessibilityHint(hinweis(fuer: rolle))
        }
    }

    private func hinweis(fuer rolle: AusweisRolle) -> String {
        switch rolle {
        case .betreiber: return "Alles, auch neue Ausweise ausstellen. Nur fuer dich."
        case .schreiber: return "Wissen und Lehren lesen und schreiben. Die richtige Wahl fuer ein Programm, das mitarbeitet."
        case .fachkundig: return "Darf lesen, aber nur aendern, was es selbst angelegt hat."
        case .leser: return "Darf alles lesen, nichts schreiben."
        case .gast: return "Sieht nur, was ausdruecklich freigegeben ist."
        case .meldeamt: return "Darf Ausweise ausstellen, sonst nichts. Sparsam vergeben."
        }
    }
}

/// Zeigt ein einmaliges Geheimnis (neuer Ausweis oder PIN): selektierbar,
/// bereits in der Zwischenablage, mit einem Knopf, der die Sicherung
/// bestaetigt -- wie die AppleScript-Alerts es tun.
private struct GeheimnisErgebnis: View {
    let titel: String
    let geheimnis: String
    let hinweis: String
    let knopf: String
    let weiter: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(titel)
                .font(.title3)
                .accessibilityAddTraits(.isHeader)
            Text(geheimnis)
                .font(.system(.body, design: .monospaced))
                .textSelection(.enabled)
                .padding(8)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.secondary.opacity(0.12))
                .accessibilityLabel("Geheimnis: \(geheimnis)")
            Text(hinweis)
                .font(.callout)
                .foregroundStyle(.secondary)
            Spacer()
            HStack {
                Spacer()
                Button(knopf, action: weiter)
                    .accessibilityLabel(knopf)
                    .keyboardShortcut(.defaultAction)
            }
        }
        .padding()
        .frame(minWidth: 420, minHeight: 260)
    }
}

private struct AusweisAnlegenSheet: View {
    @Environment(\.dismiss) private var dismiss
    var onFertig: () -> Void

    @State private var name = ""
    @State private var art: AusweisArt = .maschine
    @State private var rollen: Set<AusweisRolle> = [.schreiber]
    @State private var eigenesGeheimnis = ""
    @State private var laeuft = false
    @State private var fehler: String?
    @State private var ergebnis: AusweisAnlegenAntwort?

    var body: some View {
        if let ergebnis {
            GeheimnisErgebnis(
                titel: "Ausweis \u{201E}\(ergebnis.name)\u{201C} ist angelegt",
                geheimnis: ergebnis.geheimnis,
                hinweis: "Das Geheimnis liegt jetzt in der Zwischenablage. Es erscheint NUR DIESES EINE MAL — sichere es in deinem Passwortmanager, bevor du weitermachst.\n\nBeim Programm gehoert es in dessen Konfiguration, nicht in einen Chat.",
                knopf: "Habe ich gesichert"
            ) {
                dismiss()
                onFertig()
            }
        } else {
            VStack(spacing: 0) {
                Form {
                    Section("Ausweis anlegen") {
                        TextField("Name", text: $name, prompt: Text("z. B. laptop-markus oder codex"))
                            .accessibilityLabel("Name des neuen Ausweises")
                        Picker("Wer bekommt den Ausweis?", selection: $art) {
                            ForEach(AusweisArt.allCases, id: \.self) { Text($0.anzeigename).tag($0) }
                        }
                        Text("Nur ein Ausweis fuer einen Menschen zaehlt als menschliche Entscheidung. Ein Geheimnis in der Konfiguration eines Programms gehoert dem Programm, auch wenn es deinen Namen traegt.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    Section("Was soll erlaubt sein? (Mehrfachauswahl)") {
                        RollenAuswahl(auswahl: $rollen)
                    }
                    Section("Dein eigener Ausweis") {
                        SecureField("Dein Geheimnis", text: $eigenesGeheimnis)
                            .accessibilityLabel("Dein eigenes Geheimnis, zum Anlegen noetig")
                    }
                    if let fehler {
                        Text(fehler)
                            .foregroundStyle(.red)
                            .accessibilityLabel("Hinweis: \(fehler)")
                    }
                }
                .formStyle(.grouped)
                HStack {
                    Button("Abbrechen") { dismiss() }
                        .accessibilityLabel("Abbrechen")
                    Spacer()
                    if laeuft { ProgressView().controlSize(.small) }
                    Button("Anlegen") { Task { await anlegen() } }
                        .accessibilityLabel("Anlegen")
                        .keyboardShortcut(.defaultAction)
                        .disabled(!kannAnlegen)
                }
                .padding()
            }
            .frame(minWidth: 460, minHeight: 460)
        }
    }

    private var kannAnlegen: Bool {
        !name.trimmingCharacters(in: .whitespaces).isEmpty && !rollen.isEmpty && !eigenesGeheimnis.isEmpty && !laeuft
    }

    private func anlegen() async {
        laeuft = true
        defer { laeuft = false }
        do {
            let antwort = try await AusweisDienst.anlegen(
                name: name.trimmingCharacters(in: .whitespaces),
                art: art,
                rollen: Array(rollen),
                geheimnis: eigenesGeheimnis
            )
            NSPasteboard.general.clearContents()
            NSPasteboard.general.setString(antwort.geheimnis, forType: .string)
            fehler = nil
            ergebnis = antwort
        } catch {
            fehler = (error as? AusweisDienstFehler)?.nachricht ?? "Das hat nicht geklappt."
        }
    }
}

private struct AusweisEinladenSheet: View {
    @Environment(\.dismiss) private var dismiss
    var onFertig: () -> Void

    @State private var name = "claude-code"
    @State private var fuerWen = "markus"
    @State private var rollen: Set<AusweisRolle> = [.schreiber]
    @State private var eigenesGeheimnis = ""
    @State private var laeuft = false
    @State private var fehler: String?
    @State private var ergebnis: AusweisEinladenAntwort?

    var body: some View {
        if let ergebnis {
            GeheimnisErgebnis(
                titel: "PIN fuer \u{201E}\(ergebnis.name)\u{201C}",
                geheimnis: ergebnis.pin,
                hinweis: "Sie liegt in der Zwischenablage, gilt \(ergebnis.gueltig_minuten) Minuten und funktioniert GENAU EINMAL.\n\nGib sie ueber einen Weg weiter, den du selbst waehlst — Chat, Zuruf, Mail. Genau das ist der Sinn: Die Einloesung beweist, dass ein Mensch sie weitergegeben hat.",
                knopf: "Verstanden"
            ) {
                dismiss()
                onFertig()
            }
        } else {
            VStack(spacing: 0) {
                Form {
                    Section("Einladung erzeugen") {
                        TextField("Name des Gasts", text: $name, prompt: Text("z. B. claude-code oder codex"))
                            .accessibilityLabel("Name, unter dem sich der Gast anmeldet")
                        TextField("Verantwortlich", text: $fuerWen, prompt: Text("dein eigener Ausweisname"))
                            .accessibilityLabel("Wer diese Einladung verantwortet")
                        Text("Bleibt an allem haengen, was der Gast schreibt.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    Section("Was soll erlaubt sein? (Mehrfachauswahl)") {
                        RollenAuswahl(auswahl: $rollen)
                    }
                    Section("Dein eigener Ausweis") {
                        SecureField("Dein Geheimnis", text: $eigenesGeheimnis)
                            .accessibilityLabel("Dein eigenes Geheimnis, zum Einladen noetig")
                    }
                    if let fehler {
                        Text(fehler)
                            .foregroundStyle(.red)
                            .accessibilityLabel("Hinweis: \(fehler)")
                    }
                }
                .formStyle(.grouped)
                HStack {
                    Button("Abbrechen") { dismiss() }
                        .accessibilityLabel("Abbrechen")
                    Spacer()
                    if laeuft { ProgressView().controlSize(.small) }
                    Button("Einladen") { Task { await einladen() } }
                        .accessibilityLabel("Einladen")
                        .keyboardShortcut(.defaultAction)
                        .disabled(!kannEinladen)
                }
                .padding()
            }
            .frame(minWidth: 460, minHeight: 460)
        }
    }

    private var kannEinladen: Bool {
        !name.trimmingCharacters(in: .whitespaces).isEmpty
            && !fuerWen.trimmingCharacters(in: .whitespaces).isEmpty
            && !rollen.isEmpty && !eigenesGeheimnis.isEmpty && !laeuft
    }

    private func einladen() async {
        laeuft = true
        defer { laeuft = false }
        do {
            let antwort = try await AusweisDienst.einladen(
                name: name.trimmingCharacters(in: .whitespaces),
                fuer: fuerWen.trimmingCharacters(in: .whitespaces),
                rollen: Array(rollen),
                geheimnis: eigenesGeheimnis
            )
            NSPasteboard.general.clearContents()
            NSPasteboard.general.setString(antwort.pin, forType: .string)
            fehler = nil
            ergebnis = antwort
        } catch {
            fehler = (error as? AusweisDienstFehler)?.nachricht ?? "Das hat nicht geklappt."
        }
    }
}
