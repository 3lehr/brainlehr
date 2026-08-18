#!/usr/bin/env python3
"""Ein Lauf liest einen festgehaltenen Stand -- nicht bei jedem Aufruf die
gegenwaertige DB (INT-SNAP-001, docs/REQUIREMENTS_INTERFACE_KOMPAT.md).

ANLASS, gemessen: der Bestand waechst durch parallel arbeitende Sitzungen
(2026-08-16: 5972-5983 Kandidaten im Bedeutungskanal, 2026-08-18: 6164) --
zwei Messungen an zwei Tagen sind damit nicht vergleichbar, ohne dass
irgendwo ein Fehler passiert waere. Der Bestand hat sich schlicht bewegt.

DREI KANDIDATEN GEPRUEFT, EINER GEWAEHLT:

(a) BEGIN DEFERRED und konsequent aus DIESER Transaktion lesen.
    Preis: die Transaktion muss eine lebende Verbindung ueber die gesamte
    Laufzeit eines Laufs offenhalten -- ueberlebt keinen Prozessneustart,
    laesst sich nicht als Kennung an einen anderen Prozess weiterreichen
    ("lies X gegen genau diesen Stand" verlangt aber genau das). Ausserdem
    haelt ein langlebiger Leser in WAL den Checkpoint zurueck: die
    WAL-Datei waechst, solange irgendein alter Leser offen ist -- ein
    Preis, den andere, gleichzeitig arbeitende Sitzungen zahlen, nicht der
    Lauf selbst. Verworfen: die Kennung waere eine Verbindung, keine
    Zeichenkette.

(b) Hoechstwert auf einer monoton wachsenden Spalte (rowid/created_at) als
    Grenze, jede Anfrage filtert selbst dagegen.
    Preis: billig, keine Sperre, ueberlebt als nackte Zahl jeden
    Prozessneustart. Aber: deckt nur NEUE Zeilen ab. Eine Aenderung an
    einer VORHANDENEN Zeile (UPDATE) traegt dieselbe rowid/denselben
    created_at wie vorher und rutscht unbemerkt in jeden Schnappschuss
    hinein, ganz gleich wie alt die Grenze ist. Fuer einen Bestand, der
    Knoten laufend aktualisiert (Vertrauenswerte, Freigaben), ist das die
    Sorte Fehler, die diese Datei gerade verhindern soll. Verworfen als
    einziges Verfahren -- s.u. als Ergaenzung fuer den Zweifelsfall.

(c) Eine Kopie der Datei zum Zeitpunkt des Laufs, ueber Connection.backup()
    (SQLite Online-Backup-API), nicht shutil.copy2.
    Preis: Plattenplatz (bei dieser Bestandsgroesse ein Nachmittag, nicht
    ein Problem) und die Zeit fuer den Kopiervorgang einmal je Lauf.
    Dafuer: deckt BEIDE Faelle ab, neue Zeilen UND Aenderungen an
    vorhandenen -- die Kopie ist der Stand, nicht ein Filter auf den
    Stand. Die Kennung ist eine Zeichenkette (Verzeichnisname), ueberlebt
    einen Prozessneustart und laesst sich weiterreichen. Genau dieses
    Verfahren steht schon einmal im Haus (tests/conftest.py::
    _erzeuge_schnappschuss, dort fuer Testlaeufe) und ist dort belegt:
    Connection.backup() liest WAL-Aenderungen korrekt mit, ohne die Quelle
    zu beruehren (tests/test_bestand_schnappschuss.py).

GEWAEHLT: (c). Es ist das einzige Verfahren, das beide im Auftrag
verlangten Fragen beantwortet -- "gib mir die Kennung" (eine
Zeichenkette, kein Objekt) und "lies X gegen genau diesen Stand" (eine
vollstaendige, eigene Kopie, kein Filter mit Luecke bei UPDATE) -- und das
niemanden sonst blockiert.

WAS DIESES VERFAHREN NICHT ABDECKT:
  - UPDATEs an Zeilen, die schon VOR dem Schnappschuss existierten, UND
    die selbst wieder rueckgaengig gemacht oder ein zweites Mal geaendert
    wurden, WAEHREND die Kopie laeuft -- SQLite garantiert dabei keine
    Verzerrung (die Kopie ist immer ein konsistenter, kein zerrissener
    Stand), aber NICHT deterministisch, ob eine mitten im Kopieren
    committete Aenderung noch hineinrutscht oder nicht. Nur Schreibungen,
    die VOR dem Aufruf von festhalten() committet waren, sind GARANTIERT
    enthalten (siehe Grenzwerttest in tests/test_schnappschuss.py).
  - Schemaaenderungen zwischen zwei Schnappschuessen -- eine Kopie traegt
    das Schema ihres Zeitpunkts, ein Lauf gegen eine alte Kennung sieht
    ein altes Schema.
  - Sehr grosse Bestaende: der Preis (Plattenplatz, Kopierzeit) waechst
    mit der Dateigroesse. Bei den heutigen ~65 MB kein Thema; bei einem
    Vielfachen waere Kandidat (b) als ERGAENZUNG zu pruefen (Grenze als
    Regel, Kopie nur fuer die Zeilen bis dahin -- heute nicht gebaut, weil
    dafuer keine Messung vorliegt, die es verlangt).

Aufruf:
    python3 kern/schnappschuss.py --selftest
"""
from __future__ import annotations

import sqlite3
import sys
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "haken"))
import ort  # noqa: E402

_VERZEICHNIS_VORGABE = Path(ort.WURZEL) / "runs" / "schnappschuesse"
_METADATEI = "herkunft.txt"
_DBDATEI = "stand.db"


@dataclass(frozen=True)
class Schnappschuss:
    """Der Ausweis eines festgehaltenen Standes -- die Kennung ist eine
    Zeichenkette (Verzeichnisname), nicht ein Objekt, weil sie einen
    Prozessneustart ueberleben und an einen anderen Aufruf weitergereicht
    werden koennen muss."""
    kennung: str
    pfad: Path            # Kopie der Datenbank zu diesem Stand
    aufgenommen: str      # ISO-8601 mit Zeitzone
    quelle: Path           # woher kopiert wurde


def festhalten(
    quelle: Path | None = None,
    verzeichnis: Path | None = None,
) -> Schnappschuss:
    """Zieht eine WAL-konsistente Kopie von `quelle` (Vorgabe: ort.DB) und
    legt sie unter `verzeichnis`/<kennung>/ ab. Jede Schreibung, die VOR
    diesem Aufruf committet war, ist garantiert enthalten (Grenzwert, siehe
    Moduldocstring und Test)."""
    quelle = Path(quelle or ort.DB)
    if not quelle.exists():
        raise FileNotFoundError(f"{quelle} existiert nicht -- kein Stand festzuhalten")
    ziel_wurzel = Path(verzeichnis or _VERZEICHNIS_VORGABE)
    aufgenommen = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    kennung = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:8]}"
    ziel_dir = ziel_wurzel / kennung
    ziel_dir.mkdir(parents=True, exist_ok=False)
    ziel = ziel_dir / _DBDATEI

    quelle_conn = sqlite3.connect(f"file:{quelle}?mode=ro", uri=True)
    ziel_conn = sqlite3.connect(str(ziel))
    try:
        quelle_conn.backup(ziel_conn)
    finally:
        ziel_conn.close()
        quelle_conn.close()

    (ziel_dir / _METADATEI).write_text(
        f"quelle={quelle}\naufgenommen={aufgenommen}\n", encoding="utf-8"
    )
    return Schnappschuss(kennung=kennung, pfad=ziel, aufgenommen=aufgenommen, quelle=quelle)


@contextmanager
def lesen(
    stand: Schnappschuss | str,
    verzeichnis: Path | None = None,
) -> Iterator[sqlite3.Connection]:
    """Liest gegen GENAU den festgehaltenen Stand -- nur-lesend (mode=ro),
    ein Schreibversuch scheitert. Nimmt entweder das Schnappschuss-Objekt
    (kein Nachschlagen noetig) oder nur die Kennung (loest ueber
    `verzeichnis` auf -- fuer den Fall, dass ein anderer Prozess nur die
    Zeichenkette hat).

    Negativfall: eine Kennung, die es nicht gibt, meldet sich laut ueber
    FileNotFoundError -- keine stille Leere, kein neu angelegtes leeres
    Verzeichnis (dieselbe Falle wie bei kern/speicher.verbinde_bestand)."""
    if isinstance(stand, Schnappschuss):
        pfad = stand.pfad
        kennung = stand.kennung
    else:
        kennung = stand
        ziel_wurzel = Path(verzeichnis or _VERZEICHNIS_VORGABE)
        pfad = ziel_wurzel / kennung / _DBDATEI

    if not pfad.exists():
        raise FileNotFoundError(
            f"Schnappschuss '{kennung}' existiert nicht unter {pfad} -- "
            "Kennung pruefen oder erst festhalten() aufrufen."
        )

    conn = sqlite3.connect(f"file:{pfad}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _selftest() -> None:
    import shutil
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="schnappschuss_selftest_"))
    try:
        quelle = tmp / "live.db"
        verzeichnis = tmp / "schnappschuesse"

        halter = sqlite3.connect(str(quelle))
        halter.execute("PRAGMA journal_mode=WAL")
        halter.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, wert TEXT)")
        halter.execute("INSERT INTO t (wert) VALUES ('vor-schnappschuss')")
        halter.commit()

        # Grenzwert: eine Schreibung GENAU vor festhalten() ist garantiert
        # enthalten.
        stand = festhalten(quelle, verzeichnis)
        with lesen(stand) as conn:
            n = conn.execute("SELECT COUNT(*) FROM t").fetchone()[0]
        assert n == 1, f"Schreibung vor festhalten() haette enthalten sein muessen, war {n}"

        # ROT-Beleg: zwei Lesevorgaenge OHNE Schnappschuss, dazwischen eine
        # Schreibung -- der zweite sieht die Aenderung. Das ist das
        # Verhalten, das dieses Modul fuer einen festgehaltenen Stand
        # AUSSCHLIESST (siehe Test fuer die woertliche Gegenprobe).
        halter.execute("INSERT INTO t (wert) VALUES ('nach-schnappschuss')")
        halter.commit()

        # GRUEN: der bereits gezogene Stand sieht die spaetere Schreibung
        # NICHT.
        with lesen(stand) as conn:
            n = conn.execute("SELECT COUNT(*) FROM t").fetchone()[0]
        assert n == 1, f"Schnappschuss haette die spaetere Schreibung nicht sehen duerfen, sah {n}"

        # Reines Nachschlagen ueber die Kennung (zweiter Prozess haette nur
        # die Zeichenkette).
        with lesen(stand.kennung, verzeichnis) as conn:
            n = conn.execute("SELECT COUNT(*) FROM t").fetchone()[0]
        assert n == 1

        # Negativfall: unbekannte Kennung meldet sich laut.
        try:
            with lesen("gibt-es-nicht", verzeichnis):
                pass
            raise AssertionError("unbekannte Kennung haette scheitern muessen")
        except FileNotFoundError:
            pass

        # Ein Schreibversuch gegen den Schnappschuss scheitert (mode=ro).
        with lesen(stand) as conn:
            try:
                conn.execute("INSERT INTO t (wert) VALUES ('verboten')")
                raise AssertionError("Schreibversuch gegen Schnappschuss haette scheitern muessen")
            except sqlite3.OperationalError:
                pass

        halter.close()
        print("schnappschuss.py: selftest ok")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(__doc__)
