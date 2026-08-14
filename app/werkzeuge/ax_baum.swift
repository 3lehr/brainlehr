// Liest den Bedienungshilfen-Baum der laufenden App -- damit ein PROGRAMM prueft,
// was sonst nur ein Bildschirmabzug zeigt.
//
// ANLASS: docs/STARTPROMPT_GRUNDARCHITEKTUR_2026-08-13.md fuehrt als
// beweiskraeftigsten Punkt an, die eigene Mac-App sei nicht programmatisch
// bedienbar -- "ihr Bedienungshilfen-Baum liess sich nicht auslesen. Um das
// selbst gebaute Programm zu pruefen, mussten Bildschirmabzuege gemacht werden."
//
// GEMESSEN 2026-08-14: Die Behauptung haelt nicht. 281 Knoten, 202 mit
// zugaenglichem Namen, vollstaendige Struktur bis in den Sitzungsstrom. Der
// frueher gescheiterte Versuch war eine Eigenschaft des Aufbaus, nicht der
// Plattform -- genau die Fehlform, gegen die die Hausregel den Satz verlangt
// "MEIN Aufbau kann das nicht, weil ich X nicht gemessen habe".
//
// ZWEI AUSGABEN, und die zweite ist der eigentliche Zweck:
//   --baum     Struktur zum Ansehen und Vergleichen
//   --pruefen  WCAG 2.2: bedienbare Elemente ohne zugaenglichen Namen.
//              Der zugaengliche Name ist zugleich der Griff, an dem
//              Automatisierung, Test und KI die Oberflaeche anfassen -- deshalb
//              faellt hier Barrierefreiheit mit Maschinenbedienbarkeit zusammen.
//
// DER FEHLALARM, gegen den dieses Werkzeug gebaut ist: Ein naiver Zaehler meldet
// 40 namenlose Bedienelemente. Alle 40 stammen vom SYSTEM -- 7 Knoepfe mit
// identifizierender Subrolle (Scrollpfeile, Schliessen/Vollbild/Minimieren) und
// 33 Menuetrenner in Systemmenues. Echte Befunde: null. Ohne diesen Filter waere
// die Klasse aus der Beobachterperspektive gebildet und haette bei 0 von 40
// getroffen (L-aa889c).
//
// Kein Fremdpaket: ApplicationServices liegt im System.
// Aufruf: xcrun swift app/werkzeuge/ax_baum.swift [--baum|--pruefen|--selftest] [bundle-id]

import Foundation
import ApplicationServices
import AppKit

let STANDARD_BUNDLE = "de.brainlehr.atelier"

// Subrollen, die das System vergibt: sie IDENTIFIZIEREN das Element bereits,
// ein zusaetzlicher Titel waere Doppelung. Bewusst als Liste und nicht als
// "hat irgendeine Subrolle" -- eine unbekannte Subrolle soll auffallen.
let SYSTEM_SUBROLLEN: Set<String> = [
    "AXIncrementArrow", "AXDecrementArrow", "AXIncrementPage", "AXDecrementPage",
    "AXCloseButton", "AXMinimizeButton", "AXFullScreenButton", "AXZoomButton",
    "AXSortButton", "AXToolbarButton",
]

let BEDIENBAR: Set<String> = [
    "AXButton", "AXCheckBox", "AXRadioButton", "AXPopUpButton",
    "AXTextField", "AXTextArea", "AXSlider", "AXMenuItem", "AXLink",
]

/// Ist ein namenloses Bedienelement vom System geliefert -- also kein Mangel?
///
/// Rein, ohne Fenster, ohne laufende App: darum im Selbsttest pruefbar.
func istSystemEigen(rolle: String, subrolle: String?, pfad: [String]) -> Bool {
    if let s = subrolle, SYSTEM_SUBROLLEN.contains(s) { return true }
    // Menuetrenner tragen systembedingt keinen Titel. Sie liegen ausnahmslos
    // unter der Menueleiste; eigene Bedienelemente der App tun das nie.
    if rolle == "AXMenuItem" && pfad.contains(where: { $0.hasPrefix("AXMenuBar") }) { return true }
    return false
}

func attr(_ el: AXUIElement, _ k: String) -> Any? {
    var w: CFTypeRef?
    return AXUIElementCopyAttributeValue(el, k as CFString, &w) == .success ? w : nil
}

func text(_ el: AXUIElement, _ k: String) -> String? {
    guard let s = attr(el, k) as? String, !s.isEmpty else { return nil }
    return s
}

func selbsttest() -> Int32 {
    var fehler = 0
    func pruefe(_ was: String, _ ist: Bool, _ soll: Bool) {
        if ist != soll { print("FEHLT: \(was) -- ist \(ist), soll \(soll)"); fehler += 1 }
    }
    // Systemknopf mit Subrolle: kein Mangel.
    pruefe("Scrollpfeil", istSystemEigen(rolle: "AXButton", subrolle: "AXIncrementArrow", pfad: ["AXWindow"]), true)
    pruefe("Schliessknopf", istSystemEigen(rolle: "AXButton", subrolle: "AXCloseButton", pfad: ["AXWindow"]), true)
    // Menuetrenner unter der Menueleiste: kein Mangel.
    pruefe("Menuetrenner", istSystemEigen(rolle: "AXMenuItem", subrolle: nil, pfad: ["AXApplication", "AXMenuBar", "AXMenu"]), true)
    // NEGATIVFALL, der wichtigere: ein eigener namenloser Knopf im Fenster
    // MUSS als Mangel durchkommen, sonst prueft das Werkzeug nichts.
    pruefe("eigener Knopf ohne Namen", istSystemEigen(rolle: "AXButton", subrolle: nil, pfad: ["AXWindow", "AXGroup"]), false)
    // Grenzwert: ein Menuepunkt, der NICHT unter der Menueleiste haengt --
    // etwa in einem Aufklappmenue im Fenster -- ist ein echter Mangel.
    pruefe("Menuepunkt im Fenster", istSystemEigen(rolle: "AXMenuItem", subrolle: nil, pfad: ["AXWindow", "AXPopUpButton"]), false)
    // Grenzwert: unbekannte Subrolle darf NICHT durchgewunken werden.
    pruefe("unbekannte Subrolle", istSystemEigen(rolle: "AXButton", subrolle: "AXIrgendwasNeues", pfad: ["AXWindow"]), false)
    print(fehler == 0 ? "Selbsttest: 6 Faelle, alle gruen" : "Selbsttest: \(fehler) Fehler")
    return fehler == 0 ? 0 : 1
}

// ── Ablauf ───────────────────────────────────────────────────────────────
let argumente = CommandLine.arguments.dropFirst()
let modus = argumente.first(where: { $0.hasPrefix("--") }) ?? "--pruefen"
let bundle = argumente.first(where: { !$0.hasPrefix("--") }) ?? STANDARD_BUNDLE

if modus == "--selftest" { exit(selbsttest()) }

// Vorbedingung 1 -- Recht. Ein Fehlschlag HIER ist eine Aussage ueber den
// Messaufbau, nicht ueber die App. Das zu trennen ist der halbe Zweck.
guard AXIsProcessTrusted() else {
    print("NICHT MESSBAR: Der messende Prozess hat kein Bedienungshilfen-Recht.")
    print("Jede Abfrage liefert dann kAXErrorAPIDisabled, unabhaengig von der App.")
    print("Das ist KEIN Befund ueber die Plattform -- das Recht vergibt der Mensch")
    print("in den Systemeinstellungen fuer das aufrufende Programm.")
    exit(2)
}

// Vorbedingung 2 -- laeuft die App?
guard let ziel = NSWorkspace.shared.runningApplications.first(where: { $0.bundleIdentifier == bundle }) else {
    print("NICHT MESSBAR: keine laufende Anwendung mit Bundle '\(bundle)'.")
    print("Starten: bash app/bauen.sh && open app/Ausgabe/atelier.app")
    exit(2)
}
let app = AXUIElementCreateApplication(ziel.processIdentifier)

// Vorbedingung 3 -- antwortet sie?
var roh: CFTypeRef?
let code = AXUIElementCopyAttributeValue(app, kAXRoleAttribute as CFString, &roh)
guard code == .success else {
    print("NICHT MESSBAR: Wurzelknoten nicht lesbar, Code \(code.rawValue).")
    print(code == .cannotComplete ? "Der Prozess antwortet nicht -- haengt er?" : "")
    exit(3)
}

var knoten = 0, mitNamen = 0
var maengel: [(String, String)] = []
var systemEigen = 0

func gehe(_ el: AXUIElement, pfad: [String], tiefe: Int) {
    if tiefe > 14 { return }
    knoten += 1
    let rolle = text(el, kAXRoleAttribute as String) ?? "?"
    let subrolle = text(el, kAXSubroleAttribute as String)
    let name = text(el, kAXTitleAttribute as String)
        ?? text(el, kAXDescriptionAttribute as String)
        ?? text(el, kAXValueAttribute as String)
    if name != nil { mitNamen += 1 }

    if BEDIENBAR.contains(rolle) && name == nil {
        if istSystemEigen(rolle: rolle, subrolle: subrolle, pfad: pfad) {
            systemEigen += 1
        } else {
            maengel.append((rolle, pfad.suffix(4).joined(separator: " / ")))
        }
    }
    if modus == "--baum" {
        print(String(repeating: "  ", count: tiefe) + rolle + (name.map { " · \"\($0.prefix(70))\"" } ?? ""))
    }
    let eigen = name.map { "\(rolle)(\($0.prefix(24)))" } ?? rolle
    if let kinder = attr(el, kAXChildrenAttribute as String) as? [AXUIElement] {
        for k in kinder { gehe(k, pfad: pfad + [eigen], tiefe: tiefe + 1) }
    }
}

gehe(app, pfad: [], tiefe: 0)

print("\n=== \(ziel.localizedName ?? bundle), PID \(ziel.processIdentifier) ===")
print("Knoten: \(knoten) · mit zugaenglichem Namen: \(mitNamen)")
print("namenlose Bedienelemente vom System (kein Mangel): \(systemEigen)")
if maengel.isEmpty {
    print("MANGEL: keiner. Jedes eigene Bedienelement traegt einen zugaenglichen Namen.")
    exit(0)
}
print("MANGEL: \(maengel.count) eigene(s) Bedienelement(e) ohne zugaenglichen Namen:")
for (rolle, ort) in maengel { print("  \(rolle)  <-  \(ort)") }
exit(1)
