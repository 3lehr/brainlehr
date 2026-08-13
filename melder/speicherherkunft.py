#!/usr/bin/env python3
"""Melder: traegt eine Antwort eine Aussage aus dem Speicher, ohne ihn zu nennen?

AUFTRAG 94 (docs/PLAN_GESAMT_2026-08-13.md, Schritt 0, "Linie 0").
Betreiberanweisung: "wen aus brainlehr sollte es in zukunft heissen:
brainlehr sagt: ..." -- ANLASSFALL: ein Befund samt Zahlen (0,531 gegen
0,527, daraus die Modellwahl bge-m3) wurde als eigene Aussage weitergegeben.
Er stammte vollstaendig aus dem eingespielten Knoten
/brainlehr/das-einbettungsmodell-trennt-auf, war sechs Tage alt und aus
einem Codestand, den es nicht mehr gibt. Aus der Formulierung war nichts
davon erkennbar.

WAS GEPRUEFT WIRD: haken/knowledge_recall_hook.py::log_recall() traegt seit
Auftrag 94 zusaetzlich "zahlen" (Kommazahlen mit >=2 Nachkommastellen aus
Titel/Zusammenfassung/Beschreibung/Praevention) neben den ohnehin schon
geloggten node_ids/lessons (Knoten-/Lehrkennungen) je Abruf-Zeile. Dieser
Melder liest die JUENGSTE recall_log-Zeile der laufenden Sitzung, prueft ob
eine dieser drei Kennungsarten WOERTLICH in der Antwort steht, UND ob die
Antwort den Speicher nennt ("brainlehr sagt"). Beides zutreffend -> still.
Nur die Kennung ohne die Nennung -> beanstandet.

MERKMALSWAHL, mit Begruendung (Auftragsvorgabe: seltenes Merkmal, nicht
"Speicher" -- das kommt in beiden Texten vor und beweist nichts):
Kommazahl mit >=2 Nachkommastellen, Knoten-ID (8 Hex-Zeichen), Lehren-ID
(L-xxxxxx). Alle drei sind bewusst Merkmale, die in normaler Prosa praktisch
nie zufaellig entstehen -- anders als ein Wort wie "Speicher", das in JEDER
Antwort ueber diesen Speicher vorkommen kann, ohne dass etwas daraus
uebernommen wurde.

NUR DIE JUENGSTE ZEILE DER SITZUNG, NICHT ALLE (das ist der wichtigste
Befund der Vormessung, siehe unten): Ueber die GANZE Sitzung gemessen
(recall_log.jsonl gegen echte Transcripts, 2026-08-13, 183 Sitzungen mit
auffindbarem Protokoll) erzeugte ein sitzungsweiter Abgleich handfeste
Fehlalarme der Form "Festgehalten als `68fe57e0`" / "Abgelegt als
`6059602d`" -- der Agent kuendigt dort einen SELBST GERADE ANGELEGTEN
Knoten an, dessen ID zufaellig spaeter im selben, langen Gespraech noch
einmal automatisch abgerufen wurde. Auf das JEWEILS EINE Abruf-Ereignis
verengt, das dem geprueften Zug unmittelbar vorausging (Paarung ueber
Zeitstempel gegen echte Antworten, gleiche Sitzungen): 179 Abruf-Zug-Paare,
12 Kandidaten, ALLE 12 stichprobenhaft nachgelesen -- durchweg woertliche
Zitate der GENAU DORT abgerufenen Lehre (zwei davon bereits korrekt mit
"brainlehr sagt" attribuiert), keiner davon ein Zufallstreffer. 0 von 12
Fehlalarme fuer die Merkmalswahl selbst; die uebrigen 10 sind echte
Befunde im Sinne dieses Auftrags (Zitat ohne die neue Formel -- die
Konvention existierte zum Zeitpunkt dieser Antworten noch nicht, hier
gemessen als Beleg fuer die Merkmalswahl, nicht als Vorwurf an die
Vergangenheit). Die Zahlen-Merkmalswahl selbst (Komma, >=2 Nachkomma-
stellen) trifft in derselben engen Fensterung 0x zufaellig -- gegen den
GANZEN Bestand (nicht sitzungsverengt) liegen nur 12 von 69 Formen
mehrfach vor (17%, durchweg wiederkehrende Statistikwerte wie "0,001"),
siehe Kommentar bei _ZAHL_RE in knowledge_recall_hook.py fuer die volle
Messung inkl. der verworfenen weiteren Regex-Formen (WCAG-Versionen,
deutsche Datumsangaben).

GRENZEN: reine Textpruefung, kein Netz, keine DB-Verbindung noetig (die
Kennzeichnung liegt bereits im Protokoll). Endet IMMER mit Ergebnis, wirft
nie -- der Aufrufer (haken/antwort_abruf.py) faengt trotzdem zusaetzlich ab
(Grenze aus dem Auftrag: "faellt er mit einem Fehler aus, gibt antwort_
abruf.py trotzdem sein eigenes Ergebnis aus"). Keine JSON-Ausgabe auf
stdout (nur pruefe() liefert ein dict, melde()/main() drucken reinen Text)
-- sonst zerreisst es die Ausgabe des Stop-Hooks, der diesen Melder nur
AUFRUFT, nicht kopiert.

Aufruf:
    python3 melder/speicherherkunft.py --selftest
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
import re
import sys
from pathlib import Path

sys.path.insert(0, str(_w / "haken"))
import ort  # noqa: E402 -- liefert RECALL_LOG (kein fest verdrahteter Dateiname hier)

# Nennt die Antwort den Speicher als Quelle? Wortlaut der Betreiberanordnung
# ("brainlehr sagt: ..."), tolerant gegen Gross-/Kleinschreibung und
# beliebigen Weissraum zwischen den Woertern (kein Doppelpunkt verlangt --
# der ist Stil, keine Bedingung).
_ATTRIBUTION_RE = re.compile(r"brainlehr\s+sagt", re.IGNORECASE)


def _juengste_zeile(session: str, log_path: str | Path) -> dict | None:
    """Letzte recall_log-Zeile dieser Sitzung -- NICHT alle (siehe Moduldoc:
    sitzungsweiter Abgleich erzeugte echte Fehlalarme durch selbst angelegte
    und spaeter zufaellig mitabgerufene IDs). Die Datei ist append-only und
    chronologisch; die juengste Zeile der Sitzung ist zum Zeitpunkt eines
    --stop-Aufrufs genau die, deren Abruf der gerade geprueften Antwort
    vorausging."""
    zeile = None
    try:
        with open(log_path, encoding="utf-8") as f:
            for roh in f:
                try:
                    d = json.loads(roh)
                except Exception:
                    continue
                if d.get("session") == session:
                    zeile = d
    except OSError:
        return None
    return zeile


def _marker(zeile: dict) -> list[str]:
    """Kandidaten aus einer Protokollzeile: Zahlen (neu, Auftrag 94),
    Knoten-IDs, Lehren-IDs (beide schon vorher geloggt). Leere/fehlende
    Werte fallen weg -- .get() statt harter Schluessel, damit Altzeilen ohne
    'zahlen' nicht brechen."""
    marker = []
    marker += [z for z in (zeile.get("zahlen") or []) if z]
    marker += [i for i in (zeile.get("node_ids") or []) if i]
    marker += [i for i in (zeile.get("lessons") or []) if i]
    return marker


def pruefe(antwort: str, session_id: str | None, log_path: str | None = None) -> dict:
    """Liefert marker_gefunden (welche Kennungen woertlich in der Antwort
    stecken), genannt (steht "brainlehr sagt" irgendwo in der Antwort) und
    beanstandet (marker_gefunden nicht leer UND nicht genannt)."""
    log_path = log_path if log_path is not None else str(ort.RECALL_LOG)
    if not session_id or not antwort:
        return {"marker_gefunden": [], "genannt": False, "beanstandet": False}
    zeile = _juengste_zeile(session_id[:8], log_path)
    if zeile is None:
        return {"marker_gefunden": [], "genannt": False, "beanstandet": False}
    treffer = sorted({m for m in _marker(zeile) if m in antwort})
    if not treffer:
        return {"marker_gefunden": [], "genannt": False, "beanstandet": False}
    genannt = bool(_ATTRIBUTION_RE.search(antwort))
    return {"marker_gefunden": treffer, "genannt": genannt, "beanstandet": not genannt}


def melde(antwort: str, session_id: str | None, log_path: str | None = None) -> str:
    ergebnis = pruefe(antwort, session_id, log_path)
    if not ergebnis["beanstandet"]:
        return ""
    kennungen = ", ".join(ergebnis["marker_gefunden"][:5])
    return (
        "UNGEKENNZEICHNET (speicherherkunft): diese Antwort traegt "
        f"{len(ergebnis['marker_gefunden'])} Angabe(n) aus dem zuletzt "
        f"eingespielten Speicherabruf ({kennungen}), ohne den Speicher als "
        "Quelle zu nennen ('brainlehr sagt'). Ein Treffer heisst nicht, "
        "dass die Angabe falsch ist -- nur, dass die Herkunft fehlt."
    )


# --- Selbsttest (rot vor gruen, temporaere JSONL-Datei, keine echte DB) ----

def _zeile_schreiben(pfad: Path, **feld) -> None:
    with open(pfad, "a", encoding="utf-8") as f:
        f.write(json.dumps(feld, ensure_ascii=False) + "\n")


def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "recall_log.jsonl"

        # A) ROT (Anlassfall nachgestellt): Zahl aus dem Block landet
        # woertlich in der Antwort, kein "brainlehr sagt" -- muss anschlagen.
        _zeile_schreiben(log, session="abc12345", zahlen=["0,531", "0,527"],
                          node_ids=[], lessons=[])
        antwort = "Deshalb bge-m3: 0,531 gegen 0,527 in der Messung."
        ergebnis = pruefe(antwort, "abc12345", str(log))
        assert ergebnis["beanstandet"] is True, ergebnis
        assert "0,531" in ergebnis["marker_gefunden"], ergebnis
        assert melde(antwort, "abc12345", str(log)) != ""

        # B) GRUEN, Negativfall 1 (der wichtigere laut Auftrag): dieselbe
        # Zahl, aber mit Nennung -- darf nicht mehr anschlagen.
        attrib = "Dazu brainlehr sagt: 0,531 gegen 0,527 in der Messung."
        ergebnis = pruefe(attrib, "abc12345", str(log))
        assert ergebnis["beanstandet"] is False, ergebnis
        assert ergebnis["genannt"] is True, ergebnis
        assert melde(attrib, "abc12345", str(log)) == ""

        # C) GRUEN, Negativfall 2: Antwort ganz ohne Bezug zum Block --
        # keine der Zahlen kommt vor.
        unbeteiligt = "Der Testlauf ist gruen, alles wie erwartet, keine Zahl hier."
        ergebnis = pruefe(unbeteiligt, "abc12345", str(log))
        assert ergebnis["beanstandet"] is False, ergebnis
        assert ergebnis["marker_gefunden"] == [], ergebnis

        # D) GRENZWERT: ein haeufiges Wort ("Speicher"), das zufaellig in
        # beiden Texten vorkommt, loest NICHT aus -- es ist gar kein Merkmal.
        haeufiges_wort = "Der Speicher kennt dieses Thema schon lange."
        ergebnis = pruefe(haeufiges_wort, "abc12345", str(log))
        assert ergebnis["beanstandet"] is False, ergebnis
        assert ergebnis["marker_gefunden"] == [], ("ein haeufiges Wort darf "
                                                     "kein Merkmal sein", ergebnis)

        # E) Knoten-/Lehren-Kennung als Merkmal, gleiche Bauform.
        log2 = Path(tmp) / "recall_log2.jsonl"
        _zeile_schreiben(log2, session="sess0001", zahlen=[],
                          node_ids=["07e3ae78"], lessons=["L-1056bb"])
        ergebnis = pruefe("Siehe `L-1056bb` fuer den Hintergrund.", "sess0001", str(log2))
        assert ergebnis["beanstandet"] is True, ergebnis
        assert ergebnis["marker_gefunden"] == ["L-1056bb"], ergebnis

        # F) NUR DIE JUENGSTE ZEILE zaehlt (siehe Moduldoc, echter Fehlalarm-
        # Fund aus der Vormessung): eine AELTERE Zeile derselben Sitzung
        # traegt eine Zahl, die die neuere nicht mehr traegt -- die Antwort,
        # die auf den NEUEREN Abruf folgt, darf dafuer nicht mehr anschlagen.
        log3 = Path(tmp) / "recall_log3.jsonl"
        _zeile_schreiben(log3, session="sess0002", zahlen=["1,234"], node_ids=[], lessons=[])
        _zeile_schreiben(log3, session="sess0002", zahlen=["9,876"], node_ids=[], lessons=[])
        ergebnis = pruefe("Vorhin war von 1,234 die Rede.", "sess0002", str(log3))
        assert ergebnis["beanstandet"] is False, ("nur die juengste Zeile "
                                                    "der Sitzung darf zaehlen", ergebnis)

        # G) Andere Sitzung, keine Sitzung, leere Antwort, fehlende Datei --
        # kein Absturz, kein Fehlalarm.
        assert pruefe("0,531 irgendwo", "andere-sitzung", str(log))["beanstandet"] is False
        assert pruefe("0,531 irgendwo", None, str(log))["beanstandet"] is False
        assert pruefe("", "abc12345", str(log))["beanstandet"] is False
        assert pruefe("0,531 irgendwo", "abc12345",
                       str(Path(tmp) / "gibt-es-nicht.jsonl"))["beanstandet"] is False

        # H) Kaputte Zeilen im Protokoll stoeren nicht -- werden uebersprungen.
        log4 = Path(tmp) / "recall_log4.jsonl"
        with open(log4, "a", encoding="utf-8") as f:
            f.write("das ist kein JSON\n")
        _zeile_schreiben(log4, session="sess0003", zahlen=["5,55"], node_ids=[], lessons=[])
        ergebnis = pruefe("Wert 5,55 hier.", "sess0003", str(log4))
        assert ergebnis["beanstandet"] is True, ergebnis

    print("speicherherkunft: Selbsttest gruen")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        _selftest()
        return
    p.print_help()


if __name__ == "__main__":
    main()
