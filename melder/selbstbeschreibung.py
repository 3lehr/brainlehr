#!/usr/bin/env python3
"""selbstbeschreibung.py -- brainlehr legt sein eigenes Handbuch als Wissen ab.

DER BEFUND: Alle 58 Knoten unter /brainlehr standen auf freigabe='intern'. Ein
Fremdnutzer, der seine frische Instanz fragt "was kannst du", bekam damit NULL
-- und die eigene Instanz antwortete mit Arbeitsgeschichte statt mit
Faehigkeiten. Ein Wissensspeicher, der ueber sich selbst schweigt, ist der
schlechteste Beleg fuer sich.

WARUM NICHT EINFACH DIE 58 FREIGEBEN: Sie sind Arbeitsgeschichte -- Zitate des
Betreibers, Fehleranalysen, verworfene Wege. Fuer die Entwicklung wertvoll, fuer
einen Fremden Rauschen, und teils mit Bezuegen, die ihn nichts angehen. Diese
Datei schreibt stattdessen einen eigenen, fuer die Weitergabe gedachten Satz.

WARUM EIN SKRIPT UND KEINE HANDARBEIT: dieselbe Bauform wie build_node_index.py
und faehigkeiten.py -- erzeugen statt pflegen. Ein von Hand gepflegter
Faehigkeitstext verrottet ab dem Tag, an dem sich etwas aendert; ein Lauf ist
wiederholbar. Der Lauf ist IDEMPOTENT: vorhandene Knoten werden aktualisiert,
nicht verdoppelt.

WAS ER NICHT TUT: Er misst nichts. Die Zahlen stehen in faehigkeiten.py
(gemessen beim Zugriff) und in den Messlaeufen. Hier steht, WAS das System
kann und WO die Grenze liegt -- in der Sprache eines Menschen, der es zum
ersten Mal benutzt.

Aufruf:
    python3 selbstbeschreibung.py --anlegen     # schreibt/aktualisiert
    python3 selbstbeschreibung.py --zeigen      # nur ausgeben
    python3 selbstbeschreibung.py --selftest
"""
# ausloeser: auf-abruf -- ein Mensch fragt: was kann brainlehr, und wo liegt seine Grenze?
from __future__ import annotations

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

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(_w))
import speicher  # noqa: E402 -- nur verbinde_bestand() gegen stilles Anlegen

AST = "/brainlehr/faehigkeiten"
QUELLE = ("erzeugt von selbstbeschreibung.py aus dem gebauten Stand -- "
          "nicht von Hand gepflegt")

# Jede Faehigkeit in drei Teilen, und der dritte ist der wichtigste:
#   kann      -- was das System leistet
#   womit     -- mit welchem Werkzeug/Feld man es benutzt (ohne Namen ist eine
#                Anleitung unbenutzbar, siehe L-8c319e)
#   grenze    -- wo es aufhoert. Ohne diesen Teil entsteht Vertrauen, das die
#                Sache nicht traegt.
FAEHIGKEITEN = [
    ("herkunft", "Sagen, woher eine Aussage stammt",
     "Jeder Eintrag traegt ein Pflichtfeld `source`. Es ist per "
     "Datenbank-Trigger erzwungen, nicht per Konvention -- ein Eintrag ohne "
     "nachpruefbare Herkunft entsteht gar nicht erst. Herkunftsfelder sind "
     "nach dem Schreiben unveraenderlich.",
     "Beim Anlegen `source` mitgeben (knowledge_add). Fehlt es, weist die "
     "Datenbank ab und nennt den Feldnamen im Klartext.",
     "Der Trigger prueft, DASS eine Herkunft dasteht, nicht ob sie stimmt. "
     "Freitext kann luegen -- und er kann zuviel verraten: eine Herkunft, die "
     "einen Personennamen wiedergibt, traegt ihn dauerhaft mit."),

    ("geltung", "Sagen, ob etwas noch gilt",
     "Eine Aussage kann eine Norm sein: `norm_rang` (1 globale Regel, 2 "
     "Projektentscheidung, 3 festgehaltene Entscheidung), dazu `gilt_ab` und "
     "`gilt_bis`. Ob etwas ueberhaupt eine Norm ist, wird ausdruecklich "
     "entschieden -- ohne Vorgabewert.",
     "`norm_entscheidung` ist Pflichtfeld: keine_norm | norm_befristet | "
     "norm_unbefristet, dazu `norm_entschieden_grund`.",
     "Kein Vorgabewert heisst: es gibt keine stille Mehrheit. Das ist "
     "Absicht -- ein Vorgabewert brachte genau die Mehrdeutigkeit zurueck, "
     "die das Feld beseitigen soll. Es kostet bei jedem Eintrag eine "
     "Entscheidung."),

    ("belegrang", "Sagen, wie belastbar etwas ist",
     "Aussagen tragen eine Angabe darueber, worauf sie beruhen: gemessen, "
     "Fremdbericht, plausibel oder geraten. Damit laesst sich eine Vermutung "
     "von einem Befund unterscheiden, ohne den Text zu lesen.",
     "Im Text der Aussage ausweisen; Werkzeuge wie `pruefer.py` melden "
     "Felder, die ihre Aufgabe nicht erfuellen.",
     "Die Einstufung trifft der Schreibende. Ein System kann pruefen, DASS "
     "eine Einstufung dasteht, nicht ob sie ehrlich ist."),

    ("widerspruch", "Widersprueche aushalten statt sie zu verstecken",
     "Zwei Eintraege duerfen sich widersprechen. Der Speicher loest das nicht "
     "heimlich auf, sondern kann den Konflikt ausweisen -- mit beiden Seiten "
     "und ihrer jeweiligen Herkunft.",
     "Widersprueche werden als eigene Knoten gefuehrt; `normbestand.py` und "
     "`normachsen.py` zeigen Spannungen im Bestand.",
     "Welche Seite gewinnt, ist eine Verfassungsfrage und derzeit hart "
     "verdrahtet: der hoehere Rang sticht. Das ist EINE moegliche Ordnung, "
     "nicht die einzige -- eine waehlbare Aufloesungsregel ist entworfen, "
     "aber nicht gebaut."),

    ("normmelder", "Melden, wenn ein Zitat keinen Beleg hat",
     "Wird in einer Antwort ein Gesetz, eine Norm (DIN/ISO/BSI/RFC/WCAG) oder "
     "eine interne Kennung genannt, prueft brainlehr, ob dafuer ein Beleg im "
     "Bestand liegt -- und meldet, wenn nicht. Bei internen Kennungen heisst "
     "ein Fehltreffer nicht 'unbelegt', sondern 'erfunden'.",
     "`normbezug.py`, verdrahtet am Ende jeder Antwort. Einzeln: "
     "`python3 normbezug.py --text \"...\"`.",
     "Es prueft, ob ein Beleg EXISTIERT, nicht ob die Aussage darueber "
     "stimmt. Und ein Beleg altert: ab einem Jahr meldet es ihn als "
     "nachpruefbeduerftig, weil Gesetze sich aendern."),

    ("identitaet", "Wissen, wer etwas geschrieben hat",
     "Wer schreibt, weist sich mit einem Ausweis aus. Ohne Ausweis traegt "
     "jede Zuschreibung dauerhaft das Praefix `unbeglaubigt:` -- die "
     "Unterscheidung zwischen geprueft und behauptet bleibt damit "
     "rueckwirkend auswertbar. Rollen folgen dem Muster modul:aktion:bezug.",
     "`ausweis.py --anlegen <name> --rollen <rolle>`; das Geheimnis kommt in "
     "die Klientenkonfiguration als BRAINLEHR_GEHEIMNIS.",
     "Die Vorgabe ist weich: ohne Ausweis darf weiterhin jeder alles. Der "
     "Schutz entsteht erst mit BRAINLEHR_DURCHSETZUNG=streng. Und solange die "
     "Ausweisdatei dem laufenden Prozess gehoert, kann dieser sich selbst "
     "einen Ausweis ausstellen -- die Datei gehoert deshalb root, nicht dem "
     "Dienst."),

    ("fremdtext", "Fremden Text als Daten kennzeichnen",
     "Text aus dem Bestand, der in ein Sprachmodell fliesst, wird abgegrenzt "
     "und als Daten beschriftet. Dazu kommen sprachunabhaengige "
     "Anomaliesignale -- Skriptmischung, kodierte Bloecke, verwechselbare "
     "Zeichen -- und zuletzt Wortmuster.",
     "`einschleusung.py`, verdrahtet am Schreibvorgang.",
     "Eine Musterliste ist prinzipiell unvollstaendig; ein umformulierter "
     "Angriff faellt durch jedes Muster. Der eigentliche Schutz ist die "
     "Kennzeichnung, nicht die Erkennung. Und ein Fund BLOCKIERT nicht -- "
     "sonst koennte eine geschickte Formulierung fremde, legitime Eintraege "
     "verhindern."),

    ("lernen", "Aus wiederholten Fehlern Regeln machen",
     "Neben Sachverhalten (Knoten) fuehrt brainlehr Fehlerklassen (Lehren) "
     "mit Ursache, Behebung und Vermeidung. Wiederholt sich eine Lehre zum "
     "dritten Mal, eskaliert sie von selbst zur Regel.",
     "`lesson_record` mit type, description, root_cause, resolution, "
     "prevention; `lesson_query` zum Nachschlagen.",
     "Die Zaehlung erkennt nur, was als Wiederholung GEMELDET wird "
     "(`same_as`) oder wortgleich ist. Zwei Formulierungen derselben Sache "
     "bleiben zwei Lehren."),

    ("selbstmessung", "Die eigene Trefferquote kennen",
     "brainlehr misst, ob sein Abruf das Richtige findet -- gegen einen "
     "Pruefkorpus, teils blind bewertet, mit A/B-Vergleich zwischen "
     "Verfahren. Die Ergebnisse fallen regelmaessig schlecht aus.",
     "`abrufguete.py`, `pruefkorpus.py`, `wissensnutzen_blind.py`.",
     "Eine Messung gegen den eigenen Bestand misst die eigene Schreibweise "
     "mit. Deshalb liegt ein FREMDER Korpus bei (NASA-Lehren) -- und auch der "
     "ist nur ein Korpus, kein Beweis fuer die eigene Nuetzlichkeit."),

    ("vorschlag", "Vorschlagen, was fehlt",
     "Aus wiederkehrenden Handgriffen und ungenutzten Feldern leitet "
     "brainlehr Vorschlaege ab: welches Werkzeug fehlt, welcher Pruefstein "
     "faellig ist -- samt fertigem Auftragstext.",
     "`berichte/vorschlag.py`.",
     "Es schlaegt vor und startet nichts. Ein Vorschlag ist kein Befund: er "
     "beruht auf Mustern im Bestand, nicht auf einer Pruefung der Sache."),

    ("protokoll", "Nachweisen, was gelesen und geschrieben wurde",
     "Jeder Lese- und Schreibvorgang landet in `access_log`, per SHA-256 "
     "verkettet. Damit laesst sich beantworten, wer wann was gesehen hat -- "
     "und eine nachtraegliche Aenderung wird nachweisbar.",
     "`sichtbarkeit.py` macht Schreibvorgaenge im Gespraech sichtbar; "
     "`auditanker.py` bildet die Merkle-Wurzel.",
     "Nachweisbar heisst nicht verhindert: es gibt keine Signatur und keinen "
     "zweiten Rechner. Wer Schreibrechte auf die Datei hat, kann die Kette "
     "neu rechnen. Und das Protokoll ist selbst ein Bestand -- es traegt "
     "Aussagen ueber Personen und gehoert entsprechend geschuetzt."),
]


def texte() -> list[tuple[str, str, str]]:
    """(kennung, titel, volltext) -- ohne Datenbank, damit --zeigen und der
    Selbsttest ohne Bestand laufen."""
    raus = []
    for kennung, titel, kann, womit, grenze in FAEHIGKEITEN:
        raus.append((kennung, titel,
                     f"{kann}\n\nSO BENUTZT MAN ES\n{womit}\n\n"
                     f"WO DIE GRENZE LIEGT\n{grenze}"))
    return raus


# Der Einstiegsknoten. Er traegt die FRAGE in der Sprache des Fragenden --
# "was kannst du" fand ohne ihn null Treffer, obwohl elf Faehigkeitsknoten
# dalagen. Ein Knoten wird mit den Worten gefunden, die er TRAEGT, nicht mit
# denen, die jemand sucht (L-4d07e5: dieselbe Ursache liess eine vorhandene
# Lehre 19 Tage lang unauffindbar bleiben).
EINSTIEG = (
    "Was kannst du? Was kann brainlehr? Faehigkeiten, Uebersicht, Hilfe, "
    "Funktionen, wozu ist das gut, was leistet es, wobei hilft es.",
    "Was kann brainlehr? — Uebersicht der Faehigkeiten",
    """Diese Uebersicht beantwortet die Frage "was kannst du" und verweist auf
die einzelnen Faehigkeiten. Jede von ihnen nennt drei Dinge: was sie leistet,
mit welchem Werkzeug man sie benutzt, und wo ihre Grenze liegt.

Der dritte Teil ist der wichtigste. Eine Faehigkeitsliste ohne Grenzen erzeugt
Vertrauen, das die Sache nicht traegt -- deshalb steht bei jedem Punkt, wo er
aufhoert.

DIE ELF FAEHIGKEITEN
{liste}

WAS BRAINLEHR AUSDRUECKLICH NICHT IST
Keine Anonymisierung, keine Verschluesselung, keine Zertifizierung, kein
vollstaendiger Schutz gegen eingeschleuste Anweisungen, kein
Mehrbenutzerbetrieb. Jeder dieser Punkte ist bei der jeweiligen Faehigkeit
ausgefuehrt -- mit dem, was STATT DESSEN gebaut ist.

WIE MAN WEITERFRAGT
Diese Uebersicht ist ein Knoten wie jeder andere. Suche nach einem Stichwort
(Herkunft, Geltung, Belegrang, Widerspruch, Identitaet, Protokoll) und der
Speicher liefert die zugehoerige Faehigkeit samt Grenze.""")


PUBLIC_CONTEXT = (
    ("Public architecture", "Local-first architecture for the public release.",
     "Brainlehr is a local SQLite knowledge service exposed through MCP. It keeps "
     "semantic nodes and lessons separate, searches them with full text plus local "
     "embeddings, and records explicit provenance and relations. Public descriptions "
     "are generated from verified project artifacts; they do not include a user database."),
    ("Public workflow", "Verified workflow for project-aware coding.",
     "A client first ensures a compact project capsule, then loads task context in "
     "stages: summaries, selected direct relations, and selected full text. After a "
     "verified commit it records the affected files, checks transitive static consumers, "
     "and curates a semantic conclusion separately. Receipts name their static analyzer "
     "and supersede corrections without erasing them. Static imports and semantic similarity "
     "are never presented as runtime data flow; unsupported forms remain coverage gaps."),
)


def anlegen(db: Path | None = None) -> dict:
    """Idempotent: vorhandene Knoten werden aktualisiert, nicht verdoppelt."""
    import knowledge_mcp_server as kms
    if db is not None:
        kms.DB_PATH = db

    neu = geaendert = 0
    # Einstiegsknoten zuerst -- er ist der Elternknoten der uebrigen.
    liste = "\n".join(f"- {titel}" for _, titel, _ in texte())
    e_such, e_titel, e_text = EINSTIEG
    e_text = e_text.replace("{liste}", liste)
    if kms.knowledge_read(AST).get("error"):
        kms.knowledge_add(parent_path="/brainlehr", title=e_titel,
                          summary=e_such, content=e_text, source=QUELLE,
                          project_id="brainlehr",
                          norm_entscheidung="keine_norm",
                          norm_entschieden_grund="Uebersicht, keine Regel.",
                          anlass="skript")
        neu += 1
    else:
        kms.knowledge_update(node_id=AST, title=e_titel, summary=e_such,
                             content=e_text)
        geaendert += 1

    for kennung, titel, volltext in texte():
        # NICHT unter der Kennung nachsehen: knowledge_add leitet den Pfad aus
        # dem TITEL ab, nicht aus einer mitgegebenen Kennung. Die erste Fassung
        # suchte unter /faehigkeiten/<kennung>, fand nie etwas und meldete
        # darum bei jedem Lauf "11 neu" -- obwohl der Server sauber
        # aktualisierte und keine Dublette entstand. Der Zaehler log, nicht der
        # Bestand. Jetzt zaehlt der Rueckgabewert des Servers.
        erg = kms.knowledge_add(
                parent_path=AST, title=titel,
                summary=volltext.split("\n")[0][:400], content=volltext,
                source=QUELLE, neuer_ast=True, project_id="brainlehr",
                norm_entscheidung="keine_norm",
                norm_entschieden_grund=(
                    "Beschreibt eine Faehigkeit und ihre Grenze; setzt keine "
                    "Regel."),
                anlass="skript")
        if erg.get("status") == "created":
            neu += 1
        else:
            # knowledge_add protects paths from being overwritten.  Its
            # existing_id is therefore the explicit hand-off to the update
            # path; merely counting this result left the generated text stale.
            kms.knowledge_update(node_id=erg["existing_id"],
                                 summary=volltext.split("\n")[0][:400],
                                 content=volltext)
            geaendert += 1

    for titel, zusammenfassung, volltext in PUBLIC_CONTEXT:
        erg = kms.knowledge_add(
            parent_path=AST, title=titel, summary=zusammenfassung, content=volltext,
            source=QUELLE, neuer_ast=True, project_id="brainlehr",
            norm_entscheidung="keine_norm",
            norm_entschieden_grund="Public generated architecture/workflow description.",
            anlass="skript")
        if erg.get("status") == "created":
            neu += 1
        else:
            kms.knowledge_update(node_id=erg["existing_id"],
                                 summary=zusammenfassung, content=volltext)
            geaendert += 1

    # Freigeben: genau diese Knoten sollen in einem weitergebbaren Auszug
    # stehen. Der Rest von /brainlehr bleibt intern -- das ist
    # Arbeitsgeschichte, kein Handbuch.
    # verbinde_bestand statt sqlite3.connect: die Knoten sind gerade erst
    # ueber kms.knowledge_add angelegt worden, der Bestand existiert also
    # nachweislich -- der Schutz ist nur gegen einen extern gesetzten
    # kms.DB_PATH, der auf nichts zeigt (siehe kern/speicher.py::verbinde_bestand).
    conn = speicher.verbinde_bestand(kms.DB_PATH)
    try:
        n = conn.execute(
            "UPDATE knowledge_nodes SET freigabe='offen' "
            "WHERE path LIKE ? AND freigabe <> 'offen'", (f"{AST}%",)).rowcount
        conn.commit()
    finally:
        conn.close()
    return {"neu": neu, "aktualisiert": geaendert, "freigegeben": n}


def _selftest() -> None:
    t = texte()
    assert len(t) == len(FAEHIGKEITEN) >= 10, len(t)
    # Der Einstieg MUSS die Frage in der Sprache des Fragenden tragen --
    # ohne sie fand "was kannst du" null Treffer bei elf vorhandenen Knoten.
    such = EINSTIEG[0].lower()
    for frage in ("was kannst du", "was kann brainlehr", "faehigkeiten",
                  "uebersicht", "hilfe"):
        assert frage in such, f"Einstieg traegt {frage!r} nicht"
    kennungen = [k for k, _, _ in t]
    assert len(set(kennungen)) == len(kennungen), "doppelte Kennung"

    for kennung, titel, volltext in t:
        # Jede Faehigkeit MUSS ihre Grenze nennen -- ohne sie entsteht
        # Vertrauen, das die Sache nicht traegt. Das ist der Grund fuer diese
        # Datei, also wird es geprueft und nicht gehofft.
        assert "WO DIE GRENZE LIEGT" in volltext, kennung
        grenze = volltext.split("WO DIE GRENZE LIEGT")[1].strip()
        assert len(grenze) > 80, f"{kennung}: Grenze zu duenn ({len(grenze)})"
        # ... und einen Bezeichner, mit dem man sie benutzt (L-8c319e:
        # eine Anleitung ohne Namen ist unbenutzbar).
        womit = volltext.split("SO BENUTZT MAN ES")[1].split("WO DIE")[0]
        assert any(z in womit for z in (".py", "`", "knowledge_", "lesson_")), \
            f"{kennung}: nennt kein Werkzeug und kein Feld"
        # ... und keine interne Arbeitsgeschichte fuer fremde Leser.
        for wort in ("Betreiber", "heute", "gestern", "wir haben"):
            assert wort not in volltext, f"{kennung}: interner Bezug {wort!r}"

    print(f"selbstbeschreibung.py: Selbsttest gruen ({len(t)} Faehigkeiten, "
          f"jede mit Werkzeug und Grenze)")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--anlegen", action="store_true")
    p.add_argument("--zeigen", action="store_true")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        _selftest()
        return 0
    if a.anlegen:
        print(anlegen())
        return 0
    for kennung, titel, volltext in texte():
        print(f"\n## {titel}  ({AST}/{kennung})\n{volltext}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
