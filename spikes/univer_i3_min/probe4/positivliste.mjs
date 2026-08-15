// ADR-016 Auflage 1 -- die Positivliste selbst. Einzige Quelle der Wahrheit:
// wird von entry_positivliste.js im Browser eingelesen UND vom Ergebnis
// (siehe report()) an den Log-Server gemeldet, damit der Python-Test (siehe
// tests/test_univer_positivliste.py) gegen genau diese Liste prueft, nicht
// gegen eine zweite, von Hand kopierte Fassung.
//
// Herleitung (PLAN_I3_TABELLE_2026-08-15.md, ADR-016): gebraucht werden EUeR
// und UStVA (Summen, Prozente, Bedingungen) sowie die Fristenrechnung (Datum
// plus Zeitraum, Betrag mal Zeit, Sortierung). "Sperr im Zweifel" -- jede
// hier fehlende Funktion faellt beim ersten Gebrauch auf und ist billig
// nachzutragen; eine zu viel erlaubte faellt nie auf.
//
// AUSDRUECKLICH NICHT AUF DER LISTE, unabhaengig vom heutigen Bundle-Zustand
// (ADR-016 Auflage 2, Auftrag): WEBSERVICE (netzfaehig) und jede Funktion,
// die laut Quelltext ueber registerFunction/registerFunctions einen
// new-Function-Pfad erreichen kann (RemoteRegisterFunctionService). Diese
// Funktionen erscheinen so oder so nie in ALL_IMPLEMENTED_FUNCTIONS_SET (sie
// werden per registerFunction() zur Laufzeit dazugefuegt, nicht mitgeliefert)
// -- die Positivliste betrifft nur das mitgelieferte Univer-Grundsortiment.

export const ALLOWED_FUNCTIONS = [
  // Summen, Bedingungen, Grundrechnen (EUeR/UStVA)
  'SUM', 'SUMIF', 'SUMIFS',
  'IF', 'IFS', 'IFERROR', 'AND', 'OR', 'NOT',
  'ROUND', 'ROUNDUP', 'ROUNDDOWN', 'ABS',
  'MIN', 'MAX', 'AVERAGE', 'AVERAGEIF',
  'COUNT', 'COUNTA', 'COUNTIF', 'COUNTIFS',
  'PRODUCT',

  // Datum, Zeitraum, Sortierung (Fristenrechnung)
  'DATE', 'DATEDIF', 'EDATE', 'EOMONTH', 'DAYS',
  'TODAY', 'NOW', 'YEAR', 'MONTH', 'DAY', 'WEEKDAY',
  'NETWORKDAYS',
  'SORT', 'SORTBY', 'RANK.EQ',
];
