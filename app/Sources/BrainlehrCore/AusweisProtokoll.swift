// Reine Bruecke zu pflege/ausweis_helfer.py (Argumente bauen, Antwort-JSON
// deuten) -- Schritt 3 des Plans (docs/PLAN_MACAPP_2026-08-12.md). Der
// eigentliche Prozessaufruf und die Geheimnis-Uebergabe per Pipe leben in
// Atelier/AusweisDienst.swift (braucht Foundation.Process); hier nur,
// was ohne Subprozess pruefbar ist.
//
// kern/ausweis.py und kern/geheimnis.py bleiben tabu -- diese Datei bildet
// nur das JSON-Protokoll von pflege/ausweis_helfer.py nach, ohne dessen
// Regeln zu duplizieren.

import Foundation

/// Wie in pflege/brainlehr.applescript::frageArt(). "maschine" ist die
/// Vorgabe: nur ein Ausweis fuer einen Menschen zaehlt als menschliche
/// Entscheidung.
public enum AusweisArt: String, CaseIterable, Sendable {
    case maschine
    case mensch

    public var anzeigename: String {
        switch self {
        case .maschine: return "Programm (Vorgabe)"
        case .mensch: return "Mensch"
        }
    }
}

/// Wie in pflege/brainlehr.applescript::frageRollen().
public enum AusweisRolle: String, CaseIterable, Identifiable, Sendable {
    case schreiber, fachkundig, leser, gast, meldeamt, betreiber
    public var id: String { rawValue }
}

public func rollenText(_ rollen: [AusweisRolle]) -> String {
    rollen.map(\.rawValue).joined(separator: ",")
}

/// Argumente fuer pflege/ausweis_start.sh (Skriptname selbst nicht
/// enthalten -- der Aufrufer setzt ihn als `executableURL`).
public func argumenteAnlegen(name: String, art: AusweisArt, rollen: [AusweisRolle]) -> [String] {
    ["anlegen", name, art.rawValue, rollenText(rollen)]
}

public func argumenteEinladen(name: String, fuer: String, rollen: [AusweisRolle]) -> [String] {
    ["einladen", name, fuer, rollenText(rollen)]
}

public let argumenteListe: [String] = ["liste"]

// -- Antworten, wie pflege/ausweis_helfer.py sie als JSON druckt --

public struct AusweisFehlerAntwort: Decodable, Sendable {
    public let fehler: String
}

/// `nil`, wenn `daten` kein `{"fehler": "..."}` ist -- dann ist es die
/// erwartete Erfolgsantwort des jeweiligen Befehls.
public func gefundenerFehler(in daten: Data) -> String? {
    (try? JSONDecoder().decode(AusweisFehlerAntwort.self, from: daten))?.fehler
}

public struct AusweisEintrag: Decodable, Identifiable, Sendable {
    public let name: String
    public let art: String
    public let rollen: [String]
    public var id: String { name }
}

public struct AusweisListeAntwort: Decodable, Sendable {
    public let datei: String
    public let ausweise: [AusweisEintrag]
}

public struct AusweisAnlegenAntwort: Decodable, Sendable {
    public let name: String
    public let art: String
    public let rollen: [String]
    public let geheimnis: String
}

public struct AusweisEinladenAntwort: Decodable, Sendable {
    public let name: String
    public let fuer: String
    public let pin: String
    public let gueltig_minuten: Int
}
