# STAND brainlehr — 2026-08-14T02:55:00+0200

**Der Fund der Nacht:** `knowledge_add` schrieb ueber Stunden **null Vektorzeilen**. Nicht der Dienst — der laufende MCP-Prozess (Start 21:44) war aelter als die Identitaetsaenderung (23:51, `cd56071`) und schrieb `bge-m3` statt `bge-m3@ctx2048`; der Trigger wies ab, ein `except: pass` verschluckte seine Meldung. Der Melder dafuer existiert, ist verdrahtet, funktioniert — und haengt an `UserPromptSubmit`, feuert im Selbstlauf also nie (`L-1228cf`). Behoben: Grund haengt jetzt am Schreibvorgang (`3419f76`). **Wirkt erst nach einem Neustart der Sitzung.**

**Erledigt:** 80 Vektor-Identitaet · 86 Metaphern (Nullergebnis, Regeln bleiben woertlich) · 91 zwei `/api/generate`-Wege liefen an der Rollensperre vorbei · 69 Abschneidegrenze wird gerechnet und gemeldet. 110 Aufgaben: 81 erledigt, 12 angefangen, 17 offen.

**Offen mit Beleg:** 93 Modellwechsel bleibt **gesperrt** — die Positivkontrolle laesst sich nicht reproduzieren, weil sieben der acht Ursprungsknoten seither geaendert wurden und die Vergleichssaetze nie woertlich abgelegt waren (`L-1d31c2`). Was fehlt, ist ein eingefrorener Kontrollsatz, kein besseres Werkzeug.

**Suite:** 1386 passed, 1 skipped, 11 xfailed, kein roter Test. **Fallen:** zsh zerlegt unquotierte Variablen NICHT — `pytest $A` meldet „no tests ran" statt eines Fehlers (`L-103548`) · verschmutzten Wert nach seiner Herkunft fragen statt bisezieren, `__code__.co_filename` (`L-305730`) · wer eine Funktion kopiert, verliert die Schranke eine Ebene darueber (`L-361755`) · eine Kontrollmessung auf lebendem Bestand hat kein Datum (`L-1d31c2`). **Wartet auf den Betreiber:** Klarname geschwaerzte PDF · 101 · 105 · 77 (beruehrt hub) · Push.
