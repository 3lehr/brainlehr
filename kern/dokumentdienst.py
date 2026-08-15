#!/usr/bin/env python3
"""Der Dokumentdienst -- ein Raum, ein Dokument, beliebig viele Teilnehmer.

Linie F (F2, F3, F4) aus `docs/PLAN_DOKUMENTDIENST_2026-08-14.md` und G1 aus
`docs/PLAN_SICHERHEIT_2026-08-14.md`. Rahmen ADR-010.

WAS ER IST: die Stelle, an der das gemeinsame Dokument WOHNT. Mensch und
Modell sind hier dasselbe -- ein Teilnehmer, der Updates schickt und Updates
bekommt. Das ist keine Bequemlichkeit, sondern die Entscheidung des Betreibers
vom 2026-08-14 ("Mehrere Menschen und die ki"): sobald die KI ein Sonderfall
mit eigenem Weg waere, driften Dokument und Anmerkung auseinander.

WAS ER NICHT IST: kein Mandant, kein Konto, kein Recht. Wohl aber eine
Zugangsschranke: auf 127.0.0.1 nicht, auf allem anderen ja -- eine REGEL statt
eines Schalters (siehe zugang_noetig). Geprueft wird ueber kern/ausweis.py, es
gibt keinen zweiten Anmeldeweg.

DAS PROTOKOLL, absichtlich klein (vier Nachrichten):

    Klient -> Server  {"art": "anmelden", "geheimnis": <str>}   (nur wenn noetig)
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

BEWUSST NICHT DRIN: keine Raumverwaltung, kein `pycrdt-websocket`. Letzteres legt
Dokumente selbst an und vergibt damit die Kennung selbst; erst wenn dieser
Rahmen zu duenn wird, lohnt die Pruefung, ob es sich die Auflage vorschreiben
laesst.

Aufruf:  python3 kern/dokumentdienst.py --selftest
         python3 kern/dokumentdienst.py --starten [--lan] [--ablage DATEI]
                                                  [--kennzahlen DATEI]
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from teilnehmer import neue_kennung  # noqa: E402

HOST = os.environ.get("BRAINLEHR_DIENST_HOST", "127.0.0.1")
PORT = int(os.environ.get("BRAINLEHR_DIENST_PORT", "4610"))

# Groesste Nachricht, die angenommen wird. Nicht selbst gezaehlt -- `websockets`
# bricht groessere Rahmen selbst ab (max_size). Ein Klient, der ein Dokument
# ueber diese Grenze schiebt, hat entweder ein Problem oder ist eines.
GROESSTE_NACHRICHT = 1 * 1024 * 1024

# Nachrichten je Verbindung und Fenster. Bewusst grosszuegig: Zeichen fuer
# Zeichen tippen erzeugt viele kleine Updates, und eine zu enge Bremse macht
# genau das kaputt, wofuer der Dienst gebaut ist. Der Zaehler dient zuerst dem
# MESSEN -- die Schwelle wird aus einer Nullmessung nachgezogen, nicht geraten.
FENSTER_SEKUNDEN = 10.0
NACHRICHTEN_JE_FENSTER = 2000


def zugang_noetig(host: str) -> bool:
    """Auf 127.0.0.1 nicht, auf allem anderen ja.

    EINE Regel statt eines Schalters: wer den Dienst aus dem eigenen Rechner
    heraus oeffnet, oeffnet ihn fuer jedes Geraet im selben Netz -- und dort
    steht nicht nur seines. Ein Schalter 'LAN ohne Ausweis' waere genau der
    Schalter, den man einmal fuer einen Test umlegt und nie zurueck.
    """
    return host not in ("127.0.0.1", "localhost", "::1")


class Kennzahlen:
    """Was der Dienst ueber sich selbst weiss. Zaehlen, nicht urteilen.

    Die Trennung ist Absicht: hier stehen nur Zahlen ohne Schwelle. Wann eine
    davon eine WARNUNG ist, entscheidet ein Melder anhand einer Nullmessung --
    eine geratene Schwelle schlaegt entweder nie an oder staendig, und
    staendig heisst: weggeklickt.

    ABLAGE (G1): Ohne sie sind die Zahlen beim naechsten Neustart weg und als
    Beleg wertlos, sobald der Dienst laenger laeuft als eine Sitzung. Mit
    `ablage` liest der Zaehler beim Anlegen und schreibt fort.

    ZWEI SCHREIBANLAESSE, und die Unterscheidung ist der ganze Trick:
    SELTENE Ereignisse (ein abgewiesener Zugang, eine unbekannte Art) werden
    SOFORT geschrieben -- das sind genau die, die ein Melder sehen soll, und
    einer davon kann der letzte vor einem Absturz sein. Haeufige (jedes Update,
    jedes Byte) werden gedrosselt, sonst kostet Zeichen-fuer-Zeichen-Tippen eine
    Schreiboperation je Tastendruck.
    """

    FELDER = (
        "verbindungen", "abgewiesene_zugaenge", "abgelehnte_updates",
        "unbekannte_arten", "kennungsverstoesse", "gebremste_nachrichten",
        "updates", "bytes_empfangen",
    )

    # Sofort schreiben. Alles andere wartet auf die Drosselung.
    SOFORT = ("abgewiesene_zugaenge", "abgelehnte_updates", "unbekannte_arten",
              "kennungsverstoesse", "gebremste_nachrichten")

    DROSSEL_SEKUNDEN = 5.0

    def __init__(self, ablage: Path | None = None, uhr=None) -> None:
        self.zahlen = dict.fromkeys(self.FELDER, 0)
        self.herkunft: dict[str, int] = {}
        self.ablage = Path(ablage) if ablage else None
        # Injizierbare Uhr: ohne sie laesst sich die Drosselung nicht pruefen,
        # ohne fuenf Sekunden zu warten.
        self.uhr = uhr or time.monotonic
        self._zuletzt = 0.0
        if self.ablage and self.ablage.exists():
            try:
                alt = json.loads(self.ablage.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                alt = {}
            for feld in self.FELDER:
                self.zahlen[feld] = int(alt.get(feld, 0))
            self.herkunft = {str(k): int(v) for k, v in (alt.get("herkunft") or {}).items()}

    def zaehle(self, feld: str, um: int = 1) -> None:
        if feld not in self.zahlen:
            raise KeyError(f"unbekannte Kennzahl {feld!r} -- Feld erst in FELDER aufnehmen")
        self.zahlen[feld] += um
        self._vielleicht_sichern(sofort=feld in self.SOFORT)

    def sah(self, adresse: str) -> None:
        neu = adresse not in self.herkunft
        self.herkunft[adresse] = self.herkunft.get(adresse, 0) + 1
        # Eine NEUE Herkunftsadresse ist selten und bedeutsam -- das zweite
        # Geraet im Netz ist genau der Fall, den ein Melder sehen soll.
        self._vielleicht_sichern(sofort=neu)

    def als_dict(self) -> dict:
        return {**self.zahlen, "herkunft": dict(self.herkunft)}

    def sichern(self) -> None:
        """Schreibt den Stand. Erst daneben, dann umbenennen -- eine halbe
        Zahlendatei ist schlimmer als eine alte."""
        if not self.ablage:
            return
        import zeitmarke

        self.ablage.parent.mkdir(parents=True, exist_ok=True)
        inhalt = {"stand": zeitmarke.jetzt(), **self.als_dict()}
        vorlaeufig = self.ablage.with_suffix(self.ablage.suffix + ".neu")
        vorlaeufig.write_text(json.dumps(inhalt, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
        vorlaeufig.replace(self.ablage)
        self._zuletzt = self.uhr()

    def _vielleicht_sichern(self, *, sofort: bool) -> None:
        if not self.ablage:
            return
        if sofort or self.uhr() - self._zuletzt >= self.DROSSEL_SEKUNDEN:
            self.sichern()


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


async def _anmeldung(verbindung, kennzahlen: Kennzahlen) -> bool:
    """Erste Nachricht muss `anmelden` mit einem beglaubigten Ausweis sein.

    Geprueft wird ueber `kern/ausweis.loese_auf` -- also dieselbe Schicht, die
    auch der Wissensspeicher benutzt: scrypt, zeitkonstanter Vergleich, kein
    Klartext in einer Datei. Hier wird kein zweiter Anmeldeweg gebaut.

    Das Geheimnis wird ausdruecklich NICHT protokolliert, auch nicht gekuerzt.
    """
    try:
        roh = await asyncio.wait_for(verbindung.recv(), 10.0)
        nachricht = json.loads(roh)
    except (asyncio.TimeoutError, ValueError):
        kennzahlen.zaehle("abgewiesene_zugaenge")
        await verbindung.send(_rahmen("fehler", grund="Anmeldung erwartet"))
        return False

    if nachricht.get("art") != "anmelden":
        kennzahlen.zaehle("abgewiesene_zugaenge")
        await verbindung.send(_rahmen("fehler", grund="erste Nachricht muss 'anmelden' sein"))
        return False

    import ausweis

    ausw = ausweis.loese_auf(geheimnis=nachricht.get("geheimnis") or None)
    if not ausw.beglaubigt:
        kennzahlen.zaehle("abgewiesene_zugaenge")
        await verbindung.send(_rahmen("fehler", grund="kein beglaubigter Ausweis"))
        return False
    return True


async def _teilnehmer(verbindung, raum: Raum, *, zugang: bool = False,
                      kennzahlen: Kennzahlen | None = None) -> None:
    k = kennzahlen if kennzahlen is not None else Kennzahlen()
    k.zaehle("verbindungen")
    try:
        k.sah(str(verbindung.remote_address[0]))
    except Exception:
        pass

    if zugang and not await _anmeldung(verbindung, k):
        await verbindung.close()
        return

    raum.verbindungen.add(verbindung)
    fenster_start = asyncio.get_running_loop().time()
    im_fenster = 0
    try:
        await verbindung.send(_rahmen("willkommen", kennung=neue_kennung(), stand=raum.stand()))
        async for roh in verbindung:
            k.zaehle("bytes_empfangen", len(roh))
            jetzt = asyncio.get_running_loop().time()
            if jetzt - fenster_start > FENSTER_SEKUNDEN:
                fenster_start, im_fenster = jetzt, 0
            im_fenster += 1
            if im_fenster > NACHRICHTEN_JE_FENSTER:
                k.zaehle("gebremste_nachrichten")
                await verbindung.send(_rahmen(
                    "fehler", grund=f"zu viele Nachrichten ({NACHRICHTEN_JE_FENSTER} je "
                                    f"{FENSTER_SEKUNDEN:.0f}s)"))
                continue
            nachricht = json.loads(roh)
            if nachricht.get("art") != "update":
                k.zaehle("unbekannte_arten")
                # Unbekanntes wird BENANNT, nicht verschluckt -- ein Klient, der
                # ins Leere spricht, soll das erfahren.
                await verbindung.send(_rahmen("fehler", grund=f"unbekannte Art {nachricht.get('art')!r}"))
                continue
            daten = _daten(nachricht)
            try:
                raum.anwenden(daten)
                k.zaehle("updates")
            except Exception as e:
                k.zaehle("abgelehnte_updates")
                # Ein Update, das der Raum nicht integrieren kann, darf die
                # VERBINDUNG nicht toeten -- sonst reisst ein einziger fehlerhafter
                # Klient alle anderen mit, und das Symptom sieht wie ein Netzfehler
                # aus. Haeufigste echte Ursache: der Klient benutzt seine
                # Teilnehmerkennung fuer ein ZWEITES Dokument, dessen Zaehler wieder
                # bei null anfaengt -- dann kollidieren zwei verschiedene Eintraege
                # unter derselben (Kennung, Zaehler). Eine Kennung gehoert genau
                # einem Dokument.
                await verbindung.send(_rahmen("fehler", grund=f"Update nicht anwendbar: {e}"))
                continue
            weiter = _rahmen("update", daten=daten)
            for andere in list(raum.verbindungen):
                if andere is not verbindung:
                    await andere.send(weiter)
    finally:
        raum.verbindungen.discard(verbindung)


async def starten(host: str = HOST, port: int = PORT, raum: Raum | None = None,
                  kennzahlen: Kennzahlen | None = None, zugang: bool | None = None):
    """Startet den Dienst und gibt den laufenden Server zurueck.

    `max_size` kommt von `websockets` selbst -- eine zu grosse Nachricht wird
    dort abgebrochen, bevor sie hier Speicher kostet. Selbst zaehlen waere
    dieselbe Arbeit noch einmal, nur spaeter.
    """
    import websockets

    r = raum or Raum()
    k = kennzahlen if kennzahlen is not None else Kennzahlen()
    # `zugang` ausdruecklich setzbar, damit die Anmeldung auf 127.0.0.1
    # pruefbar ist, ohne dafuer wirklich ins Netz zu lauschen.
    noetig = zugang_noetig(host) if zugang is None else zugang
    return await websockets.serve(
        lambda v: _teilnehmer(v, r, zugang=noetig, kennzahlen=k),
        host, port, max_size=GROESSTE_NACHRICHT)


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

        # Ein Update, das der Raum nicht integrieren kann, darf die VERBINDUNG
        # nicht toeten -- sonst reisst ein einziger fehlerhafter Klient alle
        # anderen mit, und das Symptom sieht wie ein Netzfehler aus.
        #
        # Der Anlass war ein echter Fall aus dem Bau dieses Selbsttests: ein
        # Klient legte mit SEINER Kennung ein zweites Dokument an, dessen
        # Zaehler wieder bei null begann -- der Raum brach mit "block parent
        # must be deleted or shared ref type" ab und riss den Verbindungs-
        # Handler mit. Eine Kennung gehoert genau einem Dokument. Als PROBE
        # taugt dieser Fall aber nicht: yrs verwirft ein Update, dessen
        # Zaehlerbereich es schon kennt, meist stumm -- die Ablehnung haengt
        # dann davon ab, was vorher lief. Deshalb hier ein Blob, der garantiert
        # kein Update ist.
        async with websockets.connect(url) as stoerer:
            await _empfang(stoerer, "Willkommen Stoerer")
            await stoerer.send(_rahmen("update", daten=b"kein CRDT, sondern Text"))
            abgelehnt = await _empfang(stoerer, "Ablehnung des unbrauchbaren Updates")
            assert abgelehnt["art"] == "fehler" and "nicht anwendbar" in abgelehnt["grund"], abgelehnt
            # Und die Verbindung lebt weiter: derselbe Klient schickt danach
            # etwas Gueltiges, und der Raum reicht es an B weiter.
            gut = Doc(client_id=neue_kennung())
            gut["nachher"] = Text("lebt")
            await stoerer.send(_rahmen("update", daten=gut.get_update()))
            assert (await _empfang(b, "Leben nach der Ablehnung"))["art"] == "update"

        # Eine Anmerkung ueber denselben Kanal: ein Teilnehmer haengt einen
        # Auftrag an einen Baustein, ein anderer sieht Baustein UND Anmerkung
        # samt Zustand -- ohne dass es dafuer einen zweiten Weg gaebe
        # (Auftrag 4 des Dienstplans). Eigene Verbindungen, also eigene
        # Kennungen: siehe die Zeilen darueber.
        import dokument as dok
        from baustein import Anker

        async with websockets.connect(url) as d, websockets.connect(url) as e:
            will_d = await _empfang(d, "Willkommen D")
            will_e = await _empfang(e, "Willkommen E")

            schreiber = dok.leeres_dokument(will_d["kennung"])
            stelle = dok.baustein_anhaengen(schreiber, "grafik", "Abbildung 1")
            merk = dok.anmerkung_setzen(
                schreiber, Anker(baustein=stelle, suchtext="Abbildung 1"),
                "hier ist die legende unleserlich", "darstellung", "mensch")
            assert dok.zustand_setzen(schreiber, merk, "umgesetzt") == "umgesetzt"
            await d.send(_rahmen("update", daten=schreiber.get_update()))

            leser = dok.leeres_dokument(will_e["kennung"])
            leser.apply_update(_daten(await _empfang(e, "Baustein und Anmerkung")))
            drueben = dok.anmerkungen(leser)
            assert [x.kennung for x in drueben] == [merk], drueben
            assert drueben[0].zustand == "umgesetzt"
            assert drueben[0].anker.baustein == stelle
            assert dok.verwaiste(leser) == [], "der Baustein kam mit, also nichts verwaist"

            # Und jetzt sitzt das MODELL hier wirklich zum ersten Mal -- ueber
            # denselben Dienst, nicht nur als Wert in einem Selbsttest
            # (Gesamtplan F5). Verbindung E haengt eine EIGENE Anmerkung an,
            # von_wem='modell', und schickt sie ueber den Dienst zurueck an D.
            modell_merk = dok.anmerkung_setzen(
                leser, Anker(baustein=stelle, suchtext="Abbildung 1"),
                "Alternativtext fehlt fuer die Sprachausgabe.", "darstellung", "modell")
            await e.send(_rahmen("update", daten=leser.get_update()))

            schreiber.apply_update(_daten(await _empfang(d, "Anmerkung des Modells")))
            wer = dok.mitwirkende(schreiber)
            assert wer["mensch"] == [merk], wer
            assert wer["modell"] == [modell_merk], wer

            # Gegenprobe: der Mensch verwirft den Vorschlag des Modells -- der
            # verworfene Zustand bleibt sichtbar, verschwindet nicht spurlos.
            assert dok.zustand_setzen(schreiber, modell_merk, "abgelehnt") == "abgelehnt"
            await d.send(_rahmen("update", daten=schreiber.get_update()))
            leser.apply_update(_daten(await _empfang(e, "Ablehnung durch den Menschen")))
            nach_ablehnung = {x.kennung: x for x in dok.anmerkungen(leser)}[modell_merk]
            assert nach_ablehnung.zustand == "abgelehnt"
            assert nach_ablehnung.verlauf == ["offen->abgelehnt"]
            assert modell_merk in dok.mitwirkende(leser)["modell"], "verworfen ist nicht verschwunden"

        # Negativfall: Unbekanntes wird benannt, nicht verschluckt. Auf einer
        # EIGENEN Verbindung -- eine, die schon im Raum sitzt, bekommt zwischen
        # Frage und Antwort die Broadcasts der anderen, und dann prueft der Fall
        # die Reihenfolge statt die Meldung.
        async with websockets.connect(url) as f:
            await _empfang(f, "Willkommen F")
            await f.send(json.dumps({"art": "quatsch"}))
            antwort = await _empfang(f, "Fehlermeldung auf Quatsch")
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

    # --- Zugang: die Regel, nicht der Schalter -----------------------------
    assert zugang_noetig("0.0.0.0") is True
    assert zugang_noetig("192.168.1.20") is True
    for daheim in ("127.0.0.1", "localhost", "::1"):
        assert zugang_noetig(daheim) is False, daheim

    zahlen = Kennzahlen()
    wache = await starten("127.0.0.1", 0, Raum(), zahlen, zugang=True)
    wport = next(iter(wache.sockets)).getsockname()[1]
    wurl = f"ws://127.0.0.1:{wport}"

    # Ohne Anmeldung: abgewiesen, und die Verbindung wird geschlossen.
    async with websockets.connect(wurl) as ohne:
        await ohne.send(_rahmen("update", daten=b"egal"))
        antwort = await _empfang(ohne, "Abweisung ohne Anmeldung")
        assert antwort["art"] == "fehler" and "anmelden" in antwort["grund"], antwort

    # Mit falschem Geheimnis: ebenfalls abgewiesen -- und der Grund nennt das
    # Geheimnis NICHT, auch nicht gekuerzt.
    async with websockets.connect(wurl) as falsch:
        await falsch.send(json.dumps({"art": "anmelden", "geheimnis": "falsches-wort"}))
        antwort = await _empfang(falsch, "Abweisung mit falschem Geheimnis")
        assert antwort["art"] == "fehler" and "beglaubigt" in antwort["grund"], antwort
        assert "falsches-wort" not in json.dumps(antwort), "Geheimnis darf nirgends auftauchen"

    assert zahlen.zahlen["abgewiesene_zugaenge"] == 2, zahlen.als_dict()
    assert zahlen.zahlen["verbindungen"] == 2
    assert list(zahlen.herkunft) == ["127.0.0.1"], zahlen.herkunft
    # Negativfall zu den Zaehlern: was nicht passiert ist, steht auf null --
    # sonst zaehlt der Zaehler nur mit und unterscheidet nichts.
    assert zahlen.zahlen["updates"] == 0 and zahlen.zahlen["abgelehnte_updates"] == 0

    wache.close()
    await wache.wait_closed()

    # Eine unbekannte Kennzahl faellt laut auf, statt still ins Leere zu zaehlen.
    try:
        zahlen.zaehle("gibtsnicht")
    except KeyError:
        pass
    else:
        raise AssertionError("unbekannte Kennzahl haette fallen muessen")

    # --- G1: die Zahlen ueberleben den Neustart ----------------------------
    with tempfile.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "kennzahlen.json"
        takt = [0.0]                      # gestellte Uhr statt fuenf Sekunden warten

        eins = Kennzahlen(ablage=pfad, uhr=lambda: takt[0])
        eins.zaehle("abgewiesene_zugaenge")        # selten -> sofort auf Platte
        assert pfad.exists(), "ein seltenes Ereignis muss sofort geschrieben werden"

        zwei = Kennzahlen(ablage=pfad, uhr=lambda: takt[0])   # wie nach einem Neustart
        assert zwei.zahlen["abgewiesene_zugaenge"] == 1, zwei.als_dict()

        # Haeufiges wird gedrosselt: dieselbe Sekunde schreibt NICHT nach.
        zwei.zaehle("updates")
        drei = Kennzahlen(ablage=pfad, uhr=lambda: takt[0])
        assert drei.zahlen["updates"] == 0, "gedrosseltes darf nicht sofort schreiben"
        # Grenzwert: genau die Drosselzeit spaeter schreibt es doch.
        takt[0] += Kennzahlen.DROSSEL_SEKUNDEN
        zwei.zaehle("updates")
        vier = Kennzahlen(ablage=pfad, uhr=lambda: takt[0])
        assert vier.zahlen["updates"] == 2, vier.als_dict()

        # Eine NEUE Herkunftsadresse ist selten und wird sofort geschrieben,
        # dieselbe ein zweites Mal nicht.
        zwei.sah("192.168.1.20")
        assert Kennzahlen(ablage=pfad).herkunft == {"192.168.1.20": 1}
        zwei.sah("192.168.1.20")
        assert Kennzahlen(ablage=pfad).herkunft == {"192.168.1.20": 1}, "zweites Mal ist nicht selten"

        # Negativfall: ein Lauf ohne jedes Ereignis schreibt eine Zeile mit
        # NULLEN, keine leere Datei -- Schweigen und "nichts passiert" muessen
        # unterscheidbar bleiben.
        leerer = Path(tmp) / "leer.json"
        Kennzahlen(ablage=leerer).sichern()
        gelesen = json.loads(leerer.read_text(encoding="utf-8"))
        assert gelesen["verbindungen"] == 0 and gelesen["herkunft"] == {}
        assert gelesen["stand"].endswith("Z"), gelesen["stand"]

        # Eine kaputte Datei setzt den Dienst nicht ausser Gefecht -- sie
        # beginnt bei null, statt beim Start zu werfen.
        kaputt = Path(tmp) / "kaputt.json"
        kaputt.write_text("{das ist kein JSON", encoding="utf-8")
        assert Kennzahlen(ablage=kaputt).zahlen["verbindungen"] == 0

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
    p.add_argument("--kennzahlen", default=os.environ.get("BRAINLEHR_KENNZAHLEN"),
                   help="Datei, in der die Zaehler stehen (ueberleben den Neustart)")
    p.add_argument("--lan", action="store_true",
                   help="auf allen Schnittstellen lauschen (0.0.0.0). Setzt Anmeldung "
                        "mit beglaubigtem Ausweis voraus -- im Netz steht nicht nur "
                        "der eigene Rechner")
    a = p.parse_args()
    if a.selftest:
        return _selftest()
    if a.starten:
        host = "0.0.0.0" if a.lan else a.host

        async def lauf():
            zahlen = Kennzahlen(ablage=Path(a.kennzahlen) if a.kennzahlen else None)
            server = await starten(host, a.port,
                                   Raum(ablage=Path(a.ablage)) if a.ablage else None,
                                   zahlen)
            print(f"Dokumentdienst laeuft auf ws://{host}:{a.port}"
                  + (" -- Anmeldung mit Ausweis noetig" if zugang_noetig(host)
                     else " -- nur dieser Rechner, keine Anmeldung noetig"))
            await server.wait_closed()
        asyncio.run(lauf())
        return 0
    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
