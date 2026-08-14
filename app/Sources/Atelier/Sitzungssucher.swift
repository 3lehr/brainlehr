// Findet alle Sitzungen und macht sie unterscheidbar.
//
// ANLASS (Betreiber, 2026-08-13): "sollte ich in der app oberflaeche nicht
// einstellen koennen welcher chat gerade der spannende ist? weil ich habe oft
// mehrere chats gleichzeitig auf"
//
// GEMESSEN am selben Tag: 3467 Sitzungsdateien insgesamt, 37 davon aus den
// letzten drei Stunden -- und in EINEM Projektordner schrieben zwei Sitzungen
// gleichzeitig. Die urspruengliche Wahl "die zuletzt geaenderte Datei" haette
// zwischen beiden hin und her gesprungen, ohne dass irgendetwas darauf
// hinweist.
//
// WAS HIER BEWUSST NICHT PASSIERT: keine automatische Vorauswahl der
// juengsten Sitzung. Welcher Chat zaehlt, weiss nur der Mensch -- und eine
// Anzeige, die es errät und dabei falsch liegt, ist schlimmer als eine, die
// fragt. Die Sortierung ist ein Vorschlag, kein Urteil.

import BrainlehrCore
import Foundation

enum Sitzungssucher {
    /// Wie weit zurueck gesucht wird. Aeltere Sitzungen sind Archiv, nicht
    /// "gerade offen" -- und 3467 Dateien in eine Auswahlliste zu schuetten
    /// waere dasselbe wie keine Auswahl.
    static let hoechstalterStunden: Double = 24

    /// Nur die letzten Kilobytes lesen. Die groesste gemessene Sitzungsdatei
    /// hat 32 MB; sie ganz zu lesen, nur um einen Titel zu finden, waere bei
    /// jedem Oeffnen der Auswahl spuerbar. Titel und Eingaben wiederholen
    /// sich im Strom, der juengste steht ohnehin hinten.
    static let leseFenster = 512 * 1024

    static func alle(jetzt: Date = Date()) -> [Sitzungskennung] {
        let fm = FileManager.default
        let wurzel = (NSHomeDirectory() as NSString).appendingPathComponent(".claude/projects")
        guard let ordner = try? fm.contentsOfDirectory(atPath: wurzel) else { return [] }

        var gefunden: [Sitzungskennung] = []
        for o in ordner {
            // Unteragenten sind keine Chats -- sie haben keinen Menschen am
            // anderen Ende und wuerden die Auswahl zuschuetten (33 von 37
            // aktiven Dateien waren gemessen Unteragenten).
            guard o != "subagents" else { continue }
            let pfadOrdner = "\(wurzel)/\(o)"
            guard let dateien = try? fm.contentsOfDirectory(atPath: pfadOrdner) else { continue }
            for d in dateien where d.hasSuffix(".jsonl") {
                let pfad = "\(pfadOrdner)/\(d)"
                guard let attr = try? fm.attributesOfItem(atPath: pfad),
                      let geaendert = attr[.modificationDate] as? Date,
                      jetzt.timeIntervalSince(geaendert) < hoechstalterStunden * 3600
                else { continue }
                let (titel, eingabe) = kopfDaten(pfad)
                gefunden.append(Sitzungskennung(
                    pfad: pfad, titel: titel, letzteEingabe: eingabe,
                    zuletztAktiv: geaendert, projekt: Sitzungswahl.projektname(o)))
            }
        }
        return Sitzungswahl.sortiert(gefunden)
    }

    /// Titel und juengste echte Eingabe aus dem Ende der Datei.
    private static func kopfDaten(_ pfad: String) -> (String, String) {
        guard let h = FileHandle(forReadingAtPath: pfad) else { return ("", "") }
        defer { try? h.close() }
        let groesse = (try? h.seekToEnd()) ?? 0
        let ab = groesse > UInt64(leseFenster) ? groesse - UInt64(leseFenster) : 0
        try? h.seek(toOffset: ab)
        guard let daten = try? h.readToEnd(),
              let text = String(data: daten, encoding: .utf8) else { return ("", "") }

        var titel = "", eingabe = ""
        for zeile in text.split(separator: "\n") {
            let (t, e) = Sitzungswahl.deute(String(zeile))
            if let t { titel = t }
            if let e { eingabe = e }
        }
        return (titel, eingabe)
    }
}
