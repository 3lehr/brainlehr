#!/usr/bin/env python3
"""
Knowledge MCP Server — Shared Knowledge Database Access for AI Agents.

Erstellt: 2026-03-25T16:30:00+01:00
Transport: stdio (JSON-RPC 2.0)
DB: SQLite + FTS5 Baumstruktur

Portabler Kern (ADR-024), zweistufig -- ADR-024 nannte nur "der MCP-Server"
und meinte drei Dateien; die Liste ging seither einmal verloren, deshalb
hier zweigeteilt und vollstaendig gehalten. Ermittelt am 2026-08-06 durch
tatsaechliches Kopieren in ein leeres Verzeichnis + Nachziehen jedes
ModuleNotFoundError, nicht geraten:

Kern (dieses Modul starten, erster Eintrag, Werkzeuge wie knowledge_add):
diese Datei + vier Nachbarn, sonst nur Stdlib:
  - schema.sql    (Erstanlage aller Kerntabellen, siehe ensure_schema/
                   _ensure_core_schema; einzige Schemaquelle, nicht im Code
                   nachgebaut)
  - embeddings.py (lokale Embeddings + RRF-Fusion; best-effort, ein Ausfall
                   blockiert die Suche nie, siehe embeddings.py-Docstring)
  - einschleusung.py (ADR-034: Verdachtserkennung TOP-LEVEL importiert,
                   feuert live in knowledge_add/knowledge_update/
                   lesson_record/lesson_update -- kein Bestandteil der
                   Selbstpruefung mehr, sondern des Schreibpfads selbst)
  - normrang.py   (ADR-034: norm_rang faellt bei knowledge_add() deterministisch
                   aus source, TOP-LEVEL importiert, gleicher Grund)
  - knowledge_lint.find_norm_conflicts_for() (ADR-034/Auftrag 2026-08-07:
                   Widerspruchspruefung, feuert in knowledge_add/
                   knowledge_update NACH dem Commit, wenn der geschriebene
                   Knoten eine Norm ist -- VERZOEGERT importiert in
                   _check_norm_conflicts(), gleicher Zirkelgrund wie
                   kurator_lauf() unten: knowledge_lint.py importiert
                   seinerseits aus diesem Modul)

Selbstpruefung (zusaetzlich fuer knowledge_lint.py + konfidenz.py, beide
gegen eine frische DB durchlaufgeprueft): obige Kerndateien PLUS
  - ankerverfahren.py   (externe Verankerung; braucht zusaetzlich das
                         Pip-Paket 'cryptography', keine weitere Datei)
  - geltungsbereich.py  (Bereichs-/Projektzuordnung)
  - kettenerklaerung.py (Erklaerungen zu Bruechen der Auditkette)
  - konfidenz.py        (Konfidenzverfall; importiert normkraft.py mit)
  - normkraft.py         (Normrang/-kraft, von konfidenz.py gebraucht)
  - normbestand.py      (Quellstatus-Pruefung)
  - knowledge_lint.py    (die Selbstpruefung selbst, importiert alle
                         obigen; DB_PATH darin fest an
                         SHARED_KNOWLEDGE/knowledge.db, keine BEGOD_KNOWLEDGE_DB-Uebersteuerung)
kurator_lauf() (Auftrag 2026-08-07) importiert knowledge_lint.py VERZOEGERT
(erst beim Aufruf, nicht beim Laden dieses Moduls -- knowledge_lint.py
importiert seinerseits aus diesem Modul, ein Top-Level-Import waere ein
echter Zirkel) und braucht deshalb zur Laufzeit die komplette
Selbstpruefungs-Stufe, nicht nur den Kern.
ankerverfahren.py und kettenerklaerung.py sind seit ADR-034 ebenfalls vom
Schreibpfad erreichbar (Werkzeug kettenerklaerung_erklaeren), aber weiterhin
VERZOEGERT importiert -- gleicher Zirkelgrund wie kurator_lauf() oben
(kettenerklaerung.py importiert seinerseits aus diesem Modul). lesson_recorder.py
ebenso verzoegert in _auto_rule_fuer_lesson() (importiert `knowledge_mcp_server
as kms`, derselbe Zirkel).
Alle uebrigen .py-Dateien in diesem Verzeichnis (auditanker, hebb_kanten,
...) sind eigenstaendige Skripte/Cronjobs ausserhalb dieser zwei Stufen --
der MCP-Server importiert sie nicht, knowledge_lint.py auch nicht.

Tools:
  - knowledge_browse(path)        → Kinder-Knoten (nur Titel+Summary)
  - knowledge_read(node_id)       → Volltext eines Knotens
  - knowledge_search(query, scope)→ Hybrid-Suche (FTS5 + optional lokale Embeddings, RRF-fusioniert), gibt Summaries zurück
  - knowledge_add(parent_path, title, summary, content, project_id, tags)
  - knowledge_update(node_id, summary, content)
  - knowledge_zurueckziehen(node_id, grund) → leert content/summary, Zeile bleibt, reversibel
  - knowledge_freigeben(node_id) → macht Zurueckziehen rueckgaengig (Sichtbarkeit, nicht Inhalt)
  - kettenerklaerung_erklaeren(access_log_id, grund) → erklaert einen Kettenbruch (ADR-034)
  - knowledge_relation_add|list|update|remove(...) → explizite belegte Kanten
  - lesson_record(type, description, root_cause, resolution, prevention, severity, projects, same_as)
  - lesson_update(lesson_id, description, root_cause, resolution, prevention, severity, projects, status, delete)
  - lesson_query(type, project, status)
  - knowledge_stats()             → Übersichts-Statistiken
"""

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

import difflib
import fcntl
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import sys
import time
import unicodedata
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
import embeddings  # lokale Embeddings + RRF-Fusion, siehe embeddings.py
import build_embeddings  # ADR-032: resolve_lesson_projects() fuer den Bereichs-Fanout
                          # beim Einbetten am Schreibvorgang -- selbe Regel wie im
                          # expliziten Batch-Lauf, nicht daneben nachgebaut.
import ausweis  # B4.1: actor wird beglaubigt, nicht behauptet (siehe _identity)
import werkzeugrechte  # B4.3: Durchsetzung an tools/call statt nur an tools/list
import einschleusung  # ADR-034: Verdachtserkennung direkt am Schreibvorgang
                       # (knowledge_add/knowledge_update/lesson_record/lesson_update),
                       # kein Sammellauf mehr noetig. Kein Zirkel (importiert selbst nichts von hier).
import normrang  # ADR-034: norm_rang faellt bei knowledge_add() deterministisch aus
                 # source, wenn der Aufrufer keinen eigenen mitgibt. Kein Zirkel.
import schema_nachzug  # 2026-08-10: fehlende Spalten generisch aus schema.sql
import herkunft_normentscheider  # Auftrag 2026-08-09: norm_entschieden_von traegt
                                  # 'betreiber' statt actor, wenn source einen belegten
                                  # Betreiber-Urheber zeigt (CLAUDE.md-Import). Kein
                                  # Zirkel -- das Modul importiert nichts von hier.

# BEGOD_KNOWLEDGE_DB ueberschreibt den Pfad (gleiche Bauform wie die drei
# BEGOD_KNOWLEDGE_*-Vars in _identity()). Ohne sie: heutiges Verhalten
# unveraendert. Grund: ein fest an __file__ gebundener DB-Pfad verhindert
# jeden Betrieb ausserhalb dieses Verzeichnisses (Fremdclient-Test, spaeter
# Portabilitaet ausserhalb Begod2026) und laesst sich nicht gegen eine
# Testkopie fahren, ohne die echte DB anzufassen.
DB_PATH = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (Path(__file__).parent / "knowledge.db"))
BERLIN = ZoneInfo("Europe/Berlin")
# Mehrere MCP-Prozesse/Sitzungen schreiben gleichzeitig auf dieselbe WAL-DB.
# WAL erlaubt genau einen Schreiber; ohne busy_timeout wirft ein zweiter
# gleichzeitiger Schreibversuch sofort SQLITE_BUSY statt kurz zu warten.
# 2000ms = derselbe Wert, mit dem knowledge_recall_hook.py seine RO-Verbindung
# oeffnet (dort als timeout=2.0) -- lang genug fuer einen normalen Schreibvorgang
# eines anderen Prozesses, kurz genug, dass ein Hook nicht spuerbar haengt.
BUSY_TIMEOUT_MS = 2000

# Prozessuebergreifende Schreibsperre (Auftrag 2026-08-08 Punkt 3: mehrere
# gleichzeitige knowledge_mcp_server-Prozesse kollidierten in SQLite mit
# "database is locked", weil busy_timeout=2000ms bei echtem Gedraenge nicht
# reicht und SQLites eigener Busy-Retry nicht fair/FIFO ist). Sitzt als
# Datei-Lock NEBEN der DB (eigene .lock-Datei, DB_PATH selbst bleibt
# unangetastet), damit Schreiber sich auf Betriebssystemebene stauen statt
# in SQLite zu kollidieren. Pfad wird in _write_lock() bei jedem Aufruf NEU
# aus DB_PATH gebildet (nicht hier fest verdrahtet), damit ein Test, der
# DB_PATH per monkeypatch auf eine tmp-DB umbiegt, automatisch auch die
# passende Lock-Datei bekommt.
_WRITE_LOCK_TIMEOUT_S = 10.0  # ponytail: harte Obergrenze -- danach ehrlicher
                              # Fehler statt endlosem Haengen (Abnahme-Punkt
                              # "scheitert EHRLICH"), kein globaler Dienst/keine
                              # Warteschlange noetig fuer dieses eine Problem.
RELATION_TYPES = {
    "references", "supersedes", "interprets", "implements", "contradicts",
    "supports", "derived_from", "cites", "evaluates_with", "constrains",
    "produces", "requires", "replaces_component", "analogous_to", "feeds_into",
}
# "rejected" (Auftrag 2026-08-06, Mangel: Ablehnungen wurden dem Aufrufer
# gemeldet, aber nie protokolliert -- completed 1349 / started 212 / rejected
# 0 trotz mehrerer Ablehnungen taeglich). Jeder frueh scheiternde
# Eingabe-Check ruft log_access(..., status="rejected", query=<GRUND>) auf,
# bevor er zurueckkehrt. GRUND ist eine feste, kurze Kategorie (z.B.
# "source_fehlt", "knoten_nicht_gefunden") -- nicht der volle, variable
# Fehlertext, sonst gruppiert 'wie oft wegen X abgelehnt' nicht sauber.
# Wiederverwendung der bestehenden query-Spalte statt neuer Spalte: sie
# bedeutet bei anderen Actions etwas anderes (Suchtext, Relation-ID), das
# stoert nicht, weil jede Auswertung ohnehin auf status='rejected'
# einschraenkt. Optimistic-Concurrency-Konflikte (verlorenes Update) bleiben
# bewusst status="failed", nicht "rejected": kein ungueltiger Input, sondern
# ein Wettlauf, der einen Retry verlangt -- andere Kategorie, siehe
# knowledge_update.
EVENT_STATUSES = {"started", "completed", "failed", "rejected"}
# Anlass (Auftrag 2026-08-06): was hat den Eintrag ausgeloest. 'selbst' und
# 'betreiber' sind SELBSTBERICHTET vom aufrufenden Modell -- nur so gut wie
# der Schreiber, die DB kann sie nicht nachpruefen. 'hook' und 'skript' sind
# dagegen objektiv, weil der Aufrufweg sie kennt (siehe knowledge_capture_hook.py:
# der Stop-Hook ruft lesson_record/knowledge_add NICHT selbst auf, er zwingt nur
# das Modell via decision:block zum /learn-Skill, das dann wie jeder normale
# Aufruf tool-seitig entscheidet -- 'hook' ist deshalb auch dort nur so
# verlässlich wie der Skill-Prompt, der es setzt, kein von aussen erzwungener
# Wert). 'unbekannt' ist Vorgabe und deckt den gesamten Altbestand vor diesem
# Feld ab. Wer die Verteilung auswertet (knowledge_stats), darf die vier
# Werte nicht gleich behandeln.
ALLOWED_ANLASS = {"selbst", "betreiber", "hook", "skript", "unbekannt"}
# lesson_record.type nahm bisher JEDEN String klaglos an (nur im JSON-Schema
# als enum dokumentiert, nie serverseitig geprueft) -- Auftrag 2026-08-07.
ALLOWED_LESSON_TYPES = {"error", "insight", "pattern", "antipattern"}
# Rueckfuellwert fuer Bestandszeilen ohne source (Auftrag 2026-08-06, siehe
# _ensure_node_constraint_triggers/migrate_source_constraints.py). Testdaten,
# Umschreiben erlaubt -- deshalb Nachtrag statt "Regel gilt nur fuer Neues".
SOURCE_BACKFILL_PLACEHOLDER = "unbekannt (Altbestand vor Migration 2026-08-06, nachgetragen)"
# Sechs Trigger, die die drei DB-Zusicherungen an knowledge_nodes tragen
# (source nicht leer, parent_path zeigt auf vorhandenen Knoten oder '/',
# anlass aus ALLOWED_ANLASS) -- identischer Text wie in schema.sql, dort
# fuer frisch angelegte Dateien, hier als Nachzug fuer Bestands-DBs. Zwei
# Kopien statt gemeinsamer Quelle, gleiches Muster wie jede andere additive
# Migration in diesem Server (z.B. _ensure_anlass_columns neben dem
# anlass-Block in schema.sql).
# Werte-Schranke fuer lessons_learned.freigabe -- woertlich wie in schema.sql,
# dort fuer frisch angelegte Dateien, hier als Nachzug fuer Bestands-DBs.
# Zwei Kopien statt gemeinsamer Quelle, gleiches Muster wie beim Block darunter.
LESSON_FREIGABE_TRIGGERS_SQL = """
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
"""

NODE_CONSTRAINT_TRIGGERS_SQL = """
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
"""
# norm_entscheidung (Auftrag 2026-08-08): "offen" heisst nie entschieden --
# deckt AUSSCHLIESSLICH den Altbestand ab (durch ALTER TABLE ... DEFAULT
# 'offen' beim Nachzug befuellt, siehe _ensure_norm_entscheidung_column, NIE
# durch einen Trigger). Die drei anderen Werte sind ausdrueckliche
# Entscheidungen -- siehe Spaltenkommentar in schema.sql fuer die volle
# Begruendung, inklusive der vier Loecher, die ein unabhaengiges Review
# (Agent acf807ee8e6756f27, 2026-08-08) VOR der Live-Migration fand und die
# hier bereits geschlossen sind (identischer Text wie schema.sql, gleiches
# Zwei-Kopien-Muster wie NODE_CONSTRAINT_TRIGGERS_SQL oben).
# Wertebereich der Gattung -- EINE Quelle fuer Schema, Vorabpruefung und den
# Trigger knowledge_nodes_gattung_check_bi. Laufen sie auseinander, weist die
# Datenbank etwas ab, das das Werkzeugschema erlaubt hat (L-636a44).
ALLOWED_GATTUNG = ("arbeitsbestand", "nachschlagewerk")

ALLOWED_NORM_ENTSCHEIDUNG = {"keine_norm", "norm_befristet", "norm_unbefristet"}
NORM_ENTSCHEIDUNG_TRIGGERS_SQL = """
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
"""
# Auditkette ueber access_log (Auftrag 2026-08-06). Gleiche Laenge/Form wie
# ein SHA-256-Hexdigest, damit ein Genesis-Wert nicht wie ein "kaputter"
# Hash aussieht. Fachtrennung zu einer gleichnamigen Konstante in einer
# anderen App (dortige Hashkette, eigene Implementierung) bewusst: eigener
# Store, eigene Konstante.
GENESIS_KETTEN_HASH = "0" * 64


def now_iso() -> str:
    # echter Versatz statt fest "+01:00" -- isoformat() liefert bereits
    # Doppelpunkt-Form ("+02:00"), DST-Wechsel automatisch via zoneinfo.
    return datetime.now(BERLIN).isoformat(timespec="seconds")


@contextmanager
def _write_lock():
    """Prozessuebergreifende Dateisperre um EINEN kompletten tools/call
    (Auftrag 2026-08-08 Punkt 3). Sitzt bewusst in handle_request() um den
    gesamten Werkzeugaufruf, NICHT in get_db() oder an jedem der ueber zwei
    Dutzend get_db()-Aufrufer: ein Lock, dessen Freigabe an conn.close()
    haengt, bliebe bei jeder ungefangenen Exception zwischen get_db() und
    close() fuer den Rest der Prozesslaufzeit haengen -- kein finally an
    jeder Stelle einzeln nachtraeglich verifizierbar. Hier deckt EIN
    try/finally jeden tools/call-Pfad ab, garantiert freigegeben, egal was
    der Handler tut.

    ponytail: sperrt auch reine Lesewerkzeuge mit statt Lese-/Schreibpfade
    einzeln zu klassifizieren -- fast jedes Werkzeug schreibt ohnehin
    mindestens einen access_log-Eintrag (siehe log_access()), eine Trennung
    haette 26 Aufrufstellen einzeln durchgehen muessen fuer keinen belegten
    Gewinn. Aufwertung (nur Schreibwerkzeuge sperren) moeglich, wenn Lesetempo
    unter vielen Prozessen je gemessen zum Problem wird.

    Wachsende Wartezeit (50ms verdoppelt bis 500ms Deckel), harte
    Gesamt-Obergrenze _WRITE_LOCK_TIMEOUT_S -- danach RuntimeError statt
    endlosem Haengen; handle_request() faengt das wie jeden anderen
    Handler-Fehler und meldet es dem Aufrufer.

    Alt neben neu: ein Prozess mit altem Code (ohne _write_lock) nimmt diese
    Datei nie in den Mund und schreibt weiterhin direkt per busy_timeout
    (siehe get_db()) -- er wird weder ausgesperrt noch sperrt er selbst
    jemanden aus, flock() ist rein advisory zwischen Prozessen, die es
    beide anfordern."""
    lock_path = DB_PATH.parent / f"{DB_PATH.name}.lock"
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        delay = 0.05
        waited = 0.0
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if waited >= _WRITE_LOCK_TIMEOUT_S:
                    raise RuntimeError(
                        f"Schreibsperre {lock_path.name} nach {_WRITE_LOCK_TIMEOUT_S}s "
                        "nicht erhalten -- ein anderer Prozess haelt sie laenger als erwartet. "
                        "Abgebrochen, nichts geschrieben."
                    )
                time.sleep(delay)
                waited += delay
                delay = min(delay * 2, 0.5)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    return conn


def _ensure_anlass_columns(conn: sqlite3.Connection) -> None:
    """Nachzug fuer Bestands-DBs ohne die Spalte anlass (Auftrag 2026-08-06,
    Befund: schreibpruefstand.db hatte schema.sql, aber keinen Migrationslauf
    -- knowledge_add/lesson_record brachen mit rohem sqlite3.OperationalError
    '<table> has no column named anlass' ab). PRAGMA table_info ist reine
    Metadaten-Abfrage (kein Tabellen-Scan), kostet also im Normalfall (Spalte
    vorhanden) nur Mikrosekunden pro Verbindung -- gemessen in
    tests/test_anlass_schema_backfill.py. Tabellen, die es (noch) gar nicht
    gibt (z.B. eine minimale Legacy-Testfixture ohne lessons_learned), werden
    uebersprungen statt einen ALTER-Fehlschlag zu produzieren.

    Entscheidung automatisch statt nur melden: gleiches Muster wie der
    bestehende access_log-Nachzug direkt darunter in dieser Funktion, additiv
    (ALTER TABLE ADD COLUMN, NOT NULL DEFAULT 'unbekannt' -- SQLite befuellt
    Bestandszeilen beim ALTER selbst, kein separater Ruckfuell-Schritt, siehe
    migrate_anlass.py). Anders als der access_log-Nachzug (der ohne Sicherung
    auf frueher schon additiv gewachsenen Spalten laeuft) wird hier vorher
    ein WAL-Checkpoint plus Dateisicherung erzwungen (Lehre L-218f1e: ein
    reiner shutil.copy2 im WAL-Betrieb kann committete, aber noch nicht
    zurueckgeschriebene Zeilen verlieren). Schlaegt der Checkpoint fehl (ein
    anderer Prozess schreibt gerade), wird NICHT stumm weiter-ALTERt --
    sprechender Fehler statt der rohen sqlite3-Ausnahme, mit dem Hinweis auf
    den manuellen Nachzug via migrate_anlass.py --apply."""
    existing_tables = {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    missing = {
        table for table in ("knowledge_nodes", "lessons_learned")
        if table in existing_tables
        and "anlass" not in {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    }
    if not missing:
        return

    busy, log_frames, checkpointed = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    if busy:
        raise RuntimeError(
            f"Spalte 'anlass' fehlt in {sorted(missing)}, aber die Sicherung vor dem "
            f"automatischen Nachzug ist blockiert (WAL-Checkpoint busy={busy}, "
            f"{log_frames} Frames, {checkpointed} checkpointed) -- vermutlich schreibt "
            "gerade ein anderer Prozess auf dieselbe Datenbank. Nachzug abgebrochen, "
            "nichts geaendert. Von Hand nachholen: "
            "'.venv/bin/python shared-knowledge/migrate_anlass.py --apply'."
        )
    if DB_PATH.exists():
        stamp = datetime.now(BERLIN).strftime("%Y%m%dT%H%M%S")
        backup_path = DB_PATH.parent / f"{DB_PATH.name}.bak-{stamp}"
        shutil.copy2(DB_PATH, backup_path)

    for table in missing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN anlass TEXT NOT NULL DEFAULT 'unbekannt'")


def _ensure_abgeleitet_von_column(conn: sqlite3.Connection) -> None:
    """Nachzug fuer Bestands-DBs ohne die Spalte abgeleitet_von (Auftrag
    2026-08-06, ADR-027 Nachtrag 4). Gleiches Muster wie
    _ensure_anlass_columns direkt darueber: additiv, NULL-faehig, kein
    Rueckfuell-Schritt noetig (NULL ist der unveraenderte Normalfall), aber
    trotzdem WAL-Checkpoint + Sicherungskopie VOR dem ALTER (Lehre L-218f1e)."""
    if "knowledge_nodes" not in {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }:
        return
    if "abgeleitet_von" in {row[1] for row in conn.execute("PRAGMA table_info(knowledge_nodes)")}:
        return

    busy, log_frames, checkpointed = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    if busy:
        raise RuntimeError(
            f"Spalte 'abgeleitet_von' fehlt, aber die Sicherung vor dem automatischen "
            f"Nachzug ist blockiert (WAL-Checkpoint busy={busy}, {log_frames} Frames, "
            f"{checkpointed} checkpointed) -- vermutlich schreibt gerade ein anderer "
            "Prozess auf dieselbe Datenbank. Nachzug abgebrochen, nichts geaendert. "
            "Von Hand nachholen: '.venv/bin/python shared-knowledge/migrate_ableitung.py --apply'."
        )
    if DB_PATH.exists():
        stamp = datetime.now(BERLIN).strftime("%Y%m%dT%H%M%S")
        backup_path = DB_PATH.parent / f"{DB_PATH.name}.bak-{stamp}"
        shutil.copy2(DB_PATH, backup_path)

    conn.execute("ALTER TABLE knowledge_nodes ADD COLUMN abgeleitet_von TEXT")


def _ensure_norm_art_column(conn: sqlite3.Connection) -> None:
    """Nachzug fuer Bestands-DBs ohne die Spalte norm_art (Auftrag
    2026-08-07/08, Knoten dd367fd1: zweite, von norm_rang unabhaengige Achse
    -- Sein/Sollen/Duerfen). Gleiches Muster wie _ensure_abgeleitet_von_column
    direkt darueber: additiv, NULL-faehig, kein Rueckfuell-Schritt (Altbestand
    bleibt ausnahmslos NULL -- Art wird nie geraten, nur explizit gesetzt),
    aber trotzdem WAL-Checkpoint + Sicherungskopie VOR dem ALTER (Lehre
    L-218f1e)."""
    if "knowledge_nodes" not in {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }:
        return
    if "norm_art" in {row[1] for row in conn.execute("PRAGMA table_info(knowledge_nodes)")}:
        return

    busy, log_frames, checkpointed = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    if busy:
        raise RuntimeError(
            f"Spalte 'norm_art' fehlt, aber die Sicherung vor dem automatischen "
            f"Nachzug ist blockiert (WAL-Checkpoint busy={busy}, {log_frames} Frames, "
            f"{checkpointed} checkpointed) -- vermutlich schreibt gerade ein anderer "
            "Prozess auf dieselbe Datenbank. Nachzug abgebrochen, nichts geaendert."
        )
    if DB_PATH.exists():
        stamp = datetime.now(BERLIN).strftime("%Y%m%dT%H%M%S")
        backup_path = DB_PATH.parent / f"{DB_PATH.name}.bak-{stamp}"
        shutil.copy2(DB_PATH, backup_path)

    conn.execute("ALTER TABLE knowledge_nodes ADD COLUMN norm_art TEXT")


def _ensure_norm_entscheidung_column(conn: sqlite3.Connection) -> None:
    """Nachzug fuer Bestands-DBs ohne die Spalte norm_entscheidung (Auftrag
    2026-08-08). Gleiches Muster wie _ensure_anlass_columns: additiv, NOT
    NULL DEFAULT 'offen' -- SQLite befuellt Bestandszeilen beim ALTER selbst
    mit 'offen' (kein separater Rueckfuell-Schritt), und genau das ist
    gewollt: 'offen' heisst "nie entschieden", exakt der Zustand des
    gesamten Altbestands vor diesem Feld (Auftrag Punkt 2 -- nicht raten).
    WAL-Checkpoint + Sicherungskopie VOR dem ALTER (Lehre L-218f1e)."""
    if "knowledge_nodes" not in {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }:
        return
    if "norm_entscheidung" in {row[1] for row in conn.execute("PRAGMA table_info(knowledge_nodes)")}:
        return

    busy, log_frames, checkpointed = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    if busy:
        raise RuntimeError(
            f"Spalte 'norm_entscheidung' fehlt, aber die Sicherung vor dem automatischen "
            f"Nachzug ist blockiert (WAL-Checkpoint busy={busy}, {log_frames} Frames, "
            f"{checkpointed} checkpointed) -- vermutlich schreibt gerade ein anderer "
            "Prozess auf dieselbe Datenbank. Nachzug abgebrochen, nichts geaendert."
        )
    if DB_PATH.exists():
        stamp = datetime.now(BERLIN).strftime("%Y%m%dT%H%M%S")
        backup_path = DB_PATH.parent / f"{DB_PATH.name}.bak-{stamp}"
        shutil.copy2(DB_PATH, backup_path)

    conn.execute("ALTER TABLE knowledge_nodes ADD COLUMN norm_entscheidung TEXT NOT NULL DEFAULT 'offen'")


_NORM_ENTSCHIEDEN_COLUMNS = {
    "norm_entschieden_von": "TEXT",
    "norm_entschieden_am": "TEXT",
    "norm_entschieden_grund": "TEXT",
}


def _ensure_norm_entschieden_columns(conn: sqlite3.Connection) -> None:
    """Nachzug fuer Bestands-DBs ohne die drei Entscheider-Spalten (Nachtrag
    2026-08-08, Betreiber-Nachfrage "wer hat entschieden?"). Gleiches Muster
    wie _ensure_zuruecknahme_columns direkt darueber: additiv, NULL-faehig
    (kein Rueckfuellwert -- Altbestand auf 'offen' hat KEINEN Entscheider,
    das ist korrekt, nicht erfunden), WAL-Checkpoint + Sicherungskopie VOR
    dem ALTER (Lehre L-218f1e)."""
    if "knowledge_nodes" not in {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }:
        return
    existing = {row[1] for row in conn.execute("PRAGMA table_info(knowledge_nodes)")}
    missing = set(_NORM_ENTSCHIEDEN_COLUMNS) - existing
    if not missing:
        return

    busy, log_frames, checkpointed = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    if busy:
        raise RuntimeError(
            f"Spalten {sorted(missing)} fehlen an knowledge_nodes, aber die Sicherung vor "
            f"dem automatischen Nachzug ist blockiert (WAL-Checkpoint busy={busy}, "
            f"{log_frames} Frames, {checkpointed} checkpointed) -- vermutlich schreibt "
            "gerade ein anderer Prozess auf dieselbe Datenbank. Nachzug abgebrochen, nichts geaendert."
        )
    if DB_PATH.exists():
        stamp = datetime.now(BERLIN).strftime("%Y%m%dT%H%M%S")
        backup_path = DB_PATH.parent / f"{DB_PATH.name}.bak-{stamp}"
        shutil.copy2(DB_PATH, backup_path)

    for name in missing:
        conn.execute(f"ALTER TABLE knowledge_nodes ADD COLUMN {name} {_NORM_ENTSCHIEDEN_COLUMNS[name]}")


def _ensure_norm_entscheidung_triggers(conn: sqlite3.Connection) -> None:
    """Nachzug fuer Bestands-DBs ohne die 13 norm_entscheidung-Trigger
    (Auftrag 2026-08-08, vier davon aus dem unabhaengigen Review vom selben
    Tag). Anders als _ensure_node_constraint_triggers braucht es hier KEINEN
    Daten-Backfill vor der Trigger-Erzeugung: die Spalte kommt bereits mit
    'offen' befuellt aus _ensure_norm_entscheidung_column, und die
    Pflicht-/Konsistenz-Trigger greifen ausschliesslich auf Zeilen, deren
    norm_entscheidung NICHT 'offen' ist bzw. auf den UEBERGANG weg von
    'offen' (siehe Kommentar an NORM_ENTSCHEIDUNG_TRIGGERS_SQL) -- Altbestand
    bleibt beim Nachziehen unberuehrt."""
    if "knowledge_nodes" not in {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }:
        return
    node_columns = {row[1] for row in conn.execute("PRAGMA table_info(knowledge_nodes)")}
    if not {"norm_entscheidung", "norm_entschieden_von", "norm_entschieden_grund"} <= node_columns:
        return  # Spalten fehlen noch (sollte durch die Aufrufreihenfolge in ensure_schema nicht vorkommen)
    existing_triggers = {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
    }
    needed = {
        "knowledge_nodes_norm_entscheidung_check_bi", "knowledge_nodes_norm_entscheidung_check_bu",
        "knowledge_nodes_norm_entscheidung_pflicht_bi", "knowledge_nodes_norm_entscheidung_pflicht_bu",
        "knowledge_nodes_norm_entscheidung_rang_neu_bu",
        "knowledge_nodes_norm_entscheidung_wer_bi", "knowledge_nodes_norm_entscheidung_wer_bu",
        "knowledge_nodes_norm_entscheidung_rang_bi", "knowledge_nodes_norm_entscheidung_rang_bu",
        "knowledge_nodes_norm_rang_gilt_ab_bi", "knowledge_nodes_norm_rang_gilt_ab_bu",
        "knowledge_nodes_norm_entscheidung_gilt_bis_bi", "knowledge_nodes_norm_entscheidung_gilt_bis_bu",
        "knowledge_nodes_gilt_bis_vor_gilt_ab_bi", "knowledge_nodes_gilt_bis_vor_gilt_ab_bu",
    }
    if needed <= existing_triggers:
        return

    busy, log_frames, checkpointed = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    if busy:
        raise RuntimeError(
            f"norm_entscheidung-Trigger an knowledge_nodes fehlen, aber die Sicherung vor dem "
            f"automatischen Nachzug ist blockiert (WAL-Checkpoint busy={busy}, "
            f"{log_frames} Frames, {checkpointed} checkpointed) -- vermutlich schreibt "
            "gerade ein anderer Prozess auf dieselbe Datenbank. Nachzug abgebrochen, nichts geaendert."
        )
    if DB_PATH.exists():
        stamp = datetime.now(BERLIN).strftime("%Y%m%dT%H%M%S")
        backup_path = DB_PATH.parent / f"{DB_PATH.name}.bak-{stamp}"
        shutil.copy2(DB_PATH, backup_path)

    conn.executescript(NORM_ENTSCHEIDUNG_TRIGGERS_SQL)


_ZURUECKNAHME_COLUMNS = {
    "zurueckgezogen": "INTEGER NOT NULL DEFAULT 0",
    "zurueckgezogen_grund": "TEXT",
    "zurueckgezogen_am": "TEXT",
    "zurueckgezogen_von": "TEXT",
}


def _ensure_zuruecknahme_columns(conn: sqlite3.Connection) -> None:
    """Nachzug fuer Bestands-DBs ohne die vier Zuruecknahme-Spalten (Auftrag
    2026-08-06, Luecke "kein Loeschweg fuer die KI"). Gleiches Muster wie
    _ensure_abgeleitet_von_column direkt darueber: additiv, WAL-Checkpoint +
    Sicherungskopie VOR dem ALTER (Lehre L-218f1e). zurueckgezogen bekommt
    NOT NULL DEFAULT 0 -- SQLite befuellt Bestandszeilen beim ALTER selbst,
    kein separater Rueckfuell-Schritt (Manueller/CI-Weg fuer Abnahme-Belege:
    migrate_zuruecknahme.py)."""
    if "knowledge_nodes" not in {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }:
        return
    existing = {row[1] for row in conn.execute("PRAGMA table_info(knowledge_nodes)")}
    missing = set(_ZURUECKNAHME_COLUMNS) - existing
    if not missing:
        return

    busy, log_frames, checkpointed = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    if busy:
        raise RuntimeError(
            f"Spalten {sorted(missing)} fehlen an knowledge_nodes, aber die Sicherung vor "
            f"dem automatischen Nachzug ist blockiert (WAL-Checkpoint busy={busy}, "
            f"{log_frames} Frames, {checkpointed} checkpointed) -- vermutlich schreibt "
            "gerade ein anderer Prozess auf dieselbe Datenbank. Nachzug abgebrochen, "
            "nichts geaendert. Von Hand nachholen: "
            "'.venv/bin/python shared-knowledge/migrate_zuruecknahme.py --apply'."
        )
    if DB_PATH.exists():
        stamp = datetime.now(BERLIN).strftime("%Y%m%dT%H%M%S")
        backup_path = DB_PATH.parent / f"{DB_PATH.name}.bak-{stamp}"
        shutil.copy2(DB_PATH, backup_path)

    for name in missing:
        conn.execute(f"ALTER TABLE knowledge_nodes ADD COLUMN {name} {_ZURUECKNAHME_COLUMNS[name]}")


_SCHREIBER_COLUMNS = {"actor", "session", "model", "client"}


def _ensure_schreiber_columns(conn: sqlite3.Connection) -> None:
    """Nachzug fuer Bestands-DBs ohne actor/session/model auf knowledge_nodes
    UND lessons_learned (Auftrag 2026-08-06, Mangel: access_log allein reicht
    nicht, der Schreiber muss auch am Datensatz stehen -- model kam als
    Nachtrag desselben Auftrags dazu, gleiche Machart). Gleiches Muster wie
    _ensure_zuruecknahme_columns direkt darueber: additiv, NULL-faehig (kein
    Rueckfuellwert fuer Altbestand -- 'unbekannt' waere hier erfunden, anders
    als bei anlass, das von Anfang an einen Vorgabewert hatte), WAL-Checkpoint
    + Sicherungskopie VOR dem ALTER (Lehre L-218f1e). Beide Tabellen in einem
    Nachzug, weil beide vom selben Mangel betroffen sind und ein einzelner
    Checkpoint/Backup fuer beide reicht."""
    tables_present = {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    missing_by_table = {}
    for table in ("knowledge_nodes", "lessons_learned"):
        if table not in tables_present:
            continue
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        missing = _SCHREIBER_COLUMNS - existing
        if missing:
            missing_by_table[table] = missing
    if not missing_by_table:
        return

    busy, log_frames, checkpointed = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    if busy:
        raise RuntimeError(
            f"Spalten actor/session/model/client fehlen an {sorted(missing_by_table)}, aber die Sicherung "
            f"vor dem automatischen Nachzug ist blockiert (WAL-Checkpoint busy={busy}, "
            f"{log_frames} Frames, {checkpointed} checkpointed) -- vermutlich schreibt "
            "gerade ein anderer Prozess auf dieselbe Datenbank. Nachzug abgebrochen, "
            "nichts geaendert. Von Hand nachholen: "
            "'.venv/bin/python shared-knowledge/migrate_schreiber.py --apply'."
        )
    if DB_PATH.exists():
        stamp = datetime.now(BERLIN).strftime("%Y%m%dT%H%M%S")
        backup_path = DB_PATH.parent / f"{DB_PATH.name}.bak-{stamp}"
        shutil.copy2(DB_PATH, backup_path)

    for table, missing in missing_by_table.items():
        for name in missing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} TEXT")


def _ensure_node_constraint_triggers(conn: sqlite3.Connection) -> None:
    """Nachzug fuer Bestands-DBs ohne die sechs Zusicherungs-Trigger an
    knowledge_nodes (Auftrag 2026-08-06). Gleiches Muster wie
    _ensure_anlass_columns direkt darueber: WAL-Checkpoint + Sicherungskopie
    VOR jeder Aenderung (Lehre L-218f1e), Abbruch mit sprechendem Fehler
    statt stillem Weiterlaufen wenn der Checkpoint blockiert ist. Anders als
    dort aendert dieser Nachzug zusaetzlich Daten (Rueckfuellung leerer
    source-Werte auf SOURCE_BACKFILL_PLACEHOLDER) -- Testdaten, Umschreiben
    erlaubt (Betreiber-Direktive), deshalb Nachtrag statt Bestandszeilen
    dauerhaft von der Regel auszunehmen. Backfill laeuft VOR der
    Trigger-Erzeugung, sonst wuerde z.B. das access_count-Increment in
    knowledge_read jede betroffene Bestandszeile sperren, bis jemand ihren
    source-Wert von Hand nachtraegt."""
    if "knowledge_nodes" not in {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }:
        return  # minimale Testfixture ohne die Tabelle -- nichts zu sichern
    node_columns = {row[1] for row in conn.execute("PRAGMA table_info(knowledge_nodes)")}
    if not {"source", "parent_path", "anlass"} <= node_columns:
        return  # minimale Legacy-Testfixture ohne diese Spalten (z.B.
        # migrate_relations.py-Selbsttest) -- die Trigger brauchen alle drei,
        # eine echte Bestands-DB hat source/parent_path seit jeher und
        # anlass spaetestens nach _ensure_anlass_columns() oben
    existing_triggers = {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
    }
    needed = {
        "knowledge_nodes_source_check_bi", "knowledge_nodes_source_check_bu",
        "knowledge_nodes_parent_check_bi", "knowledge_nodes_parent_check_bu",
        "knowledge_nodes_anlass_check_bi", "knowledge_nodes_anlass_check_bu",
    }
    # Nachtrag 2026-08-06 (_ensure_core_schema): schema.sql legt diese sechs
    # Trigger seit diesem Auftrag selbst per CREATE TRIGGER IF NOT EXISTS an,
    # deshalb existieren sie auf JEDER DB schon, BEVOR dieser Nachzug hier
    # laeuft -- "Trigger vorhanden" ist seither kein Beleg mehr dafuer, dass
    # der Backfill schon einmal lief. Ohne die zweite Bedingung wuerde der
    # Nachzug hier fuer jede Bestands-DB sofort zurueckkehren und Zeilen mit
    # leerem source dauerhaft leer lassen, obwohl die (jetzt aktiven)
    # Trigger genau das ab dem naechsten Schreibzugriff auf diese Zeile
    # verhindern wuerden.
    unbackfilled = conn.execute(
        "SELECT COUNT(*) FROM knowledge_nodes WHERE source IS NULL OR TRIM(source) = ''"
    ).fetchone()[0]
    if needed <= existing_triggers and unbackfilled == 0:
        return

    busy, log_frames, checkpointed = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    if busy:
        raise RuntimeError(
            f"Zusicherungs-Trigger an knowledge_nodes fehlen, aber die Sicherung vor dem "
            f"automatischen Nachzug ist blockiert (WAL-Checkpoint busy={busy}, "
            f"{log_frames} Frames, {checkpointed} checkpointed) -- vermutlich schreibt "
            "gerade ein anderer Prozess auf dieselbe Datenbank. Nachzug abgebrochen, "
            "nichts geaendert. Von Hand nachholen: "
            "'.venv/bin/python shared-knowledge/migrate_source_constraints.py --apply'."
        )
    if DB_PATH.exists():
        stamp = datetime.now(BERLIN).strftime("%Y%m%dT%H%M%S")
        backup_path = DB_PATH.parent / f"{DB_PATH.name}.bak-{stamp}"
        shutil.copy2(DB_PATH, backup_path)

    # ENTSCHEIDUNG (Auftrag 2026-08-06, Nebenbefund Konfidenzverfall):
    # updated_at bleibt hier UNVERAENDERT, bewusst. konfidenz.py setzt voraus,
    # dass updated_at der Bezugszeitpunkt der letzten INHALTLICHEN Aenderung
    # oder Bestaetigung ist (siehe dortiger Modul-Docstring) -- der Verfall
    # rechnet das Alter seit genau diesem Zeitpunkt. Dieser Backfill traegt
    # nur einen technischen Platzhalter in eine leere Herkunftsangabe nach
    # (Migrationsfolge, nicht Wissenszuwachs); er bestaetigt nicht, dass der
    # Inhalt noch stimmt. Wuerde updated_at hier mitziehen, wuerde jede
    # betroffene Alt-Zeile beim naechsten ensure_schema()-Lauf kuenstlich
    # verjuengt, ohne dass irgendjemand den Inhalt geprueft haette -- die
    # Konfidenz spraenge auf den Ausgangswert zurueck, obwohl nichts an der
    # Aussage selbst neu bestaetigt wurde.
    conn.execute(
        "UPDATE knowledge_nodes SET source = ? WHERE source IS NULL OR TRIM(source) = ''",
        (SOURCE_BACKFILL_PLACEHOLDER,),
    )
    conn.executescript(NODE_CONSTRAINT_TRIGGERS_SQL)


# Dieselbe Umlaut-Faltung wie in schema.sql (Trigger lessons_ai/ad/au) und
# fold_de() -- als SQL-Ausdrucksvorlage, weil der Backfill unten row-weise
# GENAU das schreiben muss, was die Trigger ab jetzt bei jedem INSERT/UPDATE
# schreiben (nicht die Rohspalten). `INSERT INTO lessons_fts(lessons_fts)
# VALUES('rebuild')` waere hier die falsche, naheliegende Abkuerzung: das
# kopiert die Rohspalten aus lessons_learned und umgeht die Faltung komplett
# -- exakt der Fehler, den migrate_fts_trigram_fold.py fuer knowledge_fts
# bereits dokumentiert (siehe dortiger Kopfkommentar).
_LESSONS_FOLD_SQL = (
    "LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE({col},"
    "'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss'))"
)


def _ensure_lessons_fts_backfill(conn: sqlite3.Connection) -> None:
    """Nachzug fuer Lehren, die VOR den lessons_ai/ad/au-Triggern angelegt
    wurden (Auftrag 2026-08-07, Befund: knowledge_search fand 0 von 2
    einschlaegigen Lehren, obwohl die Lehren existierten -- 553 von 862
    Eintraegen sind Lehren, keiner davon durch einen Volltextindex
    erreichbar). schema.sql legt lessons_fts + die drei Trigger additiv an
    (_ensure_core_schema oben), aber Trigger feuern nur bei KUENFTIGEN
    Schreibvorgaengen -- der Bestand braucht einen einmaligen Nachtrag,
    gleiches Muster wie _ensure_node_constraint_triggers direkt darueber
    (WAL-Checkpoint + Sicherungskopie VOR jeder Aenderung, Lehre L-218f1e).

    Guard ist die fehlende Zeile selbst (NOT IN), nicht "Tabelle/Trigger
    vorhanden" -- aus genau dem am 2026-08-06 gefundenen Grund (siehe
    _ensure_node_constraint_triggers-Kommentar): schema.sql legt die leere
    lessons_fts-Tabelle sofort an, "existiert" waere also immer wahr und
    wuerde den Nachtrag fuer den Bestand nie ausloesen.

    ZWEI ROT-Befunde beim Bau dieser Funktion, hier festgehalten damit sie
    nicht wiederholt werden:

    1. "SELECT rowid FROM lessons_fts" ist als Nachzug-Guard NUTZLOS: bei
       einer externen Inhaltstabelle (content='lessons_learned') spiegelt
       COUNT(*)/rowid-Aufzaehlung auf der FTS5-Virtualtabelle OHNE MATCH die
       Zeilen der INHALTSTABELLE, nicht den tatsaechlichen invertierten
       Index -- gemessen: direkt nach CREATE VIRTUAL TABLE, VOR jedem
       INSERT, meldete "SELECT COUNT(*) FROM lessons_fts" bereits dieselbe
       Zeilenzahl wie lessons_learned, aber MATCH fand nichts. Der Guard
       muss stattdessen die FTS5-eigene Schatten-Tabelle <name>_docsize
       pruefen: die traegt NACHWEISLICH genau eine Zeile PRO tatsaechlich
       indizierter Zeile (nur durch echte INSERTs in die Virtualtabelle
       befuellt, nicht durch die Existenz der Inhaltstabelle).
    2. Nachgeordnet, erst nach Fix 1 sichtbar geworden: "INSERT INTO
       lessons_fts(...) SELECT ... FROM lessons_learned WHERE rowid NOT IN
       (SELECT rowid FROM lessons_fts)" -- Lesen UND Schreiben derselben
       Virtualtabelle in EINER Anweisung -- ist laut SQLite nicht
       spezifiziert, wenn eine Anweisung eine Tabelle gleichzeitig liest und
       schreibt. Fix: die fehlenden rowids ERST in eine Temp-Tabelle
       materialisieren (eigene, abgeschlossene Anweisung), dann in einer
       ZWEITEN Anweisung ueber die Temp-Tabelle joinen -- die schreibende
       Anweisung liest lessons_fts dann gar nicht mehr."""
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"lessons_learned", "lessons_fts", "lessons_fts_docsize"} <= tables:
        return  # minimale Testfixture ohne die Tabellen -- nichts nachzuziehen
    fehlend = conn.execute(
        "SELECT COUNT(*) FROM lessons_learned l WHERE l.rowid NOT IN (SELECT rowid FROM lessons_fts_docsize)"
    ).fetchone()[0]
    if fehlend == 0:
        return

    busy, log_frames, checkpointed = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    if busy:
        raise RuntimeError(
            f"{fehlend} Lehren fehlen noch im Volltextindex lessons_fts, aber die Sicherung vor "
            f"dem automatischen Nachzug ist blockiert (WAL-Checkpoint busy={busy}, "
            f"{log_frames} Frames, {checkpointed} checkpointed) -- vermutlich schreibt gerade ein "
            "anderer Prozess auf dieselbe Datenbank. Nachzug abgebrochen, nichts geaendert. "
            "Naechster ensure_schema()-Lauf versucht es erneut."
        )
    if DB_PATH.exists():
        stamp = datetime.now(BERLIN).strftime("%Y%m%dT%H%M%S")
        backup_path = DB_PATH.parent / f"{DB_PATH.name}.bak-{stamp}"
        shutil.copy2(DB_PATH, backup_path)

    conn.execute(
        "CREATE TEMP TABLE _lessons_fts_backfill_rowids AS "
        "SELECT rowid FROM lessons_learned WHERE rowid NOT IN (SELECT rowid FROM lessons_fts_docsize)"
    )
    fold_desc = _LESSONS_FOLD_SQL.format(col="l.description")
    fold_root = _LESSONS_FOLD_SQL.format(col="l.root_cause")
    fold_prev = _LESSONS_FOLD_SQL.format(col="l.prevention")
    conn.execute(
        f"INSERT INTO lessons_fts(rowid, description, root_cause, prevention) "
        f"SELECT l.rowid, {fold_desc}, {fold_root}, {fold_prev} "
        f"FROM lessons_learned l JOIN _lessons_fts_backfill_rowids m ON m.rowid = l.rowid"
    )
    conn.execute("DROP TABLE _lessons_fts_backfill_rowids")


def _ensure_core_schema(conn: sqlite3.Connection) -> None:
    """Legt fehlende Kerntabellen an (Auftrag 2026-08-06, Erstanlage-Luecke).

    Befund an fremdem Ort (leere DB): ensure_schema zog bisher nur Spalten
    nach (ALTER TABLE) und nahm an, dass die Kerntabellen schon existieren --
    stimmt nur fuer eine bereits gepflegte knowledge.db, nie fuer eine neue.
    Quelle ist schema.sql neben dieser Datei, nicht ein zweiter im Code
    nachgebauter Schemastand. Jede Anweisung dort steht unter IF NOT EXISTS,
    ein Lauf gegen eine vollstaendige DB aendert also nichts. Ausnahme siehe
    except-Zweig unten: knowledge_relations bleibt dort zusaetzlich
    dupliziert, als Rueckfallebene fuer eine bereits existierende, aber
    spaltenmaessig aeltere Kerntabelle (Migrationstest-Fixture), auf der
    schema.sql's Indizes/Trigger sonst hart abbrechen wuerden.
    """
    schema_path = Path(__file__).parent / "schema.sql"
    if not schema_path.exists():
        raise RuntimeError(
            f"schema.sql fehlt unter {schema_path} -- ohne sie kann "
            "ensure_schema die Kerntabellen (knowledge_nodes, lessons_learned, "
            "access_log, ...) nicht anlegen. Datei gehoert neben "
            "knowledge_mcp_server.py ins selbe Verzeichnis."
        )
    try:
        conn.executescript(schema_path.read_text(encoding="utf-8"))
    except sqlite3.OperationalError:
        # Kerntabelle existiert schon, aber in einer aelteren Spaltenform
        # (z.B. Migrationstest-Fixture ohne parent_path) -- schema.sql's
        # Indizes/Trigger auf fehlenden Spalten schlagen dann fehl. Die
        # additiven _ensure_*-Funktionen unten holen genau diese Spalten
        # fuer echte Bestands-DBs nach; hier nur das eigenstaendige,
        # spaltenunabhaengige knowledge_relations nachziehen (einzige Stelle
        # mit dieser Ausnahme, siehe Docstring oben).
        conn.executescript("""
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
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(source_path, target_path, relation_type),
                FOREIGN KEY(source_path) REFERENCES knowledge_nodes(path) ON UPDATE CASCADE ON DELETE CASCADE,
                FOREIGN KEY(target_path) REFERENCES knowledge_nodes(path) ON UPDATE CASCADE ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_relations_source ON knowledge_relations(source_path);
            CREATE INDEX IF NOT EXISTS idx_relations_target ON knowledge_relations(target_path);
            CREATE INDEX IF NOT EXISTS idx_relations_type ON knowledge_relations(relation_type);
        """)


def _ensure_herkunft_triggers(conn: sqlite3.Connection) -> None:
    """Spielt herkunft_unveraenderlich.sql ein (Befund 2026-08-08).

    Gemessen an einer Erstanlage am leeren Ort: 29 Trigger statt der 31 des
    Betriebs -- und die beiden fehlenden waren ausgerechnet
    knowledge_nodes_herkunft_bu und lessons_herkunft_bu. Wer brainlehr neu
    installierte, bekam es also ohne die Regel, die brainlehr AUSMACHT: dass
    Herkunft nachgetragen, aber nie umgeschrieben werden kann. Ursache war
    die Ablage -- die Regel stand in einer eigenen SQL-Datei, die von Hand
    eingespielt worden war und die ensure_schema nicht kannte.

    Die Datei ist idempotent (DROP TRIGGER IF EXISTS vor jedem CREATE), ein
    Lauf gegen eine vollstaendige Datenbank aendert also nichts. Fehlt sie,
    ist das ein harter Fehler und keine Warnung: eine Installation ohne
    diese Schranke sieht funktionsfaehig aus und ist es nicht.
    """
    # Erst nachsehen, dann schreiben: die Datei enthaelt DROP/CREATE TRIGGER,
    # also DDL — sie bedingungslos bei jedem get_db() auszufuehren macht aus
    # JEDER Verbindung einen Schreiber und damit aus jedem Lesezugriff einen
    # Kandidaten fuer "database is locked". Genau das ist am 2026-08-08
    # unmittelbar nach dem Einbau eingetreten, bei fuenf laufenden Servern.
    vorhanden = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND name IN "
        "('knowledge_nodes_herkunft_bu', 'lessons_herkunft_bu')")}
    if len(vorhanden) == 2:
        return

    pfad = Path(__file__).parent / "herkunft_unveraenderlich.sql"
    if not pfad.exists():
        raise RuntimeError(
            f"herkunft_unveraenderlich.sql fehlt unter {pfad} -- ohne sie "
            "entsteht eine Datenbank ohne Herkunftsschranke. Datei gehoert "
            "neben knowledge_mcp_server.py ins selbe Verzeichnis."
        )
    conn.executescript(pfad.read_text(encoding="utf-8"))


def _ensure_nachgezogene_spalten(conn: sqlite3.Connection) -> None:
    """Zwei Spalten, die per Migration in die Betriebsdatenbank kamen und in
    keiner Erstanlage ankamen (Befund 2026-08-08, Rundlauf brainlehr.py):

      lessons_learned.pruefstelle        Lehre zeigt auf ihre Pruefung
      knowledge_embeddings.text_checksum erkennt veraltete Vektoren

    Ohne sie bricht das Wiedereinlesen eines Auszugs an genau diesen Spalten
    ab -- 644 von 644 Lehren abgewiesen, gemessen. Dieselbe Fehlerklasse wie
    die fehlenden Herkunfts-Trigger: eine Regel oder Spalte, die nur die
    gewachsene Datenbank kennt, ist keine Eigenschaft des Systems."""
    for tabelle, spalte, typ in (("lessons_learned", "pruefstelle", "TEXT"),
                                 ("knowledge_embeddings", "text_checksum", "TEXT")):
        vorhanden = {r[1] for r in conn.execute(f"PRAGMA table_info({tabelle})")}
        if spalte not in vorhanden:
            conn.execute(f"ALTER TABLE {tabelle} ADD COLUMN {spalte} {typ}")


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Idempotent additive migration for old knowledge.db copies."""
    _ensure_core_schema(conn)
    # Generischer Nachzug VOR allen Trigger-Anlegern: ein Trigger, der eine
    # noch fehlende Spalte liest, laesst jeden spaeteren Schreibvorgang mit
    # 'no such column: NEW.x' auffliegen. Genau so lag es am 2026-08-10 bei
    # freigabe und gattung. Die einzelnen _ensure_*-Funktionen darunter
    # bleiben: sie tragen Sicherung und WAL-Checkpoint, die dieser Nachzug
    # bewusst nicht nachbaut -- er ergaenzt nur, was sonst niemand nennt.
    schema_nachzug.nachziehen(conn, db_path=DB_PATH)
    _ensure_herkunft_triggers(conn)
    _ensure_nachgezogene_spalten(conn)
    _ensure_anlass_columns(conn)
    _ensure_abgeleitet_von_column(conn)
    _ensure_norm_art_column(conn)
    _ensure_norm_entscheidung_column(conn)
    _ensure_norm_entschieden_columns(conn)
    _ensure_norm_entscheidung_triggers(conn)
    _ensure_zuruecknahme_columns(conn)
    _ensure_schreiber_columns(conn)
    _ensure_node_constraint_triggers(conn)
    _ensure_lessons_fts_backfill(conn)
    _ensure_lessons_freigabe_column(conn)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(access_log)")}
    for name, declaration in {
        "actor": "TEXT", "model": "TEXT", "session": "TEXT", "client": "TEXT",
        "status": "TEXT DEFAULT 'completed'",
        "zeilen_hash": "TEXT", "ketten_hash": "TEXT",
    }.items():
        if name not in columns:
            conn.execute(f"ALTER TABLE access_log ADD COLUMN {name} {declaration}")
    # dim (Auftrag 2026-08-07, Modellwechsel bge-m3): additive Nachfuehrung fuer
    # Bestands-DBs, deren knowledge_embeddings noch vor dieser Spalte angelegt
    # wurde. Nullable, keine Sicherung/Checkpoint noetig (kein Datenverlust
    # moeglich, reines Anhaengen einer leeren Spalte).
    existing_tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "knowledge_embeddings" in existing_tables:
        emb_columns = {row[1] for row in conn.execute("PRAGMA table_info(knowledge_embeddings)")}
        if "dim" not in emb_columns:
            conn.execute("ALTER TABLE knowledge_embeddings ADD COLUMN dim INTEGER")
    conn.commit()


def _ensure_lessons_freigabe_column(conn) -> None:
    """freigabe an lessons_learned nachziehen (B4.5-Nachtrag, 2026-08-10).

    Der Koederlauf zeigte: ein Gast (Bezug 'published') sah 5 von 10 Treffern,
    allesamt Lehren -- lessons_learned trug die Spalte nicht, weil
    migrate_freigabe.py nur ueber knowledge_nodes ging. Der Filter sperrt sie
    seither pauschal, was richtig, aber grob ist: KEINE Lehre kann dann je
    freigegeben werden.

    Additiv und hier statt nur im Migrationsskript -- genau die Lehre L-7e0823:
    dieselbe Spalte wurde damals per Skript nachgezogen, aber nicht in
    ensure_schema(), und eine DB mit schema.sql ohne Migrationslauf brach im
    normalen Schreibpfad mit einem rohen sqlite3-Fehler ab. Beide Wege im
    selben Arbeitsschritt.

    Kein Trigger auf den Wertebereich an lessons_learned: knowledge_nodes hat
    ihn, dort waere er ein zweiter Ort fuer dieselbe Regel. Die Pruefung sitzt
    im Schreibpfad.

    NACHTRAG 2026-08-10, und es ist genau derselbe Fehler eine Ebene tiefer:
    Diese Funktion zog die Spalte nur an lessons_learned nach und zitierte
    dabei L-7e0823 -- waehrend knowledge_nodes.freigabe seinerseits nur per
    migrate_freigabe.py existierte und in ensure_schema fehlte. Auf einer DB
    aus schema.sql ohne Migrationslauf legt _ensure_node_constraint_triggers
    die beiden freigabe-Pruefer an, und der naechste knowledge_add bricht mit
    'no such column: NEW.freigabe' ab -- ein roher SQLite-Fehler im normalen
    Schreibpfad, also die Fehlerklasse, gegen die die zitierte Lehre gerade
    schuetzen sollte. Aufgefallen ueber tests/test_anlass_schema_backfill.py,
    nachdem dessen Vorrichtung repariert war. Beide Tabellen im selben
    Schritt, damit hier nicht ein drittes Mal die Haelfte nachgezogen wird."""
    tabellen = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    for tabelle in ("lessons_learned", "knowledge_nodes"):
        if tabelle not in tabellen:
            continue
        spalten = {r[1] for r in conn.execute(f"PRAGMA table_info({tabelle})")}
        if "freigabe" not in spalten:
            conn.execute(f"ALTER TABLE {tabelle} "
                         "ADD COLUMN freigabe TEXT NOT NULL DEFAULT 'intern'")

    # Die Werte-Schranke gehoert zur Spalte, nicht daneben. Bis 2026-08-11 kam
    # die Spalte per Nachzug, der Trigger aber nur bei knowledge_nodes -- an
    # lessons_learned nahm die Datenbank jeden Wert an. Dieselbe
    # Haelfte-nachgezogen-Falle, vor der der Docstring dieser Funktion warnt
    # (L-7e0823), eine Ebene tiefer: nicht die Spalte fehlte, sondern ihre Regel.
    if "lessons_learned" in tabellen:
        conn.executescript(LESSON_FREIGABE_TRIGGERS_SQL)


def _version() -> str:
    """Die Fassung steht in EINER Datei, nicht an drei Stellen.

    Bis 2026-08-10 meldete der Server hier fest "1.0.0" -- eine
    Stabilitaetszusage, die nichts deckte, und ein Klient liest sie. Eine Zahl
    im Quelltext neben einer Zahl in der README neben einem git-Tag ist
    dieselbe Fehlklasse wie zwei Auszugsformate: sie laufen auseinander, und
    niemand merkt welche stimmt.

    Fehlt die Datei (etwa in einem Teilklon), gilt "0.0.0-unbekannt" -- eine
    erfundene Zahl waere schlimmer als das Eingestaendnis."""
    try:
        return (Path(__file__).resolve().parent / "VERSION").read_text(
            encoding="utf-8").strip() or "0.0.0-unbekannt"
    except OSError:
        return "0.0.0-unbekannt"


UNBEKANNTER_SCHREIBER = "unbekannt"

# Einmal beim Prozessstart bestimmt (Auftrag 2026-08-07, ADR-028-Rangfolge:
# "so bauen, dass der Fehler unmoeglich ist" statt im Werkzeug pruefen). Ein
# vom Claude-Code-Host gestarteter MCP-Server-Prozess erbt CLAUDE_CODE_SESSION_ID
# von der Elternsitzung -- dieselbe Kennung, die SessionStart als session_id
# an wiedereinstieg.py reicht.
#
# Auftrag 2026-08-07 (Nachtrag): auf 8 Zeichen gekuerzt -- das ist die Form,
# die im Rest vom hub bereits kanonisch ist (knowledge_recall_hook.py::
# log_recall, agent_register_hook.py, agent_reuse_guard_hook.py,
# quality_gate_hook.py, wiedereinstieg.py -- alle five schreiben/lesen
# session_id[:8]). Diese Zeile war bisher die EINZIGE Stelle, die die volle
# 36-Zeichen-UUID in eine Spalte schrieb, die anderswo als 8-stelliges
# Praefix erwartet wird (access_log.session, knowledge_relations.session) --
# ein exakter SQL-Gleichheitstest zwischen beiden Formen kann nie wahr
# werden (wirkung.py::outcome(), Auftrag 2026-08-07). ALTZEILEN in voller
# Laenge bleiben unangetastet (keine Migration) -- wirkung.py vergleicht
# deshalb per Praefix, nicht per Gleichheit.
_PROZESS_SITZUNG = (os.environ.get("CLAUDE_CODE_SESSION_ID") or "")[:8] or None

# client (Auftrag 2026-08-07): anders als actor/session/model NIE vom
# Aufrufer erwartet -- der Aufrufer fuellt es erfahrungsgemaess nie (siehe
# Fuellstand-Befund im Auftrag: actor/model/session zu 83% leer). Einmal aus
# der Umgebung abgeleitet, wie _PROZESS_SITZUNG direkt darueber. CLAUDECODE
# bzw. CLAUDE_CODE_SESSION_ID gesetzt -> vom Claude-Code-Host gestarteter
# Prozess; sonst Skriptzugriff (Cron, Handlauf, migrate_*.py). Kein
# Anbieter-Erkennungslib noetig, die Umgebungsvariable reicht.
_KLIENT = "claude-code" if (os.environ.get("CLAUDECODE") or os.environ.get("CLAUDE_CODE_SESSION_ID")) else "skript"


# Ein Modell, fuenf Schreibweisen -- gemessen 2026-08-08 am Bestand:
# "Anthropic/claude-opus-5" (27), "anthropic/claude-opus-5" (8),
# "claude-opus-5" (3), "Anthropic/Opus 5" (2), "claude-sonnet-5" (22).
# Nach Modell gruppieren geht damit nicht, auch nicht fuer die 5 Prozent,
# die ueberhaupt gefuellt sind.
#
# Bewusst KEINE geschlossene Liste erlaubter Werte: ein unbekanntes Modell
# soll eingetragen werden koennen, nicht abgewiesen. Normalisiert wird die
# Schreibweise, nicht der Inhalt -- was nicht erkannt wird, geht unveraendert
# (nur getrimmt) durch und bleibt damit sichtbar statt zu verschwinden.
_MODELL_ALIAS = {
    "opus 5": "claude-opus-5", "opus5": "claude-opus-5", "opus-5": "claude-opus-5",
    "sonnet 5": "claude-sonnet-5", "sonnet5": "claude-sonnet-5", "sonnet-5": "claude-sonnet-5",
    "haiku 4.5": "claude-haiku-4-5", "haiku-4.5": "claude-haiku-4-5",
    "fable 5": "claude-fable-5", "fable-5": "claude-fable-5",
}
_ANBIETER = ("anthropic/", "openai/", "google/", "ollama/", "meta/", "mistral/")


def modell_normalisieren(model: str | None) -> str | None:
    """Eine Schreibweise je Modell. Anbieter bleibt erhalten, wenn er
    mitgegeben wurde -- er unterscheidet ein lokales Llama von einem
    gehosteten. Rueckgabe None nur fuer None; ein leerer String bleibt leer,
    damit ein Aufrufer, der bewusst nichts sagt, nicht wie einer aussieht,
    der nichts uebergeben hat."""
    if model is None:
        return None
    roh = model.strip()
    if not roh:
        return roh
    klein = roh.lower()
    anbieter = ""
    for a in _ANBIETER:
        if klein.startswith(a):
            anbieter, klein = a, klein[len(a):]
            break
    klein = _MODELL_ALIAS.get(klein, klein)
    # Traegt der Modellname den Anbieter schon (claude-*, gpt-*, gemini-*),
    # faellt das Praefix weg -- sonst stehen "anthropic/claude-opus-5" und
    # "claude-opus-5" weiter als zwei Gruppen nebeneinander, und genau das
    # war der gemessene Mangel. Bei allem anderen bleibt es stehen: ein
    # "ollama/gemma3:12b" ist etwas anderes als ein gehostetes gemma3.
    if klein.startswith(("claude-", "gpt-", "gemini-")):
        return klein
    return anbieter + klein


def _identity(actor: str | None = None, model: str | None = None,
              session: str | None = None) -> tuple[str, str, str]:
    """Aufloesung actor/model/session (Auftrag 2026-08-06, Mangel: 9%/0,5%
    gefuellt in access_log). Ursache war hier, an der einzigen Stelle, durch
    die JEDER log_access()-Aufruf laeuft (log_access ruft _identity() intern
    IMMER auf, auch wenn ein Aufrufer nichts uebergibt): der dritte Schritt
    der Kette (Parameter -> Umgebungsvariable -> ???) fehlte. Die
    Tool-Beschreibungen in IDENTITY_PROPERTIES versprachen bereits "else
    BEGOD_KNOWLEDGE_ACTOR or unknown" -- das 'or unknown' war nie
    implementiert, `actor or os.environ.get(...)` endete bisher still bei
    None, wenn beides fehlte (der Regelfall: kein MCP-Aufrufer uebergibt
    actor/session von sich aus, und die Umgebungsvariablen sind praktisch nie
    gesetzt). Jetzt: dritter Schritt ist ein expliziter, unmissverstaendlicher
    Wert -- kein Abweisen (Punkt 4 des Auftrags: ein Schreiber, der sich nicht
    ausweist, bleibt zulaessig), aber auch kein stilles NULL mehr.

    session zusaetzlich (Auftrag 2026-08-07): vor UNBEKANNTER_SCHREIBER greift
    _PROZESS_SITZUNG, vom Server selbst ermittelt statt vom Aufrufer erwartet.
    Ein von Hand mitgegebener Wert (Parameter oder Env-Var) hat weiter Vorrang.

    UMKEHRUNG FUER actor (B4.1, docs/PLAN_B4_AUSWEIS_2026-08-09.md): Genau das
    'Parameter zuerst' war bei actor die Luecke -- wer `actor="betreiber"`
    mitschickte, WAR Betreiber, und es gab kein if und kein Abweisen
    (bauartgleich L-8487fb). Jetzt entscheidet ausweis.loese_auf(): ein
    beglaubigter Ausweis gewinnt immer, danach ist das Argument stumm.

    Ohne Ausweis bleibt der bisherige Weg offen -- Argument, dann Umgebung,
    dann UNBEKANNTER_SCHREIBER -- aber die Zuschreibung traegt das Praefix
    'unbeglaubigt:'. Kein Bruch fuer die bestehenden Schreiber (Skripte,
    ChatGPT-Zugang), und trotzdem im Protokoll dauerhaft unterscheidbar, ob
    eine Identitaet geprueft oder nur behauptet war.

    model und session bleiben absichtlich unberuehrt: sie beschreiben den
    VORGANG, nicht die Identitaet -- ein falscher Modellname erschleicht keine
    Rechte."""
    aufgeloest = ausweis.loese_auf(actor)
    return (
        aufgeloest.protokollname,
        modell_normalisieren(model or os.environ.get("BEGOD_KNOWLEDGE_MODEL")) or UNBEKANNTER_SCHREIBER,
        session or os.environ.get("BEGOD_KNOWLEDGE_SESSION") or _PROZESS_SITZUNG or UNBEKANNTER_SCHREIBER,
    )


def _bedient_von(actor: str | None = None) -> str | None:
    """Wer FUEHRT die Maschine, die gerade schreibt -- aus dem Ausweis, nie
    aus einem Argument (Betreiberweisung 2026-08-11).

    Bewusst eine eigene Aufloesung statt eines vierten Rueckgabewerts von
    _identity(): das haette alle 17 Aufrufstellen gebrochen, und der Preis
    ist gemessen gering -- 2,5 ms je Aufloesung (20 Durchlaeufe, scrypt
    n=16384). Die Zahl steht hier, weil sie den Verzicht auf einen
    Zwischenspeicher traegt; steigt sie, ist die Entscheidung neu zu treffen.

    None in drei Faellen, und alle drei sind richtig so:
      unbeglaubigt   kein Nachweis, also keine Behauptung
      Mensch selbst  niemand steht ueber ihm -- "chefin gefuehrt von chefin"
                     waere eine leere Aussage
      kein Eintrag   der Ausweis entstand per --anlegen statt per Einladung;
                     bedient_von setzt NUR der Einladungsweg, weil nur dort
                     ein Mensch die PIN ausspricht
    """
    a = ausweis.loese_auf(actor)
    if not a.beglaubigt or a.ist_mensch:
        return None
    return a.bedient_von or None


def compute_zeilen_hash(affected_row: dict | None) -> str | None:
    """SHA-256 ueber den von einer Aktion betroffenen Datensatz NACH der
    Aenderung. None (-> NULL in access_log.zeilen_hash) bei reinen
    Lesezugriffen und bei Loeschungen -- beides ein gueltiger Zustand,
    siehe Spaltenkommentar an access_log in schema.sql."""
    if affected_row is None:
        return None
    payload = json.dumps(affected_row, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_ketten_hash(prev_ketten_hash: str | None, *, node_path: str | None,
                        action: str, query: str | None, project_id: str | None,
                        actor: str | None, model: str | None, session: str | None,
                        status: str, timestamp: str, zeilen_hash: str | None) -> str:
    """Ein Schritt der Auditkette ueber access_log (Auftrag 2026-08-06).
    Feldreihenfolge ist Teil des Vertrags -- siehe Spaltenkommentar an
    access_log.ketten_hash in schema.sql; eine Aenderung hier bricht jede
    bereits geschriebene Kette rueckwirkend. KEINE Verschluesselung, keine
    Signatur: weist eine nachtraegliche Aenderung nach, verhindert sie
    nicht -- wer Schreibrechte auf die DB-Datei hat, kann die Kette neu
    rechnen (bekannte Grenze, siehe Auftrag)."""
    prev = prev_ketten_hash or GENESIS_KETTEN_HASH
    fields = (prev, node_path, action, query, project_id, actor, model,
              session, status, timestamp, zeilen_hash)
    payload = "|".join("" if f is None else str(f) for f in fields)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def log_access(conn: sqlite3.Connection, node_path: str | None, action: str,
               query: str | None = None, project_id: str | None = None,
               actor: str | None = None, model: str | None = None,
               session: str | None = None, status: str = "completed",
               affected_row: dict | None = None) -> int:
    if status not in EVENT_STATUSES:
        raise ValueError(f"Invalid event status: {status}")
    actor, model, session = _identity(actor, model, session)
    timestamp = now_iso()
    zeilen_hash = compute_zeilen_hash(affected_row)
    # Letzten ketten_hash auf DERSELBEN Verbindung lesen -- sieht auch die
    # noch nicht committete Datenaenderung dieser Transaktion (relevant,
    # weil dieser INSERT+commit gemeinsam mit dem vorangegangenen
    # Schreibzugriff (z.B. knowledge_nodes) die Transaktionsgrenze bildet,
    # siehe Aufrufer in knowledge_add/knowledge_update/etc.). Zeilen ohne
    # ketten_hash (Altbestand vor der Migration) zaehlen als Kettenanfang.
    prev_row = conn.execute(
        "SELECT ketten_hash FROM access_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    prev_ketten_hash = prev_row[0] if prev_row else None
    ketten_hash = compute_ketten_hash(
        prev_ketten_hash, node_path=node_path, action=action, query=query,
        project_id=project_id, actor=actor, model=model, session=session,
        status=status, timestamp=timestamp, zeilen_hash=zeilen_hash,
    )
    cursor = conn.execute(
        """INSERT INTO access_log
           (node_path, action, query, project_id, actor, model, session, client, status, timestamp,
            zeilen_hash, ketten_hash)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (node_path, action, query, project_id, actor, model, session, _KLIENT, status, timestamp,
         zeilen_hash, ketten_hash)
    )
    conn.commit()
    return int(cursor.lastrowid)


# ─── MCP Tool Implementations ────────────────────────────────────────────

# Credential-bound Serving policy.  The client cannot supply purpose, field,
# or recipient: the role fixes the purpose/field and the credential fixes the
# recipient.  The row may only narrow that server-side policy via tags.
_KNOWLEDGE_READ_PROJEKTION = {
    "raumplaner": ("raumplanung", "nutzinformation"),
}


def _knowledge_read_projection(row: sqlite3.Row) -> dict | None:
    ausw = ausweis.loese_auf()
    policies = [_KNOWLEDGE_READ_PROJEKTION[r]
                for r in ausw.rollen if r in _KNOWLEDGE_READ_PROJEKTION]
    if not ausw.beglaubigt or not policies:
        return None

    tags = set(json.loads(row["tags"]) if row["tags"] else [])
    for purpose, field in policies:
        if f"zweck:{purpose}" in tags and f"feld:{field}" in tags:
            return {field: row["summary"]}
    return {"error": "zugriff verweigert"}

def knowledge_browse(path: str = "/", project_filter: str | None = None, *,
                     actor: str | None = None, model: str | None = None,
                     session: str | None = None) -> dict:
    """Browse children of a knowledge tree node. Returns titles and summaries only (token-efficient)."""
    conn = get_db()
    log_access(conn, path, "browse", project_id=project_filter,
               actor=actor, model=model, session=session, status="started")

    if path == "/":
        query = "SELECT id, path, title, summary, project_id, level, access_count FROM knowledge_nodes WHERE level = 0 ORDER BY path"
        params: tuple = ()
    else:
        normalized = path.rstrip("/")
        query = "SELECT id, path, title, summary, project_id, level, access_count FROM knowledge_nodes WHERE parent_path = ? ORDER BY path"
        params = (normalized,)

    if project_filter:
        query = query.replace("ORDER BY", f"AND project_id IN ('shared', ?) ORDER BY")
        params = (*params, project_filter)

    rows = conn.execute(query, params).fetchall()
    children_count_q = "SELECT COUNT(*) FROM knowledge_nodes WHERE parent_path = ?"

    results = []
    for r in rows:
        child_count = conn.execute(children_count_q, (r["path"],)).fetchone()[0]
        results.append({
            "id": r["id"],
            "path": r["path"],
            "title": r["title"],
            "summary": r["summary"],
            "project": r["project_id"],
            "has_children": child_count > 0,
            "children_count": child_count
        })

    log_access(conn, path, "browse", project_id=project_filter,
               actor=actor, model=model, session=session)
    conn.close()
    return {"path": path, "children": results, "count": len(results)}


def knowledge_read(node_id: str, *, actor: str | None = None,
                   model: str | None = None, session: str | None = None) -> dict:
    """Read full content of a knowledge node. Use browse first to find the right node."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM knowledge_nodes WHERE id = ? OR path = ?",
        (node_id, node_id)
    ).fetchone()
    if not row:
        log_access(conn, node_id, "read", actor=actor, model=model, session=session,
                   status="rejected", query="knoten_nicht_gefunden")
        conn.close()
        return {"error": f"Node not found: {node_id}"}

    projection = _knowledge_read_projection(row)
    if projection == {"error": "zugriff verweigert"}:
        log_access(conn, None, "read", actor=actor, model=model, session=session,
                   status="rejected", query="zweckprojektion")
        conn.commit()
        conn.close()
        return projection

    log_access(conn, row["path"], "read", project_id=row["project_id"],
               actor=actor, model=model, session=session, status="started")
    # ENTSCHEIDUNG (Auftrag 2026-08-06, Nebenbefund Konfidenzverfall):
    # updated_at bleibt hier UNVERAENDERT, bewusst. Lesen ist keine
    # Bestaetigung: haette access_count++ updated_at mitgezogen, wuerde
    # haeufig ABGERUFENES Wissen automatisch als frisch/geprueft gelten
    # (konfidenz.py rechnet das Alter seit updated_at), obwohl niemand seinen
    # Inhalt bestaetigt hat -- ein oft gelesener, aber nie korrigierter
    # Altfakt wuerde nie verfallen. Bestaetigung ist ein eigener, bewusster
    # Vorgang (konfidenz.py::bestaetigen), kein Nebeneffekt des Lesens.
    conn.execute("UPDATE knowledge_nodes SET access_count = access_count + 1 WHERE id = ?", (row["id"],))
    log_access(conn, row["path"], "read", project_id=row["project_id"],
               actor=actor, model=model, session=session)
    conn.commit()

    if projection is not None:
        conn.close()
        return projection

    # Befund 2026-08-06: ein Astknoten ("Automatisch erzeugter Astknoten",
    # kein content) liefert ohne diesen Zusatz eine leere Seite -- Zweck und
    # Regeln stehen in den Kindknoten. Nur eine Ebene, nicht rekursiv (siehe
    # knowledge_browse fuer den vollen Baum).
    children = conn.execute(
        "SELECT title, summary FROM knowledge_nodes WHERE parent_path = ? ORDER BY path",
        (row["path"],)
    ).fetchall()

    result = {
        "id": row["id"],
        "path": row["path"],
        "title": row["title"],
        "summary": row["summary"],
        "content": row["content"] or "(kein Volltext)",
        "project": row["project_id"],
        "tags": json.loads(row["tags"]) if row["tags"] else [],
        "source": row["source"],
        # Kennung, NICHT aufgeloest (ADR-027 Nachtrag 4) -- Aufloesen (Kennung
        # -> echter Quellknoten) ist eine Berechtigungsfrage und steht hier
        # nicht an, siehe schema.sql-Kommentar an dieser Spalte.
        "abgeleitet_von": row["abgeleitet_von"],
        "confidence": row["confidence"],
        "norm_rang": row["norm_rang"],
        "gilt_ab": row["gilt_ab"],
        "gilt_bis": row["gilt_bis"],
        "norm_entscheidung": row["norm_entscheidung"],
        "norm_entschieden_von": row["norm_entschieden_von"],
        "norm_entschieden_am": row["norm_entschieden_am"],
        "norm_entschieden_grund": row["norm_entschieden_grund"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "children": [{"title": c["title"], "summary": c["summary"]} for c in children],
    }
    conn.close()
    return result


def _embedding_ranking(conn: sqlite3.Connection, kind: str, query_vec: list[float],
                        allowed_ids: set | None) -> list[str]:
    """Cosine-Ranking ueber die additive knowledge_embeddings-Tabelle. Fehlt die
    Tabelle (aeltere DB-Kopie ohne AP "Wissenssuche nach Bedeutung"), liefert
    leere Liste statt zu werfen -- Aufrufer faellt dann automatisch auf reines
    FTS5/LIKE-Matching zurueck.

    Modell-Sperre (Auftrag 2026-08-07): Vektoren aus zwei Embedding-Modellen
    liegen in verschiedenen Vektorraeumen -- Kosinus-Aehnlichkeit zwischen
    ihnen ist Unsinn, ohne dass die Rechnung selbst fehlschlaegt (unterschiedliche
    Dimension wuerde sogar krachen, gleiche Dimension bei anderem Modell liefert
    einfach eine falsche Zahl). Deshalb WHERE model = ? -- ein Vektor, dessen
    Modell nicht dem aktuell konfigurierten (embeddings.DEFAULT_EMBED_MODEL)
    entspricht, wird nie gelesen. Lieber kein Vektor als ein falscher."""
    try:
        rows = conn.execute(
            "SELECT ref_id, vector FROM knowledge_embeddings WHERE kind = ? AND model = ?",
            (kind, embeddings.DEFAULT_EMBED_MODEL),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    scored = []
    seen_ref_ids = set()  # mehrwertige Lehren: je Bereich eine Zeile, gleicher Vektor --
    # ohne Dedup zaehlt dieselbe Aehnlichkeit mehrfach in die RRF-Fusion und
    # haengt eine mehrwertige Lehre allein wegen ihrer Zeilenzahl vor eine
    # gleich relevante einwertige (siehe test_scope_in_query.py).
    for r in rows:
        if allowed_ids is not None and r["ref_id"] not in allowed_ids:
            continue
        if r["ref_id"] in seen_ref_ids:
            continue
        seen_ref_ids.add(r["ref_id"])
        vec = embeddings.unpack_embedding(r["vector"])
        scored.append((embeddings.cosine_similarity(query_vec, vec), r["ref_id"]))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [ref_id for _, ref_id in scored]


def _fuse_with_keyword_floor(keyword_ordered_ids: list, embedding_ordered_ids: list,
                              max_results: int) -> list:
    """RRF-Fusion, aber mit garantiertem Stichwort-Sockel: jede der Top-
    max_results Stichworttreffer-IDs bleibt im Ergebnis, egal wie das
    Embedding-Ranking ausfaellt (Abnahme-Kriterium "kein Stichworttreffer geht
    verloren"). Ohne Embedding-Treffer (leere Liste, z.B. Ollama nicht
    erreichbar oder Tabelle fehlt) reproduziert das exakt die bisherige
    Stichwort-Reihenfolge, da dict.fromkeys() den Sockel unveraendert vorn
    haelt und `fused` in diesem Fall ohnehin identisch mit
    keyword_ordered_ids ist."""
    weight = embeddings.hybrid_retrieval_weight()
    fused = embeddings.rrf_fuse(keyword_ordered_ids, embedding_ordered_ids, embedding_weight=weight)
    floor = keyword_ordered_ids[:max_results]
    return list(dict.fromkeys(floor + fused))[:max(max_results, len(floor))]


# Deutsche Umlaut-Faltung: ae/oe/ue/ss-Schreibung UND ä/ö/ü/ß treffen sich.
# Dieselbe Abbildung wie der SQL-Ausdruck in schema.sql (Trigger
# knowledge_ai/ad/au) -- SQLite-Trigger koennen keine Python-Funktion
# aufrufen, ohne sie auf jeder schreibenden Verbindung zu registrieren
# (migrate_knowledge.py/build_embeddings.py/_add_phase2_nodes.py oeffnen die
# DB roh, ohne durch dieses Modul zu gehen), darum zwei Implementierungen.
# Gleichheit ist von
# tests/test_knowledge_hybrid_search.py::test_fold_de_matches_sql_fold belegt.
_FOLD_TABLE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def fold_de(text: str) -> str:
    """'Gründer' und 'Gruender' werden beide zu 'gruender'."""
    return text.lower().translate(_FOLD_TABLE)


_QUERY_WORD_RE = re.compile(r"[A-Za-zÄÖÜäöüß0-9]+")


def _fts_phrase(word: str) -> str:
    """Ein Wort als FTS5-Phrase quoten (Anfuehrungszeichen verdoppelt escaped) --
    verhindert, dass ein Wort wie 'NOT' oder ein Bindestrich als FTS5-Operator
    statt als Suchtext interpretiert wird."""
    return '"' + word.replace('"', '""') + '"'


def _or_query(query: str) -> str:
    """Baut aus einer Anfrage eine FTS5-ODER-Verknuepfung ueber die einzelnen,
    gefalteten Woerter. Vorher lief MATCH mit mehreren Woertern als implizites
    UND -- ein einziges Wort, das nirgends vorkommt, killte die ganze Anfrage
    (gemessen: 4 von 6 Anfragen 0 Treffer trotz vorhandenem Knoten). Bei OR
    sortiert bm25/rank Dokumente mit mehr uebereinstimmenden Woertern weiter
    oben ein -- kein zusaetzliches Ranking noetig."""
    words = [fold_de(w) for w in _QUERY_WORD_RE.findall(query)]
    return " OR ".join(_fts_phrase(w) for w in words if w)


ZERO_HIT_LOG = Path(__file__).parent / "zero_hit_log.jsonl"
ZERO_HIT_LOG_MAX_BYTES = 200_000  # klein halten, gleiche Kappung wie recall_log.jsonl

INJECTION_SUSPECT_LOG = Path(__file__).parent / "injection_suspect_log.jsonl"
INJECTION_SUSPECT_LOG_MAX_BYTES = 200_000  # gleiche Kappung wie zero_hit_log.jsonl


def _check_injection_suspects(kind: str, ref: str, felder: dict) -> None:
    """ADR-034 (einschleusung.find_injection_suspects): ein neuer Verdacht
    entsteht nur beim SCHREIBEN von Text -- knowledge_lint.py scannt bislang
    den ganzen Bestand periodisch, obwohl 543 reine Lesevorgaenge nie einen
    neuen Fund erzeugen koennen. Hier direkt am Schreibvorgang: nur die
    gerade geschriebenen Felder pruefen (erkenne() ist reiner Text-Scan,
    kein DB-Zugriff), Funde anhaengen -- nie blockieren (Modul-Docstring
    einschleusung.py: 'ein Fund ist ein Befund, keine Ablehnung'). Jeder
    Fehler wird verschluckt, gleiches Muster wie _log_zero_hit: eine
    Nebenpruefung darf den Schreibvorgang nie zum Scheitern bringen."""
    try:
        funde = []
        for feld, text in felder.items():
            if not text:
                continue
            for fund in einschleusung.erkenne(text):
                funde.append({"feld": feld, **fund})
        if not funde:
            return
        entry = json.dumps({
            "ts": now_iso(), "kind": kind, "ref": ref, "funde": funde,
        }, ensure_ascii=False)
        if INJECTION_SUSPECT_LOG.exists() and INJECTION_SUSPECT_LOG.stat().st_size > INJECTION_SUSPECT_LOG_MAX_BYTES:
            lines = INJECTION_SUSPECT_LOG.read_text(encoding="utf-8").splitlines(keepends=True)
            INJECTION_SUSPECT_LOG.write_text("".join(lines[len(lines) // 2:]), encoding="utf-8")
        with INJECTION_SUSPECT_LOG.open("a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception:
        pass


def _check_norm_conflicts(node_id: str, node_path: str, norm_rang: int | None) -> None:
    """ADR-034 (Widerspruchspruefung, Auftrag 2026-08-07): ein neuer
    Normkonflikt kann nur entstehen, wenn eine Norm neu geschrieben oder
    umdatiert wird -- Bestandspaare wurden bei ihrem eigenen Schreibvorgang
    schon geprueft (knowledge_lint.find_norm_conflicts_for() ist deshalb
    O(n) gegen den restlichen Normbestand, nicht O(n^2) wie der volle Scan).

    Ein Fund wird ein VORGANG, keine Meldung (Lehre L-86e92d verlangt
    Adressat/Antwortort/Folge bei Ausbleiben, sonst ist es keiner):
      Adressat:   Betreiber, ueber dieselbe lessons_learned-Flaeche wie jede
                  andere Lehre (lesson_query, Stop-Hook-Review).
      Antwort:    normkraft.py ausser_kraft <verlierender Pfad> setzt
                  gilt_bis -- find_norm_conflicts_for() schliesst ausser
                  Kraft gesetzte Normen aus, der naechste Schreibvorgang
                  dieses Paars findet dann keinen Konflikt mehr; die Lehre
                  kann per lesson_update(status='resolved') geschlossen
                  werden.
      Ausbleiben: die Lehre bleibt status='active' und waechst bei jedem
                  weiteren Treffer desselben Paars auf occurrences (exakte
                  Textdublette in lesson_record) -- kein stiller Verlust,
                  eskaliert wie jede andere Lehre ab 3 Vorkommen.

    Nebenpruefung: darf den Schreibvorgang nie zum Scheitern bringen (Muster
    wie _check_injection_suspects). Nur wenn der geschriebene Knoten selbst
    eine Norm ist (norm_rang gesetzt) -- ein Fakt kann keinen Normkonflikt
    ausloesen."""
    if norm_rang is None:
        return
    try:
        import knowledge_lint  # noqa: PLC0415 -- verzoegert (Zirkel, siehe Moduldocstring)
        conn = knowledge_lint.get_ro_conn(DB_PATH)
        try:
            treffer = knowledge_lint.find_norm_conflicts_for(conn, node_id)
        finally:
            conn.close()
        for t in treffer:
            beschreibung = (
                f"Normkonflikt ungeloest: {t['a']} (Rang {t['a_rang']}) <-> {t['b']} "
                f"(Rang {t['b_rang']}) -- weder lex superior noch lex specialis noch "
                f"lex posterior entscheidet."
            )
            lesson_record(
                type_="antipattern", description=beschreibung,
                root_cause="Zwei Normen mit gleichem Rang, ueberschneidendem Bereich und "
                           "gleichem gilt_ab -- keine der drei Regeln "
                           "(knowledge_lint.py::_resolve_norm_conflict) kann entscheiden.",
                resolution="",
                prevention="Betreiber entscheidet per normkraft.py ausser_kraft <verlierender Pfad> "
                           "--ab <ISO> --wegen <Grund>. Sobald gilt_bis gesetzt ist, faellt die Norm "
                           "aus der Pruefung; die Lehre danach per lesson_update(status='resolved') "
                           "schliessen. Ohne Antwort bleibt sie aktiv und waechst mit jedem weiteren "
                           "Treffer auf occurrences.",
                severity="high", projects=["hub"], node_path=t["a"],
                anlass="skript",
            )
    except Exception:
        pass


def _cwd_project(cwd: str | None) -> str | None:
    """Projekt/Worktree aus cwd -- exakte Kopie von
    knowledge_recall_hook.py::_cwd_project. Bewusst dupliziert statt
    importiert: Hook-Skript und MCP-Server sind getrennte Prozesse ohne
    gemeinsamen sys.path.

    Fund 2026-08-06 (Probelauf ausserhalb dieses Verbunds): hier stand vorher
    ein fest verdrahteter Verbundname im Regex (".../Begod2026/<projekt>/...")
    -- fuer jeden fremden Nutzer immer None, weil dessen Ordner nie
    "Begod2026" heisst. Jetzt: BEGOD_KNOWLEDGE_PROJECT uebersteuert explizit
    (fuer Faelle, in denen weder Git-Wurzel noch Ordnername passen); sonst
    Name der naechsten Git-Wurzel oberhalb von cwd -- funktioniert bei uns
    zufaellig identisch, weil hier jedes Projekt (fahrtenbuch, hub, ...)
    genau auf Verbund-Ebene sein eigenes .git hat, ist aber nicht an
    "Begod2026" gebunden. Keine Git-Wurzel gefunden (z.B. /tmp/irgendwas) ->
    letzter Ordnername von cwd statt None, kein Nutzer bleibt mangels
    passendem Layout ganz ohne Wert."""
    if not cwd:
        return None
    override = os.environ.get("BEGOD_KNOWLEDGE_PROJECT")
    if override:
        return override
    p = Path(cwd)
    for parent in (p, *p.parents):
        if (parent / ".git").exists():
            return parent.name
    return p.name or None


def _log_zero_hit(query: str, cwd: str | None = None, session: str | None = None) -> None:
    """Haelt fest, welche Suchanfragen nichts fanden: Zeitpunkt, Anfragetext,
    Trefferzahl (=0), Herkunft. Grundlage fuer eine spaetere, an echten
    Ausfaellen gemessene Entscheidung ueber Synonyme, statt das zu vermuten.
    Nie ein Grund, die Suche scheitern zu lassen -- Fehler werden verschluckt,
    wie beim analogen Recall-Log (knowledge_recall_hook.py::log_recall).

    Herkunft (Auftrag 2026-08-06, Nachzug zu Commit 4bcde3574): cwd + daraus
    abgeleiteter Worktree-Name (gleiche Ableitung wie recall_log.jsonl,
    _cwd_project oben, kein zweiter Weg) sowie Sitzungskennung, gekuerzt wie
    dort (session[:8]). Fehlt ein Wert -> null im JSON, nicht weggelassen --
    Bestandszeilen ohne diese Schluessel bleiben ueber .get() lesbar. Anders
    als beim Hook gibt es hier kein sinnvolles os.getcwd()-Fallback: der
    MCP-Server ist ein langlebiger Prozess, sein eigenes cwd sagt nichts
    ueber den aufrufenden Client aus -- cwd kommt daher ausschliesslich vom
    Aufrufer (Tool-Parameter)."""
    try:
        entry = json.dumps({
            "ts": now_iso(),
            "query": query,
            "hits": 0,
            "cwd": cwd,
            "worktree": _cwd_project(cwd),
            "session": (session[:8] if session else None),
        }, ensure_ascii=False)
        if ZERO_HIT_LOG.exists() and ZERO_HIT_LOG.stat().st_size > ZERO_HIT_LOG_MAX_BYTES:
            lines = ZERO_HIT_LOG.read_text(encoding="utf-8").splitlines(keepends=True)
            ZERO_HIT_LOG.write_text("".join(lines[len(lines) // 2:]), encoding="utf-8")
        with ZERO_HIT_LOG.open("a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception:
        pass


def _geltung_status(norm_rang, gilt_ab: str | None, gilt_bis: str | None, stichtag: str) -> str | None:
    """Geltung einer Norm zum Stichtag, nach dem Vorbild von normkraft.py::in_kraft
    (gilt_ab <= stichtag AND (gilt_bis IS NULL OR ...)) -- reiner ISO-Stringvergleich,
    keine datetime-Parsung, wie dort. Kanonische Bedeutung von gilt_bis
    (inklusiv, letzter Geltungstag) ist dort an EINER Stelle festgehalten,
    nicht hier wiederholt: normkraft.py::in_kraft.
    norm_rang IS NULL (Fakt) oder gilt_ab nicht gesetzt (Norm ohne Geltungsangabe)
    -> None, unveraendert wie vor diesem Auftrag."""
    if norm_rang is None or gilt_ab is None:
        return None
    if stichtag < gilt_ab:
        return "noch_nicht_in_kraft"
    if gilt_bis is not None and stichtag > gilt_bis:
        return "abgelaufen"
    return "in_kraft"


def knowledge_search(query: str, scope: str = "all", max_results: int = 10, *,
                     stichtag: str | None = None, nur_geltende: bool = False,
                     actor: str | None = None, model: str | None = None,
                     session: str | None = None, cwd: str | None = None) -> dict:
    """Hybrid-Suche ueber Wissensknoten UND Lehren (Auftrag 2026-08-07 --
    vorher nur Knoten; Lehren sind mit 64% des Bestands die groessere
    Haelfte, hatten aber keinen Volltextindex, siehe lessons_fts in
    schema.sql und _ensure_lessons_fts_backfill). FTS5-Stichwortmatching
    (Woerter ODER-verknuepft, deutsch gefaltet) plus optionale
    Bedeutungs-Suche ueber lokale Embeddings (RRF-fusioniert). Ohne Vektoren
    (Tabelle fehlt oder leer) oder ohne erreichbares Ollama identisch zum
    reinen FTS5-Verhalten. Jedes Ergebnis traegt "kind": "node"|"lesson".
    Returns summaries (not full content) for token efficiency.

    Rangfolge ueber BEIDE Sorten (Auftrag Punkt 3): rohe bm25-Werte aus
    knowledge_fts (6 Spalten) und lessons_fts (3 Spalten) sind zwischen den
    Tabellen NICHT vergleichbar (bm25 normiert ueber tabelleneigene
    Korpusstatistik). Deshalb zweistufig, dieselbe Rang-POSITIONS-Fusion
    (embeddings.rrf_fuse, ignoriert Rohscores) zweimal angewandt: zuerst
    Knoten-FTS-Rangliste mit Lehren-FTS-Rangliste zu einer Stichwort-Rangliste
    verschmolzen, ebenso Knoten- mit Lehren-Embedding-Rangliste, dann laufen
    beide kombinierten Listen durch die UNVERAENDERTE _fuse_with_keyword_floor
    (dieselbe Funktion, die vorher Knoten-FTS mit Knoten-Embeddings fusionierte
    -- kein zweiter Fusionsmechanismus). embedding_weight=1.0 an beiden
    Stellen ist Gleichgewicht PRO RANGLISTE, nicht pro Treffer -- der
    Stichwort-Sockel (siehe _fuse_with_keyword_floor) laesst dadurch
    typischerweise ungefaehr die Haelfte der obersten Plaetze an Lehren
    fallen, UNABHAENGIG von Relevanz-Feinheiten. Das ist eine Folge der
    Bauart, keine Feinjustierung zu Lasten von Knoten -- wenn Lehren dadurch
    Knoten verdraengen, ist das laut Auftrag ein zu meldendes Ergebnis, keine
    nachtraeglich wegjustierte Unwucht (Konsil-Review 2026-08-07 vor der
    Umsetzung, s. Lehre-Suche im Chronist-Log).

    Normen (norm_rang gesetzt) mit gilt_ab/gilt_bis werden gegen `stichtag`
    (ISO, Vorgabe: jetzt) geprueft: abgelaufene oder noch nicht in Kraft
    getretene rutschen ans Ende (nachrangig, nicht verborgen) und tragen
    "geltung"/"gilt_ab"/"gilt_bis" im Ergebnis. Mit nur_geltende=True werden
    sie ganz ausgeblendet. Fakten (norm_rang IS NULL) sind davon unberuehrt.
    Lehren kennen keine Geltungsdauer -- sie stehen immer im vorrangigen Teil.

    Lehren-Filter: nur status='active' (gleiche Vorgabe wie lesson_query()'s
    Default) -- erledigte/eskalierte Lehren tauchen sonst in einer Suche auf,
    die lesson_query() bewusst verbirgt. lesson_query() selbst bleibt
    UNVERAENDERT (andere Frage: Typ-/Projektfilter, keine Rangliste)."""
    stichtag = stichtag or now_iso()
    conn = get_db()
    log_access(conn, None, "search", query=query, project_id=scope,
               actor=actor, model=model, session=session, status="started")
    fts_query = _or_query(query)
    if not fts_query:
        log_access(conn, None, "search", query=query, project_id=scope,
                   actor=actor, model=model, session=session)
        conn.close()
        return {"query": query, "scope": scope, "results": [], "count": 0}

    if scope == "all":
        fts_rows = conn.execute(
            """SELECT n.id, n.path, n.title, n.summary, n.project_id, n.norm_rang, n.gilt_ab, n.gilt_bis, n.abgeleitet_von
               FROM knowledge_fts f
               JOIN knowledge_nodes n ON f.rowid = n.rowid
               WHERE knowledge_fts MATCH ? AND n.zurueckgezogen = 0
               ORDER BY rank""",
            (fts_query,)
        ).fetchall()
        allowed_node_ids = None
        fts_lesson_rows = conn.execute(
            """SELECT l.id, l.description, l.type, l.severity, l.projects
               FROM lessons_fts f
               JOIN lessons_learned l ON f.rowid = l.rowid
               WHERE lessons_fts MATCH ? AND l.status = 'active'
               ORDER BY rank""",
            (fts_query,)
        ).fetchall()
        allowed_lesson_ids = None
    else:
        fts_rows = conn.execute(
            """SELECT n.id, n.path, n.title, n.summary, n.project_id, n.norm_rang, n.gilt_ab, n.gilt_bis, n.abgeleitet_von
               FROM knowledge_fts f
               JOIN knowledge_nodes n ON f.rowid = n.rowid
               WHERE knowledge_fts MATCH ? AND n.zurueckgezogen = 0 AND n.project_id IN ('shared', ?)
               ORDER BY rank""",
            (fts_query, scope)
        ).fetchall()
        allowed_node_ids = {r["id"] for r in conn.execute(
            "SELECT id FROM knowledge_nodes WHERE project_id IN ('shared', ?)", (scope,)
        )}
        fts_lesson_rows = conn.execute(
            """SELECT l.id, l.description, l.type, l.severity, l.projects
               FROM lessons_fts f
               JOIN lessons_learned l ON f.rowid = l.rowid
               WHERE lessons_fts MATCH ? AND l.status = 'active'
                 AND (l.projects LIKE '%"shared"%'
                      OR l.projects LIKE '%"systemweit"%'
                      OR l.projects LIKE ?)
               ORDER BY rank""",
            (fts_query, f'%"{scope}"%')
        ).fetchall()
        allowed_lesson_ids = {r["id"] for r in conn.execute(
            "SELECT id FROM lessons_learned WHERE status = 'active' "
            "AND (projects LIKE '%\"shared\"%' OR projects LIKE ?)", (f'%"{scope}"%',)
        )}

    by_id = {r["id"]: r for r in fts_rows}
    by_id_lessons = {r["id"]: r for r in fts_lesson_rows}
    fts_ordered_ids = [r["id"] for r in fts_rows]
    fts_lesson_ids = [r["id"] for r in fts_lesson_rows]
    # Stichwort-Rangfolge ueber beide Sorten: RRF auf Rangposition statt auf
    # den (zwischen den zwei FTS-Tabellen unvergleichbaren) bm25-Rohwerten --
    # siehe Docstring oben. Bei fts_lesson_ids == [] (keine Lehren-Treffer)
    # ist rrf_fuse(A, []) == A, also unveraendert wie vor diesem Auftrag.
    keyword_ordered_ids = embeddings.rrf_fuse(fts_ordered_ids, fts_lesson_ids, embedding_weight=1.0)

    query_vec = embeddings.embed_text(query)
    emb_node_ids = _embedding_ranking(conn, "node", query_vec, allowed_node_ids) if query_vec else []
    emb_lesson_ids = _embedding_ranking(conn, "lesson", query_vec, allowed_lesson_ids) if query_vec else []
    embedding_ordered_ids = embeddings.rrf_fuse(emb_node_ids, emb_lesson_ids, embedding_weight=1.0)

    final_ids = _fuse_with_keyword_floor(keyword_ordered_ids, embedding_ordered_ids, max_results)

    missing = [i for i in final_ids if i not in by_id and i not in by_id_lessons]
    if missing:
        # Beide Tabellen abfragen statt am "L-"-Praefix zu raten: 4 Lehren im
        # Bestand tragen noch die alte, praefixlose ID-Form (vor der
        # L-<hex>-Konvention) -- eine Praefix-Heuristik wuerde genau diese
        # beim Nachladen als Knoten missverstehen und stumm verlieren.
        placeholders = ",".join("?" for _ in missing)
        for r in conn.execute(
            f"SELECT id, path, title, summary, project_id, norm_rang, gilt_ab, gilt_bis, abgeleitet_von FROM knowledge_nodes WHERE id IN ({placeholders}) AND zurueckgezogen = 0",
            missing
        ):
            by_id[r["id"]] = r
        for r in conn.execute(
            f"SELECT id, description, type, severity, projects FROM lessons_learned WHERE id IN ({placeholders}) AND status = 'active'",
            missing
        ):
            by_id_lessons[r["id"]] = r

    vorrang, nachrangig = [], []
    for i in final_ids:
        if i in by_id:
            row = by_id[i]
            entry = {"kind": "node", "id": row["id"], "path": row["path"], "title": row["title"],
                      "summary": row["summary"], "project": row["project_id"],
                      # Kennung, NICHT aufgeloest -- siehe schema.sql-Kommentar an
                      # knowledge_nodes.abgeleitet_von (ADR-027 Nachtrag 4).
                      "abgeleitet_von": row["abgeleitet_von"]}
            geltung = _geltung_status(row["norm_rang"], row["gilt_ab"], row["gilt_bis"], stichtag)
            if geltung in ("abgelaufen", "noch_nicht_in_kraft"):
                if nur_geltende:
                    continue
                entry["geltung"] = geltung
                entry["gilt_ab"] = row["gilt_ab"]
                entry["gilt_bis"] = row["gilt_bis"]
                nachrangig.append(entry)
            else:
                vorrang.append(entry)
        elif i in by_id_lessons:
            row = by_id_lessons[i]
            # Keine Geltungsdauer bei Lehren -- immer vorrangig (kein
            # nachrangig-Zweig, siehe Docstring).
            vorrang.append({"kind": "lesson", "id": row["id"], "type": row["type"],
                             "severity": row["severity"], "summary": row["description"],
                             "project": json.loads(row["projects"]) if row["projects"] else []})
    results = vorrang + nachrangig
    if not results:
        _log_zero_hit(query, cwd=cwd, session=session)
    log_access(conn, results[0].get("path") if results else None, "search", query=query,
               project_id=scope, actor=actor, model=model, session=session)
    conn.close()
    return {"query": query, "scope": scope, "results": results, "count": len(results)}


SLUG_MAX_LEN = 40
_SLUG_CHAR_RE = re.compile(r"[^a-z0-9]+")


def _slugify(title: str) -> str:
    """Faltet deutsche Umlaute (fold_de), zerlegt uebrige Akzentzeichen
    (z.B. 'café' -> 'cafe') per NFKD-Normalisierung, ersetzt alles ausser
    [a-z0-9] durch '-', zieht Mehrfach-Trennstriche zusammen und kuerzt an
    der Wortgrenze statt hart bei SLUG_MAX_LEN mitten im Wort (Live-Befund:
    '...einstellungseb'). Nur ein einzelnes Wort, das schon laenger als
    SLUG_MAX_LEN ist, wird hart geschnitten -- sonst bliebe nichts uebrig."""
    decomposed = unicodedata.normalize("NFKD", fold_de(title))
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    raw = _SLUG_CHAR_RE.sub("-", without_accents).strip("-")
    raw = re.sub(r"-+", "-", raw)
    # ADR-032: ein Slug von GENAU SLUG_MAX_LEN Zeichen ist knowledge_lint.py's
    # Signal fuer verdaechtige Kappung (find_path_hygiene) -- auch wenn raw
    # zufaellig genau SLUG_MAX_LEN lang ist, OHNE dass ueberhaupt gekappt
    # wurde (kein Abschneiden, reiner Zufall der Wortlaengen). Der Vergleich
    # laeuft deshalb gegen cap = SLUG_MAX_LEN - 1, nicht SLUG_MAX_LEN selbst
    # -- sonst erzeugt genau dieser Randfall weiterhin den Fund, den die
    # Kappungslogik darunter vermeiden soll.
    cap = SLUG_MAX_LEN - 1
    if len(raw) <= cap:
        return raw
    words = raw.split("-")
    if len(words[0]) >= cap:
        return words[0][:cap]
    out = words[0]
    for w in words[1:]:
        if len(out) + 1 + len(w) > cap:
            break
        out += "-" + w
    return out


def _normalize_path(path: str) -> str:
    """Saeubert jedes Segment eines Pfades wie _slugify() einen Titel.
    NUR fuer einen Ast, der gerade neu entsteht (neuer_ast=True in
    knowledge_add) -- nie fuer einen bereits bestehenden Pfad, der sonst
    unauffindbar wuerde (andere Knoten/Relationen verweisen darauf).
    Leeres Segment (z.B. ein Segment aus reinen Satzzeichen) faellt auf das
    Rohsegment zurueck, statt den Ast stillschweigend zu verkuerzen."""
    segs = [seg for seg in path.split("/") if seg]
    cleaned = [_slugify(seg) or seg for seg in segs]
    return "/" + "/".join(cleaned)


# ─── P5: [[wikilink]] -> knowledge_relations ────────────────────────────────
# Billigster Anfang fuer das Karpathy-LLM-Wiki-Muster (eine Quelle beruehrt
# beim Einpflegen 10-15 Seiten statt eine einzelne anzulegen): die
# [[wikilink]]-Schreibweise aus den Memory-Dateien wird beim Schreiben zu
# echten Kanten aufgeloest, keine Aehnlichkeit wird erraten.
_WIKILINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")


def _extract_wikilinks(content: str) -> list[str]:
    """Deduplizierte, getrimmte Linkziele in Ursprungsreihenfolge."""
    targets = (m.strip() for m in _WIKILINK_RE.findall(content or ""))
    return list(dict.fromkeys(t for t in targets if t))


def _resolve_wikilink(conn: sqlite3.Connection, target: str) -> sqlite3.Row | None:
    """ziel darf Pfad oder Titel sein (Titel case-insensitiv)."""
    return conn.execute(
        "SELECT id, path, title FROM knowledge_nodes WHERE path = ? OR LOWER(title) = LOWER(?)",
        (target, target),
    ).fetchone()


def _sync_wikilinks(conn: sqlite3.Connection, source_path: str, content: str, *,
                    actor: str | None = None, model: str | None = None,
                    session: str | None = None) -> dict:
    """Legt fuer jedes aufloesbare [[ziel]] im content eine knowledge_relations-
    Zeile an. Unaufgeloeste Verweise werden NICHT geschrieben, sondern als
    Hinweis zurueckgegeben (ein Verweis ins Leere zeigt auf einen noch zu
    schreibenden Knoten, ist kein Fehler). Ein Selbstverweis erzeugt keine
    Kante -- deckt sich mit knowledge_relation_add(), das Selbstkanten
    ablehnt. Der Aufrufer ist verantwortlich, vorher bestehende Kanten dieses
    Knotens zu loeschen, falls es ein Update ist (siehe knowledge_update)."""
    creator, model, session = _identity(actor, model, session)
    relations_created: list[str] = []
    unresolved_links: list[str] = []
    seen_targets: set[str] = set()
    for target in _extract_wikilinks(content):
        row = _resolve_wikilink(conn, target)
        if not row:
            unresolved_links.append(target)
            continue
        if row["path"] == source_path or row["path"] in seen_targets:
            continue
        seen_targets.add(row["path"])
        timestamp = now_iso()
        conn.execute(
            """INSERT INTO knowledge_relations
               (id, source_path, target_path, relation_type, confidence, weight,
                evidence, source, creator, model, session, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (f"R-{uuid.uuid4().hex[:8]}", source_path, row["path"], "references",
             0.8, 1.0, f"[[{target}]] im content", "wikilink",
             creator, model, session, timestamp, timestamp),
        )
        relations_created.append(row["path"])
    return {"relations_created": relations_created, "unresolved_links": unresolved_links}


def _ensure_ast_chain(conn, missing_path: str, triggering_child_path: str,
                      project_id: str) -> None:
    """Legt jede fehlende Zwischenstufe von der Wurzel bis missing_path an
    (wie mkdir -p). Idempotent: vorhandene Stufen bleiben unangetastet.
    Titel = Pfadsegment, source kennzeichnet die automatische Herkunft samt
    dem Kind, das die Anlage ausgeloest hat."""
    current = ""
    for seg in [p for p in missing_path.split("/") if p]:
        current = f"{current}/{seg}"
        if conn.execute("SELECT 1 FROM knowledge_nodes WHERE path = ?", (current,)).fetchone():
            continue
        parent = current.rsplit("/", 1)[0] or "/"
        created_at = now_iso()
        conn.execute(
            """INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, content, level, tags, source, created_at, updated_at, norm_entscheidung, norm_entschieden_von, norm_entschieden_am, norm_entschieden_grund)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4())[:8], current, parent, project_id, seg,
             f"Automatisch erzeugter Astknoten fuer {seg}", "",
             current.count("/") - 1, json.dumps([]),
             f"neuer_ast=True, automatisch erzeugt durch {triggering_child_path}",
             created_at, created_at,
             # keine_norm (Auftrag 2026-08-08): ein automatisch erzeugter
             # Astknoten ist nie eine Norm -- die Entscheidung ist hier so
             # eindeutig wie die Herkunft selbst. norm_entschieden_*
             # (Nachtrag 2026-08-08): Entscheider ist der Server-Mechanismus
             # selbst, kein Aufrufer-Identitaetsargument vorhanden hier.
             "keine_norm", "system:_ensure_ast_chain", created_at,
             "automatisch erzeugter Astknoten -- kann keine Norm sein"),
        )


def _validate_geltung(norm_rang: int | None, gilt_ab: str | None, gilt_bis: str | None) -> str | None:
    """Prueft die drei Normschicht-Felder (schema.sql, N2/N3). Alle drei
    bleiben optional -- der Normalfall ist ein Fakt ohne Normangaben, NULL
    in norm_rang heisst weiterhin "kein Norm, sondern Fakt" (Plan §2).
    Nur bei gesetztem gilt_ab/gilt_bis wird ueberhaupt geparst, sonst No-op.
    Gibt eine sprechende Fehlermeldung zurueck oder None (gueltig)."""
    for name, value in (("gilt_ab", gilt_ab), ("gilt_bis", gilt_bis)):
        if value is None:
            continue
        try:
            datetime.fromisoformat(value)
        except ValueError:
            return f"{name} ist kein gueltiges ISO-8601-Datum/Zeitstempel: {value!r}"
    if gilt_ab is not None and gilt_bis is not None and gilt_bis < gilt_ab:
        return f"gilt_bis ({gilt_bis!r}) liegt vor gilt_ab ({gilt_ab!r})."
    return None


def _validate_norm_entschieden_grund(norm_entschieden_grund: str | None) -> str | None:
    """Pflicht GENAU dann, wenn eine Entscheidung neu GETROFFEN wird (nicht
    bei einer reinen Konsistenzpruefung einer bereits gespeicherten
    Entscheidung -- siehe knowledge_update()) -- Nachtrag 2026-08-08,
    Betreiber-Nachfrage "wer hat entschieden?". Wie grund bei
    knowledge_zurueckziehen(): eine Entscheidung ohne Begruendung waere
    dieselbe Blackbox. Wer entschieden hat (norm_entschieden_von) wird NICHT
    hier, sondern von den Aufrufern aus _identity() aufgeloest (wie actor)."""
    if not norm_entschieden_grund or not norm_entschieden_grund.strip():
        return ("norm_entschieden_grund fehlt: eine Norm-Entscheidung verlangt eine Begruendung, "
                "wie bei knowledge_zurueckziehen()'s grund -- wer entscheidet und warum?")
    return None


def _validate_norm_entscheidung(norm_entscheidung: str | None, norm_rang: int | None,
                                 gilt_ab: str | None, gilt_bis: str | None) -> str | None:
    """Erzwingt die Entscheidung aus dem Auftrag 2026-08-08: 'offen' (nie
    entschieden) ist fuer NEUE Knoten kein zulaessiger Wert, nur Altbestand
    traegt ihn (siehe schema.sql-Spaltenkommentar). Prueft ausserdem die
    Konsistenz zu norm_rang/gilt_ab/gilt_bis -- dieselben drei Regeln wie die
    DB-Trigger in NORM_ENTSCHEIDUNG_TRIGGERS_SQL, hier VORAB mit sprechendem
    Text statt der rohen sqlite3.IntegrityError aus RAISE(ABORT). Aufrufer
    muss norm_rang (und bei Bedarf gilt_ab/gilt_bis) VOR diesem Aufruf schon
    final gesetzt haben (inkl. ADR-034-Ableitung), sonst prueft diese
    Funktion gegen einen Zwischenstand. Prueft NICHT norm_entschieden_grund
    (siehe _validate_norm_entschieden_grund) -- getrennt, weil diese Funktion
    auch fuer die reine Konsistenzpruefung EINER SCHON GESPEICHERTEN
    Entscheidung wiederverwendet wird (knowledge_update(), Fall "Zeile war
    schon entschieden")."""
    if norm_entscheidung not in ALLOWED_NORM_ENTSCHEIDUNG:
        return (f"norm_entscheidung fehlt oder unbekannt: {norm_entscheidung!r}. Beim Anlegen "
                f"muss entschieden werden, ob dieser Knoten eine Norm ist. Erlaubt: "
                f"{sorted(ALLOWED_NORM_ENTSCHEIDUNG)} (keine_norm=Fakt ohne Rang, "
                f"norm_befristet=Norm mit Enddatum, norm_unbefristet=Norm ohne Enddatum).")
    if norm_entscheidung == "keine_norm":
        if norm_rang is not None:
            return "norm_entscheidung=keine_norm aber norm_rang gesetzt: widerspruechlich -- norm_rang weglassen oder norm_befristet/norm_unbefristet waehlen."
        return None
    # norm_befristet / norm_unbefristet
    if norm_rang is None:
        return f"norm_entscheidung={norm_entscheidung!r} verlangt norm_rang (1=global, 2=hub, 3=ADR)."
    if gilt_ab is None:
        return f"norm_entscheidung={norm_entscheidung!r} verlangt gilt_ab (ab wann die Norm gilt)."
    if norm_entscheidung == "norm_befristet" and gilt_bis is None:
        return "norm_entscheidung=norm_befristet verlangt gilt_bis; fuer unbefristet norm_unbefristet waehlen."
    if norm_entscheidung == "norm_unbefristet" and gilt_bis is not None:
        return "norm_entscheidung=norm_unbefristet aber gilt_bis gesetzt: widerspruechlich -- norm_befristet waehlen."
    return None


def _validate_anlass(anlass: str) -> str | None:
    """Sprechende Ablehnung statt stillem Erfolg oder 500 bei unbekanntem
    anlass (Auftrag 2026-08-06). Gibt eine Fehlermeldung mit der erlaubten
    Liste zurueck, oder None wenn gueltig."""
    if anlass not in ALLOWED_ANLASS:
        return (f"anlass unbekannt: {anlass!r}. Erlaubt: {sorted(ALLOWED_ANLASS)}.")
    return None


def _validate_lesson_type(type_: str) -> str | None:
    """Sprechende Ablehnung statt stillem Anlegen bei unbekanntem lesson type
    (Auftrag 2026-08-07, Befund: type='voellig_unbekannter_typ' wurde bisher
    klaglos angenommen). Gibt eine Fehlermeldung mit der erlaubten Liste
    zurueck, oder None wenn gueltig."""
    if type_ not in ALLOWED_LESSON_TYPES:
        return (f"type unbekannt: {type_!r}. Erlaubt: {sorted(ALLOWED_LESSON_TYPES)}.")
    return None


# \w{3,}: kurze Fuellwoerter (der/die/aus/of/and/...) sind in praktisch jeder
# Sprache 1-2 Zeichen lang, darum als Rauschgrenze fuer den Wortlauf-
# Vergleich geeignet, ohne eine Sprache konkret zu benennen.
_QUELLTOKEN_RE = re.compile(r"\w{3,}", re.UNICODE)
_MIN_ZITAT_LAUF = 6  # so viele Woerter am Stueck woertlich = Zitat, kein Zufall
# Ein Pfad/eine URL/ein Hash/ein Datum ist eine ueberpruefbare Fundstelle,
# unabhaengig davon, wie sie sprachlich eingeleitet wird -- rein an der
# ZEICHENFORM erkannt (Schraegstrich, Dateiendung, URL-Schema, Hex-Lauf,
# ISO-Datum), nicht am umgebenden Wortlaut.
_FUNDSTELLE_RE = re.compile(
    r"https?://\S+|[^\s]+/[^\s]+|\.[A-Za-z0-9]{2,4}\b|\b[0-9a-fA-F]{7,40}\b|"
    r"\b\d{4}-\d{2}-\d{2}\b"
)


def _inhaltstokens(*teile: str) -> list:
    return [t.lower() for t in _QUELLTOKEN_RE.findall(" ".join(t or "" for t in teile))]


def _laengster_gemeinsamer_lauf(a: list, b: list) -> int:
    return difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(
        0, len(a), 0, len(b)
    ).size


def _validate_source_provenance(source: str, title: str, summary: str, content: str) -> str | None:
    """Lehnt eine Herkunft ab, die im Kern nur den Knoten selbst zitiert
    (Lehre L-7aad34, Auftrag 2026-08-06, Befund 1 -- Tautologie: source
    'erzeugt aus Rohmaterial ... "Man hoert, dass die Sperrandrohung ..."'
    wiederholte woertlich genau den Inhalt, den sie belegen sollte).

    STRUKTURELL statt Wortliste (sprachunabhaengig, siehe Modul-Docstring von
    einschleusung.py fuer dieselbe Abwaegung an anderer Stelle): geprueft wird
    NICHT irgendein Bedeutungs-Ueberlappung (die schlaegt staendig zu Unrecht
    an -- ein Dateipfad wie 'projekt-x/.../2026-08-05-abschlussbericht.md'
    teilt zwangslaeufig Themenwoerter mit dem Titel, das ist erwuenscht, kein
    Zitieren-sich-selbst), sondern ein LAUF von mindestens sechs
    aufeinanderfolgenden Woertern, die woertlich sowohl in source als auch in
    Titel/Zusammenfassung/Inhalt DESSELBEN Knotens vorkommen. Reiner
    Zeichenfolgen-Abgleich (difflib, laengster gemeinsamer Block), kein
    Woerterbuch -- schlaegt in jeder Sprache/Schrift gleich an.

    ZWEITE BEDINGUNG, das eigentliche Herzstueck gegen Falschalarme (Auftrag
    Punkt 3, Falschalarm teurer als Durchlass): ein langer Wortlauf allein
    genuegt NICHT. Erst wenn source zusaetzlich KEINE ueberpruefbare
    Fundstelle traegt (kein Pfad, keine URL, kein Hash, kein Datum -- an der
    Zeichenform erkannt, s. _FUNDSTELLE_RE), gilt der Lauf als Beleg, dass
    source nichts ausserhalb des Knotens nennt. Ein Dateipfad, der zufaellig
    Themenwoerter mit dem Titel teilt, hat trotzdem eine Fundstelle und geht
    frei durch -- gemessen an den 290 Bestandsknoten der Produktions-DB, vor
    dieser zweiten Bedingung waren es 22 Falschalarme allein durch geteilte
    Pfad-/Dateinamen-Woerter.

    Bewusst NICHT erfasst: eine knappe, aber nicht-zitierende Angabe wie
    'Geruecht aus der Kantine' (kein langer woertlicher Lauf mit dem Inhalt,
    also greift die erste Bedingung nie) -- ob eine solche Kurzform generell
    genug Substanz hat, ist ohne Sprachverstaendnis nicht zuverlaessig zu
    entscheiden und bleibt bewusst durch, statt hart abgelehnt zu werden."""
    quelle = _inhaltstokens(source)
    if len(quelle) < _MIN_ZITAT_LAUF:
        return None  # zu kurz fuer einen verlaesslichen Zitat-Befund
    beleg = _inhaltstokens(title, summary, content)
    lauf = _laengster_gemeinsamer_lauf(quelle, beleg)
    if lauf < _MIN_ZITAT_LAUF:
        return None
    if _FUNDSTELLE_RE.search(source):
        return None  # traegt eine ueberpruefbare Fundstelle -- kein Verdacht
    return (
        f"source wirkt selbstbezueglich: {lauf} Woerter am Stueck stehen "
        "woertlich sowohl in source als auch im eigenen Titel/Zusammenfassung/"
        "Inhalt dieses Knotens, ohne dass source einen Pfad, eine URL, einen "
        "Hash oder ein Datum nennt. Herkunft ausserhalb des Knotens benennen "
        "(Datei, Person, Ort, URL, Sitzungsprotokoll), nicht den Inhalt "
        "zurueckspiegeln."
    )


def _erzeuge_source_aus_ableitung(conn: sqlite3.Connection, kennung: str) -> tuple[str | None, str | None]:
    """Baut den Herkunftstext fuer abgeleitet_von aus der ART des
    Quellknotens -- NIE aus dessen title/summary/content, denn genau die
    tragen den Inhalt, der nicht durchsickern soll (ADR-027 Nachtrag 4).
    'Art' = parent_path (Kategorie/Ast), norm_rang (Norm oder Fakt), tags.
    Gibt (source_text, None) oder (None, fehlertext) zurueck."""
    row = conn.execute(
        "SELECT path, parent_path, norm_rang, tags FROM knowledge_nodes WHERE id = ? OR path = ?",
        (kennung, kennung)
    ).fetchone()
    if not row:
        return None, (f"abgeleitet_von zeigt auf keinen vorhandenen Knoten: {kennung!r}")
    kategorie = row["parent_path"] or "/"
    art = "Norm" if row["norm_rang"] is not None else "Fakt"
    tags = json.loads(row["tags"]) if row["tags"] else []
    tag_teil = f", Tags {tags}" if tags else ""
    return (
        f"abgeleitet von Knoten unter {kategorie} (Art: {art}{tag_teil})",
        None,
    )


def _rebuild_node_embedding(conn: sqlite3.Connection, node_id: str, project_id: str,
                            path: str, title: str, summary: str, content: str | None) -> None:
    """Baut den Vektor eines Knotens SOFORT beim Schreiben (ADR-032 Gruppe 1)
    statt die Luecke bis zum naechsten build_embeddings.py-Lauf offenzulassen.
    Text-Formel identisch zu dessen Hauptschleife -- sonst zaehlt der Kurator
    die frische Zeile weiter als veraltet (find_vector_gaps vergleicht nur
    Zeitstempel, nicht Text, also muss nur die Existenz/Aktualitaet stimmen).
    Schlaegt embed_text() fehl (Ollama nicht erreichbar, Timeout) wird NICHTS
    geworfen -- der Schreibvorgang bleibt gueltig, die Luecke bleibt bestehen
    und zeigt sich weiter im naechsten Kurator-Trockenlauf. Kurzer Default-
    Timeout (embeddings.embed_text(), 5s), damit ein totes Modell einen
    Schreibvorgang nicht spuerbar verzoegert.

    Gleiches gilt, wenn embed_text() liefert, der INSERT aber am Trigger
    knowledge_embeddings_model_check_bi scheitert (Auftrag 2026-08-07,
    veralteter Prozess mit fremdem Modell im Speicher): sqlite3.IntegrityError
    wird abgefangen, der Knoten bleibt geschrieben, nur die Einbettungs-Zeile
    fehlt -- derselbe Vertrag wie beim vec is None-Fall oben."""
    text = f"{path}\n{title}\n{summary}\n{content or ''}"
    vec = embeddings.embed_text(text)
    if vec is None:
        return
    try:
        conn.execute(
            "INSERT OR REPLACE INTO knowledge_embeddings (kind, ref_id, project_id, model, dim, vector, updated_at) "
            "VALUES ('node', ?, ?, ?, ?, ?, ?)",
            (node_id, project_id, embeddings.DEFAULT_EMBED_MODEL, len(vec), embeddings.pack_embedding(vec), now_iso()),
        )
    except sqlite3.IntegrityError:
        pass


def _rebuild_lesson_embedding(conn: sqlite3.Connection, lesson_id: str, node_path: str | None,
                              projects_json: str | None, description: str,
                              root_cause: str | None, prevention: str | None) -> None:
    """Wie _rebuild_node_embedding, fuer lessons_learned -- inkl. Bereichs-
    Fanout (eine Embedding-Zeile je Bereich, gleicher Vektor) ueber
    build_embeddings.resolve_lesson_projects(), nicht danebengebaut.

    Trigger-Ablehnung (Modellsperre, siehe _rebuild_node_embedding) wird je
    Bereichs-Zeile abgefangen -- eine abgelehnte Zeile darf die uebrigen
    Bereiche und vor allem die Lehre selbst nicht mitreissen."""
    zuordnung = node_path or projects_json or ""
    text = f"{zuordnung}\n{description}\n{root_cause or ''}\n{prevention or ''}"
    vec = embeddings.embed_text(text)
    if vec is None:
        return
    packed = embeddings.pack_embedding(vec)
    ts = now_iso()
    for proj in build_embeddings.resolve_lesson_projects(projects_json):
        try:
            conn.execute(
                "INSERT OR REPLACE INTO knowledge_embeddings (kind, ref_id, project_id, model, dim, vector, updated_at) "
                "VALUES ('lesson', ?, ?, ?, ?, ?, ?)",
                (lesson_id, proj, embeddings.DEFAULT_EMBED_MODEL, len(vec), packed, ts),
            )
        except sqlite3.IntegrityError:
            pass


# Auftrag 2026-08-09: project_id-Default 'shared' verschluckte 26 von 384
# Knoten, die ihr path eindeutig einem Projekt zuordnet (z.B.
# /apps/fahrtenbuch/...). Der bekannte-Projekte-Katalog wird NICHT
# hartcodiert (Enum war schon einmal veraltet, siehe test_project_id_enum_
# stale.py) und NICHT bei jedem Aufruf per SELECT DISTINCT neu gezogen --
# ein Prozess-Cache je DB-Pfad reicht, weil sich die Projektliste innerhalb
# eines Laufs praktisch nie aendert. Key ist der DB-Pfad, nicht global,
# damit Tests mit eigener temp_db sich nicht gegenseitig verunreinigen.
_BEKANNTE_PROJEKTE_CACHE: dict[str, set[str]] = {}


def _bekannte_projekte(conn: sqlite3.Connection) -> set[str]:
    key = str(DB_PATH)
    projekte = _BEKANNTE_PROJEKTE_CACHE.get(key)
    if projekte is None:
        projekte = {r[0] for r in conn.execute(
            "SELECT DISTINCT project_id FROM knowledge_nodes WHERE project_id != 'shared'")}
        _BEKANNTE_PROJEKTE_CACHE[key] = projekte
    return projekte


def _projekt_aus_pfad(parent_path: str, projekte: set[str]) -> str:
    """Erstes Pfadsegment von parent_path, das einem bekannten Projekt
    entspricht. Container-Segmente wie 'apps'/'ops' werden dabei einfach
    uebersprungen (kein Projekt, kein Treffer): /apps/fahrtenbuch/... ->
    'fahrtenbuch', nicht 'apps'. Kein Treffer irgendwo im Pfad: 'shared' --
    keine Erfindung, siehe Auftrag Negativfall '/methodik'."""
    for segment in (parent_path or "").strip("/").split("/"):
        if segment and segment in projekte:
            return segment
    return "shared"


def knowledge_add(parent_path: str, title: str, summary: str,
                  content: str = "", project_id: str | None = None,
                  tags: list | None = None, source: str = "", *,
                  neuer_ast: bool = False,
                  norm_rang: int | None = None, gilt_ab: str | None = None,
                  gilt_bis: str | None = None, anlass: str = "unbekannt",
                  norm_entscheidung: str | None = None,
                  norm_entschieden_grund: str | None = None,
                  abgeleitet_von: str | None = None,
                  gattung: str | None = None,
                  actor: str | None = None, model: str | None = None,
                  session: str | None = None) -> dict:
    """Add a new knowledge node to the tree. Rejects an unknown parent_path
    unless neuer_ast=True (see U1 im Plan 2026-08-05, P1: erfundene Aeste
    streuten Wissen an Stellen, die nie wieder abgerufen wurden).

    anlass: was hat den Eintrag ausgeloest -- siehe ALLOWED_ANLASS oben.
    'selbst'/'betreiber' sind selbstberichtet vom Aufrufer, nicht geprueft;
    'hook'/'skript' objektiv, weil der Aufrufweg sie kennt. Unbekannter Wert
    wird abgelehnt (sprechender Fehler, kein stiller Erfolg).

    norm_entscheidung: PFLICHT (Auftrag 2026-08-08) -- keine_norm (Fakt,
    kein Rang), norm_befristet (Norm mit gilt_bis) oder norm_unbefristet
    (Norm ohne Ende). Fehlt sie oder widerspricht sie norm_rang/gilt_ab/
    gilt_bis, wird der Aufruf abgelehnt -- siehe _validate_norm_entscheidung.
    Kein Vorgabewert: 'offen' (nie entschieden) ist ausschliesslich der
    Zustand des Altbestands vor diesem Feld, niemals eine neue Entscheidung.

    norm_entschieden_grund: PFLICHT sobald norm_entscheidung gesetzt wird
    (Nachtrag 2026-08-08) -- wie grund bei knowledge_zurueckziehen(), eine
    Freitext-Begruendung, warum diese Entscheidung so gefallen ist. Wer
    entschieden hat (norm_entschieden_von) wird aus actor aufgeloest --
    AUSSER herkunft_normentscheider.ist_urheber_betreiber(source) sagt, dass
    source einen belegten Betreiber-Urheber zeigt (CLAUDE.md-Import): dann
    ist der Betreiber der Entscheider, nicht die Maschine, die ihn nur
    abgeschrieben hat (Auftrag 2026-08-09, Befund: 31 von 37 Rang-1/2-Normen
    trugen faelschlich eine Maschine).

    project_id: ohne Angabe (None) wird aus parent_path abgeleitet -- das
    erste Pfadsegment, das einem bereits im Bestand vorkommenden Projekt
    entspricht (siehe _projekt_aus_pfad). Kein Treffer: 'shared', wie bisher.
    Ausdruecklich uebergeben (auch als leerer String) gewinnt immer gegen
    die Ableitung (Auftrag 2026-08-09, Befund: 26 von 336 'shared'-Knoten
    waren aus ihrem eigenen Pfad einem Projekt zuzuordnen).

    abgeleitet_von: Kennung (id oder path) eines vorhandenen Quellknotens
    (ADR-027 Nachtrag 4, Lehre L-adfb33). Gesetzt heisst: source wird VOM
    SYSTEM aus der Art des Quellknotens erzeugt, der Aufrufer darf source
    selbst nicht mitliefern -- "dem Schreiber die Feder nehmen", denn ein
    selbst formulierter Herkunftstext kann leaken, egal wie gut die
    Zitat-Pruefung unten ist."""
    if project_id is None:
        _pid_conn = get_db()
        project_id = _projekt_aus_pfad(parent_path, _bekannte_projekte(_pid_conn))
        _pid_conn.close()

    anlass_fehler = _validate_anlass(anlass)
    if anlass_fehler:
        conn = get_db()
        log_access(conn, None, "add", project_id=project_id, actor=actor, model=model,
                   session=session, status="rejected", query="anlass_ungueltig")
        conn.close()
        return {"error": anlass_fehler}

    # Schreiber gehoert an den Datensatz, nicht nur ins Protokoll (Auftrag
    # 2026-08-06, Mangel: kein Feld fuer den Schreiber auf knowledge_nodes).
    # Vor jedem Weiterreichen aufgeloest (nie None, siehe _identity()), damit
    # die INSERT unten den echten Wert traegt statt ihn nochmal in log_access
    # zu verstecken.
    actor, model, session = _identity(actor, model, session)

    fixed = unmangle_knowledge_fields({
        "title": title, "summary": summary, "content": content, "tags": tags, "source": source,
    })
    title, summary = fixed["title"], fixed["summary"]
    content, tags, source = fixed["content"], fixed["tags"], fixed["source"]

    geltung_fehler = _validate_geltung(norm_rang, gilt_ab, gilt_bis)
    if geltung_fehler:
        conn = get_db()
        log_access(conn, None, "add", project_id=project_id, actor=actor, model=model,
                   session=session, status="rejected", query="geltung_ungueltig")
        conn.close()
        return {"error": geltung_fehler}

    conn = get_db()

    if abgeleitet_von is not None:
        if source.strip():
            log_access(conn, parent_path, "add", project_id=project_id, actor=actor, model=model,
                       session=session, status="rejected", query="source_und_abgeleitet_von_exklusiv")
            conn.close()
            return {
                "error": "source und abgeleitet_von schliessen sich aus: ist abgeleitet_von "
                         "gesetzt, erzeugt das System den Herkunftstext selbst -- kein eigenes "
                         "source mitgeben.",
            }
        erzeugte_source, ableitung_fehler = _erzeuge_source_aus_ableitung(conn, abgeleitet_von)
        if ableitung_fehler:
            log_access(conn, parent_path, "add", project_id=project_id, actor=actor, model=model,
                       session=session, status="rejected", query="abgeleitet_von_ungueltig")
            conn.close()
            return {"error": ableitung_fehler}
        source = erzeugte_source
    else:
        if not source.strip():
            log_access(conn, parent_path, "add", project_id=project_id, actor=actor, model=model,
                       session=session, status="rejected", query="source_fehlt")
            conn.close()
            return {
                "error": "source fehlt: Herkunft des Knotens angeben (aus welcher Datei/welchem Lauf er stammt). "
                         "Beispiel: 'erzeugt aus /pfad/zur/datei.md (Stand 2026-08-05T23:40:00+02:00)'.",
            }

        provenienz_fehler = _validate_source_provenance(source, title, summary, content)
        if provenienz_fehler:
            log_access(conn, parent_path, "add", project_id=project_id, actor=actor, model=model,
                       session=session, status="rejected", query="source_provenienz_ungueltig")
            conn.close()
            return {"error": provenienz_fehler}

    parent_path = parent_path.rstrip("/") or "/"

    # Derive path from parent + slugified title
    slug = _slugify(title)
    node_path = f"{parent_path}/{slug}" if parent_path != "/" else f"/{slug}"

    if parent_path != "/":
        parent_row = conn.execute(
            "SELECT 1 FROM knowledge_nodes WHERE path = ?", (parent_path,)
        ).fetchone()
        if not parent_row:
            if not neuer_ast:
                all_paths = [r[0] for r in conn.execute("SELECT path FROM knowledge_nodes")]
                log_access(conn, node_path, "add", project_id=project_id, actor=actor, model=model,
                           session=session, status="rejected", query="elternpfad_fehlt")
                conn.close()
                return {
                    "error": f"Elternpfad existiert nicht: {parent_path}. "
                             f"Mit neuer_ast=True bewusst einen neuen Ast anlegen.",
                    "vorhandene_pfade": difflib.get_close_matches(parent_path, all_paths, n=5),
                }
            # neuer_ast=True: fehlende Zwischenstufen mit anlegen (mkdir -p),
            # statt eine Waise zu hinterlassen -- genau die Klasse, gegen die
            # die Elternpfad-Pruefung oben gebaut wurde. ADR-032: der Ast
            # entsteht hier gerade erst, also wird er gleich sauber angelegt
            # (Pfad-Hygiene an der Schreibzeit) statt roh uebernommen zu
            # werden -- node_path deshalb NEU aus dem normalisierten
            # parent_path berechnet.
            parent_path = _normalize_path(parent_path)
            node_path = f"{parent_path}/{slug}" if parent_path != "/" else f"/{slug}"
            _ensure_ast_chain(conn, parent_path, node_path, project_id)

    # Check for duplicates
    existing = conn.execute("SELECT id FROM knowledge_nodes WHERE path = ?", (node_path,)).fetchone()
    if existing:
        log_access(conn, node_path, "add", project_id=project_id, actor=actor, model=model,
                   session=session, status="rejected", query="pfad_existiert_bereits")
        conn.close()
        return {"error": f"Node already exists at path: {node_path}", "existing_id": existing["id"]}

    # Calculate level
    level = node_path.count("/") - 1

    node_id = str(uuid.uuid4())[:8]
    log_access(conn, node_path, "add", project_id=project_id,
               actor=actor, model=model, session=session, status="started")
    created_at = now_iso()

    # ADR-034 (normrang): Rang folgt deterministisch aus source und entsteht
    # mit dem Knoten -- nur wenn der Aufrufer nicht selbst schon einen
    # norm_rang mitgegeben hat (der bleibt Vorrang). gilt_ab bekommt bei
    # Ableitung denselben Wert wie normrang.py's Batch-Lauf verwendet hat:
    # den eigenen Erfassungszeitpunkt des Knotens, kein erfundenes Datum.
    #
    # Auftrag 2026-08-08, Review-Punkt 3 (Agent acf807ee8e6756f27): die
    # Ableitung wird IMMER gerechnet, auch bei norm_entscheidung=keine_norm --
    # ein Unterdruecken wuerde einen echten Widerspruch verschlucken (source
    # sieht nach Direktive/ADR aus, Aufrufer sagt aber keine_norm). Der
    # Konflikt wird unten von _validate_norm_entscheidung erkannt (keine_norm
    # verlangt norm_rang NULL) und mit sprechendem Text abgelehnt, statt die
    # Ableitung still zu ignorieren.
    abgeleiteter_rang = None
    if norm_rang is None:
        abgeleiteter_rang = normrang.rang_fuer_source(source)
        if abgeleiteter_rang is not None:
            norm_rang = abgeleiteter_rang
            if gilt_ab is None:
                gilt_ab = created_at

    # Entscheidungspflicht (Auftrag 2026-08-08): erst HIER pruefbar, weil
    # norm_rang/gilt_ab bis eben noch durch ADR-034 automatisch ausfallen
    # konnten -- siehe _validate_norm_entscheidung-Docstring.
    entscheidung_fehler = (_validate_norm_entscheidung(norm_entscheidung, norm_rang, gilt_ab, gilt_bis)
                            or _validate_norm_entschieden_grund(norm_entschieden_grund))
    if entscheidung_fehler:
        if norm_entscheidung == "keine_norm" and abgeleiteter_rang is not None:
            entscheidung_fehler = (
                f"norm_entscheidung=keine_norm, aber source deutet per ADR-034 auf Rang "
                f"{abgeleiteter_rang} hin ({source!r}): pruefen, ob source stimmt, oder "
                f"norm_befristet/norm_unbefristet waehlen."
            )
        log_access(conn, node_path, "add", project_id=project_id, actor=actor, model=model,
                   session=session, status="rejected", query="norm_entscheidung_ungueltig")
        conn.close()
        return {"error": entscheidung_fehler}

    # Auftrag 2026-08-09: Entscheider ist der Betreiber, wenn source ihn als
    # belegten Urheber zeigt -- sonst bleibt es actor (unveraendertes
    # Verhalten). herkunft_normentscheider.ist_urheber_betreiber() sticht
    # explizit auf Fremdnorm (Gesetz/Urteil/WEG-Recht/...) nicht an, siehe
    # dortiger Selbsttest.
    norm_entschieden_von = (herkunft_normentscheider.BETREIBER
                             if herkunft_normentscheider.ist_urheber_betreiber(source)
                             else actor)

    if gattung is not None and gattung not in ALLOWED_GATTUNG:
        # Vorab und mit Klartext statt roher IntegrityError aus RAISE(ABORT) --
        # dasselbe Muster wie bei norm_entscheidung. Der Trigger bleibt die
        # eigentliche Schranke; er faengt auch Wege, die hier vorbeischreiben.
        conn.close()
        return {"error": f"gattung unzulaessig: {gattung!r}. Erlaubt sind "
                         f"{', '.join(ALLOWED_GATTUNG)}."}

    conn.execute(
        """INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, content, level, tags, source, created_at, updated_at, norm_rang, gilt_ab, gilt_bis, norm_entscheidung, norm_entschieden_von, norm_entschieden_am, norm_entschieden_grund, anlass, abgeleitet_von, actor, session, model, client, gattung, bedient_von)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (node_id, node_path, parent_path, project_id, title, summary, content,
         level, json.dumps(tags or []), source, created_at, created_at,
         norm_rang, gilt_ab, gilt_bis, norm_entscheidung, norm_entschieden_von, created_at, norm_entschieden_grund,
         anlass, abgeleitet_von, actor, session, model, _KLIENT,
         # Vorgabe kommt aus dem Schema (arbeitsbestand) -- None laesst sie
         # stehen, statt sie hier ein zweites Mal zu behaupten.
         gattung if gattung is not None else 'arbeitsbestand',
         # Aus dem Ausweis, nicht aus der Signatur: es gibt bewusst KEINEN
         # Parameter dafuer. Waere er da, koennte jeder Schreiber eine
         # menschliche Deckung behaupten.
         _bedient_von(actor))
    )
    log_access(conn, node_path, "add", project_id=project_id,
               actor=actor, model=model, session=session,
               affected_row={
                   "id": node_id, "path": node_path, "parent_path": parent_path,
                   "project_id": project_id, "title": title, "summary": summary,
                   "content": content, "level": level, "tags": tags or [],
                   "source": source, "created_at": created_at, "updated_at": created_at,
                   "norm_rang": norm_rang, "gilt_ab": gilt_ab, "gilt_bis": gilt_bis,
                   "norm_entscheidung": norm_entscheidung,
                   "anlass": anlass, "abgeleitet_von": abgeleitet_von,
                   "actor": actor, "session": session, "model": model,
               })
    wikilinks = _sync_wikilinks(conn, node_path, content, actor=actor, model=model, session=session)
    # ADR-032: Vektor sofort mitbauen statt eine vector_gaps-Luecke bis zum
    # naechsten build_embeddings.py-Lauf offenzulassen.
    _rebuild_node_embedding(conn, node_id, project_id, node_path, title, summary, content)
    conn.commit()
    conn.close()
    _check_injection_suspects("node", node_path, {"title": title, "summary": summary, "content": content})
    _check_norm_conflicts(node_id, node_path, norm_rang)
    return {"id": node_id, "path": node_path, "status": "created", "source": source, **wikilinks}


def knowledge_update(node_id: str, summary: str | None = None,
                     content: str | None = None, tags: list | None = None,
                     title: str | None = None, *,
                     norm_rang: int | None = None, gilt_ab: str | None = None,
                     gilt_bis: str | None = None, norm_entscheidung: str | None = None,
                     norm_entschieden_grund: str | None = None,
                     gattung: str | None = None,
                     actor: str | None = None, model: str | None = None,
                     session: str | None = None) -> dict:
    """Update an existing knowledge node. Like summary/content/tags, only
    given norm_rang/gilt_ab/gilt_bis fields are changed -- a node stays frozen
    at "no Normschicht values" until one is explicitly passed. title aendert
    nur den Titel -- path bleibt unveraendert stehen (path wird nur bei
    knowledge_add aus dem Titel abgeleitet, nie nachtraeglich).

    norm_entscheidung (Auftrag 2026-08-08): nur noetig, wenn die Aenderung
    die BESTEHENDE Entscheidung widersprechen wuerde (z.B. einer bisher
    norm_unbefristet-en Norm nachtraeglich ein gilt_bis geben -- dafuer muss
    hier zugleich norm_entscheidung='norm_befristet' mitkommen). Bleibt sie
    weg, gilt die am Knoten gespeicherte Entscheidung unveraendert weiter --
    Altbestand mit norm_entscheidung='offen' bleibt beim reinen
    Feldaenderungen 'offen' (Auftrag Punkt 2: nicht rueckwirkend erzwingen)."""
    conn = get_db()
    row = conn.execute("SELECT * FROM knowledge_nodes WHERE id = ? OR path = ?", (node_id, node_id)).fetchone()
    if not row:
        log_access(conn, node_id, "update", actor=actor, model=model, session=session,
                   status="rejected", query="knoten_nicht_gefunden")
        conn.close()
        return {"error": f"Node not found: {node_id}"}

    # Grenzwertpruefung braucht beide Werte im Kontext: wer nur gilt_bis
    # aendert, wird trotzdem gegen das vorhandene gilt_ab geprueft (und
    # umgekehrt) -- sonst liesse sich die Reihenfolge durch zwei getrennte
    # Aufrufe umgehen.
    effektiv_gilt_ab = gilt_ab if gilt_ab is not None else row["gilt_ab"]
    effektiv_gilt_bis = gilt_bis if gilt_bis is not None else row["gilt_bis"]
    geltung_fehler = _validate_geltung(norm_rang, effektiv_gilt_ab, effektiv_gilt_bis)
    if geltung_fehler:
        log_access(conn, row["path"], "update", project_id=row["project_id"],
                   actor=actor, model=model, session=session,
                   status="rejected", query="geltung_ungueltig")
        conn.close()
        return {"error": geltung_fehler}

    # norm_entscheidung-Konsistenz. Drei Faelle (Auftrag 2026-08-08, zwei
    # davon Loecher aus dem unabhaengigen Review, Agent acf807ee8e6756f27,
    # VOR der Live-Migration geschlossen):
    effektiv_norm_rang = norm_rang if norm_rang is not None else row["norm_rang"]
    entscheidung_fehler = None
    if norm_entscheidung is not None:
        # (a) Aufrufer aendert die Entscheidung ausdruecklich -- 'offen' ist
        # dabei NIE zulaessig (auch nicht als Rueckzug einer bereits
        # getroffenen Entscheidung: eine getroffene Entscheidung bleibt
        # stehen, siehe DB-Trigger knowledge_nodes_norm_entscheidung_pflicht_bu).
        # _validate_norm_entscheidung lehnt 'offen' schon ab (nicht in
        # ALLOWED_NORM_ENTSCHEIDUNG), hier nur der sprechendere Text dafuer.
        if norm_entscheidung == "offen":
            entscheidung_fehler = ("norm_entscheidung kann nicht auf offen zurueckgesetzt werden: eine "
                                    "getroffene Entscheidung bleibt stehen, hoechstens auf keine_norm/"
                                    "norm_befristet/norm_unbefristet aendern.")
        else:
            # (a) echte NEUE Entscheidung -- Begruendung Pflicht.
            entscheidung_fehler = (
                _validate_norm_entscheidung(norm_entscheidung, effektiv_norm_rang, effektiv_gilt_ab, effektiv_gilt_bis)
                or _validate_norm_entschieden_grund(norm_entschieden_grund))
    elif row["norm_entscheidung"] != "offen":
        # Zeile war schon entschieden, Aufrufer aendert norm_rang/gilt_ab/
        # gilt_bis ohne norm_entscheidung anzufassen -- muss weiter zur
        # gespeicherten Entscheidung passen (sonst liesse sich z.B. einer
        # norm_unbefristet-en Norm per gilt_bis-Update stillschweigend ein
        # Ende geben).
        entscheidung_fehler = _validate_norm_entscheidung(
            row["norm_entscheidung"], effektiv_norm_rang, effektiv_gilt_ab, effektiv_gilt_bis)
    elif norm_rang is not None:
        # (b) Zeile war 'offen' UND bleibt es (norm_entscheidung nicht
        # mitgegeben), bekommt aber jetzt einen norm_rang -- die Rang-Vergabe
        # IST eine Entscheidung und muss sie explizit tragen (DB-Trigger
        # knowledge_nodes_norm_entscheidung_rang_neu_bu waere sonst der
        # einzige Schutz, mit roher sqlite3.IntegrityError statt Klartext).
        entscheidung_fehler = ("norm_rang neu vergeben, aber diese Zeile war bisher 'offen' (nie entschieden): "
                                "norm_entscheidung mitgeben (norm_befristet oder norm_unbefristet).")
    if entscheidung_fehler:
        log_access(conn, row["path"], "update", project_id=row["project_id"],
                   actor=actor, model=model, session=session,
                   status="rejected", query="norm_entscheidung_ungueltig")
        conn.close()
        return {"error": entscheidung_fehler}

    # Schreiber gehoert an den Datensatz (Auftrag 2026-08-06, wie knowledge_add).
    actor, model, session = _identity(actor, model, session)

    # Derselbe Aufrufer-Fehler wie bei knowledge_add moeglich (Parametergrenze
    # verrutscht ins Textfeld) -- nur uebergebene Felder unmangeln.
    given = {k: v for k, v in {"summary": summary, "content": content, "tags": tags, "title": title}.items()
             if v is not None}
    if given:
        fixed = unmangle_knowledge_fields(given)
        summary = fixed.get("summary", summary)
        content = fixed.get("content", content)
        tags = fixed.get("tags", tags)
        title = fixed.get("title", title)

    updates = []
    params = []
    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if summary is not None:
        updates.append("summary = ?")
        params.append(summary)
    if content is not None:
        updates.append("content = ?")
        params.append(content)
    if tags is not None:
        updates.append("tags = ?")
        params.append(json.dumps(tags))
    if norm_rang is not None:
        updates.append("norm_rang = ?")
        params.append(norm_rang)
    if gilt_ab is not None:
        updates.append("gilt_ab = ?")
        params.append(gilt_ab)
    if gilt_bis is not None:
        updates.append("gilt_bis = ?")
        params.append(gilt_bis)
    neuer_zeitpunkt = now_iso()
    if norm_entscheidung is not None:
        updates.append("norm_entscheidung = ?")
        params.append(norm_entscheidung)
        # Entscheider (Nachtrag 2026-08-08): diese UPDATE-Anweisung IST der
        # Moment der Entscheidung -- actor/Zeitpunkt/Begruendung gehoeren
        # zusammen mit der Entscheidung selbst, nicht nachtraeglich getrennt.
        updates.append("norm_entschieden_von = ?, norm_entschieden_am = ?, norm_entschieden_grund = ?")
        params.extend([actor, neuer_zeitpunkt, norm_entschieden_grund])

    if gattung is not None:
        # Nur bei ausdruecklicher Angabe -- ein Update anderer Felder darf die
        # Gattung nicht stillschweigend auf die Vorgabe zuruecksetzen.
        updates.append("gattung = ?")
        params.append(gattung)

    updates.append("updated_at = ?")
    params.append(neuer_zeitpunkt)
    # actor/session/model bleiben stehen (2026-08-08): der Trigger
    # knowledge_nodes_herkunft_bu haelt actor und session fuer
    # unveraenderlich. Wer sie beim Update ueberschrieb, brach jeden Aufruf
    # ab, sobald ein anderer Urheber als der Anleger schrieb -- gemessen an
    # der Sammelentscheidung ueber 62 Knoten, IntegrityError beim ersten.
    # Wer die Aenderung vorgenommen hat, steht ohnehin an zwei Stellen: im
    # access_log und, bei einer Normentscheidung, in norm_entschieden_von.
    updates.append("client = ?")
    params.append(_KLIENT)
    params.append(row["id"])
    # Lost-Update-Schutz: die WHERE-Klausel bindet an den beim SELECT oben
    # gelesenen updated_at. Hat zwischenzeitlich ein anderer Schreiber
    # denselben Knoten geaendert, trifft das UPDATE null Zeilen -- das ist
    # das Signal, nicht ein Fehler der SQL selbst.
    # ponytail: now_iso() ist sekundengenau -- zwei Schreiber in derselben
    # Sekunde kollidieren zufaellig auf denselben Wert und der Schutz greift
    # dann nicht. Aufwertung braeuchte eine Versions-Spalte, das ist eine
    # Schema-Aenderung und ausserhalb dieses Auftrags.
    expected_updated_at = row["updated_at"]
    params.append(expected_updated_at)

    log_access(conn, row["path"], "update", project_id=row["project_id"],
               actor=actor, model=model, session=session, status="started")
    try:
        cursor = conn.execute(
            f"UPDATE knowledge_nodes SET {', '.join(updates)} WHERE id = ? AND updated_at = ?",
            params,
        )
    except sqlite3.IntegrityError as e:
        # Ein abweisender Trigger darf die Verbindung nicht offen lassen.
        # Gemessen am 2026-08-08: der Herkunfts-Trigger wies ein Update ab, die
        # Ausnahme flog aus dieser Funktion heraus, und die Verbindung blieb am
        # __traceback__ der Ausnahme haengen -- samt offener Schreibtransaktion.
        # Ergebnis: die gesamte Datenbank war fuer JEDEN Schreiber gesperrt, bis
        # der Serverprozess starb. Der lange Fehlerweg ist der gefaehrliche:
        # nicht das Abweisen, sondern das Aufraeumen danach.
        conn.rollback()
        log_access(conn, row["path"], "update", project_id=row["project_id"],
                   actor=actor, model=model, session=session, status="rejected")
        conn.close()
        return {"error": str(e), "id": row["id"]}
    if cursor.rowcount == 0:
        conn.rollback()
        current = conn.execute("SELECT * FROM knowledge_nodes WHERE id = ?", (row["id"],)).fetchone()
        log_access(conn, row["path"], "update", project_id=row["project_id"],
                   actor=actor, model=model, session=session, status="failed")
        conn.close()
        return {
            "error": "Conflict: node was modified by another writer since it was read",
            "id": row["id"],
            "expected_updated_at": expected_updated_at,
            "current": dict(current) if current else None,
        }

    wikilinks = {"relations_created": [], "unresolved_links": []}
    if content is not None:
        # P5: Kanten dieses Knotens komplett neu ziehen, sonst ueberlebt ein
        # aus dem content entfernter Verweis als Karteileiche.
        conn.execute(
            "DELETE FROM knowledge_relations WHERE source_path = ? AND relation_type = 'references'",
            (row["path"],),
        )
        wikilinks = _sync_wikilinks(conn, row["path"], content, actor=actor, model=model, session=session)

    updated_row = conn.execute("SELECT * FROM knowledge_nodes WHERE id = ?", (row["id"],)).fetchone()

    # ADR-032 (loest P4 ab): ein veralteter Vektor ist schlechter als gar
    # keiner (Hybridsuche gewichtet ihn gutgläubig mit, test_knowledge_hybrid_
    # search.py) -- frueher wurde er bei Textaenderung nur GELOESCHT, die
    # Luecke blieb bis zum naechsten build_embeddings.py-Lauf offen. Jetzt
    # sofort neu gebaut. updated_at bumpt bei JEDEM Update (auch reinem
    # Tags-Wechsel), also unconditional statt nur bei Text -- sonst waere
    # jede Aenderung ein neuer vector_gaps-Fund. Schlaegt der Bau fehl (Modell
    # nicht erreichbar), bleibt die Luecke offen, der Schreibvorgang bleibt
    # gueltig (siehe _rebuild_node_embedding).
    _rebuild_node_embedding(conn, row["id"], updated_row["project_id"], updated_row["path"],
                            updated_row["title"], updated_row["summary"], updated_row["content"])

    log_access(conn, row["path"], "update", project_id=row["project_id"],
               actor=actor, model=model, session=session,
               affected_row=dict(updated_row) if updated_row else None)
    conn.commit()
    conn.close()
    # ADR-034 (einschleusung): nur die tatsaechlich UMGESCHRIEBENEN Felder
    # pruefen, nicht den ganzen Knoten -- summary/content bleiben None, wo
    # der Aufrufer sie nicht mitgegeben hat.
    _check_injection_suspects("node", row["path"], {"summary": summary, "content": content})
    _check_norm_conflicts(row["id"], row["path"], updated_row["norm_rang"])
    return {"id": row["id"], "status": "updated", **wikilinks}


ALLOWED_FREIGABE = ("offen", "intern", "gesperrt")

# Welche Tabellen eine Freigabestufe tragen. Als Zuordnung und nicht als zwei
# fast gleiche Funktionen: die Lehre L-0de1a9 stammt aus genau diesem Haus --
# vierzehn `_ensure_<spalte>_column`, jede fuer sich korrekt, zusammen eine
# Handliste, die ab dem naechsten Zuwachs falsch war.
_FREIGABE_TABELLEN = (
    ("lessons_learned", "id"),
    ("knowledge_nodes", "id"),
)


def freigabe_setzen(eintrag_id: str, stufe: str, *, actor: str | None = None,
                    model: str | None = None, session: str | None = None) -> dict:
    """Entscheidet fuer EINEN Eintrag, wer ihn sehen darf.

    BEFUND, der dieses Werkzeug veranlasst hat (2026-08-11): Die Spalte
    `freigabe` gab es seit dem 2026-08-10 an lessons_learned und laenger an
    knowledge_nodes -- aber keinen Weg, sie zu setzen. 753 von 753 Lehren
    standen auf 'intern'. Das war die entworfene Vorgabe, kein Defekt; der
    Defekt war der fehlende Schreibweg.

    Was es ausdruecklich NICHT gibt, und das ist der Kern:

      KEINE MASSENZUWEISUNG. Genau eine Kennung, kein Muster, keine Liste.
      migrate_freigabe.py haelt fest: "jeder Bestandsknoten bleibt 'intern',
      bis jemand ihn EINZELN entscheidet." Der einzige heute existierende
      Knoten-Schreibweg verletzt das -- melder/selbstbeschreibung.py setzt per
      rohem `UPDATE ... WHERE path LIKE` und ohne Protokolleintrag. Dieses
      Werkzeug ist der Gegenentwurf, nicht dessen Nachbau.

      KEINE STILLE ANNAHME. Ein unzulaessiger Wert wird abgewiesen, bevor
      geschrieben wird -- und die Datenbank haelt unabhaengig davon mit einem
      Trigger dagegen. Zwei Schranken, weil 32 Serverprozesse gleichzeitig
      arbeiten und der aelteste 23 Stunden alten Code faehrt (Knoten
      4603f990): eine Pruefung hier gilt nur fuer neu gestartete, der Trigger
      fuer alle.

    Anders als bei einer Norm ist die Entscheidung NICHT bindend -- der
    Rueckweg von 'offen' nach 'intern' ist ausdruecklich erlaubt
    (Spaltenkommentar in schema.sql).
    """
    if stufe not in ALLOWED_FREIGABE:
        return {"error": f"freigabe unzulaessig: {stufe!r}. Erlaubt sind "
                         f"{', '.join(ALLOWED_FREIGABE)}."}
    kennung = (eintrag_id or "").strip()
    if not kennung:
        return {"error": "eintrag_id fehlt"}
    if "," in kennung or "%" in kennung or "*" in kennung:
        # Keine Massenzuweisung: eine Liste oder ein Muster wird nicht
        # aufgeteilt, sondern abgelehnt. Wer zehn Eintraege entscheiden will,
        # entscheidet zehnmal -- das ist der Zweck der Schranke, nicht ihr Preis.
        return {"error": "freigabe_setzen nimmt genau EINE Kennung -- keine "
                         "Liste, kein Muster. Jeder Eintrag wird einzeln "
                         "entschieden."}

    conn = get_db()
    treffer = []
    for tabelle, schluessel in _FREIGABE_TABELLEN:
        try:
            zeile = conn.execute(
                f"SELECT {schluessel} AS id, freigabe FROM {tabelle} WHERE {schluessel} = ?",
                (kennung,)).fetchone()
        except sqlite3.OperationalError:
            continue                      # Tabelle oder Spalte fehlt: nichts zu tun
        if zeile:
            treffer.append((tabelle, zeile))

    if not treffer:
        log_access(conn, kennung, "freigabe_setzen", actor=actor, model=model,
                   session=session, status="rejected", query="eintrag_nicht_gefunden")
        conn.commit()
        conn.close()
        return {"error": f"Kein Eintrag mit dieser Kennung: {kennung}"}
    if len(treffer) > 1:
        # Doppeldeutig heisst ABBRECHEN, nicht raten. Eine Kennung, die in
        # beiden Tabellen steht, ist ein Befund und keine Auswahlfrage.
        conn.close()
        return {"error": f"Kennung {kennung} kommt in mehreren Tabellen vor: "
                         f"{', '.join(t for t, _ in treffer)}"}

    tabelle, zeile = treffer[0]
    vorher = zeile["freigabe"]
    actor, model, session = _identity(actor, model, session)
    log_access(conn, kennung, "freigabe_setzen", actor=actor, model=model,
               session=session, status="started", query=f"{vorher} -> {stufe}")
    if vorher == stufe:
        conn.commit()
        conn.close()
        return {"id": kennung, "tabelle": tabelle, "freigabe": stufe,
                "status": "unchanged"}

    conn.execute(f"UPDATE {tabelle} SET freigabe = ? WHERE id = ?", (stufe, kennung))
    nachher = conn.execute(
        f"SELECT * FROM {tabelle} WHERE id = ?", (kennung,)).fetchone()
    log_access(conn, kennung, "freigabe_setzen", actor=actor, model=model,
               session=session, query=f"{vorher} -> {stufe}",
               affected_row=dict(nachher) if nachher else None)
    conn.commit()
    conn.close()
    return {"id": kennung, "tabelle": tabelle, "freigabe": stufe,
            "vorher": vorher, "status": "gesetzt"}


def knowledge_zurueckziehen(node_id: str, grund: str, *, actor: str | None = None,
                            model: str | None = None, session: str | None = None) -> dict:
    """Zieht einen Knoten zurueck: content und summary werden GELEERT (kein
    Backup -- danach ist der Inhalt weg, nur die Sichtbarkeit ist reversibel
    ueber knowledge_freigeben), title und path bleiben stehen, die Zeile
    bleibt in der Tabelle mit Grund/Zeitpunkt/Urheber (Z5: nichts aendert
    sich unbemerkt). knowledge_search und der Recall-Hook lassen den Knoten
    danach aus. Reversibel, im Unterschied zum endgueltigen Entfernen
    (endgueltig_entfernen.py, nur von Hand, kein MCP-Werkzeug) -- eine KI darf
    dieses Werkzeug ohne Rueckfrage aufrufen, genau weil nichts spurlos
    verschwindet.

    grund ist Pflicht (leer -> Ablehnung, nichts geaendert): ein Zurueckziehen
    ohne Begruendung waere dieselbe Blackbox wie ein rohes DELETE."""
    if not grund or not grund.strip():
        conn = get_db()
        log_access(conn, node_id, "zurueckziehen", actor=actor, model=model, session=session,
                   status="rejected", query="grund_fehlt")
        conn.close()
        return {"error": "grund fehlt: Zurueckziehen verlangt eine Begruendung, nichts geaendert."}

    conn = get_db()
    row = conn.execute("SELECT * FROM knowledge_nodes WHERE id = ? OR path = ?", (node_id, node_id)).fetchone()
    if not row:
        log_access(conn, node_id, "zurueckziehen", actor=actor, model=model, session=session,
                   status="rejected", query="knoten_nicht_gefunden")
        conn.close()
        return {"error": f"Node not found: {node_id}"}

    actor, model, session = _identity(actor, model, session)
    timestamp = now_iso()
    log_access(conn, row["path"], "zurueckziehen", project_id=row["project_id"],
               actor=actor, model=model, session=session, status="started")
    conn.execute(
        """UPDATE knowledge_nodes
           SET zurueckgezogen = 1, zurueckgezogen_grund = ?, zurueckgezogen_am = ?,
               zurueckgezogen_von = ?, content = '', summary = '', updated_at = ?
           WHERE id = ?""",
        (grund, timestamp, actor, timestamp, row["id"]),
    )
    # P4-Muster wie knowledge_update: ein Vektor auf jetzt geleertem Text ist
    # schlechter als gar keiner.
    conn.execute("DELETE FROM knowledge_embeddings WHERE kind = 'node' AND ref_id = ?", (row["id"],))
    updated_row = conn.execute("SELECT * FROM knowledge_nodes WHERE id = ?", (row["id"],)).fetchone()
    log_access(conn, row["path"], "zurueckziehen", project_id=row["project_id"],
               actor=actor, model=model, session=session,
               affected_row=dict(updated_row) if updated_row else None)
    conn.commit()
    conn.close()
    return {"id": row["id"], "path": row["path"], "status": "zurueckgezogen", "grund": grund}


def knowledge_freigeben(node_id: str, *, actor: str | None = None,
                        model: str | None = None, session: str | None = None) -> dict:
    """Macht ein Zurueckziehen rueckgaengig: der Knoten taucht wieder in
    knowledge_search/Recall auf. Stellt NICHTS wieder her -- content/summary
    wurden beim Zurueckziehen geleert und bleiben leer, das ist keine
    Wiederherstellung, nur eine Sichtbarkeits-Umschaltung."""
    conn = get_db()
    row = conn.execute("SELECT * FROM knowledge_nodes WHERE id = ? OR path = ?", (node_id, node_id)).fetchone()
    if not row:
        log_access(conn, node_id, "freigeben", actor=actor, model=model, session=session,
                   status="rejected", query="knoten_nicht_gefunden")
        conn.close()
        return {"error": f"Node not found: {node_id}"}
    if not row["zurueckgezogen"]:
        conn.close()
        return {"id": row["id"], "status": "unchanged", "message": "Knoten war nicht zurueckgezogen."}

    actor, model, session = _identity(actor, model, session)
    timestamp = now_iso()
    log_access(conn, row["path"], "freigeben", project_id=row["project_id"],
               actor=actor, model=model, session=session, status="started")
    conn.execute(
        "UPDATE knowledge_nodes SET zurueckgezogen = 0, updated_at = ? WHERE id = ?",
        (timestamp, row["id"]),
    )
    updated_row = conn.execute("SELECT * FROM knowledge_nodes WHERE id = ?", (row["id"],)).fetchone()
    log_access(conn, row["path"], "freigeben", project_id=row["project_id"],
               actor=actor, model=model, session=session,
               affected_row=dict(updated_row) if updated_row else None)
    conn.commit()
    conn.close()
    return {"id": row["id"], "path": row["path"], "status": "freigegeben"}


def kettenerklaerung_erklaeren(access_log_id: int, grund: str, *, commit_hash: str | None = None,
                               anker: str | None = None, actor: str | None = None,
                               model: str | None = None, session: str | None = None,
                               **anker_kwargs: object) -> dict:
    """ADR-034: kettenerklaerung.py war gebaut, aber von keinem Werkzeug
    erreichbar (nur per Hand importierbar) -- dieses Werkzeug ist der
    Anschluss. Der Schreibvorgang IST das Erklaeren selbst: ein Kettenbruch
    entsteht nur durch Umschreiben, nie durch Anhaengen/Lesen, darum kein
    Sammellauf, sondern ein Aufruf genau dann, wenn jemand eine befugte
    Umschreibung nachtraeglich erklaert (siehe kettenerklaerung.py-Docstring).

    anker (optional, "rfc3161"/"gegenzeichnung"): reicht an
    ankerverfahren.versuche_anker() durch. Genau in diesem Moment -- ein
    Anker wird eingestellt -- aendert sich auch ankerverfahren.rueckstand(),
    darum wird er hier gleich mitgemeldet (anker_rueckstand im Ergebnis)
    statt in einem periodischen Blick auf die Warteschlange, die sich sonst
    nie aendert (ADR-034). Ein Fehler beim Rueckstand-Blick darf die
    Erklaerung selbst nie zu Fall bringen (Negativfall 2) -- der Beleg wurde
    ja schon geschrieben, das ist nur eine Nebenauskunft."""
    import kettenerklaerung  # verzoegert -- kettenerklaerung.py importiert seinerseits
                              # aus diesem Modul, Top-Level waere derselbe Zirkel wie kurator_lauf().
    conn = get_db()
    try:
        actor, model, session = _identity(actor, model, session)
        ergebnis = kettenerklaerung.create_explanation(
            conn, access_log_id, grund, commit_hash=commit_hash, actor=actor,
            anker=anker, **anker_kwargs,
        )
    finally:
        conn.close()

    if anker is not None:
        try:
            import ankerverfahren
            # Derselbe queue_path wie beim Anker-Versuch selbst -- versuche_anker()
            # bekam ihn (falls mitgegeben) ueber genau dieselben anker_kwargs.
            queue_path = anker_kwargs.get("queue_path", ankerverfahren.ANKER_QUEUE_PATH)
            ergebnis["anker_rueckstand"] = ankerverfahren.rueckstand(queue_path)
        except Exception:
            pass
    return ergebnis


def _relation_node(conn: sqlite3.Connection, value: str,
                   scope: str | None = None) -> sqlite3.Row:
    row = conn.execute(
        "SELECT id,path,project_id,title FROM knowledge_nodes WHERE id=? OR path=?",
        (value, value),
    ).fetchone()
    if not row:
        raise ValueError(f"Knowledge node not found: {value}")
    if scope and scope != "all" and row["project_id"] not in ("shared", scope):
        raise ValueError(f"Node {value} is outside scope shared|{scope}")
    return row


def _relation_values(relation_type: str, confidence: float, weight: float) -> None:
    if relation_type not in RELATION_TYPES:
        raise ValueError(f"Invalid relation type: {relation_type}")
    if not 0.0 <= float(confidence) <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    if float(weight) < 0.0:
        raise ValueError("weight must be >= 0")


def knowledge_relation_add(source_node: str, target_node: str, relation_type: str,
                           confidence: float = 0.8, weight: float = 1.0,
                           evidence: str = "", source: str = "",
                           scope: str = "all", creator: str | None = None,
                           model: str | None = None, session: str | None = None) -> dict:
    """Create one explicit evidenced edge; never infers similarity."""
    _relation_values(relation_type, confidence, weight)
    conn = get_db()
    source_row = _relation_node(conn, source_node, scope)
    target_row = _relation_node(conn, target_node, scope)
    if source_row["path"] == target_row["path"]:
        conn.close()
        raise ValueError("Self-relations are not allowed")
    creator, model, session = _identity(creator, model, session)
    relation_id = f"R-{uuid.uuid4().hex[:8]}"
    timestamp = now_iso()
    log_access(conn, source_row["path"], "relation_add", query=relation_id,
               project_id=source_row["project_id"], actor=creator, model=model,
               session=session, status="started")
    try:
        conn.execute(
            """INSERT INTO knowledge_relations
               (id,source_path,target_path,relation_type,confidence,weight,evidence,source,
                creator,model,session,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (relation_id, source_row["path"], target_row["path"], relation_type,
             float(confidence), float(weight), evidence, source, creator, model, session,
             timestamp, timestamp),
        )
    except sqlite3.IntegrityError as error:
        log_access(conn, source_row["path"], "relation_add", query=relation_id,
                   project_id=source_row["project_id"], actor=creator, model=model,
                   session=session, status="failed")
        conn.close()
        raise ValueError("Relation already exists or violates the knowledge contract") from error
    log_access(conn, source_row["path"], "relation_add", query=relation_id,
               project_id=source_row["project_id"], actor=creator, model=model, session=session,
               affected_row={
                   "id": relation_id, "source_path": source_row["path"],
                   "target_path": target_row["path"], "relation_type": relation_type,
                   "confidence": float(confidence), "weight": float(weight),
                   "evidence": evidence, "source": source, "creator": creator,
                   "model": model, "session": session,
                   "created_at": timestamp, "updated_at": timestamp,
               })
    conn.close()
    return {"id": relation_id, "status": "created", "source_path": source_row["path"],
            "target_path": target_row["path"], "relation_type": relation_type}


def knowledge_relation_list(node: str | None = None,
                            relation_type: str | None = None,
                            scope: str = "all", *, actor: str | None = None,
                            model: str | None = None, session: str | None = None) -> dict:
    """List explicit relations, optionally incident to one node."""
    if relation_type and relation_type not in RELATION_TYPES:
        raise ValueError(f"Invalid relation type: {relation_type}")
    conn = get_db()
    clauses, params = [], []
    node_row = _relation_node(conn, node, scope) if node else None
    if node_row:
        clauses.append("(r.source_path=? OR r.target_path=?)")
        params.extend([node_row["path"], node_row["path"]])
    if relation_type:
        clauses.append("r.relation_type=?")
        params.append(relation_type)
    if scope != "all":
        clauses.append("s.project_id IN ('shared',?) AND t.project_id IN ('shared',?)")
        params.extend([scope, scope])
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    log_access(conn, node_row["path"] if node_row else None, "relation_list",
               project_id=scope, actor=actor, model=model, session=session, status="started")
    rows = conn.execute(
        """SELECT r.*,s.title AS source_title,t.title AS target_title
           FROM knowledge_relations r
           JOIN knowledge_nodes s ON s.path=r.source_path
           JOIN knowledge_nodes t ON t.path=r.target_path""" + where + " ORDER BY r.updated_at DESC",
        params,
    ).fetchall()
    log_access(conn, node_row["path"] if node_row else None, "relation_list",
               project_id=scope, actor=actor, model=model, session=session)
    conn.close()
    return {"relations": [dict(row) for row in rows], "count": len(rows)}


def knowledge_relation_update(relation_id: str, relation_type: str | None = None,
                              confidence: float | None = None, weight: float | None = None,
                              evidence: str | None = None, source: str | None = None,
                              creator: str | None = None, model: str | None = None,
                              session: str | None = None) -> dict:
    conn = get_db()
    row = conn.execute("SELECT * FROM knowledge_relations WHERE id=?", (relation_id,)).fetchone()
    if not row:
        log_access(conn, None, "relation_update", query="relation_nicht_gefunden",
                   actor=creator, model=model, session=session, status="rejected")
        conn.close()
        return {"error": f"Relation not found: {relation_id}"}
    next_type = relation_type or row["relation_type"]
    next_confidence = row["confidence"] if confidence is None else confidence
    next_weight = row["weight"] if weight is None else weight
    _relation_values(next_type, next_confidence, next_weight)
    creator, model, session = _identity(creator, model, session)
    values = {
        "relation_type": next_type, "confidence": float(next_confidence),
        "weight": float(next_weight), "evidence": row["evidence"] if evidence is None else evidence,
        "source": row["source"] if source is None else source,
        "creator": creator or row["creator"], "model": model or row["model"],
        "session": session or row["session"], "updated_at": now_iso(),
    }
    log_access(conn, row["source_path"], "relation_update", query=relation_id,
               actor=creator, model=model, session=session, status="started")
    try:
        conn.execute(
            """UPDATE knowledge_relations SET relation_type=:relation_type,
               confidence=:confidence,weight=:weight,evidence=:evidence,source=:source,
               creator=:creator,model=:model,session=:session,updated_at=:updated_at
               WHERE id=:id""",
            values | {"id": relation_id},
        )
    except sqlite3.IntegrityError as error:
        log_access(conn, row["source_path"], "relation_update", query=relation_id,
                   actor=creator, model=model, session=session, status="failed")
        conn.close()
        raise ValueError("Updated relation would violate the knowledge contract") from error
    log_access(conn, row["source_path"], "relation_update", query=relation_id,
               actor=creator, model=model, session=session,
               affected_row=values | {"id": relation_id, "source_path": row["source_path"],
                                       "target_path": row["target_path"]})
    conn.close()
    return {"id": relation_id, "status": "updated"}


def knowledge_relation_remove(relation_id: str, *, actor: str | None = None,
                              model: str | None = None, session: str | None = None) -> dict:
    conn = get_db()
    row = conn.execute("SELECT * FROM knowledge_relations WHERE id=?", (relation_id,)).fetchone()
    if not row:
        log_access(conn, None, "relation_remove", query="relation_nicht_gefunden",
                   actor=actor, model=model, session=session, status="rejected")
        conn.close()
        return {"error": f"Relation not found: {relation_id}"}
    log_access(conn, row["source_path"], "relation_remove", query=relation_id,
               actor=actor, model=model, session=session, status="started")
    conn.execute("DELETE FROM knowledge_relations WHERE id=?", (relation_id,))
    log_access(conn, row["source_path"], "relation_remove", query=relation_id,
               actor=actor, model=model, session=session)
    conn.close()
    return {"id": relation_id, "status": "removed"}


def _build_field_tag_re(fields: tuple) -> re.Pattern:
    """Baut die Feldgrenzen-Regex fuer eine gegebene Feldnamen-Menge.

    Zwei Tag-Stile kommen in der Wildnis vor: plain `<root_cause>...</root_cause>`
    und der antml-Tool-Call-Stil `<parameter name="root_cause">...</parameter>`
    (Schliesser dort ist generisch `</parameter>`, traegt keinen Feldnamen).
    Gemeinsame Engine fuer lesson_record UND knowledge_add -- beide leiden am
    selben Aufrufer-Fehler (Parametergrenze rutscht in den vorherigen Textwert),
    nur mit unterschiedlichen Feldnamen.
    """
    alt = "|".join(fields)
    return re.compile(
        r'<parameter\s+name="(?P<pname>' + alt + r')"\s*>'
        r"|</parameter>"
        r"|<(?P<oname>" + alt + r")>"
        r"|</(?P<cname>" + alt + r")>"
    )


LESSON_TEXT_FIELDS = ("description", "root_cause", "resolution", "prevention",
                      "severity", "projects", "node_path", "type")
_FIELD_TAG = _build_field_tag_re(LESSON_TEXT_FIELDS)

KNOWLEDGE_TEXT_FIELDS = ("content", "tags", "source", "summary", "title")
_KNOWLEDGE_FIELD_TAG = _build_field_tag_re(KNOWLEDGE_TEXT_FIELDS)

# "parameter" bewusst NICHT hier: ein `<parameter name="root_cause">` kann auch
# ein Zitat im Fliesstext sein (z.B. eine Lesson, die diesen Bug beschreibt).
# Echte, an einer Feldgrenze stehende parameter-Tags werden bereits von
# _split_tagged konsumiert und tauchen danach gar nicht mehr auf; ein
# uebrigbleibender parameter-Tag ist also so gut wie sicher ein Zitat und
# muss stehen bleiben. invoke/function_calls/antml:* sind dagegen reines
# Aufruf-Rauschen, das nie sinnvoll zitiert wird.
_CALL_NOISE = re.compile(r"</?(invoke|function_calls|antml:\w+)[^>]*>")


def _is_boundary_tag(value: str, m: re.Match) -> bool:
    """Nur Tags an einer echten Feldgrenze zaehlen, nicht als Zitat im Fliesstext.

    Eine echte verrutschte Feldgrenze steht immer isoliert: der Aufrufer
    schliesst einen Parameter und oeffnet sofort den naechsten, nie mitten in
    einem Satz. Ein oeffnender Tag zaehlt daher nur, wenn direkt davor (nur
    Leerraum dazwischen) Zeilenanfang/Stringanfang ODER das Ende eines anderen
    Tags (`>`) steht; ein schliessender Tag nur, wenn direkt danach
    Zeilenende/Stringende ODER der Anfang eines anderen Tags (`<`) folgt. Das
    deckt sowohl "jeder Tag auf eigener Zeile" als auch "Tags ohne Trenner
    aneinandergereiht" ab, verwirft aber einen Tag, der als Beispiel mitten in
    einem Satz zitiert wird (z.B. eine Lesson, die den Bug selbst beschreibt)
    — dort steht vor UND nach dem Tag echter Satztext auf derselben Zeile.
    """
    is_open = m.group("pname") is not None or m.group("oname") is not None
    if is_open:
        j = m.start()
        while j > 0 and value[j - 1] in " \t":
            j -= 1
        return j == 0 or value[j - 1] in "\n>"
    j = m.end()
    while j < len(value) and value[j] in " \t":
        j += 1
    return j == len(value) or value[j] in "\n<"


def _split_tagged(value: str, field_tag_re: re.Pattern = _FIELD_TAG) -> dict:
    """Zerlegt einen Wert an echten Feld-Tag-Grenzen (siehe _is_boundary_tag).

    Kein Zeichen NUTZTEXT geht verloren: jeder Textanteil, der keiner erkannten
    Feldgrenze zugeordnet werden kann (z.B. weil das Zielfeld gerade `current`
    None ist — etwa bei einem verwaisten schliessenden Tag), landet unter
    "_head" statt verworfen zu werden. Einzige Ausnahme: ein Anteil, der
    zwischen zwei Tags liegt UND nur aus Leerraum besteht, ist der
    Formatierungs-Zwischenraum der Tags selbst (kein Inhalt) und wird nicht
    extra angehaengt — sonst haeuften sich bei mehreren aufeinanderfolgenden
    Tags leere Zeilen im Ursprungsfeld an.

    field_tag_re: welche Feldnamen als Grenze zaehlen -- default die Lesson-
    Felder (_FIELD_TAG), knowledge_add nutzt _KNOWLEDGE_FIELD_TAG (siehe
    unmangle_knowledge_fields).
    """
    matches = [m for m in field_tag_re.finditer(value) if _is_boundary_tag(value, m)]
    out: dict[str, str] = {}
    current: str | None = None
    pos = 0
    head_parts: list[str] = []
    for m in matches:
        segment = value[pos:m.start()]
        if current is None:
            if segment.strip():
                head_parts.append(segment)
        else:
            out[current] = out.get(current, "") + segment
        pname, oname, cname = m.group("pname"), m.group("oname"), m.group("cname")
        is_open = pname is not None or oname is not None
        name = pname or oname or cname  # cname/name may be None for bare </parameter>
        current = name if is_open else None
        pos = m.end()
    tail = value[pos:]
    if current is None:
        if tail.strip():
            head_parts.append(tail)
    else:
        out[current] = out.get(current, "") + tail
    out["_head"] = "".join(head_parts)
    return out


def unmangle_lesson_fields(fields: dict) -> dict:
    """Repariert verrutschte Parametergrenzen in Lesson-Aufrufen.

    Schreibt ein Aufrufer einen langen mehrzeiligen Wert, rutscht die Grenze zum
    naechsten Parameter gelegentlich ins Textfeld — dann steht z.B. der komplette
    `root_cause` als `<root_cause>…</root_cause>` im `description`-Wert. 21 der
    218 Lessons waren so verstuemmelt, ausgerechnet die laengsten. Hier werden die
    Tags erkannt und die Anteile auf die richtigen Spalten verteilt; nur leere
    Zielfelder werden befuellt, ein echter Wert gewinnt immer. Kein Zeichen geht
    verloren: Text, dessen Zielfeld schon belegt ist oder der sich keinem Feld
    zuordnen laesst, bleibt im Ursprungsfeld erhalten statt geloescht zu werden.
    """
    out = dict(fields)
    for name in LESSON_TEXT_FIELDS:
        val = out.get(name)
        if not isinstance(val, str) or not _FIELD_TAG.search(val):
            continue
        parts = _split_tagged(val)
        head = parts.pop("_head", "")
        if not parts:
            # Kein anderes Feld zu befuellen -- entweder gar keine echte
            # Feldgrenze (dann ist head == val, No-op) oder eine selbstbezuegliche
            # Grenze wie eine verwaiste </description> ohne Gegenstueck (dann hat
            # head die Tag-Zeichen schon abgezogen, siehe efa1f597/1a714374).
            # Beide Faelle: head zurueckschreiben statt still zu ueberspringen.
            out[name] = head
            continue
        leftover = []
        for key, text in parts.items():
            stripped = text.strip()
            if not stripped:
                continue
            current_val = str(out.get(key) or "").strip()
            # severity traegt immer den Schema-Default "medium", auch wenn nie explizit
            # gesetzt — von einem echten Wert nicht unterscheidbar. Ein aus dem Tag
            # extrahierter gueltiger Enum-Wert gewinnt deshalb hier gegen den Default.
            beats_default = (key == "severity" and current_val == "medium"
                             and stripped in ("critical", "high", "medium", "low"))
            if key != name and (not current_val or beats_default):
                out[key] = stripped if key == "severity" else text
            else:
                leftover.append(text)
        out[name] = head + ("\n" + "\n".join(leftover) if leftover else "")
    for name in LESSON_TEXT_FIELDS:
        if isinstance(out.get(name), str):
            out[name] = _CALL_NOISE.sub("", out[name]).strip()
    if isinstance(out.get("projects"), str):
        try:
            out["projects"] = json.loads(out["projects"])
        except (ValueError, TypeError):
            out["projects"] = [p.strip(' "\'') for p in out["projects"].strip('[]').split(",") if p.strip(' "\'')]
    return out


def unmangle_knowledge_fields(fields: dict) -> dict:
    """Repariert verrutschte Parametergrenzen in knowledge_add/knowledge_update-
    Aufrufen -- derselbe Aufrufer-Fehler wie bei unmangle_lesson_fields, nur mit
    Knowledge-Feldnamen: der komplette content/tags/source landet dann als
    `<content>...</content>` etc. im summary-Wert (gemessen an efa1f597,
    7781dea1, 2a6098d1, c60b1b46, 3a978881, 5d899304). Nur leere Zielfelder
    werden befuellt, ein echter Wert gewinnt immer; kein Zeichen geht verloren.
    """
    out = dict(fields)
    for name in KNOWLEDGE_TEXT_FIELDS:
        val = out.get(name)
        if not isinstance(val, str) or not _KNOWLEDGE_FIELD_TAG.search(val):
            continue
        parts = _split_tagged(val, _KNOWLEDGE_FIELD_TAG)
        head = parts.pop("_head", "")
        if not parts:
            # Kein anderes Feld zu befuellen -- entweder gar keine echte
            # Feldgrenze (dann ist head == val, No-op) oder eine selbstbezuegliche
            # Grenze wie eine verwaiste </summary>/</content> ohne Gegenstueck
            # (dann hat head die Tag-Zeichen schon abgezogen, siehe 1a714374/
            # 6e22536d/698fc6b9/cbb40e73). Beide Faelle: head zurueckschreiben
            # statt still zu ueberspringen.
            out[name] = head
            continue
        leftover = []
        for key, text in parts.items():
            stripped = text.strip()
            if not stripped:
                continue
            current_val = out.get(key)
            has_value = bool(current_val) if isinstance(current_val, list) else bool(str(current_val or "").strip())
            if key != name and not has_value:
                out[key] = stripped if key == "tags" else text
            else:
                leftover.append(text)
        out[name] = head + ("\n" + "\n".join(leftover) if leftover else "")
    for name in KNOWLEDGE_TEXT_FIELDS:
        if isinstance(out.get(name), str):
            out[name] = _CALL_NOISE.sub("", out[name]).strip()
    if isinstance(out.get("tags"), str):
        try:
            out["tags"] = json.loads(out["tags"])
        except (ValueError, TypeError):
            out["tags"] = [p.strip(' "\'') for p in out["tags"].strip("[]").split(",") if p.strip(' "\'')]
    return out


MAX_REPEAT_PARAGRAPHS = 5
_REPEAT_MARKER_RE = re.compile(r"\n\n--- Wiederholung ([0-9T:+\-]+) ---\n")


def _append_repetition(base_description: str, new_text: str, when: str,
                       cap: int = MAX_REPEAT_PARAGRAPHS) -> str:
    """Haengt einen datierten Wiederholungs-Absatz an eine bestehende Beschreibung an.

    Gedeckelt auf die `cap` juengsten Wiederholungen — sonst waechst ein Eintrag
    unbegrenzt und wird unlesbar. Der urspruengliche Beschreibungstext (vor der
    ersten Wiederholung) bleibt immer erhalten, nur ueberzaehlige Wiederholungen
    fallen von vorne heraus.
    """
    parts = _REPEAT_MARKER_RE.split(base_description)
    head = parts[0]
    reps = list(zip(parts[1::2], parts[2::2]))
    reps.append((when, new_text.strip()))
    reps = reps[-cap:]
    out = head
    for date, text in reps:
        out += f"\n\n--- Wiederholung {date} ---\n{text}"
    return out


_STOPWORDS_DE = {
    "der", "die", "das", "und", "oder", "ein", "eine", "einer", "eines", "einem",
    "einen", "ist", "sind", "war", "waren", "im", "in", "am", "an", "auf", "zu",
    "von", "mit", "fuer", "für", "den", "dem", "des", "als", "auch", "nicht",
    "sich", "es", "bei", "aus", "wurde", "wurden", "werden", "sein", "seine",
    "seiner", "seinem", "je", "jede", "jeder", "jedes", "noch", "nur", "schon",
    "dann", "aber", "wenn", "hat", "hatte", "haben", "kann", "koennen", "können",
    "muss", "muessen", "müssen", "wird", "wo", "was", "wie", "so", "um", "ueber",
    "über", "nach", "vor", "durch",
}
_WORD_RE = re.compile(r"[a-zA-ZäöüÄÖÜß]+")
SIMILARITY_THRESHOLD = 0.18  # kalibriert gegen den Bestand, siehe PLAN/Bericht


def _tokenize(text: str) -> set:
    return {w for w in (m.lower() for m in _WORD_RE.findall(text))
            if w not in _STOPWORDS_DE and len(w) > 2}


def _find_similar_lesson(conn: sqlite3.Connection, type_: str, description: str,
                         threshold: float = SIMILARITY_THRESHOLD) -> dict | None:
    """Wortmengen-Jaccard-Vergleich gegen aktive Lessons desselben Typs.

    Reiner Hinweis fuer die Antwort, kein automatisches Verschmelzen (siehe
    lesson_record Docstring: zwei Lessons faelschlich zusammenzuziehen ist
    teurer als eine Dublette).
    """
    needle = _tokenize(description)
    if not needle:
        return None
    best = None
    for row in conn.execute(
        "SELECT id, occurrences, description FROM lessons_learned WHERE type = ? AND status = 'active'",
        (type_,)
    ):
        hay = _tokenize(row["description"])
        if not hay:
            continue
        score = len(needle & hay) / len(needle | hay)
        if score >= threshold and (best is None or score > best["score"]):
            best = {
                "id": row["id"],
                "occurrences": row["occurrences"],
                "score": round(score, 2),
                "description_first_line": row["description"].splitlines()[0][:200],
            }
    return best


def _auto_rule_fuer_lesson(conn: sqlite3.Connection, lesson_id: str) -> None:
    """ADR-034 (lesson_recorder.cmd_auto_rules): Ausloeser ist
    status='escalated_to_rule' bei occurrences>=3 -- entsteht ausschliesslich
    beim Schreiben einer Lehre (hier, direkt nach der Eskalation in
    _bump_lesson), nicht erst beim naechsten manuellen 'auto-rules'-CLI-Lauf.
    Verzoegerter Import (nicht Modul-Top), weil lesson_recorder.py seinerseits
    `import knowledge_mcp_server as kms` macht -- ein Top-Level-Import waere
    hier derselbe Zirkel, den kurator_lauf() weiter oben schon vermeidet.
    Nebenpruefung: darf den Schreibvorgang (die Eskalation ist bereits
    committet) nie zum Scheitern bringen, deshalb Exception geschluckt."""
    try:
        import lesson_recorder
        row = conn.execute("SELECT * FROM lessons_learned WHERE id = ?", (lesson_id,)).fetchone()
        if row is None or row["auto_rule_generated"]:
            return
        rule_text = lesson_recorder.generate_rule(row)
        lesson_recorder.write_rules_to_instructions([(row, rule_text)])
        conn.execute("UPDATE lessons_learned SET auto_rule_generated = 1 WHERE id = ?", (lesson_id,))
        conn.commit()
    except Exception:
        pass


def _bump_lesson(conn: sqlite3.Connection, lesson_id: str, node_path: str,
                 log_query: str, new_description: str | None = None, *,
                 actor: str | None = None, session: str | None = None,
                 model: str | None = None) -> dict:
    """Erhoeht occurrences einer bestehenden Lesson um eins, eskaliert ab 3.

    Gemeinsamer Pfad fuer den exakten Dublettentreffer und den expliziten
    same_as-Bezug — nur die Frage, ob dabei auch die description ersetzt wird
    (Wiederholungs-Anhang), unterscheidet die beiden Aufrufer.

    actor/session/model (Auftrag 2026-08-06): bereits aufgeloest von
    lesson_record (nie None) -- diese Zeile ist eine neue Sichtung/
    Wiederholung, also ein eigener Schreibvorgang, der den Schreiber traegt.
    Die Eskalations-UPDATE weiter unten bekommt bewusst KEIN erneutes
    actor/session/model (siehe dortiger Kommentar zu last_seen -- gleiche
    Begruendung: derselbe Vorgang, kein zweiter Schreiber)."""
    row = conn.execute("SELECT occurrences FROM lessons_learned WHERE id = ?", (lesson_id,)).fetchone()
    new_count = row["occurrences"] + 1
    if new_description is not None:
        conn.execute(
            "UPDATE lessons_learned SET occurrences = ?, description = ?, last_seen = ?, actor = ?, session = ?, model = ?, client = ? WHERE id = ?",
            (new_count, new_description, now_iso(), actor, session, model, _KLIENT, lesson_id)
        )
    else:
        conn.execute(
            "UPDATE lessons_learned SET occurrences = ?, last_seen = ?, actor = ?, session = ?, model = ?, client = ? WHERE id = ?",
            (new_count, now_iso(), actor, session, model, _KLIENT, lesson_id)
        )
    updated_row = conn.execute("SELECT * FROM lessons_learned WHERE id = ?", (lesson_id,)).fetchone()
    # ADR-032: last_seen bumpt bei JEDEM Vorkommen (auch ohne Textaenderung),
    # die alte Zeile waere sonst sofort wieder ein vector_gaps-Fund (Vektor
    # aelter als last_seen). Sofort neu gebaut statt geloescht/liegen gelassen.
    _rebuild_lesson_embedding(conn, lesson_id, updated_row["node_path"], updated_row["projects"],
                              updated_row["description"], updated_row["root_cause"],
                              updated_row["prevention"])
    log_access(conn, node_path or None, "lesson", query=log_query,
               actor=actor, model=model, session=session,
               affected_row=dict(updated_row) if updated_row else None)
    conn.commit()

    escalated = new_count >= 3
    if escalated:
        # ENTSCHEIDUNG (Auftrag 2026-08-06, Nebenbefund Konfidenzverfall):
        # last_seen bleibt hier UNVERAENDERT, bewusst -- kein fehlendes
        # Nachziehen. last_seen wurde ein paar Zeilen weiter oben, IM SELBEN
        # Aufruf, bereits auf now_iso() gesetzt (occurrences-Update). Die
        # Eskalation ist die Folge GENAU DIESES Vorkommens, keine zweite,
        # spaetere Sichtung -- ein erneutes Setzen waere redundant, nicht
        # praeziser. (Gleiches Prinzip wie bei knowledge_nodes.updated_at:
        # der Zeitstempel gehoert der inhaltlichen Aenderung/Bestaetigung,
        # nicht jeder Nebenwirkung an der Zeile.)
        conn.execute(
            "UPDATE lessons_learned SET status = 'escalated_to_rule' WHERE id = ?",
            (lesson_id,)
        )
        conn.commit()
        _auto_rule_fuer_lesson(conn, lesson_id)

    return {
        "id": lesson_id,
        "status": "incremented",
        "occurrences": new_count,
        "escalated": escalated,
        "message": f"Lesson seen {new_count}x. {'ESCALATED: Should become a rule in .instructions.md!' if escalated else ''}"
    }


def lesson_record(type_: str, description: str, root_cause: str = "",
                  resolution: str = "", prevention: str = "",
                  severity: str = "medium", projects: list | None = None,
                  node_path: str = "", same_as: str = "",
                  anlass: str = "unbekannt", *,
                  actor: str | None = None, model: str | None = None,
                  session: str | None = None) -> dict:
    """Record a lesson learned.

    same_as gesetzt: erhoeht occurrences der referenzierten Lesson, haengt
    diese Beschreibung als datierten Wiederholungs-Absatz an (gedeckelt),
    legt KEINEN neuen Eintrag an. Zeigt same_as ins Leere: Fehler, kein
    stiller Fallback.

    same_as leer: bisheriges Verhalten (exakte Dublette gleichen Typs +
    gleicher Beschreibung erhoeht occurrences; sonst neuer Eintrag). Bei
    neuem Eintrag zusaetzlich ein Aehnlichkeits-Hinweis in der Antwort
    (similar_lesson_hint), falls eine inhaltlich nahe aktive Lesson
    gleichen Typs existiert — ohne automatisches Verschmelzen.

    Ab 3 Vorkommen (same_as-Pfad wie bisheriger Exact-Match-Pfad) wird die
    Lesson auf status='escalated_to_rule' gesetzt.

    anlass: was hat den Eintrag ausgeloest -- siehe ALLOWED_ANLASS oben.
    'selbst'/'betreiber' sind selbstberichtet vom Aufrufer, nicht geprueft;
    'hook'/'skript' objektiv, weil der Aufrufweg sie kennt. Unbekannter Wert
    wird abgelehnt (sprechender Fehler, kein stiller Erfolg). Gilt nur fuer
    einen NEUEN Eintrag -- ein Bump (Dublette/same_as) laesst den anlass der
    bestehenden Zeile unveraendert.

    actor/model/session (Auftrag 2026-08-06, Mangel: lesson_record hatte
    bisher GAR KEINE Identitaets-Parameter -- strukturell unmoeglich, sie zu
    uebergeben, unabhaengig davon, ob ein Aufrufer es versucht haette). Wie
    bei knowledge_add: aufgeloest ueber _identity() (nie None), actor/session
    landen zusaetzlich auf der Zeile selbst (lessons_learned.actor/.session).
    """
    anlass_fehler = _validate_anlass(anlass)
    if anlass_fehler:
        conn = get_db()
        log_access(conn, node_path or None, "lesson", actor=actor, model=model, session=session,
                   status="rejected", query="anlass_ungueltig")
        conn.close()
        return {"status": "rejected", "error": anlass_fehler}

    actor, model, session = _identity(actor, model, session)

    fixed = unmangle_lesson_fields({
        "type": type_, "description": description, "root_cause": root_cause,
        "resolution": resolution, "prevention": prevention, "severity": severity,
        "projects": projects, "node_path": node_path,
    })
    type_, description = fixed["type"], fixed["description"]
    root_cause, resolution = fixed["root_cause"], fixed["resolution"]
    prevention, severity = fixed["prevention"], fixed["severity"] or "medium"
    projects, node_path = fixed["projects"], fixed["node_path"]

    # type_ erst NACH unmangle_lesson_fields pruefen: ein per Tag verrutschter
    # type kann durch die Unmangle-Reparatur noch gueltig werden (Auftrag
    # 2026-08-07). Vor dem Fix pruefen haette solche Faelle faelschlich abgelehnt.
    type_fehler = _validate_lesson_type(type_)
    if type_fehler:
        conn = get_db()
        log_access(conn, node_path or None, "lesson", actor=actor, model=model, session=session,
                   status="rejected", query="type_ungueltig")
        conn.close()
        return {"status": "rejected", "error": type_fehler}

    if not description.strip():
        conn = get_db()
        log_access(conn, node_path or None, "lesson", actor=actor, model=model, session=session,
                   status="rejected", query="beschreibung_leer")
        conn.close()
        return {"status": "rejected",
                "error": "description ist leer — Lesson nicht gespeichert."}

    conn = get_db()

    if same_as:
        target = conn.execute(
            "SELECT id, occurrences, description FROM lessons_learned WHERE id = ?",
            (same_as,)
        ).fetchone()
        if not target:
            log_access(conn, node_path or None, "lesson", actor=actor, model=model, session=session,
                       status="rejected", query="same_as_ungueltig")
            conn.close()
            return {"status": "rejected",
                    "error": f"same_as verweist auf keine bestehende Lesson: {same_as}"}
        merged_description = _append_repetition(target["description"], description, now_iso())
        result = _bump_lesson(conn, target["id"], node_path, description,
                              new_description=merged_description, actor=actor, session=session, model=model)
        conn.close()
        return result

    # Check for exact-duplicate existing lesson (same type + same description)
    existing = conn.execute(
        "SELECT id, occurrences FROM lessons_learned WHERE type = ? AND description = ? AND status = 'active'",
        (type_, description)
    ).fetchone()

    if existing:
        result = _bump_lesson(conn, existing["id"], node_path, description, actor=actor, session=session, model=model)
        conn.close()
        return result

    similar = _find_similar_lesson(conn, type_, description)

    lesson_id = f"L-{str(uuid.uuid4())[:6]}"
    seen_at = now_iso()
    conn.execute(
        """INSERT INTO lessons_learned (id, node_path, type, severity, description, root_cause, resolution, prevention, occurrences, projects, first_seen, last_seen, anlass, actor, session, model, client)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (lesson_id, node_path or None, type_, severity, description, root_cause,
         resolution, prevention, json.dumps(projects or []), seen_at, seen_at, anlass, actor, session, model, _KLIENT)
    )
    log_access(conn, node_path or None, "lesson", query=description,
               actor=actor, model=model, session=session,
               affected_row={
                   "id": lesson_id, "node_path": node_path or None, "type": type_,
                   "severity": severity, "description": description,
                   "root_cause": root_cause, "resolution": resolution,
                   "prevention": prevention, "occurrences": 1,
                   "projects": projects or [], "first_seen": seen_at, "last_seen": seen_at,
                   "anlass": anlass, "actor": actor, "session": session, "model": model,
               })
    # ADR-032: Vektor sofort mitbauen statt eine vector_gaps-Luecke bis zum
    # naechsten build_embeddings.py-Lauf offenzulassen.
    _rebuild_lesson_embedding(conn, lesson_id, node_path or None, json.dumps(projects or []),
                              description, root_cause, prevention)
    conn.commit()
    conn.close()
    _check_injection_suspects("lesson", lesson_id, {
        "description": description, "root_cause": root_cause,
        "resolution": resolution, "prevention": prevention,
    })
    result = {"id": lesson_id, "status": "recorded", "occurrences": 1}
    if similar:
        result["similar_lesson_hint"] = similar
    return result


def lesson_update(lesson_id: str, description: str | None = None,
                  root_cause: str | None = None, resolution: str | None = None,
                  prevention: str | None = None, severity: str | None = None,
                  projects: list | None = None, status: str | None = None,
                  delete: bool = False, *,
                  actor: str | None = None, model: str | None = None,
                  session: str | None = None) -> dict:
    """Correct or delete a recorded lesson. Only fields given are changed; the rest is left untouched."""
    actor, model, session = _identity(actor, model, session)
    conn = get_db()
    row = conn.execute("SELECT id FROM lessons_learned WHERE id = ?", (lesson_id,)).fetchone()
    if not row:
        log_access(conn, None, "lesson_update", query="lesson_nicht_gefunden",
                   actor=actor, model=model, session=session, status="rejected")
        conn.close()
        return {"error": f"Lesson not found: {lesson_id}"}

    if delete:
        conn.execute("DELETE FROM lessons_learned WHERE id = ?", (lesson_id,))
        log_access(conn, None, "lesson_delete", query=lesson_id, actor=actor, model=model, session=session)
        conn.commit()
        conn.close()
        return {"id": lesson_id, "status": "deleted"}

    raw = {
        "description": description, "root_cause": root_cause, "resolution": resolution,
        "prevention": prevention, "severity": severity, "projects": projects,
    }
    # Nur uebergebene Felder unmangeln/schreiben — derselbe Aufrufer-Fehler wie bei
    # lesson_record (Parametergrenze verrutscht ins Textfeld) kann hier genauso passieren.
    given = {k: v for k, v in raw.items() if v is not None}
    if given:
        fixed = unmangle_lesson_fields(given)
        given.update(fixed)

    updates = []
    params = []
    for col in ("description", "root_cause", "resolution", "prevention", "severity"):
        if col in given:
            updates.append(f"{col} = ?")
            params.append(given[col])
    if "projects" in given:
        updates.append("projects = ?")
        params.append(json.dumps(given["projects"] or []))
    if status is not None:
        updates.append("status = ?")
        params.append(status)

    if not updates:
        conn.close()
        return {"id": lesson_id, "status": "unchanged", "message": "Keine Felder uebergeben."}

    updates.append("last_seen = ?")
    params.append(now_iso())
    updates.append("actor = ?")
    params.append(actor)
    updates.append("session = ?")
    params.append(session)
    updates.append("model = ?")
    params.append(model)
    updates.append("client = ?")
    params.append(_KLIENT)
    params.append(lesson_id)

    conn.execute(f"UPDATE lessons_learned SET {', '.join(updates)} WHERE id = ?", params)

    updated_row = conn.execute("SELECT * FROM lessons_learned WHERE id = ?", (lesson_id,)).fetchone()

    # ADR-032 (loest P4 ab): frueher wurde die knowledge_embeddings-Zeile nur
    # bei description/root_cause/prevention GELOESCHT (der Embedding-Text
    # einer Lesson, siehe build_embeddings.py) -- resolution/severity/
    # projects/status loesten keine Loeschung aus. Aber last_seen bumpt bei
    # JEDEM Update, also waere selbst ein reiner resolution-Wechsel sofort
    # wieder ein vector_gaps-Fund (Vektor aelter als last_seen). Deshalb
    # jetzt unconditional neu gebaut statt geloescht. Schlaegt der Bau fehl,
    # bleibt die Luecke offen (siehe _rebuild_lesson_embedding).
    _rebuild_lesson_embedding(conn, lesson_id, updated_row["node_path"], updated_row["projects"],
                              updated_row["description"], updated_row["root_cause"],
                              updated_row["prevention"])
    log_access(conn, None, "lesson_update", query=lesson_id,
               actor=actor, model=model, session=session,
               affected_row=dict(updated_row) if updated_row else None)
    conn.commit()
    conn.close()
    _check_injection_suspects("lesson", lesson_id, {
        "description": given.get("description"), "root_cause": given.get("root_cause"),
        "resolution": given.get("resolution"), "prevention": given.get("prevention"),
    })
    return {"id": lesson_id, "status": "updated"}


def lesson_query(type_: str | None = None, project: str | None = None,
                 status: str = "active", max_results: int = 10,
                 query: str | None = None) -> dict:
    """Query lessons learned by type, project, or status. Optional `query`:
    Bedeutungs-/Stichwortsuche in description/root_cause/prevention (LIKE als
    Stichwort-Basis + optionale Embedding-Fusion, RRF wie knowledge_search).
    Ohne `query` unveraendertes Altverhalten (reine Filter, sortiert nach
    occurrences/last_seen)."""
    conn = get_db()
    conditions = []
    params = []

    if type_:
        conditions.append("type = ?")
        params.append(type_)
    if status:
        conditions.append("status = ?")
        params.append(status)
    if project:
        conditions.append("projects LIKE ?")
        params.append(f'%"{project}"%')

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    if not query:
        rows = conn.execute(
            f"SELECT * FROM lessons_learned {where} ORDER BY occurrences DESC, last_seen DESC LIMIT ?",
            (*params, max_results)
        ).fetchall()
        results = [dict(r) for r in rows]
        conn.close()
        return {"results": results, "count": len(results)}

    all_rows = conn.execute(f"SELECT * FROM lessons_learned {where}", tuple(params)).fetchall()
    by_id = {r["id"]: r for r in all_rows}
    # Mindestlaenge 4 + Stopwortfilter wie knowledge_recall_hook.py's STOP-Liste
    # (hier dupliziert, nicht importiert -- der Hook selbst bleibt unangetastet,
    # siehe Auftrag). Ohne Filter matchen 3-Buchstaben-Fuellwoerter ("die",
    # "und", "ist") als Substring in fast jedem Lesson-Text und ertraenken das
    # eigentliche Signal.
    _stop = {
        "und", "oder", "der", "die", "das", "den", "dem", "ein", "eine", "einen", "einem",
        "ist", "sind", "war", "wird", "werden", "kann", "soll", "muss", "für", "mit", "von",
        "auf", "aus", "bei", "zum", "zur", "des", "als", "auch", "nicht", "noch", "wie", "was",
        "wenn", "dann", "aber", "nur", "mir", "mich", "dir", "dich", "ich", "wir", "ihr", "sie",
        "sich", "durch", "the", "and", "for", "that", "this", "with", "from", "have", "has",
        "was", "are", "you", "can", "should", "must", "not", "how", "what", "when", "then",
    }
    _stop = {fold_de(w) for w in _stop}  # "für" -> auch "fuer" filtern, sonst leckt es durch
    # fold_de() statt .lower(): "Existenzgruender" (ue-Schreibung) muss dieselbe
    # Lesson finden wie "Existenzgründer" (ü) -- gleiche Luecke wie vorher bei
    # knowledge_search(), hier nur unbehoben, weil ein eigener Python-Substring-
    # Pfad statt FTS5 (siehe Auftrag: 374 Lehren standen weiter hinter der Wand).
    keywords = [w for w in re.findall(r"[A-Za-zÄÖÜäöüß0-9]{4,}", fold_de(query)) if w not in _stop]

    def kw_hits(row: sqlite3.Row) -> int:
        text = fold_de(f"{row['description']} {row['root_cause']} {row['prevention']}")
        return sum(1 for k in keywords if k in text)

    keyword_ordered_ids = sorted((i for i in by_id if kw_hits(by_id[i]) > 0),
                                  key=lambda i: kw_hits(by_id[i]), reverse=True)

    query_vec = embeddings.embed_text(query)
    embedding_ordered_ids = (
        _embedding_ranking(conn, "lesson", query_vec, set(by_id.keys())) if query_vec else []
    )
    final_ids = _fuse_with_keyword_floor(keyword_ordered_ids, embedding_ordered_ids, max_results)

    results = [dict(by_id[i]) for i in final_ids if i in by_id]
    conn.close()
    return {"results": results, "count": len(results)}


def _eintraege_nach(spalte: str, wert: str) -> dict:
    """Gemeinsamer Kern von knowledge_sitzung/knowledge_modell (Auftrag
    2026-08-06, Punkt 2 des Nachtrags: "Auswertung ergaenzen oder zweiter Weg,
    begruende"). Gewaehlt: EIN Kern, ZWEI duenne oeffentliche Funktionen --
    die SQL ist bis auf die WHERE-Spalte identisch, ein zweiter kompletter
    Funktionskoerper waere reine Kopie gewesen. spalte kommt nie vom Aufrufer
    (nur die beiden Funktionen unten rufen sie mit fest verdrahtetem 'session'
    bzw. 'model' auf), daher unkritisch als f-String in der Spaltenposition.
    NUR lesend, kein Zurueckziehen/Loeschen -- das gibt es bereits
    (knowledge_zurueckziehen/endgueltig_entfernen.py), ob es angewandt wird,
    entscheidet ein Mensch, nicht dieses Werkzeug."""
    conn = get_db()
    nodes = [dict(r) for r in conn.execute(
        f"SELECT id, path, title, summary, actor, session, model, created_at, updated_at "
        f"FROM knowledge_nodes WHERE {spalte} = ? ORDER BY created_at",
        (wert,),
    )]
    lessons = [dict(r) for r in conn.execute(
        f"SELECT id, type, description, actor, session, model, first_seen, last_seen "
        f"FROM lessons_learned WHERE {spalte} = ? ORDER BY first_seen",
        (wert,),
    )]
    conn.close()
    return {spalte: wert, "nodes": nodes, "lessons": lessons,
            "count": len(nodes) + len(lessons)}


def knowledge_sitzung(session: str) -> dict:
    """Reine Auswertung (Auftrag 2026-08-06, Punkt 3): alle Knoten und Lessons,
    die eine bestimmte Sitzung geschrieben hat -- der eigentliche Zweck der
    actor/session-Spalten, sonst waeren sie totes Gewicht."""
    return _eintraege_nach("session", session)


def knowledge_modell(model: str) -> dict:
    """Reine Auswertung nach Modell (Auftrag 2026-08-06, Nachtrag): Guete der
    Eintraege nach Herkunft messbar -- welches Modell hat abgelegt, wie oft
    wird das spaeter gezogen/korrigiert/zurueckgezogen. Gleiche Bauform wie
    knowledge_sitzung, siehe _eintraege_nach()."""
    return _eintraege_nach("model", model)


def knowledge_stats() -> dict:
    """Overview statistics of the knowledge database."""
    conn = get_db()
    total_nodes = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    by_project = dict(conn.execute(
        "SELECT project_id, COUNT(*) FROM knowledge_nodes GROUP BY project_id"
    ).fetchall())
    by_level = dict(conn.execute(
        "SELECT level, COUNT(*) FROM knowledge_nodes GROUP BY level"
    ).fetchall())
    total_lessons = conn.execute("SELECT COUNT(*) FROM lessons_learned").fetchone()[0]
    active_lessons = conn.execute("SELECT COUNT(*) FROM lessons_learned WHERE status = 'active'").fetchone()[0]
    escalated = conn.execute("SELECT COUNT(*) FROM lessons_learned WHERE status = 'escalated_to_rule'").fetchone()[0]
    recent_access = conn.execute(
        "SELECT action, COUNT(*) as cnt FROM access_log GROUP BY action"
    ).fetchall()
    # Anlass-Verteilung (Auftrag 2026-08-06) -- ganzer Zweck des Feldes.
    # selbst/betreiber selbstberichtet, hook/skript objektiv, siehe
    # ALLOWED_ANLASS. Getrennt fuer Knoten und Lehren, nicht zusammengefasst.
    nodes_by_anlass = dict(conn.execute(
        "SELECT anlass, COUNT(*) FROM knowledge_nodes GROUP BY anlass"
    ).fetchall())
    lessons_by_anlass = dict(conn.execute(
        "SELECT anlass, COUNT(*) FROM lessons_learned GROUP BY anlass"
    ).fetchall())
    conn.close()

    return {
        "nodes_total": total_nodes,
        "nodes_by_project": by_project,
        "nodes_by_level": by_level,
        "nodes_by_anlass": nodes_by_anlass,
        "lessons_total": total_lessons,
        "lessons_active": active_lessons,
        "lessons_escalated": escalated,
        "lessons_by_anlass": lessons_by_anlass,
        "access_patterns": dict(recent_access),
        "db_path": str(DB_PATH),
        "timestamp": now_iso()
    }


# recall_log.jsonl liegt neben der DB, gleiche Ableitung wie RECALL_LOG in
# hub/scripts/knowledge_recall_hook.py (dort bewusst dupliziert, nicht
# importiert -- getrennte Prozesse ohne gemeinsamen sys.path, siehe
# _cwd_project-Docstring fuer dasselbe Muster). Modulweite Konstante statt
# Funktionsparameter mit Vorgabewert, aber als eigener Name (nicht inline),
# damit ein Test sie per monkeypatch auf eine tmp_path-Kopie umbiegen kann.
RECALL_LOG_PATH = Path(__file__).parent / "recall_log.jsonl"


def _recall_sessions(kind: str, ref: str, log_path: Path | None = None) -> int:
    """Anzahl VERSCHIEDENER Sitzungen, die `ref` (Knotenpfad oder Lehren-ID)
    in recall_log.jsonl eingespielt bekamen -- nach SITZUNG dedupliziert,
    nicht nach Zeile. Kern der Selbstverstaerker-Abwehr fuer dieses Signal
    (siehe knowledge_trust_score-Docstring, Punkt 2): eine Sitzung, die den
    Hook zehnmal hintereinander mit denselben Schluesselwoertern ausloest
    (derselbe unpassende Knoten wird jedes Mal erneut eingespielt, Befund
    2026-08-06), zaehlt hier EINMAL, nicht zehnmal -- sonst waere Haeufigkeit
    der Anfrage mit Nuetzlichkeit des Treffers verwechselt.

    Gegenprobe (Konsil-Review 2026-08-07) an echten Daten deckte auf, dass
    der Dedup-Schluessel wirkungslos war: 428 von 579 recall_log-Zeilen
    tragen kein "session"-Feld (Altbestand vor dessen Einfuehrung), der
    damalige Fallback entry.get("ts") ist PRO ZEILE eindeutig (Sekunden-
    genau) -- ein Knoten mit 363 Zeilen ohne "session" wurde zu 276
    "Sitzungen" statt zu 9 tatsaechlichen Tagen, tanh saettigte prompt aufs
    Maximum. Genau die Ruckkopplung, die der Auftrag verbietet, aber durch
    den Dedup-Schluessel selbst, nicht durch die tanh-Kurve. Fix: Zeilen ohne
    "session" fallen auf den TAG (ts[:10]) zurueck -- ein ehrlicher,
    grober Sitzungs-Ersatz fuer den Altbestand, kein Pro-Zeile-Unikat mehr.
    Bounded window (Hook kappt recall_log.jsonl haelftig bei 1MB, siehe
    RECALL_LOG_MAX_BYTES in knowledge_recall_hook.py): das Signal ist ein
    gleitendes Fenster, kein Lebenszeit-Gesamtwert -- ein Score kann rein
    dadurch sinken, dass alte Zeilen aus dem Fenster fallen, nicht weil sich
    an der Bewaehrung etwas geaendert haette."""
    log_path = log_path if log_path is not None else RECALL_LOG_PATH
    field = "lessons" if kind == "lesson" else "nodes"
    sessions: set = set()
    try:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue  # kaputte Zeile ueberspringen statt abzubrechen
                values = entry.get(field)
                if not isinstance(values, list) or ref not in values:
                    continue  # kaputte Zeile (z.B. String statt Liste) -> kein Teilstring-Fehltreffer
                sessions.add(entry.get("session") or (entry.get("ts") or "")[:10])
    except OSError:
        return 0
    return len(sessions)


def _wirkung_counts(kind: str, canonical: str, events_for_ref: dict | None = None) -> dict:
    """Wirkungs-Zaehlung EINES Eintrags, aus wirkung.py abgeleitet OHNE
    wirkung.py zu aendern (Auftrag 2026-08-07 Schritt 2, Grenze -- nur
    benutzen). wirkung.report() zaehlt global ueber ALLE Refs; hier auf
    GENAU canonical gefiltert, weil trust_score einen einzelnen Eintrag
    bewertet. events-Key ist bereits der geloggte path/id (log_recall
    schreibt n['path'] bzw. l['id']) -- derselbe Wert wie canonical hier.

    events_for_ref (L-80e002, 2026-08-07): {session: ts} NUR fuer diesen
    canonical, aus einem vorab gebauten Aggregat (_trust_aggregate()) --
    spart den kompletten Protokoll-Scan, wenn der Aufrufer schon eine ganze
    Kandidatenliste vorbereitet hat. None (Vorgabe) heisst weiterhin: eigener
    voller Scan wie bisher, unveraendertes Verhalten fuer Einzelaufrufe."""
    import wirkung  # noqa: PLC0415 -- verzoegert wie knowledge_lint oben
    if events_for_ref is None:
        # RECALL_LOG_PATH explizit durchreichen (nicht wirkung.py's eigenen
        # Default nutzen) -- sonst bleibt dieses Modul bei Tests unisoliert:
        # _recall_sessions() oben respektiert bereits monkeypatch.setattr(kms,
        # "RECALL_LOG_PATH", ...), dieselbe Stelle muss auch hier gelten.
        all_events = wirkung._recall_events(kind, log_path=RECALL_LOG_PATH)
        events_for_ref = {s: ts for (s, r), ts in all_events.items() if r == canonical}
    counts = {"genutzt": 0, "ignoriert": 0, "widerlegt": 0}
    if not events_for_ref:
        return counts
    conn = get_db()
    try:
        for session, ts in events_for_ref.items():
            counts[wirkung.outcome(kind, canonical, session, ts, conn)] += 1
    finally:
        conn.close()
    return counts


def _trust_aggregate(kind: str, log_path: Path | None = None, db_path: Path | None = None) -> dict:
    """Einmal-Scan fuer eine GANZE Kandidatenliste statt je-Kandidat-Scan
    (L-80e002, gemessen 2026-08-07: knowledge_trust_score() las das
    recall_log bisher JE AUFRUF komplett neu ein -- Kosten wuchsen linear
    mit der Kandidatenzahl statt konstant zu bleiben, blockierte den
    Schattenlauf im Abruf-Hook, siehe SCHATTEN_ZEIT_BUDGET_S dort).

    Liest recall_log EINMAL, gruppiert nach Ziel (ref) -- Aufrufer (z.B.
    _apply_trust_score() im Hook) baut dieses Aggregat einmal pro Sortierlauf
    und reicht es an jeden knowledge_trust_score()-Aufruf durch. Ohne
    aggregate faellt die Funktion weiter auf den alten Pro-Kandidat-Scan
    zurueck (Rueckwaertskompatibel, keine Formel geaendert, siehe dort)."""
    import wirkung  # noqa: PLC0415
    log_path = log_path if log_path is not None else RECALL_LOG_PATH
    db_path = db_path if db_path is not None else DB_PATH
    field = "lessons" if kind == "lesson" else "nodes"
    sessions_by_ref: dict[str, set] = {}
    try:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                values = entry.get(field)
                if not isinstance(values, list):
                    continue
                sess = entry.get("session") or (entry.get("ts") or "")[:10]
                for ref in values:
                    sessions_by_ref.setdefault(ref, set()).add(sess)
    except OSError:
        pass

    events_by_ref: dict[str, dict] = {}
    for (session, ref), ts in wirkung._recall_events(kind, log_path=log_path).items():
        events_by_ref.setdefault(ref, {})[session] = ts

    genutzt_bestandsweit = wirkung.report(kind, log_path=log_path, db_path=db_path)["genutzt"] > 0

    return {
        "sessions_by_ref": sessions_by_ref,
        "events_by_ref": events_by_ref,
        "genutzt_bestandsweit": genutzt_bestandsweit,
    }


def knowledge_trust_score(kind: str, ref: str, aggregate: dict | None = None) -> dict:
    """VERDIENTER Vertrauenswert, GERECHNET bei jedem Aufruf statt
    gespeichert -- wie der Konfidenzverfall in konfidenz.py (dortiger
    Docstring: ein gespeicherter Wert veraltet still, sobald sich die
    zugrundeliegenden Ereignisse aendern und niemand den Wert manuell
    nachzieht). Kein neues Feld auf knowledge_nodes/lessons_learned, keine
    Migration -- reiner Lesezugriff auf drei bereits vorhandene Quellen.

    ABGRENZUNG zu norm_rang (Auftrag 2026-08-07, Vergleich mit Hermes Agent/
    Nous Research store.py, MIT-lizenziert, im Quelltext gelesen): norm_rang
    wird von einem Menschen/Konsil ERKLAERT ("diese Regel gewinnt bei
    Widerspruch") -- ohne Erklaerung existiert er nicht (buckeberg musste am
    2026-08-06 erst eine Rangordnung anlegen, bevor es ablegen konnte).
    trust_score wird von NIEMANDEM behauptet, er ergibt sich aus Nutzung --
    "wie gut hat sich dieser Eintrag bewaehrt". Beide Fragen sind
    unabhaengig: ein hochrangiger Fakt kann selten gebraucht werden (niedriger
    trust_score, trotzdem die geltende Regel), ein Fakt ohne Rang kann sich
    haeufig bewaehren. Deshalb ZWEI Werte, kein Ersatz des einen durch den
    anderen -- norm_rang bleibt unangetastet.

    FUENF EINGANGSGROESSEN, gegeneinander abgewogen (Konsil-Review 2026-08-07
    korrigierte drei Befunde am urspruenglichen Entwurf, siehe Anmerkungen;
    Signal 5 -- Wirkung -- kam mit demselben Auftrag als Schritt 2 dazu):

    1. BEWUSSTES LESEN (staerkstes Signal, NUR Knoten) -- access_log, action
       IN ('read','browse'), status='completed', node_path = ref. Nur fuer
       Knoten verfuegbar: knowledge_read/knowledge_browse protokollieren so;
       fuer Lehren gibt es (Stand 2026-08-07) keine entsprechende
       Einzelabruf-Aktion in access_log. Ehrlich als 0 statt erfunden.
    2. RECALL-EINSPIELUNG (schwaches Signal, siehe _recall_sessions) --
       recall_log.jsonl, nach SITZUNG dedupliziert (Fix 2026-08-07: Zeilen
       ohne "session"-Feld fallen auf den Tag zurueck, nicht auf die
       sekundengenaue Zeile, siehe dortiger Docstring). Fuer beide Sorten
       verfuegbar. Schwach, WEIL passiv: der Hook spielt per FTS/BM25-
       Vorauswahl ein, nicht weil ein Mensch/Modell den Treffer bewusst
       bestaetigt hat -- Befund 2026-08-06, derselbe unpassende Knoten wurde
       zehnmal eingespielt, ohne dass das etwas ueber seine Guete aussagt.
    3. UNABHAENGIGE WIEDERHOLUNG (schwaches Signal, NUR Lehren) --
       lessons_learned.occurrences - 1. lesson_record() erhoeht occurrences
       nur, wenn eine SPAETERE, unabhaengige Sitzung dieselbe Lehre per
       same_as erneut meldet (Dedup-Pfad) -- das bestaetigt, dass die Lehre
       unabhaengig reproduziert wurde, nicht bloss einmal notiert. -1, weil
       jede Lehre mit Vorgabewert occurrences=1 startet (kein Signal ohne
       Wiederholung). Ersatz fuer Signal 1 auf der Lehrenseite, ohne neue
       Protokollierung (Auftrag: nichts neu erheben). GEGENARGUMENT, das
       das kleine Gewicht rechtfertigt: eine wiederkehrende Lehre kann auch
       heissen, dass ihre prevention NICHT gewirkt hat -- der Zaehler
       bestaetigt die EXISTENZ/Relevanz des Problems, nicht die Wirksamkeit
       der Abhilfe. status='escalated_to_rule' bewusst NICHT als Bonus
       gewertet: das ist eine ERKLAERTE Eskalation (norm_rang-Seite), keine
       verdiente.
    4. ABLEHNUNGEN (schwaches Gegensignal, NUR Knoten -- Konsil-Review
       2026-08-07, urspruenglicher Entwurf hier falsch): "Lehren-ID steht im
       query-Feld rejizierter lesson_update/lesson_delete-Versuche" stimmt
       nicht -- der einzige Rejection-Pfad in lesson_update() schreibt
       query="lesson_nicht_gefunden" (den GRUND, wie die Konvention am
       Dateikopf verlangt), nie die ID; lesson_delete traegt zwar
       query=lesson_id, aber status='completed'. Der Pfad liefert also
       GARANTIERT immer 0 -- kein schwaches Signal, sondern ein totes.
       Schlimmer: die drei rejected-Stellen in lesson_record() (anlass_
       ungueltig/beschreibung_leer/same_as_ungueltig) schreiben node_path
       des VERKNUEPFTEN Knotens, nicht der Lehre -- ein missglueckter
       Lehren-Schreibversuch haette sonst den Wert eines voellig unbeteiligten
       Knotens gesenkt. Fuer Lehren deshalb ehrlich fest 0, keine Abfrage.
       Fuer Knoten: node_path = ref, AND action NOT LIKE 'lesson%' (schliesst
       genau diese Fehlzuschreibung aus, falls node_path zufaellig gesetzt
       war).

    KEIN SELBSTVERSTAERKER (Auftrag, explizite Auflage): zwei unabhaengige
    Sperren, nicht nur eine.
      a) Saettigende Funktion (tanh) statt linearer Zaehlung fuer jedes
         Signal: der 1. bewusste Lesevorgang zaehlt fast voll, der 50. kaum
         noch mehr (tanh(50/5) ≈ tanh(5) ≈ 0.9999, tanh(1/5) ≈ 0.197) --
         ein Eintrag kann sich nicht durch schiere Wiederholung beliebig
         hochschaukeln, der Grenznutzen sinkt von Anfang an.
      b) Recall-Signal zaehlt SITZUNGEN, nicht ZEILEN (_recall_sessions) --
         zehn Einspielungen derselben Sitzung sind ein Datenpunkt, nicht
         zehn. Ohne diese Dedup wuerde ein haeufig (aber falsch) gezogener
         Knoten seinen eigenen hohen Wert durch genau die Haeufigkeit
         erzeugen, die der Auftrag ausdruecklich als Trugschluss benennt.
      Was BEWUSST NICHT als Signal verwendet wird: reine Erwaehnung in
      knowledge_search()-Trefferlisten (action='search') -- ein Treffer, der
      nur ANGEZEIGT wurde, ist noch keine Bestaetigung, dieselbe Falle wie
      die passive Recall-Einspielung, nur ungefiltert durch die
      Sitzungs-Dedup obendrein. Nur tatsaechlich VOLLZOGENE Zugriffe
      (read/browse/recall-Einspielung) und tatsaechlich VOLLZOGENE
      Ablehnungen zaehlen.
    5. WIRKUNG (STAERKSTES Signal, beide Sorten) -- wirkung.py, ref-gefiltert
       (siehe _wirkung_counts). Staerker als Signal 2 (Recall-Einspielung),
       weil es NICHT an der Einspielung haengt, sondern am AUSGANG danach --
       genau der Unterschied, den PLAN_SELBSTLERNEN_2026-08-07.md Schritt 2
       verlangt ("misst nur noch Sichtbarkeit" vs. misst Wirkung). Drei
       Zustaende je Einspielung, 'widerlegt' hat in wirkung.outcome() bereits
       Vorrang vor 'genutzt' (fruehere Rueckgabe) -- diese Rangfolge setzt
       sich hier fort, weil pro Sitzung nur EIN Zustand gezaehlt wird.
       'unauswertbar' (fehlende Sitzung/Zeitstempel im Recall-Log) wirkt
       NICHT -- weder hebend noch senkend, siehe RUECKWIRKUNGS-GRENZE unten.

    RUECKWIRKUNGS-GRENZE (Auftrag 2026-08-07 Schritt 2, Auflage 3): Wirkung
    wird erst AB diesem Auftrag erhoben (wirkung.py-Moduldoc). Ein Eintrag
    von VOR dem Auftrag hat also grundsaetzlich 0 genutzt/0 ignoriert/0
    widerlegt -- nicht weil er sich nicht bewaehrt hat, sondern weil es die
    Messung noch nicht gab. tanh(0/n) = 0 fuer alle drei Terme: ein Eintrag
    ganz ohne Wirkungsdaten bekommt WEDER Bonus NOCH Abzug, sein Score haengt
    dann allein an den Signalen 1-4 wie bisher. Das ist keine Zusatzregel,
    sondern die Konsequenz der Sattelfunktion -- Beleg in trust_score_test.py.

    SKALA: 0.5 = Vorgabewert ohne jedes Signal (identisch zur Vorgabe von
    knowledge_nodes.confidence -- dieselbe Konvention, keine neue Skala
    erfunden). Geklemmt auf [0.05, 0.95]: nie ganz 0 (ein Eintrag ohne jede
    Nutzung ist unbewaehrt, nicht widerlegt) und nie ganz 1 (ein verdienter
    Wert bleibt immer nachtraeglich revidierbar, volles Vertrauen waere eine
    Behauptung, die dieser Mechanismus gerade vermeiden soll).

    aggregate (L-80e002, 2026-08-07): von _trust_aggregate() vorgebautes
    Protokoll-Aggregat, vom Aufrufer EINMAL fuer eine ganze Kandidatenliste
    erzeugt und hier je Kandidat nur nachgeschlagen -- spart den kompletten
    Protokoll-Scan pro Aufruf. None (Vorgabe): unveraendertes Verhalten,
    eigener voller Scan wie vor diesem Auftrag. Die ausgegebene Zahl ist in
    beiden Faellen identisch, nur der Weg dahin unterscheidet sich."""
    conn = get_db()
    if kind == "node":
        row = conn.execute(
            "SELECT id, path FROM knowledge_nodes WHERE id = ? OR path = ?", (ref, ref)
        ).fetchone()
        canonical = row["path"] if row else ref
        exists = row is not None
        deliberate = conn.execute(
            "SELECT COUNT(*) FROM access_log WHERE node_path = ? AND action IN ('read','browse') "
            "AND status = 'completed'", (canonical,)
        ).fetchone()[0]
        wiederholung = 0  # nur Lehren, siehe Docstring Punkt 3
        rejected = conn.execute(
            "SELECT COUNT(*) FROM access_log WHERE node_path = ? AND status = 'rejected' "
            "AND action NOT LIKE 'lesson%'", (canonical,)
        ).fetchone()[0]
    elif kind == "lesson":
        canonical = ref
        row = conn.execute("SELECT occurrences FROM lessons_learned WHERE id = ?", (ref,)).fetchone()
        exists = row is not None
        deliberate = 0  # siehe Docstring Punkt 1 -- kein Signal fuer Lehren vorhanden
        wiederholung = max(0, (row["occurrences"] if row else 1) - 1)
        rejected = 0  # siehe Docstring Punkt 4 -- Rejection-Pfad liefert fuer Lehren nie eine ID, toter Signalweg
    else:
        conn.close()
        return {"error": f"kind muss 'node' oder 'lesson' sein, nicht {kind!r}"}
    conn.close()

    if aggregate is not None:
        recall_sessions = len(aggregate["sessions_by_ref"].get(canonical, ()))
        wirkung_n = _wirkung_counts(kind, canonical, aggregate["events_by_ref"].get(canonical, {}))
        genutzt_bestandsweit = aggregate["genutzt_bestandsweit"]
    else:
        recall_sessions = _recall_sessions(kind, canonical)
        wirkung_n = _wirkung_counts(kind, canonical)
        # Auftrag 2026-08-07 (Nachtrag, Folge des Session-Formatfehlers oben):
        # der ignoriert-Abzug darf nur wirken, wenn im GESAMTEN Bestand (nicht
        # nur bei diesem Eintrag) schon mindestens ein 'genutzt' beobachtet
        # wurde. Solange 'genutzt' strukturell unerreichbar war (Session-Format
        # nie deckungsgleich, siehe wirkung.py::outcome()), war 'ignoriert' ein
        # Signal, das NUR senken konnte -- eine Strafe fuer alle statt einer
        # Messung. import verzoegert wie bei _wirkung_counts oben; log_path/
        # db_path explizit durchgereicht, sonst unisoliert bei Tests (dieselbe
        # Begruendung wie dort).
        import wirkung  # noqa: PLC0415
        genutzt_bestandsweit = wirkung.report(kind, log_path=RECALL_LOG_PATH, db_path=DB_PATH)["genutzt"] > 0
    ignoriert_abzug = 0.10 * math.tanh(wirkung_n["ignoriert"] / 5) if genutzt_bestandsweit else 0.0
    # 0.35 > 0.30 (Signal 1): Wirkung ist das staerkste Signal (Docstring
    # Punkt 5). Rueckwirkungs-Grenze: alle drei Zaehler sind 0 fuer jeden
    # Eintrag ohne Wirkungsdaten -> tanh(0/n)=0 -> Term traegt nichts bei,
    # weder Bonus noch Abzug (siehe Docstring RUECKWIRKUNGS-GRENZE).
    score = (
        0.5
        + 0.30 * math.tanh(deliberate / 5)
        + 0.10 * math.tanh(recall_sessions / 10)
        + 0.15 * math.tanh(wiederholung / 2)
        - 0.15 * math.tanh(rejected / 3)
        + 0.35 * math.tanh(wirkung_n["genutzt"] / 3)
        - ignoriert_abzug
        - 0.35 * math.tanh(wirkung_n["widerlegt"] / 2)
    )
    score = max(0.05, min(0.95, score))
    return {
        "kind": kind, "ref": canonical, "exists": exists, "trust_score": round(score, 4),
        "inputs": {
            "bewusstes_lesen": deliberate,
            "recall_sitzungen": recall_sessions,
            "unabhaengige_wiederholung": wiederholung,
            "ablehnungen": rejected,
            "wirkung_genutzt": wirkung_n["genutzt"],
            "wirkung_ignoriert": wirkung_n["ignoriert"],
            "wirkung_widerlegt": wirkung_n["widerlegt"],
        },
    }


# Je-Kategorie-Entscheidung fuer kurator_lauf() (Auftrag 2026-08-07, Vergleich
# mit Hermes Agent curator.py: "Never auto-deletes -- only archives"). Jede
# der 16 Befund-Kategorien aus knowledge_lint.run() einzeln bewertet -- fuer
# 15 lautet die Antwort NEIN, mit Begruendung, nicht nur behauptet:
#   orphans                braucht Reparatur (Elternknoten setzen), keine Inhaltsloeschung
#   stale                  Alter allein ist kein Wahrheitsurteil
#   never_pulled_*         Auftrag selbst: blosses (Nicht-)Abrufen ist ein schwaches Signal
#   vector_gaps            technische Luecke (Embedding fehlt) -- Werkzeug ist build_embeddings.py
#   near_duplicate_lessons "Kandidat", keine Gewissheit; welche Seite kanonisch ist, ist eine Wertfrage
#   path_hygiene           braucht Umbenennung, keine Zurueckziehung
#   truncated_embeddings   technisch, wie vector_gaps
#   escalated_without_rule Verknuepfungsfehler/Normebene, kein Inhaltsurteil
#   norm_conflicts         GENAU die Frage, die norm_rang beantwortet -- Menschendomaene per Definition
#   missing_source         Metadatenluecke, kein Wahrheitsproblem; Trigger verhindert das seit 2026-08-06 fuer Neues
#   stale_source            Provenienzfrage (Hash/Datei), kein Urteil ueber den Inhalt selbst
#   broken_chain            betrifft das Protokoll selbst, kein Knoten/Lehre zum Handeln
#   anker_queue_backlog     betrifft externe Verankerung, kein Zurueckziehen-Ziel
#   confidence_decay        Aufforderung zur Neupruefung, kein Fehlurteil -- Erase waere unverhaeltnismaessig
#   rejections              kein Bestand zum Handeln (der Schreibversuch ist schon gescheitert)
# EINE Kategorie handelt: injection_suspects, NUR sicherheit='hart' (die
# staerkste der drei Stufen aus einschleusung.py, siehe dortiges
# _SEV_ORDER) -- ein objektiv erkennbares Sicherheitsmuster, kein
# Werturteil ueber Wahrheit/Falschheit des Inhalts. 'stark'/'auffaellig'
# bleiben nur gemeldet (Fehlalarmrisiko fuer automatisches Handeln zu hoch).
# Selbst dort NUR fuer kind='node': lessons_learned hat KEIN Zurueckziehen
# (kein zurueckgezogen*-Spaltensatz wie knowledge_nodes) -- die einzige
# Loeschoperation fuer Lehren ist lesson_update(delete=True), ein echtes
# DELETE ohne Umkehrweg. Dritte Auflage des Auftrags ("wo nicht umkehrbar,
# wird nicht gehandelt, sondern gemeldet") schliesst Lehren deshalb aus,
# auch bei sicherheit='hart'.
_KURATOR_KATEGORIEN_OHNE_HANDLUNG = {
    "orphans": "braucht Reparatur (Elternknoten setzen), keine Inhaltsloeschung",
    "stale": "Alter allein ist kein Wahrheitsurteil",
    "never_pulled_nodes": "blosses Nicht-Abrufen ist laut Auftrag ein schwaches Signal",
    "never_pulled_lessons": "blosses Nicht-Abrufen ist laut Auftrag ein schwaches Signal",
    "vector_gaps": "technische Luecke -- Werkzeug ist build_embeddings.py, nicht Zurueckziehen",
    "near_duplicate_lessons": "Kandidat, keine Gewissheit; welche Seite kanonisch ist, ist eine Wertfrage",
    "path_hygiene": "braucht Umbenennung, keine Zurueckziehung",
    "truncated_embeddings": "technisch, wie vector_gaps",
    "escalated_without_rule": "Verknuepfungsfehler/Normebene, kein Inhaltsurteil",
    "norm_conflicts": "genau die Frage, die norm_rang beantwortet -- Menschendomaene per Definition",
    "missing_source": "Metadatenluecke, kein Wahrheitsproblem; Trigger verhindert das seit 2026-08-06 fuer Neues",
    "stale_source": "Provenienzfrage (Hash/Datei), kein Urteil ueber den Inhalt selbst",
    "broken_chain": "betrifft das Protokoll selbst, kein Knoten/Lehre zum Handeln",
    "anker_queue_backlog": "betrifft externe Verankerung, kein Zurueckziehen-Ziel",
    "confidence_decay": "Aufforderung zur Neupruefung, kein Fehlurteil -- Erase waere unverhaeltnismaessig",
    "rejections": "kein Bestand zum Handeln (der Schreibversuch ist schon gescheitert)",
}


def kurator_lauf(*, scharf: bool = False, actor: str | None = None,
                 model: str | None = None, session: str | None = None) -> dict:
    """Hintergrund-Kurator (Auftrag 2026-08-07, Vergleich mit Hermes Agent
    curator.py: "Never auto-deletes -- only archives"). knowledge_lint.py
    MELDET nur -- dieser Modus HANDELT zusaetzlich, aber ausschliesslich
    innerhalb der seit heute vorhandenen Grenze: knowledge_zurueckziehen()
    (reversibel in der Sichtbarkeit ueber knowledge_freigeben, siehe dortiger
    Docstring) statt endgueltig_entfernen.py (nur von Hand, kein
    MCP-Werkzeug). Siehe _KURATOR_KATEGORIEN_OHNE_HANDLUNG oben fuer die
    Begruendung je NICHT gehandelter Kategorie -- 15 von 16, absichtlich.

    DREI AUFLAGEN (Auftrag, woertlich):
    1. "Jede Handlung braucht eine Begruendung im Datensatz, wie beim
       Zurueckziehen. Kein stilles Aufraeumen." -- jede Handlung ruft
       knowledge_zurueckziehen(node_id, grund=...) auf, grund ist Pflicht
       (das Werkzeug lehnt sonst ab, siehe dortige Pruefung) und nennt
       Kategorie + Fundstelle, keine generische Floskel.
    2. "Vorgabe ist TROCKENLAUF. Handeln nur auf ausdruecklichen Schalter."
       -- scharf=False ist der Funktions-Vorgabewert. Ohne scharf=True wird
       NICHTS geschrieben, auch nicht die handelbare Kategorie: jede
       Handlung landet nur als {"ausgefuehrt": False, ...} im Bericht.
    3. "Alles ist umkehrbar. Wo nicht, wird nicht gehandelt, sondern
       gemeldet." -- deshalb NUR knowledge_nodes (kind='node'), NIEMALS
       Lehren (siehe Kommentar oben: kein Zurueckziehen fuer Lehren, nur ein
       echtes DELETE) und NUR sicherheit='hart' (die anderen zwei Stufen
       bleiben, gleiches Prinzip, nur gemeldet -- ein Fehlalarm waere zwar
       technisch umkehrbar, aber das Risiko eines falschen Sicherheitsurteils
       ist der Grund, warum ueberhaupt nur eine Kategorie handelt).

    Liest ueber knowledge_lint.run() (verzoegerter Import: knowledge_lint.py
    importiert seinerseits aus DIESEM Modul -- fold_de, SLUG_MAX_LEN,
    compute_ketten_hash -- ein Top-Level-Import hier waere ein echter Zirkel;
    verzoegert bis zum Aufruf ist unschaedlich, weil dieses Modul dann
    laengst vollstaendig in sys.modules steht)."""
    import knowledge_lint  # noqa: PLC0415 -- absichtlich verzoegert, siehe Docstring

    bericht = knowledge_lint.run(db_path=DB_PATH, log_path=RECALL_LOG_PATH)

    def _anzahl(wert):
        # Manche Kategorien sind Listen (orphans, stale, ...), manche
        # Dicts mit mehreren Unterlisten (escalated_without_rule,
        # norm_conflicts, stale_source, broken_chain) -- Summe aller
        # Listenwerte darin statt eines nichtssagenden None.
        if isinstance(wert, list):
            return len(wert)
        if isinstance(wert, dict):
            return sum(len(v) for v in wert.values() if isinstance(v, list))
        return None

    kategorien = {
        name: {"anzahl": _anzahl(bericht.get(name)), "handlung": "keine", "begruendung": begruendung}
        for name, begruendung in _KURATOR_KATEGORIEN_OHNE_HANDLUNG.items()
    }

    hart_treffer = [f for f in bericht["injection_suspects"] if f.get("sicherheit") == "hart"]
    kategorien["injection_suspects"] = {
        "anzahl": len(bericht["injection_suspects"]),
        "anzahl_hart": len(hart_treffer),
        "handlung": "zurueckziehen (nur kind=node, nur sicherheit=hart)",
        "begruendung": "objektiv erkennbares Sicherheitsmuster (Einschleusungsverdacht), kein "
                        "Werturteil ueber Wahrheit/Falschheit -- 'stark'/'auffaellig' bleiben nur "
                        "gemeldet (Fehlalarmrisiko zu hoch), Lehren bleiben ausgeschlossen (kein "
                        "Zurueckziehen fuer lessons_learned, siehe Auflage 3)",
    }

    # Nach (kind, ref) gruppiert statt je Fund einzeln zu handeln: derselbe
    # Text kann mehrere hart-Muster gleichzeitig treffen (z.B. sowohl
    # <|im_start|> als auch <|im_end|> im selben content-Feld) -- ohne
    # Gruppierung riefe kurator_lauf knowledge_zurueckziehen() mehrfach fuer
    # denselben Knoten auf, das Werkzeug selbst hat dagegen keine Sperre
    # (ueberschreibt grund/Zeitstempel beim zweiten Aufruf still) und der
    # Bericht wuerde zwei Aktionen fuer eine Zurueckziehung zeigen.
    gruppen: dict[tuple[str, str], list[dict]] = {}
    for fund in hart_treffer:
        gruppen.setdefault((fund["kind"], fund["ref"]), []).append(fund)

    aktionen = []
    for (kind_, ref_), funde in gruppen.items():
        muster_liste = sorted({f["muster"] for f in funde})
        felder = sorted({f["feld"] for f in funde})
        grund = (f"Kurator: Einschleusungsverdacht (sicherheit=hart, Muster {', '.join(muster_liste)}, "
                 f"Feld {', '.join(felder)}) -- automatisch zurueckgezogen, siehe knowledge_lint.py "
                 f"Kategorie 15 / einschleusung.py")
        eintrag = {"kind": kind_, "ref": ref_, "felder": felder, "muster": muster_liste, "grund": grund}
        if kind_ != "node":
            eintrag["ausgefuehrt"] = False
            eintrag["nicht_ausgefuehrt_weil"] = ("Lehren haben kein Zurueckziehen -- nur ein echtes "
                                                  "DELETE (lesson_update delete=True), nicht umkehrbar "
                                                  "(Auflage 3): gemeldet, nicht gehandelt.")
        elif not scharf:
            eintrag["ausgefuehrt"] = False
            eintrag["nicht_ausgefuehrt_weil"] = "Trockenlauf (Vorgabe) -- scharf=True noetig."
        else:
            ergebnis = knowledge_zurueckziehen(ref_, grund, actor=actor or "kurator",
                                               model=model, session=session)
            eintrag["ausgefuehrt"] = "error" not in ergebnis
            eintrag["ergebnis"] = ergebnis
        aktionen.append(eintrag)

    return {
        "modus": "scharf" if scharf else "trockenlauf",
        "kategorien": kategorien,
        "aktionen": aktionen,
        "aktionen_ausgefuehrt": sum(1 for a in aktionen if a.get("ausgefuehrt")),
        "timestamp": now_iso(),
    }


# ─── MCP Server Protocol (stdio JSON-RPC 2.0) ───────────────────────────

# ── Annahmen (Uebernahme aus der Stiftshuette, 2026-08-08) ────────────────
# Die Regeln stehen an der Tabelle (schema.sql), nicht hier. Diese drei
# Funktionen sind der SCHREIBER -- ohne ihn waere die Tabelle das, was
# assumptions.json in der Stiftshuette war: ein Schema ohne Befueller, sieben
# von dreizehn Dateien dort hatten keinen.

def annahme_erfassen(annahme: str, kosten_wenn_falsch: str, belegrang: str = "geraten",
                     beleg: str = "", kategorie: str = "", projects: list | None = None,
                     node_path: str = "", notizen: str = "", anlass: str = "unbekannt", *,
                     actor: str | None = None, model: str | None = None,
                     session: str | None = None) -> dict:
    """Eine Annahme festhalten, solange sie noch als Annahme erkennbar ist.

    Der Zweck ist der Zeitpunkt: eine Annahme, die man erst nachtraeglich als
    solche erkennt, ist bereits als Messung weitergetragen worden. Deshalb
    sind belegrang und kosten_wenn_falsch Pflicht -- beide zwingen beim
    Aufschreiben zu einer Aussage, die man spaeter gegen sich gelten lassen
    muss.

    Die Ablehnungen kommen aus der Datenbank (CHECK/TRIGGER), nicht von hier;
    ein zweiter Regelsatz im Aufrufer waere die naechste Stelle, die
    auseinanderlaeuft."""
    conn = get_db()
    annahme_id = f"A-{str(uuid.uuid4())[:6]}"
    jetzt = now_iso()
    try:
        conn.execute(
            """INSERT INTO annahmen (id, annahme, kategorie, status, beleg, belegrang,
                                     kosten_wenn_falsch, notizen, projects, node_path,
                                     created_at, updated_at, anlass, actor, session, model, client)
               VALUES (?, ?, ?, 'offen', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (annahme_id, annahme, kategorie or None, beleg, belegrang, kosten_wenn_falsch,
             notizen, json.dumps(projects or []), node_path or None, jetzt, jetzt,
             anlass, actor, session, model, _KLIENT),
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        log_access(conn, node_path or None, "annahme", actor=actor, model=model,
                   session=session, status="rejected", query=str(e))
        conn.close()
        return {"status": "rejected", "error": str(e)}
    log_access(conn, node_path or None, "annahme", query=annahme,
               actor=actor, model=model, session=session,
               affected_row={"id": annahme_id, "annahme": annahme, "belegrang": belegrang,
                             "kosten_wenn_falsch": kosten_wenn_falsch, "status": "offen"})
    conn.close()
    return {"id": annahme_id, "status": "offen", "belegrang": belegrang}


def annahme_entscheiden(annahme_id: str, status: str, beleg: str, geprueft_von: str,
                        belegrang: str = "", tatsaechliche_kosten: str = "", *,
                        actor: str | None = None, model: str | None = None,
                        session: str | None = None) -> dict:
    """Eine Annahme bestaetigen oder widerlegen -- nur mit Beleg und Pruefer.

    geprueft_am setzt der Server, nicht der Aufrufer: ein selbst gewaehlter
    Pruefzeitpunkt ist keine Angabe, sondern eine Behauptung."""
    conn = get_db()
    zeile = conn.execute("SELECT id, belegrang FROM annahmen WHERE id = ?", (annahme_id,)).fetchone()
    if not zeile:
        conn.close()
        return {"status": "rejected",
                "error": f"annahme_id verweist auf keine bestehende Annahme: {annahme_id}"}
    jetzt = now_iso()
    try:
        conn.execute(
            """UPDATE annahmen SET status = ?, beleg = ?, belegrang = ?, geprueft_von = ?,
                                   geprueft_am = ?, tatsaechliche_kosten = ?, updated_at = ?
               WHERE id = ?""",
            (status, beleg, belegrang or zeile["belegrang"], geprueft_von, jetzt,
             tatsaechliche_kosten, jetzt, annahme_id),
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        log_access(conn, None, "annahme", actor=actor, model=model, session=session,
                   status="rejected", query=str(e))
        conn.close()
        return {"status": "rejected", "error": str(e)}
    log_access(conn, None, "annahme", query=f"{annahme_id} -> {status}",
               actor=actor, model=model, session=session,
               affected_row={"id": annahme_id, "status": status, "beleg": beleg,
                             "geprueft_von": geprueft_von, "geprueft_am": jetzt})
    conn.close()
    return {"id": annahme_id, "status": status, "geprueft_am": jetzt}


def annahme_liste(status: str = "offen", max_results: int = 20, *,
                  actor: str | None = None, model: str | None = None,
                  session: str | None = None) -> dict:
    """Offene Annahmen sichtbar halten. Sortiert nach Belegrang (geraten
    zuerst) und Alter -- die schlechtest belegte aelteste Annahme steht oben,
    weil sie am laengsten unwidersprochen weitergetragen wurde."""
    conn = get_db()
    rang = "CASE belegrang WHEN 'geraten' THEN 0 WHEN 'plausibel' THEN 1 WHEN 'fremdbericht' THEN 2 ELSE 3 END"
    zeilen = conn.execute(
        f"""SELECT id, annahme, kategorie, status, belegrang, beleg, kosten_wenn_falsch,
                   geprueft_von, geprueft_am, created_at
            FROM annahmen WHERE status = ? ORDER BY {rang}, created_at LIMIT ?""",
        (status, max_results),
    ).fetchall()
    offen = conn.execute("SELECT COUNT(*) FROM annahmen WHERE status = 'offen'").fetchone()[0]
    log_access(conn, None, "annahme", query=f"liste:{status}",
               actor=actor, model=model, session=session)
    conn.close()
    return {"results": [dict(z) for z in zeilen], "count": len(zeilen), "offen_gesamt": offen}


def _identity_args(args: dict) -> dict:
    """Eine Stelle, durch die jeder Werkzeugaufruf laeuft -- deshalb wird die
    Schreibweise des Modells hier vereinheitlicht und nicht in 23 Handlern."""
    werte = {key: args.get(key) for key in ("actor", "model", "session")}
    werte["model"] = modell_normalisieren(werte["model"])
    return werte


def _resolve_node_ref(args: dict) -> str:
    """Loest node_id ODER path aus dem Aufrufer-Dict auf (Auftrag 2026-08-07,
    Befund: `knowledge_zurueckziehen(path="/probe", ...)` reichte den rohen
    KeyError('node_id') als {"error": "'node_id'"} durch -- nennt nur den
    Python-Schluesselnamen, keine Handlungsanweisung, siehe handle_request()s
    genereller `except Exception as e: str(e)`). Genau EINE der beiden
    Angaben ist Pflicht. Beide gesetzt und WIDERSPRUECHLICH -> Fehler, kein
    stilles Gewinnen-Lassen einer Seite; beide gesetzt und gleich -> erlaubt
    (kein Grund zum Abweisen, wenn ein Aufrufer sicherheitshalber beides
    mitgibt). ValueError statt KeyError, weil handle_request() jede Exception
    ohnehin nur ueber str(e) an den Aufrufer reicht -- der Text hier muss
    also bereits die vollstaendige, an einen Aufrufer gerichtete Meldung
    sein."""
    node_id = args.get("node_id")
    path = args.get("path")
    if node_id and path and node_id != path:
        raise ValueError(
            f"node_id ({node_id!r}) und path ({path!r}) widersprechen sich: nur eine der beiden Angaben machen."
        )
    if node_id:
        return node_id
    if path:
        return path
    raise ValueError(
        "weder node_id noch path angegeben: eine von beiden ist Pflicht -- die Node-ID oder der volle Pfad des Knotens."
    )


def _require(args: dict, key: str, hinweis: str):
    """Pflichtangabe pruefen, sprechender Fehler statt rohem KeyError (Auftrag
    2026-08-07: `werkzeugabdeckung.py` fand 12 Werkzeuge, deren Handler direkt
    `args["key"]` liest -- bei fehlender Angabe lief nur `{"error": "'key'"}`
    durch handle_request()s generisches `except Exception as e: str(e)`,
    nennt also den Python-Schluesselnamen statt einer Handlungsanweisung.
    Leerstring zaehlt als fehlend, sonst ist ein bewusst leeres Feld nicht
    von einem vergessenen zu unterscheiden. ValueError, weil handle_request()
    jede Exception ohnehin nur ueber str(e) durchreicht -- der Text hier ist
    also schon die vollstaendige, an den Aufrufer gerichtete Meldung."""
    val = args.get(key)
    if val in (None, ""):
        raise ValueError(f"Pflichtangabe '{key}' fehlt: {hinweis}")
    return val


IDENTITY_PROPERTIES = {
    "actor": {"type": "string", "description": "Calling agent identity; else BEGOD_KNOWLEDGE_ACTOR or unknown"},
    "model": {"type": "string", "description": "Calling model; else BEGOD_KNOWLEDGE_MODEL or unknown"},
    "session": {"type": "string", "description": "Stable session ID; else BEGOD_KNOWLEDGE_SESSION or unknown"},
}

def _tool_anmelden(args: dict) -> dict:
    """Eine Einladungs-PIN einloesen und den eigenen Ausweis erhalten.

    DAS EINZIGE WERKZEUG OHNE RECHTEBEDARF -- und das mit Absicht: wer sich
    anmeldet, hat noch keinen Ausweis. Die PIN IST die Berechtigung, und sie
    wurde von einem Menschen ausgestellt, der einbuergern durfte (siehe
    ausweis.einladen). Damit ist die Einloesung zugleich der Nachweis, dass ein
    Mensch sie weitergegeben hat.

    Das Geheimnis wird GENAU EINMAL zurueckgegeben und nirgends protokolliert."""
    pin = (args.get("pin") or "").strip()
    if not pin:
        return {"error": "pin fehlt"}
    try:
        erg = ausweis.einloesen(pin)
    except PermissionError as fehler:
        return {"error": str(fehler)}
    return {
        "status": "angemeldet",
        "name": erg["name"],
        "bedient_von": erg["bedient_von"],
        "rollen": erg["rollen"],
        "geheimnis": erg["geheimnis"],
        "hinweis": ("Dieses Geheimnis erscheint genau einmal. Es gehoert in die "
                    "Konfiguration des Klienten als BRAINLEHR_GEHEIMNIS, nicht "
                    "in den Gespraechsverlauf."),
    }


TOOLS = {
    "knowledge_anmelden": {
        "description": "Redeem a one-time invitation PIN and receive your own credential. "
                       "The PIN is issued by a human who is allowed to naturalise (ausweis.einladen); "
                       "redeeming it is therefore the proof that a human handed it over. The secret is "
                       "returned exactly once and is never logged. This is the only tool callable without "
                       "a credential -- whoever is signing in does not have one yet.",
        "inputSchema": {
            "type": "object",
            "properties": {"pin": {"type": "string", "description": "the one-time PIN you were given"}},
            "required": ["pin"],
        },
        "handler": _tool_anmelden,
    },
    "knowledge_browse": {
        "description": "Browse children of a knowledge tree node. Returns titles+summaries only (token-efficient). Use '/' for root.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Tree path to browse, e.g. '/' or '/shared/arch'", "default": "/"},
                "project_filter": {"type": "string", "description": "Filter by project (free-form slug, e.g. one of the app dirs under Begod2026/ -- not enforced/closed)"},
                **IDENTITY_PROPERTIES,
            }
        },
        "handler": lambda args: knowledge_browse(args.get("path", "/"), args.get("project_filter"), **_identity_args(args))
    },
    "knowledge_read": {
        "description": "Read full content of a knowledge node (by ID or path), plus title+summary of its direct children (one level, not recursive) -- a branch node's own content is usually empty, the substance lives in its children. Use browse/search first to find the right node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "Node ID or full path"},
                **IDENTITY_PROPERTIES,
            },
            "required": ["node_id"]
        },
        "handler": lambda args: knowledge_read(
            _require(args, "node_id", "die Node-ID oder der volle Pfad des zu lesenden Knotens (siehe knowledge_search/knowledge_browse zum Finden)."),
            **_identity_args(args))
    },
    "knowledge_search": {
        "description": "Full-text search across knowledge. Returns summaries (not full content) for token efficiency.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (FTS5 syntax supported: AND, OR, NOT, phrases). Hybrid: fuses keyword matches with local-embedding meaning search when vectors exist."},
                "scope": {"type": "string", "description": "Scope: 'all' or project name", "default": "all"},
                "max_results": {"type": "integer", "description": "Max results (default 10)", "default": 10},
                "stichtag": {"type": "string", "description": "ISO-8601 date/timestamp to check norm validity (gilt_ab/gilt_bis) against; default now. Expired or not-yet-effective norms rank last and are marked, never hidden (unless nur_geltende=True). Facts (norm_rang unset) are unaffected."},
                "nur_geltende": {"type": "boolean", "description": "Drop expired/not-yet-effective norms instead of ranking them last. Default False.", "default": False},
                "cwd": {"type": "string", "description": "Caller's working directory, for zero-hit-log provenance only; else null"},
                **IDENTITY_PROPERTIES,
            },
            "required": ["query"]
        },
        "handler": lambda args: knowledge_search(
            _require(args, "query", "der Suchbegriff (FTS5-Syntax: Stichwort, Phrase, AND/OR/NOT)."),
            args.get("scope", "all"), args.get("max_results", 10), stichtag=args.get("stichtag"), nur_geltende=args.get("nur_geltende", False), cwd=args.get("cwd"), **_identity_args(args))
    },
    "knowledge_add": {
        "description": "Add a new knowledge node to the tree. Specify parent_path to place it in the hierarchy. "
                        "parent_path must already exist (or be '/'); an unknown parent_path is rejected with "
                        "suggested nearby paths unless neuer_ast=True explicitly opens a new branch. "
                        "source is required and rejected if empty -- e.g. \"erzeugt aus /pfad/datei.md (Stand 2026-08-05T23:40:00+02:00)\". "
                        "norm_entscheidung is REQUIRED: 'keine_norm' (plain fact, no rank), 'norm_befristet' "
                        "(norm with an end date) or 'norm_unbefristet' (norm without one). Omitting it, or "
                        "combining it inconsistently with norm_rang/gilt_ab/gilt_bis, is rejected -- there is no "
                        "default, because a silent default would recreate the exact ambiguity this field exists "
                        "to remove (was a fact really decided to be non-normative, or did nobody look?). "
                        "norm_rang/gilt_ab/gilt_bis stay optional inputs, but 'norm_befristet'/'norm_unbefristet' "
                        "require norm_rang and gilt_ab to end up set (either given directly, or deterministically "
                        "derived from source for directive/ADR imports -- ADR-034); 'norm_befristet' additionally "
                        "requires gilt_bis, 'norm_unbefristet' requires gilt_bis stay unset. gilt_ab/gilt_bis must "
                        "be ISO-8601 date or timestamp; gilt_bis before gilt_ab is rejected. "
                        "Example -- raw material \"Sozialtarif-Zuschlag entfaellt zum 01.03.2027 "
                        "vollstaendig, loest die Uebergangsregelung von 2022 ab.\" -> "
                        "{\"parent_path\": \"/wissensnetz-pflegeverbund\", \"title\": "
                        "\"Sozialtarif-Zuschlag entfaellt 01.03.2027\", \"summary\": "
                        "\"Sozialtarif-Zuschlag entfaellt zum 01.03.2027, loest Regelung von 2022 "
                        "ab.\", \"norm_rang\": 2, \"gilt_ab\": \"2027-03-01\", \"norm_entscheidung\": "
                        "\"norm_unbefristet\", \"norm_entschieden_grund\": \"Uebergangsregelung 2022 laeuft "
                        "aus, Nachfolgeregel greift direkt\", \"source\": \"erzeugt aus Rohmaterial (Beispiel)\"}. "
                        "norm_entschieden_grund is REQUIRED whenever norm_entscheidung is given (like grund on "
                        "knowledge_zurueckziehen) -- a free-text reason for the decision. Who decided "
                        "(norm_entschieden_von) is resolved automatically from your caller identity, not a "
                        "separate input. "
                        "anlass records what triggered this entry: 'selbst' (you wrote it unprompted) or "
                        "'betreiber' (an explicit human instruction, e.g. \"merk dir das\") are SELF-REPORTED -- "
                        "only as reliable as the caller. 'hook' (the enforcing Stop-hook made you call this) and "
                        "'skript' (batch/migration/harvest run, no conversation) are objective in principle, but "
                        "note the Stop-hook itself never calls this tool -- it only forces you to run /learn, "
                        "which then calls this normally, so 'hook' is still self-reported by that skill, not "
                        "verified by the server. Default 'unbekannt' if omitted. An unknown value is rejected "
                        "with the allowed list, nothing is written.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "parent_path": {"type": "string", "description": "Parent node path, e.g. '/shared/arch' -- must exist"},
                "title": {"type": "string"},
                "summary": {"type": "string", "description": "1-2 sentences summary (token-efficient)"},
                "content": {"type": "string", "description": "Full content (loaded only on read)"},
                "project_id": {"type": "string", "description": "Free-form project slug (any app dir under Begod2026/, e.g. 'fahrtenbuch', 'openlehr'), not a fixed set. Omit to derive it from a matching segment in parent_path (falls back to 'shared' if none matches); pass explicitly (including '') to override the derivation."},
                "tags": {"type": "array", "items": {"type": "string"}},
                "source": {"type": "string", "description": "Required unless abgeleitet_von is set (then it must be omitted -- the system generates it). Origin: file path, konsil ID, or research ID. Example: 'erzeugt aus /pfad/datei.md (Stand 2026-08-05T23:40:00+02:00)'"},
                "abgeleitet_von": {"type": "string", "description": "Optional: id or path of an EXISTING source node. If set, source is generated by the system from the source node's kind (parent_path/norm_rang/tags, never its title/summary/content) -- giving your own source is rejected."},
                "neuer_ast": {"type": "boolean", "description": "Explicitly allow creating a new top-level branch when parent_path doesn't exist yet", "default": False},
                "norm_rang": {"type": "integer", "description": "Optional: rank of a norm (1=global directive, 2=hub directive, 3=ADR). Omit for plain facts."},
                "gilt_ab": {"type": "string", "description": "Optional: ISO-8601 date/timestamp the norm takes effect"},
                "gilt_bis": {"type": "string", "description": "Optional: ISO-8601 date/timestamp the norm expires; omit for indefinite. Must not be before gilt_ab."},
                "norm_entscheidung": {"type": "string", "enum": sorted(ALLOWED_NORM_ENTSCHEIDUNG),
                                       "description": "REQUIRED (no default): keine_norm=plain fact/no rank, "
                                                       "norm_befristet=norm with an end date, "
                                                       "norm_unbefristet=norm without one. See tool description."},
                "norm_entschieden_grund": {"type": "string",
                                            "description": "REQUIRED alongside norm_entscheidung: free-text reason for the decision (see tool description)."},
                "anlass": {"type": "string", "enum": sorted(ALLOWED_ANLASS), "default": "unbekannt",
                           "description": "What triggered this entry -- selbst/betreiber self-reported, hook/skript objective in principle (see tool description). Default 'unbekannt'."},
                "gattung": {"type": "string", "enum": list(ALLOWED_GATTUNG),
                            "default": "arbeitsbestand",
                            "description": "Kind of entry: 'arbeitsbestand' (working set, the default) or 'nachschlagewerk' (reference corpus -- may sit in the store as a distractor but is never the TARGET of a test case, see node 096669de). Set this for imported third-party material, otherwise it dilutes retrieval."},
                **IDENTITY_PROPERTIES,
            },
            "required": ["parent_path", "title", "summary", "norm_entscheidung", "norm_entschieden_grund"]
        },
        "handler": lambda args: knowledge_add(
            _require(args, "parent_path", "der Pfad des Elternknotens, z.B. '/shared/arch' (muss existieren oder '/' sein)."),
            _require(args, "title", "der Titel des neuen Knotens."),
            _require(args, "summary", "die 1-2-Satz-Zusammenfassung des neuen Knotens."),
            args.get("content", ""), args.get("project_id", "shared"),
            args.get("tags"), args.get("source", ""), neuer_ast=args.get("neuer_ast", False),
            norm_rang=args.get("norm_rang"), gilt_ab=args.get("gilt_ab"), gilt_bis=args.get("gilt_bis"),
            norm_entscheidung=_require(args, "norm_entscheidung", "keine_norm/norm_befristet/norm_unbefristet -- ist dieser Knoten eine Norm?"),
            norm_entschieden_grund=_require(args, "norm_entschieden_grund", "Begruendung fuer die Norm-Entscheidung -- wer entscheidet und warum?"),
            anlass=args.get("anlass", "unbekannt"), abgeleitet_von=args.get("abgeleitet_von"),
            gattung=args.get("gattung"),
            **_identity_args(args)
        )
    },
    "knowledge_update": {
        "description": "Update an existing knowledge node (title, summary, content, tags, and/or the Normschicht fields "
                        "norm_rang/gilt_ab/gilt_bis/norm_entscheidung -- see knowledge_add for their meaning). "
                        "Only given fields change; norm_entscheidung is optional here (unlike knowledge_add) and "
                        "only needed when the change would otherwise contradict the node's existing decision "
                        "(e.g. giving a norm_unbefristet norm a gilt_bis) -- if given, norm_entschieden_grund "
                        "is then REQUIRED too.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "Node ID or path"},
                "summary": {"type": "string"},
                "content": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "title": {"type": "string", "description": "Optional: rename the node. path stays unchanged (path is derived from the title only at knowledge_add, never retroactively)."},
                "norm_rang": {"type": "integer", "description": "Optional: set/change the norm rank"},
                "gilt_ab": {"type": "string", "description": "Optional: ISO-8601 date/timestamp"},
                "gilt_bis": {"type": "string", "description": "Optional: ISO-8601 date/timestamp; must not be before gilt_ab (existing or given)"},
                "norm_entscheidung": {"type": "string", "enum": sorted(ALLOWED_NORM_ENTSCHEIDUNG),
                                       "description": "Optional: change the norm/fact decision (see knowledge_add). Requires norm_entschieden_grund if given."},
                "norm_entschieden_grund": {"type": "string",
                                            "description": "Required if norm_entscheidung is given: free-text reason."},
                "gattung": {"type": "string", "enum": list(ALLOWED_GATTUNG),
                            "description": "Reclassify. Only changed when given -- omitting it leaves the current kind untouched."},
                **IDENTITY_PROPERTIES,
            },
            "required": ["node_id"]
        },
        "handler": lambda args: knowledge_update(
            _require(args, "node_id", "die Node-ID oder der Pfad des zu aendernden Knotens."),
            args.get("summary"), args.get("content"), args.get("tags"), args.get("title"),
            norm_rang=args.get("norm_rang"), gilt_ab=args.get("gilt_ab"), gilt_bis=args.get("gilt_bis"),
            norm_entscheidung=args.get("norm_entscheidung"),
            norm_entschieden_grund=args.get("norm_entschieden_grund"),
            gattung=args.get("gattung"),
            **_identity_args(args)
        )
    },
    "freigabe_setzen": {
        "description": "Decide, for ONE entry, who may see it: 'offen' (may leave the house), "
                       "'intern' (default -- stays here) or 'gesperrt'. Works for a lesson or a "
                       "node; the id decides which, and an id found in both tables is rejected as "
                       "ambiguous rather than guessed. Takes exactly ONE id -- a comma-separated "
                       "list or a wildcard is refused, not split up: every entry is decided "
                       "individually or stays 'intern' (migrate_freigabe.py). Unlike a norm "
                       "decision this is NOT binding -- the way back from 'offen' to 'intern' is "
                       "explicitly allowed. Logged in access_log like any other decision.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "eintrag_id": {"type": "string",
                               "description": "Exactly one lesson id or node id -- no list, no pattern"},
                "stufe": {"type": "string", "enum": ["offen", "intern", "gesperrt"],
                          "description": "offen = may be exported, intern = stays here, gesperrt = blocked"},
                **IDENTITY_PROPERTIES,
            },
            "required": ["eintrag_id", "stufe"]
        },
        "handler": lambda args: freigabe_setzen(args.get("eintrag_id", ""), args.get("stufe", ""), **_identity_args(args))
    },
    "knowledge_zurueckziehen": {
        "description": "Withdraw a node: clears content and summary (no backup -- the text is gone), "
                        "keeps title and path, keeps the row (with grund/timestamp/actor) so nothing "
                        "vanishes without a trace. The node then drops out of knowledge_search and the "
                        "recall hook. Reversible via knowledge_freigeben (which restores visibility only, "
                        "not the emptied text) -- unlike the permanent, human-only endgueltig_entfernen.py, "
                        "which this tool cannot reach. grund is required; empty grund is rejected, nothing "
                        "changed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "Node ID -- exactly one of node_id/path required"},
                "path": {"type": "string", "description": "Full node path -- exactly one of node_id/path required"},
                "grund": {"type": "string", "description": "Required reason for withdrawal"},
                **IDENTITY_PROPERTIES,
            },
            "required": ["grund"]
        },
        "handler": lambda args: knowledge_zurueckziehen(_resolve_node_ref(args), args.get("grund", ""), **_identity_args(args))
    },
    "knowledge_freigeben": {
        "description": "Undo a knowledge_zurueckziehen: the node reappears in knowledge_search/recall. "
                        "Restores nothing -- content/summary stay empty as they were left by the withdrawal, "
                        "this only flips visibility back.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "Node ID -- exactly one of node_id/path required"},
                "path": {"type": "string", "description": "Full node path -- exactly one of node_id/path required"},
                **IDENTITY_PROPERTIES,
            },
        },
        "handler": lambda args: knowledge_freigeben(_resolve_node_ref(args), **_identity_args(args))
    },
    "kettenerklaerung_erklaeren": {
        "description": "Explain a broken audit-chain link (access_log.ketten_hash) caused by a sanctioned "
                        "rewrite of an already-logged row -- e.g. a migration that corrected a field after "
                        "the fact. Rejects with an error if access_log_id has no break (gespeichert==erwartet) "
                        "or does not exist -- an explanation for a healthy row would itself be a fabrication. "
                        "Never changes the stored ketten_hash; the break stays visible, this only records "
                        "who/when/why next to it. Optional anker=\"rfc3161\"/\"gegenzeichnung\" builds an "
                        "external anchor for the explanation via ankerverfahren.py (dry by default, no network "
                        "without an explicit anker_kwargs override) -- when set, the current anchor backlog "
                        "(ankerverfahren.rueckstand) is reported back as anker_rueckstand, since that backlog "
                        "only ever changes at this moment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "access_log_id": {"type": "integer", "description": "access_log.id of the broken row"},
                "grund": {"type": "string", "description": "Required reason for the rewrite"},
                "commit_hash": {"type": "string", "description": "Optional: commit that performed the rewrite"},
                "anker": {"type": "string", "enum": ["rfc3161", "gegenzeichnung"],
                          "description": "Optional: build an external anchor for this explanation"},
                **IDENTITY_PROPERTIES,
            },
            "required": ["access_log_id", "grund"]
        },
        "handler": lambda args: kettenerklaerung_erklaeren(
            _require(args, "access_log_id", "die access_log.id der zu erklaerenden Zeile."),
            _require(args, "grund", "der Grund fuer die Umschreibung."),
            commit_hash=args.get("commit_hash"), anker=args.get("anker"),
            **_identity_args(args)
        )
    },
    "knowledge_relation_add": {
        "description": "Create one explicit evidenced knowledge edge between existing node IDs/paths. Never infers links from tags or text; validates endpoints, scope, type, confidence, and duplicate edges.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_node": {"type": "string", "description": "Existing source node ID or path"},
                "target_node": {"type": "string", "description": "Existing target node ID or path"},
                "relation_type": {"type": "string", "enum": sorted(RELATION_TYPES)},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.8},
                "weight": {"type": "number", "minimum": 0, "default": 1.0},
                "evidence": {"type": "string", "description": "Why this edge is true; cite the decision/source"},
                "source": {"type": "string", "description": "Source artifact path/ID"},
                "scope": {"type": "string", "description": "all or project; scoped calls permit shared + project", "default": "all"},
                **IDENTITY_PROPERTIES,
            },
            "required": ["source_node", "target_node", "relation_type", "evidence"]
        },
        "handler": lambda args: knowledge_relation_add(
            _require(args, "source_node", "die ID oder der Pfad des Quellknotens."),
            _require(args, "target_node", "die ID oder der Pfad des Zielknotens."),
            _require(args, "relation_type", f"der Beziehungstyp, einer aus: {sorted(RELATION_TYPES)}."),
            args.get("confidence", 0.8), args.get("weight", 1.0), args.get("evidence", ""),
            args.get("source", ""), args.get("scope", "all"),
            args.get("actor"), args.get("model"), args.get("session")
        )
    },
    "knowledge_relation_list": {
        "description": "List only explicit knowledge edges, optionally incident to one node and filtered by relation type/scope. This is the canonical link-read path.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Optional existing node ID or path"},
                "relation_type": {"type": "string", "enum": sorted(RELATION_TYPES)},
                "scope": {"type": "string", "default": "all"},
                **IDENTITY_PROPERTIES,
            }
        },
        "handler": lambda args: knowledge_relation_list(
            args.get("node"), args.get("relation_type"), args.get("scope", "all"), **_identity_args(args)
        )
    },
    "knowledge_relation_update": {
        "description": "Update evidence/provenance/weight/type of one explicit edge by relation ID; endpoints stay stable.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "relation_id": {"type": "string"},
                "relation_type": {"type": "string", "enum": sorted(RELATION_TYPES)},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "weight": {"type": "number", "minimum": 0},
                "evidence": {"type": "string"},
                "source": {"type": "string"},
                **IDENTITY_PROPERTIES,
            },
            "required": ["relation_id"]
        },
        "handler": lambda args: knowledge_relation_update(
            _require(args, "relation_id", "die ID der zu aendernden Beziehung."),
            args.get("relation_type"), args.get("confidence"),
            args.get("weight"), args.get("evidence"), args.get("source"),
            args.get("actor"), args.get("model"), args.get("session")
        )
    },
    "knowledge_relation_remove": {
        "description": "Remove exactly one explicit edge by relation ID. Nodes are never deleted.",
        "inputSchema": {
            "type": "object",
            "properties": {"relation_id": {"type": "string"}, **IDENTITY_PROPERTIES},
            "required": ["relation_id"]
        },
        "handler": lambda args: knowledge_relation_remove(
            _require(args, "relation_id", "die ID der zu entfernenden Beziehung."),
            **_identity_args(args))
    },
    "annahme_erfassen": {
        "description": (
            "Eine ANNAHME festhalten, solange sie noch als Annahme erkennbar ist -- nicht "
            "erst, wenn sie sich als falsch herausgestellt hat. Zwei Pflichtangaben, und "
            "sie sind der ganze Zweck: 'belegrang' (gemessen|fremdbericht|plausibel|geraten) "
            "sagt, WIE GUT der Beleg ist, 'kosten_wenn_falsch' sagt, WAS EIN IRRTUM KOSTET. "
            "belegrang='gemessen' ohne nicht leeren 'beleg' wird abgelehnt -- eine Messung "
            "ohne Protokoll ist keine. Der Eintrag beginnt immer auf status='offen'; "
            "bestaetigt/widerlegt geht nur ueber annahme_entscheiden."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "annahme": {"type": "string", "description": "Was angenommen wird, in einem Satz"},
                "kosten_wenn_falsch": {"type": "string", "description": "Was ein Irrtum kostet -- Pflicht, ohne diesen Satz kein Eintrag"},
                "belegrang": {"type": "string", "enum": ["gemessen", "fremdbericht", "plausibel", "geraten"], "default": "geraten"},
                "beleg": {"type": "string", "description": "Worauf sich das stuetzt, wortwoertlich (Lauf, Datei, Zitat)"},
                "kategorie": {"type": "string"},
                "projects": {"type": "array", "items": {"type": "string"}},
                "node_path": {"type": "string", "description": "Bezug auf einen Wissensknoten"},
                "notizen": {"type": "string"},
                "anlass": {"type": "string", "enum": sorted(ALLOWED_ANLASS), "default": "unbekannt"},
                **IDENTITY_PROPERTIES,
            },
            "required": ["annahme", "kosten_wenn_falsch"]
        },
        "handler": lambda args: annahme_erfassen(
            _require(args, "annahme", "was angenommen wird, in einem Satz."),
            _require(args, "kosten_wenn_falsch", "was ein Irrtum kostet -- ohne diesen Satz kein Eintrag."),
            args.get("belegrang", "geraten"), args.get("beleg", ""), args.get("kategorie", ""),
            args.get("projects"), args.get("node_path", ""), args.get("notizen", ""),
            args.get("anlass", "unbekannt"), **_identity_args(args)
        )
    },
    "annahme_entscheiden": {
        "description": (
            "Eine Annahme bestaetigen oder widerlegen. Beleg und Pruefer sind Pflicht -- "
            "ohne beides ist 'bestaetigt' nur eine Meinung mit Zeitstempel, und die Datenbank "
            "lehnt es ab. Den Pruefzeitpunkt setzt der Server, nicht der Aufrufer. Bei "
            "status='widerlegt' gehoert nach Moeglichkeit 'tatsaechliche_kosten' dazu: erst "
            "der Vergleich mit kosten_wenn_falsch zeigt, ob die Einschaetzung damals taugte."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "annahme_id": {"type": "string", "description": "z.B. 'A-3f9a2b'"},
                "status": {"type": "string", "enum": ["bestaetigt", "widerlegt"]},
                "beleg": {"type": "string", "description": "Was die Entscheidung traegt, wortwoertlich"},
                "geprueft_von": {"type": "string"},
                "belegrang": {"type": "string", "enum": ["gemessen", "fremdbericht", "plausibel", "geraten"],
                              "description": "Neuer Belegrang, falls die Pruefung ihn aendert; sonst bleibt der alte"},
                "tatsaechliche_kosten": {"type": "string"},
                **IDENTITY_PROPERTIES,
            },
            "required": ["annahme_id", "status", "beleg", "geprueft_von"]
        },
        "handler": lambda args: annahme_entscheiden(
            _require(args, "annahme_id", "die Kennung der Annahme, z.B. 'A-3f9a2b'."),
            _require(args, "status", "bestaetigt oder widerlegt."),
            _require(args, "beleg", "was die Entscheidung traegt -- ohne Beleg keine Entscheidung."),
            _require(args, "geprueft_von", "wer geprueft hat."),
            args.get("belegrang", ""), args.get("tatsaechliche_kosten", ""),
            **_identity_args(args)
        )
    },
    "annahme_liste": {
        "description": (
            "Offene Annahmen auflisten, schlechtest belegt und aeltest zuerst -- das ist die "
            "Reihenfolge, in der sie schaden: was am laengsten unwidersprochen weitergetragen "
            "wurde, ist am tiefsten in spaeteren Entscheidungen verbaut."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["offen", "bestaetigt", "widerlegt"], "default": "offen"},
                "max_results": {"type": "integer", "default": 20},
                **IDENTITY_PROPERTIES,
            }
        },
        "handler": lambda args: annahme_liste(
            args.get("status", "offen"), args.get("max_results", 20), **_identity_args(args)
        )
    },
    "lesson_record": {
        "description": (
            "Record a lesson learned. Pass same_as=<lesson id> when this is a repeat of an "
            "already-recorded lesson: increments that lesson's occurrences, appends this "
            "description to it as a dated, capped repetition note, and creates no new row "
            "(unknown same_as id is an error, never a silent new entry). Escalates to rule "
            "at 3+ occurrences. Without same_as: increments occurrences only on an exact "
            "duplicate (same type + byte-identical description); otherwise creates a new "
            "lesson and, if an active lesson of the same type looks similar, returns it as "
            "similar_lesson_hint (a hint only — never auto-merged; re-record with same_as to merge). "
            "anlass records what triggered this entry: 'selbst' (you wrote it unprompted) or "
            "'betreiber' (an explicit human instruction, e.g. \"merk dir das\") are SELF-REPORTED -- "
            "only as reliable as the caller. 'hook' and 'skript' are objective in principle, but "
            "note the enforcing Stop-hook never calls this tool itself -- it only forces you to run "
            "/learn, which then calls this normally, so 'hook' is still self-reported by that skill, "
            "not verified by the server. Default 'unbekannt' if omitted; an unknown value is rejected "
            "with the allowed list, nothing is written (applies even on a duplicate/same_as bump, where "
            "the existing row's anlass is left untouched anyway)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["error", "insight", "pattern", "antipattern"]},
                "description": {"type": "string"},
                "root_cause": {"type": "string"},
                "resolution": {"type": "string"},
                "prevention": {"type": "string"},
                "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"], "default": "medium"},
                "projects": {"type": "array", "items": {"type": "string"}, "description": "Affected projects"},
                "node_path": {"type": "string", "description": "Related knowledge node path"},
                "same_as": {"type": "string", "description": "ID of an existing lesson this is a repeat of, e.g. 'L-6e48a9'"},
                "anlass": {"type": "string", "enum": sorted(ALLOWED_ANLASS), "default": "unbekannt",
                           "description": "What triggered this entry -- selbst/betreiber self-reported, hook/skript objective in principle (see tool description). Default 'unbekannt'."},
                **IDENTITY_PROPERTIES,
            },
            "required": ["type", "description"]
        },
        "handler": lambda args: lesson_record(
            _require(args, "type", f"der Lesson-Typ, einer aus: {sorted(ALLOWED_LESSON_TYPES)}."),
            _require(args, "description", "der Lehrtext selbst."),
            args.get("root_cause", ""),
            args.get("resolution", ""), args.get("prevention", ""),
            args.get("severity", "medium"), args.get("projects"), args.get("node_path", ""),
            args.get("same_as", ""), args.get("anlass", "unbekannt"), **_identity_args(args)
        )
    },
    "lesson_update": {
        "description": "Correct or delete a recorded lesson. Only given fields are changed; unmangles field-tag corruption in the same way lesson_record does. Use delete:true to remove a bad entry.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lesson_id": {"type": "string", "description": "Lesson ID, e.g. 'L-6e48a9'"},
                "description": {"type": "string"},
                "root_cause": {"type": "string"},
                "resolution": {"type": "string"},
                "prevention": {"type": "string"},
                "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                "projects": {"type": "array", "items": {"type": "string"}},
                "status": {"type": "string", "enum": ["active", "resolved", "escalated_to_rule"]},
                "delete": {"type": "boolean", "description": "Delete the lesson instead of updating it", "default": False},
                **IDENTITY_PROPERTIES,
            },
            "required": ["lesson_id"]
        },
        "handler": lambda args: lesson_update(
            _require(args, "lesson_id", "die Lehr-ID, z.B. 'L-6e48a9'."),
            args.get("description"), args.get("root_cause"),
            args.get("resolution"), args.get("prevention"), args.get("severity"),
            args.get("projects"), args.get("status"), args.get("delete", False), **_identity_args(args)
        )
    },
    "lesson_query": {
        "description": "Query lessons learned. Filter by type, project, or status. Optional 'query' searches description/root_cause/prevention by keyword and meaning (hybrid).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["error", "insight", "pattern", "antipattern"]},
                "project": {"type": "string"},
                "status": {"type": "string", "enum": ["active", "resolved", "escalated_to_rule"], "default": "active"},
                "max_results": {"type": "integer", "default": 10},
                "query": {"type": "string", "description": "Optional: Stichwort-/Bedeutungssuche in description/root_cause/prevention"}
            }
        },
        "handler": lambda args: lesson_query(
            args.get("type"), args.get("project"), args.get("status", "active"),
            args.get("max_results", 10), args.get("query")
        )
    },
    "knowledge_sitzung": {
        "description": "Read-only: list every knowledge node and lesson written by one session (actor/session "
                        "columns, Auftrag 2026-08-06) -- the evaluation path for isolating one writer's entries, "
                        "e.g. before a human decides whether to knowledge_zurueckziehen them. Never withdraws or "
                        "deletes anything itself.",
        "inputSchema": {
            "type": "object",
            "properties": {"session": {"type": "string", "description": "Session ID, e.g. BEGOD_KNOWLEDGE_SESSION or 'unbekannt'"}},
            "required": ["session"]
        },
        "handler": lambda args: knowledge_sitzung(
            _require(args, "session", "die Sitzungs-ID, z.B. BEGOD_KNOWLEDGE_SESSION oder 'unbekannt'."))
    },
    "knowledge_modell": {
        "description": "Read-only: list every knowledge node and lesson written by one model (actor/session/model "
                        "columns, Auftrag 2026-08-06 Nachtrag) -- isolates one model's entries to judge its quality "
                        "by outcome (how often later pulled/corrected/withdrawn). Never withdraws or deletes "
                        "anything itself.",
        "inputSchema": {
            "type": "object",
            "properties": {"model": {"type": "string", "description": "Model name, e.g. BEGOD_KNOWLEDGE_MODEL or 'unbekannt'"}},
            "required": ["model"]
        },
        "handler": lambda args: knowledge_modell(
            _require(args, "model", "der Modellname, z.B. BEGOD_KNOWLEDGE_MODEL oder 'unbekannt'."))
    },
    "knowledge_stats": {
        "description": "Overview statistics of the knowledge database (node counts, lesson counts, access patterns, "
                        "anlass distribution). anlass_by fields split nodes_by_anlass/lessons_by_anlass into "
                        "selbst/betreiber (self-reported, only as reliable as the caller) vs. hook/skript "
                        "(objective) vs. unbekannt (default / entries older than the field) -- do not treat "
                        "the four as equally trustworthy when reading this.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda args: knowledge_stats()
    },
    "knowledge_trust_score": {
        "description": "Computed (never stored) earned-trust value in [0.05, 0.95], 0.5 = no signal yet -- "
                        "distinct from norm_rang (explained by a human/consilium, decides which rule wins) and "
                        "from confidence (a decay clock since last confirmation). Weighs deliberate reads "
                        "(strongest, nodes only), recall-log session-deduplicated injections (weak, both kinds), "
                        "independent re-occurrence (weak, lessons only), and rejected write attempts (weak "
                        "negative, nodes only -- the equivalent path for lessons never fires, see docstring) "
                        "through a saturating tanh -- diminishing returns prevent repetition alone from inflating "
                        "the score. Returns the raw input counts and an 'exists' flag alongside the score so the "
                        "number is never opaque and a typo isn't indistinguishable from the neutral default.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["node", "lesson"]},
                "ref": {"type": "string", "description": "Node id or path, or lesson id"},
            },
            "required": ["kind", "ref"]
        },
        "handler": lambda args: knowledge_trust_score(
            _require(args, "kind", "'node' oder 'lesson'."),
            _require(args, "ref", "die Node-ID/der Pfad (kind='node') bzw. die Lehr-ID (kind='lesson')."))
    },
    "kurator_lauf": {
        "description": "Background cleanup agent (Hermes curator.py comparison) that ACTS, not just reports "
                        "like knowledge_lint.py -- but only within the safe boundary: knowledge_zurueckziehen() "
                        "(reversible visibility toggle), never endgueltig_entfernen.py (human-only, no MCP tool). "
                        "Evaluates all knowledge_lint categories; 15 are report-only with a stated reason each "
                        "(see _KURATOR_KATEGORIEN_OHNE_HANDLUNG), only injection_suspects at sicherheit='hart' "
                        "acts, and only for kind='node' (lessons have no withdraw mechanism, only a real DELETE, "
                        "so they are reported, never touched). Default is a dry run (scharf=False): nothing is "
                        "written, every potential action is returned with ausgefuehrt=false. scharf=True is the "
                        "explicit switch to actually withdraw matches, each with a stated grund in the audit row.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scharf": {"type": "boolean", "description": "false (default) = dry run, true = actually withdraw matches"},
                **IDENTITY_PROPERTIES,
            }
        },
        "handler": lambda args: kurator_lauf(scharf=bool(args.get("scharf")), **_identity_args(args))
    }
}


def handle_request(req: dict) -> dict:
    method = req.get("method", "")
    req_id = req.get("id")

    if method == "initialize":
        # listChanged bleibt False (Auftrag 2026-08-08 Punkt 2, geprueft statt
        # blind auf True gesetzt): TOOLS ist ein Modul-Konstante-dict, einmal
        # beim Import gefuellt und danach nie mehr veraendert -- kein Codepfad
        # in diesem Prozess mutiert TOOLS oder sendet je eine
        # notifications/tools/list_changed-Benachrichtigung. True zu setzen
        # waere eine Faehigkeit, die nie eingeloest wird (schlimmer als sie
        # nicht anzukuendigen, siehe Auftrag). Das eigentliche Symptom
        # (Client haelt an einem veralteten Schema fest, waehrend ein
        # laengst laufender Prozess neuen Code im Speicher haette) tritt hier
        # gar nicht auf: Python laedt Code beim Start, ein bereits laufender
        # Prozess sieht spaetere Aenderungen an dieser Datei nie, sein TOOLS
        # ist exakt das Schema, mit dem er antwortet -- Versionsbruch entsteht
        # nur zwischen ALT laufendem Prozess und NEU editierter Datei, nicht
        # durch eine Aenderung waehrend der Laufzeit. Hot-Reload waere die
        # tatsaechliche Abhilfe, aber ein eigenes, hier nicht beauftragtes
        # Feature.
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "knowledge-mcp", "version": _version()},
                "instructions": (
                    "Erkläre dem Nutzer zu Beginn jeder neuen Unterhaltung kurz die vier "
                    "Brainlehr-Referenztypen: xxxxxxxx = Wissensknoten-ID für Fakt, Regel "
                    "oder Entscheidung; L-xxxxxx = Lehre/Lesson aus Erfahrung; A-xxxxxx = "
                    "offene oder entschiedene Annahme; Relation = gerichtete, typisierte "
                    "Verbindung zwischen zwei Einträgen ohne eigene Präfixform."
                ),
            }
        }

    if method == "notifications/initialized":
        return None  # No response for notifications

    if method == "tools/list":
        # BEGOD_KNOWLEDGE_PROFIL beschraenkt nur die ANKUENDIGUNG (tools/list),
        # nicht den Aufruf: tools/call bedient jedes Werkzeug in TOOLS weiter,
        # egal ob es hier gelistet wurde. Kein Autorisierungsmechanismus.
        profil = os.environ.get("BEGOD_KNOWLEDGE_PROFIL")
        names = TOOLS.keys()
        if profil == "klein":
            names = ["knowledge_search", "knowledge_read", "knowledge_add"]
        elif profil:
            print(f"BEGOD_KNOWLEDGE_PROFIL unbekannt: {profil!r} — zeige alle Werkzeuge", file=sys.stderr)

        tool_list = []
        for name in names:
            spec = TOOLS[name]
            tool_list.append({
                "name": name,
                "description": spec["description"],
                "inputSchema": spec["inputSchema"]
            })
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tool_list}}

    if method == "tools/call":
        tool_name = req.get("params", {}).get("name", "")
        arguments = req.get("params", {}).get("arguments", {})

        if tool_name not in TOOLS:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps({"error": f"Unknown tool: {tool_name}"})}], "isError": True}
            }

        # B4.3: die Pruefung, die es bisher NICHT gab. Der Kommentar an
        # BEGOD_KNOWLEDGE_PROFIL sagt es selbst -- die Profilbeschraenkung
        # betrifft nur tools/list, "kein Autorisierungsmechanismus". Hier ist
        # der eine Punkt, durch den JEDER Werkzeugaufruf laeuft; eine Pruefung
        # je Werkzeug waere die Fehlklasse aus L-44a838 (drei Umgehungen
        # desselben Choke-Points in einer Woche).
        darf, grund = werkzeugrechte.erlaubt(tool_name)
        if not darf:
            # Ablehnung im Protokoll, damit sichtbarkeit.py sie zeigt: eine
            # stille Abweisung ist von einem Absturz nicht zu unterscheiden.
            try:
                conn = get_db()
                try:
                    log_access(conn, None, tool_name, query=grund,
                               status="rejected")
                    conn.commit()
                finally:
                    conn.close()
            except Exception:  # noqa: BLE001 -- Protokoll darf nie blockieren
                pass
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(
                    {"error": "nicht erlaubt", "grund": grund},
                    ensure_ascii=False)}], "isError": True}
            }

        try:
            with _write_lock():
                result = TOOLS[tool_name]["handler"](arguments)
            # B4.4: der Bezug (:own/:published) haengt am Datensatz, nicht am
            # Werkzeug -- er wirkt darum HIER auf das Ergebnis, an derselben
            # einen Stelle wie die Erlaubnispruefung davor.
            result = werkzeugrechte.filtere(tool_name, result)
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps({"error": str(e)})}], "isError": True}
            }

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def main():
    """stdio MCP server — reads JSON-RPC from stdin, writes to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        response = handle_request(req)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
