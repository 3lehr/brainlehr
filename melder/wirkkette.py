#!/usr/bin/env python3
"""J2 -- Haken- und Prozessabgleich: was ist WIRKLICH verdrahtet, nicht was
Commit oder Plan behaupten (docs/PLAN_GESAMT_2026-08-13.md, Linie J).

Vorbild `L-b3eb79`: drei Stufen, in denen ein Mechanismus wirkungslos sein
kann, und nur die erste faellt bei der naheliegenden Pruefung auf.

  Stufe 1  GEBAUT, NICHT VERDRAHTET     -- kein Ereignis haengt daran.
  Stufe 2  VERDRAHTET, FALSCHES EREIGNIS -- das Ereignis feuert nicht, wenn
           der Schaden entsteht (Selbstlauf, Subagent, Cron -- ohne
           anwesenden Menschen).
  Stufe 3  WIRKT, MELDUNG VERSCHLUCKT   -- ein spezifischer Fehler wird
           gefangen und weggeworfen, ohne dass sein Text irgendwo ankommt.

Stufe 1 ist bereits gebaut (melder/ausloeserlos.py) -- dieses Modul RUFT sie
auf, statt sie zu duplizieren, und ergaenzt Stufe 2 und Stufe 3.

STUFE 2, konkret: `~/.claude/settings.json` wird nicht als Text durchsucht
(das leistet ausloeserlos.py schon), sondern STRUKTURIERT gelesen -- pro
Ereignisname (UserPromptSubmit, PreToolUse, Stop, ...) die Menge der Skripte,
die daran haengen (direkt oder ueber einen bereits verdrahteten Aufrufer,
transitiv). `UserPromptSubmit` ist der belegte Blindgaenger-Fall
(`haken/mcp_veraltet.py`, `L-b3eb79` Stufe 2 woertlich): dieses Ereignis
feuert nur, wenn ein Mensch einen Prompt abschickt -- ein Subagent tut das
nie. Haengt ein Mechanismus AUSSCHLIESSLICH an diesem Ereignis (kein
zusaetzliches, kein Cron), ist er im Selbstlauf blind, obwohl "verdrahtet"
technisch stimmt.

STUFE 3, bewusst schmal geschnitten: eine `except Exception:`/bare-except
Huelle um die ganze Ausfuehrung ist HIER SYSTEMWEITE ABSICHT (siehe
ausloeserlos.py-Kopf: "IMMER exit 0", dasselbe Muster in praktisch jedem
Melder) -- sie als Fund zu melden waere eine Mehrheitsentscheidung gegen die
eigene Bauform, keine Erkenntnis (`L-528f0c`). Gemeldet wird nur der enger
gefasste, am realen Vorfall (Modellsperre-Trigger, `sqlite3.IntegrityError`
verschluckt) orientierte Fall: ein NAMENTLICH SPEZIFISCHER Fehlertyp (nicht
Exception/BaseException, nicht die als Infrastruktur-Rueckzug ausgenommene
Familie -- sqlite3.Error/OSError samt Dateisystem-Existenzfehlern wie
FileNotFoundError/JSONDecodeError, siehe STUFE3_BREITE_FANGTYPEN) wird mit
einem reinen `pass`-Rumpf gefangen, UND der try-Block ist kein Testidiom
'assert False, ...; except: pass' (erwarteter Wurf, kein Befund). Erste
Fassung ohne diese beiden Ausnahmen traf 6 von 28 verdrahteten Kandidaten --
ALLE sechs erwiesen sich bei Einzelpruefung als genau diese zwei Muster,
keiner als echter Fund (gemessen 2026-08-15). Nachgeschaerft statt verdrahtet
(L-528f0c): am heutigen Bestand von melder/haken/berichte trifft der engere
Check auf keine Datei zu -- das macht den Fund selten, nicht falsch, ein
scharfes Merkmal darf leer sein.

HINWEISRECHT, KEIN VETO (wie ausloeserlos.py): immer Exit 0.

Aufruf:
    python3 wirkkette.py --bericht    # alle drei Stufen, ausfuehrlich
    python3 wirkkette.py --melder     # nur sprechen, wenn etwas anschlaegt
    python3 wirkkette.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import argparse
import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(_w / "haken"))
import ort  # noqa: E402
import ausloeserlos  # noqa: E402 -- Stufe 1 wird von hier wiederverwendet, nicht dupliziert

DIESE_DATEI = Path(__file__).resolve()

# Belegter Fall (L-b3eb79 Stufe 2, haken/mcp_veraltet.py): dieses Ereignis
# feuert nur, wenn ein Mensch im Chat einen Prompt abschickt. Ein Subagent,
# ein Selbstlauf ohne neue Eingabe, ein Cron-Aufruf loesen es nie aus --
# also genau dann still, wenn der Schaden im Hintergrund entsteht.
EVENTS_BLIND_IM_SELBSTLAUF = {"UserPromptSubmit"}

# Breite, hier als Infrastruktur-Rueckzug akzeptierte Fangtypen (Stufe 3
# meldet sie NICHT, siehe Modulkopf) -- ein reiner Name-Vergleich auf den
# entzuckerten Typ-Ausdruck (ast.unparse).
STUFE3_BREITE_FANGTYPEN = {
    "Exception", "BaseException", "sqlite3.Error", "OSError", "IOError",
    # Dateisystem-Existenzfamilie: dieselbe Infrastruktur-Rueckzug-Begruendung
    # wie OSError (siehe Modulkopf) -- "Datei/Zwischenstand fehlt (noch)" ist
    # kein verlorener Befund, sondern der Normalfall beim ersten Lauf. Ohne
    # diese Erweiterung feuerte der Check am echten Bestand ausschliesslich
    # auf genau diesem Muster (haken/antwort_abruf.py:546,
    # haken/knowledge_recall_hook.py:1520 -- gemessen 2026-08-15, siehe
    # Modulkopf), nie auf einen echten Fund: Fehlkonstruktion, nachtraeglich
    # geschaerft statt verdrahtet (L-528f0c).
    "FileNotFoundError", "FileExistsError", "IsADirectoryError",
    "NotADirectoryError", "PermissionError",
    "json.JSONDecodeError", "json.decoder.JSONDecodeError", "JSONDecodeError",
}


def _event_map(settings_pfade: list[Path | None]) -> dict[str, str]:
    """Ereignisname -> zusammengefasster Befehlstext, STRUKTURIERT aus dem
    JSON gelesen (nicht als flacher Text wie in ausloeserlos.py) -- nur so
    laesst sich einem Fund ein EreignisNAME zuordnen."""
    sammlung: dict[str, list[str]] = {}
    for sp in settings_pfade:
        if sp is None or not sp.exists():
            continue
        try:
            d = json.loads(sp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for ev, eintraege in (d.get("hooks") or {}).items():
            for eintrag in eintraege:
                for h in eintrag.get("hooks", []):
                    sammlung.setdefault(ev, []).append(h.get("command", ""))
    return {ev: "\n".join(cmds) for ev, cmds in sammlung.items()}


def ereignisse_von(pfad: Path, quellen: dict[Path, str], event_map: dict[str, str],
                    besucht: frozenset[Path] = frozenset(),
                    memo: dict[Path, set[str]] | None = None) -> set[str]:
    """Alle Ereignisnamen, ueber die `pfad` erreichbar ist -- direkt oder
    transitiv ueber einen Aufrufer, der selbst an einem Ereignis haengt.
    Cron zaehlt als eigenes Pseudo-Ereignis ('cron'), NICHT blind im
    Selbstlauf (ein Cron braucht per Definition keinen Menschen).

    `memo` ist zwingend ueber EINEN bericht()-Lauf hinweg zu teilen (nicht
    je Kandidat neu) -- ohne sie besucht jeder der ~45 Kandidaten denselben
    Aufrufer-Graphen erneut, quadratisch bis schlimmer bei ueberlappenden
    Aufrufketten. Gemessen: ohne Memoisierung lief der Selbsttest am echten
    Bestand (439 .py-Dateien) nicht in vertretbarer Zeit durch."""
    if memo is None:
        memo = {}
    if pfad in memo:
        return memo[pfad]
    if pfad in besucht:
        return set()  # Ring im Aufrufergraphen: nicht cachen, nur abbrechen
    besucht = besucht | {pfad}
    treffer = {ev for ev, txt in event_map.items() if pfad.name in txt}
    for rufer in ausloeserlos.rufer_von(pfad, quellen):
        treffer |= ereignisse_von(rufer, quellen, event_map, besucht, memo)
    memo[pfad] = treffer
    return treffer


def blind_im_selbstlauf(events: set[str]) -> bool:
    """True, wenn ein Mechanismus VERDRAHTET ist, aber ausschliesslich an
    Ereignissen haengt, die ohne anwesenden Menschen nie feuern."""
    return bool(events) and events <= EVENTS_BLIND_IM_SELBSTLAUF


def _ist_breiter_fangtyp(typ_knoten: ast.expr) -> bool:
    """Ein Tupel zaehlt als breit, sobald JEDES Element darin breit ist
    (z.B. `except (OSError, json.JSONDecodeError):`) -- ein einzelner
    spezifischer Typ im Tupel reicht, um das Ganze als spezifisch zu
    behandeln."""
    if isinstance(typ_knoten, ast.Tuple):
        return all(_ist_breiter_fangtyp(e) for e in typ_knoten.elts)
    try:
        return ast.unparse(typ_knoten) in STUFE3_BREITE_FANGTYPEN
    except Exception:
        return False


def _ist_erwarteter_wurf_test(try_rumpf: list[ast.stmt]) -> bool:
    """Testidiom 'assert False, ...' im try-Rumpf: die Probe erwartet
    ausdruecklich, dass eine Ausnahme fliegt -- das nachfolgende `except:
    pass` bestaetigt nur den Wurf, verschluckt keinen Befund. Gemessen am
    echten Bestand fielen 4 von 6 Rohtreffern in dieses Muster
    (melder/rasterblick.py x3, haken/knowledge_recall_hook.py x1)."""
    return any(isinstance(s, ast.Assert) and isinstance(s.test, ast.Constant)
               and s.test.value is False for s in try_rumpf)


def meldung_verschluckt(pfad: Path) -> list[str]:
    """Stufe 3, siehe Modulkopf: `except <spezifischer Name>: pass`, kein
    breiter Fangtyp, kein Testidiom 'muss werfen'. Syntaxfehler in der Datei
    -> stiller leerer Befund, kein Absturz (Hinweisrecht)."""
    try:
        quelle = pfad.read_text(encoding="utf-8", errors="replace")
        baum = ast.parse(quelle)
    except (OSError, SyntaxError):
        return []
    funde = []
    for knoten in ast.walk(baum):
        if not isinstance(knoten, ast.Try):
            continue
        if _ist_erwarteter_wurf_test(knoten.body):
            continue
        for handler in knoten.handlers:
            if handler.type is None:
                continue  # bare except zaehlt hier als breit, nicht spezifisch
            if _ist_breiter_fangtyp(handler.type):
                continue
            try:
                name = ast.unparse(handler.type)
            except Exception:
                continue
            rumpf = handler.body
            if len(rumpf) == 1 and isinstance(rumpf[0], ast.Pass):
                funde.append(f"{pfad.name}:{handler.lineno} except {name}: pass")
    return funde


def bericht(repo_root: Path, settings_pfade: list[Path | None]) -> dict[str, list]:
    """Alle drei Stufen fuer die Kandidaten unter melder/haken/berichte.
    Stufe 1 wird von ausloeserlos.py UEBERNOMMEN (nicht neu gerechnet).
    Stufe 2 und 3 werden nur fuer Kandidaten geprueft, die Stufe 1 bereits
    bestehen -- ein unverdrahteter Mechanismus hat kein Ereignis, ueber das
    Stufe 2 ueberhaupt eine Aussage treffen koennte."""
    quellen = ausloeserlos.alle_quellen(repo_root)
    settings_txt = ausloeserlos.settings_texte(settings_pfade)
    geplante_txt = ausloeserlos.hole_geplante_texte()
    event_map = _event_map(settings_pfade)

    stufe1 = ausloeserlos.bericht(repo_root, settings_pfade)

    stufe2, stufe3 = [], []
    ereignis_memo: dict[Path, set[str]] = {}
    for p in ausloeserlos.kandidaten(repo_root):
        if p.resolve() == DIESE_DATEI:
            continue
        ok, _weg = ausloeserlos.hat_ausloeser(p, quellen, settings_txt, geplante_txt)
        if not ok:
            continue  # Stufe 1 hat das schon gemeldet
        events = ereignisse_von(p, quellen, event_map, memo=ereignis_memo)
        if blind_im_selbstlauf(events):
            stufe2.append({
                "name": str(p.relative_to(repo_root)),
                "ereignisse": sorted(events),
            })
        for zeile in meldung_verschluckt(p):
            stufe3.append({"name": str(p.relative_to(repo_root)), "fund": zeile})

    return {"stufe1": stufe1, "stufe2": stufe2, "stufe3": stufe3}


def render(funde: dict[str, list]) -> str:
    if not any(funde.values()):
        return ("wirkkette: keine Funde auf allen drei Stufen -- jeder Kandidat "
                "unter melder/, haken/, berichte/ haengt an einem Ereignis, das "
                "auch im Selbstlauf feuert, und keine gefangene Meldung wird "
                "sichtbar weggeworfen.")
    zeilen = ["wirkkette: Soll/Wirklichkeit-Abgleich fuer Haken und Prozesse "
              "(L-b3eb79, drei Stufen):"]
    if funde["stufe1"]:
        zeilen.append(f"  Stufe 1 -- gebaut, nicht verdrahtet ({len(funde['stufe1'])}):")
        for f in funde["stufe1"]:
            zeilen.append(f"    - {f['name']}")
    if funde["stufe2"]:
        zeilen.append(f"  Stufe 2 -- verdrahtet, aber blind im Selbstlauf ({len(funde['stufe2'])}):")
        for f in funde["stufe2"]:
            zeilen.append(f"    - {f['name']} (nur {', '.join(f['ereignisse'])})")
    if funde["stufe3"]:
        zeilen.append(f"  Stufe 3 -- Meldung moeglicherweise verschluckt ({len(funde['stufe3'])}):")
        for f in funde["stufe3"]:
            zeilen.append(f"    - {f['fund']}")
    zeilen.append("Hinweisrecht, kein Veto -- geprueft wird die Existenz eines "
                  "Blindflecks, nicht seine Schadenswirkung im Einzelfall.")
    return "\n".join(zeilen)


def _settings_pfade() -> list[Path | None]:
    return [Path.home() / ".claude" / "settings.json",
            ort.WURZEL / ".claude" / "settings.json"]


def _selftest() -> None:
    import tempfile

    # -- Stufe 2: nur-UserPromptSubmit ist blind, ein zusaetzliches Ereignis
    # oder ein Cron-Eintrag rettet den Fund.
    assert blind_im_selbstlauf({"UserPromptSubmit"}) is True
    assert blind_im_selbstlauf({"UserPromptSubmit", "Stop"}) is False
    assert blind_im_selbstlauf({"UserPromptSubmit", "cron"}) is False
    assert blind_im_selbstlauf({"PreToolUse"}) is False
    assert blind_im_selbstlauf(set()) is False, "kein Ereignis ist Stufe 1, nicht Stufe 2"
    print("  Stufe-2-Einstufung: Grenzwerte (nur blind / plus ein Ereignis / kein Ereignis): ok")

    # -- Stufe 2 REAL, am tatsaechlichen Bestand (Positivkontrolle):
    # haken/mcp_veraltet.py haengt seit L-b3eb79 ausschliesslich an
    # UserPromptSubmit. Nur LESEN (haken/ ist tabu fuer diesen Auftrag).
    quellen = ausloeserlos.alle_quellen(ort.WURZEL)
    event_map = _event_map(_settings_pfade())
    ziel = ort.WURZEL / "haken" / "mcp_veraltet.py"
    if ziel.exists() and "UserPromptSubmit" in event_map:
        events = ereignisse_von(ziel, quellen, event_map)
        assert blind_im_selbstlauf(events), (
            f"haken/mcp_veraltet.py sollte als blind im Selbstlauf gelten, "
            f"gemessene Ereignisse: {events} -- entweder wurde es inzwischen "
            "zusaetzlich verdrahtet (Befund, kein Fehler dieses Tests) oder "
            "die Einstufung ist kaputt")
        print("  Stufe 2 am echten Bestand (haken/mcp_veraltet.py, nur gelesen): ok")
    else:
        print("  Stufe 2 am echten Bestand: uebersprungen (Datei oder Ereignis fehlt)")

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "schema.sql").write_text("-- Attrappe\n")
        for ordner in ("melder", "haken", "berichte"):
            (root / ordner).mkdir()

        # (a) POSITIVKONTROLLE Stufe 1, nachgebaut aus melder/vektorstand.py
        # VOR seiner Reparatur (Commit 591149ef): kein settings.json-Eintrag,
        # kein Import durch einen Pruefer, keine SOLLEN_LAUFEN-Zeile. Kopie,
        # kein Eingriff in die echte Datei.
        (root / "melder" / "vektorstand_vor_reparatur.py").write_text(
            '"""Ein Vektor, der einen Text beschreibt, den es so nicht mehr '
            'gibt -- und niemand fragt danach. (Nachbau des Zustands vor '
            'Commit 591149ef, siehe git show 591149ef^:melder/vektorstand.py)"""\n'
            "def melden(conn=None):\n    return None\n"
        )

        # (b) Stufe 2 synthetisch: nur UserPromptSubmit -> Fund.
        (root / "haken" / "nur_prompt.py").write_text('"""tut etwas."""\nprint("x")\n')

        # (c) Negativfall Stufe 2: zusaetzlich PreToolUse -> KEIN Fund.
        (root / "haken" / "prompt_und_pretooluse.py").write_text('"""tut etwas."""\nprint("x")\n')

        # (d) Stufe 3 positiv: spezifischer Fehlertyp, reiner pass-Rumpf.
        (root / "melder" / "verschluckt_spezifisch.py").write_text(
            '"""tut etwas."""\n'
            "import sqlite3\n"
            "def schreiben(conn):\n"
            "    try:\n"
            "        conn.execute('INSERT INTO t VALUES (1)')\n"
            "    except sqlite3.IntegrityError:\n"
            "        pass\n"
        )

        # (e) Negativfall Stufe 3: derselbe spezifische Typ, aber die
        # Meldung wird NICHT weggeworfen (gedruckt) -- kein Fund.
        (root / "melder" / "verschluckt_gemeldet.py").write_text(
            '"""tut etwas."""\n'
            "import sqlite3\n"
            "def schreiben(conn):\n"
            "    try:\n"
            "        conn.execute('INSERT INTO t VALUES (1)')\n"
            "    except sqlite3.IntegrityError as e:\n"
            "        print(e)\n"
        )

        # (f) Negativfall Stufe 3: breiter Fangtyp (systemweite Absicht,
        # siehe Modulkopf) -- kein Fund, auch mit reinem pass-Rumpf.
        (root / "melder" / "breiter_fang_ist_absicht.py").write_text(
            '"""tut etwas."""\n'
            "def main():\n"
            "    print('gefunden')\n"
            "try:\n"
            "    main()\n"
            "except Exception:\n"
            "    pass\n"
        )

        # (g) sauber verdrahteter Negativfall ueber alle drei Stufen:
        # PreToolUse, kein spezifischer verschluckter Fehler.
        (root / "melder" / "sauber_verdrahtet.py").write_text(
            '"""tut etwas, meldet alles."""\nprint("ok")\n'
        )

        settings_pfad = root / "settings.json"
        settings_pfad.write_text(json.dumps({
            "hooks": {
                "UserPromptSubmit": [{"hooks": [
                    {"type": "command", "command": "python3 haken/nur_prompt.py"},
                    {"type": "command", "command": "python3 haken/prompt_und_pretooluse.py"},
                ]}],
                "PreToolUse": [{"hooks": [
                    {"type": "command", "command": "python3 haken/prompt_und_pretooluse.py"},
                    {"type": "command", "command": "python3 melder/sauber_verdrahtet.py"},
                ]}],
                "Stop": [{"hooks": [
                    {"type": "command", "command": "python3 melder/verschluckt_spezifisch.py"},
                    {"type": "command", "command": "python3 melder/verschluckt_gemeldet.py"},
                    {"type": "command", "command": "python3 melder/breiter_fang_ist_absicht.py"},
                ]}],
            }
        }))

        alt = globals()["ausloeserlos"].DIESE_DATEI
        try:
            funde = bericht(root, [settings_pfad, None])
        finally:
            globals()["ausloeserlos"].DIESE_DATEI = alt

        namen_s1 = {f["name"] for f in funde["stufe1"]}
        namen_s2 = {f["name"] for f in funde["stufe2"]}
        namen_s3 = {f["name"] for f in funde["stufe3"]}

        assert "melder/vektorstand_vor_reparatur.py" in namen_s1, (
            "Positivkontrolle Stufe 1 (Nachbau vektorstand vor Reparatur) "
            "haette gefunden werden muessen -- Merkmal falsch gewaehlt")
        print("  (a) Positivkontrolle: vektorstand-Nachbau vor Reparatur -> Stufe-1-Fund: ok")

        assert "haken/nur_prompt.py" in namen_s2
        print("  (b) nur UserPromptSubmit -> Stufe-2-Fund: ok")

        assert "haken/prompt_und_pretooluse.py" not in namen_s2, (
            "zusaetzlich an PreToolUse verdrahtet, darf NICHT als blind gelten")
        print("  (c) Negativfall: zusaetzliches Ereignis rettet vor Stufe 2: ok")

        assert "melder/verschluckt_spezifisch.py" in namen_s3
        print("  (d) spezifischer Fehlertyp mit reinem pass-Rumpf -> Stufe-3-Fund: ok")

        assert "melder/verschluckt_gemeldet.py" not in namen_s3, \
            "die Meldung wird gedruckt, ist also nicht verschluckt"
        print("  (e) Negativfall: derselbe Fehlertyp, aber gemeldet -> kein Fund: ok")

        assert "melder/breiter_fang_ist_absicht.py" not in namen_s3, \
            "except Exception: pass ist systemweite Absicht, kein Fund"
        print("  (f) Negativfall: breiter Fangtyp (Absicht) -> kein Fund: ok")

        assert "melder/sauber_verdrahtet.py" not in namen_s1
        assert "melder/sauber_verdrahtet.py" not in namen_s2
        assert "melder/sauber_verdrahtet.py" not in namen_s3
        print("  (g) sauber verdrahteter Mechanismus -> auf keiner Stufe gemeldet: ok")

        # Sanity gegen Fehlkonstruktion (L-528f0c): keine Stufe darf die
        # Mehrheit der verdrahteten Kandidaten treffen.
        wired = [n for n in ("haken/nur_prompt.py", "haken/prompt_und_pretooluse.py",
                             "melder/verschluckt_spezifisch.py", "melder/verschluckt_gemeldet.py",
                             "melder/breiter_fang_ist_absicht.py", "melder/sauber_verdrahtet.py")]
        assert len(namen_s2) < len(wired) / 2, "Stufe 2 trifft die Mehrheit -- Fehlkonstruktion"
        assert len(namen_s3) < len(wired) / 2, "Stufe 3 trifft die Mehrheit -- Fehlkonstruktion"
        print("  Sanity: keine Stufe trifft die Mehrheit der verdrahteten Kandidaten: ok")

        text = render(funde)
        assert "vektorstand_vor_reparatur.py" in text
        assert "Hinweisrecht, kein Veto" in text
        print("  render() zeigt alle drei Stufen mit dem Hinweisrecht-Satz: ok")

    # -- Sanity am ECHTEN Bestand: Stufe 3 darf nicht die Mehrheit der
    # verdrahteten Kandidaten treffen (misst, meldet nicht messerscharf).
    echte_funde = bericht(ort.WURZEL, _settings_pfade())
    verdrahtet = len(ausloeserlos.kandidaten(ort.WURZEL)) - len(echte_funde["stufe1"])
    if verdrahtet > 0:
        anteil_s3 = len(echte_funde["stufe3"]) / verdrahtet
        assert anteil_s3 < 0.5, (
            f"Stufe 3 trifft {anteil_s3:.0%} der verdrahteten Kandidaten am "
            "echten Bestand -- Fehlkonstruktion, kein Befund (L-528f0c)")
        print(f"  echter Bestand: {verdrahtet} verdrahtete Kandidaten, "
              f"{len(echte_funde['stufe2'])} Stufe-2-, {len(echte_funde['stufe3'])} "
              "Stufe-3-Funde (keine Mehrheit): ok")

    print("selftest ok")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bericht", action="store_true")
    p.add_argument("--melder", action="store_true")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return

    funde = bericht(ort.WURZEL, _settings_pfade())
    if a.melder:
        if any(funde.values()):
            print(render(funde))
        return
    print(render(funde))


if __name__ == "__main__":
    main()
