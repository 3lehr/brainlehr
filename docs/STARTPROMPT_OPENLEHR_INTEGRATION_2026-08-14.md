# Startprompt: openlehr als erste Instanz auf brainlehr

Erzeugt 2026-08-14 am Ende der Grundarchitektur-Sitzung, für ein **frisches
Kontextfenster**. Alles unter „gemessen" ist an diesem Tag mit Werkzeugen
erhoben. Was hier fehlt, fehlt absichtlich — dieser Prompt gibt **keine
Empfehlung** zur Reihenfolge ab, die entscheidet der Betreiber.

---

## Der Auftrag

> **Betreiber, 2026-08-14:** *„berufschule ganz nach hinten schieben, wir wollen
> zuerst openlehr integrieren und dies mit den chaos fotografen steuer usw
> domäne"*

Die Berufsschul-Domäne (Knoten `962fbf48`) ist **zurückgestellt**, nicht
verworfen. Zuerst: openlehr wird die erste echte Instanz auf der brainlehr-
Schicht, am Fall „Fotograf mit Belegchaos".

## Was in der Grundarchitektur-Sitzung entschieden und gebaut wurde

**ADR-006 bis ADR-010** liegen in `brainlehr/docs/adr/`. Die vier Sätze, die
für diese Arbeit zählen:

| | |
|---|---|
| **ADR-007** | Zwei Schichten. **brainlehr** trägt (was gilt, und ob es belegt ist), **openlehr** wirkt (was ein Mensch in seiner Lage damit tun kann). Die Prüffrage für jede Idee: *muss sie etwas verweigern können?* → dann brainlehr |
| **ADR-006** | Python ist Grundsprache, das DB-Schema ist die Quelle der Form |
| **ADR-009** | Dokumentausgabe: LuaLaTeX mit `verapdf -f ua1` als Schranke — Rechnungen und Schreiben kommen barrierefrei UND druckfähig aus demselben Lauf |
| **ADR-010** | Das Dokumentfenster: Mensch und Modell am selben Dokument, Zeichen für Zeichen, Anmerkung = **Auftrag mit Anker**, nicht Kommentar |

**Gebaut und belegt (brainlehr, Zweig `brainlehr/b4-ausweis`, gepusht):**

- `kern/baustein.py` — Dokument als Baum aus Bausteinen mit stabilen Kennungen.
  Bausteintyp **`feld`** steht gleichberechtigt neben `absatz`: **eine Rechnung
  und ein Schriftsatz benutzen dieselbe Struktur.**
- `kern/dokument.py` — Anmerkungen liegen im **selben** Dokument wie die
  Bausteine. Zustand `offen → umgesetzt → abgenommen | abgelehnt`, Urheber
  `mensch`/`modell`.
- `kern/dokumentdienst.py` — WebSocket-Dienst, ein Raum, Stand überlebt
  Neustart, Ausweispflicht außerhalb von `127.0.0.1`, acht Kennzahlen.
- `kern/teilnehmer.py` — Kennungsauflage (< 2³², sonst verdoppelt sich Text still).
- `melder/dienstwache.py` — meldet die vier Fälle ohne Normalfall.
- **atelier** (`app/`) — native Mac-App, Ansicht **Dokument** verbunden mit dem
  Dienst; Steuerschnittstelle auf 4599 mit `/zustand`, `/ansicht`, `/blick`,
  `/dokument`.
- Suiten: Python **1489 grün**, Swift **193 grün**, 13 xfail mit Grund.

## Gemessener Ist-Stand openlehr (2026-08-14)

- Zweig `merge/daten-features`, **12 Commits ungepusht**, 1 Datei geändert.
- **529 Python-Dateien** unter `apps/openlehr`, Steuermodul unter
  `apps/openlehr/daemon/steuer/` (FastAPI-Daemon, Port 4242).
- Papernetz zum Fotografen-Steuerrecht: `docs/papers/citation-network.json`,
  **31 Knoten**. Kernbefund daraus: **es gibt keinen 9-%-Satz** — nur 19 % und
  7 %, und der 7-%-Satz für Bildrechte greift nur, wenn die Nutzungsrechte
  gesondert verhandelt und bepreist sind (FG Münster).
- Letzter eigener Stand: `docs/openlehr/STAND_2026-07-25T09-55-00+0200_…`.
  **Älter als drei Wochen — vor Gebrauch gegen `git log` prüfen.**

## Die Lehre, die diese Arbeit prägen sollte

`L-473ba2`, aus einem Prüftag an openlehr (2026-08-08/09): Acht Fehler, **sechs
davon an derselben Stelle** — der Naht zwischen Oberfläche und Fachlogik. Das
Rechnungschreiben, der Kern der App, war aus der Oberfläche heraus **tot**: der
Server verlangte `issue_date` und `service_period`, der Bildschirm hatte dafür
nie Felder. Währenddessen: 386 jsdom-Tests und über 300 pytest-Tests grün — die
einen prüfen die Oberfläche gegen einen erfundenen Server, die anderen die
Fachlogik gegen erfundene Eingaben. **Der erste E2E-Walkthrough fand in EINEM
Lauf mehr echte Fehler als beide Testbäume zusammen.**

Daraus vier Regeln für jede neue Domäne, alle mechanisch statt diszipliniert:

1. Die **E2E-Journey ist die Abnahmedefinition** und wird **vor** den
   Bildschirmen geschrieben — rot, bis die Domäne wirklich läuft.
2. Drei Nahtprüfungen: **Baustein-Bindung**, **Feldvertrag** (jedes
   serverseitige Pflichtfeld existiert auf dem besitzenden Bildschirm),
   **Textvertrag**.
3. **Ein Versprechen ist ein Test**: steht auf einem Bildschirm „wird gebraucht
   für X", muss ein Test belegen, dass X passiert.
4. Der Prüfstand wird aus der Auslieferung **abgeleitet**, nie parallel
   gepflegt.

## Beantwortet vom Betreiber, 2026-08-14 (wörtlich)

> 1. *„zum testen testdaten, erst wenn alles 100% richtig läuft echte daten!"*
> 2. *„am ende soll das ganze leben und steuerchaos, inklusive krankenkasse,
>    strafzettel wegen zu schnellen fahren usw abgearbeitet werden können"*
> 3. *„so wie du sagst"* — auf die Frage, was brainlehr verweigern können muss
> 4. *„dinge ohne menschen versenden"* — auf die Frage, was NIE passieren darf
> 5. *„garnicht falsch liegen!"*

**Was daraus folgt, und zwei Stellen brauchen einen Widerspruch:**

**Zu 1 — Testdaten, und das ist eine Sperre, keine Vorsichtsmaßnahme.**
Gearbeitet wird ausschließlich mit erfundenen Belegen, bis der Betreiber die
Freigabe ausdrücklich erteilt. **Was fehlt, ist das Kriterium:** „100 % richtig"
ist ohne Maßstab entweder nie erfüllt oder wird irgendwann gefühlt abgehakt.
Das ist die dringlichste offene Frage (F24 unten).

**Zu 2 — die Größenordnung ist eine andere geworden.** Nicht „Steuer", sondern
Lebensverwaltung: Krankenkasse, Bußgeld, Fristen. Die Schichtung trägt das
bereits (ADR-007 nennt als openlehr-Beispiele ausdrücklich Arbeitslose und
Kita-Suche), aber die **erste Instanz muss klein anfangen** — sonst gibt es nie
einen Fall, an dem sich etwas beweisen lässt. Welcher Ausschnitt zuerst, ist
F25.

**Zu 3 — die Trennlinie steht damit fest.** brainlehr verweigert: eine
Rechtsauskunft ohne Beleg, einen Steuersatz ohne Fundstelle, einen Beleg ohne
Herkunft. Alles, was etwas verweigern können muss, gehört nach unten.

**Zu 4 — nichts verlässt das Haus ohne Menschen.** Kein Versand, keine Abgabe,
keine Einspruchsfrist, kein Widerspruch — auch nicht „nach Bestätigung durch
eine Regel". Der Mensch drückt, oder es passiert nicht. Das ist stärker als die
Vorgabe aus ADR-010 (dort ist die Umsetzung einer Anmerkung *einstellbar*);
für Außenwirkung gibt es diesen Schalter nicht.

**Zu 5 — hier widerspreche ich, und der Widerspruch gehört in die Bauform.**
„Gar nicht falsch liegen" ist nicht erreichbar; kein System schafft das, auch
keins mit einem Menschen davor. Die erreichbare Form heißt **nie unbemerkt
falsch**: jede Aussage trägt ihren Beleg, und wo keiner ist, wird gefragt statt
geraten. Wer stattdessen Fehlerfreiheit verspricht, baut ein System, das im
Grenzfall rät, weil Nachfragen wie Versagen aussieht. Genau dagegen ist die
brainlehr-Schicht gebaut. **Praktische Folge:** jede Zahl und jeder Rechtssatz
im Ergebnis nennt seine Quelle; eine Zahl ohne Quelle erscheint gar nicht
erst, statt unbelegt dazustehen.

### Die Fragen, die dadurch NEU entstanden sind

24. **Woran misst sich „100 % richtig"?** Ohne Kriterium wird die Freigabe für
    echte Daten entweder nie erteilt oder irgendwann aus dem Bauch. Vorschlag
    zur Ablehnung oder Annahme: ein Satz erfundener Belege mit **bekanntem
    Sollergebnis**, den das System vollständig und ohne Nachfrage richtig
    verarbeitet — und bei dem es die absichtlich eingebauten Fallen (falscher
    Steuersatz, fehlende Fundstelle, doppelter Beleg) **von sich aus meldet**.
25. **Welcher Ausschnitt ist der erste?** Steuer, Bußgeld oder Krankenkasse —
    an einem davon wird das Regelwerk bewiesen, die anderen folgen.
26. **Woher kommen die Testdaten?** Erfunden, oder anonymisierte echte? Eine
    anonymisierte echte Rechnung ist immer noch eine echte Rechnung.
27. **Was heißt „abgearbeitet"** bei einem Strafzettel — bezahlt, Frist
    notiert, Einspruch geprüft, oder nur einsortiert?
28. **Krankenkasse: welche Lage?** Beitragsbescheid prüfen, Erstattung
    verfolgen, Rückstand klären — das sind drei verschiedene Systeme.

## Die Fragen an den Betreiber

Sie stehen bewusst **ohne Antwortvorschlag**. Nummeriert, damit er einzeln
antworten kann.

### Der Fall selbst

1. ~~Wer ist der Fotograf?~~ **Beantwortet:** Testdaten, bis die Freigabe
   ausdrücklich kommt. Offen bleibt, ob es später ein echter Mensch ist —
   davon hängt ab, ob jemals Daten Dritter im Spiel sind.
2. **Was genau ist „das Chaos"?** Schuhkarton mit Papierbelegen, ein volles
   Mailpostfach, Fotos auf dem Telefon, oder alles zusammen?
3. **Was soll am Ende herauskommen?** Eine EÜR, eine UStVA, ein Ordner
   sortierter Belege, oder eine Antwort auf „darf ich das absetzen"?
4. **Bis wann?** Gibt es eine Frist (Steuertermin), oder ist das eine
   Erprobung ohne Datum?
5. **Wie viele Belege ungefähr, über welchen Zeitraum?** Zehn oder tausend
   entscheidet die Bauform.

### Was openlehr heute schon kann und soll

6. **Was von openlehr/steuer läuft aus deiner Sicht bereits zuverlässig?**
   529 Dateien sagen nichts darüber, was du benutzt.
7. **Was hast du zuletzt selbst damit gemacht** — und was hat dabei genervt?
8. **Die 12 ungepushten Commits auf `merge/daten-features`:** soll ich die
   zuerst prüfen und pushen, oder liegen die absichtlich?
9. **Gibt es Mandanten?** Ein Fotograf oder mehrere Nutzer mit getrennten
   Daten?
10. **Soll die Steuer-Oberfläche bleiben, wie sie ist**, oder ist sie Teil
    dessen, was neu gebaut wird?

### Die Naht zu brainlehr

11. **Was soll brainlehr in diesem Fall verweigern können?** Nach ADR-007 ist
    das die Trennlinie. Kandidaten: eine Rechtsauskunft ohne Beleg, ein
    Steuersatz ohne Fundstelle, ein Beleg ohne Herkunft.
12. **Soll das Rechtswissen (Papernetz, 31 Knoten) in brainlehr wandern** oder
    in openlehr bleiben?
13. **Wer entscheidet über eine Buchung** — du, das Modell, oder das Modell mit
    deiner Bestätigung? Dieselbe Frage wie beim Dokumentfenster; dort ist die
    Antwort „einstellbar, Vorgabe Vorschlag".
14. **Soll das Dokumentfenster hier zum Einsatz kommen**, also Rechnungen und
    Schreiben im atelier statt im Browser?
15. **Gilt die Ausweispflicht auch hier?** Steuerdaten sind heikler als ein
    Schriftsatz.

### Grenzen und Risiko

16. ~~Was darf das System NIE tun?~~ **Beantwortet:** nichts ohne Menschen
    versenden. Offen als Abgrenzung: zählt eine gespeicherte Frist, die von
    selbst erinnert, schon als Außenwirkung? (Meine Lesart: nein — sie
    verlässt das Haus nicht.)
17. **Was passiert bei einer falschen Zahl** — merkst du es, oder fällt es erst
    beim Steuerberater auf?
18. **Gibt es einen Steuerberater im Spiel**, und was macht er?
19. **Sollen Belege das Haus verlassen** (Modellanfrage an einen Anbieter),
    oder bleibt alles lokal?
20. ~~Oft nachfragen oder selten falsch liegen?~~ **Beantwortet:** gar nicht
    falsch liegen — umgesetzt als *nie unbemerkt falsch*, siehe oben.

### Arbeitsweise

21. **Soll ich zuerst messen, was openlehr heute kann** (ein Walkthrough über
    den echten Ablauf), oder direkt bauen?
22. **Was ist der kleinste Fall, an dem du den Nutzen sofort sehen würdest?**
23. **Darf ich openlehr umbauen**, oder ist es produktiv genug, dass nur
    ergänzt wird?

## Zweite Runde Antworten, 2026-08-14 (wörtlich) — und die Lage ändert sich damit

> **F24** *„hört sich gut an"* — der Vorschlag für „100 % richtig" ist angenommen.
> **F25** *„steuer, fertig ist aber erst wenn wir alles erfasst haben, alles hängt
> ja auch mit allem zusammen"*
> **F26** *„erfunden, oder echten testkorpus finden"*
> **F27** *„einsortieren und der wichtigkeit nach abarbeiten / abarbeiten lassen /
> dabei unterstützen"*
> **F28** *„alles drei, und das was wir vergessen haben!"*
>
> **Und die eigentliche Lage:** *„valide auf briefe von finanzamt antworten
> können, keine steuer seit 2024 gemacht, deswegen auch keine
> krankenkassenbeiträge gezahlt, offene strafzettel (auto) usw. schufa versuchen
> zu bereinigen usw. es hat sich viel aufgestaut, was genau weiss ich auch
> nicht!"*

**Das ist kein Fotograf mehr — das ist der Betreiber selbst.** Der Unterschied
ist keine Formalie: die Zieldaten sind seine eigenen Steuer-, Kranken- und
Bonitätsdaten. Die Testdaten-Sperre aus Runde 1 gilt unverändert; sie schützt
jetzt aber nicht mehr einen Dritten, sondern ihn.

**Drei Sätze, die in dieser Sitzung nicht untergehen dürfen:**

1. **„Was genau weiß ich auch nicht" ist die eigentliche Aufgabe.** Nicht
   „Steuer machen", sondern **erst Bestand aufnehmen**. Ein System, das rechnet,
   bevor bekannt ist, was überhaupt vorliegt, rechnet über einer Lücke. Der
   erste Ausschnitt (F25: Steuer) ist damit **Erfassung**, nicht Abgabe.
2. **Rückstände haben Fristen und Folgen**, und das System darf darüber nicht
   hinwegsortieren. Ein Beitragsrückstand wächst, eine Bußgeldfrist verfällt,
   eine Schufa-Eintragung hat eine eigene Löschfrist. **Wichtigkeit ist hier
   nicht Geschmack, sondern eine Rechnung aus Frist und Folge** — genau das
   verlangt F27 („der Wichtigkeit nach").
3. **Bei Steuerrückständen seit 2024 gehört ein Steuerberater dazu.** Das System
   sortiert, bereitet vor, erinnert und formuliert Entwürfe — es ersetzt keine
   Beratung und keine Selbstanzeige. Wer das offenlässt, baut ein Werkzeug, das
   im ungünstigsten Fall eine Frist verstreichen lässt, weil sie niemandem
   aufgefallen ist. **Frage F29 dazu unten.**

**Auf Finanzamtspost „valide antworten können" ist der schärfste Punkt der
ganzen Anforderung.** Ein Brief ans Finanzamt ist Außenwirkung; nach Antwort 4
aus Runde 1 drückt der Mensch. Aber *valide* heißt mehr: jede Aussage im
Entwurf braucht ihre Fundstelle, und wo keine ist, darf der Satz nicht
entstehen. Das ist die brainlehr-Schicht, angewandt auf einen Briefentwurf.

### Weitere Fragen

29. **Steuerberater: gibt es einen, und darf er die Sachen sehen?** Wenn ja,
    ist das System sein Zuarbeiter — eine ganz andere Bauform, als wenn es
    allein steht.
30. **Weißt du, welche Briefe vom Finanzamt schon da sind** (Schätzbescheide,
    Erinnerungen, Vollstreckungsankündigungen), oder ist das Teil der
    Bestandsaufnahme?
31. **Gibt es bereits einen echten Testkorpus** (F26), oder soll ich einen
    erfinden? Ein erfundener Korpus mit bekanntem Sollergebnis ist für F24
    ohnehin nötig — ein echter kommt zusätzlich, nicht statt.

## Der Plugin-Auftrag (Betreiber, 2026-08-14)

> *„schau an was openlehr schon hat und wie wir es als ,plugin' in brainlehr und
> atelier integriert bekommen ohne altlasten mitzuschleppen!"*

**Gemessener Umfang, damit die Untersuchung nicht bei null anfängt:**

- `apps/openlehr/daemon/steuer/`: **102 Python-Dateien, 40 651 Zeilen.**
- Die vier größten: `router.py` **5841**, `api.py` **5662**, `db.py` **2526**,
  `ingest.py` **2404**. Zusammen sind das 40 % des Moduls in vier Dateien —
  dort steckt erfahrungsgemäß sowohl das Wertvolle als auch die Altlast.
- Namentlich vielversprechend für den Chaos-Fall: `chaos.py` (988,
  „Lokaler Chaos-Ordner-Workflow"), `ingest.py`, `beleg_seiten.py`,
  `classifier.py` (692), `gemma4_ocr_bridge.py`.

**Die Untersuchung, bevor irgendetwas übernommen wird** — und sie ist die erste
Arbeit dieser Sitzung, nicht ihr Nebenprodukt:

1. **Was löst openlehr heute wirklich?** Nicht nach Dateinamen urteilen. Für
   jeden Kandidaten: gibt es einen Aufrufer, einen Test, einen echten Lauf?
   `hub/scripts/wiring_check.py` findet deklarierten, aber nie erreichten Code.
2. **Was davon ist Fachwissen und was ist Gerüst?** Ein Belegklassifikator ist
   Fachwissen; eine FastAPI-Route ist Gerüst. Übernommen wird Fachwissen.
3. **Was ist Altlast?** Erkennungszeichen: kein Aufrufer, kein Test, Bezug auf
   eine Oberfläche, die neu gebaut wird, oder auf einen Beschluss, der
   zurückgenommen wurde.
4. **Die Naht:** Nach ADR-007 gehört alles, was **verweigern können muss**, nach
   brainlehr — Belegherkunft, Fundstelle, Geltung. Was ein Mensch **tut**,
   bleibt openlehr. Ein Belegklassifikator, der „das ist eine Rechnung" sagt,
   muss auch „ich weiß es nicht" sagen können; damit hat er einen Fuß in
   brainlehr.
5. **Kein Umzug ohne Beleg:** Was übernommen wird, kommt mit seinem Test — und
   wenn keiner existiert, wird er vor dem Umzug geschrieben. Sonst wandert die
   Altlast nur den Ordner.

## Wie in dieser Sitzung gearbeitet werden soll

- **Arbeitsort** `/Volumes/daten/Begod2026/openlehr`, für die brainlehr-Seite
  `/Volumes/daten/Begod2026/brainlehr` (Zweig `brainlehr/b4-ausweis`). Ein
  Startverzeichnis unter `.claude/worktrees/` ist ein alter Stand.
- Zuerst `CLAUDE.md` in beiden Repos lesen, dann diesen Prompt, dann
  `brainlehr/docs/PLAN_GESAMT_2026-08-13.md` (Linien F und G sind fertig).
- **Ein neuer Plan wird eine LINIE im Gesamtplan**, keine eigene Zählung ab 1
  (`L-30be01`).
- „Sieht der Code anders aus als hier beschrieben, halte dich an den Code und
  melde die Abweichung."
- Kein `git add -A`, kein `git stash`. Committen mit expliziter Pfadliste.
- Volle Suite **im Vordergrund** mit `timeout=600000`.

## Was in dieser Sitzung NICHT passieren soll

- **Keine Berufsschul-Domäne.** Zurückgestellt, Knoten `962fbf48`.
- **Kein Umbau am Dokumentdienst**, solange keine Domäne ihn braucht.
- **Keine Schwellen für die mengenhaften Kennzahlen** ohne Nullmessung mit dem
  zweiten Gerät (G3 steht offen, Grund in
  `brainlehr/runs/nullmessung_dokumentdienst_2026-08-14.json`).
