#!/usr/bin/env python3
"""Gemeinsame Bauform fuer Rueckwirkungs-Zaehler.

ANLASS: Norm 17b14a32 (Rang 2, 2026-08-20), Betreiberweisung woertlich --
*"wird sowas herausgefunden muss die ki oder ein tool pruefen ob auch alles
schon geschriebene diesen weg geht"*. Und zur Bauform: *"Drei Zaehler mit
derselben Aufgabe und drei verschiedenen Bauformen sind zwei zu viel."*

DER UNTERSCHIED ZUM WAECHTER, und er ist der ganze Zweck:
  Ein Waechter sagt  "dieser Commit ist in Ordnung"      -- ja/nein, Zuwachs.
  Ein Zaehler sagt   "37 von 214 Stellen erfuellen es"   -- Zahl, Bestand.
Ein Mechanismus, der nur neu Geschriebenes prueft, laesst alles Aeltere stumm
daneben liegen -- und niemand merkt es, weil der Melder gruen ist.

ZWEI ZAHLEN, NIE EINE. `zaehle()` gibt immer Treffer UND Nenner zurueck, und
`bericht()` druckt beide. Eine Fortschrittszahl ohne Nenner ist der Fall vom
2026-08-18, der zur Belegspalte fuehrte ("U1 bis U7 abgearbeitet" -- von 40).

STICHPROBE GEHOERT DAZU, nicht als Kuer. Am 2026-08-20 haette eine reine Quote
(0,9 %) einen Waechter gerechtfertigt, den die Stichprobe binnen einer Minute
entwertete: 90 % der Treffer waren vollstaendige Aussagen (`L-ca295c`).
Deshalb liefert `bericht()` immer auch Beispiele.

    python3 kern/rueckwirkung.py --selftest
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable


@dataclass
class Befund:
    """Was ein Rueckwirkungslauf gemessen hat."""
    nenner: int = 0
    treffer: int = 0
    beispiele: list[str] = field(default_factory=list)

    @property
    def quote(self) -> float:
        return self.treffer / self.nenner if self.nenner else 0.0

    def zeile(self, was: str, rahmen: str = "") -> str:
        """Eine Zeile, die beide Zahlen UND ihren Bezugsrahmen nennt.

        DER RAHMEN IST PFLICHT, seit 2026-08-20 (L-352afa, fuenf Vorkommen,
        neun gezaehlte Messartefakte): "Ein Messwerkzeug beantwortet eine
        ENGERE Frage als der Satz, in dem seine Zahl dann steht. Das Protokoll
        misst protokollierte Abrufe, nicht alle. Die Stichprobe misst
        Titel-als-Anfrage, nicht Auffindbarkeit."

        Die Regel dort lautet woertlich: nicht "1 von 2", sondern "1 von 2,
        gemessen ueber zwei Aufgaben mit LIMIT 30". Laesst sich der
        Bezugsrahmen nicht in einem Nebensatz nennen, ist es keine Messung,
        sondern ein Eindruck mit Ziffern.

        Leer bleiben darf er nur, wenn der Gegenstand die VOLLSTAENDIGE Menge
        ist -- dann steht der Rahmen im Nenner selbst."""
        satz = f"{was}: {self.treffer} von {self.nenner} ({self.quote:.1%})"
        return satz + (f", gemessen {rahmen}" if rahmen else "")


def zaehle(gegenstaende: Iterable, trifft: Callable[[object], bool],
           beschreibe: Callable[[object], str] | None = None,
           hoechstens_beispiele: int = 5) -> Befund:
    """Zaehlt, wie viele Gegenstaende die Bedingung erfuellen -- mit Nenner.

    `trifft` darf werfen; ein Gegenstand, der nicht beurteilbar ist, zaehlt in
    den NENNER, aber nicht in die Treffer. Ihn wegzulassen waere die
    gefaehrlichere Wahl: die Quote saehe besser aus, weil die schwierigen
    Faelle verschwinden."""
    b = Befund()
    for g in gegenstaende:
        b.nenner += 1
        try:
            ja = bool(trifft(g))
        except Exception:
            ja = False
        if ja:
            b.treffer += 1
            if beschreibe and len(b.beispiele) < hoechstens_beispiele:
                try:
                    b.beispiele.append(beschreibe(g)[:160])
                except Exception:
                    pass
    return b


def bericht(was: str, b: Befund, rahmen: str = "", ziel=None) -> str:
    """Zeile plus Stichprobe. Beides Pflicht, nicht Kuer -- die Stichprobe
    gegen die geschoente Quote (L-ca295c), der Rahmen gegen die zu weit
    gesprochene Zahl (L-352afa)."""
    zeilen = [b.zeile(was, rahmen)]
    for x in b.beispiele:
        zeilen.append("    | " + x.replace("\n", " "))
    text = "\n".join(zeilen)
    print(text, file=ziel or sys.stdout)
    return text


def antworten(wurzel: Path | None = None, dateien: int = 400,
              mindestens: int = 120) -> Iterable[str]:
    """Assistentenantworten aus den juengsten Transkripten.

    Der gemeinsame Korpus fuer alle Waechter ueber Antworttext -- damit drei
    Melder nicht drei verschiedene Vorstellungen davon haben, was eine
    Antwort ist."""
    import json
    w = wurzel or (Path.home() / ".claude" / "projects")
    try:
        pfade = sorted(w.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime,
                       reverse=True)[:dateien]
    except OSError:
        return
    for f in pfade:
        try:
            roh = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for zeile in roh.splitlines():
            if '"assistant"' not in zeile:
                continue
            try:
                z = json.loads(zeile)
            except ValueError:
                continue
            if z.get("type") != "assistant":
                continue
            c = (z.get("message") or {}).get("content")
            if isinstance(c, list):
                t = " ".join(b.get("text", "") for b in c
                             if isinstance(b, dict) and b.get("type") == "text")
            else:
                t = c if isinstance(c, str) else ""
            t = (t or "").strip()
            if len(t) >= mindestens:
                yield t


def _selftest() -> int:
    b = zaehle(range(10), lambda n: n % 3 == 0, str)
    assert b.nenner == 10 and b.treffer == 4, (b.nenner, b.treffer)
    assert b.zeile("teilbar") == "teilbar: 4 von 10 (40.0%)", b.zeile("teilbar")
    # DER BEZUGSRAHMEN steht im Satz, nicht in einer Fussnote (L-352afa).
    assert b.zeile("teilbar", "ueber 0..9") == "teilbar: 4 von 10 (40.0%), gemessen ueber 0..9"
    assert b.beispiele == ["0", "3", "6", "9"], b.beispiele

    # NENNER OHNE TREFFER -- die Zeile muss trotzdem beide Zahlen nennen.
    leer = zaehle(range(5), lambda n: False)
    assert leer.zeile("nichts") == "nichts: 0 von 5 (0.0%)"

    # LEERE MENGE darf nicht durch Null teilen.
    nichts = zaehle([], lambda x: True)
    assert nichts.quote == 0.0 and "0 von 0" in nichts.zeile("leer")

    # EIN WERFENDER PRUEFER zaehlt in den Nenner, nicht in die Treffer.
    def kaputt(n):
        if n == 2:
            raise ValueError("nicht beurteilbar")
        return True
    b2 = zaehle(range(4), kaputt)
    assert b2.nenner == 4 and b2.treffer == 3, (b2.nenner, b2.treffer)

    # Beispiele sind gedeckelt.
    b3 = zaehle(range(100), lambda n: True, str, hoechstens_beispiele=3)
    assert len(b3.beispiele) == 3

    print("rueckwirkung: Selbsttest gruen (6 Faelle: Bezugsrahmen im Satz, Quote mit Nenner, "
          "null Treffer nennt trotzdem beide Zahlen, leere Menge ohne "
          "Division, werfender Pruefer zaehlt in den Nenner, Beispiele "
          "gedeckelt)")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else 0)
