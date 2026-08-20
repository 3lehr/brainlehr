#!/usr/bin/env python3
# ausloeser: auf-abruf -- beantwortet vor jeder Aussage ueber den Produktstand, wie viele Katalogzeilen wirklich belegt sind
"""Haelt den Lastenkatalog gegen seine eigenen Produktgates: wie viele
Entscheidungen sind belegt, wie viele stehen auf NOT RUN, und nennt ein Gate
einen Pruefbefehl, den es gar nicht gibt?

ANLASS, und er kommt von aussen. Am 2026-08-18 antwortete die
Fahrtenbuch-Sitzung auf den Rundruf mit ihrem teuersten Vorfall des Tages: Sie
hatte "U1 bis U7 abgearbeitet" als fertige App gemeldet. Der Betreiber:
"was ist mit family sync usw, im lastenkatalog steht doch viel mehr?"
Gemessen danach: 6 von 40 belegt, 259 offene Katalogeintraege. Ihr Befund
woertlich: "ein Fortschrittsbericht ohne NENNER wird als Aussage ueber das
Ganze gelesen".

Derselbe Zustand liegt hier: der Root-Katalog fuehrt 55 BDW-Entscheidungen,
alle DECIDED, und die Produktgates stehen fast durchweg auf NOT RUN.
"Entschieden" und "belegt" sind zwei verschiedene Aussagen -- eine
Entscheidung kostet einen Satz, ein Gate kostet Arbeit.

DIE ZWEITE FRAGE IST DIE SCHAERFERE. Ein Gate, das einen Pruefbefehl nennt,
den es nicht gibt, ist schlimmer als ein ehrliches NOT RUN: es liest sich wie
ein Beleg. Deshalb prueft dieser Melder jede genannte Datei auf Existenz. Das
ist dieselbe Fehlerklasse wie ein Melder ohne Ausloeser -- gebaut, benannt,
wirkungslos.

HINWEISRECHT, KEIN VETO: immer exit 0. Die Zahl ist der Zweck, nicht die
Sperre.

Aufruf:
    python3 gatestand.py                 # Quote je Katalog
    python3 gatestand.py --bericht       # dazu jede offene Zeile
    python3 gatestand.py --selftest
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
KATALOGE = sorted((WURZEL / "docs").glob("REQUIREMENTS_*.md"))

# Eine Katalogzeile: | ID | ... | Produktgate | Quelle |
ZEILE = re.compile(r"^\|\s*(BDW-[A-Z]+-?\d+|INT-[A-Z]+-\d+)\s*\|")
# Ein Pruefbefehl im Gate-Text: Pfad mit Endung, in Backticks oder nackt.
DATEI = re.compile(r"`?((?:[\w./-]+/)?[\w.-]+\.(?:py|sh|swift|json|md))`?")


def _spalten(zeile: str) -> list[str]:
    return [t.strip() for t in zeile.strip().strip("|").split("|")]


def _gatespalte(zeilen_text: list[str]) -> int | None:
    """Index der Gate-Spalte, aus der KOPFZEILE gelesen statt geraten.

    BEFUND 2026-08-19: Der Melder nahm die vorletzte Spalte ("danach die
    Quelle"). Das stimmt fuer REQUIREMENTS_BRAINLEHR.md (Kopf: ... |
    Produktgate | Quelle |) und ist in REQUIREMENTS_INTERFACE_KOMPAT.md
    falsch -- dort ist "Gate" die LETZTE Spalte, und die vorletzte traegt den
    Anforderungstext. Gelesen wurde also jahrelang die falsche Spalte.

    Eine Position ist eine Annahme ueber ein fremdes Dokument; eine
    Ueberschrift ist eine Aussage DIESES Dokuments. Deshalb der Kopf."""
    for text in zeilen_text:
        if not text.startswith("|"):
            continue
        s = _spalten(text)
        for i, ueberschrift in enumerate(s):
            if ueberschrift.strip().lower() in ("gate", "produktgate"):
                return i
        if "ID" in [t.strip() for t in s]:
            return None  # Kopf gefunden, aber ohne Gate-Spalte
    return None


def _lattespalte(zeilen_text: list[str]) -> int | None:
    """Index der Latte-Spalte, aus der Kopfzeile (Norm b3249558, 2026-08-20).

    Die Latte ist das benannte, abrufbare Vergleichsobjekt -- woran gemessen
    wird, nicht ob gemessen wurde. Das ist eine ANDERE Frage als die des
    Produktgates: Am 2026-08-19 war BDW-E07 mit sieben gruenen Faellen belegt,
    waehrend der Bestand vollstaendig unverschluesselt war. Gemessen wurde das
    Modul, nicht der Gegenstand."""
    for text in zeilen_text:
        if not text.startswith("|"):
            continue
        s = [t.strip().lower() for t in _spalten(text)]
        if "latte" in s:
            return s.index("latte")
        if "id" in s:
            return None
    return None


def lies(pfad: Path) -> list[dict]:
    """Zeilen eines Katalogs mit Kennung, Gate-Text und genannten Dateien."""
    zeilen = []
    alle = pfad.read_text(encoding="utf-8").splitlines()
    spalte = _gatespalte(alle)
    latte_i = _lattespalte(alle)
    for text in alle:
        if not ZEILE.match(text):
            continue
        s = _spalten(text)
        if len(s) < 3:
            continue
        # Aus dem Kopf, sonst der alte Griff auf die vorletzte Spalte.
        gate = s[spalte] if spalte is not None and spalte < len(s) else s[-2]
        zeilen.append({
            "id": s[0],
            "gate": gate,
            "offen": gate.upper().startswith("NOT RUN") or not gate,
            # DEFERRED ist WEDER offen NOCH belegt. Ohne diese dritte
            # Kategorie haette die Vertagung von 22 Zeilen am 2026-08-18 die
            # Quote von 19/56 auf 41/56 gehoben, ohne dass irgendetwas
            # gemessen worden waere -- eine Schoenung durch Umetikettierung,
            # und genau die Sorte Zahl, gegen die dieser Melder gebaut ist.
            "vertagt": gate.upper().startswith("DEFERRED"),
            # VIERTE KATEGORIE, ergaenzt 2026-08-19. Bis dahin zaehlte
            # TEILWEISE voll als "belegt" -- gemessen sechs Zeilen (P04, P06,
            # E07, E13, E15, F05). Die Quote 33/56 las sich damit besser als
            # der Bestand: TEILWEISE heisst, dass ein Gate lief UND dass es
            # etwas gefunden hat. Genau die Sorte Zahl, gegen die dieser
            # Melder gebaut ist -- und er war blind dafuer, weil "hat ein Gate
            # gelaufen" und "ist belegt" hier stillschweigend gleichgesetzt
            # waren. Aufgefallen, als E18 von TEILWEISE auf PASS ging und die
            # Quote sich nicht bewegte.
            "teilweise": gate.upper().startswith("TEILWEISE"),
            # FUENFTE KATEGORIE, 2026-08-19, unmittelbar nach der vierten und
            # aus demselben Loch: BDW-E07 wurde von TEILWEISE auf FAIL
            # heruntergestuft -- und die Quote STIEG von 27 auf 28. Ein
            # durchgefallenes Kriterium galt als belegt. Das ist die
            # unangenehmste Auspraegung des Fehlers: Ehrlichkeit ueber einen
            # Fehlschlag verbesserte die Kennzahl.
            "durchgefallen": gate.upper().startswith("FAIL"),
            # UND DANN POSITIV STATT ALS REST (2026-08-19, dritte Runde
            # desselben Fehlers an einem Tag). `belegt` war "gesamt minus die
            # bekannten Ausnahmen" -- eine Restgroesse als Erfolgsmass zaehlt
            # JEDEN unbekannten Zustand zu ihren Gunsten. Dreimal ist genau
            # das passiert: DEFERRED, TEILWEISE, FAIL. Jetzt zaehlt nur, was
            # ausdruecklich PASS sagt; alles Uebrige faellt auf die
            # unguenstige Seite und wird als `unklar` sichtbar.
            #
            # Was das sofort aufdeckte: REQUIREMENTS_INTERFACE_KOMPAT.md
            # meldete 17/17 belegt. Diese Datei hat gar keine Gate-Spalte --
            # die vorletzte Spalte traegt dort den Anforderungstext. Der
            # Melder hat also einen Bestwert fuer eine Datei ausgewiesen, die
            # er ueberhaupt nicht messen kann.
            "belegt": gate.upper().startswith("PASS"),
            "dateien": [d for d in DATEI.findall(gate)],
            # Leer heisst: niemand hat entschieden. Kein Vorgabewert -- ein
            # stiller Vorgabewert vernichtet genau die Unterscheidung, fuer
            # die das Feld existiert (dieselbe Bauform wie norm_entscheidung).
            "latte": (s[latte_i].strip()
                      if latte_i is not None and latte_i < len(s) else ""),
        })
    return zeilen


def beurteile(zeilen: list[dict], wurzel: Path = WURZEL) -> dict:
    fehlend = []
    for z in zeilen:
        for d in z["dateien"]:
            if not (wurzel / d).exists() and not list(wurzel.glob(f"**/{Path(d).name}")):
                fehlend.append((z["id"], d))
    offen = [z["id"] for z in zeilen if z["offen"]]
    vertagt = [z["id"] for z in zeilen if z.get("vertagt")]
    teilweise = [z["id"] for z in zeilen if z.get("teilweise")]
    durchgefallen = [z["id"] for z in zeilen if z.get("durchgefallen")]
    # PASS OHNE LATTE ist kein Beleg (Norm b3249558): ein gruener Test sagt,
    # DASS gemessen wurde, nicht WORAN. Fehlt die Latte ganz, ist die Zeile
    # unentschieden -- sie faellt aus `belegt` heraus und wird eigens genannt.
    ohne_latte = [z["id"] for z in zeilen
                  if z.get("belegt") and not z.get("latte")]
    belegt = [z["id"] for z in zeilen
              if z.get("belegt") and z["id"] not in set(ohne_latte)]
    bekannt = (set(offen) | set(vertagt) | set(teilweise) | set(durchgefallen)
               | set(belegt) | set(ohne_latte))
    unklar = [z["id"] for z in zeilen if z["id"] not in bekannt]
    return {
        "gesamt": len(zeilen),
        "offen": len(offen),
        "vertagt": len(vertagt),
        "teilweise": len(teilweise),
        "durchgefallen": len(durchgefallen),
        "belegt": len(belegt),
        "unklar": len(unklar),
        "ohne_latte": len(ohne_latte),
        "ohne_latte_ids": ohne_latte,
        "offene_ids": offen,
        "vertagte_ids": vertagt,
        "teilweise_ids": teilweise,
        "durchgefallene_ids": durchgefallen,
        "unklare_ids": unklar,
        "phantom": fehlend,
    }


def _selftest() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        w = Path(tmp)
        (w / "docs").mkdir()
        (w / "echt.py").write_text("x")
        k = w / "docs" / "REQUIREMENTS_PROBE.md"
        k.write_text(
            "| ID | x | Latte | Produktgate | Quelle |\n"
            "|---|---|---|---|---|\n"
            "| BDW-X01 | y | n/a -- Fixture | NOT RUN | q |\n"
            "| BDW-X02 | y | n/a -- Fixture | PASS: `echt.py --selftest` gruen | q |\n"
            "| BDW-X03 | y | n/a -- Fixture | PASS: `gibtsnicht.py --selftest` | q |\n"
            "| BDW-X04 | y | n/a -- Fixture | DEFERRED: aktiviert mit dem ersten Piloten (`BDW-C03`) | q |\n"
            "| BDW-X05 | y | n/a -- Fixture | TEILWEISE: `echt.py` gruen, aber Index nicht erreicht | q |\n"
            "| BDW-X06 | y | n/a -- Fixture | FAIL: `echt.py` misst am echten Weg -- Klartext lesbar | q |\n"
            "| BDW-X08 | y |  | PASS: `echt.py` gruen | q |\n"
            "| BDW-X07 | y | n/a -- Fixture | Das Paket wird fail-closed abgewiesen, nicht geraten | q |\n",
            encoding="utf-8")
        z = lies(k)
        assert len(z) == 8, z
        e = beurteile(z, wurzel=w)
        # DIE DRITTE KATEGORIE, ergaenzt 2026-08-18: vertagt zaehlt WEDER als
        # offen NOCH als belegt. Ohne diese Zeile haette die Vertagung von 22
        # Katalogzeilen die Quote von 19/56 auf 41/56 gehoben, ohne dass
        # irgendetwas gemessen worden waere.
        assert e["gesamt"] == 8 and e["offen"] == 1 and e["belegt"] == 2 and e["vertagt"] == 1, e
        # PASS OHNE LATTE (Norm b3249558): X08 ist gruen und zaehlt trotzdem
        # nicht als Beleg -- der Test sagt, DASS gemessen wurde, nicht WORAN.
        # Rot gegen den Stand davor: `belegt` war 3 und `ohne_latte` gab es
        # nicht.
        assert e["ohne_latte"] == 1 and e["ohne_latte_ids"] == ["BDW-X08"], e
        # POSITIV STATT REST: X07 traegt keinen Status, sondern einen
        # Anforderungstext -- so sieht die INTERFACE-Datei in JEDER Zeile aus.
        # Rot gegen den Stand davor: `belegt` war 3, die Zeile zaehlte als
        # Beleg, und `unklar` gab es nicht.
        assert e["unklar"] == 1 and e["unklare_ids"] == ["BDW-X07"], e

        # KOPFZEILE STATT POSITION. Zweite Fixture in der Bauform der
        # INTERFACE-Datei: "Gate" ist die LETZTE Spalte, davor der
        # Anforderungstext. Rot gegen den Stand davor: dort las der Melder
        # s[-2] und bekam "Das Paket wird abgewiesen" statt "PASS: ...".
        k2 = w / "docs" / "REQUIREMENTS_ZWEITFORM.md"
        k2.write_text(
            "| ID | Anforderung | Latte | Gate |\n"
            "|---|---|---|---|\n"
            "| INT-ZZ-001 | Das Paket wird fail-closed abgewiesen | n/a -- Fixture "
            "| PASS: `echt.py` |\n",
            encoding="utf-8")
        z2 = lies(k2)
        assert z2[0]["gate"].startswith("PASS"), z2[0]["gate"]
        assert beurteile(z2, wurzel=w)["belegt"] == 1, beurteile(z2, wurzel=w)
        # DIE VIERTE KATEGORIE. Rot gegen den Stand vor 2026-08-19: dort war
        # `belegt` 3, weil TEILWEISE mitgezaehlt wurde, und `teilweise` gab es
        # nicht. Ohne diese Zeile blieben sechs halbfertige Katalogzeilen als
        # Beleg gezaehlt.
        assert e["teilweise"] == 1 and e["teilweise_ids"] == ["BDW-X05"], e
        # DIE FUENFTE. Rot gegen den Stand davor: `belegt` war 3, weil FAIL
        # mitzaehlte -- eine ehrliche Herabstufung verbesserte die Quote.
        assert e["durchgefallen"] == 1 and e["durchgefallene_ids"] == ["BDW-X06"], e
        assert e["offene_ids"] == ["BDW-X01"], e
        assert e["vertagte_ids"] == ["BDW-X04"], e
        # Der eigentliche Fund: ein Gate, das eine nicht existierende Datei nennt.
        assert e["phantom"] == [("BDW-X03", "gibtsnicht.py")], e
        # Gegenprobe: die existierende Datei wird NICHT gemeldet.
        assert all(p[0] != "BDW-X02" for p in e["phantom"]), e
    print("gatestand: Selbsttest gruen (Quote 2/8 belegt, 1 offen, 1 vertagt, "
          "1 teilweise, 1 durchgefallen, 1 ohne erkennbaren Status, "
          "1 PASS ohne Latte, "
          "Gate-Spalte aus dem Kopf statt aus der Position, "
          "ein Phantom-Gate gefunden, echtes Gate nicht gemeldet)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    bericht = "--bericht" in sys.argv
    for pfad in KATALOGE:
        zeilen = lies(pfad)
        if not zeilen:
            continue
        e = beurteile(zeilen)
        quote = f"{e['belegt']}/{e['gesamt']}"
        vertagt = f", {e['vertagt']} vertagt" if e.get("vertagt") else ""
        teilweise = f", {e['teilweise']} nur teilweise" if e.get("teilweise") else ""
        rot = f", {e['durchgefallen']} durchgefallen" if e.get("durchgefallen") else ""
        unklar = f", {e['unklar']} ohne erkennbaren Status" if e.get("unklar") else ""
        latte = f", {e['ohne_latte']} PASS ohne Latte" if e.get("ohne_latte") else ""
        print(f"{pfad.name}: {quote} belegt, {e['offen']} ohne Gate-Lauf"
              f"{vertagt}{teilweise}{rot}{unklar}{latte}")
        if bericht and e.get("ohne_latte_ids"):
            print("  PASS ohne Latte: " + ", ".join(e["ohne_latte_ids"]))
        if bericht and e.get("unklare_ids"):
            print("  ohne erkennbaren Status: " + ", ".join(e["unklare_ids"][:12])
                  + (" ..." if len(e["unklare_ids"]) > 12 else ""))
        if bericht and e.get("durchgefallene_ids"):
            print("  durchgefallen: " + ", ".join(e["durchgefallene_ids"]))
        if bericht and e.get("teilweise_ids"):
            print("  nur teilweise: " + ", ".join(e["teilweise_ids"]))
        for kennung, datei in e["phantom"]:
            print(f"  PHANTOM-GATE {kennung}: nennt {datei} -- existiert nicht")
        if bericht and e["offene_ids"]:
            print("  ohne Beleg: " + ", ".join(e["offene_ids"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
