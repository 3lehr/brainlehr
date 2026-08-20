#!/usr/bin/env python3
"""Ausgeliefertes Artefakt gegen seine Quelle -- die Pruefgattung, die fehlte.

ANLASS: Lehre `L-600726`. Alle bisherigen Melder pruefen den Bestand GEGEN
SICH SELBST -- Datenbank gegen Schema, Code gegen Code. Keiner prueft, ob das,
was tatsaechlich LAEUFT (installierter Hook, verdrahteter Pfad), noch der
Quelle entspricht, die im Repo steht. Genau diese Luecke fand am 2026-08-15
untergeschobenen Schadcode auf einer laufenden Homepage -- als Nebenprodukt
der Frage "laeuft online derselbe Stand wie im Repo?".

Drei Vorfaelle derselben Form, alle im eigenen Haus:
  - CLAUDE.md verlangt nach jeder Trigger-Aenderung die INSTALLIERTE Fassung
    zu lesen (`select sql from sqlite_master`), weil `CREATE TRIGGER IF NOT
    EXISTS` nur ERGAENZT, nie ERSETZT (L-55075a).
  - L-083b95: ein Haken-Eintrag verschwand binnen 36 Minuten aus
    settings.json, waehrend der Commit ihn weiter behauptete.
  - L-c9d2aa: eine Pruefung meldete 100 kaputte Dateien, die in
    Arbeitsbaum-Kopien mit eigenem, aelterem Stand lagen.

WAS DIESES MODUL PRUEFT (drei Paare Quelle/Betrieb, die NOCH KEINEN Melder
hatten):
  1. Jeder Git-Haken unter .git/hooks/ (ohne .sample) gegen seine versionierte
     Fassung unter haken/git/ -- Abweichung, fehlende Quelle und fehlende
     Installation sind drei getrennte Befunde.
  2. Jeder Pfad, den ~/.claude/settings.json als Haken-Kommando nennt,
     existiert auf der Platte. Ein Haken, der ins Leere zeigt, laeuft nie und
     meldet das nicht -- ein abgeschalteter Waechter mit gutem Gewissen.
  3. Jeder Melder/Haken-Pfad, den ein Haken-Kommando nennt, liegt in DIESEM
     Repo -- nicht unter einem Arbeitsbaum-Pfad (.claude/worktrees/...), der
     eine aeltere Kopie sein kann (L-c9d2aa).

WAS DIESES MODUL AUSDRUECKLICH NICHT PRUEFT -- vier Paare, die schon einen
Pruefer haben:
  - schema.sql gegen die installierten DB-Trigger      -> melder/schemastand.py
  - schema.sql gegen die installierten DB-Spalten       -> melder/spaltenabgleich.py
  - pre-push-Datei gegen ihre Versionierung             -> tests/test_pre_push_versioniert.py
  - commit-msg-Datei: hat KEINE Pruefung -- genau darum zaehlt sie hier mit,
    siehe Pruefung 1 oben, die pre-push UND commit-msg gemeinsam abdeckt und
    damit die Luecke bei commit-msg erstmals schliesst.

WARUM EIN MELDER STATT DREI: dieselbe Gattung (Quelle vs. Betrieb), derselbe
Befund-Typ (drei-Wege: Abweichung / fehlende Quelle / fehlende Installation
bzw. fehlender Pfad). Drei Skripte fuer dieselbe Frage waeren die Falle, die
`kern/rueckwirkung.py` in seinem eigenen Anlass benennt.

Abschaltbar: BRAINLEHR_QUELLE_GEGEN_BETRIEB=aus (siehe `_aus()`).

    python3 melder/quelle_gegen_betrieb.py --pruefen     # gegen den echten Bestand
    python3 melder/quelle_gegen_betrieb.py --selftest
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken")]

import rueckwirkung as _rw  # noqa: E402 -- gemeinsame Zaehler-Bauform

REPO_WURZEL = _w
GIT_HOOKS_ORDNER = "haken/git"
GLOBALE_SETTINGS = Path.home() / ".claude" / "settings.json"

# Pfade, die in einem Haken-Kommando als Skript-Argument auftauchen.
_PFAD_MUSTER = re.compile(r"(?:/[\w.\-]+)+\.(?:py|sh)\b")


def _aus() -> bool:
    return os.environ.get("BRAINLEHR_QUELLE_GEGEN_BETRIEB", "").strip().lower() == "aus"


# ---------------------------------------------------------------- Pruefung 1
def git_hooken_abgleich(hooks_dir: Path, quelle_dir: Path) -> list[dict]:
    """Jeder installierte Haken (ohne .sample) gegen seine versionierte
    Fassung. Drei Befundarten, namentlich getrennt -- siehe Docstring."""
    befunde: list[dict] = []
    if not hooks_dir.is_dir():
        return befunde
    installierte = {p.name for p in hooks_dir.iterdir()
                     if p.is_file() and not p.name.endswith(".sample")}
    versionierte = {p.name for p in quelle_dir.glob("*")} if quelle_dir.is_dir() else set()

    for name in sorted(installierte | versionierte):
        ist_installiert = name in installierte
        hat_quelle = name in versionierte
        if ist_installiert and not hat_quelle:
            befunde.append({"art": "fehlende_quelle", "haken": name})
        elif hat_quelle and not ist_installiert:
            befunde.append({"art": "fehlende_installation", "haken": name})
        else:
            i_text = (hooks_dir / name).read_text(errors="replace")
            q_text = (quelle_dir / name).read_text(errors="replace")
            if i_text != q_text:
                befunde.append({"art": "abweichung", "haken": name})
    return befunde


# ---------------------------------------------------------------- Pruefung 2+3
def _hook_kommandos(settings_pfad: Path) -> list[str]:
    """Alle 'command'-Strings aus jedem Hook-Eintrag der settings.json."""
    try:
        daten = json.loads(settings_pfad.read_text())
    except (OSError, ValueError):
        return []
    kommandos: list[str] = []
    for eintraege in (daten.get("hooks") or {}).values():
        for gruppe in eintraege:
            for h in gruppe.get("hooks", []):
                cmd = h.get("command")
                if cmd:
                    kommandos.append(cmd)
    return kommandos


def genannte_pfade(settings_pfad: Path) -> list[str]:
    """Jeder Skriptpfad, der in irgendeinem Haken-Kommando vorkommt (dedupliziert,
    Reihenfolge stabil)."""
    gesehen: list[str] = []
    for cmd in _hook_kommandos(settings_pfad):
        for treffer in _PFAD_MUSTER.findall(cmd):
            if treffer not in gesehen:
                gesehen.append(treffer)
    return gesehen


def fehlende_pfade(settings_pfad: Path) -> list[str]:
    """Pruefung 2: welche genannten Pfade existieren nicht auf der Platte."""
    return [p for p in genannte_pfade(settings_pfad) if not Path(p).exists()]


def melder_ausserhalb_repo(settings_pfad: Path, repo_wurzel: Path) -> list[str]:
    """Pruefung 3: welche genannten melder/haken/berichte-Pfade liegen NICHT
    in diesem Repo -- entweder unter einem fremden Baum oder unter einem
    Arbeitsbaum-Pfad (.claude/worktrees/...), der eine aeltere Kopie sein
    kann (L-c9d2aa). Nur Pfade, die tatsaechlich existieren, sind hier
    beurteilbar -- ein fehlender Pfad gehoert zu Pruefung 2."""
    repo_wurzel = repo_wurzel.resolve()
    ergebnis = []
    for roh in genannte_pfade(settings_pfad):
        p = Path(roh)
        if not any(teil in p.parts for teil in ("melder", "haken", "berichte")):
            continue
        if not p.exists():
            continue
        aufgeloest = p.resolve()
        if ".claude" in aufgeloest.parts and "worktrees" in aufgeloest.parts:
            ergebnis.append(roh)
            continue
        try:
            aufgeloest.relative_to(repo_wurzel)
        except ValueError:
            ergebnis.append(roh)
    return ergebnis


# ---------------------------------------------------------------------- bericht
def pruefen(repo_wurzel: Path = REPO_WURZEL,
            settings_pfad: Path = GLOBALE_SETTINGS) -> dict:
    hooks_dir = repo_wurzel / ".git" / "hooks"
    quelle_dir = repo_wurzel / GIT_HOOKS_ORDNER
    hooks = git_hooken_abgleich(hooks_dir, quelle_dir)
    # Die GEPRUEFTEN Mengen wandern mit, weil sie der Nenner sind. Ohne sie
    # zaehlte der Bericht die Befunde gegen sich selbst und meldete bei
    # sauberem Bestand "0 von 0" -- eine Zahl, die nicht unterscheidet, ob
    # 63 Pfade geprueft wurden oder keiner (Norm 17b14a32).
    installierte = {p.name for p in hooks_dir.iterdir()
                    if p.is_file() and not p.name.endswith(".sample")} if hooks_dir.is_dir() else set()
    versionierte = {p.name for p in quelle_dir.glob("*")} if quelle_dir.is_dir() else set()
    alle_pfade = genannte_pfade(settings_pfad)
    melderpfade = [roh for roh in alle_pfade
                   if any(t in Path(roh).parts for t in ("melder", "haken", "berichte"))
                   and Path(roh).exists()]
    return {
        "git_hooken": hooks,
        "fehlende_pfade": fehlende_pfade(settings_pfad),
        "ausserhalb_repo": melder_ausserhalb_repo(settings_pfad, repo_wurzel),
        "geprueft_hooken": sorted(installierte | versionierte),
        "geprueft_pfade": alle_pfade,
        "geprueft_melderpfade": melderpfade,
    }


def bericht(ergebnis: dict) -> str:
    zeilen = []
    befund_haken = {b["haken"]: b["art"] for b in ergebnis["git_hooken"]}
    hb = _rw.zaehle(ergebnis["geprueft_hooken"], lambda n: n in befund_haken,
                    lambda n: f"{befund_haken[n]}: {n}")
    zeilen.append(hb.zeile("git-Haken mit Befund", "gegen haken/git/"))
    for b in ergebnis["git_hooken"]:
        zeilen.append(f"    | {b['art']}: {b['haken']}")

    fehlt = set(ergebnis["fehlende_pfade"])
    fb = _rw.zaehle(ergebnis["geprueft_pfade"], lambda p: p in fehlt, str)
    zeilen.append(fb.zeile("Haken-Pfade ohne Datei", "aus settings.json-Kommandos"))
    for p in ergebnis["fehlende_pfade"]:
        zeilen.append(f"    | {p}")

    draussen = set(ergebnis["ausserhalb_repo"])
    ab = _rw.zaehle(ergebnis["geprueft_melderpfade"], lambda p: p in draussen, str)
    zeilen.append(ab.zeile("Melder-Pfade ausserhalb des Repos", "aus settings.json-Kommandos"))
    for p in ergebnis["ausserhalb_repo"]:
        zeilen.append(f"    | {p}")

    return "\n".join(zeilen)


# -------------------------------------------------------------------- Selbsttest
def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        wurzel = Path(td)
        (wurzel / ".git" / "hooks").mkdir(parents=True)
        (wurzel / "haken" / "git").mkdir(parents=True)
        (wurzel / "melder").mkdir()
        (wurzel / "schema.sql").write_text("")  # markiert Wurzel fuer andere Module irrelevant hier

        hooks = wurzel / ".git" / "hooks"
        quelle = wurzel / "haken" / "git"

        # 1a) Positiv: identischer Inhalt -> kein Befund.
        (hooks / "pre-push").write_text("echo x\n")
        (quelle / "pre-push").write_text("echo x\n")
        befund = git_hooken_abgleich(hooks, quelle)
        assert befund == [], befund

        # 1b) NEGATIV: abweichender Inhalt -> Befundart 'abweichung'.
        (hooks / "commit-msg").write_text("echo a\n")
        (quelle / "commit-msg").write_text("echo b\n")
        befund = git_hooken_abgleich(hooks, quelle)
        assert {"art": "abweichung", "haken": "commit-msg"} in befund, befund

        # 1c) NEGATIV: installiert, keine Quelle.
        (hooks / "pre-commit").write_text("echo c\n")
        befund = git_hooken_abgleich(hooks, quelle)
        assert {"art": "fehlende_quelle", "haken": "pre-commit"} in befund, befund

        # 1d) NEGATIV: Quelle vorhanden, nicht installiert.
        (quelle / "post-checkout").write_text("echo d\n")
        befund = git_hooken_abgleich(hooks, quelle)
        assert {"art": "fehlende_installation", "haken": "post-checkout"} in befund, befund

        # 1e) Grenzwert: .sample-Dateien werden ignoriert.
        (hooks / "pre-push.sample").write_text("egal\n")
        befund = git_hooken_abgleich(hooks, quelle)
        assert not any(b["haken"] == "pre-push.sample" for b in befund), befund

        # 2/3) settings.json mit vier Kommando-Faellen: existierend im Repo,
        #      fehlend, existierend aber unter einem Worktree-Pfad.
        vorhanden = wurzel / "melder" / "echt.py"
        vorhanden.write_text("# ok\n")
        worktree_pfad = wurzel / ".claude" / "worktrees" / "irgendwas" / "melder" / "kopie.py"
        worktree_pfad.parent.mkdir(parents=True)
        worktree_pfad.write_text("# alte Kopie\n")
        settings = wurzel / "settings.json"
        settings.write_text(json.dumps({
            "hooks": {
                "SessionStart": [
                    {"hooks": [
                        {"type": "command",
                         "command": f"python3 {vorhanden} 2>/dev/null || true"},
                        {"type": "command",
                         "command": f"python3 {wurzel}/melder/fehlt_nicht_da.py 2>/dev/null || true"},
                        {"type": "command",
                         "command": f"python3 {worktree_pfad} 2>/dev/null || true"},
                    ]}
                ]
            }
        }))

        # 2a) NEGATIV: existierender Pfad wird nicht als fehlend gemeldet.
        fehlt = fehlende_pfade(settings)
        assert str(vorhanden) not in fehlt, fehlt
        # 2b) Positiv: nicht existierender Pfad wird gemeldet.
        assert any("fehlt_nicht_da.py" in p for p in fehlt), fehlt

        # 3a) NEGATIV: der echte Pfad im Repo wird nicht als 'ausserhalb' gemeldet.
        ausserhalb = melder_ausserhalb_repo(settings, wurzel)
        assert str(vorhanden) not in ausserhalb, ausserhalb
        # 3b) Positiv: der Worktree-Pfad wird gemeldet.
        assert any("kopie.py" in p for p in ausserhalb), ausserhalb

        # Bericht laeuft durch und nennt beide Zahlen je Pruefung.
        ergebnis = pruefen(wurzel, settings)
        text = bericht(ergebnis)
        assert "commit-msg" in text and "kopie.py" in text, text
        # Der NENNER ist die gepruefte Menge, nicht die Befundmenge. Rot vor
        # gruen: die erste Fassung zaehlte die Befunde gegen sich selbst und
        # schrieb bei sauberem Bestand "0 von 0" -- diese Zeile faellt dort.
        assert f"von {len(ergebnis['geprueft_hooken'])}" in text, text
        assert len(ergebnis["geprueft_hooken"]) > len(ergebnis["git_hooken"]), text
        # Und die Gegenprobe: ohne Befund bleibt der Nenner stehen.
        leer = pruefen(wurzel / "leer", settings)
        assert leer["git_hooken"] == [] and "0 von 0" in bericht(leer), bericht(leer)

    # Abschaltung: die Umgebungsvariable wird ausgewertet.
    os.environ["BRAINLEHR_QUELLE_GEGEN_BETRIEB"] = "aus"
    try:
        assert _aus() is True
    finally:
        del os.environ["BRAINLEHR_QUELLE_GEGEN_BETRIEB"]
    assert _aus() is False

    print("quelle_gegen_betrieb: Selbsttest gruen (9 Faelle: identischer Haken "
          "still, Abweichung/fehlende Quelle/fehlende Installation je "
          "namentlich, .sample ignoriert, vorhandener/fehlender/ "
          "Worktree-Pfad je unterschieden, Abschaltung wirkt)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    if _aus():
        print("quelle_gegen_betrieb: abgeschaltet (BRAINLEHR_QUELLE_GEGEN_BETRIEB=aus)")
        return 0
    ergebnis = pruefen()
    print(bericht(ergebnis))
    # Nur die drei BEFUND-Listen entscheiden; die geprueft_*-Mengen sind
    # immer gefuellt und wuerden den Rueckgabewert sonst konstant auf 1 nageln.
    return 1 if any(ergebnis[k] for k in ("git_hooken", "fehlende_pfade", "ausserhalb_repo")) else 0


if __name__ == "__main__":
    sys.exit(main())
