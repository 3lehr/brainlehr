// Die native Bedienung des Wissensraums.
//
// Betreiber, 2026-08-14: "die einstellungen bei wissenraum, das geht besser. so
// wie es jetzt ist war es fuer die webversion gebaut, das bitte swift nativ und
// besser durchdacht."
//
// VIER DINGE SIND ANDERS ALS IN DER WEB-LEISTE, und jedes hat einen Grund:
//
// 1. NACH ZWECK GETRENNT, nicht nach Herkunft. "Was sehe ich" steht oben,
//    "wie sieht es aus" liegt zugeklappt darunter. Die Einteilung selbst ist
//    Fachlogik und liegt geprueft in BrainlehrCore/Wissensraumregler.swift.
//
// 2. NUR WAS WIRKT. Ein Regler, der im aktuellen Blick nichts bewirkt, wird
//    nicht ausgegraut, sondern gar nicht gezeigt. Ein ausgegrauter Regler
//    behauptet, es gaebe hier etwas einzustellen, und laesst den Nutzer nach
//    der Bedingung suchen.
//
// 3. DIE WERTE UEBERLEBEN. `@AppStorage` je Regler-Kennung. Die Web-Fassung
//    beginnt bei jedem Laden wieder bei ihren fest verdrahteten Zahlen -- wer
//    sich eine Helligkeit eingestellt hat, stellt sie beim naechsten Mal
//    wieder ein.
//
// 4. ES GIBT EINEN RUECKWEG. "Auf Vorgabe" je Gruppe. Ohne ihn ist eine
//    verstellte Feinjustage eine Sackgasse, aus der nur ein Neustart hilft --
//    und der half hier nicht einmal, seit Punkt 3 gilt.
//
// KEINE ZWEITE ZEICHENLOGIK: geschrieben wird in die Web-Regler, die es schon
// gibt. Siehe Wissensraumregler.skript.

import BrainlehrCore
import SwiftUI

/// Haelt die Werte und schiebt sie in die Seite.
///
/// `senden` wird von aussen gesetzt (die WebView haengt sich ein) -- ohne
/// diese Trennung braeuchte jede Vorschau ein WKWebView.
@MainActor
final class Wissensraumwerte: ObservableObject {
    /// Wird von `WissensraumWebView` gesetzt. Solange nichts eingehaengt ist,
    /// werden Werte gehalten und beim Einhaengen nachgereicht -- sonst gehen
    /// Einstellungen verloren, die vor dem Laden der Seite gemacht wurden.
    var senden: ((String) -> Void)? {
        didSet { if senden != nil { alleNachreichen() } }
    }

    @Published private(set) var werte: [String: Double] = [:]

    private let ablage = UserDefaults.standard
    private func schluessel(_ id: String) -> String { "wissensraum.\(id)" }

    init() {
        for regler in Wissensraumregler.alle {
            let key = schluessel(regler.id)
            let gespeichert = ablage.object(forKey: key) as? Double
            werte[regler.id] = regler.klemme(gespeichert ?? regler.vorgabe)
        }
    }

    func wert(_ regler: Wissensraumregler.Regler) -> Double {
        werte[regler.id] ?? regler.vorgabe
    }

    func setze(_ regler: Wissensraumregler.Regler, auf wert: Double) {
        let geklemmt = regler.klemme(wert)
        werte[regler.id] = geklemmt
        ablage.set(geklemmt, forKey: schluessel(regler.id))
        senden?(Wissensraumregler.skript(fuer: regler, wert: geklemmt))
    }

    /// Setzt eine Gruppe zurueck und schreibt sie sofort in die Seite.
    func aufVorgabe(_ zweck: Wissensraumregler.Zweck, blick: Int) {
        for regler in Wissensraumregler.fuer(blick: blick, zweck: zweck) {
            setze(regler, auf: regler.vorgabe)
        }
    }

    /// Nach dem Laden der Seite: alles einmal hineinschreiben, damit die
    /// gespeicherten Werte auch wirken und nicht nur angezeigt werden.
    func alleNachreichen() {
        for regler in Wissensraumregler.alle {
            senden?(Wissensraumregler.skript(fuer: regler, wert: wert(regler)))
        }
    }
}

/// Ein Schieberegler mit dauerhaft sichtbarem Namen und Wert.
///
/// Der Wert steht daneben, nicht im Namen -- WCAG 2.2: ein Bedienelement
/// braucht einen sichtbaren, dauerhaften Namen, und eine Zahl, die nur beim
/// Ziehen erscheint, ist keiner. `monospacedDigit` verhindert, dass die
/// Beschriftung beim Ziehen springt.
private struct ReglerZeile: View {
    let regler: Wissensraumregler.Regler
    @ObservedObject var werte: Wissensraumwerte

    var body: some View {
        let bindung = Binding<Double>(
            get: { werte.wert(regler) },
            set: { werte.setze(regler, auf: $0) }
        )
        HStack(spacing: 12) {
            Text(regler.name)
                .frame(width: 96, alignment: .leading)
            Slider(value: bindung, in: regler.von...regler.bis, step: regler.schritt)
                .accessibilityLabel(regler.name)
                .accessibilityValue(regler.beschriftung(werte.wert(regler)))
            Text(regler.beschriftung(werte.wert(regler)))
                .monospacedDigit()
                .foregroundStyle(.secondary)
                .frame(width: 64, alignment: .trailing)
        }
    }
}

/// Die Bedienleiste unter dem Wissensraum.
struct WissensraumBedienung: View {
    let blick: WissensraumBlick
    @ObservedObject var werte: Wissensraumwerte
    /// Zugeklappt als Vorgabe -- wer die Feinjustage nie oeffnet, verliert
    /// nichts. Der Zustand bleibt erhalten, weil das Aufklappen sonst bei
    /// jedem Ansichtswechsel zurueckfaellt.
    @AppStorage("wissensraum.darstellungOffen") private var darstellungOffen = false

    private var gegenstand: [Wissensraumregler.Regler] {
        Wissensraumregler.fuer(blick: blick.rawValue, zweck: .gegenstand)
    }
    private var darstellung: [Wissensraumregler.Regler] {
        Wissensraumregler.fuer(blick: blick.rawValue, zweck: .darstellung)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            ForEach(gegenstand) { regler in
                ReglerZeile(regler: regler, werte: werte)
            }

            if !darstellung.isEmpty {
                DisclosureGroup(isExpanded: $darstellungOffen) {
                    VStack(alignment: .leading, spacing: 10) {
                        ForEach(darstellung) { regler in
                            ReglerZeile(regler: regler, werte: werte)
                        }
                        Button("Darstellung auf Vorgabe") {
                            werte.aufVorgabe(.darstellung, blick: blick.rawValue)
                        }
                        .controlSize(.small)
                    }
                    .padding(.top, 8)
                } label: {
                    Text("Darstellung")
                }
            }
        }
        .padding(12)
        .background(.background.secondary)
    }
}
