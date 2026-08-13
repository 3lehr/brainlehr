"""Autouse-Schutz fuer die gesamte Testsuite (ADR-034, Verdrahtungspunkte).

Zwei Bausteine schreiben jetzt LIVE am Schreibvorgang, mit Vorgabe-Pfaden,
die auf echte Dateien im Repo zeigen -- jeder Test, der ueber diese
Schreibpfade laeuft, muss beide umbiegen, nicht nur die neuen ADR-034-Tests:

1. kms.knowledge_add/knowledge_update/lesson_record/lesson_update rufen
   kms._check_injection_suspects() auf, die per Vorgabe in
   shared-knowledge/injection_suspect_log.jsonl anhaengt.
2. kms._bump_lesson() loest ab occurrences>=3 jetzt SOFORT
   lesson_recorder.write_rules_to_instructions() aus (nicht mehr nur der
   manuelle 'auto-rules'-CLI-Lauf) -- dessen PROJECTS-Dict zeigt per Vorgabe
   auf die ECHTEN Repo-Wurzeln (hub/AKA2026/BEBETTER).

Beides ist beim Bau dieses Anschlusses tatsaechlich passiert (Fund
2026-08-07: ein echter Log-Eintrag aus test_knowledge_add_source.py UND
echte Dateien in hub/AKA2026/BEBETTER, alle von Hand entfernt). Autouse
statt Einzel-Fixture, weil der Fehlerpfad nicht an einer einzigen Testdatei
haengt, sondern an jedem Test, der einen dieser beiden Schreibpfade beruehrt."""
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

import os
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))


def hub_wurzel() -> Path | None:
    """Wo liegt der hub, aus dessen scripts/ vier Tests Module laden?

    Bis zum Umzug am 2026-08-08 war das schlicht der Elternordner: brainlehr
    lag als hub/shared-knowledge darin. Seit brainlehr ein eigenes Repo ist,
    stimmt diese Annahme nicht mehr, und vier Tests brachen beim Sammeln ab
    (caveman_bulk, caveman_compress, wiedereinstieg, knowledge_recall_hook).

    Bewusst tolerant statt fest verdrahtet: ein Klon von brainlehr allein hat
    keinen hub, und dann sollen diese vier Tests sich UEBERSPRINGEN, nicht die
    Sammlung sprengen. Reihenfolge: ausdrueckliche Angabe, Nachbarordner,
    alte Lage."""
    import os
    kandidaten = [
        Path(os.environ["BEGOD_HUB"]) if os.environ.get("BEGOD_HUB") else None,
        SHARED_KNOWLEDGE.parent / "hub",      # brainlehr und hub nebeneinander
        SHARED_KNOWLEDGE.parent,              # alte Lage: hub/shared-knowledge
    ]
    for k in kandidaten:
        if k and (k / "scripts").is_dir():
            return k
    return None


# Die Automatik liegt seit dem 2026-08-08 in brainlehr selbst (haken/), nicht
# mehr in hub/scripts — sie ist der Teil, der zeigt, was brainlehr ausmacht,
# und gehoert deshalb mitgeliefert.
sys.path.insert(0, str(SHARED_KNOWLEDGE / "haken"))

HUB = hub_wurzel()
if HUB:
    for zusatz in (HUB / "scripts", HUB / "begod" / "scripts"):
        if zusatz.is_dir():
            sys.path.insert(0, str(zusatz))

import atexit
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BestandSchnappschuss:
    """Ein Schnappschuss des Bestands, benennbar statt einer nackten Zahl.

    Eine Messung gegen `knoten`/`lehren` soll spaeter angeben koennen, GEGEN
    WELCHEN Stand sie gemessen hat -- `aufgenommen` traegt genau das."""
    pfad: Path
    knoten: int
    lehren: int
    aufgenommen: str


def _erzeuge_schnappschuss(quelle: Path) -> BestandSchnappschuss:
    """WAL-konsistente Kopie via sqlite3 Connection.backup() (Online-Backup-
    API), nicht shutil.copy2 -- Vorlage: kern/migrate_relations.py::migrate().
    Bewusst NICHT normrang.py::_backup()s Weg (PRAGMA wal_checkpoint(TRUNCATE)
    vor dem Kopieren): die Quelle hier ist der LEBENDE, geteilte Bestand, an
    dem andere Sitzungen gleichzeitig schreiben (siehe Auftrag-FAKTEN) -- ein
    TRUNCATE-Checkpoint dort waere ein Eingriff in fremden Betrieb, den diese
    Vorrichtung nicht braucht: Connection.backup() liest WAL-Aenderungen
    korrekt mit, ganz ohne die Quelle anzufassen (Beleg: tests/test_bestand_
    schnappschuss.py, Gegenprobe zu tests/test_backup_wal_checkpoint.py)."""
    ziel_dir = Path(tempfile.mkdtemp(prefix="brainlehr_schnappschuss_"))
    # ponytail: os-tmp-Aufraeumung statt pytest tmp_path_factory, weil
    # braucht_bestand() als nackte Funktion ohne Fixture-Parameter aus
    # mehreren Testdateien aufgerufen wird -- kein Fixture-Kontext verfuegbar.
    atexit.register(shutil.rmtree, ziel_dir, ignore_errors=True)
    ziel = ziel_dir / "brainlehr_snapshot.db"
    quelle_conn = sqlite3.connect(f"file:{quelle}?mode=ro", uri=True)
    ziel_conn = sqlite3.connect(str(ziel))
    try:
        quelle_conn.backup(ziel_conn)
    finally:
        ziel_conn.close()
        quelle_conn.close()
    con = sqlite3.connect(f"file:{ziel}?mode=ro", uri=True)
    try:
        knoten = con.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        lehren = con.execute("SELECT COUNT(*) FROM lessons_learned").fetchone()[0]
    finally:
        con.close()
    aufgenommen = datetime.now().astimezone().isoformat(timespec="seconds")
    return BestandSchnappschuss(ziel, knoten, lehren, aufgenommen)


_SCHNAPPSCHUSS: BestandSchnappschuss | None = None


def bestand_schnappschuss() -> BestandSchnappschuss | None:
    """Liefert EINEN Schnappschuss je pytest-Prozess (gecacht, nicht neu
    gezogen) -- None, wenn keine Quelle existiert. Modul-globaler Cache statt
    pytest.fixture(scope="session"): braucht_bestand() und die kopierenden
    Testdateien rufen diese Funktion als nackten Aufruf, ausserhalb jeder
    Fixture-Injektion -- ein Session-Fixture waere fuer sie unerreichbar."""
    global _SCHNAPPSCHUSS
    if _SCHNAPPSCHUSS is None:
        # Den Aufloeser fragen, nicht den Pfad bauen: ein selbst gebauter Name
        # ueberlebt keine Umbenennung (L-2b5f6f).
        from haken.ort import DB as quelle
        if not quelle.exists():
            return None
        _SCHNAPPSCHUSS = _erzeuge_schnappschuss(quelle)
    return _SCHNAPPSCHUSS


def braucht_bestand(mindestens: int = 100) -> None:
    """Ueberspringt einen Test, der gegen den gewachsenen Bestand misst.

    Einige Tests pruefen die Abrufguete an ECHTEN Eintraegen -- sie suchen
    nach Inhalten wie "Existenzgruender", die in einer frisch angelegten
    Instanz nicht stehen. Gemessen an einem Klon ausserhalb des Verbunds:
    9 solche Tests rot, und keiner davon sagte etwas ueber den Code.

    Bewusst UEBERSPRINGEN statt auf synthetische Vorrichtungen umbauen:
    diese Tests messen echte Guete an echtem Bestand, das ist ihr Zweck.
    Ein Test, dessen Voraussetzung fehlt, ist zu ueberspringen -- ein
    umgebauter Test misst etwas anderes und sieht dabei gruen aus.

    Prueft jetzt gegen den EINEN Schnappschuss des Laufs (bestand_
    schnappschuss()), nicht mehr gegen den lebenden Bestand direkt -- sonst
    koennte dieselbe Pruefung, zweimal im selben Lauf aufgerufen, durch eine
    fremde, gleichzeitig schreibende Sitzung zwei verschiedene Antworten
    geben."""
    import pytest
    snap = bestand_schnappschuss()
    if snap is None:
        from haken.ort import DB as pfad
        pytest.skip(f"kein Bestand unter {pfad} -- erst `python3 schnellstart.py --bestand`")
    if snap.knoten < mindestens:
        pytest.skip(f"Bestand zu klein ({snap.knoten} < {mindestens} Knoten) -- "
                    "erst `python3 schnellstart.py --bestand` einspielen")


import knowledge_mcp_server as kms  # type: ignore  # noqa: E402
import lesson_recorder  # type: ignore  # noqa: E402


@pytest.fixture(autouse=True)
def _kein_echter_ausweis(tmp_path, monkeypatch):
    """Isoliert JEDEN Test vom Ausweisordner des Heimatverzeichnisses (Vorgabe
    ~/Desktop/brainlehr-ausweise, siehe kern/ausweis.py/kern/geheimnis.py).

    ANLASS 2026-08-13: seit ~/Desktop/brainlehr-ausweise/mein-geheimnis.txt
    auf diesem Rechner existiert, loeste ausweis.loese_auf() ohne expliziten
    `pfad` denselben echten Ausweis auf (beglaubigt als 'claude-code') statt
    des bis dahin zufaellig unbeglaubigten Rueckfalls -- 14 Tests, die
    'unbekannt'/unbeglaubigt erwarten, wurden dadurch rot. Eine Testsuite, die
    davon abhaengt, was im Heimatverzeichnis EINES Rechners liegt, ist auf
    keinem anderen reproduzierbar.

    BRAINLEHR_AUSWEISE zeigt hier auf ein leeres, frisches Verzeichnis (nicht
    einmal angelegt -- geheimnis.py behandelt eine fehlende Datei als
    Normalfall). BRAINLEHR_GEHEIMNIS wird zusaetzlich entfernt, damit auch der
    Umgebungs-Ruecktritt (Schritt 2 der Aufloesungskette) nicht zufaellig
    einen im Prozess gesetzten Wert trifft.

    Tests, die den echten Aufloesungs-/Vorrangmechanismus PRUEFEN
    (test_geheimnisdatei_vorrang.py, test_ausweis_helfer.py,
    test_gefuehrt_von.py, test_probeinstanz.py), setzen BRAINLEHR_AUSWEISE in
    ihren EIGENEN Fixtures/Tests erneut -- das ueberschreibt diesen Wert hier
    (monkeypatch, letzter setenv-Aufruf gewinnt), sie bleiben also unberuehrt.
    Kein Test im Bestand braucht den ECHTEN, in ~/Desktop liegenden Ausweis
    selbst -- alle Ausweis-Vorrichtungen legen ihre eigene, temporaere Datei
    an."""
    monkeypatch.setenv("BRAINLEHR_AUSWEISE", str(tmp_path / "kein_ausweis_hier"))
    monkeypatch.delenv("BRAINLEHR_GEHEIMNIS", raising=False)


@pytest.fixture(autouse=True)
def _keine_echten_seiteneffekt_dateien(tmp_path, monkeypatch):
    monkeypatch.setattr(kms, "INJECTION_SUSPECT_LOG", tmp_path / "injection_suspect_log.jsonl")
    monkeypatch.setattr(lesson_recorder, "PROJECTS", {"shared": tmp_path / "auto_rule_projects"})


@pytest.fixture(autouse=True)
def _norm_entscheidung_test_default(monkeypatch):
    """norm_entscheidung ist seit Auftrag 2026-08-08 PFLICHT bei
    kms.knowledge_add() (schema.sql-Trigger knowledge_nodes_norm_entscheidung_
    pflicht_bi lehnt 'offen' bei INSERT ab). Die meisten bestehenden Tests in
    diesem Verzeichnis pruefen etwas anderes (anlass, source, Pfad-Logik,
    Embeddings, ...) und kennen dieses Feld nicht -- ohne diesen Default
    wuerden sie alle mit demselben, fuer sie irrelevanten Fehler abbrechen.
    Default nur, wenn der Aufrufer das Keyword GAR NICHT mitgibt (kwargs-
    Check VOR dem Aufruf, nicht Pythons eigener Parameter-Default) -- ein
    explizit gesetzter Wert (auch None, um die Ablehnung selbst zu pruefen)
    bleibt unangetastet. Die echte Durchsetzung inklusive Rot-vor-Gruen-Beleg
    steht in tests/test_norm_entscheidung.py, gegen die per Modul-Kopf VOR
    diesem Fixture-Lauf gesicherte Original-Funktion, nicht gegen diesen
    Wrapper."""
    original = kms.knowledge_add

    def _mit_default(*args, **kwargs):
        kwargs.setdefault("norm_entscheidung", "keine_norm")
        # norm_entschieden_grund (Nachtrag 2026-08-08): dieselbe Testbequemlichkeit
        # wie norm_entscheidung oben -- Pflicht seit dem Nachtrag, fuer diese
        # norm-fernen Tests irrelevant.
        kwargs.setdefault("norm_entschieden_grund", "Testvorrichtung, keine echte Norm-Pruefung")
        return original(*args, **kwargs)

    monkeypatch.setattr(kms, "knowledge_add", _mit_default)


@pytest.fixture(autouse=True)
def _embed_model_config_abgeglichen(monkeypatch):
    """Auftrag 80: die Vektor-Identitaet (embeddings.DEFAULT_EMBED_MODEL)
    traegt jetzt zusaetzlich zum Modellnamen die erzeugenden Parameter
    ('bge-m3@ctx2048' statt nur 'bge-m3') -- schema.sql seedet
    knowledge_config['embed_model'] weiterhin mit dem woertlichen Rohnamen
    'bge-m3' (schema.sql bleibt in diesem Auftrag unangetastet). In echten
    Laeufen gleicht build_embeddings.py das VOR dem Schreiben ab (INSERT ...
    ON CONFLICT DO UPDATE); ~40 Testdateien bauen ihre eigene schema.sql-
    Test-DB per `conn.executescript(schema)` und kennen diesen Abgleich
    nicht -- ohne ihn weist der Modellsperre-Trigger (schema.sql,
    knowledge_embeddings_model_check_bi/_bu) jede mit der aktuellen Identitaet
    geschriebene Zeile ab.

    sqlite3.Connection ist ein C-Erweiterungstyp -- seine Methoden lassen sich
    NICHT direkt monkeypatchen ('cannot set executescript attribute of
    immutable type'). Stattdessen wird sqlite3.connect() global auf eine
    Connection-Unterklasse umgebogen (deren executescript() den Nachtrag
    macht) -- das IST unterstuetzt (Standard-`factory`-Parameter), betrifft
    jeden `sqlite3.connect(...)`-Aufruf in der Suite und ersetzt so das
    Anfassen von ~40 Fixturen einzeln (gleiches Muster wie
    _norm_entscheidung_test_default oben, dort fuer einen anderen Trigger):
    ein Punkt statt vierzig. Nur Skripte, die 'knowledge_config' selbst
    anlegen (also schema.sql, nicht z.B. ein reines ALTER TABLE), bekommen
    den Nachtrag."""
    import sqlite3 as _sqlite3

    class _AbgeglicheneConnection(_sqlite3.Connection):
        def executescript(self, script, *a, **kw):
            # NUR bei der ERSTANLAGE nachziehen (kein 'embed_model'-Eintrag vor
            # diesem Aufruf): knowledge_mcp_server.ensure_schema() fuehrt
            # schema.sql idempotent bei JEDEM Schreibvorgang erneut aus (siehe
            # dort, Zeile um 1241) -- ein bedingungsloses Ueberschreiben wuerde
            # dort auch einen von einem Test ABSICHTLICH gesetzten
            # abweichenden Wert (siehe test_embedding_model_lock.py,
            # 'ein-anderes-modell') beim naechsten Schreibzugriff stillschweigend
            # zuruecksetzen -- genau der Modellsperre-Mechanismus, den jener
            # Test pruefen will.
            vorher_vorhanden = False
            if "knowledge_config" in script:
                try:
                    vorher_vorhanden = self.execute(
                        "SELECT 1 FROM knowledge_config WHERE key = 'embed_model'"
                    ).fetchone() is not None
                except _sqlite3.OperationalError:
                    vorher_vorhanden = False
            result = super().executescript(script, *a, **kw)
            if "knowledge_config" in script and not vorher_vorhanden:
                self.execute(
                    "UPDATE knowledge_config SET value = ?, updated_at = datetime('now') "
                    "WHERE key = 'embed_model'",
                    (kms.embeddings.DEFAULT_EMBED_MODEL,),
                )
                self.commit()
            return result

    original_connect = _sqlite3.connect

    def _connect_mit_abgleich(*args, **kwargs):
        kwargs.setdefault("factory", _AbgeglicheneConnection)
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(_sqlite3, "connect", _connect_mit_abgleich)
