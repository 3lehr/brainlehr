# Welche der 35 Wiederholungsfälle lassen sich überhaupt verdrahten

Stand 2026-08-14T22:10:00+0200. Vorarbeit zu der Frage, ob eine Lehre eine
**Sperre** bekommen soll, sobald sie sich wiederholt. Grundlage ist die
Messung `runs/wiederholungsprobe_2026-08-14.json` (Knoten `03792e0a`): Der
Abruf findet die einschlägige Lehre in 20 von 35 Fällen, in 12 davon auf
Rang 1 — und **keiner** der 35 wurde verhindert.

## Zuerst: zwei Messungen, die ich verwerfen muss

Die naheliegende Prüfung — wiederholen sich Lehren mit Prüfstein seltener? —
habe ich zweimal gerechnet, mit zwei Proxys, und bekam **entgegengesetzte
Antworten**:

| Proxy | mit | ohne |
|---|---|---|
| Feld `pruefstelle` | 4,3 % | 7,0 % |
| Lehrkennung im Quelltext genannt | **17,8 %** | **5,2 %** |

Beide sind wertlos, aus zwei verschiedenen Gründen.

**Der erste Proxy misst ein ungepflegtes Feld.** Von den 35 Fällen werden 9
namentlich im Quelltext genannt und haben dort einen echten Prüfstein
(`test_normrang_skala_sperre`, `test_modellsperre`,
`test_geheimnisdatei_vorrang`, `test_norm_art_pflicht`, u.a.) — bei allen
neun ist `pruefstelle` leer. Dieselbe Klasse wie die sechs Nennerfehler
desselben Tages: eine gebaute Spalte, die nichts unterscheidet.

**Der zweite Proxy misst die Wirkung rückwärts.** Stichprobe über vier Fälle,
Anlagedatum des Prüfsteins gegen das Wiederholungsdatum:

```
L-0392e4  Lehre 08-06 -> Wiederholung 08-12   Prüfstein angelegt 08-12
L-a69129  Lehre 08-07 -> Wiederholung 08-09   Prüfstein angelegt 08-11
L-ad7232  Lehre 08-10 -> Wiederholung 08-12   Prüfstein angelegt 08-12
L-f3edbf  Lehre 08-08 -> Wiederholung 08-11   Prüfstein angelegt 08-13
```

Vier von vier: der Prüfstein entstand **am Tag der Wiederholung oder danach**.
Er konnte sie nicht verhindern — er war die Reaktion auf sie. Wer die
Wiederholungsquote „mit Prüfstein" misst, misst also, wie oft ein Prüfstein
aus einer Wiederholung entstand. Das Vorzeichen ist zwangsläufig positiv.

**Folge: Die Frage ist im Querschnitt nicht beantwortbar, in keiner Richtung.
Nur prospektiv.** Das ist kein Formfehler, sondern der Grund, warum die
Entscheidung überhaupt eine Entscheidung ist.

## Die Durchsicht

Maßstab: Lässt sich der Verhütungssatz von einer Maschine prüfen, **ohne den
Sachverhalt zu verstehen**? Nur dann ist er eine Sperre. Alles andere bleibt
Text — und das ist kein Makel, sondern die ehrliche Einordnung.

### A · Sperre am Werkzeugaufruf — 4 Fälle, alle neu

Prüfbar am Kommando selbst, bevor es läuft. Das ist die Klasse, die heute
fünfmal gewirkt hat (Planform-Ratsche, `produktivcode_nutzt_ort`,
Monolith-Bremse, `norm_art`-Trigger, `mcp_veraltet`).

| Lehre | Sperre |
|---|---|
| `L-f55167` | `git commit` ohne `-- <pfade>` ablehnen, solange eine zweite Sitzung im Repo arbeitet. **Am 2026-08-14 erneut passiert** (meine vorgemerkte Entfernung landete im Commit der Parallelsitzung) — das wäre Vorkommen 3. |
| `L-3d03bd` | `git stash` ablehnen, wenn das Agentenregister eine zweite laufende Sitzung zeigt. Ausweg im Fehlertext: `git checkout <ref> -- <datei>`. |
| `L-5e40a7` | `git commit -o <pfad>` ablehnen, wenn `<pfad>` laut `git status` `??` trägt. |
| `L-ad7232` | `cat` auf eine Datei ablehnen, die neben dem Geheimnis Erklärtext enthält. Prüfstein existiert (`test_geheimnisdatei_vorrang`), die Sperre am Werkzeug fehlt. |

### B · Ratsche im Verzeichnis — 9 Fälle, davon 5 bereits gebaut

Statisch oder gegen die Datenbank prüfbar, läuft in der Suite.

**Bereits verdrahtet** (nur das Feld `pruefstelle` fehlt): `L-6c6661`
(→ `test_produktivcode_nutzt_ort`, hat mich heute selbst erwischt),
`L-9a45b7` (→ `test_alle_selftests`, heute erweitert), `L-0392e4`,
`L-a69129`, `L-f3edbf`.

**Noch nicht verdrahtet, aber greppbar** — alle vier in fahrtenbuch, also
außerhalb dieses Repos:

| Lehre | Ratsche |
|---|---|
| `L-424312`, `L-919a81` | Jeder Vollbild-Zuhörer auf `rootNavigatorKey` muss über `showBlockingPrompt()` laufen — grep auf `MaterialPageRoute(fullscreenDialog:` ohne das Gate. |
| `L-965048` | Jede Stelle mit `draft.copyWith()` auf einer Zeile, deren RAM-Feld über einen Seiteneffekt weiterläuft. |
| `L-595196` | `scrollUntilVisible` auf einem Screen mit `SettingsScaffold`. |

### C · Bleibt Text — 22 Fälle

Der Verhütungssatz verlangt ein Urteil: „die Frage zerlegen", „prüfen, ob der
Fehlerfall im Betrieb eintreten kann", „vor jeder Aussage über eine Ursache
die Fehlerausgabe lesen". Eine Maschine kann nicht feststellen, ob das
geschehen ist.

Darunter die vier häufigsten (`L-352afa` 4×, `L-0e0ab6`, `L-b088ff`,
`L-402a51` je 3×). **Die hartnäckigsten Fälle sind ausgerechnet die, die sich
nicht verdrahten lassen.** Das ist die unbequemste Zahl dieser Durchsicht.

## Was das für die Entscheidung heißt

- Von 35 Wiederholungen sind **13 überhaupt verdrahtbar**, 5 davon schon.
  Netto also **8 neue Sperren** — 4 am Werkzeug, 4 in fahrtenbuch.
- „Jede wiederholte Lehre bekommt eine Sperre" deckt damit **höchstens ein
  Drittel** ab, und nicht das schwierigste Drittel.
- Der Aufwand ist klein (8 Stück), der Nutzen unbewiesen — genau deshalb
  lohnt der prospektive Aufbau: die 8 bauen, den Rest bewusst nicht, und in
  vier Wochen die Wiederholungsraten beider Gruppen vergleichen. Das ist die
  einzige Anordnung, die die Frage entscheidet, und sie kostet nur Warten.

## Was bewusst nicht vorgeschlagen wird

- **Keine Sperre für die C-Fälle.** Eine Sperre, die ein Urteil erzwingen
  will, wird zur Klickstrecke und stumpft die anderen mit ab.
- **Kein Nachpflegen von `pruefstelle` von Hand.** Ein Feld, das gepflegt
  werden muss, verrottet — die 9 Fälle oben sind der Beleg. Wenn, dann
  abgeleitet: ein Lauf, der die Lehrkennungen im Quelltext einsammelt und
  das Feld daraus setzt.
