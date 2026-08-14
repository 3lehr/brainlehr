// Der Vorschaumonitor -- mehrere Quellen nebeneinander, wenn die Flaeche es
// traegt, sonst EIN Feld. Ein Raster aus unlesbaren Kacheln ist schlechter
// als ein lesbares Feld (ADR-004).
//
// Schritt B4 aus docs/PLAN_OBERFLAECHE_2026-08-13.md. Das Vorbild des
// Betreibers ("Vorschaumonitor eines Videomischers") ist dort eingeordnet:
// es traegt erst ab zwei tragfaehigen Feldern, sonst waere es auf dem Laptop
// ein leeres Gitter.
//
// DIE FELDZAHL STEHT WEDER HIER NOCH IN raster.json. Sie folgt aus der
// ECHTEN Bildschirmflaeche (CGDisplayScreenSize -- ein Punkt ist KEIN
// 1/72 Zoll, siehe BrainlehrCore/Anzeigeform.swift) und dem eingestellten
// Betrachtungsabstand, gerechnet ueber Anzeigeflaeche.form(...) /
// .felder(...). raster.json beschreibt nur, WAS in ein Feld darf.
//
// VERTAUSCHEN OHNE ZIEHEN (WCAG 2.5.7): jedes Feld traegt EIN Menue, das
// zugleich den Inhalt waehlt UND mit einem anderen Feld tauscht. Dasselbe
// Menue ist die Tastaturbedienung -- oeffnet mit Leertaste/Eingabe, blaettert
// mit den Pfeiltasten, kein Ziehen noetig.

import AppKit
import BrainlehrCore
import CoreGraphics
import SwiftUI

// MARK: - Katalog (raster.json)

/// Eine moegliche Feldbelegung -- WAS gezeigt werden kann, nie WIE VIELE
/// Felder es gibt.
struct RasterBelegung: Decodable, Identifiable, Equatable {
    let id: String
    let titel: String
    let symbol: String
}

private struct RasterKatalogDatei: Decodable {
    let belegungen: [RasterBelegung]
}

enum RasterKatalog {
    /// Rueckfall, falls raster.json fehlt oder kaputt ist -- dieselbe Haltung
    /// wie Lesbarkeitswerte.gemessen: eine App, die ohne ihre Beidatei gar
    /// nichts zeigt, ist schlechter als eine mit dem letzten bekannten Stand.
    static let rueckfall: [RasterBelegung] = [
        RasterBelegung(id: "leer", titel: "Leer", symbol: "square.dashed"),
    ]

    static func lade() -> [RasterBelegung] {
        guard let wurzel = DienstAufsicht.findeRepoWurzel(
            zusatzStart: Bundle.main.bundleURL.deletingLastPathComponent()
        ) else { return rueckfall }
        let pfad = wurzel.appendingPathComponent("app/Resources/raster.json")
        guard let daten = FileManager.default.contents(atPath: pfad.path),
              let datei = try? JSONDecoder().decode(RasterKatalogDatei.self, from: daten),
              !datei.belegungen.isEmpty
        else { return rueckfall }
        return datei.belegungen
    }

    /// `nil`, wenn `id` im Katalog nicht (mehr) vorkommt -- fuehrt im Feld zu
    /// einem Hinweis, nie zum Absturz.
    static func belegung(fuer id: String, in katalog: [RasterBelegung]) -> RasterBelegung? {
        katalog.first { $0.id == id }
    }
}

// MARK: - Ansicht

struct RasterAnsicht: View {
    private let katalog: [RasterBelegung]
    @State private var flaeche: Anzeigeflaeche?
    @State private var abstandMm: Double
    @State private var inhalt: [String]

    init(katalog: [RasterBelegung] = RasterKatalog.lade(), abstandMm: Double = 700) {
        self.katalog = katalog
        _abstandMm = State(initialValue: abstandMm)
        _inhalt = State(initialValue: [katalog.first?.id ?? "leer"])
    }

    /// Solange die echte Flaeche noch nicht gemessen ist, gilt der engste
    /// Fall -- ein Feld, kein Raster, das gleich wieder umgebaut wird.
    private var form: Anzeigeform { flaeche?.form(abstandMm: abstandMm) ?? .ausschnitt }

    private var feldzahl: Int {
        form == .nebeneinander ? max(2, flaeche?.felder(abstandMm: abstandMm) ?? 2) : 1
    }

    var body: some View {
        VStack(spacing: 0) {
            GeometryReader { geo in
                ZStack {
                    SchirmSensor(fensterGroesse: geo.size, flaeche: $flaeche)
                        .frame(width: 0, height: 0)
                    raster
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            Divider()
            fusszeile
        }
        .onChange(of: feldzahl) { _, neu in passeInhaltAn(auf: neu) }
    }

    @ViewBuilder private var raster: some View {
        let n = feldzahl
        // Naeherungsweise quadratisches Gitter -- reine Anordnung, keine
        // Tragfaehigkeitsfrage. Die entscheidet bereits Anzeigeflaeche.felder.
        let spalten = max(1, Int(Double(n).squareRoot().rounded(.up)))
        LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 4), count: spalten),
                  spacing: 4) {
            ForEach(0..<n, id: \.self) { i in
                RasterFeld(index: i, gesamt: n, belegungId: bindungFuerFeld(i), katalog: katalog,
                           tauschen: { ziel in tausche(i, ziel) })
            }
        }
        .padding(4)
    }

    private var fusszeile: some View {
        HStack(spacing: 12) {
            Text(form.titel).font(.callout).foregroundStyle(.secondary)
                .accessibilityLabel("Anzeigeform: \(form.titel)")
            Spacer()
            Text("Abstand")
            Slider(value: $abstandMm, in: 300...3000, step: 50)
                .frame(maxWidth: 220)
                .accessibilityLabel("Betrachtungsabstand in Zentimetern")
                .accessibilityValue("\(Int(abstandMm / 10)) Zentimeter")
            Text("\(Int(abstandMm / 10)) cm").monospacedDigit()
        }
        .padding(.horizontal).padding(.vertical, 6)
    }

    private func bindungFuerFeld(_ i: Int) -> Binding<String> {
        Binding(
            get: { i < inhalt.count ? inhalt[i] : (katalog.first?.id ?? "leer") },
            set: { neu in guard i < inhalt.count else { return }; inhalt[i] = neu }
        )
    }

    /// Waechst die Feldzahl, kommen neue Felder leer dazu. Schrumpft sie,
    /// bleiben die vorderen Felder erhalten -- wer gerade eine Quelle in
    /// Feld 1 hat, soll sie nicht verlieren, nur weil das Fenster kurz
    /// kleiner wurde.
    private func passeInhaltAn(auf n: Int) {
        if inhalt.count < n {
            inhalt.append(contentsOf: Array(repeating: katalog.first?.id ?? "leer", count: n - inhalt.count))
        } else if inhalt.count > n {
            inhalt.removeLast(inhalt.count - n)
        }
    }

    /// Tauscht zwei Felder -- die einzige Art, ihre Reihenfolge zu aendern.
    /// Kein Ziehen (WCAG 2.5.7): der Aufruf kommt aus dem Menue in
    /// RasterFeld, das ebenso per Tastatur bedienbar ist.
    private func tausche(_ a: Int, _ b: Int) {
        guard a < inhalt.count, b < inhalt.count else { return }
        inhalt.swapAt(a, b)
    }
}

// MARK: - Ein Feld

private struct RasterFeld: View {
    let index: Int
    let gesamt: Int
    @Binding var belegungId: String
    let katalog: [RasterBelegung]
    let tauschen: (Int) -> Void

    private var belegung: RasterBelegung? { RasterKatalog.belegung(fuer: belegungId, in: katalog) }
    private var beschriftung: String { belegung?.titel ?? "Unbekannte Feldbelegung" }

    var body: some View {
        VStack(spacing: 8) {
            if let b = belegung {
                Image(systemName: b.symbol).font(.largeTitle).accessibilityHidden(true)
                Text(b.titel)
            } else {
                // Eine Belegung, die es nicht (mehr) gibt, fuehrt zu einem
                // leeren Feld MIT Hinweis -- nie zum Absturz und nie zu
                // stillschweigend "leer".
                Image(systemName: "exclamationmark.triangle").font(.largeTitle)
                    .foregroundStyle(.secondary).accessibilityHidden(true)
                Text("Unbekannte Feldbelegung").font(.callout)
                Text("„\(belegungId)“ ist nicht mehr im Katalog.")
                    .font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(RoundedRectangle(cornerRadius: 6).strokeBorder(Color.secondary.opacity(0.4)))
        .overlay(alignment: .topTrailing) { menue }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Feld \(index + 1) von \(gesamt): \(beschriftung)")
    }

    private var menue: some View {
        Menu {
            Section("Belegung") {
                ForEach(katalog) { eintrag in
                    Button(eintrag.titel) { belegungId = eintrag.id }
                }
            }
            if gesamt > 1 {
                Section("Tauschen mit") {
                    ForEach(0..<gesamt, id: \.self) { ziel in
                        if ziel != index {
                            Button("Feld \(ziel + 1)") { tauschen(ziel) }
                        }
                    }
                }
            }
        } label: {
            Image(systemName: "ellipsis.circle").accessibilityHidden(true)
        }
        .menuStyle(.borderlessButton)
        .frame(minWidth: 24, minHeight: 24)
        .padding(4)
        .accessibilityLabel("Feld \(index + 1): Belegung wählen oder tauschen")
        .accessibilityHint("Wählt, was in diesem Feld gezeigt wird, oder tauscht es mit einem anderen Feld.")
    }
}

// MARK: - Schirmvermessung

/// Liest die ECHTE physische Schirmgroesse (CGDisplayScreenSize) und die vom
/// Fenster belegte Flaeche in Punkten -- kein Umrechnen ueber 1/72 Zoll.
/// Gemessen an zwei angeschlossenen Geraeten (BrainlehrCore/Anzeigeform.swift):
/// der Fehlfaktor eines solchen Ratewegs waere 1,50 bzw. 1,77 gewesen, und
/// die beiden Faktoren sind verschieden -- es gibt also nicht einmal eine
/// konstante Korrektur.
private struct SchirmSensor: NSViewRepresentable {
    let fensterGroesse: CGSize
    @Binding var flaeche: Anzeigeflaeche?

    func makeNSView(context: Context) -> NSView { NSView() }

    func updateNSView(_ v: NSView, context: Context) {
        DispatchQueue.main.async { aktualisiere(v) }
    }

    private func aktualisiere(_ v: NSView) {
        guard let schirm = v.window?.screen,
              let nummer = schirm.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? NSNumber
        else { if flaeche != nil { flaeche = nil }; return }

        let displayID = CGDirectDisplayID(nummer.uint32Value)
        let mm = CGDisplayScreenSize(displayID)
        guard mm.width > 0, mm.height > 0, fensterGroesse.width > 0, fensterGroesse.height > 0 else {
            if flaeche != nil { flaeche = nil }
            return
        }
        let neue = Anzeigeflaeche(
            schirmMm: (breite: Double(mm.width), hoehe: Double(mm.height)),
            schirmPunkte: (breite: Double(schirm.frame.width), hoehe: Double(schirm.frame.height)),
            fensterPunkte: (breite: Double(fensterGroesse.width), hoehe: Double(fensterGroesse.height)))
        if neue != flaeche { flaeche = neue }
    }
}
