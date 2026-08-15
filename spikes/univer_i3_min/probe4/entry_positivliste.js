// ADR-016 Auflage 1/2 (Positivliste), Schritt 2 von PLAN_I3_TABELLE_2026-08-15.md.
//
// Univer erzwingt technisch nur eine VERBOTSLISTE (ALL_IMPLEMENTED_FUNCTIONS
// wird per .concat() angehaengt, nie ersetzt -- gemessen und dokumentiert in
// ADR-016). Diese Datei baut die Positivliste DARAUF: alle mitgelieferten
// Funktionen aufzaehlen, die erlaubte Menge (positivliste.mjs) abziehen, den
// Rest per unregisterExecutors() aktiv abmelden -- VOR jeder Formelberechnung
// und VOR jedem Dateiimport.
//
// Der entscheidende Test ist nicht "die verbotenen sind weg", sondern:
// tatsaechlich verfuegbare Menge NACH der Einrichtung == erlaubte Menge.
// Kaeme in einer kuenftigen Univer-Fassung eine neue Funktion hinzu, faellt
// sie bei "sind die verbotenen weg" nicht auf (sie stand ja nie auf der
// Verbotsliste) -- bei "ist verfuegbar == erlaubt" schon, weil die neue
// Funktion die verfuegbare Menge groesser macht als die erlaubte.

import { createUniver, defaultTheme, LocaleType, merge } from '@univerjs/presets';
import { UniverSheetsCorePreset } from '@univerjs/preset-sheets-core';
import sheetsCoreEnUS from '@univerjs/preset-sheets-core/locales/en-US';
import '@univerjs/preset-sheets-core/lib/index.css';
import { ALL_IMPLEMENTED_FUNCTIONS_SET } from '@univerjs/engine-formula';
import { IDescriptionService } from '@univerjs/sheets-formula';
import { ALLOWED_FUNCTIONS } from './positivliste.mjs';

function meldeFehler(stelle, fehler) {
  const payload = encodeURIComponent(JSON.stringify({ fehler: stelle + ': ' + String(fehler && fehler.stack || fehler) }));
  fetch('http://127.0.0.1:8933/ergebnis?data=' + payload).catch(() => {});
}
window.addEventListener('error', (e) => meldeFehler('window.onerror', e.error || e.message));
window.addEventListener('unhandledrejection', (e) => meldeFehler('unhandledrejection', e.reason));

const { univerAPI } = createUniver({
  locale: LocaleType.EN_US,
  locales: { [LocaleType.EN_US]: merge({}, sheetsCoreEnUS) },
  theme: defaultTheme,
  presets: [UniverSheetsCorePreset({ container: 'app' })],
});

// Grenzwert "doppelter Eintrag": ein Set entfernt Duplikate von selbst, ohne
// dass unregisterExecutors zweimal denselben Namen sieht.
const erlaubtMenge = new Set(ALLOWED_FUNCTIONS);
const mitgeliefert = [...ALL_IMPLEMENTED_FUNCTIONS_SET];

// Die eigentliche Abmeldeschleife -- das IST die Positivliste, konstruiert
// auf der Verbotsliste (ADR-016, "Aufloesung").
const abzumelden = mitgeliefert.filter((name) => !erlaubtMenge.has(name));

// WICHTIG, per Messung dieser Probe: UniverFormulaEnginePlugin ist je
// UNIVER_SHEET-Einheit gescopet (redi-Kind-Injektor). Der FunctionService,
// den man VOR createWorkbook() ueber univerAPI.getFormula()._functionService
// bekommt, ist eine leere Instanz (getExecutors().size === 0) -- die
// eigentliche Registrierung (FormulaController._registerFunctions) laeuft
// erst, wenn die Sheet-Einheit onReady erreicht, also NACH createWorkbook().
// Deshalb: erst das Workbook anlegen, dann den Formel-Motor holen, dann
// abmelden -- und trotzdem VOR der ersten gesetzten Formel (siehe unten),
// wie ADR-016 es verlangt.
const workbook = univerAPI.createWorkbook({
  id: 'probe4-positivliste',
  name: 'probe4-positivliste',
  appVersion: '0.25.1',
  locale: LocaleType.EN_US,
  styles: {},
  sheetOrder: ['sheet-probe4'],
  sheets: {
    'sheet-probe4': {
      id: 'sheet-probe4',
      name: 'Probe4',
      rowCount: 10,
      columnCount: 5,
      cellData: {
        0: { 0: { v: 100 }, 1: { v: 250 } }, // A1, B1 -- Rohwerte fuer den Belegtest
      },
    },
  },
});
const sheet = workbook.getActiveSheet();

const formulaEngine = univerAPI.getFormula();
// _functionService/_injector sind in der .d.ts als privat/protected markiert,
// zur Laufzeit aber gewoehnliche Felder (TS-Sichtbarkeit ist rein statisch) --
// das ist der einzige Weg an unregisterExecutors, weil die oeffentliche
// Facade nur registerFunction/registerAsyncFunction kennt (siehe ADR-016).
const functionService = formulaEngine._functionService;
window.__vorAbmeldungExecutorAnzahl = functionService.getExecutors().size;

// unregisterExecutors ist der SICHERHEITSRELEVANTE Teil -- er entzieht der
// Formel-Engine die tatsaechliche Ausfuehrung, eine abgemeldete Funktion
// rechnet danach nicht mehr, sie ergibt #NAME? (siehe ADR-016, WEBSERVICE-
// Messung). Das ist die Positivliste in Wirkung. Laeuft noch VOR jeder
// gesetzten Formel (siehe setValue-Aufrufe weiter unten).
functionService.unregisterExecutors(...abzumelden);

// Menue/Autovervollstaendigung ebenfalls bereinigen -- kein Sicherheitsschritt
// (die Ausfuehrung ist bereits oben gesperrt), nur damit abgemeldete
// Funktionen nicht mehr als Vorschlag erscheinen. IDescriptionService haengt
// an einem PLUGIN-scoped Unterinjektor (UniverSheetsFormulaPlugin.onStarting),
// nicht am root-Injector von formulaEngine._injector -- redi loest von einem
// Elter-Injector nie in einen Kind-Injector hinein auf. Bewusst optional:
// schlaegt die Suche fehl, bleibt nur die Kosmetik aus, die Sperre oben steht
// unabhaengig davon.
try {
  formulaEngine._injector.get(IDescriptionService).unregisterDescriptions(abzumelden);
} catch (err) {
  console.warn('descriptionService (kosmetisch, keine Sperre):', err);
}

// Messung: welche der mitgelieferten Funktionen sind JETZT tatsaechlich
// ausfuehrbar? Das ist der Vergleichswert, nicht "abzumelden ist leer".
const tatsaechlichVerfuegbar = mitgeliefert.filter((name) => functionService.hasExecutor(name));

// Benannte Bereiche VOR der ersten Formel, die sie referenziert (ADR-016
// Auflage 4) -- auch wenn diese Probe kein gespeichertes Blatt ausliefert,
// demonstriert sie die Bauform, die der kommende Bildschirm erzwingen muss.
workbook.insertDefinedName('erloese', "Probe4!$A$1:$B$1");

// Positivtest: eine ERLAUBTE Formel ueber einen benannten Bereich rechnet
// weiterhin richtig (100 + 250 = 350).
sheet.getRange('C1').setValue({ f: '=SUM(erloese)' });
// Negativtest 1, woertlich verlangt: WEBSERVICE nach der Einrichtung.
sheet.getRange('C2').setValue({ f: '=WEBSERVICE("http://127.0.0.1:8933/darf-nicht-aufgerufen-werden")' });
// Negativtest 2 (Grenzwert "Formel mit unbekanntem Namen"): ein Name, den es
// bei Univer nie gab -- muss genauso #NAME? ergeben wie eine abgemeldete
// eingebaute Funktion, nicht anders behandelt werden.
sheet.getRange('C3').setValue({ f: '=NICHTVORHANDEN(1)' });
// Negativtest 3 -- der eigentliche Beleg, dass unregisterExecutors wirkt und
// nicht nur eine ohnehin schon tote Funktion trifft (WEBSERVICE hatte laut
// ADR-016 nie einen Executor). CONCATENATE ist eine ECHTE, mitgelieferte
// Funktion (in ALL_IMPLEMENTED_FUNCTIONS_SET, nicht auf der Positivliste) --
// vor der Abmeldung haette sie 'ab' berechnet, danach muss sie #NAME? sein.
sheet.getRange('C4').setValue({ f: '=CONCATENATE("a","b")' });

formulaEngine.executeCalculation();

setTimeout(() => {
  const ergebnis = {
    debug_executors_vor_abmeldung: window.__vorAbmeldungExecutorAnzahl,
    mitgeliefert_anzahl: mitgeliefert.length,
    erlaubt_anzahl: erlaubtMenge.size,
    erlaubt: [...erlaubtMenge].sort(),
    verfuegbar_anzahl: tatsaechlichVerfuegbar.length,
    verfuegbar: [...tatsaechlichVerfuegbar].sort(),
    abgemeldet_anzahl: abzumelden.length,
    c1_summe_ueber_benannten_bereich: sheet.getRange('C1').getValue(),
    c2_webservice: sheet.getRange('C2').getValue(),
    c3_unbekannte_funktion: sheet.getRange('C3').getValue(),
    c4_abgemeldete_echte_funktion_concatenate: sheet.getRange('C4').getValue(),
  };
  window.__ergebnis = ergebnis;
  const payload = encodeURIComponent(JSON.stringify(ergebnis));
  fetch('http://127.0.0.1:8933/ergebnis?data=' + payload).catch(() => {});
}, 2500);
