// I1 (ADR-014/016, PLAN_GESAMT_2026-08-13.md): Registrierung anforderbarer
// Bestandteile. Vertrag mit kern/bestandteile.py (Python-Katalog, dort
// ausfuehrlich begruendet -- dieselben Namen, dieselbe Auflagen-Entscheidung).
// tests/test_bestandteile.py::test_namen_stimmen_mit_swift_ueberein haelt
// beide Fassungen zusammen.
//
// WER FORDERT AN: die Domaene, im eigenen Paket -- optionales Feld
// "bestandteile" neben "domaene"/"quellen"/"regeln". Gelesen wird es lokal
// in DomaeneImportDienst.swift, aus dem dort ohnehin schon geparsten Paket --
// kein zweiter Weg zum Dienst noetig, kern/domaene.py bleibt unberuehrt.
//
// RECHTEFRAGE: eine Domaene kann sich damit KEINE Rechte selbst geben. Sie
// waehlt aus einem geschlossenen, hier fest verdrahteten Katalog; die Auflage
// jedes Eintrags ist Code, nicht Teil ihrer Anforderung. Anfordern schaltet
// Sichtbarkeit frei, es parametrisiert nichts.

/// Bekannte Bestandteile -- geschlossener Katalog, keine Erweiterung durch
/// ein Domaenenpaket moeglich (siehe Rechtefrage oben).
public enum Bestandteil: String, CaseIterable, Sendable {
    case dokumentfenster
    case tabellenkalkulation
}

public struct BestandteilEintrag {
    public let auflagenErfuellt: Bool
    public init(auflagenErfuellt: Bool) { self.auflagenErfuellt = auflagenErfuellt }
}

public enum BestandteilKatalog {
    public static let eintraege: [Bestandteil: BestandteilEintrag] = [
        .dokumentfenster: BestandteilEintrag(auflagenErfuellt: true),
        // ADR-016 Auflage 3 offen: Fremddatei-Import bis auf weiteres
        // gesperrt -- deshalb hier als nicht erfuellt gefuehrt, nicht erst
        // an der Ladestelle.
        // Auflagen aus ADR-016 seit 2026-08-15 erfuellt: Auflage 3 (kann eine
        // importierte Datei in `new Function` landen?) wurde gemessen und
        // aufgehoben, Auflage 1 (Positivliste) ist gebaut und gegen die
        // laufende Rechenmaschine belegt -- 37 von 511 Funktionen, geprueft
        // als Mengengleichheit statt als "die verbotenen sind weg".
        .tabellenkalkulation: BestandteilEintrag(auflagenErfuellt: true),
    ]
}

/// Entscheidet, welche angeforderten Bestandteile laden DUERFEN. Reine
/// Funktion ohne Zustand: unbekannte Namen und Eintraege mit unerfuellter
/// Auflage werden verworfen -- ohne Fehlermeldung an den Nutzer.
public enum BestandteilAnforderung {
    /// `katalog` ist einsetzbar, und das ist kein Testkomfort, sondern der
    /// Grund, warum die Verweigerungsregel ueberhaupt pruefbar BLEIBT:
    /// Gemessen 2026-08-16 steht im echten Katalog kein einziger Eintrag mehr
    /// mit unerfuellter Auflage (be74c1c1 hob die letzte auf). Ein Negativfall
    /// gegen den Produktivkatalog verschwindet damit lautlos -- die Regel
    /// stuende weiter im Code, geprueft wuerde sie von niemandem mehr.
    public static func gewaehrt(angefordert: [String],
                                katalog: [Bestandteil: BestandteilEintrag] = BestandteilKatalog.eintraege) -> Set<Bestandteil> {
        var ergebnis = Set<Bestandteil>()
        for name in angefordert {
            guard let b = Bestandteil(rawValue: name),
                  let eintrag = katalog[b],
                  eintrag.auflagenErfuellt
            else { continue }
            ergebnis.insert(b)
        }
        return ergebnis
    }
}
