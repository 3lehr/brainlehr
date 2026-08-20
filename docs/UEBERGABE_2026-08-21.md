# Übergabe — Stand 2026-08-21T00:24:53+0200

Für die nächste Sitzung. Sie ersetzt keinen Plan; sie sagt, **woran gerade
gearbeitet wird** und was als Erstes zu tun ist.

## Was in dieser Sitzung entstanden ist

| | Zustand |
|---|---|
| `docs/PLAN_BETRIEBSPROFILE_2026-08-20.md` | acht Stränge A–G, Parallelität festgeschrieben |
| `docs/REQUIREMENTS_BRAINLEHR.md` | 56 → **66** BDW-Zeilen (P09–P14, E22–E25) |
| gebaut und belegt | A1 Widerspruchserkennung · Planmitschrieb-Melder · Achsen-Melder · Kantensperre · Rangrücknahme · Modellwege-Melder |
| gemessen | Wettbewerb (8 Anbieter), Vorlaufzeit (5 Monate), Startfrequenz (8–15/Tag) |

## Der nächste Schritt

**B1 — die Achsen ins Schema.** Bindend zuerst, weil alles andere sie
voraussetzt und weil sie sich nicht nachtragen lassen:

```
mandant   Vorgabe 'lokal'      -- wem gehören die Daten
kreis     Vorgabe leer         -- wer darf sie sehen (BDW-E22)
sprache   erkannt, 98,4 %      -- BDW-P10
geltung   eigene Tabelle       -- BDW-E23, weil zweiseitig
```

Der Grund für die Reihenfolge steht im Plan und ist **nicht** die Datenmenge:
5.232 Alteinträgen ließe sich rückwirkend keine Zuordnung geben, die sie nie
hatten.

## Was sofort und parallel laufen kann

A2 (Rückzug bei Leerlauf) · A3 (Sicherung gegen tote Dienste) · D
(Zugriffsmuster) · E1 (Verfallsrate) · F (Forderungen als Vorgang) · P14-Tür
(README und CONTRIBUTING auf Englisch — zwei Dateien).

## Was auf den Betreiber wartet

* **Zweiter Faktor**: sechs Wege im Plan, keiner entschieden. Die Messung
  liegt vor — 8–15 Sitzungen am Tag, also scheidet alles aus, was bei jedem
  Start abgefragt wird.
* **Push des öffentlichen Exports**: 675 Dateien liegen bereit, Lizenz
  korrigiert (AGPL), Prüfer grün bis auf zwei belegte Fehlalarme.
* **GitHub-Konto ist wegen einer Abrechnungsfrage gesperrt** — die CI läuft
  deshalb nicht. Das ist kein Codefehler.

## Fallen, in die heute tatsächlich getreten wurde

1. **`git checkout --` auf eine generierte Dateiliste** hat zweimal fertige,
   uncommittete Arbeit gelöscht. Wer eine Massenänderung zurücknehmen können
   will, committet **vorher**, was er behalten will.
2. **Kennungen doppelt vergeben** (BDW-P06/E20) — die höchste vergebene
   Nummer wird gemessen, nicht geraten.
3. **Der laufende MCP-Prozess trägt alten Code.** Eine Änderung am Server
   wirkt erst in einer neuen Sitzung; für sofortige Wirkung ein frischer
   Python-Prozess.
4. **Melder gegen den echten Bestand fahren, bevor man ihnen glaubt.** Zwei
   von drei Entwürfen waren beim ersten Lauf falsch — einer meldete 13 von 13,
   der andere 21 Rauschtreffer.
