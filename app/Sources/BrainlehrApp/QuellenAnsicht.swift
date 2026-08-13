// Ein Dokument, aufgeschlagen an der belegten Stelle und markiert.
//
// Schritt B1 aus docs/PLAN_OBERFLAECHE_2026-08-13.md. Der Auftrag des
// Betreibers in vier Worten: "zeig mir, wo das steht".
//
// DREI ANZEIGEWEGE, weil kein einzelner alles kann -- gemessen am 2026-08-13,
// nicht aus der Doku uebernommen:
//   PDF   PDFKit. Findet die Seite selbst, sucht in 12 ms, markiert dauerhaft.
//   Text  NSTextView fuer html und txt. Kann aufschlagen UND hervorheben,
//         mit Tastatur und zugaenglichem Namen.
//   Bild  Quick Look -- aber MIT Formatpruefung davor, denn es sagt selbst
//         nie "nein": eine erfundene Endung ".zzq" wird angenommen und
//         liefert ein Symbol, das von Erfolg nicht zu unterscheiden ist.
//
// DIE QUELLDATEI WIRD NIE VERAENDERT. Markierungen entstehen im Speicher
// (PDFAnnotation ohne write) bzw. als Textattribut. Schwaerzungen erzeugen
// Kopien -- das Original ist eine Projektion wert, keine Aenderung.

import AppKit
import BrainlehrCore
import PDFKit
import QuickLookUI
import SwiftUI
import UniformTypeIdentifiers

struct QuellenAnsicht: View {
    let fundstelle: Fundstelle
    let betrachter: Betrachter
    /// Abstand zum Schirm in Millimetern. SICHTBARE Einstellung, kein
    /// Messwert: Kein Geraet weiss, wie weit jemand wegsitzt -- und der
    /// Abstand entscheidet mehr als die Bildschirmgroesse (gemessen: derselbe
    /// 27-Zoeller traegt bei 0,5 m drei Seiten und bei 0,7 m keine).
    @State private var abstandMm: Double = 700
    @State private var befund: Dokumentbefund = .bereit
    /// Eigene Suche im Dokument. DIE Handlung fuer den Regelfall: Bei 17 von
    /// 49 Quellen ist keine Stelle hinterlegt -- dann muss der Mensch selbst
    /// suchen koennen, statt auf eine Markierung zu warten, die nie kommt.
    @State private var eigeneSuche: String = ""
    @FocusState private var sucheImFokus: Bool

    private var datei: String { (fundstelle.absolut as NSString).lastPathComponent }
    private var weg: Anzeigeweg { Quelldokument.weg(fuer: datei) }

    var body: some View {
        VStack(spacing: 0) {
            Kopfzeile(fundstelle: fundstelle, befund: befund,
                      suchenGedrueckt: { sucheImFokus = true })
            if !fundstelle.markierbar || !eigeneSuche.isEmpty {
                HStack {
                    Image(systemName: "magnifyingglass").accessibilityHidden(true)
                    TextField("Im Dokument suchen", text: $eigeneSuche)
                        .textFieldStyle(.roundedBorder)
                        .focused($sucheImFokus)
                        .accessibilityLabel("Im Dokument suchen")
                }
                .padding(.horizontal).padding(.bottom, 6)
            }
            Divider()

            if befund.istBereit {
                inhalt
            } else {
                Hinweisflaeche(befund: befund, datei: fundstelle.absolut)
            }

            Divider()
            Fusszeile(abstandMm: $abstandMm, weg: weg)
        }
        .onAppear(perform: pruefe)
        .onChange(of: fundstelle.absolut) { _, _ in pruefe() }
    }

    @ViewBuilder private var inhalt: some View {
        switch weg {
        case .pdf:
            PdfAnsicht(pfad: fundstelle.absolut,
                       seite: fundstelle.seite,
                       suchtext: markierung,
                       befund: $befund)
        case .text:
            TextAnsicht(pfad: fundstelle.absolut,
                        suchtext: markierung,
                        betrachter: betrachter,
                        befund: $befund)
        case .bild, .unbekannt:
            VorschauAnsicht(pfad: fundstelle.absolut)
        }
    }

    /// Markiert wird nur, wenn ALLE drei Bedingungen stehen -- Format, Befund,
    /// Suchtext. Eine Markierung ohne Beleg sieht im Raum aus wie ein Beleg,
    /// und dort widerspricht ihr niemand.
    private var markierung: String? {
        // Die eigene Suche schlaegt die gepflegte Fundstelle -- wer selbst
        // tippt, will das sehen, was er getippt hat.
        let wort = eigeneSuche.trimmingCharacters(in: .whitespacesAndNewlines)
        let gewaehlt = wort.isEmpty ? fundstelle.suchtext : wort
        return Quelldokument.darfMarkieren(dateiname: datei, befund: befund,
                                           suchtext: gewaehlt) ? gewaehlt : nil
    }

    private func pruefe() {
        let pfad = fundstelle.absolut
        guard !pfad.isEmpty else { befund = .fehlt; return }
        let da = FileManager.default.fileExists(atPath: pfad)
        var gesperrt = false, lesbar = true
        if Quelldokument.weg(fuer: datei) == .pdf, da {
            // isLocked VOR allem anderen: Ein gesperrtes PDF ist nicht nil --
            // pageCount stimmt, eine Miniatur entsteht, und die Suche liefert
            // null Treffer. Wer zuerst auf Lesbarkeit prueft, macht daraus
            // stillschweigend "keine Fundstelle".
            if let d = PDFDocument(url: URL(fileURLWithPath: pfad)) {
                gesperrt = d.isLocked
            } else {
                lesbar = false
            }
        }
        befund = Quelldokument.befund(dateiname: datei, existiert: da,
                                      istGesperrt: gesperrt, istLesbar: lesbar)
    }
}

// MARK: - Kopf und Fuss

private struct Kopfzeile: View {
    let fundstelle: Fundstelle
    let befund: Dokumentbefund
    let suchenGedrueckt: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(fundstelle.kurz.isEmpty ? "Quelle" : fundstelle.kurz)
                .font(.headline)
                .accessibilityAddTraits(.isHeader)
            HStack(spacing: 8) {
                // Der ERFOLGSFALL bekommt ausdruecklich auch einen Text.
                // Sonst bedeutet die Abwesenheit einer Beschriftung
                // "markiert" -- dieselbe Fehlerklasse wie Bedeutung ueber
                // Farbe, nur ueber Leere statt ueber Farbton.
                Image(systemName: fundstelle.markierbar ? "text.viewfinder" : "doc")
                    .accessibilityHidden(true)
                Text(fundstelle.lage)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                if let h = fundstelle.handlung {
                    Spacer()
                    Button(h, action: suchenGedrueckt)
                        .accessibilityHint("Setzt den Schreibfokus in das Suchfeld.")
                }
            }
            .accessibilityElement(children: .combine)
            .accessibilityLabel("Lage: \(fundstelle.lage)")
        }
        .padding(.horizontal).padding(.vertical, 8)
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct Fusszeile: View {
    @Binding var abstandMm: Double
    let weg: Anzeigeweg

    var body: some View {
        HStack(spacing: 12) {
            Text("Abstand")
            Slider(value: $abstandMm, in: 300...3000, step: 50)
                .frame(maxWidth: 220)
                .accessibilityLabel("Betrachtungsabstand in Zentimetern")
                .accessibilityValue("\(Int(abstandMm / 10)) Zentimeter")
            Text("\(Int(abstandMm / 10)) cm").monospacedDigit()
            Spacer()
            if !weg.kannHervorheben {
                Text("In diesem Format kann keine Stelle hervorgehoben werden.")
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
        .padding(.horizontal).padding(.vertical, 6)
    }
}

/// Meldung UND Handlung. Eine Meldung ohne Handlung ist eine Sackgasse, und
/// eine Sackgasse mitten in einer Besprechung ist schlimmer als eine leere
/// Flaeche, weil sie zum Suchen einlaedt.
private struct Hinweisflaeche: View {
    let befund: Dokumentbefund
    let datei: String

    var body: some View {
        VStack(spacing: 12) {
            Spacer()
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.largeTitle).foregroundStyle(.secondary)
                .accessibilityHidden(true)
            Text(befund.meldung ?? "")
                .font(.title3).multilineTextAlignment(.center)
            if let h = befund.handlung {
                Button(h) {
                    NSWorkspace.shared.open(URL(fileURLWithPath: datei))
                }
                .accessibilityHint("Öffnet das Dokument mit dem Standardprogramm.")
            }
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .accessibilityElement(children: .contain)
    }
}

// MARK: - PDF

private struct PdfAnsicht: NSViewRepresentable {
    let pfad: String
    let seite: Int?
    let suchtext: String?
    @Binding var befund: Dokumentbefund

    func makeNSView(context: Context) -> PDFView {
        let v = PDFView()
        v.autoScales = true
        v.displayMode = .singlePageContinuous
        // PDFView meldet isAccessibilityElement()=false und AXUnknown -- der
        // zugaengliche Name muss gesetzt werden, sonst ist die Ansicht fuer
        // Vorlesesoftware eine namenlose Gruppe.
        v.setAccessibilityElement(true)
        v.setAccessibilityRole(.group)
        v.setAccessibilityLabel("Dokumentansicht")
        return v
    }

    func updateNSView(_ v: PDFView, context: Context) {
        guard let d = PDFDocument(url: URL(fileURLWithPath: pfad)) else {
            DispatchQueue.main.async { befund = .nichtLesbar }
            return
        }
        if d.isLocked {
            DispatchQueue.main.async { befund = .passwortNoetig }
            return
        }
        v.document = d
        v.layoutDocumentView()

        // Suchen kommt VOR dem Seitensprung: PDFKit kennt die Seite des
        // Treffers selbst, und die gepflegte Seitenzahl kann fehlen (Quelle 48
        // traegt einen Suchtext ohne Seite).
        if let s = suchtext, !s.isEmpty,
           let treffer = d.findString(s, withOptions: [.caseInsensitive]).first {
            v.setCurrentSelection(treffer, animate: false)
            v.highlightedSelections = [treffer]   // fluechtig -- die Datei bleibt unberuehrt
            v.go(to: treffer)
            v.setAccessibilityLabel("Dokumentansicht, Stelle markiert: \(s)")
        } else if let n = seite, n >= 1, n <= d.pageCount, let p = d.page(at: n - 1) {
            v.go(to: p)
            v.setAccessibilityLabel("Dokumentansicht, Seite \(n)")
        }
    }
}

// MARK: - Text (html, txt)

private struct TextAnsicht: NSViewRepresentable {
    let pfad: String
    let suchtext: String?
    let betrachter: Betrachter
    @Binding var befund: Dokumentbefund

    func makeNSView(context: Context) -> NSScrollView {
        let scroll = NSTextView.scrollableTextView()
        if let tv = scroll.documentView as? NSTextView {
            tv.isEditable = false
            tv.isSelectable = true
            tv.setAccessibilityLabel("Dokumenttext")
        }
        return scroll
    }

    func updateNSView(_ scroll: NSScrollView, context: Context) {
        guard let tv = scroll.documentView as? NSTextView else { return }
        guard let roh = FileManager.default.contents(atPath: pfad) else {
            DispatchQueue.main.async { befund = .nichtLesbar }
            return
        }
        // Kodierung AUS DER DEKLARATION lesen, nicht raten: alle 18
        // HTML-Quellen in buckeberg sind iso-8859-1 und sagen es auch.
        // utf-8 anzunehmen frisst jeden Umlaut still.
        let text = Self.lies(roh)
        guard !text.isEmpty else {
            DispatchQueue.main.async { befund = .nichtLesbar }
            return
        }
        tv.string = text

        guard let s = suchtext, !s.isEmpty,
              let bereich = text.range(of: s, options: [.caseInsensitive, .diacriticInsensitive])
        else { return }
        let nsBereich = NSRange(bereich, in: text)
        tv.scrollRangeToVisible(nsBereich)
        // Hervorheben ueber ein Textattribut -- Traeger ist die Flaeche, nicht
        // die Farbe allein: die Auswahl bleibt zusaetzlich gesetzt, damit auch
        // Vorlesesoftware die Stelle findet.
        tv.textStorage?.addAttribute(.backgroundColor, value: NSColor.findHighlightColor,
                                     range: nsBereich)
        tv.setSelectedRange(nsBereich)
        tv.setAccessibilityLabel("Dokumenttext, Stelle markiert: \(s)")
    }

    static func lies(_ roh: Data) -> String {
        let kopf = String(data: roh.prefix(4096), encoding: .isoLatin1) ?? ""
        if let m = kopf.range(of: "charset=", options: .caseInsensitive) {
            let rest = kopf[m.upperBound...].prefix(20).lowercased()
            if rest.contains("8859-1") || rest.contains("windows-1252") {
                if let s = String(data: roh, encoding: .isoLatin1) { return entferneMarken(s) }
            }
        }
        if let s = String(data: roh, encoding: .utf8) { return entferneMarken(s) }
        return entferneMarken(String(data: roh, encoding: .isoLatin1) ?? "")
    }

    /// Sichtbarer Text statt Auszeichnung. Bewusst einfach: Der Zweck ist
    /// Lesen und Finden, nicht originalgetreues Setzen -- wer das Original
    /// braucht, oeffnet es im Browser.
    static func entferneMarken(_ s: String) -> String {
        guard s.contains("<") else { return s }
        var t = s.replacingOccurrences(of: "(?is)<(script|style)\\b.*?</\\1>", with: " ",
                                       options: .regularExpression)
        t = t.replacingOccurrences(of: "(?s)<[^>]+>", with: " ", options: .regularExpression)
        for (a, b) in [("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                       ("&quot;", "\""), ("&#167;", "§")] {
            t = t.replacingOccurrences(of: a, with: b)
        }
        t = t.replacingOccurrences(of: "&#(\\d+);", with: "", options: .regularExpression)
        return t.replacingOccurrences(of: "[ \\t]{2,}", with: " ", options: .regularExpression)
    }
}

// MARK: - Alles Uebrige

/// Quick Look, aber nur nach bestandener Formatpruefung. Es sagt selbst nie
/// "nein": eine erfundene Endung wird angenommen und liefert ein Symbol, das
/// von Erfolg nicht zu unterscheiden ist.
private struct VorschauAnsicht: NSViewRepresentable {
    let pfad: String

    func makeNSView(context: Context) -> QLPreviewView {
        let v = QLPreviewView(frame: .zero, style: .normal) ?? QLPreviewView()
        v.setAccessibilityLabel("Vorschau des Dokuments")
        return v
    }

    func updateNSView(_ v: QLPreviewView, context: Context) {
        v.previewItem = URL(fileURLWithPath: pfad) as QLPreviewItem
    }
}
