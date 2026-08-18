#!/usr/bin/env python3
"""Stop-Waechter: meldet, wenn eine Antwort mit einer Entscheidungsfrage an den
Betreiber endet, OBWOHL keiner der vier Stopp-Punkte beruehrt ist.

ANLASS, und er ist gemessen statt vermutet. Am 2026-08-18 hat die brainlehr-
Sitzung sieben laufende Sitzungen dieses Rechners gefragt: "wo hat der
Betreiber dir heute widersprochen, wo musste er dich korrigieren?" Drei
antworteten, und ihre Befunde decken sich:

  atelier:  drei Vorfaelle in EINER Sitzung. Die Antwort endete mit
            "Sag 'mach' und ich baue...", "Soll ich dorthin schwenken?",
            einer Auswahlliste. Er dreimal: "mach du das für mich!" ·
            "mach das!" · "und du machst hier mit deinenaufgaben weiter!"
  openlehr: vier Vorfaelle, drei davon dieselbe Wurzel -- die Antwort stand
            im Speicher, zweimal sogar sichtbar eingeblendet, und wirkte
            nicht.
  videoki:  kein Vorfall; gestoppt hat sie an diesem Tag ausschliesslich ein
            VERDRAHTETER Waechter (dateilink_waechter).

Der gemeinsame Satz, den openlehr gefunden hat und der dieses Modul
begruendet: "Keine dieser Luecken ist eine Wissens-Luecke; alle sind
Ausloeser-Luecken. Was mich tatsaechlich gestoppt hat, waren ausnahmslos
verdrahtete Wachen. Kein einziger Recall-Treffer hat mich gestoppt."

Die Regel, die hier wirksam wird, EXISTIERT laengst und hat hohen Rang: die
Betreiberfreigabe vom 2026-08-11 ("du kannst das für mich alles machen") und
ihre Erweiterung vom 2026-08-13 ("Alles, was du sagst, was auf mich wartet
kannst und darfst du selbst erledigen"). Sie stand in CLAUDE.md, wurde
gelesen -- und blieb dreimal am selben Tag wirkungslos, weil sie KEINEN
AUSLOESER hatte. Nach der eigenen Eskalationsschwelle (n>=3) ist das ein
Regelfall, kein Einzelfall.

WAS DIESES MODUL NICHT TUT: die Frage verbieten. Die vier Stopp-Punkte --
Kennwoerter, Aussenwirkung, Unumkehrbares, Geld -- sind ausgenommen, dort
IST Rueckfrage Pflicht. Erkannt werden sie am Text der Antwort selbst; ein
Fehlalarm auf dieser Seite kostet nichts (die Frage geht durch), ein
uebersehener Stopp-Punkt waere teuer. Deshalb ist die Ausnahmeliste
absichtlich weit.

PREIS EINES FEHLALARMS: eine zusaetzliche Runde, in der der Assistent
entweder selbst entscheidet oder begruendet, warum die Frage noetig war.
Anders als ausloeserlos.py hat dieser Waechter ein VETO (decision: block) --
ein blosser Hinweis waere genau der Mechanismus, dessen Wirkungslosigkeit
er behebt.

Ausschalter: Datei ~/.brainlehr/rueckfrage-aus (oder BRAINLEHR_RUECKFRAGE_AUS).

Aufruf:
    python3 rueckfrageschleife.py              # als Stop-Hook, JSON auf stdin
    python3 rueckfrageschleife.py --selftest
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Die letzten Zeichen der Antwort. Eine Entscheidungsfrage MITTEN im Text ist
# rhetorisch ("Warum das zaehlt?"); eine am Ende wartet auf Antwort.
SCHWANZ = 400

# Rueckgabe an den Betreiber. Bewusst auf Formen beschraenkt, die eine ANTWORT
# erwarten -- nicht auf jedes Fragezeichen.
FRAGE = re.compile(
    r"(soll(en)?\s+ich\b"
    r"|sag\s+(mir\s+)?(bescheid|kurz|welche|was|ob)\b"
    r"|sag\s+[\"„']?\w+[\"“']?\s+und\s+ich\b"
    r"|willst\s+du\b|moechtest\s+du\b|möchtest\s+du\b"
    r"|was\s+(moechtest|möchtest|willst)\s+du\b"
    r"|welche[nsr]?\s+\w+\s+(soll|willst|moechtest|möchtest)\b"
    r"|wie\s+soll\s+ich\b"
    r"|deine\s+entscheidung\b|entscheide\s+du\b"
    r"|wartet\s+auf\s+(dich|deine)\b"
    r"|gib\s+mir\s+bescheid\b"
    r"|(1|2|a|b)\s*(\)|\.)\s+.{3,60}\s+(oder|bzw\.?)\s+)",
    re.I,
)

# Die vier Stopp-Punkte. Hier IST Rueckfrage Pflicht -- absichtlich weit
# gefasst, weil ein Fehlalarm hier nichts kostet und ein Uebersehen teuer ist.
STOPP = re.compile(
    r"(kennwort|passwort|password|zugangsdaten|secret|api[- ]?key|token|schluessel|schlüssel"
    r"|push(e|en|st)?\b|veroeffentlich|veröffentlich|publizier|live\s+gehen|nach\s+aussen|nach\s+außen"
    r"|pull\s*request|\bPR\b|merge.{0,20}\bmain\b|auf\s+den\s+hauptzweig"
    r"|unumkehrbar|unwiderruflich|nicht\s+rueckgaengig|nicht\s+rückgängig|endgueltig\s+loesch|endgültig\s+lösch"
    r"|\bloesch|\blösch|verwerfen|ueberschreib|überschreib|zuruecksetz|zurücksetz"
    r"|geld|kosten|bezahl|rechnung|preis|abo|lizenz|vertrag"
    r"|dritte[nr]?\b|kunde|mandant|empfaenger|empfänger|versenden|verschick)",
    re.I,
)


def _aus() -> bool:
    if os.environ.get("BRAINLEHR_RUECKFRAGE_AUS"):
        return True
    return (Path.home() / ".brainlehr" / "rueckfrage-aus").exists()


def beurteile(text: str) -> str | None:
    """None = in Ordnung. Sonst der Grund, der dem Assistenten zugestellt wird.

    Geprueft wird NUR der Schwanz der Antwort: eine Frage am Ende wartet auf
    eine Antwort, eine Frage in der Mitte ist eine Ueberschrift."""
    schwanz = (text or "")[-SCHWANZ:]
    if not schwanz.strip():
        return None
    treffer = FRAGE.search(schwanz)
    if not treffer:
        return None
    if STOPP.search(schwanz):
        return None  # Kennwort, Aussenwirkung, Unumkehrbares, Geld -> fragen ist Pflicht
    return (
        "Diese Antwort endet mit einer Entscheidungsfrage an den Betreiber "
        f"(\"{treffer.group(0).strip()}\"), und keiner der vier Stopp-Punkte ist "
        "beruehrt -- kein Kennwort, keine Aussenwirkung, nichts Unumkehrbares, kein Geld.\n\n"
        "Die Betreiberfreigabe vom 2026-08-11 und ihre Erweiterung vom 2026-08-13 gelten: "
        "\"Alles, was du sagst, was auf mich wartet kannst und darfst du selbst erledigen.\" "
        "Am 2026-08-18 musste er dreimal in EINER Sitzung \"mach das!\" antworten -- deshalb "
        "haengt dieser Waechter hier.\n\n"
        "Also: entscheide selbst, benenne die Annahme, arbeite weiter. Ist die Frage "
        "wirklich noetig, weil mehr als eine Antwort moeglich ist UND die Grundlage nicht "
        "im Code liegt, dann stelle sie -- aber sag dazu, was du bereits gemessen hast."
    )


def _letzte_antwort(transcript: Path) -> str:
    """Letzte Assistentennachricht aus dem Transcript (JSONL, eine Zeile je Zug)."""
    text = ""
    try:
        for zeile in transcript.read_text(encoding="utf-8", errors="replace").splitlines():
            if not zeile.strip():
                continue
            try:
                z = json.loads(zeile)
            except ValueError:
                continue
            if z.get("type") != "assistant":
                continue
            inhalt = (z.get("message") or {}).get("content")
            if isinstance(inhalt, list):
                stuecke = [t.get("text", "") for t in inhalt if isinstance(t, dict) and t.get("type") == "text"]
                if any(s.strip() for s in stuecke):
                    text = "\n".join(stuecke)
            elif isinstance(inhalt, str) and inhalt.strip():
                text = inhalt
    except OSError:
        return ""
    return text


def _selftest() -> int:
    # Positivfaelle: woertlich die drei Antwortenden aus dem Rundruf 2026-08-18.
    for satz in [
        "Der Katalog steht. Sag 'mach' und ich baue die Verdrahtung.",
        "Beides ist moeglich. Soll ich dorthin schwenken?",
        "Zwei Wege: 1) Melder haerten oder 2) neu messen. Was moechtest du?",
        "Das wartet auf dich.",
        "Die Messung liegt vor. Wie soll ich weiter vorgehen?",
    ]:
        assert beurteile(satz), f"haette anschlagen muessen: {satz!r}"

    # Negativfaelle: die vier Stopp-Punkte -- hier IST Fragen Pflicht.
    for satz in [
        "12 Commits liegen bereit. Soll ich pushen?",
        "Das Kennwort musst du selbst eintippen. Sag Bescheid, wenn es steht.",
        "Der Zweig waere danach weg. Soll ich ihn wirklich loeschen?",
        "Das Abo kostet monatlich. Willst du das bestellen?",
        "Die Nachricht geht an einen Dritten. Soll ich sie verschicken?",
    ]:
        assert beurteile(satz) is None, f"Fehlalarm auf Stopp-Punkt: {satz!r}"

    # Negativfaelle: gar keine Frage, oder Frage nur in der MITTE.
    for satz in [
        "Melder gebaut, Selbsttest gruen, committet als abc1234.",
        "Soll ich das bauen? Diese Frage stellte sich, und die Antwort war ja. "
        + "Gebaut, gemessen, committet. Der Selbsttest ist gruen." + " x" * 200,
        "",
    ]:
        assert beurteile(satz) is None, f"Fehlalarm: {satz[:60]!r}"

    print("rueckfrageschleife: Selbsttest gruen (5 Positiv-, 8 Negativfaelle)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    if _aus():
        return 0
    try:
        eingabe = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if eingabe.get("stop_hook_active"):
        return 0  # schon einmal geblockt -- nicht in die Schleife laufen
    pfad = eingabe.get("transcript_path")
    if not pfad:
        return 0
    grund = beurteile(_letzte_antwort(Path(pfad).expanduser()))
    if grund:
        print(json.dumps({"decision": "block", "reason": grund}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
