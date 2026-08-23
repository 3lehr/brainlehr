#!/usr/bin/env python3
"""ausschreibekatalog.py -- welche Caveman-Kuerzung im BESTAND etwas findet.

ANLASS (Aufgabe 65, Plan docs/PLAN_AUSSCHREIBEKATALOG_2026-08-13.md): Der
Betreiber hat Caveman angeordnet. Caveman kuerzt Prosa auf `db/auth/config/
req/res/fn/impl` (woertlich in ~/.claude/skills/caveman/SKILL.md, Zeile
"Abbreviate prose words"). Sobald das wirkt, sucht eine Antwort, die
"Implementierung" zu "impl" kuerzt, an genau den Eintraegen vorbei, die
"implementation"/"Implementierung" ausgeschrieben enthalten -- 133 Stueck bei
Commit 339eaee. Eine Suche nach der Kuerzung selbst findet dort: nichts.

SAAT NICHT AUS DEM GEDAECHTNIS. Die Kurzformen werden zur Laufzeit aus der
Caveman-Fertigkeit GELESEN (siehe _saat_kurzformen), nicht abgetippt -- sonst
driftet diese Datei unbemerkt von ihrer eigenen Quelle weg. Je Kurzform gibt
es ZWEI lange Formen, keine Erfindung, reine Woerterbucharbeit: die
englische UND die deutsche Ausschreibung (db=database/Datenbank,
auth=authentication/Anmeldung, config=configuration/Konfiguration,
req=request/Anfrage, res=response/Antwort, fn=function/Funktion,
impl=implementation/Umsetzung). Nachbesserung Aufgabe 65: eine Zuordnung nur
auf die englische Form uebersah, dass der Bestand deutsch ist -- 'Datenbank'
65 Erwaehnungen gegen 'database' 54, 'Funktion' 90 gegen 'function' 168,
beide Formen kommen vor.

TRIGRAMM-MINDESTLAENGE (Aufgabe 65, Nachbesserung). schema.sql setzt
tokenize='trigram' -- ein Trigramm braucht drei Zeichen, eine Anfrage darunter
kann strukturell nicht indiziert werden und findet auf dem Suchweg nichts,
auch wenn der Rohtext das Wort haeufig enthaelt ('db' 187 Erwaehnungen im
Rohtext, 0 Treffer ueber die Suche). Kurzformen unter drei Zeichen werden
darum IMMER aufgenommen, unabhaengig vom gemessenen Verhaeltnis -- siehe
_hartes_kriterium(). Trigramm deckt umgekehrt auch Teilstrings ab: eine Suche
nach 'impl' findet 'implementation' bereits ueber den gemeinsamen Trigramm-
Bestandteil, ohne dass die Anfrage die lange Form braucht. Enthaelt JEDE lange
Form eines Paares die Kurzform als Teilzeichenkette, leistet die Erweiterung
also nichts Neues und wird nicht aufgenommen -- unabhaengig vom Verhaeltnis.

BEWERTUNG AUS DEM BESTAND, SCHWELLE AUS DER VERTEILUNG. Fuer jedes Paar wird
gezaehlt, wie oft die Kurzform und wie oft die lange Form als eigenes Wort in
knowledge_nodes/lessons_learned steht (Wortgrenzen-Regex, kein Teilstring --
sonst faende "impl" sich selbst in "kompliziert"). `db` (187 Erwaehnungen
gegen 111 Erwaehnungen der langen Form) ist ein Gegenbeispiel: dort ist die
Kurzform selbst schon ein brauchbarer Suchbegriff und darf NICHT im selben
Topf wie `impl` (0:133) landen. Die Aufnahmeschwelle ist darum kein
Zufallswert, sondern die groesste Luecke in den sortierten
log((lang+1)/(kurz+1))-Verhaeltnissen der sieben Saat-Paare -- die Stelle, an
der die Messung selbst in zwei Gruppen zerfaellt.

DER KATALOG SCHLAEGT VOR, ER SETZT NICHT. `katalog()` liefert nur die Paare,
die die Schwelle ueberschritten haben -- kein Schreibzugriff, keine
Datenbankaenderung. Wer das Ergebnis nutzt (Schritt 2:
kern/anfrage_erweiterung.py), erweitert damit nur die ANFRAGE, nie den
gespeicherten Text: `L-d8c5fb` (buckeberg) -- "TG" wurde beim Einlesen still
zu "Tiefgarage" aufgeloest und wanderte in sieben abgeleitete Fundstellen,
zwei davon oeffentlich; das Objekt hat 9 Einzelgaragen und 7 Stellplaetze.
Ein Uebersetzen des GESPEICHERTEN Texts passiert hier nirgends -- diese Datei
liest nur, sie schreibt nie in knowledge_nodes/lessons_learned.

Aufruf:
    python3 kern/ausschreibekatalog.py --selftest
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "haken"))
import speicher  # noqa: E402

# Woerterbuchhafte Ausschreibung, englisch UND deutsch -- keine erfundenen
# Paare, siehe Modul-Docstring.
_LANGFORMEN: dict[str, list[str]] = {
    "db": ["database", "Datenbank"],
    "auth": ["authentication", "Anmeldung"],
    "config": ["configuration", "Konfiguration"],
    "req": ["request", "Anfrage"],
    "res": ["response", "Antwort"],
    "fn": ["function", "Funktion"],
    "impl": ["implementation", "Umsetzung"],
}

_CAVEMAN_SKILLS = (
    Path.home() / ".claude" / "skills" / "caveman" / "SKILL.md",
    Path.home() / ".agents" / "skills" / "caveman" / "SKILL.md",
)
_SAAT_ZEILE = re.compile(r"Abbreviate prose words \(([^)]+)\)")


def _saat_kurzformen() -> list[str]:
    """Liest die Kurzformenliste woertlich aus der Caveman-Fertigkeit --
    die einzige nicht geratene Quelle (Auftrag). Findet keine der beiden
    ueblichen Fertigkeits-Ablagen die Zeile, ist das ein Befund, kein
    stiller Rueckfall auf eine abgetippte Liste."""
    for pfad in _CAVEMAN_SKILLS:
        if not pfad.exists():
            continue
        treffer = _SAAT_ZEILE.search(pfad.read_text(encoding="utf-8"))
        if treffer:
            return [wort.strip().lower() for wort in treffer.group(1).split("/") if wort.strip()]
    raise RuntimeError(
        "Caveman-Kurzformenliste nicht gefunden (geprueft: "
        + ", ".join(str(p) for p in _CAVEMAN_SKILLS)
        + "). Ausschreibekatalog braucht die Ursache, nicht das Gedaechtnis."
    )


def saat() -> dict[str, list[str]]:
    """Kurzform -> Liste langer Formen, nur fuer Kurzformen, die die Caveman-
    Liste JETZT tatsaechlich nennt (schuetzt vor Drift, falls die Liste sich
    aendert und _LANGFORMEN nicht nachgezogen wurde)."""
    kurzformen = set(_saat_kurzformen())
    return {k: v for k, v in _LANGFORMEN.items() if k in kurzformen}


_WORTZEICHEN = "A-Za-zÄÖÜäöüß"


def _wortgrenze(begriff: str) -> re.Pattern:
    return re.compile(
        rf"(?<![{_WORTZEICHEN}]){re.escape(begriff)}(?![{_WORTZEICHEN}])",
        re.IGNORECASE,
    )


def _bestand_texte(conn) -> list[str]:
    knoten = conn.execute(
        "SELECT COALESCE(title,'')||' '||COALESCE(summary,'')||' '||COALESCE(content,'') "
        "FROM knowledge_nodes"
    ).fetchall()
    lehren = conn.execute(
        "SELECT COALESCE(description,'')||' '||COALESCE(root_cause,'')||' '"
        "||COALESCE(resolution,'')||' '||COALESCE(prevention,'') FROM lessons_learned"
    ).fetchall()
    return [r[0] for r in knoten] + [r[0] for r in lehren]


def zaehle_paar(texte: list[str], kurz: str, lang: str | list[str]) -> tuple[int, int]:
    """(Kurzform-Treffer, Langform-Treffer) ueber die gegebenen Texte,
    je Dokument-und-Form hoechstens einmal gezaehlt -- Wortgrenzen, kein
    Teilstring. `lang` ist eine oder mehrere lange Formen (Aufgabe 65,
    Nachbesserung: englisch UND deutsch) -- lang_n ist die SUMME der
    Treffer ueber alle uebergebenen Formen."""
    lang_formen = [lang] if isinstance(lang, str) else lang
    kurz_re = _wortgrenze(kurz)
    kurz_n = sum(1 for t in texte if kurz_re.search(t))
    lang_n = 0
    for form in lang_formen:
        lang_re = _wortgrenze(form)
        lang_n += sum(1 for t in texte if lang_re.search(t))
    return kurz_n, lang_n


_TRIGRAMM_MINDESTLAENGE = 3  # schema.sql: tokenize='trigram' -- kuerzer indiziert nicht.


def _zu_kurz_fuer_trigramm(kurz: str) -> bool:
    """Unter drei Zeichen kann tokenize='trigram' (schema.sql) die Kurzform
    strukturell nicht indizieren -- eine Suche danach findet nichts, egal wie
    haeufig sie im Rohtext steht. Darum: immer aufnehmen, vor jedem
    Verhaeltnis."""
    return len(kurz) < _TRIGRAMM_MINDESTLAENGE


def _alle_langformen_enthalten_kurzform(kurz: str, lang_formen: list[str]) -> bool:
    """Trigramm findet Teilstrings von selbst: eine Suche nach 'impl' trifft
    'implementation' schon ohne Erweiterung. Enthaelt JEDE lange Form die
    Kurzform als Teilzeichenkette, leistet die Erweiterung nichts Neues."""
    k = kurz.lower()
    return all(k in form.lower() for form in lang_formen)


def _hartes_kriterium(kurz: str, lang_formen: list[str]) -> bool | None:
    """Kriterien VOR dem Verhaeltnis (Aufgabe 65, Nachbesserung). `None`
    heisst: keines der beiden greift, das Verhaeltnis entscheidet."""
    if _zu_kurz_fuer_trigramm(kurz):
        return True
    if _alle_langformen_enthalten_kurzform(kurz, lang_formen):
        return False
    return None


def _schwelle_aus_verteilung(log_verhaeltnisse: list[float]) -> float:
    """Groesste Luecke der sortierten Werte, Schwelle = ihre Mitte. Bei
    weniger als zwei Werten gibt es keine Luecke -- 0.0 (jedes positive
    Verhaeltnis, also 'lang haeufiger als kurz', wird aufgenommen)."""
    if len(log_verhaeltnisse) < 2:
        return 0.0
    s = sorted(log_verhaeltnisse)
    luecken = [(s[i + 1] - s[i], (s[i] + s[i + 1]) / 2) for i in range(len(s) - 1)]
    return max(luecken, key=lambda breite_mitte: breite_mitte[0])[1]


def aufnehmen(log_verhaeltnis: float, schwelle: float) -> bool:
    """Die reine Entscheidungsregel, getrennt von der Messung -- Grenzwerttests
    pruefen genau diese Funktion, ohne den Bestand anzufassen."""
    return log_verhaeltnis > schwelle


def bewerte(db=None) -> dict[str, dict]:
    """Jedes Saat-Paar gegen den Bestand messen. Liefert Rohdaten UND
    Entscheidung -- wer nur die Vorschlaege braucht, nutzt katalog().

    Reihenfolge der Entscheidung (Aufgabe 65, Nachbesserung):
    1. hartes Kriterium (_hartes_kriterium: Trigramm-Mindestlaenge, dann
       Teilstring-Abdeckung) -- greift eines, entscheidet es allein.
    2. sonst das gemessene Verhaeltnis gegen die Schwelle, die nur aus den
       NICHT hart entschiedenen Paaren berechnet wird -- ein erzwungenes
       Paar (z. B. 'db' oder 'fn') soll die Luecken-Schwelle der anderen
       nicht verschieben."""
    with speicher.lesen(db) as conn:
        texte = _bestand_texte(conn)

    rohdaten: dict[str, dict] = {}
    for kurz, lang_formen in saat().items():
        kurz_n, lang_n = zaehle_paar(texte, kurz, lang_formen)
        # +1 gegen log(0) -- reine Glaettung, veraendert die Rangfolge nicht.
        log_verhaeltnis = math.log((lang_n + 1) / (kurz_n + 1))
        rohdaten[kurz] = {
            "lang": lang_formen,
            "kurz_n": kurz_n,
            "lang_n": lang_n,
            "log_verhaeltnis": log_verhaeltnis,
            "hart": _hartes_kriterium(kurz, lang_formen),
        }

    ratio_werte = [e["log_verhaeltnis"] for e in rohdaten.values() if e["hart"] is None]
    schwelle = _schwelle_aus_verteilung(ratio_werte)
    for eintrag in rohdaten.values():
        eintrag["schwelle"] = schwelle
        eintrag["aufgenommen"] = (
            aufnehmen(eintrag["log_verhaeltnis"], schwelle)
            if eintrag["hart"] is None
            else eintrag["hart"]
        )
    return rohdaten


def katalog(db=None) -> dict[str, list[str]]:
    """Nur die aufgenommenen Paare, kurz -> Liste langer Formen -- der
    Vorschlag, den kern/anfrage_erweiterung.py (Schritt 2) liest. Kein
    Schreibzugriff."""
    return {kurz: e["lang"] for kurz, e in bewerte(db).items() if e["aufgenommen"]}


def _selftest() -> None:
    # 1) Saat kommt aus der Datei, nicht aus dem Gedaechtnis.
    kurzformen = set(_saat_kurzformen())
    assert kurzformen == {"db", "auth", "config", "req", "res", "fn", "impl"}, kurzformen

    # 2) Grenzwert: ein Verhaeltnis knapp ueber der Schwelle wird aufgenommen,
    #    eines knapp darunter nicht -- unabhaengig vom Bestand.
    schwelle = 1.0
    assert aufnehmen(schwelle + 0.01, schwelle) is True
    assert aufnehmen(schwelle - 0.01, schwelle) is False
    assert aufnehmen(schwelle, schwelle) is False  # exakt auf der Schwelle: nicht ueber ihr

    # 3) Luecken-Schwelle: zwei klar getrennte Gruppen ergeben eine Schwelle
    #    zwischen ihnen, nicht irgendwo.
    schwelle_gemessen = _schwelle_aus_verteilung([-2.0, -1.8, 0.5, 0.7])
    assert -1.8 < schwelle_gemessen < 0.5, schwelle_gemessen

    # 4) Gegen den echten Bestand: 'db' und 'fn' sind unter drei Zeichen und
    #    MUESSEN aufgenommen werden (Trigramm-Mindestlaenge, Kriterium 1)
    #    -- unabhaengig vom Verhaeltnis, auch wenn 'db' im Rohtext haeufiger
    #    vorkommt als seine langen Formen. 'impl' MUSS aufgenommen werden,
    #    weil 'Umsetzung' (deutsche Form) die Kurzform nicht als Teilstring
    #    enthaelt und die lange Form insgesamt haeufiger vorkommt.
    bewertung = bewerte()
    if "db" in bewertung:
        assert bewertung["db"]["aufgenommen"] is True, bewertung["db"]
    if "fn" in bewertung:
        assert bewertung["fn"]["aufgenommen"] is True, bewertung["fn"]
    if "impl" in bewertung:
        assert bewertung["impl"]["aufgenommen"] is True, bewertung["impl"]

    # 5) Negativfall Kriterium 3: eine Abkuerzung ab drei Zeichen, deren
    #    lange Formen ALLE die Kurzform als Teilstring enthalten, wird NICHT
    #    aufgenommen -- Trigramm deckt sie bereits ab.
    assert _hartes_kriterium("xyz", ["xyzzy", "xyzabc"]) is False
    # Und der Grenzwert bei der Laenge selbst: zwei Zeichen immer aufnehmen,
    # drei Zeichen nur wenn nicht alle langen Formen die Kurzform enthalten.
    assert _hartes_kriterium("ab", ["irgendwas"]) is True
    assert _hartes_kriterium("abc", ["voellig anders"]) is None

    print("ausschreibekatalog: alle Selbsttests gruen")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        for kurz, eintrag in sorted(bewerte().items()):
            print(kurz, eintrag)
