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
    -- Belegart (SCHRITT 1 aus docs/PLAN_MENSCHLICHER_ENTSCHEID_2026-08-12.md).
    -- norm_entschieden_von sagt WER entschieden hat, diese Spalte sagt WOMIT
    -- das belegt ist -- ohne die beiden zu vermischen. ENTSCHEIDER
    -- (norm_entschieden_von) und SCHREIBER (actor, siehe unten) sind bereits
    -- getrennte Spalten; was fehlte, war ein Feld fuer die Beweiskraft der
    -- Entscheider-Angabe selbst, denn ein Name allein sagt nichts darueber,
    -- wie er zustande kam.
    -- Drei Werte, aus den Alternativen des Plans (Abschnitt "Die
    -- Alternativen"):
    --   'selbstauskunft' -- Behauptung des Schreibers, nicht geprueft. Der
    --                       heutige einzige Weg (anlass='betreiber').
    --   'systemauth'     -- lokale Systemauthentisierung (Touch ID/Kennwort,
    --                       Plan-Alternative C) hat Anwesenheit belegt.
    --   'kommandozeile'  -- der Mensch selbst hat direkt geschrieben, ohne
    --                       Assistenten dazwischen (Plan-Alternative B).
    -- Bewusst KEIN Wert, der "gelesen" oder "verstanden" behauptet: der Plan
    -- grenzt ausdruecklich ab, dass jede Systemauthentisierung nur belegt,
    -- dass ein Mensch ANWESEND war -- nicht, dass er den Inhalt gelesen hat
    -- (Plan, Abschnitt "Was der Beleg wirklich aussagt"). Ein Wert wie
    -- 'gelesen_bestaetigt' wuerde diese Grenze im Datenmodell selbst
    -- verwischen. NULL = nicht erfasst (gesamter Altbestand, und jede Zeile
    -- ohne norm_entschieden_von).
    norm_entschieden_belegart TEXT,
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
    -- WER FUEHRT DIE MASCHINE, die hier geschrieben hat (Betreiberweisung
    -- 2026-08-11: "chatgpt kann den gleichen Ausweis benutzen, muss aber
    -- mitgeben dass chatgpt gefuehrt von markus"). Der Wert stammt
    -- AUSSCHLIESSLICH aus dem beglaubigten Ausweis (ausweis.Ausweis.
    -- bedient_von), nie aus einem Argument -- waere er setzbar, koennte jeder
    -- Schreiber eine menschliche Deckung behaupten, und das Feld waere so
    -- wertlos wie actor vor B4.1 (wer actor="betreiber" mitschickte, WAR
    -- Betreiber).
    -- LEER ist der Normalfall und kein Mangel: bei unbeglaubigten Schreibern
    -- gibt es keinen Nachweis, und bei einem Menschen gibt es niemanden ueber
    -- ihm -- "chefin gefuehrt von chefin" waere eine leere Aussage.
    bedient_von TEXT,
    actor TEXT,
    session TEXT,
    model TEXT,
    -- client (Auftrag 2026-08-07): actor/session/model sind alle drei nur
    -- gefuellt, wenn der Aufrufer sie liefert -- der Klient (Claude Code vs.
    -- Skriptzugriff) tut das faktisch nie. Anders als die drei: wird
    -- serverseitig in _identity() aus der Umgebung abgeleitet, nie vom
    -- Aufrufer erwartet. NULL fuer Altbestand vor dieser Spalte.
    client TEXT,
    -- Gattung (Auftrag S1b, docs/PLAN_DESTILLE_2026-08-09.md). Haengt am
    -- WERK, nicht an der einzelnen Aussage: ein Nachschlagewerk (NASA LLIS,
    -- eine Normensammlung) wird nachgeschlagen, es draengt sich nicht auf --
    -- anders als Arbeitsbestand (eigene Direktiven, Befunde, Lehren aus
    -- diesem Haus), der im automatischen Abruf mitspielen soll. Gemessen
    -- 2026-08-09: 1638 von 2020 Knoten (81%) sind /nasa-llis, anlass='skript',
    -- source nennt nen.nasa.gov/llis.csv, norm_entscheidung durchgaengig
    -- 'offen', in der gesamten Protokollhistorie 3 mal gezogen -- ein Werk,
    -- das sich beim Abruf vor das eigene Wissen draengt (0 von 35 Pruefaellen
    -- getroffen, siehe abrufguete.py). Vorgabe 'arbeitsbestand' deckt den
    -- gesamten Altbestand ab, kein Wert wird geraten -- gleiche Bauform wie
    -- anlass oben (NOT NULL DEFAULT, Werte-Trigger bi+bu unten). NUR die 1638
    -- per migrate_gattung.py identifizierten NASA-Knoten werden per Migration
    -- auf 'nachschlagewerk' gesetzt, siehe dort fuer die Erkennungsregel und
    -- deren Begruendung.
    gattung TEXT NOT NULL DEFAULT 'arbeitsbestand',
    -- Freigabe (Planschritt S17): haelt fest, WER einen Knoten sehen darf --
    -- Rang, Art und Geltung sagen nichts darueber. Vorgabe 'intern': ein
    -- Knoten ohne eigene Entscheidung geht NIE nach 'offen' hinaus (gleiche
    -- Haltung wie norm_entscheidung='offen', nur ohne dessen Rueckfall-Sperre
    -- -- freigabe darf jederzeit in beide Richtungen geaendert werden, es
    -- gibt keine einmal getroffene, bindende Entscheidung wie bei einer
    -- Norm). Gleiche Bauform wie gattung oben (NOT NULL DEFAULT, Werte-
    -- Trigger bi+bu unten), keine Massenzuweisung ausser der Vorgabe.
    freigabe TEXT NOT NULL DEFAULT 'intern'
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

-- Herkunft wird nicht nachtraeglich umgeschrieben. Ohne diesen Trigger
-- koennte ein Schreiber die menschliche Deckung eines fremden Knotens
-- nachtraeglich auf sich selbst umbiegen -- die Kette waere dann kein
-- Nachweis mehr, sondern eine Behauptung mit Zeitstempel.
CREATE TRIGGER IF NOT EXISTS knowledge_nodes_bedient_von_unveraenderlich_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN IFNULL(NEW.bedient_von,'') <> IFNULL(OLD.bedient_von,'')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.bedient_von ist unveraenderlich -- wer eine Maschine fuehrt, steht ab dem Schreiben fest');
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

-- Gattung (Auftrag S1b): gleiche Bauform wie anlass oben, zwei Werte.
CREATE TRIGGER IF NOT EXISTS knowledge_nodes_gattung_check_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN NEW.gattung NOT IN ('arbeitsbestand','nachschlagewerk')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.gattung unzulaessig: erlaubt sind arbeitsbestand, nachschlagewerk');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_gattung_check_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN NEW.gattung NOT IN ('arbeitsbestand','nachschlagewerk')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.gattung unzulaessig: erlaubt sind arbeitsbestand, nachschlagewerk');
END;

-- Freigabe (Planschritt S17): gleiche Bauform wie gattung oben, drei Werte.
CREATE TRIGGER IF NOT EXISTS knowledge_nodes_freigabe_check_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN NEW.freigabe NOT IN ('offen','intern','gesperrt')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.freigabe unzulaessig: erlaubt sind offen, intern, gesperrt');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_freigabe_check_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN NEW.freigabe NOT IN ('offen','intern','gesperrt')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.freigabe unzulaessig: erlaubt sind offen, intern, gesperrt');
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
-- (sqlite3 brainlehr.db, 2026-08-08): julianday() parst beide Formen korrekt
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
    -- siehe Kommentar an knowledge_nodes.bedient_von: kommt nur aus
    -- dem beglaubigten Ausweis, nie aus einem Argument.
    bedient_von TEXT,
    actor TEXT,                               -- siehe Kommentar an knowledge_nodes.actor/.session/.model
    session TEXT,
    model TEXT,
    client TEXT,                              -- siehe Kommentar an knowledge_nodes.client
    -- freigabe (B4.5-Nachtrag 2026-08-10): wie an knowledge_nodes.freigabe.
    -- Nachgezogen, weil der Koederlauf zeigte, dass ein Gast (Bezug
    -- 'published') alle Lehren sah -- sie trugen kein Freigabemerkmal, und was
    -- keines tragen KANN, laesst der Filter seither pauschal weg. Mit dieser
    -- Spalte wird aus dem groben Schnitt ein feiner.
    freigabe TEXT NOT NULL DEFAULT 'intern',
    -- Nachgetragen 2026-08-14 (Aufgabe 110). Die Spalte existierte NUR im
    -- gewachsenen Bestand, nie in schema.sql -- kern/raum_daten.py liest sie
    -- (`SELECT ... l.pruefstelle ... FROM lessons_learned l`) und brach damit
    -- auf jeder Erstinstallation mit "no such column: l.pruefstelle". Belegt
    -- am 2026-08-14 in beide Richtungen: frische DB bricht, gewachsene laeuft.
    --
    -- Warum es niemandem auffiel: raum_daten.py::_selftest baut sich seine
    -- EIGENE lessons_learned-Tabelle -- mit pruefstelle. Ein Test, der sein
    -- Schema selbst definiert, kann eine Schemaluecke grundsaetzlich nicht
    -- finden; er prueft seine eigene Annahme.
    pruefstelle TEXT,
    -- Beinahefehler (Plan docs/PLAN_BEINAHEFEHLER_2026-08-16.md, 2026-08-16):
    -- bemerkt und behoben, BEVOR Schaden entstand. Eigene Spalte statt eines
    -- eigenen type-Wertes, weil type die Fehlerklasse traegt (error|insight|
    -- pattern|antipattern) und der Bericht nach §6 genau diese Klasse noch
    -- braucht -- gefragt ist "welche KLASSE trat als Beinahefehler auf", nicht
    -- nur "wie viele". Ein type-Wert 'beinahefehler' haette die Klasse
    -- ueberschrieben.
    beinahefehler INTEGER NOT NULL DEFAULT 0,
    -- WORAN er bemerkt wurde -- der eigentliche Ertrag (Plan §2). Feste
    -- Wortliste statt Freitext, weil §6 sie AUSZAEHLEN will; Freitext zaehlt
    -- nicht. Erzwungen wird sie vom Trigger darunter, denn ein Feld, das leer
    -- bleiben darf, bleibt leer -- Beleg im eigenen Bestand:
    -- lessons_learned.bedient_von ist bei 958 von 958 Zeilen leer.
    -- 'zufall' ist ausdruecklich vorgesehen: wird er der haeufigste Wert,
    -- fehlt an dieser Stelle ein Mechanismus (Plan §6).
    bemerkt_woran TEXT
);

-- Schranke fuer beinahefehler/bemerkt_woran, gleiche Bauform wie die
-- freigabe-Trigger darunter: in der Datenbank, nicht im Aufrufer. MCP laeuft
-- ueber stdio, jeder Klient haelt seinen eigenen Prozess mit eigenem
-- Codestand -- eine Pruefung in Python gilt nur fuer neu gestartete Prozesse,
-- ein Trigger ab seiner Anlage fuer alle.
CREATE TRIGGER IF NOT EXISTS lessons_learned_beinahe_check_bi
BEFORE INSERT ON lessons_learned
FOR EACH ROW WHEN NEW.beinahefehler NOT IN (0, 1)
     OR (NEW.beinahefehler = 1 AND (NEW.bemerkt_woran IS NULL
         OR TRIM(NEW.bemerkt_woran) NOT IN ('zahl','test','waechter','gegenprobe','wissen','betreiber','zufall')))
BEGIN
    SELECT RAISE(ABORT, 'lessons_learned.beinahefehler ist 0 oder 1; bei 1 muss bemerkt_woran einen dieser Werte tragen: betreiber, gegenprobe, test, waechter, wissen, zahl, zufall');
END;

CREATE TRIGGER IF NOT EXISTS lessons_learned_beinahe_check_bu
BEFORE UPDATE ON lessons_learned
FOR EACH ROW WHEN NEW.beinahefehler NOT IN (0, 1)
     OR (NEW.beinahefehler = 1 AND (NEW.bemerkt_woran IS NULL
         OR TRIM(NEW.bemerkt_woran) NOT IN ('zahl','test','waechter','gegenprobe','wissen','betreiber','zufall')))
BEGIN
    SELECT RAISE(ABORT, 'lessons_learned.beinahefehler ist 0 oder 1; bei 1 muss bemerkt_woran einen dieser Werte tragen: betreiber, gegenprobe, test, waechter, wissen, zahl, zufall');
END;

-- Werte-Trigger fuer lessons_learned.freigabe, gleiche Bauform wie an
-- knowledge_nodes darunter (B4.5-Nachtrag hatte die SPALTE gebracht, die
-- Schranke fehlte). Die Pruefung gehoert in die Datenbank und nicht in den
-- Aufrufer: gemessen 2026-08-11 arbeiten 32 Serverprozesse gleichzeitig auf
-- derselben Datei, der aelteste mit 23 Stunden altem Code (Knoten 4603f990).
-- Ein Trigger gilt ab seiner Anlage fuer alle; eine Pruefung in Python nur
-- fuer neu gestartete Prozesse.
CREATE TRIGGER IF NOT EXISTS lessons_learned_freigabe_check_bi
BEFORE INSERT ON lessons_learned
FOR EACH ROW WHEN NEW.freigabe NOT IN ('offen','intern','gesperrt')
BEGIN
    SELECT RAISE(ABORT, 'lessons_learned.freigabe unzulaessig: erlaubt sind offen, intern, gesperrt');
END;

CREATE TRIGGER IF NOT EXISTS lessons_learned_freigabe_check_bu
BEFORE UPDATE ON lessons_learned
FOR EACH ROW WHEN NEW.freigabe NOT IN ('offen','intern','gesperrt')
BEGIN
    SELECT RAISE(ABORT, 'lessons_learned.freigabe unzulaessig: erlaubt sind offen, intern, gesperrt');
END;


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
    -- siehe Kommentar an knowledge_nodes.bedient_von: kommt nur aus
    -- dem beglaubigten Ausweis, nie aus einem Argument.
    bedient_von TEXT,
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
    ketten_hash TEXT,
    -- Tokenkosten je Zugriff (ADR-003, nachgezogen 2026-08-10). Im Betrieb
    -- existierten diese vier Spalten seit laengerem, in schema.sql nicht --
    -- eine Neuanlage konnte `kern/tokenkosten.py` deshalb gar nicht tragen.
    -- Sie sind bis heute in ALLEN Zeilen NULL, und das ist kein Versaeumnis
    -- dieser Datei: der LESER existiert samt Tests, ein SCHREIBER nicht
    -- (siehe Modulkopf von kern/tokenkosten.py). Die Spalten gehoeren
    -- trotzdem hierher, damit Neuanlage und Betrieb dieselbe Sache messen,
    -- sobald ein Schreiber dazukommt.
    tokens_input INTEGER,
    tokens_output INTEGER,
    tokens_cache_creation INTEGER,
    tokens_cache_read INTEGER
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
    hinsicht TEXT,                            -- Auftrag 76: WORIN aehnlich (bisher nur die ART).
                                               -- Kein CHECK/Whitelist -- verschiedene Erzeuger
                                               -- (Bedeutungskanten, spaeter evtl. weitere) tragen
                                               -- verschiedene Hinsichten, siehe kanten_aus_bedeutung.py.
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
    -- Nachgetragen 2026-08-14 (Aufgabe 110). Anders als pruefstelle wird diese
    -- Spalte zur Laufzeit ergaenzt (kern/build_embeddings.py rueste sie beim
    -- ersten Lauf nach), eine Erstinstallation bricht daran also NICHT --
    -- gemessen. Sie stand trotzdem nicht in schema.sql, und damit war die
    -- Datei als SOLL unvollstaendig: der Schemamelder meldete eine Abweichung,
    -- die keine war, und verbrauchte Aufmerksamkeit, die den echten Fall
    -- (pruefstelle) daneben verdeckte.
    text_checksum TEXT,
    PRIMARY KEY (kind, ref_id, project_id)
);

-- knowledge_config: kleine Schluessel/Wert-Tabelle fuer Werte, die ein
-- Trigger lesen muss, eine ENV-Variable aber nicht (Auftrag 2026-08-07,
-- Modellsperre). Einziger Schluessel bisher: embed_model -- das Modell, mit
-- SEIT 2026-08-13 traegt der Wert die volle VEKTOR-IDENTITAET, nicht nur den
-- Modellnamen: 'bge-m3@ctx2048' statt 'bge-m3' (Aufgabe 80). Grund: num_ctx
-- veraendert den Vektor, ohne den Modellnamen zu aendern -- wer die Grenze
-- anhebt und nachrechnet, bekommt Vektoren gleichen Namens und anderer
-- Abschneidung, und jeder Filter laesst sie durch. Die Identitaet gehoert
-- deshalb in den Namen, nicht in eine zwoelfte Spalte.
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
    VALUES ('embed_model', 'bge-m3@ctx2048', strftime('%Y-%m-%dT%H:%M:%SZ', 'now'));

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

-- Herkunftsschranke Normrang 1/2 (S1 Teil 2, docs/PLAN_DESTILLE_2026-08-09.md,
-- korrigiert 2026-08-09 nach Betreibereinwand: eine Schranke, die JEDEN
-- maschinellen Schreiber blockt, haette 100% der 37 gemessenen Rang-1/2-
-- Normen abgewiesen -- darunter zwei legitime Aufzeichnungen deutschen
-- WEG-Rechts (/ops/verwalterwahl-weg-im-buckeberg-zum-2027/rechtslage-die-*).
-- ENTSCHEIDEN (Normsetzung, Sache des Menschen) und AUFZEICHNEN (Bericht
-- ueber eine fremde Tatsache, darf die Maschine) sind zwei Handlungen.
-- Die Schranke haengt darum an der HERKUNFT (source), nicht am Schreiber:
-- eine Hausnorm (source zeigt NICHT auf eine externe Stelle) braucht bei
-- Rang 1/2 einen menschlichen Entscheider; eine Fremdnorm (Gesetz,
-- Verordnung, Urteil, Normungsstelle) darf die Maschine mit jedem Rang
-- aufzeichnen. Die zweite WHEN-Klausel (source-Erkennung) ist von Hand aus
-- normachsen.py::FREMDE_QUELLE uebersetzt -- SQLite kennt kein eingebautes
-- REGEXP, ein registriertes Custom-Function haette ~20 raw-SQL-Skripte
-- gebrochen, die diese DB ohne eine Python-Verbindung anfassen. Die dritte
-- WHEN-Klausel (Maschinen-Erkennung) ist von Hand aus reifegrad.py::
-- MASCHINEN_MERKMALE uebersetzt -- Selbstauskunft in norm_entschieden_von,
-- gemessen: alle 33 maschinell entschiedenen Rang-1/2-Normen tragen
-- woertlich 'claude-code/opus-5'. reifegrad.py::_selftest() prueft beide
-- Python-Fassungen gegen dieselben Beispielsaetze wie hier und bricht bei
-- Abweichung; die Wahrheit fuer JEDEN Schreiber bleibt trotzdem dieser
-- Trigger, auch fuer Skripte, die reifegrad.py nie importieren.
CREATE TRIGGER IF NOT EXISTS knowledge_nodes_normrang_herkunft_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN NEW.norm_rang IN (1,2)
    AND NOT (NEW.source IS NOT NULL AND (
        NEW.source LIKE '%gesetz%' OR NEW.source LIKE '%verordnung%' OR NEW.source LIKE '%urteil%'
        OR NEW.source LIKE '%az.%' OR NEW.source LIKE '%aktenzeichen%' OR NEW.source LIKE '%BGBl%'
        OR NEW.source LIKE '%EU-Verordnung%' OR NEW.source LIKE '%Richtlinie%' OR NEW.source LIKE '%DIN %'
        OR NEW.source LIKE '%EN %' OR NEW.source LIKE '%ISO %' OR NEW.source LIKE '%IEC %'
        OR NEW.source LIKE '%BSI %' OR NEW.source LIKE '%WCAG%' OR NEW.source LIKE '%RFC%'
    ))
    -- AUSWEG, ohne den die Schranke aussperrt statt zu schuetzen:
    -- norm_entschieden_von wird vom Server automatisch aus `actor` gesetzt und
    -- traegt damit IMMER die Maschine -- ein Mensch kann dort strukturell nicht
    -- stehen. Ohne diese Zeile waere jede kuenftige Hausnorm auf Rang 1/2
    -- blockiert, auch die auf ausdrueckliche Weisung des Betreibers. Genau der
    -- Fehler aus L-40d9a5: eine Wache ohne benutzbaren Ausweg erzieht zur
    -- Umgehung. `anlass='betreiber'` ist die einzige Stelle, an der eine
    -- menschliche Weisung in die Zeile kommt. Sie ist SELBSTAUSKUNFT des
    -- Schreibers und kein Nachweis -- aber sie ist eine Behauptung im
    -- Protokoll, die sich gegen den Gespraechsverlauf pruefen laesst, und das
    -- ist mehr als das stille Selbstermaechtigen von heute (62 von 72).
    AND COALESCE(NEW.anlass, '') <> 'betreiber'
    AND (
        NEW.norm_entschieden_von LIKE '%claude%' OR NEW.norm_entschieden_von LIKE '%gpt%'
        OR NEW.norm_entschieden_von LIKE '%gemini%' OR NEW.norm_entschieden_von LIKE '%anthropic%'
        OR NEW.norm_entschieden_von LIKE '%opus%' OR NEW.norm_entschieden_von LIKE '%sonnet%'
        OR NEW.norm_entschieden_von LIKE '%haiku%'
    )
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_rang 1/2 verlangt fuer Hausnormen einen menschlichen Entscheider: norm_entschieden_von auf einen Menschen setzen -- ODER, falls dies eine Norm fremder Herkunft ist (Gesetz/Verordnung/Urteil/Normungsstelle), source entsprechend nennen (z.B. Gesetz, Urteil, DIN, ISO, BSI, WCAG) -- oder anlass=betreiber, wenn der Betreiber es angewiesen hat');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_normrang_herkunft_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN NEW.norm_rang IN (1,2)
    AND NOT (NEW.source IS NOT NULL AND (
        NEW.source LIKE '%gesetz%' OR NEW.source LIKE '%verordnung%' OR NEW.source LIKE '%urteil%'
        OR NEW.source LIKE '%az.%' OR NEW.source LIKE '%aktenzeichen%' OR NEW.source LIKE '%BGBl%'
        OR NEW.source LIKE '%EU-Verordnung%' OR NEW.source LIKE '%Richtlinie%' OR NEW.source LIKE '%DIN %'
        OR NEW.source LIKE '%EN %' OR NEW.source LIKE '%ISO %' OR NEW.source LIKE '%IEC %'
        OR NEW.source LIKE '%BSI %' OR NEW.source LIKE '%WCAG%' OR NEW.source LIKE '%RFC%'
    ))
    -- AUSWEG, ohne den die Schranke aussperrt statt zu schuetzen:
    -- norm_entschieden_von wird vom Server automatisch aus `actor` gesetzt und
    -- traegt damit IMMER die Maschine -- ein Mensch kann dort strukturell nicht
    -- stehen. Ohne diese Zeile waere jede kuenftige Hausnorm auf Rang 1/2
    -- blockiert, auch die auf ausdrueckliche Weisung des Betreibers. Genau der
    -- Fehler aus L-40d9a5: eine Wache ohne benutzbaren Ausweg erzieht zur
    -- Umgehung. `anlass='betreiber'` ist die einzige Stelle, an der eine
    -- menschliche Weisung in die Zeile kommt. Sie ist SELBSTAUSKUNFT des
    -- Schreibers und kein Nachweis -- aber sie ist eine Behauptung im
    -- Protokoll, die sich gegen den Gespraechsverlauf pruefen laesst, und das
    -- ist mehr als das stille Selbstermaechtigen von heute (62 von 72).
    AND COALESCE(NEW.anlass, '') <> 'betreiber'
    AND (
        NEW.norm_entschieden_von LIKE '%claude%' OR NEW.norm_entschieden_von LIKE '%gpt%'
        OR NEW.norm_entschieden_von LIKE '%gemini%' OR NEW.norm_entschieden_von LIKE '%anthropic%'
        OR NEW.norm_entschieden_von LIKE '%opus%' OR NEW.norm_entschieden_von LIKE '%sonnet%'
        OR NEW.norm_entschieden_von LIKE '%haiku%'
    )
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_rang 1/2 verlangt fuer Hausnormen einen menschlichen Entscheider: norm_entschieden_von auf einen Menschen setzen -- ODER, falls dies eine Norm fremder Herkunft ist (Gesetz/Verordnung/Urteil/Normungsstelle), source entsprechend nennen (z.B. Gesetz, Urteil, DIN, ISO, BSI, WCAG) -- oder anlass=betreiber, wenn der Betreiber es angewiesen hat');
END;

-- norm_art-Wertebereich (Auftrag 95 = Schritt 1, docs/PLAN_RECHTSRAUM_2026-08-13.md).
-- Werte aus Knoten dd367fd1 (Sein/Sollen/Duerfen), gleiche Bauform wie
-- knowledge_nodes_norm_entschieden_belegart_check_bi/bu oben: NULL bleibt
-- erlaubt (Altbestand, und jeder eigene Satz ohne fremdes Zitat), nur ein
-- GESETZTER, aber unbekannter Wert wird abgewiesen. bi+bu, weil beide Wege
-- (Anlegen, Nachtrag per knowledge_update) dieselbe Zusicherung umgehen
-- koennten.
CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_art_check_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN NEW.norm_art IS NOT NULL AND NEW.norm_art NOT IN ('sein','sollen','duerfen')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_art unzulaessig: erlaubt sind sein, sollen, duerfen (oder NULL fuer eigenes Wissen)');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_art_check_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN NEW.norm_art IS NOT NULL AND NEW.norm_art NOT IN ('sein','sollen','duerfen')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_art unzulaessig: erlaubt sind sein, sollen, duerfen (oder NULL fuer eigenes Wissen)');
END;

-- norm_art-Pflicht fuer fremde Herkunft. Knoten dd367fd1 legt die Werte fest
-- (sein/sollen/duerfen) aber nicht, WANN sie Pflicht sind -- das war die
-- offene Frage dieses Auftrags. Antwort: NULL bleibt der Normalfall fuer
-- eigenes Wissen (Hausregel, Selbsterfahrung) und braucht KEINEN Aufwand;
-- Pflicht wird norm_art nur, wenn source auf eine Norm FREMDER Herkunft
-- zeigt -- fast dieselbe Worterkennung wie knowledge_nodes_normrang_herkunft_bi
-- oben, mit EINER bewussten Abweichung: '%EN %' fehlt hier. Jener Trigger
-- feuert nur bei norm_rang IN (1,2) (selten), diese Pflicht bei JEDER neuen
-- Zeile -- dort erwies sich '%EN %' als False-Positive-Quelle auf ganz
-- gewoehnlichem Deutsch (z.B. "Impressen (Abruf..." oder "Knoten unter"
-- enthalten woertlich 'en ', gemessen an 4 echten Bestandsquellen aus
-- test_knowledge_add_source.py/test_ableitung.py, die dadurch fälschlich als
-- Fremdnorm griffen). kern/normachsen.py::FREMDE_QUELLE (Python-Fassung)
-- umgeht das mit einer \b-Wortgrenze vor 'EN'/'DIN' -- SQLite kennt kein
-- REGEXP (siehe Kommentar oben), LIKE kann diese Grenze nicht nachbilden,
-- darum hier ausgelassen statt eine falsche Praezision vorzutaeuschen. 'az.'
-- bleibt (braucht einen Punkt, in Fliesstext viel seltener falsch positiv).
-- knowledge_mcp_server.py::_FREMDE_QUELLE_MARKER spiegelt EXAKT diese Liste
-- (nicht normachsen.FREMDE_QUELLE), damit Vorab-Pruefung und Trigger nie
-- auseinanderlaufen.
--
-- BEWUSST NUR BEFORE INSERT, nicht BEFORE UPDATE -- gleiche Abwaegung wie
-- knowledge_nodes_norm_entscheidung_pflicht_bi (siehe dortiger Kommentar):
-- eine BEFORE-UPDATE-Fassung wuerde jede spaetere Aenderung an einer
-- Altzeile mit fremd aussehender source (Altbestand: norm_art bei 0 von
-- 2166 gefuellt) erzwingen, ihre Art rueckwirkend zu beantworten, obwohl
-- die Grenze des Auftrags genau das verbietet ("KEINE rueckwirkende
-- Massenbefuellung"). Wer eine Altzeile per knowledge_update() aendert,
-- kann source ohnehin nicht mitgeben (Server-Vertrag) -- die Herkunft ist
-- nach dem Anlegen unveraenderlich, die Pflicht darum am Anlegen genug.
-- WARNUNG, gemessen 2026-08-13 (L-55075a): Dieser Trigger wird mit
-- CREATE IF NOT EXISTS angelegt. Eine KORREKTUR an seiner Definition
-- erreicht damit ausschliesslich frisch angelegte Datenbanken -- ein
-- gewachsener Bestand behaelt die alte Fassung, ohne dass es auffaellt.
-- Am 2026-08-13 hat genau das fremde Sitzungen stundenlang blockiert: die
-- Musterliste enthielt '%EN %' und traf damit jedes deutsche Wort auf -en
-- ('gemessen ', 'Lehren ', 'Knoten '). Die Datei war korrigiert, die
-- Datenbank nicht. Wer hier etwas aendert, zieht die installierte Fassung
-- per DROP TRIGGER und Neuanlage nach und liest sie danach zurueck
-- (select sql from sqlite_master), statt der Datei zu glauben.
CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_art_pflicht_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN NEW.norm_art IS NULL
    AND NEW.source IS NOT NULL AND (
        NEW.source LIKE '%gesetz%' OR NEW.source LIKE '%verordnung%' OR NEW.source LIKE '%urteil%'
        OR NEW.source LIKE '%az.%' OR NEW.source LIKE '%aktenzeichen%' OR NEW.source LIKE '%BGBl%'
        OR NEW.source LIKE '%EU-Verordnung%' OR NEW.source LIKE '%Richtlinie%' OR NEW.source LIKE '%DIN %'
        OR NEW.source LIKE '%ISO %' OR NEW.source LIKE '%IEC %'
        OR NEW.source LIKE '%BSI %' OR NEW.source LIKE '%WCAG%' OR NEW.source LIKE '%RFC%'
    )
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_art fehlt fuer einen Satz fremder Herkunft (source nennt Gesetz/Verordnung/Urteil/DIN/ISO/IEC/BSI/WCAG/RFC): norm_art setzen -- sein (Studie/Messung), sollen (Leitlinie/Direktive) oder duerfen (Gebuehrenordnung/Lizenz), siehe Knoten dd367fd1. Eigenes Wissen ohne fremdes Zitat braucht norm_art nicht.');
END;

-- Belegart-Wertebereich (SCHRITT 1, docs/PLAN_MENSCHLICHER_ENTSCHEID_2026-08-12.md).
-- Gleiches Muster wie die anlass/norm_entscheidung-Wertebereichstrigger oben:
-- bi+bu, weil beide Wege dieselbe Zusicherung umgehen koennten. NULL bleibt
-- erlaubt (Altbestand, und jede Zeile ohne norm_entschieden_von) -- nur ein
-- GESETZTER, aber unbekannter Wert wird abgewiesen. 'weisungszitat' kam am
-- 2026-08-16 dazu (docs/PLAN_VERTRAUENSREGLER_2026-08-16.md Schritt 1,
-- Knoten a6991a6b): der Eingang, ueber den knowledge_add/knowledge_update
-- explizit einen menschlichen Entscheider eintragen -- siehe die
-- Weisungszitat-Pflicht-Trigger direkt darunter.
CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_entschieden_belegart_check_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN NEW.norm_entschieden_belegart IS NOT NULL
    AND NEW.norm_entschieden_belegart NOT IN ('selbstauskunft', 'systemauth', 'kommandozeile', 'weisungszitat')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_entschieden_belegart unzulaessig: erlaubt sind selbstauskunft, systemauth, kommandozeile, weisungszitat (oder NULL)');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_entschieden_belegart_check_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN NEW.norm_entschieden_belegart IS NOT NULL
    AND NEW.norm_entschieden_belegart NOT IN ('selbstauskunft', 'systemauth', 'kommandozeile', 'weisungszitat')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_entschieden_belegart unzulaessig: erlaubt sind selbstauskunft, systemauth, kommandozeile, weisungszitat (oder NULL)');
END;

-- Weisungszitat-Pflicht (Auftrag 2026-08-16, docs/PLAN_VERTRAUENSREGLER_2026-08-16.md
-- Schritt 1, Knoten a6991a6b). DER FEHLENDE EINGANG: der Herkunfts-Trigger
-- oben (knowledge_nodes_normrang_herkunft_bi/_bu) verlangt fuer Rang 1/2
-- einen menschlichen Entscheider, aber weder knowledge_add() noch
-- knowledge_update() boten einen Weg, ihn absichtlich einzutragen (die
-- Reflexion 2026-08-16, fuenf betroffene Knoten). 'weisungszitat' ist dieser
-- Weg: wer norm_entschieden_belegart='weisungszitat' setzt, behauptet eine
-- woertliche Betreiberweisung -- der Beleg wird hier erzwungen, nicht nur
-- behauptet. Verlangt in norm_entschieden_grund: ein oeffnendes deutsches
-- Anfuehrungszeichen „, gefolgt von mindestens 10 Zeichen, gefolgt von einem
-- schliessenden " -- die Form, die im ganzen Haus fuer woertliche Zitate
-- verwendet wird (z.B. Knoten a6991a6b selbst). INSTR(...)+SUBSTR(...) statt
-- REGEXP: SQLite kennt kein eingebautes REGEXP (siehe Kommentar am
-- Herkunfts-Trigger oben), diese beiden Funktionen reichen fuer "Zeichen X,
-- danach Zeichen Y, Mindestabstand dazwischen".
--
-- MERKMAL, KEINE SPERRE (dieselbe Einordnung wie art=mensch in
-- kern/ausweis.py, L-33d3bd): der Trigger prueft FORM (Anfuehrungszeichen,
-- Mindestlaenge), nicht WAHRHEIT. Derselbe Prozess, der diesen Beleg liefern
-- muss, koennte ebenso gut ein erfundenes, aber foermlich korrektes Zitat
-- schreiben. Die Pruefung macht eine Falschbehauptung TEURER (lang genug,
-- foermlich zitiert), nicht UNMOEGLICH -- sie ist Reibung, kein Schutz, und
-- darf in keinem Bericht als Schutz auftauchen.
--
-- BEWUSST NICHT an norm_rang IN (1,2) gebunden: die Pflicht gilt fuer JEDE
-- Zeile, die 'weisungszitat' behauptet, unabhaengig vom Rang -- eine
-- unbelegte Behauptung ist bei Rang 3 nicht weniger falsch.
--
-- BEWUSST NICHT an bereits bestehende Zeilen gebunden: kern/herkunft_
-- normentscheider.py setzt norm_entschieden_von='betreiber' fuer Altzeilen
-- per rohem UPDATE OHNE Belegart (siehe dortiger Kommentar, tabu fuer diesen
-- Auftrag) -- diese Trigger greifen nur, wenn norm_entschieden_belegart
-- SELBST auf 'weisungszitat' gesetzt wird, was jenes Werkzeug nie tut.
CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_entschieden_weisungszitat_pflicht_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN NEW.norm_entschieden_belegart = 'weisungszitat'
    AND (
        INSTR(COALESCE(NEW.norm_entschieden_grund, ''), '„') = 0
        OR INSTR(SUBSTR(COALESCE(NEW.norm_entschieden_grund, ''),
                        INSTR(COALESCE(NEW.norm_entschieden_grund, ''), '„') + 1), '"') = 0
        OR INSTR(SUBSTR(COALESCE(NEW.norm_entschieden_grund, ''),
                        INSTR(COALESCE(NEW.norm_entschieden_grund, ''), '„') + 1), '"') - 1 < 10
    )
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_entschieden_belegart=weisungszitat verlangt ein woertliches Zitat in norm_entschieden_grund: „...." mit mindestens 10 Zeichen zwischen den Anfuehrungszeichen -- kein Zitat umformulieren, woertlich uebernehmen');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_entschieden_weisungszitat_pflicht_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN NEW.norm_entschieden_belegart = 'weisungszitat'
    AND (
        INSTR(COALESCE(NEW.norm_entschieden_grund, ''), '„') = 0
        OR INSTR(SUBSTR(COALESCE(NEW.norm_entschieden_grund, ''),
                        INSTR(COALESCE(NEW.norm_entschieden_grund, ''), '„') + 1), '"') = 0
        OR INSTR(SUBSTR(COALESCE(NEW.norm_entschieden_grund, ''),
                        INSTR(COALESCE(NEW.norm_entschieden_grund, ''), '„') + 1), '"') - 1 < 10
    )
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.norm_entschieden_belegart=weisungszitat verlangt ein woertliches Zitat in norm_entschieden_grund: „...." mit mindestens 10 Zeichen zwischen den Anfuehrungszeichen -- kein Zitat umformulieren, woertlich uebernehmen');
END;

-- BEWUSST KEINE Belegart-PFLICHT hier (Befund beim Bau, 2026-08-13): ein
-- erster Versuch verlangte Belegart bei jedem neuen Rang-1/2-Knoten mit
-- menschlichem Entscheider und brach 20 bestehende, laengst gruene Tests
-- (test_konfidenz.py, test_regelwechsel.py, test_norm_entscheidung.py,
-- test_normschicht_mcp.py, mehrere kern/-Selbsttests, der Betreiber-Import
-- in test_knowledge_add_defaults.py) -- alle schreiben norm_entschieden_von
-- als Mensch (z.B. 'betreiber', 'test'), ohne dass Belegart bei ihrer
-- Entstehung je gefordert war. SCHRITT 1 verlangt additiv/rueckwaertsvertraeglich
-- ("ein alter Serverprozess ... darf nicht abbrechen"), und genau dieselbe
-- Pflicht traf hier den eigenen, gerade erst entstandenen INSERT-Pfad.
-- norm_entschieden_belegart bleibt also freiwillig: gesetzt und PLAUSIBEL
-- (Wertebereichs-Trigger oben) oder NULL, wie jede andere additive Spalte.
-- Die Pflicht durchzusetzen ist Sache des schreibenden Werkzeugs (Schritt 3:
-- die App verlangt Systemauthentisierung, BEVOR sie ueberhaupt schreibt --
-- an dieser Stelle, nicht rueckwirkend in der DB, gehoert die Durchsetzung).

-- ---------------------------------------------------------------------------
-- Fassungshistorie (2026-08-09)
--
-- Befund, der dazu fuehrte: `knowledge_versions` traegt genau zwei Spalten
-- (id, version) und 2029 Zeilen, ALLE auf 1 -- ein Zaehler, keine Historie.
-- Ein UPDATE auf title/summary/content/tags war damit endgueltig; es gab
-- keinen Weg zurueck auf Feldebene. Das fiel auf, als 384 Knoten maschinell
-- umgeschrieben werden sollten.
--
-- Warum Trigger und nicht Anwendungscode: der Trigger greift bei JEDEM
-- Schreibweg, auch bei direktem SQL an knowledge_mcp_server.py vorbei
-- (Migrationsskripte, Messlaeufe, Reparaturen von Hand). Genau dort entsteht
-- der Datenverlust, den ein Archiv verhindern soll -- eine Sicherung, die nur
-- den ordentlichen Weg absichert, sichert den Fall nicht ab, fuer den es sie
-- gibt. Dieselbe Ueberlegung wie bei den FTS-Triggern darueber.
--
-- Archiviert wird die ALTE Fassung (OLD), nicht die neue: die neue steht ja
-- in knowledge_nodes. Nur bei echter Aenderung eines der vier Textfelder --
-- ein UPDATE, das nur updated_at oder norm_rang anfasst, erzeugt keine Zeile.
CREATE TABLE IF NOT EXISTS knowledge_fassungen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    path TEXT NOT NULL,                      -- Pfad zum Zeitpunkt der Aenderung
    title TEXT,
    summary TEXT,
    content TEXT,
    tags TEXT,
    actor TEXT,                              -- wer die ABGELOESTE Fassung geschrieben hatte
    model TEXT,
    session TEXT,
    galt_bis TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_fassungen_node ON knowledge_fassungen(node_id, id DESC);

CREATE TRIGGER IF NOT EXISTS knowledge_fassung_au AFTER UPDATE ON knowledge_nodes
WHEN COALESCE(OLD.title,'')   <> COALESCE(NEW.title,'')
  OR COALESCE(OLD.summary,'') <> COALESCE(NEW.summary,'')
  OR COALESCE(OLD.content,'') <> COALESCE(NEW.content,'')
  OR COALESCE(OLD.tags,'')    <> COALESCE(NEW.tags,'')
BEGIN
    INSERT INTO knowledge_fassungen (node_id, path, title, summary, content, tags, actor, model, session)
    VALUES (OLD.id, OLD.path, OLD.title, OLD.summary, OLD.content, OLD.tags, OLD.actor, OLD.model, OLD.session);
END;

-- ---------------------------------------------------------------------------
-- Zwei Tabellen, die bisher erst beim ersten Zugriff entstanden (2026-08-11)
--
-- kern/codekanten.py und kern/pruefspruch.py legen ihre Tabelle selbst an,
-- wenn sie fehlt. Das genuegt im Betrieb und ist in der Erstanlage falsch:
-- eine frische Datenbank hat die Tabellen dann nicht, und wer ihr Schema
-- liest, sieht ein Haus mit zwei fehlenden Zimmern. Hier stehen sie, damit
-- Erstanlage und Betrieb dasselbe Schema tragen; die Selbstanlage in den
-- beiden Modulen bleibt, weil sie bestehende Datenbanken nachruestet.
CREATE TABLE IF NOT EXISTS code_kanten (
    id            TEXT PRIMARY KEY,
    quelle_art    TEXT NOT NULL CHECK(quelle_art IN ('lehre','knoten')),
    quelle_id     TEXT NOT NULL,
    kandidat      TEXT NOT NULL,
    pfad          TEXT NOT NULL,
    mehrdeutig    INTEGER NOT NULL DEFAULT 0,
    erhoben_am    TEXT NOT NULL,
    UNIQUE(quelle_art, quelle_id, pfad)
);
CREATE INDEX IF NOT EXISTS code_kanten_pfad ON code_kanten(pfad);

CREATE TABLE IF NOT EXISTS pruefsprueche (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    frage         TEXT NOT NULL,
    urteil        TEXT NOT NULL,
    begruendung   TEXT NOT NULL,
    pruefer       TEXT NOT NULL,
    auftraggeber  TEXT NOT NULL,
    modell        TEXT,
    sitzung       TEXT,
    erstellt_am   TEXT NOT NULL,
    ketten_hash   TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- Planstatus (Auftrag 2026-08-15, "dem Plan eine Ablage fuer ERLEDIGUNG
-- geben -- getrennt von der Ablage fuer ENTSCHEIDUNG").
--
-- kern/planentscheidung.py legt Knoten aus ENTSCHEIDENDEN Planabschnitten an
-- und schreibt eine Kennung zurueck -- aber es gibt kein Feld fuer den
-- FORTSCHRITT dieser Entscheidung. Gemessen am 2026-08-15: der Fortschritt
-- wurde aus dem Fliesstext von docs/PLAN_GESAMT_2026-08-13.md gelesen und aus
-- `git log` geraten, Ergebnis fuenf Agenten auf bereits Gebautes und drei
-- Phantomzeilen (`82`/`83`/`87`) faelschlich als offene Aufgaben gefuehrt.
--
-- KEINE neue Spalte an knowledge_nodes: `abgeleitet_von` (1/2217, 0,0%) und
-- `norm_entschieden_belegart` (0/2217, 0,0%) sind schon heute faktisch leere
-- Spalten -- eine vierte waere derselbe Fehler. Eine eigene Tabelle traegt
-- die Aussage klarer: eine Statuszeile ist keine Eigenschaft des Knotens
-- selbst (der Wortlaut der Entscheidung aendert sich nicht durch ihren
-- Baufortschritt), sondern eine eigene, mit Beleg versehene BEHAUPTUNG
-- darueber -- dieselbe Form wie knowledge_nodes.norm_entscheidung (Aussage)
-- + norm_entschieden_von/_grund/_belegart (Beleg dazu), nur an einer eigenen
-- Tabelle statt an der Knotenzeile selbst, weil node_path hier nicht der
-- Primaerschluessel ist, sondern eine 1:1-Referenz auf einen bereits von
-- planentscheidung.py angelegten Planknoten.
--
-- SECHS ZUSTAENDE, jeder an einem tatsaechlich am 2026-08-15 beobachteten
-- Fall in docs/PLAN_GESAMT_2026-08-13.md gemessen (dort nur gelesen, siehe
-- Auftrag):
--   'offen'              -- noch nicht begonnen (Linie E: "wartet auf den
--                           Betreiber", `H2`-`H7`: "echt offen, kein
--                           Commit-Beleg gefunden").
--   'teilweise'          -- begonnen, nicht abgeschlossen ("`73` bleibt
--                           teilweise, nicht erledigt").
--   'gebaut_wirkungslos' -- eigene Kategorie im Plan vom 2026-08-15 ("Die
--                           neue Kategorie: gebaut, aber wirkungslos") --
--                           ohne sie waere `73`/`79` nicht von echtem
--                           `teilweise` (Code fehlt noch) zu unterscheiden.
--   'nicht_nachgemessen' -- "Zeitgrenze dieses Laufs, nicht als offen zu
--                           lesen" (`G3`, `G6`, `F8`) -- ANDERS als 'offen':
--                           die Arbeit koennte fertig sein, nur ungeprueft.
--   'phantom'             -- Kennung im Plantext genannt, aber "keine eigene
--                           Definition gefunden" (`82`, `83`, `87`, `23`) --
--                           keine Aufgabe, kein Fortschritt moeglich.
--   'erledigt'            -- rot-vor-gruen belegt (`42`,`67`,`68`,`70`,`71`
--                           je mit Commit zitiert).
--
-- SIEBTER WERT 'unbelegt' UND DER ERZWUNGENE TRIGGER darunter sind die
-- Antwort auf Frage 3 des Auftrags ("wer setzt den Status, woher weiss man,
-- dass er stimmt"): eine Heuristik ueber den Plantext kann "erledigt"
-- lesen, ohne dass ein Commit/Test/Messdatei danebensteht (derselbe
-- Praezision-vs-Trefferquote-Zielkonflikt wie bei `planentscheidung.
-- ist_entscheidend()`, siehe dortiger Modulkopf). NEGATIVFALL DES AUFTRAGS:
-- "ein Status ohne Beleg wird als unbelegt gefuehrt, nicht als erledigt" --
-- der Trigger unten erzwingt das AN DER DATENBANK, nicht nur in
-- kern/planstatus.py, damit auch ein direkter SQL-Schreiber (wie
-- planordnung.py es fuer knowledge_relations bereits tut) den Negativfall
-- nicht umgehen kann.
CREATE TABLE IF NOT EXISTS plan_status (
    id            TEXT PRIMARY KEY,
    node_path     TEXT NOT NULL UNIQUE,   -- Planknoten aus planentscheidung.py; ein Knoten
                                           -- traegt genau einen AKTUELLEN Status (kein Verlauf --
                                           -- vom Auftrag nicht verlangt, siehe Modulkopf oben).
    quelle_datei  TEXT NOT NULL,          -- Plandatei, aus der der Status gelesen/gesetzt wurde.
    quelle_kennung TEXT NOT NULL,         -- Abschnittskennung dort (S12, B4.1, ...), nur zur
                                           -- Lesbarkeit -- node_path bleibt die Wahrheit ueber
                                           -- WELCHER Knoten gemeint ist (siehe Grenzwert "zwei
                                           -- Abschnitte mit derselben Kennung" in kern/planstatus.py).
    status        TEXT NOT NULL CHECK(status IN (
                      'offen', 'teilweise', 'gebaut_wirkungslos',
                      'nicht_nachgemessen', 'phantom', 'erledigt', 'unbelegt')),
    beleg_art     TEXT CHECK(beleg_art IN ('commit', 'test', 'messdatei') OR beleg_art IS NULL),
    beleg         TEXT,                   -- Commit-Hash / Testname / Pfad unter runs/ -- woertlich,
                                           -- damit der Leser in Sekunden selbst nachschlagen kann
                                           -- (gleiche Haltung wie planbindung.py's Phantom-Kennung).
    gesetzt_von   TEXT NOT NULL,
    gesetzt_am    TEXT NOT NULL,
    FOREIGN KEY(node_path) REFERENCES knowledge_nodes(path) ON UPDATE CASCADE ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_plan_status_datei ON plan_status(quelle_datei);

-- Negativfall des Auftrags, an der DB erzwungen: 'erledigt' und
-- 'gebaut_wirkungslos' behaupten beide eine geprueft abgeschlossene Arbeit
-- (der Unterschied ist nur, ob sie wirkt) -- fuer beide ist ein Beleg
-- PFLICHT, sonst ist die Zeile 'unbelegt' zu setzen, nicht 'erledigt'.
CREATE TRIGGER IF NOT EXISTS plan_status_beleg_pflicht_bi
BEFORE INSERT ON plan_status
FOR EACH ROW WHEN NEW.status IN ('erledigt', 'gebaut_wirkungslos')
    AND (NEW.beleg_art IS NULL OR TRIM(IFNULL(NEW.beleg, '')) = '')
BEGIN
    SELECT RAISE(ABORT, 'plan_status: erledigt/gebaut_wirkungslos ohne Beleg -- Status ist unbelegt, nicht erledigt');
END;

CREATE TRIGGER IF NOT EXISTS plan_status_beleg_pflicht_bu
BEFORE UPDATE ON plan_status
FOR EACH ROW WHEN NEW.status IN ('erledigt', 'gebaut_wirkungslos')
    AND (NEW.beleg_art IS NULL OR TRIM(IFNULL(NEW.beleg, '')) = '')
BEGIN
    SELECT RAISE(ABORT, 'plan_status: erledigt/gebaut_wirkungslos ohne Beleg -- Status ist unbelegt, nicht erledigt');
END;

-- Urfassungen der S12-Neuformulierung (docs/PLAN_S12_ZWEITER_ANLAUF_2026-08-11.md,
-- Nachtrag 2026-08-12T07:20, kern/sicherung_s12.py). node_id ist PRIMARY KEY,
-- damit ein Knoten nur EINMAL gesichert werden kann -- ein zweiter Lauf nach
-- dem Umschreiben darf das Original nicht mit dem schon veraenderten Text
-- ueberschreiben. Loeschbar, ohne dass am Hauptschema etwas bleibt.
CREATE TABLE IF NOT EXISTS s12_urfassungen (
    node_id       TEXT PRIMARY KEY,
    path          TEXT NOT NULL,
    title         TEXT NOT NULL,
    summary       TEXT NOT NULL,
    content       TEXT,
    gesichert_am  TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- Widerrufsarchiv (Betreiberentscheidung 2026-08-14: "zu 1 ist archevieren
-- schlecht? ich glaube nicht!")
--
-- knowledge_zurueckziehen leerte content und summary. Damit vernichtete das
-- KORRIGIEREN eines falschen Eintrags den Beweis des falschen Eintrags --
-- genau die Zeile, die man braucht, wenn er Schaden angerichtet hat.
--
-- Getrennt von s12_urfassungen, obwohl beide Wortlaute sichern: jene Tabelle
-- gehoert zum S12-Versuch und hat node_id als PRIMARY KEY, also genau eine
-- Fassung je Knoten. Ein Knoten kann mehrfach zurueckgezogen und wieder
-- freigegeben werden, deshalb braucht es hier mehrere Zeilen je Knoten.
--
-- KEIN zusammengesetzter Schluessel aus (node_id, zurueckgezogen_am): now_iso()
-- hat Sekundengranularitaet, zwei Widerrufe in derselben Sekunde teilen den
-- Schluessel, und die erste -- also die interessante -- Fassung waere weg. Beim
-- Bauen genau so passiert und von tests/test_widerruf_archiv.py gefangen. Ein
-- Zeitstempel ist eine Angabe, kein Schluessel.
--
-- Was das NICHT aendert: der Knoten bleibt aus Suche und Abruf draussen. Der
-- bewahrte Wortlaut ist nur auf gezielte Frage erreichbar -- Archiv, nicht
-- Wiederauferstehung.
CREATE TABLE IF NOT EXISTS knowledge_widerruf_archiv (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id            TEXT NOT NULL,
    path               TEXT NOT NULL,
    title              TEXT NOT NULL,
    summary            TEXT,
    content            TEXT,
    grund              TEXT NOT NULL,
    zurueckgezogen_am  TEXT NOT NULL,
    zurueckgezogen_von TEXT
);
CREATE INDEX IF NOT EXISTS idx_widerruf_archiv_node ON knowledge_widerruf_archiv(node_id, id);

-- ---------------------------------------------------------------------------
-- Schemastand (ADR-003, 2026-08-10)
--
-- Die Marke muss stehen, BEVOR die erste Migration laeuft. Danach laesst sich
-- nicht mehr feststellen, welcher Stand vorher galt -- genau das ist dem
-- Betriebsbestand am 2026-08-08 passiert, wo die einzige Zeile dieser Tabelle
-- sich selbst als nachtraeglich gesetzt ausweist. Der Grund ist die
-- Reihenfolge, nicht die Menge: er gilt bei null Zeilen wie bei einer Million.
-- Compact, append-only resume records. A checkpoint describes work-in-progress,
-- not a durable knowledge claim.
CREATE TABLE IF NOT EXISTS session_checkpoints (
    id          TEXT PRIMARY KEY,
    session     TEXT NOT NULL,
    sequence    INTEGER NOT NULL CHECK(sequence > 0),
    summary     TEXT NOT NULL CHECK(length(trim(summary)) > 0),
    open_tasks  TEXT NOT NULL DEFAULT '',
    decisions   TEXT NOT NULL DEFAULT '',
    actor       TEXT,
    model       TEXT,
    created_at  TEXT NOT NULL,
    UNIQUE(session, sequence)
);
CREATE INDEX IF NOT EXISTS idx_session_checkpoints_latest
    ON session_checkpoints(session, sequence DESC);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    angewandt_am TEXT NOT NULL,
    beschreibung TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_migrations (version, angewandt_am, beschreibung)
VALUES (1, strftime('%Y-%m-%dT%H:%M:%SZ','now'),
        'Erstanlage aus schema.sql -- Stand vollstaendig bekannt, keine Vorgeschichte');
