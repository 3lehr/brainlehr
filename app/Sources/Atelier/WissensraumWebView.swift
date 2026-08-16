// Schritt 2 des Plans (docs/PLAN_MACAPP_2026-08-12.md): die fuenf Ansichten
// aus entscheidungen.html eingebettet, Ansichtswahl nativ in der
// Seitenleiste statt als Knopfleiste im Web. entscheidungen.html selbst ist
// tabu (Auftragstabelle Schritt 2) -- die fuenf Web-Knoepfe b0..b4 bleiben
// im Dokument, werden aber per injiziertem Skript ausgeblendet und von hier
// aus per Klick angesteuert. Das ist derselbe Weg, den ein Mensch mit der
// Maus ginge, nur ferngesteuert -- keine zweite Fassung der Ansichtslogik.

import BrainlehrCore
import SwiftUI
@preconcurrency import WebKit

/// Die fuenf Ansichten aus entscheidungen.html, Reihenfolge und Kennung (b0..b4)
/// wie dort. Nur Text als Name -- ein SF-Symbol, das es auf diesem System
/// nicht gibt, faellt stumm leer aus und traegt hier nichts zur
/// Verstaendlichkeit bei, die der Name schon liefert.
enum WissensraumBlick: Int, CaseIterable, Identifiable {
    case baum = 0
    case bedeutung = 1
    case spuren = 2
    case vergleich = 3
    case abrufweg = 4

    var id: Int { rawValue }

    /// Kennung fuer die Steuerschnittstelle -- kleingeschrieben, stabil.
    /// Der Titel darf sich aendern, diese Kennung nicht: an ihr haengen
    /// Skripte und Proben.
    var kennung: String { titel.lowercased() }

    var titel: String {
        switch self {
        case .baum: return "Baum"
        case .bedeutung: return "Bedeutung"
        case .spuren: return "Spuren"
        case .vergleich: return "Vergleich"
        case .abrufweg: return "Abrufweg"
        }
    }
}

/// Eingebettetes `WKWebView` auf den lokalen Dienst. Wird nur erzeugt,
/// solange der Dienst laeuft (siehe WissensraumAnsicht) -- verschwindet die
/// View aus der Hierarchie, faellt das `WKWebView` weg und mit ihm jede
/// laufende Zeichenschleife der Seite. Das ist der verlaessliche Weg, den
/// Puls beim Ansichtswechsel anzuhalten: kein Verlass auf `document.hidden`
/// in einem eingebetteten Fenster, dessen Sichtbarkeitsmeldung von der
/// Einbettung abhaengt.
struct WissensraumWebView: NSViewRepresentable {
    var blick: WissensraumBlick
    /// Nimmt die nativen Reglerwerte entgegen. Wird beim Erzeugen eingehaengt.
    var werte: Wissensraumwerte

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeNSView(context: Context) -> WKWebView {
        let konfiguration = WKWebViewConfiguration()
        // Blendet die GANZE Web-Bedienleiste aus: Ansichtswahl sitzt nativ in
        // der Seitenleiste, die Regler seit 2026-08-14 nativ darunter
        // (WissensraumBedienung). Vorher wurden nur die fuenf Knoepfe b0..b4
        // versteckt und die Reglerleiste blieb stehen -- eine Web-Leiste in
        // einer Mac-App, gebaut fuer ein Fenster, das alles zeigen muss.
        let skript = WKUserScript(
            source: Wissensraumregler.webleisteAusblenden,
            injectionTime: .atDocumentEnd,
            forMainFrameOnly: true
        )
        konfiguration.userContentController.addUserScript(skript)

        let webView = WKWebView(frame: .zero, configuration: konfiguration)
        webView.navigationDelegate = context.coordinator
        context.coordinator.zielBlick = blick
        context.coordinator.werte = werte
        webView.load(URLRequest(url: DienstAufsicht.basisURL))
        return webView
    }

    func updateNSView(_ webView: WKWebView, context: Context) {
        context.coordinator.zielBlick = blick
        guard context.coordinator.seiteGeladen, context.coordinator.angezeigterBlick != blick else { return }
        context.coordinator.angezeigterBlick = blick
        webView.evaluateJavaScript("document.getElementById('b\(blick.rawValue)')?.click();")
    }

    @MainActor
    final class Coordinator: NSObject, WKNavigationDelegate {
        var seiteGeladen = false
        var zielBlick: WissensraumBlick = .baum
        var angezeigterBlick: WissensraumBlick = .baum
        var werte: Wissensraumwerte?

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            seiteGeladen = true
            // Erst jetzt einhaengen: vorher gibt es kein Dokument, in das
            // geschrieben werden koennte. Das Einhaengen reicht die
            // gespeicherten Werte selbst nach (siehe Wissensraumwerte.senden) --
            // sonst zeigte die native Leiste einen Wert an, den die Seite nicht
            // hat, und das ist schlimmer als gar keine Einstellung.
            werte?.senden = { [weak webView] skript in
                webView?.evaluateJavaScript(skript)
            }
            // Die Seite startet immer bei "Baum" (b0, aria-pressed bereits
            // gesetzt) -- nur bei einer abweichenden Zielansicht muss
            // tatsaechlich geklickt werden.
            if zielBlick != .baum {
                angezeigterBlick = zielBlick
                webView.evaluateJavaScript("document.getElementById('b\(zielBlick.rawValue)')?.click();")
            } else {
                angezeigterBlick = .baum
            }
        }
    }
}
