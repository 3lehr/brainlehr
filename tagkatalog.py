"""Der Tag-Katalog: eine geschlossene Liste, aus der Schreiber waehlen.

Gemessen 2026-08-09 ueber den Arbeitsbestand: 385 Knoten, 1491 Tag-Vergaben,
698 verschiedene Tags -- 493 davon (70 %) genau EINMAL vergeben. Das ist kein
Katalog, sondern Wildwuchs, und er entsteht genau dann, wenn jeder Schreiber
frei erfindet. Darum wird der Katalog hier aus dem Bestand DESTILLIERT (was
mehrfach vergeben wurde, hat sich als Begriff bewaehrt) und nicht erfunden.

Zwei Regeln, beide aus der Messung:
- Aufnahme ab MIN_VERGABEN Vergaben. Ein einmal vergebenes Tag ist keine
  Kategorie, sondern eine Notiz.
- Synonyme werden zusammengefuehrt, der HAEUFIGERE gewinnt (nicht der
  kuerzere -- der haeufigere ist der, den die Schreiber tatsaechlich treffen).

Aufruf:
  python3 tagkatalog.py                  Katalog bauen und nach runs/ schreiben
  python3 tagkatalog.py --pruefe TAG...  gehoeren diese Tags zum Katalog?
  python3 tagkatalog.py --selftest
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
sys.path.insert(0, str(WURZEL / "haken"))
import ort  # noqa: E402

KATALOG = WURZEL / "runs" / "tagkatalog.json"
MIN_VERGABEN = 2

# Ein Tag ist ein SUCHINDEX. Es macht eine Eigenschaft filterbar, unabhaengig
# davon, was im Text steht -- und genau darum ist die Aufnahme in den Katalog
# etwas anderes als das Schreiben eines Satzes. Ein Knoten, der beilaeufig eine
# Krankenkasse erwaehnt, ist eine Erwaehnung; hundert Knoten mit dem Tag
# 'krankenkasse' sind eine Liste.
#
# Darum kann Haeufigkeit allein hier nicht entscheiden: ohne diese Sperre wird
# jedes Tag ab zwei Vergaben automatisch Kategorie, und niemand sieht hin
# (Befund der Compliance-Pruefung 2026-08-09, als BLOCKER gemeldet).
#
# Die Liste deckt die besonderen Kategorien nach Art. 9 DSGVO ab (Gesundheit,
# Religion, Politik, Gewerkschaft, ethnische Herkunft, Biometrie, Sexualleben)
# und dazu Begriffe, die eine Person KENNZEICHNEN statt eine Sache zu benennen.
# Sie ist bewusst breit: ein Fehlalarm kostet eine Handentscheidung, ein
# uebersehener Treffer erzeugt einen dauerhaften Filter ueber Menschen.
ART9_STAEMME = (
    "gesundheit", "krank", "diagnos", "therapi", "patient", "arzt", "aerzt",
    "medizin", "rezept", "impf", "behinder", "pflegegrad", "sucht",
    "religion", "kirche", "konfession", "glaub",
    "partei", "politisch", "wahlverhalten", "gewerkschaft",
    "ethni", "rasse", "herkunftsland", "migrations", "asyl",
    "biometr", "fingerabdruck", "gesichtserkennung", "dna",
    "sexual", "geschlechtsident", "orientierung",
    "mandant", "klient", "patientin", "privatperson", "personenbezogen",
    "vorstrafe", "schuld", "bonitaet", "schufa",
)


def ist_pruefpflichtig(tag: str) -> bool:
    """Beruehrt dieses Tag eine besondere Kategorie oder kennzeichnet es eine
    Person? Dann entscheidet ein Mensch, nicht die Haeufigkeit."""
    t = tag.lower()
    return any(s in t for s in ART9_STAEMME)


def tags_lesen(conn: sqlite3.Connection) -> Counter:
    z: Counter = Counter()
    for r in conn.execute(
        "SELECT tags FROM knowledge_nodes WHERE gattung = 'arbeitsbestand' AND zurueckgezogen = 0"
    ):
        z.update(normalisieren(r[0]))
    return z


def normalisieren(roh: str | None) -> list[str]:
    """tags liegen als JSON-Liste vor; aeltere Zeilen tragen Kommatext."""
    if not roh:
        return []
    try:
        werte = json.loads(roh)
        if not isinstance(werte, list):
            werte = [werte]
    except (json.JSONDecodeError, TypeError):
        werte = roh.split(",")
    return [str(w).strip().lower() for w in werte if str(w).strip()]


# Was der stumpfe Stammvergleich faelschlich zusammenzieht -- von Hand geprueft
# am Lauf vom 2026-08-09 (12 Vorschlaege, 3 davon falsch). Die Liste ist der
# Grund, warum _stamm() absichtlich dumm bleiben darf: sie ist kurz genug zum
# Lesen, und eine gelesene Ausnahmeliste schlaegt einen ungelesenen Algorithmus.
NICHT_ZUSAMMENFUEHREN = {
    "geltungszeitraum",      # Zeit, nicht Raum -- 'geltungsbereich' ist etwas anderes
    "verwaltervertrag",      # der Vertrag ist nicht der Wechsel
    "schimmel_guard_app",    # die App, nicht das Thema Schimmel
}


def _stamm(tag: str) -> str:
    """Grobe Zusammenfuehrung: Trennzeichen raus, auf acht Zeichen gekuerzt.
    Absichtlich stumpf -- der Katalog wird gelesen, bevor er gilt; ein zu
    schlauer Automatismus verschmilzt Begriffe, die nichts miteinander zu tun
    haben, und niemand sieht es nach."""
    return re.sub(r"[-_ ]", "", tag)[:8]


def bauen(z: Counter, min_vergaben: int = MIN_VERGABEN) -> dict:
    # Vor der Haeufigkeit: die Art-9-Sperre. Ein pruefpflichtiges Tag wird NICHT
    # Kategorie, egal wie oft es vergeben wurde -- es landet in einer eigenen
    # Liste und wartet auf eine Handentscheidung.
    pruefpflichtig = {t: k for t, k in z.items() if k >= min_vergaben and ist_pruefpflichtig(t)}
    kandidaten = {t: k for t, k in z.items() if k >= min_vergaben and not ist_pruefpflichtig(t)}
    gruppen: dict[str, list[str]] = defaultdict(list)
    for t in kandidaten:
        # Eigener Stamm -> eigene Gruppe -> bleibt eigenstaendige Kategorie
        gruppen[t if t in NICHT_ZUSAMMENFUEHREN else _stamm(t)].append(t)
    katalog, ersetzungen = {}, {}
    for mitglieder in gruppen.values():
        mitglieder.sort(key=lambda t: (-kandidaten[t], t))
        leit = mitglieder[0]
        katalog[leit] = sum(kandidaten[m] for m in mitglieder)
        for m in mitglieder[1:]:
            ersetzungen[m] = leit
    # Einmal vergebene Tags sind nicht verloren: fuehrt ihr Stamm auf einen
    # Katalogeintrag, werden sie darauf abgebildet -- sonst verschwinden sie,
    # und das ist beabsichtigt.
    stamm_zu_leit = {_stamm(t): t for t in katalog if t not in NICHT_ZUSAMMENFUEHREN}
    for t, k in z.items():
        if t in katalog or t in ersetzungen or t in NICHT_ZUSAMMENFUEHREN:
            continue
        if ist_pruefpflichtig(t):
            # Auch als ERSETZUNG nicht durchlassen: sonst kaeme 'krankenkassen'
            # ueber den Stammvergleich doch noch auf eine Kategorie und waere
            # damit wieder filterbar.
            continue
        leit = stamm_zu_leit.get(_stamm(t))
        if leit:
            ersetzungen[t] = leit
    return {
        "stand": "aus dem Arbeitsbestand destilliert",
        "min_vergaben": min_vergaben,
        "tags": dict(sorted(katalog.items(), key=lambda p: (-p[1], p[0]))),
        "ersetzungen": dict(sorted(ersetzungen.items())),
        "pruefpflichtig": dict(sorted(pruefpflichtig.items(), key=lambda p: (-p[1], p[0]))),
    }


def pruefe(tags: list[str], katalog: dict) -> dict:
    """Was ein Schreiber vor dem Setzen fragt. 'bekannt' geht durch,
    'ersetzt' wird stillschweigend korrigiert, 'unbekannt' ist ein VORSCHLAG
    -- er wird gesammelt und von Hand entschieden, nie automatisch
    aufgenommen. Sonst waechst der Katalog beim Anwenden, und genau so sind
    die 698 entstanden."""
    bekannt, ersetzt, unbekannt, pruefpflichtig = [], {}, [], []
    for t in (x.strip().lower() for x in tags if x.strip()):
        if ist_pruefpflichtig(t):
            # Vor allem anderen: auch ein Tag, das schon einmal im Katalog
            # stuende, wird hier abgefangen -- die Sperre soll auch dann
            # greifen, wenn ein alter Katalogstand weiterbenutzt wird.
            pruefpflichtig.append(t)
        elif t in katalog["tags"]:
            bekannt.append(t)
        elif t in katalog["ersetzungen"]:
            ersetzt[t] = katalog["ersetzungen"][t]
        else:
            unbekannt.append(t)
    return {"bekannt": bekannt, "ersetzt": ersetzt, "vorschlaege": unbekannt,
            "pruefpflichtig": pruefpflichtig}


def main() -> None:
    conn = sqlite3.connect(f"file:{ort.DB}?mode=ro", uri=True)
    z = tags_lesen(conn)
    conn.close()
    k = bauen(z)
    KATALOG.write_text(json.dumps(k, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Bestand: {len(z)} verschiedene Tags, {sum(z.values())} Vergaben")
    print(f"Katalog: {len(k['tags'])} Kategorien, {len(k['ersetzungen'])} Ersetzungen")
    abgedeckt = sum(v for t, v in z.items() if t in k["tags"] or t in k["ersetzungen"])
    print(f"Abgedeckte Vergaben: {abgedeckt} von {sum(z.values())} "
          f"({100 * abgedeckt // sum(z.values())} %)")
    print(f"geschrieben: {KATALOG}")


def demo() -> None:
    """Gegenprobe in beide Richtungen plus Negativfall, ohne DB."""
    z = Counter({"methodik": 91, "adr": 43, "entscheidung": 8, "entscheid": 3,
                 "einzelstueck": 1, "entscheidungslage": 1})
    k = bauen(z)
    assert "methodik" in k["tags"], k
    assert "einzelstueck" not in k["tags"], "einmal vergeben ist keine Kategorie"
    assert "einzelstueck" not in k["ersetzungen"], "fremder Stamm darf nicht abgebildet werden"
    assert k["ersetzungen"].get("entscheid") == "entscheidung", (
        f"der haeufigere muss gewinnen, nicht der kuerzere: {k['ersetzungen']}")
    assert k["ersetzungen"].get("entscheidungslage") == "entscheidung", k["ersetzungen"]
    assert k["tags"]["entscheidung"] == 11, f"Gruppe muss summieren: {k['tags']}"

    p = pruefe(["Methodik", "entscheid", "voellig-neues-tag"], k)
    assert p["bekannt"] == ["methodik"], p
    assert p["ersetzt"] == {"entscheid": "entscheidung"}, p
    assert p["vorschlaege"] == ["voellig-neues-tag"], p

    # Art-9-Sperre, rot gegen den Stand vor der Compliance-Pruefung: dort wurde
    # 'krankenkasse' bei fuenf Vergaben zur Kategorie. Gegenprobe in beide
    # Richtungen -- ein harmloses Tag derselben Haeufigkeit geht weiter durch.
    z9 = Counter({"krankenkasse": 5, "diagnose": 4, "mandant": 3, "methodik": 5})
    k9 = bauen(z9)
    for heikel in ("krankenkasse", "diagnose", "mandant"):
        assert heikel not in k9["tags"], f"{heikel} darf keine Kategorie werden: {k9['tags']}"
        assert heikel not in k9["ersetzungen"], f"{heikel} darf auch keine Ersetzung sein"
        assert heikel in k9["pruefpflichtig"], f"{heikel} muss zur Handentscheidung: {k9}"
    assert "methodik" in k9["tags"], "harmloses Tag gleicher Haeufigkeit muss durchgehen"

    p9 = pruefe(["krankenkasse", "methodik"], k9)
    assert p9["pruefpflichtig"] == ["krankenkasse"], p9
    assert p9["bekannt"] == ["methodik"], p9
    assert "krankenkasse" not in p9["vorschlaege"], "darf nicht als harmloser Vorschlag durchgehen"

    # Negativfall: die Sperre darf nicht alles fangen, was entfernt aehnlich klingt.
    assert not ist_pruefpflichtig("methodik") and not ist_pruefpflichtig("kanten")
    assert ist_pruefpflichtig("Krankenkassen-Beitrag"), "Wortform darf nicht entkommen"

    assert normalisieren('["a","B"]') == ["a", "b"]
    assert normalisieren("a, B") == ["a", "b"], "Kommatext aus Altbestand"
    assert normalisieren(None) == [] and normalisieren("[]") == []
    print("tagkatalog.demo ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        demo()
    elif "--pruefe" in sys.argv:
        k = json.loads(KATALOG.read_text(encoding="utf-8"))
        print(json.dumps(pruefe(sys.argv[sys.argv.index("--pruefe") + 1:], k),
                         ensure_ascii=False, indent=2))
    else:
        main()
