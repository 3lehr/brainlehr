# Startprompt: Atelier-Sitzung (ab 2026-08-18)

**Ort.** `cd /Volumes/daten/Begod2026/atelier` — eigener Arbeitsbaum, Zweig
`brainlehr/atelier`. Nicht im Hauptcheckout arbeiten (ADR-025: ein Repo,
getrennte Sitzungen). Absolute Pfade in den Hauptcheckout sind der Fehler
`L-7a719d`.

**Erst prüfen, dann anfangen.** Am 2026-08-18 lief dort ein Agent an
`INT-REG-001` (Domänenregistry, `DienstAufsicht.swift`). Vor dem ersten Edit:
`git -C /Volumes/daten/Begod2026/atelier status --short` und das Agentenregister
(`python3 -c "import sys; sys.path.insert(0,'hub/scripts'); from agent_register_ort import pfad; print(pfad())"`).

**Stand, gemessen.** `cd app && /usr/bin/xcrun swift test` → 241 passed.
74 getrackte Dateien unter `app/`, 376 KB Quelltext.

**Was gilt.** ADR-008 (Werkbank heißt Atelier) · ADR-013 (drei Teile je Domäne,
Oberfläche ist Beschreibung) · ADR-014 (was ins Atelier gehört) · ADR-023
(Mitstart ist eine Einstellung) · ADR-024 (V1 nativ, Beschreibung
plattformblind) · ADR-025 (Repo/Sitzungen).

**Offen, in dieser Reihenfolge.**
1. `INT-REG-001` fertigstellen bzw. abnehmen — Port 8799 und
   `einzelunternehmer` sind heute fest verdrahtet.
2. B5 zu Ende: sichtbarer Schalter in den Einstellungen, Aufsicht über *n*
   Dienste (hängt an 1).
3. Der native Zeichner für den Domänen-Bildschirm — die Beschreibung reist
   seit `INT-DNST-001`/`INT-API-002`, gezeichnet wird sie noch nicht.

**Die Falle, die heute zugeschlagen hat (`L-51e6d8`).** Wer einen Rückgabewert
oder ein Schema auf der Python-Seite ändert, muss die Swift-Konsumenten prüfen —
das Atelier hätte einen Aktualisierungs-Import als „enthielt nichts Neues"
gemeldet. Umgekehrt gilt dasselbe: Wer hier eine Antwort anders liest, prüft die
Python-Seite. Der Vertrag steht in `docs/REQUIREMENTS_INTERFACE_KOMPAT.md`.

**Zwei vorbestehende rote Swift-Tests** in `BestandteilAnforderungTests` sind
nicht von B5 und nicht von dir.
