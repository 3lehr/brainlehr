// Reine Zustandslogik der Dienstaufsicht -- kein Foundation.Process, kein
// Netzwerk, darum ohne Mock testbar. Die Aufsicht selbst (Atelier/
// DienstAufsicht.swift) treibt diese Funktion mit echten Beobachtungen.
//
// B5 / ADR-023: Der Mensch entscheidet per Schalter, ob eine Domaene
// mitstartet. Die ADR verlangt dafuer VIER unterscheidbare Zustaende, nicht
// zwei -- woertlich: "aus (Schalter steht aus -- kein Defekt, eine
// Entscheidung) - startet - laeuft - kommt nicht hoch. Die ersten beiden sind
// heute nicht unterscheidbar, und genau diese Verwechslung beschreibt der
// Betreiber." Vor B5 gab es weder `aus` noch `kommtNichtHoch`; ein Dienst, der
// nie hochkam, blieb fuer immer in `startetGerade`, und "startet fuer immer"
// liest sich wie ein Defekt, ohne einen zu benennen.

/// Zustand des ueberwachten Dienstes aus Sicht der Oberflaeche.
public enum DienstZustand: Equatable, Sendable {
    /// Der Schalter steht aus. KEIN Defekt, sondern eine Entscheidung des
    /// Menschen -- und der wichtigste der vier Zustaende, weil sein Fehlen
    /// die ADR ausgeloest hat. Voreinstellung fuer jede frisch importierte
    /// Domaene (ADR-023, Punkt 5: installiert heisst nicht gestartet).
    case aus
    /// Wird gerade gestartet oder wurde bereits laufend vorgefunden, aber
    /// die erste Erreichbarkeitspruefung steht noch aus.
    case startetGerade
    /// Erreichbar, alles in Ordnung.
    case laeuft
    /// Eingeschaltet, aber nach der Geduldsspanne nie erreichbar gewesen.
    /// Abgegrenzt von `unerwartetBeendet`: dort LIEF er schon einmal.
    case kommtNichtHoch
    /// War erreichbar, ist es jetzt nicht mehr -- der Fall, den die
    /// Oberflaeche ungefragt anzeigen muss.
    case unerwartetBeendet
    /// Von der App selbst angehalten (z.B. beim Beenden). Kein Fehler.
    case angehalten

    public var istFehler: Bool { self == .unerwartetBeendet || self == .kommtNichtHoch }
}

public enum DienstUebergang {
    /// Wie lange ein eingeschalteter Dienst hochfahren darf, bevor aus
    /// "startet" ein "kommt nicht hoch" wird -- in Sekunden.
    ///
    /// Der Wert ist eine gesetzte Schranke, keine Messung, und er ist
    /// bewusst grosszuegig: zu kurz erzeugt Fehlalarme auf langsamen
    /// Rechnern, und ein Fehlalarm kostet mehr Vertrauen als eine
    /// Verzoegerung Zeit kostet. Ein spaeter Erfolg schlaegt die Spanne
    /// jederzeit (siehe unten) -- die Schranke sperrt also nichts, sie
    /// benennt nur.
    public static let geduldsspanne = 20

    /// Naechster Zustand aus aktuellem Zustand und einer Beobachtung.
    ///
    /// - `erreichbar`: letzte Gesundheitspruefung war erfolgreich.
    /// - `wurdeAngehalten`: die App hat den Dienst selbst beendet.
    /// - `eingeschaltet`: der Schalter des Menschen (ADR-023). Steht er aus,
    ///   ist der Zustand `aus` -- unabhaengig von allem anderen.
    /// - `versucheSeit`: Sekunden seit dem Einschalten. Nur im Zustand
    ///   `startetGerade` gelesen.
    public static func naechsterZustand(
        aktuell: DienstZustand,
        erreichbar: Bool,
        wurdeAngehalten: Bool,
        eingeschaltet: Bool = true,
        versucheSeit: Int = 0
    ) -> DienstZustand {
        // Der Schalter des Menschen schlaegt JEDE Beobachtung, und zwar aus
        // jedem Zustand heraus. Sonst koennte ein fremder Prozess auf
        // demselben Port bestimmen, was ueber die eigene Domaene angezeigt
        // wird -- und der Mensch saehe "laeuft", obwohl er abgeschaltet hat.
        if !eingeschaltet {
            return .aus
        }
        if wurdeAngehalten {
            return .angehalten
        }
        switch aktuell {
        case .aus:
            // Gerade eingeschaltet: der Start beginnt, das Ergebnis steht noch aus.
            return erreichbar ? .laeuft : .startetGerade
        case .angehalten:
            // Bleibt an, bis ein expliziter Neustart den Zustand zuruecksetzt.
            return .angehalten
        case .startetGerade:
            // Waehrend des Hochfahrens ist "noch nicht erreichbar" normal,
            // kein Fehler. Aber NICHT unbegrenzt: nach der Geduldsspanne wird
            // daraus eine Aussage, die der Mensch gebrauchen kann.
            if erreichbar { return .laeuft }
            return versucheSeit >= geduldsspanne ? .kommtNichtHoch : .startetGerade
        case .laeuft:
            return erreichbar ? .laeuft : .unerwartetBeendet
        case .kommtNichtHoch, .unerwartetBeendet:
            // Erholt sich der Dienst von selbst (z.B. von aussen gestartet),
            // zeigt die Oberflaeche das ohne Zutun wieder als "laeuft".
            return erreichbar ? .laeuft : aktuell
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

    /// `aus` braucht einen eigenen Satz, und er ist der Grund fuer ADR-023:
    /// Ohne ihn steht der Mensch vor einer Oberflaeche, die nichts tut, und
    /// kann eine Entscheidung nicht von einem Defekt unterscheiden.
    public static let ausgeschaltet =
        "Diese Anwendung ist ausgeschaltet. Du kannst sie in den Einstellungen einschalten \u{2013} dann startet sie beim Anmelden mit."

    public static let kommtNichtHoch =
        "Diese Anwendung wurde eingeschaltet, meldet sich aber nicht. Schalte sie in den Einstellungen aus und wieder ein; bleibt es dabei, ist sie auf diesem Rechner nicht startbereit."

    public static func fuer(_ zustand: DienstZustand) -> String? {
        switch zustand {
        case .unerwartetBeendet:
            return nichtErreichbar
        case .aus:
            return ausgeschaltet
        case .kommtNichtHoch:
            return kommtNichtHoch
        case .startetGerade, .laeuft, .angehalten:
            return nil
        }
    }
}
