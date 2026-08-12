// Fenster mit nativer Seitenleiste. Die Eintraege sind Platzhalter -- Schritt
// 2 und 3 des Plans fuellen sie mit dem eingebetteten Wissensraum bzw. den
// Ausweisformularen. Hier zaehlt der Rahmen und die Dienstaufsicht.

import SwiftUI

enum SeitenleistenEintrag: String, CaseIterable, Identifiable {
    case wissensraum
    case ausweise
    case abrufmonitor
    case einstellungen
    case offeneArbeit
    case eilmeldungen

    var id: String { rawValue }

    var titel: String {
        switch self {
        case .wissensraum: return "Wissensraum"
        case .ausweise: return "Ausweise und Einladungen"
        case .abrufmonitor: return "Abrufmonitor"
        case .einstellungen: return "Einstellungen"
        case .offeneArbeit: return "Offene Arbeit"
        case .eilmeldungen: return "Eilmeldungen"
        }
    }

    var symbol: String {
        switch self {
        case .wissensraum: return "point.3.filled.connected.trianglepath.dotted"
        case .ausweise: return "person.text.rectangle"
        case .abrufmonitor: return "waveform.path.ecg"
        case .einstellungen: return "gearshape"
        case .offeneArbeit: return "checklist"
        case .eilmeldungen: return "bell.badge"
        }
    }
}

struct HauptFenster: View {
    @Bindable var aufsicht: DienstAufsicht
    @State private var auswahl: SeitenleistenEintrag? = .wissensraum
    @State private var wissensraumBlick: WissensraumBlick = .baum

    var body: some View {
        NavigationSplitView {
            List(selection: $auswahl) {
                ForEach(SeitenleistenEintrag.allCases) { eintrag in
                    Label(eintrag.titel, systemImage: eintrag.symbol)
                        .accessibilityLabel(eintrag.titel)
                        .tag(eintrag)
                    // Die Ansichtswahl des Wissensraums sitzt nativ direkt
                    // unter seinem Eintrag in derselben Seitenleiste --
                    // nicht als Knopfleiste im eingebetteten Web.
                    if eintrag == .wissensraum && auswahl == .wissensraum {
                        ForEach(WissensraumBlick.allCases) { blick in
                            Button {
                                wissensraumBlick = blick
                            } label: {
                                Text(blick.titel)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            }
                            .buttonStyle(.plain)
                            .padding(.leading, 24)
                            .foregroundStyle(blick == wissensraumBlick ? Color.accentColor : Color.primary)
                            .accessibilityAddTraits(blick == wissensraumBlick ? [.isSelected] : [])
                            .accessibilityHint("Zeigt die Ansicht \(blick.titel) im Wissensraum.")
                        }
                    }
                }
            }
            .navigationTitle("Brainlehr")
            .navigationSplitViewColumnWidth(min: 200, ideal: 220, max: 280)
        } detail: {
            VStack(spacing: 0) {
                DienstBanner(aufsicht: aufsicht)
                if auswahl == .wissensraum {
                    WissensraumAnsicht(aufsicht: aufsicht, blick: wissensraumBlick)
                } else {
                    PlatzhalterAnsicht(eintrag: auswahl)
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

    var body: some View {
        switch aufsicht.zustand {
        case .laeuft:
            WissensraumWebView(blick: blick)
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

private struct PlatzhalterAnsicht: View {
    let eintrag: SeitenleistenEintrag?

    var body: some View {
        VStack {
            Spacer()
            Text(eintrag?.titel ?? "Brainlehr")
                .font(.title2)
                .accessibilityAddTraits(.isHeader)
            Text("Diese Ansicht wird als Naechstes gebaut.")
                .foregroundStyle(.secondary)
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
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
