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
    /// Liegt hier und nicht im App-Rumpf, damit die Steuerschnittstelle sie
    /// erreicht -- sie muss die Ansicht umschalten koennen, und sie lebt so
    /// lange wie die Anwendung, nicht so lange wie ein Fenster.
    let wahl = Ansichtswahl()

    #if DEBUG
    private var steuerung: Steuerschnittstelle?
    #endif

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
        aufsicht.start()
        #if DEBUG
        let s = Steuerschnittstelle(wahl: wahl, aufsicht: aufsicht)
        s.start()
        steuerung = s
        #endif
    }

    /// Der Rueckweg, wenn das letzte Fenster geschlossen wurde.
    ///
    /// GEFUNDEN 2026-08-14 von der Steuerschnittstelle bei ihrem ersten
    /// Einsatz, nicht von einem Auge: Nach einem Neustart lief die Anwendung
    /// mit NULL Fenstern weiter, und `open` holte keines zurueck -- der Nutzer
    /// haette sie abschiessen muessen. Die Anwendung meldete dabei einen
    /// vollkommen gesunden Zustand.
    ///
    /// Das ist dieselbe Fehlerklasse wie die eingeklappte Seitenleiste weiter
    /// oben, nur eine Ebene hoeher: ein Zustand ohne Rueckweg. Die Hausregel
    /// dazu ist dieselbe -- aus jedem dichten Zustand muss ein Weg
    /// hinausfuehren, der ohne dessen eigene Bedienmittel auffindbar ist.
    /// Beim Klick aufs Programmsymbol ist das Symbol dieser Weg.
    /// Setzt der App-Rumpf, sobald die Fenstergruppe existiert. Ohne diesen
    /// Umweg kommt der Delegat nicht an SwiftUIs `openWindow` heran -- und
    /// die AppKit-Wege (`newWindowForTab:`, `newDocument:`) greifen bei einer
    /// WindowGroup nachweislich NICHT: am 2026-08-14 ausprobiert, danach
    /// meldeten Bedienungshilfen-Baum und CGWindowList weiterhin null Fenster.
    var fensterOeffnen: (() -> Void)?

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if !flag { fensterOeffnen?() }
        NSApp.activate(ignoringOtherApps: true)
        return true
    }

    func applicationWillTerminate(_ notification: Notification) {
        #if DEBUG
        steuerung?.stop()
        #endif
        aufsicht.stop()
    }
}

@main
struct BrainlehrApp: App {
    @NSApplicationDelegateAdaptor(BrainlehrAppDelegate.self) private var appDelegate
    @Environment(\.openWindow) private var oeffneFenster

    var body: some Scene {
        // `Window` statt `WindowGroup`, und das ist kein Geschmack:
        //
        // GEMESSEN 2026-08-14 ueber drei unabhaengige Kanaele (Steuerschnittstelle,
        // Bedienungshilfen-Baum, CGWindowList): Mit `WindowGroup` lief die
        // Anwendung nach dem Schliessen des letzten Fensters dauerhaft OHNE
        // Fenster weiter -- weder ein Neustart noch `open` holte eines zurueck.
        // Der Nutzer haette sie abschiessen muessen.
        //
        // Das ist die Hausregel "zwei Ausgangszustaende" an der eigenen App:
        // FRISCH installiert erschien ein Fenster, GEWACHSEN (mit gesicherter
        // Fensterlage "keine Fenster") nie wieder. Geprueft wird fast immer nur
        // der frische Zustand, und der ungepruefte ist der, den der Nutzer hat.
        //
        // `WindowGroup` modelliert mehrere gleichartige Fenster und darf
        // deshalb auf null gehen. Diese Anwendung hat genau ein Hauptfenster --
        // `Window` sagt das, stellt es beim Start wieder her und traegt einen
        // Eintrag im Fenstermenue, der der Rueckweg ist.
        Window("Brainlehr", id: "main") {
            HauptFenster(aufsicht: appDelegate.aufsicht, wahl: appDelegate.wahl)
                .frame(minWidth: 760, minHeight: 480)
                // Der Rueckweg wird hier verdrahtet, nicht im Delegaten:
                // `openWindow` gibt es nur in der SwiftUI-Umgebung.
                .onAppear { appDelegate.fensterOeffnen = { oeffneFenster(id: "main") } }
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
                        appDelegate.wahl.aktuell = e
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
