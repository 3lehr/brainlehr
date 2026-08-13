# Enigma: was mit den beiden Machbarkeitsstudien geschieht

Angelegt 2026-08-13T17:55:00+0200. Aufgabe 8. Die Aufgabe nannte als nächsten
Schritt „Plan für die Verdrahtung der beiden Machbarkeitsstudien mit dem echten
Speicher — oder der belegte Nachweis, dass sie synthetisch bleiben sollen."

## Der gemessene Ist-Stand

Beide Studien sind grün und von guter Bauform: sie beweisen nicht, dass etwas
geht, sondern dass **Abschwächungen abgewiesen werden**.

| Datei | Zeilen | Tests | Was widerlegt wird |
|---|---|---|---|
| `tests/test_enigma_crypto_shredding_spike.py` | 125 | 6 | Schlüsselkopie, deterministische Ableitung, Klartext im Protokoll, geteilter Blob, Wiederherstellung ohne Anker |
| `tests/test_enigma_two_process_spike.py` | 564 | 6 | Wiedereinspielung, Widerruf, gelöschtes Subjekt, gemeinsamer Dateideskriptor, gleiche Benutzerkennung |

**Der Befund, der die Aufgabe umdreht.** Die tragenden Begriffe der Studien
kommen im Produktivcode **null**mal vor:

| Begriff | Fundstellen in `kern/` + `knowledge_mcp_server.py` |
|---|---|
| `grant_id` · `expiry` · `audience_policy` · `protected_edge_reads` | 0 |
| `recipient` · `nonce` | je 1, beides **Kommentare**, keine Verwendung |

Das ist keine fehlende Verdrahtung. Es sind **zwei verschiedene Modelle**:

- Die Studien entwerfen ein **Erlaubnismodell je Vorgang** — eine Erlaubnis mit
  Subjekt, Feldern, Zweck, Empfänger, Ablauf, Kennung und Einmalwert, einzeln
  widerrufbar.
- Der Speicher führt ein **Rollenmodell**: `knowledge_mcp_server.py` sagt es
  selbst — die Rolle legt Zweck und Feld fest, der Ausweis legt den Empfänger
  fest, die Zeile darf das nur **enger** machen.

Ein Rollenmodell kennt keinen Ablauf und keinen Widerruf einer einzelnen
Auskunft. „Verdrahten" hieße also nicht anschließen, sondern das zweite Modell
bauen.

## Die Alternativen, samt Ablehnungsgrund

1. **Erlaubnismodell bauen und die Studien daran hängen.** Abgelehnt für jetzt:
   Es ist ein eigenes Vorhaben, kein Schritt. Und es hat heute keinen Anlass —
   kein offener Fall verlangt Ablauf oder Einzelwiderruf.
2. **Studien löschen, weil sie nichts Produktives testen.** Abgelehnt: Sie
   sind der einzige Ort, an dem die Abschwächungen benannt sind. Gelöscht
   verlieren wir die Widerlegungen, nicht nur den Code.
3. **Studien so lassen und weiter als „offen" führen.** Abgelehnt: Genau daraus
   entsteht der Eindruck, es sei etwas gesichert, was nirgends greift — die
   Klasse, die heute zwölfmal aufgetreten ist.
4. **Gewählt: Studien bleiben synthetisch und werden als solche AUSGEWIESEN,
   und ihre Annahmen über den Speicher werden einzeln gegen den Speicher
   geprüft.** Das beantwortet die Frage, die wirklich beißt — nicht „ist der
   Entwurf gut", sondern „hat der Speicher die Eigenschaft, die der Entwurf
   voraussetzt".

## Was bewusst nicht getan wird, samt Preis

- **Kein Erlaubnismodell.** Preis: Ablauf und Einzelwiderruf bleiben unmöglich.
  Das gehört in eine eigene Aufgabe, wenn ein Fall es verlangt.
- **Keine Änderung an den Studien selbst.** Preis: 689 Zeilen Testcode prüfen
  weiterhin keinen Produktivpfad. Der Ausweis im Kopf der Datei macht das
  sichtbar, statt es zu beheben.

### Ein Schritt B gab es, er entfiel beim Schreiben des Auftrags

Er hätte gelautet: die Zusicherung „Ablehnung ohne Inhalt, Metadaten und
Grund" von `knowledge_read` auf Suche und Blättern ausdehnen. Beim Ausfüllen
der Zeile **Fakten** stellte sich heraus, dass `tests/test_freigabe_suchpfade.py`
das bereits vollständig deckt: Positivfall, Negativfall, ein eigener Leck-Test
über `count`, `children_count` und die Elternpfade — und eine Gegenprobe, die
belegt, dass der Test ohne die Prüfung rot wäre. Aufgabe 22 ist dafür
abgeschlossen.

Es ist heute der **zweite** Fall dieser Art — Schritt A des Regeldatei-Plans
war identisch mit der offenen Aufgabe 96. Beide Male hat die erzwungene
**Fakten**-Zeile die Dublette gefunden, nicht die Aufmerksamkeit. Der Preis
der Auftragsform ist Schreibarbeit; ihr Ertrag sind zwei nicht doppelt
vergebene Aufträge an einem Nachmittag.

## Woran sich Erfolg misst

Eine Prüfung, die vorher rot war: Der Speicher hält die Zusicherung, die beide
Studien voraussetzen — eine Ablehnung trägt keinen Inhalt, keine Metadaten und
keinen Grund. Für `knowledge_read` ist das belegt
(`test_enigma_hausmeister_contract.py`); für Suche und Blättern ist es zu
zeigen.

## Aufträge, fertig zum Übergeben

| | |
|---|---|
| **Tabu für alle Schritte** | `knowledge_mcp_server.py` wird in diesem Plan **nicht** geändert — kein Modellumbau. Ebenso tabu: `app/`, `berichte/`, `pflege/`, `~/.claude/`. |

### Schritt A · Die Studien als synthetisch ausweisen

| | |
|---|---|
| **Darf ändern** | `tests/test_enigma_crypto_shredding_spike.py`, `tests/test_enigma_two_process_spike.py` (nur Kopfkommentar), neue Datei in `tests/` |
| **Fakten** | Beide Kopfzeilen sagen bereits „synthetic … no production storage involved" bzw. „no P2 claim". Was fehlt, ist die Zahl: `grant_id`, `expiry`, `audience_policy`, `protected_edge_reads` kommen im Produktivcode 0-mal vor, `recipient` und `nonce` je einmal als Kommentar. |
| **Abnahme** | Eine Ratsche, die genau diese Liste prüft: findet sie einen der Begriffe im Produktivcode, schlägt sie an — dann ist das Modell im Bau und der Ausweis überholt. Rot-Probe: den Begriff testweise in eine Produktivdatei schreiben, Ratsche muss rot werden. |
| **Einsatz** | Ein grüner Test, der keinen Produktivpfad berührt, sieht in jeder Bilanz aus wie Absicherung. |

**Sieht der Code anders aus als hier beschrieben, halte dich an den Code und
melde die Abweichung.**
