// swift-tools-version:5.9
// Wegwerf-Spike zur Frage: laedt yswift (Yjs-Familie) auch signiert mit
// com.apple.security.app-sandbox=true? Siehe spikes/crdt_sandbox_probe/README-BEFUND.txt
import PackageDescription
let package = Package(
    name: "SandboxProbe",
    platforms: [.macOS(.v12)],
    dependencies: [.package(url: "https://github.com/y-crdt/yswift.git", from: "0.2.0")],
    targets: [.executableTarget(name: "SandboxProbe", dependencies: [.product(name: "YSwift", package: "yswift")])]
)
