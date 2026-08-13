// Findet Textstellen samt Position in einem Bild -- fuer gescannte Seiten,
// die keine Textebene haben.
//
// ANLASS (Betreiber, 2026-08-13): "und pdfs und bilder die ein 'scan' eines
// dokumentes sind muessen wir auch beruecksichtigen!"
//
// GEMESSEN im echten Bestand (1067 Seiten aus buckeberg):
//   528 Seiten  Scan MIT OCR-Textebene   -> Schwaerzung greift, belegt
//   508 Seiten  echter Text              -> greift
//    27 Seiten  REINER Scan ohne Text    -> hier greift NICHTS, ohne dieses
//                                            Werkzeug, und zwar STILL
//
// Der letzte Fall ist der gefaehrliche: `search_for()` findet nichts, also
// wird nichts markiert, also wird nichts entfernt -- und die Datei sieht
// hinterher aus wie erfolgreich geschwaerzt.
//
// WARUM VISION UND NICHT TESSERACT -- gemessen an einem echten reinen Scan
// (Angebot Jungwirth, 200 dpi):
//   Vision:     70 Textbloecke mit Position, Konfidenz 1,00, "Christian
//               Jungwirth GmbH", "HEIZUNG · SANITÄR SOLAR" sauber erkannt
//   tesseract:  "Christian", "Jungwirth", dann "Fe a"
// Vision ist eingebaut (kein Paket), erkennt hier besser und liefert
// RECHTECKE -- und die Rechtecke sind der eigentliche Grund, denn ohne
// Position laesst sich nichts schwaerzen.
//
// Ausgabe: JSON-Zeilen mit Text und Rechteck in 0..1, Ursprung UNTEN LINKS
// (Vision-Konvention). Wer nach PDF-Koordinaten umrechnet, muss y spiegeln --
// darauf weist die Ausgabe ausdruecklich hin, weil eine verkehrt herum
// gesetzte Schwaerzung die falsche Zeile trifft und trotzdem plausibel
// aussieht.

import AppKit
import Foundation
import Vision

let args = CommandLine.arguments
guard args.count > 1 else {
    FileHandle.standardError.write("Aufruf: ocr_stellen <bild.png> [suchwort ...]\n".data(using: .utf8)!)
    exit(2)
}
let pfad = args[1]
let gesucht = Array(args.dropFirst(2)).map { $0.lowercased() }

guard let bild = NSImage(contentsOfFile: pfad),
      let cg = bild.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    FileHandle.standardError.write("Bild nicht lesbar: \(pfad)\n".data(using: .utf8)!)
    exit(1)
}

let anfrage = VNRecognizeTextRequest()
anfrage.recognitionLevel = .accurate
anfrage.recognitionLanguages = ["de-DE", "en-US"]
anfrage.usesLanguageCorrection = true

do {
    try VNImageRequestHandler(cgImage: cg, options: [:]).perform([anfrage])
} catch {
    FileHandle.standardError.write("OCR fehlgeschlagen: \(error)\n".data(using: .utf8)!)
    exit(1)
}

struct Stelle: Encodable {
    let text: String
    let x: Double, y: Double, breite: Double, hoehe: Double
    let konfidenz: Double
}

var stellen: [Stelle] = []
for beob in anfrage.results ?? [] {
    guard let kandidat = beob.topCandidates(1).first else { continue }
    let ganz = kandidat.string
    // Ohne Suchwoerter: alles zurueckgeben. Mit: nur die Treffer, und zwar
    // WORTGENAU ueber den Kandidatenbereich -- ein ganzer Zeilenblock waere
    // zu viel geschwaerzt, und zu viel ist hier zwar sicher, aber unlesbar.
    if gesucht.isEmpty {
        let r = beob.boundingBox
        stellen.append(.init(text: ganz, x: r.minX, y: r.minY,
                             breite: r.width, hoehe: r.height,
                             konfidenz: Double(kandidat.confidence)))
        continue
    }
    let klein = ganz.lowercased()
    for wort in gesucht where klein.contains(wort) {
        var rechteck = beob.boundingBox
        // Genauer Bereich des Wortes, wo Vision ihn liefert.
        if let bereich = klein.range(of: wort),
           let genau = try? kandidat.boundingBox(for: bereich.lowerBound..<bereich.upperBound) {
            rechteck = genau.boundingBox
        }
        stellen.append(.init(text: wort, x: rechteck.minX, y: rechteck.minY,
                             breite: rechteck.width, hoehe: rechteck.height,
                             konfidenz: Double(kandidat.confidence)))
    }
}

let aus: [String: Any] = [
    "_hinweis": "Rechtecke in 0..1, Ursprung UNTEN LINKS (Vision). Fuer PDF y spiegeln.",
    "bloecke": (anfrage.results ?? []).count,
    "stellen": stellen.map { ["text": $0.text, "x": $0.x, "y": $0.y,
                              "breite": $0.breite, "hoehe": $0.hoehe,
                              "konfidenz": $0.konfidenz] },
]
let daten = try JSONSerialization.data(withJSONObject: aus, options: [.prettyPrinted, .sortedKeys])
FileHandle.standardOutput.write(daten)
