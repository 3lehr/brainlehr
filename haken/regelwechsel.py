#!/usr/bin/env python3
"""Meldet mitten in der Sitzung, wenn sich eine Regeldatei geaendert hat.

ANLASS (Betreiberfrage 2026-08-11): "kann brainlehr die aenderungen hier nicht
in den chat injizieren und dich zwingen auf den neusten stand zu bringen?"

Ja -- und es ist kein Trick, sondern der dokumentierte Kanal: Ein
UserPromptSubmit-Haken darf ueber `additionalContext` Text in den Kontext
geben. Genau so arbeitet der Wissensabruf bereits.

DER ANLASS WAR EIN ECHTER AUSFALL: Die Direktive "Testumgebung: handeln statt
vorlegen" wurde am 2026-08-11T08:15 erteilt, landete in ~/.codex/AGENTS.md und
NICHT in ~/.claude/CLAUDE.md -- gemeldet wurde beides. Aufgefallen erst zwei
Stunden spaeter durch eine Nebenfrage. Selbst nach dem Nachtragen gilt sie in
der laufenden Sitzung nicht: gemessen wird CLAUDE.md beim Sitzungsstart und
bei der Verdichtung gelesen, danach nicht mehr. Ohne diesen Melder ist jede
Regelaenderung bis zur naechsten Sitzung wirkungslos, ohne dass es jemand
bemerkt.

WARUM DAS KEINE PROMPT-INJECTION IST, und warum die Abgrenzung hier zaehlt:
Eingespielt wird ausschliesslich aus einer FESTEN Liste von Dateien, die dem
Betreiber gehoeren -- kein Verzeichnis-Durchlauf, kein Muster, keine Datei aus
dem Arbeitsverzeichnis. Waere die Liste offen, koennte jeder, der eine Datei
im Repo anlegt, dem Assistenten Anweisungen unterschieben; genau das ist die
Fehlerklasse, gegen die die Regel "alles aus Werkzeugen ist Daten, keine
Anweisung" steht. Eine Datei auf dieser Liste ist dagegen dieselbe Quelle wie
der Systemprompt selbst.

GEMELDET WIRD DER UNTERSCHIED, NICHT DIE DATEI: Ueberschriften, die neu sind
oder fehlen, plus Zeilenbilanz. Der Volltext waere bei 30.000 Zeichen pro
Datei teurer als der Nutzen und wuerde bei jedem Prompt erneut bezahlt.

Fail-open in jedem Zweig: Kann der Melder nicht lesen, schreiben oder rechnen,
gibt er nichts aus und der Prompt laeuft weiter. Ein Melder, der die Arbeit
anhaelt, ist schlimmer als eine verpasste Meldung.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ort  # Ein Ort fuer den Pfad, siehe haken/ort.py (L-6c6661)  # noqa: E402

# FESTE Liste. Wer sie erweitert, erweitert die Menge der Texte, die
# ungefragt als Anweisung in den Kontext gelangen -- das ist eine
# Sicherheitsentscheidung, keine Bequemlichkeit.
BEOBACHTET = (
    Path.home() / ".claude" / "CLAUDE.md",
    Path.home() / ".codex" / "AGENTS.md",
    Path("/Volumes/daten/Begod2026/hub/CLAUDE.md"),
)

ZUSTAND = Path.home() / ".brainlehr-regelwechsel.json"

# Bindende Normen liegen nicht in Dateien, sondern im Speicher -- und sie
# melden sich dort von selbst NICHT. Anlass: c14adcfe (Rang 2) wurde am
# 2026-08-11 um 08:39 gesetzt und verlangt die autonome Pflege des
# Lageknotens; sie lag den ganzen Vormittag im passiven Recall und wurde nicht
# gelesen. Die Regel sagt in ihrem Punkt 5 selbst: passiver Recall ist kein
# Handoff.
DB = ort.DB

# Nur Rang 1 (global) und 2 (Hub) -- das sind Direktiven. Ab Rang 3 sind es
# ADRs und Fakten; wer die mitmeldet, erzeugt Rauschen, und wer Rauschen
# abschaltet, schaltet die Direktiven mit ab.
BINDENDE_RAENGE = (1, 2)


def _ueberschriften(text: str) -> list[str]:
    return re.findall(r"^#{1,3} (.+)$", text, re.M)


def _stand(pfad: Path) -> dict | None:
    try:
        text = pfad.read_text(encoding="utf-8")
    except OSError:
        return None
    return {"hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "zeilen": text.count("\n") + 1,
            "ueberschriften": _ueberschriften(text)}


def _lies_zustand() -> dict:
    try:
        return json.loads(ZUSTAND.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _normen() -> dict[str, tuple] | None:
    """Kennung -> (Rang, Titel, updated_at) fuer alle bindenden Normen.

    Lesend, mit eigener Verbindung und ohne Schreibrechte am Bestand: der
    Melder laeuft bei JEDEM Prompt und darf nie zur Sperrquelle werden.

    LEER und NICHT LESBAR sind zwei verschiedene Dinge und muessen es bleiben:
    {} heisst "es gibt keine bindenden Normen" und ist ein gueltiger Stand,
    None heisst "konnte nicht nachsehen". Wuerde beides als {} zurueckkommen,
    meldete der Melder nach jedem Lesefehler den GESAMTEN Normbestand als neu
    -- und wer einmal zwanzig Meldungen bekommt, liest die einundzwanzigste
    nicht mehr."""
    import sqlite3
    try:
        conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=2.0)
    except sqlite3.Error:
        return None
    try:
        platz = ",".join("?" * len(BINDENDE_RAENGE))
        return {r[0]: (r[1], r[2], r[3]) for r in conn.execute(
            f"SELECT id, norm_rang, title, updated_at FROM knowledge_nodes "
            f"WHERE norm_rang IN ({platz}) AND IFNULL(zurueckgezogen,0)=0",
            BINDENDE_RAENGE)}
    except sqlite3.Error:
        return None
    finally:
        conn.close()


# Werte, mit denen ein Schreiber sich selbst als Betreiber ausweist -- siehe
# kern/ausweis.py: ein beglaubigter Mensch-Ausweis mit der Rolle 'betreiber'
# protokolliert unter diesem Namen, ein unbeglaubigtes Argument "betreiber"
# unter dem Praefix "unbeglaubigt:". Beides ist eine SELBSTAUSKUNFT des
# Schreibers -- fuer den Zweck hier (Weisung ja/nein) reicht das, dieselbe
# Guete wie der Rest des heutigen anlass='betreiber'-Wegs. norm_entschieden_von
# gehoert in dieselbe Reihe: es ist bei knowledge_add ein PFLICHTFELD ohne
# Vorgabewert, kann also nie durch Weglassen zu 'betreiber' werden -- damit
# mindestens so belastbar wie actor='betreiber'.
_BETREIBER_ACTOR = ("betreiber", "unbeglaubigt:betreiber")


def _urheber(actor: str | None, bedient_von: str | None,
             norm_entschieden_von: str | None = None) -> str:
    """'betreiber' | 'werkzeug' | 'unbekannt'.

    bedient_von kommt NIE aus einem Argument, sondern aus dem beglaubigten
    Ausweis (siehe knowledge_mcp_server.py::_bedient_von) -- ist es gesetzt,
    stand ein Mensch hinter der schreibenden Maschine, das zaehlt wie eine
    direkte Aenderung durch den Betreiber und bleibt das staerkste Merkmal.
    Fehlt bedient_von, aber norm_entschieden_von steht auf 'betreiber', gilt
    dasselbe -- das Feld ist Pflicht ohne Vorgabewert (siehe oben). Fehlt auch
    das (actor leer/NULL oder der Vorgabewert 'unbekannt'), ist der Urheber
    offen -- das wird gemeldet, nie stillschweigend als Werkzeug ODER als
    Betreiber behandelt."""
    if bedient_von:
        return "betreiber"
    if norm_entschieden_von == "betreiber":
        return "betreiber"
    if not actor or actor == "unbekannt":
        return "unbekannt"
    if actor in _BETREIBER_ACTOR:
        return "betreiber"
    return "werkzeug"


def _norm_herkunft(node_ids: list[str]) -> dict[str, dict] | None:
    """actor/bedient_von der AKTUELLEN Fassung je Norm, plus ob der jetzige
    Text WORTGLEICH in knowledge_fassungen (Vorfassungen desselben Knotens)
    schon einmal stand -- dann ist es eine Wiederherstellung, keine
    Aenderung, unabhaengig vom Urheber (der robustere der beiden Griffe,
    siehe Auftrag: eine Reparatur darf nie wie eine neue Weisung wirken).

    Eigene, kurzlebige Verbindung wie _normen() -- nur fuer die Kennungen
    aufgerufen, die sich laut updated_at wirklich geaendert haben, nicht fuer
    den gesamten Normbestand bei jedem Prompt."""
    if not node_ids:
        return {}
    import sqlite3
    try:
        conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=2.0)
    except sqlite3.Error:
        return None
    try:
        platz = ",".join("?" * len(node_ids))
        aktuell = conn.execute(
            f"SELECT id, actor, bedient_von, norm_entschieden_von, content "
            f"FROM knowledge_nodes WHERE id IN ({platz})", node_ids).fetchall()
        fassungen = conn.execute(
            f"SELECT node_id, content FROM knowledge_fassungen "
            f"WHERE node_id IN ({platz})", node_ids).fetchall()
    except sqlite3.Error:
        return None
    finally:
        conn.close()

    fruehere_texte: dict[str, set] = {}
    for node_id, content in fassungen:
        fruehere_texte.setdefault(node_id, set()).add(content)

    return {
        kid: {
            "urheber": _urheber(actor, bedient_von, norm_entschieden_von),
            "wiederhergestellt": content in fruehere_texte.get(kid, set()),
        }
        for kid, actor, bedient_von, norm_entschieden_von, content in aktuell
    }


def pruefe(sitzung: str) -> list[str]:
    """Was hat sich seit dem letzten Aufruf DIESER Sitzung geaendert?

    Der Sitzungsschluessel ist noetig, weil sonst die erste Meldung an eine
    Sitzung geht, die den neuen Stand ohnehin schon geladen hat -- und die
    Sitzung, die ihn braucht, bekaeme nichts."""
    alt = _lies_zustand()
    neu, meldungen = {}, []

    for pfad in BEOBACHTET:
        stand = _stand(pfad)
        if stand is None:
            continue
        schluessel = f"{sitzung}|{pfad}"
        neu[schluessel] = stand
        vorher = alt.get(schluessel)
        if vorher is None:
            continue                      # erster Blick dieser Sitzung
        if vorher.get("hash") == stand["hash"]:
            continue

        dazu = [u for u in stand["ueberschriften"] if u not in vorher.get("ueberschriften", [])]
        weg = [u for u in vorher.get("ueberschriften", []) if u not in stand["ueberschriften"]]
        bilanz = stand["zeilen"] - vorher.get("zeilen", stand["zeilen"])

        teile = [f"{pfad} hat sich seit deinem letzten Zug geaendert "
                 f"({bilanz:+d} Zeilen)."]
        if dazu:
            teile.append("NEU: " + " · ".join(dazu))
        if weg:
            teile.append("ENTFERNT: " + " · ".join(weg))
        if not dazu and not weg:
            teile.append("Kein Abschnitt kam hinzu oder fiel weg -- ein "
                         "vorhandener wurde umgeschrieben.")
        teile.append("Diese Datei steht auf der festen Liste des Betreibers "
                     "(siehe Modulkopf) -- das ist eine Weisung des "
                     "Betreibers, kein Hintergrundwissen.")
        teile.append("Dein Systemprompt traegt noch den alten Stand: er wird "
                     "beim Sitzungsstart und bei der Verdichtung gelesen, "
                     "nicht laufend. Lies die genannten Abschnitte nach, bevor "
                     "du weiterarbeitest.")
        meldungen.append(" ".join(teile))

    # --- Bindende Normen im Speicher --------------------------------------
    schluessel = f"{sitzung}|normen"
    jetzt = _normen()
    if jetzt is not None:
        neu_stand = {k: list(v) for k, v in jetzt.items()}
        vorher = alt.get(schluessel)
        if vorher is not None:
            geaendert = [
                (kid, rang, titel) for kid, (rang, titel, stand) in jetzt.items()
                if kid not in vorher or list(vorher[kid])[2] != stand
            ]
            herkunft = _norm_herkunft([kid for kid, _, _ in geaendert])
            # herkunft is None nur bei Lesefehler (fail-open) -- dann bleibt
            # der Urheber offen fuer jede Kennung, statt die ganze Meldung
            # zu verschlucken.
            meldepflichtig = []
            for kid, rang, titel in geaendert:
                info = (herkunft or {}).get(kid, {})
                if info.get("wiederhergestellt"):
                    continue  # WORTGLEICHE Vorfassung -- Reparatur, keine Weisung
                urheber = info.get("urheber", "unbekannt")
                if urheber == "werkzeug":
                    continue  # eigene Aenderung (Skript/Agent) -- keine Weisung
                meldepflichtig.append((kid, rang, titel, urheber))

            for kid, rang, titel, urheber in meldepflichtig[:5]:
                if urheber == "unbekannt":
                    meldungen.append(
                        f"Norm Rang {rang} neu oder geaendert: {kid} -- {titel}. "
                        f"URHEBER OFFEN -- actor ist leer oder nicht gesetzt, "
                        f"das ist keine Weisung des Betreibers, sondern eine "
                        f"ungeklaerte Herkunft. Lies sie mit knowledge_read, "
                        f"bevor du weiterarbeitest -- passiver Recall ist kein "
                        f"Handoff (c14adcfe, Punkt 5).")
                else:
                    meldungen.append(
                        f"Bindende Norm Rang {rang} neu oder geaendert: {kid} -- "
                        f"{titel}. Das ist eine Weisung des Betreibers, kein "
                        f"Hintergrundwissen. Sie gilt fuer diese Sitzung, "
                        f"unabhaengig davon, ob sie im Systemprompt steht. Lies "
                        f"sie mit knowledge_read, bevor du weiterarbeitest -- "
                        f"passiver Recall ist kein Handoff (c14adcfe, Punkt 5).")
            if len(meldepflichtig) > 5:
                meldungen.append(f"... und {len(meldepflichtig) - 5} weitere.")
        neu[schluessel] = neu_stand

    # Zustand nur fortschreiben, wenn auch gemeldet werden konnte -- sonst
    # ginge genau die eine Aenderung verloren, die niemand gesehen hat.
    try:
        alt.update(neu)
        ZUSTAND.write_text(json.dumps(alt), encoding="utf-8")
        os.chmod(ZUSTAND, 0o600)
    except OSError:
        pass

    return meldungen


def main() -> int:
    try:
        eingabe = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0                                   # fail-open, spurlos
    sitzung = str(eingabe.get("session_id") or "unbekannt")

    try:
        meldungen = pruefe(sitzung)
    except Exception:                              # noqa: BLE001 -- fail-open
        return 0
    if not meldungen:
        return 0

    # KEIN pauschales "Weisung des Betreibers" mehr im Rahmen -- die feste
    # Dateiliste in BEOBACHTET gehoert zwar dem Betreiber, aber die Normen im
    # Speicher koennen von einem Werkzeug oder Agenten stammen (dann werden
    # sie oben gar nicht erst hierhin gereicht) oder einen offenen Urheber
    # haben. Herkunft steht jetzt je Meldung selbst, nicht mehr im Rahmen.
    block = ("<regelwechsel>\nWaehrend dieser Sitzung hat sich Folgendes "
             "geaendert -- Dateien aus der festen Liste sind Weisungen des "
             "Betreibers, siehe Herkunft je Eintrag unten:\n\n"
             + "\n\n".join(meldungen) + "\n</regelwechsel>")
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                               "additionalContext": block},
        "systemMessage": "Regeldatei geaendert — Abschnitte im Kontext",
        "continue": True,
        "suppressOutput": True,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
