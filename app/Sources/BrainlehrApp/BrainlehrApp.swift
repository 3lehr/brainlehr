// Einstiegspunkt. Nach Vorbild openlehr/.../OpenLehrApp.swift, aber ohne
// MenuBarExtra und ohne KeyboardShortcuts-Fremdpaket -- Schritt 1 des Plans
// braucht nur ein Fenster mit Seitenleiste und Dienstaufsicht.

import SwiftUI
import AppKit

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

    var body: some Scene {
        WindowGroup("Brainlehr", id: "main") {
            HauptFenster(aufsicht: appDelegate.aufsicht)
                .frame(minWidth: 760, minHeight: 480)
        }
        .defaultSize(width: 880, height: 600)
        // Groesse und Lage ueberleben einen Neustart bereits von selbst:
        // WindowGroup sichert die Fensterlage unter der Kennung "main"
        // automatisch (AppKit-Bordmittel, geprueft per Verschieben+Neustart --
        // Schluessel "NSWindow Frame main-AppWindow-1" in
        // ~/Library/Preferences/de.brainlehr.app.plist). Kein eigener Code noetig.

        Settings {
            EinstellungenAnsicht()
                .frame(minWidth: 420, minHeight: 240)
        }
    }
}

/// Platzhalter -- Schritt 5 des Plans fuellt die acht Abschnitte aus der
/// heutigen HTML-Seite. Hier zaehlt nur, dass Befehlstaste-Komma ein Fenster
/// oeffnet, wie es ein Mac-Programm tut.
private struct EinstellungenAnsicht: View {
    var body: some View {
        VStack(spacing: 8) {
            Text("Einstellungen")
                .font(.title2)
                .accessibilityAddTraits(.isHeader)
            Text("Diese Ansicht wird als Naechstes gebaut.")
                .foregroundStyle(.secondary)
        }
        .padding(32)
    }
}
