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
import sys
from datetime import datetime, timezone
from pathlib import Path

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
}
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
    try:
        offene = [dict(r) for r in conn.execute(
            "SELECT * FROM knowledge_nodes WHERE freigabe='offen' "
            "AND zurueckgezogen=0")]
        # fehlende Elternknoten nachziehen, bis die Kette steht
        vorhanden = {z["path"] for z in offene}
        fehlend = {z["parent_path"] for z in offene
                   if z.get("parent_path") and z["parent_path"] not in vorhanden} - {"/"}
        while fehlend:
            platz = ",".join("?" * len(fehlend))
            neu = [dict(r) for r in conn.execute(
                f"SELECT * FROM knowledge_nodes WHERE path IN ({platz})",
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
                           "SELECT * FROM lessons_learned WHERE freigabe='offen' "
                           "AND status='active' ORDER BY id")]
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
    return {"status": "geschrieben", "zeilen": len(zeilen), "ziel": str(ziel)}


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

    print("export_offen.py: Selbsttest gruen")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--db", type=Path,
                   default=Path(__file__).resolve().parent.parent / "knowledge.db")
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
