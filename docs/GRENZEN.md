# Was brainlehr ausdrücklich NICHT ist

Ausgelagert aus `README.md` (2026-08-10T09:10:00+0200). Diese Liste ist
wichtiger als jede Merkmalsliste, weil sie das Vertrauen bestimmt.

Diese Liste ist wichtiger als die obere, weil sie das Vertrauen bestimmt:

- **Keine Anonymisierung.** `kanonymitaet.py` *misst* k-Anonymität und
  verwendet das Wort „anonym" bewusst nie — ob ein gemessenes k genügt, ist
  eine Rechtsfrage und hängt von Kontextwissen ab, das keine Datenbank hat.
  Das Werkzeug liefert die Zahl, den Schluss zieht ein Mensch.
- **Keine Verschlüsselung.** Die Hashkette weist Änderungen nach, sie verhindert
  sie nicht.
- **Keine BSI-Zertifizierung.** Es gibt ein Prüfprofil und harte Verbote
  (keine Secrets im Code, kein `eval` auf Nutzereingaben, Passwort-Hashing).
  „Erfüllt den Stand der Technik" wäre eine Behauptung, kein Nachweis.
- **Kein *vollständiger* Schutz gegen Promptinjektion — aber auch nicht nichts.**
  Gebaut ist `einschleusung.py`, dreistufig und am Schreibvorgang verdrahtet:
  jeder Bestandstext wird bei der Ausgabe als **Daten abgegrenzt und
  gekennzeichnet** (das ist der eigentliche Schutz), dazu kommen
  sprachunabhängige Anomaliesignale (Skriptmischung, kodierte Blöcke,
  verwechselbare Zeichen) und zuletzt Wortmuster. 16 Angriffsformen im
  Selbsttest erkannt, 9 harmlose Gegenbeispiele nicht.
  Was es **nicht** leistet, sagt das Modul selbst: eine Musterliste ist
  prinzipiell unvollständig, ein umformulierter Angriff fällt durch jedes
  Regex-Set. Und ein Fund **blockiert nicht** — sonst könnte eine geschickte
  Formulierung das Schreiben fremder, legitimer Einträge verhindern.
  Die Grenze darüber bleibt: Rechte begrenzen den *Radius*, nicht die
  *Möglichkeit* — wer den Kontext eines Modells steuert, handelt mit dessen
  Rechten, und die Prüfung sieht einen legitimen Aufruf
  (`docs/KONZEPT_BETEILIGUNG_UND_DATENPUNKTE_2026-08-09.md`, Kapitel 5b).
- **Kein Mehrbenutzerbetrieb.** Ausweise und Rollen existieren, aber der
  Transport ist stdio: ein Prozess, ein Rechner. HTTP ist entschieden
  (`ADR-001`), nicht gebaut.
- **Die Rechtedurchsetzung ist per Vorgabe WEICH.** Ohne gesetztes
  `BRAINLEHR_DURCHSETZUNG=streng` wird ein Schreibvorgang ohne Ausweis
  ausgeführt und lediglich als `unbeglaubigt_weich:<recht>` vermerkt — er wird
  **nicht** abgewiesen. Erst `streng` weist jeden schreibenden Aufruf ohne
  Ausweis zurück (`kein_ausweis_streng:<recht>`).

  Das ist Absicht und keine Nachlässigkeit: Eine frische Instanz hat keinen
  Ausweis, und eine harte Vorgabe würde jeden Erstlauf blockieren, bevor
  jemand einen anlegen kann. Es heißt aber, dass die Zuschreibung im
  Auslieferungszustand eine **Kennzeichnung** ist und keine **Schranke**.
  Wer die Schranke will, setzt die Variable — und muss vorher einen Ausweis
  angelegt haben, sonst schreibt niemand mehr.

