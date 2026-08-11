# Konsil: Darf eine Lehre den Weg blockieren?

2026-08-11T17:30:00+0200 · drei unabhängige Stimmen (Sonnet), getrennte Fenster,
Aufträge ohne die These des Auftraggebers.

**Anlass:** Fremdbericht `f581bd8f` (neun Ingenieurssysteme): „Wirksam wird ein
Wissensspeicher nicht durch bessere Suche, sondern durch administrativen Zwang."
Bei NASA/ESA hält ein unquittierter Treffer den Meilenstein an; die Beweislast
ist umgekehrt — begründet werden muss, warum eine Lehre NICHT zutrifft.

## Ergebnis in einem Satz

> **BERICHTIGT am selben Tag durch den Einspruch des Betreibers — siehe letzten
> Abschnitt. Der Satz unten war zu weit gefasst und ist an den Daten dieses
> Tages widerlegt.**

Der Zwang in der Bauform des Fremdberichts ist hier **nicht übertragbar**, weil
seine Voraussetzung fehlt — und die Form, in der er üblicherweise gebaut wird
(Prosa-Begründung), ist genau die, die binnen Sekunden zum Ritual wird. Was
trägt, ist nicht die Sperre, sondern **die Währung**: ein Beleg, der scheitern
kann, statt eines Satzes, der immer plausibel ist.

## Die drei Stimmen

### 1 · Betriebssicht — empfiehlt die Planvorlage

Blockiert würde nicht die Arbeit, sondern das Fertigstellen des Plandokuments:
jede thematisch passende, unquittierte Lehre braucht einen Satz — „trifft zu,
deshalb Punkt X" oder „trifft nicht zu, weil Y". Geschätzt 2–5 Auslösungen am
Tag. Preis eines Fehlalarms: ein Satz in einem Dokument, das ohnehin entsteht.

Ausdrücklich verworfen: **Werkzeugaufruf** (Edit/Write) — höchste Frequenz, und
genau diese Ebene hat belegt versagt: die Regel stand im Kontext und wurde am
selben Tag zweimal verletzt; mitten in der Ausführung wird eine Erinnerung
übergangen. **Commit** — zu spät, die Handlung ist geschehen, erzwingt Nacharbeit
statt Umlenkung.

### 2 · Widersacher — zerlegt die Bauform, nicht den Ort

Fünf Umgehungswege, der gefährlichste ohne jede Unehrlichkeit: *„Trifft hier
nicht zu, andere Codebasis"* ist in zehn Sekunden getippt und fast immer
plausibel, weil sich fast jeder Fall in irgendeinem Detail unterscheidet. Weitere
Wege: technische Abschaltung nach vorhandenem Muster (`_DECISION_BLOCK=False`
existiert bereits), nachträgliche Verengung des Geltungsbereichs (sieht aus wie
sorgfältige Arbeit), Sammelquittierung, und Delegation der Pflichtprosa an einen
billigen Subagenten — Letzteres folgt exakt der hier gelebten Logik, Prosa als
Boilerplate zu behandeln.

**Der härteste Einwand:** Dieses Haus hat sich per CLAUDE.md auf Anti-Reibung
festgelegt — „handeln statt vorlegen", „kurze Zustimmung ist eine Entscheidung",
„committen ohne Aufforderung". Eine blockierende Lehre widerspricht der eigenen
Betriebsphilosophie und wird nicht als Schutz erlebt, sondern als Reibungsverlust.

Am schwersten zu umgehen ist keine Prosa-Form, sondern ein **falsifizierbarer,
gegen den echten Stand geprüfter Beleg** — Grep-Treffer, Diff, Testlauf. Dieselbe
Logik wie „rot vor grün".

Vier Messwerte für „rituell geworden" (heute keiner erhoben): Quittierungszeit
relativ zur Textlänge · Entropie der Begründungstexte · nachträgliche
Widerlegungsrate · Stapelgröße je Quittierungsereignis.

### 3 · Fremdsysteme — prüft die Voraussetzungen, nicht die Ähnlichkeit

**Closed-Loop Infusion braucht eine ZWEITE Person** (ein Fachexperte dokumentiert
den Status eines *anderen*) plus Meilensteine mit externer Einsicht. Beides fehlt.
Ohne die zweite Person bleibt ein Gate im Ablauf, kein Kontrollmechanismus — und
das ist bereits gebaut. Übertragbar ist allein die **Frageform**: „warum trifft
das NICHT zu" statt „hier ist relevantes Wissen".

Ausdrücklich verworfen: das **gesetzlich-quantitative Regime** (Meldepflicht,
standardisierte Kodierung, Ausfallwahrscheinlichkeiten). Keine Rechtsfolge, kein
großes N, kein Abnehmer für eine Risikoanalyse — Formulararbeit ohne Adressat.

Anonymität ist bei einer Person sinnlos; **Straffreiheit** dagegen ist hier schon
erfüllt („geändert, nicht verifiziert" ist eine zulässige Aussage) und leistet
mehr als im Großbetrieb: Schutz nicht vor dem Vorgesetzten, sondern vor der
eigenen Neigung zum Schönreden.

**Größter unausgeschöpfter Wert: Common-Cause-Failure auf die Agenten-Redundanz.**
Mehrere Sitzungen sind echte Redundanz. Machen zwei unabhängige Sitzungen
denselben Fehler, ist das kein Doppelbefund, sondern ein blinder Fleck im
GEMEINSAMEN Kontext (CLAUDE.md, Werkzeugverhalten, Trainingsstand). Im Großbetrieb
geht das in der Meldungsmenge unter; hier führt das Agentenregister die Zuordnung
bereits. Kein Neubau, ein Auswertungsfeld auf vorhandenen Daten.

**Bestes fachfremdes Gegenstück: Laborbuch / Präregistrierung.** Die einzige
Mechanik der ganzen Auswahl, die von Grund auf für EINE Person gebaut ist:
Hypothese-Zeitstempel liegt vor Ergebnis-Zeitstempel. Sie adressiert exakt das in
dieser CLAUDE.md bereits benannte Problem („ein Auftrag lässt messen, nicht
bestätigen", dreimal geschehen, dreimal widerlegt).

## Wo die Stimmen sich widersprechen

Stimme 1 empfiehlt eine **Prosa-Begründung** an der Planstelle. Stimme 2 nennt
genau diese Form als den Weg, der in Sekunden zum Ritual wird. Stimme 3 nimmt dem
Mechanismus die Voraussetzung.

Der Widerspruch löst sich nicht durch Mehrheit, sondern durch Trennung von **Ort**
und **Währung**: Der Ort von Stimme 1 überlebt (die Planvorlage ist die einzige
Stelle mit passender Frequenz und vernachlässigbarem Fehlalarmpreis). Die Währung
fällt — kein Satz, sondern ein Beleg, der scheitern kann.

## Beschluss-Vorschlag, in dieser Reihenfolge

1. **Common-Cause zuerst** (Stimme 3). Kein Blocker, keine Ritualgefahr, Daten
   liegen im Agentenregister. Fragestellung: derselbe Fehler in zwei unabhängigen
   Sitzungen = blinder Fleck im gemeinsamen Kontext.
2. **Frageform umstellen** (Stimme 3, billigster Einzelgriff): der Recall-Block
   rahmt Treffer als Ablehnungsfrage statt als Fundliste. Keine Sperre, keine
   Reibung, prüfbar über die Messwerte von Stimme 2.
3. **Präregistrierung an der Planstelle** (Synthese 1+2+3), und erst hier eine
   Blockade: Eine einschlägige Lehre wird zu einer **prüfbaren Erwartung** für
   dieses Vorhaben, festgehalten VOR dem Ergebnis. Lässt sich keine formulieren,
   steht „kein Prüfsatz möglich" da — selbst ein Signal.
4. **Nicht bauen:** ~~Zwang ohne zweite Person~~ (durch den Einspruch des
   Betreibers hinfällig, siehe unten), Prosa-Quittierung, kodierte Meldepflicht.

## Was dieses Konsil nicht geklärt hat

Ob die Messwerte aus Stimme 2 überhaupt erhebbar sind, ohne selbst zum Ritual zu
werden. Und die Frage des Betreibers nach der Gegenrichtung — welche NORM einer
Lehre widerspricht — ist hier nur gestreift: sie braucht die Achse „Art"
(Sein/Sollen/Dürfen), gesetzt bei 2 von 82 Normen.

---

## Einspruch des Betreibers, 2026-08-11T17:50:00+0200 — und er trägt

Wörtlich: *„zudem haben wir hier zweite Person! ersten ich, zweiten du als ki,
3 einen subagent als ki, das konsil hat es bewiesen. ausserdem wenn brainlehr
von unternehmen genutzt wird!"*

**Der Einspruch ist begründet, und der Beleg ist dieses Konsil selbst.** Drei
Stimmen in getrennten Fenstern haben den Vorschlag des Auftraggebers verworfen —
genau das, was eine Prüfinstanz leisten soll und was eine Selbstauskunft nicht
kann. Die Behauptung „ein Ein-Personen-Haus hat keine zweite Instanz" ist damit
an den eigenen Daten dieses Tages widerlegt.

Ich habe sie zu bereitwillig übernommen. Dieselbe Fehlerform wie heute Mittag
bei der kontaminierten Messung: eine plausible Erklärung akzeptiert, statt sie
gegen das zu halten, was im selben Raum passiert ist.

### Was sich an der Voraussetzung ändert

Die Voraussetzung heißt nicht „zweite PERSON". Sie heißt **Unabhängigkeit**, und
die zerfällt in drei Teile, die getrennt erfüllbar sind:

| Teil | heute erfüllt? |
|---|---|
| **a) eigener Kontext** — die Instanz teilt den blinden Fleck nicht | teilweise |
| **b) eigener Zugang zum Rohmaterial** — sie sieht nicht nur meine Zusammenfassung | **nein** |
| **c) das Urteil ist nicht still zu unterdrücken** | **nein** |

Zu (a): Die drei Stimmen hatten getrennte Fenster und verschiedene Blickwinkel —
aber dieselbe CLAUDE.md, denselben Speicher, dieselbe Modellfamilie. Das ist
genau der Common-Cause-Kanal, den Stimme 3 selbst benennt. Unabhängig in der
Perspektive, nicht im Kontext.

Zu (b): Ich habe die Faktenlage in die Aufträge geschrieben und ausdrücklich
„keine Websuche, nicht breit recherchieren" verlangt — aus Kostengründen. Damit
hing jede Stimme an meiner Auswahl. Ein Prüfer, der nur sieht, was der Geprüfte
ihm vorlegt, prüft die Vorlage, nicht die Sache.

Zu (c): Ich habe die Aufträge geschrieben UND das Ergebnis zusammengefasst.
Nichts hätte mich gehindert, das Konsil stillschweigend fallen zu lassen. Dass
ich es nicht getan habe, ist keine Eigenschaft des Verfahrens.

### Folge für den Beschlussvorschlag

Punkt 4 („Zwang ohne zweite Person nicht bauen") entfällt in dieser Form. An
seine Stelle tritt eine Bedingung, die prüfbar ist:

**Eine Prüfinstanz zählt, wenn sie (b) das Rohmaterial selbst ziehen darf und
(c) ihr Urteil an einer Stelle landet, die der Geprüfte nicht schreibt.**

Beides ist billig herstellbar: (b) heißt, dem Prüfagenten Lesezugriff auf
Speicher und Code zu geben statt einer Faktenliste — teurer in Token, aber das
ist der Preis der Prüfung. (c) heißt, dass das Urteil als eigener Eintrag
entsteht, nicht als Absatz in meinem Bericht.

### Und der Unternehmensfall

Dort ist die ursprüngliche Voraussetzung ohnehin erfüllt: mehrere Menschen,
verschiedene Rollen, echte Arbeitsteilung. Der Mechanismus überträgt sich
unverändert — die Einschränkung von Stimme 3 galt nur für den Ein-Personen-Fall
und war auch dort zu eng. Was daraus für den Bau folgt: die Prüferrolle wird von
Anfang an als eigene Identität geführt (`actor`, `freigabe`), nicht als
Sonderfall des Schreibers. Sonst ist der Unternehmensfall ein Umbau statt einer
Konfiguration.
