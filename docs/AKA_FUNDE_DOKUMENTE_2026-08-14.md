# AKA-Funde: Dokumenterzeugung, Design-Guide, Präsentationen, Tabellen — 2026-08-14T00:00:00+0200

Suchraeume: aka-raumstation, design-lab/apps/{aka-*,akapp}, aka1, "aka 22".
Eigene Datei. Nichts geaendert, kein git.

## Q4 Tabellen/Tabellenkalkulation — NICHTS gefunden, weder lesend noch schreibend
Grep xlsx|csv|excel|tabellenkalkulation ueber aka-raumstation + design-lab/apps/aka* + Konsile:
0 Treffer die xlsx/Excel als Funktion beschreiben. Einzige Treffer (2. Muster, Taetigkeit statt Name):
`design-lab/begod/knowledge/konsil/konsil-phoenix-universal-scanner-roadmap-2025-07-01.json:142,464,470`
— DOCX/XLSX/PPTX dort nur als ZIP-Recovery-Ziel genannt (Datei-Wiederherstellung nach Korruption),
nicht Lesen/Erzeugen/Bearbeiten von Tabelleninhalt. Gehoert nicht zu AKA, ist Phoenix-App.
Ergebnis: kein Beschluss zu lesenden ODER rechnenden Tabellen in AKA. Leere Antwort ist der Befund.

## Q3 Praesentationen — NICHTS erzeugt, nur als Negativ-Kontrast erwaehnt
`konsil-akapp-ueberzeugungsstrategie-2026-03-02.json:167,207` + `konsil-akapp-demo-pitch-2026-03-04.json:43`
+ `konsil-akapp-stakeholder-pitch-2026-03-02.json:86,354`: PowerPoint wird 5x genannt, immer als das,
was die Live-Demo SCHLAEGT ("Ein funktionierender Prototyp ueberzeugt 10x mehr als eine PowerPoint").
Kein Beschluss zur Erzeugung von Folien. Kein pptx-Generator im Repo gefunden (find leer).

## Q1 Dokumenterzeugung (PDF/Druck/Vorlage/Zertifikat) — nur LESEN, nicht ERZEUGEN
`aka-raumstation/begod/SYSTEM_PROTOCOLS.md:240-250` Protokoll P25 "Volltext-Pflicht fuer Wissens-PDFs":
Pflicht, dass jedes Paper-PDF (`knowledge/apps/<app>/papers/`) einen Volltext-TXT via PyMuPDF bekommt.
Das ist PDF-LESEN (Extraktion), nicht Erzeugen. Begruendet: "Snippets reichen nicht" — knapp, kein
Werkzeugvergleich. Scripts: `extract_cached_fulltexts.py`, `extract_local_pdfs.py`, `audit_paper_fulltext.py`.
Bescheinigung/Zertifikat: nur als Wortfund in `aka-kurse-zae-2026.json`/`aka-kurse-zfa-2026.json`
(Deep-Research-Marktdaten ueber Fortbildungspflicht ZAE/ZFA) — keine Systementscheidung, wie AKA
selbst ein Zertifikat/eine Teilnahmebescheinigung ERZEUGT. Kein LaTeX/Tectonic/wkhtmltopdf/weasyprint
im Repo (find leer). Ergebnis: kein Beschluss zu Dokumenterzeugung, nur zu PDF-Quellenaufbereitung.

## Q2 Design-Guide — JA, begruendeter Beschluss, liegt als PROSA + DATEN
Zwei Konsile, beide in `design-lab/begod/knowledge/konsil/` + `design-lab/docs/konsil/`:

1. `konsil-design-system-2026-02-19.json` (Datum 2026-02-19, Status finalisiert, 12/12 einstimmig)
   Prosa-Fassung: `design-lab/docs/konsil/konsil-design-guide.md` (941 Zeilen).
   Beschluss: EIN Design-Token-System fuer Mobile/Desktop/Print/Web, adaptive Implementierungsschicht.
   Vollstaendig BEGRUENDET: 12 Experten (UX/A11y/Typografie/Psychologie/Gerontologie/iOS/Android/
   Flutter/Brand/Print/Farbe), 20 zitierte Primaerquellen (Bandura, WCAG 2.2, Miller 1956 etc.),
   Konflikttabelle mit aufgeloesten Zielkonflikten (z.B. Kontrast AAA vs. warmes Off-White).
   Farben/Spacing/Radii/Typo/Animation/Print-Mapping als JSON (`design_tokens`-Block) UND als Dart-
   Klasse `DesignTokens` im Dokument. Print-Mapping Screen↔mm/pt/Pantone explizit tabelliert.

2. `konsil-design-wissensarchiv-2026-03-05.json` (2026-03-05, 9 Teilnehmer, einstimmig) — Folge-Audit
   des Design-Wissensarchivs (39 Quellen, 20 Cluster). Findet 2 Fake-arXiv-IDs, fordert generisches
   Token-SCHEMA (`begod/knowledge/meta/design-token-schema.json`, Empfehlung U1 — Status "offen",
   NICHT umgesetzt laut Dokument) und Trennung global vs. AKA-spezifisch (U2, offen).
   Begruendet Dark-Mode-Verbot fuer AKA (Piepenbrock 2013, Halation 50+) vs. optional fuer Under-40-Apps.

**Als Daten bereits generiert und live im Repo (DO-NOT-EDIT, autogen 2026-03-05T15:51:45Z aus
`aka-design-guide.json` v3.1.0, Quelle "PyMuPDF-Audit 144 Seiten"):**
`design-lab/apps/aka-homepage/src/styles/aka-tokens.css`,
`design-lab/apps/aka-pretix/custom-scss/_design_tokens.scss`,
`design-lab/apps/aka-scanner/lib/theme/aka_design_tokens.dart`,
`design-lab/apps/akapp/lib/theme/aka_design_tokens.dart`.
Generator: `design-lab/begod/scripts/generate_design_tokens.py` (auch in ~15 Worktree-Kopien).
Quell-JSON `aka-design-guide.json` liegt an >10 Stellen (X-Postfach-Archive, begod/knowledge/apps/
akademia/, begod/knowledge/apps/akapp/) — kanonisch vermutlich `design-lab/begod/knowledge/apps/
akademia/aka-design-guide.json`, NICHT verifiziert welche die aktuell aktive Quelle ist (mehrere
gleich benannte Dateien, kein Zeitvergleich gemacht — das ist offen).

**Fazit Q2:** Es existiert bereits ein begruendetes, mehrfach geprueftes, medienuebergreifendes
Design-Token-System mit Pipeline JSON→CSS/SCSS/Dart. Ein zweiter, neuer Gestaltungsvorrat-Beschluss
waere Doppelarbeit — das generische Schema (Empfehlung U1) ist aber selbst noch offen/nicht gebaut.

## aka1 / "aka 22"
Reine Foto-Archive (JPG-Dateien im Root). Kein Konsil, kein ADR, keine Doku-Datei gefunden (find
nach *konsil*/*ADR* leer, top-level ls zeigt nur Bildnamen). Nicht durchwuehlt, nur Existenzpruefung.
