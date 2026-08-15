// H8b: liest die vom Nutzer gewaehlte Paketdatei und schickt sie an
// POST /api/domaene-import -- genau der Weg, den QuellenBereich.swift schon
// fuer /api/fundstelle geht (URLSession gegen DienstAufsicht.port). Kein
// zweiter Weg zum Dienst, kein eigener Prozessaufruf.
//
// Die Datei ist DATEN: sie wird gelesen und weitergereicht, nie ausgefuehrt.
// Die Pruefung (annehmen/ablehnen mit Grund) liegt in kern/domaene.py
// (H8a) und in BrainlehrCore.DomaeneImportUebersetzung (Uebersetzung der
// Antwort in Nutzersprache).
//
// I1: das optionale Feld "bestandteile" im selben Paket wird HIER lokal
// gelesen, nicht vom Dienst -- kern/domaene.py kennt es nicht und muss es
// nicht kennen (Bestandteile sind eine Darstellungsfrage, kein
// Wissensvertrag, siehe kern/bestandteile.py). Gewaehrt wird nur, was der
// Katalog in BrainlehrCore.BestandteilAnforderung zulaesst -- und nur, wenn
// der Dienst das Paket selbst angenommen hat. WIRKUNG NULL (wie
// kern/domaene.py bei einem abgelehnten Paket): `bestandteile == nil`
// bedeutet "nichts geaendert", nicht "nichts gewaehrt" -- eine abgelehnte
// oder unlesbare Datei loescht keine bereits geltende Anforderung einer
// frueher angenommenen Domaene.

import BrainlehrCore
import Foundation

enum DomaeneImportDienst {
    static func importiere(dateiURL: URL) async -> (ergebnis: DomaeneImportErgebnis, bestandteile: Set<Bestandteil>?) {
        guard let daten = try? Data(contentsOf: dateiURL),
              let paket = try? JSONSerialization.jsonObject(with: daten) as? [String: Any]
        else {
            let e = DomaeneImportErgebnis(
                titel: "Nicht gelesen",
                text: "Diese Datei lässt sich nicht als Paket lesen.")
            return (e, nil)
        }
        let angefordert = paket["bestandteile"] as? [String] ?? []

        guard let url = URL(string: "http://127.0.0.1:\(DienstAufsicht.port)/api/domaene-import") else {
            return (unerreichbar, nil)
        }
        var anfrage = URLRequest(url: url)
        anfrage.httpMethod = "POST"
        anfrage.setValue("application/json", forHTTPHeaderField: "Content-Type")
        anfrage.httpBody = try? JSONSerialization.data(withJSONObject: paket)

        guard let (antwortDaten, _) = try? await URLSession.shared.data(for: anfrage),
              let roh = try? JSONSerialization.jsonObject(with: antwortDaten) as? [String: Any]
        else {
            return (unerreichbar, nil)
        }
        let angenommen = (roh["angenommen"] as? Bool) == true
        let bestandteile = angenommen ? BestandteilAnforderung.gewaehrt(angefordert: angefordert) : nil
        return (DomaeneImportUebersetzung.uebersetze(roh), bestandteile)
    }

    private static var unerreichbar: DomaeneImportErgebnis {
        DomaeneImportErgebnis(titel: "Nicht übernommen", text: "Der Import kann gerade nicht geprüft werden.")
    }
}
