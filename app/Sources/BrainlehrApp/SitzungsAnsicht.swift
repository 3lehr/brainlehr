// Der laufende Sitzungsstrom -- Chat, Denken, Werkzeuge, waehlbare
// Ausfuehrlichkeit. Schritt B3 aus docs/PLAN_OBERFLAECHE_2026-08-13.md.
//
// Die Zerlegung (Sitzungsstrom.zerlege/gefiltert/aktuellerSchritt) ist fertig
// und getestet -- diese Datei tut nur, was eine Schicht hoeher liegt: die
// wachsende Datei finden, laufend nachlesen, anzeigen.
//
// NUR DER ZUWACHS WIRD GELESEN. Die Datei kann ueber Stunden auf mehrere MB
// wachsen (gemessen: 3 MB in einer Sitzung) -- bei jedem Timer-Tick von vorn
// zu lesen waere die bequeme, aber falsche Antwort. Der Dateizeiger merkt
// sich die Leseposition, ein Tick liest nur, was seit dem letzten Mal
// dazukam.

import BrainlehrCore
import SwiftUI

struct SitzungsAnsicht: View {
    @StateObject private var beobachter = SitzungsBeobachter()
    @State private var stufe: Ausfuehrlichkeit = .normal

    private var gefiltert: [Sitzungsereignis] {
        Sitzungsstrom.gefiltert(beobachter.ereignisse, stufe)
    }

    var body: some View {
        VStack(spacing: 0) {
            Picker("Ausführlichkeit", selection: $stufe) {
                ForEach(Ausfuehrlichkeit.allCases, id: \.self) { s in
                    Text(s.titel).tag(s)
                }
            }
            .pickerStyle(.segmented)
            .padding()
            .accessibilityLabel("Ausführlichkeit")

            // Das Denken-Fenster: NICHTS, solange aktuellerSchritt() nil
            // liefert -- eine Anzeige, die einen alten Stand als laufend
            // ausgibt, ist schlechter als eine leere Zeile.
            if let schritt = beobachter.aktuellerSchritt {
                HStack(spacing: 6) {
                    ProgressView().controlSize(.small)
                    Text(schritt).font(.callout).foregroundStyle(.secondary).lineLimit(1)
                }
                .padding(.horizontal).padding(.bottom, 8)
                .accessibilityElement(children: .combine)
                .accessibilityLabel("Läuft gerade: \(schritt)")
            }

            Divider()

            if let meldung = beobachter.meldung {
                VStack {
                    Spacer()
                    Text(meldung).font(.title3).multilineTextAlignment(.center).padding()
                    Spacer()
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                Strom(ereignisse: gefiltert)
            }
        }
        .onAppear { beobachter.starte() }
        .onDisappear { beobachter.stoppe() }
    }
}

/// Die Liste selbst, juengstes Ereignis unten und der Bildlauf folgt ihm.
private struct Strom: View {
    let ereignisse: [Sitzungsereignis]

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 10) {
                    ForEach(Array(ereignisse.enumerated()), id: \.offset) { i, e in
                        EreignisZeile(ereignis: e).id(i)
                    }
                }
                .padding()
            }
            .onChange(of: ereignisse.count) { _, _ in
                guard let letzter = ereignisse.indices.last else { return }
                withAnimation { proxy.scrollTo(letzter, anchor: .bottom) }
            }
        }
    }
}

private struct EreignisZeile: View {
    let ereignis: Sitzungsereignis

    var body: some View {
        switch ereignis.art {
        case .eingabe:
            sprechblase(text: ereignis.text, bezeichnung: "Sie", trailing: true, betont: true)
        case .antwort:
            sprechblase(text: ereignis.text, bezeichnung: "Antwort", trailing: false, betont: true)
        case .denken:
            arbeitsschritt(symbol: "ellipsis.bubble", text: ereignis.text, bezeichnung: "Gedanke")
        case .werkzeug:
            arbeitsschritt(symbol: "wrench.and.screwdriver", text: ereignis.werkzeug ?? ereignis.text,
                           bezeichnung: "Werkzeugaufruf")
        case .ergebnis:
            arbeitsschritt(symbol: "arrow.turn.down.right", text: ereignis.text, bezeichnung: "Ergebnis")
        }
    }

    /// Chat-Blase -- Eingabe rechts, Antwort links, das ist der erkennbare
    /// Unterschied. Nicht allein ueber Farbe: die Ausrichtung UND die
    /// vorgelesene Bezeichnung tragen ihn.
    private func sprechblase(text: String, bezeichnung: String, trailing: Bool, betont: Bool) -> some View {
        HStack {
            if trailing { Spacer(minLength: 40) }
            Text(text)
                .font(.body)
                .padding(10)
                .background(trailing ? Color.accentColor.opacity(0.15) : Color.secondary.opacity(0.12),
                           in: RoundedRectangle(cornerRadius: 10))
            if !trailing { Spacer(minLength: 40) }
        }
        .frame(maxWidth: .infinity, alignment: trailing ? .trailing : .leading)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(bezeichnung): \(text)")
    }

    private func arbeitsschritt(symbol: String, text: String, bezeichnung: String) -> some View {
        HStack(alignment: .top, spacing: 6) {
            Image(systemName: symbol).foregroundStyle(.tertiary).accessibilityHidden(true)
            Text(text).font(.caption).foregroundStyle(.secondary)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(bezeichnung): \(text)")
    }
}

// MARK: - Beobachtung der wachsenden Datei

/// Findet die Strom-Datei der laufenden Sitzung und liest sie laufend nach.
/// Ein Timer statt eines Dateisystem-Beobachters -- der Plan verlangt nicht
/// mehr, und ein Tick pro anderthalb Sekunden reicht bei einem Strom, der im
/// Sekundentakt waechst.
@MainActor
final class SitzungsBeobachter: ObservableObject {
    @Published private(set) var ereignisse: [Sitzungsereignis] = []
    /// Gesetzt, wenn nichts angezeigt werden kann -- Nutzersprache, kein Pfad.
    @Published private(set) var meldung: String?

    var aktuellerSchritt: String? { Sitzungsstrom.aktuellerSchritt(ereignisse) }

    private var handle: FileHandle?
    private var restZeile = Data()
    private var timer: Timer?

    func starte() {
        guard timer == nil else { return }
        guard let pfad = Self.neuesteStromdatei() else {
            meldung = "Für diese Sitzung liegt noch kein Verlauf vor."
            return
        }
        guard let h = FileHandle(forReadingAtPath: pfad) else {
            meldung = "Der Sitzungsverlauf lässt sich gerade nicht lesen."
            return
        }
        handle = h
        lies()
        timer = Timer.scheduledTimer(withTimeInterval: 1.5, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.lies() }
        }
    }

    func stoppe() {
        timer?.invalidate(); timer = nil
        try? handle?.close(); handle = nil
    }

    /// Liest nur, was seit dem letzten Aufruf angehaengt wurde. Eine halbe
    /// letzte Zeile ist der Normalfall -- sie wird zurueckgehalten und beim
    /// naechsten Tick vervollstaendigt.
    private func lies() {
        guard let h = handle else { return }
        let neu = h.readDataToEndOfFile()
        guard !neu.isEmpty else { return }
        restZeile.append(neu)

        guard let trennerAmEnde = restZeile.range(of: Data([0x0A]), options: .backwards) else { return }
        let vollstaendig = restZeile.subdata(in: restZeile.startIndex..<trennerAmEnde.upperBound)
        restZeile = restZeile.subdata(in: trennerAmEnde.upperBound..<restZeile.endIndex)

        guard let text = String(data: vollstaendig, encoding: .utf8) else { return }
        let frisch = text.split(separator: "\n", omittingEmptySubsequences: true)
            .flatMap { Sitzungsstrom.zerlege(String($0)) }
        if !frisch.isEmpty { ereignisse.append(contentsOf: frisch) }
    }

    /// Die zuletzt geaenderte `.jsonl` im Sitzungsordner der Repo-Wurzel --
    /// das ist die laufende Sitzung, aeltere Dateien sind vergangene.
    private static func neuesteStromdatei() -> String? {
        guard let wurzel = DienstAufsicht.findeRepoWurzel(
            zusatzStart: Bundle.main.bundleURL.deletingLastPathComponent()
        ) else { return nil }

        // Claude Code legt den Sitzungsordner unter dem Pfad der Repo-Wurzel
        // an, jedes Zeichen ausser Buchstabe/Ziffer wird zu "-".
        let kennung = String(wurzel.standardizedFileURL.path.map { z in
            z.isLetter || z.isNumber ? z : "-"
        })
        let ordner = (NSHomeDirectory() as NSString)
            .appendingPathComponent(".claude/projects/\(kennung)")

        let fm = FileManager.default
        guard let dateien = try? fm.contentsOfDirectory(atPath: ordner) else { return nil }
        let stroeme = dateien.filter { $0.hasSuffix(".jsonl") }
        let neueste = stroeme.max { a, b in
            geaendertAm(fm, "\(ordner)/\(a)") < geaendertAm(fm, "\(ordner)/\(b)")
        }
        return neueste.map { "\(ordner)/\($0)" }
    }

    private static func geaendertAm(_ fm: FileManager, _ pfad: String) -> Date {
        (try? fm.attributesOfItem(atPath: pfad)[.modificationDate] as? Date) ?? nil ?? .distantPast
    }
}
