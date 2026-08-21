# brainlehr als Speicher-Anbieter fuer Hermes

Hermes (Nous Research, MIT, github.com/NousResearch/Hermes-Agent) bietet unter
Einstellungen einen **Memory Provider**. Am 2026-08-20 standen dort acht
Anbieter zur Auswahl und brainlehr nicht.

## Einbauen

    mkdir -p ~/.hermes/plugins/brainlehr
    cp integrations/hermes/plugin/* ~/.hermes/plugins/brainlehr/
    export BRAINLEHR_HOME=/pfad/zu/brainlehr     # falls nicht ~/brainlehr
    hermes memory status                          # muss brainlehr auffuehren

**Der Ort ist nicht beliebig.** `~/.hermes/plugins/` ist der Nutzerbereich und
ueberlebt ein Hermes-Update. Der naheliegende Ort waere
`~/.hermes/hermes-agent/plugins/memory/` gewesen, wo die acht mitgelieferten
liegen -- der wird beim Update ersetzt.

## Was er anders macht als die acht

Gemessen am 2026-08-20 ueber `hermes memory status`: Sieben der acht brauchen
einen API-Schluessel, nur `holographic` laeuft rein lokal. brainlehr ist der
zweite lokale -- und der einzige, bei dem **jeder Eintrag eine nachpruefbare
Herkunft tragen muss**. Das ist keine Konvention, sondern ein
Datenbank-Trigger: Ein Eintrag ohne `source` entsteht gar nicht erst.

Der Abruf liefert die Herkunft deshalb mit. Sie wegzulassen hiesse, den
Unterschied zu verschenken.

## Was von den anderen uebernommen wurde

Aus dem Quelltext der acht, jeweils weil es MEHRFACH vorkam -- was in drei von
vier Anbietern gleich geloest ist, ist eher Stand der Technik als Geschmack:

* **Abruf im Hintergrund mit kurzer Wartefrist** statt blockierend (mem0
  wartet 3 s, ebenso retaindb und supermemory). Zaehlt hier doppelt, weil
  brainlehrs Abruf lokale Einbettungen rechnen kann.
* **Trivialfilter** vor Abruf. Die Schnittstelle bringt ihn selbst mit
  (`is_trivial_prompt`) -- byterover und supermemory bauen ihn trotzdem nach.
  Wir nehmen den vorhandenen.
* **Kein Schreiben aus nebenlaeufigen Kontexten.** Die Schnittstelle warnt
  ausdruecklich: Cron-Systemprompts wuerden die Nutzerdarstellung verderben.

Bewusst NICHT uebernommen: honchos Wettlauf aus drei Hintergrund-Threads mit
sieben Zeitfenstern und Veraltungswaechter in einer Methode.

## Grenze

Dieser Anbieter liest und schreibt den echten Bestand. Er ist kein Ersatz fuer
die MCP-Anbindung, sondern ihr Gegenstueck: MCP heisst "das Modell KANN
nachschlagen", ein Speicher-Anbieter heisst "es weiss es schon".

## Installation: Symlink, keine Kopie

```bash
ln -s /Volumes/daten/Begod2026/brainlehr/integrations/hermes/plugin ~/.hermes/plugins/brainlehr
```

**Warum ausdruecklich ein Symlink:** Bis zum 2026-08-21 lag dort eine KOPIE.
Sie war beim Anlegen identisch und driftete danach lautlos — eine Aenderung im
Repo erreichte Hermes nie, und niemand konnte es sehen. Genau diese Fehlklasse
hat dieses Haus schon mehrfach getroffen (`L-55075a`: ein korrigierter Trigger
erreicht eine gewachsene Datenbank nicht von selbst).

Gegenprobe nach der Installation:

```bash
readlink ~/.hermes/plugins/brainlehr    # muss den Repo-Pfad nennen
ls ~/.hermes/plugins/brainlehr/         # muss config_schema.py enthalten
```

Die alte Kopie liegt als `~/.hermes/plugins/brainlehr.kopie-20260821` daneben
und kann entfernt werden, sobald der Symlink einmal benutzt wurde.
