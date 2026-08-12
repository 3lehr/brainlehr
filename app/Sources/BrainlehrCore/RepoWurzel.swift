// Reine Aufstiegslogik, um von einem Startpunkt aus die Repo-Wurzel zu
// finden -- vorher als private Kopie in DienstAufsicht.swift, jetzt geteilt,
// weil AusweisDienst.swift (Schritt 3) dieselbe Suche braucht. Die eigentliche
// Existenzpruefung (FileManager) kommt von aussen, wie bei PythonAuswahl.waehle
// -- hier nur der Pfad-Aufstieg, ohne Mock testbar.
//
// Foundation liefert nur NSString.deletingLastPathComponent, kein Fenster,
// keine Oberflaeche -- von der Schichtregel-Wache ausdruecklich erlaubt
// (verboten sind nur SwiftUI/AppKit).
import Foundation

public enum RepoWurzel {
    /// Steigt von `start` aus bis zu `maximalTiefe`-mal auf, bis `istWurzel`
    /// zutrifft. `nil`, wenn nichts gefunden wurde oder die Dateisystemwurzel
    /// erreicht ist.
    public static func suche(ab start: String, istWurzel: (String) -> Bool, maximalTiefe: Int = 10) -> String? {
        var aktuell = start
        for _ in 0..<maximalTiefe {
            if istWurzel(aktuell) { return aktuell }
            let eltern = (aktuell as NSString).deletingLastPathComponent
            if eltern == aktuell || eltern.isEmpty { return nil }
            aktuell = eltern
        }
        return nil
    }
}
