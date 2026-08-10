"""Der Haken, der die eigene ANTWORT prueft statt der Frage.

Betreiber-Befund 2026-08-08: Der Wissensabruf haengt am UserPromptSubmit,
feuert also auf die Frage. Wer in der ANTWORT schreibt "dafuer haben wir
wohl nicht genug Daten", hat die Datenbank nie gefragt — und niemand merkt
es. Zweimal am selben Tag passiert, einmal davon mit Datensaetzen, die seit
Tagen bereitlagen.
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

import sqlite3
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL / "haken"))

import existenzpruefung as ep  # type: ignore  # noqa: E402


def test_existenzverneinung_wird_erkannt():
    text = ("Der Aufbau steht. Dafuer haben wir noch keine Messdaten. "
            "Der Testlauf ist gruen.")
    assert ep.verneinungen(text) == ["Dafuer haben wir noch keine Messdaten."]


def test_sachverneinung_schlaegt_nicht_an():
    """Die Gegenrichtung, ohne die der Melder bei jeder zweiten Antwort
    anschlaegt: verneint wird taeglich, EXISTENZ selten. 'Das stimmt nicht'
    ist keine Aussage darueber, ob etwas vorhanden ist."""
    assert ep.verneinungen("Das stimmt nicht, die Zahl war anders.") == []
    assert ep.verneinungen("Ich habe den Test nicht gefahren.") == []
    assert ep.verneinungen("") == []


def test_suchbegriffe_nehmen_die_inhaltswoerter():
    """Laengste zuerst: in einem deutschen Satz tragen die langen Woerter die
    Sache, die kurzen die Grammatik."""
    b = ep.suchbegriffe("Bei rund 2000 Protokollzeilen ist das Wirkungssignal zu duenn.")
    assert "Protokollzeilen" in b and "Wirkungssignal" in b
    assert "das" not in b.split() and "ist" not in b.split()


def test_treffer_im_bestand_werden_gemeldet(tmp_path):
    db = tmp_path / "k.db"
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE knowledge_nodes (path TEXT, title TEXT, summary TEXT)")
    c.execute("INSERT INTO knowledge_nodes VALUES "
              "('/mess/korpus','Pruefkorpus V3 fuer den Abrufvergleich','...')")
    c.commit()
    c.close()
    assert ep.bestand_fragen(db, "Pruefkorpus Abrufvergleich")
    # Gegenrichtung: keine Erfindung, wo nichts steht
    assert ep.bestand_fragen(db, "Quantenchromodynamik") == []


def test_kaputte_datenbank_bleibt_still(tmp_path):
    """Ein Melder, der bei einem eigenen Fehler laut wird, wird abgeschaltet."""
    assert ep.bestand_fragen(tmp_path / "gibtsnicht.db", "irgendwas") == []
