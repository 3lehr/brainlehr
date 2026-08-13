# ADR-007: Zwei Schichten — brainlehr trägt, openlehr wirkt

**Stand** 2026-08-13T22:46:17+0200
**Status** Angenommen
**Betrifft** den ganzen Verbund: `brainlehr`, `openlehr`, `buckeberg`, künftige Instanzen
**Entscheider** Betreiber, 2026-08-13

## Was entschieden wurde

Wörtlich, und die Begründung ist der eigentliche Inhalt:

> *„für mich ist brainlehr die basis auf die gleichzeitig die verschiedensten domänen
> arbeiten können … deswegen möchte ich alles über der schicht brainlehr, openlehr nennen.
> openlehr entstand um steuerchaos für selbständige zu beseitigen, bucke weg um mutter bei
> verwaltersuche zu unterstützen, openlehr könnte so auch arbeitslose unterstützen, oder
> familien die eine kita suchen. **vorgefertigtes valides ki wissen + werkzeug um das wissen
> einzusetzen. in welcher form auch immer das werkzeug dann ist**"*

**Zwei Schichten, nicht drei:**

| | |
|---|---|
| **brainlehr** | Was gilt, und ob es belegt ist. Ausweis, Freigabe, Norm mit Rang und Geltung, Herkunft, Widerruf, Abruf, Aufsicht über die eigene Arbeitsweise. |
| **openlehr** | Was ein Mensch in seiner Lage damit tun kann. Die abgeleiteten Konventionen, die gemeinsame Werkzeugbasis und die **Instanzen** je Lage. |

Die Werkzeugform ist **keine** Schichtgrenze — Formularfelder, Schriftsatz, Gespräch,
Nachrichtendienst sind Ausprägungen einer Schicht, nicht verschiedene Schichten.

## Warum der Name nicht kollidiert

Der erste Einwand in der Sitzung lautete, `openlehr` sei vergeben: eigenes privates Repo
`3lehr/openlehr`, 262 Beschlussdokumente unter `docs/openlehr/`, eigene `steuer.db`.

**Der Einwand war das schwächere Argument** und beantwortet eine Zuschnittsfrage, wo eine
Zweckfrage gestellt war. Der Name war nicht vergeben, er war **zu eng angewandt**: Das
heutige openlehr ist die erste **Instanz** der Kategorie, nicht die Kategorie.

Folge, die erledigt werden muss: Die Steuerinstanz braucht einen eigenen Namen, und der
Repo-Zuschnitt folgt später. Das ist eine Aufgabe, kein Einwand.

## Der Befund, der aus der Definition folgt

`docs/STARTPROMPT_GRUNDARCHITEKTUR_2026-08-13.md` hält fest, ein Andock-Regelwerk komme
„erst nach der zweiten echten Domäne, sonst wäre es geraten".

**Nach dieser Definition existiert die zweite Instanz seit Monaten.** openlehr/Steuer
(Selbständige im Steuerchaos) und buckeberg/Verwaltersuche (WEG-Eigentümerin vor einer
Vergabeentscheidung) sind zwei Fälle derselben Form: geprüftes Wissen plus Werkzeug für
eine Lage, die den Betroffenen überfordert. An der Oberfläche maximal verschieden —
Formularfelder gegen Schriftsatz mit Quellenbelegen —, in der Bauform gleich.

Übersehen wurde das, weil nach **App** sortiert wurde statt nach **Gestalt**. Dieselbe
Fehlerform wie `L-9e1d80`: nach dem Namen gesucht, den man kennt, statt nach der Sache.

Das Regelwerk aus Frage 4 ist damit nicht mehr Vorratshaltung. Es hat zwei bezahlte Fälle,
und ein an einer echten Domäne erarbeiteter Entwurf liegt bereits vor — `L-473ba2`, vier
Regeln „für JEDE neue Domäne", entstanden aus acht Fehlern an einem Tag, sechs davon in
der Naht zwischen Oberfläche und Fachlogik.

## Was ausdrücklich NICHT dazugehört

**Die Geräte-Apps** — fahrtenbuch und die übrigen Handy-Anwendungen. Betreiberentscheidung
2026-08-13, wörtlich: *„das fahrtenbuch und die anderen handyapps würde ich erst einmal
aussen vorlassen, was wir daraus gelernt haben aber eben nicht."*

**Das Kriterium dahinter, nachträglich formuliert und prüfbar:** Eine openlehr-Instanz
setzt eine Lage voraus, die den Betroffenen ohne Hilfe überfordert, und geprüftes Wissen,
das ihn handlungsfähig macht. Beim fahrtenbuch fehlt beides — ein Gerät zeichnet Fahrten
auf. Es ist keine Instanz.

**Die Lehren daraus bleiben vollständig in Kraft.** 295 von 865 Lehren stammen aus
fahrtenbuch — der größte Einzelposten des Bestands kommt aus einem Projekt, das keine
Instanz ist. Kein Widerspruch: brainlehrs Wissen handelt davon, **wie man baut**, nicht
wovon eine Anwendung handelt. Der Wissensbestand ist nicht auf openlehr-Instanzen
zugeschnitten und wird es nicht.

## Die Schichtgrenze ist Autorität, nicht Abstraktion

Vorgeschlagenes Kriterium, damit die Grenze nicht Geschmackssache bleibt:

**brainlehr kann nein sagen** — Freigabe verweigert, Norm greift, Trigger blockiert, Melder
schlägt an. **openlehr kann es nicht**; es stellt Wissen und Werkzeug bereit.

Daraus folgt unmittelbar, wo die gemeinsame Dokumentbasis hingehört (Baum mit stabilen
Kennungen, Eingabeformen, LaTeX-Ausgabe, Anzeige nach ADR-004): **nach openlehr**, als
geteilter Unterbau der Instanzen — sie verweigert nichts, sie stellt bereit.

**Das Kriterium ist widerlegbar, und so wird es widerlegt:** Findet sich ein Fall, in dem
die Dokumentbasis etwas **verweigern muss**, ist sie keine Werkzeugkiste, sondern eine
eigene Schicht. Bis dahin bleibt es bei zwei.

## Warum die obere Schicht schnell gebaut werden darf

Der Betreiber nennt die Instanzen „vibe gecodet". Das ist keine Nachlässigkeit, sondern
folgt aus der Schichtung — **und es gilt nur wegen ihr.**

Belegt in beide Richtungen:

- **Schreiben ist billig geworden.** Microsoft-Rollout Anfang 2026, Zehntausende
  Ingenieure, vier Monate: Adoptierende mergen rund 24 % mehr Pull Requests
  (arXiv 2607.01418). METR musste sein Messverfahren einstellen, weil Entwickler nicht mehr
  ohne KI arbeiten wollen — auch nicht für 50 $/Stunde.
- **Unbemerktes Auseinanderlaufen ist teurer geworden.** `L-473ba2`: sechs von acht Fehlern
  in der Naht, während 386 jsdom- und über 300 pytest-Tests grün waren; das Rechnungschreiben
  — der Kern der App — war aus der Oberfläche heraus tot. `L-5431a3`: zwei gleichnamige
  Klassen, monatelang die tote gepflegt.

Schnell geschriebener Code mit grünen Tests und ohne widersprechende Schicht darunter ist
genau der Zustand, der diese Fehler erzeugt hat. **Oben darf schnell gearbeitet werden,
weil unten etwas nein sagen kann.** Ohne Schicht 1 wäre dasselbe Vorgehen fahrlässig.

## Alternativen, samt Ablehnungsgrund

| Weg | Abgelehnt weil |
|---|---|
| **Drei Schichten** (Wissen · Regeln · Apps) | Die mittlere Schicht trennt nichts, was das Autoritätskriterium trennt. Regelableitung ist Aufsicht und gehört zu 1; Domänenkonventionen sind Handreichung und gehören zu 2. |
| **Neuer Name für die obere Schicht** statt `openlehr` | Zweimal verlangt, mit Begründung. Und die Begründung trägt: die Kategorie war schon da, nur eng benannt. |
| **fahrtenbuch als dritte Instanz führen** | Erfüllt das Kriterium nicht — keine überfordernde Lage, kein geprüftes Wissen als Gegenstand. Es mit hineinzunehmen würde das Kriterium wertlos machen. |
| **Regelwerk weiter aufschieben** bis eine „richtige" zweite Domäne existiert | Sie existiert. Weiter zu warten hieße, auf etwas zu warten, das schon eingetreten ist. |

## Was das kostet

- **Die Steuerinstanz verliert ihren Namen** und braucht einen neuen; Repo-Zuschnitt,
  Pfade und 262 Beschlussdokumente unter `docs/openlehr/` tragen ihn heute. Umbenennen ist
  billig, Verwechseln ist teuer — solange beides koexistiert, ist jede Aussage „läuft auf
  openlehr" zweideutig.
- **Zwei Schichten sind weniger Führung als drei.** Wo eine Konvention hingehört, ist im
  Zweifel offen. Das Autoritätskriterium ist die Entscheidungsregel — es ist neu und
  ungeprüft.
- **Das Kriterium schließt Projekte aus**, die heute im selben Verbund liegen. fahrtenbuch
  und die Geräte-Apps bekommen von dieser Architektur nichts; sie geben weiter, ohne zu
  nehmen.

## Woran sich Erfolg misst

- Für jede neue Idee lässt sich in einem Satz sagen, ob sie brainlehr oder openlehr ist —
  über die Frage, ob sie etwas verweigern können muss.
- Das Andock-Regelwerk entsteht aus den **zwei vorhandenen** Instanzen und wird an einer
  dritten geprüft, nicht an ihnen erfunden.
- Keine Aussage im Verbund ist mehr zweideutig zwischen Schicht und Steuerinstanz.
