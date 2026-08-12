#!/usr/bin/env python3
"""regelpaket.py -- Export/Import von CLAUDE.md-Regeln fuer fremde Instanzen.

ANLASS: brainlehr wird ueber GitHub installiert. Die Regeldateien
(~/.claude/CLAUDE.md, hub/CLAUDE.md), die diesen Speicher erst nutzbar machen,
werden dabei NICHT mitgeliefert -- ein frischer Nutzer bekommt eine leere
Datenbank und haelt sie fuer das Produkt. Betreiberauftrag: die Regeln nach
Kategorie geordnet mitliefern, so dass der neue Nutzer waehlen kann, und die
Frage, ob eine importierte Regel eine eigene brechen darf, technisch statt
per Disziplin beantworten.

TEIL 1 -- DIE TRENNUNG (Auftragspunkt 1). Von 35 Abschnitten (18 global + 17
hub, beide Zahlen mit `grep -c '^## '` nachgezaehlt) sind 24 UEBERTRAGBAR --
sie nennen keinen Pfad, kein Projekt und kein Geraet des Betreibers, die zum
Verstehen der Regel noetig waeren. Die uebrigen 11 sind BETREIBERSPEZIFISCH,
u.a. weil ihre eigentliche Handlung an einem Pfad haengt, der bei einer
fremden Installation nicht existiert -- global: 'BSI-Compliance' (laedt
hub/shared-knowledge/bsi-dev-profile.json), 'Wissen festhalten & abrufen'
(hub/scripts/knowledge_recall_hook.py), 'Testumgebung: handeln statt
vorlegen' (woertliches Betreiberzitat, eine Freigabe an EINE Person); hub:
'Fokus' (apps/fahrtenbuch_legacy), 'Hard Stops' (/Volumes/daten-Pfad),
'Konsile & ADRs', 'Arbeitsweise', 'Routing (Subagents)', 'Fluss-Karten', alle
mit begod/- bzw. hub/-Pfaden, 'Modell-Kaskade v3' (Kostenmessung in Euro fuer
15 KONKRETE Repos), 'Eskalierte Lehren' (L-IDs, die nur in dieser DB
existieren). Diese Trennung ist HARDCODIERTE DATEN unten (REGELN), keine
Heuristik auf dem Text -- ein Wortfilter haette hier mehr geraten als
gemessen; die Zuordnung ist eine Leseentscheidung und steht als solche im
Bericht, nicht im Code als Erratungslogik.

TEIL 2 -- FORMAT. Jede Regel im Paket traegt Herkunft (welche Datei),
Kategorie (s.u.) und ob der Abschnittstext selbst eine Begruendung enthaelt
(nicht nur eine Anweisung) -- 22 von 24 tun das; die zwei Ausnahmen sind reine
Stil-/Kommunikationsvorgaben ('Caveman mode', 'Identitaet') ohne Warum im
Text. Kategorien sind aus dem Material abgeleitet, nicht erfunden: sechs
Buendel, die sich beim Lesen tatsaechlich bildeten (sicherheit-datenumgang,
oberflaeche-nutzertext, agentenfuehrung, qualitaetssicherung-testen,
arbeitsweise-dokumentation, kommunikationsstil) -- grob genug, dass ein neuer
Nutzer sinnvoll waehlen kann ("ich will die Testdisziplin, nicht den
Kommunikationsstil"), fein genug, dass keine Kategorie zur Restekiste wird.

TEIL 3 -- DIE KONFLIKTFRAGE (Auftragspunkt 4), durch BAUFORM statt Disziplin:
dieses Skript schreibt jede importierte Regel mit
    norm_rang = NULL, norm_entscheidung = 'keine_norm'
in knowledge_nodes -- und mit NICHTS ANDEREM. norm_rang bleibt bei JEDEM
Import ungesetzt, ganz gleich was ein Paket behauptet (das Paketformat traegt
gar kein Rang-Feld, damit es nichts zu ignorieren gibt). Diese beiden Felder
sind nicht von diesem Skript erfunden, sondern ZWEI BEREITS BESTEHENDE
Mechanismen des Hauses, hier nur zusammengefuehrt:
  a) rangfolge.py::norm_score(None) == 0.0 -- ein Knoten ohne Rang bekommt im
     Abrufranking keinen Bonus, exakt wie ein gewoehnlicher Fakt. Eine
     importierte Regel WIRKT NICHT STAERKER als jede andere Notiz.
  b) schema.sql-Trigger knowledge_nodes_normrang_herkunft_bi/_bu (Zeile ~930):
     norm_rang IN (1,2) fuer eine Hausnorm (source nennt kein Gesetz/DIN/ISO/
     WCAG/Urteil) wird abgewiesen, wenn norm_entschieden_von eine Maschine
     nennt. Die Quelle eines importierten Pakets ('fremdregelpaket:...')
     matcht keins der Fremdnorm-Muster -- ein Import bleibt also eine
     Hausnorm-KANDIDATIN der Zielinstanz, fuer die die bestehende Schranke
     unveraendert gilt: Rang 1/2 nur mit einem nachweislich menschlichen
     Entscheider. Diese Datei fuegt der Schranke nichts hinzu und nichts
     Neues -- sie stellt nur sicher, dass ein Import sie GAR NICHT ERST
     umgeht (kein Rang-Feld im Paket, keine Sonderbehandlung beim Schreiben).
  Damit kann eine importierte Regel eine lokale nie BRECHEN, hoechstens
  EINSCHRAENKEN -- wie die Vertrauens-Obergrenze in der Foederation (falls in
  dieser Instanz vorhanden; siehe TEIL 5): sie kommt nie hoeher herein als
  'keine Wirkung', und alles darueber ist ein Willensakt eines Menschen HIER.

TEIL 4 -- Kein Rueckbau noetig: idempotent (INSERT OR IGNORE ueber die
Primaerschluessel-id), restlos entfernbar ueber
project_id='fremdregel-import' (Muster aus nasa_llis_import.py, hier
uebernommen statt neu erfunden -- Ladder-Rung 2).

TEIL 5 -- WANN WIRD GEFRAGT ("beim ERSTEN Auftreten", Auftragspunkt 5).
Befund, keine Loesung: erstverwendung.py beantwortet GENAU diese Frage fuer
EINEN Knoten (--vorschlag <id>) oder den ganzen offenen Bestand (--bericht),
aber NUR auf Zuruf -- kein Aufrufer im ganzen Baum (grep bestaetigt: die
Datei nennt sich nur selbst). Der naheliegende automatische Ort waere
haken/knowledge_recall_hook.py::query(), das bei JEDEM Prompt laeuft und
Treffer zurueckgibt -- genau der Moment, in dem eine importierte Regel dem
Agenten zum ERSTEN MAL im laufenden Betrieb vorgelegt wird. Der Hook ruft
erstverwendung.analysiere() heute nicht auf. Das ist keine Kleinigkeit, die
diese Datei nebenbei mitfixt: der Hook laeuft im UserPromptSubmit-Pfad mit
eigenem Perf-Budget (Kommentarzeilen dort sprechen von Radar-Auswahl,
Ensemble-Pflicht, Vertrauens-Score), ein zusaetzlicher DB-Write pro Prompt
waere eine eigene Abwaegung wert. Befund fuer den Bericht: DER ORT EXISTIERT
IM PRINZIP, IST ABER NICHT VERDRAHTET -- das ist die ehrliche Antwort auf
Auftragspunkt 5, kein Nachbau in dieser Datei.

Aufruf:
    python3 regelpaket.py --export --instanz <name> --ziel PFAD.json
    python3 regelpaket.py --import PFAD.json --db PFAD [--write]
    python3 regelpaket.py --selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Die Wurzel wird an schema.sql erkannt, nicht an einer Anzahl von Ebenen --
# dieselbe Bauform wie in tests/ und melder/. Beim Uebertragen aus einem
# Arbeitsbaum, in dem diese Datei noch im Wurzelverzeichnis lag, war HERE
# gleich der Wurzel; unter kern/ ist es das nicht mehr.
WURZEL = HERE
while not (WURZEL / "schema.sql").exists() and WURZEL != WURZEL.parent:
    WURZEL = WURZEL.parent
CET = timezone(timedelta(hours=1))
FORMAT_KENNUNG = "brainlehr-regelpaket-1"
PARENT_PATH = "/fremdregeln"
PROJECT_ID = "fremdregel-import"

DEFAULT_GLOBAL = Path.home() / ".claude" / "CLAUDE.md"
# hub/ liegt NICHT im brainlehr-Repo -- es ist der Begod2026-Verbund des
# Betreibers (mehrere Apps + gemeinsamer Speicher), ein Geschwisterordner.
# Fester Pfad hier nur als Vorgabewert fuer diese Instanz; --hub-pfad
# ueberschreibt ihn.
DEFAULT_HUB = Path("/Volumes/daten/Begod2026/hub/CLAUDE.md")


def now_iso() -> str:
    return datetime.now(CET).strftime("%Y-%m-%dT%H:%M:%S+01:00")


# ---------------------------------------------------------------------------
# TEIL 1+2: die kuratierte Trennung. quelle+index waehlt den Abschnitt aus der
# per abschnittsliste() gelesenen Reihenfolge (## Ueberschriften, 1-basiert) --
# ueber den Index statt den Titel woertlich abzutippen, weil Titel Sonder-
# zeichen (—, „ ") tragen, bei denen ein Tippfehler den Abschnitt lautlos
# verfehlen wuerde; der Index bricht dagegen LAUT (siehe exportieren()), wenn
# die Quelldatei sich seit der Klassifikation strukturell geaendert hat.
REGELN = [
    # -- global (~/.claude/CLAUDE.md), 18 Abschnitte gesamt --
    ("global", 1, "sicherheit-datenumgang", True),       # ALLES IST BETA...
    ("global", 2, "arbeitsweise-dokumentation", True),   # Datumsangaben
    ("global", 3, "kommunikationsstil", False),          # Caveman mode: always on
    # 4 BSI-Compliance -- ausgelassen: Mechanismus haengt an hub/-Pfaden
    ("global", 5, "oberflaeche-nutzertext", True),        # WCAG 2.2 AA
    ("global", 6, "agentenfuehrung", True),                # Auftraege sind Schnappschuesse
    ("global", 7, "agentenfuehrung", True),                # Wie ein Agentenauftrag geschrieben wird
    ("global", 8, "agentenfuehrung", True),                # Abwesenheitsmodus
    ("global", 9, "oberflaeche-nutzertext", True),         # Keine Entwicklerinformation in der UI
    # 10 Wissen festhalten & abrufen -- ausgelassen: hub/scripts/hub/shared-knowledge-Pfade
    # 11 Testumgebung: handeln statt vorlegen -- ausgelassen: woertliche Freigabe an EINE Person
    ("global", 12, "agentenfuehrung", True),               # Kurze Zustimmung ist eine Entscheidung
    ("global", 13, "agentenfuehrung", True),               # Zweimal ist die Grenze
    ("global", 14, "qualitaetssicherung-testen", True),    # Walkthrough-Doktrin
    ("global", 15, "arbeitsweise-dokumentation", True),    # Committen ohne Aufforderung
    ("global", 16, "arbeitsweise-dokumentation", True),    # Nachsehen, bevor gefragt
    ("global", 17, "qualitaetssicherung-testen", True),    # "Es funktioniert" braucht Beleg
    ("global", 18, "arbeitsweise-dokumentation", True),    # Plan vor Umsetzung

    # -- hub (hub/CLAUDE.md), 17 Abschnitte gesamt --
    ("hub", 1, "agentenfuehrung", False),                   # Identitaet
    # 2 Fokus -- ausgelassen: apps/fahrtenbuch_legacy (Betreiber-App)
    ("hub", 3, "arbeitsweise-dokumentation", True),         # Wissen (Knowledge-MCP)
    # 4 Hard Stops -- ausgelassen: /Volumes/daten-Pfad als Kernaussage
    # 5 Konsile & ADRs -- ausgelassen: begod/-Pfade
    # 6 Arbeitsweise -- ausgelassen: begod/scripts/chronist.py
    # 7 Routing (Subagents) -- ausgelassen: eigener Agentenkatalog + hub/-Pfade
    # 8 Fluss-Karten (Metroviz) -- ausgelassen: hub/tools/flowmaps
    ("hub", 9, "agentenfuehrung", True),                    # Token-Workflow
    ("hub", 10, "qualitaetssicherung-testen", True),        # Geraete per Text bedienen
    ("hub", 11, "qualitaetssicherung-testen", True),        # Monolith-Bremse
    ("hub", 12, "arbeitsweise-dokumentation", True),        # STAND.md
    ("hub", 13, "kommunikationsstil", True),                # Caveman (Token-Kompression)
    # 14 Modell-Kaskade v3 -- ausgelassen: Euro-Kostenmessung fuer 15 konkrete Repos
    ("hub", 15, "agentenfuehrung", True),                   # Modellverhalten Opus 5 / Sonnet 5
    ("hub", 16, "agentenfuehrung", True),                   # Den Betreiber korrigieren
    # 17 Eskalierte Lehren -- ausgelassen: L-IDs nur in dieser DB aufloesbar
]

KATEGORIEN = {
    "sicherheit-datenumgang": "Umgang mit Daten, Testumgebung, Freigaben",
    "oberflaeche-nutzertext": "Was der Nutzer sieht: Barrierefreiheit, Text, Datenschutz in der UI",
    "agentenfuehrung": "Wie Agenten beauftragt, gefuehrt und korrigiert werden",
    "qualitaetssicherung-testen": "Testdisziplin, Belegpflicht, Geraetefuehrung",
    "arbeitsweise-dokumentation": "Format, Commit-Disziplin, Recherche, Uebergabe",
    "kommunikationsstil": "Ton und Kuerze der Antworten",
}


def abschnittsliste(pfad: Path) -> list[tuple[str, str]]:
    """[(Titel, Body), ...] in Dateireihenfolge, 1-basiert ueber den Index."""
    text = pfad.read_text(encoding="utf-8")
    teile = re.split(r"(?m)^## ", text)
    raus = []
    for teil in teile[1:]:
        kopf, *rest = teil.split("\n", 1)
        raus.append((kopf.strip(), (rest[0] if rest else "").strip()))
    return raus


def slug(titel: str) -> str:
    s = titel.lower()
    s = re.sub(r"[^a-z0-9äöüß]+", "-", s).strip("-")
    return s[:60] or "abschnitt"


def exportieren(global_pfad: Path, hub_pfad: Path, instanz: str) -> dict:
    quellen = {"global": abschnittsliste(global_pfad), "hub": abschnittsliste(hub_pfad)}
    regeln = []
    for quelle, index, kategorie, begruendung in REGELN:
        abschnitte = quellen[quelle]
        if not (1 <= index <= len(abschnitte)):
            raise RuntimeError(
                f"Klassifikation veraltet: {quelle}#{index} existiert nicht mehr "
                f"({quelle} hat nur {len(abschnitte)} Abschnitte) -- REGELN pruefen.")
        titel, body = abschnitte[index - 1]
        regeln.append({
            "id": f"{quelle}-{index:02d}-{slug(titel)}",
            "herkunft": quelle,
            "kategorie": kategorie,
            "titel": titel,
            "text": body,
            "begruendung": begruendung,
        })
    return {
        "format": FORMAT_KENNUNG,
        "erzeugt_am": now_iso(),
        "quell_instanz": instanz,
        "kategorien": KATEGORIEN,
        "anzahl": len(regeln),
        "regeln": regeln,
    }


# ---------------------------------------------------------------------------
# TEIL 3: Import. norm_rang/gilt_ab werden NICHT gesetzt -- keine Spalte im
# INSERT dafuer, kein Weg, sie ueber das Paket zu fuellen.
INSERT_SQL = """
INSERT OR IGNORE INTO knowledge_nodes
    (id, path, parent_path, project_id, title, summary, content, level, tags,
     source, confidence, created_at, updated_at, anlass, actor,
     norm_entscheidung, norm_entschieden_von, norm_entschieden_grund)
VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'keine_norm','skript:regelpaket.py',
        'Import aus Fremdpaket -- Rang muss ein Mensch der Zielinstanz vergeben')
"""
SUMMARY_MAXLEN = 400


def paket_lesen(pfad: Path) -> dict:
    paket = json.loads(pfad.read_text(encoding="utf-8"))
    if paket.get("format") != FORMAT_KENNUNG:
        raise RuntimeError(f"unbekanntes Paketformat: {paket.get('format')!r}")
    return paket


def zeilen_aus_paket(paket: dict, ts: str) -> list[tuple]:
    zeilen = []
    for r in paket["regeln"]:
        summary = r["text"] if len(r["text"]) <= SUMMARY_MAXLEN else r["text"][:SUMMARY_MAXLEN].rstrip() + " [...]"
        if not summary:
            summary = r["titel"]
        tags = [
            "fremdregel-import",
            f"kategorie:{r['kategorie']}",
            f"herkunft:{r['herkunft']}",
            f"quelle:{paket.get('quell_instanz') or 'unbekannt'}",
            f"begruendet:{'ja' if r.get('begruendung') else 'nein'}",
        ]
        source = f"fremdregelpaket:{paket.get('quell_instanz') or 'unbekannt'}/{r['herkunft']}/{r['id']}"
        zeilen.append((
            f"fremdregel-{r['id']}",              # id
            f"{PARENT_PATH}/{r['id']}",            # path
            PARENT_PATH,                            # parent_path
            PROJECT_ID,                             # project_id
            r["titel"],                             # title
            summary,                                # summary
            r["text"],                              # content
            1,                                       # level
            json.dumps(tags, ensure_ascii=False),   # tags
            source,                                  # source
            0.5,                                     # confidence
            ts, ts,                                  # created_at, updated_at
            "skript",                                # anlass
            "regelpaket.py",                         # actor
        ))
    return zeilen


PARENT_ROW_TEMPLATE = (
    "fremdregeln-root", PARENT_PATH, None, PROJECT_ID,
    "Fremdregeln (Import)", "Wurzelknoten fuer importierte Regelpakete fremder Instanzen.",
    None, 0, json.dumps(["fremdregel-import"], ensure_ascii=False),
    "regelpaket.py", 0.5, None, None, "skript", "regelpaket.py",
)


def _ensure_parent(conn: sqlite3.Connection, ts: str) -> None:
    zeile = list(PARENT_ROW_TEMPLATE)
    zeile[11] = zeile[12] = ts
    conn.execute(INSERT_SQL, zeile)


def importieren(db_pfad: Path, paket: dict, schreiben: bool) -> tuple[int, int]:
    ts = now_iso()
    conn = sqlite3.connect(str(db_pfad))
    conn.execute("PRAGMA journal_mode=WAL")
    if schreiben:
        _ensure_parent(conn, ts)
    zeilen = zeilen_aus_paket(paket, ts)
    eingefuegt = uebersprungen = 0
    for z in zeilen:
        if schreiben:
            cur = conn.execute(INSERT_SQL, z)
            if cur.rowcount:
                eingefuegt += 1
            else:
                uebersprungen += 1
        else:
            vorhanden = conn.execute("SELECT 1 FROM knowledge_nodes WHERE id=?", (z[0],)).fetchone()
            uebersprungen += bool(vorhanden)
            eingefuegt += not vorhanden
    if schreiben:
        conn.commit()
    conn.close()
    return eingefuegt, uebersprungen


def entfernen(db_pfad: Path) -> int:
    conn = sqlite3.connect(str(db_pfad))
    cur = conn.execute("DELETE FROM knowledge_nodes WHERE project_id=?", (PROJECT_ID,))
    conn.commit()
    n = cur.rowcount
    conn.close()
    return n


# ---------------------------------------------------------------------------
# Selbsttest: Ausfuhr gegen die echten Dateien, Einfuhr gegen ein frisches
# Schema, Negativfall (Maschine darf keinen Rang vergeben), Gegenprobe
# (Mensch darf), Betreiberspezifisches landet nicht im Paket, Ranking-Wirkung.
def _selftest() -> None:
    import tempfile

    # 1) Ausfuhr gegen die echten Regeldateien dieser Instanz.
    paket = exportieren(DEFAULT_GLOBAL, DEFAULT_HUB, instanz="selftest-instanz")
    assert paket["anzahl"] == len(REGELN) == 24, paket["anzahl"]
    titel_menge = {r["titel"] for r in paket["regeln"]}

    # Negativfall Auftragspunkt 1: ein betreiberspezifischer Abschnitt darf
    # NICHT im Paket landen -- geprueft an drei Titeln, die garantiert
    # betreiberspezifische Pfade/Zitate tragen.
    for verboten in ("BSI-Compliance", "Fokus", "Hard Stops"):
        assert not any(verboten in t for t in titel_menge), f"betreiberspezifisch durchgerutscht: {verboten}"
    # und die Gegenprobe: ein bekannt uebertragbarer Titel MUSS drin sein.
    assert any("WCAG" in t for t in titel_menge)

    begruendet = sum(1 for r in paket["regeln"] if r["begruendung"])
    assert begruendet == 22, begruendet  # 24 uebertragbare, 2 ohne Begruendung

    # 2) Einfuhr gegen ein frisches Schema.
    schema_src = (WURZEL / "schema.sql").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "ziel.db"
        conn = sqlite3.connect(str(db))
        conn.executescript(schema_src)
        conn.close()

        # Trockenlauf zaehlt richtig, schreibt nichts.
        ein, ueb = importieren(db, paket, schreiben=False)
        assert ein == 24 and ueb == 0, (ein, ueb)
        conn = sqlite3.connect(str(db))
        assert conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0] == 0
        conn.close()

        # Echter Lauf.
        ein, ueb = importieren(db, paket, schreiben=True)
        assert ein == 24 and ueb == 0, (ein, ueb)

        # Idempotenz: zweiter Lauf importiert nichts neu.
        ein2, ueb2 = importieren(db, paket, schreiben=True)
        assert ein2 == 0 and ueb2 == 24, (ein2, ueb2)

        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        zeile = conn.execute(
            "SELECT id, norm_rang, norm_entscheidung, gilt_ab FROM knowledge_nodes "
            "WHERE id LIKE 'fremdregel-%' LIMIT 1"
        ).fetchone()
        assert zeile["norm_rang"] is None, "importierte Regel traegt einen Rang -- das darf nie passieren"
        assert zeile["norm_entscheidung"] == "keine_norm"

        # 3) NEGATIVFALL: eine importierte Regel wirkt nicht, solange kein
        # Mensch ihr einen Rang gibt.
        #  a) Wirkung im Ranking: norm_score(None) ist neutral, kein Bonus.
        sys.path.insert(0, str(HERE))
        import rangfolge  # noqa: E402
        assert rangfolge.norm_score(zeile["norm_rang"]) == 0.0

        #  b) Eine MASCHINE darf den Rang nicht nachtraeglich setzen -- der
        #  bestehende Trigger (schema.sql, Herkunftsschranke Normrang 1/2)
        #  weist das ab, weil die Quelle keine Fremdnorm ist.
        try:
            conn.execute(
                "UPDATE knowledge_nodes SET norm_rang=1, gilt_ab=?, "
                "norm_entscheidung='norm_unbefristet', "
                "norm_entschieden_von='claude-code/opus-5', "
                "norm_entschieden_grund='Selbstermaechtigung, darf nicht durchgehen' "
                "WHERE id=?", (now_iso(), zeile["id"]))
            conn.commit()
            raise AssertionError("Maschine konnte einer importierten Regel einen Rang geben -- Schranke wirkungslos")
        except sqlite3.IntegrityError as e:
            assert "menschlichen Entscheider" in str(e), e

        #  c) GEGENPROBE: ein MENSCH darf genau das -- das ist der Punkt, an
        #  dem eine importierte Regel zum ersten Mal wirken kann, und zwar
        #  nur, weil hier ausdruecklich jemand entschieden hat.
        conn.execute(
            "UPDATE knowledge_nodes SET norm_rang=1, gilt_ab=?, "
            "norm_entscheidung='norm_unbefristet', "
            "norm_entschieden_von='betreiber', "
            "norm_entschieden_grund='von Hand geprueft und uebernommen' "
            "WHERE id=?", (now_iso(), zeile["id"]))
        conn.commit()
        neu = conn.execute("SELECT norm_rang FROM knowledge_nodes WHERE id=?", (zeile["id"],)).fetchone()
        assert neu[0] == 1
        assert rangfolge.norm_score(neu[0]) == 1.0
        conn.close()

        # 4) Restlos entfernbar, anderer Bestand unangetastet.
        vorher = sqlite3.connect(str(db)).execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        entfernt = entfernen(db)
        assert entfernt == 25, entfernt  # 24 Regeln + 1 Wurzelknoten
        nachher = sqlite3.connect(str(db)).execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        assert nachher == vorher - 25, (vorher, nachher)

    print("SELFTEST OK: Ausfuhr (24 uebertragbar, 3 Betreiberspezifische ausgeschlossen, "
          "22/24 begruendet), Einfuhr idempotent, Rang bleibt leer, Ranking neutral, "
          "Maschine abgewiesen, Mensch darf, restlos entfernbar.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--global-pfad", type=Path, default=DEFAULT_GLOBAL)
    ap.add_argument("--hub-pfad", type=Path, default=DEFAULT_HUB)
    ap.add_argument("--instanz", default="unbekannt")
    ap.add_argument("--ziel", type=Path, default=Path("regelpaket.json"))
    ap.add_argument("--import-paket", dest="import_paket", type=Path)
    ap.add_argument("--db", type=Path, default=HERE / "brainlehr.db")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--entfernen", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        _selftest()
        return 0

    if a.export:
        paket = exportieren(a.global_pfad, a.hub_pfad, a.instanz)
        a.ziel.write_text(json.dumps(paket, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{paket['anzahl']} Regeln exportiert -> {a.ziel}")
        return 0

    if a.entfernen:
        n = entfernen(a.db)
        print(f"entfernt: {n} Knoten (project_id={PROJECT_ID})")
        return 0

    if a.import_paket:
        paket = paket_lesen(a.import_paket)
        ein, ueb = importieren(a.db, paket, schreiben=a.write)
        mode = "SCHREIB-LAUF" if a.write else "TROCKENLAUF"
        print(f"{mode}: {ein} anlegbar/angelegt, {ueb} uebersprungen (schon vorhanden). "
              "Rang bleibt bei jeder importierten Regel leer, bis ein Mensch dieser Instanz "
              "ihn vergibt.")
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
