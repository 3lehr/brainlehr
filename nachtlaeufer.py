#!/usr/bin/env python3
"""nachtlaeufer.py — Beobachter, der vorlegt, nicht entscheidet.

ROLLENTRENNUNG IST DER KERN (Auftrag 2026-08-07): der Laeufer beobachtet und
legt vor, er entscheidet nichts -- das ist baulich erzwungen, nicht per
Kommentar. Er oeffnet knowledge.db NUR LESEND (SQLite-URI mode=ro, s.
_ro_connect()) -- ein Schreibversuch scheitert mit sqlite3.OperationalError
("attempt to write a readonly database"), unabhaengig davon, was der Code
spaeter mal versucht. Einzige Ausnahme: die eigene Vorlage schreibt er in
eine EIGENE Datei (VORLAGE_PFAD), nie nach knowledge.db.

KONFIGURATION in der vorhandenen Tabelle knowledge_config (Muster: embed_model
in schema.sql, dort per Trigger gesichert -- hier nur gelesen, kein Trigger
noetig, weil ein nur-lesender Client dort ohnehin nichts schreiben kann):
  nachtlaeufer_aktiv     'ein'/'aus', Vorgabe 'aus' -- wir kennen weder Budget
                         noch angeschlossenes Modell des Nutzers, Einschalten
                         ist eine bewusste Handlung.
  nachtlaeufer_backend   freier String, Vorgabe 'keiner'. KEIN Modell fest
                         verdrahtet -- nur 'keiner' ist hier implementiert
                         (lokale Kandidatenerzeugung, s. _erzeuge_kandidaten).
                         Ein echtes Backend (Ollama o.ae.) anzuschliessen ist
                         YAGNI, solange niemand eines gewaehlt hat.
  nachtlaeufer_budget    Hoechstzahl AUFRUFE je Lauf, Vorgabe '5'. In Aufrufen
                         gezaehlt, nicht in Tokens: auf dieser Maschine ist
                         kein Tokenizer installiert und die Zaehl-Schnittstelle
                         der Anbieter braucht Zugangsdaten (die dieser Laeufer
                         nicht anfassen darf) -- eine Token-Obergrenze waere
                         eine Zahl, die Genauigkeit vortaeuscht, die hier nicht
                         herstellbar ist. Ein "Aufruf" ist die Arbeitseinheit
                         gegen das Backend: bei 'keiner' (Vorgabe) ist das eine
                         lokal erzeugte Kandidatenmessung -- der Zaehler bleibt
                         so wirksam und ohne Netz testbar, statt ein Backend
                         vorzutaeuschen, das nicht angeschlossen ist.
  nachtlaeufer_deckel    Hoechstzahl Funde je Vorlage, Vorgabe '8'.

DIE VORLAGE enthaelt MESSUNGEN MIT FUNDSTELLE, keine Urteile -- der Empfaenger
prueft in Sekunden, nicht in Minuten (Begruendung: das Modell des Nutzers kann
schwach sein und Falschbefunde erzeugen; ein Urteil waere dann nicht
nachpruefbar, eine Messung schon). Was der Deckel abschneidet, wird
AUSDRUECKLICH genannt ("N von M gezeigt"), nie stillschweigend weggelassen.

ERSTE AUFGABE, fest eingebaut (Anlass: runs/pruefkorpus_v3.json vom
2026-08-07, 42 Faelle -- Kategorie 'kombiniert_ablenker' ist die EINZIGE mit
0 von 2 bestanden, alle anderen Kategorien bestehen. Zwei Faelle sind keine
Quote): weitere Pruefaelle derselben Kategorie ERZEUGEN, als VORSCHLAG in der
Vorlage -- aufgenommen werden sie erst nach Freigabe. pruefkorpus_v3.py wird
dabei NUR GELESEN (importiert), nie geaendert (Tabu laut Auftrag).

UEBERGABE: Bauform von scripts/modell_abfrage_hook.py abgeschaut (SessionStart
druckt <block>, sonst still). Ist der Laeufer aus, oder liegt keine frische
Vorlage vor -> NICHTS gedruckt. Eine gedruckte Vorlage wird als 'vorgelegt'
markiert (Datei umbenannt), damit sie nicht bei jedem Sitzungsstart erneut
erscheint -- ein neuer --lauf legt die naechste vor.

Aufruf:
    python3 nachtlaeufer.py --lauf         # Beobachtung fahren, Vorlage schreiben
    python3 nachtlaeufer.py                # SessionStart-Hook: Vorlage drucken (falls da+aktiv)
    python3 nachtlaeufer.py --selbsttest
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parent
DB_PATH = SHARED_KNOWLEDGE / "knowledge.db"
VORLAGE_PFAD = SHARED_KNOWLEDGE / "nachtlaeufer_vorlage.md"

_DEFAULTS = {
    "nachtlaeufer_aktiv": "aus",
    "nachtlaeufer_backend": "keiner",
    "nachtlaeufer_budget": "5",
    "nachtlaeufer_deckel": "8",
}


def _ro_connect(db_path: Path) -> sqlite3.Connection:
    """Nur-lesender Zugang -- der wichtigste Beleg der Rollentrennung.
    Ein INSERT/UPDATE/DELETE ueber diese Verbindung scheitert immer, auch
    wenn ein spaeterer Programmierfehler versucht, etwas zu schreiben."""
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0)


def _config(conn: sqlite3.Connection) -> dict[str, str]:
    out = dict(_DEFAULTS)
    try:
        rows = conn.execute(
            "SELECT key, value FROM knowledge_config WHERE key LIKE 'nachtlaeufer_%'"
        ).fetchall()
        out.update({k: v for k, v in rows})
    except sqlite3.OperationalError:
        pass  # Tabelle fehlt (alte/minimale DB) -> Vorgaben gelten
    return out


# ---------------------------------------------------------------------------
# Erste Aufgabe: Vorschlaege fuer Kategorie 'kombiniert_ablenker'.
# Nutzt die vorhandenen Bausteine aus pruefkorpus_v3.py NUR LESEND (Import).

def _aehnlich_paare() -> list[tuple[str, str]]:
    """Alle im Korpus bereits vorhandenen aehnlich-benannten Paare (Sorte 1) --
    das sind die einzigen Kandidaten fuer einen benannten Ablenker, weil nur
    sie eine Einheit mit einem Ziel teilen UND einen nahen Namen tragen."""
    import pruefkorpus_v3 as pk3  # nur lesend/importierend, s. Moduldoc

    namen = {slug: name for slug, name, *_ in pk3.GEGENSTAENDE}
    einheiten = {slug: einheit for slug, _, einheit, *_ in pk3.GEGENSTAENDE}
    paare = []
    for a, b in [("velunit", "velunip"), ("frastek", "frastel"), ("moldrian", "moldrion")]:
        if einheiten.get(a) == einheiten.get(b):
            paare.append((a, b))
    return paare


def _erzeuge_kandidaten(budget: int, bereits: set[str]) -> tuple[list[dict], int]:
    """Erzeugt bis zu `budget` NEUE (noch nicht in `bereits` vorgeschlagene)
    kombiniert_ablenker-Kandidaten. Rueckgabe: (Kandidaten, Aufrufe).
    Ein Kandidat = ein Aufruf (s. Moduldoc-Begruendung nachtlaeufer_budget)."""
    import pruefkorpus_v3 as pk3

    paare = _aehnlich_paare()
    kandidaten: list[dict] = []
    aufrufe = 0
    for i, (s1, a1) in enumerate(paare):
        for j, (s2, a2) in enumerate(paare):
            if i == j:
                continue
            for m1 in (1, 2, 3, 4):
                for m2 in (1, 2, 3, 4):
                    if aufrufe >= budget:
                        return kandidaten, aufrufe
                    kennung = f"{s1}{m1}-{s2}{m2}"
                    if kennung in bereits:
                        continue  # schon in fruehrer Nacht vorgeschlagen -- kein neuer Aufruf noetig
                    aufrufe += 1  # Kandidatenmessung = 1 Aufruf (s. Moduldoc-Begruendung Budget)
                    task, zahl = pk3._task_kombiniert_ablenker(s1, m1, s2, m2, [a1, a2])
                    kandidaten.append({
                        "kennung": kennung, "kategorie": "kombiniert_ablenker",
                        "task": task, "erwartete_zahl": zahl,
                        "ziel_slugs": [s1, s2], "ablenker_slugs": [a1, a2],
                        "fundstelle": ("pruefkorpus_v3.py::_task_kombiniert_ablenker "
                                       f"(Muster wie v3-39/v3-40); Anlass: runs/pruefkorpus_v3.json "
                                       f"2026-08-07, Kategorie kombiniert_ablenker 0/2 bestanden"),
                    })
    return kandidaten, aufrufe


def _bereits_vorgeschlagen(vorlage_pfad: Path) -> set[str]:
    """Kennungen aus fruehern Laeufen (persistiert in vorlage_pfad.with_suffix
    '.jsonl'), damit aufeinanderfolgende Naechte sich nicht wiederholen."""
    pfad = vorlage_pfad.with_suffix(".jsonl")
    if not pfad.exists():
        return set()
    out = set()
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        if zeile.strip():
            out.add(json.loads(zeile)["kennung"])
    return out


def _merke_vorgeschlagen(kandidaten: list[dict], vorlage_pfad: Path) -> None:
    pfad = vorlage_pfad.with_suffix(".jsonl")
    with pfad.open("a", encoding="utf-8") as f:
        for k in kandidaten:
            f.write(json.dumps({"kennung": k["kennung"]}, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Vorlage bauen: Messungen mit Fundstelle, gedeckelt, Abschnitt ausdruecklich.

def _vorlage_text(kandidaten: list[dict], deckel: int, aufrufe: int, budget: int) -> str:
    gezeigt = kandidaten[:deckel]
    lines = [
        "<nachtlaeufer-vorlage>",
        f"Beobachtung, nicht Entscheidung. {aufrufe} von {budget} moeglichen Aufrufen verwendet.",
        f"Aufgabe: Vorschlaege fuer Pruefkategorie 'kombiniert_ablenker' "
        f"(Fundstelle: runs/pruefkorpus_v3.json 2026-08-07, 0 von 2 bestanden -- einzige "
        f"scheiternde Kategorie unter 42 Faellen).",
    ]
    for k in gezeigt:
        lines.append(
            f"- [{k['kennung']}] task={k['task']!r} erwartete_zahl={k['erwartete_zahl']} "
            f"ziel={k['ziel_slugs']} ablenker={k['ablenker_slugs']} ({k['fundstelle']})"
        )
    if len(kandidaten) > deckel:
        lines.append(f"… {len(kandidaten) - deckel} von {len(kandidaten)} weitere nicht gezeigt (Deckel {deckel}).")
    lines.append("Aufnahme in pruefkorpus_v3.py erst nach Freigabe -- der Laeufer entscheidet nicht.")
    lines.append("</nachtlaeufer-vorlage>")
    return "\n".join(lines)


def lauf(db_path: Path = DB_PATH, vorlage_pfad: Path = VORLAGE_PFAD) -> str | None:
    """Fuehrt einen Beobachtungslauf aus, schreibt die Vorlage-Datei.
    Rueckgabe None, wenn der Laeufer aus ist (dann wird auch nichts geschrieben)."""
    conn = _ro_connect(db_path)
    try:
        cfg = _config(conn)
    finally:
        conn.close()
    if cfg["nachtlaeufer_aktiv"] != "ein":
        return None
    budget = int(cfg["nachtlaeufer_budget"])
    deckel = int(cfg["nachtlaeufer_deckel"])
    kandidaten, aufrufe = _erzeuge_kandidaten(budget, _bereits_vorgeschlagen(vorlage_pfad))
    text = _vorlage_text(kandidaten, deckel, aufrufe, budget)
    vorlage_pfad.write_text(text, encoding="utf-8")
    if kandidaten:
        _merke_vorgeschlagen(kandidaten, vorlage_pfad)
    return text


def _sitzungsstart(vorlage_pfad: Path = VORLAGE_PFAD, db_path: Path = DB_PATH) -> str | None:
    """Hook-Modus: druckt die vorliegende Vorlage genau einmal, nur wenn
    aktiv. Danach als 'vorgelegt' markiert (umbenannt), kein Rauschen bei
    jedem weiteren Sitzungsstart bis zum naechsten --lauf."""
    if not vorlage_pfad.exists():
        return None
    try:
        conn = _ro_connect(db_path)
        try:
            aktiv = _config(conn)["nachtlaeufer_aktiv"] == "ein"
        finally:
            conn.close()
    except sqlite3.OperationalError:
        aktiv = False
    if not aktiv:
        return None
    text = vorlage_pfad.read_text(encoding="utf-8")
    vorlage_pfad.rename(vorlage_pfad.with_suffix(".vorgelegt.md"))
    return text


def main() -> None:
    if "--lauf" in sys.argv[1:]:
        out = lauf()
        if out:
            print(out)
        return
    out = _sitzungsstart()
    if out:
        print(out)


# ---------------------------------------------------------------------------

def _selbsttest() -> None:
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        db_path = tmp / "wissenstest.db"
        schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
        conn = sqlite3.connect(str(db_path))
        conn.executescript(schema)
        conn.commit()
        conn.close()

        # Abnahme 1: nur-lesender Zugang -- Schreibversuch scheitert.
        ro = _ro_connect(db_path)
        try:
            ro.execute("INSERT INTO knowledge_config (key, value, updated_at) VALUES ('x','y','z')")
            raise AssertionError("Schreibversuch auf nur-lesendem Zugang haette scheitern muessen")
        except sqlite3.OperationalError as e:
            assert "readonly" in str(e), f"unerwartete Fehlermeldung: {e}"
            print(f"Abnahme 1 (nur lesend): {e}")
        finally:
            ro.close()

        # Abnahme 2: Laeufer AUS (Vorgabe) -> lauf() schreibt nichts, Hook druckt nichts.
        vorlage = tmp / "vorlage.md"
        assert lauf(db_path, vorlage) is None
        assert not vorlage.exists()
        assert _sitzungsstart(vorlage, db_path) is None
        print("Abnahme 2 (aus, Vorgabe): kein Druck, keine Datei.")

        # Aktivieren.
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT OR REPLACE INTO knowledge_config (key, value, updated_at) VALUES "
            "('nachtlaeufer_aktiv','ein','t'), ('nachtlaeufer_budget','3','t'), "
            "('nachtlaeufer_deckel','2','t')"
        )
        conn.commit()
        conn.close()

        # nachtlaeufer_vorlage.jsonl / pruefkorpus_v3 muessen im Pfad liegen.
        sys.path.insert(0, str(SHARED_KNOWLEDGE))

        # Abnahme 4: Budget wirkt.
        text = lauf(db_path, vorlage)
        assert text is not None
        assert "3 von 3" in text, text
        print("Abnahme 4 (Budget=3): genau 3 Aufrufe -- 'gezeigt in Vorlage: 3 von 3'.")

        # Abnahme 3: gedeckelt (Deckel=2 < 3 Kandidaten) + ausdruecklicher Hinweis.
        assert "1 von 3 weitere nicht gezeigt" in text, text
        assert vorlage.exists()

        gedruckt = _sitzungsstart(vorlage, db_path)
        assert gedruckt == text
        assert not vorlage.exists()  # als vorgelegt markiert/umbenannt
        assert vorlage.with_suffix(".vorgelegt.md").exists()
        print("Abnahme 3 (an, Vorlage vorhanden): Sitzungsstart druckt sie einmal, danach still.")

        # Kein zweites Drucken ohne neuen Lauf.
        assert _sitzungsstart(vorlage, db_path) is None

    print("Selbsttest gruen.")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--selbsttest"]:
        try:
            _selbsttest()
        except AssertionError as e:
            print(f"Selbsttest FEHLGESCHLAGEN: {e}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)
    main()
