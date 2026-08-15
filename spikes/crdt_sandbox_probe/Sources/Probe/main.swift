import Foundation
import YSwift

let doc = YDocument()
let text = doc.getOrCreateText(named: "t")
doc.transactSync { txn in
    text.insert("Hallo Sandbox", at: 0, in: txn)
}
let ergebnis = doc.transactSync { txn in text.getString(in: txn) }
print("OK:\(ergebnis)")

// Zusatzprobe: schreibt die Sandbox wirklich, oder wurde das Entitlement nur
// angenommen, ohne zu wirken? Ein Schreibversuch ausserhalb des Containers
// (Home-Verzeichnis direkt) MUSS scheitern, wenn die Sandbox aktiv ist.
let verbotenesZiel = FileManager.default.homeDirectoryForCurrentUser
    .appendingPathComponent("brainlehr_sandbox_probe_verboten.txt")
do {
    try "sollte nicht klappen".write(to: verbotenesZiel, atomically: true, encoding: .utf8)
    print("SANDBOX_INAKTIV: Schreiben ausserhalb Container gelang")
} catch {
    print("SANDBOX_AKTIV: Schreiben ausserhalb Container verweigert: \(error)")
}
