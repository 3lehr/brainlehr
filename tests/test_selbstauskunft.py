"""Die Selbstauskunft wird ERZEUGT, nie gepflegt.

DER ANLASS (2026-08-20): Der Betreiber fragte einen fremden Klienten (Hermes),
ob er brainlehr kenne. Die Antwort war inhaltlich sehr gut -- die vier
Kerndisziplinen, der Zweck, die Architektur, sogar der Zeitpunkt der letzten
Sicherung auf die Minute. Und JEDE gepflegte Zahl war falsch, alle in
dieselbe Richtung:

    20 Tabellen   gemessen 35
    31 Trigger    gemessen 63
    ~20 Werkzeuge gemessen 30
    "reines Python 3, keine externen Pakete"  -- tatsaechlich fuenf

Kein Halluzinieren, sondern ein Schnappschuss von frueher: brainlehr, wie es
einmal war. Genau die Fehlerklasse, fuer die brainlehr gebaut wurde -- ein
Befund von gestern ist keine Tatsache von heute. Prinzipien altern langsam,
Zahlen schnell.

Deshalb steht hier die Regel, die das unmoeglich macht: In der Selbstauskunft
darf keine dieser Zahlen als Literal stehen. Was gemessen wird, kann nicht
veralten; was gepflegt wird, veraltet immer -- die Frage ist nur, wann es
jemand merkt.
"""
import sqlite3
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent.parent / "kern"),
                str(Path(__file__).resolve().parent.parent)]
import selbstauskunft as sa  # noqa: E402


def _bestand(tmp_path):
    db = tmp_path / "probe.db"
    c = sqlite3.connect(db)
    c.executescript("CREATE TABLE a(x); CREATE TABLE b(y);"
                    "CREATE TRIGGER t1 BEFORE INSERT ON a BEGIN SELECT 1; END;")
    c.commit(); c.close()
    return db


def test_zahlen_folgen_dem_bestand(tmp_path):
    """DIE PROBE, DIE ZAEHLT: Waechst der Bestand, waechst die Auskunft.

    Eine gepflegte Zahl haette hier stillgestanden -- und genau daran ist
    Hermes' Beschreibung gescheitert."""
    db = _bestand(tmp_path)
    vorher = sa.erhebe(db)
    assert vorher["bestand"]["tabellen"] == 2
    assert vorher["bestand"]["trigger"] == 1

    c = sqlite3.connect(db)
    c.executescript("CREATE TABLE c(z);"
                    "CREATE TRIGGER t2 BEFORE INSERT ON b BEGIN SELECT 1; END;")
    c.commit(); c.close()

    nachher = sa.erhebe(db)
    assert nachher["bestand"]["tabellen"] == 3, "die Zahl folgt dem Bestand nicht"
    assert nachher["bestand"]["trigger"] == 2


def test_keine_dieser_zahlen_steht_als_literal_im_quelltext():
    """Der Mechanismus zur Regel: Wer eine Zahl hinschreibt, hat sie gepflegt.

    Geprueft werden die Zahlen, die Hermes falsch hatte -- und ihre heutigen
    Werte. Beides, weil ein Nachfolger sonst den EINEN aktuellen Wert
    einträgt und die Regel damit genau so bricht, wie sie gebrochen wurde."""
    quelle = (Path(sa.__file__)).read_text(encoding="utf-8")
    import re
    # Zeilen mit Erklaertext ausnehmen -- der Befund selbst nennt die Zahlen,
    # und das muss er duerfen. Verboten ist die Zahl im CODE.
    code = "\n".join(z for z in quelle.splitlines()
                     if not z.lstrip().startswith("#")
                     and '"""' not in z)
    for verboten in ("20", "31", "30", "35", "63"):
        assert not re.search(rf"=\s*{verboten}\b", code), (
            f"{verboten} steht als Vorgabewert im Code -- gepflegt statt gemessen")


def test_werkzeuge_kommen_aus_der_registrierung():
    """Nicht aus einer Liste daneben: Ein neues Werkzeug erscheint von selbst,
    ein entferntes verschwindet."""
    erhoben = sa.erhebe(None)
    import knowledge_mcp_server as kms
    assert erhoben["werkzeuge"]["anzahl"] == len(kms.TOOLS)
    assert "knowledge_add" in erhoben["werkzeuge"]["namen"]


def test_abhaengigkeiten_kommen_aus_requirements():
    """Die Aussage 'keine externen Pakete' war der teuerste Einzelfehler --
    sie klingt nach einer Eigenschaft und ist eine Momentaufnahme."""
    erhoben = sa.erhebe(None)
    namen = erhoben["abhaengigkeiten"]
    assert "numpy" in namen and "cryptography" in namen
    assert len(namen) == len([
        z for z in (Path(sa.__file__).resolve().parent.parent / "requirements.txt")
        .read_text(encoding="utf-8").splitlines()
        if z.strip() and not z.lstrip().startswith("#")])


def test_text_nennt_stand_und_quelle():
    """Eine Zahl ohne Zeitpunkt ist genau das, was Hermes weitergegeben hat."""
    text = sa.als_text(sa.erhebe(None))
    assert "erhoben" in text.lower()
    assert "brainlehr" in text.lower()


def test_fehlender_bestand_ist_kein_absturz(tmp_path):
    """NEGATIVFALL: Ein fremder Klient ohne Bestand bekommt eine Auskunft
    ueber den Code, nicht eine Ausnahme."""
    erhoben = sa.erhebe(tmp_path / "gibtsnicht.db")
    assert erhoben["bestand"]["tabellen"] is None
    assert erhoben["werkzeuge"]["anzahl"] > 0


def test_fremde_klienten_erreichen_sie_ueber_mcp():
    """DER PUNKT DER GANZEN UEBUNG: Ein Skript im Repo haette Hermes nicht
    geholfen -- er sieht das Repo nicht, er sieht die Werkzeuge.

    Deshalb muss die Auskunft ein WERKZEUG sein, kein Kommandozeilenaufruf.
    Und der Handler muss ausgefuehrt werden, nicht nur registriert sein: Eine
    Eintragung ohne funktionierenden Handler sieht in jeder Liste richtig aus
    und faellt erst beim Aufruf auf (L-9d668e, derselbe Server)."""
    import knowledge_mcp_server as kms
    assert "knowledge_selbstauskunft" in kms.TOOLS
    eintrag = kms.TOOLS["knowledge_selbstauskunft"]
    assert "inputSchema" in eintrag and callable(eintrag["handler"])
    ergebnis = eintrag["handler"]({})
    assert isinstance(ergebnis, dict)
    assert ergebnis["werkzeuge"]["anzahl"] == len(kms.TOOLS)
    assert "knowledge_selbstauskunft" in ergebnis["werkzeuge"]["namen"], (
        "die Auskunft zaehlt sich selbst nicht mit -- dann ist sie schon falsch")
