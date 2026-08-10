# Fremdbestände: was drin ist und was noch fehlt

Ausgelagert aus `README.md` (2026-08-10T09:10:00+0200).

brainlehr enthält einen fremden Prüfkorpus, damit die Abrufmessungen nicht nur
gegen den eigenen, selbst geschriebenen Bestand laufen — sonst misst man die
eigene Schreibweise statt der Suchgüte.

| Quelle | Betreiber | Ampel | Stand |
|---|---|---|---|
| [NASA LLIS](https://llis.nasa.gov/) | NASA | 🟢 grün | **1.637 Einträge importiert**, in `auszug-offen/` enthalten |
| [ESA Lessons Learned](https://www.esa.int/) | ESA | ⚪ ungeprüft | offen |
| [ASRS](https://asrs.arc.nasa.gov/search/database.html) | NASA/FAA | ⚪ ungeprüft | offen |
| [FAA Lessons Learned](https://lessonslearned.faa.gov/) | FAA | ⚪ ungeprüft | offen |
| [NRC Licensee Event Reports](https://www.nrc.gov/reading-rm/doc-collections/event-status/) | US NRC | ⚪ ungeprüft | offen |
| [CROSS](https://www.cross-safety.org/) | CROSS-UK/US | ⚪ ungeprüft | vertrauliche Meldungen — Weitergabe voraussichtlich nicht gedeckt |
| [NIST](https://www.nist.gov/) | NIST | ⚪ ungeprüft | Teilbestand noch zu benennen |
| [FDA MAUDE](https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfmaude/search.cfm) | FDA | ⚪ ungeprüft | **Art.-9-Risiko**: Gesundheitsdaten möglich |
| [IAEA IRS](https://www.iaea.org/) | IAEA | ⚪ ungeprüft | Zugang beschränkt — voraussichtlich rot |
| [BSI Stand-der-Technik-Bibliothek](https://github.com/BSI-Bund/Stand-der-Technik-Bibliothek) | BSI | 🟢 grün | CC BY-SA 4.0 — `bsi-dev-profile.json` liegt bei, **Share-Alike** siehe `NOTICE` |

Die Ampel steht in `quellen/fremdquellen.json` mit Prüfauftrag je Quelle.
**Vorgabe ist deny:** Was nicht ausdrücklich grün ist, wird weder importiert noch
weitergegeben.

Warum überall „ungeprüft": Lizenzangaben aus einem Modellgedächtnis sind wertlos
— es ist eingefroren, und Nutzungsbedingungen ändern sich. Die Felder
`lizenz_vermutet` und `url` tragen diesen Vorbehalt ausdrücklich; grün wird eine
Zeile erst, wenn jemand die Lizenzseite aufgerufen und Datum plus Fundstelle
eingetragen hat.

**Zum BSI-Profil:** Quelle ist die
[BSI Stand-der-Technik-Bibliothek](https://github.com/BSI-Bund/Stand-der-Technik-Bibliothek)
unter **CC BY-SA 4.0** — kommerzielle Nutzung, Bearbeitung und Weitergabe sind
erlaubt. Die **Share-Alike-Bedingung** gilt und steht in `NOTICE`: Das
abgeleitete Profil bleibt CC BY-SA 4.0, unabhängig von der Lizenz des übrigen
Quelltextes.

Und der Katalog hat eine gemessene
Lücke: **keine Controls zu Negativtests, Grenzwertprüfung, Nachweis der
Testwirksamkeit und statischer Analyse.** Wer diese vier Bereiche regelt, trifft
eine eigene Entscheidung — „Stand der Technik laut BSI" deckt sie nicht.

---

