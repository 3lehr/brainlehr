// Swift-Haelfte der Rot-Probe zu ADR-010. Gegenstueck: ../../probe.py
//
// Prueft drei Dinge und nur diese: Liest die native Seite einen Stand, den
// Python geschrieben hat? Ist das Anwenden idempotent (zweimal darf nichts
// verdoppeln)? Und was kommt zurueck?

import Foundation
import YSwift

let hier = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let doc = YDocument()
let text = doc.getOrCreateText(named: "t")

let ausPython = [UInt8](try! Data(contentsOf: hier.appendingPathComponent("py_update.bin")))
let zustandsvektor = [UInt8](try! Data(contentsOf: hier.appendingPathComponent("py_sv.bin")))

doc.transactSync { txn in
    try! txn.transactionApplyUpdate(update: ausPython)
    print("Swift liest aus Python-Update:", text.getString(in: txn))

    // Negativfall: dasselbe Update ein zweites Mal darf den Text nicht aendern.
    try! txn.transactionApplyUpdate(update: ausPython)
    print("nach zweimal anwenden:", text.getString(in: txn))

    text.insert("[Swift] ", at: 0, in: txn)
    print("nach Swift-Einfuegung:", text.getString(in: txn))
}

let gegenVektor = doc.transactSync { txn in doc.diff(txn: txn, from: zustandsvektor) }
let gegenLeer = doc.transactSync { txn in doc.diff(txn: txn, from: [0]) }
print("diff gegen py-SV:", gegenVektor.count, "bytes | diff gegen leer:", gegenLeer.count, "bytes")

try! Data(gegenVektor).write(to: hier.appendingPathComponent("swift_update.bin"))
