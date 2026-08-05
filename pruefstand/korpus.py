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
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys

CORPUS_VERSION = "1.0.0"

DEFAULT_SEED = 20260805

DEFAULT_PATHOLOGIES = {
    "dominant_node": True,
    "komposita_umlaute": True,
    "near_duplicates": True,
    "oversized_docs": True,
    "multi_project": True,
    "orphan_parent": True,
    "zero_hit_queries": True,
}

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


def build_corpus(seed: int = DEFAULT_SEED, pathologies: dict | None = None) -> dict:
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out", type=str, default=None, help="Korpus als JSON schreiben")
    ap.add_argument("--pathology-off", action="append", default=[], choices=list(DEFAULT_PATHOLOGIES))
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    pathologies = {name: False for name in args.pathology_off}
    corpus = build_corpus(seed=args.seed, pathologies=pathologies)
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
