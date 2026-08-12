#!/usr/bin/env python3
"""Ein Pruefkorpus, der nicht erfunden wird, sondern anfaellt.

ANLASS (2026-08-11, zwei Befunde desselben Tages): Der bisherige Pruefkorpus
wurde AUS den Eintraegen erzeugt, die er finden soll -- im Handel heisst das
data snooping bias, und es macht jede Abrufzahl daraus wertlos (Lopez de Prado
2017, Recherche im Pruefspruch #6). Der zweite Befund kam vom Messaufbau
selbst: drei Subagenten bekamen die Loesung durch den Abruf-Haken eingespielt,
bevor sie die Aufgabe lasen.

Beide Fehler haben dieselbe Wurzel: Aufgabentext und Zielangabe stammten aus
DERSELBEN Quelle. Dieses Modul trennt die Kanaele:

  Aufgabentext  eine ECHTE Nachricht aus recall_log.jsonl -- so gestellt, wie
                sie gestellt wurde, ohne Kenntnis eines Ziels
  Zielangabe    ueber code_kanten, also ueber den DATEIPFAD -- ein Kanal, der
                mit dem Wortlaut der Nachricht nichts zu tun hat

Ein Fall entsteht nur, wenn eine echte Nachricht einen spezifischen Pfad nennt
UND an diesem Pfad Wissen haengt. Niemand formuliert dafuer etwas.

WARUM SAMMLER UND NICHT KORPUS: Der erste Lauf am 2026-08-11 ergab aus 299
menschlichen Nachrichten genau VIER brauchbare Faelle. Das misst nichts. Die
ehrliche Antwort darauf ist nicht, die Anforderungen zu senken, bis genug
zusammenkommt -- dann waere man wieder beim erfundenen Korpus. Die ehrliche
Antwort ist, zu warten: jede kuenftige Nachricht, die eine Datei nennt, legt
einen Fall dazu, ohne dass jemand etwas tut.

DREI FILTER, jeder gegen einen beobachteten Fehlerweg:
  1. Systemmeldungen raus (<task-notification> und Verwandte). Ohne diesen
     Filter waren 38 von 38 Kandidaten zur Haelfte Maschinentext.
  2. Nur SPEZIFISCHE Pfade (mit Verzeichnisteil). 'settings.json' ist keine
     Adresse, sondern ein Wort.
  3. Nur eindeutige Kanten und hoechstens drei Ziele. Ein Fall mit zwanzig
     richtigen Antworten prueft nichts.

DRITTER KANAL 'lese' (2026-08-12): 'pfad' und 'kennung' lesen das Ziel AUS
der Nachricht -- das Ziel steht im Wortlaut. 'lese' braucht das nicht: ein
GEZIELTES access_log-read auf einen Knotenpfad, das zeitlich auf eine echte
Nachricht folgt, belegt, dass jemand genau diesen Knoten wollte. Die Nachricht
liefert weiterhin recall_log.jsonl -- derselbe Weg wie bei 'kennung', keine
zweite Zuordnung ueber Sitzungstranskripte. Die Fenster-/Sitzungslogik
(Praefixvergleich, Cutoff per Zeitstempel) stammt aus kern/wirkung.py, das
dieselbe Frage schon fuer den Recall-Haken beantwortet -- hier nur auf ein
einzelnes Nachrichtenfenster statt auf die ganze Sitzung verengt (sonst
wuerde ein spaeteres Lesen mehreren fruehen Nachrichten zugleich zugeschrieben).

Zwei zusaetzliche Ausschluesse, beide an der SPALTENBEDEUTUNG festgemacht,
nicht an einer neuen Liste von Namen:
  - client != 'claude-code' bleibt aussen vor. 'skript' traegt jeder
    Selbstlauf (chatgpt/codex/terra/sol/enigma-Laeufer, siehe Modulkopf-
    Auftrag); ein leerer client traegt Migrationen und Alt-Skripte ohne
    Ausweis (ausweis.py nennt normbestand.py, hebb_kanten.py). Beide liegen
    ohnehin nie in einer echten Betreiber-Sitzung mit recall_log-Eintrag --
    der Filter macht das nur ausdruecklich.
  - Kontamination: wurde derselbe Knoten von DERSELBEN Einspielung schon
    eingespielt (recall_log-Feld 'nodes'/'node_ids'), ist das Lesen kein
    unabhaengiger Beleg, sondern ein Griff nach dem, was ohnehin im Kontext
    stand (siehe messungen/kontamination.py fuer dieselbe Frage bei
    Subagenten). Ein solcher Fall wird VERWORFEN, nicht markiert -- markiert
    saehe er in jeder Zaehlung noch wie ein Fall aus.

Aufruf:
    python3 echtkorpus.py --sammeln --out runs/echtkorpus.json
    python3 echtkorpus.py --selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "haken"))
sys.path.insert(0, str(WURZEL / "kern"))

import codekanten as ck  # noqa: E402
import ort  # noqa: E402
import speicher  # noqa: E402
import teilung_s12  # noqa: E402
import wirkung  # noqa: E402 -- Session-Fenster-Logik (_parse_ts/_fmt_ts) wiederverwendet, nicht zweimal gebaut

# Das Protokoll liegt NEBEN der Datenbank, nicht neben dem Quelltext.
# ort.RECALL_LOG leitet den Pfad aus der Wurzel des Arbeitsbaums ab -- und ein
# Arbeitsbaum traegt keine Daten (heute schon einmal erlebt, L-0f4036: eine
# leere Datenbank statt einer fehlenden Datei). Deshalb wird der Ort aus dem
# tatsaechlich benutzten Datenbankpfad abgeleitet; nur wenn dort nichts liegt,
# bleibt es bei der Ableitung aus dem Quelltextort.
_NEBEN_DER_DB = Path(ort.DB).parent / "recall_log.jsonl"
RECALL_LOG = _NEBEN_DER_DB if _NEBEN_DER_DB.exists() else ort.RECALL_LOG
MASCHINENTEXT = re.compile(
    r"<task-notification>|<system-reminder>|<knowledge-recall>|tool-use-id|"
    r"<antwort-recall>|<persisted-output>")
# Fertigkeits-/Werkzeug-Vorspann ist kein Betreibertext (gemessen 2026-08-11:
# 4 von 92 Faellen waren genau das). Erkennbar am Anfang der Nachricht.
VORSPANN = re.compile(r"^\s*Base directory for this skill:")
MIN_LAENGE = 25
MAX_ZIELE = 3

# Satzart als eigenes Feld (nicht als Filter, siehe Modulkopf-Auftrag): eine
# Auskunftsfrage und ein Arbeitsauftrag loesen verschiedenes Verhalten aus
# (L-4be9bf), beides in einen Topf zu werfen misst zwei Dinge gleichzeitig.
_IMPERATIV = re.compile(
    r"\b(lies|lese|arbeite|übernimm|übernehme|mach|erledige|bearbeite|"
    r"fahre fort|setze fort|starte|beginne|erstelle|implementiere|behebe|"
    r"fixe|prüfe|ändere)\b", re.IGNORECASE)
_UEBERSCHRIFT = re.compile(r"^[A-ZÄÖÜ][A-ZÄÖÜa-zäöüß ]{2,30}:?\s*$")
AUFTRAG_LAENGE = 300


def satzart(text: str) -> str:
    """Beobachtbare Merkmale, nicht Laenge allein: Imperativ am Anfang,
    oder mehrzeilige Struktur mit Ueberschriften, oder langer Fliesstext
    mit mehreren Zeilen.

    Maschinentext-Check ZUERST (gemessen 2026-08-12, Aufgabe 46): eine
    Task-Notification ist oft selbst mehrzeilig mit ueberschriftartiger
    erster Zeile und traf darum 'auftrag', BEVOR der _ist_echte_frage-Filter
    sie ausscheiden konnte -- in echtkorpus.py folgenlos (satzart() wird dort
    erst nach dem Filter aufgerufen), aber trichter_fragen.py bestimmt die
    Satzart bewusst VOR dem Filter (das ist der Trichter-Zweck) und uebernahm
    die Fehlklassifikation direkt in die Rohzahl. Entscheidung: eigene Klasse
    statt Reihenfolge-Tausch, weil der Trichter den vollen Rohbestand als
    Nenner braucht -- ein vorgezogener Filter wuerde die erste Trichterstufe
    entwerten."""
    if MASCHINENTEXT.search(text):
        return "maschine"
    zeilen = text.split("\n")
    imperativ_am_anfang = bool(_IMPERATIV.search(text[:120]))
    mehrzeilig_mit_ueberschrift = len(zeilen) >= 3 and any(
        _UEBERSCHRIFT.match(z.strip()) for z in zeilen)
    langer_fliesstext = len(text) > AUFTRAG_LAENGE and len(zeilen) > 1
    if imperativ_am_anfang or mehrzeilig_mit_ueberschrift or langer_fliesstext:
        return "auftrag"
    return "frage"

# Zweiter Zielkanal: eine Kennung STEHT im Text -- keine Aufloesung noetig,
# nur eine Existenzpruefung gegen die Datenbank. Das macht diese Faelle
# LEICHT (Antwort im Prompt) und darum eine eigene Klasse (siehe Modulkopf).
_LEHRE = re.compile(r"\bL-[0-9a-f]{6}\b")
# Knotenpfad: beginnt mit '/', mindestens zwei Segmente -- ein blosses '/etc'
# waere Rauschen. Die DB-Pruefung filtert den Rest (dieselbe Wirklichkeit-
# statt-Vertrauen-Regel wie in codekanten.aufloesen): ein Kandidat wie
# '/Volumes/daten/...' loest sich hier einfach nicht auf.
_KNOTENPFAD = re.compile(r"(?<!\S)/[a-zA-Z][\w\-]*(?:/[\w\-]+)+")
SITZUNGEN = Path.home() / ".claude" / "projects"


def _ist_echte_frage(text: str) -> bool:
    """Gemeinsamer Filter beider Quellen. '<' am Anfang und Maschinentext
    sind keine Fragen -- eine Frage ist der Gegenstand der Messung."""
    return (len(text) >= MIN_LAENGE and not text.startswith("<")
            and not MASCHINENTEXT.search(text)
            and not VORSPANN.match(text))


def echte_nachrichten(pfad: Path = RECALL_LOG) -> list[str]:
    """Quelle 1: recall_log.jsonl -- nur was den Haltepunkt erreicht hat."""
    if not pfad.exists():
        return []
    raus = []
    for zeile in pfad.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            satz = json.loads(zeile)
        except json.JSONDecodeError:
            continue
        text = (satz.get("prompt") or "").strip()
        if _ist_echte_frage(text):
            raus.append(text)
    return raus


def sitzungs_nachrichten(wurzel: Path = SITZUNGEN) -> list[str]:
    """Quelle 2: Sitzungstranskripte -- auch die Nachrichten, die den
    Haltepunkt nie erreicht haben (gemessen: 18,3 % tun das nicht)."""
    if not wurzel.exists():
        return []
    raus = []
    for pfad in wurzel.glob("*/[0-9a-f-]*.jsonl"):
        try:
            zeilen = pfad.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for zeile in zeilen:
            try:
                satz = json.loads(zeile)
            except json.JSONDecodeError:
                continue
            if satz.get("type") != "user":
                continue
            inhalt = (satz.get("message") or {}).get("content")
            if isinstance(inhalt, str):
                text = inhalt.strip()
            elif isinstance(inhalt, list):
                text = "\n".join(
                    t.get("text", "") for t in inhalt
                    if isinstance(t, dict) and t.get("type") == "text").strip()
            else:
                continue
            if _ist_echte_frage(text):
                raus.append(text)
    return raus


def _ohne_doppelte(nachrichten: list[str]) -> list[str]:
    return list(dict.fromkeys(nachrichten))


def faelle_bilden(nachrichten: list[str], conn) -> list[dict]:
    """Klasse 'pfad': die Zielangabe kommt ueber code_kanten, nicht aus dem
    Text -- der schwere Fall, um den es diesem Korpus eigentlich geht."""
    faelle = []
    for text in nachrichten:
        pfade = sorted(k for k in ck.kandidaten(text) if "/" in k)
        ziele = set()
        for k in pfade:
            for w in ck.wissen_zu(k, conn):
                if not w["mehrdeutig"]:
                    ziele.add((w["quelle_art"], w["quelle_id"]))
        if ziele and len(ziele) <= MAX_ZIELE:
            faelle.append({"prompt": text, "klasse": "pfad", "satzart": satzart(text),
                            "pfade": pfade,
                            "ziele": [{"art": a, "id": i} for a, i in sorted(ziele)]})
    return faelle


def kennungen(text: str) -> set[str]:
    return set(_LEHRE.findall(text or "")) | set(_KNOTENPFAD.findall(text or ""))


def kennung_pruefen(kandidat: str, conn) -> dict | None:
    """Existenzpruefung -- eine erfundene Kennung ist kein Fall."""
    if _LEHRE.fullmatch(kandidat):
        zeile = conn.execute(
            "SELECT id FROM lessons_learned WHERE id = ?", (kandidat,)).fetchone()
        return {"art": "lehre", "id": zeile["id"]} if zeile else None
    zeile = conn.execute(
        "SELECT path FROM knowledge_nodes WHERE path = ?", (kandidat,)).fetchone()
    return {"art": "knoten", "id": zeile["path"]} if zeile else None


def kennung_faelle_bilden(nachrichten: list[str], conn) -> list[dict]:
    """Klasse 'kennung': die Zielangabe steht wortwoertlich im Text -- der
    LEICHTE Fall, deshalb eigene Klasse statt gemeinsamer Topf mit 'pfad'."""
    faelle = []
    for text in nachrichten:
        ziele = set()
        for k in sorted(kennungen(text)):
            treffer = kennung_pruefen(k, conn)
            if treffer:
                ziele.add((treffer["art"], treffer["id"]))
        if ziele:
            faelle.append({"prompt": text, "klasse": "kennung", "satzart": satzart(text),
                            "ziele": [{"art": a, "id": i} for a, i in sorted(ziele)]})
    return faelle


# Dritter Kanal, siehe Modulkopf-Auftrag: 8 Hex-Ziffern ist die echte Form
# einer Claude-Code-Sitzungskennung (session_id[:8], siehe knowledge_recall_
# hook.py). 'probe'/'betriebs'/'probe2'/... sind Testzeilen aus der eigenen
# Arbeit an diesem Sammler und an wirkung.py -- keine Betreiber-Sitzung.
_SESSION_HEX = re.compile(r"^[0-9a-f]{8}$")


def _einspielungen(pfad: Path = RECALL_LOG) -> list[dict]:
    """Jede recall_log-Zeile mit echter Nachricht (siehe _ist_echte_frage)
    und echter Sitzungskennung, sortiert je Sitzung nach Zeit -- die
    Reihenfolge, die lese_faelle_bilden fuer die Fensterbildung braucht."""
    if not pfad.exists():
        return []
    raus = []
    for zeile in pfad.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            satz = json.loads(zeile)
        except json.JSONDecodeError:
            continue
        session = satz.get("session")
        ts = wirkung._parse_ts(satz.get("ts"))
        text = (satz.get("prompt") or "").strip()
        if not session or not ts or not _SESSION_HEX.match(session):
            continue
        if not _ist_echte_frage(text):
            continue
        raus.append({
            "session": session, "ts": ts, "prompt": text,
            "eingespielt": set(satz.get("nodes") or []) | set(satz.get("node_ids") or []),
        })
    raus.sort(key=lambda e: (e["session"], e["ts"]))
    return raus


def lese_faelle_bilden(conn, pfad: Path = RECALL_LOG) -> tuple[list[dict], int]:
    """Klasse 'lese': das Ziel kommt aus einem GEZIELTEN access_log-read, der
    zeitlich auf genau diese Nachricht folgt (und vor der naechsten Nachricht
    derselben Sitzung liegt, falls es eine gibt). Gibt (Faelle, Anzahl
    verworfener Kontaminationsfaelle) zurueck -- die Zahl gehoert in den
    Bericht (Auftrag Punkt 3), nicht ins Dunkel."""
    nach_sitzung: dict[str, list[dict]] = {}
    for e in _einspielungen(pfad):
        nach_sitzung.setdefault(e["session"], []).append(e)

    faelle: list[dict] = []
    kontaminiert = 0
    for session, eintraege in nach_sitzung.items():
        for i, e in enumerate(eintraege):
            fenster_ende = eintraege[i + 1]["ts"] if i + 1 < len(eintraege) else None
            sql = ("SELECT DISTINCT node_path FROM access_log WHERE action = 'read' "
                   "AND status = 'completed' AND client = 'claude-code' "
                   "AND node_path IS NOT NULL AND session LIKE ? AND timestamp > ?")
            params = [f"{session}%", wirkung._fmt_ts(e["ts"])]
            if fenster_ende is not None:
                sql += " AND timestamp <= ?"
                params.append(wirkung._fmt_ts(fenster_ende))
            gelesen = {r[0] for r in conn.execute(sql, params)}

            unabhaengig = sorted(gelesen - e["eingespielt"])
            kontaminiert += len(gelesen & e["eingespielt"])
            if unabhaengig and len(unabhaengig) <= MAX_ZIELE:
                faelle.append({
                    "prompt": e["prompt"], "klasse": "lese", "satzart": satzart(e["prompt"]),
                    "ziele": [{"art": "knoten", "id": p} for p in unabhaengig],
                })
    return faelle, kontaminiert


def s12_bericht(faelle: list[dict], conn) -> dict:
    """Der Nenner fuer den S12-Versuch (Auftrag: 'Sammellauf mit Nenner'):
    Knotenziele, verschiedene Knoten, und Faelle je Haelfte der Teilung aus
    kern/teilung_s12.py. Reine Auszaehlung -- die Teilung selbst ist dort
    bereits deterministisch, hier wird nicht neu gezogen.

    ALLE drei Kanaele tragen den Knotenpfad als 'id' (siehe codekanten.erheben:
    'SELECT path AS id ...' und kennung_pruefen: row['path']) -- die Faelle
    dieses Sammlers kennen keine DB-id. teilung_s12.py teilt aber ausdruecklich
    ueber die id, NICHT ueber den Pfad (dort begruendet: ein umbenannter Knoten
    wanderte sonst lautlos die Haelfte). Ohne Aufloesung path->id wuerde hier
    also eine ANDERE, instabile Teilung gemessen als die kanonische -- darum
    die Aufloesung ueber knowledge_nodes vor jedem haelfte()-Aufruf."""
    knotenziele = [z for f in faelle for z in f["ziele"] if z["art"] == "knoten"]
    pfade = {z["id"] for z in knotenziele}
    id_je_pfad = teilung_s12.id_je_pfad(conn, pfade)

    je_haelfte = {teilung_s12.BEHANDELT: 0, teilung_s12.UNBEHANDELT: 0, "gemischt": 0}
    for f in faelle:
        haelften = set()
        for z in f["ziele"]:
            if z["art"] == "knoten":
                db_id = id_je_pfad.get(z["id"])
                if db_id is None:
                    continue  # Pfad ohne (mehr) passenden Knoten -- keine Haelfte zuweisbar
                haelften.add(teilung_s12.haelfte("knoten", db_id))
            else:
                haelften.add(teilung_s12.haelfte("lehre", z["id"]))
        if haelften:
            je_haelfte["gemischt" if len(haelften) > 1 else haelften.pop()] += 1
    return {
        "knotenziele": len(knotenziele),
        "verschiedene_knoten": len(pfade),
        "faelle_je_haelfte": je_haelfte,
    }


def _selftest() -> None:
    import tempfile

    log = Path(tempfile.mkdtemp()) / "recall.jsonl"
    log.write_text("\n".join(json.dumps(z) for z in [
        {"prompt": "Sieh dir bitte lib/trip_service.dart an, da stimmt etwas nicht."},
        {"prompt": "<task-notification>lib/trip_service.dart ist fertig</task-notification>"},
        {"prompt": "kurz"},
        {"prompt": "Was ist mit settings.json?"},
        {"prompt": "Base directory for this skill: /Volumes/daten/foo\n\nTu etwas Sinnvolles hier."},
    ]) + "\n")

    n = echte_nachrichten(log)
    assert len(n) == 2, n                      # Maschinentext, Vorspann und zu Kurzes raus
    assert all("task-notification" not in x for x in n)
    assert all("Base directory for this skill" not in x for x in n)

    # Vorspann ergibt auch bei erfundener Kennung/spezifischem Pfad keinen Fall.
    vorspann_text = "Base directory for this skill: /Volumes/x\n\nSiehe L-0f4036 dazu."
    assert not _ist_echte_frage(vorspann_text)

    class FakeConn:
        def __init__(self, treffer): self.treffer = treffer
        def execute(self, *a, **k): raise AssertionError("nicht benutzt")

    # Kanal-Trennung: die Ziele kommen NICHT aus dem Text, sondern aus der
    # Kantenabfrage -- hier gestellt.
    import unittest.mock as mock
    with mock.patch.object(ck, "wissen_zu",
                            lambda pfad, conn: [{"quelle_art": "lehre", "quelle_id": "L-1",
                                                  "mehrdeutig": 0}] if "trip_service" in pfad else []):
        f = faelle_bilden(n, None)
    assert len(f) == 1, f                      # nur die Nachricht mit spezifischem Pfad
    assert f[0]["ziele"] == [{"art": "lehre", "id": "L-1"}]
    assert "settings.json" not in json.dumps(f), "unspezifischer Name wurde als Adresse genommen"

    # Gegenprobe: zu viele Ziele -> kein Fall. Ein Fall mit zwanzig richtigen
    # Antworten prueft nichts.
    with mock.patch.object(ck, "wissen_zu",
                            lambda pfad, conn: [{"quelle_art": "lehre", "quelle_id": f"L-{i}",
                                                  "mehrdeutig": 0} for i in range(MAX_ZIELE + 1)]):
        assert faelle_bilden(n, None) == []

    # Gegenprobe: mehrdeutige Kante zaehlt nicht.
    with mock.patch.object(ck, "wissen_zu",
                            lambda pfad, conn: [{"quelle_art": "lehre", "quelle_id": "L-1",
                                                  "mehrdeutig": 1}]):
        assert faelle_bilden(n, None) == []

    # Klasse 'kennung': existierende Kennung im Text ergibt einen Fall,
    # eine erfundene keinen -- beide Richtungen, wie beim Pfad-Kanal.
    class FakeCursor:
        def __init__(self, treffer): self._treffer = treffer
        def fetchone(self): return self._treffer

    class FakeConn2:
        def __init__(self, echte_lehre_ids, echte_pfade):
            self._lehren = echte_lehre_ids
            self._pfade = echte_pfade

        def execute(self, sql, params):
            wert = params[0]
            if "lessons_learned" in sql:
                return FakeCursor({"id": wert} if wert in self._lehren else None)
            return FakeCursor({"path": wert} if wert in self._pfade else None)

    echte_kennung_text = "Siehe L-0f4036 zur Lesetuer, das war der Befund."
    erfundene_kennung_text = "Siehe L-ffffff, das steht nirgends."
    knotenpfad_text = "Der Knoten /agents/mcp-tools erklaert das genauer."
    uebergabe_text = (
        "brainlehr, Fortsetzung. Lies zuerst STAND.md, dann arbeite.\n\n"
        "FAKTEN (gemessen 2026-08-09):\n"
        "  Der Knoten /agents/mcp-tools traegt den Befund.\n"
        "  Weitere Zeile Kontext, damit der Text lang genug ist fuer die Pruefung.\n")

    conn2 = FakeConn2(echte_lehre_ids={"L-0f4036"}, echte_pfade={"/agents/mcp-tools"})

    kf = kennung_faelle_bilden([echte_kennung_text], conn2)
    assert len(kf) == 1 and kf[0]["klasse"] == "kennung", kf
    assert kf[0]["ziele"] == [{"art": "lehre", "id": "L-0f4036"}]
    assert kf[0]["satzart"] == "frage", kf              # kurzer Fliesstext, kein Imperativ

    assert kennung_faelle_bilden([erfundene_kennung_text], conn2) == [], \
        "eine erfundene Kennung wurde als Fall gezaehlt"

    kf_pfad = kennung_faelle_bilden([knotenpfad_text], conn2)
    assert len(kf_pfad) == 1
    assert kf_pfad[0]["ziele"] == [{"art": "knoten", "id": "/agents/mcp-tools"}]

    # Uebergabe-Prompt: echt, aber keine Frage -- bleibt erhalten, satzart 'auftrag'.
    kf_uebergabe = kennung_faelle_bilden([uebergabe_text], conn2)
    assert len(kf_uebergabe) == 1, kf_uebergabe
    assert kf_uebergabe[0]["satzart"] == "auftrag", kf_uebergabe

    # Ein 'pfad'-Fall bleibt Klasse 'pfad', nicht vermischt mit 'kennung'.
    with mock.patch.object(ck, "wissen_zu",
                            lambda pfad, conn: [{"quelle_art": "lehre", "quelle_id": "L-1",
                                                  "mehrdeutig": 0}] if "trip_service" in pfad else []):
        f_pfad = faelle_bilden(n, None)
    assert f_pfad[0]["klasse"] == "pfad", f_pfad
    assert f_pfad[0]["satzart"] == "frage", f_pfad      # Bitte-Formulierung, kein Auftrag-Marker

    # Doppelter Text ergibt einen Fall, nicht zwei.
    doppelt = _ohne_doppelte([echte_kennung_text, echte_kennung_text, knotenpfad_text])
    assert doppelt == [echte_kennung_text, knotenpfad_text], doppelt
    assert len(kennung_faelle_bilden(doppelt, conn2)) == 2

    print("selftest ok (Gegenprobe je Klasse in beide Richtungen)", file=sys.stderr)

    # Kanal 'lese': ein gezieltes read auf ein echtes Nachrichtenfenster ist
    # ein Fall -- ohne Wortlaut-Ueberschneidung mit dem Prompt (anders als
    # 'pfad'/'kennung'). Drei Gegenproben: Fenstergrenze, Kontamination,
    # Selbstlauf-Ausschluss.
    import sqlite3 as _sqlite3

    recall_lese = Path(tempfile.mkdtemp()) / "recall_log.jsonl"
    recall_lese.write_text("\n".join(json.dumps(z) for z in [
        {"session": "aaaa1111", "ts": "2026-08-12T10:00:00+00:00",
         "prompt": "Wo steht die Regel zur Fenstergroesse genau?", "nodes": []},
        {"session": "aaaa1111", "ts": "2026-08-12T10:00:20+00:00",
         "prompt": "Und was gilt fuer die zweite Frage in derselben Sitzung?", "nodes": []},
        {"session": "bbbb2222", "ts": "2026-08-12T10:00:00+00:00",
         "prompt": "Erklaer mir das Ergebnis, das du gerade eingespielt hast.",
         "nodes": ["/x/schon-da"]},
        {"session": "cccc3333", "ts": "2026-08-12T10:00:00+00:00",
         "prompt": "Was steht eigentlich in der Fenstergroessen-Regel?", "nodes": []},
        {"session": "probe", "ts": "2026-08-12T10:00:00+00:00",
         "prompt": "Testzeile aus der eigenen Arbeit an diesem Sammler selbst.", "nodes": []},
    ]) + "\n", encoding="utf-8")

    conn3 = _sqlite3.connect(":memory:")
    conn3.row_factory = _sqlite3.Row
    conn3.execute("CREATE TABLE access_log (node_path TEXT, action TEXT, status TEXT, "
                   "client TEXT, session TEXT, timestamp TEXT)")

    def _log(session, node_path, ts, client="claude-code", action="read", status="completed"):
        conn3.execute("INSERT INTO access_log VALUES (?,?,?,?,?,?)",
                       (node_path, action, status, client, session, ts))

    _log("aaaa1111", "/x/echt", "2026-08-12T10:00:05Z")            # im ersten Fenster -> Fall
    _log("aaaa1111", "/x/nach-naechster", "2026-08-12T10:00:25Z")  # nach der 2. Nachricht -> gehoert dorthin
    _log("bbbb2222", "/x/schon-da", "2026-08-12T10:00:05Z")        # Kontamination -> verworfen
    _log("cccc3333", "/x/skript-only", "2026-08-12T10:00:05Z", client="skript")  # Selbstlauf -> kein Fall
    conn3.commit()

    lese_f, kontam = lese_faelle_bilden(conn3, recall_lese)
    ziele_je_prompt = {f["prompt"]: [z["id"] for z in f["ziele"]] for f in lese_f}
    assert ziele_je_prompt.get("Wo steht die Regel zur Fenstergroesse genau?") == ["/x/echt"], ziele_je_prompt
    assert ziele_je_prompt.get("Und was gilt fuer die zweite Frage in derselben Sitzung?") \
        == ["/x/nach-naechster"], ziele_je_prompt
    assert "Erklaer mir das Ergebnis, das du gerade eingespielt hast." not in ziele_je_prompt, \
        "ein kontaminierter Fall (Knoten war schon eingespielt) haette verworfen werden muessen"
    assert kontam == 1, kontam
    assert "Was steht eigentlich in der Fenstergroessen-Regel?" not in ziele_je_prompt, \
        "ein Selbstlauf-Read (client='skript') wurde faelschlich als Fall gezaehlt"
    assert all(f["klasse"] == "lese" for f in lese_f)
    assert all(e["session"] != "probe" for e in _einspielungen(recall_lese)), \
        "eine Testzeile (session 'probe') wurde als Betreiber-Sitzung genommen"

    print("selftest ok (lese-Kanal: Fenstergrenze, Kontamination, Selbstlauf-Ausschluss geprueft)",
          file=sys.stderr)

    # s12_bericht: der Pfad aus den Faellen muss ueber knowledge_nodes.id
    # aufgeloest werden, NICHT direkt als Teilungsschluessel dienen -- sonst
    # misst der Nenner eine andere Teilung als teilung_s12.py selbst (siehe
    # Funktions-Docstring). Gegenprobe: derselbe Pfad mit zwei verschiedenen
    # ids muesste (Zufallsfall vorbehalten) unterschiedliche Haelften ziehen
    # koennen -- hier reicht der Nachweis, dass ueberhaupt aufgeloest wird.
    conn3.execute("CREATE TABLE knowledge_nodes (path TEXT, id TEXT)")
    conn3.execute("INSERT INTO knowledge_nodes VALUES ('/x/a', 'nodeid-a')")
    conn3.execute("INSERT INTO knowledge_nodes VALUES ('/x/b', 'nodeid-b')")
    conn3.commit()
    faelle_s12 = [
        {"prompt": "p1", "klasse": "lese", "satzart": "frage",
         "ziele": [{"art": "knoten", "id": "/x/a"}]},
        {"prompt": "p2", "klasse": "lese", "satzart": "frage",
         "ziele": [{"art": "knoten", "id": "/x/ohne-knoten"}]},  # kein passender Knoten mehr
    ]
    s12_test = s12_bericht(faelle_s12, conn3)
    assert s12_test["knotenziele"] == 2 and s12_test["verschiedene_knoten"] == 2, s12_test
    erwartete_haelfte = teilung_s12.haelfte("knoten", "nodeid-a")
    andere_haelfte = teilung_s12.haelfte("knoten", "/x/a")  # der FALSCHE Schluessel (Pfad)
    gezogene_haelfte = [h for h, n in s12_test["faelle_je_haelfte"].items() if n > 0
                         and h != "gemischt"]
    assert gezogene_haelfte == [erwartete_haelfte], (s12_test, erwartete_haelfte)
    assert sum(s12_test["faelle_je_haelfte"].values()) == 1, \
        "Fall p2 ohne aufloesbaren Knoten haette keine Haelfte bekommen duerfen"
    if erwartete_haelfte != andere_haelfte:
        print("  s12_bericht loest ueber die id auf, nicht ueber den Pfad (Gegenprobe traf zu)",
              file=sys.stderr)

    print("selftest ok (s12_bericht: Pfad->id-Aufloesung, unaufloesbarer Fall ohne Haelfte)",
          file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sammeln", action="store_true")
    p.add_argument("--out", type=Path)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return

    aus_log = echte_nachrichten()
    aus_sitzungen = sitzungs_nachrichten()
    nachrichten = _ohne_doppelte(aus_log + aus_sitzungen)

    with speicher.lesen() as conn:
        faelle = faelle_bilden(nachrichten, conn) + kennung_faelle_bilden(nachrichten, conn)
        lese_f, lese_kontaminiert = lese_faelle_bilden(conn)
        faelle += lese_f
        s12 = s12_bericht(faelle, conn)

    KLASSEN = ("pfad", "kennung", "lese")
    nach_klasse = {k: sum(1 for f in faelle if f["klasse"] == k) for k in KLASSEN}
    nach_satzart = {s: sum(1 for f in faelle if f["satzart"] == s) for s in ("frage", "auftrag")}
    print(f"{len(aus_log)} aus recall_log + {len(aus_sitzungen)} aus Sitzungen "
          f"-> {len(nachrichten)} eindeutige Nachrichten -> {len(faelle)} Faelle "
          f"(pfad: {nach_klasse['pfad']}, kennung: {nach_klasse['kennung']}, "
          f"lese: {nach_klasse['lese']}) "
          f"(frage: {nach_satzart['frage']}, auftrag: {nach_satzart['auftrag']})")
    print(f"    lese-Kanal: {lese_kontaminiert} Kontaminationsfaelle verworfen "
          "(Knoten war der Sitzung schon eingespielt)")
    for k in KLASSEN:
        for s in ("frage", "auftrag"):
            n = sum(1 for f in faelle if f["klasse"] == k and f["satzart"] == s)
            print(f"    {k} x {s}: {n}")
    if len(faelle) < 20:
        print(f"  ZU WENIG ZUM MESSEN. {len(faelle)} Faelle sind ein Anfang, keine "
              "Grundlage -- die Anforderungen zu senken waere der Rueckweg zum "
              "erfundenen Korpus.")
    for f in faelle[:6]:
        quelle = f.get("pfade", sorted(kennungen(f["prompt"])))[:2]
        print(f"  [{f['klasse']}/{f['satzart']}] {quelle} -> {[z['id'] for z in f['ziele']]}")

    print(f"  S12-Nenner: {s12['knotenziele']} Knotenziele, {s12['verschiedene_knoten']} "
          f"verschiedene Knoten, Faelle je Haelfte: {s12['faelle_je_haelfte']}")

    if a.out:
        a.out.write_text(json.dumps(
            {"verfahren": "Aufgabentext aus recall_log + Sitzungstranskripten (echte "
                          "Nachricht), Ziel ueber code_kanten (Pfad), Existenzpruefung "
                          "(Kennung) oder gezieltes access_log-read im Nachrichtenfenster "
                          "(lese) -- getrennte Kanaele, keine Erzeugung",
             "nachrichten": len(nachrichten),
             "nachrichten_aus_log": len(aus_log),
             "nachrichten_aus_sitzungen": len(aus_sitzungen),
             "faelle_je_kanal": nach_klasse,
             "lese_kontaminationsfaelle_verworfen": lese_kontaminiert,
             "s12_nenner": s12,
             "faelle": faelle},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nGeschrieben: {a.out}")


if __name__ == "__main__":
    main()
