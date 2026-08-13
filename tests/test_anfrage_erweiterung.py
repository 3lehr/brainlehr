"""Aufgabe 65, Schritt 2: kern/anfrage_erweiterung.py wendet den
Ausschreibekatalog (Schritt 1) nur auf die ANFRAGE an, nie auf den
gespeicherten Text. Grund: L-d8c5fb (buckeberg) -- 'TG' wurde beim Einlesen
still zu 'Tiefgarage' aufgeloest und wanderte in sieben abgeleitete
Fundstellen, zwei davon oeffentlich; das Objekt hat 9 Einzelgaragen und
7 Stellplaetze, gefunden hat es der Nutzer.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "kern"))
sys.path.insert(0, str(REPO / "haken"))

import anfrage_erweiterung as ae  # noqa: E402
import ausschreibekatalog as ak  # noqa: E402
import speicher  # noqa: E402


def test_ergaenzt_nicht_ersetzt():
    ergaenzt = ae.erweitere_anfrage("impl gesucht", katalog={"impl": "implementation"})
    assert ergaenzt == ["impl", "gesucht", "implementation"]


def test_ohne_katalogtreffer_unveraendert():
    assert ae.erweitere_anfrage("xyz123", katalog={"impl": "implementation"}) == ["xyz123"]


def test_kurzform_bleibt_teil_der_anfrage_auch_bei_treffer():
    """Die Kurzform wird nie entfernt -- eine Anfrage nach genau 'impl' im
    Sinn des Kuerzels selbst funktioniert weiter."""
    ergaenzt = ae.erweitere_anfrage("impl", katalog={"impl": "implementation"})
    assert ergaenzt[0] == "impl"


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


def test_negativfall_db_verschlechtert_sich_nicht():
    """'db' ist im Katalog NICHT aufgenommen (Schritt 1, Negativfall) -- die
    Erweiterung darf die Treffermenge fuer 'db' folglich nicht veraendern."""
    katalog = ak.katalog()
    assert "db" not in katalog, "Testannahme verletzt: 'db' waere aufgenommen"
    vorher = ae.treffer("db", katalog={})
    nachher = ae.treffer("db")
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
