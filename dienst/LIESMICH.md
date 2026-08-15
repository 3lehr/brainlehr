# Wissensraum-Dienst als eigenstaendiger Hintergrunddienst

## Was sich aendert

Bisher startete die App (`app/`) den Wissensraum-Dienst
(`berichte/entscheidungen_server.py`) selbst als Kindprozess. Die App liest
und schreibt seither ausschliesslich per HTTP gegen `127.0.0.1:8799` --
das war schon vorher so, aendert sich also nicht. Neu ist: die App startet
den Dienst nicht mehr. Sie stellt nur noch fest, ob er erreichbar ist, und
zeigt einen Hinweis, wenn nicht.

Grund: solange die App den Dienst selbst gebiert, laufen beide im selben
Rechte-Raum -- der Dienst gehoert dann zwangslaeufig demselben angemeldeten
Benutzer, der eigentlich eingeschraenkt werden soll, und die App kann nicht
in einer Sandbox laufen. Ein eigenstaendiger Hintergrunddienst ist der erste
Schritt dahin.

## Laden (einmalig, ohne Verwalterrechte)

Als LaunchAgent im eigenen Benutzerkonto -- **braucht kein Passwort und kein
`sudo`**:

```sh
REPO=/absoluter/pfad/zu/diesem/repo   # die Repo-Wurzel selbst eintragen
mkdir -p "$REPO/dienst/log"
sed "s#__REPO_PFAD__#$REPO#g" "$REPO/dienst/de.brainlehr.dienst.plist" \
    > ~/Library/LaunchAgents/de.brainlehr.dienst.plist
launchctl load ~/Library/LaunchAgents/de.brainlehr.dienst.plist
```

Der Dienst startet danach sofort (`RunAtLoad`) und bei jedem Login neu,
und launchd startet ihn automatisch neu, falls er beendet wird
(`KeepAlive`). Protokolle stehen in `dienst/log/dienst.log` und
`dienst/log/dienst.err`.

## Entladen

```sh
launchctl unload ~/Library/LaunchAgents/de.brainlehr.dienst.plist
```

## Verwalterrechte

Der Weg oben (LaunchAgent, `~/Library/LaunchAgents`) braucht **keine**
Verwalterrechte -- er laeuft im eigenen Benutzerkonto, wie jede andere App
auch.

Verwalterrechte (`sudo`) werden erst noetig, sobald der Dienst spaeter unter
einem eigenen, eingeschraenkten Systembenutzer laufen soll (das eigentliche
Ziel dieser Umstellung). Das bedeutet dann: die Beschreibung liegt unter
`/Library/LaunchDaemons/` statt `~/Library/LaunchAgents/`, und ein
Systembenutzer muss zuerst angelegt werden. Beides ist **nicht** Teil dieser
Umstellung und wird hier nicht ausgefuehrt -- der Betreiber tippt sein
Passwort dafuer selbst ein, wenn dieser Schritt ansteht.

## Manuell starten, ohne launchd

Fuer einen einzelnen Testlauf ohne Hintergrunddienst funktioniert weiterhin
`pflege/wissensraum_start.sh` wie bisher.
