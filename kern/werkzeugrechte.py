#!/usr/bin/env python3
"""werkzeugrechte.py -- B4.3: Durchsetzung am Aufruf, nicht an der Ankuendigung.

Plan: docs/PLAN_B4_AUSWEIS_2026-08-09.md

DIE LUECKE, die der Quelltext selbst benennt. In knowledge_mcp_server.py steht
ueber BEGOD_KNOWLEDGE_PROFIL woertlich:

    "beschraenkt nur die ANKUENDIGUNG (tools/list), nicht den Aufruf:
     tools/call bedient jedes Werkzeug in TOOLS weiter, egal ob es hier
     gelistet wurde. Kein Autorisierungsmechanismus."

Ein nicht angekuendigtes Werkzeug ist also trotzdem aufrufbar. Diese Datei
liefert die fehlende Pruefung -- an EINER Stelle, durch die jeder Werkzeugaufruf
laeuft. Nicht je Werkzeug: das ist die Fehlklasse aus L-44a838, drei Umgehungen
desselben Choke-Points in einer Woche.

EIGENES MODUL statt Ergaenzung im Server: knowledge_mcp_server.py hat ueber 5000
Zeilen, die Monolith-Bremse ist aktiv. Dort steht nur der Aufruf.

ZWEI STUFEN, und die Vorgabe ist bewusst die schwaechere:

  weich (Vorgabe) -- ein UNbeglaubigter Aufrufer darf alles, wie bisher. Ein
      BEGLAUBIGTER wird an seinen Rollen gemessen. Damit bricht nichts: die
      lokalen Skripte, der ChatGPT-Zugang und jede Sitzung ohne Ausweis laufen
      unveraendert weiter.
  streng -- ohne Ausweis geht nichts Schreibendes mehr.

DAS MUSS MAN EHRLICH SAGEN: 'weich' ist KEIN Schutz. Wer keinen Ausweis vorlegt,
hat weiterhin vollen Zugriff -- genau wie heute. Der Gewinn ist, dass ab jetzt
ein Ausweis WIRKT (ein Leser kann nicht mehr schreiben) und dass der Schalter
existiert. Der Schutz entsteht erst mit 'streng', und dieser Schritt gehoert dem
Betreiber, weil er den Betrieb betrifft: BRAINLEHR_DURCHSETZUNG=streng.

VORGABE IST DENY: ein Werkzeug ohne Eintrag in RECHTE gilt als gesperrt, nicht
als frei. Sonst waere jedes kuenftig hinzugefuegte Werkzeug automatisch offen --
und niemand merkt es, weil nichts fehlschlaegt.

FEHLKLASSE: ein Aufrufer erhaelt ein Werkzeug, das seine Rolle nicht traegt.
PREIS EINES FEHLALARMS: ein beglaubigter Aufrufer wird abgewiesen und muss eine
Rolle nachtragen -- laut und behebbar. Der umgekehrte Fehler ist still.

Aufruf:
    python3 werkzeugrechte.py --selftest
    python3 werkzeugrechte.py --liste
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

import os
import sys
from pathlib import Path

sys.path.insert(0, str(_w))
import ausweis  # noqa: E402

ENV_DURCHSETZUNG = "BRAINLEHR_DURCHSETZUNG"

# Werkzeug -> benoetigtes Recht (modul:aktion). Der BEZUG (:own/:published)
# steht bewusst NICHT hier: er haengt am einzelnen Datensatz, nicht am Werkzeug,
# und wird in B4.4 im Handler ausgewertet.
# Das einzige Werkzeug OHNE Rechtebedarf. Kein Versehen, sondern die einzige
# Stelle, an der die Deny-Vorgabe nicht gelten darf: wer sich anmeldet, hat noch
# keinen Ausweis. Die Berechtigung ist die PIN, und die hat ein Mensch
# ausgestellt, der einbuergern durfte.
OHNE_RECHT = frozenset({"knowledge_anmelden"})

RECHTE: dict[str, str] = {
    # lesen
    "knowledge_search": "wissen:lesen",
    "knowledge_read": "wissen:lesen",
    "knowledge_browse": "wissen:lesen",
    "knowledge_stats": "wissen:lesen",
    "knowledge_trust_score": "wissen:lesen",
    "knowledge_modell": "wissen:lesen",
    "knowledge_sitzung": "wissen:lesen",
    "kettenerklaerung_erklaeren": "wissen:lesen",
    "lesson_query": "lehre:lesen",
    "knowledge_relation_list": "kante:lesen",
    "annahme_liste": "annahme:lesen",
    "prompt_invarianz_planen": "wissen:lesen",
    "prompt_invarianz_pruefen": "wissen:lesen",
    "session_checkpoint_lesen": "wissen:lesen",
    # schreiben
    "knowledge_add": "wissen:schreiben",
    "knowledge_update": "wissen:schreiben",
    "knowledge_freigeben": "wissen:schreiben",
    "knowledge_zurueckziehen": "wissen:schreiben",
    "lesson_record": "lehre:schreiben",
    "lesson_update": "lehre:schreiben",
    "knowledge_relation_add": "kante:schreiben",
    "knowledge_relation_update": "kante:schreiben",
    "knowledge_relation_remove": "kante:schreiben",
    "annahme_erfassen": "annahme:schreiben",
    "annahme_entscheiden": "annahme:schreiben",
    "session_checkpoint_setzen": "wissen:schreiben",
    "session_checkpoint_schliessen": "wissen:schreiben",
    # verwaltend -- laeuft ueber den ganzen Bestand, darum eigene Aktion
    "freigabe_setzen": "verwaltung:schreiben",
    "kurator_lauf": "verwaltung:schreiben",
    "katalog_holen": "verwaltung:schreiben",  # Netzzugriff + Schreiben aufs Dateisystem
}

# Welche Aktionen als schreibend gelten -- gebraucht fuer die Stufe 'streng'.
_SCHREIBEND = ("schreiben",)


def stufe() -> str:
    """Unbekannter Wert faellt auf 'weich' zurueck, mit Meldung: ein Tippfehler
    in der Umgebungsvariable darf nicht stillschweigend die Durchsetzung
    abschalten -- aber auch nicht den Betrieb anhalten."""
    roh = (os.environ.get(ENV_DURCHSETZUNG) or "weich").strip().lower()
    if roh in ("weich", "streng"):
        return roh
    print(f"werkzeugrechte: {ENV_DURCHSETZUNG}={roh!r} unbekannt — 'weich'",
          file=sys.stderr)
    return "weich"


def erlaubt(werkzeug: str, *, ausw: ausweis.Ausweis | None = None,
            durchsetzung: str | None = None) -> tuple[bool, str]:
    """(darf, grund). Der Grund ist immer gefuellt, auch bei Erlaubnis --
    er wandert ins Protokoll, damit hinterher nachvollziehbar ist, WARUM
    etwas durchging, nicht nur dass es durchging."""
    ausw = ausw if ausw is not None else ausweis.loese_auf()
    durchsetzung = durchsetzung or stufe()

    if werkzeug in OHNE_RECHT:
        return True, f"anmeldung_ohne_ausweis:{werkzeug}"

    recht = RECHTE.get(werkzeug)
    if recht is None:
        # Vorgabe deny. Gilt auch fuer unbeglaubigte Aufrufer: ein Werkzeug,
        # das niemand zugeordnet hat, ist ein Versehen, kein Freibrief.
        return False, f"werkzeug_ohne_recht:{werkzeug}"

    if not ausw.beglaubigt:
        if durchsetzung == "streng" and recht.split(":")[1] in _SCHREIBEND:
            return False, f"kein_ausweis_streng:{recht}"
        return True, f"unbeglaubigt_weich:{recht}"

    bezug = ausweis.bezug_fuer(ausw, recht)
    if bezug is None:
        return False, f"rolle_ohne_recht:{recht}"
    return True, f"erlaubt:{recht}:{bezug}"


# --- B4.4: der Bezug -------------------------------------------------------
# Die dritte Stelle eines Rechts (:own, :published) haengt am einzelnen
# DATENSATZ, nicht am Werkzeug -- darum wirkt sie nach dem Aufruf auf das
# Ergebnis, nicht davor auf die Erlaubnis.
#
# WARUM AN EINER STELLE UND NICHT IN DEN HANDLERN: knowledge_search,
# knowledge_read, knowledge_browse und lesson_query liefern alle Treffer.
# Vier Filter waeren vier Gelegenheiten, einen zu vergessen -- dieselbe
# Fehlklasse wie bei der Erlaubnispruefung (L-44a838).
#
# WAS ES KOSTET, ehrlich: der Filter braucht Felder, die im Ergebnis nicht
# stehen (freigabe, actor). Er schlaegt sie mit EINEM Query fuer alle Treffer
# nach, nicht mit einem je Treffer.

# Welche Ergebnisliste welches Werkzeugs Knoten bzw. Lehren traegt.
_LISTEN = ("results", "nodes", "children", "relations")


def _bezug_pruefen(eintraege: list[dict], bezug: str, ausw: ausweis.Ausweis,
                   db_pfad) -> list[dict]:
    """Behaelt nur, was der Bezug zulaesst. 'alle' geht ungefiltert durch."""
    if bezug == "alle" or not eintraege:
        return eintraege

    import sqlite3
    ids = [e.get("id") for e in eintraege if e.get("id")]
    if not ids:
        return eintraege
    platz = ",".join("?" * len(ids))
    conn = sqlite3.connect(f"file:{db_pfad}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        merkmale = {r["id"]: dict(r) for r in conn.execute(
            f"SELECT id, freigabe, actor FROM knowledge_nodes WHERE id IN ({platz})",
            ids)}
        # Lehren tragen dieselben zwei Merkmale, seit die Spalte nachgezogen
        # ist (B4.5-Nachtrag). Eigener Query statt UNION, weil eine DB ohne
        # die Spalte hier scheitern darf, ohne die Knoten mitzureissen: dann
        # bleiben Lehren beim groben Schnitt (kein Merkmal -> nicht sichtbar).
        try:
            merkmale.update({r["id"]: dict(r) for r in conn.execute(
                f"SELECT id, freigabe, actor FROM lessons_learned WHERE id IN ({platz})",
                ids)})
        except sqlite3.OperationalError:
            pass
    except sqlite3.OperationalError:
        return eintraege          # altes Schema ohne freigabe -> nicht filtern
    finally:
        conn.close()

    eigene = ausweis.zugaenge_derselben_person(ausw) if bezug == "own" else frozenset()
    behalten = []
    for e in eintraege:
        m = merkmale.get(e.get("id"))
        if m is None:
            # Kein Knoten -- in der Praxis eine LEHRE. lessons_learned traegt
            # keine freigabe-Spalte (migrate_freigabe.py ging nur ueber
            # knowledge_nodes), der Bezug ist hier also nicht entscheidbar.
            #
            # DENY, NICHT DURCHLASSEN. Die erste Fassung liess durch und
            # markierte nur -- der Koederlauf am 2026-08-10 zeigte sofort, was
            # das heisst: ein Gast sah 5 von 10 Treffern statt 0, allesamt
            # Lehren. Und Lehren sind das DESTILLAT, also gerade die kompakten,
            # merkbaren Aussagen. "published" heisst "nur ausdruecklich
            # Freigegebenes"; was kein Freigabemerkmal tragen KANN, ist nicht
            # freigegeben. Bei "own" gilt dasselbe: was ich nicht als meines
            # belegen kann, ist nicht meines.
            continue
        if bezug == "published" and (m.get("freigabe") or "intern") != "offen":
            continue
        # 'own' meint die PERSON, nicht den Zugang: wer ueber zwei Zugaenge
        # arbeitet (Claude Code und ChatGPT), soll sich nicht selbst aussperren.
        if bezug == "own" and (m.get("actor") or "") not in eigene:
            continue
        behalten.append(e)
    return behalten


def filtere(werkzeug: str, ergebnis, *, ausw: ausweis.Ausweis | None = None,
            db_pfad=None):
    """Wendet den Bezug des Aufrufers auf ein Werkzeugergebnis an.

    Unbeglaubigte Aufrufer werden NICHT gefiltert -- sie haben keine Rollen und
    damit keinen Bezug; ihre Sichtbarkeit regelt die Stufe (weich/streng), nicht
    diese Funktion. Sonst saehe ein Aufrufer ohne Ausweis plotzlich weniger als
    vorher, und das waere der Bruch, den B4.1 ausdruecklich vermeidet."""
    if not isinstance(ergebnis, dict):
        return ergebnis
    ausw = ausw if ausw is not None else ausweis.loese_auf()
    if not ausw.beglaubigt:
        return ergebnis
    recht = RECHTE.get(werkzeug)
    if not recht:
        return ergebnis
    bezug = ausweis.bezug_fuer(ausw, recht)
    if bezug is None or bezug == "alle":
        return ergebnis

    if db_pfad is None:
        import knowledge_mcp_server as kms
        db_pfad = kms.DB_PATH

    gefiltert = dict(ergebnis)
    for schluessel in _LISTEN:
        wert = gefiltert.get(schluessel)
        if isinstance(wert, list):
            vorher = len(wert)
            wert = _bezug_pruefen(wert, bezug, ausw, db_pfad)
            gefiltert[schluessel] = wert
            if len(wert) != vorher:
                # Die Zahl daneben muss mitwandern, sonst behauptet 'count'
                # mehr, als die Liste zeigt.
                if isinstance(gefiltert.get("count"), int):
                    gefiltert["count"] = len(wert)
                gefiltert["gefiltert_nach_bezug"] = bezug
    return gefiltert


def fehlende_zuordnung(werkzeuge) -> list[str]:
    """Welche Werkzeuge haben kein Recht? Fuer den Selbsttest des Servers --
    ohne diese Probe faellt ein neu hinzugefuegtes Werkzeug erst auf, wenn es
    jemand aufruft und abgewiesen wird."""
    return sorted(w for w in werkzeuge if w not in RECHTE and w not in OHNE_RECHT)


def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "a.json"
        # Gruendungsakt, dann buergert der Gruender ein (Einbuergerungsregel).
        G = ausweis.anlegen("gruender", ["betreiber"], art="mensch", pfad=pfad)
        g_leser = ausweis.anlegen("nur-lesen", ["leser"], pfad=pfad, aussteller=G)
        g_schreib = ausweis.anlegen("schreiber1", ["schreiber"], pfad=pfad, aussteller=G)
        L = ausweis.loese_auf(geheimnis=g_leser, pfad=pfad)
        S = ausweis.loese_auf(geheimnis=g_schreib, pfad=pfad)
        U = ausweis.loese_auf("irgendwer", geheimnis=None, pfad=pfad)
        assert not U.beglaubigt

        # --- P3: die Kernprobe. Ein Leser kann nicht schreiben -------------
        darf, grund = erlaubt("knowledge_add", ausw=L)
        assert not darf and grund.startswith("rolle_ohne_recht"), (darf, grund)
        assert erlaubt("knowledge_search", ausw=L)[0]

        # Schreiber darf beides
        assert erlaubt("knowledge_add", ausw=S)[0]
        assert erlaubt("knowledge_search", ausw=S)[0]
        # ... aber nicht verwalten
        assert not erlaubt("kurator_lauf", ausw=S)[0]

        # --- P4: Werkzeug ohne Eintrag ist gesperrt, nicht frei ------------
        for wer in (L, S, U):
            darf, grund = erlaubt("neues_werkzeug_von_morgen", ausw=wer)
            assert not darf and grund.startswith("werkzeug_ohne_recht"), grund

        # --- weich: unbeglaubigt darf alles Zugeordnete -------------------
        for w in ("knowledge_search", "knowledge_add", "kurator_lauf"):
            darf, grund = erlaubt(w, ausw=U, durchsetzung="weich")
            assert darf and grund.startswith("unbeglaubigt_weich"), (w, grund)

        # --- streng: unbeglaubigt darf lesen, nicht schreiben -------------
        assert erlaubt("knowledge_search", ausw=U, durchsetzung="streng")[0]
        for w in ("knowledge_add", "lesson_record", "kurator_lauf"):
            darf, grund = erlaubt(w, ausw=U, durchsetzung="streng")
            assert not darf and grund.startswith("kein_ausweis_streng"), (w, grund)
        # ... ein Ausweis wirkt in 'streng' genauso wie in 'weich'
        assert erlaubt("knowledge_add", ausw=S, durchsetzung="streng")[0]
        assert not erlaubt("knowledge_add", ausw=L, durchsetzung="streng")[0]

        # --- Stufe aus der Umgebung, inkl. Tippfehler ---------------------
        alt = os.environ.get(ENV_DURCHSETZUNG)
        try:
            for wert, erwartet in ((None, "weich"), ("streng", "streng"),
                                   ("STRENG", "streng"), (" weich ", "weich"),
                                   ("scharf", "weich"), ("", "weich")):
                if wert is None:
                    os.environ.pop(ENV_DURCHSETZUNG, None)
                else:
                    os.environ[ENV_DURCHSETZUNG] = wert
                assert stufe() == erwartet, (wert, stufe())
        finally:
            os.environ.pop(ENV_DURCHSETZUNG, None)
            if alt is not None:
                os.environ[ENV_DURCHSETZUNG] = alt

    # --- jedes Werkzeug des Servers hat eine Zuordnung --------------------
    try:
        import knowledge_mcp_server as kms
    except Exception:  # noqa: BLE001 -- Selbsttest laeuft auch ohne Server
        print("werkzeugrechte.py: Selbsttest gruen (ohne Serverabgleich)")
        return
    fehlt = fehlende_zuordnung(kms.TOOLS)
    assert not fehlt, (
        f"Werkzeuge ohne Rechtezuordnung: {fehlt}. Sie waeren fuer JEDEN "
        f"gesperrt (Vorgabe deny) -- in RECHTE eintragen.")
    print("werkzeugrechte.py: Selbsttest gruen")


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--liste", action="store_true")
    a = p.parse_args()
    if a.selftest:
        _selftest()
        return 0
    if a.liste:
        print(f"Durchsetzung: {stufe()}")
        for w, r in sorted(RECHTE.items()):
            print(f"  {w:32s} {r}")
        return 0
    aktuell = ausweis.loese_auf()
    print(f"Ausweis: {aktuell.protokollname}  Rollen: "
          f"{','.join(aktuell.rollen) or '-'}  Durchsetzung: {stufe()}")
    for w in sorted(RECHTE):
        darf, grund = erlaubt(w, ausw=aktuell)
        print(f"  {'ja ' if darf else 'NEIN'}  {w:32s} {grund}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
