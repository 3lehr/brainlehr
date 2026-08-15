// Reine Zustandslogik der Dienstaufsicht -- kein Foundation.Process, kein
// Netzwerk, darum ohne Mock testbar. Die Aufsicht selbst (Atelier/
// DienstAufsicht.swift) treibt diese Funktion mit echten Beobachtungen.

/// Zustand des ueberwachten Dienstes aus Sicht der Oberflaeche.
public enum DienstZustand: Equatable, Sendable {
    /// Wird gerade gestartet oder wurde bereits laufend vorgefunden, aber
    /// die erste Erreichbarkeitspruefung steht noch aus.
    case startetGerade
    /// Erreichbar, alles in Ordnung.
    case laeuft
    /// War erreichbar, ist es jetzt nicht mehr -- der Fall, den die
    /// Oberflaeche ungefragt anzeigen muss.
    case unerwartetBeendet
    /// Von der App selbst angehalten (z.B. beim Beenden). Kein Fehler.
    case angehalten

    public var istFehler: Bool { self == .unerwartetBeendet }
}

public enum DienstUebergang {
    /// Naechster Zustand aus aktuellem Zustand und einer Beobachtung.
    ///
    /// - `erreichbar`: letzte Gesundheitspruefung (z.B. HTTP-Anfrage) war erfolgreich.
    /// - `wurdeAngehalten`: die App hat den Dienst selbst und absichtlich beendet.
    public static func naechsterZustand(
        aktuell: DienstZustand,
        erreichbar: Bool,
        wurdeAngehalten: Bool
    ) -> DienstZustand {
        if wurdeAngehalten {
            return .angehalten
        }
        switch aktuell {
        case .angehalten:
            // Bleibt an, bis ein expliziter Neustart den Zustand zuruecksetzt.
            return .angehalten
        case .startetGerade:
            // Waehrend des Hochfahrens ist "noch nicht erreichbar" normal,
            // kein Fehler -- das waere sonst ein falscher unerwartetBeendet-Alarm.
            return erreichbar ? .laeuft : .startetGerade
        case .laeuft:
            return erreichbar ? .laeuft : .unerwartetBeendet
        case .unerwartetBeendet:
            // Erholt sich der Dienst von selbst (z.B. von aussen neu gestartet),
            // zeigt die Oberflaeche das ohne Zutun wieder als "laeuft".
            return erreichbar ? .laeuft : .unerwartetBeendet
        }
    }
}

/// Der Satz fuer die Oberflaeche je Zustand -- in Nutzersprache, niemals
/// Pfad, Port, Prozessname oder Programmiersprache. Seit die App den Dienst
/// nicht mehr selbst startet (siehe Atelier/DienstAufsicht.swift), heisst der
/// Weg fuer den Menschen: den Dienst starten (ausserhalb der App), dann
/// erneut nachsehen.
public enum DienstMeldung {
    public static let nichtErreichbar =
        "Der Wissensraum ist gerade nicht gestartet. Bitte starte ihn, dann kann hier mit \u{201E}Erneut versuchen\u{201C} nachgesehen werden."

    public static func fuer(_ zustand: DienstZustand) -> String? {
        switch zustand {
        case .unerwartetBeendet:
            return nichtErreichbar
        case .startetGerade, .laeuft, .angehalten:
            return nil
        }
    }
}
