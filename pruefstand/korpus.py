"""Synthetischer Wissenskorpus fuer den Abruf-Pruefstand (Plan B1,
docs/PLAN_ABRUF_PRUEFSTAND_2026-08-05.md).

Konstruierte Wahrheit statt Beurteilung: jedes Dokument (Node/Lesson) traegt
eine verborgene Themen-Kennung (`topic_id`). Anfragen werden aus derselben
Kennung gebaut -- relevant ist genau, was denselben `topic_id` traegt. Kein
Sprachmodell, kein Netz, keine LLM-Beurteilung. Vorbild:
shared-knowledge/tests/test_knowledge_hybrid_search.py (synthetische Vektoren,
"damit er ohne Netzwerk/Modell deterministisch bleibt").

Determinismus: einziger Zufallsstrom ist `random.Random(seed)`, kein `time`,
kein `os.urandom`. Zwei Laeufe mit demselben seed erzeugen byteidentischen
Korpus (siehe checksum).

VERSIONIERUNGSREGEL (verbindlich): eine einmal freigegebene CORPUS_VERSION
wird NIE nachtraeglich geaendert -- sonst ist kein Vergleich zweier
Messlaeufe ueber die Zeit moeglich (Plan §2). Jede inhaltliche Erweiterung
(neue Topics, mehr Pathologie-Auspraegung, andere Anfragen) bekommt eine neue
Versionsnummer. Ein Bugfix an DIESEM Erzeuger, der den gleichen seed anders
ausgeben laesst, zaehlt als Erweiterung im Sinne dieser Regel.

Die sieben Pathologien aus Plan §3, jede einzeln abschaltbar:
  dominant_node    -- ein Thema zieht den Grossteil der Anfragen
  komposita_umlaute -- deutsche Komposita/Umlaute in Titel/Content
  near_duplicates  -- Themen mit fast-identischem Zwillingsknoten
  oversized_docs   -- Knoten ueber der 2048-Token-Grenze
  multi_project    -- Lessons mit mehreren Projekten
  orphan_parent    -- Knoten mit parent_path ohne existierenden Elternknoten
  zero_hit_queries -- Anfragen ohne jedes relevante Dokument

CORPUS_VERSION 1.1.0 (additiv, waehlbar ueber build_corpus(version=...), siehe
docs/PLAN_ABRUF_PRUEFSTAND_2026-08-05.md Folgeauftrag "Nachsicht bestrafen"):
1.0.0 bleibt dabei in JEDEM Detail unveraendert -- 1.1.0 baut 1.0.0 zuerst
unveraendert auf und haengt danach mit einem zweiten, unabhaengigen
Zufallsstrom (rng2 = random.Random(seed ^ _V11_RNG_XOR)) drei weitere,
einzeln abschaltbare Pathologien an, die NIEDRIGE Schwellen bestrafen statt
nur zu belohnen:
  lockvogel_docs        -- Dokument teilt Stichworte mit einer Anfrage,
                            traegt aber eine ANDERE topic_id -> nach
                            konstruierter Wahrheit nicht relevant
  generic_word_queries  -- Anfragen aus Woertern, die in (fast) jedem
                            Dokument vorkommen ("Uebersicht"/"Zusammenhang"
                            stehen bereits in jedem Titel/jeder Summary von
                            1.0.0) -- Wahrheit: nichts ist relevant
  topic_neighbors       -- zwei neue Themen mit ueberlappendem Wortschatz
                            (teilen Stichworte), deren Dokumente sich
                            trotzdem nicht gegenseitig beantworten
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys

CORPUS_VERSION = "1.0.0"
CORPUS_VERSION_1_1 = "1.1.0"
CORPUS_VERSIONS = (CORPUS_VERSION, CORPUS_VERSION_1_1)

DEFAULT_SEED = 20260805
_V11_RNG_XOR = 0x1976  # zweiter, von der 1.0.0-Erzeugung unabhaengiger Zufallsstrom

DEFAULT_PATHOLOGIES = {
    "dominant_node": True,
    "komposita_umlaute": True,
    "near_duplicates": True,
    "oversized_docs": True,
    "multi_project": True,
    "orphan_parent": True,
    "zero_hit_queries": True,
}

# Neu in 1.1.0, Plan-Folgeauftrag "Nachsicht bestrafen" -- jede einzeln
# abschaltbar, Default an. 1.0.0 kennt diese Schluessel nicht.
DEFAULT_PATHOLOGIES_1_1 = {
    "lockvogel_docs": True,
    "generic_word_queries": True,
    "topic_neighbors": True,
}

# Zwei neue Themen fuer topic_neighbors: teilen das erste Stichwort woertlich
# (ueberlappender Wortschatz), der Rest ist themenfremd -- ihre Dokumente
# beantworten sich trotzdem nicht gegenseitig (eigene topic_id, eigene
# relevant_node_paths).
_NEIGHBOR_TOPIC_A = ("nachbar-wartung-fahrzeug",
                      ["Wartungsplan", "Inspektionstermin", "Serviceintervall", "Fahrzeugpflege"],
                      "fahrtenbuch")
_NEIGHBOR_TOPIC_B = ("nachbar-wartung-gebaeude",
                      ["Wartungsplan", "Instandhaltungstermin", "Reinigungsintervall", "Gebaeudepflege"],
                      "shared")

# Fuer lockvogel_docs: zwei bereits vorhandene, unverwandte 1.0.0-Themen (kein
# neues Vokabular noetig). Index 1/2 in _TOPIC_BANK, siehe unten -- bewusst
# NICHT das dominante Thema (Index 0), das haette eine eigene Pathologie.
_LOCKVOGEL_TOPIC_INDICES = (1, 2)

# Fuer generic_word_queries: Woerter, die in JEDEM 1.0.0-Knoten-Titel bzw.
# jeder Summary woertlich vorkommen (siehe Titel-/Summary-Format oben) --
# "Allerweltswoerter" ohne dass dafuer neue Dokumente noetig sind.
_GENERIC_WORDS = ("Uebersicht", "Zusammenhang")

PROJECTS = ["shared", "fahrtenbuch", "openlehr", "afrika", "setfunk"]

# Themenbank: (topic_id, [Stichwort-Varianten, deutsch, Komposita+Umlaute],
# project). topics[0] ist das Kandidat-Thema fuer "dominant_node". Die letzten
# PHANTOM_TOPIC_COUNT Themen liefern nie Dokumente -- nur fuer
# zero_hit_queries.
_TOPIC_BANK = [
    ("kilometerstand", ["Kilometerstand", "Kilometerstandserfassung", "Tachostand", "Streckenzähler"], "fahrtenbuch"),
    ("steuerabschreibung", ["Abschreibung", "Steuerabschreibung", "AfA-Tabelle", "Anlagevermögen"], "openlehr"),
    ("ladeinfrastruktur", ["Ladesäule", "Ladeinfrastruktur", "Stromtankstelle", "E-Auto-Ladepunkt"], "fahrtenbuch"),
    ("gobd-hashkette", ["GoBD-Hash-Kette", "Prüfkette", "Manipulationsschutz", "Hash-Verkettung"], "fahrtenbuch"),
    ("existenzgruendung", ["Existenzgründung", "Existenzgründerberatung", "Förderprogramm", "Gründungszuschuss"], "openlehr"),
    ("wachhund-isolate", ["Wachhund", "Main-Isolate", "Hängender-Prozess", "Watchdog-Überwachung"], "fahrtenbuch"),
    ("tile-praefetch", ["Kachel-Vorabruf", "Offline-Kartenkacheln", "Tile-Prefetch", "Kartenzwischenspeicher"], "fahrtenbuch"),
    ("audio-latenz", ["Audio-Latenz", "Signalverarbeitung", "Aufnahmeverzögerung", "Klangverzögerung"], "afrika"),
    ("funkkanal", ["Funkkanal", "Drehbeginn-Stummschaltung", "Globales-Rufen", "Sendersuche"], "setfunk"),
    ("nas-integritaet", ["Datei-Integrität", "Forensik-Prüfung", "Speicherzugriff", "Bitfehler-Erkennung"], "shared"),
    ("wcag-kontrast", ["Kontrastverhältnis", "Barrierefreiheit", "Fokusring", "Bedienelement-Größe"], "shared"),
    ("bsi-grundschutz", ["Grundschutz", "Stand-der-Technik", "Sicherheitskatalog", "Compliance-Prüfung"], "shared"),
    ("embedding-grenze", ["Einbettungsgrenze", "Token-Obergrenze", "Vektorabschneidung", "Modellkontext"], "shared"),
    ("wikilink-aufloesung", ["Wikilink-Auflösung", "Querverweis", "Verlinkungsmuster", "Kantenbildung"], "shared"),
    ("carplay-sync", ["CarPlay-Synchronisation", "Fahrzeugdisplay", "Zustandsabgleich", "Bordcomputer-Anbindung"], "fahrtenbuch"),
    ("empfangsbestaetigung", ["Empfangsbestätigung", "Belegpflicht", "Quittierung", "Nachweisführung"], "openlehr"),
    ("stiftshuette-mcp", ["MCP-Werkzeuglöschung", "Reaktivierungslauf", "Serverkonfiguration", "Werkzeugregister"], "shared"),
    ("buckeberg-weg", ["WEG-Selbstverwaltung", "Hausverwaltung", "Eigentümerversammlung", "Verwaltungsübergabe"], "shared"),
    ("permission-handler", ["Berechtigungsdialog", "iOS-Makro", "Zugriffsfreigabe", "Systemberechtigung"], "fahrtenbuch"),
    ("device-deploy", ["Geräte-Installation", "USB-Bereitstellung", "Build-Übertragung", "Simulator-Abgrenzung"], "fahrtenbuch"),
    ("cascade-guard", ["Modell-Kaskade", "Eskalationsstufe", "Hauptfaden-Absicherung", "Subagenten-Steuerung"], "shared"),
    ("recall-hook", ["Auto-Recall", "Prompt-Einspritzung", "Relevanzschwelle", "Kontexteinspeisung"], "shared"),
    ("papernetz-adr", ["Zitationsnetzwerk", "Papernetz-Schema", "Quellenbeleg", "Forschungsanbindung"], "shared"),
    ("beinahe-dublette", ["Beinahe-Dublette", "Fastduplikat", "Redundanzbereinigung", "Ähnlichkeitsprüfung"], "shared"),
    ("orphan-reparatur", ["Elternpfad-Reparatur", "Waisenknoten", "Baumreparatur", "Pfadzuordnung"], "shared"),
    # Phantom-Themen: haben nie Dokumente, dienen nur zero_hit_queries.
    ("phantom-quantencomputer", ["Quantenverschränkung", "Kryo-Kühlung", "Qubit-Fehlerkorrektur", "Supraleitung"], "shared"),
    ("phantom-bienenzucht", ["Bienenstockpflege", "Honigschleuder", "Wabenbau", "Königinnenzucht"], "shared"),
    ("phantom-astrologie", ["Sternzeichen-Deutung", "Horoskoperstellung", "Planetenkonstellation", "Tierkreiszeichen"], "shared"),
]
PHANTOM_TOPIC_COUNT = 3
_REAL_TOPICS = _TOPIC_BANK[:-PHANTOM_TOPIC_COUNT]
_PHANTOM_TOPICS = _TOPIC_BANK[-PHANTOM_TOPIC_COUNT:]

# ASCII-Fallback ohne Umlaute/Komposita-Charakter, fuer die Ablation von
# "komposita_umlaute" -- ersetzt nur die Sonderzeichen hart (aggressiver als
# fold_de: ae statt a, damit der Unterschied zur Faltungslogik messbar bleibt).
_ASCII_FOLD = str.maketrans({"ä": "a", "ö": "o", "ü": "u", "ß": "s",
                              "Ä": "A", "Ö": "O", "Ü": "U"})

# Fuellwoerter fuer Content-Padding (deterministisch, kein echtes Lorem noetig).
_FILLER = [
    "Damit", "ist", "die", "Ablaufreihenfolge", "im", "Betrieb", "nachvollziehbar",
    "geblieben", "und", "der", "Zustand", "wurde", "vor", "jeder", "Auswertung",
    "festgehalten", "Der", "Vorgang", "betrifft", "mehrere", "Komponenten", "die",
    "aufeinander", "aufbauen", "Eine", "genaue", "Beschreibung", "findet", "sich",
    "im", "zugehoerigen", "Protokoll", "sowie", "in", "den", "begleitenden",
    "Notizen", "zur", "Umsetzung", "Weitere", "Einzelheiten", "ergeben", "sich",
    "aus", "dem", "Kontext", "der", "jeweiligen", "Anfrage", "und", "der",
    "damit", "verbundenen", "Antwort",
]


def _fold_pathology(text: str, enabled: bool) -> str:
    return text if enabled else text.translate(_ASCII_FOLD)


def _build_content(rng: random.Random, keywords: list[str], target_words: int) -> str:
    """Deterministischer Fliesstext: Saetze aus Stichwoertern + Fuellwoertern,
    bis target_words Woerter erreicht sind."""
    words: list[str] = []
    while len(words) < target_words:
        sentence = [rng.choice(keywords)] + rng.sample(_FILLER, k=min(9, len(_FILLER)))
        rng.shuffle(sentence)
        words.extend(sentence)
    return " ".join(words[:target_words]) + "."


def _build_corpus_1_0_0(seed: int = DEFAULT_SEED, pathologies: dict | None = None) -> dict:
    """Unveraendert seit CORPUS_VERSION 1.0.0 -- kein Byte hier anfassen,
    sonst ist kein Messlauf mehr mit einem frueheren vergleichbar (Plan §2)."""
    flags = {**DEFAULT_PATHOLOGIES, **(pathologies or {})}
    rng = random.Random(seed)

    nodes: list[dict] = []
    lessons: list[dict] = []
    queries: list[dict] = []
    node_ids_by_path: dict[str, str] = {}

    def _mk_keywords(kws: list[str]) -> list[str]:
        return [_fold_pathology(k, flags["komposita_umlaute"]) for k in kws]

    # --- Knoten je Thema -----------------------------------------------
    # Feste Themen-Indizes fuer oversized_docs, bewusst AUSSERHALB des
    # near_duplicates-Bereichs (ti<18) -- sonst wuerde der Zwilling die
    # ueberlange Laenge mitkopieren und die Zaehlung verdoppeln.
    OVERSIZED_TOPIC_INDICES = {18, 19, 20}
    for ti, (topic_id, kws_raw, project) in enumerate(_REAL_TOPICS):
        kws = _mk_keywords(kws_raw)
        is_dominant = flags["dominant_node"] and ti == 0
        base_count = 16 if is_dominant else 3 + (rng.randint(0, 5))
        for n in range(base_count):
            node_id = f"n-{topic_id}-{n}"
            path = f"/pruefstand/{topic_id}/{n}"
            title = f"{kws[n % len(kws)]} Uebersicht {n}"
            summary = f"{kws[(n + 1) % len(kws)]}: {kws[n % len(kws)]} im Zusammenhang mit {project}."
            make_oversized = flags["oversized_docs"] and n == 0 and ti in OVERSIZED_TOPIC_INDICES
            target_words = 2200 if make_oversized else rng.randint(30, 80)
            content = _build_content(rng, kws, target_words)
            level = 1 if n == 0 else 2
            # gueltiger Default: n>0 haengt am ersten (real existierenden)
            # Knoten des Themas, /0 -- nie an einem nur virtuellen Ordnerpfad.
            parent_path = f"/pruefstand/{topic_id}/0" if n > 0 else None
            if flags["orphan_parent"] and rng.random() < 0.45 and n > 0:
                parent_path = f"/pruefstand/{topic_id}/verwaist-{n}"  # existiert nicht
            node = {
                "id": node_id, "path": path, "parent_path": parent_path,
                "project_id": project, "title": title, "summary": summary,
                "content": content, "level": level, "tags": [topic_id],
                "topic_id": topic_id,
            }
            nodes.append(node)
            node_ids_by_path[path] = node_id

        # Beinahe-Dubletten: fuer die ersten 18 (Nicht-Phantom-)Themen ein
        # fast-identischer Zwilling des ersten Knotens -> 18 Zwillingsknoten,
        # spiegelt die 18 Beinahe-Dubletten-Kandidaten aus dem Echtbestand.
        if flags["near_duplicates"] and ti < 18:
            twin_id = f"n-{topic_id}-dup"
            twin = {
                "id": twin_id, "path": f"/pruefstand/{topic_id}/dup",
                "parent_path": f"/pruefstand/{topic_id}/0",
                "project_id": project, "title": nodes[-base_count]["title"] + " (Kopie)",
                "summary": nodes[-base_count]["summary"],
                "content": nodes[-base_count]["content"] + " Ergaenzter Zusatz.",
                "level": 2, "tags": [topic_id], "topic_id": topic_id,
            }
            nodes.append(twin)
            node_ids_by_path[twin["path"]] = twin_id

    # --- Lessons je Thema (jedes zweite Thema bekommt 1-3 Lessons) ------
    for ti, (topic_id, kws_raw, project) in enumerate(_REAL_TOPICS):
        if ti % 2 != 0:
            continue
        kws = _mk_keywords(kws_raw)
        for n in range(1 + (ti % 3)):
            lesson_id = f"L-{topic_id}-{n}"
            projects = [project]
            if flags["multi_project"] and rng.random() < 0.6:
                others = [p for p in PROJECTS if p != project]
                projects = [project] + rng.sample(others, k=rng.randint(1, 2))
            lessons.append({
                "id": lesson_id, "type": rng.choice(["error", "insight", "pattern", "antipattern"]),
                "description": f"{kws[n % len(kws)]} verursachte einen Fehlschlag im Ablauf.",
                "root_cause": f"Ursache lag bei {kws[(n + 1) % len(kws)]}.",
                "prevention": f"Kuenftig {kws[(n + 2) % len(kws)]} vorab pruefen.",
                "projects": projects, "topic_id": topic_id,
            })

    # --- Anfragen ---------------------------------------------------------
    topic_node_paths: dict[str, list[str]] = {}
    for n in nodes:
        topic_node_paths.setdefault(n["topic_id"], []).append(n["path"])
    topic_lesson_ids: dict[str, list[str]] = {}
    for l in lessons:
        topic_lesson_ids.setdefault(l["topic_id"], []).append(l["id"])

    qi = 0
    for ti, (topic_id, kws_raw, project) in enumerate(_REAL_TOPICS):
        kws = _mk_keywords(kws_raw)
        is_dominant = flags["dominant_node"] and ti == 0
        n_queries = 30 if is_dominant else 2
        for q in range(n_queries):
            text = f"{kws[q % len(kws)]} {kws[(q + 1) % len(kws)]}"
            queries.append({
                "id": f"q-{qi}", "text": text, "topic_id": topic_id,
                "relevant_node_paths": list(topic_node_paths.get(topic_id, [])),
                "relevant_lesson_ids": list(topic_lesson_ids.get(topic_id, [])),
            })
            qi += 1

    if flags["zero_hit_queries"]:
        for topic_id, kws_raw, _project in _PHANTOM_TOPICS:
            kws = _mk_keywords(kws_raw)
            for q in range(2):
                text = f"{kws[q % len(kws)]} {kws[(q + 1) % len(kws)]}"
                queries.append({
                    "id": f"q-{qi}", "text": text, "topic_id": topic_id,
                    "relevant_node_paths": [], "relevant_lesson_ids": [],
                })
                qi += 1

    corpus = {
        "version": CORPUS_VERSION,
        "seed": seed,
        "pathologies": flags,
        "nodes": nodes,
        "lessons": lessons,
        "queries": queries,
    }
    corpus["checksum"] = _checksum(corpus)
    return corpus


def _extend_lockvogel_docs(corpus: dict, rng2: random.Random, komposita: bool) -> None:
    """Lockvogel: Dokument teilt Stichworte mit einer Anfrage eines fremden
    Themas, traegt aber die EIGENE (andere) topic_id -- nach konstruierter
    Wahrheit also nicht relevant fuer diese Anfrage. Verwendet zwei bereits
    vorhandene 1.0.0-Themen, keine neue Themenbank noetig."""
    ia, ib = _LOCKVOGEL_TOPIC_INDICES
    (topic_a, kws_a_raw, _proj_a) = _TOPIC_BANK[ia]
    (topic_b, _kws_b_raw, proj_b) = _TOPIC_BANK[ib]
    kws_a = [_fold_pathology(k, komposita) for k in kws_a_raw]
    # Titel/Summary woertlich aus topic_a's Vokabular -- trifft topic_a's
    # Anfrage "kws_a[0] kws_a[1]" (siehe Query-Formel oben) mit hits()==2,
    # traegt aber topic_id=topic_b -> Lockvogel.
    decoy = {
        "id": f"n-{topic_b}-lockvogel", "path": f"/pruefstand/{topic_b}/lockvogel",
        "parent_path": f"/pruefstand/{topic_b}/0", "project_id": proj_b,
        "title": f"{kws_a[0]} {kws_a[1]} Uebersicht",
        "summary": f"{kws_a[0]}: {kws_a[1]} im Zusammenhang mit {proj_b}",
        "content": _build_content(rng2, kws_a, 40),
        "level": 2, "tags": [topic_b], "topic_id": topic_b,
        "lockvogel_for_topic": topic_a,
    }
    corpus["nodes"].append(decoy)


def _extend_generic_word_queries(corpus: dict) -> None:
    """Anfragen aus Woertern, die in (fast) jedem Dokument vorkommen --
    "Uebersicht" steht in jedem Knoten-Titel, "Zusammenhang" in jeder
    Summary (siehe Titel-/Summary-Format in _build_corpus_1_0_0). Wahrheit:
    keine dieser Anfragen hat ein echtes Thema -> alles, was zurueckkommt,
    ist ein Fehlalarm."""
    qi = len(corpus["queries"])
    w1, w2 = _GENERIC_WORDS
    for text in (f"{w1} {w2}", f"{w2} {w1}"):
        corpus["queries"].append({
            "id": f"q11-generic-{qi}", "text": text, "topic_id": "allerweltswort",
            "relevant_node_paths": [], "relevant_lesson_ids": [],
        })
        qi += 1


def _extend_topic_neighbors(corpus: dict, rng2: random.Random, flags: dict) -> None:
    """Zwei neue Themen mit ueberlappendem Wortschatz (teilen kws[0]
    woertlich), deren Dokumente sich trotzdem nicht gegenseitig beantworten
    -- jedes Thema bekommt eigene Knoten + Anfragen mit ausschliesslich
    eigenen relevant_node_paths."""
    for topic_id, kws_raw, project in (_NEIGHBOR_TOPIC_A, _NEIGHBOR_TOPIC_B):
        kws = [_fold_pathology(k, flags["komposita_umlaute"]) for k in kws_raw]
        paths = []
        for n in range(4):
            node_id = f"n-{topic_id}-{n}"
            path = f"/pruefstand/{topic_id}/{n}"
            node = {
                "id": node_id, "path": path,
                "parent_path": f"/pruefstand/{topic_id}/0" if n > 0 else None,
                "project_id": project, "title": f"{kws[n % len(kws)]} Uebersicht {n}",
                "summary": f"{kws[(n + 1) % len(kws)]}: {kws[n % len(kws)]} im Zusammenhang mit {project}",
                "content": _build_content(rng2, kws, rng2.randint(30, 80)),
                "level": 1 if n == 0 else 2, "tags": [topic_id], "topic_id": topic_id,
            }
            corpus["nodes"].append(node)
            paths.append(path)
        for q in range(2):
            text = f"{kws[q % len(kws)]} {kws[(q + 1) % len(kws)]}"
            corpus["queries"].append({
                "id": f"q11-nachbar-{topic_id}-{q}", "text": text, "topic_id": topic_id,
                "relevant_node_paths": list(paths), "relevant_lesson_ids": [],
            })
        # Lockvogel zwischen den beiden Nachbarthemen: Titel/Summary aus dem
        # EIGENEN 2-Wort-Anfragemuster (kws[0] kws[1], siehe Query-Schleife
        # oben), aber unter der topic_id des ANDEREN Nachbarn -- triggert nur
        # ueber die normale, bereits vorhandene 2-Wort-Anfrage (kein eigenes,
        # breiteres Anfragemuster, das den MIN_HITS-Gate erst bei hoher
        # Schwelle passieren wuerde und die Fehlalarmquote dort verzerrt).
        if flags["lockvogel_docs"]:
            # Titel/Summary aus TOPIC_ID's eigenem Vokabular (kws) -- trifft
            # topic_id's Anfrage "kws[0] kws[1]". Das Dokument selbst gehoert
            # aber zum ANDEREN Nachbarn (other_topic): geschriebene topic_id
            # ist other_topic, nicht topic_id -- exakt das Lockvogel-Muster
            # aus _extend_lockvogel_docs, nur zwischen den beiden neuen
            # Nachbarthemen statt zwischen zwei 1.0.0-Themen.
            other_topic = _NEIGHBOR_TOPIC_B[0] if topic_id == _NEIGHBOR_TOPIC_A[0] else _NEIGHBOR_TOPIC_A[0]
            corpus["nodes"].append({
                "id": f"n-{other_topic}-lockvogel-von-{topic_id}",
                "path": f"/pruefstand/{other_topic}/lockvogel-von-{topic_id}",
                "parent_path": f"/pruefstand/{other_topic}/0", "project_id": project,
                "title": f"{kws[0]} {kws[1]} Uebersicht",
                "summary": f"{kws[0]}: {kws[1]} im Zusammenhang mit {project}",
                "content": _build_content(rng2, kws, 40),
                "level": 2, "tags": [other_topic], "topic_id": other_topic,
                "lockvogel_for_topic": topic_id,
            })


def build_corpus(seed: int = DEFAULT_SEED, pathologies: dict | None = None,
                  version: str = CORPUS_VERSION) -> dict:
    """Oeffentliche Fabrik. version=CORPUS_VERSION (1.0.0, Default) liefert
    byteidentisch denselben Korpus wie vor diesem Auftrag -- siehe Selbsttest.
    version=CORPUS_VERSION_1_1 haengt drei zusaetzliche, "Nachsicht
    bestrafende" Pathologien an, gesteuert ueber dieselbe pathologies-dict
    (alte + neue Schluessel gemischt erlaubt)."""
    if version == CORPUS_VERSION:
        return _build_corpus_1_0_0(seed=seed, pathologies=pathologies)
    if version != CORPUS_VERSION_1_1:
        raise ValueError(f"unbekannte CORPUS_VERSION: {version!r} (bekannt: {CORPUS_VERSIONS})")

    old_keys = set(DEFAULT_PATHOLOGIES)
    given = pathologies or {}
    base = _build_corpus_1_0_0(seed=seed, pathologies={k: v for k, v in given.items() if k in old_keys})
    flags_1_1 = {**DEFAULT_PATHOLOGIES_1_1, **{k: v for k, v in given.items() if k not in old_keys}}

    corpus = {
        "version": CORPUS_VERSION_1_1,
        "seed": seed,
        "pathologies": {**base["pathologies"], **flags_1_1},
        "nodes": list(base["nodes"]),
        "lessons": list(base["lessons"]),
        "queries": list(base["queries"]),
    }
    rng2 = random.Random(seed ^ _V11_RNG_XOR)
    if flags_1_1["lockvogel_docs"]:
        _extend_lockvogel_docs(corpus, rng2, komposita=base["pathologies"]["komposita_umlaute"])
    if flags_1_1["generic_word_queries"]:
        _extend_generic_word_queries(corpus)
    if flags_1_1["topic_neighbors"]:
        _extend_topic_neighbors(corpus, rng2, {**base["pathologies"], **flags_1_1})

    corpus["checksum"] = _checksum(corpus)
    return corpus


def _checksum(corpus: dict) -> str:
    payload = {k: v for k, v in corpus.items() if k != "checksum"}
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def pathology_evidence(corpus: dict) -> dict:
    """Rohe Kennzahlen je Pathologie -- fuer Selbsttest und Bericht, keine
    Bewertung."""
    nodes, lessons, queries = corpus["nodes"], corpus["lessons"], corpus["queries"]
    dominant_topic = _REAL_TOPICS[0][0]
    total_draws = sum(1 for q in queries if q["relevant_node_paths"] or q["relevant_lesson_ids"])
    dominant_draws = sum(1 for q in queries if q["topic_id"] == dominant_topic)
    umlaut_chars = set("äöüßÄÖÜ")
    return {
        "dominant_query_share": (dominant_draws / total_draws) if total_draws else 0.0,
        "umlaut_node_count": sum(1 for n in nodes if umlaut_chars & set(n["title"] + n["content"])),
        "near_dup_node_count": sum(1 for n in nodes if n["path"].endswith("/dup")),
        "oversized_doc_count": sum(1 for n in nodes if len(n["content"].split()) > 2048),
        "multi_project_lesson_count": sum(1 for l in lessons if len(l["projects"]) > 1),
        "orphan_node_count": sum(
            1 for n in nodes
            if n["parent_path"] and n["parent_path"] not in {x["path"] for x in nodes}
        ),
        "zero_hit_query_count": sum(1 for q in queries if not q["relevant_node_paths"] and not q["relevant_lesson_ids"]),
        # Neu in 1.1.0 -- auf 1.0.0-Korpora immer 0, da diese Marker/Themen
        # dort nicht existieren.
        "lockvogel_doc_count": sum(1 for n in nodes if "lockvogel_for_topic" in n),
        "generic_word_query_count": sum(1 for q in queries if q["topic_id"] == "allerweltswort"),
        "topic_neighbor_pair_count": len({n["topic_id"] for n in nodes
                                           if n["topic_id"] in (_NEIGHBOR_TOPIC_A[0], _NEIGHBOR_TOPIC_B[0])}),
    }


def selftest() -> None:
    a = build_corpus()
    b = build_corpus()
    assert a["checksum"] == b["checksum"], "gleicher seed muss gleiche Pruefsumme ergeben"
    c = build_corpus(seed=DEFAULT_SEED + 1)
    assert a["checksum"] != c["checksum"], "anderer seed muss andere Pruefsumme ergeben"

    ev_all = pathology_evidence(a)
    assert ev_all["dominant_query_share"] > 0.3, "dominanter Knoten nicht sichtbar"
    assert ev_all["umlaut_node_count"] > 0
    assert ev_all["near_dup_node_count"] == 18, f"erwartet 18 Beinahe-Dubletten, war {ev_all['near_dup_node_count']}"
    assert ev_all["oversized_doc_count"] == 3, f"erwartet 3 ueberlange Knoten, war {ev_all['oversized_doc_count']}"
    assert ev_all["multi_project_lesson_count"] > 0
    assert ev_all["orphan_node_count"] > 0
    assert ev_all["zero_hit_query_count"] > 0

    # jede Pathologie einzeln abgeschaltet -> messbarer Unterschied
    off = build_corpus(pathologies={"dominant_node": False})
    ev_off = pathology_evidence(off)
    assert ev_off["dominant_query_share"] < ev_all["dominant_query_share"]

    off = build_corpus(pathologies={"komposita_umlaute": False})
    assert pathology_evidence(off)["umlaut_node_count"] == 0

    off = build_corpus(pathologies={"near_duplicates": False})
    assert pathology_evidence(off)["near_dup_node_count"] == 0

    off = build_corpus(pathologies={"oversized_docs": False})
    assert pathology_evidence(off)["oversized_doc_count"] == 0

    off = build_corpus(pathologies={"multi_project": False})
    assert pathology_evidence(off)["multi_project_lesson_count"] == 0

    off = build_corpus(pathologies={"orphan_parent": False})
    assert pathology_evidence(off)["orphan_node_count"] == 0

    off = build_corpus(pathologies={"zero_hit_queries": False})
    assert pathology_evidence(off)["zero_hit_query_count"] == 0

    print(f"korpus.py selftest ok (version={CORPUS_VERSION}, checksum={a['checksum'][:12]}..., "
          f"nodes={len(a['nodes'])}, lessons={len(a['lessons'])}, queries={len(a['queries'])})")

    # --- 1.1.0 (additiv, beruehrt keinen der obigen 1.0.0-Werte) ----------
    v11_a = build_corpus(version=CORPUS_VERSION_1_1)
    v11_b = build_corpus(version=CORPUS_VERSION_1_1)
    assert v11_a["checksum"] == v11_b["checksum"], "1.1.0: gleicher seed muss gleiche Pruefsumme ergeben"
    assert v11_a["version"] == CORPUS_VERSION_1_1
    assert v11_a["checksum"] != a["checksum"], "1.1.0 muss von 1.0.0 abweichen"

    ev11_all = pathology_evidence(v11_a)
    assert ev11_all["lockvogel_doc_count"] > 0
    assert ev11_all["generic_word_query_count"] > 0
    assert ev11_all["topic_neighbor_pair_count"] == 2

    off11 = build_corpus(version=CORPUS_VERSION_1_1, pathologies={"lockvogel_docs": False})
    assert pathology_evidence(off11)["lockvogel_doc_count"] == 0

    off11 = build_corpus(version=CORPUS_VERSION_1_1, pathologies={"generic_word_queries": False})
    assert pathology_evidence(off11)["generic_word_query_count"] == 0

    off11 = build_corpus(version=CORPUS_VERSION_1_1, pathologies={"topic_neighbors": False})
    ev_off11 = pathology_evidence(off11)
    assert ev_off11["topic_neighbor_pair_count"] == 0
    assert ev_off11["lockvogel_doc_count"] > 0, "lockvogel_docs bleibt unabhaengig von topic_neighbors wirksam"

    print(f"korpus.py selftest ok (version={CORPUS_VERSION_1_1}, checksum={v11_a['checksum'][:12]}..., "
          f"nodes={len(v11_a['nodes'])}, lessons={len(v11_a['lessons'])}, queries={len(v11_a['queries'])})")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out", type=str, default=None, help="Korpus als JSON schreiben")
    ap.add_argument("--corpus-version", type=str, default=CORPUS_VERSION, choices=list(CORPUS_VERSIONS))
    ap.add_argument("--pathology-off", action="append", default=[],
                     choices=list(DEFAULT_PATHOLOGIES) + list(DEFAULT_PATHOLOGIES_1_1))
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    pathologies = {name: False for name in args.pathology_off}
    corpus = build_corpus(seed=args.seed, pathologies=pathologies, version=args.corpus_version)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(corpus, f, ensure_ascii=False, indent=2)
        print(f"geschrieben: {args.out} (checksum={corpus['checksum'][:12]}...)")
    else:
        print(json.dumps({"version": corpus["version"], "seed": corpus["seed"],
                           "checksum": corpus["checksum"], "pathologies": corpus["pathologies"],
                           "counts": {"nodes": len(corpus["nodes"]), "lessons": len(corpus["lessons"]),
                                      "queries": len(corpus["queries"])}},
                          ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
