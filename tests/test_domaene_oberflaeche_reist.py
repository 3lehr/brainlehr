"""Rot-vor-gruen: die Oberflaechen-Beschreibung muss den Import ueberleben.

ANLASS: Seit B1 traegt ein Domaenenpaket eine Bildschirm-Beschreibung
(ADR-013, drei Teile). `speichere()` legte davon bisher NICHTS ab -- es
schrieb Wurzel, Quellen und Regeln, die Oberflaeche fiel durch. Folge: Das
atelier konnte die Beschreibung nach dem Import nirgends lesen und musste die
Manifest-Datei im Dateisystem suchen (`DomaenenSeite`, dort ausdruecklich als
BRUECKE benannt). Damit war der Importweg fuer die Oberflaeche wirkungslos --
ein Fremder, der nur das Paket bekommt, haette nie einen Bildschirm gesehen.

WARUM DAS DER PUNKT IST, an dem ADR-012 haengt: Dort steht, das Wissenspaket
reise FREI (Datei, Netz, Weitergabe) und das Werkzeug werde installiert. Die
Oberflaechen-Beschreibung ist Teil des Wissenspakets -- sie ist Daten, sie kann
nichts ausfuehren. Wenn sie den Import nicht ueberlebt, reist sie nicht, und
die Domaene bleibt beim Empfaenger unsichtbar, obwohl ihr Wissen ankam.

ROT-PROBE: runs/rotprobe_oberflaeche_reist_2026-08-16.txt
"""

import json
import sqlite3

import pytest

from kern.domaene import lies_oberflaeche, speichere


def _paket(**zusatz):
    basis = {
        "domaene": "probe-ob",
        "bezeichnung": "Probe Oberflaeche",
        "herkunft": "test",
        "stand": "2026-08-16T18:00:00+0200",
        "quellen": {"q1": {"bezeichnung": "Q", "hinweistext": "Belegtext"}},
        "regeln": [{"id": "r1", "ziel_id": "q1", "fundstelle": "Belegtext"}],
        "contract_version": 1,
        "dienst": {},
        "oberflaeche": {
            "fassung": 1,
            "bildschirme": [
                {
                    "kennung": "euer",
                    "art": "tabelle",
                    "titel": "Übertragung in die Anlage EÜR",
                    "spalten": [{"name": "betrag_cent", "titel": "Betrag", "art": "betrag"}],
                    "leerfall": "Noch nichts zugeordnet.",
                }
            ],
        },
    }
    basis.update(zusatz)
    return basis


@pytest.fixture
def frische_db(tmp_path):
    from kern.speicher import ort

    ziel = tmp_path / "probe.db"
    quelle = sqlite3.connect(str(ort.DB))
    neu = sqlite3.connect(str(ziel))
    quelle.backup(neu)
    neu.execute("DELETE FROM knowledge_nodes WHERE id LIKE 'domaene%'")
    neu.commit()
    neu.close()
    quelle.close()
    return ziel


def test_oberflaeche_ueberlebt_den_import(frische_db):
    """DER Test. Ohne ihn reist die Beschreibung nicht mit, und der Empfaenger
    sieht nichts."""
    speichere(_paket(), db=frische_db)

    ob = lies_oberflaeche("probe-ob", db=frische_db)

    assert ob is not None, "die Oberflaeche hat den Import nicht ueberlebt"
    assert ob["fassung"] == 1
    assert len(ob["bildschirme"]) == 1
    assert ob["bildschirme"][0]["titel"] == "Übertragung in die Anlage EÜR"
    assert ob["bildschirme"][0]["spalten"][0]["art"] == "betrag"


def test_unbekannte_domaene_liefert_nichts(frische_db):
    """Kein Fehler, kein leeres Gerippe -- None. Der Aufrufer muss den
    Unterschied zwischen 'nicht importiert' und 'ohne Bildschirm' sehen."""
    assert lies_oberflaeche("gibtesnicht", db=frische_db) is None


def test_domaene_ohne_bildschirme_ist_kein_fehler(frische_db):
    """Eine Domaene, die nur Wissen mitbringt, ist nach ADR-013 ausdruecklich
    zulaessig. Sie liefert eine leere Liste, nicht None -- sonst waere sie von
    'gar nicht importiert' nicht zu unterscheiden."""
    speichere(_paket(domaene="probe-leer",
                     oberflaeche={"fassung": 1, "bildschirme": []}), db=frische_db)

    ob = lies_oberflaeche("probe-leer", db=frische_db)

    assert ob is not None
    assert ob["bildschirme"] == []


def test_zwei_domaenen_stoeren_einander_nicht(frische_db):
    speichere(_paket(), db=frische_db)
    speichere(_paket(domaene="probe-zwei", bezeichnung="Zwei",
                     oberflaeche={"fassung": 1, "bildschirme": [
                         {"kennung": "x", "art": "tabelle", "titel": "Zweiter",
                          "spalten": [{"name": "a", "titel": "A", "art": "text"}]}]}),
              db=frische_db)

    assert lies_oberflaeche("probe-ob", db=frische_db)["bildschirme"][0]["titel"].startswith("Übertragung")
    assert lies_oberflaeche("probe-zwei", db=frische_db)["bildschirme"][0]["titel"] == "Zweiter"


def test_zweiter_import_ueberschreibt_nicht_still(frische_db):
    """Idempotenz wie beim Rest des Pakets: derselbe Import zweimal darf den
    Bestand nicht verdoppeln."""
    speichere(_paket(), db=frische_db)
    speichere(_paket(), db=frische_db)

    with sqlite3.connect(str(frische_db)) as conn:
        (n,) = conn.execute(
            "SELECT COUNT(*) FROM knowledge_nodes WHERE id = ?",
            ("domaeneoberflaeche-probe-ob",)).fetchone()
    assert n == 1


def test_die_beschreibung_wird_unveraendert_zurueckgegeben(frische_db):
    """Kein Umbau, keine Ergaenzung, keine Vorgabewerte: was die Domaene
    beschrieben hat, kommt so zurueck. Sonst entscheidet der Speicher ueber
    das Aussehen, und ADR-024 waere ausgehebelt."""
    paket = _paket()
    speichere(paket, db=frische_db)

    assert lies_oberflaeche("probe-ob", db=frische_db) == paket["oberflaeche"]
