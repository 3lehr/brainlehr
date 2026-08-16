import Foundation

/// Ob eine Domaene beim Anmelden mitstartet -- ADR-023.
///
/// WARUM EINE EIGENE EINHEIT und nicht ein Feld in der Aufsicht: Der Schalter
/// liegt nach ADR-014 im KERN, nicht in der Domaene ("ins atelier gehoert, was
/// keine Domaene ueber sich selbst entscheiden darf"). Eine Domaene, die ihren
/// eigenen Autostart erteilt, ist keine Schranke. Und weil er hier ohne
/// Oberflaeche und ohne Netz liegt, ist er ohne Mock pruefbar -- dieselbe
/// Trennung wie bei DienstZustand.
///
/// VORAUSSETZUNG, die diese Bauform traegt (ADR-023, Punkt 5): Voreinstellung
/// AUS. Eine frisch importierte Domaene startet nichts von selbst. Der
/// Unterschied zum Zustand davor ist trotzdem gross, denn das Aus ist jetzt
/// SICHTBAR und umlegbar statt unsichtbar und raetselhaft.
public struct Mitstart: Sendable {
    /// Schluessel je Domaene. Bewusst mit Praefix: der Speicher ist mit
    /// anderen Einstellungen geteilt, und ein nackter Domaenenname waere dort
    /// eine Kollision, die niemand bemerkt.
    public static func schluessel(fuer domaene: String) -> String {
        "mitstart.\(domaene)"
    }

    /// Voreinstellung ist AUS -- und zwar auch dann, wenn zum Schluessel gar
    /// nichts gespeichert ist. `UserDefaults.bool` liefert fuer einen
    /// fehlenden Schluessel `false`, was hier zufaellig richtig waere; darauf
    /// wird sich NICHT verlassen, weil ein Zufall keine Entscheidung ist.
    public static func istEingeschaltet(
        _ domaene: String, speicher: [String: Bool]
    ) -> Bool {
        speicher[schluessel(fuer: domaene)] ?? false
    }
}
