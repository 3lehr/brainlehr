#!/usr/bin/env python3
"""Stop-Waechter: der Betreiber hat korrigiert -- und nichts wurde festgehalten.

ANLASS (Betreiberfrage 2026-08-20): *"dann brauchen wir einen automatismus der
den fall aufnimmt, wenn ich dich darauf hinweist?"*

DIE LUECKE, die er meint, ist gemessen: Die zwei Muster, die am selben Tag in
den Vermutungswaechter kamen, stammen BEIDE aus Faellen, in denen er selbst
hingewiesen hat. Kein Muster stammte aus eigener Einsicht. Wer die Faelle
nicht einsammelt, hat keine Muster -- und die Musterliste ist genau so gut wie
die Sammlung der Faelle.

WARUM DER MARKER ENG IST, und das ist die ganze Bauentscheidung. Gemessen an
841 echten Betreibernachrichten:

  breite Marker (aber/doch/nein/warum/sollten wir)   146   17,4 %
  enge Marker (diese Liste)                           10    1,2 %

Bei 17,4 % waere aus dem Waechter eine Gewohnheit geworden, die man wegklickt.
Von den 10 engen Treffern sind 8 echte Beanstandungen -- geprueft, nicht
geschaetzt.

ZWEI BEDINGUNGEN, nicht eine: Es reicht nicht, dass er korrigiert hat. Der
Waechter schlaegt nur an, wenn im selben Zug AUCH nichts festgehalten wurde
(kein lesson_record, kein knowledge_add). Wer die Lehre schon geschrieben hat,
soll nicht daran erinnert werden.

    python3 melder/korrekturlehre.py --selftest
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Nur Formen, die eine BEANSTANDUNG tragen -- nicht Zustimmung, nicht die
# gewoehnliche Nachfrage. Jede Zeile stammt aus einer echten Nachricht des
# Betreibers, nicht aus der Vorstellung, wie er schreiben koennte.
KORREKTUR = re.compile(
    r"(warum (hast|machst|schreibst|ist|nicht|ungepr)"
    r"|wie oft (noch|denn)"
    r"|das ist (doch )?falsch|stimmt nicht"
    r"|nie wieder|schon wieder"
    r"|h(ä|ae)ttest du"
    r"|musst du (das )?nicht"
    r"|das geh(ö|oe)rt (aber )?(in|zu|nicht)"
    r"|vergiss das nicht|merk dir"
    r"|zu einfach gemacht)",
    re.I,
)

# Werkzeuge, die einen Fall dauerhaft festhalten. Ein Zug, der eines davon
# gerufen hat, ist fertig -- egal ob die Lehre gut ist, das entscheidet dieser
# Waechter nicht.
FESTGEHALTEN = ("lesson_record", "knowledge_add", "lesson_update", "knowledge_update")


# Was als "user" ankommt, aber keine Nachricht des Betreibers ist. Gefunden
# von der Pflicht-Stichprobe des Rueckwirkungszaehlers (Norm 17b14a32): die
# ersten fuenf Beispiele waren allesamt der eingespielte Text der
# `/abwesend`-Faehigkeit, der "nie wieder" und "merk dir" enthaelt. Ohne
# diesen Filter haette der Waechter beim Aufruf einer Faehigkeit angeschlagen
# -- eine Quote allein haette das nie gezeigt.
FREMDTEXT = ("<", "{", "Caveat", "Stop hook", "Base directory for this skill",
             "# Abwesend", "<command-name>", "<local-command",
             "This session is being continued")


def _keine_betreibernachricht(text: str) -> bool:
    return text.startswith(FREMDTEXT) or "Base directory for this skill" in text[:200]


def _aus() -> bool:
    return os.environ.get("BRAINLEHR_KORREKTURLEHRE", "").strip().lower() == "aus"


def beurteile(betreibertext: str, festgehalten: bool) -> str | None:
    if festgehalten:
        return None
    treffer = KORREKTUR.search(betreibertext or "")
    if not treffer:
        return None
    return (
        f'Der Betreiber hat in diesem Zug korrigiert ("{treffer.group(0)}") -- '
        "und es wurde nichts festgehalten.\n\n"
        "Die zwei Muster, die am 2026-08-20 in den Vermutungswaechter kamen, "
        "stammen BEIDE aus Faellen, in denen er hingewiesen hat; keines aus "
        "eigener Einsicht. Die Musterliste ist genau so gut wie die Sammlung "
        "der Faelle.\n\n"
        "Also: `lesson_record` mit dem Fall (was war die Behauptung, was war "
        "richtig, woran haette ich es merken koennen) -- oder `knowledge_add`, "
        "wenn es eine Entscheidung war. Erst dann abschliessen.\n\n"
        "Betrifft die Korrektur nur diesen einen Handgriff und nichts "
        "Dauerhaftes, halte das ausdruecklich fest ('nichts Dauerhaftes') und "
        "arbeite weiter."
    )


def _zug(transcript: Path) -> tuple[str, bool]:
    """(letzte Betreibernachricht, ob im Zug etwas festgehalten wurde).

    Gezaehlt wird ab der LETZTEN echten Betreibernachricht -- Werkzeug-
    ergebnisse und Hakenausgaben kommen ebenfalls als 'user' an und wuerden
    den Zug sonst falsch schneiden."""
    text = ""
    festgehalten = False
    try:
        for zeile in transcript.read_text(encoding="utf-8", errors="replace").splitlines():
            if not zeile.strip():
                continue
            try:
                z = json.loads(zeile)
            except ValueError:
                continue
            art = z.get("type")
            if art == "user":
                inhalt = (z.get("message") or {}).get("content")
                roh = inhalt if isinstance(inhalt, str) else (
                    " ".join(b.get("text", "") for b in inhalt
                             if isinstance(b, dict) and b.get("type") == "text")
                    if isinstance(inhalt, list) else "")
                roh = (roh or "").strip()
                if not roh or _keine_betreibernachricht(roh):
                    continue
                text, festgehalten = roh, False      # neuer Zug
            elif art == "assistant":
                inhalt = (z.get("message") or {}).get("content")
                if isinstance(inhalt, list):
                    for b in inhalt:
                        if isinstance(b, dict) and b.get("type") == "tool_use":
                            if any(w in str(b.get("name", "")) for w in FESTGEHALTEN):
                                festgehalten = True
    except OSError:
        return "", True          # nicht lesbar -> lieber schweigen
    return text, festgehalten


def _selftest() -> int:
    # a) Korrektur ohne Festhalten -> Beanstandung.
    assert beurteile("warum ungeprueft, ungeprueft geht bei nicht!!!!", False)
    assert beurteile("das gehoert zuallererst in die lehratelier app!", False)
    assert beurteile("die uhrzeit ist egal wie oft noch?", False)

    # b) DIESELBE Korrektur MIT Festhalten -> still. Das ist die Haelfte, die
    #    den Waechter ertraeglich macht.
    assert beurteile("warum ungeprueft, ungeprueft geht bei nicht!!!!", True) is None

    # c) NEGATIVFALL: gewoehnliche Auftraege und Zustimmung schlagen nicht an.
    for t in ("bau mir bitte den regler ein",
              "ja, erst regler, dann den rest, vollstaendig!",
              "go",
              "sollten wir die musterliste nicht groesser anlegen?",
              "wie geht es nun weiter?"):
        assert beurteile(t, False) is None, f"Fehlalarm auf: {t}"

    # d) Abschaltbar, und der Schalter wirkt.
    os.environ["BRAINLEHR_KORREKTURLEHRE"] = "aus"
    assert _aus() is True
    del os.environ["BRAINLEHR_KORREKTURLEHRE"]
    assert _aus() is False

    # e) Der Zugschnitt: ein Werkzeugaufruf VOR der letzten Betreibernachricht
    #    zaehlt nicht -- sonst deckte eine Lehre von gestern die Korrektur von
    #    heute.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "t.jsonl"
        t.write_text("\n".join(json.dumps(z) for z in [
            {"type": "user", "message": {"content": "alter Auftrag"}},
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "mcp__knowledge__lesson_record"}]}},
            {"type": "user", "message": {"content": "warum hast du das nicht geprueft?"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "..."}]}},
        ]), encoding="utf-8")
        text, fest = _zug(t)
        assert "warum hast du" in text and fest is False, (text, fest)
        assert beurteile(text, fest), "die Lehre von davor darf nicht decken"

    # FREMDTEXT: der eingespielte Text einer Faehigkeit ist keine Nachricht
    # des Betreibers. Gefunden von der Pflicht-Stichprobe, nicht von der Quote.
    assert _keine_betreibernachricht(
        "Base directory for this skill: /Users/x/.claude/skills/abwesend\n# Abwesend\n"
        "nie wieder will ich so einen text hoeren")
    assert _keine_betreibernachricht("warum hast du das nicht geprueft?") is False

    print("korrekturlehre: Selbsttest gruen (3 Korrekturen, Festhalten deckt, "
          "5 Negativfaelle, Schalter wirkt, Zugschnitt haelt, Faehigkeitstext ausgeschlossen)")
    return 0



def _verlauf(dateien: int = 400) -> int:
    """Rueckwirkungs-Zaehler (Norm 17b14a32). Gegenstand sind hier ZUEGE, nicht
    Antworten -- ein Zug ist die Einheit, in der korrigiert und festgehalten
    wird. Gemeinsame Bauform aus kern/rueckwirkung.py."""
    _w = Path(__file__).resolve().parent
    while not (_w / "schema.sql").exists() and _w != _w.parent:
        _w = _w.parent
    sys.path[:0] = [str(_w / "kern")]
    import rueckwirkung as r

    def zuege():
        wurzel = Path.home() / ".claude" / "projects"
        try:
            pfade = sorted(wurzel.rglob("*.jsonl"),
                           key=lambda x: x.stat().st_mtime, reverse=True)[:dateien]
        except OSError:
            return
        for f in pfade:
            try:
                roh = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            text, fest = "", False
            for zeile in roh.splitlines():
                if not zeile.strip():
                    continue
                try:
                    z = json.loads(zeile)
                except ValueError:
                    continue
                if z.get("type") == "user":
                    c = (z.get("message") or {}).get("content")
                    roh_t = c if isinstance(c, str) else (
                        " ".join(b.get("text", "") for b in c
                                 if isinstance(b, dict) and b.get("type") == "text")
                        if isinstance(c, list) else "")
                    roh_t = (roh_t or "").strip()
                    if not roh_t or _keine_betreibernachricht(roh_t):
                        continue
                    if text:
                        yield (text, fest)
                    text, fest = roh_t, False
                elif z.get("type") == "assistant":
                    c = (z.get("message") or {}).get("content")
                    if isinstance(c, list):
                        for b in c:
                            if isinstance(b, dict) and b.get("type") == "tool_use" and any(
                                    w in str(b.get("name", "")) for w in FESTGEHALTEN):
                                fest = True

    b = r.zaehle(zuege(), lambda p: beurteile(p[0], p[1]) is not None,
                 lambda p: p[0][:130])
    r.bericht("Zuege mit Korrektur ohne Lehre", b)
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    if "--pruefe-verlauf" in sys.argv:
        i = sys.argv.index("--pruefe-verlauf")
        return _verlauf(int(sys.argv[i + 1]) if len(sys.argv) > i + 1 else 400)
    if _aus():
        return 0
    try:
        eingabe = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if eingabe.get("stop_hook_active"):
        return 0
    pfad = eingabe.get("transcript_path")
    if not pfad:
        return 0
    text, fest = _zug(Path(pfad).expanduser())
    grund = beurteile(text, fest)
    if grund:
        print(json.dumps({"decision": "block", "reason": grund}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
