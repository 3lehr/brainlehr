"""Die Annahmen-Tabelle haelt ihre eigenen Regeln, nicht der Aufrufer.

Uebernommen aus der Stiftshuette (assumptions.json), wo dasselbe Schema tot
lag: entworfen, nie befuellt, kein Schreiber. Der Unterschied hier ist nicht
die Tabelle, sondern dass die Disziplin an ihr haengt -- darum pruefen diese
Faelle die TRIGGER, nicht die Bequemlichkeit einer Hilfsfunktion.

Gegenprobe in beide Richtungen: jede Regel wird einmal verletzt (muss
scheitern) und einmal eingehalten (muss durchgehen). Ein Test, der nur den
guten Fall kennt, prueft nicht die Regel, sondern die Tabelle.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

import knowledge_mcp_server as kms  # noqa: E402

PFLICHT = dict(kosten_wenn_falsch="Neubau der Auswertung, etwa zwei Tage")


@pytest.fixture()
def db(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "probe.db"))
    kms.ensure_schema(conn)
    yield conn
    conn.close()


def _einfuegen(conn, id_="A-000001", **felder):
    spalten = {"id": id_, "annahme": "Der Abruf trifft in 80 Prozent der Faelle",
               "belegrang": "geraten", **PFLICHT, **felder}
    conn.execute(
        f"INSERT INTO annahmen ({','.join(spalten)}) VALUES ({','.join('?' * len(spalten))})",
        tuple(spalten.values()),
    )
    conn.commit()


def test_ohne_kosten_wenn_falsch_kein_eintrag(db):
    """Der Satz, der beim Aufschreiben zum Nachdenken zwingt, ist Pflicht."""
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO annahmen (id, annahme) VALUES ('A-1', 'irgendwas')")
    _einfuegen(db)  # mit dem Satz geht es
    assert db.execute("SELECT COUNT(*) FROM annahmen").fetchone()[0] == 1


def test_gemessen_ohne_beleg_wird_abgelehnt(db):
    """'gemessen' ohne Protokoll ist eine Behauptung mit besserem Namen."""
    with pytest.raises(sqlite3.IntegrityError, match="beleg"):
        _einfuegen(db, belegrang="gemessen", beleg="   ")
    _einfuegen(db, belegrang="gemessen", beleg="messlauf_abrufguete.py, Lauf 2026-08-08, n=240")

    # und beim Aendern greift dieselbe Regel, nicht nur beim Anlegen
    with pytest.raises(sqlite3.IntegrityError, match="beleg"):
        db.execute("UPDATE annahmen SET beleg = '' WHERE id = 'A-000001'")


def test_entscheidung_ohne_pruefung_wird_abgelehnt(db):
    """bestaetigt/widerlegt verlangt Beleg, Pruefer und Zeitpunkt."""
    _einfuegen(db)
    with pytest.raises(sqlite3.IntegrityError, match="geprueft"):
        db.execute("UPDATE annahmen SET status = 'bestaetigt' WHERE id = 'A-000001'")
    with pytest.raises(sqlite3.IntegrityError, match="geprueft"):
        db.execute("UPDATE annahmen SET status = 'widerlegt', beleg = 'Lauf 3' "
                   "WHERE id = 'A-000001'")
    db.execute("UPDATE annahmen SET status = 'widerlegt', beleg = 'Lauf 3: 61 Prozent', "
               "geprueft_von = 'markus', geprueft_am = '2026-08-08T18:00:00+0200' "
               "WHERE id = 'A-000001'")
    db.commit()
    assert db.execute("SELECT status FROM annahmen").fetchone()[0] == "widerlegt"


def test_unbekannter_status_und_belegrang_werden_abgelehnt(db):
    with pytest.raises(sqlite3.IntegrityError):
        _einfuegen(db, status="vielleicht")
    with pytest.raises(sqlite3.IntegrityError):
        _einfuegen(db, belegrang="gefuehlt")


def test_wortlaut_und_entstehung_sind_unveraenderlich(db):
    """Wer die Annahme umschreibt, faelscht die Vorgeschichte der Entscheidung."""
    _einfuegen(db)
    with pytest.raises(sqlite3.IntegrityError, match="unveraenderlich"):
        db.execute("UPDATE annahmen SET annahme = 'etwas ganz anderes' WHERE id = 'A-000001'")
    with pytest.raises(sqlite3.IntegrityError, match="unveraenderlich"):
        db.execute("UPDATE annahmen SET created_at = '2020-01-01T00:00:00Z' WHERE id = 'A-000001'")
    # Notizen bleiben aenderbar -- die Gegenprobe, dass nicht die ganze Zeile erstarrt
    db.execute("UPDATE annahmen SET notizen = 'siehe Lauf 3' WHERE id = 'A-000001'")
    db.commit()
    assert db.execute("SELECT notizen FROM annahmen").fetchone()[0] == "siehe Lauf 3"


# ── Der Schreiber ─────────────────────────────────────────────────────────
# Ohne ihn waere die Tabelle das, was assumptions.json in der Stiftshuette
# war: ein Schema ohne Befueller. Darum gehen diese Faelle durch die
# MCP-Werkzeuge, nicht an ihnen vorbei.

@pytest.fixture()
def kms_db(tmp_path, monkeypatch):
    pfad = tmp_path / "werkzeug.db"
    conn = sqlite3.connect(str(pfad))
    kms.ensure_schema(conn)
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", pfad)
    return pfad


def _ruf(name, **args):
    return kms.TOOLS[name]["handler"](args)


def test_werkzeug_legt_an_und_listet_schlechtesten_beleg_zuerst(kms_db):
    gut = _ruf("annahme_erfassen", annahme="Abrufguete liegt bei 80 Prozent",
               kosten_wenn_falsch="Rangfolge muss neu gebaut werden",
               belegrang="gemessen", beleg="messlauf_abrufguete.py, n=240")
    schlecht = _ruf("annahme_erfassen", annahme="Niemand nutzt den Umlaut-Zweig",
                    kosten_wenn_falsch="Suche bleibt fuer halbe Begriffe blind")
    assert gut["id"].startswith("A-") and gut["status"] == "offen"

    liste = _ruf("annahme_liste")
    assert liste["offen_gesamt"] == 2
    assert liste["results"][0]["id"] == schlecht["id"], "geraten muss vor gemessen stehen"


def test_werkzeug_lehnt_gemessen_ohne_beleg_ab_statt_still_zu_speichern(kms_db):
    antwort = _ruf("annahme_erfassen", annahme="Der Abruf spart Kontext",
                   kosten_wenn_falsch="Wir optimieren die falsche Stelle",
                   belegrang="gemessen")
    assert antwort["status"] == "rejected"
    assert "beleg" in antwort["error"]
    assert _ruf("annahme_liste")["offen_gesamt"] == 0


def test_werkzeug_entscheidet_nur_mit_beleg_und_pruefer(kms_db):
    a = _ruf("annahme_erfassen", annahme="Der Symlink hat keine Nutzer mehr",
             kosten_wenn_falsch="Vier Melder fallen lautlos aus")

    with pytest.raises(ValueError, match="geprueft_von"):
        _ruf("annahme_entscheiden", annahme_id=a["id"], status="widerlegt", beleg="neun Fundstellen")

    fertig = _ruf("annahme_entscheiden", annahme_id=a["id"], status="widerlegt",
                  beleg="neun Fundstellen, Symlink abgeklemmt gemessen",
                  geprueft_von="markus", belegrang="gemessen",
                  tatsaechliche_kosten="eine Sitzung")
    assert fertig["status"] == "widerlegt" and fertig["geprueft_am"]
    assert _ruf("annahme_liste")["offen_gesamt"] == 0
    assert _ruf("annahme_liste", status="widerlegt")["count"] == 1


def test_werkzeug_meldet_unbekannte_kennung_statt_still_nichts_zu_tun(kms_db):
    antwort = _ruf("annahme_entscheiden", annahme_id="A-gibtsnicht", status="bestaetigt",
                   beleg="irgendwas", geprueft_von="markus")
    assert antwort["status"] == "rejected" and "A-gibtsnicht" in antwort["error"]
