# Beiträge zu brainlehr

Danke für das Interesse. Bevor Code fließt: **erst ein Issue, dann Code.** Das
schützt dich davor, umsonst zu arbeiten, und uns davor, einen Beitrag ablehnen
zu müssen, der schon geschrieben ist.

---

## 1. Der Ablauf

1. **Issue eröffnen** und beschreiben, was du ändern willst und warum.
2. Warten, bis das Vorhaben bestätigt ist. Ohne Bestätigung kein Merge — auch
   nicht bei gutem Code.
3. Branch vom aktuellen Arbeitszweig, nicht von `main`.
4. Pull Request mit dem unterzeichneten CLA (Abschnitt 3) und einem
   Sign-off je Commit (Abschnitt 4).
5. Jeder Beitrag braucht eine Prüfung, die **vor** der Änderung fehlschlägt und
   danach besteht. Ein Test, der von Anfang an grün war, beweist nur, dass er
   die Änderung nicht berührt.

## 2. Die Lizenz, unter der du beiträgst

brainlehr steht unter der **GNU Affero General Public License v3.0** (siehe
[`LICENSE`](./LICENSE)). Dein Beitrag wird unter derselben Lizenz
veröffentlicht.

**Zusätzlich** räumst du dem Projektinhaber die in Abschnitt 3 beschriebenen
Rechte ein. Der Grund steht offen in [`LICENSE_FAQ.md`](./LICENSE_FAQ.md): das
Projekt soll später auch **kommerziell lizenziert** werden können. Ohne diese
Rechteeinräumung wäre das für jede Datei unmöglich, an der jemand anders
mitgeschrieben hat — ein einziger Beitrag ohne CLA blockiert die kommerzielle
Lizenzierung der gesamten Datei dauerhaft.

Wenn dir das zu weit geht: das ist eine legitime Entscheidung. Sag es im Issue,
dann finden wir eine andere Form (Fehlerbericht, Reproduktionsfall,
Dokumentation), die keine Rechteeinräumung braucht.

## 3. Contributor License Agreement (CLA)

> **Dies ist ein Entwurf und keine Rechtsberatung.** Der Text ist bewusst weit
> gefasst. Vor dem ersten Einsatz gegenüber Dritten gehört er einer
> Rechtsanwältin oder einem Rechtsanwalt für Urheber- und IT-Recht vorgelegt.
> Bis dahin gilt er als Absichtserklärung des Projekts, nicht als geprüftes
> Vertragswerk.

Mit dem Einreichen eines Beitrags erklärst du Folgendes:

**§1 Rechteeinräumung.** Du räumst dem Projektinhaber an deinem Beitrag ein
**ausschließliches, räumlich, zeitlich und inhaltlich unbeschränktes,
unwiderrufliches, übertragbares und unterlizenzierbares Nutzungsrecht** für
alle bekannten und künftigen Nutzungsarten ein. Das umfasst insbesondere
Vervielfältigung, Verbreitung, öffentliche Zugänglichmachung, Bearbeitung,
Umgestaltung und die Verwertung der bearbeiteten Fassung — auch kommerziell,
auch unter einer anderen als der AGPLv3, auch als Teil eines geschlossenen
Produkts.

*Hinweis zum deutschen Recht:* Das Urheberrecht selbst ist nach § 29 Abs. 1
UrhG nicht übertragbar. Eine vollständige Rechteübertragung nach US-Vorbild
("copyright assignment") ist hier nicht möglich; § 1 ist deshalb als
umfassende Einräumung ausschließlicher Nutzungsrechte formuliert — das ist die
weitestgehende Form, die das deutsche Recht kennt. Soweit deine Rechtsordnung
eine vollständige Übertragung zulässt, überträgst du zusätzlich alle
übertragbaren Rechte.

**§2 Rückfallrecht für dich.** Du behältst das Recht, deinen eigenen Beitrag
uneingeschränkt weiter zu nutzen, zu veröffentlichen und anderen zu
lizenzieren. Die Einräumung nach §1 nimmt dir nichts weg; sie gibt dem Projekt
etwas dazu.

**§3 Patente.** Du erteilst dem Projektinhaber und allen Nutzern des Projekts
eine unwiderrufliche, weltweite, gebührenfreie Lizenz an allen Patentansprüchen,
die du kontrollierst und die durch deinen Beitrag oder dessen Verbindung mit
dem Projekt verletzt würden. Erhebst du gegen jemanden eine Patentklage wegen
des Projekts, erlöschen die dir aus dem Projekt eingeräumten Lizenzen mit dem
Tag der Klageerhebung.

**§4 Urheberpersönlichkeitsrechte.** Soweit gesetzlich zulässig, verzichtest du
auf die Ausübung von Urheberpersönlichkeitsrechten gegenüber dem Projektinhaber
und dessen Lizenznehmern — insbesondere auf das Recht auf Namensnennung in
jeder einzelnen abgeleiteten Fassung. Ein nicht verzichtbarer Kern bleibt
unberührt; nach deutschem Recht ist der Verzicht auf das
Urheberpersönlichkeitsrecht als solches unwirksam.

**§5 Zusicherung.** Du sicherst zu, dass der Beitrag von dir stammt, dass du
über die eingeräumten Rechte verfügst, und dass er keine Rechte Dritter
verletzt. Stehst du in einem Arbeits- oder Dienstverhältnis, dessen
Rechtsordnung oder Vertrag deinem Arbeitgeber Rechte an deiner Arbeit einräumt,
sicherst du zu, dessen schriftliche Freigabe eingeholt zu haben.

**§6 Herkunft von Maschinenerzeugtem.** Enthält dein Beitrag Text oder Code,
der ganz oder teilweise von einem KI-System erzeugt wurde, benennst du das im
Pull Request. Der Beitrag wird dadurch nicht abgelehnt; unbenannt bleiben darf
es nicht, weil an der Herkunft die Zusicherung nach §5 hängt.

**§7 Keine Gegenleistung, keine Verwendungspflicht.** Für den Beitrag wird
keine Vergütung geschuldet. Das Projekt ist nicht verpflichtet, ihn zu
verwenden, zu behalten oder zu pflegen.

**§8 Gewährleistung.** Der Beitrag wird ohne Gewähr eingebracht, soweit
gesetzlich zulässig — ausgenommen bleibt die Haftung für Vorsatz und grobe
Fahrlässigkeit sowie für Schäden aus der Verletzung von Leben, Körper oder
Gesundheit.

**§9 Recht und Gerichtsstand.** Es gilt deutsches Recht unter Ausschluss des
UN-Kaufrechts. Gerichtsstand ist der Sitz des Projektinhabers, soweit du
Kaufmann bist oder keinen allgemeinen Gerichtsstand in Deutschland hast. Ist
eine Bestimmung unwirksam, bleibt der Rest wirksam.

### Wie du zustimmst

Schreibe in den Pull Request eine Zeile:

```
Ich habe CONTRIBUTING.md gelesen und stimme dem CLA in Abschnitt 3 zu.
Name: <voller Name>   E-Mail: <Adresse>   Datum: <YYYY-MM-DD>
```

Firmenbeiträge brauchen zusätzlich die Zeichnung durch eine vertretungs-
berechtigte Person mit Angabe der Funktion.

## 4. Sign-off je Commit

Zusätzlich zum CLA trägt jeder Commit den Sign-off nach dem
[Developer Certificate of Origin](https://developercertificate.org/) 1.1:

```bash
git commit -s
```

Das hängt `Signed-off-by: Name <mail>` an. Der CLA regelt die Rechte, der
Sign-off die Herkunft — beides ist nötig, keines ersetzt das andere.

## 5. Was ohne CLA geht

Kein CLA nötig für: Fehlerberichte, Reproduktionsfälle, Messergebnisse,
Fragen, Übersetzungen einzelner Wörter, Tippfehlerkorrekturen ohne
schöpferische Höhe.
