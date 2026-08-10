"""Demo-Datenbank fuer den Schreibpruefstand (Plan C1,
docs/PLAN_SCHREIBPRUEFSTAND_2026-08-05.md).

Baut shared-knowledge/schreibpruefstand/demo/schreibpruefstand.db aus
schema.sql -- NIE die echte shared-knowledge/knowledge.db, das ist ueber
_assert_not_real_db() erzwungen, nicht nur behauptet. Grundbestand (Haertung
Runde 2, Plan §1): ein 3 Ebenen tiefer, thema-spezifischer Baum statt der
ersten, zu flachen Fassung ("/begod" existierte als bequemer Sammelplatz,
lauf1.json traf ihn 21/21 mal). Kein Knoten heisst mehr wie ein generischer
Rateversuch. Wird vor jedem Lauf frisch gebaut (bestehende Datei +
-wal/-shm werden geloescht).

Rohmaterial (RAW_MATERIAL): woertliche Ausschnitte aus echten
Projektdokumenten dieses Repos (docs/*.md, docs/adr/*.md) -- OHNE Titel-
oder Pfad-Hinweis. Das schreibende Modell in schreiblauf.py bekommt nur den
Text und "halte das fest", nie eine Quellenangabe. Darunter zwei Stuecke
(Audio/DSP-Domaene, Verfassungsschicht-Beispiel OpenHood/OBD2), die zu
keinem Ast im Grundbestand passen -- dort ist neuer_ast=True die richtige
Antwort, nicht ein Rateversuch auf einen der vorhandenen Pfade.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import hashlib
import json
import sqlite3
from pathlib import Path

SCHREIBPRUEFSTAND_DIR = Path(__file__).resolve().parent
SHARED_KNOWLEDGE = SCHREIBPRUEFSTAND_DIR.parent
REAL_DB_PATH = SHARED_KNOWLEDGE / "knowledge.db"
DEMO_DIR = SCHREIBPRUEFSTAND_DIR / "demo"
DEMO_DB_PATH = DEMO_DIR / "schreibpruefstand.db"

DEFAULT_SEED = 20260805  # dokumentiert den Startwert; der Grundbestand ist
                          # eine feste Liste, seed steuert hier nichts, das
                          # macht den Lauf reproduzierbar ohne Zufallscode.

_SCHEMA_SQL = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")

# --- Grundbestand: Namensraum-Knoten (parent_path, title, project_id) -----
# 3 Ebenen tief, jeder Titel ein spezifisches Mehr-Wort-Kompositum -- kein
# Knoten heisst "Begod"/"Shared"/"Fahrtenbuch" allein, das war der
# Sammelplatz, den lauf1.json 21/21 mal traf.
BASE_NAMESPACES = [
    ("/", "Wissensnetz-Pflegeverbund", "shared"),
    ("/wissensnetz-pflegeverbund", "Fahrtenbuch-App", "shared"),
    ("/wissensnetz-pflegeverbund/fahrtenbuch-app", "Feldmessung-Geraetebindung", "shared"),
    ("/wissensnetz-pflegeverbund", "Pflege-Lotse-App", "begod"),
    ("/wissensnetz-pflegeverbund/pflege-lotse-app", "Betaphase-Externe-Inhalte", "begod"),
    ("/wissensnetz-pflegeverbund/pflege-lotse-app", "Rechtlicher-Rahmen-Legal-Trias", "begod"),
    ("/", "Entwicklungsplattform-Toolbox", "begod"),
    ("/entwicklungsplattform-toolbox", "BSI-Stand-der-Technik-Bibliothek", "shared"),
    ("/entwicklungsplattform-toolbox", "Code-Qualitaet-God-Files", "begod"),
    ("/", "Aka2026-Sprintplanung", "aka"),
    ("/aka2026-sprintplanung", "Phase0-Quick-Wins", "aka"),
]

# --- Rohmaterial: 20 woertliche Ausschnitte aus docs/*.md, ohne Titel/Pfad -
RAW_MATERIAL = [
    '~~ALT: 4,99 Einmalkauf | NEU: Kostenlos+Werbefrei~~ KORREKTUR (Session 22): '
    '"Kostenlos" war PR-Narrativ aus PK-Simulation (K3), KEINE Entscheidung. K1 '
    '(Analyse) empfahl 4,99€ Einmalkauf. Evidenz-Pyramide P14: Analyse (Rang 5) > '
    'Simulation (Rang 5, aber TYPE=simulation). Pricing-Entscheidung steht noch aus '
    '— weder K1 noch K3 haben autoritativen Rang.',

    '"Null check" Crash: Overlay-Bug (FAB tooltip ohne Overlay-Ancestor in '
    'DemoOverlay). Fix: tooltip=\'\' | DemoOverlay prueft previousCrashDetected | '
    'Crash-Handler loggt voller Stack. Commits: acbef54, 51eb046, 85c0384.',

    'Zwei Wizard-Pfade: NbaWizardScreen (64Q PageView) + DecisionTreeWizardScreen '
    '(Ja/Nein). Demo-Modus: Settings -> aktivieren -> "Protokoll teilen" -> '
    'SharePlus. System: Android 6.0+, ~65MB, kein Internet.',

    'Drift: Migration im Konstruktor, forTesting() Factory. Riverpod: Plain 2.x '
    '(kein Codegen wegen Konflikte mit drift_dev/json_serializable). Flutter '
    "Driver Bug: type 'int' not subtype 'String?' bei Finder-Befehlen. Nur "
    'screenshot+get_health OK.',

    'TalkBack/VoiceOver: lokal, unkritisch. TTS: meist lokal, manche Stimmen '
    'online. STT: potenziell cloudbasiert (Google). Transparenz in '
    'Onboarding/Settings noetig. Aktuell: GBoard-Mikrofon (potenziell cloud). '
    'Kein eigener SpeechRecognizer.',

    'pdf v3.x hat kein Passwort-Support. Einziges Paket (ares_defence_labs) zu '
    'riskant (84 Downloads). Entscheidung: Kein PDF-Passwort. Stattdessen: '
    'Drucken priorisieren, E-Mail-Warnung, Personendaten optional.',

    'God-Files: 7 Dateien >500 Zeilen, davon 3 >800 (settings 1156, onboarding '
    '1186, dashboard 989). Duplikation: jscpd 26 Klone, 1.38% Rate. Hotspot: '
    'decision_tree_wizard_screen vs nba_wizard_screen (7 Klon-Paare!). Regel: Max '
    '1 public Widget pro Datei.',

    'Context: BeGood needs a local, attractive, automatically updated 3D view '
    'without changing the existing knowledge sources. Chosen: a read-only Python '
    'standard-library HTTP API and Vanilla HTML/CSS/JS UI under '
    '`tools/knowledge-viz`, with pinned `3d-force-graph` loaded by the browser.',

    'Context: semantic strength, provenance, and live readers/writers must be '
    'factual and remain current after knowledge changes; 237 permanent text '
    'sprites would waste GPU memory. Chosen: extend the existing knowledge MCP '
    'with validated `knowledge_relations` CRUD and access identity/status.',

    'Fuer die Beta-Phase und darueber hinaus besteht die Moeglichkeit, externe '
    'Inhalte in die App zu integrieren: AWO Plus Magazin (Monatliches '
    'Kundenmagazin als In-App-Content), Bundestag-Abstimmungsverhalten '
    '(Pflegerelevante Abstimmungen ohne Wahlempfehlung), Veranstaltungen/Kurse.',

    'Die Kernfrage: Koennen wir externe Inhalte empfangen, ohne dass diese '
    'Zugriff auf medizinische/persoenliche Daten haben? Zone A: Medical '
    '(Offline-Only, DSGVO Household Exemption). Internet: NIEMALS. DB: '
    'Bestehende app_database.dart (medical tables).',

    'Die Pflege-Lotse Plattform wird ueber PflegeTageBuch hinaus weitere '
    'Schwester-Apps bekommen. Die Toolbox (BegodApp) ist das entwicklerseitige '
    'Steuerungswerkzeug und braucht visuelle Eigenstaendigkeit. Gleichzeitig muss '
    'die Familien-DNA erkennbar bleiben.',

    'Teal #2E7D6F erscheint in JEDER App als Wiedererkennungs-Element -- im '
    'Logo-Bereich, Footer, oder als Accent-Zweitfarbe, nie als Primary einer '
    'Nicht-Pflege-App. Warmes Off-White #FAFAF5 als Surface (nicht kalt-weiss). '
    'Kein aggressives Rot -- immer warmes Orange fuer Fehler.',

    'Phase 0 Quick Wins (Sofort, 0-1 Tag): stiftshuette-errors.json geleert '
    '(DONE); git-wall-setup-v1-UNSAFE.sh entfernen/archivieren (OFFEN); '
    'Worktree-Pfade in copilot-instructions.md verifizieren (OFFEN); '
    'Rate-Tracking bei naechster Session befuellen (OFFEN).',

    'Sprint 1.1 Pre-Release Blocker (1-2 Tage): Pre-existing Test-Fail fixen (1 '
    'von 1618); dart pub outdated Dependency-Audit; In-App '
    'Datenschutzerklaerung-Screen erstellen; Privacy Policy URL auf '
    'begod-homepage hosten; Apple Privacy Manifests pruefen.',

    'REDIRECT: Komprimierter Status in toolbox/knowledge/context-snapshot.json. '
    'Diese Datei existiert als Marker fuer ProjectPaths (Root-Erkennung). '
    'Projekt: Pflege-Lotse | Case: B | Branch: feature/1-frage-pro-screen | '
    'Phase: 3 (Polish+Release) | Tests: 228/228 | Features: 6 complete.',

    'Die BSI Stand-der-Technik-Bibliothek (Grundschutz++ Katalog, 647 Controls '
    'in 20 Gruppen, plus Kernel-Katalog -- gesamt 1855 Controls im OSCAL-Format) '
    'wurde als Evidenz-Rang 2 in die obersten Direktiven aller drei Repositories '
    'verankert.',

    'Status: MVP Complete, Phase 3 (Polish+Release). App-DNA: Offline-First, '
    'Privacy-First, Kein Account, Kostenlos+Werbefrei, 70-Jahre-Test. Stack: '
    'Flutter 3.38.9, Dart 3.10.8, Riverpod(plain), Drift(SQLite), GoRouter, '
    'Material 3, Freezed, pdf+printing, ARB(DE/EN).',

    'Legal: Konjunktiv-Zwang | Disclaimer-Trias(3 Stellen) | NBA!=Rechtsberatung '
    '(RDG) | !=Medizinprodukt(MDR) | DSGVO Household. Hard Stops: Nie '
    '"Anspruch", nie "Widerspruch einlegen", nie Schreiben, nie med. '
    'Einschaetzung.',

    'Fork-Entscheid: Patch wuchs 89 -> 1397 -> 1613 Zeilen (Schwelle 300). User '
    '2026-07-24: Fork = Klon versionieren (nach diesem Handoff umgesetzt -- '
    'siehe Changelog unten). Damit entfallen Patch-Datei + '
    'Clone/Apply-Reproduktionsritual.',

    'Nachsehen schlaegt erinnern. Bevor du sagst „das gibt es nicht", „das ist '
    'fest verdrahtet" oder „dafuer braeuchten wir ein neues Paket": sieh in der '
    'naheliegendsten Datei nach. Wer nicht nachgesehen hat, sagt „ich habe '
    'nicht nachgesehen" -- nicht „es gibt das nicht".',

    # -- ab hier: passt zu KEINEM Ast im Grundbestand (docs/AFRIKA_HANDOFF_KOMPLETT.md) --
    'Domain: Audio / DSP / Music Information Retrieval. EA1 Keine Latenz-Spikes '
    'im Echtzeit-Pfad -- Audio-Dropouts sind sofort hoerbar und zerstoeren das '
    'User-Erlebnis, Max 10ms im Audio-Callback. EA4 Audio-Daten = '
    'personenbezogen -- Stimmen in Audio-Aufnahmen sind PII (Art. 4 Nr. 1 '
    'DSGVO), Offline-First, keine Audio-Uploads. Keine Allokation im '
    'Audio-Thread -- stackalloc oder ArrayPool. Keine BPM ohne Konfidenz -- '
    '"120 BPM (0.85)" statt "120 BPM".',

    # -- passt ebenfalls zu KEINEM Ast (docs/BEGOD_SYSTEM_DEEP_RESEARCH.md) --
    'Plus App-spezifische Ewigkeitsklauseln (EA1-EA5) pro Kontinent-Verfassung. '
    'Beispiel OpenHood: EA1 verbietet OBD2 Mode 04/08 (Fehlercodes loeschen, '
    'Komponenten-Tests starten). Durchsetzung: Das Verfassungsgericht '
    '(BVerfG-Agent) kann Urteile faellen. Antragsberechtigt sind Hippokrates, '
    'Legal und Polizei (Stufe 1), Guide (Stufe 2) und User (Stufe 3). Urteile '
    'werden als JSON archiviert.',
]


def _assert_not_real_db(path: Path) -> None:
    """Zusicherung als Pruefung, nicht als Kommentar -- bricht den Lauf ab,
    bevor irgendein Schreibversuch die echte Datenbank erreichen koennte."""
    if path.resolve() == REAL_DB_PATH.resolve():
        raise RuntimeError(
            f"Zusicherung verletzt: Ziel {path} ist die echte Datenbank "
            f"({REAL_DB_PATH}). Abbruch vor jedem Schreibzugriff."
        )


def build_demo_db(db_path: Path = DEMO_DB_PATH) -> Path:
    """Baut die Demo-DB frisch aus schema.sql + Grundbestand. Loescht eine
    vorhandene Datei samt WAL/SHM zuerst -- 'vor jedem Lauf frisch'."""
    _assert_not_real_db(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-shm", "-wal"):
        p = Path(str(db_path) + suffix)
        if p.exists():
            p.unlink()

    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA_SQL)
    now = "2026-08-05T00:00:00+01:00"
    for i, (parent_path, title, project_id) in enumerate(BASE_NAMESPACES):
        slug = title.lower().replace(" ", "-")
        path = f"{parent_path.rstrip('/')}/{slug}" if parent_path != "/" else f"/{slug}"
        level = path.count("/") - 1
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, "
            "summary, content, level, tags, source, created_at, updated_at, "
            "norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'keine_norm','skript:demo_db.py','Namensraum-Knoten, kein Normtext')",
            (f"NS-{i:02d}", path, parent_path, project_id, title,
             f"Namensraum-Knoten fuer {title}.", "", level, "[]",
             "schreibpruefstand-grundbestand", now, now),
        )
    conn.commit()
    conn.close()
    return db_path


def checksum(db_path: Path = DEMO_DB_PATH) -> str:
    """Pruefsumme ueber den Knoten-Bestand (nicht die Rohdatei -- SQLite-
    Dateilayout ist nicht byteweise deterministisch ueber mehrere Baeufe)."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT path, parent_path, project_id, title, summary, tags "
        "FROM knowledge_nodes ORDER BY path"
    ).fetchall()
    conn.close()
    payload = json.dumps([dict(r) for r in rows], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def selftest() -> None:
    real_hash_before = hashlib.sha256(REAL_DB_PATH.read_bytes()).hexdigest() if REAL_DB_PATH.exists() else None

    build_demo_db()
    c1 = checksum()
    build_demo_db()
    c2 = checksum()
    assert c1 == c2, f"gleicher Startwert muss gleiche Pruefsumme ergeben: {c1} != {c2}"

    try:
        _assert_not_real_db(REAL_DB_PATH)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Zusicherung gegen die echte Datenbank griff NICHT")

    assert 15 <= len(RAW_MATERIAL) <= 25, f"Rohmaterial ausserhalb 15-25: {len(RAW_MATERIAL)}"

    real_hash_after = hashlib.sha256(REAL_DB_PATH.read_bytes()).hexdigest() if REAL_DB_PATH.exists() else None
    assert real_hash_before == real_hash_after, "echte knowledge.db wurde waehrend des Selbsttests veraendert"

    print(f"demo_db.py selftest ok (checksum={c1[:12]}..., raw_material={len(RAW_MATERIAL)} Stuecke, "
          f"echte DB unveraendert: {real_hash_before == real_hash_after})")


if __name__ == "__main__":
    selftest()
