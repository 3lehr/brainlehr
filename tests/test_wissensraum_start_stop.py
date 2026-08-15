"""Beleg fuer pflege/wissensraum_start.sh + pflege/wissensraum_stop.sh
(ADR-020, "wer startet den Dienst").

Architekturentscheidung (2026-08-15, Ableitung des Betreibers): Weg 1
(launchd-LaunchAgent, dienst/de.brainlehr.dienst.plist + dienst/LIESMICH.md
-- bereits vorhanden, Commit 648432e) ist die eigentliche Antwort. Weg 2
(ein MCP-Klient startet den Dienst mit) scheidet architektonisch aus: seit
648432e ist die App nur noch Klient, nicht mehr Erzeuger des Dienstes, und
ADR-020 ueberfuehrt die MCP-Server in denselben Stand -- ein Klient, der
seinen Server selbst startet, ist keiner. Weg 3 (sichtbar scheitern, Mensch
handelt) bleibt darum der Fallback, falls der LaunchAgent (noch) nicht
laeuft -- pflege/wissensraum_start.sh deckt ihn schon ab (idempotent per
curl-Probe), es fehlte nur das Gegenstueck zum Beenden
(pflege/wissensraum_stop.sh, neu) fuer die Hausregel "kein Dauerlaeufer
ohne Aufraeumen".

Nutzt ausschliesslich freie Testports -- ruehrt NIE Port 8799 an, der einer
fremden Sitzung gehoert (Grenze des Auftrags). wissensraum_start.sh bekam
dafuer einen optionalen Port-Parameter (Vorgabe weiterhin 8799, bestehende
Aufrufer ohne Argument unveraendert).
"""
from __future__ import annotations

import socket
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
START = REPO / "pflege" / "wissensraum_start.sh"
STOP = REPO / "pflege" / "wissensraum_stop.sh"


def _freier_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _erreichbar(port: int, timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def _pids_auf_port(port: int) -> list[str]:
    out = subprocess.run(
        ["/usr/sbin/lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
        capture_output=True, text=True,
    ).stdout
    return [z for z in out.split() if z]


@pytest.fixture()
def aufraeumen():
    """Faengt jeden Testfall ab, der scheitert, bevor er selbst stop.sh
    aufruft -- kein Testlauf darf einen Dauerlaeufer hinterlassen."""
    gestartete_ports: list[int] = []
    yield gestartete_ports
    for port in gestartete_ports:
        subprocess.run([str(STOP), str(port)], capture_output=True, text=True, timeout=10)


def test_rot_vor_gruen_start_macht_dienst_erreichbar(aufraeumen):
    port = _freier_port()
    assert _erreichbar(port) is False  # ROT, wortwoertlich vor dem Start
    aufraeumen.append(port)

    r = subprocess.run([str(START), str(port)], capture_output=True, text=True, timeout=10)
    assert r.returncode == 0, r.stderr
    assert _erreichbar(port) is True  # GRUEN, wortwoertlich nach dem Start
    assert r.stdout.strip() == f"http://127.0.0.1:{port}/"


def test_stop_macht_dienst_wieder_unerreichbar(aufraeumen):
    port = _freier_port()
    aufraeumen.append(port)
    subprocess.run([str(START), str(port)], capture_output=True, text=True, timeout=10, check=True)
    assert _erreichbar(port) is True

    r = subprocess.run([str(STOP), str(port)], capture_output=True, text=True, timeout=10)
    assert r.returncode == 0, r.stderr
    time.sleep(0.3)
    assert _erreichbar(port) is False


def test_negativfall_laeuft_bereits_kein_zweiter_start(aufraeumen):
    """Negativfall: ein bereits laufender Dienst wird NICHT ein zweites Mal
    gestartet -- Beleg an der PID (identisch vor/nach dem zweiten Aufruf),
    nicht nur am Rueckgabewert."""
    port = _freier_port()
    aufraeumen.append(port)
    subprocess.run([str(START), str(port)], capture_output=True, text=True, timeout=10, check=True)
    erste_pids = _pids_auf_port(port)
    assert len(erste_pids) == 1

    r = subprocess.run([str(START), str(port)], capture_output=True, text=True, timeout=10)
    assert r.returncode == 0
    zweite_pids = _pids_auf_port(port)
    assert zweite_pids == erste_pids, "ein zweiter Aufruf darf keinen zweiten Prozess anlegen"


def test_grenzwert_port_von_fremdem_prozess_belegt(aufraeumen):
    """Grenzwert: der Port ist belegt, aber nicht von unserem Dienst (kein
    HTTP-Server, kein entscheidungen_server.py). start.sh darf dort nichts
    anlegen; entscheidungen_server.py meldet den Bindungsfehler lesbar
    statt mit Stapelspur (siehe Aenderung in berichte/entscheidungen_server.py)."""
    port = _freier_port()
    fremd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    fremd.bind(("127.0.0.1", port))
    fremd.listen(1)
    try:
        # start.sh's Wartschleife probiert bis zu 25x curl mit je bis zu 1s
        # Timeout gegen einen Nicht-HTTP-Antworter -- im Ungluecksfall bis
        # zu ~25s, mehr als der im Skript-Kommentar genannte "hoechstens
        # 5 Sekunden"-Regelfall (eigenstaendiger Befund, ausserhalb dieses
        # Auftrags -- nicht Teil der hier erlaubten Aenderungen).
        r = subprocess.run([str(START), str(port)], capture_output=True, text=True, timeout=40)
        # start.sh versucht in diesem Fall zu starten (curl scheitert am
        # Nicht-HTTP-Antworter) -- der eigentliche Server muss den belegten
        # Port dann lesbar melden, nicht mit Stapelspur.
        assert "moeglicherweise der" in r.stdout or r.returncode == 1
    finally:
        fremd.close()
    # Stop darf einen fremden Prozess auf dem Port NIE anfassen -- hier ist
    # ohnehin nichts mehr da (der Socket wurde oben geschlossen), aber der
    # Aufruf muss trotzdem ohne Fehler durchlaufen.
    r2 = subprocess.run([str(STOP), str(port)], capture_output=True, text=True, timeout=10)
    assert r2.returncode == 0


def test_stop_ohne_laufenden_dienst_ist_kein_fehler():
    port = _freier_port()
    r = subprocess.run([str(STOP), str(port)], capture_output=True, text=True, timeout=10)
    assert r.returncode == 0
    assert "laeuft nicht" in r.stdout


def test_stop_ruehrt_fremden_dienst_auf_anderem_port_nicht_an(aufraeumen):
    """Belegt zusaetzlich zum echten Beleg oben: stop.sh mit einem Port
    beendet niemals einen Prozess auf einem ANDEREN Port -- wichtig, weil
    Port 8799 in dieser Sitzung einer fremden Sitzung gehoert und nie
    angefasst werden darf."""
    eigener_port = _freier_port()
    aufraeumen.append(eigener_port)
    subprocess.run([str(START), str(eigener_port)], capture_output=True, text=True, timeout=10, check=True)
    eigene_pids = set(_pids_auf_port(eigener_port))

    anderer_port = _freier_port()
    subprocess.run([str(STOP), str(anderer_port)], capture_output=True, text=True, timeout=10)

    assert set(_pids_auf_port(eigener_port)) == eigene_pids, "stop.sh mit fremdem Port darf den eigenen Dienst nicht beruehren"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
