"""Der Selbsttest von melder/agentendauer.py laeuft mit -- sonst ist er ein
Skript, das niemand aufruft (siehe test_alle_selftests.py). Zusaetzlich hier:
die Positivkontrolle aus dem Auftrag (2026-08-15) gegen die ECHTE
Protokolldatei der laufenden Sitzung -- kein konstruierter Fall, sondern der
belegte laengste Lauf des Tages ("Sechs blinde Mechanismen",
1334164 ms / 204640 Token / 97 Werkzeugaufrufe)."""

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import sys
from pathlib import Path

import json
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "melder"))

import agentendauer  # noqa: E402

SESSION = (
    Path.home() / ".claude" / "projects"
    / "-Volumes-daten-Begod2026-brainlehr--claude-worktrees-baum-20260815T054407-65075"
    / "01c01c7f-2c38-4eff-96e5-2e3d8e4d9677.jsonl"
)


def test_selftest():
    agentendauer._selftest()


def test_usage_regex_gegen_positivkontrolle():
    """Die drei Zahlen aus dem Auftrag muessen exakt aus dem <usage>-Tag
    fallen -- kein Runden, kein Umrechnen."""
    text = ("<usage><subagent_tokens>204640</subagent_tokens>"
            "<tool_uses>97</tool_uses><duration_ms>1334164</duration_ms></usage>")
    m = agentendauer.USAGE_RE.search(text)
    assert m.groups() == ("204640", "97", "1334164")


@pytest.mark.skipif(not SESSION.exists(), reason="Sitzungsprotokoll nicht vorhanden (anderer Rechner/Nutzer)")
def test_positivkontrolle_echte_sitzung():
    """Findet das Werkzeug den laengsten Lauf des Tages mit genau den drei
    im Auftrag genannten Zahlen? Wenn nicht, ist zuerst das Werkzeug
    verdaechtig, nicht das Protokoll (Auftrag, woertlich)."""
    laeufe = agentendauer.sammle([SESSION])
    treffer = [l for l in laeufe if l.dauer_ms == 1334164]
    assert len(treffer) == 1, f"erwartet genau ein Treffer, gefunden: {len(treffer)}"
    l = treffer[0]
    assert l.tokens == 204640
    assert l.werkzeugaufrufe == 97
    assert l.beschreibung == "Sechs blinde Mechanismen"


@pytest.mark.skipif(not SESSION.exists(), reason="Sitzungsprotokoll nicht vorhanden (anderer Rechner/Nutzer)")
def test_gegenprobe_gleichzeitigkeit_echte_sitzung():
    """Es muss mindestens einen allein laufenden UND einen mit vielen
    parallelen Laeufen geben -- sonst waere Gleichzeitigkeit nie ein
    Stoerfaktor gewesen (Auftrag: 'Kannst du keinen Unterschied zeigen,
    sag das ausdruecklich')."""
    laeufe = agentendauer.sammle([SESSION])
    mit_intervall = [l for l in laeufe if l.gleichzeitig_max is not None]
    allein = [l for l in mit_intervall if l.gleichzeitig_max == 1]
    viele = [l for l in mit_intervall if (l.gleichzeitig_max or 0) >= 5]
    assert allein, "kein allein laufender Agent gefunden"
    assert viele, "kein Agent mit mind. 5 gleichzeitigen Laeufen gefunden"



def _agent_werkzeugaufruf_ids(pfad) -> set:
    """Die tool_use_id JEDES Agent-Werkzeugaufrufs im Protokoll. Zugehoerigkeit
    statt Anzahl: waechst die Sitzung weiter, waechst die Menge mit, und ein
    noch laufender Agent fehlt zwar in den gesammelten Laeufen, macht die
    Zusicherung aber nicht falsch."""
    import json as _json
    ids = set()
    for zeile in pfad.read_text(encoding="utf-8", errors="ignore").splitlines():
        if '"tool_use"' not in zeile or '"Agent"' not in zeile:
            continue
        try:
            d = _json.loads(zeile)
        except Exception:
            continue
        if d.get("type") != "assistant":
            continue
        for c in ((d.get("message") or {}).get("content") or []):
            if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Agent":
                ids.add(c.get("id"))
    return ids


def _hintergrundmeldungen(pfad) -> int:
    """Bash-/Monitor-Hintergrundmeldungen -- sie teilen sich die
    <task-notification>-Vorlage mit echten Agentenmeldungen und sind der
    Grund fuer den Filter."""
    text = pfad.read_text(encoding="utf-8", errors="ignore")
    return text.count("Background command")


def test_hintergrundmeldung_erzeugt_keinen_lauf_fixtur(tmp_path):
    """Dieselbe Behauptung wie oben, aber gegen eine EIGENE Fixtur -- und erst
    hier ist sie belegbar.

    Gemessen 2026-08-19: Auf dem echten Sitzungsprotokoll bewirkt der
    Unterscheider NICHTS -- 114 Laeufe mit und ohne ihn. Die urspruengliche
    Zusicherung (`== 79`) stammt aus einem Protokollzustand, den es so nicht
    mehr gibt; sie war zuletzt weder richtig noch aussagekraeftig. Ein Test,
    der seine eigene Behauptung am vorliegenden Material nicht mehr pruefen
    kann, gehoert auf Material, das er selbst stellt.

    Die Fixtur enthaelt genau zwei <task-notification>-Bloecke, die sich
    ausschliesslich in <summary> unterscheiden -- das ist der Unterscheider in
    `melder/agentendauer.py::_completions` (`startswith('Agent \"')`)."""
    def notification(task_id, summary):
        inhalt = (
            f"<task-notification><task-id>{task_id}</task-id>"
            f"<summary>{summary}</summary>"
            f"<usage><subagent_tokens>1000</subagent_tokens>"
            f"<tool_uses>2</tool_uses><duration_ms>5000</duration_ms></usage>"
            f"</task-notification>"
        )
        return json.dumps({"type": "user", "content": inhalt,
                           "timestamp": "2026-08-19T12:00:00.000Z"})

    protokoll = tmp_path / "fixtur.jsonl"
    protokoll.write_text(
        notification("a_echt", 'Agent "Beispiel" finished') + "\n"
        + notification("b_bash", 'Background command "irgendwas" completed (exit code 0)') + "\n",
        encoding="utf-8")

    laeufe = agentendauer.sammle([protokoll])
    ids = {l.task_id for l in laeufe}
    assert "a_echt" in ids, f"echter Agentenabschluss fehlt: {ids}"
    assert "b_bash" not in ids, (
        f"Bash-Hintergrundlauf als Subagentenlauf gezaehlt: {ids}")

@pytest.mark.skipif(not SESSION.exists(), reason="Sitzungsprotokoll nicht vorhanden (anderer Rechner/Nutzer)")
def test_bash_hintergrundlauf_zaehlt_nicht_als_subagent():
    """Rot-Probe fuer den beim ersten Anlauf gefundenen Fehler: eine
    <task-notification> mit <summary>Background command ...</summary>
    (Bash-Hintergrundlauf, kein Agent) darf keinen Lauf erzeugen. Vor der
    Korrektur lieferte sammle() 116 Laeufe statt der 79 echten
    Agent-Aufrufe -- die Bash-/Monitor-Meldungen der Sitzung teilen sich
    dieselbe Vorlage."""
    laeufe = agentendauer.sammle([SESSION])

    # BIS 2026-08-19 stand hier `assert len(laeufe) == 79` -- eine feste Zahl
    # gegen ein Sitzungsprotokoll, das WEITERWAECHST, solange die Sitzung
    # laeuft. Heute gemessen: 114 statt 79, ohne dass am Filter etwas
    # geaendert worden waere. Dritter Fall derselben Klasse an diesem Tag
    # (die beiden anderen: haken/mehrstufiger_abruf.py und
    # haken/knowledge_recall_hook.py, beide waren deshalb als xfail
    # eingetragen).
    #
    # Geprueft wird jetzt, was der Test MEINT: kein Bash-/Monitor-Lauf darf
    # einen Eintrag erzeugen. Das ist eine BEZIEHUNG zwischen zwei Zahlen
    # desselben Protokolls und damit unabhaengig davon, wie lang die Sitzung
    # noch laeuft.
    # Geprueft wird die BEHAUPTUNG, nicht eine Zahl: jeder gesammelte Lauf
    # muss zu einem echten Agent-Werkzeugaufruf desselben Protokolls
    # gehoeren. Damit faellt jeder Bash-/Monitor-Hintergrundlauf auf, ohne
    # dass irgendwo eine Anzahl steht.
    #
    # Die vorige Fassung verglich zwei ANZAHLEN und scheiterte an 114 gegen
    # 115 -- der fehlende eine ist ein Agent, der noch LAEUFT und darum noch
    # keine Abschlussmeldung hat. Eine Gleichheit von Anzahlen ist hier also
    # selbst dann falsch, wenn der Filter stimmt; die Zugehoerigkeit ist es
    # nicht.
    echte = _agent_werkzeugaufruf_ids(SESSION)
    fremd = [l for l in laeufe if l.tool_use_id not in echte]
    assert not fremd, (
        f"{len(fremd)} Lauf/Laeufe gehoeren zu keinem Agent-Werkzeugaufruf -- "
        f"Bash-/Monitor-Hintergrundlaeufe teilen sich die "
        f"<task-notification>-Vorlage und muessen herausgefiltert bleiben: "
        f"{[l.tool_use_id for l in fremd][:3]}"
    )
    # Gegenprobe, damit die Zusicherung nicht trivial haelt: das Protokoll
    # muss ueberhaupt Hintergrundmeldungen enthalten, sonst filtert der Test
    # nichts und waere auch ohne Filter gruen.
    assert _hintergrundmeldungen(SESSION) > 0, (
        "keine Bash-/Monitor-Hintergrundmeldung im Protokoll -- dieser Test "
        "prueft dann nichts")
