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
    project_id TEXT NOT NULL DEFAULT 'shared', -- free-form project slug, not enforced/closed
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
    -- Art (Auftrag 2026-08-07/08, Knoten dd367fd1): zweite, von norm_rang
    -- UNABHAENGIGE Achse. norm_rang sagt wie bindend ein Satz ist, norm_art
    -- sagt, WAS FUER EINEN Satz er ueberhaupt macht -- Sein (Studie/Messung),
    -- Sollen (Leitlinie/Direktive) oder Duerfen (Gebuehrenordnung/Lizenz).
    -- Zwei Normen verschiedener Art konkurrieren nicht, egal welchen Rang sie
    -- tragen (knowledge_lint.py::_is_spannung). NULL = Art nicht erfasst --
    -- fuer den gesamten Altbestand der Fall, wird nie geraten, nur explizit
    -- gesetzt. Werte bewusst nicht per CHECK erzwungen (gleiche Haltung wie
    -- norm_rang: die Skala/Menge ist noch nicht abschliessend belegt).
    norm_art TEXT,
    -- Entscheidung (Auftrag 2026-08-08, Konsil docs/KONSIL_WISSENSRAUM_ANSICHT_2026-08-08.md):
    -- norm_rang/gilt_bis NULL sind seit N2 doppeldeutig -- "Fakt, bewusst
    -- keine Norm" UND "nie jemand hat hingesehen" sehen in der Spalte
    -- IDENTISCH aus. Bei einer Million Zeilen ist das nicht mehr nachholbar,
    -- nur noch geraten. norm_entscheidung traegt die Entscheidung SELBST,
    -- getrennt von ihrem Ergebnis:
    --   'offen'            -- nie entschieden. Einziger Vorgabewert, deckt
    --                          AUSSCHLIESSLICH den Altbestand vor diesem
    --                          Feld ab (ALTER TABLE befuellt ihn beim
    --                          Anlegen der Spalte, das laeuft NICHT durch
    --                          die Trigger unten). Wird nie neu vergeben --
    --                          siehe knowledge_nodes_norm_entscheidung_pflicht_bi.
    --   'keine_norm'        -- ausdruecklich entschieden: Fakt, kein Rang.
    --   'norm_befristet'    -- Norm mit Enddatum (gilt_bis gesetzt).
    --   'norm_unbefristet'  -- Norm ausdruecklich ohne Ende (gilt_bis NULL
    --                          heisst ab jetzt "entschieden unbefristet",
    --                          nicht mehr "keiner hat gilt_bis ausgefuellt").
    -- Same Bauform wie anlass oben (NOT NULL DEFAULT, Werte-Trigger bi+bu),
    -- zusaetzlich ein reiner BEFORE-INSERT-Trigger, der 'offen' beim
    -- Neuanlegen ablehnt -- ABSICHTLICH nicht auch bei UPDATE, sonst würde
    -- jede spaetere Aenderung (auch eine, die mit Normen nichts zu tun hat)
    -- an einer Altzeile erzwingen, ihre Normfrage rueckwirkend zu
    -- beantworten, obwohl Punkt 2 des Auftrags genau das verbietet ("Der
    -- Altbestand wird NICHT geraten"). Konsistenz-Trigger
    -- (norm_entscheidung_rang_*, norm_rang_gilt_ab_*,
    -- norm_entscheidung_gilt_bis_*) sichern die drei Felder gegeneinander
    -- ab, bei INSERT wie bei UPDATE, weil das ein Datenintegritaets- kein
    -- Geschichtsproblem ist: eine Zeile darf nie widerspruechlich WERDEN,
    -- unabhaengig davon, ob sie neu oder alt ist.
    norm_entscheidung TEXT NOT NULL DEFAULT 'offen',
    -- Entscheider (Nachtrag zum Auftrag 2026-08-08, Betreiber-Nachfrage:
    -- "wer hat entschieden?"). GEMESSEN: actor/session halten fest, wer den
    -- KNOTEN ANGELEGT hat, nicht wer ueber seinen Normstatus entschieden hat
    -- -- bei nachtraeglichen Sammelentscheidungen (siehe die 67 Alt-Knoten
    -- mit vorbestehendem norm_rang) faellt die Entscheidung Monate spaeter
    -- und von jemand anderem als dem urspruenglichen Schreiber. Gleiche
    -- Bauform wie zurueckgezogen_grund/_am/_von oben (drei einfache TEXT-
    -- Spalten, kein Vorgabewert ausser NULL) -- NICHT eine eigene Machart.
    -- Altbestand auf 'offen' hat KEINEN Entscheider: alle drei bleiben NULL,
    -- das ist korrekt (niemand hat entschieden). Sobald norm_entscheidung
    -- von 'offen' abweicht, verlangt der Trigger
    -- knowledge_nodes_norm_entscheidung_wer_bi/bu unten norm_entschieden_von
    -- UND norm_entschieden_grund nicht-leer -- exakt dieselbe Pflicht wie
    -- knowledge_zurueckziehen() sie fuer grund schon durchsetzt (Python-
    -- seitig dort, hier zusaetzlich als DB-Trigger, weil norm_entscheidung
    -- -- anders als zurueckziehen -- auch von Skripten direkt per SQL
    -- gesetzt wird, nicht nur ueber ein einzelnes MCP-Werkzeug).
    norm_entschieden_von TEXT,
    norm_entschieden_am TEXT,
    norm_entschieden_grund TEXT,
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
    -- Wert, siehe UNBEKANNTER_SCHREIBER in knowledge_mcp_server.py).
    --
    -- NACHTRAG (Auftrag 2026-08-06, zweiter Teil): model kommt DOCH dazu,
    -- gleiche Machart. Grund fuer den Sinneswandel: der erste Auftrag fragte
    -- "wer/welche Sitzung schrieb das", dieser fragt "welches MODELL --
    -- Guete der Eintraege nach Herkunft messbar machen (wie oft wird ein
    -- Ergebnis dieses Modells spaeter gezogen/korrigiert/zurueckgezogen)".
    -- Ueber access_log allein ist das nur per Zeit+Pfad-Verknuepfung
    -- rekonstruierbar, und die ist bei gleichzeitigen Schreibern (mehrere
    -- Worktrees) nicht eindeutig -- derselbe Grund, der schon actor/session
    -- an den Datensatz gebracht hat.
    actor TEXT,
    session TEXT,
    model TEXT,
    -- client (Auftrag 2026-08-07): actor/session/model sind alle drei nur
    -- gefuellt, wenn der Aufrufer sie liefert -- der Klient (Claude Code vs.
    -- Skriptzugriff) tut das faktisch nie. Anders als die drei: wird
    -- serverseitig in _identity() aus der Umgebung abgeleitet, nie vom
    -- Aufrufer erwartet. NULL fuer Altbestand vor dieser Spalte.
    client TEXT
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

-- norm_entscheidung (Auftrag 2026-08-08): 13 Zusicherungen, siehe
-- Spaltenkommentar oben fuer die Begruendung je Regel. Identischer Text wie
-- NORM_ENTSCHEIDUNG_TRIGGERS_SQL in knowledge_mcp_server.py (gleiches
-- Zwei-Kopien-Muster wie die drei Trigger-Paare oben). Vier Loecher hier
-- geschlossen, gefunden im unabhaengigen Review vor der Live-Migration
-- (Agent acf807ee8e6756f27, 2026-08-08): (a) ein UPDATE/UPSERT konnte eine
-- ENTSCHIEDENE Zeile stillschweigend zurueck auf 'offen' setzen -- die
-- Doppeldeutigkeit, die die ganze Spalte beseitigen soll, waere wieder da;
-- (b) ein UPDATE konnte auf einer 'offen'-Zeile norm_rang NEU vergeben, ohne
-- die Entscheidung mitzuschreiben (genau das tat normrang.py::anwenden roh);
-- (c) keine_norm liess gilt_ab/gilt_bis unbeachtet -- ein "Fakt" mit
-- Ablaufdatum ist dieselbe Ambiguitaet nur an anderer Stelle; (d) gilt_bis <
-- gilt_ab war nur python-seitig geprueft (_validate_geltung), nicht in der
-- DB selbst -- ~20 Skripte schreiben direkt per SQL.
CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_entscheidung_check_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN NEW.norm_entscheidung NOT IN ('offen','keine_norm','norm_befristet','norm_unbefristet')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_entscheidung unzulaessig: erlaubt sind offen, keine_norm, norm_befristet, norm_unbefristet');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_entscheidung_check_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN NEW.norm_entscheidung NOT IN ('offen','keine_norm','norm_befristet','norm_unbefristet')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_entscheidung unzulaessig: erlaubt sind offen, keine_norm, norm_befristet, norm_unbefristet');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_entscheidung_pflicht_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN NEW.norm_entscheidung = 'offen'
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_entscheidung fehlt: beim Anlegen entscheiden, ob dieser Knoten eine Norm ist -- keine_norm (Fakt), norm_befristet (Norm mit Enddatum) oder norm_unbefristet (Norm ohne Ende)');
END;

-- (a) Loch aus dem Review: 'offen' darf bei UPDATE (und damit auch bei
-- INSERT ... ON CONFLICT DO UPDATE, das nur den bu-Zweig feuert) niemals
-- NEU gesetzt werden -- nur Zeilen, die schon vor diesem Feld 'offen'
-- waren, duerfen es bleiben (OLD.norm_entscheidung = 'offen' AND NEW = 'offen'
-- ist in dieser WHEN-Klausel nicht erfasst, bleibt also erlaubt).
CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_entscheidung_pflicht_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN NEW.norm_entscheidung = 'offen' AND OLD.norm_entscheidung <> 'offen'
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_entscheidung kann nicht auf offen zurueckgesetzt werden: eine getroffene Entscheidung bleibt stehen, hoechstens auf einen anderen entschiedenen Wert aendern');
END;

-- (b) Loch aus dem Review: eine bisher 'offen'e Zeile bekommt per UPDATE
-- einen norm_rang, OHNE dass norm_entscheidung mitgeschrieben wird -- die
-- Rang-Vergabe IST die Entscheidung und muss sie explizit tragen.
CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_entscheidung_rang_neu_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN OLD.norm_entscheidung = 'offen' AND NEW.norm_entscheidung = 'offen'
    AND OLD.norm_rang IS NULL AND NEW.norm_rang IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_rang neu vergeben, aber norm_entscheidung fehlt: norm_befristet oder norm_unbefristet mitgeben');
END;

-- Entscheider (Nachtrag 2026-08-08, Betreiber-Nachfrage "wer hat
-- entschieden?"): jede Zeile mit norm_entscheidung <> 'offen' braucht
-- norm_entschieden_von UND norm_entschieden_grund nicht-leer -- dieselbe
-- Pflicht, die knowledge_zurueckziehen() fuer grund schon durchsetzt
-- (Python-seitig dort), hier zusaetzlich als DB-Trigger (bi+bu, Daten-
-- integritaet, kein Geschichtsproblem: eine Zeile darf nie ENTSCHIEDEN
-- OHNE Entscheider sein, unabhaengig davon ob neu oder alt). Altbestand
-- bleibt unberuehrt: 'offen' matcht die WHEN-Klausel nicht.
CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_entscheidung_wer_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN NEW.norm_entscheidung <> 'offen'
    AND (NEW.norm_entschieden_von IS NULL OR TRIM(NEW.norm_entschieden_von) = ''
         OR NEW.norm_entschieden_grund IS NULL OR TRIM(NEW.norm_entschieden_grund) = '')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_entscheidung gesetzt, aber norm_entschieden_von/norm_entschieden_grund fehlen: wer entscheidet und warum?');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_entscheidung_wer_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN NEW.norm_entscheidung <> 'offen'
    AND (NEW.norm_entschieden_von IS NULL OR TRIM(NEW.norm_entschieden_von) = ''
         OR NEW.norm_entschieden_grund IS NULL OR TRIM(NEW.norm_entschieden_grund) = '')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_entscheidung gesetzt, aber norm_entschieden_von/norm_entschieden_grund fehlen: wer entscheidet und warum?');
END;

-- (c) erweitert um gilt_ab/gilt_bis: keine_norm verlangt ALLE DREI
-- Normschicht-Felder leer, nicht nur norm_rang.
CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_entscheidung_rang_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN (NEW.norm_entscheidung = 'keine_norm' AND (NEW.norm_rang IS NOT NULL OR NEW.gilt_ab IS NOT NULL))
    OR (NEW.norm_entscheidung IN ('norm_befristet','norm_unbefristet') AND NEW.norm_rang IS NULL)
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_entscheidung widerspricht norm_rang/gilt_ab: keine_norm verlangt norm_rang und gilt_ab NULL, norm_befristet/norm_unbefristet verlangen norm_rang gesetzt');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_entscheidung_rang_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN (NEW.norm_entscheidung = 'keine_norm' AND (NEW.norm_rang IS NOT NULL OR NEW.gilt_ab IS NOT NULL))
    OR (NEW.norm_entscheidung IN ('norm_befristet','norm_unbefristet') AND NEW.norm_rang IS NULL)
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_entscheidung widerspricht norm_rang/gilt_ab: keine_norm verlangt norm_rang und gilt_ab NULL, norm_befristet/norm_unbefristet verlangen norm_rang gesetzt');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_rang_gilt_ab_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN NEW.norm_rang IS NOT NULL AND NEW.gilt_ab IS NULL
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_rang gesetzt aber gilt_ab fehlt: ab wann gilt die Norm?');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_rang_gilt_ab_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN NEW.norm_rang IS NOT NULL AND NEW.gilt_ab IS NULL
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_rang gesetzt aber gilt_ab fehlt: ab wann gilt die Norm?');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_entscheidung_gilt_bis_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN (NEW.norm_entscheidung = 'norm_befristet' AND NEW.gilt_bis IS NULL)
    OR (NEW.norm_entscheidung = 'norm_unbefristet' AND NEW.gilt_bis IS NOT NULL)
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_entscheidung widerspricht gilt_bis: norm_befristet verlangt gilt_bis gesetzt, norm_unbefristet verlangt gilt_bis NULL');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_entscheidung_gilt_bis_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN (NEW.norm_entscheidung = 'norm_befristet' AND NEW.gilt_bis IS NULL)
    OR (NEW.norm_entscheidung = 'norm_unbefristet' AND NEW.gilt_bis IS NOT NULL)
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_entscheidung widerspricht gilt_bis: norm_befristet verlangt gilt_bis gesetzt, norm_unbefristet verlangt gilt_bis NULL');
END;

-- (d) Loch aus dem Review: gilt_bis < gilt_ab war nur python-seitig
-- geprueft (_validate_geltung in knowledge_mcp_server.py), nicht in der DB
-- selbst -- Skripte, die direkt per SQL schreiben, waren ungeschuetzt.
-- julianday() statt Stringvergleich: L-ec167a (Bestand mischt Datumsform
-- "YYYY-MM-DD" und volle ISO-Zeit mit Offset, ein reiner "<"-Stringvergleich
-- waere an dieser Grenze falsch) -- gemessen gegen den echten Bestand
-- (sqlite3 knowledge.db, 2026-08-08): julianday() parst beide Formen korrekt
-- und vergleichbar. Gleicher Tag ist ERLAUBT (Grenzwert, Auftrag Punkt 4):
-- eine Norm, die am Tag ihres Inkrafttretens schon wieder endet (z.B.
-- Direktive, die am selben Tag zurueckgenommen wird), ist ein legitimer,
-- wenn auch entarteter Fall -- nur "danach" wird abgelehnt.
CREATE TRIGGER IF NOT EXISTS knowledge_nodes_gilt_bis_vor_gilt_ab_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN NEW.gilt_ab IS NOT NULL AND NEW.gilt_bis IS NOT NULL
    AND julianday(NEW.gilt_bis) < julianday(NEW.gilt_ab)
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.gilt_bis liegt vor gilt_ab');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_gilt_bis_vor_gilt_ab_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN NEW.gilt_ab IS NOT NULL AND NEW.gilt_bis IS NOT NULL
    AND julianday(NEW.gilt_bis) < julianday(NEW.gilt_ab)
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.gilt_bis liegt vor gilt_ab');
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
    actor TEXT,                               -- siehe Kommentar an knowledge_nodes.actor/.session/.model
    session TEXT,
    model TEXT,
    client TEXT                               -- siehe Kommentar an knowledge_nodes.client
);

-- Volltext-Suche ueber Lehren (Auftrag 2026-08-07). Gleiche Bauart wie
-- knowledge_fts oben, nicht anders: externe Inhaltstabelle, trigram-
-- Tokenizer, dieselbe Umlaut-Faltung vor dem Indizieren, ein Trigger-Trio
-- (INSERT/DELETE/UPDATE, UPDATE mit den zwei ueblichen Zweigen). Befund
-- 2026-08-07: description/root_cause/prevention wurden bisher nur per
-- Python-Substring (lesson_query, knowledge_recall_hook) durchsucht --
-- Volltabellendurchlauf, keine Rangfolge, keine Umlautfaltung, obwohl
-- Lehren mit 64% die GROESSERE Haelfte des Bestands sind. Indiziert werden
-- genau die drei Spalten, die heute schon durchsucht werden (kw_hits() in
-- knowledge_mcp_server.py::lesson_query) -- nicht mehr, nicht weniger.
-- lesson_query bleibt UNVERAENDERT (andere Frage: Typ-/Projektfilter), nur
-- knowledge_search nutzt diese Tabelle zusaetzlich zu knowledge_fts.
CREATE VIRTUAL TABLE IF NOT EXISTS lessons_fts USING fts5(
    description, root_cause, prevention,
    content='lessons_learned',
    content_rowid='rowid',
    tokenize="trigram case_sensitive 0"
);

CREATE TRIGGER IF NOT EXISTS lessons_ai AFTER INSERT ON lessons_learned BEGIN
    INSERT INTO lessons_fts(rowid, description, root_cause, prevention)
    VALUES (new.rowid,
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.description,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.root_cause,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.prevention,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')));
END;

CREATE TRIGGER IF NOT EXISTS lessons_ad AFTER DELETE ON lessons_learned BEGIN
    INSERT INTO lessons_fts(lessons_fts, rowid, description, root_cause, prevention)
    VALUES ('delete', old.rowid,
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(old.description,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(old.root_cause,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(old.prevention,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')));
END;

CREATE TRIGGER IF NOT EXISTS lessons_au AFTER UPDATE ON lessons_learned BEGIN
    INSERT INTO lessons_fts(lessons_fts, rowid, description, root_cause, prevention)
    VALUES ('delete', old.rowid,
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(old.description,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(old.root_cause,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(old.prevention,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')));
    INSERT INTO lessons_fts(rowid, description, root_cause, prevention)
    VALUES (new.rowid,
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.description,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.root_cause,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
        LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.prevention,
            'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')));
END;

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
    client TEXT,                              -- siehe Kommentar an knowledge_nodes.client
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
    dim INTEGER,                      -- Vektorlaenge des erzeugenden Modells (Auftrag
                                       -- 2026-08-07: macht einen Modellwechsel/gemischten
                                       -- Bestand erkennbar; die Sperre selbst filtert in
                                       -- knowledge_mcp_server._embedding_ranking auf model)
    vector BLOB NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (kind, ref_id, project_id)
);

-- knowledge_config: kleine Schluessel/Wert-Tabelle fuer Werte, die ein
-- Trigger lesen muss, eine ENV-Variable aber nicht (Auftrag 2026-08-07,
-- Modellsperre). Einziger Schluessel bisher: embed_model -- das Modell, mit
-- dem build_embeddings.py zuletzt ALLE Vektoren neu gerechnet hat. Seed unten
-- haelt den Wert synchron zu embeddings.DEFAULT_EMBED_MODEL (Python-Default);
-- ein Modellwechsel schreibt beide Stellen (build_embeddings.py macht das
-- beim Neu-Rechnen automatisch, siehe dortiger UPSERT vor der Schreibschleife).
CREATE TABLE IF NOT EXISTS knowledge_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
INSERT OR IGNORE INTO knowledge_config (key, value, updated_at)
    VALUES ('embed_model', 'bge-m3', strftime('%Y-%m-%dT%H:%M:%SZ', 'now'));

-- Sperre Stufe 2 (ADR-028, Vorgang 2026-08-07): ein veralteter Prozess mit
-- fremdem Modell im Speicher kann keinen Vektor mit diesem Modell mehr in
-- knowledge_embeddings schreiben -- unabhaengig vom Melder in
-- scripts/mcp_veraltet.py (nur Stufe 4, meldet, verhindert nichts). Bewusst
-- NUR an knowledge_embeddings, nicht an knowledge_nodes/lessons_learned: ein
-- Knoten/eine Lehre muss auch geschrieben werden koennen, wenn NUR die
-- Einbettung abgelehnt wird (Entscheidung 2026-08-07 frueh, bereits so
-- gehandhabt in _rebuild_node_embedding/_rebuild_lesson_embedding in
-- knowledge_mcp_server.py -- try/except dort um genau diesen INSERT).
-- WHEN NEW.model <> (SELECT ...): liefert die Unterabfrage NULL (Tabelle
-- ohne Zeile, z.B. eine minimale Testfixture ohne den Seed-INSERT oben),
-- ist der Vergleich NULL -> WHEN false -> Trigger bleibt aus, kein Absturz
-- auf einer DB ohne Konfigurationszeile.
CREATE TRIGGER IF NOT EXISTS knowledge_embeddings_model_check_bi
BEFORE INSERT ON knowledge_embeddings
FOR EACH ROW WHEN NEW.model <> (SELECT value FROM knowledge_config WHERE key = 'embed_model')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_embeddings.model weicht vom gueltigen Modell in knowledge_config ab -- Prozess laeuft vermutlich mit veraltetem Code (siehe scripts/mcp_veraltet.py), Sitzung neu starten oder build_embeddings.py fuer das aktuelle Modell erneut laufen lassen');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_embeddings_model_check_bu
BEFORE UPDATE ON knowledge_embeddings
FOR EACH ROW WHEN NEW.model <> (SELECT value FROM knowledge_config WHERE key = 'embed_model')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_embeddings.model weicht vom gueltigen Modell in knowledge_config ab -- Prozess laeuft vermutlich mit veraltetem Code (siehe scripts/mcp_veraltet.py), Sitzung neu starten oder build_embeddings.py fuer das aktuelle Modell erneut laufen lassen');
END;

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

-- Eskalation von Lehren zu Regeln (Nachtrag 2026-08-08).
-- Beide Tabellen wurden von eskalation_vorlage.py zur Laufzeit angelegt und
-- fehlten darum jeder Erstinstallation: gemessen an einem Rundlauf
-- (brainlehr.py raus/rein) trug eine frische Datenbank sechs Tabellen und
-- zwei Spalten weniger als der Betrieb, ohne dass irgendetwas es meldete.
-- Schema gehoert hierher, nicht in das Skript, das die Tabelle zufaellig
-- zuerst braucht.
CREATE TABLE IF NOT EXISTS eskalation_historie (
    lesson_id TEXT PRIMARY KEY,
    promoted_at TEXT NOT NULL,
    occurrences_at_promotion INTEGER NOT NULL,
    demoted_at TEXT
);
CREATE TABLE IF NOT EXISTS eskalation_vorschlag (
    lesson_id TEXT PRIMARY KEY,
    regel_vorschlag TEXT NOT NULL,
    erzeugt_am TEXT NOT NULL
);

-- ── Annahmen (Uebernahme aus der Stiftshuette, 2026-08-08) ────────────────
-- Uebernommen aus assumptions.json (hub/docs/PLAN_STIFTSHUETTE_UEBERNAHME_
-- 2026-08-08.md, Punkt 1). Dort lag das Schema tot: es gab keinen Schreiber,
-- weil es einen Reiter gebraucht haette. Hier braucht es keine Oberflaeche.
--
-- Der Zweck ist nicht Ablage, sondern Zwang: wer eine Annahme eintraegt, muss
-- sagen, WIE GUT der Beleg ist und WAS EIN IRRTUM KOSTET. Beides sind Felder,
-- die man nicht ausfuellen kann, ohne nachzudenken -- dieselbe Klasse wie
-- "keine Zahl ohne Nenner".
--
-- Warum die Regeln in der Datenbank stehen und nicht im aufrufenden Code:
-- ein Schreiber, der sie vergisst, ist der Normalfall (gemessen: BEGOD_
-- KNOWLEDGE_DB wurde von 3 von 6 Skripten geachtet, L-6c6661). Was gelten
-- soll, gilt an der Tabelle.
CREATE TABLE IF NOT EXISTS annahmen (
    id TEXT PRIMARY KEY,
    annahme TEXT NOT NULL,                    -- was angenommen wird, in einem Satz
    kategorie TEXT,                           -- frei, z.B. 'technik'|'nutzung'|'recht'
    status TEXT NOT NULL DEFAULT 'offen'
        CHECK (status IN ('offen', 'bestaetigt', 'widerlegt')),
    beleg TEXT DEFAULT '',                    -- worauf sich das stuetzt, wortwoertlich
    belegrang TEXT NOT NULL DEFAULT 'geraten'
        CHECK (belegrang IN ('gemessen', 'fremdbericht', 'plausibel', 'geraten')),
    kosten_wenn_falsch TEXT NOT NULL,         -- ohne diesen Satz kein Eintrag
    geprueft_von TEXT DEFAULT '',
    geprueft_am TEXT DEFAULT '',
    tatsaechliche_kosten TEXT DEFAULT '',     -- erst nach einem Irrtum ausfuellbar
    notizen TEXT DEFAULT '',
    projects TEXT DEFAULT '[]',               -- JSON-Array wie lessons_learned.projects
    node_path TEXT,                           -- Bezug auf knowledge_nodes.path
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    anlass TEXT NOT NULL DEFAULT 'unbekannt', -- siehe knowledge_nodes.anlass
    actor TEXT,
    session TEXT,
    model TEXT,
    client TEXT
);

CREATE INDEX IF NOT EXISTS idx_annahmen_status ON annahmen(status);

-- 'gemessen' ohne Beleg ist keine Messung, sondern eine Behauptung mit
-- besserem Namen. Die teuerste Verwechslung des Hauses, darum an der Tabelle.
CREATE TRIGGER IF NOT EXISTS annahmen_gemessen_braucht_beleg_bi
BEFORE INSERT ON annahmen
WHEN new.belegrang = 'gemessen' AND TRIM(COALESCE(new.beleg, '')) = ''
BEGIN
    SELECT RAISE(ABORT, 'belegrang=gemessen verlangt einen nicht leeren beleg -- eine Messung ohne Protokoll ist keine');
END;

CREATE TRIGGER IF NOT EXISTS annahmen_gemessen_braucht_beleg_bu
BEFORE UPDATE ON annahmen
WHEN new.belegrang = 'gemessen' AND TRIM(COALESCE(new.beleg, '')) = ''
BEGIN
    SELECT RAISE(ABORT, 'belegrang=gemessen verlangt einen nicht leeren beleg -- eine Messung ohne Protokoll ist keine');
END;

-- Eine Annahme verlaesst 'offen' nur mit Beleg UND Pruefer UND Zeitpunkt.
-- Ohne diese drei ist "bestaetigt" bloss eine Meinung mit Zeitstempel.
CREATE TRIGGER IF NOT EXISTS annahmen_entscheidung_braucht_pruefung_bu
BEFORE UPDATE ON annahmen
WHEN new.status <> 'offen'
 AND (TRIM(COALESCE(new.beleg, '')) = ''
      OR TRIM(COALESCE(new.geprueft_von, '')) = ''
      OR TRIM(COALESCE(new.geprueft_am, '')) = '')
BEGIN
    SELECT RAISE(ABORT, 'status bestaetigt/widerlegt verlangt beleg, geprueft_von und geprueft_am');
END;

-- Herkunft ist unveraenderlich, wie bei knowledge_nodes: der Wortlaut der
-- Annahme und ihr Entstehungszeitpunkt bleiben stehen. Wer die Annahme
-- umschreibt, faelscht die Vorgeschichte der Entscheidung, die auf ihr fusst.
CREATE TRIGGER IF NOT EXISTS annahmen_herkunft_unveraenderlich_bu
BEFORE UPDATE ON annahmen
WHEN new.annahme <> old.annahme OR new.created_at <> old.created_at
BEGIN
    SELECT RAISE(ABORT, 'annahme und created_at sind unveraenderlich -- neue Annahme anlegen, alte widerlegen');
END;
