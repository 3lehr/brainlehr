# Ein menschlicher Entscheid, den die Maschine nicht erzeugen kann

Stand 2026-08-12T21:00:00+0200. Anlass: Betreiberfrage, wörtlich — *„dann
brauchen wir einen menschlichen trigger? vll die app die wir gerage bauen?"*

## Der gemessene Ist-Stand

| | Befund |
|---|---|
| Auslöser | Betreiber entschied eine Hausnorm Rang 1 ausdrücklich; das Eintragen scheiterte zweimal (`knowledge_add`, `knowledge_update`) |
| Grund | Die Schranke verlangt für Rang 1/2 einen menschlichen Entscheider und leitet `norm_entschieden_von` aus dem Ausweis des **Schreibenden** ab |
| Wer schreibt | immer die Maschine — der Mensch entscheidet im Gespräch |
| Fehlende Unterscheidung | **Entscheider** gegen **Schreiber**, wie Autor und Co-Autor in einem Commit |
| Vorhandene Rollen | `kern/ausweis.py`: betreiber `*`, meldeamt `ausweis:ausstellen`, fachkundig/schreiber `wissen:lesen` |
| Behelf bis dahin | Die Anweisung steht in `~/.claude/CLAUDE.md` und erreicht so jede Sitzung |

## Warum ein Knopf in der App nicht genügt

**Belegt in derselben Sitzung, nicht vermutet:** Ein Subagent löste heute den
Knopf „Erneut versuchen" der Dienstaufsicht per Accessibility-Klick aus — als
Teil seiner Abnahme, völlig regelkonform. Genau diese Fähigkeit macht jeden
Knopf als Menschbeleg wertlos. Wer klicken kann, kann bestätigen.

Dasselbe gilt für: ein Häkchen, eine Texteingabe, ein Bestätigungsdialog, einen
Menüeintrag. Alles davon ist über AppleScript oder die Bedienungshilfen
erreichbar, und der Assistent hat beides.

## Die Alternativen

**A — Knopf in der App.** Abgelehnt, siehe oben. Er sieht aus wie ein Beleg
und ist keiner. Das ist die schlechtere Sorte Fehler, weil sie Sicherheit
vortäuscht.

**B — Der Betreiber trägt es selbst über die Kommandozeile ein.** Funktioniert
heute schon und braucht nichts Neues. Abgelehnt als Regelfall, weil es genau
die Handarbeit ist, die er loswerden wollte — aber es bleibt der Rückweg,
wenn C nicht verfügbar ist.

**C — Systemauthentisierung in der App (gewählt).** macOS bietet über
`LocalAuthentication` eine Prüfung „ist gerade ein Mensch da": Touch ID, Apple
Watch oder das Anmeldekennwort. Der Assistent kann Touch ID nicht simulieren,
und das Kennwort tippt der Betreiber ohnehin selbst — das ist bereits eine
bestehende Regel, hier fällt sie mit der technischen Notwendigkeit zusammen.

**D — Ein zweiter Ausweis nur für die App.** Ergänzt C, ersetzt es nicht: Die
App hält ein Geheimnis, das der Assistent nicht liest. Allein genügt das
nicht, weil ein Geheimnis auf derselben Maschine liegt und der Assistent dort
Dateien lesen kann — die Systemauthentisierung ist der Teil, der nicht auf
einer Datei beruht.

## Der Ablauf

1. **Der Assistent schlägt vor.** Er schreibt den Knoten wie bisher, ohne Rang,
   und markiert ihn als Vorschlag. Das kann er heute schon.
2. **Die App zeigt die offenen Vorschläge.** Titel, Wortlaut der Zustimmung,
   vorgeschlagener Rang, Herkunft.
3. **Der Betreiber entscheidet, und die App verlangt dafür die
   Systemauthentisierung.** Erst danach schreibt sie — mit ihrem eigenen
   Ausweis, nicht mit dem des Assistenten.
4. **Der Datensatz trennt beides:** wer entschieden hat, wer geschrieben hat,
   womit belegt.

## Was der Beleg wirklich aussagt — ehrlich abgegrenzt

Die Systemauthentisierung belegt: **an diesem Rechner war in diesem Moment ein
Mensch anwesend und hat sich ausgewiesen.** Sie belegt nicht, dass er den
Inhalt gelesen oder verstanden hat. Diese Grenze gehört in das Feld, nicht in
eine Fußnote — sonst wird aus „ein Mensch war da" später „der Betreiber hat
das geprüft".

Zweite Grenze: Läuft die App auf demselben Rechner wie der Assistent, ist die
Trennung organisatorisch, nicht physikalisch. Ein Angreifer mit vollem Zugriff
auf diesen Rechner umgeht alles. Das ist hinnehmbar, weil die Schranke gegen
**versehentliche Selbstermächtigung** gebaut ist, nicht gegen einen Angreifer —
aber es wird benannt statt verschwiegen.

## Was bewusst nicht getan wird, samt Preis

- **Die Schranke wird nicht gelockert.** Kein Sonderweg, kein Kennzeichen
  „vom Menschen gesagt". Preis: Bis die App das kann, bleiben Ränge offen.
  Das ist der richtige Preis — eine Norm, die sich eine Maschine selbst gibt,
  ist genau das, wogegen die Schranke steht.
- **Keine Fernbestätigung** (Telefon, Netz, zweites Gerät). Preis: Der
  Betreiber muss am Rechner sein. Gewinn: keine neue Außenkante.

## Reihenfolge, bindend

1. Der Datensatz lernt die Unterscheidung Entscheider/Schreiber samt Belegart.
   **Zuerst** — solange sie fehlt, hat die App nichts, wohin sie schreiben
   könnte, und ein nachträglich eingezogenes Feld lässt jeden Altbestand
   unentscheidbar.
2. Die App zeigt offene Vorschläge (nur lesen).
3. Systemauthentisierung und Schreiben mit eigenem Ausweis.

## Woran sich Erfolg messen lässt

- Ein Rang-1-Knoten existiert, dessen Entscheider ein Mensch ist und dessen
  Schreiber die App — beides getrennt im Datensatz nachlesbar.
- **Rot-Probe, die den Kern trifft:** Der Assistent versucht denselben Weg
  ohne Systemauthentisierung und wird abgewiesen. Ohne diese Probe ist die
  Trennung eine Absicht.
- Der bestehende Weg über den Ausweis des Assistenten bleibt für Rang 3 und
  rangloses Wissen unverändert nutzbar — gemessen, nicht angenommen.
