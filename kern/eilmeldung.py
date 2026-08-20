#!/usr/bin/env python3
"""Eilmeldung senden -- mit Anlass, Adressat und Frist, sonst gar nicht.

ANLASS: Betreiberfragen 2026-08-20 -- *"wann waere es gerechtfertigt das ein
'chat' llm nachrichten an andere schicken darf? wann waere es gerechtfertigt
das sie antworten einfordern darf?"* -- und die Freigabe, das zu bauen.

DIE KRITERIEN STEHEN HIER ALS PFLICHTFELDER, nicht als Absatz in einer
Regeldatei. Der Unterschied ist der ganze Punkt dieses Tages: Ein Text sagt,
was gelten SOLL; eine Signatur laesst das Falsche gar nicht erst zu. Wer keinen
Anlass nennen kann, hat keinen.

DREI ANLAESSE, und nur diese drei:

  kollision   Ich halte etwas, das eine andere Sitzung gerade anfasst.
              Schweigen kostet hier fremde Arbeit -- der einzige Fall, in dem
              eine Meldung immer billiger ist als keine.
  entwertung  Eine Annahme, auf der eine andere Sitzung nachweislich arbeitet,
              ist widerlegt. Nicht "ich habe etwas Interessantes gefunden",
              sondern "das, worauf du baust, stimmt nicht mehr".
  befund      Etwas zwingt den Empfaenger zum Handeln, BEVOR er weitermacht.

NICHT gesendet wird fuer Fortschritt, Erfolge, Lehren, Statusberichte. Dafuer
ist der Wissensspeicher da, und der wird gelesen, wenn er gebraucht wird.

EINE FRAGE BRAUCHT EINE FRIST. Wer eine Antwort einfordert, sagt, was er tut,
wenn keine kommt -- sonst blockiert eine unbeantwortete Frage auf Dauer. Der
Bestand kennt die richtige Form bereits: "wer die Datei haelt, moege sich
melden; sonst wird sie am 2026-08-17 als frei behandelt."

RUECKWIRKUNG (Norm 17b14a32): `--pruefe-verlauf` misst, wie viele der
BESTEHENDEN Eilmeldungen diese Schranke bestehen wuerden -- nicht nur die
neuen.

    python3 kern/eilmeldung.py --selftest
    python3 kern/eilmeldung.py --pruefe-verlauf
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken")]

ANLAESSE = ("kollision", "entwertung", "befund")


class Unzulaessig(ValueError):
    """Die Meldung erfuellt die Sendekriterien nicht.

    Eine Ausnahme, kein stilles Weglassen: Wer eine Eilmeldung absetzen will
    und es nicht darf, soll den Grund lesen -- nicht ins Leere senden."""


def pruefe(anlass: str, an: str, titel: str, zusammenfassung: str,
           frage: bool = False, frist: str = "", sonst: str = "") -> dict:
    """Prueft eine geplante Meldung. Wirft, statt sie stumm abzulehnen."""
    if anlass not in ANLAESSE:
        raise Unzulaessig(
            f"Anlass {anlass!r} ist keiner der drei zulaessigen: "
            + ", ".join(ANLAESSE)
            + ". Fortschritt, Erfolge und Lehren gehoeren in den "
              "Wissensspeicher, nicht in den Eilkanal.")
    if not an.strip():
        raise Unzulaessig(
            "Adressat fehlt. `alle` ist zulaessig, muss aber DASTEHEN -- "
            "gemessen am 2026-08-20: 17 laufende Sitzungen, und wer dreimal "
            "eine fremde Meldung bekommt, liest die vierte nicht mehr.")
    if len(titel.strip()) < 12 or len(zusammenfassung.strip()) < 40:
        raise Unzulaessig(
            "Titel oder Zusammenfassung zu kurz. Der Empfaenger sieht NUR "
            "diese beiden -- was dort nicht steht, existiert fuer ihn nicht.")
    if frage and (not frist.strip() or not sonst.strip()):
        raise Unzulaessig(
            "Eine Frage braucht eine Frist UND die Angabe, was ohne Antwort "
            "geschieht. Ohne beides blockiert sie auf Dauer. Vorbild aus dem "
            "Bestand: 'wer die Datei haelt, moege sich melden; sonst wird sie "
            "am <Datum> als frei behandelt.'")
    etiketten = ["dringend", f"an:{an.strip().lower()}", f"anlass:{anlass}"]
    return {"tags": etiketten, "titel": titel.strip(),
            "zusammenfassung": zusammenfassung.strip(),
            "frage": bool(frage), "frist": frist.strip(), "sonst": sonst.strip()}


def _verlauf(db: Path | None = None) -> int:
    """Wie viele der BESTEHENDEN Eilmeldungen bestuenden diese Schranke?"""
    import ort
    import rueckwirkung as r
    pfad = db or Path(ort.DB)
    try:
        conn = sqlite3.connect(f"file:{pfad}?mode=ro", uri=True)
    except sqlite3.Error:
        return 0
    zeilen = conn.execute(
        "SELECT title, summary, tags FROM knowledge_nodes "
        "WHERE tags LIKE '%\"dringend\"%' AND IFNULL(zurueckgezogen,0)=0").fetchall()
    conn.close()

    def etiketten_von(z) -> list[str]:
        try:
            e = json.loads(z[2] or "[]")
        except ValueError:
            return []
        return [str(x).lower() for x in e] if isinstance(e, list) else []

    # ZWEI ZAHLEN, nicht eine. Der erste Lauf meldete "39 von 39 (100 %)" --
    # richtig gerechnet und trotzdem alarmistisch: Eine fehlende Adresse ist
    # KEIN Mangel, sie bedeutet absichtlich "an alle" (siehe
    # haken/eilmeldung_frisch.py). Ein Zaehler, der eine Vorgabe als Verstoss
    # zaehlt, erzeugt eine Zahl, die niemand ernst nimmt -- und das ist
    # dieselbe Klasse wie ein Waechter, der immer anschlaegt.
    ohne_anlass = r.zaehle(
        zeilen, lambda z: not any(e.startswith("anlass:") for e in etiketten_von(z)),
        lambda z: z[0])
    r.bericht("Eilmeldungen ohne Anlass (echter Mangel)", ohne_anlass)
    gerichtet = r.zaehle(
        zeilen, lambda z: any(e.startswith("an:") for e in etiketten_von(z)),
        lambda z: z[0], hoechstens_beispiele=0)
    print(gerichtet.zeile("davon ausdruecklich adressiert (Rest gilt fuer alle)"))
    return 0


def _selftest() -> int:
    gut = pruefe("kollision", "fahrtenbuch", "Ich halte DienstAufsicht.swift",
                 "Seit 10:15 in Bearbeitung, bitte nicht anfassen bis zum Commit.")
    assert gut["tags"] == ["dringend", "an:fahrtenbuch", "anlass:kollision"], gut

    # a) Kein Anlass -> abgewiesen, mit den drei zulaessigen im Text.
    for schlecht in ("fortschritt", "", "wichtig"):
        try:
            pruefe(schlecht, "alle", "Ein langer Titel hier",
                   "Eine hinreichend lange Zusammenfassung fuer den Empfaenger.")
            raise AssertionError(f"{schlecht!r} haette abgewiesen werden muessen")
        except Unzulaessig as e:
            assert "kollision" in str(e)

    # b) Kein Adressat -> abgewiesen. 'alle' ist erlaubt, muss aber dastehen.
    try:
        pruefe("befund", "  ", "Ein langer Titel hier",
               "Eine hinreichend lange Zusammenfassung fuer den Empfaenger.")
        raise AssertionError("fehlender Adressat haette abgewiesen werden muessen")
    except Unzulaessig:
        pass
    assert pruefe("befund", "alle", "Ein langer Titel hier",
                  "Eine hinreichend lange Zusammenfassung fuer den Empfaenger.")

    # c) Zu kurz -> abgewiesen. Der Empfaenger sieht nur Titel und Zusammenfassung.
    try:
        pruefe("befund", "alle", "kurz", "auch kurz")
        raise AssertionError("zu kurze Meldung haette abgewiesen werden muessen")
    except Unzulaessig:
        pass

    # d) EINE FRAGE OHNE FRIST -> abgewiesen. Das ist der Kern der zweiten
    #    Betreiberfrage: eine Antwort einfordern darf nur, wer sagt, was ohne
    #    Antwort geschieht.
    try:
        pruefe("kollision", "alle", "Wer haelt DienstAufsicht.swift?",
               "Bitte melden, ich brauche die Datei fuer ADR-023.", frage=True)
        raise AssertionError("Frage ohne Frist haette abgewiesen werden muessen")
    except Unzulaessig as e:
        assert "Frist" in str(e)
    assert pruefe("kollision", "alle", "Wer haelt DienstAufsicht.swift?",
                  "Bitte melden, ich brauche die Datei fuer ADR-023.",
                  frage=True, frist="2026-08-21T12:00:00+0200",
                  sonst="wird die Datei als frei behandelt")

    print("eilmeldung: Selbsttest gruen (7 Faelle: gueltige Meldung, drei "
          "unzulaessige Anlaesse, fehlender Adressat, zu kurz, Frage ohne "
          "Frist abgewiesen und mit Frist zugelassen)")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    if "--pruefe-verlauf" in sys.argv:
        sys.exit(_verlauf())
    print(__doc__.strip().splitlines()[0])
