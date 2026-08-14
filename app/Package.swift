// swift-tools-version: 5.10
//
// Brainlehr macOS-App — Schritt 1 des Plans (docs/PLAN_MACAPP_2026-08-12.md):
// Geruest und Dienstaufsicht. Kein Fremdpaket: Foundation/SwiftUI/AppKit
// reichen fuer Fenster, Seitenleiste und Prozessaufsicht.

import PackageDescription

let package = Package(
    name: "Atelier",
    defaultLocalization: "de",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "Atelier", targets: ["Atelier"]),
    ],
    // Erste Fremdabhaengigkeit ueberhaupt. Begruendung in ADR-010: yswift ist
    // das Gegenstueck zu pycrdt im Dienst, gemessen ueber die Sprachgrenze.
    // Version fest, nicht "from" -- eine Bibliothek mit ueber ein Jahr altem
    // letztem PR soll sich nicht unbemerkt bewegen (Spike 2 in ADR-010).
    dependencies: [
        .package(url: "https://github.com/y-crdt/yswift.git", exact: "0.2.1"),
    ],
    targets: [
        .executableTarget(
            name: "Atelier",
            dependencies: ["BrainlehrCore", .product(name: "YSwift", package: "yswift")],
            path: "Sources/Atelier"
        ),
        .target(
            name: "BrainlehrCore",
            dependencies: [],
            path: "Sources/BrainlehrCore"
        ),
        .testTarget(
            name: "BrainlehrCoreTests",
            dependencies: ["BrainlehrCore"],
            path: "Tests/BrainlehrCoreTests"
        ),
    ]
)
