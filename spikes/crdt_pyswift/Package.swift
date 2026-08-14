// swift-tools-version:5.9
import PackageDescription
let package = Package(
    name: "Probe",
    platforms: [.macOS(.v12)],
    dependencies: [.package(url: "https://github.com/y-crdt/yswift.git", from: "0.2.0")],
    targets: [.executableTarget(name: "Probe", dependencies: [.product(name: "YSwift", package: "yswift")])]
)
