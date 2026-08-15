// Ruft den Dienst (berichte/entscheidungen_server.py, DienstAufsicht.port)
// auf -- denselben Weg, den QuellenBereich.swift und DomaeneImportDienst.swift
// fuer /api/fundstelle bzw. /api/domaene-import schon gehen.
//
// FRUEHERE FASSUNG startete pflege/ausweis_start.sh als eigenen Unterprozess
// (Foundation.Process). Seit die App-Sandbox scharf ist (app-sandbox,
// network.client, app/Resources/atelier.entitlements) blockiert das
// Betriebssystem den Start eines Prozesses ausserhalb des Bundles -- der
// Ausweis-Weg war tot, gemessen in runs/sandbox_scharf_g6_2026-08-15T103800+0200.json
// (Punkt 2: "GEHT NICHT ... Oberflaeche zeigt 'Der Ausweis-Helfer wurde
// nicht gefunden.'"). Der Dienst laeuft schon ausserhalb der Sandbox
// (launchd, siehe dienst/) und bedient die App bereits fuer Quellenliste und
// Domaenen-Import -- der Ausweis-Weg folgt jetzt demselben Muster statt
// einer eigenen Ausnahme vom Bundle.
//
// GEHEIMNIS-UEBERGABE: im JSON-Body des POST, nie in der URL/Query (dort
// landen Werte in Log-Zeilen, die ueber den Anfragekoerper hinausreichen).
// Der Dienst reicht es unveraendert per STDIN an pflege/ausweis_start.sh
// weiter -- wie zuvor beim Process()-Aufruf, nur eine Netzhuelle mehr. Ein
// frisch erzeugtes Geheimnis (bei "anlegen") steht dabei EINMAL in der
// Antwort -- das ist keine neue Undichtigkeit, sondern der Zweck des
// Befehls (kern/ausweis.py::anlegen() gibt es genau einmal zurueck); der
// Dienst schreibt keinen Anfrage- oder Antwortkoerper in ein Protokoll
// (log_message() dort stillgelegt).
//
// HERKUNFTSSCHRANKE: der Dienst prueft bei jedem POST den Origin-Header
// gegen seine eigene Adresse (berichte/entscheidungen_server.py::_herkunft_ok,
// Fund O2) -- dieselbe Schranke wie bei /api/domaene-import. Dieser Klient
// setzt ihn genauso.
//
// kern/ausweis.py und kern/geheimnis.py bleiben tabu -- diese Datei bildet
// nur das HTTP-Protokoll des Dienstes nach.

import Foundation
import BrainlehrCore

struct AusweisDienstFehler: Error, LocalizedError {
    let nachricht: String
    var errorDescription: String? { nachricht }
}

enum AusweisDienst {
    private static var basis: URL { URL(string: "http://127.0.0.1:\(DienstAufsicht.port)")! }
    private static var origin: String { "http://127.0.0.1:\(DienstAufsicht.port)" }

    private static func get(_ pfad: String) async throws -> Data {
        var anfrage = URLRequest(url: basis.appendingPathComponent(pfad))
        anfrage.timeoutInterval = 25
        guard let (daten, antwort) = try? await URLSession.shared.data(for: anfrage) else {
            throw unerreichbar
        }
        return try gepruefteAntwort(daten, antwort)
    }

    private static func post(_ pfad: String, _ koerper: [String: Any]) async throws -> Data {
        var anfrage = URLRequest(url: basis.appendingPathComponent(pfad))
        anfrage.httpMethod = "POST"
        anfrage.timeoutInterval = 25
        anfrage.setValue("application/json", forHTTPHeaderField: "Content-Type")
        anfrage.setValue(origin, forHTTPHeaderField: "Origin")
        anfrage.httpBody = try? JSONSerialization.data(withJSONObject: koerper)
        guard let (daten, antwort) = try? await URLSession.shared.data(for: anfrage) else {
            throw unerreichbar
        }
        return try gepruefteAntwort(daten, antwort)
    }

    /// {"fehler": "..."} wird zur Ausnahme, im Wortlaut des Ausweis-Helfers.
    /// Ein HTTP-Status ausserhalb 200 ohne dieses Feld (z. B. 403 bei
    /// fremder Herkunft, 404 bei unbekanntem Pfad) bekommt einen
    /// verstaendlichen Ersatztext -- kein Rohstatus in der Oberflaeche.
    private static func gepruefteAntwort(_ daten: Data, _ antwort: URLResponse) throws -> Data {
        if let fehler = gefundenerFehler(in: daten) {
            throw AusweisDienstFehler(nachricht: fehler)
        }
        guard let http = antwort as? HTTPURLResponse, http.statusCode == 200 else {
            throw AusweisDienstFehler(nachricht: "Das hat gerade nicht geklappt. Bitte versuche es erneut.")
        }
        return daten
    }

    /// Wortlaut wie BrainlehrCore.DienstMeldung.nichtErreichbar -- derselbe
    /// Wissensraum, derselbe Satz, egal welcher Teil der Oberflaeche ihn
    /// gerade nicht erreicht.
    private static var unerreichbar: AusweisDienstFehler {
        AusweisDienstFehler(nachricht: DienstMeldung.nichtErreichbar)
    }

    static func liste() async throws -> AusweisListeAntwort {
        let daten = try await get("/api/ausweisliste")
        do {
            return try JSONDecoder().decode(AusweisListeAntwort.self, from: daten)
        } catch {
            throw AusweisDienstFehler(nachricht: "Die Antwort des Ausweis-Dienstes konnte nicht gelesen werden.")
        }
    }

    static func anlegen(name: String, art: AusweisArt, rollen: [AusweisRolle], geheimnis: String) async throws -> AusweisAnlegenAntwort {
        let daten = try await post("/api/ausweis-anlegen", [
            "name": name, "art": art.rawValue,
            "rollen": rollenText(rollen), "geheimnis": geheimnis,
        ])
        do {
            return try JSONDecoder().decode(AusweisAnlegenAntwort.self, from: daten)
        } catch {
            throw AusweisDienstFehler(nachricht: "Die Antwort des Ausweis-Dienstes konnte nicht gelesen werden.")
        }
    }

    static func einladen(name: String, fuer: String, rollen: [AusweisRolle], geheimnis: String) async throws -> AusweisEinladenAntwort {
        let daten = try await post("/api/ausweis-einladen", [
            "name": name, "fuer": fuer,
            "rollen": rollenText(rollen), "geheimnis": geheimnis,
        ])
        do {
            return try JSONDecoder().decode(AusweisEinladenAntwort.self, from: daten)
        } catch {
            throw AusweisDienstFehler(nachricht: "Die Antwort des Ausweis-Dienstes konnte nicht gelesen werden.")
        }
    }
}
