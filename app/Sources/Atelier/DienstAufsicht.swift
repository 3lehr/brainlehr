// Der Dienst laeuft eigenstaendig ausserhalb der App (siehe dienst/, launchd)
// -- diese Klasse startet ihn NICHT mehr, sie stellt nur fest, ob er
// erreichbar ist, und sagt der Oberflaeche in Nutzersprache, was zu tun ist,
// wenn nicht.
//
// Vorherige Fassung startete den Dienst als Kindprozess (Process, Pipe,
// Interpreter-Suche) -- das verhinderte eine Sandbox und machte den Dienst
// zum Besitz des angemeldeten Benutzers. Entfernt, nicht auskommentiert.

import Foundation
import Observation
import BrainlehrCore

@MainActor
@Observable
final class DienstAufsicht {
    private(set) var zustand: DienstZustand = .startetGerade
    /// Meldung fuer die Oberflaeche -- niemals Pfad, Port oder Rohfehler.
    private(set) var meldung: String?

    static let port = 8799
    static let basisURL = URL(string: "http://127.0.0.1:\(port)/")!

    private var pollTimer: Timer?
    private var wurdeAngehalten = false

    func start() {
        wurdeAngehalten = false
        zustand = .startetGerade
        meldung = nil
        Task { await pruefeBeimStart() }
        startPolling()
    }

    func stop() {
        wurdeAngehalten = true
        pollTimer?.invalidate()
        pollTimer = nil
        zustand = DienstUebergang.naechsterZustand(aktuell: zustand, erreichbar: false, wurdeAngehalten: true)
    }

    /// Erneuter Versuch nach einem angezeigten Ausfall (Knopf in der Oberflaeche).
    func erneutVersuchen() {
        guard !wurdeAngehalten else { return }
        zustand = .startetGerade
        meldung = nil
        Task { await pruefeBeimStart() }
    }

    // MARK: - Erreichbarkeit

    private func startPolling() {
        pollTimer?.invalidate()
        let timer = Timer(timeInterval: 2.0, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.pruefeUndAktualisiere() }
        }
        RunLoop.main.add(timer, forMode: .common)
        pollTimer = timer
    }

    private func pruefeUndAktualisiere() {
        Task {
            let erreichbar = await istErreichbar()
            await MainActor.run {
                let neu = DienstUebergang.naechsterZustand(
                    aktuell: zustand, erreichbar: erreichbar, wurdeAngehalten: wurdeAngehalten
                )
                zustand = neu
                meldung = meldungFuer(neu)
            }
        }
    }

    private func meldungFuer(_ zustand: DienstZustand) -> String? {
        DienstMeldung.fuer(zustand)
    }

    private func istErreichbar() async -> Bool {
        // GET, nicht HEAD: der Dienst (BaseHTTPServer) beantwortet HEAD mit
        // 501 Unsupported method -- das sah wie ein Ausfall aus, obwohl der
        // Dienst lief. Rot-Probe dieses Fehlers: siehe Testlauf im Auftrag.
        var request = URLRequest(url: Self.basisURL)
        request.timeoutInterval = 1.5
        request.httpMethod = "GET"
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse else { return false }
            return (200..<500).contains(http.statusCode)
        } catch {
            return false
        }
    }

    // MARK: - Start (nur noch Erreichbarkeitspruefung, kein Prozessstart)

    private func pruefeBeimStart() async {
        if await istErreichbar() {
            zustand = .laeuft
        } else {
            zustand = .unerwartetBeendet
            meldung = DienstMeldung.nichtErreichbar
        }
    }

    // MARK: - Repo-Wurzel finden

    /// Sucht die Repo-Wurzel, erkannt an `berichte/entscheidungen_server.py`
    /// und `VERSION` -- geteilt mit AusweisDienst.swift (Aufstiegslogik
    /// selbst liegt in BrainlehrCore.RepoWurzel, pruefbar ohne Dateisystem).
    nonisolated static func findeRepoWurzel(zusatzStart: URL) -> URL? {
        if let env = ProcessInfo.processInfo.environment["BRAINLEHR_REPO_ROOT"] {
            let url = URL(fileURLWithPath: env)
            if istRepoWurzel(url) { return url }
        }
        let startpunkte = [
            FileManager.default.currentDirectoryPath,
            zusatzStart.standardizedFileURL.path,
        ]
        for start in startpunkte {
            if let fund = RepoWurzel.suche(ab: start, istWurzel: { istRepoWurzel(URL(fileURLWithPath: $0)) }) {
                return URL(fileURLWithPath: fund)
            }
        }
        return nil
    }

    private nonisolated static func istRepoWurzel(_ url: URL) -> Bool {
        let fm = FileManager.default
        let server = url.appendingPathComponent("berichte/entscheidungen_server.py")
        let version = url.appendingPathComponent("VERSION")
        return fm.fileExists(atPath: server.path) && fm.fileExists(atPath: version.path)
    }
}
