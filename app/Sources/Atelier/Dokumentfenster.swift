// Das Dokumentfenster -- Mensch und Modell am selben Dokument (F5, ADR-010).
//
// Betreiberziel vom 2026-08-14: links das fertige Dokument, live bearbeitet,
// mehrere Menschen UND die KI gleichzeitig, Zeichen fuer Zeichen.
//
// WAS HIER LAEUFT UND WAS NICHT:
//   - Der Text lebt im CRDT (yswift), nicht in dieser Ansicht. Was auf dem
//     Bildschirm steht, ist eine Abbildung davon -- nie die Quelle.
//   - Die Teilnehmerkennung kommt vom DIENST und wird trotzdem geprueft
//     (Dokumentprotokoll). Ein Klient, der sie nur voraussetzt, merkt den Tag
//     nicht, an dem der Dienst sie anders vergibt: der Text verdoppelt sich
//     dann STILL (ADR-010, `L-44dc9f`).
//   - Beim Tippen wird nicht der ganze Text ersetzt, sondern die kleinste
//     Aenderung gebildet (BrainlehrCore/Textabgleich). Wer den ganzen Text
//     schreibt, loescht die Aenderung des anderen mit -- aus "beide tippen im
//     selben Satz" wird "der Schnellere gewinnt".
//
// WARUM URLSessionWebSocketTask und keine Bibliothek: Foundation kann es. Eine
// Abhaengigkeit fuer eine Verbindung, die im eigenen Netz laeuft, waere Vorbau.
//
// NOCH NICHT DRIN, bewusst: die Anmerkungsspalte. Ihre Daten stehen bereits
// (kern/dokument.py, F4) -- die Ansicht dazu ist ein eigener Schritt, und ein
// halb gebautes Bedienfeld ist schlimmer als keines.

import BrainlehrCore
import Foundation
import SwiftUI
import YSwift

@MainActor
final class Dokumentsitzung: ObservableObject {

    enum Lage: Equatable {
        case getrennt
        case verbindet
        case verbunden(kennung: UInt64)
        case fehler(String)

        /// Was ein Mensch liest. Kein Dateiname, keine Kennung, kein Rohfehler --
        /// er soll seine Lage erkennen, nicht unseren Quelltext.
        var satz: String {
            switch self {
            case .getrennt: return "Nicht verbunden"
            case .verbindet: return "Verbindet …"
            case .verbunden: return "Verbunden"
            case .fehler(let grund): return grund
            }
        }
    }

    @Published private(set) var lage: Lage = .getrennt
    /// Der Text, wie ihn das Fenster zeigt. Wird aus dem CRDT nachgezogen.
    @Published var text: String = ""

    private var aufgabe: URLSessionWebSocketTask?
    private var doc: YDocument?
    private var ytext: YText?
    /// Der zuletzt in das CRDT geschriebene Stand. Ohne ihn liesse sich eine
    /// eingehende Aenderung nicht von einer eigenen unterscheiden, und jede
    /// fremde Einfuegung wuerde als eigene zurueckgesendet -- eine Schleife.
    private var zuletzt: String = ""
    private var sendetGerade = false

    func verbinde(zu url: URL, geheimnis: String?) {
        trenne()
        lage = .verbindet
        let sitzung = URLSession(configuration: .default)
        let aufgabe = sitzung.webSocketTask(with: url)
        self.aufgabe = aufgabe
        aufgabe.resume()

        if let geheimnis, !geheimnis.isEmpty {
            sende(Dokumentprotokoll.anmeldung(geheimnis: geheimnis))
        }
        empfange()
    }

    func trenne() {
        aufgabe?.cancel(with: .goingAway, reason: nil)
        aufgabe = nil
        doc = nil
        ytext = nil
        zuletzt = ""
        lage = .getrennt
    }

    /// Wird bei jeder Tastatureingabe gerufen.
    func schreibe(_ neu: String) {
        guard let doc, let ytext, !sendetGerade else { return }
        let aenderung = Textabgleich.aenderung(von: zuletzt, nach: neu)
        guard !aenderung.istLeer else { return }

        doc.transactSync { txn in
            if aenderung.geloescht > 0 {
                ytext.removeRange(start: aenderung.bei, length: aenderung.geloescht, in: txn)
            }
            if !aenderung.eingefuegt.isEmpty {
                ytext.insert(aenderung.eingefuegt, at: aenderung.bei, in: txn)
            }
        }
        zuletzt = neu
        sendeStand()
    }

    /// Fuegt an einer Stelle ein -- genau das, was ein Tastendruck tut.
    /// Anders als `schreibe` setzt es KEINEN Volltext und kann darum die
    /// gleichzeitige Aenderung eines anderen nicht mitloeschen.
    func fuegeEin(_ text: String, bei: Int) {
        guard let doc, let ytext, !text.isEmpty else { return }
        doc.transactSync { txn in
            let laenge = UInt32(ytext.getString(in: txn).utf8.count)
            ytext.insert(text, at: min(UInt32(max(0, bei)), laenge), in: txn)
        }
        zeigeAusDokument()
        sendeStand()
    }

    // MARK: Verbindung

    private func sende(_ text: String) {
        aufgabe?.send(.string(text)) { fehler in
            guard let fehler else { return }
            Task { @MainActor [weak self] in
                self?.lage = .fehler("Die Verbindung zum Dokument ist unterbrochen.")
                _ = fehler
            }
        }
    }

    private func sendeStand() {
        guard let doc else { return }
        let aktualisierung = doc.transactSync { txn in doc.diff(txn: txn, from: [0]) }
        sende(Dokumentprotokoll.update(Data(aktualisierung)))
    }

    private func empfange() {
        aufgabe?.receive { [weak self] ergebnis in
            Task { @MainActor in
                guard let self else { return }
                switch ergebnis {
                case .failure:
                    self.lage = .fehler("Die Verbindung zum Dokument ist unterbrochen.")
                case .success(let nachricht):
                    if case .string(let roh) = nachricht { self.verarbeite(roh) }
                    self.empfange()
                }
            }
        }
    }

    private func verarbeite(_ roh: String) {
        switch Dokumentprotokoll.deute(roh) {
        case .failure(let fehler):
            // Eine Kennung ausserhalb der Schranke ist kein Schoenheitsfehler:
            // sie fuehrt zu still verdoppeltem Text. Also nicht weiterarbeiten.
            lage = .fehler(fehlertext(fehler))
            trenneStill()

        case .success(.willkommen(let kennung, let stand)):
            // GEMESSEN 2026-08-14, und es aendert die Rolle der Kennung auf
            // dieser Seite: `YDocument()` nimmt KEINE Kennung entgegen --
            // yswift vergibt sie selbst. 50 frische Dokumente ergaben
            // Kennungen zwischen 38 704 772 und 4 260 997 537, alle unter
            // 2^32. Die Auflage aus ADR-010 haelt hier also von selbst; sie
            // gilt weiterhin fuer Klienten, die ihre Kennung waehlen KOENNEN
            // (pycrdt wuerfelt bis 2^53).
            //
            // Die Kennung aus `willkommen` wird trotzdem geprueft und nicht
            // stillschweigend verworfen: sie ist der Melder dafuer, dass der
            // Dienst je etwas anderes vergibt -- und dann verdoppelt sich Text
            // still statt laut zu scheitern.
            _ = kennung
            let neu = YDocument()
            let t = neu.getOrCreateText(named: "t")
            if !stand.isEmpty {
                neu.transactSync { txn in try? txn.transactionApplyUpdate(update: [UInt8](stand)) }
            }
            doc = neu
            ytext = t
            lage = .verbunden(kennung: kennung)
            zeigeAusDokument()

        case .success(.update(let daten)):
            guard let doc else { return }
            doc.transactSync { txn in try? txn.transactionApplyUpdate(update: [UInt8](daten)) }
            zeigeAusDokument()

        case .success(.fehler(let grund)):
            lage = .fehler(grund)
        }
    }

    /// Der Bildschirm folgt dem Dokument, nie umgekehrt.
    private func zeigeAusDokument() {
        guard let doc, let ytext else { return }
        let aktuell = doc.transactSync { txn in ytext.getString(in: txn) }
        guard aktuell != text else { return }
        sendetGerade = true          // sonst deutet `schreibe` das als Eingabe
        text = aktuell
        zuletzt = aktuell
        sendetGerade = false
    }

    private func trenneStill() {
        aufgabe?.cancel(with: .goingAway, reason: nil)
        aufgabe = nil
        doc = nil
        ytext = nil
    }

    /// Was der Mensch liest. Der technische Grund bleibt im Protokoll.
    private func fehlertext(_ fehler: Dokumentprotokoll.Fehler) -> String {
        switch fehler {
        case .kennungAusserhalb:
            return "Das Dokument kann nicht sicher geteilt werden. Bitte neu verbinden."
        case .vomDienst(let grund):
            return grund
        default:
            return "Die Antwort des Dokuments war unlesbar. Bitte neu verbinden."
        }
    }
}

struct DokumentAnsicht: View {
    /// Kommt von aussen (AtelierAppDelegate), damit die Steuerschnittstelle
    /// dieselbe Sitzung erreicht -- zwei Sitzungen waeren zwei Wahrheiten.
    @ObservedObject var sitzung: Dokumentsitzung
    @AppStorage("dokument.adresse") private var adresse = "ws://127.0.0.1:4610"
    @State private var geheimnis = ""

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 12) {
                Text("Dokument")
                    .frame(width: 96, alignment: .leading)
                TextField("Adresse des Dokumentdienstes", text: $adresse)
                    .textFieldStyle(.roundedBorder)
                    .accessibilityLabel("Adresse des Dokumentdienstes")
                // Das Feld steht immer da. Die erste Fassung blendete es bei
                // 127.0.0.1 aus -- falsch: ob eine Anmeldung noetig ist,
                // entscheidet der Dienst danach, worauf ER lauscht, nicht der
                // Klient danach, wen er anspricht. Ein Dienst auf 0.0.0.0
                // verlangt sie auch von einer Verbindung ueber 127.0.0.1, und
                // dann fehlte genau das Feld, das gebraucht wird.
                SecureField("Zugangswort", text: $geheimnis)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 180)
                    .accessibilityLabel("Zugangswort")
                Button(istVerbunden ? "Trennen" : "Verbinden") {
                    if istVerbunden { sitzung.trenne() }
                    else if let url = URL(string: adresse) {
                        sitzung.verbinde(zu: url, geheimnis: geheimnis.isEmpty ? nil : geheimnis)
                    }
                }
                Text(sitzung.lage.satz)
                    .foregroundStyle(.secondary)
                    .accessibilityLabel("Verbindungslage: \(sitzung.lage.satz)")
            }
            .padding(12)

            Divider()

            TextEditor(text: Binding(
                get: { sitzung.text },
                set: { sitzung.text = $0; sitzung.schreibe($0) }
            ))
            .font(.body)
            .accessibilityLabel("Dokumenttext")
            .disabled(!istVerbunden)
        }
    }

    private var istVerbunden: Bool {
        if case .verbunden = sitzung.lage { return true }
        return false
    }
}
