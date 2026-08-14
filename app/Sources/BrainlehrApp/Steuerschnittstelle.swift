// Lokale Steuerschnittstelle -- NUR im Debug-Build.
//
// ANLASS: Hausregel H6 verlangt fuer native Anwendungen "eine debug-only lokale
// Control-API fuer Kernaktionen + State-Abfrage vorsehen, statt sich bei
// Verifikation auf UI-Automatisierung zu verlassen". Begruendung dort:
// robuster gegen Aenderungen, pro Aufruf guenstiger, per curl statt per
// Bildschirmabzug pruefbar.
//
// Sie ergaenzt app/werkzeuge/ax_baum.swift, sie ersetzt es nicht: der Baum
// sagt, WAS auf dem Schirm steht, diese Schnittstelle sagt, in welchem ZUSTAND
// die App ist. Layout und Aussehen bleiben Sache des Baums.
//
// DREI AUFLAGEN, jede aus einem bezahlten Fehler:
//
// 1. NUR DEBUG. Die ganze Datei liegt in `#if DEBUG`. Im Auslieferungsbau
//    existiert kein Port, kein Lauscher, kein Symbol.
//
// 2. NUR 127.0.0.1. Ausdruecklich an die Rueckschleife gebunden, nicht an alle
//    Schnittstellen -- eine Steuerschnittstelle im Netz waere eine Fernsteuerung.
//
// 3. DER PORT WIRD NICHT GERATEN, SONDERN GEMELDET. L-37117d: zwei Prueftische
//    stritten sich still um einen fest verdrahteten Port, und das Symptom sah
//    aus wie eine tote App -- kommentarlos leere Antwort, kein Fehler. Deshalb
//    hier: Wunschport aus der Umgebung, bei Belegung weicht das System selbst
//    aus (Port 0), und der TATSAECHLICH gebundene Port wird in eine Datei
//    geschrieben und auf die Standardausgabe gemeldet. Wer sie liest, raet nie.

#if DEBUG

import AppKit
import Foundation
import Network
import BrainlehrCore

@MainActor
final class Steuerschnittstelle {
    /// Wo der tatsaechlich gebundene Port steht. Bewusst im Temp-Verzeichnis:
    /// eine Laufzeitangabe, die einen Neustart nicht ueberleben SOLL.
    static var portDatei: URL {
        FileManager.default.temporaryDirectory.appendingPathComponent("brainlehr-steuerport")
    }

    /// Wie viele Fenster dieser Anwendung TATSAECHLICH auf dem Schirm liegen.
    ///
    /// GEMESSEN 2026-08-14, und der Umweg ist bezahlt: Der erste Versuch nahm
    /// `NSApp.windows.filter(\.isVisible).count` und meldete 1, waehrend zwei
    /// unabhaengige Kanaele -- der Bedienungshilfen-Baum und CGWindowList --
    /// uebereinstimmend 0 sagten. `isVisible` ist eine Aussage ueber den
    /// AppKit-Zustand eines Fensterobjekts, nicht darueber, ob ein Mensch es
    /// sieht. Ein Statusfeld, das gegen die Wirklichkeit 1 meldet, ist genau
    /// die Unehrlichkeit, gegen die es eingebaut wurde.
    ///
    /// CGWindowList mit `.optionOnScreenOnly` ist dieselbe Quelle, aus der das
    /// System seine Fensterliste speist -- damit misst die Schnittstelle das,
    /// was der Mensch sieht, und nicht das, was die App glaubt.
    static func fensterAufDemSchirm() -> Int {
        let eigen = ProcessInfo.processInfo.processIdentifier
        guard let liste = CGWindowListCopyWindowInfo(
            [.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]]
        else { return 0 }
        return liste.filter {
            ($0[kCGWindowOwnerPID as String] as? Int32) == eigen
            // Schicht 0 ist die gewoehnliche Fensterschicht. Alles darueber
            // sind Einblendungen des Systems, die niemand als "die App ist
            // offen" verstehen wuerde.
            && (($0[kCGWindowLayer as String] as? Int) ?? -1) == 0
        }.count
    }

    private let wahl: Ansichtswahl
    private let aufsicht: DienstAufsicht
    private var lauscher: NWListener?

    init(wahl: Ansichtswahl, aufsicht: DienstAufsicht) {
        self.wahl = wahl
        self.aufsicht = aufsicht
    }

    func start() {
        // Wunschport, aber kein Zwang: ist er belegt, waehlt das System einen
        // freien (Port 0). Lieber ein anderer Port als ein stiller Streit.
        let wunsch = ProcessInfo.processInfo.environment["BRAINLEHR_STEUERPORT"].flatMap { UInt16($0) } ?? 4599

        for kandidat in [wunsch, 0] as [UInt16] {
            do {
                let parameter = NWParameters.tcp
                parameter.requiredLocalEndpoint = NWEndpoint.hostPort(host: .ipv4(.loopback),
                                                                     port: NWEndpoint.Port(rawValue: kandidat)!)
                let l = try NWListener(using: parameter)
                l.newConnectionHandler = { [weak self] verbindung in
                    verbindung.start(queue: .main)
                    Task { @MainActor in self?.bediene(verbindung) }
                }
                l.stateUpdateHandler = { [weak self] zustand in
                    guard case .ready = zustand else { return }
                    Task { @MainActor in self?.meldePort() }
                }
                l.start(queue: .main)
                lauscher = l
                return
            } catch {
                FileHandle.standardError.write(Data(
                    "Steuerschnittstelle: Port \(kandidat) nicht bindbar (\(error)), weiche aus.\n".utf8))
            }
        }
        FileHandle.standardError.write(Data("Steuerschnittstelle: kein Port bindbar, bleibt AUS.\n".utf8))
    }

    func stop() {
        lauscher?.cancel()
        lauscher = nil
        try? FileManager.default.removeItem(at: Self.portDatei)
    }

    private func meldePort() {
        guard let port = lauscher?.port?.rawValue else { return }
        try? String(port).write(to: Self.portDatei, atomically: true, encoding: .utf8)
        print("Steuerschnittstelle: http://127.0.0.1:\(port) — Port auch in \(Self.portDatei.path)")
    }

    // ── Eine Anfrage bedienen ────────────────────────────────────────────

    private func bediene(_ verbindung: NWConnection) {
        verbindung.receive(minimumIncompleteLength: 1, maximumLength: 64 * 1024) { daten, _, _, _ in
            let roh = daten.flatMap { String(data: $0, encoding: .utf8) } ?? ""
            Task { @MainActor in
                let antwort = self.beantworte(roh)
                self.sende(antwort, ueber: verbindung)
            }
        }
    }

    /// Ganze Anfrage rein, fertige Antwort raus. Kein Netzwerk darin -- der
    /// entscheidende Teil steckt in BrainlehrCore und ist dort getestet.
    private func beantworte(_ roh: String) -> Steuerantwort {
        let teile = roh.components(separatedBy: "\r\n\r\n")
        let kopf = teile.first ?? ""
        let koerper = teile.count > 1 ? teile[1] : ""

        guard let erste = kopf.split(separator: "\r\n").first.map(String.init),
              let zerlegt = Steuerdeutung.zerlegeAnfragezeile(erste)
        else {
            return Steuerantwort(code: 400,
                                 koerper: #"{"fehler":"Unlesbare Anfragezeile.","hinweis":"Erwartet: METHODE /pfad HTTP/1.1"}"#)
        }

        let ansichten = SeitenleistenEintrag.allCases.map(\.rawValue)
        switch Steuerdeutung.deute(methode: zerlegt.methode, pfad: zerlegt.pfad,
                                   koerper: koerper, erlaubteAnsichten: ansichten) {
        case .failure(let ablehnung):
            return ablehnung
        case .success(let befehl):
            return fuehreAus(befehl, ansichten: ansichten)
        }
    }

    private func fuehreAus(_ befehl: Steuerbefehl, ansichten: [String]) -> Steuerantwort {
        switch befehl {
        case .gesundheit:
            return Steuerantwort(code: 200, koerper: #"{"lebt":true}"#)

        case .zustand:
            return Steuerantwort(code: 200, koerper: Steuerdeutung.zustandJSON(
                ansicht: wahl.aktuell.rawValue,
                dienst: String(describing: aufsicht.zustand),
                pid: ProcessInfo.processInfo.processIdentifier,
                fassung: (Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String) ?? "unbekannt",
                fenster: Self.fensterAufDemSchirm(),
                ansichten: ansichten))

        case .ansichtWaehlen(let name):
            guard let eintrag = SeitenleistenEintrag(rawValue: name) else {
                // Kann nur eintreten, wenn Kern und Oberflaeche auseinanderlaufen --
                // dann ist Schweigen das Schlimmste, was passieren kann.
                return Steuerantwort(code: 500, koerper:
                    #"{"fehler":"Ansicht '\#(name)' ist erlaubt, aber unbekannt.","hinweis":"Kern und Seitenleiste laufen auseinander."}"#)
            }
            wahl.aktuell = eintrag
            // Den ERREICHTEN Zustand zurueckgeben, nie ein nacktes "ok":
            // sonst ist eine wirkungslose Aktion von einer wirksamen nicht zu
            // unterscheiden.
            return Steuerantwort(code: 200, koerper: Steuerdeutung.zustandJSON(
                ansicht: wahl.aktuell.rawValue,
                dienst: String(describing: aufsicht.zustand),
                pid: ProcessInfo.processInfo.processIdentifier,
                fassung: (Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String) ?? "unbekannt",
                fenster: Self.fensterAufDemSchirm(),
                ansichten: ansichten))
        }
    }

    private func sende(_ antwort: Steuerantwort, ueber verbindung: NWConnection) {
        let rumpf = Data(antwort.koerper.utf8)
        let kopf = """
        HTTP/1.1 \(antwort.code)\r
        Content-Type: application/json; charset=utf-8\r
        Content-Length: \(rumpf.count)\r
        Connection: close\r
        \r

        """
        verbindung.send(content: Data(kopf.utf8) + rumpf,
                        completion: .contentProcessed { _ in verbindung.cancel() })
    }
}

#endif
