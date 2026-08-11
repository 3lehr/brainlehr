"""Der zweite Suchkanal muss vollstaendig sein -- und das faellt sonst nicht auf.

BEFUND, gemessen 2026-08-11: Der Kaltstart von bge-m3 dauert 11,5 s, der
Timeout in kern/embeddings.py lag bei 5,0 s. Jeder Einbettungsversuch lief in
den Timeout und gab still None zurueck -- embed_text ist ausdruecklich
best-effort. Ergebnis: 39 Knoten und 17 Lehren ohne Vektor, dazu rund 550
VERALTETE (Text geaendert, Vektor vom alten Stand). Der Nachzug rechnete 607
Eintraege neu.

WARUM ES OHNE PRUEFUNG NIE AUFFAELLT, und das ist der eigentliche Grund fuer
diese Datei: Die Suche mischt zwei Kanaele. Der FTS5-Trigramm-Index braucht
kein Modell und liefert weiter Treffer; die vorhandenen Vektoren werden weiter
GELESEN. Es gibt also keinen Fehler, keine leere Antwort und keinen roten Test
-- nur schleichend schlechtere Treffer fuer alles Neue. Ein stiller Ausfall
mit funktionierender Oberflaeche.

Diese Tests pruefen die LAGE des echten Bestands, nicht eine Funktion. Fehlt
der Bestand (frischer Klon, fremder Rechner), wird uebersprungen statt falsch
Alarm zu schlagen.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent

# Aufloeser statt selbst gebautem Namen -- siehe tests/test_testumgebung_nutzt_ort.py
from haken.ort import DB

if not DB.exists():
    pytest.skip("kein Bestand vorhanden -- nichts zu pruefen",
                allow_module_level=True)


@pytest.fixture()
def conn():
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        yield c
    finally:
        c.close()


def _fehlend(conn) -> tuple[int, int]:
    n = conn.execute(
        "SELECT COUNT(*) FROM knowledge_nodes n WHERE NOT EXISTS "
        "(SELECT 1 FROM knowledge_embeddings e WHERE e.kind='node' AND e.ref_id=n.id)"
    ).fetchone()[0]
    l = conn.execute(
        "SELECT COUNT(*) FROM lessons_learned l WHERE NOT EXISTS "
        "(SELECT 1 FROM knowledge_embeddings e WHERE e.kind='lesson' AND e.ref_id=l.id)"
    ).fetchone()[0]
    return n, l


def test_kein_eintrag_ohne_vektor(conn):
    """ROT VOR GRUEN: vor dem Nachzug 39 Knoten und 17 Lehren ohne Vektor.

    Die Schwelle ist bewusst NULL und keine Quote. Eine Quote wuerde einen
    dauerhaften Rueckstand als 'noch im Rahmen' durchwinken -- und genau so
    entsteht der Zustand, den dieser Test verhindern soll."""
    ohne_knoten, ohne_lehren = _fehlend(conn)
    assert (ohne_knoten, ohne_lehren) == (0, 0), (
        f"{ohne_knoten} Knoten und {ohne_lehren} Lehren ohne Vektor. "
        f"Nachziehen: python3 kern/build_embeddings.py")


def test_alle_vektoren_aus_einem_modell(conn):
    """Vektoren verschiedener Modelle liegen in verschiedenen Raeumen -- ihre
    Abstaende sind nicht vergleichbar. Ein gemischter Bestand macht die
    Aehnlichkeitssuche still falsch, nicht kaputt."""
    modelle = {r[0] for r in conn.execute(
        "SELECT DISTINCT model FROM knowledge_embeddings")}
    assert len(modelle) == 1, f"gemischte Modelle im Bestand: {sorted(modelle)}"


def test_keine_verwaisten_vektoren(conn):
    """GEGENPROBE zur anderen Richtung: ein Vektor ohne Eintrag verfaelscht
    jede Trefferliste, weil er als Kandidat gezogen wird und dann ins Leere
    zeigt."""
    verwaist = conn.execute(
        "SELECT COUNT(*) FROM knowledge_embeddings e WHERE "
        "(e.kind='node' AND NOT EXISTS (SELECT 1 FROM knowledge_nodes n WHERE n.id=e.ref_id)) "
        "OR (e.kind='lesson' AND NOT EXISTS (SELECT 1 FROM lessons_learned l WHERE l.id=e.ref_id))"
    ).fetchone()[0]
    assert verwaist == 0, f"{verwaist} Vektoren ohne zugehoerigen Eintrag"


def test_der_dienst_antwortet_schnell_genug():
    """Der Timeout muss ueber der ECHTEN Antwortzeit liegen, nicht ueber einer
    angenommenen. Laeuft Ollama nicht, wird uebersprungen -- der stille
    Rueckfall auf Stichwortsuche ist dann gewollt und kein Fehler."""
    import time
    sys.path.insert(0, str(_w / "kern"))
    import embeddings

    start = time.perf_counter()
    vektor = embeddings.embed_text("Probe der Antwortzeit")
    dauer = time.perf_counter() - start
    if vektor is None:
        pytest.skip("Einbettungsdienst nicht erreichbar -- stiller Rueckfall")
    assert dauer < embeddings.DEFAULT_TIMEOUT, (
        f"Antwort brauchte {dauer:.1f} s bei einem Timeout von "
        f"{embeddings.DEFAULT_TIMEOUT} s -- zu knapp")
