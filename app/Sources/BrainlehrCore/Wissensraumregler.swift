// Die Bedienung des Wissensraums als DATEN statt als Bildschirm.
//
// ANLASS (Betreiber, 2026-08-14): "die einstellungen bei wissenraum, das geht
// besser. so wie es jetzt ist war es fuer die webversion gebaut, das bitte
// swift nativ und besser durchdacht."
//
// WAS DARAN "FUER DIE WEBVERSION GEBAUT" WAR, gemessen an entscheidungen.html:
// Sieben Bedienelemente liegen dort in einer einzigen Leiste nebeneinander --
// Zeit, Taktung, Helligkeit, Pulsstaerke, Pulsdauer, Nachleuchten, Anfragefeld.
// Sie sind nach HERKUNFT gruppiert (alles, was die Seite kann), nicht nach
// ZWECK. Fuer eine Webseite, die alles in einem Fenster zeigen muss, ist das
// richtig; in einer Mac-App steht damit die Feinjustage des Leuchtens
// gleichrangig neben der Frage, WAS gezeigt wird.
//
// DIE EINTEILUNG, die daraus folgt, und sie ist der eigentliche Inhalt dieser
// Datei: Ein Regler beantwortet entweder "was sehe ich" (Gegenstand) oder "wie
// sieht es aus" (Darstellung). Der Gegenstand steht immer sichtbar, die
// Darstellung liegt zugeklappt darunter -- wer sie nie oeffnet, verliert nichts.
//
// WARUM DIE LOGIK HIER LIEGT UND NICHT IN DER ANSICHT: `app/Sources/Atelier/`
// hat keine Tests, `BrainlehrCore` hat 151. Welcher Regler zu welchem Blick
// gehoert, wie ein Wert geklemmt wird und welches Skript daraus entsteht, ist
// pruefbare Fachlogik -- ein SwiftUI-Slider ist es nicht.
//
// KEINE ZWEITE ZEICHENLOGIK: Die nativen Regler schreiben ihren Wert in genau
// die Web-Regler, die es schon gibt, und loesen dort `input` aus. Das ist
// derselbe Weg, den ein Mensch mit der Maus ginge -- wie bereits bei den fuenf
// Ansichtsknoepfen b0..b4. Eine eigene Fassung der Darstellung waere eine
// zweite Wahrheit ueber dasselbe Bild.

import Foundation

public enum Wissensraumregler {

    /// Wozu ein Bedienelement gehoert. Die Trennung entscheidet, was oben steht.
    public enum Zweck: String, Sendable, CaseIterable {
        /// Was gezeigt wird -- immer sichtbar.
        case gegenstand
        /// Wie es aussieht -- zugeklappt, Feinjustage.
        case darstellung
    }

    /// Ein Regler, so wie ihn die Seite kennt.
    public struct Regler: Equatable, Sendable, Identifiable {
        /// Die `id` des `<input>` in entscheidungen.html. Zugleich unsere.
        public let id: String
        public let name: String
        public let zweck: Zweck
        public let von: Double
        public let bis: Double
        public let schritt: Double
        public let vorgabe: Double
        /// Wie der Wert dem Menschen gezeigt wird -- die Seite tut dasselbe,
        /// aber in JavaScript, wo wir es nicht pruefen koennen.
        public let einheit: Einheit
        /// Blicke, in denen der Regler ueberhaupt etwas bewirkt. Leer heisst:
        /// in allen.
        public let nurBei: Set<Int>

        public enum Einheit: String, Equatable, Sendable {
            case roh          // 0.83
            case sekunden     // 15 s
            case millisekunden// 3200 ms
            case sekundenAusMillis // 4.0 s
            case prozent      // 100 %
        }

        public func klemme(_ wert: Double) -> Double {
            min(max(wert, von), bis)
        }

        public func beschriftung(_ wert: Double) -> String {
            switch einheit {
            case .roh:
                return String(format: "%.2f", wert)
            case .sekunden:
                return "\(Int(wert.rounded())) s"
            case .millisekunden:
                return "\(Int(wert.rounded())) ms"
            case .sekundenAusMillis:
                return String(format: "%.1f s", wert / 1000)
            case .prozent:
                return "\(Int(wert.rounded())) %"
            }
        }
    }

    /// Blickkennungen wie in entscheidungen.html (b0..b4).
    public static let baum = 0, bedeutung = 1, spuren = 2, vergleich = 3, abrufweg = 4

    /// Die sieben Bedienelemente der Seite, hier nach Zweck getrennt.
    ///
    /// Die Werte (Grenzen, Schrittweite, Vorgabe) sind aus entscheidungen.html
    /// uebernommen, nicht neu erfunden -- eine abweichende Vorgabe hier waere
    /// eine zweite Wahrheit, und der Regler spraenge beim ersten Anfassen.
    public static let alle: [Regler] = [
        Regler(id: "zeit", name: "Zeit", zweck: .gegenstand,
               von: 0, bis: 100, schritt: 1, vorgabe: 100, einheit: .prozent,
               // Beim Abrufweg zeigt die Seite die Zeitleiste nicht -- ein
               // Regler ohne Wirkung ist schlimmer als keiner: er behauptet
               // eine Einstellmoeglichkeit, die es nicht gibt.
               nurBei: [baum, bedeutung, spuren, vergleich]),
        Regler(id: "reglerTaktung", name: "Taktung", zweck: .gegenstand,
               von: 8, bis: 60, schritt: 1, vorgabe: 15, einheit: .sekunden,
               nurBei: [abrufweg]),
        Regler(id: "reglerHelligkeit", name: "Helligkeit", zweck: .darstellung,
               von: 0.4, bis: 1, schritt: 0.01, vorgabe: 0.83, einheit: .roh,
               nurBei: [abrufweg]),
        Regler(id: "reglerPulsstaerke", name: "Pulsstärke", zweck: .darstellung,
               von: 0, bis: 0.35, schritt: 0.01, vorgabe: 0.13, einheit: .roh,
               nurBei: [abrufweg]),
        Regler(id: "reglerPulsdauer", name: "Pulsdauer", zweck: .darstellung,
               von: 1000, bis: 6000, schritt: 100, vorgabe: 3200, einheit: .millisekunden,
               nurBei: [abrufweg]),
        Regler(id: "reglerNachleuchten", name: "Nachleuchten", zweck: .darstellung,
               von: 1000, bis: 15000, schritt: 500, vorgabe: 4000, einheit: .sekundenAusMillis,
               nurBei: [abrufweg]),
    ]

    /// Was in diesem Blick tatsaechlich etwas bewirkt.
    public static func fuer(blick: Int, zweck: Zweck? = nil) -> [Regler] {
        alle.filter { regler in
            (regler.nurBei.isEmpty || regler.nurBei.contains(blick))
                && (zweck == nil || regler.zweck == zweck)
        }
    }

    /// Ob es fuer diesen Blick ueberhaupt etwas zum Aufklappen gibt -- sonst
    /// wird das Aufklappelement gar nicht erst gezeigt.
    public static func hatDarstellung(blick: Int) -> Bool {
        !fuer(blick: blick, zweck: .darstellung).isEmpty
    }

    /// Schreibt einen Wert in den Web-Regler und loest dort `input` aus.
    ///
    /// Der Wert wird VORHER geklemmt: ein Wert ausserhalb der Grenzen wuerde
    /// vom Browser stillschweigend zurechtgebogen, und danach stuenden native
    /// und Web-Seite auf verschiedenen Zahlen, ohne dass es jemand merkt.
    public static func skript(fuer regler: Regler, wert: Double) -> String {
        let geklemmt = regler.klemme(wert)
        return """
        (function(){
          var e = document.getElementById('\(regler.id)');
          if (!e) return 'fehlt';
          e.value = '\(zahl(geklemmt))';
          e.dispatchEvent(new Event('input', {bubbles: true}));
          return 'ok';
        })();
        """
    }

    /// Blendet die Web-Bedienleiste aus. Die Ansichtsknoepfe b0..b4 werden
    /// dabei NICHT einzeln versteckt -- sie liegen in derselben Tafel.
    ///
    /// Der Klappknopf der Seite wird mitversteckt: er wuerde eine Leiste
    /// ein- und ausblenden, die es aus Sicht des Nutzers nicht mehr gibt.
    public static let webleisteAusblenden = """
    (function(){
      ['tafel','klapper'].forEach(function(id){
        var e = document.getElementById(id);
        if (e) e.style.display = 'none';
      });
    })();
    """

    /// Ohne Exponentialschreibweise und ohne Landeseinstellung -- `0,83` waere
    /// im DOM ungueltig und faellt dort stumm auf den alten Wert zurueck.
    static func zahl(_ wert: Double) -> String {
        if wert == wert.rounded() && abs(wert) < 1e15 {
            return String(Int(wert))
        }
        return String(format: "%.4f", wert)
    }
}
