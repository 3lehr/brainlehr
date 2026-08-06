-- Knowledge Database Schema (SQLite + FTS5)
-- Erstellt: 2026-03-25T16:20:00+01:00
-- Zweck: Baumstruktur-Wissens-DB für Cross-Projekt Agent-Zugriff
--
-- Zeitstempel-Vorgabewerte (created_at/updated_at/first_seen/last_seen/timestamp):
-- UTC mit 'Z', kein lokaler Versatz. SQLite kennt kein %z/zoneinfo, ein fest
-- eingetragener Versatz ("+01:00") ist bei DST falsch (Befund 2026-08-06:
-- Winterversatz im Sommer geschrieben). UTC+Z ist immer korrekt und
-- zwischen zwei Zeilen derselben Spalte string-vergleichbar/sortierbar.
-- Der Anwendungscode (now_iso() in knowledge_mcp_server.py u.a.) schreibt
-- ohnehin explizit einen echten Europe/Berlin-Versatz bei jedem INSERT --
-- dieser Vorgabewert greift nur, wenn eine Spalte mal nicht gesetzt wird.

-- Haupttabelle: Wissensknoten mit Materialized Path
CREATE TABLE IF NOT EXISTS knowledge_nodes (
    id TEXT PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,               -- Materialized Path: /shared/arch/mcp
    parent_path TEXT,                        -- Parent: /shared/arch
    project_id TEXT NOT NULL DEFAULT 'shared', -- shared|begod|aka|bebetter
    title TEXT NOT NULL,
    summary TEXT NOT NULL,                   -- 1-2 Sätze (Token-sparend!)
    content TEXT,                            -- Volltext (nur bei Bedarf laden)
    level INTEGER NOT NULL DEFAULT 0,        -- Tiefe im Baum (0=root)
    tags TEXT DEFAULT '[]',                  -- JSON Array
    source TEXT,                             -- Herkunft: Datei/Konsil/Research
    confidence REAL DEFAULT 0.8,
    access_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    -- Normschicht (N2, docs/PLAN_NORMSCHICHT_2026-08-05.md). Additiv, alle
    -- drei NULL-faehig und nach N2 ausnahmslos NULL -- Rang vergeben ist N3.
    -- norm_rang IS NULL ist die zentrale Unterscheidung des Plans (§2):
    -- es heisst "das hier ist ein FAKT, keine NORM". Nur Normen (Direktiven,
    -- ADRs, eskalierte Lehren) bekommen je einen Rang, Wissensknoten nie --
    -- ein Rang auf einem Fakt waere eine Ordnung, die nichts ordnet. Die
    -- beiden Gueltigkeitsfelder sind nur bei gesetztem norm_rang sinnvoll.
    norm_rang INTEGER,
    gilt_ab TEXT,
    gilt_bis TEXT,                            -- NULL = unbefristet in Kraft
    -- Quellhash (Auftrag 2026-08-06, Betreiber-Idee "Selbstentwertung statt
    -- Beleg"). Hash des ABSCHNITTS, aus dem der Knoten erzeugt wurde (siehe
    -- normbestand.py::parse_sections) -- NICHT der ganzen Quelldatei: eine
    -- Datei mit mehreren '## '-Abschnitten teilt sonst eine Bearbeitung auf
    -- alle Geschwisterknoten aus, gemessen an den 14 Direktiven-Knoten, die
    -- alle aus derselben CLAUDE.md-Bearbeitung als "veraltet" gegolten
    -- haetten, obwohl vermutlich nur ein Abschnitt betroffen war. NULL heisst
    -- "nicht pruefbar" (Altbestand vor diesem Feld, oder Quelle ohne
    -- Dateibezug) -- kein Befund, nur Abwesenheit einer Aussage.
    quell_hash TEXT,
    -- Anlass (Auftrag 2026-08-06): was hat den Eintrag ausgeloest. Vier
    -- Werte + Vorgabe, siehe ALLOWED_ANLASS in knowledge_mcp_server.py fuer
    -- die volle Erklaerung. Kurzfassung: 'selbst'/'betreiber' sind
    -- SELBSTBERICHTET vom Schreiber (nur so gut wie er), 'hook'/'skript'
    -- sind objektiv, weil der Aufrufweg sie kennt. 'unbekannt' ist Vorgabe
    -- und deckt den gesamten Altbestand vor diesem Feld ab.
    anlass TEXT NOT NULL DEFAULT 'unbekannt',
    -- abgeleitet_von (Auftrag 2026-08-06, ADR-027 Nachtrag 4, Lehre L-adfb33).
    -- Optionale Kennung (id oder path) eines VORHANDENEN Quellknotens. Gesetzt
    -- heisst: source wurde nicht vom Schreiber formuliert, sondern vom System
    -- aus der ART des Quellknotens erzeugt (parent_path/norm_rang/tags --
    -- NIE aus dessen title/summary/content, die tragen den Inhalt, der genau
    -- nicht durchsickern soll). Grund: Freitext-source kann nur nennen, indem
    -- er wiedergibt -- eine Person in source zu nennen heisst, sie zu leaken,
    -- egal wie gut die Zitat-Regel oben ist. "Dem Schreiber die Feder nehmen"
    -- ist der Kern des Auftrags. NULL = Normalfall, unveraendert wie bisher.
    -- Aufloesung (Kennung -> echter Knoten) ist eine Berechtigungsfrage und
    -- bewusst NICHT Teil von knowledge_read/knowledge_search -- siehe dort.
    abgeleitet_von TEXT,
    -- Zurueckziehen (Auftrag 2026-08-06, Luecke "kein Loeschweg fuer die KI").
    -- Reversibler Vorgang, den knowledge_zurueckziehen/knowledge_freigeben in
    -- knowledge_mcp_server.py bedienen -- siehe dort fuer die Abgrenzung zum
    -- endgueltigen, nur menschlichen Entfernen (endgueltig_entfernen.py, NICHT
    -- ueber ein MCP-Werkzeug erreichbar). zurueckgezogen=1 heisst: content und
    -- summary wurden GELEERT (kein Backup, der Inhalt ist damit weg -- nur
    -- knowledge_freigeben schaltet die Sichtbarkeit zurueck, stellt aber nichts
    -- wieder her), title und path bleiben stehen, die Zeile bleibt in der
    -- Tabelle (Auditkette, Z5: nichts aendert sich unbemerkt). knowledge_search
    -- und der Recall-Hook lassen zurueckgezogen=1 aus; knowledge_read/browse
    -- liefern die Zeile weiterhin (leer statt verschwunden).
    zurueckgezogen INTEGER NOT NULL DEFAULT 0,
    zurueckgezogen_grund TEXT,
    zurueckgezogen_am TEXT,
    zurueckgezogen_von TEXT,
    -- Schreiber am Datensatz (Auftrag 2026-08-06, Mangel: access_log.actor
    -- nur 9%, .session nur 0,5% gefuellt UND kein Feld fuer den Schreiber auf
    -- knowledge_nodes selbst -- das Protokoll allein reicht nicht, weil sich
    -- ein einzelner Schreiber ohne diese Spalten nicht isoliert aus dem
    -- Bestand herausfiltern laesst, siehe Einsatz im Auftrag: ein Modell mit
    -- fremdem/veraltetem Kontext, das ueber Zeit Unsinn ablegt). NULL fuer
    -- Altbestand vor dieser Spalte (kein Rueckfuellwert, das waere erfunden);
    -- ab jetzt schreibt knowledge_add/knowledge_update den aufgeloesten Wert
    -- aus _identity() (nie None -- 'unbekannt' ist ein zulaessiger, expliziter
    -- Wert, siehe UNBEKANNTER_SCHREIBER in knowledge_mcp_server.py). model
    -- bewusst NICHT hier dupliziert -- steht bereits in access_log, und
    -- welches Modell schrieb ist fuer die Isolation eines Schreibers weniger
    -- trennscharf als session (mehrere Modelle koennen in einer Sitzung
    -- laufen, eine Sitzung ist die adressierbare Einheit zum Zurueckrollen).
    actor TEXT,
    session TEXT
);

-- Volltext-Suche über Titel, Summary und Content.
-- tokenize='trigram': Substring- statt Wort-Tokenizer (SQLite >= 3.34,
-- gemessen vorhanden). Loest das groessere Loch als Umlaute: deutsche
-- Komposita ("Broschüre" soll "Existenzgründer-Broschüren" finden), die ein
-- Wort-Tokenizer prinzipiell verpasst. case_sensitive 0, weil ohnehin
-- gefaltet+kleingeschrieben gespeichert wird (siehe Trigger unten).
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    title, summary, content, path, tags, project_id,
    content='knowledge_nodes',
    content_rowid='rowid',
    tokenize="trigram case_sensitive 0"
);

-- Deutsche Umlaut-Faltung (ä→ae ö→oe ü→ue ß→ss, dann kleingeschrieben) VOR
-- dem Indizieren -- Trigram kennt keine Diakritika-Faltung, und FTS5s
-- eingebautes remove_diacritics deckt nur ü→u ab, nicht die alternative
-- Schreibung ue→u (siehe Auftrag: "Existenzgruender" fand "Existenzgründer"
-- sonst weiterhin nicht). Dieselbe Faltung laeuft anfrageseitig in
-- knowledge_mcp_server.py::fold_de() -- zwei Implementierungen (SQL kann
-- keine Python-Funktion aufrufen, ohne sie auf jeder schreibenden Verbindung
-- zu registrieren, und mehrere Skripte oeffnen die DB roh), Gleichheit belegt
-- tests/test_knowledge_hybrid_search.py::test_fold_de_matches_sql_fold.
-- Trigger: FTS bei INSERT/UPDATE/DELETE synchron halten
CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge_nodes BEGIN
    INSERT INTO knowledge_fts(rowid, title, summary, content, path, tags, project_id)
    VALUES (new.rowid,
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.title,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.summary,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.content,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.path,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.tags,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.project_id,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')));
END;

CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge_nodes BEGIN
    INSERT INTO knowledge_fts(knowledge_fts, rowid, title, summary, content, path, tags, project_id)
    VALUES ('delete', old.rowid,
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(old.title,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(old.summary,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(old.content,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(old.path,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(old.tags,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(old.project_id,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')));
END;

CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge_nodes BEGIN
    INSERT INTO knowledge_fts(knowledge_fts, rowid, title, summary, content, path, tags, project_id)
    VALUES ('delete', old.rowid,
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(old.title,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(old.summary,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(old.content,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(old.path,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(old.tags,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(old.project_id,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')));
    INSERT INTO knowledge_fts(rowid, title, summary, content, path, tags, project_id)
    VALUES (new.rowid,
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.title,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.summary,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.content,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.path,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.tags,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.project_id,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')));
END;

-- Zusicherungen an knowledge_nodes DIREKT in der Datenbank (Auftrag
-- 2026-08-06, Befund: ein roher INSERT am knowledge_mcp_server.py-Werkzeug
-- vorbei erzeugte 17 Knoten ohne source, mit freiem parent_path -- die
-- Python-seitigen Pruefungen (source-Leercheck in knowledge_add,
-- _validate_anlass) schuetzen nur den Weg ueber das Werkzeug, nicht die
-- Datei selbst, zumal PRAGMA foreign_keys hier aus (0) steht. SQLite kennt
-- kein nachtraegliches CHECK auf einer bestehenden Tabelle -- BEFORE-Trigger
-- mit RAISE(ABORT,...) statt Tabellenneubau: knowledge_nodes.path ist
-- Fremdschluessel-Ziel von knowledge_relations, ein Neubau (neue Tabelle +
-- Rename) haette diese Referenzen und laufende Fremdverbindungen gefaehrdet
-- -- der additive Trigger-Weg aendert keine bestehende Zeile und keinen
-- bestehenden Verweis. Je Regel ein BEFORE-INSERT- und ein BEFORE-UPDATE-
-- Trigger, weil beide Wege dieselbe Zusicherung umgehen koennen (siehe
-- Nachzug in knowledge_mcp_server.py::_ensure_node_constraint_triggers()
-- fuer Bestands-DBs, migrate_source_constraints.py fuer die Rueckfuellung
-- vorhandener leerer source-Werte).
CREATE TRIGGER IF NOT EXISTS knowledge_nodes_source_check_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN NEW.source IS NULL OR TRIM(NEW.source) = ''
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.source darf nicht leer sein: Herkunft angeben (Datei, Konsil oder Recherche, aus der dieser Knoten stammt)');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_source_check_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN NEW.source IS NULL OR TRIM(NEW.source) = ''
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.source darf nicht leer sein: Herkunft angeben (Datei, Konsil oder Recherche, aus der dieser Knoten stammt)');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_parent_check_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN NEW.parent_path IS NOT NULL AND NEW.parent_path <> '/'
    AND NOT EXISTS (SELECT 1 FROM knowledge_nodes WHERE path = NEW.parent_path)
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.parent_path zeigt auf keinen vorhandenen Knoten: zuerst den Elternknoten anlegen, dann parent_path erneut setzen');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_parent_check_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN NEW.parent_path IS NOT NULL AND NEW.parent_path <> '/'
    AND NOT EXISTS (SELECT 1 FROM knowledge_nodes WHERE path = NEW.parent_path)
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.parent_path zeigt auf keinen vorhandenen Knoten: zuerst den Elternknoten anlegen, dann parent_path erneut setzen');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_anlass_check_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN NEW.anlass NOT IN ('selbst','betreiber','hook','skript','unbekannt')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.anlass unzulaessig: erlaubt sind selbst, betreiber, hook, skript, unbekannt');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_anlass_check_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN NEW.anlass NOT IN ('selbst','betreiber','hook','skript','unbekannt')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.anlass unzulaessig: erlaubt sind selbst, betreiber, hook, skript, unbekannt');
END;

-- Lessons Learned Tabelle
CREATE TABLE IF NOT EXISTS lessons_learned (
    id TEXT PRIMARY KEY,
    node_path TEXT,                           -- Referenz auf knowledge_nodes.path
    type TEXT NOT NULL,                       -- error|insight|pattern|antipattern
    severity TEXT DEFAULT 'medium',           -- critical|high|medium|low
    description TEXT NOT NULL,
    root_cause TEXT,
    resolution TEXT,
    prevention TEXT,
    occurrences INTEGER DEFAULT 1,
    projects TEXT DEFAULT '[]',               -- JSON Array: ["begod","aka"]
    status TEXT DEFAULT 'active',             -- active|resolved|escalated_to_rule
    first_seen TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    last_seen TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    auto_rule_generated INTEGER DEFAULT 0,    -- 1 wenn bereits Regel generiert
    anlass TEXT NOT NULL DEFAULT 'unbekannt', -- siehe Kommentar an knowledge_nodes.anlass
    actor TEXT,                               -- siehe Kommentar an knowledge_nodes.actor/.session
    session TEXT
);

-- Session-Log (wer hat wann was abgefragt)
CREATE TABLE IF NOT EXISTS access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_path TEXT,
    action TEXT NOT NULL,                     -- browse|read|search|add|lesson
    query TEXT,
    project_id TEXT,
    actor TEXT,                               -- explizite Identitaet; sonst NULL
    model TEXT,
    session TEXT,
    status TEXT DEFAULT 'completed',          -- started|completed|failed
    timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    -- Auditkette (Nachtrag 2026-08-06, additiv per migrate_auditkette.py).
    -- Bestandszeilen (1223 vor der Migration) bleiben in beiden Spalten
    -- NULL -- ungedeckter Zeitraum, kein Fehler, nachtraeglich verkettet
    -- waere kein Beweis (siehe Lehre L-636a44 zu schema.sql vs. Live-DB und
    -- Auftrag 2026-08-06). Kettenanfang ist die erste Zeile nach der
    -- Migration.
    --
    -- zeilen_hash: SHA-256 ueber json.dumps(affected_row, sort_keys=True)
    -- des von dieser Aktion betroffenen Datensatzes NACH der Aenderung
    -- (z.B. die geschriebene knowledge_nodes-/lessons_learned-/
    -- knowledge_relations-Zeile als dict) -- siehe knowledge_mcp_server.py
    -- ::compute_zeilen_hash(). NULL bei reinen Lesezugriffen (browse/read/
    -- search) und bei Loeschungen (relation_remove, lesson_update mit
    -- delete=True) -- beides ein gueltiger Zustand, kein fehlender Wert.
    --
    -- ketten_hash: SHA-256 aus ketten_hash der Vorgaengerzeile (oder dem
    -- Genesis-Wert '0'*64, wenn die Vorgaengerzeile fehlt oder NULL
    -- traegt) verkettet mit den identitaetsstiftenden Feldern DIESER
    -- Zeile, in dieser Reihenfolge mit '|' verbunden: node_path, action,
    -- query, project_id, actor, model, session, status, timestamp,
    -- zeilen_hash -- siehe knowledge_mcp_server.py::compute_ketten_hash().
    -- Die eigene id (AUTOINCREMENT) fliesst bewusst NICHT ein: sie steht
    -- vor dem INSERT noch nicht fest.
    -- Weist eine nachtraegliche Aenderung EINER Zeile nach, mehr nicht --
    -- keine Verschluesselung, keine Signatur. Wer Schreibrechte auf die
    -- DB-Datei hat, kann die Kette neu rechnen.
    zeilen_hash TEXT,
    ketten_hash TEXT
);

-- Erklaerte Kettenbrueche (Nachtrag 2026-08-06, additiv per
-- migrate_kettenerklaerung.py, siehe kettenerklaerung.py).
--
-- WARUM: eine befugte Umschreibung von access_log-Feldern, die in den
-- ketten_hash einfliessen (z.B. die Zeitzonen-Rueckrechnung 2026-08-06,
-- Commit 684251b6ecb910f2c7ae55451726a1e6702d0d6a), bricht die Kette an
-- genau der umgeschriebenen Zeile -- das ist keine Fehlfunktion, das ist
-- die Kette, die tut, wofuer sie gebaut ist. Ein Verfahren, das den Bruch
-- WEGMACHT (den gespeicherten ketten_hash stumm nachrechnen), waere
-- wertlos: das koennte jeder Angreifer genauso. Diese Tabelle macht den
-- Bruch stattdessen ERKLAERBAR, ohne ihn zu verstecken -- der gespeicherte
-- ketten_hash in access_log bleibt UNVERAENDERT, kettenerklaerung.py::
-- create_explanation() schreibt nur daneben.
--
-- SELBSTSCHUTZ DES ERKLAERUNGSEINTRAGS -- ehrliche Grenze, siehe
-- Modul-Docstring kettenerklaerung.py: INNERHALB dieser Datenbank ist ein
-- Erklaerungseintrag NICHT vor nachtraeglicher Erfindung geschuetzt -- wer
-- Schreibrechte auf die DB-Datei hat, kann eine Zeile hier genauso frei
-- einfuegen wie einen ketten_hash in access_log neu rechnen (dieselbe
-- Grenze wie am Kopf von access_log dokumentiert). Schutz entsteht nur,
-- wenn anker_beleg tatsaechlich AUSSERHALB dieser DB verankert wurde
-- (ankerverfahren.py: RFC 3161 mit senden=True gegen eine externe TSA,
-- oder Gegenzeichnung mit einem Schluessel, der nicht in dieser DB liegt)
-- -- dann verraet ein spaeter geaenderter vorher_hash/nachher_hash/grund
-- sich selbst, weil er nicht mehr zum extern verankerten Hash passt.
-- anker_beleg ist NULL, wenn kein Anker gebaut wurde (trocken ist
-- Voreinstellung in ankerverfahren.py) -- ein Erklaerungseintrag ohne
-- Anker bleibt dann intern glaubwuerdig, extern nicht.
CREATE TABLE IF NOT EXISTS chain_explanations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    access_log_id INTEGER NOT NULL,          -- welche access_log.id erklaert wird
    grund TEXT NOT NULL,                     -- Begruendung, wer/wann/warum, im Klartext
    commit_hash TEXT,                        -- Commit der befugten Umschreibung, falls vorhanden
    vorher_hash TEXT NOT NULL,               -- ketten_hash, wie er tatsaechlich in access_log
                                              -- stand, als der Bruch erklaert wurde ("gespeichert")
    nachher_hash TEXT NOT NULL,              -- frisch aus den aktuellen Feldern berechneter
                                              -- ketten_hash ("erwartet") -- siehe compute_ketten_hash()
    erstellt_am TEXT NOT NULL,
    erstellt_von TEXT,                       -- actor, sonst NULL
    anker_beleg TEXT                         -- JSON-Beleg aus ankerverfahren.py, NULL wenn keiner gebaut
);

-- Explizite, belegte Wissensbeziehungen. Keine Tag-Aehnlichkeit und keine
-- automatisch vermuteten Kanten: beide Endpunkte muessen echte Node-Pfade sein.
CREATE TABLE IF NOT EXISTS knowledge_relations (
    id TEXT PRIMARY KEY,
    source_path TEXT NOT NULL,
    target_path TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.8 CHECK(confidence BETWEEN 0.0 AND 1.0),
    weight REAL NOT NULL DEFAULT 1.0 CHECK(weight >= 0.0),
    evidence TEXT,
    source TEXT,
    creator TEXT,
    model TEXT,
    session TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE(source_path, target_path, relation_type),
    FOREIGN KEY(source_path) REFERENCES knowledge_nodes(path) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY(target_path) REFERENCES knowledge_nodes(path) ON UPDATE CASCADE ON DELETE CASCADE
);

-- Embeddings (additiv, AP "Wissenssuche nach Bedeutung", 2026-07-31).
-- Eigene, separate Tabelle -- keine Aenderung an knowledge_nodes/lessons_learned.
-- Fehlt diese Tabelle (altere DB-Kopie), faellt jede Suche automatisch auf
-- reines FTS5/LIKE-Matching zurueck (siehe knowledge_mcp_server.py), kein Fehler.
-- Erzeugt/gefuellt wird sie ausschliesslich durch den explizit gerufenen Lauf
-- build_embeddings.py, nie als Nebeneffekt von knowledge_add/lesson_record.
--
-- project_id (Nachtrag 2026-08-05, Bereichstrennung): eigene Spalte statt
-- Nachschlagen bei der Suche -- eine Kandidatenmenge muss VOR der
-- Aehnlichkeitsrechnung nach Bereich einschraenkbar sein, sonst rechnet die
-- Suche unnoetig ueber Vektoren, die der Fragende nie sehen darf. Bei Knoten
-- einwertig (== knowledge_nodes.project_id). Bei Lessons ist projects
-- mehrwertig -- deshalb PRIMARY KEY um project_id erweitert: eine Lehre mit N
-- Bereichen bekommt N Zeilen mit demselben Vektor (siehe build_embeddings.py,
-- resolve_lesson_projects()), keine Kodierung mehrerer Bereiche in einer
-- Zeile. Das dupliziert Vektoren, berechnet aber keinen neu.
CREATE TABLE IF NOT EXISTS knowledge_embeddings (
    kind TEXT NOT NULL,               -- 'node' | 'lesson'
    ref_id TEXT NOT NULL,             -- knowledge_nodes.id | lessons_learned.id
    project_id TEXT NOT NULL DEFAULT 'shared',
    model TEXT NOT NULL,
    vector BLOB NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (kind, ref_id, project_id)
);

-- Indices für Performance
CREATE INDEX IF NOT EXISTS idx_nodes_path ON knowledge_nodes(path);
CREATE INDEX IF NOT EXISTS idx_nodes_parent ON knowledge_nodes(parent_path);
CREATE INDEX IF NOT EXISTS idx_nodes_project ON knowledge_nodes(project_id);
CREATE INDEX IF NOT EXISTS idx_nodes_level ON knowledge_nodes(level);
CREATE INDEX IF NOT EXISTS idx_lessons_type ON lessons_learned(type);
CREATE INDEX IF NOT EXISTS idx_lessons_status ON lessons_learned(status);
CREATE INDEX IF NOT EXISTS idx_lessons_project ON lessons_learned(projects);
CREATE INDEX IF NOT EXISTS idx_relations_source ON knowledge_relations(source_path);
CREATE INDEX IF NOT EXISTS idx_relations_target ON knowledge_relations(target_path);
CREATE INDEX IF NOT EXISTS idx_relations_type ON knowledge_relations(relation_type);
