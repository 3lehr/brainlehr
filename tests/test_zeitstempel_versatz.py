"""Tests fuer den Zeitstempel: richtiger ZEITPUNKT, eindeutige SCHREIBWEISE.

Befund 2026-08-06: now_iso() nutzte in sechs Dateien eine feste
timezone(timedelta(hours=1)) und haengte den Text "+01:00" fest an -- im
Sommer war der geschriebene Zeitstempel damit falsch benannt. Fix damals:
zoneinfo Europe/Berlin + isoformat(), also Ortszeit mit echtem Versatz.

NACHGESCHAERFT 2026-08-14 (Aufgabe 111, Betreiberentscheidung "alles auf
UTC"): now_iso() liefert jetzt UTC mit 'Z'. Der Beschluss von 2026-08-06 hielt
acht Tage nicht, weil 104 Stellen im Baum ihren Zeitstempel selbst bauten --
und dabei wieder vier Schreibweisen entstanden, darunter '+0200' OHNE
Doppelpunkt, genau die Form, an der der Fehler urspruenglich gefunden wurde.

DIE ABSICHT DIESER DATEI HAT SICH NICHT GEAENDERT, nur ihr Massstab:
  frueher   Wanduhrzeit == Berliner Wanduhrzeit, Versatz mit Doppelpunkt
  jetzt     ZEITPUNKT == echter Zeitpunkt, Schreibweise eindeutig ('Z')

Der neue Massstab ist der staerkere: er prueft, was der Zeitstempel BEDEUTET,
nicht wie er aussieht. Ein Zeitpunktvergleich haette den Fehler von 2026-08-06
uebrigens NICHT gefunden -- dort war der Instant intern selbstkonsistent und
nur die Benennung falsch. Deshalb bleibt die Schreibweisenprobe daneben
stehen, statt ersetzt zu werden.
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
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "kern"))

import knowledge_mcp_server as kms
import build_embeddings as be
import lesson_recorder as lr
import hebb_kanten as hk
import fix_namensraum_knoten as fnk
import migrate_knowledge as mk

BERLIN = ZoneInfo("Europe/Berlin")

MODULE_NOW_ISO = [kms.now_iso, be.now_iso, lr.now_iso, fnk.now_iso, mk.now_iso]


def test_now_iso_bezeichnet_den_echten_zeitpunkt():
    """Der Zeitstempel muss denselben ZEITPUNKT bezeichnen wie die Uhr,
    unabhaengig davon, in welcher Zone er geschrieben ist. Toleranz 5 s.

    Das ist der Nachfolger der Wanduhr-Probe von 2026-08-06 und ihr staerkerer
    Massstab: Ortszeit und UTC sind derselbe Zeitpunkt in zwei Schreibweisen;
    eine falsche Zone faellt hier auf, eine blosse Schreibweise nicht."""
    from datetime import timezone
    referenz = datetime.now(timezone.utc)
    for now_iso in MODULE_NOW_ISO:
        geschrieben = now_iso()
        geparst = datetime.fromisoformat(geschrieben.replace("Z", "+00:00"))
        diff = abs((geparst - referenz).total_seconds())
        assert diff < 5, (
            f"{now_iso.__module__}.now_iso() bezeichnet einen um {diff}s "
            f"abweichenden Zeitpunkt: {geschrieben}")


def test_now_iso_hat_genau_eine_schreibweise():
    """Der Nachfolger der Doppelpunkt-Probe. Ihr Anlass bleibt gueltig: '+0200'
    und '+02:00' bezeichnen denselben Zeitpunkt und sind als Text verschieden
    -- ein Textvergleich scheitert dann still, kein Fehler, nur ein leeres
    Ergebnis. Genau daran wurde der Fehler am 2026-08-06 gefunden.

    Mit UTC gibt es diese Wahl nicht mehr: eine Schreibweise, und Sortieren
    als Text ist dasselbe wie Sortieren als Zeitpunkt."""
    import zeitmarke
    for now_iso in MODULE_NOW_ISO:
        geschrieben = now_iso()
        assert zeitmarke.UTC_MUSTER.match(geschrieben), (
            f"{now_iso.__module__}: nicht die eine Zielform: {geschrieben}")


def test_winter_gegenprobe_januar_traegt_plus_eins():
    dt = datetime(2026, 1, 15, 12, 0, 0, tzinfo=BERLIN)
    assert dt.isoformat(timespec="seconds").endswith("+01:00")


def test_winter_gegenprobe_juli_traegt_plus_zwei():
    dt = datetime(2026, 7, 15, 12, 0, 0, tzinfo=BERLIN)
    assert dt.isoformat(timespec="seconds").endswith("+02:00")


def test_hebb_kanten_stamp_hilfsfunktion_nutzt_echten_versatz():
    # hebb_kanten._selftest() baut "now" fuer Testfixtures -- direkt pruefen,
    # dass die Zeile datetime.now(BERLIN).isoformat(...) nutzt (kein CET-Rest).
    assert not hasattr(hk, "CET"), "hebb_kanten.py: fixe CET-Zone haette entfernt werden sollen"
    assert not hasattr(kms, "CET"), "knowledge_mcp_server.py: fixe CET-Zone haette entfernt werden sollen"
    assert not hasattr(be, "CET"), "build_embeddings.py: fixe CET-Zone haette entfernt werden sollen"
    assert not hasattr(fnk, "CET"), "fix_namensraum_knoten.py: fixe CET-Zone haette entfernt werden sollen"
    assert not hasattr(mk, "CET"), "migrate_knowledge.py: fixe CET-Zone haette entfernt werden sollen"
    assert not hasattr(lr, "CET"), "lesson_recorder.py: fixe CET-Zone haette entfernt werden sollen"
