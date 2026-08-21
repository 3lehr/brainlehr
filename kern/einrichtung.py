#!/usr/bin/env python3
"""Erststart im Chat -- der Einrichtungsassistent (BDW-P11, Auftrag C).

DIE BAUFORM ERGIBT SICH AUS DER BAUART: brainlehr ist ein MCP-Server, also
laeuft die Einrichtung IM Chat und nicht in einem zweiten Programm. Es gibt
kein Fenster, keinen Installer und keine zweite Oberflaeche, die gepflegt
werden muesste -- nur ein Werkzeug (`einrichtung_starten`), das gegen einen
LEEREN Bestand von selbst anspringt.

DER ANLASS IST GEMESSEN, nicht vermutet: Eine Anmeldung kostete einmal ueber
eine Stunde und vier Fehlversuche, und von vier eingetragenen Ausweisen liess
sich am 2026-08-19 nur einer aufloesen.

DIE HAERTESTE REGEL HIER IST EINE NEGATIVE: Auf einem GEWACHSENEN Bestand
springt nichts von selbst an, und ohne ausdrueckliche Bestaetigung wird nichts
ueberschrieben. Das ist die Haelfte, die ein Labor nie faehrt -- ein Testlauf
startet immer frisch, der Betrieb nie (L-8bde89 / L-96db3e, beide Richtungen
am eigenen Haus belegt).

VIER FRAGEN, mehr nicht (C1):
  profil            einzelplatz | unternehmen        -> kern/betriebsprofil.py
  sprache           Sprache des eigenen Materials    -> kern/spracherkennung.py
  einbettungsdienst erreichbar? welches Modell?      -> kern/embeddings.py
  kataloge          welche Nachschlagewerke sollen mit?

Die dritte ist die, die sonst still ausfaellt: ohne erreichbaren Dienst
entstehen Eintraege OHNE Vektor und sind ueber die Bedeutungssuche
unauffindbar, ohne dass ein Fehler erschiene -- am 2026-08-20 dreizehnmal
passiert. Geprueft wird mit der vorhandenen Aussetzer-Sicherung aus
kern/embeddings.py und dem Melder melder/einbettungsaussetzer.py, nicht mit
einer zweiten Pruefung.

DIE GATTUNG IST DER GANZE PUNKT BEI DEN KATALOGEN: Sie werden als
`nachschlagewerk` eingelesen, nicht als `arbeitsbestand` -- sonst verduennen
951 fremde Controls die eigene Trefferquote. Geschrieben wird ueber den EINEN
Importweg in kern/fremdimport.py, damit die Herkunftspruefung aus BDW-P12
nicht umgangen werden kann.

Aufruf:
    python3 kern/einrichtung.py --lage
    python3 kern/einrichtung.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                             ("kern", "haken", "melder")]

import argparse  # noqa: E402
import json  # noqa: E402
import subprocess  # noqa: E402
import urllib.request  # noqa: E402
from configparser import ConfigParser  # noqa: E402
from datetime import datetime  # noqa: E402
from pathlib import Path  # noqa: E402

import betriebsprofil  # noqa: E402
import einbettungsaussetzer  # noqa: E402
import embeddings  # noqa: E402
import fremdimport  # noqa: E402
import ort  # noqa: E402
import speicher  # noqa: E402
import spracherkennung  # noqa: E402

WURZEL = _w

SCHLUESSEL_FERTIG = "einrichtung_abgeschlossen"
SCHLUESSEL_SPRACHE = "sprache_eigenes_material"


def _vorgabe_db() -> Path:
    """Die Betriebsdatenbank -- ueber haken/ort.py erfragt, nie getippt."""
    return ort.DB


# --- C2: Kataloge, vorgeschlagen statt versteckt -------------------------
# Was heute schon vorliegt und nur niemand anbietet. Der Umfang wird
# GEZAEHLT, wenn die Datei da ist, nicht aus dem Plan abgeschrieben -- eine
# hinterlegte Zahl ist ab der ersten Aktualisierung des Katalogs falsch und
# wird trotzdem geglaubt.

def _bsi_datei() -> Path:
    return WURZEL / "bsi-dev-profile.json"


def _wcag_datei() -> Path:
    return Path.home() / ".claude" / "regeln" / "wcag.md"


def _bsi_submodul_git_url() -> str | None:
    """Die eingetragene remote-URL des abgeschalteten Submoduls -- NICHT
    geraten, sondern gelesen. `.git_disabled/config` ist der Name, den das
    Abschalten hinterlassen hat; ein normal aktives Submodul haette
    `.git/config`."""
    wurzel = WURZEL / "bsi-stand-der-technik"
    for kandidat in (wurzel / ".git_disabled" / "config", wurzel / ".git" / "config"):
        if not kandidat.exists():
            continue
        cfg = ConfigParser()
        try:
            cfg.read(kandidat, encoding="utf-8")
            return cfg.get('remote "origin"', "url")
        except Exception:
            continue
    return None


def kataloge(db: Path | str | None = None) -> list[dict]:
    """Was zum Mitnehmen bereitliegt, mit gemessenem Umfang und dem Hinweis,
    was davon schon im Bestand steht.

    JEDER Eintrag traegt zusaetzlich `quelle` -- WOHER er kaeme, falls er noch
    fehlt. Reines Lesen lokaler Dateien, KEIN Netzzugriff -- das bleibt
    `katalog_holen()` vorbehalten, das nur auf ausdruecklichen Aufruf laeuft."""
    raus = []

    bsi = _bsi_datei()
    umfang = None
    if bsi.exists():
        try:
            umfang = len(json.loads(bsi.read_text(encoding="utf-8"))["controls"])
        except (json.JSONDecodeError, KeyError, OSError):
            umfang = None
    bsi_url = _bsi_submodul_git_url()
    raus.append({"name": "bsi", "titel": "BSI Stand der Technik (Dev-Profil)",
                 "gattung": "nachschlagewerk", "liegt": str(bsi),
                 "vorhanden": bsi.exists() and umfang is not None,
                 "umfang": umfang, "wurzel": "/bsi-sdt",
                 "quelle": ({"art": "git", "ort": bsi_url,
                            "lizenz": "CC BY-SA 4.0 (siehe LICENSE im Submodul)",
                            "hinweis": "abgeschaltetes Submodul bsi-stand-der-technik/"
                                       ", remote-URL aus .git_disabled/config gelesen"}
                           if bsi_url else
                           {"art": "keine", "ort": None, "lizenz": "ungeprueft",
                            "hinweis": "keine remote-URL im Submodul gefunden "
                                       "(.git_disabled/config bzw. .git/config fehlt "
                                       "oder ohne [remote \"origin\"])"})})

    raus.append({"name": "nasa-llis", "titel": "NASA Lessons Learned (LLIS)",
                 "gattung": "nachschlagewerk", "liegt": "bereits im Bestand",
                 "vorhanden": False, "umfang": None, "wurzel": "/nasa-llis",
                 "hinweis": "keine lokale Quelldatei -- der Bestand traegt ihn "
                            "bereits, ein Nachladen gaebe es nur ueber das "
                            "fremde Repository, aus dem er einmal kam",
                 "quelle": {"art": "keine", "ort": None, "lizenz": "ungeprueft",
                            "hinweis": "Herkunft steht je Knoten in "
                                       "knowledge_nodes.source, Form "
                                       "'https://nen.nasa.gov/web/11/viewall/-/"
                                       "viewall/<id> (NASA LLIS LessonId <id>)' -- "
                                       "1638 einzelne Lehren, kein Sammel-Endpunkt. "
                                       "Der Bestand traegt sie bereits vollstaendig, "
                                       "es gibt nichts nachzuladen."}})

    wcag = _wcag_datei()
    raus.append({"name": "wcag", "titel": "WCAG 2.2 AA (Regeltext)",
                 "gattung": "nachschlagewerk", "liegt": str(wcag),
                 "vorhanden": wcag.exists(), "umfang": None,
                 "wurzel": "/wcag-2-2",
                 "quelle": {"art": "keine", "ort": None, "lizenz": "ungeprueft",
                            "hinweis": "keine ausliefertbare Quelle -- die Datei "
                                       "ist Eigentum des Betreibers. Der Regeltext "
                                       "stammt von w3.org (WCAG 2.2); wer ihn "
                                       "braucht, muss ihn selbst beibringen."}})

    if db is not None:
        with speicher.lesen(db) as conn:
            for k in raus:
                k["schon_im_bestand"] = conn.execute(
                    "SELECT COUNT(*) FROM knowledge_nodes WHERE path = ? "
                    "OR path LIKE ?", (k["wurzel"], k["wurzel"] + "/%")
                ).fetchone()[0]
    return raus


def _bsi_eintraege() -> list[dict]:
    controls = json.loads(_bsi_datei().read_text(encoding="utf-8"))["controls"]
    return [{"kennung": c.get("id") or "", "titel": f"{c.get('id','')} {c.get('title','')}".strip(),
             "text": c.get("prose") or "",
             "tags": [t for t in ("bsi", c.get("group"), c.get("sec_level")) if t]}
            for c in controls]


def _wcag_eintraege() -> list[dict]:
    text = _wcag_datei().read_text(encoding="utf-8")
    # An den Ueberschriften geteilt statt als ein Klotz: ein Regeltext, den
    # man nur ganz oder gar nicht lesen kann, ist beim Nachschlagen wertlos.
    teile, aktuell = [], []
    for zeile in text.splitlines():
        if zeile.startswith("## ") and aktuell:
            teile.append(aktuell)
            aktuell = []
        aktuell.append(zeile)
    if aktuell:
        teile.append(aktuell)
    raus = []
    for block in teile:
        kopf = block[0].lstrip("#").strip() or "WCAG"
        raus.append({"kennung": kopf, "titel": kopf, "text": "\n".join(block).strip(),
                     "tags": ["wcag", "barrierefreiheit"]})
    return raus


def katalog_einlesen(name: str, db: Path | str | None = None,
                     gattung: str = "nachschlagewerk") -> dict:
    """Liest einen der vorgeschlagenen Kataloge ein -- ueber den EINEN
    Importweg aus kern/fremdimport.py, samt Herkunftspruefung (BDW-P12)."""
    if db is None:
        db = _vorgabe_db()
    eintrag = next((k for k in kataloge() if k["name"] == name), None)
    if eintrag is None:
        raise ValueError(f"unbekannter Katalog: {name!r} "
                         f"(bekannt: {[k['name'] for k in kataloge()]})")
    if not eintrag["vorhanden"]:
        return {"knoten": 0, "katalog": name, "uebersprungen": True,
                "hinweis": eintrag.get("hinweis",
                                        f"{eintrag['liegt']} liegt nicht vor")}

    if name == "bsi":
        eintraege, weg, projekt, norm_art = (
            _bsi_eintraege(), _bsi_datei().name, "bsi-sdt", None)
    elif name == "wcag":
        # source enthaelt 'wcag' -- der Trigger knowledge_nodes_norm_art_pflicht_bi
        # verlangt dann eine Normart. 'sollen' ist die ehrliche: WCAG 2.2 AA ist
        # eine Leitlinie, keine Messaussage und keine Erlaubnis.
        eintraege, weg, projekt, norm_art = (
            _wcag_eintraege(), str(_wcag_datei()), "wcag", "sollen")
    else:
        return {"knoten": 0, "katalog": name, "uebersprungen": True,
                "hinweis": eintrag.get("hinweis", "kein Einleseweg hinterlegt")}

    ergebnis = fremdimport.eintragen(
        eintraege, quelle=fremdimport.importherkunft(weg),
        projekt=projekt, wurzel=eintrag["wurzel"], db=db, gattung=gattung,
        norm_art=norm_art, titel_wurzel=eintrag["titel"])
    ergebnis["katalog"] = name
    return ergebnis


def katalog_holen(name: str, ziel: Path | str | None = None) -> dict:
    """Holt einen Katalog, dessen quelle.art nicht 'keine' ist, in ein
    lokales Verzeichnis. NETZZUGRIFF NUR HIER -- kataloge() selbst bleibt
    davon frei.

    'keine' wird NICHT geraten oder umgangen, sondern ehrlich als
    `geholt: False` mit dem hinterlegten Hinweis zurueckgegeben."""
    eintrag = next((k for k in kataloge() if k["name"] == name), None)
    if eintrag is None:
        raise ValueError(f"unbekannter Katalog: {name!r} "
                         f"(bekannt: {[k['name'] for k in kataloge()]})")
    quelle = eintrag["quelle"]
    if quelle["art"] == "keine":
        return {"katalog": name, "geholt": False, "hinweis": quelle["hinweis"]}

    ziel = Path(ziel) if ziel is not None else WURZEL / "katalog-holen" / name
    ziel.parent.mkdir(parents=True, exist_ok=True)

    if quelle["art"] == "git":
        if ziel.exists():
            lauf = subprocess.run(["git", "-C", str(ziel), "pull", "--ff-only"],
                                  capture_output=True, text=True)
        else:
            lauf = subprocess.run(["git", "clone", "--depth", "1",
                                   quelle["ort"], str(ziel)],
                                  capture_output=True, text=True)
        return {"katalog": name, "geholt": lauf.returncode == 0, "ziel": str(ziel),
                "lizenz": quelle["lizenz"],
                "hinweis": lauf.stdout.strip() or lauf.stderr.strip()}

    if quelle["art"] == "http":
        with urllib.request.urlopen(quelle["ort"]) as antwort:
            ziel.write_bytes(antwort.read())
        return {"katalog": name, "geholt": True, "ziel": str(ziel),
                "lizenz": quelle["lizenz"], "hinweis": f"heruntergeladen von {quelle['ort']}"}

    raise ValueError(f"unbekannte quelle.art {quelle['art']!r} bei Katalog {name!r}")


# --- C1, dritte Frage: der Einbettungsdienst -----------------------------

def einbettungsdienst(base_url: str = "") -> dict:
    """Erreichbar? Welches Modell? -- gefahren, nicht angenommen.

    Benutzt embeddings.embed_text() mit seiner Aussetzer-Sicherung und den
    Melder melder/einbettungsaussetzer.py. Keine zweite Pruefung: eine
    zweite haette einen zweiten Begriff von 'erreichbar'."""
    vektor = embeddings.embed_text("Probe der Einbettung", base_url=base_url)
    return {
        "erreichbar": vektor is not None,
        "modell": embeddings.DEFAULT_EMBED_MODEL,
        "dienst": (base_url or embeddings.DEFAULT_OLLAMA_URL),
        "dimension": len(vektor) if vektor else None,
        "aussetzer": einbettungsaussetzer.melde(),
        "folge_wenn_aus": ("Eintraege entstehen OHNE Vektor und sind ueber die "
                           "Bedeutungssuche unauffindbar, ohne dass ein Fehler "
                           "erscheint -- am 2026-08-20 dreizehnmal passiert."),
    }


def sprachvorschlag(db: Path | str | None = None) -> str | None:
    """Sprache des eigenen Materials, aus dem Arbeitsbestand ERKANNT.
    None heisst nicht erkannt -- geraten wird nichts (BDW-P10)."""
    with speicher.lesen(db) as conn:
        zeilen = conn.execute(
            "SELECT title, summary FROM knowledge_nodes "
            "WHERE gattung = 'arbeitsbestand' ORDER BY updated_at DESC LIMIT 50"
        ).fetchall()
    if not zeilen:
        return None
    return spracherkennung.erkenne(
        " ".join(f"{r['title']} {r['summary']}" for r in zeilen))


# --- Lage und Durchlauf --------------------------------------------------

def _konfig(conn, schluessel: str) -> str | None:
    row = conn.execute("SELECT value FROM knowledge_config WHERE key = ?",
                       (schluessel,)).fetchone()
    return row["value"] if row else None


def _konfig_setzen(conn, schluessel: str, wert: str) -> None:
    conn.execute(
        "INSERT INTO knowledge_config (key, value, updated_at) "
        "VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now')) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
        "updated_at = excluded.updated_at", (schluessel, wert))


def lage(db: Path | str | None = None) -> dict:
    """Was ist hier los, und muss der Assistent anspringen?

    `springt_an` ist die einzige Stelle, die das entscheidet -- leer UND noch
    nicht eingerichtet. Ein gewachsener Bestand faellt hier heraus, und zwar
    ohne dass ein Aufrufer daran denken muss."""
    if db is None:
        db = _vorgabe_db()
    with speicher.lesen(db) as conn:
        knoten = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        lehren = conn.execute("SELECT COUNT(*) FROM lessons_learned").fetchone()[0]
        fertig = _konfig(conn, SCHLUESSEL_FERTIG)
        sprache = _konfig(conn, SCHLUESSEL_SPRACHE)
    leer = (knoten == 0 and lehren == 0)
    profil = betriebsprofil.profil(db)
    dienst = einbettungsdienst()
    katalogliste = kataloge(db)

    return {
        "bestand_leer": leer,
        "eingerichtet": fertig is not None,
        "eingerichtet_am": fertig,
        "springt_an": leer and fertig is None,
        "knoten": knoten,
        "lehren": lehren,
        "profil": profil,
        "sprache": sprache,
        "einbettung": dienst,
        "kataloge": katalogliste,
        "fragen": [
            {"feld": "profil",
             "frage": "Einzelplatz oder Unternehmen?",
             "auswahl": list(betriebsprofil.PROFILE),
             "vorschlag": betriebsprofil.EINZELPLATZ,
             "hinweis": "einzelplatz ist der Auslieferungszustand; der Wechsel "
                        "zu unternehmen ist spaeter moeglich und braucht dann "
                        "einen benannten Mandanten"},
            {"feld": "sprache",
             "frage": "In welcher Sprache ist Ihr eigenes Material?",
             "auswahl": ["de", "en"],
             "vorschlag": sprache or sprachvorschlag(db),
             "hinweis": "wird nur ausgezeichnet, nie uebersetzt -- eine "
                        "Oberflaeche braucht sie fuer WCAG 3.1.2"},
            {"feld": "einbettungsdienst",
             "frage": f"Einbettungsdienst {dienst['dienst']} erreichbar?",
             "auswahl": None,
             "vorschlag": dienst["modell"],
             "hinweis": ("erreichbar" if dienst["erreichbar"]
                         else "NICHT erreichbar -- " + dienst["folge_wenn_aus"])},
            {"feld": "kataloge",
             "frage": "Welche Nachschlagewerke sollen mit?",
             "auswahl": [k["name"] for k in katalogliste if k["vorhanden"]],
             "vorschlag": [k["name"] for k in katalogliste if k["vorhanden"]],
             "hinweis": "werden als Gattung nachschlagewerk eingelesen und "
                        "verduennen die eigene Trefferquote deshalb nicht"},
        ],
    }


def durchlaufen(profil: str | None = None, sprache: str | None = None,
                kataloge: tuple | list = (), mandant: str | None = None,
                db: Path | str | None = None, bestaetigt: bool = False) -> dict:
    """Der Durchlauf. Ohne Antworten wird nur gefragt.

    DIE SPERRE: Auf einem gewachsenen oder bereits eingerichteten Bestand
    passiert ohne `bestaetigt=True` NICHTS -- kein Profilwechsel, keine
    Sprache, kein Katalog. Zurueckgegeben wird `geaendert: false` samt
    Hinweis, nicht ein Fehler: der Aufrufer soll die Lage sehen, nicht
    stolpern."""
    if db is None:
        db = _vorgabe_db()
    stand = lage(db)
    antworten = bool(profil or sprache or kataloge)

    if not antworten:
        return {"geaendert": False, "lage": stand, "fragen": stand["fragen"],
                "hinweis": "keine Antworten uebergeben -- es wurde nur gefragt"}

    if not stand["springt_an"] and not bestaetigt:
        return {
            "geaendert": False, "lage": stand, "fragen": stand["fragen"],
            "hinweis": (
                "Bestand ist nicht leer oder bereits eingerichtet "
                f"({stand['knoten']} Knoten, {stand['lehren']} Lehren, Profil "
                f"{stand['profil']}). Es wurde NICHTS geaendert. Wer die "
                "Einrichtung hier trotzdem fahren will, ruft erneut mit "
                "bestaetigt=true auf -- eine Einrichtung ueber Bestand "
                "ueberschreibt Profil und Sprache."),
        }

    getan: list[str] = []
    if profil:
        ergebnis = betriebsprofil.wechsel(profil, mandant=mandant, db=db)
        getan.append(f"Profil {ergebnis['profil']} (Mandant {ergebnis['mandant']}, "
                     f"Sicherung {ergebnis['sicherung']})")
    if sprache:
        with speicher.schreiben(db) as conn:
            _konfig_setzen(conn, SCHLUESSEL_SPRACHE, sprache)
        getan.append(f"Sprache {sprache}")

    katalogergebnisse = []
    for name in kataloge or ():
        katalogergebnisse.append(katalog_einlesen(name, db=db))
        getan.append(f"Katalog {name}: {katalogergebnisse[-1]['knoten']} Knoten")

    with speicher.schreiben(db) as conn:
        _konfig_setzen(conn, SCHLUESSEL_FERTIG,
                       datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"))

    nachher = lage(db)
    return {"geaendert": True, "profil": nachher["profil"],
            "sprache": nachher["sprache"], "kataloge": katalogergebnisse,
            "getan": getan, "lage": nachher,
            "hinweis": "Einrichtung abgeschlossen -- der Bestand ist benutzbar."}


def _selftest() -> None:
    # Nur das, was ohne Bestand pruefbar ist; die Abnahme liegt in
    # tests/test_einrichtung.py (beide Ausgangszustaende, Negativfaelle).
    namen = {k["name"] for k in kataloge()}
    assert {"bsi", "nasa-llis", "wcag"} <= namen, namen
    for k in kataloge():
        assert k["gattung"] == "nachschlagewerk", k
        assert {"art", "ort", "lizenz", "hinweis"} <= set(k["quelle"]), k
    assert katalog_holen("wcag")["geholt"] is False
    if _bsi_datei().exists():
        assert len(_bsi_eintraege()) > 0
    if _wcag_datei().exists():
        assert len(_wcag_eintraege()) > 0
    print("einrichtung: alle Proben bestanden")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lage", action="store_true")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        _selftest()
        return
    print(json.dumps(lage(), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
