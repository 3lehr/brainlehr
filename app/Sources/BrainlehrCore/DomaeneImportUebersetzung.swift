// H8b (docs/PLAN_OPENLEHR_2026-08-14.md): Antwort von
// POST /api/domaene-import in Nutzersprache uebersetzen. Reine Funktion,
// ohne Netzwerk pruefbar -- die Pruefung selbst liegt in kern/domaene.py
// (H8a, anderer Agent) und entscheidet "angenommen"/"grund". Diese Datei
// UEBERSETZT nur, sie prueft nicht nach.
//
// Vertrag mit dem Server (berichte/entscheidungen_server.py::_domaene_import):
//   angenommen:  {"angenommen": true,  "bezeichnung": String?, "anzahl_regeln": Int?}
//   abgelehnt:   {"angenommen": false, "grund": String}   -- grund bereits
//                in Nutzersprache, z.B. "Die Regel 'Bewirtung' nennt keine Quelle."
//   H8a fehlt noch: {"verfuegbar": false}

public struct DomaeneImportErgebnis: Equatable, Sendable {
    public let titel: String
    public let text: String
    public init(titel: String, text: String) {
        self.titel = titel
        self.text = text
    }
}

public enum DomaeneImportUebersetzung {
    public static func uebersetze(_ antwort: [String: Any]) -> DomaeneImportErgebnis {
        if (antwort["verfuegbar"] as? Bool) == false {
            return DomaeneImportErgebnis(
                titel: "Noch nicht möglich",
                text: "Der Import kann auf diesem Rechner gerade nicht geprüft werden.")
        }
        guard let angenommen = antwort["angenommen"] as? Bool else {
            return DomaeneImportErgebnis(
                titel: "Nicht übernommen",
                text: "Aus der Datei ließ sich kein Ergebnis lesen.")
        }
        if angenommen {
            let name = (antwort["bezeichnung"] as? String) ?? "Die Domäne"
            let anzahl = antwort["anzahl_regeln"] as? Int
            let satz: String
            switch anzahl {
            case 1: satz = "Eine Regel wurde übernommen."
            case let n?: satz = "\(n) Regeln wurden übernommen."
            case nil: satz = "Die Regeln wurden übernommen."
            }
            return DomaeneImportErgebnis(titel: "Übernommen", text: "„\(name)“ gilt jetzt. \(satz)")
        }
        let grund = (antwort["grund"] as? String) ?? "Aus dem Paket ließ sich keine Regel übernehmen."
        return DomaeneImportErgebnis(titel: "Nicht übernommen", text: grund)
    }

    /// INT-UPD-001: seit dem Reimport-Update ist "nichts angelegt" nicht mehr
    /// dasselbe wie "nichts geaendert". Wer nur auf 'gespeichert' schaut,
    /// meldet einem Menschen "enthielt nichts Neues", waehrend die Datei
    /// gerade eine korrigierte Fachregel eingespielt hat.
    /// Reine Funktion, damit die Unterscheidung pruefbar bleibt -- der
    /// Bildschirm (Atelier) baut daraus nur noch den Satz.
    public static func wirkung(_ antwort: [String: Any]) -> DomaeneImportWirkung {
        let neu = (antwort["gespeichert"] as? Int) ?? 0
        let geaendert = (antwort["aktualisiert"] as? Int) ?? 0
        if neu > 0 { return .angelegt }
        if geaendert > 0 { return .aktualisiert }
        return .unveraendert
    }
}

public enum DomaeneImportWirkung: Equatable, Sendable {
    case angelegt
    case aktualisiert
    case unveraendert
}
