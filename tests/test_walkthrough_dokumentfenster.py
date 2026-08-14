#!/usr/bin/env python3
"""F5-Abnahme: zwei Teilnehmer tippen GLEICHZEITIG in denselben Satz.

Der eine ist das native Fenster (ueber die Debug-Steuerschnittstelle bedient),
der andere ein Python-Klient am selben Dienst. Danach muessen beide dasselbe
zeigen UND beide Beitraege tragen.

WARUM BEIDES GEPRUEFT WIRD: "beide zeigen dasselbe" allein ist wertlos -- das
gilt auch, wenn einer den anderen ueberschrieben hat. Genau das ist beim ersten
Anlauf passiert.

WARUM EINGEFUEGT UND NICHT GESETZT WIRD: Wer einen ganzen Text setzt, setzt ihn
gegen einen Stand, den er vorher gelesen hat. Trifft dazwischen die Aenderung
eines anderen ein, loescht der Volltext sie mit -- und die Probe misst dann die
Reihenfolge der Aufrufe statt die Zusammenfuehrung (`L-235ab8`). Ein
Tastendruck fuegt EIN, also fuegt auch die Probe ein.

Uebersprungen, wenn atelier oder Dienst nicht laufen -- diese Probe braucht
beide und behauptet nichts, wenn sie fehlen.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL / "kern"))

PORTDATEI = Path(os.environ.get("TMPDIR", "/tmp")) / "atelier-steuerport"
DIENST_URL = os.environ.get("BRAINLEHR_DOKUMENTDIENST", "ws://127.0.0.1:4611")


def _steuerport() -> str | None:
    try:
        return PORTDATEI.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _steuer(pfad: str, rumpf: dict | None = None) -> dict:
    befehl = ["curl", "-s", "--max-time", "5", f"http://127.0.0.1:{_steuerport()}{pfad}"]
    if rumpf is not None:
        befehl += ["-X", "POST", "-d", json.dumps(rumpf)]
    roh = subprocess.run(befehl, capture_output=True, text=True).stdout
    return json.loads(roh) if roh.strip() else {}


def _atelier_laeuft() -> bool:
    if not _steuerport():
        return False
    try:
        return _steuer("/gesundheit").get("lebt") is True
    except (ValueError, OSError):
        return False


pytestmark = pytest.mark.skipif(
    not _atelier_laeuft(),
    reason="atelier laeuft nicht (Steuerschnittstelle nicht erreichbar) -- "
           "Aufbau: app/bauen.sh, App starten, kern/dokumentdienst.py --starten --port 4611")


async def _probe() -> tuple[str, str]:
    import websockets
    from pycrdt import Doc, Text

    from teilnehmer import neue_kennung

    async with websockets.connect(DIENST_URL) as w:
        will = json.loads(await asyncio.wait_for(w.recv(), 5))
        doc = Doc(client_id=neue_kennung())
        doc["t"] = text = Text()
        if will.get("stand"):
            doc.apply_update(base64.b64decode(will["stand"]))

        async def lesen():
            async for roh in w:
                nachricht = json.loads(roh)
                if nachricht.get("art") == "update":
                    doc.apply_update(base64.b64decode(nachricht["daten"]))

        mitlesen = asyncio.create_task(lesen())

        # Gleichzeitig, und jeder ohne den Stand des anderen: der eine haengt
        # hinten an, das Fenster fuegt vorne ein.
        text.insert(len(str(text)), "[Python]")
        await asyncio.gather(
            w.send(json.dumps({"art": "update",
                               "daten": base64.b64encode(doc.get_update()).decode()})),
            asyncio.to_thread(_steuer, "/dokument", {"einfuegen": "[Fenster] ", "bei": 0}),
        )
        await asyncio.sleep(3)
        mitlesen.cancel()

        return str(doc["t"]), _steuer("/zustand").get("dokumenttext", "")


def test_zwei_teilnehmer_tippen_gleichzeitig():
    verbunden = _steuer("/dokument", {"adresse": DIENST_URL})
    if verbunden.get("dokumentlage", "").startswith("Verbind") is False:
        pytest.skip(f"Dokumentdienst nicht erreichbar: {verbunden.get('dokumentlage')}")
    for _ in range(10):
        if _steuer("/zustand").get("dokumentlage") == "Verbunden":
            break
        import time
        time.sleep(0.5)
    else:
        pytest.skip("Fenster wurde nicht verbunden -- laeuft der Dienst auf " + DIENST_URL + "?")

    hier, dort = asyncio.run(_probe())

    assert hier == dort, f"divergent -- Python {hier!r}, Fenster {dort!r}"
    assert "[Python]" in hier, (
        "der Beitrag des Python-Klienten fehlt -- 'beide zeigen dasselbe' ist "
        f"wertlos, wenn einer den anderen ueberschrieben hat: {hier!r}")
    assert "[Fenster]" in hier, f"der Beitrag des Fensters fehlt: {hier!r}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
