"""B4.1: _identity() nimmt den Aufrufer nicht mehr beim Wort.

Plan: docs/PLAN_B4_AUSWEIS_2026-08-09.md, Proben P1/P2.

ROT VOR GRUEN: Gegen den Stand vor dieser Aenderung faellt
test_ausweis_ueberstimmt_argument mit actor == 'betreiber' durch --
`actor or os.environ.get(...)` liess das Argument gewinnen. Genau das ist
die Fehlklasse, die hier geschlossen wird (bauartgleich L-8487fb).
"""
from __future__ import annotations

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

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ausweis  # noqa: E402
import knowledge_mcp_server as kms  # noqa: E402


@pytest.fixture()
def ausweisdatei(tmp_path, monkeypatch):
    pfad = tmp_path / "ausweise.json"
    monkeypatch.setenv(ausweis.ENV_AUSWEISDATEI, str(pfad))
    monkeypatch.delenv(ausweis.ENV_GEHEIMNIS, raising=False)
    monkeypatch.delenv("BEGOD_KNOWLEDGE_ACTOR", raising=False)
    return pfad


def test_ausweis_ueberstimmt_argument(ausweisdatei, monkeypatch):
    """P2 -- der ganze Plan in einer Zeile.

    Ein gueltiger Aufruf mit selbstbehauptetem actor im Rumpf darf diesen
    Wert NICHT uebernehmen (Negativfall aus ADR-001).
    """
    geheimnis = ausweis.anlegen("hausmeister", ["leser"], pfad=ausweisdatei)
    monkeypatch.setenv(ausweis.ENV_GEHEIMNIS, geheimnis)

    actor, _model, _session = kms._identity(actor="betreiber")

    assert actor == "hausmeister", (
        "Das Argument hat den Ausweis ueberstimmt -- wer die Rolle waehlen "
        "kann, hat jede Rolle."
    )


def test_ohne_ausweis_bleibt_das_argument_zulaessig_aber_markiert(ausweisdatei):
    """P1 -- kein Bruch fuer die bestehenden Schreiber, aber sichtbar.

    3.998 Protokollzeilen und mehrere lokale Skripte schreiben ohne Ausweis.
    Sie duerfen weiter schreiben; die Zuschreibung traegt nur ihr Praefix.
    """
    actor, _model, _session = kms._identity(actor="normbestand.py")
    assert actor == "unbeglaubigt:normbestand.py"


def test_falsches_geheimnis_gibt_nicht_mehr_als_gar_keines(ausweisdatei, monkeypatch):
    ausweis.anlegen("hausmeister", ["leser"], pfad=ausweisdatei)
    monkeypatch.setenv(ausweis.ENV_GEHEIMNIS, "falsch")

    actor, _model, _session = kms._identity(actor="betreiber")

    assert actor == "unbeglaubigt:betreiber"


def test_umgebungsvariable_verliert_ebenfalls(ausweisdatei, monkeypatch):
    """BEGOD_KNOWLEDGE_ACTOR ist eine Behauptung wie jede andere -- sie
    stammt aus derselben Umgebung, die ein Aufrufer setzen kann, und traegt
    keinen Nachweis."""
    geheimnis = ausweis.anlegen("hausmeister", ["leser"], pfad=ausweisdatei)
    monkeypatch.setenv(ausweis.ENV_GEHEIMNIS, geheimnis)
    monkeypatch.setenv("BEGOD_KNOWLEDGE_ACTOR", "betreiber")

    actor, _model, _session = kms._identity()

    assert actor == "hausmeister"


def test_kein_actor_nirgends(ausweisdatei):
    actor, _model, _session = kms._identity()
    assert actor == kms.UNBEKANNTER_SCHREIBER


def test_praefix_im_argument_wird_nicht_verdoppelt(ausweisdatei):
    """Untergrabungsversuch: wer das Praefix selbst mitliefert, soll weder
    doppelt markiert werden noch echt aussehen."""
    actor, _model, _session = kms._identity(actor="unbeglaubigt:betreiber")
    assert actor == "unbeglaubigt:betreiber"


def test_model_und_session_bleiben_unveraendert(ausweisdatei, monkeypatch):
    """Grenze der Aenderung: B4.1 fasst nur actor an. model und session sind
    Angaben ueber den Vorgang, keine Identitaetsbehauptung -- sie duerfen
    weiter aus Argument und Umgebung kommen."""
    geheimnis = ausweis.anlegen("hausmeister", ["leser"], pfad=ausweisdatei)
    monkeypatch.setenv(ausweis.ENV_GEHEIMNIS, geheimnis)

    _actor, model, session = kms._identity(model="claude-opus-5", session="s-1")

    assert model == "claude-opus-5"
    assert session == "s-1"
