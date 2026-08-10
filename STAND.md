# STAND brainlehr — 2026-08-10T06:40:00+0200

Gebaut auf Zweig `brainlehr/b4-ausweis` (17 Commits, NICHT gepusht): B4.1-B4.5.
Identitaet aus Ausweis statt Behauptung (`ausweis.py`), Durchsetzung an
`tools/call` (`werkzeugrechte.py`), Bezug :own/:published, Einbuergerungsamt
(`ausweis:ausstellen`, nicht delegierbar, Gruendungsakt ausgenommen). Dazu
`normbezug.py` — meldet bei jeder Antwort unbelegte Normzitate und erfundene
Kennungen, verdrahtet in `haken/antwort_abruf.py --stop`. Entscheidung: ADR-002.
Nebenbefund mit groesster Wirkung: der Bereichsfilter kannte `systemweit` nicht —
150 Lehren waren bei gesetztem scope unsichtbar, jetzt behoben.
Naechstes: B4.6 Verfassung, Zweckprojektion (Konzept Kap. 7b), Abstimmung.
WICHTIG: `weich` ist die Vorgabe und KEIN Schutz — ohne Ausweis darf jeder
alles. Wartet auf den Betreiber: ersten Ausweis anlegen (Gruendungsakt),
`sudo chown root` am Ausweisordner, `BRAINLEHR_DURCHSETZUNG=streng`.
