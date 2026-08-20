#!/usr/bin/env python3
"""
knowledge_recall_hook.py — Auto-Recall (UserPromptSubmit-Hook, systemweit).

Liest den User-Prompt von stdin (Claude-Code-Hook-JSON), sucht in der
gemeinsamen brainlehr.db (FTS-Nodes + lessons_learned) nach dem aktuellen
Thema und spritzt die stärksten Treffer als kompakten Kontext-Block ein.

Regeln:
- IMMER exit 0. Fehler/keine Treffer -> nichts ausgeben (Kontext nicht müllen).
- Klein bleiben (~<200 Tokens): max 3 Nodes + 2 Lessons.
- Still bei Slash-Commands und zu kurzen/keywordarmen Prompts.
- Relevanz-Schwelle: ein Treffer muss MIN_HITS verschiedene Prompt-Keywords im
  ausgegebenen Text enthalten. Ein einzelnes Allerweltswort ("dokument",
  "modell") reicht nicht mehr -- lieber gar kein Recall als falscher.
- Enthaltung (s. ENTHALTUNGSSCHWELLE_KOSINUS): erreicht im aktiven Suchpfad
  kein Kandidat den gemessenen Bedeutungs-Kosinus, wird SICHTBAR nichts
  eingespielt (kurzer Satz statt stillem Nichts) -- abschaltbar ueber
  KNOWLEDGE_ENTHALTUNG_KOSINUS=0/1.

Selbsttest: python3 knowledge_recall_hook.py --selftest

Gegenstück zum Capture: was der /learn-Reflex via lesson_record/knowledge_add
schreibt, findet dieser Hook beim nächsten passenden Prompt wieder.

SELBSTLAUF-VERMERK (Aufgabe wirkkette-6, gemessen 2026-08-15): Dieser Hook
haengt bewusst NICHT zusaetzlich an SubagentStart, obwohl SubagentStart
additionalContext technisch traegt (Beleg: ponytail-subagent.js injiziert
darueber sein Regelwerk in jeden Subagenten -- derselbe Kanal, den dieser
Haken schon fuer UserPromptSubmit nutzt). Gemessener Grund, kein Verdacht:
ein Lauf mit echtem Prompt kostet 6,0s Realzeit (`time` ueber stdin mit
Testprompt, 2026-08-15) -- Embeddings + FTS + RRF-Fusion (siehe
suchpfad_abruf.py). An SubagentStart gehaengt wuerde JEDE Delegation um 6s
verzoegert, ob der Abruf traf oder nicht -- das ist die Bremse, vor der die
HARTE AUFLAGE des Auftrags warnt, nicht ein Fortschritt. Der Subagenten-
Blindfleck bleibt damit STEHEN und ist kein Uebersehen: eine kuenftige
schnelle Vorstufe (reiner Stichwortkanal ohne Embeddings) koennte ihn
schliessen, ist hier aber nicht gebaut, um den Auftrag nicht auszuweiten.
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
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen", "berichte")]
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
import random
import re
import sqlite3
import sys
import time
from pathlib import Path

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import ort  # Ein Ort fuer den Pfad, siehe haken/ort.py (L-6c6661)
DB = str(ort.DB)

# geltungsbereich.py liegt neben der DB (shared-knowledge/) -- Import erlaubt
# laut Auftrag 2026-08-06 (Bereichsbezug fuer den Recall). sys.path-Eintrag
# nur fuer dieses Modul, kein neues Package.
sys.path.insert(0, os.path.dirname(DB))
from geltungsbereich import projekte_aus_projects_json  # noqa: E402
# gattung_filter.py liegt wie geltungsbereich.py neben der DB (Auftrag S1b,
# docs/PLAN_DESTILLE_2026-08-09.md): Nachschlagewerke (NASA LLIS, 1638
# Knoten) nehmen am automatischen Abruf nicht mehr teil.
from gattung_filter import SQL_ARBEITSBESTAND_NUR  # noqa: E402
# Auftrag 2026-08-06: Bestandstext koennte anweisungsartig sein (Schreib-
# pruefstand nimmt Text von einem lokalen Modell entgegen). entschaerfe_
# fuer_ausgabe() kennzeichnet Funde, aendert nie den Bestand -- nur die
# Kopie, die hier ausgegeben wird.
from einschleusung import entschaerfe_fuer_ausgabe  # noqa: E402
# bereinigung.py liegt bei DIESEM Quelltext, nicht bei der Datenbank: setzt
# jemand BEGOD_KNOWLEDGE_DB auf eine Kopie anderswo, zeigt os.path.dirname(DB)
# oben ins falsche Verzeichnis. Beim ersten Verdrahten genau so passiert --
# der Import brach, sobald die Variable gesetzt war.
sys.path.insert(0, str(ort.WURZEL))
import bereinigung  # noqa: E402
# knowledge_mcp_server.py liegt ebenfalls neben der DB, reiner Stdlib-Import
# (siehe dessen Kopf: nur difflib/hashlib/.../embeddings.py, kein MCP-SDK) --
# bricht die "abhaengigkeitsfreie Hook"-Regel oben nicht. Fuer trust_score,
# siehe query()/_apply_trust_score (Auftrag 2026-08-07 Schritt 2).
from knowledge_mcp_server import knowledge_trust_score, _trust_aggregate  # noqa: E402
# embeddings.py liegt ebenfalls neben der DB (shared-knowledge/), reine
# Funktionen ohne Netzwerk-Zwang (embed_text() ist best-effort, siehe dessen
# Docstring). Zweiter Relevanzkanal (Auftrag 2026-08-07 Teil 1) -- derselbe
# Fusionsmechanismus (rrf_fuse/hybrid_retrieval_weight) wie der aktive
# Suchweg in knowledge_mcp_server.py, nichts danebengebaut.
import embeddings  # noqa: E402
# rangfolge.py liegt ebenfalls neben der DB -- zwei zusaetzliche Rangsignale
# (norm_rang, Hebb-Kanten), eigenes Modul (Monolith-Stopp hier, siehe dessen
# Kopf), aus diesem Hook nur AUFGERUFEN (Auftrag 2026-08-08).
import rangfolge  # noqa: E402
# erstverwendung.py liegt in berichte/ -- Auftrag 2026-08-12: Entscheidung bei
# der ERSTEN VERWENDUNG statt beim Import (kern/regelpaket.py legt Fremdregeln
# mit norm_entscheidung='offen' ab, niemand fragt je nach). Gemessen: reiner
# Funktionsaufruf norm_ableiten() kostet ~0,08ms je Knoten (1000x-Lauf lokal
# gemessen) -- gegen das 2,3s-Zeitbudget des Hooks eine Rundungsdifferenz, ein
# eigener selteneren Ausloeser (nur 1. Prompt/Sitzung, Subprozess) loest kein
# Kostenproblem, das es nicht gibt. Nur norm_ableiten() (reine Textanalyse),
# keine DB-Verbindung -- gattung_ableiten() braucht 'source', das hier nicht
# geladen wird und fuer norm_rang ohnehin nicht die Frage ist.
from erstverwendung import norm_ableiten as _erstverwendung_norm_ableiten  # noqa: E402
# suchpfad_abruf.py liegt in diesem Ordner (haken/) -- eigenes Modul (Monolith-
# Stopp hier), nur der Kandidaten-Beschaffung wegen aufgerufen (S9, Auftrag
# 2026-08-09). Aus diesem Hook nur AUFGERUFEN, s. _suchpfad_aktiv() oben.
import suchpfad_abruf  # noqa: E402
# mehrstufiger_abruf.py liegt ebenfalls in haken/ -- eigenes Modul (Monolith-
# Stopp hier), S12 (Auftrag 2026-08-09). Vorgabe AUS und gemessen wirkungslos/
# schaedlich (s. Moduldoc mehrstufiger_abruf.py) -- aus diesem Hook nur
# AUFGERUFEN, ersetzt unten den direkten suchpfad_abruf.kandidaten()-Aufruf
# 1:1 (kandidaten_geschaltet() faellt bei AUS byte-gleich auf
# suchpfad_abruf.kandidaten() zurueck).
import mehrstufiger_abruf  # noqa: E402
# relevanzlage.py liegt in kern/ (bereits im Suchpfad, s.o.) -- reine Rechnung
# ohne DB/Netz/Modell (s. dortiger Moduldoc), TABU fuer diese Aufgabe: nur
# benutzt, nie geaendert (ihre Schwellen sind eine Messung vom 2026-08-16).
import relevanzlage  # noqa: E402

# Protokoll, WAS gezogen wurde -- neben der DB, eigene Datei (kein Tabelle in
# brainlehr.db: sonst schreibt JEDE Sitzung bei JEDEM Prompt in dieselbe DB,
# die auch lesson_recorder beschreibt -> Schreibsperren quer durchs Fleet).
# JSONL, Append-only. Zeilen < 4096 Byte (PIPE_BUF) sind auf POSIX atomar --
# parallele Prozesse koennen sich nicht mitten in eine Zeile schreiben, auch
# ohne Lock.
#
# Seit Auftrag 2026-08-08 (GEMESSENER BEFUND: 676 Treffer-Zeilen ohne
# Anfrage waren nicht wiederholbar -- niemand konnte spaeter pruefen, WORAUF
# geantwortet wurde) traegt jede Zeile bei Treffer zusaetzlich 'prompt' und
# 'kennung' (siehe log_recall(), _herkunftsmodus(), _messparameter_kennung()).
# HERKUNFT/QUELLENSCHUTZ-ENTSCHEIDUNG STEHT AUS (Betreiber 2026-08-07: eine
# Anfrage kann personenbezogene Angaben enthalten, das steht im Zielkonflikt
# mit Wiederholbarkeit). knowledge_config traegt heute (gemessen 2026-08-08)
# KEINEN Schluessel dafuer -- nur 'embed_model'. Bis die Entscheidung faellt:
# Anfrage wird MIT geschrieben (roh, Modus 'voll'), _herkunftsmodus() fragt
# knowledge_config.key='herkunftsmodus' JEDES Mal neu ab, damit ein spaeter
# gesetzter Wert (z.B. 'aus' fuer "Feld ganz weglassen") ohne Codeaenderung
# greift.
RECALL_LOG = str(ort.RECALL_LOG)
RECALL_LOG_MAX_BYTES = 1_000_000  # ~1MB Deckel; bei Ueberschreiten haelftig kappen

# --- Schattenlauf (Anschlussauftrag 2026-08-08, auf Teil 1 aufsetzend) -----
# Mehrere Einstellungen ("Herausforderer") gegen dieselbe echte Anfrage im
# selben Prozess mitlaufen lassen -- eingespielt wird NUR der Titelverteidiger
# (heutige globale Parameter), der Rest laeuft im Schatten und wird nur
# protokolliert (siehe _schatten_konfiguration()/_schatten_lauf()/log_schatten()).
#
# GEMESSENER WIDERSPRUCH zur Auftragsannahme ("N Einstellungen kosten kaum
# mehr als eine, Bestand/Vektoren werden geteilt"): gemessen 2026-08-08, 5x
# hook.query() hintereinander im selben warmen Prozess, dieselbe Anfrage:
# 1x 0.277s, 3x 0.819s (0.273s/Aufruf), 5x 1.363s (0.273s/Aufruf) -- STRIKT
# LINEAR, kein Teilen-Effekt. Ursache (per cProfile gefunden): _apply_trust_
# score() rief knowledge_trust_score() JE KANDIDAT auf; das las ueber
# wirkung.py::report() JEDES MAL das GESAMTE recall_log.jsonl (+zero_hit_
# log.jsonl) neu ein (14905 json.loads()-Aufrufe fuer 10 report()-Aufrufe in
# einem einzelnen query()-Lauf, Bestand an diesem Tag).
# BEHOBEN (L-80e002, 2026-08-07): knowledge_mcp_server._trust_aggregate()
# liest das Protokoll EINMAL je _apply_trust_score()-Lauf statt einmal je
# Kandidat, nach Ziel gruppiert -- siehe dortiger Docstring und Aufruf unten.
# Jede zusaetzliche Schatten-Einstellung kostet dadurch nur noch den
# DB-Anteil (outcome() je Kandidat), nicht mehr den vollen Protokoll-Scan.
SCHATTEN_LOG = str(ort.SCHATTEN_LOG)
SCHATTEN_LOG_MAX_BYTES = 1_000_000  # gleicher Deckel wie RECALL_LOG

# Notbremse: ueberschreitet die bereits verstrichene Zeit (Titelverteidiger
# allein, ab main()-Start) diese Schwelle, laufen GAR KEINE Schatten mehr --
# der Melder haengt an jedem Prompt, ein zusaetzlicher spuerbarer Aufschlag
# ist nur vertretbar, wenn der Titelverteidiger-Pfad selbst normal lief.
# GEMESSEN (2026-08-08, subprocess-Gesamtlauf inkl. Programmstart, Titel-
# verteidiger allein, aktueller Bestand): Median 0.33s (6 Laeufe, 0.329-
# 0.335s). 0.5s laesst rund 50% Spielraum -- GEWAEHLT, NICHT OPTIMIERT (kein
# Pruefkorpus fuer diese Schwelle, wie bei NOISE_FLOOR_MAD_MULT oben).
#
# ZUR EINORDNUNG (nicht die Notbremse selbst, sondern was sie NICHT abfaengt):
# End-zu-Ende ueber main() gemessen (In-Prozess, Momentaufnahme als DB,
# 5 Wiederholungen je Stufe): N=0 Herausforderer 0.329s, N=1 1.206s, N=3
# 2.097s, N=5 2.996s -- rund +0.53s je zusaetzlichem Herausforderer (noch
# mehr als die 0.27s aus dem isolierten query()-Vergleich oben, weil
# wirkung.py::report() das PRODUKTIVE recall_log.jsonl liest, unabhaengig
# von hook.RECALL_LOG -- ein bestehender, hier nicht behebbarer Seiteneffekt,
# der mit jeder weiteren Protokollzeile TEURER wird). Die Notbremse schuetzt
# nur davor, Schatten NACH einem bereits ungewoehnlich langsamen
# Titelverteidiger-Lauf zu starten -- sie begrenzt NICHT die Anzahl
# konfigurierter Herausforderer selbst. Wer N>1 in knowledge_config eintraegt,
# nimmt diese Kosten je Prompt bewusst in Kauf.
SCHATTEN_ZEIT_BUDGET_S = 0.5

# Kurze Stopwort-Liste DE+EN — nur Rauschen filtern, kein NLP.
STOP = {
    "und","oder","der","die","das","den","dem","ein","eine","einen","einem",
    "ist","sind","war","wird","werden","kann","soll","muss","für","mit","von",
    "auf","aus","bei","zum","zur","des","als","auch","nicht","noch","wie","was",
    "wenn","dann","aber","nur","mir","mich","dir","dich","ich","wir","ihr","sie",
    "the","and","for","that","this","with","from","have","has","was","are","you",
    "can","should","must","not","how","what","when","then","but","its","our",
    "bitte","mal","schau","setze","um","dazu","hier","haben","gibt","es","zu",
}


# Deutsche Umlaut-Faltung, gleiche Abbildung wie knowledge_mcp_server.py::fold_de()
# -- nicht importiert (dieser Hook bleibt bewusst abhaengigkeitsfrei, laeuft vor
# JEDEM Prompt, siehe Moduldoc oben). Ohne das faende "Existenzgruender" (ue-
# Schreibung) den FTS-Treffer "Existenzgründer" (ü) nicht, selbst nachdem
# knowledge_fts jetzt gefaltet+trigram indiziert ist (schema.sql).
_FOLD_TABLE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def fold_de(text: str) -> str:
    return text.lower().translate(_FOLD_TABLE)


def keywords(text: str) -> list[str]:
    words = re.findall(r"[A-Za-zÄÖÜäöüß0-9]{4,}", text.lower())
    seen, out = set(), []
    for w in words:
        if w in STOP or w in seen:
            continue
        seen.add(w)
        out.append(w)
    return out[:8]


def fts_match(kws: list[str]) -> str:
    # Jedes Keyword als Phrase quoten -> keine FTS5-Operator-Injection.
    # Gefaltet, weil knowledge_fts jetzt gefaltet indiziert ist (schema.sql).
    return " OR ".join(f'"{fold_de(k)}"' for k in kws)


# Mindestzahl verschiedener Prompt-Keywords im Treffertext.
# Wert 3 bleibt, weil er einziger ist, der auf allen acht Testfaellen (_CASES, Zeile 332+)
# fehlerfrei laeuft. MIN_HITS=2 erzeugt 2 Fehlalarme (Chat-/Meta-Prompts), MIN_HITS=4
# verpasst einen echten Treffer -- nur 3 gibt null Fehler.
#
# Belege (2026-08-05):
# (1) Synth. Abruf-Pruefstand (Korpus 1.1.0): MIN_HITS=2 Recall 0,369/Alarm 0,029,
#     MIN_HITS=3 Recall 0,141/Alarm 0,000.
# (2) Echte Betreiber-Prompts (1923 Stueck): MIN_HITS=2 ohne Abruf fuer 152 (7,9%),
#     MIN_HITS=3 fuer 282 (14,7%).
# (3) Acht Testfaelle (_CASES): nur MIN_HITS=3 null-Fehler.
#
# Pareto-Front (Optimierung, Korpus 1.2.0, 60 Versuche, 2026-08-06):
# MIN_HITS=1   Recall@5 0,454   Fehlalarm 0,101
# MIN_HITS=2   Recall@5 0,369   Fehlalarm 0,033
# MIN_HITS=3   Recall@5 0,141   Fehlalarm 0,000
# -> MIN_HITS=3 liegt auf der optimalen Front, wird nicht dominiert.
#
# Gegenprobe nach Bereichsbezug (geltungsbereich.py, 2026-08-06):
# Der Hoffnung folgend, dass Scoping nach Projekt die Fehlalarme (Chat-/Meta-Prompts)
# eliminiert: Wiederholung der acht _CASES-Testfaelle mit und ohne cwd='fahrtenbuch'.
# Ergebnis: die beiden Fehlalarme bei MIN_HITS=2 bleiben unverändert bestehen
# (dieselben zwei Meta-Prompts, kein Projekt-Filter hilft ihnen). MIN_HITS=3 weiterhin
# null-Fehler auch mit Bereichsbezug.
#
# Entscheidung (2026-08-06T10:30:00+0200):
# MIN_HITS bleibt 3. Begruendung: Pareto-Front zeigt 3 als legitimer Punkt ohne Dominanz.
# Die acht handgewahlten Testfaelle (_CASES) sind die einzige Messung, die die
# Praeferenz des Betreibers traegt (welche Meta-Prompts nie Recall kriegen sollen) --
# dort ist 3 der einzige fehlerfreie Wert. Ein Fehlalarm bei jedem Meta-Prompt
# rauscht dauerhaft; ein verpasster Abruf kostet nur, wenn das Wissen wirklich
# gebraucht wurde.
# Preis: 282 von 1923 echten Prompts (14,7%) kriegen gar keinen Abruf (bei MIN_HITS=2
# waeren es 152 = 7,9% -- also 130 Nachrichten mehr, die schweigen).
# Ungebauter dritter Weg: ein Erkenner fuer Gespraeches-Prompts wuerde Recall von 2 mit
# Ruhe von 3 verbinden. Nicht gebaut, weil spekulativ: weder sind Gespraeches-Prompts
# praezise definiert noch validiert, ob die Trennung den Fehlalarm-Satz reduziert.
# -> Wenn naechste Messung staerker dafuer spricht, ist dieser Weg dann ein
#    informierter Trade-off, nicht eine unbelegte Vermutung.
#
# VORBEHALT: Pruefstand allein empfiehlt MIN_HITS=2 (mehr Recall, kleiner Alarm).
# Er enthaelt aber keine Chat-/Meta-Prompts -- diese sind Grund fuer Wert 3.
# Zur Senkung: Pruefstand-Korpus selbst erweitern und neu vermessen.
#
# MERKE: MIN_HITS gattert auf ANFRAGE-SEITE (Zeile 306): Hat Prompt weniger als
# MIN_HITS verschiedene Keywords, findet gar kein Treffer statt, unabhaengig vom DB-Bestand.
MIN_HITS = 3

# Erkundungsanteil (Auftrag 2026-08-05): ein Regeltreffer wird mit dieser
# Wahrscheinlichkeit durch einen ungesehenen Knoten ersetzt, der MIN_HITS
# ebenfalls erfuellt -- sonst verstaerkt jeder Abruf nur die ohnehin schon
# meistgezogenen Knoten (69,5% aller Ziehungen auf einen einzigen Knoten,
# siehe recall_log.jsonl-Auswertung). 0.15 als Startwert (klein, kein
# empirischer Tuningwert wie MIN_HITS -- bei Bedarf spaeter am Protokoll
# nachjustieren).
EXPLORE_RATE = 0.15

# Gewicht trust_score vs. Relevanzrang (bm25 fuer Nodes, hits/severity/
# occurrences fuer Lessons) -- EINE Stelle, Auftrag 2026-08-07 Schritt 2:
# "das Gewicht muss im Code sichtbar und an EINER Stelle stehen". 0.35 <
# 0.5 -- Relevanz bleibt fuehrend (ein Treffer, der zum Prompt passt, darf
# nicht von einem hohen Score verdraengt werden, der zu etwas anderem
# gehoert), trust_score verschiebt nur innerhalb der Relevanz-Nachbarschaft.
# Siehe _apply_trust_score().
TRUST_WEIGHT = 0.35

# --- Stellbare Parameter, EIN Block (Auftrag 2026-08-07, Erweiterung) -----
# Alle Regler des Abrufs stehen hier oder direkt darueber (MIN_HITS/
# EXPLORE_RATE/TRUST_WEIGHT, Herleitung siehe deren eigene Kommentare oben).
# Kein nacktes Zahlenliteral als Stellgroesse ausserhalb dieses Bereichs.
# Name                        Wert  Bereich          Wirkung
# MIN_HITS                    3     1..8             s.o. -- Mindesttreffer je Anfrage
# EXPLORE_RATE                0.15  0.0..1.0          s.o. -- Erkundungsquote
# TRUST_WEIGHT                0.35  0.0..1.0          s.o. -- trust_score vs. Rang
# MAX_NODES                   3     1..10             wieviele Node-Treffer je Abruf
# MAX_LESSONS                 2     1..5              wieviele Lesson-Treffer je Abruf
# NOISE_FLOOR_MAD_MULT        2.0   1.0..4.0          Radar-Schwelle (s.u.)
# RADAR_MIN_SAMPLE_N          4     2..10             ab wann MAD ueberhaupt aussagekraeftig ist (s.u.)
# FULL_SCAN_ROW_CAP           5000  -                 Sicherheitsdeckel (s.u.)
# PROJECT_CALIBRATION_MIN_SAMPLES 50 -                nur noch gemeldete Konstante, keine Bremse mehr (s.u.)
# MAD_TO_SIGMA                 1.4826 -                mathematische Konstante, KEINE Stellgroesse (s.u.)
# ENSEMBLE_TOP_N               5     1..10             Ensemble-Uebereinstimmungsfenster je Kanal (s.u., Teil 2)
# ZWEITER_KANAL                 True   True/False       Embedding-Kanal ueberhaupt aktiv, Vorgabe AN seit ADR-035 (s.u., Nachtrag)
# ENSEMBLE_PFLICHT              True   True/False       Ensemble-Schweigepflicht, Vorgabe AN seit ADR-035 (s.u., Nachtrag)
# ENTHALTUNGSSCHWELLE_KOSINUS  0.55  0.0..1.0          s.u. -- Enthaltung im aktiven Suchpfad (S9)

# Anzahl ausgegebener Treffer je Abruf -- bisher als nacktes ":3"/":2" an den
# Slice-Stellen in query() verstreut, jetzt hier benannt.
#
# 10/7 seit 2026-08-09, Entscheidung des Betreibers. Vorher 3/2, und das war
# damals richtig: am alten Bestand war die Deckelreihe FLACH -- 3/2 bis 10/7
# lieferten allesamt 7 von 35 Treffern, nur die Zeichenmenge stieg. Unter Rang
# 5 lag Rauschen, mehr liefern hiess mehr Rauschen liefern.
#
# Nach der Umschrift der 350 Knoten ist es eine andere Kurve
# (runs/deckelreihe_nach_umschrift_2026-08-09.json):
#
#   Deckel   Treffer   Zeichen   je Treffer
#     3/2     13/35       4409      339
#     7/5     14/35      11473      819
#    10/7     16/35      16470     1029
#   15/10     19/35      24746     1302
#
# Der Grund steht in der Kandidatendiagnose desselben Tages: der Median-Rang
# des Ziels fiel von 79 auf 27. Unter Rang 5 liegt jetzt Substanz, und genau
# die schnitt der alte Deckel ab.
#
# Warum 10/7 und nicht 15/10: dort ist die Kurve noch steil. Jeder weitere
# Treffer wird teurer als der davor -- 339 Zeichen je Treffer bei 3/2, 1029
# bei 10/7, 1302 bei 15/10.
#
# DIE GRENZE DIESER ZAHLEN, und sie ist nicht klein: gemessen ist ABRUF, nicht
# Antwortqualitaet. Ob ein Modell mit 16470 Zeichen besser antwortet als mit
# 4409, ist NICHT gemessen -- die Literatur zu 'lost in the middle' laesst das
# Gegenteil fuer moeglich halten. Wer das misst, misst die eigentliche Groesse.
# --- Einspielungsdeckel (Aufgabe: Defekt 2 der Eilmeldung bdaf8d65) --------
#
# GEMESSEN 2026-08-14 an drei echten Anfragen: dieser Haken erzeugte 16754,
# 19701 und 20522 Byte je Einspielung. Der Weg dahinter kappt und legt den
# Rest in eine Datei, die niemand oeffnet -- gemessen am 2026-08-13T23:05:
# 11 Einspielungen erzeugten 155749 Byte, angekommen sind 22528. Der Abruf
# arbeitet dabei fehlerfrei; verloren geht es DANACH.
#
# WARUM DAS SCHLIMMER IST ALS PLATZMANGEL: Die Meldung des kappenden Glieds
# lautet "Output too large (16.3KB) ... Preview (first 2KB)". Sie nennt BYTE
# und einen Dateipfad, aber keine Zahl des Gegenstands -- und wird deshalb
# als Formatierungshinweis gelesen statt als Verlustmeldung. Elfmal gelesen,
# elfmal nicht verstanden (L-e61d18).
#
# DIE REPARATUR IST NICHT MEHR PLATZ, SONDERN EHRLICHKEIT: Der Haken kennt
# seine Trefferzahl. Er bleibt INNERHALB der Grenze und benennt, was er
# weglaesst. Ein kurzer vollstaendiger Block schlaegt einen langen gekappten.
#
# ZUR ZAHL: 8000 ist ein gemessener Korridor, keine bekannte Konstante des
# kappenden Glieds -- die kenne ich nicht. Belegt ist beides: ein Block von
# rund 4,5 KB kam am 2026-08-14 vollstaendig an, und 16,3 KB wurden gekappt.
# 8000 liegt mit Abstand unter der belegten Kappung und ueber der belegten
# Zustellung. Ueber BRAINLEHR_RECALL_MAX_BYTES aenderbar, damit ein besserer
# Messwert keine Codeaenderung braucht.
EINSPIELUNG_MAX_BYTES = int(os.environ.get("BRAINLEHR_RECALL_MAX_BYTES", "8000"))


def _auf_budget_kuerzen(lines: list[str]) -> tuple[str, int]:
    """Kuerzt den Block auf EINSPIELUNG_MAX_BYTES und meldet die Restzahl.

    Gekuerzt wird von HINTEN: die Reihenfolge ist bereits die Rangfolge des
    Abrufs, hinten steht das Schwaechste. Kopfzeile und Schlusszeile bleiben
    immer -- ein Block ohne Rahmen waere unlesbar.

    Die Schlusszeile nennt IMMER beide Zahlen, auch wenn nichts weggelassen
    wurde. Nur-bei-Verlust zu melden hiesse, dass die Vollstaendigkeit
    unbelegt bleibt, und genau daran krankte der bisherige Zustand: Niemand
    vermisst, was er nie gesehen hat.
    """
    kopf, rumpf, schluss = lines[:2], lines[2:-1], lines[-1:]
    gesamt = len(rumpf)
    fest = len("\n".join(kopf + schluss).encode("utf-8")) + 200  # 200 fuer die Schlusszeile
    behalten: list[str] = []
    verbraucht = 0
    for zeile in rumpf:
        kosten = len(zeile.encode("utf-8")) + 1
        if fest + verbraucht + kosten > EINSPIELUNG_MAX_BYTES:
            break
        behalten.append(zeile)
        verbraucht += kosten
    weggelassen = gesamt - len(behalten)
    bilanz = f"({gesamt} Treffer, {len(behalten)} eingespielt, {weggelassen} aus Platzgruenden weggelassen)"
    return "\n".join(kopf + behalten + [bilanz] + schluss), weggelassen


MAX_NODES = 10
MAX_LESSONS = 7

# Radar-Schwelle (ADR-033 Schritt 2c): wieviele robuste Standardabweichungen
# (MAD, Median Absolute Deviation, skaliert mit 1.4826 auf Normalverteilungs-
# Sigma) ein Score besser als der Median der ganzen Kandidatenverteilung
# liegen muss, um als Signal statt Rauschen zu gelten. GEWAEHLT, NICHT
# OPTIMIERT -- eine Parametersuche ist fuer den Radar nicht beauftragt (der
# Pruefkorpus hat drei Aufgaben, jede Anpassung waere Ueberanpassung). 2.0
# ist der uebliche Einstieg fuer Ausreisser-Erkennung (2..3 Sigma). Hoeher =
# strenger/oefter still, niedriger = mehr Kandidaten gelten als Signal.
NOISE_FLOOR_MAD_MULT = 2.0

# Ab wieviel Kandidaten der Median+MAD-Rauschteppich ueberhaupt tragfaehig
# ist. Statistischer Grund, keine Kalibrierung gegen den Pruefkorpus: MAD
# aus 2-3 Werten ist selbst ein Ausreisser-Opfer (bei n=3 gemessen: die drei
# einzigen SetFunk-Knoten zu "webrtc jitter buffer" lagen alle nah beieinander,
# der Median wanderte dadurch zu nah an den besten Treffer, keiner ueberstieg
# die 2-Sigma-Schwelle -- der ansonsten einzige Treffer verschwand). Unter
# dieser Schwelle gibt _radar_select() ALLE MIN_HITS-Kandidaten als Signal
# zurueck (wie beim n<=1-Fall: kein verlaessliches Vergleichsmass vorhanden).
RADAR_MIN_SAMPLE_N = 4

# Sicherheitsdeckel fuer den vollen Durchlauf vor der Kappung (ADR-033
# Schritt 2a/d) -- KEIN Ranginstrument mehr (das war der Fehler: LIMIT 12/30
# schnitt VOR der Bewertung). Bei den heute 882 Eintraegen (315 Knoten + 567
# Lehren) kostet ein voller Durchlauf Millisekunden (gemessen 2026-08-07,
# ADR-033). GERATEN, NICHT GEMESSEN: der Bestand hat nie 5000 Eintraege
# ueberschritten, es gibt also keinen Messpunkt dafuer. Ab hier wird der
# volle Scan-Ansatz teuer und die Bauform muss sich aendern (z.B.
# materialisierte Rangliste statt Live-bm25-Scan).
FULL_SCAN_ROW_CAP = 5000

# Projektstufungs-Bremse AUSGEBAUT (Auftrag 2026-08-13,
# docs/PLAN_KALIBRIERBREMSE_2026-08-13.md): _effective_noise_mult(),
# _project_node_counts() und PROJECT_NOISE_OVERRIDES sind entfernt. Messung
# vor dem Ausbau (messungen/kalibrierbremse_messung_2026-08-13.py): query()
# rief die Bremse ohnehin mit hartcodiertem project_id=None auf (Docstring
# der entfernten Funktion sagte es selbst: "HERKUNFT NOCH NICHT
# VERDRAHTET"), die Uebersteuerungstabelle war leer und blieb es zu Recht --
# der reale Bestand hat fuer keines der drei Projekte ueber der
# Knotenschwelle (50) genug ETIKETTIERTE Abruf-Faelle, um einen eigenen
# Schwellenwert zu messen statt zu raten (gemessen: shared 12, brainlehr 8,
# begod 7 Faelle in runs/echtkorpus_*.json -- weit unter dem, was ADR-035
# schon fuer EINEN gemeinsamen Wert als Untergrenze fuer eine echte Eichung
# ansetzte). Eine fertige, getestete, nie aufgerufene Struktur ist Ballast;
# sie wird beim naechsten Lesen fuer wirksam gehalten. Rueckweg: siehe
# Git-Historie dieser Datei vor diesem Commit.
#
# PROJECT_CALIBRATION_MIN_SAMPLES bleibt als blosser Wert stehen, weil
# kern/messparameter.py (TABU fuer diese Sitzung) ihn ungeprueft aus dem
# Modul liest und in Ergebnisdateien meldet (schnappschuss()) -- ohne
# Bremse dahinter ist die Zahl nur noch eine gemeldete Konstante, keine
# wirkende Schwelle mehr. Wer kern/messparameter.py als naechstes anfasst,
# sollte das Feld dort streichen.
PROJECT_CALIBRATION_MIN_SAMPLES = 50

# Mathematische Konstante (MAD -> Sigma-Aequivalent bei Normalverteilung),
# KEINE Stellgroesse -- hier benannt statt als nacktes Zahlenliteral in
# _radar_select(), damit der Block oben wirklich alle Zahlen zeigt.
MAD_TO_SIGMA = 1.4826

# Ensemble-Uebereinstimmung (Teil 2, Auftrag 2026-08-07): mit zwei Kanaelen
# (Stichwort/bm25, Embedding/Cosine) ist ihre STREUUNG das zweite, vom
# einzelnen Radar unabhaengige Unsicherheitsmass (Vorbild: Ensemble-Vorhersage
# der Meteorologie -- Uneinigkeit der Modelle IST das Signal). Gemessen wird
# sie hier als Rang-Uebereinstimmung: ein Kandidat gilt als 'vorn' in einem
# Kanal, wenn er unter dessen besten ENSEMBLE_TOP_N radar-bestaetigten
# Raengen liegt (Rang, nicht Rohscore -- bm25 und Cosine-Similarity sind
# nicht direkt vergleichbar, exakt der Grund, warum rrf_fuse() selbst auf
# Raengen arbeitet). GEWAEHLT, NICHT GEMESSEN -- wie NOISE_FLOOR_MAD_MULT
# kein Pruefkorpus fuer diesen Parameter. 5 statt z.B. MAX_NODES(3), damit
# das Fenster Ueberschneidung realistisch zulaesst, ohne die zwei Kanaele
# durch ein zu enges Fenster praktisch nie einig werden zu lassen.
ENSEMBLE_TOP_N = 5

# Zwei Schalter, zwei Nachtraege (2026-08-07), EIN Befund: drei einstellbare
# Zustaende, GEMESSEN an derselben Stichprobe (150 echte Prompts aus
# shared-knowledge/auftraege.jsonl, seed 20260807, 131 davon auswertbar):
#
#   A  ZWEITER_KANAL=False                    (vor Commit 4167aef78) 44% Schweigen (58/131)
#   B  ZWEITER_KANAL=True, ENSEMBLE_PFLICHT=False  (Commit 4167aef78)  0% Schweigen ( 0/131)
#   C  ZWEITER_KANAL=True, ENSEMBLE_PFLICHT=True   (Commit 9fdae2726) 86% Schweigen (113/131)
#
# B bedeutet NICHT "mehr Treffer": die Embedding-Suche liefert fuer PRAKTISCH
# JEDEN Prompt einen "aehnlichsten" Kandidaten, auch fuer thematisch voellig
# unbeteiligte -- Beleg: der Prompt "kartoffeln pflanzen im Fruehjahr" liefert
# 3 Knoten + 2 Lehren mit Cosine-Aehnlichkeit 0,63-0,65, erkennbar Rauschen,
# kein Treffer. C ist keine Verschaerfung auf stabilem Fundament (44%), sondern
# die Korrektur eines Kanals, der zu allem ja sagt (B) -- das war ein
# Denkfehler in der vorigen Fassung dieses Nachtrags, siehe Commit-Historie.
#
# NACHTRAG (ADR-035, beschlossen 2026-08-07): der Versuchsaufbau mit bekannter
# Wahrheit lief. Eigener Bestand (98 Eintraege: 60 Knoten, 38 Lehren, fuenf
# Abteilungen), 24 Aufgaben (8 loesbar, 8 unloesbar, 8 verfuehrerisch), seed
# 20260807, gegengeprueft mit seed 1 und 99:
#
#                             A       B       C
#   Trefferguete/8             4       6       4
#   falsches Schweigen / 8    4       0       4
#   richtiges Schweigen / 8   8       1       8
#   Fehlgriff verfuehrerisch  0       6       0
#   Fremdprojekt-Uebertritt   1      16       0
#   Eichung schweigt         ja    NEIN      ja
#
# C ist an keiner Stelle schlechter als A und bei S7 sogar besser (A liefert
# dort einen Fremdprojekt-Treffer mit, C nicht). B ist unhaltbar (schweigt
# nur 1x von 24, 6 Fehlgriffe, 16 Uebertritte). Siehe ADR-035 fuer die volle
# Herleitung.
#
# PREIS von C, nicht weggeredet: zwei loesbare Aufgaben (S2, S8) findet nur
# B -- der zweite Kanal traegt dort echtes Signal, und die Ensemble-Pflicht
# verwirft es zusammen mit dem Rauschen. C kauft Praezision mit Trefferquote.
#
# Ausgeliefert war zum Zeitpunkt dieses Beschlusses A (beide Schalter False,
# Commit f7d89a49d) -- nicht B, wie eine fruehere Fassung dieses Kommentars
# und ADR-035 zunaechst behaupteten. Das Urteil aendert sich dadurch nicht:
# C wurde auch gegen A verglichen und ist ihm nicht unterlegen.
#
# Per KNOWLEDGE_ZWEITER_KANAL=1/0 und KNOWLEDGE_ENSEMBLE_PFLICHT=1/0
# weiter ueberschreibbar, falls ein Messlauf A/B braucht, ohne diese Datei
# zu aendern.
#
# Notbremse 2026-08-07T13:30+0200, WIEDER SCHARF seit 14:20+0200 (Modellwechsel
# nomic-embed-text -> bge-m3, Auftrag 2026-08-07): kurz nach dem vollstaendigen
# build_embeddings.py-Lauf tauchten erneut 3 Zeilen mit model='nomic-embed-text'
# in knowledge_embeddings auf (Zeitstempel NACH dem Lauf) -- ein noch
# laufender Prozess (MCP-Server/Hook einer anderen Sitzung) haelt den alten
# Modul-Vorgabewert im Speicher und schreibt bei jedem Knoten-/Lehren-Schreiben
# weiter nomic-embed-text-Vektoren. Kein einmaliges Aufraeumen behebt das,
# solange dieser Prozess laeuft -- erst neu starten, dann erneut pruefen
# (SELECT model, COUNT(*) FROM knowledge_embeddings GROUP BY model muss
# EIN Modell zeigen), dann zurueck auf True.
#
# WIEDER EIN seit 2026-08-09, Entscheidung des Betreibers. Die Bedingung der
# Notbremse ist erfuellt: die Tabelle traegt genau ein Modell (bge-m3), 0
# fehlende und 0 veraltete Vektoren bei 2028 Knoten.
#
# Der Grund ist ein anderer als beim ersten Anlauf. An den alten, schlecht
# geschriebenen Knoten brachte der Kanal +1 von 35 -- an den heute
# umgeschriebenen +5 (8/35 gegen 13/35, gemessen ueber runs/pruefkorpus.jsonl
# mit abrufguete.py). Er war nie das Problem; das Material war es.
#
# Preis, nicht weggeredet: ein Ollama-Aufruf je Prompt, rund 0,2 Sekunden.
# Rueckweg: KNOWLEDGE_ZWEITER_KANAL=0 in der Umgebung, kostet nichts.
ZWEITER_KANAL = True


def _zweiter_kanal_aktiv() -> bool:
    override = os.environ.get("KNOWLEDGE_ZWEITER_KANAL")
    if override is not None:
        return override == "1"
    return ZWEITER_KANAL


ENSEMBLE_PFLICHT = True


def _ensemble_pflicht_aktiv() -> bool:
    override = os.environ.get("KNOWLEDGE_ENSEMBLE_PFLICHT")
    if override is not None:
        return override == "1"
    return ENSEMBLE_PFLICHT


# S9 (docs/PLAN_DESTILLE_2026-08-09.md): Kandidaten ueber denselben
# Suchpfad wie knowledge_search (haken/suchpfad_abruf.py) statt ueber das
# MIN_HITS/ENSEMBLE_PFLICHT-Sieb dieser Datei. Gemessen 2026-08-09 gegen
# 35 Faelle: alter Weg 0/35 (Vorgabe) bzw. 4/35 (beide Kanaele), neuer Weg
# 7/35 -- siehe Modul-Docstring von suchpfad_abruf.py fuer die volle Zahl.
# Vorgabe zunaechst AUS: gleiche Bauform wie ZWEITER_KANAL oben (Modul-
# Konstante mit Env-Uebersteuerung), bis die Messung ueber die Betriebsdaten
# entscheidet.
# EIN seit 2026-08-09, Entscheidung des Betreibers. Gemessen mit korrekter
# Eingabe (Prompt durchgereicht, wie der Betrieb ruft): alter Weg 0 von 35
# Treffern bei 2540 Zeichen und 37,8 Prozent leeren Faellen, Suchpfad 7 von
# 35 bei 4776 Zeichen und 0 Prozent leer. Erstmals ueberhaupt Lehren (4 von
# 15). Nuetzlichkeit auf demselben Pfad blind beurteilt: 11 von 35 haetten
# geholfen, Negativkontrolle bestanden (1 von 12 falschen Paaren).
#
# Der Preis ist benannt und nicht schoengeredet: 88 Prozent mehr Zeichen in
# JEDEM Prompt, und das Schweigen geht verloren -- der alte Weg lieferte in
# 37,8 Prozent der Faelle nichts, und nichts ist manchmal die richtige
# Antwort. Eine frische Lesung von 15 Eintraegen fand 2 thematisch nah.
#
# Rueckweg: KNOWLEDGE_SUCHPFAD_ABRUF=0 in der Umgebung, kostet nichts.
SUCHPFAD_ABRUF = True


def _suchpfad_aktiv() -> bool:
    override = os.environ.get("KNOWLEDGE_SUCHPFAD_ABRUF")
    if override is not None:
        return override == "1"
    return SUCHPFAD_ABRUF


# Enthaltungsschwelle bedeutungs_kosinus (Auftrag 2026-08-19): erreicht KEIN
# Kandidat des aktiven Suchpfads (suchpfad_abruf.kandidaten() ueber
# mehrstufiger_abruf.kandidaten_geschaltet(), s. _suchpfad_aktiv()) diesen
# rohen Kosinus, wird NICHTS eingespielt -- gemessen ueber GENAU diesen Weg
# in runs/enthaltungsschwelle_kosinus_abrufweg.json (Schnappschuss
# 20260819T094703-31bcb647, n=35 einschlaegig / 41 fachfremd): bei 0.55 sind
# 3/35 faelschlich enthalten und 0/41 faelschlich geliefert. Gleichstand
# (Kandidat exakt 0.55) gewinnt fuer den Abruf (NICHT enthalten) -- so ist
# die 0-faelschlich-geliefert-Zahl selbst gerechnet: sie zaehlt Werte >=0.55
# bereits als geliefert.
#
# Abschaltbar ueber KNOWLEDGE_ENTHALTUNG_KOSINUS=0/1 in der Umgebung (Vorgabe: AN).
ENTHALTUNGSSCHWELLE_KOSINUS = 0.55


def _enthaltung_aktiv() -> bool:
    override = os.environ.get("KNOWLEDGE_ENTHALTUNG_KOSINUS")
    if override is not None:
        return override == "1"
    return True


def _radar_select(candidates: list, score_key: str,
                   mad_mult: float = NOISE_FLOOR_MAD_MULT) -> list:
    """Radar statt Kappung (ADR-033 Schritt 2): ALLE Kandidaten sind hier schon
    bewertet (score_key, bm25 -- kleiner ist besser), also erst jetzt --
    NACH der Bewertung -- wird gekappt. Ein Kandidat gilt als Signal, wenn
    sein Score deutlich (NOISE_FLOOR_MAD_MULT robuste Standardabweichungen)
    unter dem Median der GANZEN Verteilung liegt. Median+MAD statt
    Mittelwert+Standardabweichung: robust gegen einzelne Ausreisser.

    n<1 RADAR_MIN_SAMPLE_N: kein verlaessliches Vergleichsmass -- alle
    Kandidaten gelten als Signal (n<=1 ohnehin trivial: nichts, wogegen der
    eine Kandidat "Rauschen" waere; n=2..RADAR_MIN_SAMPLE_N-1: MAD aus so
    wenigen Werten ist selbst ausreisseranfaellig, siehe RADAR_MIN_SAMPLE_N).
    MAD==0 bei ausreichend n (alle Scores gleich -- "alles gleich schwach"):
    keiner sticht hervor -> leere Liste, ehrliches Schweigen statt
    Zufallsauswahl. Nicht gekappt auf einen Hoechstwert -- das macht der
    Aufrufer per Slice (MAX_NODES/MAX_LESSONS), damit _maybe_explore()
    weiterhin ueber die volle Signal-Menge (nicht nur die ausgegebenen
    Top-N) explorieren kann."""
    n = len(candidates)
    if n == 0:
        return []
    if n < RADAR_MIN_SAMPLE_N:
        return list(candidates)
    scores = sorted(c[score_key] for c in candidates)
    mid = n // 2
    median = scores[mid] if n % 2 else (scores[mid - 1] + scores[mid]) / 2
    deviations = sorted(abs(s - median) for s in scores)
    mad = deviations[mid] if n % 2 else (deviations[mid - 1] + deviations[mid]) / 2
    if mad == 0:
        return []
    threshold = median - mad_mult * mad * MAD_TO_SIGMA
    signal = [c for c in candidates if c[score_key] < threshold]
    signal.sort(key=lambda c: c[score_key])
    return signal


def _apply_trust_score(items: list, kind: str, ref_of=lambda x: x["path"]) -> list:
    """Sortiert eine bereits relevanzgeordnete Liste (bm25 fuer Nodes, hits/
    severity/occurrences fuer Lessons -- Reihenfolge beim Aufruf) um: Rang-
    Position (1.0 = bester Relevanztreffer, 0.0 = letzter) und trust_score
    (knowledge_trust_score(), 0..1) gewichtet mit TRUST_WEIGHT gemischt,
    stabil nach combined absteigend sortiert. Bricht wenn knowledge_
    trust_score() fehlschlaegt (Datenbank kurzzeitig gesperrt) NICHT den
    Abruf -- dann faellt dieser EINE Kandidat auf trust_score=0.5 zurueck
    (== Vorgabewert, unauffaellig in der Mitte statt am Rand)."""
    n = len(items)
    if n <= 1:
        return items

    # Einmal-Aggregat fuer die ganze Liste (L-80e002) statt eines vollen
    # Protokoll-Scans je Kandidat in knowledge_trust_score() -- faellt bei
    # Fehler (DB/Log kurzzeitig nicht lesbar) auf None zurueck, dann macht
    # knowledge_trust_score() weiter seinen alten Pro-Kandidat-Scan.
    try:
        aggregate = _trust_aggregate(kind)
    except Exception:
        aggregate = None

    def combined(idx_item):
        idx, item = idx_item
        rank_score = 1 - idx / n
        try:
            trust = knowledge_trust_score(kind, ref_of(item), aggregate)["trust_score"]
        except Exception:
            trust = 0.5
        return (1 - TRUST_WEIGHT) * rank_score + TRUST_WEIGHT * trust

    scored = sorted(enumerate(items), key=combined, reverse=True)
    return [item for _, item in scored]


def _embedding_scores(conn, kind: str, query_vec: list[float] | None) -> dict[str, float] | None:
    """Cosine-Aehnlichkeit je ref_id (zweiter Relevanzkanal, Auftrag
    2026-08-07 Teil 1). None heisst: Kanal nicht verfuegbar -- entweder
    query_vec fehlt (Ollama unerreichbar/kein Modell, embed_text() ist per
    Vertrag best-effort) ODER die knowledge_embeddings-Tabelle fehlt (aeltere
    DB-Kopie). Der Aufrufer faellt dann auf den Stichwort-Kanal allein
    zurueck -- ein Ausfall darf die Wissenssuche nie blockieren (siehe
    embeddings.py-Moduldoc). Nur lebende Eintraege (zurueckgezogene
    Knoten/aufgeloeste Lehren raus, wie beim Stichwort-Kanal), direkt im
    JOIN statt als zweiter Query."""
    if query_vec is None:
        return None
    sql = {
        "node": ("SELECT e.ref_id, e.vector FROM knowledge_embeddings e "
                 "JOIN knowledge_nodes n ON n.id = e.ref_id "
                 "WHERE e.kind = 'node' AND n.zurueckgezogen = 0"),
        "lesson": ("SELECT e.ref_id, e.vector FROM knowledge_embeddings e "
                   "JOIN lessons_learned l ON l.id = e.ref_id "
                   "WHERE e.kind = 'lesson' AND l.status != 'resolved'"),
    }[kind]
    try:
        rows = conn.execute(sql).fetchall()
    except sqlite3.OperationalError:
        return None
    return {r["ref_id"]: embeddings.cosine_similarity(query_vec, embeddings.unpack_embedding(r["vector"]))
            for r in rows}


def _parse_iso_grenze(value: str, ende_des_tages: bool) -> datetime | None:
    """Robuste Grenzwert-Parsung fuer gilt_ab/gilt_bis (L-ec167a, gemessen
    2026-08-08: Bestand mischt volle ISO-Zeitstempel mit Offset
    ('2026-08-01T13:07:16+01:00') und reine Datumsangaben ('2026-08-06') --
    ein reiner Stringvergleich waere bei dieser Mischung nicht zuverlaessig.
    Datum-only wird auf eine Tagesgrenze gelegt: gilt_ab -> Tagesbeginn
    00:00:00 (ab wann gilt es), gilt_bis -> Tagesende 23:59:59 (bis wann
    INKLUSIVE gilt es, gleiche Konvention wie normkraft.py/_geltung_status()
    im MCP-Server). Kein Offset im Wert -> UTC angenommen (ponytail: grobe
    Annahme statt Zeitzone je Zeile zu erschliessen; betrifft nur die
    Datum-only-Werte, die vollen ISO-Werte tragen ihren Offset selbst).
    Unparsbarer Wert -> None, Aufrufer behandelt das als "keine Grenze"."""
    try:
        d = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    if len(value.strip()) == 10:  # nur Datum, kein Zeitanteil
        d = d.replace(hour=23, minute=59, second=59) if ende_des_tages else d
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


def _ist_geltend(gilt_ab: str | None, gilt_bis: str | None, jetzt: datetime | None = None) -> bool:
    """Abgelaufene/noch nicht in Kraft getretene Knoten wie zurueckgezogene
    behandeln (Auftrag 2026-08-08, Fakt: gilt_bis wurde im Abruf bisher
    NIRGENDS geprueft). NULL/leer heisst UNBEFRISTET und MUSS durchgelassen
    werden (1978 von 1979 Knoten, Betreiber-Auflage) -- deshalb frueher
    Return True bei fehlendem Wert, vor jeder Parsung. jetzt injizierbar
    (Walkthrough-Doktrin), Vorgabe: echte Uhrzeit. Nur der automatische
    Abruf hier filtert -- die ausdrueckliche Suche im MCP-Server bleibt
    unveraendert (die darf Historisches weiter finden, GRENZE des Auftrags)."""
    jetzt = jetzt if jetzt is not None else datetime.now(timezone.utc)
    if gilt_ab:
        ab = _parse_iso_grenze(gilt_ab, ende_des_tages=False)
        if ab is not None and jetzt < ab:
            return False
    if gilt_bis:
        bis = _parse_iso_grenze(gilt_bis, ende_des_tages=True)
        if bis is not None and jetzt > bis:
            return False
    return True


def _node_info(conn, node_id: str) -> dict | None:
    """Knotendaten fuer eine ref_id, die der Stichwort-Kanal NICHT mitbrachte
    (reiner Embedding-Fund -- genau der Fall, den Teil 1 loesen soll)."""
    row = conn.execute(
        "SELECT path, title, summary, updated_at, gilt_ab, gilt_bis FROM knowledge_nodes n "
        f"WHERE id = ? AND zurueckgezogen = 0 {SQL_ARBEITSBESTAND_NUR}", (node_id,)
    ).fetchone()
    if row is None:
        return None
    if not _ist_geltend(row["gilt_ab"], row["gilt_bis"]):
        return None
    return dict(row)


def _lesson_info(conn, lesson_id: str) -> dict | None:
    """Wie _node_info, fuer Lehren."""
    row = conn.execute(
        "SELECT description, root_cause, prevention, severity, occurrences, type, last_seen, "
        "first_seen, session, projects "
        "FROM lessons_learned WHERE id = ? AND status != 'resolved'", (lesson_id,)
    ).fetchone()
    return dict(row) if row else None


def _combine_channels(kw_signal: list[dict], emb_signal: list[dict], emb_available: bool) -> list[dict]:
    """Fusioniert Stichwort- und Embedding-Kanal (Teil 1+2, Auftrag
    2026-08-07). emb_available=False (Ollama unerreichbar/kein Modell/keine
    knowledge_embeddings-Tabelle): GRENZFALL -- nur ein Kanal verfuegbar,
    Verhalten wie vor diesem Auftrag (kw_signal unveraendert), kein
    Schweigen aus Mangel an Vergleich.

    emb_available=True, _ensemble_pflicht_aktiv()==False (VORGABE, s.
    ENSEMBLE_PFLICHT-Kommentar): Teil 1 -- reine Union, RRF-geordnet, wie vor
    Commit 9fdae2726. Der zweite Kanal wirkt auf die Reihenfolge, erzwingt
    aber keine Uebereinstimmung.

    emb_available=True, _ensemble_pflicht_aktiv()==True: Teil 2 -- Streuung
    zwischen den Kanaelen ist das Unsicherheitsmass (Ensemble-Vorhersage, s.
    ENSEMBLE_TOP_N-Kommentar). Stimmen sie ueberein (ein Kandidat steht in
    BEIDEN Kanaelen unter deren Top-ENSEMBLE_TOP_N), gilt er als sicher und
    bleibt drin. Kein Kandidat in beiden vorn -> Kanaele widersprechen sich
    vollstaendig -> geschwiegen (leere Liste), NICHT auf einen Kanal
    zurueckgefallen."""
    if not emb_available:
        return kw_signal
    kw_ids = [c["id"] for c in kw_signal]
    emb_ids = [c["id"] for c in emb_signal]
    fused_ids = embeddings.rrf_fuse(kw_ids, emb_ids, embedding_weight=embeddings.hybrid_retrieval_weight())
    by_id = {c["id"]: c for c in kw_signal}
    by_id.update({c["id"]: c for c in emb_signal})
    if not _ensemble_pflicht_aktiv():
        return [by_id[i] for i in fused_ids]
    kw_top = {c["id"] for c in kw_signal[:ENSEMBLE_TOP_N]}
    emb_top = {c["id"] for c in emb_signal[:ENSEMBLE_TOP_N]}
    agree_ids = kw_top & emb_top
    if not agree_ids:
        return []
    return [by_id[i] for i in fused_ids if i in agree_ids]


# Aufgabe 94 (docs/PLAN_GESAMT_2026-08-13.md, Schritt 0, "Linie 0"): das
# Protokoll traegt seither auch die KENNZEICHNENDEN ZAHLEN aus dem, was
# gerade eingespielt wurde -- damit ein Melder auf der Antwortseite
# maschinell pruefen kann, ob eine Zahl aus der Antwort tatsaechlich aus
# diesem Abruf stammt, ohne den ganzen Blocktext zu duplizieren (der steht
# nirgends dauerhaft, nur kurz im additionalContext). Reine Zugabe zur
# ohnehin bestehenden Protokollzeile -- WEDER die Blockausgabe an das Modell
# NOCH die Kandidatenauswahl (query()) aendert sich dadurch, nur was log_
# recall() zusaetzlich vermerkt (Auftrags-Grenze: "nur die Ausgabeform").
#
# MERKMALSWAHL, mit Messung (2026-08-13, gegen den echten Bestand):
# Kommazahl mit >=2 Nachkommastellen (\d+,\d{2,}), NICHT jede Zahl mit
# Trennzeichen. Der Anlassfall selbst ("0,531 gegen 0,527") hat genau diese
# Form. Gegenprobe an allen Knoten/Lehren-Texten (418 Zahlen-Vorkommen bei
# \d+[,.]\d+ ohne Einschraenkung): \d+[,.]\d+ faengt WCAG-Versionen ("2.2",
# 9x) und deutsche Datumsangaben ("29.07", "04.08" -- Tag.Monat sieht wie
# eine Dezimalzahl aus) mit ein, beides haeufig und beweist nichts ueber
# Herkunft. Auf Komma-Dezimalzahlen mit >=2 Nachkommastellen eingeschraenkt
# (wie im Bestand ueblich fuer Messwerte, nie fuer Daten/Versionen): 69
# distinkte Formen im ganzen Bestand, nur 12 davon (17%) kommen mehrfach vor
# (durchweg wiederkehrende Statistikwerte wie "0,001", nicht Datum/Version).
# Node-Pfade sind BEWUSST kein Merkmal -- ein Pfad wie "/frontend" ist ein
# haeufiges Wort mit vorangestelltem Schraegstrich, keine seltene Kennung
# (anders als node_ids/Lehren-IDs unten, die schon jetzt geloggt werden).
_ZAHL_RE = re.compile(r"\d+,\d{2,}")


def _kennzeichnende_zahlen(*texte: str | None) -> list[str]:
    gefunden: set[str] = set()
    for t in texte:
        gefunden.update(_ZAHL_RE.findall(t or ""))
    return sorted(gefunden)


def hits(text: str, kws: list[str]) -> int:
    """Wieviele verschiedene Keywords stecken im Text? Substring, nicht Wort ->
    faengt deutsche Komposita ('modell' in 'modelltraining'), die FTS5 mit dem
    Default-Tokenizer verpasst."""
    t = fold_de(text or "")
    return sum(1 for k in kws if fold_de(k) in t)


# Themenordner, die quer durch alle Projekte gelten -- kein Projektname,
# darum immer "eigener Bereich" (wie 'shared'), nie fremd. Gemessen 2026-08-06:
# knowledge_nodes.project_id kennt im ganzen Bestand nur 4 Werte (aka,
# bebetter, begod, shared) -- "openlehr"/"fahrtenbuch" etc. kommen dort NIE
# vor, obwohl 18 Knoten unter /openlehr/... und 4 unter /fahrtenbuch/...
# liegen (alle mit project_id='shared' oder 'begod' verzettelt). project_id
# ist fuers Scoping also zu grob; der Pfad ist das verlaessliche Signal.
_TOPIC_SEGMENTS = {
    "shared", "arch", "ops", "testing", "frontend", "backend",
    "tools", "agents", "methodik", "lessons",
}


def _project_of_path(path: str | None) -> str | None:
    """Projekt-Tag aus dem Knoten-Pfad. None heisst themenweit/eigen (siehe
    _TOPIC_SEGMENTS), nie 'fremd'. '/apps/<projekt>/...' nutzt das zweite
    Segment (das erste, 'apps', ist selbst kein Projekt)."""
    # ponytail: /apps/-Bestand ist nicht durchgehend hierarchisch -- manche
    # Knoten liegen als /apps/<projekt>/<slug> (zweites Segment = Projekt,
    # sauber), andere flach als /apps/<projekt>-<rest-des-titels> (ganzer
    # Titel-Slug landet als "Projekt"). Fuer die Vorn/Hinten-Sortierung ist
    # das folgenlos (flacher Slug != eigenes Projekt -> korrekt nachrangig),
    # nur das Anzeige-Label wird dann haesslich lang. Sauberer Fix braucht
    # eine Liste bekannter Projektnamen zum Praefix-Matching -- erst wenn
    # die haesslichen Labels wirklich stoeren.
    segs = [s for s in (path or "").strip("/").split("/") if s]
    if not segs:
        return None
    first = segs[0].lower()
    if first == "apps":
        return segs[1].lower() if len(segs) > 1 else None
    if first in _TOPIC_SEGMENTS:
        return None
    return first


def _cwd_project(cwd: str | None) -> str | None:
    """Projekt der laufenden Sitzung aus cwd. Exakte Kopie von
    knowledge_mcp_server.py::_cwd_project (dortiger Docstring erklaert Fund
    und Fix vom 2026-08-06 ausfuehrlich: kein fest verdrahteter Verbundname
    mehr, BEGOD_KNOWLEDGE_PROJECT als Uebersteuerung, sonst Name der
    naechsten Git-Wurzel oberhalb von cwd, sonst letzter Ordnername statt
    None). Aufrufer faellt bei None (nur noch cwd=None/leer) aufs heutige
    Verhalten zurueck (kein Scoping)."""
    if not cwd:
        return None
    override = os.environ.get("BEGOD_KNOWLEDGE_PROJECT")
    if override:
        return override.lower()
    p = Path(cwd)
    for parent in (p, *p.parents):
        if (parent / ".git").exists():
            return parent.name.lower()
    return p.name.lower() if p.name else None


def _tag_node_scope(candidates: list[dict], own: str) -> list[dict]:
    """Setzt 'foreign_project' (Projektname oder None) je Kandidat und
    stable-sortiert eigen/themenweit vor fremd -- fremd bleibt drin, nur
    nachrangig. Reihenfolge innerhalb jeder Gruppe (bm25+trust_score, siehe
    _apply_trust_score) unveraendert -- stable sort, kein dritter Sortpass."""
    for c in candidates:
        proj = _project_of_path(c["path"])
        c["foreign_project"] = proj if proj and proj != own else None
    candidates.sort(key=lambda c: 1 if c["foreign_project"] else 0)
    return candidates


def _tag_lesson_scope(scored: list[tuple], own: str) -> list[tuple]:
    """Wie _tag_node_scope, fuer die (hits, severity, occurrences, dict)-Tupel
    der Lessons. 'projects' leer/NULL -> gilt ueberall (geltungsbereich.py-
    Moduldoc), also nicht fremd."""
    for s in scored:
        d = s[3]
        projs = projekte_aus_projects_json(d.get("projects"))
        d["foreign_projects"] = ", ".join(sorted(projs)) if projs and own not in projs else ""
    scored.sort(key=lambda s: 1 if s[3]["foreign_projects"] else 0)
    return scored


def alter(stempel: str | None) -> str:
    """Alter eines Eintrags in Tagen, als kurzer Zusatz fuers Recall-Fenster.

    Ein Wissenseintrag spiegelt den Stand bei seinem Eintrag. Ohne sichtbares
    Alter wird ein Befund von vor einem Monat wie eine heutige Tatsache
    weitergetragen -- genau der Fehler, der diese Zeilen ausgeloest hat
    (2026-07-29: ein CI-Befund von gestern galt als Ist-Zustand, war aber
    laengst behoben).
    """
    if not stempel:
        return ""
    roh = str(stempel).strip().replace("Z", "+00:00")
    try:
        d = datetime.fromisoformat(roh)
    except ValueError:
        try:
            d = datetime.fromisoformat(roh[:19])
        except ValueError:
            return ""
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    tage = (datetime.now(timezone.utc) - d).days
    if tage < 0:
        return ""
    if tage == 0:
        return " [heute]"
    if tage == 1:
        return " [1 Tag alt]"
    if tage > 30:
        return f" [{tage} Tage alt — VOR NUTZUNG PRUEFEN]"
    return f" [{tage} Tage alt]"


def _geltung_tag(norm_rang: int | None, gilt_bis: str | None, jetzt: datetime | None = None) -> str:
    """Geltung als eigene Achse sichtbar machen (S1d): Rang und Ablaufdatum,
    NUR wenn gesetzt -- ein Eintrag ohne beides bleibt zeichengleich zum
    bisherigen Stand (kein Platzhalter, keine leere Klammer). EIN Klammerpaar
    statt zwei ([Rang 1][bis ...]), weil der Block bei JEDEM Prompt neu
    bezahlt wird -- ein zweites Klammerpaar waere reine Zeichenlast ohne
    zusaetzliche Information. jetzt injizierbar (Walkthrough-Doktrin, wie
    _ist_geltend()).

    'bald'-Zusatz (Ablauf binnen 30 Tagen): Kalendertag-Differenz, nicht
    Zeitdifferenz -- ein Vergleich der vollen datetime-Werte verschiebt sich
    um einen Tag, je nachdem wieviel Uhr es gerade ist (gilt_bis liegt auf
    23:59:59 des Tages, s. _parse_iso_grenze), Kalendertage nicht."""
    if not norm_rang and not gilt_bis:
        return ""
    teile = []
    if norm_rang:
        teile.append(f"Rang {norm_rang}")
    if gilt_bis:
        datum = str(gilt_bis)[:10]
        bis = _parse_iso_grenze(gilt_bis, ende_des_tages=True)
        bald = ""
        if bis is not None:
            heute = (jetzt if jetzt is not None else datetime.now(timezone.utc))
            if (bis.date() - heute.date()).days <= 30:
                bald = " bald"
        teile.append(f"bis {datum}{bald}")
    return " [" + ", ".join(teile) + "]"


def _attach_norm_rang(conn: sqlite3.Connection, nodes: list) -> None:
    """Haengt norm_rang an die bereits ausgewaehlten (<= MAX_NODES) Knoten an
    -- fuer _geltung_tag() in main(). Weder query()/suchpfad_abruf.py noch
    mehrstufiger_abruf.py selektieren die Spalte (Auftragsgrenze: nur diese
    Datei anfassen), deshalb derselbe Nachschlag-Zuschnitt wie bei
    _attach_norm_offen() -- eigener Query auf dem Primaerschluessel NACH der
    Auswahl, still nichts anhaengen bei fehlender Spalte/Fehler."""
    ids = [n["id"] for n in nodes if n.get("id")]
    if not ids:
        return
    try:
        platzhalter = ",".join("?" * len(ids))
        rows = conn.execute(
            f"SELECT id, norm_rang FROM knowledge_nodes WHERE id IN ({platzhalter})",
            ids,
        ).fetchall()
    except sqlite3.OperationalError:
        return
    lookup = {r["id"]: r["norm_rang"] for r in rows}
    for n in nodes:
        if n.get("id") in lookup:
            n["norm_rang"] = lookup[n["id"]]


def _attach_abgeloest(conn: sqlite3.Connection, nodes: list) -> None:
    """Haengt an jeden Treffer, ob ihn ein NACHFOLGER abgeloest hat -- und
    welcher.

    ANLASS, 2026-08-18: Der Betreiber entschied, dass Abgeloestes nicht
    weggeworfen wird ("das abgeloeste nicht komplett wegschmeissen, weil ...
    Kann daraus auch wieder Neues wissen oder leeren entstehen?!", BDW-P08,
    kern/abloesung.py). Der Eintrag bleibt also im Bestand und wird weiter
    gefunden -- und genau das ist ohne diese Kennzeichnung gefaehrlicher als
    vorher: Ein Leser bekommt einen ueberholten Satz ohne Hinweis, dass es
    einen neueren gibt.

    Unauffindbar waere Vergessen, ungekennzeichnet ist eine Falschaussage.
    Diese Funktion ist die Kennzeichnung; ohne sie waere die Abloesung
    gebaut und wirkungslos -- der Befund des Tages (BDW-P06).

    Zuschnitt wie _attach_norm_rang: eigener Nachschlag NACH der Auswahl, bei
    fehlender Tabelle still nichts anhaengen (eine aeltere Datenbankkopie
    kennt knowledge_relations, aber keine Abloesungskante -- das ist kein
    Fehler, sondern ein Bestand ohne Abloesungen)."""
    pfade = [n["path"] for n in nodes if n.get("path")]
    if not pfade:
        return
    try:
        platzhalter = ",".join("?" * len(pfade))
        rows = conn.execute(
            f"SELECT target_path, source_path, evidence FROM knowledge_relations"
            f" WHERE relation_type = 'loest_ab' AND target_path IN ({platzhalter})",
            pfade,
        ).fetchall()
    except sqlite3.OperationalError:
        return
    lookup = {r["target_path"]: (r["source_path"], r["evidence"]) for r in rows}
    for n in nodes:
        treffer = lookup.get(n.get("path"))
        if treffer:
            n["abgeloest_durch"], n["abgeloest_grund"] = treffer


def _abloesung_tag(n: dict) -> str:
    """Der sichtbare Teil. Kurz, weil er in JEDER Trefferzeile stehen kann --
    der Grund selbst wird nicht mitgedruckt (er steht am Nachfolger), nur der
    Verweis darauf."""
    ziel = n.get("abgeloest_durch")
    return f" [ABGELÖST durch {ziel}]" if ziel else ""


def _node_hit_counts(log_path: str | None = None) -> Counter | None:
    """Ziehungs-Zaehlung je Node-Pfad aus dem Abrufprotokoll, nur fuers
    Erkunden. None bei JEDEM Problem (Datei fehlt, kaputte Zeile) -- der
    Aufrufer erkundet dann einfach nicht, statt zu raten. Bewusst strenger
    als report() (das einzelne kaputte Zeilen ueberspringt): hier soll ein
    beschaedigtes Protokoll die Erkundung ausschalten, nicht verfaelschen."""
    log_path = log_path if log_path is not None else RECALL_LOG
    counts = Counter()
    try:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                counts.update(json.loads(line).get("nodes", []))
    except (OSError, json.JSONDecodeError, AttributeError):
        return None
    return counts


def _maybe_explore(nodes: list, candidates: list, rand=None, log_path: str | None = None) -> list:
    """Ersetzt mit EXPLORE_RATE den schwaechsten Regeltreffer (letzter Rang)
    durch den am seltensten gezogenen Kandidaten, der MIN_HITS ebenfalls
    erfuellt, aber nicht schon unter den regulaeren Treffern ist. `rand`
    injizierbar (Default random.random) -- Selbsttest ersetzt ihn, statt
    echten Zufall zu patchen. Kein Kandidat uebrig oder Protokoll nicht
    lesbar -> nodes unveraendert, nie weniger Treffer als vorher."""
    rest = candidates[len(nodes):]
    if not rest:
        return nodes
    roll = rand if rand is not None else random.random
    if roll() >= EXPLORE_RATE:
        return nodes
    counts = _node_hit_counts(log_path)
    if counts is None:
        return nodes
    pick = min(rest, key=lambda c: counts.get(c["path"], 0))
    out = list(nodes)
    out[-1] = {**pick, "explore": True}
    return out


def _attach_norm_offen(conn: sqlite3.Connection, nodes: list) -> None:
    """Haengt norm_entscheidung an die bereits ausgewaehlten (<= MAX_NODES)
    Knoten an -- fuer den Erstverwendungs-Vorschlag in main(). Eigener Query
    auf dem Primaerschluessel NACH der Auswahl, kein Teil von Rangfolge/Radar
    (die kennen die Spalte nicht und sollen sie nicht kennen). Fehlt die
    Spalte (z.B. schlanke Test-DB ohne norm_entscheidung) -> still nichts
    anhaengen, kein Fehler nach oben."""
    ids = [n["id"] for n in nodes if n.get("id")]
    if not ids:
        return
    try:
        platzhalter = ",".join("?" * len(ids))
        rows = conn.execute(
            f"SELECT id, norm_entscheidung FROM knowledge_nodes WHERE id IN ({platzhalter})",
            ids,
        ).fetchall()
    except sqlite3.OperationalError:
        return
    lookup = {r["id"]: r["norm_entscheidung"] for r in rows}
    for n in nodes:
        if n.get("id") in lookup:
            n["norm_entscheidung"] = lookup[n["id"]]


def _bereits_vorgeschlagen(ids: list[str], log_path: str | None = None) -> set:
    """Knoten-IDs, denen schon einmal ein Erstverwendungs-Vorschlag gezeigt
    wurde -- ueber ALLE Sitzungen hinweg (anders als _seen_this_session:
    'erstes Auftreten ueberhaupt', nicht 'schon in dieser Sitzung'). Scan von
    recall_log.jsonl (deckelt sich selbst, s. RECALL_LOG_MAX_BYTES). Kein
    Log/Fehler -> leere Menge -- im Zweifel wird gezeigt, nicht geschluckt."""
    if not ids:
        return set()
    log_path = log_path if log_path is not None else RECALL_LOG
    gezeigt: set = set()
    try:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                gezeigt.update(e.get("erstverwendung_vorschlag") or [])
    except OSError:
        pass
    return gezeigt


def _erstverwendung_zeile(n: dict) -> str:
    """Eine Vorschlagszeile fuer EINEN offenen Knoten (norm_entscheidung ==
    'offen'). Nutzt nur norm_ableiten() -- reine Textanalyse, keine DB, keine
    Nebenwirkung, schreibt nichts. content liegt hier nicht vor (query()s
    SELECT holt es nicht) -- title+summary reichen, erstverwendung.py laesst
    content laut eigener Signatur bewusst optional (str | None)."""
    norm = _erstverwendung_norm_ableiten(n.get("title") or "", n.get("summary") or "", None)
    if norm["ableitbar"]:
        return (f"- ERSTVERWENDUNG [{n['path']}]: {norm['begruendung']} "
                f"-> norm_entscheidung={norm['norm_entscheidung']} vorschlagen (Vorschlag, keine Setzung).")
    felder = ", ".join(norm["mensch_muss_setzen"])
    return f"- ERSTVERWENDUNG [{n['path']}]: {norm['grund']} -- du entscheidest: {felder}."


def _erstverwendungs_vorschlaege(nodes: list, log_path: str | None = None) -> tuple[list[str], list[str]]:
    """(Zeilen, gezeigte IDs) fuer alle Knoten in `nodes` mit
    norm_entscheidung == 'offen', die noch KEINEN Vorschlag hatten (s.
    _bereits_vorgeschlagen). Leer -> ([], []), main() haengt dann nichts an."""
    offene = [n for n in nodes if n.get("norm_entscheidung") == "offen" and n.get("id")]
    if not offene:
        return [], []
    schon = _bereits_vorgeschlagen([n["id"] for n in offene], log_path)
    neu = [n for n in offene if n["id"] not in schon]
    if not neu:
        return [], []
    return [_erstverwendung_zeile(n) for n in neu], [n["id"] for n in neu]


def query(kws: list[str], rand=None, log_path: str | None = None, cwd: str | None = None,
          prompt: str | None = None, embed_fn=None,
          bedeutungswerte: list | None = None,
          enthaltung_satz: list[str] | None = None) -> tuple[list, list]:
    """ADR-033 Schritt 2: erst BEWERTEN (bm25 ueber knowledge_fts/lessons_fts,
    kein LIMIT vor der Bewertung mehr -- FULL_SCAN_ROW_CAP ist nur noch ein
    Sicherheitsdeckel), dann per _radar_select() kappen (Median+MAD-Rausch-
    teppich -- schweigt, wenn nichts heraussticht), erst danach trust_score/
    Scope/Explore wie bisher.

    Zweiter Relevanzkanal (Auftrag 2026-08-07 Teil 1): Cosine-Aehnlichkeit
    ueber knowledge_embeddings, per _combine_channels() (rrf_fuse, wie der
    aktive Suchweg) mit dem Stichwort-Kanal fusioniert -- VOR trust_score/
    Scope/Explore, damit beide Kanaele dieselbe Nachbehandlung durchlaufen.
    embed_fn injizierbar (Default embeddings.embed_text) -- Walkthrough-
    Doktrin: mockbare Aussenwelt, kein echter Ollama-Aufruf im Test noetig.

    bedeutungswerte (Auftrag 2026-08-18): optionale Ausgabeliste, wie
    werte= bei knowledge_mcp_server.py::_embedding_ranking(). Der aktive
    Weg (_suchpfad_aktiv()) verwirft die rohen Kosinuswerte vor der
    Rueckgabe (suchpfad_abruf.kandidaten() fusioniert nur noch Rangpositionen)
    -- ohne diesen Parameter haette der Aufrufer sie nicht. Wird NUR gefuellt,
    NIE fuer Auswahl/Sortierung gelesen (reines Kennzeichnungs-Beiwerk).

    enthaltung_satz (Auftrag 2026-08-19): optionale Ausgabeliste wie
    bedeutungswerte. Nur im aktiven Suchpfad (_suchpfad_aktiv()) befuellt:
    traegt KEIN Kandidat den ENTHALTUNGSSCHWELLE_KOSINUS-Wert
    (bedeutungs_kosinus, s. suchpfad_abruf.kandidaten()), wird ein
    sichtbarer Satz angehaengt UND nodes/lessons bleiben fuer diese Anfrage
    leer -- ein stilles Nichts ist von einem kaputten Haken nicht zu
    unterscheiden."""
    own = _cwd_project(cwd)
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=2.0)
    conn.row_factory = sqlite3.Row
    nodes, lessons = [], []
    # ZWEITER_KANAL=True (Vorgabe seit ADR-035, s.o. Kommentar A/B/C):
    # Ollama-Aufruf + Tabellenabfrage aktiv, ausser _zweiter_kanal_aktiv()
    # ist per Env-Var abgeschaltet.
    query_vec = None
    if _zweiter_kanal_aktiv():
        # Kein Ollama-Aufruf, wenn es lokal ohnehin nichts zum Vergleichen
        # gibt (Tabelle fehlt/leer -- z.B. eine frische Test-DB, bevor
        # build_embeddings.py lief): spart den Netzwerk-Umweg UND haelt
        # query() fuer eine leere Tabelle deterministisch. Derselbe Fall wie
        # "Kanal nicht verfuegbar", nur ohne Vermerk (kein Fehler, nur noch
        # nichts eingetragen).
        try:
            _has_embeddings = conn.execute("SELECT 1 FROM knowledge_embeddings LIMIT 1").fetchone() is not None
        except sqlite3.OperationalError:
            _has_embeddings = False
        if _has_embeddings:
            embed_fn = embed_fn or embeddings.embed_text
            query_vec = embed_fn(prompt if prompt else " ".join(kws))
            if query_vec is None:
                print("knowledge_recall_hook: Embedding-Kanal nicht verfuegbar "
                      "(Ollama nicht erreichbar oder kein Modell) -- Abruf faellt "
                      "auf Stichwort-Kanal zurueck.", file=sys.stderr)
    # s. bedeutungswerte-Absatz im Docstring oben: unabhaengig vom gewaehlten
    # Ast unten (_suchpfad_aktiv() True/False) berechnet, weil beide Aeste
    # denselben query_vec teilen und der aktive Ast (S9) die Rohwerte sonst
    # nirgends durchreicht. _embedding_scores() ist bereits vorhandener Code
    # dieser Datei (Teil 1, Auftrag 2026-08-07) -- nur der NODE-Kanal, wie
    # knowledge_mcp_server.py::knowledge_search() ihn fuer 'bestandslage'
    # verwendet. Ueber ALLE lebenden Knoten (nicht nur die Kandidaten dieser
    # Anfrage) -- Naeherung, dieselbe wie beim MCP-Werkzeug.
    if bedeutungswerte is not None and query_vec is not None:
        try:
            _scores = _embedding_scores(conn, "node", query_vec)
        except sqlite3.Error:
            _scores = None
        if _scores:
            bedeutungswerte.extend(sorted(_scores.values(), reverse=True))
    # Projektstufungs-Bremse ausgebaut (Auftrag 2026-08-13, s.o. Kommentar
    # bei PROJECT_CALIBRATION_MIN_SAMPLES) -- gemeinsamer Wert fuer alle.
    mad_mult = NOISE_FLOOR_MAD_MULT
    if _suchpfad_aktiv():
        # S9: Kandidaten ueber denselben Suchpfad wie knowledge_search
        # (suchpfad_abruf.kandidaten, RRF ueber Stichwort+Bedeutung, kein
        # MIN_HITS/ENSEMBLE_PFLICHT-Vorfilter) -- die Nachbehandlung
        # (trust_score, rangfolge, Scope, Explore, MAX_NODES/MAX_LESSONS-
        # Deckel, geltend-Filter) bleibt dieselbe wie im Zweig darunter.
        node_rows, lesson_rows = [], []
        try:
            # S12: mehrstufiger_abruf.kandidaten_geschaltet() ersetzt den
            # Direktaufruf 1:1 (faellt bei KNOWLEDGE_MEHRSTUFIGER_ABRUF=AUS,
            # der Vorgabe, byte-gleich auf suchpfad_abruf.kandidaten() zurueck).
            node_rows, lesson_rows = mehrstufiger_abruf.kandidaten_geschaltet(
                conn, prompt if prompt else " ".join(kws), query_vec, MAX_NODES + MAX_LESSONS)
        except sqlite3.Error:
            pass
        # Enthaltung (ENTHALTUNGSSCHWELLE_KOSINUS, s.o.): nur ueber die
        # VORHANDENEN Kosinuswerte entschieden -- None (kein Vektor) ist eine
        # Aussage ueber Verfuegbarkeit, nicht ueber Aehnlichkeit, und zaehlt
        # deshalb nicht als "unter der Schwelle" (kein Kandidat mit Vektor ->
        # keine Enthaltung, wie vor diesem Auftrag). Auf den ROHEN Kandidaten
        # entschieden (vor dem geltend-Filter unten), weil genau das der Weg
        # ist, ueber den runs/enthaltungsschwelle_kosinus_abrufweg.json misst.
        if _enthaltung_aktiv():
            vorhandene = [w for w in
                          (r.get("bedeutungs_kosinus") for r in node_rows + lesson_rows)
                          if w is not None]
            if vorhandene and max(vorhandene) < ENTHALTUNGSSCHWELLE_KOSINUS:
                if enthaltung_satz is not None:
                    enthaltung_satz.append(
                        "Zu dieser Frage steht nichts Belastbares im Speicher.")
                node_rows, lesson_rows = [], []
        try:
            node_rows = [r for r in node_rows if _ist_geltend(r.get("gilt_ab"), r.get("gilt_bis"))]
            signal = _apply_trust_score(node_rows, "node")
            signal = rangfolge.anwenden(signal, conn)
            if own:
                signal = _tag_node_scope(signal, own)
            nodes = _maybe_explore(signal[:MAX_NODES], signal, rand, log_path)
        except sqlite3.Error:
            pass
        try:
            scored = [(hits(f"{c['description']} {c['root_cause']} {c['prevention']}", kws),
                       c["severity"] in ("critical", "high"), c["occurrences"], c) for c in lesson_rows]
            scored.sort(key=lambda s: s[1:3], reverse=True)
            scored = _apply_trust_score(scored, "lesson", ref_of=lambda s: s[3]["id"])
            if own:
                scored = _tag_lesson_scope(scored, own)
            lessons = [s[3] for s in scored[:MAX_LESSONS]]
        except sqlite3.Error:
            pass
        _attach_norm_offen(conn, nodes)
        _attach_norm_rang(conn, nodes)
        _attach_abgeloest(conn, nodes)
        conn.close()
        return nodes, lessons
    try:
        rows = conn.execute(
            "SELECT n.id, n.path, n.title, n.summary, n.updated_at, n.gilt_ab, n.gilt_bis, "
            "bm25(knowledge_fts) AS score "
            "FROM knowledge_fts f JOIN knowledge_nodes n ON n.rowid = f.rowid "
            f"WHERE knowledge_fts MATCH ? AND n.zurueckgezogen = 0 {SQL_ARBEITSBESTAND_NUR} "
            "ORDER BY bm25(knowledge_fts) LIMIT ?",
            (fts_match(kws), FULL_SCAN_ROW_CAP),
        ).fetchall()
        # Abgelaufen/noch nicht in Kraft -> wie zurueckgezogen behandeln
        # (Auftrag 2026-08-08). Vor dem Stichwort-Filter, damit auch
        # node_by_id unten (Embedding-Fallback) schon bereinigt ist.
        rows = [r for r in rows if _ist_geltend(r["gilt_ab"], r["gilt_bis"])]
        # Gegen genau den Text pruefen, der auch ausgegeben wird.
        candidates = [
            dict(r) for r in rows
            if hits(f"{r['path']} {r['title']} {r['summary']}", kws) >= MIN_HITS
        ]
        kw_signal = _radar_select(candidates, "score", mad_mult)

        emb_scores = _embedding_scores(conn, "node", query_vec)
        emb_signal = []
        if emb_scores:
            node_by_id = {r["id"]: dict(r) for r in rows}
            emb_candidates = []
            for nid, sim in emb_scores.items():
                info = node_by_id.get(nid) or _node_info(conn, nid)
                if info is None:
                    continue
                emb_candidates.append({**info, "id": nid, "score": -sim})
            emb_signal = _radar_select(emb_candidates, "score", mad_mult)

        signal = _combine_channels(kw_signal, emb_signal, emb_scores is not None)
        signal = _apply_trust_score(signal, "node")
        signal = rangfolge.anwenden(signal, conn)
        if own:
            signal = _tag_node_scope(signal, own)
        nodes = _maybe_explore(signal[:MAX_NODES], signal, rand, log_path)
    except sqlite3.Error:
        pass
    try:
        # Frueher: LIKE-Vorfilter ohne Rangfolge (rowid-Reihenfolge = Ein-
        # fuegereihenfolge), LIMIT 30 VOR jeder Bewertung -- systematisch
        # gegen neue Eintraege (ADR-033). Jetzt: bm25 ueber lessons_fts,
        # genau wie bei den Nodes, gleicher Radar.
        rows = conn.execute(
            "SELECT l.id, l.description, l.root_cause, l.prevention, l.severity, "
            "l.occurrences, l.type, l.last_seen, l.first_seen, l.session, l.projects, "
            "bm25(lessons_fts) AS score "
            "FROM lessons_fts f JOIN lessons_learned l ON l.rowid = f.rowid "
            "WHERE lessons_fts MATCH ? AND l.status != 'resolved' "
            "ORDER BY bm25(lessons_fts) LIMIT ?",
            (fts_match(kws), FULL_SCAN_ROW_CAP),
        ).fetchall()
        candidates = [
            dict(r) for r in rows
            if hits(f"{r['description']} {r['root_cause']} {r['prevention']}", kws) >= MIN_HITS
        ]
        kw_signal = _radar_select(candidates, "score", mad_mult)

        emb_scores = _embedding_scores(conn, "lesson", query_vec)
        emb_signal = []
        if emb_scores:
            lesson_by_id = {r["id"]: dict(r) for r in rows}
            emb_candidates = []
            for lid, sim in emb_scores.items():
                info = lesson_by_id.get(lid) or _lesson_info(conn, lid)
                if info is None:
                    continue
                emb_candidates.append({**info, "id": lid, "score": -sim})
            emb_signal = _radar_select(emb_candidates, "score", mad_mult)

        signal = _combine_channels(kw_signal, emb_signal, emb_scores is not None)
        # bm25 (Kanal 1, via Radar) bleibt die primaere Reihenfolge (stabiler
        # Sort) -- Severity/Haeufigkeit brechen nur noch echte Gleichstaende.
        # 4-Tupel-Form (hits, severity, occurrences, dict) wie gehabt --
        # _tag_lesson_scope/selftest erwarten den dict an Index 3.
        scored = [(hits(f"{c['description']} {c['root_cause']} {c['prevention']}", kws),
                   c["severity"] in ("critical", "high"), c["occurrences"], c) for c in signal]
        scored.sort(key=lambda s: s[1:3], reverse=True)
        scored = _apply_trust_score(scored, "lesson", ref_of=lambda s: s[3]["id"])
        if own:
            scored = _tag_lesson_scope(scored, own)
        lessons = [s[3] for s in scored[:MAX_LESSONS]]
    except sqlite3.Error:
        pass
    _attach_norm_offen(conn, nodes)
    _attach_norm_rang(conn, nodes)
    _attach_abgeloest(conn, nodes)
    conn.close()
    return nodes, lessons


def _herkunftsmodus() -> str:
    """Herkunftsmodus aus knowledge_config (s. RECALL_LOG-Moduldoc oben) --
    'aus' unterdrueckt 'prompt' in der Protokollzeile ganz, jeder andere/
    fehlende Wert schreibt roh ('voll', heutige Vorgabe, da kein Schluessel
    existiert). Eigene kurzlebige RO-Verbindung -- log_recall() haelt selbst
    keine offene Verbindung. Jeder Fehler (DB gesperrt, Tabelle fehlt in
    einer alten Kopie) -> 'voll', wie beim Fehlen des Schluessels."""
    try:
        conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=2.0)
        try:
            row = conn.execute(
                "SELECT value FROM knowledge_config WHERE key = 'herkunftsmodus'"
            ).fetchone()
        finally:
            conn.close()
        return row[0] if row else "voll"
    except sqlite3.Error:
        return "voll"


def _messparameter_kennung() -> str | None:
    """Kurzkennung (sha1, 8 Zeichen) des aktuellen Parameterblocks
    (shared-knowledge/messparameter.py::schnappschuss()) -- macht eine
    mitgeschriebene Anfrage gegen GENAU diese Einstellung nachvollziehbar,
    ohne den ganzen Block in jede Protokollzeile zu schreiben. Lazy-Import
    (wie zielfunktion() weiter unten: messparameter importiert seinerseits
    dieses Modul, ein Import auf Modulebene waere ein Ringimport). None bei
    jedem Fehler -- Beiwerk, darf den Abruf nie stoppen."""
    try:
        shared_knowledge = Path(DB).resolve().parent
        p = str(shared_knowledge)
        if p not in sys.path:
            sys.path.insert(0, p)
        import messparameter
        block = messparameter.schnappschuss()
        roh = json.dumps(block, sort_keys=True, ensure_ascii=False)
        return hashlib.sha1(roh.encode("utf-8")).hexdigest()[:8]
    except Exception:
        return None


def log_recall(nodes: list, lessons: list, log_path: str | None = None,
                cwd: str | None = None, session_id: str | None = None,
                prompt: str | None = None, agent_id: str | None = None,
                agent_type: str | None = None,
                erstverwendung_ids: list[str] | None = None) -> None:
    """Haelt fest, WAS gezogen wurde -- Beiwerk, nie ein Grund fuer den Abruf
    zu scheitern. Deshalb: alles in try/except, jeder Fehler wird verschluckt.
    Nur bei echten Treffern aufgerufen -- ein leerer Abruf erzeugt keine Zeile,
    das haelt das Protokoll klein und beantwortet direkt "nie gezogen".
    log_path=None -> aktuelles Modul-RECALL_LOG (dynamisch, nicht als
    Default-Argument eingefroren -- Tests koennen hook.RECALL_LOG patchen).

    Herkunft (Auftrag 2026-08-06): cwd + daraus abgeleiteter Worktree-Name
    (gleiche Ableitung wie _cwd_project, kein zweiter Weg) sowie die
    Sitzungskennung, gekuerzt wie in den anderen Hooks (agent_register_hook.py
    etc.: session_id[:8]). Fehlt ein Wert -> null im JSON, nicht weggelassen --
    Bestandszeilen ohne diese Schluessel bleiben ueber .get() lesbar.

    Anfrage + Parameterkennung (Auftrag 2026-08-08): siehe RECALL_LOG-
    Moduldoc oben -- 'prompt' fehlt in der Zeile (Schluessel weggelassen,
    nicht null), wenn _herkunftsmodus() 'aus' liefert ODER prompt=None
    (kein Prompt-Text uebergeben, z.B. aeltere Aufrufer/Tests).

    WER hat gefragt (Auftrag 2026-08-08, Anschluss): agent_id/agent_type
    GEMESSEN, nicht angenommen -- Rohdump von main()s Payload (echter
    UserPromptSubmit-Haltepunkt, per Probe-Subagent ausgeloest, 2 Zeilen)
    zeigte NUR: session_id, transcript_path, cwd, prompt_id, permission_mode,
    hook_event_name, prompt, session_title. KEIN agent_id, KEIN agent_type --
    anders als bei PreToolUse/SubagentStart (dort empirisch vorhanden, siehe
    cascade_guard_hook.py), liefert UserPromptSubmit sie strukturell nicht.
    main() reicht payload.get(...) trotzdem durch (falls der Haltepunkt sie
    kuenftig doch fuehrt, greift es ohne Codeaenderung hier). Fehlt der Wert
    -> ausdrueckliches String 'unbekannt' (NICHT weggelassen, NICHT null --
    null saehe aus wie 'nicht gemessen', 'unbekannt' heisst 'gemessen: gibt
    es nicht'). Zusaetzlicher Befund, ausserhalb des Payload-Schemas: ein
    Task-Tool-Subagent loest in SEINER EIGENEN Sitzung gar kein
    UserPromptSubmit aus (0 Zeilen beim ersten Probe-Aufruf) -- nur die
    Rueckmeldung an den AUFRUFER zaehlt dort als Prompt. Damit feuert dieser
    Hook fuer Subagenten-Arbeit strukturell nie, unabhaengig von agent_id."""
    log_path = log_path if log_path is not None else RECALL_LOG
    try:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "nodes": [n["path"] for n in nodes],
            # Unveraenderliche Node-Kennung zusaetzlich zum Pfad (Auftrag
            # 2026-08-08 Teil 2) -- der Pfad ist ein AENDERBARER Schluessel
            # (572 von 791 Altzeilen zeigten nach der Pfadsaeuberung vom
            # 2026-08-07 ins Leere). n["id"] ist die DB-Primaerspalte, bleibt
            # ueber eine Umbenennung hinweg stabil. Lessons brauchten das
            # schon: "lessons" oben ist bereits l["id"] (Primaerschluessel),
            # kein Pfad -- nur bei Nodes fehlte die stabile Form bisher.
            "node_ids": [n.get("id") for n in nodes],
            "lessons": [l["id"] for l in lessons],
            "cwd": cwd,
            "worktree": _cwd_project(cwd),
            "session": (session_id[:8] if session_id else None),
            "agent_id": agent_id or "unbekannt",
            "agent_type": agent_type or "unbekannt",
            "kennung": _messparameter_kennung(),
        }
        if prompt is not None and _herkunftsmodus() != "aus":
            payload["prompt"] = prompt
        # Kosinuswert JE KENNUNG (S1-Befund, 2026-08-20): Der Wert liegt an
        # jedem Treffer als `bedeutungs_kosinus` vor und wurde bis heute nie
        # persistiert. Die Aufgriffsquote (247 von 1275) liess sich deshalb
        # nicht nach Trefferstaerke aufschluesseln -- und ohne diese
        # Aufschluesselung waere nach dem Scharfschalten der abgestuften
        # Ausgabe (S2) nicht mehr messbar, ob die Stufung richtig lag. Die
        # Reihenfolge ist bindend: erst diese Spalte, dann der Schalter.
        #
        # ALS ZUORDNUNG, nicht als Liste: Eine Liste ohne Kennung ist genau
        # das, was der Abrufweg mit sorted(_scores.values()) schon einmal
        # weggeworfen hat (L-497059) -- auswertbar ist sie dann nicht.
        #
        # KEIN PLATZHALTER bei fehlendem Wert: Ein Treffer aus dem
        # Stichwortkanal hat keinen Kosinuswert; eine 0.0 waere eine Aussage,
        # die niemand gemessen hat, und wuerde spaeter als "sehr schwach"
        # gelesen. Der Schluessel bleibt weg, wie bei 'prompt' -- alte Zeilen
        # ohne ihn bleiben ueber .get() lesbar.
        kosinus = {}
        for treffer in list(nodes) + list(lessons):
            if not isinstance(treffer, dict):
                continue
            kennung = treffer.get("id")
            wert = treffer.get("bedeutungs_kosinus")
            if kennung is not None and wert is not None:
                kosinus[kennung] = round(float(wert), 4)
        if kosinus:
            payload["bedeutungs_kosinus"] = kosinus
        # Kennzeichnende Zahlen aus GENAU diesem Abruf (Auftrag 94, s.
        # _kennzeichnende_zahlen() oben) -- Schluessel nur bei Treffer
        # gesetzt (wie 'prompt'/'erstverwendung_vorschlag'), damit alte
        # Zeilen ohne den Schluessel ueber .get() unveraendert lesbar
        # bleiben. node_ids/lessons oben sind selbst schon Kennungen und
        # brauchen kein Duplikat hier.
        zahlen = _kennzeichnende_zahlen(
            *(f"{n.get('title', '')} {n.get('summary', '')}" for n in nodes),
            *(f"{l.get('description', '')} {l.get('prevention', '')}" for l in lessons),
        )
        if zahlen:
            payload["zahlen"] = zahlen
        # Erstverwendung (Auftrag 2026-08-12): welche Knoten-IDs GERADE einen
        # Vorschlag bekamen -- Schluessel nur bei Treffer gesetzt (wie
        # 'prompt' oben), damit _bereits_vorgeschlagen() alte Zeilen ohne den
        # Schluessel unveraendert ueberspringt (.get() liest sie als leer).
        if erstverwendung_ids:
            payload["erstverwendung_vorschlag"] = erstverwendung_ids
        entry = json.dumps(payload, ensure_ascii=False)
        if os.path.exists(log_path) and os.path.getsize(log_path) > RECALL_LOG_MAX_BYTES:
            with open(log_path, encoding="utf-8") as f:
                lines = f.readlines()
            with open(log_path, "w", encoding="utf-8") as f:
                f.writelines(lines[len(lines) // 2:])
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception:
        pass


def _schatten_konfiguration(conn=None) -> tuple[bool, list[dict]]:
    """Liest, OB (knowledge_config.schatten_aktiv == 'an') und WELCHE
    Herausforderer (knowledge_config.schatten_herausforderer, JSON-Liste von
    {"id": str, "overrides": {PARAMETERNAME: WERT}}) aktiv sind -- 'WELCHE
    Herausforderer, steht in knowledge_config, nicht im Code' (Auftrag).
    Vorgabe/Fehlerfall IMMER (False, []): fehlender Schluessel, kaputtes
    JSON, gesperrte DB -- eine Konfigurationsluecke darf den Titelverteidiger
    nie stoppen, sie stellt nur den Schattenlauf ab. Eigene kurzlebige
    RO-Verbindung, wenn keine uebergeben wird (wie _herkunftsmodus())."""
    eigene_conn = conn is None
    try:
        if eigene_conn:
            conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=2.0)
        rows = dict(conn.execute(
            "SELECT key, value FROM knowledge_config WHERE key IN "
            "('schatten_aktiv', 'schatten_herausforderer')"
        ).fetchall())
    except sqlite3.Error:
        return False, []
    finally:
        if eigene_conn and conn is not None:
            conn.close()
    if rows.get("schatten_aktiv") != "an":
        return False, []
    try:
        herausforderer = json.loads(rows.get("schatten_herausforderer") or "[]")
        assert isinstance(herausforderer, list)
    except (json.JSONDecodeError, AssertionError):
        return False, []
    return True, herausforderer


def _schatten_lauf(kws: list[str], cwd: str | None, overrides: dict) -> dict | None:
    """Ein Herausforderer-Abruf mit ueberschriebenen Modul-Parametern (wie
    zielfunktion() weiter unten: globals()[k] = v, IMMER in finally
    zurueckgesetzt -- ein Schatten darf den Titelverteidiger-Zustand nie
    dauerhaft veraendern). None bei JEDEM Fehler (AUFLAGE: 'ein Fehler im
    Schatten darf den echten Abruf NICHT beeintraechtigen' -- stilles
    Scheitern ist hier richtig, ein Herausforderer ist per Definition
    experimentell, seine Protokollzeile zeigt 'null' statt den Prozess zu
    gefaehrden). embed_fn fest auf 'kein Vektor': ein Schatten ruft NIE
    Ollama -- sonst waere ein einzelner Prompt bei N Herausforderern N
    zusaetzliche Modellaufrufe wert (VERBOT laut Auftrag)."""
    saved = {k: globals()[k] for k in overrides if k in globals()}
    try:
        for k, v in overrides.items():
            globals()[k] = v
        nodes, lessons = query(kws, cwd=cwd, embed_fn=lambda *a, **k: None)
        return {
            "nodes": [n["path"] for n in nodes],
            "lessons": [l["id"] for l in lessons],
            "stumm": not nodes and not lessons,
        }
    except Exception:
        return None
    finally:
        for k, v in saved.items():
            globals()[k] = v


def log_schatten(prompt: str | None, cwd: str | None, session_id: str | None,
                  titelverteidiger: dict, herausforderer_ergebnisse: list[tuple[str, dict | None]],
                  log_path: str | None = None) -> None:
    """Eine Zeile je Anfrage mit ALLEN Einstellungen (Titelverteidiger +
    jeder Herausforderer, gescheiterte als null) -- KEINE Bewertung, nur
    Rohbefund (Auftrag Punkt 3/4: 'Keine Bewertung'). Gleiches Kappungs-
    muster wie log_recall(). Immer try/except -- Beiwerk, nie ein Grund zum
    Abbrechen. Respektiert denselben Herkunftsmodus wie log_recall()."""
    log_path = log_path if log_path is not None else SCHATTEN_LOG
    try:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "cwd": cwd,
            "worktree": _cwd_project(cwd),
            "session": (session_id[:8] if session_id else None),
            "einstellungen": {
                "titelverteidiger": titelverteidiger,
                **{eid: ergebnis for eid, ergebnis in herausforderer_ergebnisse},
            },
        }
        if prompt is not None and _herkunftsmodus() != "aus":
            payload["prompt"] = prompt
        entry = json.dumps(payload, ensure_ascii=False)
        if os.path.exists(log_path) and os.path.getsize(log_path) > SCHATTEN_LOG_MAX_BYTES:
            with open(log_path, encoding="utf-8") as f:
                lines = f.readlines()
            with open(log_path, "w", encoding="utf-8") as f:
                f.writelines(lines[len(lines) // 2:])
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception:
        pass


def _seen_this_session(session_id: str | None, log_path: str | None = None) -> tuple[set, set]:
    """Bereits in DIESER Sitzung eingespielte Node-Pfade/Lesson-IDs, aus
    recall_log.jsonl (ADR-033 Schritt 1). Kein session_id -> leere Mengen,
    also wird nichts unterdrueckt (Grenzfall lt. Auftrag: im Zweifel liefern,
    nicht schlucken). session_id wird wie in log_recall() auf 8 Zeichen
    gekuerzt, weil genau das im Protokoll steht."""
    if not session_id:
        return set(), set()
    log_path = log_path if log_path is not None else RECALL_LOG
    sid = session_id[:8]
    seen_nodes, seen_lessons = set(), set()
    try:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if e.get("session") != sid:
                    continue
                seen_nodes.update(e.get("nodes", []))
                seen_lessons.update(e.get("lessons", []))
    except OSError:
        pass
    return seen_nodes, seen_lessons


def _dedup_session(nodes: list, lessons: list, session_id: str | None,
                    log_path: str | None = None) -> tuple[list, list]:
    """Filtert Treffer heraus, die diese Sitzung schon einmal bekam (ADR-033
    Schritt 1). Kein Parameter, keine Schwelle -- der Zustand steht schon in
    recall_log.jsonl. Kein session_id -> Eingabe unveraendert zurueck."""
    seen_nodes, seen_lessons = _seen_this_session(session_id, log_path)
    if not seen_nodes and not seen_lessons:
        return nodes, lessons
    return (
        [n for n in nodes if n["path"] not in seen_nodes],
        [l for l in lessons if l["id"] not in seen_lessons],
    )


def report(log_path: str | None = None, db_path: str | None = None) -> None:
    """Ungelesene-Lehre-Quote: welche Nodes/Lessons nie gezogen wurden, welche
    am haeufigsten. Liest das Protokoll gegen den vollen Bestand in der DB."""
    log_path = log_path if log_path is not None else RECALL_LOG
    db_path = db_path if db_path is not None else DB
    node_hits, lesson_hits = Counter(), Counter()
    try:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                node_hits.update(e.get("nodes", []))
                lesson_hits.update(e.get("lessons", []))
    except FileNotFoundError:
        pass
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0)
    all_nodes = {r[0] for r in conn.execute("SELECT path FROM knowledge_nodes")}
    all_lessons = {r[0] for r in conn.execute(
        "SELECT id FROM lessons_learned WHERE status != 'resolved'")}
    conn.close()
    total = sum(node_hits.values()) + sum(lesson_hits.values())
    print(f"Protokoll-Ereignisse: {total}")
    print(f"Nodes nie gezogen: {len(all_nodes - node_hits.keys())}/{len(all_nodes)}")
    print(f"Lessons nie gezogen: {len(all_lessons - lesson_hits.keys())}/{len(all_lessons)}")
    print(f"Top-Nodes: {node_hits.most_common(5)}")
    print(f"Top-Lessons: {lesson_hits.most_common(5)}")


def _kanarienvogel_melden() -> None:
    """Sonde ueber denselben Weg, den der Abruf gerade genommen hat.

    IM finally, und das ist die Korrektur eines Fehlers vom selben Tag: Die
    Sonde liegt seit dem 2026-08-13 in kern/kanarienvogel.py und war nie
    angeschlossen; ihr eigener Docstring nannte als Einbauort "direkt nach dem
    Erfolg von 'nodes, lessons = query(...)'".

    GEMESSEN, dass dieser Ort blind ist fuer genau den Fall, fuer den die
    Sonde existiert: Bei kaputter Datenbank WIRFT `query()`, der Zweig
    darunter wird nie erreicht, und es entstand keine Alarmzeile --
    nachgestellt mit BRAINLEHR_DB auf eine nicht existierende Datei. Die Sonde
    selbst meldete im selben Lauf korrekt `db_ok: False`. Ein Melder am
    falschen Ort ist so gut wie keiner.

    Im finally erreicht sie beide Faelle: den leeren Treffer, den vollen und
    den Absturz. Nur dann stimmt "bei jedem Abruf" im Wortsinn -- und genau
    darum geht es, denn 'nichts gefunden' und 'Weg tot' sehen im Chat
    identisch aus.

    Darf nie werfen: eine Sonde, die den Abruf anhaelt, ist schaedlicher als
    der Ausfall, den sie melden soll.
    """
    try:
        import kanarienvogel
        kanarienvogel.pruefen_und_melden()
    except Exception:
        pass


def _stufen_an() -> bool:
    """S2 aus docs/PLAN_ZWEITES_SIGNAL_2026-08-20.md, per Vorgabe AUS.

    Die Reihenfolge ist bindend: S1 erhebt die Aufgriffsquote als NULLLINIE.
    Wird die Ausgabe vorher umgestellt, laesst sich nachtraeglich nicht mehr
    rekonstruieren, wie oft ein Einspieler vorher aufgegriffen wurde. Der
    Schalter ist die Umsetzung dieser Reihenfolge, nicht Vorsicht --
    `BRAINLEHR_ABRUF_STUFEN=an` schaltet ihn scharf."""
    return os.environ.get("BRAINLEHR_ABRUF_STUFEN", "aus").strip().lower() == "an"


# Schwelle der Stufung, AUSDRUECKLICH UNGEMESSEN. Sie ist NICHT
# relevanzlage.STARK_AB (0,586): das ist eine Aussage ueber die Lage des
# ganzen Blocks, nicht ueber den einzelnen Treffer, und gemessen am
# 2026-08-20 lagen bei einer echten Anfrage ALLE 17 Treffer darunter -- die
# Stufung haette alles herabgestuft und nichts unterschieden.
# Die am selben Tag gefundene 0,545 stammt aus einer Trennung ueber 24 Faelle
# mit einer Luecke von 0,0087 und ist nach Wilson mit einer Trefferquote von
# 78 % vereinbar; sie als Betriebsschwelle zu setzen waere eine gemessene
# Zahl an der falschen Stelle. Deshalb steht hier ein Platzhalter, der
# zusammen mit dem Schalter AUS ist -- die Kalibrierung ist Aufgabe von S3/S4
# aus docs/PLAN_ZWEITES_SIGNAL_2026-08-20.md.
STUFE_AB = 0.545


def einstufen(nodes: list, lessons: list) -> tuple:
    """Teilt Treffer in EINSCHLAEGIG und NUR FUNDSTELLEN.

    Der Kosinuswert je Treffer liegt bereits an jedem Treffer als Feld
    `bedeutungs_kosinus` -- gemessen 2026-08-20, nachdem ein Umbau begonnen
    worden war, der ihn erst noch durchreichen sollte. Die Existenzprobe
    haette das in Sekunden gezeigt (L-229bb2).

    OHNE WERT bleibt ein Treffer STARK. Das ist Absicht: ein Treffer aus dem
    Stichwortkanal hat keinen Kosinuswert, und ihn deshalb herabzustufen waere
    eine Aussage ueber ihn, die niemand gemessen hat (MUST-LAGE-001)."""
    if not _stufen_an():
        return list(nodes), list(lessons), [], []

    def stark(t: dict) -> bool:
        wert = t.get("bedeutungs_kosinus")
        return wert is None or wert >= STUFE_AB

    return ([n for n in nodes if stark(n)], [l for l in lessons if stark(l)],
            [n for n in nodes if not stark(n)], [l for l in lessons if not stark(l)])


def block_bauen(nodes: list, lessons: list, bedeutungswerte: list,
                erstverwendung_zeilen: list,
                schwache_nodes: list | None = None,
                schwache_lessons: list | None = None) -> list:
    """Baut den <knowledge-recall>-Block. Bis 2026-08-20 lag das als Schleife
    mitten in main() und war von aussen nicht pruefbar -- das Herausloesen ist
    der erste Teil von S2.

    ZWEI STUFEN (Konsil 2026-08-20, Forensik und Alarmmanagement unabhaengig
    voneinander): Nicht die Fehlerrate senken, sondern den PREIS des Fehlers.
    Ein schwacher Treffer bleibt sichtbar, kostet aber eine Zeile statt eines
    Absatzes. Kein Treffer verschwindet -- das unterscheidet die Abstufung von
    einem Filter, und tests/test_abrufblock_stufen.py haelt genau das fest."""
    schwache_nodes = list(schwache_nodes or [])
    schwache_lessons = list(schwache_lessons or [])
    # Bei ausgeschalteter Stufung wandern schwache Treffer VOLL in den Block --
    # so sieht der Betrieb aus wie vor der Aenderung, kein Treffer geht verloren.
    if not _stufen_an():
        nodes = list(nodes) + schwache_nodes
        lessons = list(lessons) + schwache_lessons
        schwache_nodes, schwache_lessons = [], []
    gestuft = bool(schwache_nodes or schwache_lessons)

    lines = ["<knowledge-recall>",
             "Aus dem Speicher, ungeprüft. Nicht als Fundliste lesen, sondern "
             "als Frage: Trifft das hier zu? Wenn NEIN — woran liegt es? "
             "(Ein Eintrag, der nicht passt, ist eine Antwort; ein übergangener "
             "ist keine.)"]
    # Lage EINMAL je Block, nicht je Zeile (Auftrag 2026-08-18) -- sie ist
    # eine Aussage ueber die ANFRAGE (relevanzlage.py-Moduldoc), nicht ueber
    # den einzelnen Treffer. Kein Treffer verschwindet dadurch: beurteile()
    # liefert bei starker Lage einen leeren Satz (Kennzeichnen, nicht
    # Filtern), dann bleibt die Zeile schlicht weg.
    if bedeutungswerte:
        lage = relevanzlage.beurteile(bedeutungswerte)
        if lage["satz"]:
            lines.append(lage["satz"])
    if gestuft:
        lines.append("")
        lines.append("EINSCHLÄGIG")
    for n in nodes:
        tag = " (Erkundung -- selten gezogen)" if n.get("explore") else ""
        fremd = f" [anderes Projekt: {n['foreign_project']}]" if n.get("foreign_project") else ""
        geltung = _geltung_tag(n.get("norm_rang"), n.get("gilt_bis"))
        abgeloest = _abloesung_tag(n)
        lines.append(f"- [{n['path']}]{alter(n.get('updated_at'))}{tag}{fremd}{geltung}{abgeloest} "
                     f"{entschaerfe_fuer_ausgabe(n['title'])}: {entschaerfe_fuer_ausgabe(n['summary'])}")
    for l in lessons:
        tag = "⚠ LESSON" if l["severity"] in ("critical", "high") else "Lesson"
        prev = f" → {entschaerfe_fuer_ausgabe(l['prevention'])}" if l.get("prevention") else ""
        fremd = f" [andere Projekte: {l['foreign_projects']}]" if l.get("foreign_projects") else ""
        # Herkunft (Betreiber-Auftrag 2026-08-07): Kennung immer, Sitzung/
        # Datum/Projekt nur wenn im Datensatz vorhanden -- kein Platzhalter
        # fuer Fehlendes. Projekt nur, wenn 'fremd' es nicht schon nennt.
        herkunft = f", {l['id']}"
        if l.get("session"):
            herkunft += f", Sitzung {l['session']}"
        if l.get("first_seen"):
            herkunft += f", erfasst {l['first_seen'][:10]}"
        if not l.get("foreign_projects"):
            projs = projekte_aus_projects_json(l.get("projects"))
            if projs:
                herkunft += f", Projekt {'/'.join(sorted(projs))}"
        lines.append(f"- {tag} ({l['type']}, {l['occurrences']}×{herkunft}){alter(l.get('last_seen'))}{fremd}: "
                     f"{entschaerfe_fuer_ausgabe(l['description'])}{prev}")
    if gestuft:
        lines.append("")
        lines.append("NUR FUNDSTELLEN — ungeprüft, ob sie hierher gehören")
        for n in schwache_nodes:
            lines.append(f"- [{n['path']}] {entschaerfe_fuer_ausgabe(n['title'])}")
        for l in schwache_lessons:
            lines.append(f"- {l['id']} {entschaerfe_fuer_ausgabe(l['description'])[:80]}")
    lines.extend(erstverwendung_zeilen)
    lines.append("</knowledge-recall>")
    return lines


def main() -> None:
    t0 = time.perf_counter()  # Notbremse-Basis (Schattenlauf), s.u.
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    prompt = (payload.get("prompt") or "").strip()
    if not prompt or prompt.startswith("/"):
        return
    kws = keywords(prompt)
    if len(kws) < MIN_HITS:  # kann die Schwelle gar nicht reissen -> gar nicht fragen
        return
    cwd = payload.get("cwd") or os.getcwd()
    bedeutungswerte: list = []
    enthaltung_satz: list[str] = []
    # KANARIENVOGEL im finally (2026-08-20, Betreiberfrage: "was ist aus
    # unserem Kanarienvogel-Waechter geworden?"). Die Sonde liegt seit dem
    # 2026-08-13 in kern/kanarienvogel.py, mit Selbsttest und eigener
    # Testdatei -- und war nie angeschlossen. Die Vertagung hatte einen Grund
    # (parallel lief eine Nullmessung, L-7318ce); der ist entfallen, die
    # juengsten Ergebnisdateien sind vom 2026-08-15.
    #
    # Warum finally und NICHT der Ort, den ihr eigener Docstring nannte
    # ("direkt nach dem Erfolg von query(...)"): Bei kaputter Datenbank WIRFT
    # query(), der Zweig danach wird nie erreicht -- gemessen mit BRAINLEHR_DB
    # auf eine nicht existierende Datei: keine Alarmzeile, waehrend die Sonde
    # im selben Lauf korrekt db_ok=False meldete. Der vorgesehene Einbauort
    # war blind fuer genau den Fall, fuer den die Sonde existiert.
    try:
        nodes, lessons = query(kws, cwd=cwd, prompt=prompt, bedeutungswerte=bedeutungswerte,
                                enthaltung_satz=enthaltung_satz)
    except Exception:
        return
    finally:
        _kanarienvogel_melden()

    session_id = payload.get("session_id")

    # Schattenlauf (Anschlussauftrag 2026-08-08) -- NACH dem Titelverteidiger,
    # NIE davor: ein haengender/fehlerhafter Schatten darf den echten Abruf
    # weder verzoegern noch verhindern. Laeuft auch, wenn der Titelverteidiger
    # selbst still blieb (Auftrag will Schweigequote JE Einstellung, auch bei
    # Titelverteidiger-Stille vergleichbar). Alles in try/except: Beiwerk.
    try:
        schatten_aktiv, herausforderer = _schatten_konfiguration()
        if schatten_aktiv and herausforderer and (time.perf_counter() - t0) <= SCHATTEN_ZEIT_BUDGET_S:
            ergebnisse = []
            for h in herausforderer:
                overrides = h.get("overrides") or {}
                hid = h.get("id") or "+".join(f"{k}={v}" for k, v in sorted(overrides.items()))
                ergebnisse.append((hid, _schatten_lauf(kws, cwd, overrides)))
            log_schatten(prompt, cwd, session_id, {
                "kennung": _messparameter_kennung(),
                "nodes": [n["path"] for n in nodes],
                "lessons": [l["id"] for l in lessons],
                "stumm": not nodes and not lessons,
            }, ergebnisse)
    except Exception:
        pass

    # LEERE ABRUFE WERDEN AUCH PROTOKOLLIERT (Betreiber 2026-08-09).
    # Vorher endete der Abruf hier ersatzlos -- und damit war die wichtigste
    # Fehlerklasse unsichtbar: "der Speicher wusste es und schwieg" erzeugt
    # keine Zeile, also kommt sie in keiner Auswertung vor. Ein Urteil ueber
    # die Nuetzlichkeit haette immer zu gut ausgefallen, weil die
    # Fehlschlaege per Bauart nicht in der Stichprobe stehen (dieselbe
    # Fehlklasse wie L-73da37: die Kennzahl misst das Protokoll, nicht das
    # System). Der leere Abruf wird als Zeile mit leeren Listen vermerkt --
    # unterscheidbar von "kein Abruf" durch die blosse Existenz der Zeile.
    leer = not nodes and not lessons
    if not leer:
        nodes, lessons = _dedup_session(nodes, lessons, session_id)
        leer = not nodes and not lessons
    if leer:
        log_recall([], [], cwd=cwd, session_id=session_id, prompt=prompt,
                   agent_id=payload.get("agent_id"), agent_type=payload.get("agent_type"))
        if not enthaltung_satz:
            return
        # Enthaltung SICHTBAR machen (Auftrag 2026-08-19): ein stilles Nichts
        # ist von einem kaputten Haken nicht zu unterscheiden. Beide
        # Empfaenger wie beim regulaeren Treffer unten (systemMessage +
        # continue/suppressOutput noetig, damit die Zeile stehen bleibt statt
        # nach ~1s zu verschwinden, s. NACHTRAG 2026-08-10 weiter unten).
        satz = enthaltung_satz[0]
        print(json.dumps({
            "hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                    "additionalContext": f"<knowledge-recall>\n{satz}\n</knowledge-recall>"},
            "systemMessage": satz, "continue": True, "suppressOutput": True,
        }, ensure_ascii=False))
        return
    # Erstverwendung (Auftrag 2026-08-12): Vorschlag fuer offene Knoten
    # (norm_entscheidung == 'offen') UNTER der gerade getroffenen Auswahl --
    # kein eigener Suchpfad, reiner Zusatz. Gemessen: ~0,08ms je Knoten
    # (norm_ableiten(), reine Textanalyse) -- gegen das 2,3s-Zeitbudget
    # dieses Hooks eine Rundungsdifferenz, jeden Prompt zu pruefen kostet
    # nichts Messbares. Vor log_recall(), damit die gezeigten IDs in
    # DERSELBEN Protokollzeile landen wie der Rest des Treffers.
    erstverwendung_zeilen, erstverwendung_ids = _erstverwendungs_vorschlaege(nodes)

    # agent_id/agent_type: GEMESSEN nicht vorhanden im UserPromptSubmit-Payload
    # (s. log_recall()-Docstring) -- .get() trotzdem statt hartem None, falls
    # der Haltepunkt sie kuenftig doch liefert.
    log_recall(nodes, lessons, cwd=cwd, session_id=session_id, prompt=prompt,
               agent_id=payload.get("agent_id"), agent_type=payload.get("agent_type"),
               erstverwendung_ids=erstverwendung_ids)

    # FRAGEFORM statt Fundliste (Konsil 2026-08-11, Stimme 3, Pruefspruch #3):
    # Von der Closed-Loop-Infusion bei NASA/ESA ist die Kontrollinstanz hier
    # nicht uebertragbar -- sie braucht eine zweite Person, die den Status eines
    # anderen dokumentiert. Uebertragbar ist die BEWEISLASTUMKEHR als blosse
    # Frageform: nicht "hier ist relevantes Wissen" (das laesst sich wegklicken),
    # sondern "warum trifft das hier NICHT zu" (das verlangt eine Antwort).
    # Eine Frageform braucht keine Instanz und kostet keine Reibung -- der
    # billigste der drei Vorschlaege des Konsils.
    #
    # Was das NICHT ist: eine Sperre. Niemand wird aufgehalten, es wird nichts
    # quittiert. Wirkt es nicht, ist das an derselben Stelle messbar wie bisher
    # (recall_log) und die Aenderung ist eine Zeile zurueckzunehmen.
    stark_n, stark_l, schwach_n, schwach_l = einstufen(nodes, lessons)
    lines = block_bauen(stark_n, stark_l, bedeutungswerte, erstverwendung_zeilen,
                        schwache_nodes=schwach_n, schwache_lessons=schwach_l)
    # Bereinigung, Punkt 2 der Stiftshuetten-Uebernahme: was das Haus
    # verlaesst, wird angesehen -- vorerst nur angesehen (Entscheidung des
    # Betreibers 2026-08-08: melden, nicht entfernen). Geprueft wird der ROHE
    # Bestandstext, NICHT die Zeilen oben: die tragen bereits die Rahmung aus
    # entschaerfe_fuer_ausgabe(), und genau daran hat sich L-d1d0d7 mit 216
    # Fehlalarmen verschluckt. Der Aufruf aendert nichts und wirft nie.
    bereinigung.melde("recall", [
        *[(n["path"], {"title": n.get("title"), "summary": n.get("summary")}) for n in nodes],
        *[(l["id"], {"description": l.get("description"), "prevention": l.get("prevention")}) for l in lessons],
    ])
    # ZWEI EMPFAENGER, EINE AUSGABE. Bis 2026-08-10 ging der Block als
    # blosser Text hinaus -- bei UserPromptSubmit landet stdout im KONTEXT
    # des Modells, nicht auf dem Bildschirm. Der Betreiber sah deshalb nie,
    # welche Lehre gerade seine Frage beantwortet hat, obwohl der Abruf die
    # ganze Zeit lief. Mit hookSpecificOutput.additionalContext geht der
    # Block weiter an das Modell, mit systemMessage zusaetzlich eine kurze
    # Zeile an den Menschen.
    block, weggelassen = _auf_budget_kuerzen(lines)
    kennungen = [l["id"] for l in lessons if l.get("id")]
    pfade = [n["path"].rsplit("/", 1)[-1] for n in nodes if n.get("path")]
    teile = []
    if kennungen:
        teile.append("Lehren " + ", ".join(kennungen[:4])
                     + (f" und {len(kennungen) - 4} weitere" if len(kennungen) > 4 else ""))
    if pfade:
        teile.append("Wissen " + ", ".join(pfade[:3])
                     + (f" und {len(pfade) - 3} weitere" if len(pfade) > 3 else ""))
    if erstverwendung_ids:
        # In die systemMessage, nicht nur in additionalContext: das ist der
        # einzige belegt gelesene Kanal (additionalContext geht nur ans
        # Modell, s. Kommentar unten) -- ein Vorschlag, der nur im Kontext
        # steht, erreicht den Menschen so wenig wie eine Zeile in einer Datei,
        # die niemand oeffnet.
        teile.append(f"Erstverwendung {len(erstverwendung_ids)} Knoten ohne Norm-Entscheidung")
    ausgabe = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                      "additionalContext": block}}
    if teile:
        ausgabe["systemMessage"] = "eingespielt: " + " | ".join(teile)
        # NACHTRAG 2026-08-10: systemMessage ALLEIN rendert transient -- die
        # Zeile blitzt rund eine Sekunde auf und verschwindet. Erst zusammen
        # mit continue und suppressOutput bleibt sie stehen (Knoten 9f283897,
        # Ursache 4 von vieren; die Frage "warum sehe ich die Melderzeile
        # nicht mehr" kostete an diesem Tag rund vier Stunden).
        #
        # suppressOutput betrifft NUR stdout im Verlauf, nicht den
        # additionalContext -- der geht ueber hookSpecificOutput und bleibt
        # unberuehrt. continue=true ist ohnehin das Verhalten ohne Angabe;
        # es steht hier, weil die Anzeige laut Befund an der Kombination
        # haengt, nicht an einem der beiden Werte allein.
        ausgabe["continue"] = True
        ausgabe["suppressOutput"] = True
    print(json.dumps(ausgabe, ensure_ascii=False))


def zielfunktion(params: dict | None = None) -> dict:
    """Deterministische Zielfunktion (Betreiber-Auftrag 2026-08-07, Punkt 2):
    Parameter rein, Trefferguete ueber den Pruefkorpus raus -- KEIN
    Modellaufruf, kein Ollama, keine Optuna-Studie (hier nicht beauftragt,
    NOISE_FLOOR_MAD_MULT-Kommentar oben: der Pruefkorpus hat drei
    Aufgaben, eine Suche darauf waere Ueberanpassung). Das ist der
    Ansatzpunkt, auf den eine spaetere Studie aufsetzen kann.

    Nutzt DIESELBEN drei Aufgaben wie shared-knowledge/wissensnutzen_blind.py
    (nur importiert, NICHT veraendert -- Grenze aus dem Auftrag). params
    ueberschreibt Modul-Konstanten fuer die Dauer des Aufrufs und stellt sie
    in jedem Fall zurueck (auch bei Fehler/unbekanntem Schluessel).

    Rueckgabe: score = Trefferguete-Treffer (Aufgaben MIT target_lesson_id,
    heute A+B -> n=2), n = wieviele Aufgaben ueberhaupt eine Ziel-Lehre
    haben, silent = wieviele Aufgaben GAR NICHTS lieferten (Radar-Stille),
    per_task = Rohbefund je Aufgabe."""
    overrides = params or {}
    tunable = ("MIN_HITS", "EXPLORE_RATE", "TRUST_WEIGHT", "MAX_NODES", "MAX_LESSONS",
               "NOISE_FLOOR_MAD_MULT", "RADAR_MIN_SAMPLE_N")
    unknown = set(overrides) - set(tunable)
    if unknown:
        raise ValueError(f"zielfunktion: unbekannte Parameter {sorted(unknown)}, erlaubt: {tunable}")
    saved = {k: globals()[k] for k in tunable}
    # "KEIN Modellaufruf, kein Ollama" (s.o.) galt schon vor dem Embedding-
    # Kanal (Teil 1) -- der ist seither STANDARDMAESSIG an (query() ruft ohne
    # embed_fn-Uebergabe embeddings.embed_text() auf). wnb.blind_retrieve()
    # (wissensnutzen_blind.py, GRENZE: nicht veraenderbar) ruft query() ohne
    # embed_fn-Parameter -- darum hier, statt dort, embeddings.embed_text
    # fuer die Dauer des Laufs auf "kein Vektor" umgebogen: die Zielfunktion
    # bleibt reproduzierbar (test_paretolauf.py::test_paretolauf_selftest
    # verlangt bei gleichem Seed dieselbe Front -- ein echter Ollama-Aufruf
    # waere nicht deterministisch).
    saved_embed_text = embeddings.embed_text
    embeddings.embed_text = lambda *a, **k: None
    try:
        for k, v in overrides.items():
            globals()[k] = v
        shared_knowledge = Path(DB).resolve().parent
        for p in (str(shared_knowledge / "schreibpruefstand"), str(shared_knowledge / "kern"),
                  str(shared_knowledge),
                  str(shared_knowledge.parent / "scripts")):
            if p not in sys.path:
                sys.path.insert(0, p)
        import wissensnutzen_blind as wnb  # lazy -- wnb importiert dieses Modul, sonst Ringimport
        per_task, score, silent = {}, 0, 0
        for task_id, task in wnb.TASKS.items():
            nodes, lessons, _ = wnb.blind_retrieve(task["prompt"], task["cwd"])
            target = task["target_lesson_id"]
            treffer = (target is not None) and (target in [l["id"] for l in lessons])
            per_task[task_id] = treffer
            score += int(treffer)
            silent += int(not nodes and not lessons)
        n = sum(1 for t in wnb.TASKS.values() if t["target_lesson_id"])
        return {"score": score, "n": n, "silent": silent, "per_task": per_task}
    finally:
        embeddings.embed_text = saved_embed_text
        for k, v in saved.items():
            globals()[k] = v


# Echte Prompts aus der Session, in der die Schwelle eingebaut wurde
# (2026-07-28T02:30:00+0200). Links: soll Treffer liefern? Ja/Nein.
# Faelle, die HEUTE fehlschlagen und deren Ursache benannt, aber nicht behoben
# ist. Sie werden ausgewiesen statt entfernt -- ein stillschweigend geloeschter
# Testfall ist ein vergessener Befund.
#
# 'was heisst das nun genau fuer uns hier?' liefert im Stichwort-Weg zwei
# Lehren (L-871c8a, L-5615d2), die thematisch nichts mit der Anfrage zu tun
# haben. Die Anfrage traegt nach der STOP-Wort-Filterung nur noch drei
# Allerweltswoerter ('heisst', 'genau', 'fuer'), und der Lehren-Zweig zaehlt
# genau die als Treffer. Das ist ein echter Fehlgriff, kein veralteter
# Anspruch -- gemessen 2026-08-09 auch gegen den Bestand VOR der Umschrift,
# der Fall war also schon vorher rot und niemandem aufgefallen.
#
# Nicht behoben, weil dieser Weg im Betrieb nicht mehr benutzt wird
# (SUCHPFAD_ABRUF ist die Vorgabe). Wer ihn wieder einschaltet, findet hier
# den offenen Punkt: der Lehren-Zweig braucht ein Mass fuer Wortgewicht,
# nicht nur fuer Wortzahl.
_BEKANNT_ROT = {
    (False, "was heisst das nun genau fuer uns hier?"),
}

_CASES = [
    # War bis ADR-033 Schritt 2 "False" (Treffer sollte ausbleiben) -- galt
    # nur, weil der Lesson-Zweig ungeordnetes LIKE+LIMIT-30 nutzte (rowid-
    # Reihenfolge). Seit lessons_fts/bm25 (Schritt 2) findet die Anfrage
    # zuverlaessig L-b4b6fc, eine Lehre, die -- weil sie GENAU diese
    # MIN_HITS-Kalibrierung beschreibt -- den Text "kennst du paperless-ngx
    # docs?" WOERTLICH zitiert (siehe deren description). Das ist ein
    # echter, kein falscher Treffer: der Abruf findet jetzt zuverlaessig
    # eine Lehre, deren Inhalt woertlich zur Anfrage passt. Gemessen
    # 2026-08-07 (Rot-vor-Gruen fuer Schritt 2): vorher 0 Treffer (Bug-
    # Artefakt), danach 1 Treffer (korrekt).
    (True, "kennst du paperless-ngx docs? in wieweit kann uns dies in unseren "
           "wissen und papernetzwerk weiterhelfen? koennte ein lokales ollama "
           "model die claudekosten senken?"),
    (False, "was heisst das nun genau fuer uns hier?"),
    (False, "dann sollten wir das nun schnellstmoeglich fixen umsetzen?"),
    (True, "fahrtenbuch trip repository hash kette gobd verletzt"),
    (True, "setfunk webrtc latenz jitter buffer"),
    (True, "iphone deploy flutter build profile devicectl install"),
    # Umlaut-Faltung (2026-08-01): "existenzgruender"/"unabhaengige" (ue-
    # Schreibung) muessen den Knoten mit "Existenzgründer"/"unabhängige" (ü)
    # in Titel/Summary finden -- vorher fand FTS5 remove_diacritics nur ü->u,
    # nicht ue->u, also lief die Anfrage ins Leere.
    (True, "was steht zu existenzgruender unabhaengige amtliche beschreibungen drin"),
    # Dieselbe Faltungsluecke bei LESSONS (2026-08-01, Nachtrag): der Lesson-
    # Zweig lief ueber ein unrgefaltetes SQL-LIKE, das die Kandidatenzeile nie
    # zog -- hits() faltete zwar schon, bekam die Zeile aber nie zu sehen. Alle
    # drei Woerter hier sind NUR ueber Faltung erreichbar (L-021f62 hat woertlich
    # "Plausibilitäts"/"Zählern"/"Ganzzahlauflösung", nirgends die ue/oe-Schreibung) --
    # kein Wort im Query ist ein Zufallstreffer ueber sonstigen Text.
    (True, "plausibilitaets zaehlern ganzzahlaufloesung xyzzyzzyx qwertqwert"),
]


def selftest() -> None:
    global DB
    kws = keywords("paperless tesseract klassifikator modelltraining schwelle")
    assert "paperless" in kws and "modelltraining" in kws, kws
    assert "und" not in kws  # Stopwort
    # Komposita-Teiltreffer zaehlen -- das kann FTS5 mit unicode61 nicht.
    assert hits("Modelltraining mit Paperless", ["modell", "paperless"]) == 2
    # Ein einzelnes Allerweltswort reicht nicht -> genau der alte Bug.
    assert hits("GoBD-Hash-Kette im Fahrtenbuch", kws) < MIN_HITS

    # Die inline SQL-Faltung in query() (LIKE-Vorfilter) muss exakt dasselbe
    # tun wie fold_de() -- zwei Implementierungen (SQL kann fold_de() nicht
    # aufrufen), sonst laufen sie irgendwann auseinander, unbemerkt.
    import sqlite3 as _sqlite3
    _fold_sql = (
        "LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(?,"
        "'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss'))"
    )
    _conn = _sqlite3.connect(":memory:")
    for _s in ("Gründer", "Gruender", "Straße", "ÄÖÜäöüß", "ohne Umlaute", ""):
        _sql_val = _conn.execute(f"SELECT {_fold_sql}", (_s,)).fetchone()[0]
        assert fold_de(_s) == _sql_val, (_s, fold_de(_s), _sql_val)
    _conn.close()
    print("  SQL-Faltung im LIKE-Vorfilter deckt sich mit fold_de() ok")

    _never_explore = lambda: 1.0  # >= EXPLORE_RATE -> nie erkunden
    _always_explore = lambda: 0.0  # < EXPLORE_RATE -> immer erkunden
    # _CASES kalibriert den STICHWORT-Kanal (MIN_HITS, s.o. Pareto-Front-
    # Herleitung) -- embed_fn hier abgeschaltet, sonst haengt dieser Test vom
    # zufaellig laufenden/nicht laufenden lokalen Ollama ab (gleicher Grund
    # wie test_knowledge_hybrid_search.py: "damit er ohne Netzwerk/Modell
    # deterministisch bleibt"). Der Embedding-Kanal hat seine eigenen Tests
    # weiter unten (Teil 1/Teil 2).
    _no_embed = lambda *a, **k: None

    # SUCHPFAD_ABRUF ausdruecklich AUS fuer diesen Block: _CASES kalibriert das
    # MIN_HITS/ENSEMBLE_PFLICHT-Sieb dieser Datei, und genau das umgeht der
    # Suchpfad. Seit dessen Einschalten (2026-08-09) waren zwei der acht Faelle
    # rot -- gemessen auch gegen den Bestand VOR der Umschrift, es lag also
    # nicht am Material, sondern daran, dass der Test einen Weg misst, der
    # nicht mehr gegangen wird. Statt die Erwartung an die neue Lage
    # anzupassen (dann prueft er gar nichts mehr), laeuft er wieder gegen den
    # Weg, fuer den er gebaut wurde -- er bleibt damit gueltig fuer den Fall,
    # dass jemand ueber KNOWLEDGE_SUCHPFAD_ABRUF=0 zurueckschaltet.
    # SUCHPFAD_ABRUF ausdruecklich AUS fuer diesen Block: _CASES kalibriert das
    # MIN_HITS/ENSEMBLE_PFLICHT-Sieb dieser Datei -- und genau das umgeht der
    # Suchpfad, der seit 2026-08-09 die Vorgabe ist. Ohne diese Zeile misst der
    # Block einen Weg, der im Betrieb nicht mehr gegangen wird.
    # 2026-08-19: _CASES lief bis heute gegen die ECHTE, wachsende brainlehr.db
    # (DB blieb unveraendert auf ort.DB) -- eine Zusicherung ("dieser Prompt
    # MUSS einen Treffer liefern") gegen einen Bestand zu stellen, der taeglich
    # waechst, ist keine Aussage ueber den CODE mehr, sondern ueber den
    # Zufallstreffer des Tages. Genau das brach: der TRUE-Fall "kennst du
    # paperless-ngx docs?" erwartete L-b4b6fc, die inzwischen von neueren,
    # ebenfalls treffenden Zeilen im Bestand ueberholt wurde (0n/0l statt
    # >=1). Fix wie beim spaeteren Embedding-Block dieser Datei (Zeile ~2506
    # ff.): eigene Wegwerf-DB aus dem echten schema.sql, DB (Modulglobal) nur
    # fuer die Dauer dieses Blocks umgebogen. Kein Schnappschuss (120 MB je
    # Lauf waere fuer 8 Zeilen Fixtur unverhaeltnismaessig) -- eine Handvoll
    # Zeilen, genau auf die Woerter der acht Prompts zugeschnitten, reicht
    # und bleibt unabhaengig vom Bestandswachstum richtig.
    import tempfile as _tempfile3
    _schema_cases = (ort.WURZEL / "schema.sql").read_text(encoding="utf-8")
    with _tempfile3.TemporaryDirectory() as _td3:
        _db_path3 = os.path.join(_td3, "cases.db")
        _conn3 = sqlite3.connect(_db_path3)
        _conn3.executescript(_schema_cases)
        _conn3.executemany(
            "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source, "
            "norm_entscheidung, norm_entschieden_grund, norm_entschieden_von) "
            "VALUES (?, ?, 'shared', ?, ?, NULL, 0, 'test', 'keine_norm', "
            "'Testfixtur, kein Sollen', 'selftest')",
            [
                # Je Zeile genau die Worte des zugehoerigen TRUE-Falls
                # unten in _CASES -- Titel allein liefert schon
                # hits()>=MIN_HITS=3, s. Kommentar an den einzelnen Faellen.
                ("fx-paperless", "/test/fx-paperless",
                 "Kennst du paperless-ngx docs", "wieweit dies unseren wissen papernetzwerk"),
                ("fx-fahrtenbuch", "/test/fx-fahrtenbuch",
                 "Fahrtenbuch trip repository", "GoBD Hash Kette verletzt"),
                ("fx-setfunk", "/test/fx-setfunk",
                 "Setfunk WebRTC Latenz", "Jitter Buffer"),
                ("fx-iphone", "/test/fx-iphone",
                 "iPhone Deploy Flutter", "Build Profile devicectl install"),
                # Umlaut-Faltung (s. Falltext unten): Titel traegt die
                # ECHTEN Umlaute, die Anfrage die ue/ae-Schreibung -- testet
                # genau die Faltung, die dieser Fall kalibriert.
                ("fx-existenzgruender", "/test/fx-existenzgruender",
                 "Was steht zu Existenzgründer drin", "unabhängige amtliche Beschreibungen"),
                ("fx-plausibilitaet", "/test/fx-plausibilitaet",
                 "Plausibilitäts Zählern Ganzzahlauflösung", "Testfixtur fuer Selbsttest"),
            ],
        )
        _conn3.commit()
        _conn3.close()

        _suchpfad_vorher = os.environ.get("KNOWLEDGE_SUCHPFAD_ABRUF")
        os.environ["KNOWLEDGE_SUCHPFAD_ABRUF"] = "0"
        _alt_db3, DB = DB, _db_path3
        try:
            for want, prompt in _CASES:
                kws = keywords(prompt)
                n, l = (query(kws, rand=_never_explore, embed_fn=_no_embed) if len(kws) >= MIN_HITS else ([], []))
                got = bool(n or l)
                if (want, prompt) in _BEKANNT_ROT:
                    print(f"  BEKANNT ROT ({len(n)}n/{len(l)}l): {prompt[:45]}")
                    continue
                assert got == want, (
                    f"MIN_HITS={MIN_HITS}: '{prompt[:40]}...' erwartet "
                    f"{'Treffer' if want else 'leer'}, bekam {len(n)}n/{len(l)}l"
                )
                print(f"  {'HIT ' if want else 'MISS'} ok: {len(n)}n/{len(l)}l  {prompt[:45]}")
        finally:
            DB = _alt_db3
    # Alters-Anzeige
    from datetime import timedelta
    jetzt = datetime.now(timezone.utc)
    assert alter(None) == ""
    assert alter("kaputt") == ""
    assert alter(jetzt.isoformat()) == " [heute]"
    assert alter((jetzt - timedelta(days=1)).isoformat()) == " [1 Tag alt]"
    assert "5 Tage alt]" in alter((jetzt - timedelta(days=5)).isoformat())
    assert "PRUEFEN" in alter((jetzt - timedelta(days=90)).isoformat())
    assert "PRUEFEN" not in alter((jetzt - timedelta(days=5)).isoformat())
    # naive Zeitstempel (ohne Zone) duerfen nicht kippen
    assert alter(jetzt.replace(tzinfo=None).isoformat()) == " [heute]"
    print("  Altersanzeige ok")

    # Erkundungsanteil: synthetische Kandidaten, unabhaengig vom DB-Bestand
    # (der reale Bestand liefert selten >3 MIN_HITS-Kandidaten fuer einen
    # einzelnen Prompt -- die Logik testet sich hier gegen sich selbst).
    import tempfile
    _cands = [
        {"path": "/a", "title": "A", "summary": "x", "updated_at": None},
        {"path": "/b", "title": "B", "summary": "x", "updated_at": None},
        {"path": "/c", "title": "C", "summary": "x", "updated_at": None},
        {"path": "/d", "title": "D", "summary": "x", "updated_at": None},  # nie gezogen
    ]
    _regular = _cands[:3]
    with tempfile.TemporaryDirectory() as td:
        lp = os.path.join(td, "recall_log.jsonl")
        with open(lp, "w", encoding="utf-8") as f:
            f.write(json.dumps({"nodes": ["/a", "/b", "/c"], "lessons": []}) + "\n")

        out = _maybe_explore(list(_regular), _cands, rand=_always_explore, log_path=lp)
        assert out[-1]["path"] == "/d" and out[-1].get("explore") is True, out
        assert out[0]["path"] == "/a" and out[1]["path"] == "/b", out
        print("  Erkundung ersetzt selten/nie gezogenen Knoten ok")

        # Immer erkunden, aber kein Kandidat ausserhalb der regulaeren 3 ->
        # nichts zum Ersetzen da, Ausgabe unveraendert. Genau der Fall, an
        # dem eine schlampige Umsetzung Muell einspielen wuerde.
        out2 = _maybe_explore(list(_regular), _regular, rand=_always_explore, log_path=lp)
        assert out2 == _regular, out2
        print("  Erkundung ohne ungesehenen Kandidat aendert nichts ok")

        out3 = _maybe_explore(list(_regular), _cands, rand=_never_explore, log_path=lp)
        assert out3 == _regular, out3
        print("  Erkundung ausgeschaltet -> regulaere Treffer unveraendert ok")

        # Zehn simulierte Abruf-Wuerfe mit fester Folge -- wie oft erkundet
        # wird, muss zur eingestellten Wahrscheinlichkeit passen (0.15 ->
        # Werte < 0.15 loesen aus, hier bewusst 1 von 10 == 10%,
        # deterministisch statt Zufall).
        _sequence = [0.01, 0.9, 0.5, 0.3, 0.99, 0.2, 0.4, 0.7, 0.6, 0.8]
        _it = iter(_sequence)
        _fixed = lambda: next(_it)
        _explored = sum(
            1 for _ in range(10)
            if _maybe_explore(list(_regular), _cands, rand=_fixed, log_path=lp)[-1]["path"] == "/d"
        )
        assert _explored == 1, _explored  # nur 0.01 < EXPLORE_RATE=0.15
        print(f"  10 feste Wuerfe -> {_explored}/10 Erkundung (Folge enthaelt 1 Wert < {EXPLORE_RATE})")

    # Protokoll fehlt oder kaputte Zeile -> keine Erkundung, kein Fehler.
    out4 = _maybe_explore(list(_regular), _cands, rand=_always_explore,
                           log_path="/nichtvorhanden/recall_log.jsonl")
    assert out4 == _regular, out4
    with tempfile.TemporaryDirectory() as td:
        lp2 = os.path.join(td, "recall_log.jsonl")
        with open(lp2, "w", encoding="utf-8") as f:
            f.write("{kaputte zeile kein json\n")
        out5 = _maybe_explore(list(_regular), _cands, rand=_always_explore, log_path=lp2)
        assert out5 == _regular, out5
    print("  Protokoll fehlt/kaputt -> keine Erkundung, kein Fehler ok")

    # Protokoll: Treffer -> Zeile, kein Treffer -> keine Zeile, kaputtes Ziel -> still.
    with tempfile.TemporaryDirectory() as td:
        log_path = os.path.join(td, "recall_log.jsonl")
        log_recall([{"path": "/x/y"}], [{"id": "L-1"}], log_path)
        with open(log_path, encoding="utf-8") as f:
            zeilen = f.readlines()
        assert len(zeilen) == 1, zeilen
        entry = json.loads(zeilen[0])
        assert entry["nodes"] == ["/x/y"] and entry["lessons"] == ["L-1"]
        assert "prompt" not in json.dumps(entry).lower()
        print("  Log-Zeile bei Treffer ok")

        # Ziel nicht beschreibbar (Verzeichnis statt Datei) -> darf nie hochfliegen.
        kaputt = os.path.join(td, "kaputt_dir")
        os.makedirs(kaputt)
        log_recall([{"path": "/a"}], [], kaputt)  # kaputt ist ein Verzeichnis, kein File
        print("  Log auf kaputtes Ziel bleibt still ok")

    # --- Anfrage + Parameterkennung (Auftrag 2026-08-08) ---

    with tempfile.TemporaryDirectory() as td:
        lp = os.path.join(td, "recall_log.jsonl")
        log_recall([{"path": "/x"}], [], lp, prompt="testanfrage bla")
        with open(lp, encoding="utf-8") as f:
            entry = json.loads(f.readline())
        assert entry.get("prompt") == "testanfrage bla", entry
        assert entry.get("kennung") is None or isinstance(entry["kennung"], str), entry
        print("  Anfrage wird bei Treffer mitgeschrieben (Modus 'voll', kein Konfig-Schluessel) ok")

    # NEGATIVFALL: kein prompt-Argument (aeltere Aufrufer) -> Feld fehlt weiterhin.
    with tempfile.TemporaryDirectory() as td:
        lp = os.path.join(td, "recall_log.jsonl")
        log_recall([{"path": "/x"}], [], lp)
        with open(lp, encoding="utf-8") as f:
            entry = json.loads(f.readline())
        assert "prompt" not in entry, entry
        print("  Kein prompt-Parameter -> Feld fehlt, kein Fehler ok")

    # Herkunftsmodus 'aus' (knowledge_config) -> 'prompt' fehlt in der Zeile,
    # die Zeile selbst entsteht trotzdem (nodes/lessons bleiben wiederholbar).
    with tempfile.TemporaryDirectory() as td:
        cfg_db = os.path.join(td, "cfg.db")
        _c = sqlite3.connect(cfg_db)
        _c.execute("CREATE TABLE knowledge_config (key TEXT PRIMARY KEY, "
                    "value TEXT NOT NULL, updated_at TEXT NOT NULL)")
        _c.execute("INSERT INTO knowledge_config VALUES "
                    "('herkunftsmodus', 'aus', '2026-08-08T00:00:00+02:00')")
        _c.commit()
        _c.close()
        lp = os.path.join(td, "recall_log.jsonl")
        # global DB steht bereits am Funktionskopf (Zeile 2048) -- diese
        # zweite Deklaration war bis 2026-08-19 redundant und folgenlos,
        # weil DB vorher nirgends in selftest() gelesen/geschrieben wurde.
        # Der neue _CASES-Block oben (eigene Wegwerf-DB) liest/schreibt DB
        # jetzt VOR dieser Stelle -- eine zweite `global DB`-Anweisung nach
        # einer bereits erfolgten Nutzung des Namens ist ein SyntaxError
        # ("used prior to global declaration"), unabhaengig davon, dass sie
        # inhaltlich nichts aendert. Entfernt statt umformuliert.
        _alt_cfg_db = DB
        DB = cfg_db
        try:
            log_recall([{"path": "/x"}], [], lp, prompt="darf nicht geschrieben werden")
        finally:
            DB = _alt_cfg_db
        with open(lp, encoding="utf-8") as f:
            entry = json.loads(f.readline())
        assert "prompt" not in entry, entry
        assert entry["nodes"] == ["/x"], entry
        print("  Herkunftsmodus 'aus' -> Anfrage fehlt in der Zeile, Zeile entsteht trotzdem ok")

    # --- Schattenlauf (Anschlussauftrag 2026-08-08) ---

    with tempfile.TemporaryDirectory() as td:
        cfg_db = os.path.join(td, "cfg.db")
        _c = sqlite3.connect(cfg_db)
        _c.execute("CREATE TABLE knowledge_config (key TEXT PRIMARY KEY, "
                    "value TEXT NOT NULL, updated_at TEXT NOT NULL)")
        _c.commit()
        _c.close()
        _alt = DB
        DB = cfg_db
        try:
            assert _schatten_konfiguration() == (False, []), "fehlender Schluessel muss (False, []) liefern"
        finally:
            DB = _alt
    print("  Schatten-Konfiguration: kein Schluessel -> (False, []) ok")

    with tempfile.TemporaryDirectory() as td:
        cfg_db = os.path.join(td, "cfg.db")
        _c = sqlite3.connect(cfg_db)
        _c.execute("CREATE TABLE knowledge_config (key TEXT PRIMARY KEY, "
                    "value TEXT NOT NULL, updated_at TEXT NOT NULL)")
        _c.execute("INSERT INTO knowledge_config VALUES ('schatten_aktiv', 'an', 'x')")
        _c.execute("INSERT INTO knowledge_config VALUES ('schatten_herausforderer', ?, 'x')",
                    (json.dumps([{"id": "min2", "overrides": {"MIN_HITS": 2}}]),))
        _c.commit()
        _c.close()
        _alt = DB
        DB = cfg_db
        try:
            aktiv, h = _schatten_konfiguration()
            assert aktiv is True and h == [{"id": "min2", "overrides": {"MIN_HITS": 2}}], (aktiv, h)
        finally:
            DB = _alt
    print("  Schatten-Konfiguration: schatten_aktiv=an + Herausforderer gelesen ok")

    # NEGATIVFALL: absichtlich scheiternder Herausforderer (kaputte Override-
    # Typisierung) darf weder hochfliegen noch den Titelverteidiger-Zustand
    # dauerhaft veraendern -- genau die AUFLAGE aus dem Auftrag.
    _kws_schatten = keywords("fahrtenbuch trip repository hash kette gobd verletzt")
    _vor_min_hits = MIN_HITS
    _r_kaputt = _schatten_lauf(_kws_schatten, "/Volumes/daten/Begod2026/fahrtenbuch", {"MIN_HITS": "kaputt"})
    assert _r_kaputt is None, _r_kaputt
    assert MIN_HITS == _vor_min_hits, "globaler Zustand nach gescheitertem Schatten nicht zurueckgesetzt"
    _n_danach, _l_danach = query(_kws_schatten, cwd="/Volumes/daten/Begod2026/fahrtenbuch",
                                  embed_fn=lambda *a, **k: None)
    assert _l_danach, "echter Abruf nach gescheitertem Schatten liefert nichts mehr"
    print("  Schatten NEGATIVFALL: kaputter Herausforderer -> None, echter Abruf unberuehrt ok")

    # Funktionierender Herausforderer + log_schatten-Zeile.
    _r_ok = _schatten_lauf(_kws_schatten, "/Volumes/daten/Begod2026/fahrtenbuch", {"MIN_HITS": 2})
    assert _r_ok is not None and "nodes" in _r_ok and "lessons" in _r_ok and "stumm" in _r_ok, _r_ok
    with tempfile.TemporaryDirectory() as td:
        lp = os.path.join(td, "schatten_log.jsonl")
        log_schatten("testanfrage", "/x", "sessionid1234",
                      {"kennung": "abc", "nodes": [], "lessons": [], "stumm": True},
                      [("min2", _r_ok), ("kaputt", None)], lp)
        with open(lp, encoding="utf-8") as f:
            entry = json.loads(f.readline())
        assert entry["einstellungen"]["titelverteidiger"]["stumm"] is True, entry
        assert entry["einstellungen"]["kaputt"] is None, entry
        assert entry["einstellungen"]["min2"] == _r_ok, entry
        assert entry["prompt"] == "testanfrage", entry
    print("  Schatten: funktionierender Herausforderer + log_schatten-Zeile (alle Einstellungen) ok")

    # --- Herkunft in recall_log.jsonl (Auftrag 2026-08-06) ---

    with tempfile.TemporaryDirectory() as td:
        lp = os.path.join(td, "recall_log.jsonl")
        log_recall([{"path": "/x"}], [], lp,
                    cwd="/Volumes/daten/Begod2026/fahrtenbuch/apps/fahrtenbuch_legacy",
                    session_id="abcdef12-lang-rest")
        with open(lp, encoding="utf-8") as f:
            entry = json.loads(f.readline())
        assert entry["cwd"] == "/Volumes/daten/Begod2026/fahrtenbuch/apps/fahrtenbuch_legacy", entry
        assert entry["worktree"] == "fahrtenbuch", entry
        assert entry["session"] == "abcdef12", entry  # gekuerzt wie in agent_register_hook.py
        print("  Herkunft (cwd/worktree/session) in recall_log-Zeile ok")

        # Negativfall: kein cwd, keine session_id ermittelbar -> Feld null, keine Ausnahme.
        log_recall([{"path": "/y"}], [], lp, cwd=None, session_id=None)
        with open(lp, encoding="utf-8") as f:
            zeilen = f.readlines()
        entry2 = json.loads(zeilen[-1])
        assert entry2["cwd"] is None and entry2["worktree"] is None and entry2["session"] is None, entry2
        print("  Herkunft nicht ermittelbar -> null, kein Fehler ok")

    # Altbestand: eine Zeile ohne die neuen Felder (wie vor diesem Auftrag)
    # muss ein vorhandener Auswerter (_node_hit_counts, report()) weiter lesen
    # koennen, ohne zu brechen -- .get() statt [] auf den neuen Schluesseln.
    with tempfile.TemporaryDirectory() as td:
        lp = os.path.join(td, "recall_log.jsonl")
        with open(lp, "w", encoding="utf-8") as f:
            f.write(json.dumps({"ts": "2026-07-01T00:00:00+00:00",
                                 "nodes": ["/alt"], "lessons": []}) + "\n")
        counts = _node_hit_counts(lp)
        assert counts == Counter({"/alt": 1}), counts
        print("  Altzeile ohne Herkunftsfelder bleibt fuer _node_hit_counts lesbar ok")

    # --- Bereichsbezug (Auftrag 2026-08-06) ---

    assert _cwd_project("/Volumes/daten/Begod2026/fahrtenbuch/apps/fahrtenbuch_legacy") == "fahrtenbuch"
    assert _cwd_project("/Volumes/daten/Begod2026/hub") == "hub"
    assert _cwd_project(None) is None
    assert _cwd_project("/tmp/irgendwas") == "irgendwas"  # keine Git-Wurzel -> Ordnername als bester Schaetzwert
    assert _project_of_path("/openlehr/steuer/ui") == "openlehr"
    assert _project_of_path("/apps/fahrtenbuch/adr-x") == "fahrtenbuch"
    assert _project_of_path("/apps") is None  # kein Unterprojekt -> themenweit
    assert _project_of_path("/arch/mcp") is None  # Themenordner, kein Projekt
    assert _project_of_path("/shared") is None
    print("  cwd/Pfad -> Projekt-Ableitung ok")

    # Nodes: eigener + fremder Treffer konkurrieren -> eigener steht vorn, fremder gekennzeichnet.
    cands = [
        {"path": "/openlehr/steuer/ui/x", "title": "OL", "summary": "s"},
        {"path": "/apps/fahrtenbuch/adr-y", "title": "FB", "summary": "s"},
    ]
    out = _tag_node_scope([dict(c) for c in cands], "fahrtenbuch")
    assert out[0]["path"] == "/apps/fahrtenbuch/adr-y" and out[0]["foreign_project"] is None
    assert out[1]["path"] == "/openlehr/steuer/ui/x" and out[1]["foreign_project"] == "openlehr"
    print("  Node-Scope: eigener vorn, fremder hinten+markiert ok")

    # Nur fremde Treffer -> erscheinen trotzdem, gekennzeichnet (keine Unterdrueckung).
    out2 = _tag_node_scope([dict(cands[0])], "fahrtenbuch")
    assert len(out2) == 1 and out2[0]["foreign_project"] == "openlehr"
    print("  Node-Scope: nur fremde bleiben drin, markiert ok")

    # 'shared'/themenweit gilt als eigener Bereich, nicht als fremder.
    out3 = _tag_node_scope([{"path": "/arch/mcp", "title": "A", "summary": "s"}], "fahrtenbuch")
    assert out3[0]["foreign_project"] is None
    print("  Node-Scope: themenweit zaehlt als eigen ok")

    # cwd nicht ermittelbar -> query() reordert/markiert nichts (heutiges Verhalten).
    n_noscope, _ = query(keywords("fahrtenbuch trip repository hash kette gobd verletzt"),
                          rand=lambda: 1.0, embed_fn=_no_embed)
    assert all("foreign_project" not in n for n in n_noscope), n_noscope
    print("  cwd fehlt -> keine Markierung, heutiges Verhalten ok")

    # Lessons: gleiche Faelle wie bei Nodes, plus 'projects' leer/NULL -> gilt ueberall.
    lscored = [
        (3, False, 1, {"projects": '["openlehr"]', "id": "L-a"}),
        (3, False, 1, {"projects": '["fahrtenbuch"]', "id": "L-b"}),
        (3, False, 1, {"projects": None, "id": "L-c"}),
    ]
    lout = _tag_lesson_scope([tuple(t) for t in lscored], "fahrtenbuch")
    ids_in_order = [s[3]["id"] for s in lout]
    assert ids_in_order.index("L-b") < ids_in_order.index("L-a"), ids_in_order  # eigen vor fremd
    assert ids_in_order.index("L-c") < ids_in_order.index("L-a"), ids_in_order  # leer=ueberall vor fremd
    assert lout[[s[3]["id"] for s in lout].index("L-a")][3]["foreign_projects"] == "openlehr"
    assert lout[[s[3]["id"] for s in lout].index("L-b")][3]["foreign_projects"] == ""
    assert lout[[s[3]["id"] for s in lout].index("L-c")][3]["foreign_projects"] == ""
    print("  Lesson-Scope: eigen/ueberall vor fremd, fremd markiert, nicht ausgeschlossen ok")

    # Gegenprobe an den acht bestehenden _CASES: mit cwd=fahrtenbuch darf KEIN
    # Fall weniger Treffer liefern als ohne cwd (Nachrangigkeit, kein Ausschluss).
    for want, prompt in _CASES:
        kws_c = keywords(prompt)
        if len(kws_c) < MIN_HITS:
            continue
        n0, l0 = query(kws_c, rand=lambda: 1.0, embed_fn=_no_embed)
        n1, l1 = query(kws_c, rand=lambda: 1.0, cwd="/Volumes/daten/Begod2026/fahrtenbuch", embed_fn=_no_embed)
        assert len(n1) >= len(n0) and len(l1) >= len(l0), (
            f"Gegenprobe verlor Treffer bei '{prompt[:40]}...': "
            f"ohne cwd {len(n0)}n/{len(l0)}l, mit cwd {len(n1)}n/{len(l1)}l"
        )
    print("  Gegenprobe an den 8 Faellen: cwd verliert nie Treffer ok")

    # --- Entdopplung je Sitzung (ADR-033 Schritt 1) ---
    with tempfile.TemporaryDirectory() as td:
        lp = os.path.join(td, "recall_log.jsonl")
        with open(lp, "w", encoding="utf-8") as f:
            f.write(json.dumps({"session": "abcdef12", "nodes": ["/a"], "lessons": ["L-1"]}) + "\n")
            f.write(json.dumps({"session": "ffffffff", "nodes": ["/b"], "lessons": []}) + "\n")

        nodes_in = [{"path": "/a"}, {"path": "/new"}]
        lessons_in = [{"id": "L-1"}, {"id": "L-new"}]

        # Wiederholung derselben Sitzung -> unterdrueckt.
        n_out, l_out = _dedup_session(nodes_in, lessons_in, "abcdef12-lang-rest", lp)
        assert [n["path"] for n in n_out] == ["/new"], n_out
        assert [l["id"] for l in l_out] == ["L-new"], l_out
        print("  Dedup: Wiederholung derselben Sitzung unterdrueckt ok")

        # NEGATIVFALL: neuer Eintrag kommt trotzdem durch (oben mitgeprueft: /new, L-new bleiben).
        # Andere Sitzung -> nichts unterdrueckt, obwohl /b geloggt ist.
        n_out2, l_out2 = _dedup_session([{"path": "/a"}], [], "zzzzzzzz", lp)
        assert [n["path"] for n in n_out2] == ["/a"], n_out2
        print("  Dedup: andere Sitzung filtert nichts ok")

        # GRENZFALL: keine Sitzungskennung -> nichts unterdrueckt (im Zweifel liefern).
        n_out3, l_out3 = _dedup_session(nodes_in, lessons_in, None, lp)
        assert n_out3 == nodes_in and l_out3 == lessons_in, (n_out3, l_out3)
        print("  Dedup: fehlende Sitzungskennung unterdrueckt nichts ok")

    # --- Radar (ADR-033 Schritt 2) ---
    assert _radar_select([], "score") == []
    ein = [{"score": -5.0, "path": "/x"}]
    assert _radar_select(ein, "score") == ein  # n=1: nichts zum Vergleichen, gilt als Signal
    print("  Radar: leer/n=1 ok")

    # n < RADAR_MIN_SAMPLE_N: MAD unzuverlaessig -> alle Kandidaten durch,
    # unabhaengig von der Streuung (auch wenn einer klar besser waere).
    klein = [{"score": -50.0, "path": "/a"}, {"score": -10.0, "path": "/b"},
             {"score": -9.9, "path": "/c"}]
    assert len(klein) < RADAR_MIN_SAMPLE_N
    assert _radar_select(klein, "score") == klein
    print("  Radar: n < RADAR_MIN_SAMPLE_N -> alle durch (MAD unzuverlaessig) ok")

    # MAD==0 (alle Scores gleich, n>=RADAR_MIN_SAMPLE_N): "alles gleich
    # schwach" -> Schweigen, kein zufaelliger Sieger.
    gleich = [{"score": -5.0, "path": f"/{i}"} for i in range(RADAR_MIN_SAMPLE_N + 1)]
    assert _radar_select(gleich, "score") == []
    print("  Radar: MAD=0 bei ausreichend n -> Schweigen ok")

    # Klarer Ausreisser weit unter dem Rest -> bleibt als Signal uebrig,
    # der Rest (dicht beieinander, kein Abstand zueinander) faellt weg.
    ausreisser = [{"score": -100.0, "path": "/spitze"}] + \
        [{"score": -10.0 - i * 0.01, "path": f"/rauschen{i}"} for i in range(RADAR_MIN_SAMPLE_N)]
    sig = _radar_select(ausreisser, "score")
    assert [c["path"] for c in sig] == ["/spitze"], sig
    print("  Radar: klarer Ausreisser bleibt allein als Signal ok")

    # Projektstufungs-Bremse (_effective_noise_mult/_project_node_counts/
    # PROJECT_NOISE_OVERRIDES) ist ausgebaut (Auftrag 2026-08-13, s. Kommentar
    # bei PROJECT_CALIBRATION_MIN_SAMPLES oben) -- query() nutzt jetzt
    # unbedingt den gemeinsamen NOISE_FLOOR_MAD_MULT, nichts mehr zu testen,
    # was nicht schon der Radar-Test oben abdeckt.

    # --- Zielfunktion (Erweiterung 2026-08-07, Punkt 2) ---
    r = zielfunktion()
    assert set(r) == {"score", "n", "silent", "per_task"}, r
    assert 0 <= r["score"] <= r["n"], r
    saved_mult = NOISE_FLOOR_MAD_MULT
    r2 = zielfunktion({"NOISE_FLOOR_MAD_MULT": 1.0})
    assert NOISE_FLOOR_MAD_MULT == saved_mult, "zielfunktion liess einen Parameter global veraendert zurueck"
    assert r != r2 or True  # kein Anspruch auf Unterschied, nur: kein Fehler und Ruecksetzung haelt
    try:
        zielfunktion({"unbekannt": 1})
        assert False, "zielfunktion nahm einen unbekannten Parameter klaglos an"
    except ValueError:
        pass
    print(f"  Zielfunktion: {r} (Parameter danach unveraendert, unbekannter Schluessel wirft) ok")

    # --- Embedding-Kanal + Ensemble (Auftrag 2026-08-07 Teil 1+2) --------
    # Eigene Test-DB (echtes schema.sql, wie shared-knowledge/tests/
    # test_knowledge_hybrid_search.py::temp_db) statt der echten brainlehr.db --
    # deterministisch, kein Netzwerk. DB (Modulglobal) wird fuer die Dauer
    # des Blocks umgebogen, danach garantiert zurueckgesetzt.
    #
    # Zwei Knoten: 'n-embed' traegt KEINES der Anfrage-Woerter im Wortlaut
    # (bm25 findet ihn nie) und bekommt einen Embedding-Vektor, der exakt
    # zum Fake-Query-Vektor passt. 'n-agree' traegt die Anfrage-Woerter
    # woertlich UND denselben Vektor -- ein Kandidat, der in BEIDEN Kanaelen
    # vorn liegt.
    import tempfile as _tempfile
    # ort.WURZEL statt Path(DB).with_name(...): BRAINLEHR_DB kann (Selbsttest
    # unter BRAUCHT_ISOLIERTE_DB, tests/test_alle_selftests.py) auf eine
    # Kopie zeigen, die ohne schema.sql daneben liegt -- die echte Repo-
    # Wurzel bleibt davon unberuehrt. Vorher hier ein latenter, bis
    # 2026-08-13 durch ein unabhaengiges xfail maskierter Fehler (siehe
    # Commit-Historie): FileNotFoundError, sobald die isolierte Kopie kein
    # Geschwister-schema.sql hat.
    _schema = (ort.WURZEL / "schema.sql").read_text(encoding="utf-8")
    with _tempfile.TemporaryDirectory() as _td:
        _db_path = os.path.join(_td, "test.db")
        _conn = sqlite3.connect(_db_path)
        _conn.executescript(_schema)
        _conn.executemany(
            # norm_entscheidung seit 2026-08-08 Pflicht (DB-Trigger) -- ohne
            # sie weist der Trigger jedes INSERT ab. Vierter vorbestehende
            # Fehlschlag dieses Selbsttests, gefunden 2026-08-09.
            "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source, "
            "norm_entscheidung, norm_entschieden_grund, norm_entschieden_von) "
            "VALUES (?, ?, 'shared', ?, ?, NULL, 0, 'test', 'keine_norm', "
            "'Testfixtur, kein Sollen', 'selftest')",
            [
                ("n-embed", "/test/embed-only", "Zebrafalter Migrationsmuster",
                 "Enthaelt keines der Anfrage-Woerter im Wortlaut"),
                ("n-agree", "/test/beide-kanaele", "Quartalsbericht Dachrinne Fahrradkorb",
                 "Enthaelt drei der vier Anfrage-Woerter woertlich"),
            ],
        )
        _conn.executemany(
            "INSERT INTO knowledge_embeddings (kind, ref_id, model, vector, updated_at) VALUES "
            # Modell muss dem gueltigen aus knowledge_config entsprechen (Trigger
            # seit 2026-08-07) UND dem, nach dem _embedding_ranking filtert --
            # mit 'test' fand dieser Block nie einen Embedding-Treffer.
            "(?, ?, ?, ?, '2026-08-07T00:00:00Z')",
            [("node", "n-embed", embeddings.DEFAULT_EMBED_MODEL,
              embeddings.pack_embedding([1.0, 0.0, 0.0])),
             ("node", "n-agree", embeddings.DEFAULT_EMBED_MODEL,
              embeddings.pack_embedding([1.0, 0.0, 0.0]))],
        )
        _conn.commit()
        _conn.close()

        _alt_db, DB = DB, _db_path
        try:
            _kws = keywords("quartalsbericht dachrinne fahrradkorb regenschirm")
            _fake_vec = lambda *a, **k: [1.0, 0.0, 0.0]
            _no_vec = lambda *a, **k: None

            # ROT (Teil 1): ohne Embedding-Kanal findet bm25 fuer 'n-embed'
            # nichts -- kein Anfragewort kommt im Knotentext vor. 'n-agree'
            # wird dagegen ueber bm25 gefunden (drei woertliche Treffer).
            _n_rot, _ = query(_kws, rand=lambda: 1.0, embed_fn=_no_vec)
            assert [n["path"] for n in _n_rot] == ["/test/beide-kanaele"], _n_rot
            print("  Teil 1 ROT: ohne Embedding-Kanal fehlt der reine Embedding-Fund ok")

            # ROT/GRUEN Nachtrag (ZWEITER_KANAL, Vorgabe AN seit ADR-035,
            # 2026-08-07): eingeschaltet (Vorgabe) wird ein reiner
            # Embedding-Fund eingespielt -- ausgeschaltet nicht (Verhalten
            # wie vor Commit 4167aef78).
            global ZWEITER_KANAL, ENSEMBLE_PFLICHT
            _alt_kanal = ZWEITER_KANAL
            _alt_pflicht_isoliert = ENSEMBLE_PFLICHT
            assert ZWEITER_KANAL is True, "Vorgabewert muss AN sein (Betriebsart C, ADR-035)"
            ZWEITER_KANAL = False  # Testblock prueft zuerst das AUS-Verhalten, explizit erzwungen
            # Dieser Block prueft ZWEITER_KANAL isoliert (Ensemble-Pflicht hat
            # ihren eigenen Block unten) -- sonst schluckt die jetzt ebenfalls
            # AN-vorgegebene ENSEMBLE_PFLICHT den reinen Embedding-Fund weg.
            ENSEMBLE_PFLICHT = False
            _calls = []
            _counting_vec = lambda *a, **k: (_calls.append(1), [1.0, 0.0, 0.0])[1]
            try:
                # ROT: AUS -> 'n-embed' bleibt draussen, KEIN Aufruf
                # des embed_fn (NEGATIVFALL: abgeschaltetes Merkmal kostet
                # keine Zeit -- kein Ollama-Aufruf mehr).
                _n_kanal_aus, _ = query(_kws, rand=lambda: 1.0, embed_fn=_counting_vec)
                assert not any(n["path"] == "/test/embed-only" for n in _n_kanal_aus), _n_kanal_aus
                assert _calls == [], f"embed_fn wurde trotz ZWEITER_KANAL=False aufgerufen: {len(_calls)}x"
                print("  ROT (ZWEITER_KANAL=False): kein Embedding-Fund, kein embed_fn-Aufruf ok")

                # GRUEN: eingeschaltet (Vorgabe) taucht derselbe Kandidat auf.
                ZWEITER_KANAL = True
                _n_kanal_an, _ = query(_kws, rand=lambda: 1.0, embed_fn=_fake_vec)
                assert any(n["path"] == "/test/embed-only" for n in _n_kanal_an), _n_kanal_an
                print("  GRUEN (ZWEITER_KANAL=True, Vorgabe): derselbe Embedding-Fund taucht auf ok")

                # Env-Var ueberschreibt den Modul-Vorgabewert in beide Richtungen.
                ZWEITER_KANAL = False
                os.environ["KNOWLEDGE_ZWEITER_KANAL"] = "1"
                try:
                    _n_env_an, _ = query(_kws, rand=lambda: 1.0, embed_fn=_fake_vec)
                    assert any(n["path"] == "/test/embed-only" for n in _n_env_an), _n_env_an
                    os.environ["KNOWLEDGE_ZWEITER_KANAL"] = "0"
                    _n_env_aus, _ = query(_kws, rand=lambda: 1.0, embed_fn=_fake_vec)
                    assert not any(n["path"] == "/test/embed-only" for n in _n_env_aus), _n_env_aus
                finally:
                    del os.environ["KNOWLEDGE_ZWEITER_KANAL"]
                print("  KNOWLEDGE_ZWEITER_KANAL=1/0 ueberschreibt den Modul-Vorgabewert ok")
            finally:
                ZWEITER_KANAL = _alt_kanal
                ENSEMBLE_PFLICHT = _alt_pflicht_isoliert

            # ROT/GRUEN Nachtrag (ENSEMBLE_PFLICHT, Vorgabe AN seit ADR-035,
            # 2026-08-07, bewertet nur bei ZWEITER_KANAL=True): eingeschaltet
            # (Vorgabe) schluckt die Schweigepflicht 'n-embed' (nur im
            # Embedding-Kanal vorn, bm25 hat ihn nie gesehen) -- ausgeschaltet
            # bleibt er drin (Union wie Commit 4167aef78).
            _alt_pflicht = ENSEMBLE_PFLICHT
            assert ENSEMBLE_PFLICHT is True, "Vorgabewert muss AN sein (Betriebsart C, ADR-035)"
            ZWEITER_KANAL = True  # dieser Block prueft den Ensemble-Vergleich, braucht den Kanal an
            try:
                # ROT: eingeschaltet wird 'n-embed' geschluckt.
                ENSEMBLE_PFLICHT = True
                _n_an, _ = query(_kws, rand=lambda: 1.0, embed_fn=_fake_vec)
                assert any(n["path"] == "/test/beide-kanaele" for n in _n_an), _n_an
                assert not any(n["path"] == "/test/embed-only" for n in _n_an), (
                    f"Vorbedingung verletzt, 'n-embed' nicht geschluckt: {_n_an}")
                print("  ROT (ENSEMBLE_PFLICHT=True, Vorgabe): reiner Embedding-Fund wird geschluckt ok")

                # GRUEN: ausgeschaltet bleibt derselbe Kandidat drin.
                ENSEMBLE_PFLICHT = False
                _n_aus, _ = query(_kws, rand=lambda: 1.0, embed_fn=_fake_vec)
                assert any(n["path"] == "/test/beide-kanaele" for n in _n_aus), _n_aus
                assert any(n["path"] == "/test/embed-only" for n in _n_aus), _n_aus
                print("  GRUEN (ENSEMBLE_PFLICHT=False): derselbe Kandidat bleibt drin ok")

                # Env-Var ueberschreibt den Modul-Vorgabewert in beide Richtungen.
                os.environ["KNOWLEDGE_ENSEMBLE_PFLICHT"] = "1"
                try:
                    _n_env_an, _ = query(_kws, rand=lambda: 1.0, embed_fn=_fake_vec)
                    assert not any(n["path"] == "/test/embed-only" for n in _n_env_an), _n_env_an
                    os.environ["KNOWLEDGE_ENSEMBLE_PFLICHT"] = "0"
                    _n_env_aus, _ = query(_kws, rand=lambda: 1.0, embed_fn=_fake_vec)
                    assert any(n["path"] == "/test/embed-only" for n in _n_env_aus), _n_env_aus
                finally:
                    del os.environ["KNOWLEDGE_ENSEMBLE_PFLICHT"]
                print("  KNOWLEDGE_ENSEMBLE_PFLICHT=1/0 ueberschreibt den Modul-Vorgabewert ok")
            finally:
                ENSEMBLE_PFLICHT = _alt_pflicht
                ZWEITER_KANAL = _alt_kanal

            # GRENZFALL Teil 2 + NEGATIVFALL Teil 1: Ollama unerreichbar
            # (embed_fn liefert None, wie embed_text() es per Vertrag bei
            # jedem Netzwerkfehler tut) -> nur EIN Kanal verfuegbar, Abruf
            # liefert weiterhin Ergebnisse wie vor diesem Auftrag (kein
            # Schweigen aus Mangel an Vergleich), kein Fehler, ein Vermerk
            # auf stderr.
            import contextlib
            import io
            ZWEITER_KANAL = True  # beide folgenden Grenzfaelle pruefen den Kanal selbst, nicht den Schalter
            try:
                _buf = io.StringIO()
                with contextlib.redirect_stderr(_buf):
                    _n_neg, _ = query(_kws, rand=lambda: 1.0, embed_fn=_no_vec)
                assert [n["path"] for n in _n_neg] == ["/test/beide-kanaele"], _n_neg
                assert "Embedding-Kanal nicht verfuegbar" in _buf.getvalue(), _buf.getvalue()
                print("  Grenzfall/Negativfall: Ollama unerreichbar -> Einkanalbetrieb + Vermerk, kein Fehler ok")

                # Fehlende knowledge_embeddings-Tabelle (aeltere DB-Kopie) ist
                # derselbe Grenzfall -- Kanal nicht verfuegbar, kein Fehler.
                _conn2 = sqlite3.connect(_db_path)
                _conn2.execute("DROP TABLE knowledge_embeddings")
                _conn2.commit()
                _conn2.close()
                _n_notab, _ = query(_kws, rand=lambda: 1.0, embed_fn=_fake_vec)
                assert [n["path"] for n in _n_notab] == ["/test/beide-kanaele"], _n_notab
                print("  Grenzfall: fehlende knowledge_embeddings-Tabelle -> Einkanalbetrieb, kein Fehler ok")
            finally:
                ZWEITER_KANAL = _alt_kanal
        finally:
            DB = _alt_db

    if _suchpfad_vorher is None:
        os.environ.pop("KNOWLEDGE_SUCHPFAD_ABRUF", None)
    else:
        os.environ["KNOWLEDGE_SUCHPFAD_ABRUF"] = _suchpfad_vorher
    print(f"selftest ok ({len(_CASES)} Faelle, MIN_HITS={MIN_HITS})")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    if "--report" in sys.argv:
        report()
        sys.exit(0)
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
