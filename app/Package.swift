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
    targets: [
        .executableTarget(
            name: "Atelier",
            dependencies: ["BrainlehrCore"],
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
