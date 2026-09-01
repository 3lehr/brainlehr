"""Aufgabe 65, Schritt 2: kern/anfrage_erweiterung.py wendet den
Ausschreibekatalog (Schritt 1) nur auf die ANFRAGE an, nie auf den
gespeicherten Text. Grund: L-d8c5fb (buckeberg) -- 'TG' wurde beim Einlesen
still zu 'Tiefgarage' aufgeloest und wanderte in sieben abgeleitete
Fundstellen, zwei davon oeffentlich; das Objekt hat 9 Einzelgaragen und
7 Stellplaetze, gefunden hat es der Nutzer.
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "kern"))
sys.path.insert(0, str(REPO / "haken"))

import anfrage_erweiterung as ae  # noqa: E402
import ausschreibekatalog as ak  # noqa: E402
import speicher  # noqa: E402


def test_ergaenzt_nicht_ersetzt():
    """Nachbesserung Aufgabe 65: BEIDE langen Formen (englisch + deutsch)
    werden ergaenzt, in der Reihenfolge der Katalogliste."""
    ergaenzt = ae.erweitere_anfrage(
        "impl gesucht", katalog={"impl": ["implementation", "Umsetzung"]}
    )
    assert ergaenzt == ["impl", "gesucht", "implementation", "Umsetzung"]


def test_ohne_katalogtreffer_unveraendert():
    assert ae.erweitere_anfrage("xyz123", katalog={"impl": ["implementation"]}) == ["xyz123"]


def test_kurzform_bleibt_teil_der_anfrage_auch_bei_treffer():
    """Die Kurzform wird nie entfernt -- eine Anfrage nach genau 'impl' im
    Sinn des Kuerzels selbst funktioniert weiter."""
    ergaenzt = ae.erweitere_anfrage("impl", katalog={"impl": ["implementation"]})
    assert ergaenzt[0] == "impl"


@pytest.mark.skipif(
    os.environ.get("BRAINLEHR_RUN_LIVE") != "1",
    reason="requires explicit BRAINLEHR_RUN_LIVE=1 and the grown corpus",
)
def test_rot_vor_gruen_an_impl_gegen_echten_bestand():
    """Rot: ohne Erweiterung (katalog={}) findet 'impl' nur die woertliche
    Kurzform im Bestand. Gruen: mit dem echten Katalog kommen die Dokumente
    mit der langen Form ('implementation') dazu -- echt mehr, nicht nur
    behauptet mehr."""
    vorher = ae.treffer("impl", katalog={})
    nachher = ae.treffer("impl")
    assert len(nachher) > len(vorher), (
        f"vorher {len(vorher)}, nachher {len(nachher)} -- Erweiterung hat nichts bewegt"
    )
    # Die vorher gefundene Menge bleibt vollstaendig erhalten (Ergaenzung,
    # keine Ersetzung).
    assert vorher <= nachher


@pytest.mark.skipif(
    os.environ.get("BRAINLEHR_RUN_LIVE") != "1",
    reason="requires explicit BRAINLEHR_RUN_LIVE=1 and the grown corpus",
)
def test_db_findet_ueber_die_erweiterung_mehr_rot_vor_gruen():
    """Nachbesserung Aufgabe 65 (Fehler 1): 'db' ist unter drei Zeichen
    (Trigramm-Mindestlaenge) und darum IMMER im Katalog -- die Kurzform
    findet auf dem Suchweg strukturell nichts, egal wie oft sie im Rohtext
    vorkommt. Rot: ohne Erweiterung nur die woertliche Kurzform. Gruen: mit
    Erweiterung zusaetzlich Dokumente mit 'database'/'Datenbank'."""
    katalog = ak.katalog()
    assert "db" in katalog, "Testannahme verletzt: 'db' muesste aufgenommen sein (< 3 Zeichen)"
    vorher = ae.treffer("db", katalog={})
    nachher = ae.treffer("db")
    assert len(nachher) > len(vorher), (
        f"vorher {len(vorher)}, nachher {len(nachher)} -- Erweiterung hat nichts bewegt"
    )
    assert vorher <= nachher


def test_negativfall_ausgeschlossene_kurzform_verschlechtert_sich_nicht():
    """Eine Kurzform, die der Katalog NICHT aufnimmt (Verhaeltnis unter der
    Schwelle), darf die Treffermenge nicht veraendern -- sonst waere die
    Ausschlussregel aus Schritt 1 wirkungslos."""
    katalog = ak.katalog()
    ausgeschlossen = next(
        (k for k in ("auth", "config", "req", "res") if k not in katalog), None
    )
    if ausgeschlossen is None:
        return  # Bestand hat sich so verschoben, dass alle Saat-Paare aufgenommen sind
    vorher = ae.treffer(ausgeschlossen, katalog={})
    nachher = ae.treffer(ausgeschlossen)
    assert nachher == vorher


def test_grenzwert_wird_von_ausschreibekatalog_geerbt():
    """anfrage_erweiterung erfindet keine eigene Schwelle -- sie nutzt
    ausschreibekatalog.katalog() unveraendert. Grenzwerttest liegt darum in
    tests/test_ausschreibekatalog.py; hier nur die Kopplung belegt."""
    katalog_direkt = ak.katalog()
    ergaenzt = ae.erweitere_anfrage("impl", katalog=None)
    assert ("implementation" in ergaenzt) == ("impl" in katalog_direkt)


def _bestand_hash() -> str:
    with speicher.lesen() as conn:
        knoten = conn.execute(
            "SELECT id, title, summary, content FROM knowledge_nodes ORDER BY id"
        ).fetchall()
        lehren = conn.execute(
            "SELECT id, description, root_cause, resolution, prevention "
            "FROM lessons_learned ORDER BY id"
        ).fetchall()
    h = hashlib.sha256()
    for row in knoten:
        for feld in row:
            h.update(str(feld).encode("utf-8", "replace"))
    for row in lehren:
        for feld in row:
            h.update(str(feld).encode("utf-8", "replace"))
    return h.hexdigest()


def test_gespeicherter_text_byteweise_unveraendert():
    """Gezaehlt, nicht angenommen: SHA-256 ueber alle Textspalten von
    knowledge_nodes und lessons_learned, einmal vor und einmal nach dem
    vollen Ablauf (Bewertung + Erweiterung + Trefferzaehlung). Weicht der
    Hash ab, hat irgendetwas geschrieben -- das darf nicht passieren, weil
    speicher.lesen() ausschliesslich mode=ro oeffnet."""
    vorher = _bestand_hash()

    ak.bewerte()
    ak.katalog()
    ae.erweitere_anfrage("impl config auth db")
    ae.treffer("impl config auth db")

    nachher = _bestand_hash()
    assert vorher == nachher, "Bestand hat sich waehrend Katalog/Erweiterung veraendert"
