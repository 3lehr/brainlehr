#!/usr/bin/env python3
"""Der erste Melder, der URTEILT statt zaehlt.

Anlass: Der Betreiber vermisste am 2026-08-09, dass sich Pruefer von selbst
melden -- frueher habe ein Skeptiker-Agent auf Dogmen hingewiesen. Die
Recherche ergab (L-479171): er hat NIE autonom gefeuert. Er war Schritt 3
einer von Hand gestarteten Pipeline, und die "ACTIVATION: proaktiv"-Zeilen
im Frontmatter waren Prosa fuer ein Modell, kein Mechanismus.

Die Lage ist trotzdem besser als damals: heute feuern 23 Haken autonom. Es
fehlt nicht an Autonomie, sondern daran, dass einer ein URTEIL faellt.

DER UNTERSCHIED, auf den es ankommt: Ein Melder vergleicht eine Schwelle
("18 Tage alt", "12 ohne Vermerk"). Ein Pruefer sagt, dass etwas SCHIEF
STEHT, obwohl keine Zahl ueberschritten ist. Das ist heikler, weil es
Fehlalarme gibt -- darum drei Auflagen fuer jede Pruefung hier:

  1. Sie muss sich aus dem Bestand MESSEN lassen, nicht aus Stimmung.
  2. Sie nennt, welcher Fehlklasse sie nachgeht -- ein Befund ohne
     Fehlklasse ist eine Meinung.
  3. Sie nennt den Preis eines Fehlalarms. Wer den nicht beziffern kann,
     hat die Pruefung nicht zu Ende gedacht.

Und sie schweigt, solange nichts anschlaegt. Ein Pruefer, der bei jedem
Start dasselbe sagt, wird ueberlesen -- dann faellt er genauso aus wie
einer, den es nicht gibt.

Aufruf:
    python3 pruefer.py             # alle Pruefungen, ausfuehrlich
    python3 pruefer.py --melder    # nur sprechen, wenn etwas anschlaegt
    python3 pruefer.py --selftest
"""
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
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(_w / "haken"))  # diese Datei liegt IN der Wurzel: eine Ebene, nicht zwei
import ort  # noqa: E402
import ausweis  # noqa: E402 -- Auftrag 2026-08-12: Rollenkatalog gegen Lesetabellen

# Woran ein KI-Entscheider erkennbar ist. Gleiche Liste wie in der
# Herkunftsschranke (schema.sql) -- bewusst hier wiederholt und nicht
# importiert, weil dieses Modul ohne Server und ohne Schemazugriff laufen
# koennen muss (Regel aus S7: jeder Lesepfad ohne den Server).
KI_MARKER = ("claude", "gpt", "gemini", "anthropic", "opus", "sonnet", "haiku")

# Ab wann eine Quote ueberhaupt etwas bedeutet. Unter dieser Zahl ist jede
# Prozentangabe Rauschen -- 2 von 3 sind 67 Prozent und sagen nichts.
MINDESTZAHL = 20


def _verbindung(db: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db or ort.DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def selbstzuschreibung(conn: sqlite3.Connection) -> dict | None:
    """Wieviele Normentscheidungen hat sich die Maschine selbst gegeben?

    FEHLKLASSE: stille Selbstermaechtigung. Eine Maschine, die ihre eigenen
    Aussagen fuer verbindlich erklaert, erzeugt eine Geltung ohne
    Gegenueber -- und niemandem faellt es auf, weil jede einzelne
    Entscheidung fuer sich plausibel aussieht.

    PREIS EINES FEHLALARMS: gering. Der Befund fordert kein Handeln, er
    macht eine Verteilung sichtbar. Wer ihn ignoriert, verliert nichts;
    wer ihm folgt, sieht sich 33 Zeilen an.

    Gemessen 2026-08-09 vor dem Bau: 62 von 72. Heute haette kein Melder
    das gesagt -- der Betreiber hat es selbst gefunden."""
    zeilen = conn.execute(
        "SELECT norm_entschieden_von FROM knowledge_nodes "
        "WHERE norm_rang IS NOT NULL AND zurueckgezogen = 0"
    ).fetchall()
    n = len(zeilen)
    if n < MINDESTZAHL:
        return None
    ki = sum(1 for z in zeilen
             if any(m in (z["norm_entschieden_von"] or "").lower() for m in KI_MARKER))
    anteil = ki / n
    if anteil < 0.5:
        return None
    return {
        "pruefung": "selbstzuschreibung",
        "befund": f"{ki} von {n} Normentscheidungen ({anteil:.0%}) hat ein KI-Akteur sich selbst gegeben",
        "fehlklasse": "stille Selbstermaechtigung -- Geltung ohne Gegenueber",
        "fehlalarm_kostet": "gering: der Befund fordert kein Handeln, er macht eine Verteilung sichtbar",
    }


# Ausnahmeliste fuer die generische stumme-Spalte-Pruefung (Auftrag
# 2026-08-09). Jede Spalte hier wurde einzeln am Schema (schema.sql)
# nachgesehen, keine geraten. Drei Sorten, wie im Auftrag verlangt:
# Schluessel, Zeitstempel der Anlage, technische Felder -- je Eintrag
# steht daneben, warum genau diese Spalte von Bauart her einwertig sein
# DARF, ohne dass das ein Schreiber-Ausfall waere.
_AUSNAHMEN_KNOWLEDGE_NODES = {
    "id": "Schluesselspalte (PRIMARY KEY) -- Eindeutigkeit ist die Bauart selbst",
    "path": "Schluesselspalte (UNIQUE NOT NULL) -- dasselbe wie id",
    "created_at": "Zeitstempel der Anlage (NOT NULL, strftime-Vorgabe) -- ein "
                  "Sammelimport darf identische Werte tragen, das ist kein Ausfall",
    "updated_at": "Zeitstempel der Aenderung, gleiche Begruendung wie created_at",
    "norm_rang": "technisches Unterscheidungsmerkmal Norm-vs-Fakt. Laut Schema-"
                 "Kommentar IST norm_rang IS NULL bei der Mehrheit der Zeilen "
                 "die Aussage selbst ('das hier ist ein Fakt, keine Norm') -- "
                 "keine Luecke, sondern der Zweck der Spalte",
    "zurueckgezogen": "technisches Statusflag -- eine ueberwiegende Mehrheit auf "
                      "0 ist der gesunde Normalfall (wenige Zurueckziehungen)",
    # Gemessen 2026-08-14, nicht angenommen -- und der SCHREIBER wurde
    # nachgeschlagen, bevor die Spalte hier landete (knowledge_mcp_server.py,
    # UPDATE ... access_count + 1 bei knowledge_read). Eine Spalte OHNE
    # Schreiber gehoerte gemeldet, diese hat einen.
    "access_count": "Nutzungszaehler. 2101 von 2195 auf 0 sind 96 Prozent und "
                    "trotzdem kein Ausfall: die Spalte zaehlt laut "
                    "kern/knowledge_lint.py AUSSCHLIESSLICH knowledge_read(), "
                    "nie browse oder search -- und gezielt gelesen wird nur ein "
                    "kleiner Teil eines Nachschlagebestands. Sie unterscheidet "
                    "sehr wohl: 94 Knoten ueber 0, gestaffelt bis 23. Dass die "
                    "Mehrheit nie GEZIELT geholt wurde, ist die Aussage der "
                    "Spalte, nicht ihr Versagen",
    # NUR HIER Ausnahme, NICHT bei lessons_learned und access_log -- die
    # Unterscheidung ist der eigentliche Befund und wurde gemessen:
    #   knowledge_nodes   78 von 2201 gesetzt  -> Schreiber arbeitet
    #   lessons_learned    0 von  902 gesetzt  -> kein Schreiber
    #   access_log         0 von 12972 gesetzt -> kein Schreiber
    # Dreimal dieselbe leere Spalte, aber nur einmal aus demselben Grund.
    "bedient_von": "beglaubigter Mensch hinter der schreibenden Maschine "
                   "(knowledge_mcp_server.py::_bedient_von). Selten ist hier "
                   "der Normalfall -- die meisten Schreibvorgaenge kommen von "
                   "einem Werkzeug ohne Menschenausweis. Der Schreiber ARBEITET "
                   "nachweislich: 78 von 2201 Zeilen tragen einen Wert. In "
                   "lessons_learned und access_log dagegen steht die Spalte bei "
                   "0 von 902 bzw. 0 von 12972 -- dort fehlt der Schreiber "
                   "wirklich, und dort wird weiter gemeldet",
}
_AUSNAHMEN_LESSONS_LEARNED = {
    "id": "Schluesselspalte (PRIMARY KEY)",
    "first_seen": "Zeitstempel der Anlage, gleiche Begruendung wie bei knowledge_nodes",
    "last_seen": "Zeitstempel der letzten Beobachtung, gleiche Begruendung",
    # Beide gemessen 2026-08-14, nicht angenommen -- die Einwertigkeit ist
    # hier die gesunde Verteilung, nicht ihr Ausfall.
    "status": "Lebenszyklus-Feld. 853 von 894 auf 'active' sind 95 Prozent und "
              "trotzdem kein Ausfall: es gibt fuenf belegte Werte, und die "
              "seltenen tragen die Aussage (13 escalated_to_rule, 25 resolved, "
              "2 in_claude_md, 1 open). Dass die Mehrheit offen ist, IST der "
              "Normalfall eines Lehrenbestands",
    "auto_rule_generated": "Kennzeichen der automatischen Eskalation. 12 von 894 "
                           "auf 1 sind 1 Prozent -- gemessen passt das zur "
                           "Schwelle: 16 Lehren haben occurrences>=3. Die Spalte "
                           "unterscheidet also, sie ist nur zu Recht selten",
}
_AUSNAHMEN_ACCESS_LOG = {
    "id": "Schluesselspalte (PRIMARY KEY AUTOINCREMENT)",
    "timestamp": "Zeitstempel der Anlage, gleiche Begruendung wie oben",
    "zeilen_hash": "technisches Auditketten-Feld -- laut Schema-Kommentar "
                   "planmaessig NULL bei reinen Lesezugriffen und bei "
                   "Loeschungen, dokumentierter Zustand, keine Luecke",
    "ketten_hash": "technisches Auditketten-Feld -- laut Schema-Kommentar fuer "
                   "alle Bestandszeilen vor der Migration NULL (kein "
                   "Kettenanfang vor 2026-08-06), dokumentierter Zustand",
}

# Sechs Spalten der Normschicht (schema.sql-Kommentar an knowledge_nodes)
# gelten nur fuer die Teilmenge der Zeilen, die ueberhaupt eine Norm sind
# (norm_rang IS NOT NULL) -- ausserhalb davon ist NULL Bauart, nicht
# Ausfall (dieselbe Begruendung wie oben bei norm_rang selbst). Statt sie
# auf die Ausnahmeliste zu setzen (und damit den urspruenglichen Fund an
# norm_art zu verlieren), bekommen sie den ENGEREN Nenner -- exakt das,
# was die alte Einzelpruefung schon fuer norm_art tat. Neu generisch: die
# anderen fuenf (gilt_ab, gilt_bis, norm_entschieden_*) wurden vorher nie
# geprueft.
_NORMSCHICHT_SPALTEN = {
    "norm_art", "gilt_ab",
    "norm_entschieden_von", "norm_entschieden_am", "norm_entschieden_grund",
    # 2026-08-14 nachgetragen: wurde ueber alle 2195 Zeilen gemessen statt
    # ueber die 85 Normen. Der Befund bleibt (85 von 85 leer), aber der
    # Nenner war falsch -- und ein Befund mit falschem Nenner ist beim
    # naechsten Lesen nicht nachpruefbar.
    "norm_entschieden_belegart",
}

# gilt_bis braucht einen NOCH engeren Nenner als die uebrige Normschicht und
# ist deshalb hier statt oben. knowledge_add verlangt bei 'norm_unbefristet'
# ausdruecklich, dass gilt_bis LEER BLEIBT -- ueber alle Normen gemessen war
# "98 Prozent leer" also wieder die Bauart und nicht der Ausfall. Gemessen
# 2026-08-14: 2 befristete Normen, beide mit gilt_bis; 78 unbefristete, alle
# 78 ohne; 5 mit noch offener Entscheidung, ebenfalls ohne. Der Nenner ist
# damit die befristete Norm, und solange es davon weniger als MINDESTZAHL
# gibt, schweigt die Pruefung -- richtig, aus zwei Zeilen folgt nichts.
_BEFRISTUNGS_SPALTEN = {"gilt_bis"}

# Dieselbe Konstruktion, aber der Fehler war hier STRUKTURELL garantiert und
# nicht bloss wahrscheinlich: Der Grundnenner dieser Tabelle ist
# 'zurueckgezogen = 0'. Die drei Rueckzugsspalten werden also ausgerechnet
# ueber den Zeilen gemessen, in denen sie definitionsgemaess leer sein
# MUESSEN -- 100 Prozent leer war kein Befund, sondern die einzige moegliche
# Antwort. Gemessen 2026-08-14: 2200 Knoten, 5 zurueckgezogen, und genau
# diese 5 tragen die Felder. Die Spalten unterscheiden also perfekt; der
# Melder meldete das Gegenteil.
#
# Nicht auf die Ausnahmeliste, sondern in den engeren Nenner: eine
# Rueckziehung OHNE Grund waere ein echter Fund, und den soll der Melder
# weiterhin sehen koennen. Solange es weniger als MINDESTZAHL Rueckziehungen
# gibt, greift die uebliche Untergrenze und es wird schlicht nichts gesagt --
# das ist richtig, aus fuenf Zeilen laesst sich nichts schliessen.
_RUECKZUGS_SPALTEN = {
    "zurueckgezogen_grund", "zurueckgezogen_von", "zurueckgezogen_am",
}


def _tabellenspalten(conn: sqlite3.Connection, tabelle: str) -> list[str]:
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({tabelle})")]


def _stille_spalten(conn: sqlite3.Connection, tabelle: str, wo: str,
                    ausnahmen: dict[str, str], sonderwo: dict[str, str] | None = None
                    ) -> list[dict]:
    """Prueft ALLE Spalten einer Tabelle generisch auf zwei Signaturen
    derselben Fehlklasse: durchgehend leer, oder durchgehend derselbe Wert
    (einwertig). Beides sagt dasselbe -- die Spalte unterscheidet nichts.

    FEHLKLASSE: gebaute Regel ohne Wirkung. Sie sieht im Quelltext aus wie
    Schutz oder wie eine erfasste Unterscheidung und traegt keine -- dieselbe
    Signatur wie vier Tokenspalten ueber 3638 Zeilen NULL und wie actor bei
    366 von 390 Zeilen ohne Aussage.

    PREIS EINES FEHLALARMS: gering, aber nicht null -- eine Spalte darf von
    Bauart her einwertig sein (Schluessel, Zeitstempel, technische Felder).
    Genau dafuer gibt es die Ausnahmeliste mit Begruendung je Eintrag; wer
    sie ignoriert, sieht sich eine Spalte an, die es nicht wert war.

    Schwelle 95 Prozent statt 100: anders als beim alten Einzelfall (nur
    100 Prozent leer) soll die generische Pruefung auch eine Spalte finden,
    die zu 96 Prozent 'unbekannt' sagt -- das unterscheidet praktisch
    nichts, auch wenn vier Zeilen einen echten Wert tragen."""
    funde = []
    for spalte in _tabellenspalten(conn, tabelle):
        if spalte in ausnahmen:
            continue
        eigene_wo = (sonderwo or {}).get(spalte, wo)
        leer_ausdruck = f"{spalte} IS NULL OR TRIM(CAST({spalte} AS TEXT))=''"
        r = conn.execute(
            f"SELECT COUNT(*) n, SUM(CASE WHEN {leer_ausdruck} THEN 1 ELSE 0 END) leer "
            f"FROM {tabelle} WHERE {eigene_wo}"
        ).fetchone()
        n, leer = r["n"] or 0, r["leer"] or 0
        if n < MINDESTZAHL:
            continue
        leer_anteil = leer / n
        if leer_anteil >= 0.95:
            funde.append({
                "pruefung": f"stumme_spalte:{tabelle}.{spalte}",
                "befund": f"{tabelle}.{spalte} ist bei {leer} von {n} Zeilen ({leer_anteil:.0%}) leer",
                "fehlklasse": "gebaute Regel ohne Wirkung -- Spalte unterscheidet nichts",
                "fehlalarm_kostet": "gering: eine Spalte darf ueberwiegend leer sein, "
                                    "steht sie nicht auf der begruendeten Ausnahmeliste, lohnt ein Blick",
            })
            continue
        top = conn.execute(
            f"SELECT TRIM(CAST({spalte} AS TEXT)) wert, COUNT(*) c FROM {tabelle} "
            f"WHERE ({eigene_wo}) AND NOT ({leer_ausdruck}) "
            f"GROUP BY wert ORDER BY c DESC LIMIT 1"
        ).fetchone()
        if top and (top["c"] / n) >= 0.95:
            anteil = top["c"] / n
            funde.append({
                "pruefung": f"stumme_spalte:{tabelle}.{spalte}",
                "befund": f"{tabelle}.{spalte} ist bei {top['c']} von {n} Zeilen ({anteil:.0%}) "
                          f"derselbe Wert ('{top['wert']}')",
                "fehlklasse": "gebaute Regel ohne Wirkung -- Spalte unterscheidet nichts",
                "fehlalarm_kostet": "gering: eine Spalte darf ueberwiegend einwertig sein, "
                                    "steht sie nicht auf der begruendeten Ausnahmeliste, lohnt ein Blick",
            })
    return funde


def stumme_spalten(conn: sqlite3.Connection) -> list[dict]:
    """Generische Fassung der stummen-Spalte-Pruefung ueber alle drei
    Kern-Tabellen (Auftrag 2026-08-09) -- ersetzt die alte Einzelpruefung,
    die nur auf norm_art zeigte. Siehe _stille_spalten fuer Fehlklasse und
    Preis, hier nur die drei Nenner + Ausnahmelisten je Tabelle."""
    sonderwo = {s: "norm_rang IS NOT NULL AND zurueckgezogen = 0" for s in _NORMSCHICHT_SPALTEN}
    sonderwo.update({s: "zurueckgezogen = 1" for s in _RUECKZUGS_SPALTEN})
    sonderwo.update({s: "norm_entscheidung = 'norm_befristet' AND zurueckgezogen = 0"
                     for s in _BEFRISTUNGS_SPALTEN})
    return (
        _stille_spalten(conn, "knowledge_nodes", "zurueckgezogen = 0",
                        _AUSNAHMEN_KNOWLEDGE_NODES, sonderwo)
        + _stille_spalten(conn, "lessons_learned", "1=1", _AUSNAHMEN_LESSONS_LEARNED)
        + _stille_spalten(conn, "access_log", "1=1", _AUSNAHMEN_ACCESS_LOG)
    )


# Epoche als Untergrenze, wenn ein Protokoll beim ersten Lauf leer ist --
# dann zaehlt ab dem naechsten Lauf jede vorhandene Zeile als "seit".
_EPOCHE = datetime(1970, 1, 1, tzinfo=timezone.utc)

# Feldname unterscheidet sich je Protokoll gemessen: recall_log.jsonl
# schreibt "ts", bereinigung_log.jsonl schreibt "zeit" -- keins der beiden
# schreibt "timestamp", das bleibt als dritter Kandidat fuer kuenftige
# Protokolle stehen.
_ZEITFELDER = ("ts", "timestamp", "zeit")


def _zeile_zeit(d: dict) -> datetime | None:
    """Liest das Zeitfeld einer Protokollzeile, oder None wenn keins passt."""
    for feld in _ZEITFELDER:
        wert = d.get(feld)
        if wert:
            try:
                return datetime.fromisoformat(str(wert).replace("Z", "+00:00"))
            except ValueError:
                return None
    return None


def _lies_zeiten(datei: Path) -> tuple[list[datetime], int]:
    """Liest alle Zeilen einer JSONL-Datei.

    Rueckgabe (Zeitstempel aller Zeilen mit verwertbarem Zeitfeld, Anzahl
    Zeilen OHNE eins -- kaputtes JSON zaehlt dazu). Die zweite Zahl wird nie
    verschluckt, sie geht an den Aufrufer weiter."""
    zeiten: list[datetime] = []
    uebersprungen = 0
    if not datei.exists():
        return zeiten, uebersprungen
    with datei.open(encoding="utf-8") as fh:
        for zeile in fh:
            zeile = zeile.strip()
            if not zeile:
                continue
            zeit = None
            try:
                zeit = _zeile_zeit(json.loads(zeile))
            except Exception:
                zeit = None
            if zeit is None:
                uebersprungen += 1
            else:
                zeiten.append(zeit)
    return zeiten, uebersprungen


def _seit_untergrenze(datei: Path) -> tuple[int, int] | None:
    """Zaehlt Protokollzeilen juenger als die gespeicherte Zeit-Untergrenze.

    Rueckgabe (Anzahl juengerer Zeilen, Anzahl uebersprungener Zeilen ohne
    Zeitfeld) -- oder None beim ersten Lauf: der setzt die Untergrenze aus
    der juengsten vorhandenen Zeile (Epoche, wenn keine da ist) und meldet
    nie sofort, aus demselben Grund wie vorher bei der Zeilenzahl."""
    zeiten, uebersprungen = _lies_zeiten(datei)
    marke = datei.with_suffix(datei.suffix + ".nulllinie")
    untergrenze = None
    if marke.exists():
        try:
            untergrenze = datetime.fromisoformat(marke.read_text(encoding="utf-8").strip())
        except ValueError:
            untergrenze = None   # altes Format (Zeilenzahl) -- wie erster Lauf behandeln
    if untergrenze is None:
        neu = max(zeiten) if zeiten else _EPOCHE
        marke.write_text(neu.isoformat(), encoding="utf-8")
        return None
    seit = sum(1 for z in zeiten if z > untergrenze)
    return seit, uebersprungen


def faellige_auswertung(conn: sqlite3.Connection) -> dict | None:
    """Wartet eine Auswertung auf genug FAELLE -- nicht auf genug Tage.

    FEHLKLASSE: Zeit als Massstab. "Eine Woche laufen lassen" ist derselbe
    Fehler wie "der Bestand ist noch klein" -- beides setzt einen Betrieb
    voraus, dessen Umfang niemand kennt. Eine Woche kann drei Abrufe
    bedeuten oder dreitausend; die Aussagekraft haengt an der Zahl der
    Faelle, nie am Kalender. Am 2026-08-09 habe ich die Zeitform zweimal an
    einem Tag benutzt, und der Betreiber hat beide Male widersprochen.

    PREIS EINES FEHLALARMS: keiner. Der Befund sagt "jetzt lohnt sich ein
    Blick", er verlangt nichts.

    Die offenen Auswertungen stehen unten als Tabelle -- Datei, Schwelle,
    was dann zu tun ist. Wer eine neue vertagt, traegt sie hier ein statt
    ein Datum zu nennen."""
    # NULLLINIE, und sie wird GEMESSEN statt eingetragen. Zweimal in drei
    # Minuten falsch gewesen: erst zaehlte der Melder den Gesamtbestand
    # (866 von 200 "erreicht", ueberwiegend aus dem alten Weg), dann trug
    # ich sie von Hand ein -- aus dem Hauptverzeichnis (42 Zeilen), waehrend
    # der Melder die Datei an SEINEM Ort liest (866). Zwei verschiedene
    # Dateien, eine Zahl.
    #
    # Darum: der erste Lauf legt die Nulllinie selbst an, dort wo er laeuft.
    # Eine Zahl, die im Quelltext steht, gilt fuer einen Ort, den der Autor
    # im Kopf hatte -- nicht fuer den, an dem sie gelesen wird.
    #
    # ZEIT statt ZEILENZAHL (L-cb3f28): eine Zeilenzahl sagt nichts darueber,
    # AB WANN ein Protokoll den Negativfall ueberhaupt aufzeichnet -- wer von
    # Hand nacheintraegt oder ein Protokoll zusammenfuehrt, verschiebt die
    # Zeilenzahl, nicht die Zeit. Darum haelt die Markerdatei jetzt einen
    # ISO-Zeitstempel, keinen Zaehlerstand, und es zaehlt nur, wessen
    # Zeitfeld JUENGER als dieser Stempel ist.
    offen = [
        # (Bezeichnung, Zaehldatei, zusaetzliche Faelle, was dann zu tun ist)
        ("Suchpfad im Abruf", ort.WURZEL / "recall_log.jsonl", 200,
         "frisch lesen, ob das Mehr an Zeichen Nutzen oder Rauschen ist -- "
         "und ob der Verlust des Schweigens (vorher 37,8 % leer) stoert"),
        ("Bereinigung", ort.WURZEL / "bereinigung_log.jsonl", 500,
         "python3 bereinigung.py --bericht -- Schwelle und Schwaerzung an "
         "gemessenen Daten entscheiden statt an geratenen"),
    ]
    faellig = []
    for name, datei, schwelle, dann in offen:
        try:
            ergebnis = _seit_untergrenze(datei)
        except Exception:
            continue
        if ergebnis is None:
            continue   # erster Lauf setzt die Untergrenze und meldet nie sofort
        seit, uebersprungen = ergebnis
        if seit >= schwelle:
            hinweis = f", {uebersprungen} ohne Zeitfeld uebersprungen" if uebersprungen else ""
            faellig.append(f"{name}: {seit} von {schwelle} Faellen seit der Umstellung{hinweis} -- {dann}")
    if not faellig:
        return None
    return {
        "pruefung": "faellige_auswertung",
        "befund": " | ".join(faellig),
        "fehlklasse": "Zeit als Massstab -- eine Woche kann drei Faelle bedeuten oder dreitausend",
        "fehlalarm_kostet": "keiner: der Befund sagt 'jetzt lohnt ein Blick', er verlangt nichts",
    }


def platzhalterfuellung(conn: sqlite3.Connection, spalte: str, zweck: str,
                        schwelle: float = 0.8) -> dict | None:
    """Eine Spalte, die formal gefuellt ist und nichts sagt.

    FEHLKLASSE: Tautologisch erfuelltes Pflichtfeld. Nicht dieselbe wie
    stumme_spalte -- die meldet nur bei 100 Prozent LEER, weil eine
    teilweise gefuellte Spalte wenigstens dort wirkt, wo sie gefuellt ist.
    Hier ist die Spalte GEFUELLT, aber mit 'unbekannt' bzw. leerem Text,
    und faellt damit durch beide Netze: kein NULL, also nicht stumm; kein
    Inhalt, also ohne Wirkung. Gemessen 2026-08-09 an actor/model:
    361 von 383 Knoten ausserhalb des NASA-Imports, darunter der Knoten,
    in dem ich zwei Minuten zuvor genau diese Felder als Alleinstellung
    gegen fremde Systeme aufgeschrieben hatte.

    Verwandt und schon belegt: L-7aad34 (source liess sich mit einer
    Tautologie erfuellen) und L-86e92d (ordnungsgemaess abgelegt, in einer
    Ablage, die der Empfaenger nicht kennt). Dieselbe Signatur, andere
    Spalte -- ein Feld sieht befuellt aus und traegt nichts.

    PREIS EINES FEHLALARMS: gering. 'unbekannt' kann ehrlich sein, wo die
    Herkunft wirklich nicht feststellbar war. Darum die Schwelle bei 80
    Prozent statt bei jedem Einzelfall, und darum nennt der Befund die
    Zahl mit, statt nur zu urteilen.

    Warum nicht bei 100 Prozent wie stumme_spalte: ein Identitaetsfeld,
    das bei vier von fuenf Zeilen 'unbekannt' sagt, ist als Nachweis schon
    tot -- man kann daraus keine Aussage ueber den Bestand mehr ziehen.
    Der Unterschied zwischen 80 und 100 Prozent aendert daran nichts.

    NUR ARBEITSBESTAND, und das ist keine Bequemlichkeit, sondern der
    Nenner. Beim ersten Entwurf zaehlte die Pruefung ueber ALLE Knoten und
    schwieg: 361 blinde von 2021 sind 18 Prozent, weil der NASA-Import mit
    1638 Zeilen einen echten Schreiber traegt ('nasa_llis_import.py') und
    die Quote verduennt. Gemessen, BEVOR die Pruefung eingebaut wurde --
    dieselbe Fehlerklasse wie 'ortsabhaengige Zahl' im Arbeitsmelder.
    Sachlich richtig ist der engere Nenner ohnehin: bei einem
    Nachschlagewerk IST der Schreiber der Importeur, das sagt nichts ueber
    die Herkunftskette. Beim Arbeitsbestand ist er der ganze Punkt."""
    leerwerte = ("unbekannt", "unknown", "", "n/a", "none", "null")
    platz = ",".join("?" * len(leerwerte))
    r = conn.execute(
        f"SELECT COUNT(*) n, SUM(LOWER(TRIM(COALESCE({spalte},''))) IN ({platz})) blind "
        f"FROM knowledge_nodes WHERE zurueckgezogen = 0 "
        f"AND COALESCE(gattung,'arbeitsbestand') = 'arbeitsbestand'", leerwerte
    ).fetchone()
    n, blind = r["n"] or 0, r["blind"] or 0
    if n < MINDESTZAHL or blind / n < schwelle:
        return None
    return {
        "pruefung": f"platzhalterfuellung:{spalte}",
        "befund": f"{spalte} sagt bei {blind} von {n} Zeilen ({blind / n:.0%}) nichts aus",
        "fehlklasse": f"tautologisch erfuelltes Pflichtfeld -- Zweck laut Schema: {zweck}",
        "fehlalarm_kostet": "gering: 'unbekannt' darf ehrlich sein, die Quote steht daneben",
    }


def rollen_ohne_lesetabelle(conn: sqlite3.Connection) -> dict | None:
    """Jede vergebbare Rolle mit einem Leserecht muss in einer der beiden
    Lesetabellen von knowledge_mcp_server.py stehen (_KNOWLEDGE_READ_VOLLZUGRIFF
    oder _KNOWLEDGE_READ_PROJEKTION) -- seit Commit ec3a443 gilt dort
    Default-Deny: eine Rolle in keiner der beiden bekommt
    {"error": "zugriff verweigert"}, auch wenn ROLLEN (kern/ausweis.py) ihr
    ein Leserecht gibt.

    QUELLE: kern.ausweis.ROLLEN (was ueberhaupt vergebbar ist), nicht die
    tatsaechlich ausgestellten Ausweise. Die Ausweisdatei traegt heute nur
    betreiber/fachkundig/schreiber, alle drei bereits eingetragen -- ein
    Vergleich gegen die Ausweisdatei waere also JETZT immer still und faende
    genau die Luecke nicht, die den Fehlerfall aus dem Auftrag ausmacht:
    eine Rolle steht schon in ROLLEN, wird aber erst MORGEN eingebuergert,
    und ihr Traeger sitzt dann vor der leeren Antwort. ROLLEN ist die Menge,
    die diesen Fall vor der Einbuergerung sichtbar macht.

    Gefiltert auf Rollen mit einem 'wissen:'-Recht oder '*' -- eine Rolle
    ganz ohne Leserecht (z.B. 'meldeamt': nur 'ausweis:ausstellen') kann
    _knowledge_read_projection nie mit Gewinn erreichen und gehoert nicht in
    dessen Tabellen; sie mitzuzaehlen waere ein Fehlalarm, der nie verstummt.

    FEHLKLASSE: vergessene Eintragung -- Rollenkatalog und Zugriffstabellen
    pflegen sich unabhaengig voneinander, Default-Deny macht das Vergessen
    zum Vollausfall statt zum (frueheren) Vollzugriff.

    PREIS EINES FEHLALARMS: keiner -- der Befund verlangt nur einen Eintrag
    in einer der beiden Tabellen, oder die begruendete Feststellung, dass
    die Rolle nie ueber diesen Weg lesen soll."""
    relevante = {name for name, rechte in ausweis.ROLLEN.items()
                 if "*" in rechte or any(r.startswith("wissen:") for r in rechte)}
    import knowledge_mcp_server as _server
    eingetragen = set(_server._KNOWLEDGE_READ_VOLLZUGRIFF) | set(_server._KNOWLEDGE_READ_PROJEKTION)
    fehlend = sorted(relevante - eingetragen)
    if not fehlend:
        return None
    return {
        "pruefung": "rollen_ohne_lesetabelle",
        "befund": f"Rolle(n) mit Leserecht ohne Eintrag in "
                  f"_KNOWLEDGE_READ_VOLLZUGRIFF/_KNOWLEDGE_READ_PROJEKTION: {', '.join(fehlend)}",
        "fehlklasse": "vergessene Eintragung -- Default-Deny macht sie zum Vollausfall",
        "fehlalarm_kostet": "keiner: der Befund verlangt nur einen Tabelleneintrag oder "
                            "die begruendete Feststellung, dass die Rolle nie so lesen soll",
    }


def alle(conn: sqlite3.Connection) -> list[dict]:
    funde = [
        selbstzuschreibung(conn),
        faellige_auswertung(conn),
        platzhalterfuellung(conn, "actor",
                            "wer die Aussage geschrieben hat -- traegt die ganze Herkunftskette"),
        platzhalterfuellung(conn, "model",
                            "welches Modell die Aussage geschrieben hat"),
        rollen_ohne_lesetabelle(conn),
    ]
    return [f for f in funde if f] + stumme_spalten(conn)


def _selftest() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE knowledge_nodes (norm_rang INTEGER, norm_art TEXT,
                    norm_entschieden_von TEXT, zurueckgezogen INTEGER DEFAULT 0)""")

    def fuelle(n, wer, art=None, rang=1, zurueck=0):
        for _ in range(n):
            conn.execute("INSERT INTO knowledge_nodes VALUES (?,?,?,?)", (rang, art, wer, zurueck))

    # Negativfall zuerst und er ist der wichtigste: unter der Mindestzahl
    # schweigt die Pruefung, auch bei 100 Prozent. Sonst meldet sie bei
    # zwei Zeilen einen Missstand.
    fuelle(3, "claude-code/opus-5")
    assert selbstzuschreibung(conn) is None, "unter der Mindestzahl wird nicht geurteilt"

    fuelle(30, "claude-code/opus-5")
    f = selbstzuschreibung(conn)
    assert f and "33 von 33" in f["befund"], f
    assert f["fehlklasse"] and f["fehlalarm_kostet"], "Fehlklasse und Preis sind Pflicht"

    # Gegenprobe: kippt die Mehrheit auf Menschen, schweigt die Pruefung.
    fuelle(40, "markus")
    assert selbstzuschreibung(conn) is None, "bei menschlicher Mehrheit kein Befund"

    # Zurueckgezogene zaehlen nicht mit.
    fuelle(100, "claude-code/opus-5", zurueck=1)
    assert selbstzuschreibung(conn) is None, "zurueckgezogene Zeilen duerfen nicht kippen"

    # Generische stumme Spalte -- fuenf Pflichtfaelle aus dem Auftrag
    # 2026-08-09. Eigene Tabelle "t", weil die Pruefung ALLE Spalten einer
    # Tabelle abgeht, nicht mehr eine benannte.
    g = sqlite3.connect(":memory:"); g.row_factory = sqlite3.Row
    g.execute("CREATE TABLE t (leer TEXT, verteilt TEXT, grenzwert TEXT, ausnahme TEXT)")

    def g_fuelle(n, leer=None, verteilt=None, grenzwert=None, ausnahme=None):
        for _ in range(n):
            g.execute("INSERT INTO t VALUES (?,?,?,?)", (leer, verteilt, grenzwert, ausnahme))

    # (d) zuerst, unter MINDESTZAHL: 19 Zeilen, 'leer' zu 100 Prozent leer,
    # trotzdem kein Befund -- die Mindestzahl schlaegt jede Prozentzahl.
    g_fuelle(19)
    assert _stille_spalten(g, "t", "1=1", {}) == [], "unter MINDESTZAHL wird nicht geurteilt, auch bei 100 Prozent"

    # (a) 100 Prozent leer, jetzt ueber der Mindestzahl -> gemeldet.
    g_fuelle(1)  # 20. Zeile, 'leer' bleibt NULL
    funde = _stille_spalten(g, "t", "1=1", {})
    treffer = [f for f in funde if f["pruefung"] == "stumme_spalte:t.leer"]
    assert treffer and "20 von 20" in treffer[0]["befund"], treffer

    # (b) gleichmaessig verteilte Werte -> kein Befund, egal wie viele Zeilen.
    g.execute("DELETE FROM t")
    for i in range(100):
        g.execute("INSERT INTO t (verteilt) VALUES (?)", (f"wert{i % 20}",))
    funde = _stille_spalten(g, "t", "1=1", {})
    assert not [f for f in funde if "verteilt" in f["pruefung"]], "gleichmaessige Verteilung ist kein Befund"

    # (c) Grenzwert: 94 Prozent Einwertigkeit schweigt, 95 Prozent meldet.
    g.execute("DELETE FROM t")
    for _ in range(94):
        g.execute("INSERT INTO t (grenzwert) VALUES ('x')")
    for _ in range(6):
        g.execute("INSERT INTO t (grenzwert) VALUES ('y')")
    funde = _stille_spalten(g, "t", "1=1", {})
    assert not [f for f in funde if "grenzwert" in f["pruefung"]], "94 Prozent ist unter der Schwelle"
    g.execute("UPDATE t SET grenzwert = 'x' WHERE grenzwert = 'y' AND rowid IN (SELECT rowid FROM t WHERE grenzwert='y' LIMIT 1)")
    funde = _stille_spalten(g, "t", "1=1", {})
    treffer = [f for f in funde if "grenzwert" in f["pruefung"]]
    assert treffer and "95 von 100" in treffer[0]["befund"], (treffer, "bei 95 Prozent muss gemeldet werden")

    # (e) Ausnahmeliste: eine Spalte, die 100 Prozent leer ist, aber auf
    # der Ausnahmeliste steht, wird NICHT gemeldet.
    g.execute("DELETE FROM t")
    g_fuelle(25)
    funde_ohne_ausnahme = _stille_spalten(g, "t", "1=1", {})
    assert [f for f in funde_ohne_ausnahme if "ausnahme" in f["pruefung"]], "Kontrollprobe: ohne Ausnahmeliste wird gemeldet"
    funde_mit_ausnahme = _stille_spalten(g, "t", "1=1", {"ausnahme": "Testbegruendung"})
    assert not [f for f in funde_mit_ausnahme if "ausnahme" in f["pruefung"]], "Ausnahmeliste muss greifen"

    # Normschicht-Sonderfall: norm_art wird nur INNERHALB der Normen
    # geprueft (norm_rang IS NOT NULL), nicht ueber den ganzen Bestand --
    # das ist der urspruengliche Einzelfund, den die generische Fassung
    # nicht verlieren darf.
    n2 = sqlite3.connect(":memory:"); n2.row_factory = sqlite3.Row
    n2.execute("""CREATE TABLE knowledge_nodes (id TEXT, path TEXT, norm_rang INTEGER,
                 norm_art TEXT, gilt_ab TEXT, gilt_bis TEXT, norm_entschieden_von TEXT,
                 norm_entschieden_am TEXT, norm_entschieden_grund TEXT,
                 norm_entscheidung TEXT, created_at TEXT, updated_at TEXT,
                 zurueckgezogen INTEGER DEFAULT 0)""")
    for i in range(25):
        n2.execute("INSERT INTO knowledge_nodes "
                   "VALUES (?,?,1,NULL,NULL,NULL,'x','x','x','norm_unbefristet','t','t',0)",
                   (str(i), str(i)))
    for i in range(500):  # viele Fakt-Zeilen ohne norm_rang -- duerfen die Quote nicht verduennen
        n2.execute("INSERT INTO knowledge_nodes "
                   "VALUES (?,?,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'t','t',0)",
                   (f"f{i}", f"f{i}"))
    # gilt_bis darf hier NICHT anschlagen: 25 unbefristete Normen muessen es
    # leer lassen, befristete gibt es keine. Das ist der Nenner-Fall.
    assert not [f for f in stumme_spalten(n2)
                if f["pruefung"] == "stumme_spalte:knowledge_nodes.gilt_bis"], (
        "gilt_bis: unbefristete Normen MUESSEN es leer lassen -- sie duerfen "
        "nicht der Nenner sein")
    funde = stumme_spalten(n2)
    treffer = [f for f in funde if f["pruefung"] == "stumme_spalte:knowledge_nodes.norm_art"]
    assert treffer and "25 von 25" in treffer[0]["befund"], (treffer, "norm_art muss auf die Normen-Teilmenge bezogen sein, nicht auf 525 Zeilen")
    # id/path/created_at/updated_at/norm_rang/zurueckgezogen stehen auf der
    # Ausnahmeliste und duerfen trotz Einwertigkeit nicht auftauchen.
    for spalte in ("id", "path", "created_at", "updated_at", "norm_rang", "zurueckgezogen"):
        assert not [f for f in funde if f["pruefung"] == f"stumme_spalte:knowledge_nodes.{spalte}"], spalte

    # Rueckzugs-Sonderfall. Der Grundnenner der Tabelle ist
    # 'zurueckgezogen = 0' -- ueber DIESEN Zeilen muessen die drei
    # Rueckzugsspalten leer sein, "100 Prozent leer" war dort also die
    # einzige moegliche Antwort und nie ein Befund. Geprueft wird deshalb
    # innerhalb der zurueckgezogenen Zeilen.
    n3 = sqlite3.connect(":memory:"); n3.row_factory = sqlite3.Row
    n3.execute("""CREATE TABLE knowledge_nodes (id TEXT, path TEXT, norm_rang INTEGER,
                 zurueckgezogen_grund TEXT, zurueckgezogen_von TEXT,
                 zurueckgezogen_am TEXT, norm_entscheidung TEXT,
                 created_at TEXT, updated_at TEXT,
                 zurueckgezogen INTEGER DEFAULT 0)""")
    for i in range(25):  # sauber zurueckgezogen: Grund, Urheber, Zeitpunkt stehen
        # Werte je Zeile verschieden: _stille_spalten kennt ZWEI Signaturen,
        # leer UND einwertig. 25x derselbe Grund waere einwertig und damit zu
        # Recht ein Fund -- er wuerde hier den Nenner-Fall verdecken.
        n3.execute("INSERT INTO knowledge_nodes VALUES (?,?,NULL,?,?,?,NULL,'t','t',1)",
                   (f"z{i}", f"z{i}", f"grund{i}", f"wer{i}", f"wann{i}"))
    for i in range(500):  # lebende Zeilen -- hier MUESSEN die drei leer sein
        n3.execute("INSERT INTO knowledge_nodes VALUES (?,?,NULL,NULL,NULL,NULL,NULL,'t','t',0)",
                   (f"l{i}", f"l{i}"))
    funde = stumme_spalten(n3)
    for spalte in _RUECKZUGS_SPALTEN:
        assert not [f for f in funde if f["pruefung"] == f"stumme_spalte:knowledge_nodes.{spalte}"], (
            f"{spalte}: 500 lebende Zeilen duerfen den Nenner nicht stellen -- "
            "dort ist leer die Bauart, nicht der Ausfall")

    # Gegenprobe, damit der engere Nenner nicht einfach blind macht: wird
    # zurueckgezogen OHNE Grund, ist das ein echter Fund und muss kommen.
    n3.execute("UPDATE knowledge_nodes SET zurueckgezogen_grund = NULL WHERE zurueckgezogen = 1")
    treffer = [f for f in stumme_spalten(n3)
               if f["pruefung"] == "stumme_spalte:knowledge_nodes.zurueckgezogen_grund"]
    assert treffer and "25 von 25" in treffer[0]["befund"], (
        treffer, "Rueckziehung ohne Grund muss gemeldet werden, bezogen auf die 25")

    # Platzhalterfuellung. Eigene Tabelle, weil gattung dazukommt.
    c3 = sqlite3.connect(":memory:"); c3.row_factory = sqlite3.Row
    c3.execute("""CREATE TABLE knowledge_nodes (actor TEXT, gattung TEXT,
                  zurueckgezogen INTEGER DEFAULT 0)""")

    def p3(n, actor, gattung='arbeitsbestand', zur=0):
        for _ in range(n):
            c3.execute("INSERT INTO knowledge_nodes VALUES (?,?,?)", (actor, gattung, zur))

    # Negativfall: unter der Mindestzahl schweigt sie, auch bei 100 Prozent.
    p3(5, "unbekannt")
    assert platzhalterfuellung(c3, "actor", "z") is None, "unter der Mindestzahl kein Urteil"

    # Grenzwert um die Schwelle: 79 Prozent schweigt, 80 Prozent meldet.
    c3.execute("DELETE FROM knowledge_nodes")
    p3(79, "unbekannt"); p3(21, "markus")
    assert platzhalterfuellung(c3, "actor", "z") is None, "79 Prozent ist unter der Schwelle"
    c3.execute("DELETE FROM knowledge_nodes")
    p3(80, "unbekannt"); p3(20, "markus")
    f3 = platzhalterfuellung(c3, "actor", "z")
    assert f3 and "80 von 100" in f3["befund"], f3
    assert f3["fehlklasse"] and f3["fehlalarm_kostet"], "Fehlklasse und Preis sind Pflicht"

    # Der Fehler, der beim Bau fast durchging: ein Nachschlagewerk mit
    # echtem Schreiber darf die Quote NICHT verduennen.
    p3(1000, "nasa_llis_import.py", gattung="nachschlagewerk")
    f4 = platzhalterfuellung(c3, "actor", "z")
    assert f4 and "80 von 100" in f4["befund"], ("Nachschlagewerk darf den Nenner nicht aufblaehen", f4)

    # Gegenprobe in die andere Richtung: echte Schreiber im Arbeitsbestand
    # muessen den Melder wieder zum Schweigen bringen.
    p3(200, "claude-code/opus-5")
    assert platzhalterfuellung(c3, "actor", "z") is None, "echte Schreiber loeschen den Befund"

    # Leerer Text zaehlt wie 'unbekannt' -- sonst faellt er durch beide Netze.
    c3.execute("DELETE FROM knowledge_nodes")
    p3(30, ""); p3(2, "markus")
    assert platzhalterfuellung(c3, "actor", "z") is not None, "leerer Text ist auch blind"

    # Zeit-Untergrenze statt Zeilenzahl-Nulllinie (L-cb3f28): eine Zeile
    # zaehlt nur, wenn ihr Zeitfeld JUENGER als die gespeicherte Untergrenze
    # ist -- Grenzwert bei Untergrenze-1/-genau/-plus1, plus der Negativfall
    # "kein Zeitfeld wird uebersprungen und ausgewiesen, nicht verschluckt".
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        protokoll = Path(tmp) / "z.jsonl"
        marke = Path(tmp) / "z.jsonl.nulllinie"
        marke.write_text("2026-08-09T12:00:00+00:00", encoding="utf-8")
        protokoll.write_text(
            '{"ts": "2026-08-09T11:59:59+00:00", "x": 1}\n'   # Untergrenze-1s: zaehlt NICHT
            '{"ts": "2026-08-09T12:00:00+00:00", "x": 2}\n'   # genau Untergrenze: zaehlt NICHT
            '{"ts": "2026-08-09T12:00:01+00:00", "x": 3}\n'   # Untergrenze+1s: zaehlt
            '{"x": 4}\n',                                      # kein Zeitfeld: uebersprungen
            encoding="utf-8",
        )
        seit, uebersprungen = _seit_untergrenze(protokoll)
        assert seit == 1, f"nur die Zeile nach der Untergrenze darf zaehlen, war {seit}"
        assert uebersprungen == 1, f"die Zeile ohne Zeitfeld muss ausgewiesen sein, war {uebersprungen}"

    # rollen_ohne_lesetabelle: vollstaendig kontrollierte Wegwerf-Kulisse fuer
    # beide Faelle -- ROLLEN und die beiden echten Lesetabellen werden per
    # Monkeypatch auf erfundene Werte gesetzt und danach exakt
    # wiederhergestellt. NICHT gegen den echten Bestand geprueft: der traegt
    # heute die Rolle 'leser' (wissen:lesen) ohne Eintrag in einer der beiden
    # Tabellen -- ein echter Befund (siehe Bericht), keine Testkulisse, und
    # darum hier bewusst nicht als Negativfall verwendet.
    import knowledge_mcp_server as _server
    _alte_rollen = dict(ausweis.ROLLEN)
    _alte_voll = frozenset(_server._KNOWLEDGE_READ_VOLLZUGRIFF)
    _alte_proj = dict(_server._KNOWLEDGE_READ_PROJEKTION)
    ausweis.ROLLEN.clear()
    ausweis.ROLLEN.update({
        "testbetreiber": ("*",),
        "testleser": ("wissen:lesen",),
        # kein Leserecht -- darf nie gemeldet werden, auch wenn sie fehlt.
        "testmeldeamt": ("ausweis:ausstellen",),
    })
    try:
        _server._KNOWLEDGE_READ_VOLLZUGRIFF = frozenset({"testbetreiber", "testleser"})
        _server._KNOWLEDGE_READ_PROJEKTION = {}
        assert rollen_ohne_lesetabelle(conn) is None, "vollstaendig eingetragen muss schweigen"

        # Rote Kulisse: 'testleser' hat ein Leserecht, steht aber in keiner
        # der beiden Tabellen -- das ist der Fall aus dem Auftrag.
        _server._KNOWLEDGE_READ_VOLLZUGRIFF = frozenset({"testbetreiber"})
        f = rollen_ohne_lesetabelle(conn)
        assert f and "testleser" in f["befund"], f
        assert f["fehlklasse"] and f["fehlalarm_kostet"], "Fehlklasse und Preis sind Pflicht"
        assert "testmeldeamt" not in f["befund"], (
            "Rolle ohne Leserecht darf nie gemeldet werden", f)
    finally:
        ausweis.ROLLEN.clear()
        ausweis.ROLLEN.update(_alte_rollen)
        _server._KNOWLEDGE_READ_VOLLZUGRIFF = _alte_voll
        _server._KNOWLEDGE_READ_PROJEKTION = _alte_proj

    print("selftest ok (20 Faelle)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--melder", action="store_true", help="nur sprechen, wenn etwas anschlaegt")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--db", type=Path, default=None)
    a = p.parse_args()
    if a.selftest:
        _selftest()
        return
    conn = _verbindung(a.db)
    funde = alle(conn)
    conn.close()

    if a.melder:
        if funde:
            zeilen = [f"{f['befund']} ({f['fehlklasse']})" for f in funde]
            print("⚠️ Pruefer: " + "\n   ".join(zeilen))
        return

    if not funde:
        print("Pruefer: nichts anzumerken.")
        return
    for f in funde:
        print(f"[{f['pruefung']}] {f['befund']}")
        print(f"   Fehlklasse:  {f['fehlklasse']}")
        print(f"   Fehlalarm:   {f['fehlalarm_kostet']}")


if __name__ == "__main__":
    main()
