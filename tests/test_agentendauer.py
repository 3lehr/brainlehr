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


@pytest.mark.skipif(not SESSION.exists(), reason="Sitzungsprotokoll nicht vorhanden (anderer Rechner/Nutzer)")
def test_bash_hintergrundlauf_zaehlt_nicht_als_subagent():
    """Rot-Probe fuer den beim ersten Anlauf gefundenen Fehler: eine
    <task-notification> mit <summary>Background command ...</summary>
    (Bash-Hintergrundlauf, kein Agent) darf keinen Lauf erzeugen. Vor der
    Korrektur lieferte sammle() 116 Laeufe statt der 79 echten
    Agent-Aufrufe -- die Bash-/Monitor-Meldungen der Sitzung teilen sich
    dieselbe Vorlage."""
    laeufe = agentendauer.sammle([SESSION])
    assert len(laeufe) == 79, (
        f"erwartet 79 (== Anzahl der Agent-Werkzeugaufrufe der Sitzung), "
        f"gefunden {len(laeufe)} -- Bash-/Monitor-Hintergrundlaeufe muessen "
        f"herausgefiltert bleiben"
    )
