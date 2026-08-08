-- Herkunft und Identitaet sind unveraenderlich.
--
-- Grund: Ein Verdichter (cavelehr), ein Kurator oder ein Migrationsskript, das einen
-- Datensatz NEU ERZEUGT statt ihn zu ergaenzen, laesst Herkunftsfelder weg oder schreibt
-- sie um. Der Skilltext verbietet das bereits -- aber ein Text bindet nur, wer ihn liest.
-- Diese Schranke gilt fuer jeden Schreiber, auch fuer sqlite3 von Hand.
--
-- Was NICHT hier steht, ist Absicht: title, summary, content, tags, status, occurrences,
-- last_seen, access_count bleiben frei aenderbar -- das ist der Zweck des Speichers.
-- norm_rang/gilt_ab/gilt_bis aendern sich rechtmaessig (eine Norm wird abgeloest) und
-- gehoeren darum ebenfalls nicht hierher.
--
-- Nachtragen ist erlaubt (Luecke -> Wert): eine Luecke zu fuellen schreibt keine Herkunft um.
-- Luecke heisst NULL ODER Leerstring (Nachtrag 2026-08-08). Der erste Entwurf pruefte nur auf
-- NULL und sperrte damit den source-Nachtrag in _ensure_node_constraint_triggers aus, der
-- genau die Zeilen mit TRIM(source)='' fuellt -- gemessen als roter Test
-- test_ensure_schema_heilt_alte_db_nach_und_traegt_source_nach. Ein leeres Feld ist keine
-- Herkunft, die man ueberschreiben koennte; es ist ihr Fehlen.
-- lessons_learned.actor/session meinen ZULETZT gesehen von (mcp_server:2640 ueberschreibt sie
-- bei jeder Wiederholung) -- sie sind darum kein Herkunftsanker, first_seen ist es.
--
-- Vorbild: knowledge_embeddings_model_check_bu (gleiche Bauform, gleicher Zweck).

DROP TRIGGER IF EXISTS knowledge_nodes_herkunft_bu;
CREATE TRIGGER knowledge_nodes_herkunft_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN
       (TRIM(COALESCE(OLD.id, '')) <> '' AND NEW.id IS NOT OLD.id)
    OR (TRIM(COALESCE(OLD.created_at, '')) <> '' AND NEW.created_at IS NOT OLD.created_at)
    OR (TRIM(COALESCE(OLD.source, '')) <> '' AND NEW.source IS NOT OLD.source)
    OR (TRIM(COALESCE(OLD.quell_hash, '')) <> '' AND NEW.quell_hash IS NOT OLD.quell_hash)
    OR (TRIM(COALESCE(OLD.abgeleitet_von, '')) <> '' AND NEW.abgeleitet_von IS NOT OLD.abgeleitet_von)
    OR (TRIM(COALESCE(OLD.session, '')) <> '' AND NEW.session IS NOT OLD.session)
    OR (TRIM(COALESCE(OLD.actor, '')) <> '' AND NEW.actor IS NOT OLD.actor)
BEGIN
    SELECT RAISE(ABORT, 'Herkunftsfeld unveraenderlich (id, created_at, source, quell_hash, abgeleitet_von, session, actor). Ein Eintrag ohne nachpruefbare Herkunft ist eine Behauptung. Inhalt aendern: title/summary/content/tags. Aussage zurueckziehen: knowledge_zurueckziehen. Neue Erkenntnis: neuen Knoten anlegen und mit abgeleitet_von auf diesen zeigen.');
END;

DROP TRIGGER IF EXISTS lessons_herkunft_bu;
CREATE TRIGGER lessons_herkunft_bu
BEFORE UPDATE ON lessons_learned
FOR EACH ROW WHEN
       (TRIM(COALESCE(OLD.id, '')) <> '' AND NEW.id IS NOT OLD.id)
    OR (TRIM(COALESCE(OLD.first_seen, '')) <> '' AND NEW.first_seen IS NOT OLD.first_seen)
    OR (TRIM(COALESCE(OLD.anlass, '')) <> '' AND NEW.anlass IS NOT OLD.anlass)
BEGIN
    SELECT RAISE(ABORT, 'Herkunftsfeld unveraenderlich (id, first_seen, anlass). Wiederholung zaehlen: occurrences/last_seen. Inhalt schaerfen: description/root_cause/resolution/prevention.');
END;
