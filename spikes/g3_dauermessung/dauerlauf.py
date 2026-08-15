#!/usr/bin/env python3
"""G3-Dauermessung -- Verzoegerung und Stundenbetrieb OHNE zweites Geraet
und OHNE Administratorrechte.

WOZU. Die Vormessung (runs/nullmessung_dokumentdienst_2026-08-14.json) nennt
selbst ihre Grenze: kein Mini im Netz (also keine Netzlaufzeit, keine zweite
Herkunftsadresse), nur 180 Sekunden. Der Betreiber hat daraus geschlossen, G3
brauche zwingend echte zweite Hardware und eine Stunde Handbetrieb. Dieser
Aufbau prueft genau das: die DAUER laesst sich ohne Mensch erzeugen (ein
Tippmuster, das Stunden laeuft), die NETZLAUFZEIT laesst sich ohne
Administratorrechte erzeugen (ein Relais im eigenen Prozess statt pfctl/dnctl
auf Betriebssystemebene -- rung 4 der Ladder waere ein OS-Werkzeug, das ein
Passwort braucht; ein WS-Relais in Python braucht keins und ist eine Zwischen-
schicht, kein neuer Dienst).

WAS ER NICHT LOEST: die Herkunftspruefung bleibt ungeprueft (siehe GRENZE
unten in der Ergebnisdatei) -- beide Teilnehmer bleiben Prozesse auf
127.0.0.1, egal wie das Relais dazwischenhaengt. Das wird nicht verschwiegen.

AUFBAU
    echter Dienst (kern/dokumentdienst.Raum + .starten, UNVERAENDERT benutzt)
        |
        +-- Teilnehmer "fenster"  -- direkte Verbindung, wie in der Vormessung
        |
        +-- Relais (dieses Skript) -- kuenstliche Verzoegerung + Schwankung
                |
                +-- Teilnehmer "mini"     -- verbindet sich NUR ueber das Relais

Beide Teilnehmer tippen nach einem Muster mit Schueben, Pausen und
gelegentlichem Loeschen (siehe TIPPMUSTER unten) -- endlos, bis SIGINT/SIGTERM
oder --dauer-sekunden ablaeuft. Alle `--intervall-sekunden` (Standard 15)
wird der Stand nach `lauf/status_fortlaufend.json` geschrieben, atomar
(erst .neu, dann umbenennen) -- ein Abbruch nach drei Stunden verliert
hoechstens ein Intervall, nicht den Lauf.

TIPPMUSTER, und woran "realistisch" hier festgemacht wird (Annahme, nicht
gemessen -- es gibt keine eigene Typing-Studie in diesem Repo):
Menschliches Tippen ist NICHT im Gleichtakt, sondern buendig: kurze Schuebe
von wenigen bis rund einem Dutzend Zeichen (60-220 ms je Zeichen entspricht
gaengigen 40-90 Woertern/Minute), dann eine Denkpause (1-8 s), seltener eine
laengere Ablenkung (10-60 s, ~1x je 1-3 Minuten), und ein kleiner Anteil der
Schuebe loescht statt zu schreiben (Korrektur, ~8 %). Das steht bewusst nicht
als gemessener Fakt da -- es ist die Annahme, die diesen Aufbau von einem
Metronom unterscheidet, mehr nicht.

Aufruf:
    python3 spikes/g3_dauermessung/dauerlauf.py --selftest
    python3 spikes/g3_dauermessung/dauerlauf.py --dauer-sekunden 120
    python3 spikes/g3_dauermessung/dauerlauf.py            # endlos, bis Strg-C
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import random
import signal
import sys
import time
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parents[1]
KERN = WURZEL / "kern"
LAUF = HIER / "lauf"

sys.path.insert(0, str(KERN))
import dokumentdienst as dd  # noqa: E402  -- NUR benutzt, nicht geaendert.

WORT_POOL = (
    "und", "der", "die", "das", "Befund", "Messung", "Dienst", "Zeichen",
    "Absatz", "heute", "spaeter", "pruefen", "Schwelle", "Netz", "Update",
    "Teilnehmer", "also", "damit", "weil", "noch", "nicht", "immer", "kaum",
    " ", " ", ".", ",",
)


def _burst_text(rng: random.Random) -> str:
    n = rng.randint(1, 12)
    return "".join(rng.choice(WORT_POOL) for _ in range(n))


# ---------------------------------------------------------------- Relais --

def _verzoegerung(rng: random.Random, min_ms: float, max_ms: float):
    """Ein Aufruf = eine Wartezeit in Sekunden. 3 % Ausreisser nach oben --
    WLAN-Nachzuegler/Wiederholung, kein reines Gleichmass wie ein Kabel."""
    def _ziehen() -> float:
        if rng.random() < 0.03:
            return rng.uniform(0.1, 0.3)
        return rng.uniform(min_ms / 1000, max_ms / 1000)
    return _ziehen


async def _weiterleiten(quelle, ziel, verzoegerung_fn) -> None:
    async for nachricht in quelle:
        await asyncio.sleep(verzoegerung_fn())
        await ziel.send(nachricht)


async def _relais_handler(verbindung, ziel_url: str, verzoegerung_fn) -> None:
    import websockets
    async with websockets.connect(ziel_url) as ziel:
        hin = asyncio.create_task(_weiterleiten(verbindung, ziel, verzoegerung_fn))
        her = asyncio.create_task(_weiterleiten(ziel, verbindung, verzoegerung_fn))
        try:
            await asyncio.wait([hin, her], return_when=asyncio.FIRST_COMPLETED)
        finally:
            hin.cancel()
            her.cancel()


async def _relais_starten(host: str, port: int, ziel_url: str, verzoegerung_fn):
    import websockets
    return await websockets.serve(
        lambda v: _relais_handler(v, ziel_url, verzoegerung_fn), host, port)


# ------------------------------------------------------------ Teilnehmer --

async def _drain(ws) -> None:
    """Eingehendes leer lesen -- sonst waechst der interne Puffer bei einem
    Stundenlauf unbeschraenkt. Der Inhalt wird nicht gebraucht: die Messung
    interessiert sich fuer das, was DIESER Teilnehmer sendet."""
    try:
        async for _ in ws:
            pass
    except asyncio.CancelledError:
        pass
    except Exception:
        pass


async def teilnehmer(name: str, url: str, statz: dict, stop: asyncio.Event) -> None:
    import websockets
    from pycrdt import Doc, Text

    statz.update(updates_gesendet=0, bytes_gesendet=0, zeichen_getippt=0,
                 loeschungen=0, fehler=0, verbindungen=0)
    rng = random.Random(f"{name}-{time.time()}")

    while not stop.is_set():
        try:
            async with websockets.connect(url) as ws:
                statz["verbindungen"] += 1
                willkommen = json.loads(await ws.recv())
                assert willkommen["art"] == "willkommen", willkommen
                doc = Doc(client_id=willkommen["kennung"])
                text = Text()
                doc["dauerlauf"] = text
                doc.apply_update(base64.b64decode(willkommen["stand"]))
                letzter_stand = doc.get_state()

                drain_task = asyncio.create_task(_drain(ws))
                try:
                    while not stop.is_set():
                        for _ in range(rng.randint(2, 8)):
                            pos = len(str(text))
                            if rng.random() < 0.08 and pos > 0:
                                n = min(pos, rng.randint(1, 5))
                                with doc.transaction():
                                    del text[pos - n:pos]
                                statz["loeschungen"] += 1
                            else:
                                stueck = _burst_text(rng)
                                with doc.transaction():
                                    text.insert(pos, stueck)
                                statz["zeichen_getippt"] += len(stueck)
                            update = doc.get_update(letzter_stand)
                            letzter_stand = doc.get_state()
                            await ws.send(dd._rahmen("update", daten=update))
                            statz["updates_gesendet"] += 1
                            statz["bytes_gesendet"] += len(update)
                            await asyncio.sleep(rng.uniform(0.06, 0.22))
                            if stop.is_set():
                                break
                        pause = rng.uniform(10, 60) if rng.random() < 0.05 else rng.uniform(1, 8)
                        try:
                            await asyncio.wait_for(stop.wait(), timeout=pause)
                        except asyncio.TimeoutError:
                            pass
                finally:
                    drain_task.cancel()
        except asyncio.CancelledError:
            raise
        except Exception:
            statz["fehler"] += 1
            if stop.is_set():
                break
            await asyncio.sleep(1.0)  # kurze Atempause, dann neu verbinden


# -------------------------------------------------------------- Auswerten --

def _ableiten(z: dict, sekunden: float) -> dict:
    minuten = max(sekunden / 60, 1e-9)
    updates = z.get("updates_gesendet", 0)
    bytes_ = z.get("bytes_gesendet", 0)
    return {
        "updates_je_minute": round(updates / minuten, 1),
        "bytes_je_update": round(bytes_ / updates, 1) if updates else 0,
        "bytes_je_minute": round(bytes_ / minuten, 1),
        "bytes_je_zeichen": round(bytes_ / z["zeichen_getippt"], 1)
        if z.get("zeichen_getippt") else 0,
    }


def _schreibe_status(pfad: Path, start: float, stats: dict, dienst_kz) -> dict:
    import zeitmarke
    sekunden = time.monotonic() - start
    inhalt = {
        "stand": zeitmarke.jetzt(),
        "laufzeit_sekunden": round(sekunden, 1),
        "teilnehmer": {
            name: {**z, "abgeleitet": _ableiten(z, sekunden)}
            for name, z in stats.items()
        },
        "dienst_kennzahlen": dienst_kz.als_dict(),
    }
    pfad.parent.mkdir(parents=True, exist_ok=True)
    vorlaeufig = pfad.with_suffix(pfad.suffix + ".neu")
    vorlaeufig.write_text(json.dumps(inhalt, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    vorlaeufig.replace(pfad)
    return inhalt


# ------------------------------------------------------------------ Lauf --

async def hauptlauf(a: argparse.Namespace) -> dict:
    LAUF.mkdir(parents=True, exist_ok=True)
    dienst_kz = dd.Kennzahlen(ablage=LAUF / "dienst_kennzahlen.json")
    raum = dd.Raum(ablage=LAUF / "dokument.crdt")
    dienst_server = await dd.starten("127.0.0.1", a.dienst_port, raum, dienst_kz, zugang=False)
    dienst_port = next(iter(dienst_server.sockets)).getsockname()[1]

    rng = random.Random(1)
    verz_fn = _verzoegerung(rng, a.verzoegerung_min_ms, a.verzoegerung_max_ms)
    relais_server = await _relais_starten(
        "127.0.0.1", a.relais_port, f"ws://127.0.0.1:{dienst_port}", verz_fn)
    relais_port = next(iter(relais_server.sockets)).getsockname()[1]

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass  # Plattform ohne Signalhandler im Event-Loop (z.B. manche Tests)

    stats = {"fenster": {}, "mini": {}}
    t_fenster = asyncio.create_task(
        teilnehmer("fenster", f"ws://127.0.0.1:{dienst_port}", stats["fenster"], stop))
    t_mini = asyncio.create_task(
        teilnehmer("mini", f"ws://127.0.0.1:{relais_port}", stats["mini"], stop))

    start = time.monotonic()
    ende = start + a.dauer_sekunden if a.dauer_sekunden else None
    letzter_inhalt: dict = {}
    try:
        while not stop.is_set():
            warte = a.intervall_sekunden
            if ende is not None:
                warte = min(warte, max(0.1, ende - time.monotonic()))
            try:
                await asyncio.wait_for(stop.wait(), timeout=warte)
            except asyncio.TimeoutError:
                pass
            letzter_inhalt = _schreibe_status(LAUF / "status_fortlaufend.json", start, stats, dienst_kz)
            if ende is not None and time.monotonic() >= ende:
                break
    finally:
        stop.set()
        for t in (t_fenster, t_mini):
            t.cancel()
        await asyncio.gather(t_fenster, t_mini, return_exceptions=True)
        letzter_inhalt = _schreibe_status(LAUF / "status_fortlaufend.json", start, stats, dienst_kz)
        relais_server.close()
        dienst_server.close()
        await relais_server.wait_closed()
        await dienst_server.wait_closed()
    return letzter_inhalt


# --------------------------------------------------------------- Selbst --

def _selftest() -> int:
    """Kleinstpruefung, kein Framework: laeuft der Aufbau ueberhaupt, sendet
    er Zuwachs statt Vollstand (der Fund aus L-0a05b2/5b86ee4), und wird
    beim simulierten Teilnehmer tatsaechlich verzoegert?"""
    async def _lauf() -> None:
        a = argparse.Namespace(dienst_port=0, relais_port=0, dauer_sekunden=6,
                               intervall_sekunden=2, verzoegerung_min_ms=30,
                               verzoegerung_max_ms=60)
        ergebnis = await hauptlauf(a)
        fenster = ergebnis["teilnehmer"]["fenster"]
        mini = ergebnis["teilnehmer"]["mini"]
        assert fenster["updates_gesendet"] > 0, "fenster hat nichts gesendet"
        assert mini["updates_gesendet"] > 0, "mini hat nichts gesendet"
        # Der behobene Fehler war 1952 Byte je Update (Vollstand). Ein
        # Zuwachs fuer 1-12 Zeichen bleibt weit darunter.
        assert fenster["abgeleitet"]["bytes_je_update"] < 300, fenster["abgeleitet"]
        assert mini["abgeleitet"]["bytes_je_update"] < 300, mini["abgeleitet"]
        assert ergebnis["dienst_kennzahlen"]["updates"] >= (
            fenster["updates_gesendet"] + mini["updates_gesendet"])
        print("selftest OK:", json.dumps(
            {"fenster_bytes_je_update": fenster["abgeleitet"]["bytes_je_update"],
             "mini_bytes_je_update": mini["abgeleitet"]["bytes_je_update"],
             "dienst_updates": ergebnis["dienst_kennzahlen"]["updates"]}))

    asyncio.run(_lauf())
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--dauer-sekunden", type=float, default=0,
                   help="0 = endlos, bis Strg-C")
    p.add_argument("--dienst-port", type=int, default=4711)
    p.add_argument("--relais-port", type=int, default=4712)
    p.add_argument("--intervall-sekunden", type=float, default=15)
    p.add_argument("--verzoegerung-min-ms", type=float, default=5)
    p.add_argument("--verzoegerung-max-ms", type=float, default=40)
    a = p.parse_args()

    if a.selftest:
        return _selftest()

    ergebnis = asyncio.run(hauptlauf(a))
    print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
