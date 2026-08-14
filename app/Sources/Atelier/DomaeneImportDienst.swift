// H8b: liest die vom Nutzer gewaehlte Paketdatei und schickt sie an
// POST /api/domaene-import -- genau der Weg, den QuellenBereich.swift schon
// fuer /api/fundstelle geht (URLSession gegen DienstAufsicht.port). Kein
// zweiter Weg zum Dienst, kein eigener Prozessaufruf.
//
// Die Datei ist DATEN: sie wird gelesen und weitergereicht, nie ausgefuehrt.
// Die Pruefung (annehmen/ablehnen mit Grund) liegt in kern/domaene.py
// (H8a) und in BrainlehrCore.DomaeneImportUebersetzung (Uebersetzung der
// Antwort in Nutzersprache).

import BrainlehrCore
import Foundation

enum DomaeneImportDienst {
    static func importiere(dateiURL: URL) async -> DomaeneImportErgebnis {
        guard let daten = try? Data(contentsOf: dateiURL),
              let paket = try? JSONSerialization.jsonObject(with: daten) as? [String: Any]
        else {
            return DomaeneImportErgebnis(
                titel: "Nicht gelesen",
                text: "Diese Datei lässt sich nicht als Paket lesen.")
        }
        guard let url = URL(string: "http://127.0.0.1:\(DienstAufsicht.port)/api/domaene-import") else {
            return unerreichbar
        }
        var anfrage = URLRequest(url: url)
        anfrage.httpMethod = "POST"
        anfrage.setValue("application/json", forHTTPHeaderField: "Content-Type")
        anfrage.httpBody = try? JSONSerialization.data(withJSONObject: paket)

        guard let (antwortDaten, _) = try? await URLSession.shared.data(for: anfrage),
              let roh = try? JSONSerialization.jsonObject(with: antwortDaten) as? [String: Any]
        else {
            return unerreichbar
        }
        return DomaeneImportUebersetzung.uebersetze(roh)
    }

    private static var unerreichbar: DomaeneImportErgebnis {
        DomaeneImportErgebnis(titel: "Nicht übernommen", text: "Der Import kann gerade nicht geprüft werden.")
    }
}
