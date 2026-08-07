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
-- Nachtragen ist erlaubt (NULL -> Wert): eine Luecke zu fuellen schreibt keine Herkunft um.
-- lessons_learned.actor/session meinen ZULETZT gesehen von (mcp_server:2640 ueberschreibt sie
-- bei jeder Wiederholung) -- sie sind darum kein Herkunftsanker, first_seen ist es.
--
-- Vorbild: knowledge_embeddings_model_check_bu (gleiche Bauform, gleicher Zweck).

DROP TRIGGER IF EXISTS knowledge_nodes_herkunft_bu;
CREATE TRIGGER knowledge_nodes_herkunft_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN
       (OLD.id IS NOT NULL AND NEW.id IS NOT OLD.id)
    OR (OLD.created_at IS NOT NULL AND NEW.created_at IS NOT OLD.created_at)
    OR (OLD.source IS NOT NULL AND NEW.source IS NOT OLD.source)
    OR (OLD.quell_hash IS NOT NULL AND NEW.quell_hash IS NOT OLD.quell_hash)
    OR (OLD.abgeleitet_von IS NOT NULL AND NEW.abgeleitet_von IS NOT OLD.abgeleitet_von)
    OR (OLD.session IS NOT NULL AND NEW.session IS NOT OLD.session)
    OR (OLD.actor IS NOT NULL AND NEW.actor IS NOT OLD.actor)
BEGIN
    SELECT RAISE(ABORT, 'Herkunftsfeld unveraenderlich (id, created_at, source, quell_hash, abgeleitet_von, session, actor). Ein Eintrag ohne nachpruefbare Herkunft ist eine Behauptung. Inhalt aendern: title/summary/content/tags. Aussage zurueckziehen: knowledge_zurueckziehen. Neue Erkenntnis: neuen Knoten anlegen und mit abgeleitet_von auf diesen zeigen.');
END;

DROP TRIGGER IF EXISTS lessons_herkunft_bu;
CREATE TRIGGER lessons_herkunft_bu
BEFORE UPDATE ON lessons_learned
FOR EACH ROW WHEN
       (OLD.id IS NOT NULL AND NEW.id IS NOT OLD.id)
    OR (OLD.first_seen IS NOT NULL AND NEW.first_seen IS NOT OLD.first_seen)
    OR (OLD.anlass IS NOT NULL AND NEW.anlass IS NOT OLD.anlass)
BEGIN
    SELECT RAISE(ABORT, 'Herkunftsfeld unveraenderlich (id, first_seen, anlass). Wiederholung zaehlen: occurrences/last_seen. Inhalt schaerfen: description/root_cause/resolution/prevention.');
END;
