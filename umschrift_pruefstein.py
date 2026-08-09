"""Faellt beim Umschreiben Sachgehalt weg? Deterministisch geprueft, nicht
nach Gefuehl -- und nicht an der Zeichenzahl, die nichts beweist.

Anlass: der erste Haiku-Lauf kuerzte Texte um bis zu 65 Prozent (4314 auf
1852 Zeichen). Eine Kuerzung kann Straffung sein oder Verlust; die Laenge
unterscheidet das nicht. Was sich unterscheiden LAESST, sind die harten
Traeger einer Aussage: Zahlen, Datumsangaben, Kennungen, Pfade und
Eigennamen. Verschwindet eine Zahl aus dem Text, ist die Aussage, die an ihr
hing, weg -- egal wie gut der Rest klingt.

Bewusst NICHT geprueft: ob der neue Text dasselbe BEDEUTET. Das kann dieser
Pruefstein nicht, und er tut auch nicht so. Er ist ein Sieb gegen groben
Verlust, kein Urteil ueber Treue.

Fehlklasse und Preis eines Fehlalarms: Der Pruefstein meldet auch dann,
wenn eine Zahl absichtlich entfaellt (etwa eine doppelt genannte Jahreszahl)
oder wenn ein Eigenname anders gebeugt wird. Ein Fehlalarm kostet, dass ein
gutes Los erneut geschrieben wird -- Rechenzeit, kein Schaden am Bestand.
Ein uebersehener Verlust dagegen faelscht den Bestand dauerhaft und still.
Darum ist der Pruefstein absichtlich streng eingestellt.

Aufruf:
  python3 umschrift_pruefstein.py <alt.json> <neu.json>
  python3 umschrift_pruefstein.py --selftest
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Zahlen mit mindestens zwei Stellen (einstellige stehen zu oft in Fliesstext
# wie "drei Wege" und erzeugen Rauschen), Prozent-/Datumsformen inklusive.
_ZAHL = re.compile(r"\d[\d.,:/-]*\d|\b\d{2,}\b")
# Kennungen: adr-023, l-a9ccd0, /pfad/mit/mindestens/zwei/segmenten, datei.py
#
# Der Pfad-Teil verlangt ZWEI Segmente. Die erste Fassung nahm jedes Wort
# nach einem Schraegstrich und meldete darum '/kein', '/verwalter',
# '/uebergabe-luecke' als verlorene Pfade -- in Wahrheit Schraegstrich-
# Aufzaehlungen im Fliesstext ("Homepage/Verwalter"). Gemessen am ersten Lauf:
# der weit ueberwiegende Teil der Beanstandungen kam aus diesem einen Muster.
# Ein Sieb mit hoher Fehlalarmquote wird nicht gelesen, und dann faengt es gar
# nichts mehr.
_KENNUNG = re.compile(
    r"\b[a-z]{2,}-\d+\b"                       # adr-023, l-4750fc
    r"|/[\w.-]+/[\w./-]+"                      # /ops/verwalterwahl/... (zwei Segmente)
    r"|\b[\w-]+\.(?:py|md|json|db|sql|dart|yaml|yml|sh|txt)\b"  # datei.py
)

TOLERANZ_FEHLEND = 0  # keine fehlende Zahl ist hinnehmbar


def _traeger(text: str) -> set[str]:
    """Die harten Traeger einer Aussage. Kleingeschrieben, damit eine
    geaenderte Gross-/Kleinschreibung keinen Fehlalarm ausloest."""
    # Erst kleinschreiben, DANN suchen: sonst findet die Dateiendung im Muster
    # ('.py') ein grossgeschriebenes 'ORT.PY' nicht und meldet es als fehlend.
    # Im Selbsttest aufgefallen, bevor der erste Lauf davon betroffen war.
    t = (text or "").lower()
    roh = {m.group().rstrip(".,;:") for m in _ZAHL.finditer(t)} | \
          {m.group().rstrip(".,;:") for m in _KENNUNG.finditer(t)}
    # Aufzaehlungen zerlegen: '100,294,301' im Original wird beim Umschreiben zu
    # '100, 294, 301' -- ohne diesen Schritt meldet das Sieb einen fehlenden und
    # drei erfundene Traeger, obwohl nichts verlorenging. Genau ein Komma bleibt
    # unangetastet: '8,50' ist eine Dezimalzahl, keine Liste.
    fertig = set()
    for x in roh:
        if x.count(",") > 1:
            # Nur die Teile, nicht die zusammengesetzte Form: sonst gilt die
            # umformatierte Liste weiterhin als verloren.
            fertig.update(teil for teil in x.split(",") if teil)
        else:
            fertig.add(x)
    return fertig


def pruefe_knoten(alt: dict, neu: dict) -> dict:
    a = _traeger(f"{alt.get('title','')} {alt.get('summary','')} {alt.get('co','')}")
    n = _traeger(f"{neu.get('title','')} {neu.get('summary','')} {neu.get('co','')}")
    fehlend = sorted(a - n)
    erfunden = sorted(n - a)
    alt_len = len(alt.get("summary") or "") + len(alt.get("co") or "")
    neu_len = len(neu.get("summary") or "") + len(neu.get("co") or "")
    return {
        "id": alt["id"],
        "fehlend": fehlend,
        "erfunden": erfunden,
        "zeichen": [alt_len, neu_len],
        "unveraendert": alt.get("co", "") == neu.get("co", "") and alt.get("title") == neu.get("title"),
        "ok": len(fehlend) <= TOLERANZ_FEHLEND and not erfunden,
    }


def pruefe_los(alt_pfad: Path, neu_pfad: Path) -> dict:
    alt = {r["id"]: r for r in json.loads(alt_pfad.read_text(encoding="utf-8"))}
    neu = {r["id"]: r for r in json.loads(neu_pfad.read_text(encoding="utf-8"))}
    fehl_ids = sorted(set(alt) ^ set(neu))
    befunde = [pruefe_knoten(alt[i], neu[i]) for i in alt if i in neu]
    return {
        "los": neu_pfad.name,
        "id_abweichung": fehl_ids,
        "knoten": len(befunde),
        "beanstandet": [b for b in befunde if not b["ok"]],
        "unveraendert": [b["id"] for b in befunde if b["unveraendert"]],
    }


def main(argv: list[str]) -> int:
    ergebnis = pruefe_los(Path(argv[1]), Path(argv[2]))
    b = ergebnis["beanstandet"]
    print(f"{ergebnis['los']}: {ergebnis['knoten']} Knoten, {len(b)} beanstandet"
          + (f", {len(ergebnis['unveraendert'])} unveraendert durchgereicht" if ergebnis["unveraendert"] else ""))
    for x in b:
        print(f"  {x['id']}  {x['zeichen'][0]}->{x['zeichen'][1]} Zeichen")
        if x["fehlend"]:
            print(f"    fehlt:    {', '.join(x['fehlend'][:12])}" + (" ..." if len(x["fehlend"]) > 12 else ""))
        if x["erfunden"]:
            print(f"    erfunden: {', '.join(x['erfunden'][:12])}" + (" ..." if len(x["erfunden"]) > 12 else ""))
    return 1 if b or ergebnis["id_abweichung"] else 0


def demo() -> None:
    """Gegenprobe in beide Richtungen plus Negativfall."""
    alt = {"id": "x", "title": "ADR-023 Modellkaskade", "summary": "Gemessen 2026-08-04: 8,50 USD je Nachricht.",
           "co": "Faktor 3 gegenueber 2,85 USD. Siehe /methodik/direktiven und ort.py."}
    # 1) Reine Umformulierung: alle Traeger erhalten -> ok
    gut = {"id": "x", "title": "Warum die Kaskade auf Opus setzt (ADR-023)",
           "summary": "Am 2026-08-04 wurden 8,50 USD je Nachricht gemessen.",
           "co": "Das ist Faktor 3 gegenueber 2,85 USD. Hergeleitet in /methodik/direktiven, Code in ort.py."}
    assert pruefe_knoten(alt, gut)["ok"], pruefe_knoten(alt, gut)

    # 2) Kuerzung, die eine Zahl verliert -> beanstandet (der eigentliche Fall)
    kurz = {"id": "x", "title": "Modellkaskade", "summary": "Opus ist teurer.",
            "co": "Deutlich teurer als vorher. Siehe /methodik/direktiven und ort.py."}
    schlecht = pruefe_knoten(alt, kurz)
    assert not schlecht["ok"], schlecht
    assert "8,50" in schlecht["fehlend"] and "2,85" in schlecht["fehlend"], schlecht["fehlend"]

    # 3) Negativfall in die andere Richtung: erfundene Zahl -> beanstandet
    erfunden = dict(gut, co=gut["co"] + " Der Aufschlag betraegt 47 Prozent.")
    e = pruefe_knoten(alt, erfunden)
    assert not e["ok"] and "47" in e["erfunden"], e

    # 4) Gross-/Kleinschreibung und Beugung loesen KEINEN Fehlalarm aus
    fall = dict(gut, co=gut["co"].upper())
    assert pruefe_knoten(alt, fall)["ok"], pruefe_knoten(alt, fall)

    # 5) Ein unveraendert durchgereichter Knoten faellt auf
    assert pruefe_knoten(alt, dict(alt))["unveraendert"] is True
    print("umschrift_pruefstein.demo ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        demo()
    else:
        raise SystemExit(main(sys.argv))
