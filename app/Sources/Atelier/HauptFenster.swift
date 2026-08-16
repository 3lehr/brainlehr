// Fenster mit nativer Seitenleiste. Die Eintraege sind Platzhalter -- Schritt
// 2 und 3 des Plans fuellen sie mit dem eingebetteten Wissensraum bzw. den
// Ausweisformularen. Hier zaehlt der Rahmen und die Dienstaufsicht.

import BrainlehrCore
import SwiftUI

enum SeitenleistenEintrag: String, CaseIterable, Identifiable {
    case quellen
    case raster
    case bearbeitung
    case dokument
    case sitzung
    case wissensraum
    case landkarten
    case ausweise

    var id: String { rawValue }

    /// I1 (ADR-014): nil == Kern, immer da. Ein Wert == Bestandteil, nur da
    /// wenn die aktive Domaene ihn angefordert bekam (AtelierApp.swift
    /// filtert Seitenleiste UND Menue danach, HauptFenster.body sperrt
    /// zusaetzlich die Darstellung selbst -- doppelt, weil `aktuell` auch
    /// programmatisch gesetzt werden kann, siehe Steuerschnittstelle).
    var bestandteil: Bestandteil? {
        self == .dokument ? .dokumentfenster : nil
    }

    var titel: String {
        switch self {
        case .quellen: return "Quellen"
        case .raster: return "Mehrfachansicht"
        case .bearbeitung: return "Bearbeiten"
        case .dokument: return "Dokument"
        case .sitzung: return "Sitzung"
        case .wissensraum: return "Wissensraum"
        case .landkarten: return "Landkarten"
        case .ausweise: return "Ausweise und Einladungen"
        }
    }

    var symbol: String {
        switch self {
        case .quellen: return "doc.text.magnifyingglass"
        case .raster: return "square.grid.2x2"
        case .bearbeitung: return "square.and.pencil"
        case .dokument: return "person.2.badge.gearshape"
        case .sitzung: return "bubble.left.and.text.bubble.right"
        case .wissensraum: return "point.3.filled.connected.trianglepath.dotted"
        case .landkarten: return "map"
        case .ausweise: return "person.text.rectangle"
        }
    }
}

struct HauptFenster: View {
    let dokument: Dokumentsitzung
    @Bindable var aufsicht: DienstAufsicht
    /// Die Ansichtswahl liegt AUSSERHALB des Fensters, damit die Menueleiste
    /// sie umschalten kann -- sie ist der Rueckweg, wenn die Seitenleiste
    /// eingeklappt ist.
    @ObservedObject var wahl: Ansichtswahl

    /// I1: Kern-Eintraege immer, Bestandteil-Eintraege nur wenn angefordert
    /// UND gewaehrt (Ansichtswahl.bestandteile). Dieselbe Filterung wie im
    /// Menue (AtelierApp.swift) -- zwei Bedienwege zur selben Seitenleiste.
    private var sichtbareEintraege: [SeitenleistenEintrag] {
        SeitenleistenEintrag.allCases.filter {
            $0.bestandteil == nil || wahl.bestandteile.contains($0.bestandteil!)
        }
    }

    var body: some View {
        NavigationSplitView {
            List(selection: Binding(
                get: { Optional(wahl.aktuell) },
                set: { if let n = $0 { wahl.aktuell = n } })) {
                ForEach(sichtbareEintraege) { eintrag in
                    Label(eintrag.titel, systemImage: eintrag.symbol)
                        .accessibilityLabel(eintrag.titel)
                        .tag(eintrag)
                }
            }
            .navigationTitle("Brainlehr")
            .navigationSplitViewColumnWidth(min: 200, ideal: 220, max: 280)
            // Die Blickwahl des Wissensraums steht UNTER der Liste, nicht
            // darin. Bis zum 2026-08-16 lag sie im ForEach der
            // List(selection:) und wurde dadurch selbst zur Auswahlzeile:
            // gemessen ueber die Steuerschnittstelle warf ein Setzen des
            // Blicks die ANSICHT auf einen fremden Eintrag ("ausweise",
            // nach einem ersten Reparaturversuch "bearbeitung") -- die beiden
            // Zustaende rissen einander um, und die Verbund-Ansicht war weder
            // per Maus noch per Schnittstelle erreichbar. `selectionDisabled()`
            // allein genuegte nicht; die Knoepfe duerfen gar nicht erst
            // Zeilen einer auswaehlbaren Liste sein.
            .safeAreaInset(edge: .bottom, spacing: 0) {
                if wahl.aktuell == .wissensraum {
                    VStack(alignment: .leading, spacing: 2) {
                        ForEach(WissensraumBlick.allCases) { blick in
                            Button {
                                wahl.blick = blick
                            } label: {
                                Text(blick.titel)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .contentShape(Rectangle())
                            }
                            .buttonStyle(.plain)
                            .padding(.vertical, 4)
                            .padding(.leading, 24)
                            .foregroundStyle(blick == wahl.blick ? Color.accentColor : Color.primary)
                            .accessibilityAddTraits(blick == wahl.blick ? [.isSelected] : [])
                            .accessibilityHint("Zeigt die Ansicht \(blick.titel) im Wissensraum.")
                        }
                    }
                    .padding(.vertical, 8)
                }
            }
        } detail: {
            VStack(spacing: 0) {
                if wahl.aktuell == .quellen {
                    QuellenBereich()
                } else if wahl.aktuell == .raster {
                    RasterAnsicht()
                } else if wahl.aktuell == .bearbeitung {
                    BearbeitungsAnsicht()
                } else if wahl.aktuell == .dokument && wahl.bestandteile.contains(.dokumentfenster) {
                    // I1: zweite Sperre, nicht nur die Seitenleiste oben --
                    // `aktuell` laesst sich auch programmatisch setzen
                    // (Steuerschnittstelle), das darf den Bestandteil nicht
                    // umgehen.
                    DokumentAnsicht(sitzung: dokument)
                } else if wahl.aktuell == .sitzung {
                    SitzungsAnsicht()
                } else if wahl.aktuell == .wissensraum {
                    // Banner nur hier: er meldet den Wissensraum-Dienst, mit
                    // dem der Ausweis-Ablauf (eigener Subprozess) nichts zu
                    // tun hat -- auf der Ausweise-Seite waere er irrefuehrend.
                    DienstBanner(aufsicht: aufsicht)
                    WissensraumAnsicht(aufsicht: aufsicht, blick: wahl.blick)
                } else if wahl.aktuell == .landkarten {
                    // Eigener Punkt, NICHT ein Blick des Wissensraums
                    // (Betreiberentscheidung 2026-08-16): die Karten
                    // beschreiben das System, der Wissensraum den Bestand --
                    // eine Ebene darueber. Derselbe Dienst, eigene Seite,
                    // keine gemeinsame Bedienung und keine mitlaufende
                    // Zeichenflaeche.
                    DienstBanner(aufsicht: aufsicht)
                    LandkartenAnsicht(aufsicht: aufsicht)
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
        case .aus:
            // ADR-023: der Schalter steht aus -- das ist eine Entscheidung des
            // Nutzers, kein Defekt. Ohne diesen Zweig saehe er eine leere
            // Flaeche und koennte beides nicht unterscheiden; genau dafuer
            // wurde die ADR geschrieben. Der Satz kommt aus DienstMeldung,
            // damit er an einer Stelle steht und keine Entwicklerinformation
            // traegt.
            VStack(spacing: 8) {
                Spacer()
                Text(DienstMeldung.ausgeschaltet)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 32)
                Spacer()
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        case .unerwartetBeendet, .angehalten, .kommtNichtHoch:
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
                // Der Knopf startet nichts mehr, seit der Wissensraum
                // eigenstaendig laeuft -- er sieht nur erneut nach. Ein
                // Hinweis, der etwas anderes verspricht als der Knopf tut,
                // ist fuer jemanden, der ihn VORGELESEN bekommt, die einzige
                // Beschreibung der Schaltflaeche.
                .accessibilityHint("Sieht erneut nach, ob der Wissensraum bereit ist.")
            }
            .padding()
            .background(.red.opacity(0.12))
            .transition(.move(edge: .top).combined(with: .opacity))
        }
    }
}
