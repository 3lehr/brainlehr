from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "docs" / "REQUIREMENTS_BRAINLEHR.md"

EXPECTED = {
    **{f"BDW-R{i:02d}": "keep" for i in range(1, 6)},
    "BDW-C01": "new-decision", "BDW-C02": "governed-core", "BDW-C03": "pilot",
    "BDW-P01": "regulated", "BDW-P02": "root-index", "BDW-P03": "profiles",
    "BDW-P04": "eval-suite", "BDW-P05": "A",
    # 2026-08-18: drei Zeilen aus Betreiberentscheidungen desselben Tages.
    # Der Test hat ihr Auftauchen gemeldet (53 gepinnt) -- genau dafuer ist er
    # da. Wer hier ergaenzt, hat den Katalog gelesen und die Entscheidung
    # belegt; ein stilles Wachsen des Katalogs bleibt ausgeschlossen.
    "BDW-P06": "trigger-or-nothing", "BDW-P07": "id-not-name",
    "BDW-P08": "supersede-not-expire",
    "BDW-E01": "external", "BDW-E02": "base", "BDW-E03": "intersection",
    "BDW-E04": "first-pilot", "BDW-E05": "pilot", "BDW-E06": "tested",
    "BDW-E07": "sensitive", "BDW-E08": "operator", "BDW-E09": "customer",
    "BDW-E10": "tamper", "BDW-E11": "stream-export", "BDW-E12": "class-policy",
    "BDW-E13": "verified", "BDW-E14": "policy", "BDW-E15": "managed",
    "BDW-E16": "regular", "BDW-E17": "later", "BDW-E18": "risk",
    "BDW-E19": "tenant-region", "BDW-E20": "default-deny", "BDW-E21": "profile",
    **{f"BDW-F{i:02d}": "must" for i in range(1, 11)},
    "BDW-F11": "should",
    "BDW-U01": "org-ceiling", "BDW-U02": "receipt", "BDW-U03": "separate",
    "BDW-U04": "allowlist", "BDW-U05": "policy", "BDW-U06": "risk",
    "BDW-U07": "approved", "BDW-U08": "org-wins",
    "BDW-P09": "standalone",
    "BDW-P10": "sprache",
    "BDW-P11": "assistent",
    "BDW-P12": "herkunftstreu",
    "BDW-P13": "vorlauf",
    "BDW-P14": "englisch",
    "BDW-P15": "ablage",
    "BDW-P16": "gegenstand",
    "BDW-P17": "faelligkeit",
    "BDW-P18": "namensfrage",
    "BDW-P19": "oberflaechensprache",
    "BDW-P20": "grundbestand",
    "BDW-P21": "auslieferungsform",
    "BDW-P22": "bauvermeidung",
    "BDW-P23": "projektkontext",
    "BDW-P24": "lazy-context-ladder",
    "BDW-P25": "project-tool-registry",
    "BDW-P26": "versioned-code-impact",
    "BDW-P27": "public-context-export",
    "BDW-P28": "public-context-no-private-data",
    "BDW-P29": "project-context-hardening",
    "BDW-P30": "separate-code-retrieval",
    "BDW-P31": "retrieval-modality-matrices",
    "BDW-P32": "request-local-boundary",
    "BDW-P33": "staged-impact-ack",
    "BDW-P34": "impact-visual-projection",
    "BDW-P35": "typed-impact-graph",
    "BDW-P36": "oss-analysis-research-gate",
    "BDW-P37": "agent-reuse-recommendation",
    "BDW-P38": "ephemeral-analysis-overlay",
    "BDW-P39": "client-neutral-lazy-bootstrap",
    **{f"BDW-P{i}": value for i, value in {
        40: "evidence-graph-v2", 41: "adapter-abi-registry", 42: "real-static-symbol-channels",
        43: "cpg-runtime-channels", 44: "reconciliation-impact-selection",
        45: "immutable-overlay-concurrency", 46: "client-mode-policy",
        47: "human-graph-projections", 48: "reuse-checkpoint-graph",
        49: "evidence-evaluation-privacy",
        50: "optional-codeql-sarif",
        51: "dependency-evidence-lifecycle",
        52: "supply-chain-release-identity", 53: "compatibility-deployment-identity", 54: "coverage-provenance-gaps", 55: "local-actor-project-boundary", 56: "ack-content-authenticity", 57: "analyzer-sandbox-redaction", 58: "trace-sanitization-lifecycle", 59: "injection-restart-resilience", 60: "graph-durability-erasure", 61: "safe-accessible-projections",
        62: "graph-vector-separation",
    }.items()},
    "BDW-P67": "release-readiness-priority",
    "BDW-P68": "audit-chain-utc-repair",
    "BDW-P69": "typed-relation-endpoints",
    "BDW-P70": "legacy-chain-cutover-anchor",
    "BDW-P74": "client-lifecycle-lazy-contract",
    "BDW-P99": "ai-comment-policy",
    "BDW-P100": "registry-anchor-lineage-resolver",
    "BDW-P101": "immutable-merkle-lineage-joins",
    "BDW-P102": "rationale-index-failure-lifecycle",
    "BDW-P103": "sealed-annotation-coderank-ablation",
    "BDW-P104": "forbid-freeform-ai-comments",
    "BDW-E22": "kreis",
    "BDW-E23": "je-kreis",
    "BDW-E24": "zweiter-faktor",
    "BDW-E25": "muster",
}

EXPECTED_LABELS = {
    **{f"BDW-R{i:02d}": "Beibehalten" for i in range(1, 6)},
    "BDW-C01": "Neuen Root-Zweckbeschluss aus Research ableiten",
    "BDW-C02": "Governierter Kern mit optionalem Enterprise-Profil",
    "BDW-C03": "Mit erstem realen Mehrbenutzer-Piloten",
    "BDW-P01": "Regulierte Großunternehmen",
    "BDW-P02": "Ein Root-Katalog mit referenzierten Abschnitten",
    "BDW-P03": "Ein Kern mit klaren Profilen",
    "BDW-P04": "Treffer-, Falschmelde-, Abstention- und Aktionsgates",
    "BDW-P05": "A · governierter Local-first-Memory-Kern",
    "BDW-P06": "trigger-or-nothing",
    "BDW-P07": "id-not-name",
    "BDW-P08": "supersede-not-expire",
    "BDW-E01": "Externer zentraler IdP", "BDW-E02": "RBAC als Basisschicht",
    "BDW-E03": "Rolle ∩ Objekt ∩ Zweck", "BDW-E04": "Ab erstem Mehrbenutzer-Pilot",
    "BDW-E05": "Ab erstem Enterprise-Pilot",
    "BDW-E06": "Technisch erzwungen und negativ getestet",
    "BDW-E07": "Alle sensiblen Daten und Ableitungen",
    "BDW-E08": "Betreiber entscheidet", "BDW-E09": "Kundenseitig kontrollierbar",
    "BDW-E10": "Manipulationsgeschützt und versioniert",
    "BDW-E11": "Standardexport plus Streaming",
    "BDW-E12": "Zentrale Policy je Datenklasse",
    "BDW-E13": "Automatisch, protokolliert und prüfbar",
    "BDW-E14": "Explizite Policy mit Freigabe und Audit",
    "BDW-E15": "Automatisch, getrennt, offline-fähig",
    "BDW-E16": "Regelmäßiger isolierter Restore-Test",
    "BDW-E17": "Später entscheiden",
    "BDW-E18": "Risikobasierte Matrix; Vier-Augen selektiv",
    "BDW-E19": "Zulässige Regionen je Mandant",
    "BDW-E20": "Klassifiziert, minimiert, default-deny",
    "BDW-E21": "SLI/SLO je Betriebsprofil",
    **{f"BDW-F{i:02d}": "MUSS erste Version" for i in range(1, 11)},
    "BDW-F11": "SOLL später",
    "BDW-U01": "Org setzt Maximalstufe, Nutzer darf absenken",
    "BDW-U02": "Kompakter Quellen-/Policy-Beleg je Antwort",
    "BDW-U03": "Getrennte Sichten mit expliziter Freigabe",
    "BDW-U04": "Org-Allowlist, Nutzer wählt daraus",
    "BDW-U05": "Policy plus risikobasierte Genehmigung",
    "BDW-U06": "Risikobasiert mit Nutzerkanälen",
    "BDW-U07": "Org-Allowlist, Nutzer wählt",
    "BDW-U08": "Org-Grenze gewinnt sichtbar",
    "BDW-P09": "Der Wechsel standalone -> multiuser MUSS spaeter moeglich sein",
    "BDW-P10": "KEIN Uebersetzungssystem",
    "BDW-P11": "Der Erststart fuehrt durch die Einrichtung -- im Chat",
    "BDW-P12": "Fremdimporte erfinden KEINE Herkunft",
    "BDW-P13": "Quellen werden zur Laufzeit GESUCHT, nicht hinterlegt",
    "BDW-P14": "Schnittstelle, Feldnamen, Docstrings und Dokumentation werden englisch",
    "BDW-P15": "brainlehr ist auch Dokumentenablage. Drei Schichten,",
    "BDW-P16": "Wer oder was gemeint ist, ist",
    "BDW-P17": "Was wann von wem zu tun",
    "BDW-P18": "Eine Frage nach einer PERSON wird",
    "BDW-P19": "Nutzersichtbare Texte folgen der Sprache des",
    "BDW-P20": "Das Paket liefert KEINEN Wissensbestand mit",
    "BDW-P21": "Der Kern bleibt **AGPL-3.0-or-later**, der Hermes-Adapter",
    "BDW-P22": "Bevor gebaut wird, sieht brainlehr im",
    "BDW-P23": "genau einen klientneutralen Projektkontext",
    "BDW-P24": "Der Klient MUSS Projektkontext stufenweise laden",
    "BDW-P25": "verweist sein Projektkontext auf Faehigkeiten",
    "BDW-P26": "Nach jedem verifizierten Code-Commit hinterlegt der Codeschreiber",
    "BDW-P27": "Verifizierte oeffentliche Selbstbeschreibung, Architektur und Workflow",
    "BDW-P28": "Der oeffentliche Kontext-Export darf weder rohe Datenbankfelder",
    "BDW-P29": "Projektkontext benennt die Grenzen seiner deterministischen",
    "BDW-P30": "Projektcode DARF neben dem allgemeinen BGE-M3-Wissenskanal",
    "BDW-P31": "Der eingefrorene Retrievalvergleich umfasst Python",
    "BDW-P32": "Jeder Klient kann einen request-lokalen Modus",
    "BDW-P33": "Ein Projekt aktiviert das Commit-Gate nur durch die explizite",
    "BDW-P34": "Eine optionale menschliche Visualisierung darf nur einen nach Revision",
    "BDW-P35": "Nach einem verifizierten Commit erzeugt `project_change`",
    "BDW-P36": "Vor einer neuen Analyseabhängigkeit wird anhand offizieller",
    "BDW-P37": "Brainlehr ergänzt seinen temporären technischen Checkpoint",
    "BDW-P38": "Code-/Mixed-Arbeit verwendet einen unveränderlichen Basisgraphen",
    "BDW-P39": "Ein kleines, immer geladenes T0-Bootstrap",
    "BDW-P40": "Brainlehr ist eine revisionsgebundene Code-Evidenzplattform",
    "BDW-P41": "Alle Analyzer registrieren eine kleine ABI",
    "BDW-P42": "tree-sitter, SCIP und Semgrep liefern getrennte",
    "BDW-P43": "Joern/CPG und OTLP liefern getrennte",
    "BDW-P44": "Normalisierte Evidenz wird pro Revision vereinigt",
    "BDW-P45": "P38 wird auf Graph-v2 fortgeführt",
    "BDW-P46": "P32/P39 bleiben clientneutral",
    "BDW-P47": "Mermaid, Metroviz-Vertrag und eine lokale/offline Cytoscape-Ansicht",
    "BDW-P48": "Ein Registry-Eintrag trägt stabile Agent-/Task-ID",
    "BDW-P49": "Jede Tranche misst Laufzeit/Timeout",
    "BDW-P50": "CodeQL ist ein optionaler, nie still aktivierter SARIF-Kanal",
    "BDW-P51": "Dependencies werden als revisionsgebundene Paket-/Version-/Lizenz-/Advisory-Knoten",
    "BDW-P52": "Locks, SBOM, Hash/Signatur", "BDW-P53": "Schema/API/Event/Deploy-Identität", "BDW-P54": "Dynamic/plugin/reflection/vendor", "BDW-P55": "Lokale Actor-/Project-Grenze", "BDW-P56": "Ack bindet Basis", "BDW-P57": "Analyzer haben Allowlist", "BDW-P58": "OTel nutzt Sampling", "BDW-P59": "Injection kann Policy", "BDW-P60": "Graph-Schema-Migration", "BDW-P61": "Cytoscape/Mermaid/Metroviz haben CSP",
    "BDW-P62": "Maschinen-Graph/Analyzer-/Trace-Evidenz wird getrennt",
    "BDW-P67": "Vor P2-Visualisierung ist der gesamte Brainlehr-Kern P1",
    "BDW-P68": "Die 11.119 gegen eine benannte Vor-UTC-Sicherung",
    "BDW-P69": "`knowledge_relations` speichert typisierte Endpunkte",
    "BDW-P70": "Die 50 offen gebliebenen historischen Kettenlücken",
    "BDW-P74": "Der gleiche maschinenlesbare Lazy-Load- und `edit_batch_complete`-Vertrag",
    "BDW-P99": "AI-Kommentare sind standardmäßig `NONE`",
    "BDW-P100": "Registry- und Anchor-Validierung bindet stabile IDs",
    "BDW-P101": "Daten- und Wirkungs-Lineage werden in unveränderlichen",
    "BDW-P102": "Rationale, Retrieval-Index, Failure-Taxonomie",
    "BDW-P103": "Die Code-Retrieval-Entscheidung verlangt eine versiegelte",
    "BDW-P104": "AI darf keine Freiform-Kommentare",
    "BDW-E22": "Der Kreis steht VON ANFANG AN fest",
    "BDW-E23": "Geltung ist zweiseitig, sobald Kreise existieren",
    "BDW-E24": "der zweite liegt nicht auf demselben Geraet",
    "BDW-E25": "Nicht die MENGE ist das Signal",
}


def test_root_catalog_decodes_all_operator_selections():
    text = CATALOG.read_text()
    rows = re.findall(r"^\| (BDW-[RCPU EF]\d{2,3}) \| `([^`]+)` \| ([^|]+) \| ([^|]+) \|", text, re.M)
    decoded = {requirement_id: selection for requirement_id, selection, _, _ in rows}
    # DIE ZAHL KOMMT AUS EXPECTED, nicht aus dem Quelltext (2026-08-21).
    # Bis dahin stand hier eine feste 56 -- dieselbe Bauform wie das
    # `assert "NOT RUN"` weiter unten, das am 2026-08-18 entfernt wurde:
    # ein Test, der jeden Zuwachs des Katalogs verbietet. Die Zusicherung
    # bleibt dieselbe (jede Zeile dekodiert, keine doppelte Kennung, jede
    # traegt ihr AC1) -- sie haengt nur nicht mehr an einer Zahl, die beim
    # naechsten Eintrag von Hand nachgezogen werden muss.
    assert len(rows) == len(decoded) == len(EXPECTED)
    assert decoded == EXPECTED
    catalog_rows = {line.split("|")[1].strip(): line for line in text.splitlines() if line.startswith("| BDW-")}
    assert set(catalog_rows) == set(EXPECTED_LABELS)
    for requirement_id, label in EXPECTED_LABELS.items():
        assert label in catalog_rows[requirement_id]
        assert f"`{requirement_id}-AC1`" in catalog_rows[requirement_id]
        # BIS 2026-08-18 stand hier `assert "NOT RUN" in ...` -- ein Test, der
        # FORTSCHRITT VERBOTEN haette: die erste belegte Zeile machte ihn rot.
        # Er stammt aus dem Tag, an dem alle 53 Gates NOT RUN waren, und hat
        # diesen Zustand versehentlich zementiert.
        # Geprueft wird jetzt, was gemeint war: jede Zeile TRAEGT ein
        # Produktgate -- entweder ehrlich offen (NOT RUN) oder belegt, und dann
        # mit nachfahrbarem Pruefbefehl. Ein Gate, das eine nicht existierende
        # Datei nennt, faengt melder/gatestand.py (Phantom-Gate).
        # strip("|") zuerst -- sonst ist das letzte Feld leer und [-2] liefert
        # die Quelle statt des Gates. Gleiche Lesart wie melder/gatestand.py.
        gate = catalog_rows[requirement_id].strip().strip("|").split("|")[-2].strip()
        assert gate, f"{requirement_id}: Produktgate-Spalte leer"
        # DEFERRED ist seit 2026-08-18 eine DRITTE Lage neben offen und belegt:
        # die Betreiberentscheidung 9d77ad16 hat 22 Zeilen an den ersten
        # Mehrbenutzer-Piloten gebunden. Ein vertagtes Gate ist weder offen
        # (niemand arbeitet daran) noch belegt (nichts ist gemessen) -- es
        # als eines von beiden zu fuehren, waere in beide Richtungen falsch.
        assert gate.startswith(("NOT IMPLEMENTED", "NOT RUN", "DEFERRED", "FUTURE")) or any(
            marke in gate for marke in ("PASS", "TEILWEISE", "FAIL")
        ), f"{requirement_id}: Gate weder offen noch vertagt noch belegt: {gate!r}"
        if gate.startswith("DEFERRED"):
            assert "BDW-C03" in gate or "Pilot" in gate, (
                f"{requirement_id}: vertagt ohne Bedingung -- wann wird es wieder faellig?")
        # FUTURE ist seit 2026-08-21 die VIERTE Lage: nicht an den Piloten
        # gebunden (das waere DEFERRED), sondern schlicht noch nicht
        # gebraucht -- Betreiberwort zu BDW-E24: "als future markieren,
        # brauchen wir noch nicht". Die Auflage bleibt trotzdem dieselbe,
        # und sie ist der ganze Grund fuer die Lage: ein vertagter Punkt
        # ohne Wiedervorlage ist nicht vertagt, sondern still abgeschafft.
        if gate.startswith("FUTURE"):
            # Klein- und Umschrift-blind: der Katalog schreibt "**Wieder
            # faellig**", ein Suchmuster in Kleinschreibung haette das nie
            # getroffen -- genau L-8fce9c, ein Waechter, der seine WOERTER
            # prueft statt die Sache.
            flach = gate.lower().replace("ä", "ae").replace("\u00e4", "ae")
            assert "wieder faellig" in flach or "wieder fallig" in flach, (
                f"{requirement_id}: FUTURE ohne Wiedervorlage -- was macht es wieder faellig?")
        if not gate.startswith(("NOT IMPLEMENTED", "NOT RUN", "DEFERRED", "FUTURE")):
            assert "`" in gate, (
                f"{requirement_id}: belegtes Gate ohne nachfahrbaren Pruefbefehl -- "
                "eine Behauptung ohne Beleg ist schlimmer als ein ehrliches NOT RUN")
    assert all(norm.strip() in {"MUSS", "SOLL", "MUSS-NICHT", "Profil", "Pilot", "Deferred"} for _, _, norm, _ in rows)
    assert all(status.strip() in {"DECIDED", "OPEN", "CONFLICT", "DEFERRED", "PILOT"} for _, _, _, status in rows)


def test_root_is_the_only_normative_catalog():
    text = CATALOG.read_text()
    assert "Offene IDs: **keine**" in text
    assert "Offene Konflikte: **keine**" in text
    assert "BDW-E17" in text and "Später entscheiden" in text
    assert "Produkt-Teststatus" in text and "NOT RUN" in text
    marker = "Untergeordnet zu `docs/REQUIREMENTS_BRAINLEHR.md`; lokale IDs sind nur Umsetzungsgates."
    for name in ("REQUIREMENTS_PROMPT_INVARIANZ.md", "REQUIREMENTS_SESSION_CHECKPOINT.md", "REQUIREMENTS_INTERFACE_KOMPAT.md"):
        assert marker in (ROOT / "docs" / name).read_text()
