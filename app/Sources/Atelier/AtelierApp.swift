// Einstiegspunkt. Nach Vorbild openlehr/.../OpenLehrApp.swift, aber ohne
// MenuBarExtra und ohne KeyboardShortcuts-Fremdpaket.

import AppKit
import BrainlehrCore
import SwiftUI
import UniformTypeIdentifiers

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
    /// Der Blick INNERHALB des Wissensraums. Liegt hier statt als @State im
    /// Fenster, damit die Steuerschnittstelle ihn erreicht -- ohne diesen Griff
    /// laesst sich programmatisch nicht pruefen, dass die Regler je Blick
    /// verschieden sind, und genau das ist ihre Fachlogik.
    @Published var blick: WissensraumBlick = .baum
    /// I1 (ADR-014): welche Bestandteile die zuletzt angenommene Domaene
    /// angefordert UND gewaehrt bekommen hat. Leer bei frischer Installation
    /// (zwei Ausgangszustaende, Hausregel) -- ohne importierte Domaene laedt
    /// keiner. UserDefaults statt eigener Datei: ueberlebt einen Neustart,
    /// braucht kein Entitlement, ist eingebautes Systemmittel.
    @Published private(set) var bestandteile: Set<Bestandteil>

    private static let bestandteileSchluessel = "gewaehrteBestandteile"

    init() {
        let namen = UserDefaults.standard.stringArray(forKey: Self.bestandteileSchluessel) ?? []
        bestandteile = Set(namen.compactMap(Bestandteil.init(rawValue:)))
    }

    /// Ersetzt die Menge -- eine neu importierte Domaene erklaert, was SIE
    /// braucht, sie ergaenzt keine Reste einer frueheren.
    func setzeBestandteile(_ neu: Set<Bestandteil>) {
        bestandteile = neu
        UserDefaults.standard.set(neu.map(\.rawValue), forKey: Self.bestandteileSchluessel)
    }
}

@MainActor
final class AtelierAppDelegate: NSObject, NSApplicationDelegate {
    let aufsicht = DienstAufsicht()
    /// Liegt hier und nicht im App-Rumpf, damit die Steuerschnittstelle sie
    /// erreicht -- sie muss die Ansicht umschalten koennen, und sie lebt so
    /// lange wie die Anwendung, nicht so lange wie ein Fenster.
    let wahl = Ansichtswahl()
    /// Liegt hier statt in der Ansicht, damit die Steuerschnittstelle sie
    /// erreicht -- ohne diesen Griff laesst sich die Abnahme des
    /// Dokumentfensters nur von Hand fahren.
    let dokument = Dokumentsitzung()

    #if DEBUG
    private var steuerung: Steuerschnittstelle?
    #endif

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
        aufsicht.start()
        #if DEBUG
        let s = Steuerschnittstelle(wahl: wahl, aufsicht: aufsicht, dokument: dokument)
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
struct AtelierApp: App {
    @NSApplicationDelegateAdaptor(AtelierAppDelegate.self) private var appDelegate
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
            HauptFenster(dokument: appDelegate.dokument, aufsicht: appDelegate.aufsicht, wahl: appDelegate.wahl)
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
                // I1: dieselbe Filterung wie in der Seitenleiste
                // (HauptFenster.swift) -- sonst waere die Menueleiste ein
                // zweiter, ungeprueften Weg zu einem nicht angeforderten
                // Bestandteil.
                ForEach(Array(sichtbareEintraege.enumerated()), id: \.element) { nr, e in
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
            // H8b (docs/PLAN_OPENLEHR_2026-08-14.md): eigener Menuepunkt statt
            // versteckt im Toolbar-Block -- "Importieren" ist der Systemplatz
            // dafuer (CommandGroupPlacement.importExport, landet im
            // Ablage-Menue). Rueckweg ist der OK-Knopf des Ergebnisdialogs,
            // nicht dieser Menuepunkt selbst.
            CommandGroup(after: .importExport) {
                Button("Domäne importieren …") { domaeneImportieren() }
                    .keyboardShortcut("i", modifiers: [.command, .shift])
            }
        }

        Settings {
            EinstellungenAnsicht()
                .frame(minWidth: 460, minHeight: 300)
        }
    }

    /// I1: Kern-Eintraege immer, Bestandteil-Eintraege (aktuell nur
    /// "Dokument") nur wenn die aktive Domaene sie angefordert bekam.
    private var sichtbareEintraege: [SeitenleistenEintrag] {
        SeitenleistenEintrag.allCases.filter {
            $0.bestandteil == nil || appDelegate.wahl.bestandteile.contains($0.bestandteil!)
        }
    }

    /// Dateiauswahl (nur die Paketdatei) + Ergebnis in Nutzersprache. Ergebnis
    /// kommt als NSAlert -- der einzig zumutbare Weg fuer eine Rueckmeldung
    /// aus einem Menuebefehl heraus, der zu keiner View gehoert. Der
    /// OK-Knopf des Alerts ist der Rueckweg aus dem Zustand.
    @MainActor
    private func domaeneImportieren() {
        let panel = NSOpenPanel()
        panel.title = "Domäne importieren"
        panel.prompt = "Importieren"
        panel.allowedContentTypes = [.json]
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        panel.canChooseFiles = true
        guard panel.runModal() == .OK, let url = panel.url else { return }
        // NACHTRAG 2026-08-15: der Import schreibt jetzt tatsaechlich in den
        // Bestand (siehe DomaeneImportDienst.swift) und braucht darum einen
        // Ausweis, wie /api/ausweis-anlegen ihn schon abfragt (AusweisAnsicht.swift,
        // "Dein Geheimnis" per SecureField) -- hier als NSAlert, weil dieser
        // Befehl zu keinem Fenster/View gehoert. Nichts wird gespeichert:
        // das Geheimnis lebt nur fuer diesen einen Aufruf im Arbeitsspeicher.
        guard let geheimnis = Self.ausweisAbfragen() else { return }
        Task {
            let (ergebnis, bestandteile) = await DomaeneImportDienst.importiere(dateiURL: url, geheimnis: geheimnis)
            // nil == Wirkung Null: eine abgelehnte oder unlesbare Datei
            // aendert nichts an einer bereits geltenden Anforderung.
            if let bestandteile { appDelegate.wahl.setzeBestandteile(bestandteile) }
            let alert = NSAlert()
            alert.messageText = ergebnis.titel
            alert.informativeText = ergebnis.text
            alert.addButton(withTitle: "OK")
            alert.runModal()
        }
    }

    /// `nil` heisst: Nutzer hat abgebrochen oder nichts eingegeben -- dann
    /// unterbleibt der ganze Aufruf, ohne eine weitere Meldung (Abbrechen
    /// braucht keine Erklaerung).
    @MainActor
    private static func ausweisAbfragen() -> String? {
        let alert = NSAlert()
        alert.messageText = "Ausweis für den Import"
        alert.informativeText = "Der Import schreibt in den Bestand und braucht deinen Ausweis."
        alert.addButton(withTitle: "Importieren")
        alert.addButton(withTitle: "Abbrechen")
        let feld = NSSecureTextField(frame: NSRect(x: 0, y: 0, width: 260, height: 24))
        feld.setAccessibilityLabel("Dein Ausweis-Geheimnis")
        alert.accessoryView = feld
        alert.window.initialFirstResponder = feld
        guard alert.runModal() == .alertFirstButtonReturn else { return nil }
        let wert = feld.stringValue.trimmingCharacters(in: .whitespaces)
        return wert.isEmpty ? nil : wert
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
