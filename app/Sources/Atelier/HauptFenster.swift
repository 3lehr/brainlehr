// Fenster mit nativer Seitenleiste. Die Eintraege sind Platzhalter -- Schritt
// 2 und 3 des Plans fuellen sie mit dem eingebetteten Wissensraum bzw. den
// Ausweisformularen. Hier zaehlt der Rahmen und die Dienstaufsicht.

import SwiftUI

enum SeitenleistenEintrag: String, CaseIterable, Identifiable {
    case quellen
    case raster
    case bearbeitung
    case sitzung
    case wissensraum
    case ausweise

    var id: String { rawValue }

    var titel: String {
        switch self {
        case .quellen: return "Quellen"
        case .raster: return "Mehrfachansicht"
        case .bearbeitung: return "Bearbeiten"
        case .sitzung: return "Sitzung"
        case .wissensraum: return "Wissensraum"
        case .ausweise: return "Ausweise und Einladungen"
        }
    }

    var symbol: String {
        switch self {
        case .quellen: return "doc.text.magnifyingglass"
        case .raster: return "square.grid.2x2"
        case .bearbeitung: return "square.and.pencil"
        case .sitzung: return "bubble.left.and.text.bubble.right"
        case .wissensraum: return "point.3.filled.connected.trianglepath.dotted"
        case .ausweise: return "person.text.rectangle"
        }
    }
}

struct HauptFenster: View {
    @Bindable var aufsicht: DienstAufsicht
    /// Die Ansichtswahl liegt AUSSERHALB des Fensters, damit die Menueleiste
    /// sie umschalten kann -- sie ist der Rueckweg, wenn die Seitenleiste
    /// eingeklappt ist.
    @ObservedObject var wahl: Ansichtswahl

    var body: some View {
        NavigationSplitView {
            List(selection: Binding(
                get: { Optional(wahl.aktuell) },
                set: { if let n = $0 { wahl.aktuell = n } })) {
                ForEach(SeitenleistenEintrag.allCases) { eintrag in
                    Label(eintrag.titel, systemImage: eintrag.symbol)
                        .accessibilityLabel(eintrag.titel)
                        .tag(eintrag)
                    // Die Ansichtswahl des Wissensraums sitzt nativ direkt
                    // unter seinem Eintrag in derselben Seitenleiste --
                    // nicht als Knopfleiste im eingebetteten Web.
                    if eintrag == .wissensraum && wahl.aktuell == .wissensraum {
                        ForEach(WissensraumBlick.allCases) { blick in
                            Button {
                                wahl.blick = blick
                            } label: {
                                Text(blick.titel)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            }
                            .buttonStyle(.plain)
                            .padding(.leading, 24)
                            .foregroundStyle(blick == wahl.blick ? Color.accentColor : Color.primary)
                            .accessibilityAddTraits(blick == wahl.blick ? [.isSelected] : [])
                            .accessibilityHint("Zeigt die Ansicht \(blick.titel) im Wissensraum.")
                        }
                    }
                }
            }
            .navigationTitle("Brainlehr")
            .navigationSplitViewColumnWidth(min: 200, ideal: 220, max: 280)
        } detail: {
            VStack(spacing: 0) {
                if wahl.aktuell == .quellen {
                    QuellenBereich()
                } else if wahl.aktuell == .raster {
                    RasterAnsicht()
                } else if wahl.aktuell == .bearbeitung {
                    BearbeitungsAnsicht()
                } else if wahl.aktuell == .sitzung {
                    SitzungsAnsicht()
                } else if wahl.aktuell == .wissensraum {
                    // Banner nur hier: er meldet den Wissensraum-Dienst, mit
                    // dem der Ausweis-Ablauf (eigener Subprozess) nichts zu
                    // tun hat -- auf der Ausweise-Seite waere er irrefuehrend.
                    DienstBanner(aufsicht: aufsicht)
                    WissensraumAnsicht(aufsicht: aufsicht, blick: wahl.blick)
                } else if wahl.aktuell == .ausweise {
                    AusweisAnsicht()
                }
            }
        }
    }
}

/// Traegt den Wechsel zwischen "Dienst laeuft" (Web-Fenster), "startet
/// gerade" (kurzer Hinweis statt leerer Flaeche) und Fehler (Banner deckt
/// die Meldung bereits ab, hier bleibt die Flaeche neutral).
private struct WissensraumAnsicht: View {
    @Bindable var aufsicht: DienstAufsicht
    let blick: WissensraumBlick
    /// Ueberlebt den Ansichtswechsel -- sonst faenge jede Rueckkehr in den
    /// Wissensraum wieder bei den Vorgaben an.
    @StateObject private var werte = Wissensraumwerte()

    var body: some View {
        switch aufsicht.zustand {
        case .laeuft:
            WissensraumWebView(blick: blick, werte: werte)
            Divider()
            WissensraumBedienung(blick: blick, werte: werte)
        case .startetGerade:
            VStack {
                Spacer()
                ProgressView("Wissensraum wird geladen …")
                Spacer()
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        case .unerwartetBeendet, .angehalten:
            // Kein leeres weisses Rechteck, aber auch keine doppelte
            // Fehlermeldung -- die steht schon im Banner darueber.
            Color.clear
        }
    }
}

/// Zeigt ein unerwartetes Ende des Dienstes ungefragt an -- ohne dass der
/// Benutzer erst irgendwo hinklicken muss.
private struct DienstBanner: View {
    @Bindable var aufsicht: DienstAufsicht

    var body: some View {
        if let meldung = aufsicht.meldung, aufsicht.zustand.istFehler {
            HStack(spacing: 12) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundStyle(.red)
                    .accessibilityHidden(true)
                Text(meldung)
                    .accessibilityLabel("Hinweis: \(meldung)")
                Spacer()
                Button("Erneut versuchen") {
                    aufsicht.erneutVersuchen()
                }
                .accessibilityHint("Startet den Wissensraum neu.")
            }
            .padding()
            .background(.red.opacity(0.12))
            .transition(.move(edge: .top).combined(with: .opacity))
        }
    }
}
