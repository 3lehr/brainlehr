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
        }
        .defaultSize(width: 880, height: 600)
        .commands {
            CommandGroup(replacing: .newItem) {}
        }
    }
}
