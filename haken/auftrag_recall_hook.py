#!/usr/bin/env python3
"""
auftrag_recall_hook.py — Anweisungsregister-Recall (UserPromptSubmit-Hook).

Liest hub/shared-knowledge/auftraege.jsonl direkt (append-only, Statuswechsel
als zusätzliche Zeile am Ende — letzte Zeile zu einer id gewinnt) und zeigt
die offenen Anweisungen des Betreibers für das aktuelle Projekt, gedeckelt.

Bewusst KEIN Unterprozess, KEIN Import eines anderen Moduls für das Lesen —
dieser Hook läuft vor jeder Eingabe und muss allein und schnell sein. Die
kleine Doppelung der Lesemechanik ggü. einem eventuellen auftragsregister.py
ist gewollt (siehe hub/docs/PLAN_ANWEISUNGSREGISTER_2026-08-05.md, A2).

Regeln:
- IMMER exit 0. Fehler/keine Treffer -> nichts ausgeben.
- Still bei Slash-Commands und zu kurzen Eingaben.
- auftraege.jsonl wird NIE geschrieben, nur gelesen.

Selbsttest: python3 auftrag_recall_hook.py --selftest
"""

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
from datetime import datetime, timezone
import json
import os
import sys

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import ort  # Ein Ort fuer den Pfad, siehe haken/ort.py (L-6c6661)
REGISTER = str(ort.REGISTER)
CAP = 5
MIN_PROMPT_LEN = 3
TEXT_CUT = 100

# Auftrag 2026-08-06: dieser Hook gibt woertliche Nutzernachrichten aus --
# groesste Gefahr im ganzen Auftrag. entschaerfe_fuer_ausgabe() kennzeichnet
# anweisungsartige Funde, aendert nie auftraege.jsonl (nur die Ausgabe-Kopie).
sys.path.insert(0, os.path.dirname(REGISTER))
from einschleusung import entschaerfe_fuer_ausgabe  # noqa: E402


def alter_tage(ts: str | None) -> int | None:
    if not ts:
        return None
    roh = str(ts).strip().replace("Z", "+00:00")
    try:
        d = datetime.fromisoformat(roh)
    except ValueError:
        try:
            d = datetime.fromisoformat(roh[:19])
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    tage = (datetime.now(timezone.utc) - d).days
    return tage if tage >= 0 else 0


def read_offene(path: str, projekt_filter: str | None) -> list[dict]:
    """Alle Eintraege mit WIRKSAMEM Status 'offen' fuer projekt_filter (Praefix
    von cwd), neueste zuerst. Kaputte Zeilen werden uebersprungen, nicht
    geworfen."""
    status_by_id: dict[str, str] = {}
    meta_by_id: dict[str, dict] = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(d, dict):
                    continue
                eid = d.get("id")
                status = d.get("status")
                if not eid or not status:
                    continue
                status_by_id[eid] = status  # letzte Zeile gewinnt
                if "text" in d:
                    meta_by_id[eid] = d
    except (FileNotFoundError, OSError):
        return []

    out = []
    for eid, status in status_by_id.items():
        if status != "offen":
            continue
        meta = meta_by_id.get(eid)
        if not meta:
            continue
        projekt = meta.get("projekt")
        if projekt_filter is not None:
            if not projekt or not projekt_filter.startswith(projekt):
                continue
        out.append(meta)
    # Älteste zuerst — die jüngsten stehen dem Betreiber ohnehin noch vor Augen,
    # die vergessenen sind die alten.
    out.sort(key=lambda m: m.get("ts") or "")
    return out


def format_zeile(meta: dict) -> str:
    tage = alter_tage(meta.get("ts"))
    alter = f"{tage} Tage alt" if tage is not None else "Alter unbekannt"
    text = " ".join((meta.get("text") or "").split())
    if len(text) > TEXT_CUT:
        text = text[:TEXT_CUT].rstrip() + "…"
    return f"- [{alter}] {entschaerfe_fuer_ausgabe(text)}"


def build_block(cwd: str, register: str = REGISTER, session_id: str | None = None) -> str | None:
    offene = read_offene(register, cwd)
    if not offene:
        return None

    # Ohne Sitzungskennung: heutiges Verhalten, eine Gruppe, keine Ausnahme.
    if not session_id:
        gezeigt = offene[:CAP]
        rest = len(offene) - len(gezeigt)
        lines = [
            "<offene-auftraege>",
            "Offene Anweisungen des Betreibers aus frueheren Nachrichten, noch nicht erledigt:",
        ]
        lines.extend(format_zeile(m) for m in gezeigt)
        if rest > 0:
            lines.append(f"… und {rest} weitere, nicht gezeigt.")
        lines.append("</offene-auftraege>")
        return "\n".join(lines)

    eigene = [m for m in offene if m.get("session") == session_id]
    fremde = [m for m in offene if m.get("session") != session_id]

    gezeigt_eigene = eigene[:CAP]
    rest_platz = CAP - len(gezeigt_eigene)
    gezeigt_fremde = fremde[:rest_platz] if rest_platz > 0 else []
    rest = (len(eigene) - len(gezeigt_eigene)) + (len(fremde) - len(gezeigt_fremde))

    lines = ["<offene-auftraege>"]
    if gezeigt_eigene:
        lines.append("Offene Anweisungen des Betreibers aus diesem Gespraech, noch nicht erledigt:")
        lines.extend(format_zeile(m) for m in gezeigt_eigene)
    if gezeigt_fremde:
        lines.append(
            "Offene Anweisungen des Betreibers aus einem anderen Gespraech — "
            "nicht an dieses gerichtet, aber noch nicht erledigt:"
        )
        lines.extend(f"{format_zeile(m)} [{(m.get('session') or '?')[:8]}]" for m in gezeigt_fremde)
    if rest > 0:
        lines.append(f"… und {rest} weitere, nicht gezeigt.")
    lines.append("</offene-auftraege>")
    return "\n".join(lines)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    prompt = (payload.get("prompt") or "").strip()
    if not prompt or prompt.startswith("/") or len(prompt) < MIN_PROMPT_LEN:
        return
    cwd = payload.get("cwd") or os.getcwd()
    session_id = payload.get("session_id")
    try:
        block = build_block(cwd, session_id=session_id)
    except Exception:
        return
    if block:
        print(block)


def selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        reg = os.path.join(td, "auftraege.jsonl")

        rows = [
            # 1: bleibt offen
            {"id": "a1", "ts": "2026-07-20T10:00:00Z", "projekt": "/proj/x",
             "text": "Anweisung eins", "status": "offen"},
            # 2: neu -> offen -> erledigt: letzte Zeile gewinnt, darf NICHT erscheinen
            {"id": "a2", "ts": "2026-07-21T10:00:00Z", "projekt": "/proj/x",
             "text": "Anweisung zwei", "status": "neu"},
            {"art": "statuswechsel", "id": "a2", "status": "offen", "ts": "2026-07-22T10:00:00Z"},
            {"art": "statuswechsel", "id": "a2", "status": "erledigt", "ts": "2026-07-23T10:00:00Z"},
            # 3: anderes Projekt -> Filter muss greifen
            {"id": "a3", "ts": "2026-07-24T10:00:00Z", "projekt": "/proj/y",
             "text": "Anweisung drei", "status": "offen"},
            # n1: bleibt 'neu' -> darf nie erscheinen (nur 'offen' zaehlt)
            {"id": "n1", "ts": "2026-07-25T10:00:00Z", "projekt": "/proj/x",
             "text": "Anweisung neu", "status": "neu"},
            # 4-9: fuer den Deckel
            *[{"id": f"cap{i}", "ts": f"2026-07-{10+i:02d}T10:00:00Z", "projekt": "/proj/x",
               "text": f"Deckeltest {i}", "status": "offen"} for i in range(6)],
        ]
        with open(reg, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
            f.write("{kaputt json\n")  # kaputte Zeile

        offene = read_offene(reg, "/proj/x")
        ids = {m["id"] for m in offene}
        assert "a1" in ids, ids
        assert "a2" not in ids, "ueberholter Status (offen->erledigt) darf nicht erscheinen"
        assert "a3" not in ids, "Projektfilter muss greifen"
        assert "n1" not in ids, "Status 'neu' ist nicht 'offen'"
        assert len(ids) == 1 + 6, ids  # a1 + 6 cap-Eintraege
        print("  Status-Ueberholung + Projektfilter ok")

        block = build_block("/proj/x", reg)
        assert block is not None
        assert "und 2 weitere" in block, block  # 7 offen, CAP=5 -> 2 uebrig
        assert block.count("\n- [") == CAP
        print("  Deckel + Kappungshinweis ok")

        # Richtungs-Test: älteste zuerst
        offene = read_offene(reg, "/proj/x")
        # offene[0] sollte älter sein als offene[-1]
        ts_first = offene[0].get("ts") or ""
        ts_last = offene[-1].get("ts") or ""
        assert ts_first < ts_last, \
            f"Sortierung falsch: erste ({ts_first}) sollte älter sein als letzte ({ts_last}), aber {ts_first} >= {ts_last}"
        assert offene[0]["id"] == "cap0", \
            f"Erster sollte cap0 sein (2026-07-10, älteste offene), ist {offene[0]['id']}"
        assert offene[-1]["id"] == "a1", \
            f"Letzter sollte a1 sein (2026-07-20, neueste offene), ist {offene[-1]['id']}"
        print("  Sortierung: älteste zuerst ok")

        # leeres Register -> keine Ausgabe
        leer = os.path.join(td, "leer.jsonl")
        open(leer, "w").close()
        assert read_offene(leer, "/proj/x") == []
        print("  leeres Register ok")

        # fehlende Datei -> keine Ausgabe, kein Fehler
        assert read_offene(os.path.join(td, "fehlt.jsonl"), "/proj/x") == []
        print("  fehlende Datei ok")

        # nur kaputte Zeile -> keine Ausgabe, kein Fehler
        kaputt = os.path.join(td, "kaputt.jsonl")
        with open(kaputt, "w") as f:
            f.write("{ nicht json\n")
            f.write("42\n")  # gueltiges JSON, aber kein dict
        assert read_offene(kaputt, "/proj/x") == []
        print("  kaputte Registerdatei ok")

        # kein Projektfilter (None) -> alles offene, unabhaengig vom Projekt
        alle = read_offene(reg, None)
        assert any(m["id"] == "a3" for m in alle)
        print("  ohne Filter ok")

        # --- Sitzungs-Kennzeichnung (Reparatur 2026-08-05) ---

        reg2 = os.path.join(td, "sitzungen.jsonl")
        rows2 = [
            {"id": "eig1", "ts": "2026-08-01T10:00:00Z", "projekt": "/proj/z",
             "session": "mein-sess-lang", "text": "eigene Anweisung eins", "status": "offen"},
            {"id": "eig2", "ts": "2026-08-02T10:00:00Z", "projekt": "/proj/z",
             "session": "mein-sess-lang", "text": "eigene Anweisung zwei", "status": "offen"},
            {"id": "frd1", "ts": "2026-07-30T10:00:00Z", "projekt": "/proj/z",
             "session": "fremd-sess-lang", "text": "fremde Anweisung eins", "status": "offen"},
            {"id": "frd2", "ts": "2026-07-31T10:00:00Z", "projekt": "/proj/z",
             "session": "fremd-sess-lang", "text": "fremde Anweisung zwei", "status": "offen"},
        ]
        with open(reg2, "w", encoding="utf-8") as f:
            for r in rows2:
                f.write(json.dumps(r) + "\n")

        # beide Herkuenfte vorhanden -> zwei Gruppen, eigene zuerst, fremde gekennzeichnet
        block = build_block("/proj/z", reg2, session_id="mein-sess-lang")
        assert "aus diesem Gespraech" in block, block
        assert "aus einem anderen Gespraech" in block, block
        pos_eigen = block.index("aus diesem Gespraech")
        pos_fremd = block.index("aus einem anderen Gespraech")
        assert pos_eigen < pos_fremd, "eigene Gruppe muss zuerst stehen"
        assert block.index("eigene Anweisung") < block.index("fremde Anweisung")
        assert "[fremd-se]" in block, block  # verkuerzte Kennung
        print("  Sitzungstrennung: beide Herkuenfte, eigene zuerst, fremde gekennzeichnet ok")

        # nur eigene -> keine Fremdgruppe, kein leerer Abschnitt
        reg3 = os.path.join(td, "nur_eigene.jsonl")
        with open(reg3, "w", encoding="utf-8") as f:
            for r in rows2[:2]:
                f.write(json.dumps(r) + "\n")
        block = build_block("/proj/z", reg3, session_id="mein-sess-lang")
        assert "aus diesem Gespraech" in block
        assert "aus einem anderen Gespraech" not in block, block
        print("  nur eigene: keine Fremdgruppe ok")

        # nur fremde -> erscheinen trotzdem, gekennzeichnet (keine Unterdrueckung!)
        reg4 = os.path.join(td, "nur_fremde.jsonl")
        with open(reg4, "w", encoding="utf-8") as f:
            for r in rows2[2:]:
                f.write(json.dumps(r) + "\n")
        block = build_block("/proj/z", reg4, session_id="mein-sess-lang")
        assert block is not None
        assert "aus diesem Gespraech" not in block, block
        assert "aus einem anderen Gespraech" in block, block
        assert "fremde Anweisung" in block
        print("  nur fremde: erscheinen trotzdem, gekennzeichnet ok")

        # mehr eigene als Deckel -> nur eigene, Kappungshinweis stimmt, keine fremden
        reg5 = os.path.join(td, "deckel_eigene.jsonl")
        rows5 = [
            {"id": f"e{i}", "ts": f"2026-08-{i+1:02d}T10:00:00Z", "projekt": "/proj/z",
             "session": "mein-sess-lang", "text": f"eigene {i}", "status": "offen"}
            for i in range(7)
        ] + [
            {"id": "frd9", "ts": "2026-08-09T10:00:00Z", "projekt": "/proj/z",
             "session": "fremd-sess-lang", "text": "fremde neun", "status": "offen"},
        ]
        with open(reg5, "w", encoding="utf-8") as f:
            for r in rows5:
                f.write(json.dumps(r) + "\n")
        block = build_block("/proj/z", reg5, session_id="mein-sess-lang")
        assert "aus einem anderen Gespraech" not in block, block
        assert "und 3 weitere" in block, block  # 7 eigene, CAP=5 -> 2 uebrig + 1 fremde verdraengt
        print("  Deckel: eigene haben Vorrang, keine fremden gezeigt ok")

        # fehlende Sitzungskennung -> heutiges Verhalten, keine Ausnahme
        block_mit = build_block("/proj/z", reg2, session_id="mein-sess-lang")
        block_ohne = build_block("/proj/z", reg2, session_id=None)
        assert "aus diesem Gespraech" not in block_ohne, block_ohne
        assert "Offene Anweisungen des Betreibers aus frueheren Nachrichten" in block_ohne, block_ohne
        assert block_mit != block_ohne
        print("  fehlende Sitzungskennung: Fallback aufs bisherige Verhalten ok")

    print(f"selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
