// Reine Auswahllogik: aus einer Liste moeglicher Python-Interpreter denjenigen
// waehlen, der die noetige Faehigkeit hat -- nach Vorbild
// pflege/wissensraum_start.sh (sucht nach "import cryptography", nicht nach
// einem festen Pfad, weil Apples Systempython das Paket nicht hat).
//
// Die eigentliche Pruefung (Prozess starten, Import versuchen) braucht
// Foundation.Process und lebt darum in BrainlehrApp; hier nur die Auswahl
// aus bereits geprueften Ergebnissen -- ohne Mock testbar.

public enum PythonAuswahl {
    /// Erster Pfad aus `kandidaten`, der laut `faehig` die Faehigkeit hat.
    /// `nil`, wenn keiner passt (dann fehlt auf dem Rechner ein brauchbarer
    /// Interpreter -- die Oberflaeche zeigt das als "Dienst nicht startbar").
    public static func waehle(kandidaten: [String], faehig: (String) -> Bool) -> String? {
        for pfad in kandidaten where faehig(pfad) {
            return pfad
        }
        return nil
    }
}
