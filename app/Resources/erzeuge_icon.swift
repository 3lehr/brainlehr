// Erzeugt die PNG-Rohlinge fuer das App-Symbol in allen von macOS erwarteten
// Groessen -- kein Fremdmaterial, keine heruntergeladenen Bilder. Schlichtes
// eigenes Motiv: abgerundetes Quadrat, blauer Verlauf, weisses "b".
//
// Aufruf: xcrun swift Resources/erzeuge_icon.swift <Ziel-Iconset-Ordner>
// app/bauen.sh ruft das bei jedem Bau frisch auf (kein committetes Binaer-PNG).

import AppKit

func zeichneIcon(pixel: Int) -> Data {
    let groesse = CGFloat(pixel)
    guard let bild = NSBitmapImageRep(
        bitmapDataPlanes: nil, pixelsWide: pixel, pixelsHigh: pixel,
        bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
        colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0
    ) else { fatalError("Bitmap konnte nicht angelegt werden") }
    bild.size = NSSize(width: groesse, height: groesse)

    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bild)

    let rand = groesse * 0.06 // sichtbarer Abstand zum Kachelrand, wie macOS es erwartet
    let rechteck = NSRect(x: rand, y: rand, width: groesse - 2 * rand, height: groesse - 2 * rand)
    let radius = rechteck.width * 0.22
    let pfad = NSBezierPath(roundedRect: rechteck, xRadius: radius, yRadius: radius)
    let oben = NSColor(calibratedRed: 0.20, green: 0.47, blue: 0.90, alpha: 1)
    let unten = NSColor(calibratedRed: 0.08, green: 0.22, blue: 0.55, alpha: 1)
    NSGradient(starting: oben, ending: unten)!.draw(in: pfad, angle: -90)

    let schrift = NSFont.systemFont(ofSize: groesse * 0.44, weight: .semibold)
    let text = NSAttributedString(string: "b", attributes: [
        .font: schrift,
        .foregroundColor: NSColor.white,
    ])
    let textGroesse = text.size()
    let punkt = NSPoint(
        x: (groesse - textGroesse.width) / 2,
        y: (groesse - textGroesse.height) / 2 - groesse * 0.02
    )
    text.draw(at: punkt)

    NSGraphicsContext.restoreGraphicsState()

    guard let daten = bild.representation(using: .png, properties: [:]) else {
        fatalError("PNG-Kodierung fehlgeschlagen")
    }
    return daten
}

let argumente = CommandLine.arguments
guard argumente.count == 2 else {
    FileHandle.standardError.write("Nutzung: erzeuge_icon.swift <Ziel-Iconset-Ordner>\n".data(using: .utf8)!)
    exit(1)
}
let ziel = URL(fileURLWithPath: argumente[1])
try FileManager.default.createDirectory(at: ziel, withIntermediateDirectories: true)

let groessen: [(name: String, pixel: Int)] = [
    ("icon_16x16", 16), ("icon_16x16@2x", 32),
    ("icon_32x32", 32), ("icon_32x32@2x", 64),
    ("icon_128x128", 128), ("icon_128x128@2x", 256),
    ("icon_256x256", 256), ("icon_256x256@2x", 512),
    ("icon_512x512", 512), ("icon_512x512@2x", 1024),
]

for eintrag in groessen {
    let daten = zeichneIcon(pixel: eintrag.pixel)
    try daten.write(to: ziel.appendingPathComponent("\(eintrag.name).png"))
}
