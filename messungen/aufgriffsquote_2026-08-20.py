#!/usr/bin/env python3
"""S1 aus docs/PLAN_ZWEITES_SIGNAL_2026-08-20.md -- Aufgriffsquote ueber den
GESAMTEN verfuegbaren Zeitraum (alle Transkripte dieses Repos, alle Worktrees,
2026-08-08 bis heute), nicht nur einen Tag.

Baut auf melder/abrufwirkung.py auf (kennungen_aus_block, wortgrenzen_treffer,
transkript_zeilen -- alle bereits durch tests/test_abrufwirkung.py belegt).
NICHT wiederverwendet: abrufwirkung.lauf()/git_verwendungen() selbst, weil sie
git-Commits PRO TRANSKRIPT neu abfragen (31 Dateien x ~1121 Commits x 2
Subprozesse waere ein Vielfaches der Laufzeit). Stattdessen: EIN git-Dump,
EIN Parsdurchlauf, dann global pro Kennung geprueft -- gleiche Logik
(Wortgrenzen, Zeitrichtung), andere Bauform fuer die Haeufigkeit.

Nur lesend: Transkripte und git log werden gelesen, nichts geschrieben ausser
dem Ergebnis unter runs/.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(REPO), str(REPO / "melder"), str(REPO / "kern")]

import abrufwirkung as aw  # noqa: E402
import zeitmarke  # noqa: E402
import rueckwirkung  # noqa: E402

GIT_SEIT = "2026-08-08 00:00"
PROJECTS_ROOT = Path.home() / ".claude" / "projects"


# --- 1. Alle Transkripte dieses Repos finden --------------------------------

def alle_transkripte() -> list[Path]:
    out = []
    for d in PROJECTS_ROOT.glob("-Volumes-daten-Begod2026-brainlehr*"):
        if not d.is_dir():
            continue
        out.extend(sorted(d.glob("*.jsonl")))
    return out


# --- 2. Aus jedem Transkript: Einspielungen + Werkzeugtexte (Agent/knowledge_add/lesson_record) ---

def _ts_utc_oder_none(ts) -> str | None:
    if not ts:
        return None
    try:
        return zeitmarke.nach_utc(ts)
    except ValueError:
        return None


def sammle_transkript(pfad: Path) -> tuple[list[dict], list[dict]]:
    """(recalls, werkzeugtexte) -- beide global datiert (UTC-ISO), damit sie
    ueber Dateien hinweg vergleichbar sind (anders als 'seq', das nur
    innerhalb EINER Datei zaehlt)."""
    recalls: list[dict] = []
    werkzeuge: list[dict] = []
    for seq, d in aw.transkript_zeilen(pfad):
        ts = _ts_utc_oder_none(d.get("timestamp"))
        att = d.get("attachment")
        if isinstance(att, dict) and att.get("type") == "hook_additional_context":
            inhalt = att.get("content") or []
            text = "\n".join(c for c in inhalt if isinstance(c, str))
            if "<knowledge-recall>" in text:
                for kennung, art in aw.kennungen_aus_block(text).items():
                    recalls.append({"kennung": kennung, "art": art, "ts": ts,
                                     "datei": pfad.name, "seq": seq})
        texte = aw._tool_use_texte(d, aw._WERKZEUGE_AUFTRAG | aw._WERKZEUGE_SCHREIBEND)
        for t in texte:
            werkzeuge.append({"ts": ts, "text": t, "datei": pfad.name, "seq": seq})
    return recalls, werkzeuge


# --- 3. Git-Kanal: EIN Dump statt N -----------------------------------------

_COMMIT_SPLIT_RE = re.compile(r"\x02")


# FALLE (waehrend dieser Messung selbst gefunden, siehe Bericht):
# auszug/bestand_*.jsonl ist ein TAEGLICHER VOLLEXPORT der Wissensdatenbank
# (2200 bis 5223 "path"-Eintraege je Datei) -- jede Kennung, die je existiert
# hat, steht darin, ganz ohne dass sie je "benutzt" wurde. runs/deckelreihe_*
# und runs/wissenskorpus_import_* sind Messartefakte, die selbst tausende
# L-Kennungen als Rohdaten enthalten (Parametersweeps, Importstatistik) --
# keine Zitate. spikes/ und docs/karten/*.json sind generiert bzw. fremder
# Code. Ohne Ausschluss zaehlt der taegliche Bestands-Commit praktisch jede
# existierende Kennung faelschlich als "im Commit gefunden" -- das ist der
# Pruefstand, der mitmisst (CLAUDE.md: 'Der Pruefstand misst mit'), keine
# Wirkung. Commit-NACHRICHTEN bleiben unbeschraenkt (Pfadfilter wirkt nur auf
# den Diff-Inhalt der Commits, die weiterhin gelistet werden).
_GIT_AUSSCHLUSS = [
    ":!auszug/*", ":!auszug-offen/*", ":!runs/*", ":!spikes/*",
    ":!docs/karten/*", ":!berichte/statisch/*",
    # NACHTRAG (zweite Runde): git rm --cached von recall_log.jsonl/
    # zero_hit_log.jsonl/wissensverlauf.jsonl (Commit d153f24d) loescht
    # 864/815/881 Zeilen -- als Diff-DELETION, numstat zeigt sie in Spalte
    # 'geloescht', nicht 'hinzugefuegt'. Reine Protokolldateien, keine
    # Zitate; jede vor 2026-08-08T19:24 eingespielte Kennung stuende sonst
    # als 'in diesem Commit gefunden' da, nur weil sie irgendwann geloggt
    # wurde.
    ":!recall_log.jsonl", ":!zero_hit_log.jsonl", ":!wissensverlauf.jsonl",
    # NACHTRAG (dritte Runde, Befund des Auftraggebers): NODE_INDEX.md
    # (kern/build_node_index.py -- "Landkarte aller Knoten", listet die
    # NEUESTE_N juengsten Knoten/Lehren mit vollem Pfad/Titel) und
    # antwort_treffer.json (Kandidatenliste je Session mit path+title+
    # bedeutungs_kosinus) sind beides ERZEUGTE Dateien, die bei praktisch
    # jeder Aenderung Kennungen in Masse fuehren, ohne dass sie benutzt
    # wurden. Ebenso docs/WAS_BRAINLEHR_KANN.md (tool/faehigkeitskarte.py,
    # "erzeugt aus dem Quellcode"). melder/landkarten.py wurde geprueft --
    # schreibt ausschliesslich nach docs/karten/*.json|md (schon oben).
    ":!NODE_INDEX.md", ":!antwort_treffer.json", ":!docs/WAS_BRAINLEHR_KANN.md",
]


def git_commits_einmal(wurzel: Path, seit: str) -> list[tuple[str, str, str]]:
    """[(hash, ts_utc, text=Nachricht+Diff)] chronologisch (aeltester zuerst),
    EIN Prozessaufruf statt 2 * anzahl_commits (Falle: 'git show' pro Commit
    ist bei ueber tausend Commits der teuerste Teil der Messung). Diff-Inhalt
    schliesst bekannte Massenexport-/Messartefakt-Verzeichnisse aus (siehe
    _GIT_AUSSCHLUSS) -- Commit-Nachrichten bleiben immer vollstaendig."""
    lauf = subprocess.run(
        ["git", "-C", str(wurzel), "log", "--since", seit, "--reverse",
         "--format=%x02%H%x1f%aI%x1f%B%x03", "-p",
         "--", ".", *_GIT_AUSSCHLUSS],
        capture_output=True, text=True, check=False,
    )
    out = []
    for block in _COMMIT_SPLIT_RE.split(lauf.stdout):
        if "\x1f" not in block:
            continue
        kopf, rest = block.split("\x03", 1) if "\x03" in block else (block, "")
        teile = kopf.split("\x1f", 2)
        if len(teile) < 3:
            continue
        h, ts_roh, nachricht = teile
        try:
            ts_utc = zeitmarke.nach_utc(ts_roh.strip())
        except ValueError:
            continue
        out.append((h, ts_utc, nachricht + "\n" + rest))
    return out


# --- 4. Aufgriff je Kennung global pruefen ----------------------------------

def aufgriff_pruefen(kennung: str, art: str, frueheste_einspielung: str,
                      werkzeuge_sortiert: list[dict],
                      commits: list[tuple[str, str, str]]) -> dict:
    """Liefert {benutzt: bool, quelle, ts, echo: bool, echo_quelle}.

    'benutzt' zaehlt nur Treffer STRIKT NACH frueheste_einspielung (Falle
    Zeitrichtung). 'echo' meldet, ob es OHNE diese Zeitschranke einen
    (frueheren) Treffer gegeben haette -- das ist der Scheintreffer-Fall aus
    dem Auftrag: der Commit/Werkzeugaufruf hat die Kennung selbst ERZEUGT,
    bevor sie je eingespielt wurde."""
    ist_pfad = art == "knoten"

    frueheste_valide = None
    frueheste_beliebige = None
    for w in werkzeuge_sortiert:
        if w["ts"] is None:
            continue
        if not aw.wortgrenzen_treffer(w["text"], kennung, ist_pfad):
            continue
        if frueheste_beliebige is None:
            frueheste_beliebige = {"ts": w["ts"], "quelle": f"transkript:{w['datei']}#{w['seq']}"}
        if w["ts"] > frueheste_einspielung and frueheste_valide is None:
            frueheste_valide = {"ts": w["ts"], "quelle": f"transkript:{w['datei']}#{w['seq']}"}
            break  # chronologisch sortiert -> erster valider Treffer reicht

    if frueheste_valide is None:
        for h, ts_utc, text in commits:
            if not aw.wortgrenzen_treffer(text, kennung, ist_pfad):
                continue
            if frueheste_beliebige is None or ts_utc < frueheste_beliebige["ts"]:
                if frueheste_beliebige is None:
                    frueheste_beliebige = {"ts": ts_utc, "quelle": f"git:{h[:8]}"}
            if ts_utc > frueheste_einspielung:
                frueheste_valide = {"ts": ts_utc, "quelle": f"git:{h[:8]}"}
                break

    if frueheste_valide is not None:
        return {"benutzt": True, **frueheste_valide, "echo": False, "echo_quelle": None}
    if frueheste_beliebige is not None:
        return {"benutzt": False, "ts": None, "quelle": None,
                "echo": True, "echo_quelle": frueheste_beliebige["quelle"]}
    return {"benutzt": False, "ts": None, "quelle": None, "echo": False, "echo_quelle": None}


# --- 5. Alter in Tagen -------------------------------------------------------

def _alter_tage(frueheste_ts: str, jetzt_ts: str) -> float | None:
    try:
        a = zeitmarke.nach_utc(frueheste_ts)
        b = zeitmarke.nach_utc(jetzt_ts)
    except ValueError:
        return None
    from datetime import datetime
    da = datetime.fromisoformat(a.replace("Z", "+00:00"))
    db = datetime.fromisoformat(b.replace("Z", "+00:00"))
    return round((db - da).total_seconds() / 86400.0, 2)


# --- Hauptlauf ---------------------------------------------------------------

def hauptlauf() -> dict:
    jetzt_ts = zeitmarke.jetzt()
    dateien = alle_transkripte()

    alle_recalls: list[dict] = []
    alle_werkzeuge: list[dict] = []
    dateien_ok, dateien_fehler = 0, []
    for pfad in dateien:
        try:
            r, w = sammle_transkript(pfad)
        except (OSError, UnicodeDecodeError) as e:
            dateien_fehler.append({"datei": str(pfad), "fehler": str(e)})
            continue
        alle_recalls.extend(r)
        alle_werkzeuge.extend(w)
        dateien_ok += 1

    alle_werkzeuge = [w for w in alle_werkzeuge if w["ts"] is not None]
    alle_werkzeuge.sort(key=lambda w: w["ts"])

    commits = git_commits_einmal(REPO, GIT_SEIT)

    # frueheste Einspielung je Kennung, ueber ALLE Dateien hinweg.
    art_je_kennung: dict[str, str] = {}
    frueheste: dict[str, str] = {}
    haeufigkeit: Counter = Counter()
    for e in alle_recalls:
        k = e["kennung"]
        haeufigkeit[k] += 1
        art_je_kennung[k] = e["art"]
        if e["ts"] is None:
            continue
        if k not in frueheste or e["ts"] < frueheste[k]:
            frueheste[k] = e["ts"]

    kennungen_ohne_zeitstempel = sorted(set(art_je_kennung) - set(frueheste))

    ergebnis_je_kennung: dict[str, dict] = {}
    for k, art in art_je_kennung.items():
        if k not in frueheste:
            continue
        ergebnis_je_kennung[k] = aufgriff_pruefen(k, art, frueheste[k], alle_werkzeuge, commits)

    # --- Kennzahlen --------------------------------------------------------
    kennungen_gesamt = len(ergebnis_je_kennung)
    benutzt = {k: v for k, v in ergebnis_je_kennung.items() if v["benutzt"]}
    echo = {k: v for k, v in ergebnis_je_kennung.items() if v["echo"]}

    quote = rueckwirkung.zaehle(
        ergebnis_je_kennung.items(),
        lambda kv: kv[1]["benutzt"],
        lambda kv: f"{kv[0]} -> {kv[1]['quelle']}",
        hoechstens_beispiele=15,
    )

    nach_typ: dict[str, dict] = {}
    for typ in ("knoten", "lehre"):
        teilmenge = {k: v for k, v in ergebnis_je_kennung.items() if art_je_kennung[k] == typ}
        b = rueckwirkung.zaehle(teilmenge.items(), lambda kv: kv[1]["benutzt"])
        nach_typ[typ] = {"nenner": b.nenner, "treffer": b.treffer, "quote_prozent": round(100 * b.quote, 1)}

    alter_bins = [(0, 1), (1, 3), (3, 7), (7, 999)]
    nach_alter: dict[str, dict] = {}
    for lo, hi in alter_bins:
        label = f"{lo}-{hi if hi < 999 else 'inf'}_tage"
        teilmenge = {k: v for k, v in ergebnis_je_kennung.items()
                     if (a := _alter_tage(frueheste[k], jetzt_ts)) is not None and lo <= a < hi}
        b = rueckwirkung.zaehle(teilmenge.items(), lambda kv: kv[1]["benutzt"])
        nach_alter[label] = {"nenner": b.nenner, "treffer": b.treffer,
                              "quote_prozent": round(100 * b.quote, 1) if b.nenner else None}

    top3 = haeufigkeit.most_common(3)
    top3_anteil = round(100 * sum(n for _, n in top3) / sum(haeufigkeit.values()), 1) if haeufigkeit else 0.0

    # STREUENDE Stichprobe (Auftraggeber-Befund): chronologisch sortieren
    # reiht faktisch nach Quelle, weil viele Treffer aus demselben Commit
    # stammen (Reihenfolge im Diff). Stattdessen: je Quelle (Datei bzw.
    # Commit-Hash) nur der ERSTE Treffer, bis 10 verschiedene Quellen stehen.
    stichprobe_benutzt_sortiert = sorted(benutzt.items(), key=lambda kv: kv[1]["ts"])
    stichprobe_benutzt: list[tuple[str, dict]] = []
    gesehene_quellen: set[str] = set()
    for k, v in stichprobe_benutzt_sortiert:
        if v["quelle"] in gesehene_quellen:
            continue
        gesehene_quellen.add(v["quelle"])
        stichprobe_benutzt.append((k, v))
        if len(stichprobe_benutzt) >= 10:
            break
    stichprobe_echo = sorted(echo.items())[:10]

    return {
        "messung": "Aufgriffsquote -- S1 aus docs/PLAN_ZWEITES_SIGNAL_2026-08-20.md",
        "erstellt": jetzt_ts,
        "protokoll_nur_gelesen": True,
        "bezugsrahmen": {
            "beschreibung": ("alle .jsonl-Transkripte unter ~/.claude/projects/, deren "
                              "Verzeichnisname mit '-Volumes-daten-Begod2026-brainlehr' beginnt "
                              "(Hauptrepo + alle Worktrees), git log seit '" + GIT_SEIT + "'"),
            "dateien_gefunden": len(dateien),
            "dateien_ausgewertet": dateien_ok,
            "dateien_fehler": dateien_fehler,
            "commits_seit_git_seit": len(commits),
            "zeitspanne_aelteste_einspielung": min(frueheste.values()) if frueheste else None,
            "zeitspanne_juengste_einspielung": max(frueheste.values()) if frueheste else None,
        },
        "nenner": {
            "verschiedene_kennungen_mit_zeitstempel": kennungen_gesamt,
            "kennungen_ohne_auswertbaren_zeitstempel": len(kennungen_ohne_zeitstempel),
            "einspielungen_roh_gesamt": sum(haeufigkeit.values()),
            "top3_anteil_prozent": top3_anteil,
            "top3_kennungen": [{"kennung": k, "einspielungen": n} for k, n in top3],
            "hinweis_top3": ("> 50% hiesse: die Zahl beschreibt die Suche (wenige, oft "
                              "gezogene Kennungen), nicht die Wirkung -- siehe melder/abrufwirkung.py."),
        },
        "aufgriffsquote": {
            "zeile": quote.zeile("Aufgriff (Kennung spaeter belegt verwendet)",
                                  f"ueber {kennungen_gesamt} verschiedene eingespielte Kennungen, "
                                  f"{sum(haeufigkeit.values())} Einspielungen roh, Zeitraum "
                                  f"{min(frueheste.values()) if frueheste else '?'} bis {jetzt_ts}"),
            "treffer": quote.treffer,
            "nenner": quote.nenner,
            "quote_prozent": round(100 * quote.quote, 1),
            "beispiele": quote.beispiele,
        },
        "aufschluesselung_nach_typ": nach_typ,
        "aufschluesselung_nach_alter_der_einspielung": nach_alter,
        "aufschluesselung_nach_staerke_des_treffers": {
            "verfuegbar": False,
            "grund": ("Weder recall_log.jsonl noch der eingespielte Blocktext (siehe "
                      "haken/knowledge_recall_hook.py Zeile ~1849, 'f\"<knowledge-recall>\\n{satz}\\n"
                      "</knowledge-recall>\"') fuehren einen Aehnlichkeitswert oder eine Stark/"
                      "Schwach-Lage mit. Der Wert EXISTIERT zur Rechenzeit (bedeutungs_kosinus in "
                      "kern/relevanzlage.py, sichtbar z.B. in antwort_treffer.json), wird aber NICHT "
                      "in recall_log.jsonl persistiert -- also eine Persistenzluecke, keine "
                      "prinzipielle Datenluecke. STARK_AB in kern/relevanzlage.py existiert nur als "
                      "spaeter geplante Ausgabestufe (Plan S2), NICHT im heutigen Protokoll."),
            "folge_fuer_s2": ("Wird die Ausgabe auf abgestufte Stark/Schwach-Anzeige umgestellt, "
                              "OHNE vorher den Score je Kennung in recall_log.jsonl mitzuschreiben, "
                              "ist NACH der Umstellung nicht mehr messbar, ob die Stufung richtig "
                              "lag -- die Nulllinie fuer 'stark' vs. 'schwach' fehlt dann fuer immer, "
                              "aus demselben Grund, aus dem dieser gesamte Lauf VOR S2 laufen musste. "
                              "Empfehlung: recall_log.jsonl um ein Score-Feld je Kennung ergaenzen, "
                              "BEVOR S2 scharf geschaltet wird."),
        },
        "echo_faelle_ausgeschlossen": {
            "definition": ("Kennung hat KEINEN Treffer nach ihrer fruehesten Einspielung, aber "
                            "einen Treffer VOR/AN ihr -- der Commit oder Werkzeugaufruf hat die "
                            "Kennung selbst erzeugt/zitiert, bevor sie ueberhaupt eingespielt "
                            "wurde. Diese Faelle stehen NICHT im Zaehler oben (schon vorab "
                            "ausgefiltert durch die Zeitschranke), werden hier separat benannt."),
            "anzahl": len(echo),
            "anteil_an_allen_kennungen_prozent": round(100 * len(echo) / kennungen_gesamt, 1) if kennungen_gesamt else 0.0,
            "beispiele": [{"kennung": k, "echo_quelle": v["echo_quelle"]} for k, v in stichprobe_echo],
        },
        "stichprobe_von_hand_benutzt": [
            {"kennung": k, "art": art_je_kennung[k], "ts_erster_treffer": v["ts"], "quelle": v["quelle"]}
            for k, v in stichprobe_benutzt
        ],
        "kennungen_ohne_zeitstempel_beispiele": kennungen_ohne_zeitstempel[:10],
    }


# Vorlaeufe DIESES Auftrags, vor Erweiterung des Ausschlusses (im Bericht
# als Befund ausgewiesen, siehe 'vorlaeufe_dieses_auftrags' unten):
#   Lauf 1 (kein Ausschluss ausser NICHTS)                 61.9% (789/1275)
#     -- auszug/bestand_*.jsonl (Tagesvollexport der DB) faelschte fast
#        jede existierende Kennung zu 'benutzt', weil sie im Export steht.
#   Lauf 2 (auszug/runs/spikes/docs-karten ausgeschlossen)  20.0% (255/1275)
#     -- Fund des Auftraggebers: NODE_INDEX.md und antwort_treffer.json
#        (beide generiert, listen Kennungen in Masse) waren noch nicht
#        ausgeschlossen; 9 von 10 Stichprobentreffern kamen aus einem
#        einzigen NODE_INDEX.md-Commit.
#   Lauf 3 (dieser Lauf): zusaetzlich NODE_INDEX.md, antwort_treffer.json,
#        docs/WAS_BRAINLEHR_KANN.md ausgeschlossen.
_VORLAEUFE = [
    {"lauf": 1, "quote_prozent": 61.9, "treffer": 789, "nenner": 1275,
     "ausschluss": "keiner", "befund": "auszug/bestand_*.jsonl (Tagesvollexport) faelscht praktisch jede Kennung zu 'benutzt'"},
    {"lauf": 2, "quote_prozent": 20.0, "treffer": 255, "nenner": 1275,
     "ausschluss": "auszug/, auszug-offen/, runs/, spikes/, docs/karten/, berichte/statisch/, recall_log.jsonl, zero_hit_log.jsonl, wissensverlauf.jsonl",
     "befund": "Stichprobe zu 9/10 aus einem Commit (NODE_INDEX.md); NODE_INDEX.md und antwort_treffer.json fehlten noch im Ausschluss"},
]


if __name__ == "__main__":
    ergebnis = hauptlauf()
    ergebnis["vorlaeufe_dieses_auftrags"] = {
        "hinweis": ("Drei Messlaeufe noetig, weil jeder vorherige Lauf einen neuen "
                    "Pruefstand-Artefakt fand (generierte Dateien, die Kennungen in Masse "
                    "fuehren, ohne dass je jemand sie benutzt haette). Die Differenz "
                    "zwischen den Laeufen IST der Befund, nicht nur ein Zwischenschritt."),
        "laeufe": _VORLAEUFE,
        "dieser_lauf_quote_prozent": ergebnis["aufgriffsquote"]["quote_prozent"],
    }
    text = json.dumps(ergebnis, ensure_ascii=False, indent=1)
    print(text)
    ziel = REPO / "runs" / "aufgriffsquote_2026-08-20.json"
    ziel.write_text(text, encoding="utf-8")
    print(f"\ngeschrieben nach {ziel}", file=sys.stderr)
