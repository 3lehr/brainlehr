#!/usr/bin/env python3
"""
knowledge_recall_hook.py — Auto-Recall (UserPromptSubmit-Hook, systemweit).

Liest den User-Prompt von stdin (Claude-Code-Hook-JSON), sucht in der
gemeinsamen knowledge.db (FTS-Nodes + lessons_learned) nach dem aktuellen
Thema und spritzt die stärksten Treffer als kompakten Kontext-Block ein.

Regeln:
- IMMER exit 0. Fehler/keine Treffer -> nichts ausgeben (Kontext nicht müllen).
- Klein bleiben (~<200 Tokens): max 3 Nodes + 2 Lessons.
- Still bei Slash-Commands und zu kurzen/keywordarmen Prompts.
- Relevanz-Schwelle: ein Treffer muss MIN_HITS verschiedene Prompt-Keywords im
  ausgegebenen Text enthalten. Ein einzelnes Allerweltswort ("dokument",
  "modell") reicht nicht mehr -- lieber gar kein Recall als falscher.

Selbsttest: python3 knowledge_recall_hook.py --selftest

Gegenstück zum Capture: was der /learn-Reflex via lesson_record/knowledge_add
schreibt, findet dieser Hook beim nächsten passenden Prompt wieder.
"""
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
# suchpfad_abruf.py liegt in diesem Ordner (haken/) -- eigenes Modul (Monolith-
# Stopp hier), nur der Kandidaten-Beschaffung wegen aufgerufen (S9, Auftrag
# 2026-08-09). Aus diesem Hook nur AUFGERUFEN, s. _suchpfad_aktiv() oben.
import suchpfad_abruf  # noqa: E402

# Protokoll, WAS gezogen wurde -- neben der DB, eigene Datei (kein Tabelle in
# knowledge.db: sonst schreibt JEDE Sitzung bei JEDEM Prompt in dieselbe DB,
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
# PROJECT_CALIBRATION_MIN_SAMPLES 50 -                Projektstufungs-Bremse (s.u.)
# MAD_TO_SIGMA                 1.4826 -                mathematische Konstante, KEINE Stellgroesse (s.u.)
# ENSEMBLE_TOP_N               5     1..10             Ensemble-Uebereinstimmungsfenster je Kanal (s.u., Teil 2)
# ZWEITER_KANAL                 True   True/False       Embedding-Kanal ueberhaupt aktiv, Vorgabe AN seit ADR-035 (s.u., Nachtrag)
# ENSEMBLE_PFLICHT              True   True/False       Ensemble-Schweigepflicht, Vorgabe AN seit ADR-035 (s.u., Nachtrag)

# Anzahl ausgegebener Treffer je Abruf -- bisher als nacktes ":3"/":2" an den
# Slice-Stellen in query() verstreut, jetzt hier benannt.
MAX_NODES = 3
MAX_LESSONS = 2

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

# Projektstufung mit gemessener Bremse (Betreiber-Auftrag 2026-08-07): eine
# projektspezifische Uebersteuerung von NOISE_FLOOR_MAD_MULT (siehe
# PROJECT_NOISE_OVERRIDES/_effective_noise_mult()) gilt nur, wenn dieses
# Projekt (project_id-Spalte, NICHT der aus cwd abgeleitete Ordnername --
# Lehre L-fd1221 zu versteckten Umgebungsannahmen) mindestens so viele
# eigene Knoten hat. GERATEN, NICHT GEMESSEN -- Begruendung: eine Eichung
# auf einem einzigen Beispiel waere schlechter als der gemeinsame Wert.
# Gemessener Bestand 2026-08-07 (_project_node_counts()): shared 286,
# begod 25, stadtwerke 2, aka 1, bebetter 1, openlehr 1 -- KEIN Projekt
# ausser 'shared' erreicht auch nur die Haelfte dieser Schwelle, darum
# bleibt PROJECT_NOISE_OVERRIDES unten bewusst leer.
PROJECT_CALIBRATION_MIN_SAMPLES = 50

# Projektspezifische Uebersteuerungen von NOISE_FLOOR_MAD_MULT. Leer, weil
# heute kein Projekt PROJECT_CALIBRATION_MIN_SAMPLES erreicht (s.o.) -- die
# Struktur ist gebaut und getestet (_effective_noise_mult()), aber unbenutzt,
# bis ein Projekt genug eigene Daten fuer eine eigene Eichung hat.
PROJECT_NOISE_OVERRIDES: dict[str, float] = {}

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
ZWEITER_KANAL = False


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
SUCHPFAD_ABRUF = False


def _suchpfad_aktiv() -> bool:
    override = os.environ.get("KNOWLEDGE_SUCHPFAD_ABRUF")
    if override is not None:
        return override == "1"
    return SUCHPFAD_ABRUF


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


def _project_node_counts(conn) -> dict:
    """Rohbestand je project_id aus knowledge_nodes (Betreiber-Auftrag
    2026-08-07, Punkt 3) -- die echte Bestandsspalte, nicht der aus cwd
    abgeleitete Ordnername (siehe PROJECT_CALIBRATION_MIN_SAMPLES-Kommentar).
    Gemessen 2026-08-07: {'shared': 286, 'begod': 25, 'stadtwerke': 2,
    'aka': 1, 'bebetter': 1, 'openlehr': 1}."""
    rows = conn.execute(
        "SELECT project_id, COUNT(*) FROM knowledge_nodes GROUP BY project_id"
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def _effective_noise_mult(project_id: str | None, project_counts: dict | None) -> float:
    """Projektstufung MIT Bremse: eine Uebersteuerung aus
    PROJECT_NOISE_OVERRIDES gilt nur, wenn project_counts[project_id] >=
    PROJECT_CALIBRATION_MIN_SAMPLES ist -- sonst (auch wenn eine
    Uebersteuerung fuer diese project_id existiert) der gemeinsame
    NOISE_FLOOR_MAD_MULT. Kein project_id/project_counts -> gemeinsamer Wert.
    HERKUNFT NOCH NICHT VERDRAHTET: query() ruft dies heute mit
    project_id=None auf, weil cwd (Ordnername) und project_id (Bestands-
    spalte) sich nicht zuverlaessig aufeinander abbilden lassen (siehe
    _TOPIC_SEGMENTS-Kommentar oben: 18 Knoten unter /openlehr/... tragen
    project_id='shared'). Diese Funktion ist fertig und getestet; das
    Herstellen eines verlaesslichen cwd->project_id-Bezugs ist ein eigener,
    hier nicht beauftragter Schritt."""
    if not project_id or not project_counts:
        return NOISE_FLOOR_MAD_MULT
    if project_counts.get(project_id, 0) < PROJECT_CALIBRATION_MIN_SAMPLES:
        return NOISE_FLOOR_MAD_MULT
    return PROJECT_NOISE_OVERRIDES.get(project_id, NOISE_FLOOR_MAD_MULT)


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


def query(kws: list[str], rand=None, log_path: str | None = None, cwd: str | None = None,
          prompt: str | None = None, embed_fn=None) -> tuple[list, list]:
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
    Doktrin: mockbare Aussenwelt, kein echter Ollama-Aufruf im Test noetig."""
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
    try:
        project_counts = _project_node_counts(conn)
    except sqlite3.Error:
        project_counts = {}
    # project_id=None: cwd->project_id-Bezug noch nicht verdrahtet, siehe
    # _effective_noise_mult()-Docstring. Faellt auf den gemeinsamen Wert zurueck.
    mad_mult = _effective_noise_mult(None, project_counts)
    if _suchpfad_aktiv():
        # S9: Kandidaten ueber denselben Suchpfad wie knowledge_search
        # (suchpfad_abruf.kandidaten, RRF ueber Stichwort+Bedeutung, kein
        # MIN_HITS/ENSEMBLE_PFLICHT-Vorfilter) -- die Nachbehandlung
        # (trust_score, rangfolge, Scope, Explore, MAX_NODES/MAX_LESSONS-
        # Deckel, geltend-Filter) bleibt dieselbe wie im Zweig darunter.
        node_rows, lesson_rows = [], []
        try:
            node_rows, lesson_rows = suchpfad_abruf.kandidaten(
                conn, prompt if prompt else " ".join(kws), query_vec, MAX_NODES + MAX_LESSONS)
        except sqlite3.Error:
            pass
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
                agent_type: str | None = None) -> None:
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
    try:
        nodes, lessons = query(kws, cwd=cwd, prompt=prompt)
    except Exception:
        return
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

    if not nodes and not lessons:
        return
    nodes, lessons = _dedup_session(nodes, lessons, session_id)
    if not nodes and not lessons:
        return
    # agent_id/agent_type: GEMESSEN nicht vorhanden im UserPromptSubmit-Payload
    # (s. log_recall()-Docstring) -- .get() trotzdem statt hartem None, falls
    # der Haltepunkt sie kuenftig doch liefert.
    log_recall(nodes, lessons, cwd=cwd, session_id=session_id, prompt=prompt,
               agent_id=payload.get("agent_id"), agent_type=payload.get("agent_type"))

    lines = ["<knowledge-recall>",
             "Relevantes Wissen aus der Knowledge-DB (Auto-Recall, ungeprüft — "
             "vor Nutzung kurz verifizieren):"]
    for n in nodes:
        tag = " (Erkundung -- selten gezogen)" if n.get("explore") else ""
        fremd = f" [anderes Projekt: {n['foreign_project']}]" if n.get("foreign_project") else ""
        lines.append(f"- [{n['path']}]{alter(n.get('updated_at'))}{tag}{fremd} "
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
    lines.append("</knowledge-recall>")
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
    print("\n".join(lines))


def zielfunktion(params: dict | None = None) -> dict:
    """Deterministische Zielfunktion (Betreiber-Auftrag 2026-08-07, Punkt 2):
    Parameter rein, Trefferguete ueber den Pruefkorpus raus -- KEIN
    Modellaufruf, kein Ollama, keine Optuna-Studie (hier nicht beauftragt,
    siehe PROJECT_NOISE_OVERRIDES-Kommentar oben: der Pruefkorpus hat drei
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
        for p in (str(shared_knowledge / "schreibpruefstand"), str(shared_knowledge),
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

    for want, prompt in _CASES:
        kws = keywords(prompt)
        n, l = (query(kws, rand=_never_explore, embed_fn=_no_embed) if len(kws) >= MIN_HITS else ([], []))
        got = bool(n or l)
        assert got == want, (
            f"MIN_HITS={MIN_HITS}: '{prompt[:40]}...' erwartet "
            f"{'Treffer' if want else 'leer'}, bekam {len(n)}n/{len(l)}l"
        )
        print(f"  {'HIT ' if want else 'MISS'} ok: {len(n)}n/{len(l)}l  {prompt[:45]}")
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
        global DB
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

    # --- Projektstufung mit Bremse (Erweiterung 2026-08-07, Punkt 3) ---
    assert _effective_noise_mult(None, {"begod": 25}) == NOISE_FLOOR_MAD_MULT
    assert _effective_noise_mult("begod", None) == NOISE_FLOOR_MAD_MULT
    counts = {"begod": 25, "shared": 286}
    # NEGATIVFALL: Projekt unterhalb der Schwelle bekommt den gemeinsamen
    # Wert, AUCH WENN eine Uebersteuerung fuer diese project_id existiert --
    # das Vorhandensein einer Uebersteuerung darf die Bremse nicht umgehen.
    global PROJECT_NOISE_OVERRIDES
    alt_overrides = dict(PROJECT_NOISE_OVERRIDES)
    PROJECT_NOISE_OVERRIDES["begod"] = 9.9
    try:
        assert 25 < PROJECT_CALIBRATION_MIN_SAMPLES
        assert _effective_noise_mult("begod", counts) == NOISE_FLOOR_MAD_MULT, (
            "Projekt unterhalb der Schwelle nutzte trotzdem eine Uebersteuerung")
        print("  Projektstufung NEGATIVFALL: begod (25 < Schwelle) bekommt gemeinsamen Wert ok")

        # Positivfall: oberhalb der Schwelle greift die Uebersteuerung.
        counts_hoch = {"begod": PROJECT_CALIBRATION_MIN_SAMPLES}
        assert _effective_noise_mult("begod", counts_hoch) == 9.9
        print("  Projektstufung: oberhalb der Schwelle greift die Uebersteuerung ok")
    finally:
        PROJECT_NOISE_OVERRIDES.clear()
        PROJECT_NOISE_OVERRIDES.update(alt_overrides)

    # Reale project_id-Verteilung (gemessen 2026-08-07): kein Nicht-'shared'-
    # Projekt erreicht PROJECT_CALIBRATION_MIN_SAMPLES -- also greift heute
    # ueberall der gemeinsame Wert, wenn diese Funktion echt verdrahtet waere.
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=2.0)
    real_counts = _project_node_counts(conn)
    conn.close()
    for proj, n_proj in real_counts.items():
        if proj == "shared":
            continue
        assert n_proj < PROJECT_CALIBRATION_MIN_SAMPLES, (proj, n_proj)
    print(f"  Realer Bestand {real_counts}: kein Nicht-shared-Projekt erreicht die Schwelle ok")

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
    # test_knowledge_hybrid_search.py::temp_db) statt der echten knowledge.db --
    # deterministisch, kein Netzwerk. DB (Modulglobal) wird fuer die Dauer
    # des Blocks umgebogen, danach garantiert zurueckgesetzt.
    #
    # Zwei Knoten: 'n-embed' traegt KEINES der Anfrage-Woerter im Wortlaut
    # (bm25 findet ihn nie) und bekommt einen Embedding-Vektor, der exakt
    # zum Fake-Query-Vektor passt. 'n-agree' traegt die Anfrage-Woerter
    # woertlich UND denselben Vektor -- ein Kandidat, der in BEIDEN Kanaelen
    # vorn liegt.
    import tempfile as _tempfile
    _schema = Path(DB).with_name("schema.sql").read_text(encoding="utf-8")
    with _tempfile.TemporaryDirectory() as _td:
        _db_path = os.path.join(_td, "test.db")
        _conn = sqlite3.connect(_db_path)
        _conn.executescript(_schema)
        _conn.executemany(
            "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source) "
            "VALUES (?, ?, 'shared', ?, ?, NULL, 0, 'test')",
            [
                ("n-embed", "/test/embed-only", "Zebrafalter Migrationsmuster",
                 "Enthaelt keines der Anfrage-Woerter im Wortlaut"),
                ("n-agree", "/test/beide-kanaele", "Quartalsbericht Dachrinne Fahrradkorb",
                 "Enthaelt drei der vier Anfrage-Woerter woertlich"),
            ],
        )
        _conn.executemany(
            "INSERT INTO knowledge_embeddings (kind, ref_id, model, vector, updated_at) VALUES "
            "(?, ?, 'test', ?, '2026-08-07T00:00:00Z')",
            [("node", "n-embed", embeddings.pack_embedding([1.0, 0.0, 0.0])),
             ("node", "n-agree", embeddings.pack_embedding([1.0, 0.0, 0.0]))],
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
