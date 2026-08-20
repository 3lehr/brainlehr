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
    r"|(1|2|a|b)\s*(\)|\.)\s+.{3,60}\s+(oder|bzw\.?)\s+)"
    # ENGLISCH (2026-08-20). Gemessen: von vier englischen Rueckfragen fing
    # dieser Waechter NULL. Der Assistent antwortet nicht immer deutsch --
    # Subagenten, Werkzeugausgaben und ganze Zuege laufen englisch, und ein
    # Waechter, der nur eine Sprache kennt, ist in der anderen abgeschaltet,
    # ohne dass es jemand merkt.
    r"|should\s+i\b|shall\s+i\b|want\s+me\s+to\b"
    r"|(do|would)\s+you\s+(want|like)\s+me\s+to\b"
    r"|let\s+me\s+know\s+(if|which|whether|what)\b"
    r"|which\s+\w+\s+(should|do)\s+(i|you)\b"
    r"|your\s+call\b|up\s+to\s+you\b"
    r"|say\s+the\s+word\b"
    r"|(tell|let)\s+me\s+which\b",
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
    r"|dritte[nr]?\b|kunde|mandant|empfaenger|empfänger|versenden|verschick"
    r"|publish|deploy|release\b|irreversible|permanently\s+delete|force[- ]push"
    r"|payment|invoice|billing|subscription|contract|customer|tenant|recipient)",
    re.I,
)


# Ein VORHABEN am Ende der Antwort: Absichtsform in der ersten Person, oder
# eine Fortsetzungsansage. Bewusst breiter als die Frageliste oben, weil hier
# nicht die Formulierung entscheidet, sondern der fehlende Werkzeugaufruf --
# das Muster grenzt nur ein, WORAUF die strukturelle Pruefung angewandt wird.
VORHABEN = re.compile(
    r"(ich\s+(baue|mache|schreibe|pruefe|prüfe|messe|nehme|ziehe|starte|setze|fange|erweitere|behebe|"
    r"trage|lege|melde|arbeite|fahre|committe|beginne)\b"
    r"|ich\s+(werde|will)\b"
    r"|als\s+n(ae|ä)chstes\b"
    r"|jetzt\s+(baue|mache|folgt|kommt)\b"
    r"|weiter\s+(mit|geht)\b"
    r"|(fange|beginne)\s+(ich\s+)?(mit|bei)\b"
    r"|dann\s+(baue|mache|pruefe|prüfe)\s+ich\b"
    r"|i(\s+a|')?ll\s+(build|write|check|measure|add|fix|start|run|take|extend)\b"
    r"|i\s+will\s+\w+"
    r"|next\s+(up|step|i)\b"
    r"|let(\s+me|'s)\s+(build|write|check|measure|add|fix|start|run)\b)",
    re.I,
)


def _aus() -> bool:
    if os.environ.get("BRAINLEHR_RUECKFRAGE_AUS"):
        return True
    return (Path.home() / ".brainlehr" / "rueckfrage-aus").exists()


def beurteile(text: str, *, hat_werkzeug: bool | None = None) -> str | None:
    """None = in Ordnung. Sonst der Grund, der dem Assistenten zugestellt wird.

    ZWEI PRUEFUNGEN, und die zweite ist die wichtigere.

    Die erste sucht eine Entscheidungsfrage am Ende. Sie ist eine Liste von
    Formulierungen -- und damit genau der Fehler, den die lehrAtelier-Sitzung
    am 2026-08-18 gemeldet hat: "Wer eine Erkennungsregel aus EINEM Vorfall
    ableitet, beschreibt dessen Oberflaeche. Erkennungszeichen dafuer, dass
    man es falsch macht: die Regel besteht aus einer Liste von
    Formulierungen." Sie ist an diesem Waechter vorbeigelaufen, nicht mit
    einer Frage, sondern mit einer ANKUENDIGUNG -- "Der Arbeitsbereich ist
    sauber, ich fange mit Punkt 1 an" -- und tat es dann nicht. Wirkung
    identisch, Wortlaut anders.

    Die zweite Pruefung ist ihr Vorschlag und braucht keine Wortliste:
    **Ein Zug, der den naechsten Schritt BENENNT, muss ihn ENTHALTEN.**
    Steht am Ende ein Vorhaben und im selben Zug kein einziger
    Werkzeugaufruf, ist der Zug unfertig. Das faengt Frage, Angebot und
    Ankuendigung zugleich -- und die vierte Form, die noch niemand gesehen
    hat.

    `hat_werkzeug=None` heisst "nicht ermittelt"; dann laeuft nur die erste
    Pruefung. Der Haken reicht den Wert herein, der Selbsttest setzt ihn."""
    schwanz = (text or "")[-SCHWANZ:]
    if not schwanz.strip():
        return None

    if STOPP.search(schwanz):
        return None  # Kennwort, Aussenwirkung, Unumkehrbares, Geld -> fragen ist Pflicht

    if hat_werkzeug is False and VORHABEN.search(schwanz):
        vorhaben = VORHABEN.search(schwanz)
        return (
            f"Diese Antwort kuendigt einen naechsten Schritt an (\"{vorhaben.group(0).strip()}\"), "
            "fuehrt ihn aber nicht aus -- im ganzen Zug steht kein einziger Werkzeugaufruf.\n\n"
            "Ein Zug, der den naechsten Schritt BENENNT, muss ihn ENTHALTEN. Sonst wartet der "
            "Betreiber auf etwas, das angekuendigt und nicht getan wurde, und muss nachstossen -- "
            "am 2026-08-18 mehrfach geschehen, in zwei verschiedenen Sitzungen.\n\n"
            "Also: den angekuendigten Schritt jetzt tun. Geht er nicht, sag WARUM er nicht geht, "
            "statt ihn stehen zu lassen."
        )

    treffer = FRAGE.search(schwanz)
    if not treffer:
        return None
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


def _letzte_antwort(transcript: Path) -> tuple[str, bool]:
    """(Text der letzten Assistentenantwort, ob im Zug ein Werkzeug lief).

    Der zweite Wert ist die strukturelle Pruefung: Ein Zug ohne jeden
    Werkzeugaufruf hat nichts getan, egal was er ankuendigt. Gezaehlt wird ab
    der letzten Nachricht des Betreibers -- ein Zug kann aus vielen
    Assistentennachrichten bestehen, und ein Werkzeugaufruf irgendwo darin
    zaehlt."""
    text = ""
    werkzeug = False
    try:
        for zeile in transcript.read_text(encoding="utf-8", errors="replace").splitlines():
            if not zeile.strip():
                continue
            try:
                z = json.loads(zeile)
            except ValueError:
                continue
            if z.get("type") == "user":
                # Neuer Zug: was davor lief, gehoert nicht dazu.
                werkzeug = False
                continue
            if z.get("type") != "assistant":
                continue
            inhalt = (z.get("message") or {}).get("content")
            if isinstance(inhalt, list):
                if any(isinstance(b, dict) and b.get("type") == "tool_use" for b in inhalt):
                    werkzeug = True
                stuecke = [b.get("text", "") for b in inhalt if isinstance(b, dict) and b.get("type") == "text"]
                if any(s.strip() for s in stuecke):
                    text = "\n".join(stuecke)
            elif isinstance(inhalt, str) and inhalt.strip():
                text = inhalt
    except OSError:
        return "", False
    return text, werkzeug


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

    # --- ANKUENDIGUNG OHNE AUSFUEHRUNG (2026-08-18, von der lehrAtelier-Sitzung
    # gemeldet: sie ist an der Frageliste oben vorbeigelaufen) ---
    for satz in [
        "Der Arbeitsbereich ist sauber, ich fange mit Punkt 1 an.",   # ihr Wortlaut
        "Ich baue ihre Regel jetzt ein.",                             # meiner, eine Stunde spaeter
        "Als naechstes messe ich LongMemEval-V2 nach.",
        "Weiter mit den 32 BAU-Gates.",
    ]:
        assert beurteile(satz, hat_werkzeug=False), f"Ankuendigung nicht gefangen: {satz!r}"
        # Mit Werkzeugaufruf im selben Zug ist derselbe Satz in Ordnung --
        # das ist der ganze Unterschied zwischen Ankuendigen und Tun.
        assert beurteile(satz, hat_werkzeug=True) is None, f"Fehlalarm trotz Ausfuehrung: {satz!r}"

    # Ein Zug ohne Vorhaben darf auch ohne Werkzeug durchgehen -- eine
    # beantwortete Frage ist fertig, nicht unfertig.
    for satz in ["Die Zahl liegt bei 13 von 56, gemessen ueber gatestand.py.",
                 "Nein, das ist nicht einmalig -- die Bauform ist Forschungsfront."]:
        assert beurteile(satz, hat_werkzeug=False) is None, f"Fehlalarm ohne Vorhaben: {satz!r}"

    # Stopp-Punkt schlaegt auch die strukturelle Pruefung: hier IST Warten richtig.
    assert beurteile("Ich pushe die 45 Commits.", hat_werkzeug=False) is None

    # ENGLISCH, beide Richtungen. Gemessen am 2026-08-20: vorher fing dieser
    # Waechter NULL von vier englischen Rueckfragen -- in einem englischen Zug
    # war er abgeschaltet, ohne dass es jemand merkte.
    for text in ("Should I build that?",
                 "Want me to go ahead with the sliders?",
                 "Let me know which one you prefer.",
                 "Your call."):
        assert beurteile(text, hat_werkzeug=True), f"englische Rueckfrage nicht gefangen: {text}"
    # Gegenprobe: englischer Fliesstext ohne Rueckfrage bleibt still. Ohne
    # diesen Fall waere die Erweiterung eine Sperre gegen die Sprache.
    for text in ("Measured 377 tests, all green. The slider cuts 84 % of the edges.",
                 "I measured it and the column was missing."):
        assert beurteile(text, hat_werkzeug=True) is None, f"Fehlalarm auf: {text}"
    # Und ein Stopp-Punkt auf Englisch bleibt erlaubt -- dort IST Frage Pflicht.
    assert beurteile("Should I push this to the remote?", hat_werkzeug=True) is None

    print("rueckfrageschleife: Selbsttest gruen (5 Frage-, 4 Ankuendigungsfaelle, "
          "11 Negativfaelle, Stopp-Punkt schlaegt beide Pruefungen)")
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
    text, werkzeug = _letzte_antwort(Path(pfad).expanduser())
    grund = beurteile(text, hat_werkzeug=werkzeug)
    if grund:
        print(json.dumps({"decision": "block", "reason": grund}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
