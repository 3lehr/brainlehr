// Instrumentierung VOR jedem Univer-Import: jeder Aufruf von `new Function(...)`
// waehrend des gesamten Ladens/Renderns/Neuberechnens wird mitgeschnitten --
// Quelle des Strings, nicht nur ob WEBSERVICE im Bundle-Text vorkommt.
const __funcCalls = [];
const __RealFunction = window.Function;
const __FunctionProxy = new Proxy(__RealFunction, {
  construct(target, args) {
    __funcCalls.push(args.map((a) => String(a)).join(' || '));
    return Reflect.construct(target, args);
  },
  apply(target, thisArg, args) {
    __funcCalls.push('APPLY:' + args.map((a) => String(a)).join(' || '));
    return Reflect.apply(target, thisArg, args);
  },
});
window.Function = __FunctionProxy;
window.__funcCalls = __funcCalls;
// Eigentest der Instrumentierung selbst: dieser Aufruf MUSS in __funcCalls
// auftauchen, sonst ist die Messung unten wertlos (Selbsttest vor Messung).
new window.Function('return 1')();

import { createUniver, defaultTheme, LocaleType, merge } from '@univerjs/presets';
import { UniverSheetsCorePreset } from '@univerjs/preset-sheets-core';
import sheetsCoreEnUS from '@univerjs/preset-sheets-core/locales/en-US';
import '@univerjs/preset-sheets-core/lib/index.css';

const { univerAPI } = createUniver({
  locale: LocaleType.EN_US,
  locales: {
    [LocaleType.EN_US]: merge({}, sheetsCoreEnUS),
  },
  theme: defaultTheme,
  presets: [
    UniverSheetsCorePreset({
      container: 'app',
    }),
  ],
});

// Snapshot einer IMPORTIERTEN Tabellendatei (Univer-eigenes JSON-Format).
// Zelle A1 traegt eine Formel, die aus dem Dokumentmodell stammt -- nicht aus Programmcode.
const importedSnapshot = {
  id: 'probe3-import',
  name: 'probe3-import',
  appVersion: '0.25.1',
  locale: LocaleType.EN_US,
  styles: {},
  sheetOrder: ['sheet-probe3'],
  sheets: {
    'sheet-probe3': {
      id: 'sheet-probe3',
      name: 'Probe3',
      rowCount: 5,
      columnCount: 5,
      cellData: {
        0: {
          0: { f: '=WEBSERVICE("http://127.0.0.1:8933/getroffen-webservice")' },
          1: { f: '=SUM(fetch("http://127.0.0.1:8933/getroffen-sum"),1)' },
          2: { v: 'fetch("http://127.0.0.1:8933/getroffen-plain-value")' },
        },
      },
    },
  },
  // Versuch, eine Custom-Function-Registrierung ueber das generische
  // Plugin-Datenfeld `resources` einzuschleusen (wie eine Fremddatei es
  // versuchen wuerde, wenn ein solcher Weg existierte).
  resources: [
    {
      name: 'SHEET_FORMULA_PLUGIN',
      data: JSON.stringify({
        registeredFunctions: [
          ['function(){return fetch("http://127.0.0.1:8933/getroffen-resource")}', 'BOESE'],
        ],
      }),
    },
  ],
};

univerAPI.createWorkbook(importedSnapshot);

// Positivkontrolle (muss die Instrumentierung treffen): der EINZIGE laut
// Quelltext zulaessige Weg zu `new Function` -- Registrierung durch
// HOST-CODE, nicht durch importierte Daten. Beweist, dass die Messung oben
// (n=0) keine kaputte Instrumentierung ist, sondern echte Abwesenheit.
try {
  univerAPI.registerFunction({
    calculate: [[function () { return 42; }, 'HOSTPROBE', 'Positivkontrolle']],
  });
} catch (err) {
  window.__registerFunctionError = String(err && err.message || err);
}

// Nach Ablauf einer kurzen Frist Ergebnis an den lokalen Log-Server melden
// (localhost ist unter der Sandbox erlaubt, das ist kein Auswaertsgang).
setTimeout(() => {
  window.__univerReady = true;
  const payload = encodeURIComponent(JSON.stringify({
    funcCalls: __funcCalls,
    registerFunctionError: window.__registerFunctionError || null,
  }));
  fetch('http://127.0.0.1:8933/funcCalls?n=' + __funcCalls.length + '&data=' + payload).catch(() => {});
}, 4000);
