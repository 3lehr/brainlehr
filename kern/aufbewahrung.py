#!/usr/bin/env python3
"""Aufbewahrungsfristen je Datenklasse -- und ein Fristlauf, der den
SCHLUESSEL vernichtet, nicht die Zeile.

BDW-E12-AC1: „Jede persistierte Datenklasse besitzt Zweck, Frist und
Ablaufverhalten."
BDW-E13-AC1: „Ein Fristlauf entfernt alle Testableitungen und erzeugt einen
minimierten Nachweis."

GRUNDLAGE ist ADR-029 (2026-08-18): Eine Frist vernichtet den Schluessel,
nicht die Zeile. Kennung, Zeitpunkt und die Tatsache bleiben; der
Chiffretext darf stehen und belegt, dass nicht heimlich geloescht wurde.
Ohne diese Entscheidung waere eine Frist hier nicht baubar gewesen --
`knowledge_widerruf_archiv` behaelt Inhalte absichtlich fuer immer, weil das
Zurueckziehen eines Eintrags sonst seinen eigenen Beweis vernichtet.

DREI EIGENSCHAFTEN, die eine Datenklasse tragen MUSS (E12), und keine davon
ist Beiwerk:
  zweck            -- wofuer wird das aufbewahrt? Ohne Zweck laesst sich eine
                      Frist weder begruenden noch verlaengern.
  frist_tage       -- None heisst UNBEFRISTET, und das ist eine Entscheidung,
                      kein fehlender Wert. Deshalb muss sie ausdruecklich
                      getroffen werden (`unbefristet=True`), sonst wird
                      abgewiesen.
  ablaufverhalten  -- was beim Ablauf geschieht. Heute nur `schluessel_weg`;
                      die Aufzaehlung existiert, damit ein zweites Verhalten
                      spaeter benannt werden MUSS statt still danebenzulaufen.

DER MINIMIERTE NACHWEIS (E13) ist die schwierigere Haelfte. Ein
Loeschprotokoll, das den geloeschten Inhalt beschreibt, hebt die Loeschung
auf. Deshalb enthaelt der Nachweis: Kennung, Datenklasse, Zeitpunkt,
Ablaufverhalten -- und NICHTS aus dem Inhalt, keinen Titel, keinen Auszug.

Zeit kommt IMMER als Parameter (`jetzt_ts`). Ein Fristlauf, der die
Systemuhr liest, ist nicht nachstellbar -- und genau ein Fristlauf muss
nachstellbar sein, weil sein Ergebnis unwiederbringlich ist.

Aufruf:
    python3 aufbewahrung.py --selftest
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(WURZEL / "kern")]

from kundenschluessel import Kundenschluesselspeicher, Rechtssperre  # noqa: E402

TAG = 86_400.0

# Was beim Ablauf geschieht. Bewusst eine Aufzaehlung mit EINEM Wert: ein
# zweites Verhalten (etwa "anonymisieren") muss dann hier benannt werden,
# statt sich als Sonderfall einzuschleichen.
ABLAUFVERHALTEN = ("schluessel_weg",)


@dataclass(frozen=True)
class Datenklasse:
    name: str
    zweck: str
    frist_tage: float | None
    ablaufverhalten: str = "schluessel_weg"

    def __post_init__(self) -> None:
        if not self.zweck.strip():
            raise ValueError(f"{self.name}: zweck ist Pflicht -- ohne ihn ist die Frist nicht begruendbar")
        if self.ablaufverhalten not in ABLAUFVERHALTEN:
            raise ValueError(f"{self.name}: unbekanntes Ablaufverhalten {self.ablaufverhalten!r}, "
                             f"erlaubt: {ABLAUFVERHALTEN}")
        if self.frist_tage is not None and self.frist_tage <= 0:
            raise ValueError(f"{self.name}: frist_tage muss positiv sein oder None (unbefristet)")


@dataclass
class Aufbewahrungsordnung:
    """Die zentrale Policy (E12). Eine Datenklasse ohne Eintrag hier ist ein
    BEFUND, kein Standardfall -- deshalb wirft `frist_fuer` statt einen
    Vorgabewert zu erfinden."""

    _klassen: dict[str, Datenklasse] = field(default_factory=dict)

    def eintragen(self, klasse: Datenklasse) -> None:
        self._klassen[klasse.name] = klasse

    def unbefristet_eintragen(self, name: str, zweck: str) -> None:
        """Unbefristet ist eine ENTSCHEIDUNG, kein fehlender Wert -- deshalb
        ein eigener, ausdruecklicher Weg statt frist_tage=None nebenbei."""
        self.eintragen(Datenklasse(name=name, zweck=zweck, frist_tage=None))

    def frist_fuer(self, name: str) -> Datenklasse:
        if name not in self._klassen:
            raise KeyError(f"Datenklasse {name!r} hat keine Aufbewahrungsregel -- "
                           "das ist ein Befund, kein Standardfall (BDW-E12)")
        return self._klassen[name]

    def klassen(self) -> list[Datenklasse]:
        return sorted(self._klassen.values(), key=lambda k: k.name)


def fristlauf(speicher: Kundenschluesselspeicher, ordnung: Aufbewahrungsordnung,
              zuordnung: dict[str, str], jetzt_ts: float,
              nachweis_pfad: Path | None = None) -> dict:
    """Vernichtet die Schluessel aller abgelaufenen Eintraege und erzeugt
    einen minimierten Nachweis (E13).

    `zuordnung` bildet Kennung -> Datenklassenname ab.

    DREI LAGEN, die getrennt gezaehlt werden, weil sie Verschiedenes
    bedeuten:
      vernichtet  -- Frist abgelaufen, Schluessel weg.
      gehalten    -- Frist abgelaufen, aber ein Legal Hold sperrt (ADR-029).
                     Das ist KEIN Fehler des Laufs und wird laut gezaehlt.
      offen       -- Frist noch nicht abgelaufen oder unbefristet.
    """
    vernichtet, gehalten, offen, ohne_regel = [], [], [], []

    for ref, klassenname in sorted(zuordnung.items()):
        try:
            klasse = ordnung.frist_fuer(klassenname)
        except KeyError:
            ohne_regel.append(ref)
            continue
        if klasse.frist_tage is None:
            offen.append(ref)
            continue
        if not speicher.hat_bestanden(ref):
            continue
        alter_s = jetzt_ts - speicher.angelegt_ts(ref)
        if alter_s < klasse.frist_tage * TAG:
            offen.append(ref)
            continue
        try:
            speicher.widerrufen(ref)
            vernichtet.append({"ref": ref, "klasse": klassenname,
                               "verhalten": klasse.ablaufverhalten})
        except Rechtssperre as sperre:
            gehalten.append({"ref": ref, "klasse": klassenname, "grund": str(sperre)})

    nachweis = {
        "zeit": jetzt_ts,
        "vernichtet": vernichtet,
        "gehalten": gehalten,
        "offen_anzahl": len(offen),
        "ohne_regel": ohne_regel,
        # Die Selbstauskunft gehoert in den Nachweis, nicht in eine Doku, die
        # niemand neben ihm liest.
        "hinweis": ("Minimierter Nachweis (BDW-E13): enthaelt Kennung, Datenklasse, "
                    "Zeitpunkt und Ablaufverhalten. KEINEN Inhalt, keinen Titel, keinen "
                    "Auszug -- ein Loeschprotokoll, das den geloeschten Inhalt "
                    "beschreibt, hebt die Loeschung auf."),
    }
    if nachweis_pfad is not None:
        nachweis_pfad.parent.mkdir(parents=True, exist_ok=True)
        with nachweis_pfad.open("a", encoding="utf-8") as f:
            f.write(json.dumps(nachweis, ensure_ascii=False) + "\n")
    return nachweis


class _BestandsSpeicher:
    """Ein `Kundenschluesselspeicher`-Aussehen fuer den ECHTEN Bestand.

    ADR-031 Schritt 3, 2026-08-19. Bis heute nahm `fristlauf()` einen
    In-Prozess-Speicher entgegen und konnte den Bestand deshalb gar nicht
    erreichen -- gemessen und als BDW-E13 auf FAIL gesetzt (27ac332e). Statt
    `fristlauf()` umzubauen bekommt es hier das, was es ohnehin verlangt: ein
    Objekt mit `hat_bestanden`, `angelegt_ts` und `widerrufen`.

    Der Grund fuer diese Bauform statt einer zweiten Fristlauf-Funktion: die
    Zaehlweise (vernichtet / gehalten / offen / ohne_regel), der minimierte
    Nachweis und das Verhalten bei Legal Hold sind bereits belegt. Eine
    zweite Fassung waere eine zweite Stelle, an der sie auseinanderlaufen.

    Die Schluessel kommen aus `kern/schluesselablage.py` (eigene Datei), die
    Zeitpunkte aus `knowledge_nodes.created_at`.
    """

    def __init__(self, conn):
        self._conn = conn

    def hat_bestanden(self, ref: str) -> bool:
        import schluesselablage
        return schluesselablage.lage(ref) == "vorhanden"

    def angelegt_ts(self, ref: str) -> float:
        from datetime import datetime, timezone
        r = self._conn.execute(
            "select created_at from knowledge_nodes where id = ?", (ref,)).fetchone()
        if not r:
            raise KeyError(ref)
        return datetime.fromisoformat(
            r[0].replace("Z", "+00:00")).replace(tzinfo=timezone.utc).timestamp()

    def widerrufen(self, ref: str, jetzt_ts: float | None = None) -> None:
        import schluesselablage
        if schluesselablage.rechtssperre_steht(ref) is not None:
            raise Rechtssperre(
                f"{ref}: {schluesselablage.rechtssperre_steht(ref)}")
        schluesselablage.vernichten(ref, jetzt_ts if jetzt_ts is not None else 0.0)


def sensible_knoten(conn) -> dict[str, str]:
    """Kennung -> Datenklassenname fuer alle sensiblen Knoten.

    Die Klasse steht als Etikett `datenklasse:<name>` in `tags`. Warum dort
    und nicht in einer eigenen Spalte: Ein Knoten ohne Etikett faellt in
    `ohne_regel` und wird SICHTBAR -- eine Spalte mit Vorgabewert haette ihn
    still einer Klasse zugeschlagen, und damit einer Frist, die nie jemand
    fuer ihn entschieden hat (BDW-E12: eine Datenklasse ohne Eintrag ist ein
    Befund, kein Standardfall)."""
    import json as _json
    treffer = {}
    for kennung, etiketten in conn.execute(
            "select id, tags from knowledge_nodes where sensibel = 1"):
        klasse = "ohne_datenklasse"
        for e in _json.loads(etiketten or "[]"):
            if isinstance(e, str) and e.startswith("datenklasse:"):
                klasse = e.split(":", 1)[1]
                break
        treffer[kennung] = klasse
    return treffer


def fristlauf_bestand(conn, ordnung: Aufbewahrungsordnung, jetzt_ts: float,
                      nachweis_pfad: Path | None = None) -> dict:
    """Fristlauf ueber den ECHTEN Bestand (BDW-E13, ADR-031 Schritt 3).

    REIHENFOLGE, bindend und der Grund fuer Schritt 3 als letztem: Ein
    Fristlauf, der den Schluessel vernichtet, waehrend der Volltextindex noch
    Klartext haelt, erzeugt einen Nachweis ueber eine Loeschung, die nicht
    stattgefunden hat. Deshalb wirft diese Funktion, solange ein sensibler
    Knoten im Index steht -- lieber ein sprechender Abbruch als ein falscher
    Nachweis."""
    # Gezaehlt wird in knowledge_fts_docsize (eine Zeile je INDIZIERTEM
    # Dokument), nicht in knowledge_fts. Der erste Versuch fragte
    # `from knowledge_fts f join knowledge_nodes n on n.rowid = f.rowid` --
    # und zaehlte JEDEN sensiblen Knoten, weil eine fts5-Tabelle mit externer
    # Inhaltstabelle ohne MATCH schlicht die Inhaltstabelle liest. Die Sperre
    # haette damit immer ausgeloest und den Fristlauf dauerhaft blockiert:
    # ein Waechter, der immer anschlaegt, wird abgeschaltet.
    im_index = conn.execute(
        "select count(*) from knowledge_fts_docsize d join knowledge_nodes n "
        "on n.rowid = d.id where n.sensibel = 1").fetchone()[0]
    if im_index:
        raise RuntimeError(
            f"{im_index} sensible Knoten stehen im Volltextindex -- ein Fristlauf "
            "wuerde eine Loeschung bescheinigen, die nicht stattfindet. Erst "
            "migrationen/migrate_sensible_knoten.py fahren (ADR-031 Schritt 1).")
    return fristlauf(_BestandsSpeicher(conn), ordnung, sensible_knoten(conn),
                     jetzt_ts, nachweis_pfad)


def _selftest() -> int:
    o = Aufbewahrungsordnung()
    o.eintragen(Datenklasse("protokoll", "Nachvollziehbarkeit von Laeufen", frist_tage=30))
    o.unbefristet_eintragen("norm", "Betreiberentscheidungen gelten bis Widerruf")

    s = Kundenschluesselspeicher()
    for ref in ("p_alt", "p_neu", "n_alt", "p_gehalten"):
        s.neuer_schluessel(ref, ts=0.0)
        s.ablegen(ref, f"Inhalt {ref}", ts=0.0)
    s.rechtssperre_setzen("p_gehalten", grund="Betriebspruefung", ts=1.0)

    jetzt = 40 * TAG
    zuordnung = {"p_alt": "protokoll", "p_gehalten": "protokoll",
                 "p_neu": "protokoll", "n_alt": "norm", "fremd": "gibtsnicht"}
    # p_neu bekommt einen jungen Anlagezeitpunkt.
    s._metadaten["p_neu"] = jetzt - 5 * TAG

    n = fristlauf(s, o, zuordnung, jetzt_ts=jetzt)

    # Abgelaufen und ohne Sperre -> Schluessel weg, Chiffretext DA.
    assert [v["ref"] for v in n["vernichtet"]] == ["p_alt"], n["vernichtet"]
    assert s.chiffretext_vorhanden("p_alt"), "Chiffretext heimlich geloescht"
    assert s.hat_bestanden("p_alt"), "Tatsache verloren -- das ist der ganze Punkt"

    # Abgelaufen MIT Sperre -> gehalten, nicht vernichtet, und laut gezaehlt.
    assert [g["ref"] for g in n["gehalten"]] == ["p_gehalten"], n["gehalten"]
    assert s.lesen("p_gehalten") == "Inhalt p_gehalten"

    # Unbefristet und jung -> unangetastet.
    assert s.lesen("n_alt") and s.lesen("p_neu")
    assert n["offen_anzahl"] == 2, n["offen_anzahl"]

    # Klasse ohne Regel ist ein BEFUND, kein Standardfall.
    assert n["ohne_regel"] == ["fremd"], n["ohne_regel"]

    # DER NACHWEIS DARF NICHTS AUS DEM INHALT ENTHALTEN.
    text = json.dumps(n, ensure_ascii=False)
    assert "Inhalt p_alt" not in text, "Nachweis traegt den geloeschten Inhalt"

    # Pflichtfelder je Datenklasse (E12).
    for schlecht in (
        dict(name="x", zweck="  ", frist_tage=1),
        dict(name="x", zweck="ok", frist_tage=1, ablaufverhalten="wegwerfen"),
        dict(name="x", zweck="ok", frist_tage=0),
    ):
        try:
            Datenklasse(**schlecht)
        except ValueError:
            pass
        else:
            raise AssertionError(f"haette abgewiesen werden muessen: {schlecht}")

    print("aufbewahrung: Selbsttest gruen (1 vernichtet, 1 durch Legal Hold gehalten, "
          "2 offen, 1 ohne Regel; Nachweis inhaltsfrei; 3 Negativfaelle)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
