// Startet berichte/entscheidungen_server.py (Port 8799), erkennt einen
// bereits laufenden Dienst, und macht ein unerwartetes Ende sichtbar --
// nach dem Muster von openlehr/apps/openlehr/macshell/Sources/OpenLehrApp/
// ServiceSupervisor.swift, aber bewusst kleiner:
//
// NICHT uebernommen, mit Grund:
// - .env-Datei einlesen/mergen: brainlehr braucht dafuer heute nichts.
// - Bundle-Resource-Hinweis (openlehr_repo_root.txt) und Volltext-Suche
//   ueber /Volumes: dieses Paket laeuft aus dem Repo heraus (per `swift run`
//   in app/), Hochlaufen per Verzeichnis-Walk reicht.
// - UserDefaults-Cache des Repo-Pfads: gleicher Grund, kein Mehrwert bei
//   einem Repo, das sich nicht bewegt.
//
// UEBERNOMMEN: Prozess mit eigenem Pipe/Log, terminationHandler, SIGTERM vor
// SIGKILL beim Stop, Kandidatenliste statt PATH-Suche fuer den Interpreter.

import Foundation
import Observation
import BrainlehrCore

@MainActor
@Observable
final class DienstAufsicht {
    private(set) var zustand: DienstZustand = .startetGerade
    /// Meldung fuer die Oberflaeche -- niemals Pfad, Port oder Rohfehler.
    private(set) var meldung: String?

    private static let port = 8799
    private static let basisURL = URL(string: "http://127.0.0.1:\(port)/")!

    private var prozess: Process?
    private var pollTimer: Timer?
    private var wurdeAngehalten = false

    func start() {
        wurdeAngehalten = false
        zustand = .startetGerade
        meldung = nil
        Task { await starteWennNoetig() }
        startPolling()
    }

    func stop() {
        wurdeAngehalten = true
        pollTimer?.invalidate()
        pollTimer = nil
        beendeEigenenProzessFallsVorhanden()
        zustand = DienstUebergang.naechsterZustand(aktuell: zustand, erreichbar: false, wurdeAngehalten: true)
    }

    /// Erneuter Versuch nach einem angezeigten Ausfall (Knopf in der Oberflaeche).
    func erneutVersuchen() {
        guard !wurdeAngehalten else { return }
        zustand = .startetGerade
        meldung = nil
        Task { await starteWennNoetig() }
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
        switch zustand {
        case .unerwartetBeendet:
            return "Der Wissensraum ist gerade nicht erreichbar. Mit \u{201E}Erneut versuchen\u{201C} kann er neu gestartet werden."
        default:
            return nil
        }
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

    // MARK: - Start

    private func starteWennNoetig() async {
        if await istErreichbar() {
            // Schon jemand da -- egal wer, nicht doppelt starten.
            zustand = DienstUebergang.naechsterZustand(aktuell: .startetGerade, erreichbar: true, wurdeAngehalten: false)
            return
        }

        guard let wurzel = repoWurzel() else {
            zustand = .unerwartetBeendet
            meldung = "Der Wissensraum konnte nicht gefunden werden."
            return
        }
        guard let python = waehlePython() else {
            zustand = .unerwartetBeendet
            meldung = "Auf diesem Rechner fehlt eine Voraussetzung fuer den Wissensraum."
            return
        }

        let server = wurzel.appendingPathComponent("berichte/entscheidungen_server.py")
        let process = Process()
        process.executableURL = URL(fileURLWithPath: python)
        process.arguments = [server.path, "--port", String(Self.port)]
        process.currentDirectoryURL = wurzel

        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        pipe.fileHandleForReading.readabilityHandler = { handle in
            _ = handle.availableData // Ausgabe wird verworfen -- keine Entwicklerinfo in der App.
        }

        process.terminationHandler = { [weak self] proc in
            Task { @MainActor in
                pipe.fileHandleForReading.readabilityHandler = nil
                guard let self, self.prozess === proc else { return }
                self.prozess = nil
                if !self.wurdeAngehalten {
                    self.zustand = DienstUebergang.naechsterZustand(
                        aktuell: self.zustand, erreichbar: false, wurdeAngehalten: false
                    )
                    self.meldung = self.meldungFuer(self.zustand)
                }
            }
        }

        do {
            try process.run()
            prozess = process
        } catch {
            zustand = .unerwartetBeendet
            meldung = "Der Wissensraum konnte nicht gestartet werden."
            return
        }

        // Kurz abwarten, bis der Dienst antwortet -- hoechstens 5 Sekunden,
        // wie pflege/wissensraum_start.sh es tut.
        for _ in 0..<25 {
            if await istErreichbar() {
                zustand = DienstUebergang.naechsterZustand(aktuell: .startetGerade, erreichbar: true, wurdeAngehalten: false)
                return
            }
            try? await Task.sleep(nanoseconds: 200_000_000)
        }
        // Bleibt .startetGerade -- der naechste Poll-Tick entscheidet weiter.
    }

    private func beendeEigenenProzessFallsVorhanden() {
        guard let process = prozess, process.isRunning else {
            prozess = nil
            return
        }
        process.terminationHandler = nil
        process.terminate()
        let deadline = Date().addingTimeInterval(3.0)
        while process.isRunning && Date() < deadline {
            RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.05))
        }
        if process.isRunning {
            kill(process.processIdentifier, SIGKILL)
        }
        prozess = nil
    }

    // MARK: - Interpreter-Wahl (Faehigkeit statt fester Pfad)

    private func waehlePython() -> String? {
        let kandidaten = [
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3",
        ]
        return PythonAuswahl.waehle(kandidaten: kandidaten) { pfad in
            guard FileManager.default.isExecutableFile(atPath: pfad) else { return false }
            let probe = Process()
            probe.executableURL = URL(fileURLWithPath: pfad)
            probe.arguments = ["-c", "import cryptography"]
            probe.standardOutput = FileHandle.nullDevice
            probe.standardError = FileHandle.nullDevice
            do {
                try probe.run()
                probe.waitUntilExit()
                return probe.terminationStatus == 0
            } catch {
                return false
            }
        }
    }

    // MARK: - Repo-Wurzel finden

    private func repoWurzel() -> URL? {
        if let env = ProcessInfo.processInfo.environment["BRAINLEHR_REPO_ROOT"] {
            let url = URL(fileURLWithPath: env)
            if istRepoWurzel(url) { return url }
        }
        let startpunkte = [
            URL(fileURLWithPath: FileManager.default.currentDirectoryPath),
            Bundle.main.bundleURL.deletingLastPathComponent(),
        ]
        for start in startpunkte {
            if let fund = geheHoch(von: start) {
                return fund
            }
        }
        return nil
    }

    private func geheHoch(von url: URL) -> URL? {
        var current = url.standardizedFileURL
        for _ in 0..<10 {
            if istRepoWurzel(current) { return current }
            let parent = current.deletingLastPathComponent()
            if parent.path == current.path { return nil }
            current = parent
        }
        return nil
    }

    private func istRepoWurzel(_ url: URL) -> Bool {
        let fm = FileManager.default
        let server = url.appendingPathComponent("berichte/entscheidungen_server.py")
        let version = url.appendingPathComponent("VERSION")
        return fm.fileExists(atPath: server.path) && fm.fileExists(atPath: version.path)
    }
}
