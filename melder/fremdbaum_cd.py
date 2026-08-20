#!/usr/bin/env python3
"""Wiederholtes `cd <fremdes Repo>` im Bash-Aufruf -- die Sitzung, die im
falschen Baum arbeitet.

ANLASS: `L-bdfeef` (3x, high, `escalated_to_rule`). Kern der Lehre: Ein `cd`
im Bash-Aufruf wechselt nur das Arbeitsverzeichnis DIESES Aufrufs, nicht den
Verankerungspunkt der Sitzung (geladene CLAUDE.md, Melder, STAND-Abruf).
Nichts warnt dabei -- jeder einzelne Befehl gelingt. Die Lehre selbst nennt
das Erkennungszeichen woertlich: "mehr als zwei Bash-Aufrufe hintereinander
beginnen mit `cd <anderer Pfad>`".

WARUM MELDER UND NICHT SPERRE: Ein PreToolUse-Haken, der `cd` am
Werkzeugaufruf ablehnt, waere die staerkere Sperre -- aber `haken/git/*` und
jeder verdrahtete Klienten-Haken sind hier tabu (fremde Baustelle), und ein
Verbot von `cd` an sich waere falsch: `cd` in ein UNTERVERZEICHNIS des eigenen
Projekts ist taeglich noetig. Blockierbar ist nur die Wiederholung in einen
ANDEREN Projektbaum -- und die ist erst als MUSTER erkennbar, nicht am
einzelnen Aufruf. Die Lehre selbst haelt fest: der ehrliche Ausweg ist eine
neue Sitzung, kein technischer Zwang. Dieser Melder liefert dafuer die
Sichtbarkeit: er liest, was ohnehin protokolliert wird (Sitzungs-Transkripte),
und zaehlt, wie oft das Muster tatsaechlich auftrat.

WIE ERKANNT: Jede Sitzungsdatei (`~/.claude/projects/**/*.jsonl`) traegt an
jedem Assistenten-Eintrag ein `cwd`-Feld -- das ist der Verankerungspunkt
dieser Sitzung, gesetzt vom Klienten, nicht vom letzten `cd`. Innerhalb der
Sitzung wird jeder `Bash`-Werkzeugaufruf daraufhin geprueft, ob sein Kommando
mit `cd <pfad>` beginnt und `<pfad>` zu einem ANDEREN Projekt gehoert als der
Anker (Projektname = Verzeichnis unmittelbar nach `<arbeitsbereich>/`, oder die
ersten vier Pfadteile, wenn `<arbeitsbereich>` fehlt -- das faengt auch
Arbeitsbaum-Pfade wie `.claude/worktrees/...` als "gleiches Projekt" ab, weil
sie unterhalb desselben Projektnamens haengen, es sei denn der Pfad wechselt
das Repo). Drei oder mehr solcher `cd`-Aufrufe HINTEREINANDER in dieselbe
fremde Wurzel sind ein Treffer -- Wortlaut der Lehre: "mehr als zwei".

Abschaltbar: BRAINLEHR_FREMDBAUM_CD=aus.

    python3 melder/fremdbaum_cd.py --pruefen     # gegen die echten Transkripte
    python3 melder/fremdbaum_cd.py --selftest
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

SCHWELLE = 3  # "mehr als zwei" -- Wortlaut der Lehre
_CD_MUSTER = re.compile(r'^\s*cd\s+(?:"([^"]+)"|\'([^\']+)\'|(\S+))')

# SCHAERFUNG (Nachschlag 2026-08-20): Die Lehre beschreibt den Schaden als
# "im falschen Baum SCHREIBEN" -- Lesen (grep/cat/ls/git status/git diff/git
# log) ist Alltag und harmlos. Ein Treffer zaehlt nur, wenn innerhalb der
# Fremdbaum-Serie mindestens ein SCHREIBENDER Befehl vorkam. Heuristisch,
# nicht vollstaendig: erkennt Shell-Text, keine Semantik. `2>&1`/`2>/dev/null`
# sind haeufige Stderr-Umlenkungen und werden bewusst NICHT als Schreiben
# gewertet (negative lookbehind auf eine Ziffer vor `>`).
_SCHREIB_MUSTER = re.compile(
    r'\bgit\s+(?:commit|add|checkout|reset|rm|mv)\b'
    r'|\bsed\s+-i\b'
    r'|\brm\s'
    r'|\bmv\s'
    r'|\bcp\s'
    r'|\bmkdir\s'
    r'|\btee\b'
    r'|(?<!\d)>{1,2}(?!&)'
)


def ist_schreibend(kommando: str) -> bool:
    """Enthaelt das Kommando einen SCHREIBENDEN Befehl (Commit/Add/Checkout/
    Reset, Datei-Umlenkung, sed -i, rm/mv/cp/mkdir, tee) -- als Gegensatz zu
    reinem Lesen (grep/cat/ls/git status/git diff/git log/...)."""
    return bool(_SCHREIB_MUSTER.search(kommando))


def _aus() -> bool:
    return os.environ.get("BRAINLEHR_FREMDBAUM_CD", "").strip().lower() == "aus"


def projekt(pfad: str) -> str:
    """Projektname eines Pfads -- das Verzeichnis nach '<arbeitsbereich>', sonst die
    ersten vier Pfadteile. Ein Arbeitsbaum (.claude/worktrees/...) traegt
    denselben Projektnamen wie sein Hauptcheckout, ein fremdes Repo nicht."""
    teile = Path(pfad).parts
    if "Begod2026" in teile:
        i = teile.index("Begod2026")
        if i + 1 < len(teile):
            return teile[i + 1]
    return "/".join(teile[:4])


def cd_ziel(kommando: str) -> str | None:
    """Das Ziel eines fuehrenden `cd`, oder None wenn das Kommando nicht mit
    `cd` beginnt. Nimmt auch `cd <pfad> && ...` -- der Regex verlangt kein
    Zeilenende."""
    treffer = _CD_MUSTER.match(kommando)
    if not treffer:
        return None
    return next(g for g in treffer.groups() if g)


def _bash_kommandos(sitzungsdatei: Path) -> tuple[str | None, list[str]]:
    """(Anker-cwd der Sitzung, alle Bash-Kommandos in Reihenfolge)."""
    anker = None
    kommandos: list[str] = []
    try:
        roh = sitzungsdatei.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return anker, kommandos
    for zeile in roh.splitlines():
        if '"tool_use"' not in zeile and '"cwd"' not in zeile:
            continue
        try:
            z = json.loads(zeile)
        except ValueError:
            continue
        if z.get("type") != "assistant":
            continue
        if anker is None and z.get("cwd"):
            anker = z["cwd"]
        for c in (z.get("message") or {}).get("content") or []:
            if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Bash":
                cmd = (c.get("input") or {}).get("command")
                if cmd:
                    kommandos.append(cmd)
    return anker, kommandos


def fremdlaeufe(anker: str, kommandos: list[str]) -> list[tuple[int, str, bool]]:
    """Alle MAXIMALEN Folgen aufeinanderfolgender Bash-Kommandos, die mit `cd`
    in dieselbe fremde Projektwurzel beginnen. Je Folge (Laenge, Projektname,
    schreibend) -- schreibend ist True, wenn IRGENDEIN Kommando der Folge
    `ist_schreibend()` ist (nicht nur das `cd` selbst, meist `cd X && Y`)."""
    eigen = projekt(anker) if anker else None
    laeufe: list[tuple[int, str, bool]] = []
    lauf: list[str] = []
    laufprojekt: str | None = None

    def _abschliessen() -> None:
        if lauf:
            laeufe.append((len(lauf), laufprojekt, any(ist_schreibend(c) for c in lauf)))

    for cmd in kommandos:
        ziel = cd_ziel(cmd)
        p = projekt(ziel) if ziel else None
        fremd = ziel is not None and eigen is not None and p != eigen
        if fremd and p == laufprojekt:
            lauf.append(cmd)
        elif fremd:
            _abschliessen()
            lauf = [cmd]
            laufprojekt = p
        else:
            _abschliessen()
            lauf = []
            laufprojekt = None
    _abschliessen()
    return laeufe


def laengster_fremdlauf(anker: str, kommandos: list[str]) -> tuple[int, str | None]:
    """Laenge und Projekt der laengsten Fremdbaum-Serie -- Projektname None,
    wenn kein `cd` vorkam."""
    laeufe = fremdlaeufe(anker, kommandos)
    if not laeufe:
        return 0, None
    laenge, proj, _ = max(laeufe, key=lambda t: t[0])
    return laenge, proj


def schreibender_fremdlauf(anker: str, kommandos: list[str]) -> tuple[int, str | None]:
    """Wie `laengster_fremdlauf`, aber nur unter den Serien ab SCHWELLE, die
    mindestens einen SCHREIBENDEN Befehl enthalten. (0, None), wenn keine
    solche Serie vorkommt -- auch wenn eine rein lesende Serie existiert."""
    kandidaten = [(l, p) for l, p, schreibt in fremdlaeufe(anker, kommandos)
                  if l >= SCHWELLE and schreibt]
    if not kandidaten:
        return 0, None
    return max(kandidaten, key=lambda t: t[0])


def sitzungsdateien(wurzel: Path | None = None, dateien: int = 300) -> list[Path]:
    """Nur HAUPTSITZUNGEN, keine Subagenten-Transkripte (`agent-*.jsonl`).

    STICHPROBE 2026-08-20 deckte das auf: von 167 Treffern ueber den vollen
    Bestand waren 153 (92 %) Subagenten -- deren `cwd` ist die des
    AUFRUFENDEN Elternprozesses, nicht ein eigener Verankerungspunkt, und ihr
    Auftrag lautet routinemaessig "arbeite in Repo B" (siehe CLAUDE.md,
    Abschnitt Agentenauftraege). Ein Subagent, der dorthin `cd`t, tut genau
    das Vorgesehene -- das ist nicht die Lehre L-bdfeef, sondern deren
    Gegenteil. Ungefiltert waere die Quote (56,6 %) also die falsche Zahl."""
    w = wurzel or (Path.home() / ".claude" / "projects")
    try:
        pfade = sorted(w.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return []
    pfade = [p for p in pfade if not p.name.startswith("agent-")]
    return pfade[:dateien]


def pruefen(wurzel: Path | None = None, dateien: int = 300) -> dict:
    """Treffer bleibt die ROHE Fremdbaum-Serie (>= SCHWELLE, jedes `cd`)
    -- NICHT auf schreibende Serien verengt. Gemessen am 2026-08-20
    (Nachschlag zum Erstlauf): unter den 105 rohen Treffern hatten 89 (84,8 %)
    zusaetzlich eine Serie MIT schreibendem Befehl (`git commit`/`add`,
    Datei-Umlenkung, `sed -i`, `rm`/`mv`/`cp`/`mkdir`) -- die Stichprobe zeigt
    echte `git commit`-Serien in fremden Repos ohne deren CLAUDE.md. Die
    Schaerfung TRENNT DIE KLASSE ALSO NICHT (Richtwert fuer eine Trennung
    waere unter 25 % gewesen); sie WUERDE das Signal nur um 15 % verkleinern,
    ohne den ueberwiegenden Anteil zu entlasten. Deshalb bleibt der rohe
    Treffer der Massstab, das schreibend-Flag wird als ZUSATZINFORMATION je
    Treffer mitgefuehrt (Feld `schreibt`), nicht als Filter."""
    geprueft = []  # nur Sitzungen mit mindestens einem Bash-Aufruf zaehlen als Nenner
    treffer = {}
    for pfad in sitzungsdateien(wurzel, dateien):
        anker, kommandos = _bash_kommandos(pfad)
        if not kommandos or not anker:
            continue
        geprueft.append(pfad)
        lauf, projektname = laengster_fremdlauf(anker, kommandos)
        if lauf >= SCHWELLE:
            schreibt = any(l >= SCHWELLE and s for l, _, s in fremdlaeufe(anker, kommandos))
            treffer[pfad] = (lauf, projektname, anker, schreibt)
    return {"geprueft": geprueft, "treffer": treffer}


def bericht(ergebnis: dict) -> str:
    treffer = ergebnis["treffer"]
    b = _rw.zaehle(ergebnis["geprueft"], lambda p: p in treffer,
                   lambda p: f"{p.name}: {treffer[p][0]}x cd nach {treffer[p][1]} "
                             f"(Anker {treffer[p][2]}, schreibend={treffer[p][3]})")
    zeilen = [b.zeile("Sitzungen mit Fremdbaum-cd-Serie (>= 3 hintereinander)",
                      f"ueber die juengsten {len(ergebnis['geprueft'])} Sitzungsdateien mit Bash-Aufrufen")]
    for x in b.beispiele:
        zeilen.append("    | " + x)
    # ZUSATZ, siehe pruefen()-Docstring: schaerft NICHT, zeigt nur, wie viele
    # der Treffer zusaetzlich eine schreibende Serie hatten. Nenner ist die
    # TREFFERMENGE, nicht geprueft -- eine andere Frage als die Hauptzeile.
    if treffer:
        sb = _rw.zaehle(list(treffer.keys()), lambda p: treffer[p][3], hoechstens_beispiele=0)
        zeilen.append(sb.zeile("  davon mit schreibendem Befehl in der Fremdbaum-Serie",
                               "unter den obigen Treffern"))
    return "\n".join(zeilen)


# -------------------------------------------------------------------- Selbsttest
def _selftest() -> int:
    anker = "/Volumes/daten/Begod2026/brainlehr"

    # 1) POSITIV: drei cd hintereinander in dasselbe fremde Projekt.
    kommandos = [
        "cd /Volumes/daten/Begod2026/openlehr && python3 -m pytest",
        "cd /Volumes/daten/Begod2026/openlehr && git status",
        "cd /Volumes/daten/Begod2026/openlehr && git add -p foo.py",
    ]
    lauf, proj = laengster_fremdlauf(anker, kommandos)
    assert lauf == 3 and proj == "openlehr", (lauf, proj)

    # 2) POSITIV: vier hintereinander, unterbrochen von einem NICHT-cd-Befehl
    #    zaehlt als zwei getrennte Laeufe (2 und 1) -- der laengste ist 2.
    kommandos2 = [
        "cd /Volumes/daten/Begod2026/openlehr && ls",
        "cd /Volumes/daten/Begod2026/openlehr && cat x",
        "echo dazwischen",
        "cd /Volumes/daten/Begod2026/openlehr && ls",
    ]
    lauf2, _ = laengster_fremdlauf(anker, kommandos2)
    assert lauf2 == 2, lauf2

    # 3) NEGATIV: cd bleibt im EIGENEN Projekt (Unterverzeichnis) -> kein Treffer.
    kommandos3 = [
        "cd /Volumes/daten/Begod2026/brainlehr/melder && ls",
        "cd /Volumes/daten/Begod2026/brainlehr/kern && ls",
        "cd /Volumes/daten/Begod2026/brainlehr/tool && ls",
    ]
    lauf3, _ = laengster_fremdlauf(anker, kommandos3)
    assert lauf3 == 0, lauf3

    # 4) NEGATIV: cd in fremdes Projekt, aber nur EIN Mal (unter Schwelle 3).
    kommandos4 = [
        "cd /Volumes/daten/Begod2026/openlehr && ls",
        "pwd",
    ]
    lauf4, _ = laengster_fremdlauf(anker, kommandos4)
    assert lauf4 == 1 and lauf4 < SCHWELLE, lauf4

    # 5) Grenzwert: ein Arbeitsbaum-Pfad desselben Projekts zaehlt NICHT als fremd.
    kommandos5 = [
        "cd /Volumes/daten/Begod2026/brainlehr/.claude/worktrees/baum-1 && ls",
        "cd /Volumes/daten/Begod2026/brainlehr/.claude/worktrees/baum-1 && cat x",
        "cd /Volumes/daten/Begod2026/brainlehr/.claude/worktrees/baum-1 && git status",
    ]
    lauf5, _ = laengster_fremdlauf(anker, kommandos5)
    assert lauf5 == 0, lauf5

    # ROT-PROBE: eine bewusst kaputte Erkennung (haelt jedes Projekt fuer
    # gleich, erkennt also NIE ein fremdes `cd`) gegen denselben Fall-1-Input.
    # Die Behauptung "das ist ein Treffer" (lauf == 3) muss an dieser kaputten
    # Fassung SCHEITERN -- sonst waere Fall 1 kein Beleg, sondern haette auch
    # bei einer wirkungslosen Erkennung gruen angezeigt.
    def kaputt_projekt(_pfad: str) -> str:
        return "immer_gleich"

    def kaputt_lauf(anker_: str, kommandos_: list[str]) -> int:
        eigen = kaputt_projekt(anker_)
        bester = lauf_ = 0
        for cmd in kommandos_:
            ziel = cd_ziel(cmd)
            fremd = ziel is not None and kaputt_projekt(ziel) != eigen
            lauf_ = lauf_ + 1 if fremd else 0
            bester = max(bester, lauf_)
        return bester

    kaputtes_ergebnis = kaputt_lauf(anker, kommandos)
    schlug_fehl = False
    try:
        assert kaputtes_ergebnis == 3, kaputtes_ergebnis
    except AssertionError:
        schlug_fehl = True
    assert schlug_fehl, "Rot-Probe wirkungslos: die kaputte Fassung haette hier scheitern muessen"
    assert kaputtes_ergebnis == 0, kaputtes_ergebnis

    # 6) SCHAERFUNG POSITIV: 3er-Serie MIT schreibendem Befehl (git commit)
    #    -> schreibender_fremdlauf findet sie.
    kommandos6 = [
        "cd /Volumes/daten/Begod2026/openlehr && cat x.py",
        "cd /Volumes/daten/Begod2026/openlehr && git commit -m fix -- x.py",
        "cd /Volumes/daten/Begod2026/openlehr && git status",
    ]
    slauf6, sproj6 = schreibender_fremdlauf(anker, kommandos6)
    assert slauf6 == 3 and sproj6 == "openlehr", (slauf6, sproj6)

    # 7) SCHAERFUNG NEGATIV: 3er-Serie NUR mit Lesebefehlen (grep/cat/ls/git
    #    status/git diff/git log) -> kein schreibender Treffer, obwohl die
    #    ROHE Erkennung (laengster_fremdlauf) hier durchaus 3 meldet.
    kommandos7 = [
        "cd /Volumes/daten/Begod2026/openlehr && grep -rn foo .",
        "cd /Volumes/daten/Begod2026/openlehr && cat x.py",
        "cd /Volumes/daten/Begod2026/openlehr && git status --short && git diff --stat && git log --oneline -5",
    ]
    slauf7, sproj7 = schreibender_fremdlauf(anker, kommandos7)
    assert (slauf7, sproj7) == (0, None), (slauf7, sproj7)
    # Die ROHE Erkennung findet dieselbe Serie sehr wohl -- Beleg, dass die
    # Schaerfung tatsaechlich eine ANDERE, engere Frage beantwortet.
    roh7, _ = laengster_fremdlauf(anker, kommandos7)
    assert roh7 == 3, roh7

    # ROT-PROBE zur Schaerfung: eine kaputte Fassung, die JEDE Fremdbaum-Serie
    # blind als "schreibend" durchwinkt (== die alte, ungeschaerfte Logik),
    # MUSS am Negativfall (Fall 7, reine Lesebefehle) falsch liegen --
    # sonst waere Fall 7 kein Beleg fuer die Schaerfung.
    def kaputt_schreibend_immer(anker_, kommandos_):
        l, p = laengster_fremdlauf(anker_, kommandos_)
        return (l, p) if l >= SCHWELLE else (0, None)

    kaputt7 = kaputt_schreibend_immer(anker, kommandos7)
    schlug_fehl_7 = False
    try:
        assert kaputt7 == (0, None), kaputt7
    except AssertionError:
        schlug_fehl_7 = True
    assert schlug_fehl_7, "Rot-Probe der Schaerfung wirkungslos: die alte Logik haette hier faelschlich getroffen"
    assert kaputt7 == (3, "openlehr"), kaputt7

    # cd_ziel: Anfuehrungszeichen und reines cd ohne &&.
    assert cd_ziel('cd "/x/y z" && ls') == "/x/y z"
    assert cd_ziel("cd /x/y") == "/x/y"
    assert cd_ziel("ls -la") is None

    # bericht() nennt den Nenner (Zahl gepruefter Sitzungen), nicht nur die Treffer.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        w = Path(td)
        treffer_datei = w / "treffer.jsonl"
        treffer_datei.write_text("\n".join(
            json.dumps({"type": "assistant", "cwd": anker,
                        "message": {"content": [{"type": "tool_use", "name": "Bash",
                                                   "input": {"command": c}}]}})
            for c in kommandos))
        sauber_datei = w / "sauber.jsonl"
        sauber_datei.write_text("\n".join(
            json.dumps({"type": "assistant", "cwd": anker,
                        "message": {"content": [{"type": "tool_use", "name": "Bash",
                                                   "input": {"command": c}}]}})
            for c in kommandos3))
        ergebnis = pruefen(w)
        assert len(ergebnis["geprueft"]) == 2, ergebnis
        assert len(ergebnis["treffer"]) == 1, ergebnis
        text = bericht(ergebnis)
        assert "1 von 2" in text and "openlehr" in text, text

        # Sauberer Bestand -> "0 von N", kein Falschtreffer.
        ergebnis_sauber = pruefen(w, dateien=1)  # nur die juengste (sauber.jsonl)
        # dateien=1 nimmt nach mtime die zuletzt geschriebene -- beide fast
        # gleichzeitig geschrieben, daher hier ueber alle pruefen und Treffer-
        # freiheit fuer die bekannt saubere Datei einzeln zusichern.
        anker2, kommandos_sauber = _bash_kommandos(sauber_datei)
        lauf_sauber, _ = laengster_fremdlauf(anker2, kommandos_sauber)
        assert lauf_sauber == 0

    # Abschaltung
    os.environ["BRAINLEHR_FREMDBAUM_CD"] = "aus"
    try:
        assert _aus() is True
    finally:
        del os.environ["BRAINLEHR_FREMDBAUM_CD"]
    assert _aus() is False

    print("fremdbaum_cd: Selbsttest gruen (5 Erkennungsfaelle + Rot-Probe + "
          "Nenner im Bericht + 2 Schaerfungsfaelle (schreibend/nur-lesend) + "
          "Schaerfungs-Rot-Probe + Abschaltung)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    if _aus():
        print("fremdbaum_cd: abgeschaltet (BRAINLEHR_FREMDBAUM_CD=aus)")
        return 0
    ergebnis = pruefen()
    print(bericht(ergebnis))
    return 1 if ergebnis["treffer"] else 0


if __name__ == "__main__":
    sys.exit(main())
