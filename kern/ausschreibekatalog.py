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
driftet diese Datei unbemerkt von ihrer eigenen Quelle weg. Die LANGE Form je
Kurzform ist keine Erfindung: es ist die woerterbuchhafte Ausschreibung der
Abkuerzung selbst (db=database, auth=authentication, config=configuration,
req=request, res=response, fn=function, impl=implementation) -- kein
geratenes Synonym, keine Uebersetzung.

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

# Woerterbuchhafte Ausschreibung -- keine erfundenen Paare, siehe Modul-Docstring.
_LANGFORMEN: dict[str, str] = {
    "db": "database",
    "auth": "authentication",
    "config": "configuration",
    "req": "request",
    "res": "response",
    "fn": "function",
    "impl": "implementation",
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


def saat() -> dict[str, str]:
    """Kurzform -> lange Form, nur fuer Kurzformen, die die Caveman-Liste
    JETZT tatsaechlich nennt (schuetzt vor Drift, falls die Liste sich
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


def zaehle_paar(texte: list[str], kurz: str, lang: str) -> tuple[int, int]:
    """(Kurzform-Treffer, Langform-Treffer) ueber die gegebenen Texte,
    je Dokument hoechstens einmal gezaehlt -- Wortgrenzen, kein Teilstring."""
    kurz_re = _wortgrenze(kurz)
    lang_re = _wortgrenze(lang)
    kurz_n = sum(1 for t in texte if kurz_re.search(t))
    lang_n = sum(1 for t in texte if lang_re.search(t))
    return kurz_n, lang_n


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
    Entscheidung -- wer nur die Vorschlaege braucht, nutzt katalog()."""
    with speicher.lesen(db) as conn:
        texte = _bestand_texte(conn)

    rohdaten: dict[str, dict] = {}
    for kurz, lang in saat().items():
        kurz_n, lang_n = zaehle_paar(texte, kurz, lang)
        # +1 gegen log(0) -- reine Glaettung, veraendert die Rangfolge nicht.
        log_verhaeltnis = math.log((lang_n + 1) / (kurz_n + 1))
        rohdaten[kurz] = {
            "lang": lang,
            "kurz_n": kurz_n,
            "lang_n": lang_n,
            "log_verhaeltnis": log_verhaeltnis,
        }

    schwelle = _schwelle_aus_verteilung([e["log_verhaeltnis"] for e in rohdaten.values()])
    for eintrag in rohdaten.values():
        eintrag["schwelle"] = schwelle
        eintrag["aufgenommen"] = aufnehmen(eintrag["log_verhaeltnis"], schwelle)
    return rohdaten


def katalog(db=None) -> dict[str, str]:
    """Nur die aufgenommenen Paare, kurz -> lang -- der Vorschlag, den
    kern/anfrage_erweiterung.py (Schritt 2) liest. Kein Schreibzugriff."""
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

    # 4) Gegen den echten Bestand: db darf NICHT aufgenommen werden (eigenes
    #    Vorkommen dominiert), impl MUSS aufgenommen werden (lange Form
    #    dominiert klar). Negativfall und Positivfall in einem Lauf.
    bewertung = bewerte()
    if "db" in bewertung:
        assert bewertung["db"]["aufgenommen"] is False, bewertung["db"]
    if "impl" in bewertung:
        assert bewertung["impl"]["aufgenommen"] is True, bewertung["impl"]

    print("ausschreibekatalog: alle Selbsttests gruen")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        for kurz, eintrag in sorted(bewerte().items()):
            print(kurz, eintrag)
