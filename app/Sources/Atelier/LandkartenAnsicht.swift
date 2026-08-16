// Die Landkarten des brainlehr-Universums -- Verbund, Aufbau der Anwendung,
// Code-Struktur je Repo, Wissensbestand.
//
// EIGENE SICHT, kein Blick des Wissensraums. Betreiberentscheidung vom
// 2026-08-16, woertlich: "es gehoert nicht unter wissensraum! [...] es steht
// ja eine stufe darueber, ist info ueber die app, das gesamte brainlehr
// universum und nicht ueber den wissensraum der datenbank!" Ein sechster
// Blick neben "Baum" und "Bedeutung" behauptete eine Gleichrangigkeit, die es
// nicht gibt -- und schleppte nebenbei die Zeichenflaeche des Wissensraums
// mit, die die Karte aus dem sichtbaren Bereich schob.
//
// Warum eine eigene Seite (/landkarten) statt eines Blocks in
// entscheidungen.html: die beiden teilen keine Bedienung, keine Regler und
// keine Zeichenflaeche. Ein gemeinsames Dokument haette sie aneinander
// gekettet.

import BrainlehrCore
import SwiftUI
@preconcurrency import WebKit

/// Traegt denselben Wechsel wie die Wissensraum-Ansicht: laeuft der Dienst
/// nicht, gibt es hier nichts zu zeigen -- die Karten liegen als Erzeugnis
/// hinter ihm.
struct LandkartenAnsicht: View {
    @Bindable var aufsicht: DienstAufsicht

    var body: some View {
        switch aufsicht.zustand {
        case .laeuft:
            // Der Rahmen ist nicht Kosmetik: ohne ihn hat das WKWebView im
            // umgebenden VStack keine eigene Groesse und wird zu einer
            // Flaeche von null Punkten -- gemessen 2026-08-16, die Ansicht
            // war ausgewaehlt, der Dienst lief, die Seite lieferte 200, und
            // zu sehen war eine leere schwarze Flaeche. Die Wissensraum-Sicht
            // faellt nicht darauf herein, weil dort Divider und Bedienleiste
            // darunter das Layout aufspannen.
            LandkartenWebView()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        case .startetGerade:
            VStack {
                Spacer()
                ProgressView("Landkarten werden geladen …")
                Spacer()
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        case .unerwartetBeendet, .angehalten:
            // Kein leeres weisses Rechteck, aber auch keine zweite
            // Fehlermeldung -- die steht schon im Banner darueber.
            Color.clear
        }
    }
}

private struct LandkartenWebView: NSViewRepresentable {
    func makeNSView(context: Context) -> WKWebView {
        let webView = WKWebView(frame: .zero, configuration: WKWebViewConfiguration())
        webView.navigationDelegate = context.coordinator
        webView.load(URLRequest(url: DienstAufsicht.basisURL.appendingPathComponent("landkarten")))
        return webView
    }

    func makeCoordinator() -> Melder { Melder() }

    /// Meldet Ladefehler. Bleibt, obwohl die Sonde weg ist: ohne
    /// navigationDelegate ist "die Flaeche ist leer" nicht von "die Seite
    /// kam nicht" zu unterscheiden -- drei verschiedene Ursachen, ein
    /// identisches Bild. Genau daran hat die Fehlersuche am 2026-08-16
    /// zwei Anlaeufe verloren.
    @MainActor
    final class Melder: NSObject, WKNavigationDelegate {
        func webView(_ w: WKWebView, didFail n: WKNavigation!, withError e: Error) {
            FileHandle.standardError.write(Data("Landkarten: \(e.localizedDescription)\n".utf8))
        }
        func webView(_ w: WKWebView, didFailProvisionalNavigation n: WKNavigation!, withError e: Error) {
            FileHandle.standardError.write(Data("Landkarten: \(e.localizedDescription)\n".utf8))
        }
    }

    /// Nichts nachzufuehren: die Seite waehlt ihre Karte selbst, es gibt
    /// keinen Zustand auf der Swift-Seite, der sie steuern muesste. Genau das
    /// ist der Unterschied zum Wissensraum -- dort haelt Swift den Blick.
    func updateNSView(_ webView: WKWebView, context: Context) {}
}
