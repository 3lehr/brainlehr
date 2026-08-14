#!/usr/bin/env python3
"""Der Dokumentdienst -- ein Raum, ein Dokument, beliebig viele Teilnehmer.

Schritt 2 aus `docs/PLAN_DOKUMENTDIENST_2026-08-14.md`, Rahmen ADR-010.

WAS ER IST: die Stelle, an der das gemeinsame Dokument WOHNT. Mensch und
Modell sind hier dasselbe -- ein Teilnehmer, der Updates schickt und Updates
bekommt. Das ist keine Bequemlichkeit, sondern die Entscheidung des Betreibers
vom 2026-08-14 ("Mehrere Menschen und die ki"): sobald die KI ein Sonderfall
mit eigenem Weg waere, driften Dokument und Anmerkung auseinander.

WAS ER NICHT IST: kein Mandant, kein Konto, kein Recht. "Erst LAN, Konten
spaeter" -- und deshalb bindet er per Vorgabe auf 127.0.0.1. Wer ihn ins Netz
stellt, tut das ueber BRAINLEHR_DIENST_HOST und weiss dann, dass jeder im
selben Netz schreiben darf. Der Ausweis (kern/ausweis.py) ist die vorgesehene
Naht, nicht ein spaeterer Einfall.

DAS PROTOKOLL, absichtlich klein (drei Nachrichten):

    Server -> Klient  {"art": "willkommen", "kennung": <int>, "stand": <base64>}
    Klient -> Server  {"art": "update", "daten": <base64>}
    Server -> Klient  {"art": "update", "daten": <base64>}    (an alle anderen)

Die Kennung kommt VOM DIENST. Genau das ist der Punkt: `yswift` schneidet auf
32 Bit ab, `pycrdt` wuerfelt bis 2^53, und darueber verdoppelt sich Text still
(ADR-010, `L-44dc9f`). Ein Klient, der sich selbst eine Kennung gibt, ist die
Fehlerquelle -- also gibt der Dienst sie aus, ueber `kern/teilnehmer.py`.

WARUM BASE64 UND NICHT ROHE BINAERRAHMEN: ein Rahmen, den man mit blossem Auge
lesen kann, ist bei einem Protokollfehler in Sekunden zu diagnostizieren; ein
Binaerrahmen kostet dafuer ein Werkzeug. Der Preis ist ein Drittel mehr Bytes
auf einer Verbindung, die im eigenen Netz laeuft. Wenn das je knapp wird, ist
der Wechsel eine Zeile in `_sende`/`_lies`.

BEWUSST NICHT DRIN: keine Ablage (Schritt 3 des Plans -- der Stand lebt bis zum
Neustart), keine Raumverwaltung, kein `pycrdt-websocket`. Letzteres legt
Dokumente selbst an und vergibt damit die Kennung selbst; erst wenn dieser
Rahmen zu duenn wird, lohnt die Pruefung, ob es sich die Auflage vorschreiben
laesst.

Aufruf:  python3 kern/dokumentdienst.py --selftest
         python3 kern/dokumentdienst.py --starten [--port 4610]
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from teilnehmer import neue_kennung  # noqa: E402

HOST = os.environ.get("BRAINLEHR_DIENST_HOST", "127.0.0.1")
PORT = int(os.environ.get("BRAINLEHR_DIENST_PORT", "4610"))


class Raum:
    """Ein Dokument und die Verbindungen, die daran haengen.

    Der Raum haelt ein eigenes pycrdt-Dokument -- nicht, weil er mitreden
    wuerde, sondern weil ein Neuankoemmling den STAND braucht und nicht die
    Geschichte aller Updates seit dem Start.

    ABLAGE (Schritt 3 des Plans): Wird ein `ablage`-Pfad uebergeben, liest der
    Raum ihn beim Anlegen und schreibt nach jedem Update. Bewusst eine DATEI
    und nicht die Wissensdatenbank: ein Dokument ist kein Wissensknoten, und
    eine Tabelle anzulegen, deren Form noch niemand kennt, waere eine leere
    Spalte auf Vorrat (`b6305304`). Wenn die Ablage je mehr koennen muss --
    Fassungen, Suche, Rechte --, ist DAS der Moment fuer ein Schema, nicht
    heute.
    """

    def __init__(self, ablage: Path | None = None) -> None:
        from pycrdt import Doc

        # Auch der Dienst selbst haelt sich an die Auflage: sein Dokument ist
        # ein Teilnehmer wie jeder andere.
        self.doc = Doc(client_id=neue_kennung())
        self.verbindungen: set = set()
        self.ablage = Path(ablage) if ablage else None
        if self.ablage and self.ablage.exists():
            self.doc.apply_update(self.ablage.read_bytes())

    def stand(self) -> bytes:
        return self.doc.get_update()

    def anwenden(self, daten: bytes) -> None:
        self.doc.apply_update(daten)
        self._sichern()

    def _sichern(self) -> None:
        """Vollstand nach jedem Update. Erst schreiben, dann umbenennen.

        ponytail: schreibt den GANZEN Stand je Update statt nur den Zuwachs --
        bei einem Schriftsatz sind das Kilobytes, das traegt lange. Wird es
        knapp, ist der Umstieg auf angehaengte Updates plus gelegentliche
        Verdichtung die naechste Stufe.

        Das Umbenennen ist kein Zierat: ein Absturz mitten im Schreiben wuerde
        sonst eine halbe Datei hinterlassen, und eine halbe CRDT-Ablage ist
        nicht halb gut, sondern unlesbar.
        """
        if not self.ablage:
            return
        self.ablage.parent.mkdir(parents=True, exist_ok=True)
        vorlaeufig = self.ablage.with_suffix(self.ablage.suffix + ".neu")
        vorlaeufig.write_bytes(self.stand())
        vorlaeufig.replace(self.ablage)


def _rahmen(art: str, **felder) -> str:
    for k, v in list(felder.items()):
        if isinstance(v, (bytes, bytearray)):
            felder[k] = base64.b64encode(v).decode("ascii")
    return json.dumps({"art": art, **felder})


def _daten(nachricht: dict) -> bytes:
    return base64.b64decode(nachricht["daten"])


async def _teilnehmer(verbindung, raum: Raum) -> None:
    raum.verbindungen.add(verbindung)
    try:
        await verbindung.send(_rahmen("willkommen", kennung=neue_kennung(), stand=raum.stand()))
        async for roh in verbindung:
            nachricht = json.loads(roh)
            if nachricht.get("art") != "update":
                # Unbekanntes wird BENANNT, nicht verschluckt -- ein Klient, der
                # ins Leere spricht, soll das erfahren.
                await verbindung.send(_rahmen("fehler", grund=f"unbekannte Art {nachricht.get('art')!r}"))
                continue
            daten = _daten(nachricht)
            raum.anwenden(daten)
            weiter = _rahmen("update", daten=daten)
            for andere in list(raum.verbindungen):
                if andere is not verbindung:
                    await andere.send(weiter)
    finally:
        raum.verbindungen.discard(verbindung)


async def starten(host: str = HOST, port: int = PORT, raum: Raum | None = None):
    """Startet den Dienst und gibt den laufenden Server zurueck."""
    import websockets

    r = raum or Raum()
    return await websockets.serve(lambda v: _teilnehmer(v, r), host, port)


async def _empfang(verbindung, was: str, sekunden: float = 5.0) -> dict:
    """Warten mit Frist. Ohne sie HAENGT der Selbsttest bei einem Defekt, statt
    zu fallen -- gemessen: wird das Weiterreichen abgeschaltet, wartet er ewig.
    Ein Test, der haengt, blockiert die Suite und sieht dabei nicht wie ein
    Fehler aus."""
    try:
        return json.loads(await asyncio.wait_for(verbindung.recv(), sekunden))
    except asyncio.TimeoutError:
        raise AssertionError(f"nichts empfangen binnen {sekunden}s: {was}") from None


async def _selftest_async() -> int:
    import websockets
    from pycrdt import Doc, Text

    raum = Raum()
    # Port 0: das Betriebssystem sucht einen freien. Ein fest verdrahteter Port
    # in einem Selbsttest streitet sich irgendwann mit einem laufenden Dienst,
    # und das Symptom sieht dann wie ein Fehler im Protokoll aus.
    server = await starten("127.0.0.1", 0, raum)
    port = next(iter(server.sockets)).getsockname()[1]
    url = f"ws://127.0.0.1:{port}"

    async with websockets.connect(url) as a, websockets.connect(url) as b:
        will_a = await _empfang(a, "Willkommen A")
        will_b = await _empfang(b, "Willkommen B")
        assert will_a["art"] == "willkommen"
        # Die Auflage, und sie ist der Grund fuer diesen Dienst:
        assert 1 <= will_a["kennung"] <= 2**32 - 1, will_a["kennung"]
        assert will_a["kennung"] != will_b["kennung"], "zwei Teilnehmer, eine Kennung"

        # A schreibt, B bekommt es -- ohne je mit A gesprochen zu haben.
        doc_a = Doc(client_id=will_a["kennung"])
        doc_a["t"] = ta = Text("Hallo")
        await a.send(_rahmen("update", daten=doc_a.get_update()))

        doc_b = Doc(client_id=will_b["kennung"])
        doc_b["t"] = Text()
        doc_b.apply_update(_daten(await _empfang(b, "Update von A")))
        assert str(doc_b["t"]) == "Hallo", str(doc_b["t"])

        # Gleichzeitig in denselben Satz: beide Seiten laufen zusammen.
        ta.insert(5, " Welt")
        doc_b["t"].insert(0, ">> ")
        await a.send(_rahmen("update", daten=doc_a.get_update()))
        await b.send(_rahmen("update", daten=doc_b.get_update()))
        doc_b.apply_update(_daten(await _empfang(b, "gleichzeitiges Update von A")))
        doc_a.apply_update(_daten(await _empfang(a, "gleichzeitiges Update von B")))
        assert str(doc_a["t"]) == str(doc_b["t"]), f"divergent: {str(doc_a['t'])!r} {str(doc_b['t'])!r}"
        assert "Welt" in str(doc_a["t"]) and ">>" in str(doc_a["t"])

        # Der Dienst haelt den Stand: ein Dritter bekommt ihn beim Verbinden,
        # ohne dass jemand etwas wiederholt.
        async with websockets.connect(url) as c:
            will_c = await _empfang(c, "Willkommen C")
            doc_c = Doc(client_id=will_c["kennung"])
            doc_c["t"] = Text()
            doc_c.apply_update(base64.b64decode(will_c["stand"]))
            assert str(doc_c["t"]) == str(doc_a["t"]), str(doc_c["t"])

        # Negativfall: Unbekanntes wird benannt, nicht verschluckt.
        await a.send(json.dumps({"art": "quatsch"}))
        antwort = await _empfang(a, "Fehlermeldung auf Quatsch")
        assert antwort["art"] == "fehler" and "quatsch" in antwort["grund"], antwort

    server.close()
    await server.wait_closed()

    # Ablage: der Stand ueberlebt den Dienst. Rot davor -- ohne Ablagepfad
    # startet ein Raum leer, und genau das prueft der Negativfall unten.
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "raum.ycrdt"
        eins = Raum(ablage=pfad)
        d = Doc(client_id=neue_kennung())
        d["t"] = Text("Ueberlebt einen Neustart")
        eins.anwenden(d.get_update())
        assert pfad.exists(), "nach dem ersten Update muss die Ablage liegen"

        zwei = Raum(ablage=pfad)          # so, als waere der Dienst neu gestartet
        gelesen = Doc(client_id=neue_kennung())
        gelesen["t"] = Text()
        gelesen.apply_update(zwei.stand())
        assert str(gelesen["t"]) == "Ueberlebt einen Neustart", str(gelesen["t"])

        # Negativfall: OHNE Ablage faengt ein Raum leer an -- sonst pruefte der
        # Fall oben nur, dass irgendein Stand existiert.
        ohne = Raum()
        leer = Doc(client_id=neue_kennung())
        leer["t"] = Text()
        leer.apply_update(ohne.stand())
        assert str(leer["t"]) == "", f"Raum ohne Ablage muss leer starten, war {str(leer['t'])!r}"

        # Kein Halbstand: waehrend des Schreibens existiert die Zieldatei
        # entweder ganz alt oder ganz neu, nie halb.
        assert not list(Path(tmp).glob("*.neu")), "vorlaeufige Datei blieb liegen"

    print("dokumentdienst: Selbsttest bestanden")
    return 0


def _selftest() -> int:
    try:
        import websockets  # noqa: F401
        from pycrdt import Doc  # noqa: F401
    except ImportError as e:
        print(f"dokumentdienst: uebersprungen -- {e.name} fehlt (siehe requirements.txt)")
        return 0
    return asyncio.run(_selftest_async())


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--starten", action="store_true")
    p.add_argument("--host", default=HOST)
    p.add_argument("--port", type=int, default=PORT)
    p.add_argument("--ablage", default=os.environ.get("BRAINLEHR_DOKUMENT"),
                   help="Datei, in der der Stand liegt (ueberlebt den Neustart)")
    a = p.parse_args()
    if a.selftest:
        return _selftest()
    if a.starten:
        async def lauf():
            server = await starten(a.host, a.port,
                                   Raum(ablage=Path(a.ablage)) if a.ablage else None)
            print(f"Dokumentdienst laeuft auf ws://{a.host}:{a.port}")
            await server.wait_closed()
        asyncio.run(lauf())
        return 0
    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
