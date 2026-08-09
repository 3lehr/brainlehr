# Fremde Regelwerke fuer brainlehr — Recherche

Datum: 2026-08-09T07:08:03+0200
Anlass: LLIS-Stichprobe (39 Knoten, 33 domaenenfrei uebertragbar, 13 Bestaetigungen eigener Regeln) legt nahe: fremde, unabhaengig entstandene Regelwerke koennen die eigenen stuetzen. Zwei Fragen: (1) vergleichbare Fallsammlungen, (2) mitzuliefernde Regelwerke — plus die Kernfrage, ob ein System sie selbst finden kann.

Recherchemethode: Websuche, keine Zugangsdaten, keine Downloads ausser dem, was eine normale Recherche liest. Zahlen, die keine Quelle hergab, sind als "nicht ermittelt" markiert, nicht geschaetzt.

---

## 1. Abgesuchte Raster

Bearbeitete Fachgebiete (mit Ergebnis unten):

- Luftfahrt (Vorfallmeldung: freiwillig) — ASRS
- Luftfahrt/Verkehr (Untersuchung: behoerdlich, alle Verkehrstraeger) — NTSB/CAROL
- Anlagensicherheit/Chemie — CSB
- Medizin/Patientensicherheit — AHRQ PSNet/WebM&M, FDA MAUDE
- IT-Betrieb/Software-Ausfaelle — VOID (Verica), danluu/post-mortems, Google-SRE-Postmortem-Kultur
- IT-Sicherheit/Schwachstellen — NVD/CVE, CISA KEV, CWE (MITRE)
- Kernenergie — IAEA/NEA IRS
- Schifffahrt (UK) — MAIB
- Schiene (UK) — RAIB
- Lizenzrecht (Software) — SPDX License List
- Sicherheits-Regelwerke (Web/App) — OWASP ASVS, OWASP Top 10
- Barrierefreiheit (EU-Pendant zu WCAG) — EN 301 549

Bewusst NICHT bearbeitet (Grenze der Zeit, nicht der Relevanz — als Luecke benannt, nicht verschwiegen):

- Luftfahrt-Untersuchung ausserhalb USA/UK: ICAO ADREP, EASA, BEA (Frankreich), BFU (Deutschland) — nur die US/UK-Seite (NTSB, ASRS) und die britische Schiene/See-Seite (RAIB, MAIB) wurden geprueft. Deutsche/europaeische Pendants sind eine offene Flanke.
- Bauwesen/Statik (Versagensanalysen, z. B. ASCE Forensic Engineering) — nicht gesucht.
- Arbeitsschutz allgemein jenseits CSB (OSHA-Fallberichte direkt, nicht nur CSB) — nicht gesucht.
- Landwirtschaft/Lebensmittelsicherheit (z. B. RASFF der EU) — nicht gesucht.
- Militaer/Verteidigung (Lessons-Learned-Systeme wie JLLIS) — bewusst ausgelassen, da Zugang typischerweise nicht offen.
- Finanzaufsicht (SEC-Untersuchungsberichte, Bankenaufsicht) — nicht gesucht.
- Automobil (NHTSA-Rueckrufdatenbank) — nicht gesucht, waere naheliegende Ergaenzung zu NTSB.
- Nicht-englischsprachige Quellen generell — die gesamte Recherche lief auf Englisch; deutschsprachige oder sonstige Fallsammlungen wurden nicht gesucht.

---

## 2. Sammlungen — Merkmalspruefung

Pruefkriterien je Fund: (a) nachpruefbare Einzelfaelle mit Kennung/Datum, (b) fremdes, dokumentiertes Verfahren dahinter, (c) Preis des Irrtums lag beim Urheber (nicht bei Dritten, die nur berichten).

### Treffer

**ASRS — Aviation Safety Reporting System (NASA)**
- Betreiber: NASA Ames, administriert durch Booz Allen Hamilton im Auftrag.
- Umfang: ueber 1,4 Mio. Meldungen seit 1976 (Selbstangabe NASA); Online-Datenbank deckt 1988–heute ab, monatlich aktualisiert.
- Zugang: https://asrs.arc.nasa.gov/search/database.html, Suchmaske + Volltextexport.
- Lizenz: keine explizite Lizenzangabe gefunden; als Bundeswerk der NASA im Kern gemeinfrei (Public Domain), Verwaltung durch Auftragnehmer moeglicherweise mit Nutzungshinweisen — nicht abschliessend geklaert, daher "nicht ermittelt" fuer die exakte Lizenzformel.
- Format: strukturierte Datensaetze (Ereignis, Faktoren, Erzaehltext), CSV/HTML-Export ueber Suchmaske.
- Merkmalspruefung: (a) ja, ID + Datum je Meldung; (b) ja, festes Kodierschema (ASRS Coding Taxonomy); (c) ja, Meldende sind selbst Beteiligte, deren Fehler beschrieben wird.
- Uebertragbarkeit auf Softwarearbeit: mittel-hoch. Freiwillige, deidentifizierte Selbstmeldung ist ein Verfahrensmuster (kein Vorwurf, sondern Lernanreiz), das sich auf Incident-Reporting in Software direkt uebertraegt — naeher an brainlehrs Rot-vor-Gruen-Kultur als an LLIS' fertigen Lehren.

**NTSB / CAROL (Case Analysis and Reporting Online)**
- Betreiber: National Transportation Safety Board (US-Bundesbehoerde).
- Umfang: rund 180.000 historische Datensaetze; Luftfahrt ab 1962, andere Verkehrstraeger (Schiene, Pipeline, Gefahrgut, Strasse, Schiff) ab 2010.
- Zugang: https://data.ntsb.gov/carol-main-public/query-builder, plus API fuer Partnerbehoerden.
- Lizenz: als US-Bundesbehoerdenwerk grundsaetzlich gemeinfrei; explizite Lizenzformel auf der Website nicht gefunden ("nicht ermittelt").
- Format: durchsuchbare Datenbank, Berichte als PDF, Dockets mit Rohdaten.
- Merkmalspruefung: (a) ja, Fallnummer + Datum; (b) ja, formales Untersuchungsverfahren mit Probable-Cause-Feststellung; (c) ja, behoerdlich unabhaengig von den untersuchten Organisationen.
- Uebertragbarkeit: mittel. Sehr belastbares Verfahren, aber Domaene (Fahrzeugunfaelle) liegt weiter von Software weg als IT-eigene Quellen; Wert liegt im Verfahren selbst (Ursachenkette, Empfehlungswesen), nicht im Fallinhalt.

**CSB — U.S. Chemical Safety and Hazard Investigation Board**
- Betreiber: unabhaengige US-Bundesbehoerde.
- Umfang: 129 abgeschlossene Untersuchungen ueber rund 25 Jahre (Stand einer 2024er Quelle); Tempo stark schwankend (historisch ca. 3/Jahr, 2023 elf Berichte).
- Zugang: https://www.csb.gov/ (offizielle Berichte), zusaetzlich Drittanbieter-Wiki https://incidents.tychodata.com/ (aggregiert CSB-Inhalte).
- Lizenz: Bundeswerk, grundsaetzlich frei nutzbar unter US-Open-Data-Politik; exakte Lizenzformel auf csb.gov nicht verifiziert ("nicht ermittelt").
- Format: PDF-Berichte, Safety Bulletins, Videos; kein strukturiertes Massendatenformat gefunden.
- Merkmalspruefung: (a) ja; (b) ja, standardisierte Root-Cause-Methodik; (c) ja, Preis (Explosionen, Todesfaelle) lag bei den untersuchten Betrieben selbst.
- Uebertragbarkeit: hoch fuer das Verfahren (Root-Cause-Baum, Empfehlungen an Regulierer UND Betreiber getrennt), gering fuer den Fallinhalt selbst (Prozesssicherheit, nicht Software). Geringer Umfang (129 Faelle) im Vergleich zu LLIS (1638 Knoten).

**AHRQ PSNet / WebM&M (Patientensicherheit)**
- Betreiber: Agency for Healthcare Research and Quality (US-Bundesbehoerde).
- Umfang: nicht ermittelt als Fallzahl; PSNet-Gesamtressource nennt ca. 11.000 Ressourcen (Artikel, Berichte, Websites), davon WebM&M ein monatlicher Fall+Kommentar-Strom, keine Gesamtfallzahl gefunden.
- Zugang: https://psnet.ahrq.gov/, https://www.ahrq.gov/cpi/about/otherwebsites/webmm.ahrq.gov/index.html
- Lizenz: nicht ermittelt (US-Bundesressource, vermutlich frei nutzbar, aber keine explizite Lizenzangabe gefunden).
- Format: redaktionelle Fallberichte mit Experten-Kommentar, kein Rohdatenexport.
- Merkmalspruefung: (a) teilweise — Faelle sind anonymisiert/deidentifiziert, keine pruefbare Kennung wie bei ASRS/CSB; (b) ja, redaktionelles Peer-Review-Verfahren; (c) ja im Ursprung (Behandlungsfehler), aber durch Anonymisierung nicht extern nachpruefbar.
- Uebertragbarkeit: mittel, vor allem als Vorbild fuer FORMAT ("Fall + Kommentar", nicht nur Rohfall) — naeher an brainlehrs Zielbild eines Nachschlagewerks als an einer reinen Datenbank.

**FDA MAUDE (Medical Device Adverse Events)**
- Betreiber: US Food and Drug Administration.
- Umfang: ueber 24 Mio. Berichte (Meldungen, nicht Einzelfaelle mit Ursachenanalyse); Datenbank wird laut Suche 2026 in "AEMS" ueberfuehrt (Konsolidierung mehrerer Systeme, Abschluss angeblich Mai 2026 — nicht verifiziert, da nach Wissensstand der Suche).
- Zugang: MAUDE-Weboberflaeche, openFDA-API, Bulk-Downloads — frei, ohne Registrierung.
- Lizenz: als FDA/Bundeswerk grundsaetzlich frei; openFDA-Nutzungsbedingungen nicht im Detail geprueft ("nicht ermittelt").
- Format: strukturierte Meldedaten (JSON/CSV via API).
- Merkmalspruefung: (a) ja, Berichts-ID + Datum; (b) teilweise — MAUDE ist primaer eine MELDESAMMLUNG, keine abgeschlossene Ursachenanalyse je Fall (anders als CSB/NTSB); (c) gemischt, da viele Meldungen vom Hersteller selbst stammen (Pflichtmeldung), nicht immer vom Geschaedigten.
- Uebertragbarkeit: gering-mittel. Grosser Umfang, aber naeher an einer Rohdaten-Fehlerdatenbank als an einer Lehren-Sammlung — muesste erst durch eigene Analyse zu "Lessons" verdichtet werden, das leistet die Quelle selbst nicht.

**VOID — Verica Open Incident Database (Software-Vorfaelle)**
- Betreiber: Verica (kommerzielles Unternehmen, community-getragen weitergefuehrt).
- Umfang: ueber 10.000 kategorisierte Artefakte (Postmortems, Statusseiten, Konferenzvortraege) von 590 Organisationen.
- Zugang: https://www.thevoid.community/database
- Lizenz: nicht ermittelt (Community-Projekt, Lizenzangabe auf der Seite nicht verifiziert).
- Format: kuratierte Linksammlung/Katalog zu Originalquellen, kein einheitliches Datenschema ueber alle Eintraege.
- Merkmalspruefung: (a) teilweise — Herkunftsdatum und Organisation meist vorhanden, aber uneinheitliche Tiefe je Quelle; (b) schwach — VOID selbst aggregiert nur, das Verfahren dahinter ist das der jeweils meldenden Firma (uneinheitlich); eigener Befund aus VOID: nur ein Viertel der Berichte nennt ueberhaupt eine Ursache; (c) ja, Preis lag bei der jeweils berichtenden Organisation.
- Uebertragbarkeit: hoch als Domaenen-Treffer (ist Software), aber schwach als VERFAHREN — VOID selbst warnt vor der Qualitaet der Einzelquellen. Eher Fundgrube als geprueftes Nachschlagewerk.

**danluu/post-mortems (GitHub-Sammlung) + Google-SRE-Postmortem-Kultur**
- Betreiber: privat kuratiertes GitHub-Repo (danluu) bzw. Google (SRE-Buch/Workbook als Methodendokument, nicht als Fallsammlung).
- Umfang: nicht ermittelt (Linksammlung, keine Zaehlung gefunden).
- Zugang: https://github.com/danluu/post-mortems (offen, PRs moeglich); Google SRE Book/Workbook frei online (https://sre.google/sre-book/postmortem-culture/).
- Lizenz: danluu-Repo vermutlich Standard-GitHub-Lizenzlage (nicht verifiziert); Google-SRE-Buch unter CC BY.
- Format: Linksammlung zu Originalpostmortems verschiedener Firmen; Google-Buch ist Prosa/Methodik, kein Fallkorpus.
- Merkmalspruefung: (a) unterschiedlich je verlinkter Quelle, nicht einheitlich; (b) das Google-SRE-Material liefert das VERFAHREN (blameless postmortem) sehr klar dokumentiert, aber keine Falldatenbank; (c) ja bei den verlinkten Originalquellen.
- Uebertragbarkeit: das SRE-Verfahren (blameless, strukturierte Root-Cause-Vorlage) ist die naechste Verwandte zu brainlehrs eigenem Anspruch, aber es ist ein METHODENDOKUMENT, keine Fallsammlung wie LLIS.

**CISA KEV (Known Exploited Vulnerabilities), NVD/CVE, CWE (MITRE)**
- Betreiber: CISA (KEV), NIST (NVD), MITRE (CVE-Programm, CWE) — alle US-staatlich getragen bzw. -gesponsert.
- Umfang: CVE/NVD nicht exakt beziffert in dieser Recherche (bekannt gross, sechsstellig), KEV deutlich kleiner (kuratierte Teilmenge tatsaechlich ausgenutzter Schwachstellen).
- Zugang: NVD als XML/JSON-Feeds frei ohne Gebuehr/Registrierung; KEV als CSV/JSON auf github.com/cisagov/kev-data; CWE als Downloadliste auf cwe.mitre.org.
- Lizenz: NVD/CVE gemeinfrei (Title 17 US Code, Bundeswerk), KEV-Daten unter CC0 (explizit, github.com/cisagov/kev-data); CWE unter eigenen "Terms of Use" (SPDX-Referenz "LicenseRef-scancode-cwe-tou"), NICHT Standard-Open-Source-Lizenz.
- Format: strukturierte Feeds (JSON/CSV/XML).
- Merkmalspruefung: (a) ja, CVE-ID + Datum; (b) ja, formales Aufnahmeverfahren (CNA-Prozess bei CVE, Ausnutzungsnachweis bei KEV); (c) gemischt — der "Schaden" traf die betroffenen Organisationen, nicht die meldende Stelle; CVE/CWE sind eher technische Klassifikation als Lehren-aus-Schaden-Sammlung im LLIS-Sinn.
- Uebertragbarkeit: hoch als KATALOG (Fehlerklassen, CWE als Taxonomie von Schwachstellenarten ist strukturell mit BSI-Controls vergleichbar), aber die einzelne CVE ist kein narrativer Lernfall wie ein LLIS-Eintrag.

**IAEA/NEA IRS (Incident Reporting System, Kernenergie)**
- Betreiber: IAEA gemeinsam mit OECD/NEA.
- Umfang: nicht ermittelt.
- Zugang: EINGESCHRAENKT — nur autorisierte Nutzer teilnehmender Laender, nicht oeffentlich.
- Lizenz: entfaellt (kein oeffentlicher Zugang).
- Merkmalspruefung: (a)/(b) vermutlich stark (aeltestes und strengstes Verfahren der Liste), aber nicht nachpruefbar mangels Zugang; (c) ja im Ursprung.
- Uebertragbarkeit: NICHT BEWERTBAR mangels Zugang. Als Vorbild fuer VERFAHRENSSTRENGE dennoch interessant (naechster Schritt waere ein Blick in oeffentliche IAEA-Publikationen ueber das Verfahren, nicht die Falldaten selbst).

**MAIB (Marine Accident Investigation Branch, UK) und RAIB (Rail Accident Investigation Branch, UK)**
- Betreiber: beide unabhaengige Stellen des UK Department for Transport.
- Umfang: MAIB-Datenbank seit 1991 (reportable accidents), RAIB-Umfang nicht ermittelt.
- Zugang: MAIB-Datenportal https://maps.dft.gov.uk/maib-data-portal/ (anonymisierte Teilmenge, halbjaehrlich aktualisiert), RAIB-Berichte unter gov.uk/raib-reports.
- Lizenz: als UK-Regierungsstelle vermutlich Open Government Licence (nicht explizit auf den gefundenen Seiten verifiziert, "nicht ermittelt").
- Format: PDF-Berichte, MAIB zusaetzlich Schiffs-Datenbank.
- Merkmalspruefung: (a) ja; (b) ja, unabhaengige gesetzlich verankerte Untersuchung; (c) ja, Preis trug jeweils der untersuchte Betrieb/Schiff/Bahnbetreiber.
- Uebertragbarkeit: mittel, strukturell aehnlich zu NTSB — Wert liegt im Verfahren, nicht im Fallinhalt.

### Geprueft und verworfen

- **CSB Incident Wiki (incidents.tychodata.com)** — verworfen als EIGENSTAENDIGE Quelle: es ist ein Drittanbieter-Aggregat der offiziellen CSB-Berichte, keine eigene Faktenbasis. Fuer eine Uebernahme waere die Originalquelle (csb.gov) massgeblich, nicht das Wiki.
- **PSNet-Gesamtbestand jenseits WebM&M** (11.000 Ressourcen: Zeitschriftenartikel, Buecher) — verworfen als Fallsammlung im LLIS-Sinn: das ist ueberwiegend Sekundaerliteratur UEBER Patientensicherheit, keine Sammlung nachpruefbarer Einzelfaelle mit Kennung.
- **IAEA/NEA IRS als Ganzes** — de facto verworfen fuer eine Uebernahme (nicht fuer die Bewertung), weil der Zugang auf autorisierte Fachleute teilnehmender Laender beschraenkt ist; brainlehr haette keinen legalen Zugriffsweg.
- **FDA MAUDE als Lehren-Quelle** (nicht als Rohdaten-Quelle) — verworfen: die Datenbank ist eine Meldesammlung ohne abgeschlossene Ursachenanalyse je Fall; das unterscheidet sie kategorisch von LLIS, CSB, NTSB. Waere nur nach eigener Nachbearbeitung brauchbar, nicht im Rohzustand.
- **VOID als geprueftes Verfahren** — die Domaenenpassung (Software) ist die staerkste aller Funde, aber VOID warnt selbst, dass ein Grossteil der aggregierten Postmortems keine Ursache benennt; als NACHSCHLAGEWERK (fertige Lehren) daher schwaecher als LLIS, eher Rohmaterial fuer eigene Auswertung.

---

## 3. Mitzuliefernde Regelwerke

### Allgemeingueltig (gilt unabhaengig von der Domaene des Nutzers)

| Regelwerk | Warum dazugehoert | Herkunft | Stabilitaet | Einschraenkung |
|---|---|---|---|---|
| WCAG 2.2 AA (bereits vorhanden) | Barrierefreiheit gilt fuer jede Oberflaeche, unabhaengig von der Branche | W3C | hoch, 2.2 seit Okt. 2023 final, 3.0 in Arbeit | keine, offener Standard |
| EN 301 549 | EU-rechtliche Ebene ueber WCAG hinaus (Hardware, Telekommunikation, biometrische Zugaenge); relevant sobald ein Nutzer in der EU an Endkunden liefert | ETSI/CEN/CENELEC, basiert auf WCAG 2.1 AA (2.2 ab Version 4.1.1, 2026 erwartet) | mittel — folgt WCAG mit Verzoegerung | nur einschlaegig bei EU-Marktzugang, sonst Overhead ohne Nutzen |
| SPDX License List | Lizenzpruefung von Abhaengigkeiten ist branchenunabhaengig noetig, sobald fremder Code eingebunden wird | Linux Foundation / SPDX-Projekt | hoch, aktiv gepflegt, IDs bleiben stabil (Deprecation statt Loeschung) | erfordert eigene Zuordnung Paket→Lizenz, liefert nur das Vokabular, keine automatische Pruefung |
| CWE (MITRE) | Taxonomie von SchwachstellenARTEN, ergaenzt das BSI-Profil um eine international anerkannte Klassifikation | MITRE/CISA-gesponsert | hoch, Versionsnummern, aktiv gepflegt | eigene Terms of Use, keine Standard-OSS-Lizenz — Weitergabe pruefen, nicht automatisch wie CC0 |
| OWASP ASVS / OWASP Top 10 | Konkreter, pruefbarer Kontrollkatalog fuer Anwendungssicherheit, ergaenzt BSI-Profil um Web/App-spezifische Tiefe | OWASP Foundation | mittel-hoch, ASVS regelmaessig versioniert, Top 10 alle paar Jahre neu | CC BY-SA 4.0 — Weitergabe muss Lizenz nennen und Ableitungen unter gleicher Lizenz stellen (Copyleft-Pflicht!) |
| CISA KEV | Ergaenzt CVE/NVD um die praktisch relevante Teilmenge ("tatsaechlich ausgenutzt"), kompakter als Vollkatalog | CISA | hoch, taeglich aktualisiert | CC0, keine Einschraenkung |
| NVD/CVE (NIST/MITRE) | Referenzkatalog fuer bekannte Schwachstellen, Grundlage jeder Dependency-Pruefung | NIST/MITRE | hoch, Kernstandard der Branche | gemeinfrei, keine Einschraenkung |

Datenschutz (DSGVO/GDPR) wurde als Kandidat geprueft, aber NICHT in die Tabelle aufgenommen: es ist kein "Regelwerk" im Sinne pruefbarer Einzelkontrollen wie BSI/WCAG, sondern ein Rechtstext mit Auslegungsbedarf durch Juristen — eine automatische Uebernahme waere Anmassung. Empfehlung waere hoechstens, DSGVO-PRINZIPIEN (Zweckbindung, Datenminimierung) als Merksatz zu fuehren, nicht den Gesetzestext als Kontrollkatalog.

### Domaenenspezifisch (nur wenn der Nutzer in der Domaene arbeitet)

| Regelwerk | Domaene | Warum dazugehoert | Herkunft | Stabilitaet | Einschraenkung |
|---|---|---|---|---|---|
| CSB-Root-Cause-Methodik | Anlagen-/Prozesssicherheit | Wenn brainlehr bei einem Betreiber chemischer/industrieller Anlagen liefe, waere die CSB-Ursachenbaum-Methode das naechste Pendant zu LLIS | CSB (US-Bundesbehoerde) | mittel, Verfahren stabil, Fallzahl klein (129) | Bundeswerk, vermutlich frei, exakte Lizenz nicht verifiziert |
| NTSB-Probable-Cause-Verfahren | Verkehr/Transport | Bei einem Nutzer aus Transport/Logistik-Software waere das NTSB-Untersuchungsschema die naechste Domaenenquelle | NTSB | hoch | Bundeswerk, vermutlich frei, exakte Lizenz nicht verifiziert |
| Google-SRE-Postmortem-Schema | Software-Betrieb/SRE | Direktestes Pendant zur eigenen Domaene (Software), liefert eine PRUEFBARE VORLAGE (blameless, Ursache, Zeitachse) statt nur Prosa | Google | hoch, seit Jahren stabil publiziert | CC BY, Weitergabe mit Namensnennung erlaubt |
| AHRQ WebM&M-Format | Medizinische/Gesundheits-Software | Falls ein Nutzer im Gesundheitswesen arbeitet: Format "Fall + Kommentar" als Vorbild fuer eigene Lehrentexte | AHRQ (US-Bundesbehoerde) | mittel | Lizenz nicht ermittelt |
| IAEA-IRS-Verfahrensbeschreibung (nicht die Falldaten) | Sicherheitskritische Steuerungssoftware | Als Vorbild fuer die STRENGE des Verfahrens (nicht als Falldatenquelle, da Zugang beschraenkt) | IAEA/OECD-NEA | hoch | oeffentliche Verfahrensbeschreibungen frei, Falldaten nicht zugaenglich |

---

## 4. Der Weg zum Selberfinden

Kernfrage: Kann ein System wie brainlehr solche Regelwerke SELBST finden — ohne dass jemand sie nennt, und ohne beliebiges Netz-Sammelverhalten?

**Ergebnis vorweg: Teilweise ja, mit einer harten Grenze — und die Grenze ist wichtiger als der Weg.**

### Was nachpruefbar automatisierbar waere

Ein System kann aus dem eigenen Bestand Signale ziehen, OHNE frei im Netz zu suchen:

1. **Domaenenerkennung aus dem eigenen Korpus, nicht aus dem Netz.** brainlehr kennt bereits, welche Faelle/Regeln im eigenen Wissensspeicher liegen (Tags, Projektzuordnung). Aus der Verteilung laesst sich ableiten, in welchen Domaenen der Nutzer tatsaechlich arbeitet (z. B. "Gesundheitsdaten kommen in 40 % der Knoten vor" → Kandidat AHRQ/HIPAA-Nachbarschaft). Das ist eine MESSUNG am eigenen Bestand, kein Vermuten.
2. **Ein FESTES, kuratiertes Kandidatenregister statt freier Suche.** Genau diese Recherche liefert eine Liste von Kandidaten mit Merkmalspruefung (Abschnitt 2/3). Ein System duerfte diese Liste periodisch neu PRUEFEN (existiert die Quelle noch, hat sich die Lizenz geaendert, gibt es eine neue Version) — das ist nachpruefbares Nachschlagen in einer begrenzten, von einem Menschen freigegebenen Menge, kein Sammelverhalten.
3. **Registrierungsstellen als Ankerpunkte, nicht Volltextsuche.** Es gibt tatsaechlich zentrale, begrenzte Verzeichnisse, die selbst kuratieren: SPDX (fuer Lizenzen), CWE/CVE (fuer Schwachstellenklassen), W3C-Standardverzeichnis (fuer Web-Standards). Ein System, das nach NEUEN Regelwerken sucht, kann sich auf solche ANERKANNTEN VERZEICHNISSE beschraenken statt auf eine allgemeine Web-Suche — das reduziert das Risiko, eine unseriose Quelle aufzunehmen, ohne dass ein Mensch jede Quelle einzeln nennen muss.
4. **Das Drei-Merkmale-Raster aus dieser Recherche als Filter, nicht als Meinung.** Jeder Fund muss (a) nachpruefbare Einzelfaelle/Kontrollen mit Kennung, (b) ein dokumentiertes fremdes Verfahren, (c) Publikation durch die Stelle, die den Schaden/die Autoritaet selbst traegt, erfuellen. Das ist eine MASCHINELL PRUEFBARE Checkliste (existiert eine ID? existiert eine Verfahrensbeschreibung? ist der Herausgeber die pruefende oder die geschaedigte Stelle?), kein Geschmacksurteil.

### Wo die harte Grenze liegt

1. **Lizenzbewertung ist keine Faktenfrage, sondern eine rechtliche Wertung.** Diese Recherche selbst musste mehrfach "nicht ermittelt" schreiben, weil eine Lizenzseite keine klare Formel nennt (ASRS, NTSB, CSB, MAIB/RAIB, PSNet, VOID). Ein automatisches System, das eine Lizenz FALSCH einordnet (z. B. CC BY-SA mit Copyleft-Pflicht wie bei OWASP als "frei nutzbar" behandelt), erzeugt einen rechtlichen Fehler, der sich erst spaet zeigt. Das ist keine Aufgabe fuer automatische Klassifikation ohne menschliche Freigabe.
2. **Domaenenspezifische Autoritaet ist nicht an Popularitaet erkennbar.** Die Abgrenzungsregel des Auftrags selbst ("keine Bewertung nach Ansehen") gilt genauso fuer ein automatisches System: eine hohe Trefferzahl in einer Suchmaschine ist kein Beleg fuer die drei Merkmale (siehe IAEA IRS: schwer auffindbar, aber vermutlich das strengste Verfahren der ganzen Liste; VOID: leicht auffindbar, aber selbst mit der Einschraenkung, dass ein Grossteil der Quellen keine Ursache nennt). Popularitaet und Verfahrensguete laufen auseinander — ein automatischer Rang nach Trefferzahl waere die falsche Metrik.
3. **Der Unterschied zwischen "Kandidat vorschlagen" und "Kandidat einspielen" muss bei einem Menschen bleiben.** Genau das schreibt der Auftrag selbst vor ("keine Empfehlung, etwas einzuspielen"). Ein automatischer Weg darf also NUR bis zur Kandidatenliste mit Merkmalspruefung fuehren (wie in dieser Datei), nie bis zur Uebernahme. Diese Grenze ist keine technische, sondern eine Entwurfsentscheidung, die bei jeder Automatisierung erhalten bleiben muss, sonst kippt "Kandidaten pruefen" in "beliebig sammeln" — genau das Risiko, das die Aufgabe ausdruecklich ausschliessen wollte.

### Zusammengefasst als Verfahren

Ein verantwortbarer automatischer Weg waere ein PERIODISCHER, gedeckelter Lauf, kein freies Krabbeln:
- Domaenensignal aus dem EIGENEN Bestand ziehen (kein Raten).
- Nur in einer kleinen Menge ANERKANNTER Register-/Verzeichnisstellen nachsehen (SPDX, CWE/CVE, W3C, ggf. je Domaene ein behoerdliches Aequivalent wie CSB/NTSB), nicht in der offenen Websuche.
- Jeden Fund gegen das Drei-Merkmale-Raster UND eine Lizenzpruefung laufen lassen; beides scheitert lieber mit "nicht ermittelt" als mit einer Vermutung.
- Ergebnis ist IMMER eine Kandidatenliste mit Beleg, nie eine automatische Uebernahme — die Entscheidung bleibt beim Betreiber, wie in dieser Datei selbst vorgemacht.

Diese Grenze ist der eigentliche Befund der Kernfrage: nicht "es gibt keinen Weg", sondern "der Weg endet technisch belegbar an der Stelle, an der eine rechtliche oder Vertrauens-Wertung beginnt — und genau dort muss er enden."
