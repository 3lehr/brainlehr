#!/usr/bin/env python3
"""export_offen.py -- Auszug fuer ein weitergebbares Repo: nur Freigegebenes.

ANLASS (Betreiber, 2026-08-10): "wir muessen das ohne meine daten hochladen,
regeln waeren ok. der nasa stamm bsi usw auch. aber bitte so das ich die repo
prinzipiell an fremde weiter geben kann. wir sollten dafuer schon datenfelder
haben um es einfach zu haben?"

DAS DATENFELD GIBT ES SCHON: knowledge_nodes.freigabe / lessons_learned.freigabe
mit den Werten offen | intern | gesperrt. Dieses Werkzeug erfindet nichts, es
macht das vorhandene Feld zur Exportgrenze.

VORGABE IST DENY, wie ueberall: exportiert wird ausschliesslich freigabe='offen'.
Ein neuer Knoten ist per Datenbank-Vorgabe 'intern' und faellt damit automatisch
heraus -- niemand muss daran denken. Eine Blacklist waere der Fehler: jede
Blacklist hat ein Loch, und bei Personenbezug ist dieses Loch teuer
(/shared/arch/extraktion-aus-dokumenten-whitelist).

DIE POSITIVKONTROLLE IST PFLICHT, NICHT KUER. Ein Export, der "keine
personenbezogenen Daten gefunden" meldet, sagt ohne sie nichts ueber den
Bestand, sondern nur ueber das Werkzeug (L-732ae9: 44 Fehlalarme, null echte
Treffer, waehrend ein echter Name im Bestand stand). Darum laeuft nach jedem
Export eine Suche nach bekannten Werten, die NICHT enthalten sein duerfen --
findet sie einen, bricht der Lauf ab und schreibt nichts.

WAS DIESES WERKZEUG NICHT LEISTET: Es entscheidet nicht, WAS freigegeben wird.
Das ist eine Bewertung (Lizenz, Personenbezug, Betriebsgeheimnis) und bleibt
beim Menschen -- knowledge_freigeben ist das Werkzeug dafuer. Hier wird nur
ausgefuehrt, was dort entschieden wurde.

Aufruf:
    python3 export_offen.py --ziel auszug-offen/bestand.jsonl
    python3 export_offen.py --was-waere-offen      # Vorschau ohne Schreiben
    python3 export_offen.py --selftest
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

# Liegt eine Ebene unter der Wurzel: die Wurzel muss auf den Suchpfad,
# sonst findet `import knowledge_mcp_server` nichts. Muster aus haken/.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))

import argparse
import json
import re
import sqlite3

import trennung  # B3: der Auszug traegt nur den Mandanten/Kreis des Aufrufers
import sys
from datetime import datetime, timezone
from pathlib import Path

import ort  # noqa: E402 -- liefert DB, siehe haken/ort.py (L-6c6661)

# Werte, die im Export NICHT vorkommen duerfen. Zwei Sorten, beide noetig:
# bekannte Koeder (sie MUESSEN fehlen -- sonst ist der Filter blind) und
# Formmuster fuer Kontaktdaten. Die Koeder sind die eigentliche Kontrolle;
# ein Formkatalog allein findet einen Nachnamen ohne Anrede nie.
# DIE KOEDERLISTE STEHT NICHT IM CODE. Ein Koeder, der im Repo liegt, ist
# keiner mehr -- wer die Liste liest, weiss, welche Werte markiert sind. Aus
# demselben Grund wird auch die Pseudonym-Mapping-Tabelle nie committet
# (L-dc0f44). Die Werte liegen daneben in koederwerte.txt, eine Zeile je Wert,
# gitignored. Fehlt die Datei, laeuft der Export NICHT ohne Kontrolle durch --
# er bricht ab, denn eine Positivkontrolle ohne bekannte Werte ist keine.
KOEDERDATEI = Path(__file__).resolve().parent.parent / "koederwerte.txt"  # Wurzel, eine Ebene ueber diesem Ordner (Umzug 2026-08-10)


def koederwerte() -> tuple[str, ...]:
    if not KOEDERDATEI.exists():
        raise SystemExit(
            f"Keine Koederliste unter {KOEDERDATEI}. Ohne bekannte Werte ist "
            f"die Positivkontrolle blind, und ein 'sauber' saegt nichts aus. "
            f"Eine Zeile je Wert anlegen (die Datei ist gitignored).")
    return tuple(z.strip() for z in
                 KOEDERDATEI.read_text(encoding="utf-8").splitlines()
                 if z.strip() and not z.startswith("#"))
VERBOTENE_MUSTER = {
    "IBAN": re.compile(r"\bDE\d{2}[ ]?(?:\d{4}[ ]?){4}\d{2}\b"),
    # Kein Buchstabe unmittelbar davor: sonst trifft das Muster
    # Teilenummern wie "GSC-05-82730-00" (gemessen 2026-08-10, einziger
    # Treffer in 1731 NASA-/Methodik-Knoten -- und ein Fehlalarm).
    "Telefon": re.compile(r"(?<![A-Za-z0-9-])(?:\+49|0)[\d /()-]{9,20}\d\b"),
    # Nachtrag 2026-08-10: Ein Heimatverzeichnis traegt den Benutzernamen des
    # Betreibers, ein Plattenpfad sein Ablagelayout. Gemessen im Auszug vom
    # selben Tag: 61 von 1746 freigegebenen Knoten trugen so etwas, 59 davon im
    # Herkunftsfeld -- darunter 15 mit "erzeugt aus /Users/<name>/.claude/
    # CLAUDE.md", also dem Pfad zu den privaten Arbeitsanweisungen. FREIGABE
    # HEISST NICHT FREI VON INTERNEN SPUREN: das Feld sagt, dass der INHALT
    # hinausgehen darf, nicht dass die Herkunftsangabe daneben es auch darf.
    "Heimatverzeichnis": re.compile(r"/Users/[^/\s\"]+/"),
    "Plattenpfad": re.compile(r"/Volumes/[^/\s\"]+/"),
}

# Ersetzungen, die VOR der Kontrolle laufen. Sie nehmen der Herkunftsangabe den
# Personen- und Geraetebezug und lassen ihre Aussage stehen: welche Datei die
# Quelle war, bleibt lesbar, nur Benutzername und Plattenlayout entfallen.
# Genau die Regel aus L-adfb33 -- ein Beleg braucht die FORM des Datums, nicht
# seinen INHALT. Der Empfaenger ist hier ein Dritter, und nur dort ist
# Maskierung richtig (Direktive "Keine Entwicklerinformation in der
# Oberflaeche": der Unterschied ist der Empfaenger, nicht die Technik).
ENTLOKALISIERUNG = (
    (re.compile(r"/Users/[^/\s\"]+/"), "<heim>/"),
    (re.compile(r"/Volumes/[^/\s\"]+/"), "<ablage>/"),
    # Seit 2026-08-20, gefunden beim ersten vollstaendigen Export: Die zwei
    # Regeln oben nehmen den PFAD, lassen aber die NAMEN stehen. Gemessen im
    # fertigen Auszug: Fundstellen mit `Begod2026` oder `brainlehr-privat` im
    # Fliesstext freigegebener Eintraege. Kein Geheimnis -- aber
    # Verzeichnisstruktur und Nomenklatur des Betreibers, und der Pruefer des
    # oeffentlichen Repos beanstandet sie zu Recht als `private-context`.
    #
    # Ersetzt wird durch SPRECHENDE Platzhalter, nicht durch Sterne: Die
    # Aussage eines Eintrags bleibt lesbar ("die Hausregeln verlangen X"),
    # nur der Ort verschwindet. Eine Maskierung, die den Satz unverstaendlich
    # macht, waere schlimmer als der Verzicht auf den Eintrag.
    #
    # NICHT in dieser Liste steht CLAUDE.md, und das ist eine Entscheidung
    # vom selben Tag mit einem konkreten Anlass: Die Regel stand hier kurz
    # und schrieb den Docstring von kern/normrang.py von RICHTIG auf FALSCH.
    # Er beschreibt "Rang 1 == globale CLAUDE.md", und der Code prueft genau
    # diesen Dateinamen -- "Rang 1 == globale <Hausregeln>" nennt nicht mehr,
    # worauf geprueft wird. Sachlich gehoerte sie ohnehin nicht hierher:
    # CLAUDE.md ist die oeffentlich dokumentierte Projektdatei von Claude
    # Code, nicht die Nomenklatur des Betreibers. Verraten wuerde ihr INHALT,
    # nicht ihr Name.
    (re.compile(r"\bBegod2026\b", re.I), "<arbeitsbereich>"),
    (re.compile(r"\bbrainlehr-privat\b", re.I), "<privates Repo>"),
)


_LEHRENKENNUNG = re.compile(r"\bL-[0-9a-f]{6}\b")


def verweise_entschaerfen(zeilen: list[dict]) -> tuple[list[dict], int]:
    """Verweise auf Lehren, die NICHT mitgeliefert werden, ersetzen.

    Gefunden am 2026-08-20 beim ersten vollstaendigen Export: 35 freigegebene
    Eintraege verweisen im Fliesstext auf Lehren, die selbst nicht freigegeben
    sind. Fuer den Leser ist das ein Zeiger ins Leere -- und er verraet allein
    durch sein Vorhandensein, dass es dort etwas gibt, das er nicht sehen
    darf.

    Die Menge der mitgelieferten Kennungen ergibt sich aus den Zeilen SELBST,
    nicht aus einer zweiten Abfrage: Was hier im Auszug steht, ist per Bauart
    genau das, was der Leser bekommt. Eine zweite Quelle koennte abweichen.

    Ersetzt wird durch einen sprechenden Platzhalter, nicht geloescht -- der
    Satz bleibt lesbar ("dieselbe Klasse wie <nicht oeffentliche Lehre>"), und
    der Leser sieht, dass dort etwas fehlt, statt einen unerklaerten Bruch zu
    finden."""
    vorhanden = {str(e["zeile"].get("id") or "") for e in zeilen}
    getroffen = 0
    raus = []
    for eintrag in zeilen:
        zeile = dict(eintrag["zeile"])
        for feld, wert in zeile.items():
            if not isinstance(wert, str) or "L-" not in wert:
                continue
            neu_wert = _LEHRENKENNUNG.sub(
                lambda m: m.group(0) if m.group(0) in vorhanden
                else "<nicht oeffentliche Lehre>", wert)
            if neu_wert != wert:
                zeile[feld] = neu_wert
                getroffen += 1
        raus.append({**eintrag, "zeile": zeile})
    return raus, getroffen


def entlokalisiere(zeilen: list[dict]) -> tuple[list[dict], int]:
    """Pfade entschaerfen. Gibt die bereinigten Zeilen und die Zahl der
    betroffenen Felder zurueck -- eine stille Ersetzung waere schlimmer als
    keine, weil niemand merkt, wie viel sie anfasst."""
    getroffen = 0
    sauber = []
    for eintrag in zeilen:
        zeile = dict(eintrag["zeile"])
        for feld, wert in zeile.items():
            if not isinstance(wert, str):
                continue
            neu = wert
            for rx, ersatz in ENTLOKALISIERUNG:
                neu = rx.sub(ersatz, neu)
            if neu != wert:
                zeile[feld] = neu
                getroffen += 1
        sauber.append({**eintrag, "zeile": zeile})
    return sauber, getroffen
# Mailadressen aus oeffentlichen Fremdquellen sind kein Personenbezug des
# Betreibers -- die NASA-LLIS-Eintraege tragen Behoerdenadressen.
MAIL = re.compile(r"\b[\w.%+-]+@([\w.-]+\.[a-zA-Z]{2,})\b")
MAIL_ERLAUBT = ("nasa.gov", "1x.png")


def _db(pfad: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{pfad}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def sammle(pfad: Path) -> list[dict]:
    """Alles mit freigabe='offen' -- im Format von brainlehr.py raus.

    DASSELBE FORMAT, NICHT EIN ZWEITES: Der erste Entwurf schrieb eine eigene,
    reduzierte Zeilenform. Der Erstlauf an einem leeren Ort zeigte, was das
    heisst -- `brainlehr.py rein` weist die Datei ab (Kopfzeile
    'brainlehr_auszug' fehlt), der Beispielbestand liess sich also gar nicht
    einspielen, und die Suche lieferte 0 Treffer. Ein zweites Format ist eine
    zweite Wahrheit.

    ELTERN VOR KINDERN: knowledge_nodes_parent_check_bi weist ein Kind ab,
    dessen Elternknoten fehlt. Der Filter 'path LIKE /nasa-llis/%' trifft den
    Astknoten '/nasa-llis' NICHT -- er wird darum ergaenzt, sonst ist der
    Auszug nicht einlesbar. Auch das fiel erst beim Erstlauf auf."""
    conn = _db(pfad)
    # BDW-E06 "Cross-Tenant-Export scheitert": derselbe Filter wie beim
    # Lesen, an DERSELBEN Stelle wie die Freigabe. Die Freigabe regelt, was
    # nach aussen darf; der Mandant regelt, WESSEN Daten das ueberhaupt sind.
    # Beides ist noetig -- ein 'offen' des fremden Mandanten ist nicht meine
    # Entscheidung gewesen und geht darum auch nicht in meinen Auszug.
    # sichtbar_sql_wenn_spalte statt sichtbar_sql: diese Verbindung ist
    # NUR LESEND geoeffnet (_db) und kann eine fehlende Spalte nicht
    # nachziehen. Eine Datenbank vor B1 hat genau einen Mandanten.
    _sicht = trennung.sichtbar_sql_wenn_spalte(conn)
    try:
        offene = [dict(r) for r in conn.execute(
            f"SELECT * FROM knowledge_nodes WHERE freigabe='offen' "
            f"AND zurueckgezogen=0 AND {_sicht}")]
        # fehlende Elternknoten nachziehen, bis die Kette steht
        vorhanden = {z["path"] for z in offene}
        fehlend = {z["parent_path"] for z in offene
                   if z.get("parent_path") and z["parent_path"] not in vorhanden} - {"/"}
        while fehlend:
            platz = ",".join("?" * len(fehlend))
            # Auch die nachgezogenen ELTERN bleiben an der Grenze: ein
            # Astknoten des fremden Mandanten waere sonst der Weg, auf dem
            # die Trennung ueber die Baumkette doch noch leckt.
            neu = [dict(r) for r in conn.execute(
                f"SELECT * FROM knowledge_nodes WHERE path IN ({platz}) AND {_sicht}",
                sorted(fehlend))]
            if not neu:
                break
            offene += neu
            vorhanden |= {z["path"] for z in neu}
            fehlend = {z["parent_path"] for z in neu
                       if z.get("parent_path") and z["parent_path"] not in vorhanden} - {"/"}
        zeilen = [{"tabelle": "knowledge_nodes", "zeile": z}
                  for z in sorted(offene, key=lambda z: (z.get("level") or 0, z["path"]))]
        try:
            zeilen += [{"tabelle": "lessons_learned", "zeile": dict(r)}
                       for r in conn.execute(
                           f"SELECT * FROM lessons_learned WHERE freigabe='offen' "
                           f"AND status='active' AND {_sicht} ORDER BY id")]
        except sqlite3.OperationalError:
            pass          # DB ohne die Spalte -> keine Lehren im Export
    finally:
        conn.close()
    return zeilen


def pruefe(zeilen: list[dict]) -> list[str]:
    """Findet, was nicht hinausgehen darf. Leere Liste = sauber."""
    text = json.dumps(zeilen, ensure_ascii=False)
    funde = [f"Koederwert im Export: {w[:4]}…" for w in koederwerte() if w in text]
    funde += [f"{name} im Export: {m.group(0)[:8]}…"
              for name, rx in VERBOTENE_MUSTER.items()
              for m in [rx.search(text)] if m]
    funde += [f"fremde Mailadresse im Export: …@{d}"
              for d in {m.group(1) for m in MAIL.finditer(text)}
              if d not in MAIL_ERLAUBT]
    return funde


def exportiere(db: Path, ziel: Path, *, jetzt: datetime | None = None) -> dict:
    """Schreibt NUR, wenn die Kontrolle sauber ist. Ein Export, der beim
    Fund noch schreibt, verlaesst sich darauf, dass jemand die Warnung liest."""
    zeilen = sammle(db)
    # Reihenfolge ist tragend: erst entschaerfen, dann pruefen. Umgekehrt waere
    # die Kontrolle bloss die Ansage dessen, was gleich ersetzt wird -- und ein
    # Muster, das die Ersetzung uebersieht, faende niemand mehr.
    zeilen, ersetzt = entlokalisiere(zeilen)
    zeilen, verweise = verweise_entschaerfen(zeilen)
    funde = pruefe(zeilen)
    if funde:
        return {"status": "abgebrochen", "zeilen": len(zeilen), "funde": funde}
    ziel.parent.mkdir(parents=True, exist_ok=True)
    # Kopfzeile im Format von brainlehr.py raus -- sonst weist `rein` sie ab.
    anzahl = {}
    for z in zeilen:
        anzahl[z["tabelle"]] = anzahl.get(z["tabelle"], 0) + 1
    kopf = {"brainlehr_auszug": 1,
            "erzeugt": (jetzt or datetime.now(timezone.utc)).isoformat(),
            "quelle": "Auszug des Freigegebenen (freigabe='offen')",
            "regel": "nur freigabe='offen'",
            "trigger": [], "zeilen": anzahl}
    with ziel.open("w", encoding="utf-8") as f:
        f.write(json.dumps(kopf, ensure_ascii=False) + "\n")
        for z in zeilen:
            f.write(json.dumps(z, ensure_ascii=False) + "\n")
    return {"status": "geschrieben", "zeilen": len(zeilen), "ziel": str(ziel),
            "entlokalisierte_felder": ersetzt,
            "entschaerfte_verweise": verweise}


def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        kw = koederwerte()
        db = Path(tmp) / "k.db"
        conn = sqlite3.connect(str(db))
        conn.executescript((Path(__file__).resolve().parent.parent / "schema.sql")
                           .read_text(encoding="utf-8"))
        def add(nid, path, summary, freigabe):
            conn.execute(
                "INSERT INTO knowledge_nodes (id, path, title, summary, source,"
                " anlass, norm_entscheidung, freigabe, zurueckgezogen)"
                " VALUES (?,?,?,?,'test','selbst','keine_norm',?,0)"
                .replace("norm_entscheidung, freigabe",
                         "norm_entscheidung, norm_entschieden_von,"
                         " norm_entschieden_grund, freigabe")
                .replace("'keine_norm',?", "'keine_norm','test','test',?"),
                (nid, path, path, summary, freigabe))
        add("n1", "/nasa-llis/1", "Ventil versagte bei Kaelte", "offen")
        add("n2", "/ops/weg", f"Vorgang {kw[0]}", "intern")
        conn.commit(); conn.close()

        # --- Vorgabe deny: nur 'offen' geht raus ---------------------------
        z = sammle(db)
        assert [x["zeile"]["id"] for x in z] == ["n1"], z
        erg = exportiere(db, Path(tmp) / "out.jsonl")
        assert erg["status"] == "geschrieben" and erg["zeilen"] == 1

        # --- POSITIVKONTROLLE: waere der Koeder offen, MUSS es auffallen ---
        conn = sqlite3.connect(str(db))
        conn.execute("UPDATE knowledge_nodes SET freigabe='offen' WHERE id='n2'")
        conn.commit(); conn.close()
        erg = exportiere(db, Path(tmp) / "out2.jsonl")
        assert erg["status"] == "abgebrochen", erg
        assert any("Koederwert" in f for f in erg["funde"]), erg["funde"]
        assert not (Path(tmp) / "out2.jsonl").exists(), \
            "bei einem Fund darf NICHTS geschrieben werden"

        # --- Formmuster: IBAN und Telefon ----------------------------------
        for text, wort in (("Konto DE89 3704 0044 0532 0130 00", "IBAN"),
                           ("Ruf 0721 1234567 an", "Telefon"),
                           ("Mail an kunde@example.com", "Mailadresse")):
            assert any(wort in f for f in pruefe([{"summary": text}])), text
        # ... und die erlaubte Ausnahme
        assert pruefe([{"summary": "david@nasa.gov"}]) == []

    # Entlokalisierung (Nachtrag 2026-08-10). Rot vor gruen: gegen den Stand
    # ohne ENTLOKALISIERUNG scheitert dieser Block an der ersten Zusicherung,
    # denn dann steht der Benutzername unveraendert im Export.
    probe = [{"tabelle": "knowledge_nodes", "zeile": {
        "id": "p1",
        "source": "erzeugt aus /Users/mustermann/.claude/CLAUDE.md (Stand X)",
        "content": "Massgeblich ist /Volumes/platte/verbund/hub/laufzeit/register.jsonl.",
        "level": 0}}]
    sauber, getroffen = entlokalisiere(probe)
    z = sauber[0]["zeile"]
    assert "/Users/" not in z["source"], z["source"]
    assert z["source"] == "erzeugt aus <heim>/.claude/CLAUDE.md (Stand X)", z["source"]
    assert z["content"] == "Massgeblich ist <ablage>/verbund/hub/laufzeit/register.jsonl.", z["content"]
    assert getroffen == 2, getroffen

    # Die Aussage bleibt: der Dateiname ist weiter lesbar, nur Person und
    # Ablageort sind weg. Ein Beleg braucht die Form, nicht den Inhalt.
    assert "CLAUDE.md" in z["source"] and "register.jsonl" in z["content"]

    # Negativfall: was keinen lokalen Pfad traegt, wird nicht angefasst.
    unberuehrt = [{"tabelle": "knowledge_nodes", "zeile": {
        "id": "p2", "source": "NASA LLIS 1227", "level": 0}}]
    gleich, null = entlokalisiere(unberuehrt)
    assert gleich[0]["zeile"] == unberuehrt[0]["zeile"] and null == 0, gleich

    # Nichtzeichenketten ueberstehen den Durchgang unveraendert.
    gemischt = [{"tabelle": "knowledge_nodes", "zeile": {
        "id": "p3", "level": 3, "confidence": 1.0, "tags": None,
        "source": "/Users/x/y"}}]
    g, _ = entlokalisiere(gemischt)
    assert g[0]["zeile"]["level"] == 3 and g[0]["zeile"]["tags"] is None

    # Das Netz hinter der Ersetzung: pruefe() faengt, was sie uebersieht.
    assert pruefe([{"tabelle": "knowledge_nodes",
                    "zeile": {"id": "p4", "source": "/Users/rest/pfad"}}]), \
        "Heimatverzeichnis muss von pruefe() gefunden werden"

    print("export_offen.py: Selbsttest gruen")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--db", type=Path, default=ort.DB)
    p.add_argument("--ziel", type=Path)
    p.add_argument("--was-waere-offen", action="store_true")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return 0
    if a.was_waere_offen:
        z = sammle(a.db)
        print(f"freigabe='offen': {len(z)} Eintraege")
        for x in z[:20]:
            print("  ", x.get("path") or x.get("id"))
        funde = pruefe(z)
        if not z:
            print("\nNICHTS FREIGEGEBEN. Das ist kein sauberer Export, sondern")
            print("ein leerer -- die Kontrolle hatte nichts zu pruefen.")
            print("Freigeben mit knowledge_freigeben, dann erneut ansehen.")
            return 0
        print(f"\nKontrolle: {'SAUBER' if not funde else 'FUNDE!'}")
        for f in funde:
            print("  ", f)
        return 0
    if not a.ziel:
        p.error("--ziel fehlt (oder --was-waere-offen benutzen)")
    erg = exportiere(a.db, a.ziel)
    print(json.dumps(erg, ensure_ascii=False, indent=2))
    return 0 if erg["status"] == "geschrieben" else 1


if __name__ == "__main__":
    raise SystemExit(main())
