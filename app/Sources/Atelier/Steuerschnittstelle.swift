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
        FileManager.default.temporaryDirectory.appendingPathComponent("atelier-steuerport")
    }

    /// Hat die Anwendung ein Hauptfenster? Eine Eigenschaft der ANWENDUNG --
    /// ausdruecklich keine Aussage darueber, ob gerade jemand hinsieht.
    ///
    /// DREI ANLAEUFE, drei Messfehler, und der dritte ist der lehrreiche:
    ///
    /// 1. `NSApp.windows.filter(\.isVisible).count` meldete 1, waehrend nichts
    ///    zu sehen war. SwiftUI haelt Hilfsfenster -- diese Anwendung hat stets
    ///    FUENF Fenster, davon VIER ohne Namen. `isVisible` ist eine Aussage
    ///    ueber ein AppKit-Objekt, nicht ueber ein Fenster im Wortsinn.
    ///
    /// 2. `CGWindowList` mit `.optionOnScreenOnly` meldete daraufhin mal 0, mal
    ///    1, scheinbar unbestaendig -- und ich habe daraus zweimal einen Fehler
    ///    in der App geschlossen, den es nicht gab.
    ///
    /// 3. Die Erklaerung kam vom Betreiber, fuer den ich blind war: er wechselte
    ///    waehrend der Messung Fenster und Schreibtisch. `.optionOnScreenOnly`
    ///    zaehlt nur, was auf dem gerade sichtbaren Schreibtisch liegt.
    ///
    /// DARAUS DIE REGEL, die den Ausschlag gibt: Ein Pruefkanal, dessen Wert
    /// davon abhaengt, was der MENSCH gerade tut, ist kein Pruefkanal. Er ist
    /// nicht wiederholbar, nicht vergleichbar, und er verwandelt einen
    /// Schreibtischwechsel in einen Befund. Deshalb misst diese Schnittstelle
    /// den Zustand der ANWENDUNG und nie den Zustand des Bildschirms -- das war
    /// von Anfang an ihr Zweck, und ich hatte ihn selbst unterlaufen.
    ///
    /// `canBecomeMain` trennt die echten Fenster von SwiftUIs Hilfsfenstern:
    /// nur ein Hauptfenster kann der Ort sein, an dem jemand arbeitet.
    static func hauptfenster() -> Int {
        NSApp.windows.filter { $0.canBecomeMain && $0.isVisible }.count
    }

    private let wahl: Ansichtswahl
    private let dokument: Dokumentsitzung
    private let aufsicht: DienstAufsicht
    private var lauscher: NWListener?

    init(wahl: Ansichtswahl, aufsicht: DienstAufsicht, dokument: Dokumentsitzung) {
        self.wahl = wahl
        self.dokument = dokument
        self.aufsicht = aufsicht
    }

    func start() {
        // Abschaltbar, und das ist keine Bequemlichkeit: Eine Schnittstelle,
        // die sich nicht abschalten laesst, kann man nicht als Ursache
        // ausschliessen. Am 2026-08-14 zeigte die App ein unbestaendiges
        // Fensterverhalten (mal 0, mal 1 Fenster beim Start); ohne diesen
        // Schalter ist nicht entscheidbar, ob die Schnittstelle daran beteiligt
        // ist -- und ein Verdacht ohne Gegenprobe bleibt ein Verdacht.
        guard ProcessInfo.processInfo.environment["BRAINLEHR_STEUERUNG"] != "aus" else {
            FileHandle.standardError.write(Data("Steuerschnittstelle: per BRAINLEHR_STEUERUNG=aus abgeschaltet.\n".utf8))
            return
        }

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
        let blicke = WissensraumBlick.allCases.map(\.kennung)
        switch Steuerdeutung.deute(methode: zerlegt.methode, pfad: zerlegt.pfad,
                                   koerper: koerper, erlaubteAnsichten: ansichten,
                                   erlaubteBlicke: blicke) {
        case .failure(let ablehnung):
            return ablehnung
        case .success(let befehl):
            return fuehreAus(befehl, ansichten: ansichten)
        }
    }

    /// Der erreichte Zustand -- eine Stelle, damit /zustand, /ansicht und
    /// /blick nicht dreimal dasselbe zusammenbauen und auseinanderlaufen.
    private func zustandsantwort(ansichten: [String]) -> Steuerantwort {
        Steuerantwort(code: 200, koerper: Steuerdeutung.zustandJSON(
            ansicht: wahl.aktuell.rawValue,
            dienst: String(describing: aufsicht.zustand),
            pid: ProcessInfo.processInfo.processIdentifier,
            fassung: (Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String) ?? "unbekannt",
            fenster: Self.hauptfenster(),
            ansichten: ansichten,
            blick: wahl.blick.kennung,
            blicke: WissensraumBlick.allCases.map(\.kennung),
            dokumentlage: dokument.lage.satz,
            dokumenttext: dokument.text))
    }

    private func fuehreAus(_ befehl: Steuerbefehl, ansichten: [String]) -> Steuerantwort {
        switch befehl {
        case .gesundheit:
            return Steuerantwort(code: 200, koerper: #"{"lebt":true}"#)

        case .zustand:
            return zustandsantwort(ansichten: ansichten)

        case .blickWaehlen(let name):
            guard let blick = WissensraumBlick.allCases.first(where: { $0.kennung == name }) else {
                return Steuerantwort(code: 500, koerper:
                    #"{"fehler":"Blick '\#(name)' ist erlaubt, aber unbekannt.","hinweis":"Kern und Oberflaeche laufen auseinander."}"#)
            }
            wahl.blick = blick
            return zustandsantwort(ansichten: ansichten)

        case .dokumentVerbinden(let adresse, let geheimnis):
            guard let url = URL(string: adresse), url.scheme?.hasPrefix("ws") == true else {
                return Steuerantwort(code: 400, koerper:
                    #"{"fehler":"Adresse '\#(adresse)' ist keine ws://-Adresse.","hinweis":"Erwartet: ws://host:port"}"#)
            }
            dokument.verbinde(zu: url, geheimnis: geheimnis.isEmpty ? nil : geheimnis)
            return zustandsantwort(ansichten: ansichten)

        case .dokumentTrennen:
            dokument.trenne()
            return zustandsantwort(ansichten: ansichten)

        case .dokumentEinfuegen(let text, let bei):
            dokument.fuegeEin(text, bei: bei)
            return zustandsantwort(ansichten: ansichten)

        case .dokumentSchreiben(let text):
            dokument.text = text
            dokument.schreibe(text)
            return zustandsantwort(ansichten: ansichten)

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
            return zustandsantwort(ansichten: ansichten)
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
