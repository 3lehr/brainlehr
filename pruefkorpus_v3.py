"""Pruefkorpus V3 -- erfundene Gegenstaende mit Zahlenwerten, Aufgaben die
RECHNEN (Betreiber-Entwurf 2026-08-07). Ueberschreibt pruefkorpus.py und
pruefkorpus_v2.py NICHT -- die bleiben als gescheiterte Vorstufen stehen.

WARUM DIESE FORM (vs. v1/v2, die an Formulierungsermessen/Zirkularitaet
scheiterten, siehe deren eigene Docstrings und L-352afa):
  Wissen:   "Ein Glimberg hat 7 Zacken."
  Aufgabe:  "Wie viele Zacken haben drei Glimberge zusammen?"
  Pruefung: Antwort enthaelt "21" -- kein Ermessen, keine Prueffunktion
            strenger als das Wissen selbst.
  ohne Wissen -> unmoeglich zu erraten, faellt garantiert durch.
  mit Wissen  -> reine Rechnung, erzwingt BENUTZUNG (wer nur "7" wiederkaeut,
                 statt 7*3 zu rechnen, faellt durch -- Nutzungsnachweis).

ECHTER ABRUFWEG (Auflage 1): dieselbe Funktion, die im Betrieb vor jedem
Prompt feuert -- knowledge_recall_hook.query()/keywords()/hits() --,
importiert und unveraendert aufgerufen. Kein Wissen wird in den Prompt
kopiert; die erfundenen Knoten liegen als echte Zeilen in knowledge.db
zwischen dem echten Bestand.

RESTLOS ENTFERNBAR (Auflage 2): alle erfundenen Knoten tragen
project_id='pruefkorpus_v3' und Tag TAG -- delete_nodes() loescht exakt und
nur diese (WHERE project_id=?), FTS raeumt sich per Trigger (schema.sql)
automatisch mit.

KEYWORD-UEBERLAPP IST HIER ABSICHT, nicht Zirkularitaet: anders als v1/v2
(dort ging es um FORMULIERUNGS-Vermeidung bei echten, im Bestand bereits
vorhandenen Lehren/Fakten) ist hier das Wissen selbst erfunden -- es gibt
keine "eigene Formulierung" zu umgehen. Aufgabe und Knotentext teilen
absichtlich Name(+Plural)/Einheit/"zusammen", damit der reale bm25-Kanal
(MIN_HITS=3 verschiedene Substring-Treffer in Pfad+Titel+Summary, siehe
knowledge_recall_hook.hits()) ueberhaupt greifen KANN -- geprueft wird die
Rechnung, nicht die Tarnung der Formulierung.

Laufzeit-Modell: gemma4:e4b (NICHT gemma4:12b -- 140s/Aufruf waere bei
30 Faellen x 2 Aufrufen Stunden lang und stirbt mit dem Zug, Betreiber-
Auflage). Aufgaben/Pruefungen liegen als Daten (CASES) vor, answer() ist
austauschbar -- der Hauptfaden kann die Beantwortung spaeter ueber
Haiku-Subagenten fahren, ohne dieses Modul zu aendern.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sqlite3
import statistics
import sys
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parent
HUB = SHARED_KNOWLEDGE.parent
sys.path.insert(0, str(HUB / "scripts"))
sys.path.insert(0, str(SHARED_KNOWLEDGE / "schreibpruefstand"))
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_recall_hook as hook  # noqa: E402 -- echter Abrufweg
import messparameter  # noqa: E402 -- Parameterblock fuer jede Ergebnisdatei
import schreiblauf as sl  # noqa: E402 -- _call_with_retry fuer die Eichung/Vollauf

PROJECT_ID = "pruefkorpus_v3"
TAG = "pruefkorpus_v3_erfunden"
CAL_MODEL = "gemma4:e4b"  # schneller als gemma4:12b -- s. Moduldoc
CAL_TIMEOUT = 90.0
BANNED_RESULTS = {0, 1, 2, 10, 100}

OUT_JSON = SHARED_KNOWLEDGE / "runs" / "pruefkorpus_v3.json"
OUT_JSON_ERWEITERT = SHARED_KNOWLEDGE / "runs" / "pruefkorpus_v3_erweitert.json"

# Erweiterung 2026-08-07/08 (Auftrag Wiederholung/Grundrate/Positivkontrolle/
# Saettigung, 4 gemessene Maengel des bisherigen Pruefstands):
N_RUNS_DEFAULT = 3  # kleinste ungerade Zahl -- Median ohne Mittelung zweier
# Werte, und zwei identische Laeufe zeigten bereits 7 Faelle Streuung (Auftrag
# Punkt 1); 3 ist der billigste Schritt, der einen echten Median liefert statt
# nur "zwei Werte, nimm den Mittelpunkt".
GRUNDRATE_ZIEL_ANTEIL = 0.80  # Betriebsschaetzung Auftrag Punkt 2 -- die im
# 42er-Korpus gemessenen 14% Eichfaelle sind ein Laborartefakt, kein Feldwert.

ZAHLWORT = {1: "ein", 2: "zwei", 3: "drei", 4: "vier", 5: "fuenf", 6: "sechs"}


def _plural_noun(anzahl: int, name: str) -> str:
    """Name ohne Mehrzahl-'e' bei anzahl==1 (sonst Einzahl-Zahlwort +
    Mehrzahl-Endung, s. Vorlagenfehler-Befund v3-16/v3-17, 2026-08-07)."""
    return name if anzahl == 1 else f"{name}e"


def _plural_name(anzahl: int, name: str) -> str:
    return f"{ZAHLWORT[anzahl]} {_plural_noun(anzahl, name)}"


def _haben(anzahl: int) -> str:
    return "hat" if anzahl == 1 else "haben"

# ---------------------------------------------------------------------------
# Erfundene Gegenstaende -- werden als echte Knoten eingespielt.
# (slug, name, einheit, wert)
GEGENSTAENDE = [
    ("glimberg", "Glimberg", "Zacken", 7),
    ("trebolit", "Trebolit", "Ringe", 9),
    ("fasnerkel", "Fasnerkel", "Noppen", 6),
    ("quandtor", "Quandtor", "Facetten", 11),
    ("bilkrone", "Bilkrone", "Zaehne", 13),
    ("snarwal", "Snarwal", "Kerben", 8),
    ("worbel", "Worbel", "Streben", 12),
    ("kessnitt", "Kessnitt", "Rippen", 14),
    ("dromfeld", "Dromfeld", "Falten", 17),
    ("miglor", "Miglor", "Speichen", 16),
    ("pentrusch", "Pentrusch", "Dornen", 19),
    ("halbsted", "Halbsted", "Kanten", 18),
    ("orbeling", "Orbeling", "Waben", 23),
    ("tuckram", "Tuckram", "Stege", 22),
    # aehnlich benannte Paare (unterscheiden sich im letzten Buchstaben) --
    # pruefen, ob der Abruf den RICHTIGEN zieht statt irgendeinen.
    ("velunit", "Velunit", "Klammern", 21),
    ("velunip", "Velunip", "Klammern", 15),
    ("frastek", "Frastek", "Naehte", 5),
    ("frastel", "Frastel", "Naehte", 24),
    # weiteres aehnlich-benanntes Paar (2026-08-07-Erweiterung, Sorte 1).
    ("moldrian", "Moldrian", "Sprossen", 39),
    ("moldrion", "Moldrion", "Sprossen", 26),
    # gleicher Name, zwei Eintraege mit VERSCHIEDENER Eigenschaft (Sorte 2):
    # Abruf muss die Aussage zur gefragten Eigenschaft ziehen, nicht die
    # andere Aussage ueber denselben Gegenstand.
    ("kraiber_zacken", "Kraiber", "Zacken", 31),
    ("kraiber_gewicht", "Kraiber", "Kilo", 4),
    ("silphon_kanten", "Silphon", "Kanten", 33),
    ("silphon_hoehe", "Silphon", "Meter", 2),
    # gleiche Einheit, zwei VERSCHIEDENE Gegenstaende, in einer Aufgabe
    # kombiniert (Sorte 3): zwingt zu zwei echten Treffern statt einem
    # doppelt verwendeten.
    ("nafur", "Nafur", "Riemen", 41),
    ("boltrek", "Boltrek", "Riemen", 37),
    ("zirkulat", "Zirkulat", "Bahnen", 43),
    ("torkade", "Torkade", "Bahnen", 29),
]
_G = {slug: (name, einheit, wert) for slug, name, einheit, wert in GEGENSTAENDE}

# Sorte-2-Paare (gleicher Name, andere Eigenschaft): die Partner-Einheit muss
# EXTRA im Ablenkertext stehen (Bindeglied-Satz in node_text_eigenschaft()),
# sonst teilt der Ablenker mit der Aufgabe zu wenig Woerter fuer MIN_HITS und
# taucht im Abruf nie auf -- geprueft/verworfen per Eichung 2026-08-07 (roher
# Befund: Kraiber/Kilo-Knoten mit reinem node_text() blieb bei 2 Treffern,
# MIN_HITS=3 nicht erreicht, Ablenker kam im Live-Abruf nicht mit).
EIGENSCHAFT_PAARE = [("kraiber_zacken", "kraiber_gewicht"), ("silphon_kanten", "silphon_hoehe")]
_PARTNER_EINHEIT = {}
for _a, _b in EIGENSCHAFT_PAARE:
    _PARTNER_EINHEIT[_a] = _G[_b][1]
    _PARTNER_EINHEIT[_b] = _G[_a][1]

# Sorte 4 -- veraltete Fassung: zwei Knoten zum selben Gegenstand, der alte
# traegt gilt_bis (echte Normschicht-Spalte, s. schema.sql). Eigene Liste,
# weil (anders als GEGENSTAENDE) zwei Werte + zwei Knoten pro Eintrag noetig
# sind. (slug, name, einheit, wert_alt, wert_aktuell)
VERALTET = [
    ("drallmesser", "Drallmesser", "Ringe", 12, 45),
    ("quirlband", "Quirlband", "Spulen", 9, 52),
]
_V = {slug: (name, einheit, wert_alt, wert_neu) for slug, name, einheit, wert_alt, wert_neu in VERALTET}
GILT_BIS_ALT = "2026-01-01T00:00:00+0100"  # vor 'heute' -- eindeutig ueberholt

# Nicht eingespielte Fantasiewoerter fuer die Eichfaelle ohne Wissen.
EICHFALL_WOERTER = [
    ("Fluxnorbel", "Ecken"), ("Krispatur", "Zapfen"), ("Dellwark", "Haken"),
    ("Tangvolk", "Bogen"), ("Orsprint", "Riegel"), ("Halmquin", "Spangen"),
]


def node_text(name: str, einheit: str, wert: int) -> str:
    """Summary/Content eines Knotens -- enthaelt Singular UND Plural(+e) des
    Namens sowie 'zusammen', damit hook.hits() (Substring-Match) bei
    MIN_HITS=3 mit ueblicher Aufgaben-Phrasierung ueberhaupt greifen kann."""
    return (f"Ein {name} hat {wert} {einheit}. Mehrere {name}e zusammen "
            f"ergeben entsprechend mehr {einheit}.")


def node_text_eigenschaft(name: str, einheit: str, wert: int, einheit_partner: str) -> str:
    """Sorte 2: wie node_text(), aber mit Bindeglied-Satz zur Partner-
    Einheit -- ohne den Satz teilt der Ablenkerknoten zu wenige Woerter mit
    einer Aufgabe zur ANDEREN Eigenschaft und erreicht MIN_HITS nicht (s.
    Kommentar bei EIGENSCHAFT_PAARE)."""
    return (f"Ein {name} hat {wert} {einheit} (getrennt von den "
            f"{einheit_partner}-Angaben). Mehrere {name}e zusammen ergeben "
            f"entsprechend mehr {einheit}.")


def node_text_veraltet(name: str, einheit: str, wert_alt: int) -> str:
    """Sorte 4 (alter Knoten): traegt dieselben Substrings wie node_text()
    (Name/Plural/'zusammen'), damit er ebenfalls MIN_HITS erreicht und im
    Abruf AUFTAUCHT -- sonst laenkt er nichts ab (s. Moduldoc Eichung)."""
    return (f"Ein {name} hatte frueher {wert_alt} {einheit}. Mehrere {name}e "
            f"zusammen ergaben damals entsprechend mehr {einheit}. Diese Angabe "
            f"ist veraltet und nicht mehr gueltig.")


def node_text_aktuell(name: str, einheit: str, wert_aktuell: int, wert_alt: int) -> str:
    return (f"Ein {name} hat aktuell {wert_aktuell} {einheit}. Mehrere {name}e "
            f"zusammen ergeben entsprechend mehr {einheit} (ersetzt die veraltete "
            f"Angabe von {wert_alt} {einheit}).")


# ---------------------------------------------------------------------------
# Aufgaben -- Kennung, Kategorie, Aufgabentext, Ziel-Pfade, erwartete Zahl.

def _task_einzelwert(slug: str, anzahl: int) -> tuple[str, int]:
    name, einheit, wert = _G[slug]
    return (f"Wie viele {einheit} {_haben(anzahl)} {_plural_name(anzahl, name)} zusammen?", wert * anzahl)


def _task_kombiniert(slug1: str, anzahl1: int, slug2: str, anzahl2: int) -> tuple[str, int]:
    name1, einheit1, wert1 = _G[slug1]
    name2, einheit2, wert2 = _G[slug2]
    task = (f"{_plural_name(anzahl1, name1)} {_haben(anzahl1)} zusammen wie viele {einheit1}? "
            f"Und {_plural_name(anzahl2, name2)} {_haben(anzahl2)} zusammen wie viele {einheit2}? "
            f"Nenne die Gesamtsumme aus beiden Werten ({einheit1} der {_plural_noun(anzahl1, name1)} plus "
            f"{einheit2} der {_plural_noun(anzahl2, name2)}).")
    return task, wert1 * anzahl1 + wert2 * anzahl2


def _zahl_ziffer(anzahl: int, name: str) -> str:
    """Ziffer statt ZAHLWORT (nur Sorte 5): hook.keywords() haelt nur Woerter
    ab 4 Zeichen fest, eine Ziffer (1-6, 1 Zeichen) frisst also KEIN Keyword-
    Kontingent -- bei drei Objekten in einer Aufgabe reicht das Kontingent
    (out[:8] in keywords(), s. Moduldoc) sonst nicht fuer alle drei Namen."""
    return f"{anzahl} {_plural_noun(anzahl, name)}"


def _task_kombiniert3(slug1: str, a1: int, slug2: str, a2: int, slug3: str, a3: int) -> tuple[str, int]:
    """Sorte 5 (Haertung Weg 2, 2026-08-07): DREI Ziel-Knoten in einer Aufgabe --
    MAX_NODES=3 (knowledge_recall_hook.py) laesst dabei keinen Slack mehr, jeder
    zusaetzliche Kandidat verdraengt einen der drei echten Treffer. KEIN
    zusaetzlicher Ablenker hier (s. _task_kombiniert_ablenker Docstring, warum
    das am Keyword-Kontingent scheitert). Ziffern statt ZAHLWORT (s.
    _zahl_ziffer): mit drei ZAHLWORT-Namen plus 'zusammen'/'viele' sprengt die
    Aufgabe sonst das 8er-Keyword-Kontingent, bevor das dritte Ziel ueberhaupt
    als Keyword auftaucht -- roh geprueft 2026-08-07 (kws blieben bei den
    ersten zwei Objekten + Zahlwoertern haengen, drittes Ziel bekam 0 eigene
    Treffer)."""
    name1, einheit1, wert1 = _G[slug1]
    name2, einheit2, wert2 = _G[slug2]
    name3, einheit3, wert3 = _G[slug3]
    task = (f"{_zahl_ziffer(a1, name1)} {_haben(a1)} zusammen wie viele {einheit1}? "
            f"Und {_zahl_ziffer(a2, name2)} {_haben(a2)} zusammen wie viele {einheit2}? "
            f"Und {_zahl_ziffer(a3, name3)} {_haben(a3)} zusammen wie viele {einheit3}? "
            f"Nenne die Gesamtsumme aus allen drei Werten.")
    return task, wert1 * a1 + wert2 * a2 + wert3 * a3


def _task_kombiniert_ablenker(slug1: str, a1: int, slug2: str, a2: int,
                               ablenker_slugs: list[str]) -> tuple[str, int]:
    """Sorte 5b (Haertung Weg 1+2 kombiniert, 2026-08-07): ZWEI Ziel-Knoten +
    ZWEI benannte Ablenker (je einer pro Ziel, teilt dessen Einheit) = VIER
    MIN_HITS-faehige Kandidaten fuer NUR drei Ausgabeplaetze (MAX_NODES=3) --
    echter Overlauf, nicht nur volle Ausnutzung. Mit nur EINEM Ablenker
    (2 Ziele + 1 Ablenker = 3 Kandidaten) passen alle drei ohne Verdraengung
    in die drei Plaetze -- roh gemessen 2026-08-07: Quote blieb bei 36/36,
    weil niemand verdraengt werden musste. Reiner Sorte-5-Ansatz (drei ECHTE
    Ziele + Ablenker) scheitert am 8er-Keyword-Kontingent von hook.keywords():
    drei Objekt-Namen+Einheiten (6 Woerter) plus 'zusammen'/'viele' fuellen es
    bereits vollstaendig. Ziffern statt ZAHLWORT (s. _zahl_ziffer): sonst
    fressen zwei Zahlwoerter zwei der acht Keyword-Plaetze. '(nicht X)' statt
    '(nicht zu verwechseln mit X)': 'nicht' ist Stoppwort (kostenlos), 'zu'/
    'verwechseln'/'mit' fressen sonst weitere Plaetze -- bei ZWEI Ablenkern
    reicht das Kontingent (6 Kernwoerter + zusammen + viele = exakt 8) nur mit
    der knappsten Formulierung; erste Fassung mit 'verwechseln' liess den
    zweiten Ablenker aus dem Kontingent fallen (roh geprueft 2026-08-07)."""
    name1, einheit1, wert1 = _G[slug1]
    name2, einheit2, wert2 = _G[slug2]
    name_a1 = _G[ablenker_slugs[0]][0]
    name_a2 = _G[ablenker_slugs[1]][0]
    task = (f"{_zahl_ziffer(a1, name1)} (nicht {name_a1}) {_haben(a1)} zusammen wie viele {einheit1}? "
            f"Und {_zahl_ziffer(a2, name2)} (nicht {name_a2}) {_haben(a2)} zusammen wie viele {einheit2}? "
            f"Nenne die Gesamtsumme aus beiden Werten.")
    return task, wert1 * a1 + wert2 * a2


def _task_aehnlich(slug_ziel: str, anzahl: int, slug_ablenker: str) -> tuple[str, int, int]:
    name, einheit, wert = _G[slug_ziel]
    name_ablenker, _, wert_ablenker = _G[slug_ablenker]
    task = (f"Wie viele {einheit} {_haben(anzahl)} {_plural_name(anzahl, name)} zusammen "
            f"(nicht zu verwechseln mit {name_ablenker})?")
    return task, wert * anzahl, wert_ablenker * anzahl


def _task_eigenschaft(slug_richtig: str, anzahl: int, slug_falsch: str) -> tuple[str, int, int]:
    """Sorte 2: slug_richtig/slug_falsch teilen denselben Anzeigenamen (zwei
    Knoten, zwei Eigenschaften) -- Aufgabe fragt nach EINER Eigenschaft."""
    task, korrekt = _task_einzelwert(slug_richtig, anzahl)
    _, _, wert_falsch = _G[slug_falsch]
    return task, korrekt, wert_falsch * anzahl


def _task_gleiche_einheit(slug1: str, anzahl1: int, slug2: str, anzahl2: int) -> tuple[str, int, int]:
    """Sorte 3: slug1/slug2 sind verschiedene Gegenstaende mit GLEICHER
    Einheit, in einer Aufgabe kombiniert -- zwingt zu zwei echten Treffern.
    Fehlermodus (falsche_zahl): nur ein Eintrag gezogen, auf die
    Gesamtanzahl beider Gegenstaende angewandt."""
    name1, einheit, wert1 = _G[slug1]
    name2, einheit2, wert2 = _G[slug2]
    assert einheit == einheit2, f"{slug1}/{slug2}: Einheiten weichen ab ({einheit} != {einheit2})"
    task = (f"{_plural_name(anzahl1, name1)} und {_plural_name(anzahl2, name2)} "
            f"zusammen: wie viele {einheit} sind das insgesamt?")
    korrekt = wert1 * anzahl1 + wert2 * anzahl2
    falsch = wert1 * (anzahl1 + anzahl2)
    return task, korrekt, falsch


def _task_veraltet(slug: str, anzahl: int) -> tuple[str, int, int]:
    name, einheit, wert_alt, wert_aktuell = _V[slug]
    task = (f"Wie viele {einheit} {_haben(anzahl)} {_plural_name(anzahl, name)} zusammen "
            f"(aktueller Stand)?")
    return task, wert_aktuell * anzahl, wert_alt * anzahl


def _task_eichfall(name: str, einheit: str, anzahl: int) -> str:
    return f"Wie viele {einheit} haben {ZAHLWORT[anzahl]} {name} zusammen?"


def build_cases() -> list[dict]:
    cases: list[dict] = []
    n = 0

    def add(kategorie: str, task: str, erwartete_zahl: int | None, ziel_slugs: list[str],
            falsche_zahl: int | None = None, ablenker_slugs: list[str] | None = None):
        nonlocal n
        n += 1
        cases.append({
            "kennung": f"v3-{n:02d}", "kategorie": kategorie, "task": task,
            "erwartete_zahl": erwartete_zahl,
            "ziel_pfade": [f"/{PROJECT_ID}/{s}" for s in ziel_slugs],
            "falsche_zahl": falsche_zahl,  # Zahl bei Ablenker- statt Zieltreffer (Auflage 3)
            "ablenker_slugs": ablenker_slugs or [],  # Sorte 5b: echte Overlauf-Konkurrenten
        })

    # einfache Rechnung: ein Wert, eine Operation (14 Faelle)
    for slug, anzahl in [
        ("glimberg", 3), ("trebolit", 4), ("fasnerkel", 5), ("quandtor", 3),
        ("bilkrone", 2), ("snarwal", 6), ("worbel", 5), ("kessnitt", 3),
        ("dromfeld", 2), ("miglor", 5), ("pentrusch", 2), ("halbsted", 3),
        ("orbeling", 2), ("tuckram", 3),
    ]:
        task, zahl = _task_einzelwert(slug, anzahl)
        add("einzelwert", task, zahl, [slug])

    # mehrere Werte aus verschiedenen Knoten kombinieren (8 Faelle)
    for slug1, a1, slug2, a2 in [
        ("glimberg", 1, "trebolit", 2), ("fasnerkel", 1, "quandtor", 3),
        ("bilkrone", 1, "snarwal", 4), ("worbel", 1, "kessnitt", 2),
        ("dromfeld", 1, "miglor", 2), ("pentrusch", 1, "halbsted", 2),
        ("orbeling", 1, "tuckram", 2), ("glimberg", 2, "kessnitt", 1),
    ]:
        task, zahl = _task_kombiniert(slug1, a1, slug2, a2)
        add("kombiniert", task, zahl, [slug1, slug2])

    # aehnlich benannte Gegenstaende -- Abruf muss den richtigen ziehen (2 Faelle)
    task, zahl, falsch = _task_aehnlich("velunit", 3, "velunip")
    add("aehnlich", task, zahl, ["velunit"], falsch)
    task, zahl, falsch = _task_aehnlich("frastek", 4, "frastel")
    add("aehnlich", task, zahl, ["frastek"], falsch)

    # Eichfaelle ohne passendes Wissen -- richtige Antwort ist "weiss ich nicht" (6 Faelle)
    for (wort, einheit), anzahl in zip(EICHFALL_WOERTER, [2, 3, 4, 2, 3, 4]):
        task = _task_eichfall(wort, einheit, anzahl)
        add("eichfall", task, None, [])

    # -- Ab hier Erweiterung 2026-08-07 (Auflage 1: 30 Faelle oben bleiben
    # unveraendert, nur ergaenzt) -- vier Sorten NAHER Ablenkung, je mehrere
    # Faelle (s. Moduldoc-Auftrag "AUFGABE").

    # Sorte 1 (aehnlicher Name, andere Zahl) -- 2 weitere Faelle, neues Paar.
    task, zahl, falsch = _task_aehnlich("moldrian", 5, "moldrion")
    add("aehnlich", task, zahl, ["moldrian"], falsch)
    task, zahl, falsch = _task_aehnlich("frastek", 1, "frastel")
    add("aehnlich", task, zahl, ["frastek"], falsch)

    # Sorte 2 (gleicher Name, andere Eigenschaft) -- 2 Faelle.
    task, zahl, falsch = _task_eigenschaft("kraiber_zacken", 2, "kraiber_gewicht")
    add("eigenschaft", task, zahl, ["kraiber_zacken"], falsch)
    task, zahl, falsch = _task_eigenschaft("silphon_kanten", 3, "silphon_hoehe")
    add("eigenschaft", task, zahl, ["silphon_kanten"], falsch)

    # Sorte 3 (gleiche Einheit, zwei Gegenstaende in einer Aufgabe) -- 2 Faelle.
    task, zahl, falsch = _task_gleiche_einheit("nafur", 2, "boltrek", 3)
    add("gleiche_einheit", task, zahl, ["nafur", "boltrek"], falsch)
    task, zahl, falsch = _task_gleiche_einheit("zirkulat", 3, "torkade", 2)
    add("gleiche_einheit", task, zahl, ["zirkulat", "torkade"], falsch)

    # Sorte 4 (veraltete Fassung, gilt_bis) -- 2 Faelle.
    task, zahl, falsch = _task_veraltet("drallmesser", 3)
    add("veraltet", task, zahl, ["drallmesser"], falsch)
    task, zahl, falsch = _task_veraltet("quirlband", 4)
    add("veraltet", task, zahl, ["quirlband"], falsch)

    # Sorte 5 (Haertung Weg 2, 2026-08-07): DREI Ziel-Knoten in einer Aufgabe --
    # MAX_NODES=3 (knowledge_recall_hook.py) laesst keinen Slack mehr.
    task, zahl = _task_kombiniert3("pentrusch", 2, "halbsted", 3, "orbeling", 2)
    add("kombiniert3", task, zahl, ["pentrusch", "halbsted", "orbeling"])
    task, zahl = _task_kombiniert3("tuckram", 2, "dromfeld", 3, "miglor", 2)
    add("kombiniert3", task, zahl, ["tuckram", "dromfeld", "miglor"])

    # Sorte 5b (Weg 1+2 kombiniert, 2026-08-07): ZWEI Ziele + EIN benannter
    # Ablenker (Partner eines bestehenden Aehnlich-Paares, teilt die Einheit
    # mit einem der zwei Ziele) = drei MIN_HITS-faehige Kandidaten fuer drei
    # Ausgabeplaetze (MAX_NODES=3) -- kein Slack (s. _task_kombiniert_ablenker
    # Docstring, warum drei ECHTE Ziele + Ablenker am Keyword-Kontingent scheitert).
    task, zahl = _task_kombiniert_ablenker("velunit", 3, "frastek", 2, ["velunip", "frastel"])
    add("kombiniert_ablenker", task, zahl, ["velunit", "frastek"], ablenker_slugs=["velunip", "frastel"])
    task, zahl = _task_kombiniert_ablenker("moldrian", 2, "velunit", 4, ["moldrion", "velunip"])
    add("kombiniert_ablenker", task, zahl, ["moldrian", "velunit"], ablenker_slugs=["moldrion", "velunip"])

    return cases


CASES = build_cases()


# ---------------------------------------------------------------------------
# Auftrag B (Grundrate): zusaetzliche Eichfaelle ueber die 6 vorhandenen
# hinaus, einstellbar -- CASES/build_cases() bleiben unveraendert (Auflage 1),
# das hier ist rein additiv und nur aktiv, wenn ausdruecklich angefordert.

_EICH_SILBEN_A = ["Flux", "Kris", "Dell", "Tang", "Ors", "Halm", "Wob", "Zirn",
                   "Plor", "Kesk", "Nuv", "Trab", "Glorn", "Speft", "Morq", "Yswal",
                   "Brindt", "Quolm"]
_EICH_SILBEN_B = ["norbel", "patur", "wark", "volk", "print", "quin", "belat", "ulor",
                   "aster", "idom", "enkar", "ostrum", "avil", "ycht", "ombrik",
                   "aldan", "ovist", "ekrum"]
_EICH_EINHEITEN_POOL = ["Ecken", "Zapfen", "Haken", "Bogen", "Riegel", "Spangen",
                          "Klinken", "Fasern", "Splitter", "Ranken", "Duebel",
                          "Laschen", "Knoten", "Falze", "Kerne", "Naben"]


def _generate_eichfall_pool(n_total: int) -> list[tuple[str, str]]:
    """Eichfaelle ohne Wissen: erste len(EICHFALL_WOERTER) wie bisher
    (unveraendert/vergleichbar), Rest deterministisch aus Silbenkombinationen
    -- vermeidet, hunderte Fantasiewoerter von Hand zu pflegen, um die
    Grundrate einstellbar zu machen (Auftrag Punkt 2/B). Kollisionscheck
    gegen echte Namen (GEGENSTAENDE/VERALTET) per hook.fold_de-Substring,
    damit kein Eichfall zufaellig zu einem echten Wissensknoten passt."""
    pool = list(EICHFALL_WOERTER)
    if n_total <= len(pool):
        return pool[:n_total]
    echte_namen = {hook.fold_de(g[1]) for g in GEGENSTAENDE} | {hook.fold_de(v[1]) for v in VERALTET}
    for a, b in itertools.product(_EICH_SILBEN_A, _EICH_SILBEN_B):
        if len(pool) >= n_total:
            break
        wort = a + b
        folded = hook.fold_de(wort)
        if any(folded in en or en in folded for en in echte_namen):
            continue
        if wort in {w for w, _e in pool}:
            continue
        einheit = _EICH_EINHEITEN_POOL[len(pool) % len(_EICH_EINHEITEN_POOL)]
        pool.append((wort, einheit))
    return pool[:n_total]


def build_grundrate_cases(n_extra: int) -> list[dict]:
    """Zusaetzliche Eichfall-Faelle, eigene Kategorie 'eichfall_grundrate'
    fuer getrennte Berichterstattung (Auflage B: loesbare Quote darf nicht
    in der Eichfall-Masse verduennen)."""
    if n_extra <= 0:
        return []
    pool = _generate_eichfall_pool(len(EICHFALL_WOERTER) + n_extra)[len(EICHFALL_WOERTER):]
    extra = []
    for i, (wort, einheit) in enumerate(pool):
        anzahl = [2, 3, 4, 5][i % 4]
        extra.append({
            "kennung": f"v3g-{i + 1:03d}", "kategorie": "eichfall_grundrate",
            "task": _task_eichfall(wort, einheit, anzahl),
            "erwartete_zahl": None, "ziel_pfade": [], "falsche_zahl": None, "ablenker_slugs": [],
        })
    return extra


def target_grundrate_n_extra(ziel_anteil: float = GRUNDRATE_ZIEL_ANTEIL) -> int:
    """Wie viele zusaetzliche Eichfaelle noetig, damit der Eichfall-Anteil am
    Gesamtkorpus ziel_anteil erreicht (Auftrag Punkt 2: Betriebsschaetzung
    ~80%, die gemessenen 14% im 42er-Korpus sind das Laborartefakt)."""
    loesbare = sum(1 for c in CASES if c["erwartete_zahl"] is not None)
    vorhandene_eichfaelle = len(CASES) - loesbare
    ziel_eichfaelle = round(loesbare * ziel_anteil / (1 - ziel_anteil))
    return max(0, ziel_eichfaelle - vorhandene_eichfaelle)


# ---------------------------------------------------------------------------
# DB: einspielen / entfernen (echter Bestand, restlos loeschbar ueber project_id)

def _insert_node(conn: sqlite3.Connection, node_id: str, path: str, name: str, text: str,
                  gilt_bis: str | None = None) -> None:
    conn.execute(
        "INSERT INTO knowledge_nodes "
        "(id, path, parent_path, project_id, title, summary, content, level, "
        " tags, source, confidence, anlass, gilt_bis, norm_entscheidung) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (node_id, path, None, PROJECT_ID, name, text, text,
         0, json.dumps([TAG]), f"{PROJECT_ID} (erfunden, restlos loeschbar via delete_nodes())",
         0.8, "skript", gilt_bis,
         # keine_norm (Auftrag 2026-08-08): erfundene Pruefkorpus-Knoten sind
         # Fakten, kein norm_rang -- gilt_bis bleibt hier wie bisher ein
         # inertes "veraltet"-Flag (_geltung_status wirkt nur bei gesetztem
         # norm_rang, siehe knowledge_mcp_server.py), kein Normschicht-Feld.
         "keine_norm"),
    )


def insert_nodes(conn: sqlite3.Connection) -> None:
    for slug, name, einheit, wert in GEGENSTAENDE:
        if slug in _PARTNER_EINHEIT:
            text = node_text_eigenschaft(name, einheit, wert, _PARTNER_EINHEIT[slug])
        else:
            text = node_text(name, einheit, wert)
        _insert_node(conn, f"pk3-{slug}", f"/{PROJECT_ID}/{slug}", name, text)
    for slug, name, einheit, wert_alt, wert_aktuell in VERALTET:
        _insert_node(conn, f"pk3-{slug}-alt", f"/{PROJECT_ID}/{slug}_alt", name,
                      node_text_veraltet(name, einheit, wert_alt), gilt_bis=GILT_BIS_ALT)
        _insert_node(conn, f"pk3-{slug}", f"/{PROJECT_ID}/{slug}", name,
                      node_text_aktuell(name, einheit, wert_aktuell, wert_alt))
    conn.commit()


def delete_nodes(conn: sqlite3.Connection) -> int:
    """Loeschbefehl (Auflage 2/Abnahme 4): trifft NUR project_id='pruefkorpus_v3'.
    FTS raeumt sich per AFTER-DELETE-Trigger (schema.sql) automatisch mit."""
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM knowledge_nodes WHERE project_id=?", (PROJECT_ID,)).fetchall()]
    if ids:
        placeholders = ",".join("?" * len(ids))
        conn.execute(
            f"DELETE FROM knowledge_embeddings WHERE kind='node' AND ref_id IN ({placeholders})", ids)
    cur = conn.execute("DELETE FROM knowledge_nodes WHERE project_id=?", (PROJECT_ID,))
    conn.commit()
    return cur.rowcount


# ---------------------------------------------------------------------------
# Abruf (echter Weg) + Beantwortung (austauschbar)

def retrieve(task: str) -> tuple[str | None, list]:
    kws = hook.keywords(task)
    if len(kws) < hook.MIN_HITS:
        return None, []
    nodes, lessons = hook.query(kws, cwd=None, prompt=task)
    if not nodes:
        return None, nodes
    context = "\n".join(f"- {n['title']}: {n['summary']}" for n in nodes)
    return context, nodes


def answer(task: str, context: str | None, model: str = CAL_MODEL) -> str:
    """Austauschbar (Docstring-Auflage): spaeter per Haiku-Subagent aufrufbar,
    hier per lokalem Ollama fuer Eichung/Vollauf."""
    if context:
        prompt = (f"Bekanntes Wissen:\n{context}\n\nFrage: {task}\n"
                   "Antworte NUR mit der Zahl, keine Erklaerung. Wenn du sie nicht "
                   "berechnen kannst, antworte 'weiss ich nicht'.")
    else:
        prompt = (f"Frage: {task}\nAntworte NUR mit der Zahl, keine Erklaerung. "
                   "Wenn du sie nicht weisst, antworte 'weiss ich nicht'.")
    raw, err, _retries = sl._call_with_retry(prompt, model=model, base_url=sl.DEFAULT_OLLAMA_URL, timeout=CAL_TIMEOUT)
    return (raw or f"[FEHLER: {err}]").strip()


def check(raw: str, erwartete_zahl: int | None) -> bool:
    if erwartete_zahl is None:
        return str(erwartete_zahl) not in raw  # Platzhalter, siehe run_all() Zeilenausgabe
    return str(erwartete_zahl) in raw


def target_hit(case: dict, nodes: list) -> bool:
    gefunden = {n["path"] for n in nodes}
    return all(p in gefunden for p in case["ziel_pfade"]) if case["ziel_pfade"] else False


def classify(case: dict, raw: str, nodes: list) -> str:
    """Auflage 4: trennt 'nichts gefunden' von 'Falsches gefunden' von
    'richtig gefunden, falsch gerechnet' -- bisher (vor dieser Erweiterung)
    gab es nur bestanden/nicht-bestanden in einem Topf."""
    if case["erwartete_zahl"] is None:
        return "eichfall"
    if check(raw, case["erwartete_zahl"]):
        return "bestanden"
    if not nodes:
        return "kein_treffer"
    if not target_hit(case, nodes):
        return "falscher_treffer"
    return "richtig_falsch_gerechnet"


# ---------------------------------------------------------------------------
# Eichung (Abnahme 1) + Vollauf (Abnahme 2-4)

def eichung(conn: sqlite3.Connection, model: str = CAL_MODEL) -> dict:
    """EIN Fall (v3-01, Glimberg -- das Entwurfsbeispiel), VOR dem Rest:
    ohne Abruf muss durchfallen, mit Abruf bestehen. Rohe Ausgabe beider Laeufe."""
    case = CASES[0]
    ohne = answer(case["task"], None, model=model)
    context, nodes = retrieve(case["task"])
    mit = answer(case["task"], context, model=model)
    result = {
        "kennung": case["kennung"], "task": case["task"], "erwartete_zahl": case["erwartete_zahl"],
        "falsche_zahl": case["falsche_zahl"],
        "ohne_abruf_roh": ohne, "ohne_abruf_bestanden": check(ohne, case["erwartete_zahl"]),
        "mit_abruf_roh": mit, "mit_abruf_bestanden": check(mit, case["erwartete_zahl"]),
        "ziel_gefunden": target_hit(case, nodes),
        "abgerufene_pfade": [n["path"] for n in nodes],
    }
    result["einordnung"] = classify(case, mit, nodes)
    ok = (not result["ohne_abruf_bestanden"]) and result["mit_abruf_bestanden"] and result["ziel_gefunden"]
    result["eichung_ok"] = ok
    return result


def run_all(model: str = CAL_MODEL, out_path: Path = OUT_JSON) -> dict:
    conn = sqlite3.connect(hook.DB)
    conn.row_factory = sqlite3.Row
    vorher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    insert_nodes(conn)
    print(f"Bestand vorher: {vorher}. {len(GEGENSTAENDE)} erfundene Knoten eingespielt.", flush=True)

    eich = eichung(conn, model=model)
    print(f"\nEICHUNG {eich['kennung']}  erwartet={eich['erwartete_zahl']}", flush=True)
    print(f"  ohne Abruf: {eich['ohne_abruf_roh']!r}  bestanden={eich['ohne_abruf_bestanden']}", flush=True)
    print(f"  mit  Abruf: {eich['mit_abruf_roh']!r}  bestanden={eich['mit_abruf_bestanden']}  "
          f"ziel_gefunden={eich['ziel_gefunden']}", flush=True)
    if not eich["eichung_ok"]:
        print("\nEICHUNG FEHLGESCHLAGEN -- Entwurf ist falsch, Abbruch VOR Vollauf. "
              "Erfundene Knoten werden trotzdem entfernt.", flush=True)
        n_entfernt = delete_nodes(conn)
        nachher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        conn.close()
        out = {"eichung": eich, "aborted": True, "vorher": vorher, "entfernt": n_entfernt, "nachher": nachher,
               "konfiguration": messparameter.schnappschuss()}
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        return out

    print(f"\nEICHUNG OK -- Vollauf ueber {len(CASES)} Faelle:", flush=True)
    rows = [{"kennung": eich["kennung"], "kategorie": CASES[0]["kategorie"],
             "erwartete_zahl": eich["erwartete_zahl"], "falsche_zahl": CASES[0]["falsche_zahl"],
             "ohne_abruf": eich["ohne_abruf_roh"], "mit_abruf": eich["mit_abruf_roh"],
             "ohne_bestanden": eich["ohne_abruf_bestanden"], "mit_bestanden": eich["mit_abruf_bestanden"],
             "ziel_gefunden": eich["ziel_gefunden"], "abgerufene_pfade": eich["abgerufene_pfade"],
             "einordnung": eich["einordnung"]}]
    print(f"  {rows[0]['kennung']}  erwartet={rows[0]['erwartete_zahl']}  "
          f"ohne={rows[0]['ohne_abruf']!r}  mit={rows[0]['mit_abruf']!r}  "
          f"einordnung={rows[0]['einordnung']}", flush=True)

    for case in CASES[1:]:
        context, nodes = retrieve(case["task"])
        ohne = answer(case["task"], None, model=model)
        mit = answer(case["task"], context, model=model)
        row = {
            "kennung": case["kennung"], "kategorie": case["kategorie"],
            "erwartete_zahl": case["erwartete_zahl"], "falsche_zahl": case["falsche_zahl"],
            "ohne_abruf": ohne, "mit_abruf": mit,
            "ohne_bestanden": check(ohne, case["erwartete_zahl"]),
            "mit_bestanden": check(mit, case["erwartete_zahl"]),
            "ziel_gefunden": target_hit(case, nodes),
            "abgerufene_pfade": [n["path"] for n in nodes],
            "einordnung": classify(case, mit, nodes),
        }
        rows.append(row)
        print(f"  {row['kennung']}  erwartet={row['erwartete_zahl']}  "
              f"ohne={row['ohne_abruf']!r}  mit={row['mit_abruf']!r}  "
              f"einordnung={row['einordnung']}", flush=True)

    n_vor_delete = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    n_entfernt = delete_nodes(conn)
    nachher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    conn.close()
    print(f"\nLoeschbefehl: vorher={n_vor_delete}  entfernt={n_entfernt}  nachher={nachher}  "
          f"(Original-Bestand vor Einspielen war {vorher} -> {'unveraendert' if nachher == vorher else 'ABWEICHUNG!'})",
          flush=True)

    out = {
        "eichung": eich, "aborted": False, "model": model,
        "vorher": vorher, "vor_delete": n_vor_delete, "entfernt": n_entfernt, "nachher": nachher,
        "n_cases": len(CASES), "rows": rows,
        "konfiguration": messparameter.schnappschuss(),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGeschrieben: {out_path}", flush=True)
    return out


# ---------------------------------------------------------------------------
# Auftrag A/C/D: ein Fall auswerten (wiederverwendbar), Positivkontrolle
# mitten im Lauf, Saettigungskurve, Vollauf mit n Wiederholungen.

def _run_case(case: dict, model: str, *, force_fail: bool = False) -> dict:
    """Ein Fall auswerten. force_fail (Auflage C, NUR fuer den Abbruch-Beweis
    Abnahme 3): erzeugt eine SYNTHETISCHE Fehlmeldung ohne Modellaufruf --
    klar als 'synthetisch' markiert, damit sie nie mit einem echten
    Modellfehlschlag verwechselt wird."""
    if force_fail:
        return {
            "kennung": case["kennung"], "kategorie": case["kategorie"],
            "erwartete_zahl": case["erwartete_zahl"], "falsche_zahl": case["falsche_zahl"],
            "ohne_abruf": None, "mit_abruf": None,
            "ohne_bestanden": False, "mit_bestanden": False,
            "ziel_gefunden": False, "abgerufene_pfade": [],
            "einordnung": "synthetisch_kaputt", "synthetisch": True,
        }
    context, nodes = retrieve(case["task"])
    ohne = answer(case["task"], None, model=model)
    mit = answer(case["task"], context, model=model)
    return {
        "kennung": case["kennung"], "kategorie": case["kategorie"],
        "erwartete_zahl": case["erwartete_zahl"], "falsche_zahl": case["falsche_zahl"],
        "ohne_abruf": ohne, "mit_abruf": mit,
        "ohne_bestanden": check(ohne, case["erwartete_zahl"]),
        "mit_bestanden": check(mit, case["erwartete_zahl"]),
        "ziel_gefunden": target_hit(case, nodes),
        "abgerufene_pfade": [n["path"] for n in nodes],
        "einordnung": classify(case, mit, nodes),
        "synthetisch": False,
    }


def _positivkontrolle_pruefen(case: dict, model: str, *, force_fail: bool = False,
                               max_versuche: int = 3) -> tuple[bool, list[dict]]:
    """Mehrheitsentscheid statt Einzelversuch (Coordinator-Befund 2026-08-08,
    Fehlerklasse L-01783a): ein Einzelversuch von CASES[0] unterliegt
    derselben Streuung wie der Rest des Korpus (22/36 vs. 15/36 bei zwei
    identischen Laeufen, s. Auftrag Punkt 1) und darf einen gueltigen Lauf
    nicht wegen EINES Ausreissers abbrechen. Erst ab Mehrheit der Versuche
    durchgefallen (2 von 3) gilt das Messgeraet als kaputt. Fruehabbruch,
    sobald die Mehrheit in eine Richtung feststeht (2 Erfolge -> ok ohne
    dritten Versuch, 2 Fehlschlaege -> Abbruch ohne dritten Versuch)."""
    noetig = max_versuche // 2 + 1
    versuche: list[dict] = []
    erfolge = fehlschlaege = 0
    for _ in range(max_versuche):
        row = _run_case(case, model, force_fail=force_fail)
        versuche.append(row)
        if row["mit_bestanden"]:
            erfolge += 1
        else:
            fehlschlaege += 1
        if erfolge >= noetig or fehlschlaege >= noetig:
            break
    return erfolge >= noetig, versuche


def kalibriere_positivkontrolle(
        model: str = CAL_MODEL, n: int = 10,
        out_path: Path = SHARED_KNOWLEDGE / "runs" / "positivkontrolle_kalibrierung.json") -> dict:
    """Wie oft faellt CASES[0] bei unveraendertem Bestand/Einstellung durch --
    billig zu messen (n Aufrufe desselben Falls), entscheidet ueber die
    Bauform der Positivkontrolle (s. _positivkontrolle_pruefen-Docstring)."""
    conn = sqlite3.connect(hook.DB)
    conn.row_factory = sqlite3.Row
    vorher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    insert_nodes(conn)
    case = CASES[0]
    versuche = [_run_case(case, model) for _ in range(n)]
    n_entfernt = delete_nodes(conn)
    nachher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    conn.close()
    n_durchgefallen = sum(1 for v in versuche if not v["mit_bestanden"])
    out = {
        "kennung": case["kennung"], "n": n, "model": model,
        "n_durchgefallen": n_durchgefallen, "quote_durchgefallen": n_durchgefallen / n,
        "roh": [v["mit_bestanden"] for v in versuche],
        "konfiguration": messparameter.schnappschuss(),
        "vorher": vorher, "entfernt": n_entfernt, "nachher": nachher,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"CASES[0] durchgefallen: {n_durchgefallen}/{n} ({out['quote_durchgefallen']:.0%})", flush=True)
    print(f"Geschrieben: {out_path}", flush=True)
    return out


def saturation_curve(rows: list[dict]) -> list[dict]:
    """Kumulative Menge distinkter classify()-Kategorien in Fallreihenfolge
    -- Wachstumskurve fuer das Saettigungskriterium (Auftrag D)."""
    seen: set[str] = set()
    curve = []
    for i, row in enumerate(rows, start=1):
        seen.add(row["einordnung"])
        curve.append({"n": i, "anzahl_kategorien": len(seen), "kategorien": sorted(seen)})
    return curve


def saturation_point(rows: list[dict]) -> int:
    """Kleinstes n, ab dem in saturation_curve() keine neue Kategorie mehr
    hinzukommt (Auftrag D: berechenbares Abbruchkriterium statt geratener
    Korpusgroesse). 0 bei leerer Fallliste."""
    curve = saturation_curve(rows)
    if not curve:
        return 0
    letzte_neue = 1
    for i in range(1, len(curve)):
        if curve[i]["anzahl_kategorien"] > curve[i - 1]["anzahl_kategorien"]:
            letzte_neue = i + 1
    return letzte_neue


def run_repeated(model: str = CAL_MODEL, out_path: Path = OUT_JSON_ERWEITERT,
                  n_runs: int = N_RUNS_DEFAULT, grundrate_n_extra: int = 0,
                  positivkontrolle_index: int | None = None,
                  force_positivkontrolle_fail: bool = False) -> dict:
    """Erweiterter Vollauf, Auftrag A-D:
      A: n_runs Wiederholungen derselben Einstellung -- Median+Spanne, nie
         ein Einzelwert.
      B: grundrate_n_extra zusaetzliche Eichfaelle (build_grundrate_cases()),
         loesbare/eichfall-Quote getrennt berichtet.
      C: Positivkontrolle (CASES[0], derselbe Fall wie die Startkontrolle)
         wird zusaetzlich MITTEN im Lauf gezogen -- faellt sie durch, bricht
         der GESAMTE Lauf ab, keine Zeilen werden als Ergebnis ausgewiesen.
      D: saturation_point()/saturation_curve() ueber die Fallreihenfolge des
         ersten Laufs.
    Erfundene Knoten werden einmal eingespielt, alle n_runs Wiederholungen
    laufen darueber, danach einmal entfernt (Auflage 2: restlos)."""
    conn = sqlite3.connect(hook.DB)
    conn.row_factory = sqlite3.Row
    vorher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    insert_nodes(conn)

    cases = CASES + build_grundrate_cases(grundrate_n_extra)
    pk_index = positivkontrolle_index if positivkontrolle_index is not None else len(cases) // 2
    pk_case = CASES[0]

    eich = eichung(conn, model=model)
    print(f"EICHUNG {eich['kennung']}  eichung_ok={eich['eichung_ok']}", flush=True)
    if not eich["eichung_ok"]:
        print("EICHUNG FEHLGESCHLAGEN -- Abbruch VOR Vollauf.", flush=True)
        n_entfernt = delete_nodes(conn)
        nachher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        conn.close()
        out = {"eichung": eich, "aborted": True, "grund": "startkontrolle_fehlgeschlagen",
               "konfiguration": messparameter.schnappschuss(),
               "vorher": vorher, "entfernt": n_entfernt, "nachher": nachher}
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        return out

    print(f"EICHUNG OK -- {n_runs} Laeufe ueber je {len(cases)} Faelle "
          f"({len(CASES)} Grundkorpus + {len(cases) - len(CASES)} Grundrate-Eichfaelle), "
          f"Positivkontrolle bei n={pk_index}.", flush=True)

    laeufe = []
    messgeraet_kaputt = False
    for lauf_nr in range(n_runs):
        rows = []
        pk_versuche = None
        for i, case in enumerate(cases):
            if i == pk_index:
                pk_ok, pk_versuche = _positivkontrolle_pruefen(pk_case, model, force_fail=force_positivkontrolle_fail)
                bestanden = sum(1 for v in pk_versuche if v["mit_bestanden"])
                print(f"  [lauf {lauf_nr}] Positivkontrolle n={i}: {bestanden}/{len(pk_versuche)} "
                      f"Versuche bestanden -> ok={pk_ok}", flush=True)
                if not pk_ok:
                    print("MESSGERAET KAPUTT (Mehrheit der Versuche durchgefallen) -- "
                          "Abbruch, keine Ergebnisse aus diesem Lauf.", flush=True)
                    messgeraet_kaputt = True
                    break
            row = _run_case(case, model)
            rows.append(row)
            print(f"  [lauf {lauf_nr}] {row['kennung']}  einordnung={row['einordnung']}", flush=True)
        laeufe.append({"lauf_nr": lauf_nr, "rows": rows, "messgeraet_kaputt": messgeraet_kaputt,
                        "positivkontrolle_versuche": pk_versuche})
        if messgeraet_kaputt:
            break

    n_entfernt = delete_nodes(conn)
    nachher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    conn.close()

    if messgeraet_kaputt:
        out = {
            "eichung": eich, "aborted": True, "grund": "positivkontrolle_mitten_im_lauf_fehlgeschlagen",
            "positivkontrolle_index": pk_index, "konfiguration": messparameter.schnappschuss(),
            "vorher": vorher, "entfernt": n_entfernt, "nachher": nachher, "laeufe": laeufe,
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Geschrieben (Abbruch): {out_path}", flush=True)
        return out

    def _quote(rows, pred):
        rel = [r for r in rows if pred(r)]
        return sum(1 for r in rel if r["mit_bestanden"]), len(rel)

    ist_eichfall = lambda r: r["erwartete_zahl"] is None  # noqa: E731
    ist_loesbar = lambda r: r["erwartete_zahl"] is not None  # noqa: E731

    pro_lauf = []
    for l in laeufe:
        best_loesbar, n_loesbar = _quote(l["rows"], ist_loesbar)
        best_eich, n_eich = _quote(l["rows"], ist_eichfall)
        pro_lauf.append({
            "lauf_nr": l["lauf_nr"],
            "loesbar_bestanden": best_loesbar, "loesbar_n": n_loesbar,
            "eichfall_bestanden": best_eich, "eichfall_n": n_eich,
        })

    def _median_spanne(werte):
        return {"werte": werte, "median": statistics.median(werte),
                "spanne": (max(werte) - min(werte)) if len(werte) > 1 else 0}

    saett_curve = saturation_curve(laeufe[0]["rows"])
    saett_n = saturation_point(laeufe[0]["rows"])

    out = {
        "eichung": eich, "aborted": False, "model": model,
        "vorher": vorher, "entfernt": n_entfernt, "nachher": nachher,
        "konfiguration": messparameter.schnappschuss(),
        "n_runs": n_runs, "n_cases": len(cases), "n_grundkorpus": len(CASES),
        "grundrate_n_extra": grundrate_n_extra, "positivkontrolle_index": pk_index,
        "laeufe": laeufe, "pro_lauf": pro_lauf,
        "loesbar_bestanden_median_spanne": _median_spanne([p["loesbar_bestanden"] for p in pro_lauf]),
        "eichfall_bestanden_median_spanne": _median_spanne([p["eichfall_bestanden"] for p in pro_lauf]),
        "saettigung": {"n": saett_n, "kurve": saett_curve},
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Geschrieben: {out_path}", flush=True)
    return out


# ---------------------------------------------------------------------------
# Selbsttest -- netzlos, DB-los: prueft das Korpus-DESIGN, nicht den Abruf live.

def _selftest() -> None:
    assert 30 <= len(CASES) <= 45, f"{len(CASES)} Faelle ausserhalb 30..45"

    kategorien = {}
    for c in CASES:
        kategorien[c["kategorie"]] = kategorien.get(c["kategorie"], 0) + 1
    assert kategorien.get("einzelwert", 0) >= 1
    assert kategorien.get("kombiniert", 0) >= 1
    assert kategorien.get("aehnlich", 0) >= 2, "Sorte 1 (aehnlicher Name) braucht mehrere Faelle"
    assert kategorien.get("eigenschaft", 0) >= 2, "Sorte 2 (gleicher Name, andere Eigenschaft) braucht mehrere Faelle"
    assert kategorien.get("gleiche_einheit", 0) >= 2, "Sorte 3 (gleiche Einheit) braucht mehrere Faelle"
    assert kategorien.get("veraltet", 0) >= 2, "Sorte 4 (veraltete Fassung) braucht mehrere Faelle"
    assert kategorien.get("kombiniert3", 0) >= 2, "Sorte 5 (drei Ziel-Knoten) braucht mehrere Faelle"
    assert kategorien.get("kombiniert_ablenker", 0) >= 2, "Sorte 5b (zwei Ziele + Ablenker) braucht mehrere Faelle"
    assert kategorien.get("eichfall", 0) >= 1
    print(f"  Streuung ok: {kategorien}")

    solvable = [c for c in CASES if c["erwartete_zahl"] is not None]
    zahlen = [c["erwartete_zahl"] for c in solvable]
    assert len(zahlen) == len(set(zahlen)), "erwartete Zahlen nicht paarweise verschieden"
    assert not (set(zahlen) & BANNED_RESULTS), f"verbotener trivialer Wert dabei: {set(zahlen) & BANNED_RESULTS}"
    print(f"  {len(zahlen)} loesbare Faelle, alle Ergebnisse paarweise verschieden, keins in {BANNED_RESULTS}")

    eichfaelle = [c for c in CASES if c["kategorie"] == "eichfall"]
    assert all(c["erwartete_zahl"] is None and not c["ziel_pfade"] for c in eichfaelle)
    print(f"  {len(eichfaelle)} Eichfaelle ohne Ziel-Knoten: ok")

    # Kernpruefung: MIN_HITS=3 wird fuer jeden Ziel-Knoten durch die eigene
    # Aufgaben-Phrasierung tatsaechlich erreicht (Substring-Match wie hook.hits()
    # ihn live gegen path+title+summary anwendet) -- rein textuell, keine DB.
    # Deckt auch Sorte 4 ab: slug aus ziel_pfade liegt fuer 'veraltet'-Faelle
    # in _V statt _G, Text kommt aus node_text_aktuell() statt node_text().
    for c in CASES:
        if not c["ziel_pfade"]:
            continue
        kws = hook.keywords(c["task"])
        assert len(kws) >= hook.MIN_HITS, f"{c['kennung']}: zu wenige Keywords ({kws})"
        for slug in [p.rsplit("/", 1)[-1] for p in c["ziel_pfade"]]:
            if slug in _V:
                name, einheit, wert_alt, wert = _V[slug]
                text = node_text_aktuell(name, einheit, wert, wert_alt)
            else:
                name, einheit, wert = _G[slug]
                text = (node_text_eigenschaft(name, einheit, wert, _PARTNER_EINHEIT[slug])
                        if slug in _PARTNER_EINHEIT else node_text(name, einheit, wert))
            full = f"/{PROJECT_ID}/{slug} {name} {text}"
            n_hits = hook.hits(full, kws)
            assert n_hits >= hook.MIN_HITS, (
                f"{c['kennung']}/{slug}: nur {n_hits} Treffer < MIN_HITS={hook.MIN_HITS} "
                f"(kws={kws})")
    print("  MIN_HITS-Vorbedingung fuer jeden Ziel-Knoten offline bestaetigt (kein DB-Zugriff)")

    # Auflage 3: falsche_zahl (falls gesetzt) unterscheidet sich von der
    # erwarteten Zahl -- sonst waere ein Ablenkertreffer nicht erkennbar.
    mit_falsch = [c for c in CASES if c["falsche_zahl"] is not None]
    assert len(mit_falsch) >= 8, f"nur {len(mit_falsch)} Faelle mit falsche_zahl (Sorten 1-4 sollten je >=2 haben)"
    for c in mit_falsch:
        assert c["falsche_zahl"] != c["erwartete_zahl"], (
            f"{c['kennung']}: falsche_zahl == erwartete_zahl ({c['falsche_zahl']}) -- Ablenkertreffer waere nicht erkennbar")
    print(f"  {len(mit_falsch)} Faelle mit falsche_zahl, alle != erwartete_zahl: ok")

    # Aehnlich-Faelle: Ablenker-Name darf NICHT als Substring im Zieltext
    # stecken (sonst waere das kein sauberer Unterscheidungstest).
    aehnlich = [c for c in CASES if c["kategorie"] == "aehnlich"]
    assert len(aehnlich) >= 2
    for c in aehnlich:
        ziel_slug = c["ziel_pfade"][0].rsplit("/", 1)[-1]
        name_ziel = _G[ziel_slug][0]
        for slug, name, *_r in GEGENSTAENDE:
            if slug != ziel_slug and name.lower() != name_ziel.lower() and name.lower().startswith(name_ziel.lower()[:6]):
                assert hook.fold_de(name) not in hook.fold_de(name_ziel), \
                    f"{c['kennung']}: Ablenkername {name} steckt im Zielnamen {name_ziel}"
    print(f"  {len(aehnlich)} Aehnlich-Faelle: Ablenkername != Substring des Zielnamens: ok")

    # Sorte 2 (gleicher Name, andere Eigenschaft): Ziel- und Ablenker-Slug
    # muessen denselben Anzeigenamen tragen -- sonst ist es kein Test dieser
    # Sorte, sondern versehentlich ein 'aehnlich'-Fall.
    eigenschaft = [c for c in CASES if c["kategorie"] == "eigenschaft"]
    assert len(eigenschaft) >= 2
    for c in eigenschaft:
        ziel_slug = c["ziel_pfade"][0].rsplit("/", 1)[-1]
        name_ziel, einheit_ziel, _w = _G[ziel_slug]
        geschwister = [(s, n, e) for s, n, e, _w2 in GEGENSTAENDE if n == name_ziel and s != ziel_slug]
        assert geschwister, f"{c['kennung']}: kein Geschwisterknoten mit Name {name_ziel}"
        assert all(e != einheit_ziel for _s, _n, e in geschwister), (
            f"{c['kennung']}: Geschwisterknoten teilt die Einheit {einheit_ziel} -- keine andere Eigenschaft")
        # Ablenker muss selbst MIN_HITS gegen DIESE Aufgabe erreichen, sonst
        # taucht er im Abruf nie auf (roher Live-Befund vor dem Bindeglied-
        # Satz: nur 2 Treffer, s. Kommentar bei EIGENSCHAFT_PAARE).
        kws = hook.keywords(c["task"])
        for slug_g, name_g, einheit_g in geschwister:
            wert_g = _G[slug_g][2]
            text_g = f"/{PROJECT_ID}/{slug_g} {name_g} {node_text_eigenschaft(name_g, einheit_g, wert_g, _PARTNER_EINHEIT[slug_g])}"
            n_hits = hook.hits(text_g, kws)
            assert n_hits >= hook.MIN_HITS, (
                f"{c['kennung']}/{slug_g}: Ablenker nur {n_hits} Treffer < MIN_HITS={hook.MIN_HITS}")
    print(f"  {len(eigenschaft)} Eigenschaft-Faelle: Geschwisterknoten mit anderer Einheit + eigener MIN_HITS-Deckung: ok")

    # Sorte 3 (gleiche Einheit): beide Ziel-Slugs muessen dieselbe Einheit
    # tragen -- sonst zwingt die Aufgabe nicht zu zwei echten Treffern.
    gleiche_einheit = [c for c in CASES if c["kategorie"] == "gleiche_einheit"]
    assert len(gleiche_einheit) >= 2
    for c in gleiche_einheit:
        assert len(c["ziel_pfade"]) == 2, f"{c['kennung']}: erwartet zwei Ziel-Knoten"
        einheiten = {_G[p.rsplit('/', 1)[-1]][1] for p in c["ziel_pfade"]}
        assert len(einheiten) == 1, f"{c['kennung']}: Einheiten weichen ab ({einheiten})"
    print(f"  {len(gleiche_einheit)} Gleiche-Einheit-Faelle: beide Ziele teilen die Einheit: ok")

    # Sorte 4 (veraltete Fassung): jeder Eintrag in VERALTET hat einen
    # eigenen alten Knoten mit gilt_bis gesetzt, Text erreicht ebenfalls
    # MIN_HITS (sonst wird die Ablenkung nie gezogen, s. Auflage 2/Eichung).
    veraltet = [c for c in CASES if c["kategorie"] == "veraltet"]
    assert len(veraltet) >= 2
    assert GILT_BIS_ALT, "GILT_BIS_ALT muss gesetzt sein (Sorte 4 braucht eine echte gilt_bis-Markierung)"
    for slug, name, einheit, wert_alt, wert_neu in VERALTET:
        assert wert_alt != wert_neu, f"{slug}: alter und neuer Wert identisch"
        kws = hook.keywords(_task_veraltet(slug, 3)[0])
        alt_text = f"/{PROJECT_ID}/{slug}_alt {name} {node_text_veraltet(name, einheit, wert_alt)}"
        assert hook.hits(alt_text, kws) >= hook.MIN_HITS, f"{slug}_alt: Ablenker erreicht MIN_HITS nicht -- lenkt nichts ab"
    print(f"  {len(veraltet)} Veraltet-Faelle: gilt_bis gesetzt, alter Knoten erreicht MIN_HITS: ok")

    # Sorte 5 (drei Ziel-Knoten, ohne Ablenker): jede Aufgabe hat genau drei
    # Ziel-Pfade -- MAX_NODES=3 (knowledge_recall_hook.py) laesst dann keinen
    # Slack mehr.
    kombiniert3 = [c for c in CASES if c["kategorie"] == "kombiniert3"]
    assert len(kombiniert3) >= 2
    for c in kombiniert3:
        assert len(c["ziel_pfade"]) == 3, f"{c['kennung']}: erwartet drei Ziel-Knoten"
    print(f"  {len(kombiniert3)} Drei-Knoten-Faelle: je drei Ziele (MAX_NODES=3, kein Slack): ok")

    # Sorte 5b: zwei Ziele + ZWEI benannte Ablenker -- macht VIER MIN_HITS-
    # faehige Kandidaten fuer nur drei Ausgabeplaetze (MAX_NODES=3), echter
    # Overlauf statt nur voller Ausnutzung (s. Docstring _task_kombiniert_ablenker,
    # warum ein einzelner Ablenker die Quote 2026-08-07 nicht senkte: 3
    # Kandidaten passen ohne Verdraengung in 3 Plaetze).
    ablenker_faelle = [c for c in CASES if c["kategorie"] == "kombiniert_ablenker"]
    assert len(ablenker_faelle) >= 2
    for c in ablenker_faelle:
        assert len(c["ziel_pfade"]) == 2, f"{c['kennung']}: erwartet zwei Ziel-Knoten (plus Ablenker)"
        assert len(c["ablenker_slugs"]) == 2, f"{c['kennung']}: erwartet zwei Ablenker (echter Overlauf, kein Slack)"
        kws = hook.keywords(c["task"])
        for slug_a in c["ablenker_slugs"]:
            name_a, einheit_a, wert_a = _G[slug_a]
            text_a = f"/{PROJECT_ID}/{slug_a} {name_a} {node_text(name_a, einheit_a, wert_a)}"
            n_hits = hook.hits(text_a, kws)
            assert n_hits >= hook.MIN_HITS, (
                f"{c['kennung']}/{slug_a}: Ablenker nur {n_hits} Treffer < MIN_HITS={hook.MIN_HITS} -- "
                f"kein echter Konkurrent (kws={kws})")
    print(f"  {len(ablenker_faelle)} Zwei-Knoten-Faelle mit je zwei Ablenkern: alle vier Kandidaten erreichen MIN_HITS (echter Overlauf): ok")

    # Auftrag B: Grundrate-Generator liefert eindeutige, kollisionsfreie
    # Zusatz-Eichfaelle, CASES selbst bleibt dabei unangetastet.
    n_vorher_cases = len(CASES)
    extra = build_grundrate_cases(20)
    assert len(CASES) == n_vorher_cases, "build_grundrate_cases() darf CASES nicht veraendern"
    assert len(extra) == 20
    woerter = [c["task"] for c in extra]
    assert len(woerter) == len(set(woerter)), "generierte Eichfall-Aufgaben nicht paarweise verschieden"
    assert all(c["erwartete_zahl"] is None and not c["ziel_pfade"] for c in extra)
    ziel_n = target_grundrate_n_extra(0.80)
    loesbare_n = sum(1 for c in CASES if c["erwartete_zahl"] is not None)
    eich_n = len(CASES) - loesbare_n
    assert abs((eich_n + ziel_n) / (loesbare_n + eich_n + ziel_n) - 0.80) < 0.01, \
        f"target_grundrate_n_extra(0.80) trifft die 80%-Vorgabe nicht: {ziel_n}"
    print(f"  Grundrate: 20 generierte Zusatz-Eichfaelle eindeutig/kollisionsfrei, "
          f"target_grundrate_n_extra(0.80)={ziel_n} trifft 80% exakt: ok")

    # Auftrag D: Saettigungskurve waechst monoton und stoppt korrekt beim
    # letzten Auftreten einer neuen Kategorie.
    fake_rows = [{"einordnung": k} for k in
                 ["bestanden", "bestanden", "kein_treffer", "bestanden", "falscher_treffer", "bestanden"]]
    curve = saturation_curve(fake_rows)
    assert [c["anzahl_kategorien"] for c in curve] == [1, 1, 2, 2, 3, 3]
    assert saturation_point(fake_rows) == 5, f"erwartet 5 (letzte neue Kategorie bei n=5), war {saturation_point(fake_rows)}"
    assert saturation_point([]) == 0
    print("  Saettigungskurve: monoton, Saettigungspunkt = letztes Neuauftreten: ok")

    # Auftrag C: _run_case(force_fail=True) liefert eine als synthetisch
    # markierte Fehlmeldung ohne Modellaufruf (Positivkontrolle-Abbruchpfad).
    pk_fail = _run_case(CASES[0], CAL_MODEL, force_fail=True)
    assert pk_fail["mit_bestanden"] is False and pk_fail["synthetisch"] is True
    print("  _run_case(force_fail=True): synthetische Fehlmeldung ohne Netzaufruf: ok")

    # Coordinator-Befund 2026-08-08 (L-01783a): Einzelversuch der Positiv-
    # kontrolle unterliegt derselben Streuung wie der Rest des Korpus und
    # darf einen gueltigen Lauf nicht abbrechen -- ab jetzt Mehrheitsentscheid
    # (2 von 3) mit Fruehabbruch. force_fail=True bricht nach genau 2
    # Versuchen ab (kein dritter noetig); ein einzelner Ausreisser (2. von 3
    # Versuchen faellt durch, Rest besteht) darf NICHT abbrechen.
    self_mod = sys.modules[__name__]
    orig_run_case = self_mod._run_case
    calls = {"n": 0}

    def _fake_ein_ausreisser(case, model, *, force_fail=False):
        calls["n"] += 1
        bestanden = calls["n"] != 2  # nur der zweite Versuch faellt durch
        return {"mit_bestanden": bestanden, "kennung": case["kennung"], "kategorie": case["kategorie"],
                "erwartete_zahl": case["erwartete_zahl"], "falsche_zahl": case["falsche_zahl"],
                "ohne_abruf": None, "mit_abruf": None, "ziel_gefunden": bestanden,
                "abgerufene_pfade": [], "einordnung": "bestanden" if bestanden else "kein_treffer",
                "synthetisch": False}

    try:
        self_mod._run_case = _fake_ein_ausreisser
        ok, versuche = _positivkontrolle_pruefen(CASES[0], CAL_MODEL)
        assert ok is True and len(versuche) == 3, (
            f"1 von 3 Fehlschlaegen (Einzelausreisser) darf nicht abbrechen: ok={ok} n={len(versuche)}")
    finally:
        self_mod._run_case = orig_run_case

    ok2, versuche2 = _positivkontrolle_pruefen(CASES[0], CAL_MODEL, force_fail=True)
    assert ok2 is False and len(versuche2) == 2, (
        f"force_fail muss ab 2 Fehlschlaegen fruehabbrechen: ok={ok2} n={len(versuche2)}")
    print("  Positivkontrolle: Mehrheitsentscheid (2/3) uebersteht Einzelausreisser, "
          "force_fail bricht nach 2 Fehlschlaegen frueh ab: ok")

    print(f"selftest ok ({len(CASES)} Faelle)", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true", help="netzlos, DB-los")
    ap.add_argument("--eichung-only", action="store_true",
                     help="nur der Eichfall (v3-01), erfundene Knoten danach entfernt")
    ap.add_argument("--model", default=CAL_MODEL)
    ap.add_argument("--delete", action="store_true",
                     help="nur Loeschbefehl vorfuehren (falls Knoten aus vorigem Lauf uebrig sind)")
    ap.add_argument("--erweitert", action="store_true",
                     help="Auftrag A-D: n Wiederholungen, Grundrate, Positivkontrolle mitten im Lauf, Saettigung")
    ap.add_argument("--n-runs", type=int, default=N_RUNS_DEFAULT)
    ap.add_argument("--grundrate-n", type=int, default=0, help="zusaetzliche Eichfaelle")
    ap.add_argument("--grundrate-auto", action="store_true",
                     help=f"Grundrate automatisch Richtung {int(GRUNDRATE_ZIEL_ANTEIL * 100)}%% Wirklichkeitsanteil")
    ap.add_argument("--positivkontrolle-index", type=int, default=None)
    ap.add_argument("--force-positivkontrolle-fail", action="store_true",
                     help="NUR Demo/Abnahme: erzwingt synthetischen Abbruch, kein echter Lauf")
    ap.add_argument("--kalibriere-positivkontrolle", action="store_true",
                     help="misst, wie oft CASES[0] bei n Versuchen durchfaellt (entscheidet ueber die Kontroll-Bauform)")
    ap.add_argument("--kalibriere-n", type=int, default=10)
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return

    if args.kalibriere_positivkontrolle:
        kalibriere_positivkontrolle(model=args.model, n=args.kalibriere_n)
        return

    if args.delete:
        conn = sqlite3.connect(hook.DB)
        vorher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        n = delete_nodes(conn)
        nachher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        conn.close()
        print(f"vorher={vorher}  entfernt={n}  nachher={nachher}")
        return

    if args.eichung_only:
        conn = sqlite3.connect(hook.DB)
        vorher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        insert_nodes(conn)
        eich = eichung(conn, model=args.model)
        print(json.dumps(eich, ensure_ascii=False, indent=2))
        n = delete_nodes(conn)
        nachher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        conn.close()
        print(f"vorher={vorher}  entfernt={n}  nachher={nachher}")
        return

    if args.erweitert:
        n_extra = target_grundrate_n_extra() if args.grundrate_auto else args.grundrate_n
        run_repeated(model=args.model, n_runs=args.n_runs, grundrate_n_extra=n_extra,
                     positivkontrolle_index=args.positivkontrolle_index,
                     force_positivkontrolle_fail=args.force_positivkontrolle_fail)
        return

    run_all(model=args.model)


if __name__ == "__main__":
    main()
