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

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ausweis  # noqa: E402

ENV_DURCHSETZUNG = "BRAINLEHR_DURCHSETZUNG"

# Werkzeug -> benoetigtes Recht (modul:aktion). Der BEZUG (:own/:published)
# steht bewusst NICHT hier: er haengt am einzelnen Datensatz, nicht am Werkzeug,
# und wird in B4.4 im Handler ausgewertet.
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
    # verwaltend -- laeuft ueber den ganzen Bestand, darum eigene Aktion
    "kurator_lauf": "verwaltung:schreiben",
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


def fehlende_zuordnung(werkzeuge) -> list[str]:
    """Welche Werkzeuge haben kein Recht? Fuer den Selbsttest des Servers --
    ohne diese Probe faellt ein neu hinzugefuegtes Werkzeug erst auf, wenn es
    jemand aufruft und abgewiesen wird."""
    return sorted(w for w in werkzeuge if w not in RECHTE)


def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "a.json"
        g_leser = ausweis.anlegen("nur-lesen", ["leser"], pfad=pfad)
        g_schreib = ausweis.anlegen("schreiber1", ["schreiber"], pfad=pfad)
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
