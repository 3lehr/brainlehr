// H8b: liest die vom Nutzer gewaehlte Paketdatei und schickt sie an
// POST /api/domaene-import -- genau der Weg, den QuellenBereich.swift schon
// fuer /api/fundstelle geht (URLSession gegen DienstAufsicht.port). Kein
// zweiter Weg zum Dienst, kein eigener Prozessaufruf.
//
// Die Datei ist DATEN: sie wird gelesen und weitergereicht, nie ausgefuehrt.
// Die Pruefung (annehmen/ablehnen mit Grund) liegt in kern/domaene.py
// und in BrainlehrCore.DomaeneImportUebersetzung (Uebersetzung der
// Antwort in Nutzersprache) -- ergebnisText() unten baut nur den
// angenommen-Zweig lokal weiter aus (siehe NACHTRAG unten), BrainlehrCore
// bleibt fuer diesen Auftrag unangetastet.
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
//
// NACHTRAG 2026-08-15 (Befund desselben Tages): der Dienst schrieb bislang
// nichts (domaene.pruefe()), meldete der App aber "gilt jetzt". Jetzt ruft
// der Dienst domaene.speichere() -- das schreibt tatsaechlich, darum
// braucht dieser Aufruf jetzt einen Ausweis (Kopf 'Authorization: Bearer
// <Geheimnis>', wie AusweisDienst.swift es fuer seine POSTs beschreibt) und
// die Rueckmeldung unterscheidet "gespeichert" von "gilt" -- Wirkung Null
// (ADR-018): eine gespeicherte Regel WIRKT NOCH NICHT, das ist ein
// getrennter, in der App aktuell nicht vorhandener Schritt.
import BrainlehrCore
import Foundation

enum DomaeneImportDienst {
    /// `geheimnis`: der Ausweis, den der Aufrufer (AtelierApp.swift) vorher
    /// beim Nutzer abgefragt hat -- diese Datei beschafft und speichert kein
    /// Geheimnis selbst, sie reicht nur weiter, was sie bekommt.
    static func importiere(dateiURL: URL, geheimnis: String) async -> (ergebnis: DomaeneImportErgebnis, bestandteile: Set<Bestandteil>?) {
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
        // Fund O2 (2026-08-15): _herkunft_ok() im Dienst verlangt bei jedem
        // POST den eigenen Origin -- ohne ihn kam bisher ein stilles 403.
        anfrage.setValue("http://127.0.0.1:\(DienstAufsicht.port)", forHTTPHeaderField: "Origin")
        anfrage.setValue("Bearer \(geheimnis)", forHTTPHeaderField: "Authorization")
        anfrage.httpBody = try? JSONSerialization.data(withJSONObject: paket)

        guard let (antwortDaten, _) = try? await URLSession.shared.data(for: anfrage),
              let roh = try? JSONSerialization.jsonObject(with: antwortDaten) as? [String: Any]
        else {
            return (unerreichbar, nil)
        }
        let angenommen = (roh["angenommen"] as? Bool) == true
        let bestandteile = angenommen ? BestandteilAnforderung.gewaehrt(angefordert: angefordert) : nil
        return (ergebnisText(roh), bestandteile)
    }

    /// Baut auf BrainlehrCore.DomaeneImportUebersetzung auf, ersetzt aber
    /// den angenommen-Satz: der dortige Text sagt "gilt jetzt", was seit
    /// domaene.speichere() (Wirkung Null, ADR-018) nicht mehr stimmt --
    /// gespeichert und wirksam sind seither zwei verschiedene Zustaende.
    /// Fehlt der Ausweis oder stimmt die Herkunft nicht, antwortet der
    /// Dienst mit einem "error"-Feld statt "angenommen" -- auch dafuer ein
    /// eigener, nicht-technischer Satz statt des allgemeinen Ersatztexts.
    private static func ergebnisText(_ roh: [String: Any]) -> DomaeneImportErgebnis {
        if roh["error"] != nil {
            return DomaeneImportErgebnis(
                titel: "Nicht übernommen",
                text: "Dafür wird ein gültiger Ausweis gebraucht.")
        }
        guard (roh["angenommen"] as? Bool) == true else {
            return DomaeneImportUebersetzung.uebersetze(roh)
        }
        let name = (roh["bezeichnung"] as? String) ?? "Die Domäne"
        let anzahl = roh["anzahl_regeln"] as? Int
        switch DomaeneImportUebersetzung.wirkung(roh) {
        case .unveraendert:
            return DomaeneImportErgebnis(
                titel: "Bereits vorhanden",
                text: "„\(name)“ war schon gespeichert. Diese Datei enthielt nichts Neues.")
        case .aktualisiert:
            // INT-UPD-001: ein Reimport mit geaendertem Inhalt legt nichts an
            // und ist trotzdem nicht folgenlos -- der alte Satz haette hier
            // "nichts Neues" gemeldet, waehrend eine korrigierte Regel gerade
            // eingespielt wurde.
            return DomaeneImportErgebnis(
                titel: "Aktualisiert",
                text: "„\(name)“ war schon gespeichert und wurde aufgefrischt. Was bereits gilt, bleibt unverändert.")
        case .angelegt:
            break
        }
        let satz: String
        switch anzahl {
        case 1: satz = "Eine Regel liegt jetzt bereit."
        case let n?: satz = "\(n) Regeln liegen jetzt bereit."
        case nil: satz = "Die Regeln liegen jetzt bereit."
        }
        return DomaeneImportErgebnis(
            titel: "Gespeichert",
            text: "„\(name)“ wurde übernommen. \(satz) Sie gelten noch nicht — das ist ein eigener Schritt, der in dieser App noch nicht möglich ist.")
    }

    private static var unerreichbar: DomaeneImportErgebnis {
        DomaeneImportErgebnis(titel: "Nicht übernommen", text: "Der Import kann gerade nicht geprüft werden.")
    }
}
