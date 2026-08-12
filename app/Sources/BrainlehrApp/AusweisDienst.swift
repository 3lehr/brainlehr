// Ruft pflege/ausweis_start.sh -- Schritt 3 des Plans. kern/ausweis.py und
// kern/geheimnis.py bleiben tabu, diese Datei ruft nur den vorhandenen
// Helfer auf, wie es die AppleScript-Fassung auch tut.
//
// GEHEIMNIS-UEBERGABE: staerker als das AppleScript-Vorbild, nicht nur
// gleichwertig. Dort schreibt `open for access` das Geheimnis in eine
// mktemp-600-Datei, weil `do shell script` kein direktes Pipen von STDIN
// kennt -- die Datei existiert kurz auf der Platte, wird aber in jedem Fall
// geloescht (auch nach Fehler). Foundation.Process kann STDIN direkt aus dem
// Prozessspeicher fuettern: Pipe().fileHandleForWriting.write(...). Damit
// beruehrt das Geheimnis WEDER die Befehlszeile (wie im Auftrag verlangt)
// NOCH je die Platte -- eine Verbesserung gegenueber der Vorlage, keine
// Abweichung von ihrer Auflage.

import Foundation
import BrainlehrCore

struct AusweisDienstFehler: Error, LocalizedError {
    let nachricht: String
    var errorDescription: String? { nachricht }
}

enum AusweisDienst {
    /// Repo-Wurzel wie DienstAufsicht sie findet -- ein Ort der Wahrheit
    /// (BrainlehrCore.RepoWurzel), zwei Aufrufer.
    private static func repoWurzel() throws -> URL {
        guard let url = DienstAufsicht.findeRepoWurzel(zusatzStart: Bundle.main.bundleURL.deletingLastPathComponent()) else {
            throw AusweisDienstFehler(nachricht: "Der Wissensraum konnte nicht gefunden werden.")
        }
        return url
    }

    /// Fuehrt pflege/ausweis_start.sh mit `argumente` aus. `geheimnis` geht,
    /// falls gesetzt, ueber eine In-Memory-Pipe an STDIN -- nie ueber argv.
    /// Wirft `AusweisDienstFehler` mit dem Wortlaut aus `{"fehler": "..."}`,
    /// wenn der Helfer einen kennt; sonst mit einem verstaendlichen
    /// Ersatztext (kein Rohfehler, keine Stapelspur in der Oberflaeche).
    private static func rufeAuf(_ argumente: [String], geheimnis: String?) async throws -> Data {
        let wurzel = try repoWurzel()
        let skript = wurzel.appendingPathComponent("pflege/ausweis_start.sh")
        guard FileManager.default.isExecutableFile(atPath: skript.path) else {
            throw AusweisDienstFehler(nachricht: "Der Ausweis-Helfer wurde nicht gefunden.")
        }

        let process = Process()
        process.executableURL = skript
        process.arguments = argumente
        process.currentDirectoryURL = wurzel

        let stdinPipe = Pipe()
        let stdoutPipe = Pipe()
        process.standardOutput = stdoutPipe
        process.standardError = stdoutPipe
        process.standardInput = geheimnis == nil ? FileHandle.nullDevice : stdinPipe

        do {
            try process.run()
        } catch {
            throw AusweisDienstFehler(nachricht: "Der Ausweis-Helfer konnte nicht gestartet werden.")
        }

        if let geheimnis, let daten = geheimnis.data(using: .utf8) {
            stdinPipe.fileHandleForWriting.write(daten)
        }
        try? stdinPipe.fileHandleForWriting.close()

        let ausgabe = stdoutPipe.fileHandleForReading.readDataToEndOfFile()
        process.waitUntilExit()

        if let fehler = gefundenerFehler(in: ausgabe) {
            throw AusweisDienstFehler(nachricht: fehler)
        }
        guard process.terminationStatus == 0 else {
            throw AusweisDienstFehler(nachricht: "Der Ausweis-Helfer hat mit einem unerwarteten Fehler abgebrochen.")
        }
        return ausgabe
    }

    static func liste() async throws -> AusweisListeAntwort {
        let daten = try await rufeAuf(argumenteListe, geheimnis: nil)
        do {
            return try JSONDecoder().decode(AusweisListeAntwort.self, from: daten)
        } catch {
            throw AusweisDienstFehler(nachricht: "Die Antwort des Ausweis-Helfers konnte nicht gelesen werden.")
        }
    }

    static func anlegen(name: String, art: AusweisArt, rollen: [AusweisRolle], geheimnis: String) async throws -> AusweisAnlegenAntwort {
        let daten = try await rufeAuf(argumenteAnlegen(name: name, art: art, rollen: rollen), geheimnis: geheimnis)
        do {
            return try JSONDecoder().decode(AusweisAnlegenAntwort.self, from: daten)
        } catch {
            throw AusweisDienstFehler(nachricht: "Die Antwort des Ausweis-Helfers konnte nicht gelesen werden.")
        }
    }

    static func einladen(name: String, fuer: String, rollen: [AusweisRolle], geheimnis: String) async throws -> AusweisEinladenAntwort {
        let daten = try await rufeAuf(argumenteEinladen(name: name, fuer: fuer, rollen: rollen), geheimnis: geheimnis)
        do {
            return try JSONDecoder().decode(AusweisEinladenAntwort.self, from: daten)
        } catch {
            throw AusweisDienstFehler(nachricht: "Die Antwort des Ausweis-Helfers konnte nicht gelesen werden.")
        }
    }
}
