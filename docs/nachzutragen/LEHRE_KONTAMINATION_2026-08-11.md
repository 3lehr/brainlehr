# Nachzutragen: Lehre zur Kontamination durch den Abruf-Haken

Stand 2026-08-11T14:55:00+0200 — **noch nicht in der Knowledge-DB.**
`lesson_record` scheitert seit 14:10 mit `database is locked`; das WAL steht,
eine fremde Sitzung haelt die Datenbank. Beim naechsten freien Fenster
eintragen und diese Datei loeschen.

    type: antipattern · severity: critical · anlass: selbst
    projects: brainlehr, hub, systemweit · node_path: /brainlehr

## description

Eine Messung mit Subagenten gefahren und dabei uebersehen, dass der
UserPromptSubmit-Haken auf den AUFTRAGSTEXT AN DEN SUBAGENTEN feuert und ihm
die gesuchte Antwort einspielt. Gemessen 2026-08-11 in brainlehr: Der
dreigeteilte Antwortlauf (wissensnutzen_blind.py) sollte messen, ob
eingespieltes Wissen die Antwortguete hebt. Drei Haiku-Subagenten beantworteten
je sechs Aufgaben. Ergebnis: Aufgabe A stieg von 0,00 auf 0,67 — bei
Trefferguete FALSE, die Ziel-Lehre war also gar nicht im gemessenen Block. Ich
habe das im Commit als interessanten Befund verkauft ("der Nutzen kam von
anderen Treffern"). In Wahrheit stand in allen drei Agentenprotokollen eine
`user`-Nachricht, die ich nicht geschrieben hatte: `knowledge_recall_hook`
hatte auf meinen Auftragstext hin genau die Ziel-Lehre `L-c0e910` eingespielt,
woertlich samt Loesungswort `ActionScreen`. Das Wort kommt im gemessenen Block
nullmal vor. Drei von vier Vergleichszellen waren damit unbrauchbar, darunter
beide OHNE-Baselines — also gerade die Zellen, die "kennt es die Loesung nicht"
zeigen sollten.

## root_cause

Der Messaufbau behandelt den Subagenten als leeres Gefaess, das nur bekommt,
was im Prompt steht. Tatsaechlich ist er ein vollwertiger Sitzungsteilnehmer:
Haken feuern auf seinen Auftragstext, Projektvorgaben liegen in seinem Kontext.
Verstaerkend und der eigentliche Fehler: Als das Ergebnis eine Merkwuerdigkeit
zeigte (Nutzen steigt ohne Treffer der Ziel-Lehre), habe ich dafuer eine
inhaltliche Erklaerung gebaut, statt zu fragen, ob die Messung ueberhaupt
gemessen hat, was sie behauptet. Eine plausible Geschichte zu einem
unerwarteten Wert ist die bequemste Art, eine kaputte Messung zu konservieren.

## resolution

`kontamination.py` gebaut: prueft am Agentenprotokoll, ob ein TRAEGER der
richtigen Antwort im zugetragenen Kontext auftaucht, ohne im gestellten Prompt
zu stehen — deterministisch, mit Fundstelle, Gegenprobe in beide Richtungen.
`auswerten()` verwirft betroffene Zellen, statt sie mit Fussnote mitzufuehren.
Commit 4360a82 widerruft cade91d.

## prevention

Vor jeder Messung, die einen Subagenten antworten laesst: aufschreiben, was
ausser dem Prompt in seinem Kontext landet — Haken auf UserPromptSubmit,
Projektvorgaben, Verzeichnisinhalte. Danach am PROTOKOLL pruefen, nicht am
Ergebnis. Prueffrage, die den ganzen Fall abkuerzt: "Steht das Wort, an dem
meine Bewertungsfunktion die richtige Antwort erkennt, irgendwo in seinem
Kontext ausser in der Aufgabe?"

Zweitens, die uebertragbare Haelfte: Zeigt ein Messwert eine Merkwuerdigkeit,
ist die ERSTE Hypothese "der Aufbau misst etwas anderes", nicht "die Welt ist
interessanter als gedacht". Erklaerungen fuer unerwartete Werte werden erst
gesucht, nachdem der Aufbau entlastet ist.

Drittens: Verhindern ist hier schwaecher als Pruefen — dass etwas NICHT
eingespielt wurde, sieht man einer Zahl nicht an, ein Befund am Protokoll
dagegen ist ein Artefakt.
