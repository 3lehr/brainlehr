// Einstiegspunkt. Nach Vorbild openlehr/.../OpenLehrApp.swift, aber ohne
// MenuBarExtra und ohne KeyboardShortcuts-Fremdpaket.

import AppKit
import SwiftUI

/// Welche Ansicht gerade gezeigt wird -- getrennt vom Fenster gehalten, weil
/// die MENUELEISTE sie umschalten koennen muss.
///
/// ANLASS (Betreiber, 2026-08-13): "zudem bin ich nun im dokumenten fenster
/// und seh die haupt menue liste nicht mehr! wir brauchen das mindestens die
/// auswahl unter fenster ganz oben in der betriebsystemleiste"
///
/// Er sass fest. Die Seitenleiste laesst sich einklappen, und danach fuehrte
/// der einzige Weg zurueck ueber ihren eigenen Knopf -- also ueber genau das
/// Bedienmittel, das gerade verschwunden war. Die Hausregel dazu ist
/// eindeutig: aus einem dichten Modus muss ein Rueckweg fuehren, der OHNE
/// dessen eigene Bedienmittel auffindbar ist. Die Menueleiste des Systems ist
/// dieser Rueckweg -- sie ist immer da, auch im Vollbild.
@MainActor
final class Ansichtswahl: ObservableObject {
    @Published var aktuell: SeitenleistenEintrag = .quellen
}

@MainActor
final class BrainlehrAppDelegate: NSObject, NSApplicationDelegate {
    let aufsicht = DienstAufsicht()

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
        aufsicht.start()
    }

    func applicationWillTerminate(_ notification: Notification) {
        aufsicht.stop()
    }
}

@main
struct BrainlehrApp: App {
    @NSApplicationDelegateAdaptor(BrainlehrAppDelegate.self) private var appDelegate
    @StateObject private var wahl = Ansichtswahl()

    var body: some Scene {
        WindowGroup("Brainlehr", id: "main") {
            HauptFenster(aufsicht: appDelegate.aufsicht, wahl: wahl)
                .frame(minWidth: 760, minHeight: 480)
        }
        .defaultSize(width: 880, height: 600)
        // Groesse und Lage ueberleben einen Neustart bereits von selbst:
        // WindowGroup sichert die Fensterlage unter der Kennung "main"
        // automatisch (AppKit-Bordmittel, geprueft per Verschieben+Neustart --
        // Schluessel "NSWindow Frame main-AppWindow-1" in
        // ~/Library/Preferences/de.brainlehr.app.plist). Kein eigener Code noetig.
        .commands {
            // Unter "Darstellung", weil es die Ansicht wechselt -- und
            // zusaetzlich mit Zifferntasten, damit der Wechsel auch ohne Maus
            // geht. Beides zusammen ist der Rueckweg aus jedem Zustand.
            CommandGroup(before: .toolbar) {
                ForEach(Array(SeitenleistenEintrag.allCases.enumerated()), id: \.element) { nr, e in
                    Button {
                        wahl.aktuell = e
                    } label: {
                        Label(e.titel, systemImage: e.symbol)
                    }
                    .keyboardShortcut(KeyEquivalent(Character("\(nr + 1)")), modifiers: .command)
                }
                Divider()
                Button("Seitenleiste ein- oder ausblenden") {
                    NSApp.keyWindow?.firstResponder?.tryToPerform(
                        #selector(NSSplitViewController.toggleSidebar(_:)), with: nil)
                }
                .keyboardShortcut("s", modifiers: [.command, .control])
                Divider()
            }
        }

        Settings {
            EinstellungenAnsicht()
                .frame(minWidth: 460, minHeight: 300)
        }
    }
}

/// Was sich einstellen laesst -- und was ausdruecklich nicht.
///
/// Der Vorgaenger stand hier als "Diese Ansicht wird als Naechstes gebaut."
/// Das ist Entwicklerinformation im sichtbaren Text und sagt dem Nutzer
/// nichts ueber seine Lage. Jetzt steht da, was tatsaechlich gilt.
private struct EinstellungenAnsicht: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Einstellungen")
                .font(.title2).accessibilityAddTraits(.isHeader)

            VStack(alignment: .leading, spacing: 6) {
                Text("Betrachtungsabstand").font(.headline)
                Text("Der Abstand wird dort eingestellt, wo er wirkt — "
                     + "unten in der Quellenansicht. Er entscheidet, ob ein "
                     + "Dokument ganz, als Ausschnitt oder mehrfach nebeneinander "
                     + "gezeigt wird.")
                    .font(.callout).foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            VStack(alignment: .leading, spacing: 6) {
                Text("Sitzung").font(.headline)
                Text("Welcher Chat beobachtet wird, wählen Sie oben in der "
                     + "Sitzungsansicht — dort sehen Sie zugleich, wann er "
                     + "zuletzt aktiv war.")
                    .font(.callout).foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer()
        }
        .padding(24)
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
