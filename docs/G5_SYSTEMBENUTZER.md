# G5 — eigener Systembenutzer fuer Bestand und Ausweisdatei

Angelegt 2026-08-15T00:00:00+0200. Vorbereitung fuer
`docs/PLAN_GESAMT_2026-08-13.md` Abschnitt G5 und Fund O4 in
`docs/SICHERHEITSFUNDE_2026-08-14.md`. **Braucht das Passwort des
Betreibers — deshalb hier nur vorbereitet, nicht ausgefuehrt.**

Sieht der Code an einer Stelle anders aus als hier beschrieben: an den Code
halten, Abweichung melden.

## Teil 1 — was auf den Bestand zugreift, und wie

Gemessen 2026-08-15 gegen den Stand dieses Zweigs (`brainlehr/b4-ausweis`).
Zwei Dateien sind der eigentliche Bestand:

- `brainlehr.db` — Repo-Wurzel (an `schema.sql` erkannt, `kern/auditanker.py`,
  `haken/ort.py`), aktuell `-rw-------` unter `lehrmacbook`, 86 MB.
- `~/Desktop/brainlehr-ausweise/` — Ausweisordner (`kern/ausweis.py`,
  `VORGABE_AUSWEISORDNER`, override `BRAINLEHR_AUSWEISE`), aktuell `drwx------`
  unter `lehrmacbook`.

**Zugreifer, mit Kennung und Zugriffsart:**

| # | Zugreifer | Pfad | Zugriffsart | Kennung heute |
|---|---|---|---|---|
| 1 | Dienst `berichte/entscheidungen_server.py` | via `dienst/de.brainlehr.dienst.plist`, geladen als `~/Library/LaunchAgents/de.brainlehr.dienst.plist`, `RunAtLoad`+`KeepAlive` | lesend+schreibend (Bestand direkt, Ausweisordner via `kern/ausweis.py`) | `lehrmacbook` (LaunchAgent im eigenen Konto, kein `UserName`-Schluessel in der plist) |
| 2 | App `Atelier.app` (`app/`) | HTTP-Klient von `127.0.0.1:8799` | **keine** — gegrept ohne Treffer fuer `sqlite3`/`.db` in `app/Sources`; `AusweisDienst.swift` reicht Anfragen per HTTP an den Dienst weiter | `lehrmacbook`, sandboxed seit O5 (`app-sandbox`, `network.client`) |
| 3 | MCP-Server `knowledge_mcp_server.py` (Werkzeuge `mcp__knowledge__*`, `mcp__knowledge-probe__*`) | eigener Prozess pro Klient (stdio), `sqlite3.connect(DB_PATH)` direkt in Zeile 608 | lesend+schreibend | `lehrmacbook` (Prozess des angemeldeten Nutzers, kein zentraler Neustart) |
| 4 | Haken (`haken/*.py`, in `settings.json` als Hooks verdrahtet) | 8 von 8 Dateien mit `DB_PATH`/`sqlite3.connect`-Treffer, u.a. `knowledge_recall_hook.py`, `auszug_nachziehen.py`, `kurator_taeglich.py` | ueberwiegend lesend, `auszug_nachziehen.py`/`kurator_taeglich.py` auch schreibend | `lehrmacbook` (Subprozess des Claude-Code-Hooks) |
| 5 | Melder (`melder/*.py`) | 12 von 24 Dateien mit DB-Zugriff | lesend (Melder melden, sie schreiben Befunde meist in eigene JSON/JSONL, nicht in `brainlehr.db`) | `lehrmacbook`, manuell oder per Cron/Terminal gestartet |
| 6 | Pflegeskripte (`pflege/*.py`, `pflege/*.sh`) | 11 von 26 Dateien, u.a. `ausweis_helfer.py`, `ausweis_start.sh`, `knowledge_db_snapshot.py` | lesend+schreibend (Backups, Rotation, Einloesung) | `lehrmacbook`, manuell gestartet |
| 7 | Schreibpruefstand (`schreibpruefstand/`) | 8 von 14 Dateien | schreibend (Testschreibungen gegen den Bestand, Teil des Pruefkorpus) | `lehrmacbook`, aus Testlaeufen |
| 8 | `kern/` selbst | 50 von ~60 Dateien importieren `speicher.py`/`ausweis.py` oder oeffnen `sqlite3.connect` | lesend+schreibend, dies ist die Naht, durch die 1–7 laufen | `lehrmacbook` (importiert von allen obigen) |

**Zahl: 8 Kategorien von Zugreifern, alle unter derselben Kennung
(`lehrmacbook`), 6 davon schreibend (1, 3, 4 teilweise, 6, 7, 8) — Kategorie 2
(die App) greift nachweislich NICHT direkt zu.**

**Was das fuer G5 bedeutet:** Ein zweiter Systembenutzer bricht nicht *einen*
Zugreifer, sondern *sieben* gleichzeitig — jeder Prozess, der `sqlite3.connect`
oder `kern/ausweis.py` direkt aufruft, verliert Schreib- (und je nach
Rechtevergabe auch Lese-)Zugriff, sobald der Bestand einem anderen
Systembenutzer gehoert und die Datei-Rechte eng genug sind. Das ist kein
Ein-Schritt-Umbau, sondern **mindestens drei getrennte Migrationen**: der
Dienst (Kategorie 1, launchd-Neustart als `LaunchDaemon` unter dem neuen
Benutzer), die MCP-Server (Kategorie 3, koennen NICHT umziehen, solange sie
als Klientprozess des angemeldeten Nutzers starten — stdio-MCP kennt keinen
Benutzerwechsel), und alles Uebrige (4–8, manuell gestartete Werkzeuge, die
dann `sudo` oder eine Gruppenzugehoerigkeit brauchen, um noch lesen zu
koennen).

**Der Bruch, der am schwersten wiegt:** Kategorie 3 (MCP) laesst sich mit
Bordmitteln nicht umziehen — ein MCP-Klient (Claude Code) startet seinen
Server-Subprozess immer unter der eigenen Anmeldekennung. Wird `brainlehr.db`
strikt `0600` unter einem fremden Benutzer, verliert **jede laufende
Wissens-Sitzung** Lese- **und** Schreibzugriff, bis eine Gruppenloesung
(gemeinsame Gruppe, `g+rw` auf DB und Ordner, `setgid`) das wieder oeffnet.
Reiner Benutzerwechsel ohne Gruppe macht G5 scharf, aber bricht die MCP-Werkzeuge
komplett — das gehoert in die Abwaegung, bevor der erste Befehl faellt.

## Teil 2 — die Befehlsfolge (nicht ausgefuehrt, nur aufgeschrieben)

Reihenfolge bindend: 1→2 vor 3 (Benutzer muss existieren, bevor ihm etwas
gehoert), 3 vor 4 (Eigner vor Rechten), 4 vor 5 (Rechte vor Dienstumzug).
Schritt 6/7 sind der einzige Teil ohne Rueckweg im engeren Sinn — markiert.

1. **Neuen Systembenutzer anlegen** (versteckt, kein Login-Fenster, keine
   Shell):
   ```sh
   sudo sysadminctl -addUser _brainlehr -fullName "brainlehr Dienst" -home /var/empty -shell /usr/bin/false
   ```
   Tut: legt `_brainlehr` als lokalen Dienstkonto-Benutzer an.
   Hier fragt das System nach deinem Passwort.
   Rueckweg: `sudo sysadminctl -deleteUser _brainlehr`.
   Prüfung: `id _brainlehr` → muss eine UID liefern (vorher: „no such user").

2. **Gemeinsame Gruppe anlegen**, damit MCP-Klienten (Kategorie 3, laufen
   weiter unter `lehrmacbook`) lesend/schreibend bleiben:
   ```sh
   sudo dseditgroup -o create brainlehr-bestand
   sudo dseditgroup -o edit -a lehrmacbook -t user brainlehr-bestand
   sudo dseditgroup -o edit -a _brainlehr -t user brainlehr-bestand
   ```
   Tut: neue Gruppe, beide Benutzer Mitglied.
   Hier fragt das System nach deinem Passwort.
   Rueckweg: `sudo dseditgroup -o delete brainlehr-bestand`.
   Pruefung: `dseditgroup -o checkmember -m lehrmacbook brainlehr-bestand` UND
   `dseditgroup -o checkmember -m _brainlehr brainlehr-bestand` → je „yes".

3. **Eigner der Dateien umziehen**:
   ```sh
   sudo chown _brainlehr:brainlehr-bestand /Volumes/daten/Begod2026/brainlehr/brainlehr.db
   sudo chown -R _brainlehr:brainlehr-bestand ~/Desktop/brainlehr-ausweise
   ```
   Tut: Eigner wechselt von `lehrmacbook` auf `_brainlehr`, Gruppe auf die
   gemeinsame.
   Hier fragt das System nach deinem Passwort.
   Rueckweg: `sudo chown lehrmacbook:staff brainlehr.db` bzw. `-R` fuer den
   Ordner (macht Teil 1 des Fundes O4 wieder rueckgaengig, nicht mehr, nicht
   weniger).
   Pruefung: `stat -f "%Su:%Sg" brainlehr.db` → `_brainlehr:brainlehr-bestand`
   (vorher: `lehrmacbook:admin` bzw. `lehrmacbook:staff`).

4. **Rechte auf Gruppen-Lesen/-Schreiben setzen** (nicht `0600` — sonst bricht
   Kategorie 3 sofort, siehe Teil 1):
   ```sh
   chmod 660 /Volumes/daten/Begod2026/brainlehr/brainlehr.db
   chmod -R 770 ~/Desktop/brainlehr-ausweise
   ```
   Tut: Eigner und Gruppe duerfen lesen/schreiben, „Andere" nichts mehr.
   Braucht **kein** Passwort (der ausfuehrende Benutzer ist nach Schritt 3
   nicht mehr Eigner — dieser Befehl schlaegt nach Schritt 3 ohne `sudo`
   fehl; **also**: `sudo chmod 660 ...` bzw. `sudo chmod -R 770 ...`).
   Hier fragt das System nach deinem Passwort.
   Rueckweg: `sudo chmod 600 brainlehr.db` / `sudo chmod -R 700 ausweisordner`.
   Pruefung: `stat -f "%OLp" brainlehr.db` → `660` (vorher `600`).

5. **Dienst auf den neuen Benutzer umziehen** (Kategorie 1 aus Teil 1):
   ```sh
   launchctl unload ~/Library/LaunchAgents/de.brainlehr.dienst.plist
   sudo cp dienst/de.brainlehr.dienst.plist /Library/LaunchDaemons/de.brainlehr.dienst.plist
   sudo /usr/libexec/PlistBuddy -c "Add :UserName string _brainlehr" /Library/LaunchDaemons/de.brainlehr.dienst.plist
   sudo /usr/libexec/PlistBuddy -c "Add :GroupName string brainlehr-bestand" /Library/LaunchDaemons/de.brainlehr.dienst.plist
   sudo launchctl load /Library/LaunchDaemons/de.brainlehr.dienst.plist
   ```
   Tut: alter LaunchAgent runter, neuer LaunchDaemon (systemweit, unter
   `_brainlehr`) rauf.
   Hier fragt das System nach deinem Passwort (fuer die `sudo`-Zeilen; das
   `launchctl unload` ohne `sudo` nicht).
   Rueckweg: `sudo launchctl unload /Library/LaunchDaemons/de.brainlehr.dienst.plist`,
   Datei loeschen, alten Weg aus `dienst/LIESMICH.md` erneut laden.
   Pruefung: `launchctl print system/de.brainlehr.dienst | grep -i "user ="`
   → `_brainlehr` (vorher gar kein Eintrag unter `system/`, nur unter
   `gui/<uid>/`).

6. **Probe fahren** (dieser Auftrag, `melder/systembenutzer_probe.py`):
   ```sh
   python3 melder/systembenutzer_probe.py
   ```
   Tut: zeigt `g5_erfuellt: true`, wenn 1–4 gewirkt haben.
   Kein Passwort noetig, rein lesend.
   Rueckweg: entfaellt (reine Pruefung).
   Pruefung: ist der Befehl selbst — `g5_erfuellt` im JSON.

**Ohne Rueckweg im engeren Sinn:** keiner der obigen Schritte — jeder ist mit
seinem Gegenbefehl umkehrbar. Der einzige Punkt, der nicht sauber umkehrbar
ist: **laufende MCP-Sitzungen**, die zwischen Schritt 3 und 4 (Eigner
gewechselt, Rechte noch `0600` vom alten Zustand oder bereits `0660`, aber
Gruppenmitgliedschaft aus Schritt 2 noch nicht im Sitzungsprozess wirksam,
weil Gruppenmitgliedschaften erst bei neuem Login/neuer Shell greifen)
`database is locked` oder `permission denied` werfen koennen. Rueckweg dafuer:
MCP-Klient (Claude Code) neu starten, keine Datenaenderung noetig.

## Teil 3 — die Probe

`melder/systembenutzer_probe.py::pruefe()` — vergleicht Dateieigner
(`os.stat().st_uid`) gegen die angemeldete Kennung (`os.getuid()`) und prueft
zusaetzlich `os.access(pfad, os.W_OK)`. `g5_erfuellt` ist nur `True`, wenn
BEIDE Dateien (`brainlehr.db`, Ausweisordner) einem fremden Eigner gehoeren
UND der angemeldete Benutzer nicht mehr schreiben kann — enge Rechte allein
(0600 unter der eigenen Kennung, der heutige Stand nach O4) reichen
ausdruecklich NICHT, das ist genau die Luecke, die Fund O4 als „halb" markiert.

**Heute rot, woertlich** (`python3 melder/systembenutzer_probe.py`, Stand
2026-08-15):
```json
{
  "g5_erfuellt": false,
  "brainlehr_db": {
    "eigner_uid": 501,
    "angemeldeter_uid": 501,
    "fremder_eigner": false,
    "nicht_beschreibbar": false,
    "gilt": false,
    "grund": "Bestand gehoert noch der angemeldeten Kennung -- G5 offen."
  },
  "ausweisordner": { "...": "gleiches Bild, gilt: false" }
}
```
Test dazu: `tests/test_systembenutzer_probe.py::test_g5_ist_heute_noch_nicht_erfuellt`
(rot-vor-gruen belegt live gegen den echten Bestand) und
`::test_probe_wird_gruen_wenn_bestand_fremd_und_nicht_beschreibbar` (Gegenprobe:
simulierter Erfolgsfall wird tatsaechlich `gilt: true` — ohne diesen Test waere
nicht belegt, dass die Probe ueberhaupt umschlagen KANN, statt strukturell immer
`False` zu liefern). Vier Tests insgesamt, `python3 -m pytest
tests/test_systembenutzer_probe.py -q` → `4 passed`.

Nach Ausfuehrung der Befehlsfolge oben wird `g5_erfuellt` bei erneutem Lauf
`true` — das ist der einzige Beleg, der zaehlt, kein „sollte jetzt gehen".

## Grenze — was diese Vorbereitung NICHT abdeckt

- **Sie legt keinen Benutzer an, aendert keinen Eigner, keine Rechte.** Reine
  Vorbereitung, siehe Auftragsgrenzen oben.
- **Sie loest den MCP-Bruch nicht, sie macht ihn nur sichtbar.** Die
  Gruppenloesung in Schritt 2/4 ist ein Vorschlag, kein gemessener Fakt — ob
  `g+rw` unter SQLite bei gleichzeitigem Schreibzugriff aus zwei Kennungen
  (Dienst als `_brainlehr`, MCP als `lehrmacbook`) tatsaechlich kollisionsfrei
  laeuft, ist NICHT geprueft. SQLite-Locking ist dateibasiert, nicht
  kennungsbasiert — das sollte funktionieren, ist aber eine Annahme, keine
  Messung.
- **Sie deckt Kategorien 4–8 aus Teil 1 nicht bis ins letzte Skript ab.** Die
  Zahlen (8/24 Melder, 11/26 Pflegeskripte, 8/14 Pruefstand-Dateien) sind
  Dateizahlen mit einem DB-Zugriffsmuster, keine Einzelpruefung, ob jedes
  dieser Skripte nach dem Umzug noch mit Gruppenrechten laeuft.
- **Sie sagt nichts zu O5/Sandbox-Wechselwirkung.** Ob die App-Sandbox das
  Gruppen-Setup irgendwo beruehrt, ist nicht gemessen (die App greift laut
  Teil 1 ohnehin nicht direkt zu, daher vermutlich irrelevant — aber
  „vermutlich" ist kein Beleg).
- **Sie loest O2 nicht neu aus.** Der Dienst bleibt nach dem Umzug weiter
  unter `127.0.0.1:8799` mit der bestehenden Herkunftspruefung (O2, behoben
  in `91f096a`) — G5 aendert daran nichts, ergaenzt sie nur.
