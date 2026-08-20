"""Traegt die HANDBEURTEILUNG der 20 BF_CF-Faelle ein (Auftrag 2026-08-20)
und zaehlt sie ueber kern/rueckwirkung.zaehle()/bericht() aus (Norm 17b14a32
-- gemeinsame Zaehler-Bauform, nicht neu erfunden).

Grundlage: runs/roh_bf_cf_2026-08-20.json (von messungen/beurteilung_bf_cf.py
erzeugt -- tatsaechlich ausgelieferte Titel/Zusammenfassungen im Zustand B,
plus bester_kosinus aus der Vorgabedatei runs/kreuztabelle_bc_2026-08-20.json,
NUR gelesen, nicht neu berechnet).

Die Klassenzuordnung je Fall (URTEIL unten) ist von Hand getroffen, nicht
automatisch abgeleitet -- Auftrag ausdruecklich "Beurteilung von Hand, keine
Automatik". Fuer zwei Faelle wurde vor der Zuordnung der volle DB-Inhalt
(Titel+Zusammenfassung, nicht nur die Kennung) direkt aus der DB nachgelesen
(kalibrierbremse-Knoten: Zusammenfassung erwies sich als inhaltsleeres
Standardformular -- deshalb TEILWEISE statt BRAUCHBAR_ANDERS trotz passender
Metapher im Titel; L-b63633/​/testing/​Regel-15-Knoten: Volltext bestaetigt
den Treffer als BRAUCHBAR_ANDERS)."""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent.parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w), str(_w / "kern")]

import rueckwirkung  # noqa: E402

ROH = _w / "runs/roh_bf_cf_2026-08-20.json"
OUT = _w / "runs/beurteilung_bf_cf_2026-08-20.json"

# target_id -> (Klasse, Begruendungssatz mit konkreten Titeln)
URTEIL: dict[str, tuple[str, str]] = {
    "L-298823": ("TEILWEISE",
        "„Synergien finden: welche Datenpunkte sollten voneinander wissen“ beruehrt das Thema "
        "unverbundener Bausteine, beantwortet aber nicht die konkrete Frage, warum ein "
        "geschriebenes Feld nie ausgewertet wird -- die anderen beiden Treffer "
        "(„Keine Entwicklerinformation in der Oberflaeche“, „niemand-misst-automatisch-ob“) "
        "liegen daneben."),
    "L-f9f654": ("DANEBEN",
        "Keiner der drei Treffer („Testumgebung: selbstaendig handeln“, „Keine "
        "Entwicklerinformation in der Oberflaeche“, „Es funktioniert braucht einen Beleg“) "
        "spricht async-Fehlerbehandlung oder fire-and-forget-Aufrufe an."),
    "L-b4b443": ("TEILWEISE",
        "„DRINGEND: Normbezugs-Melder bestaetigt aufgehobene Normen als belegt“ ist dieselbe "
        "Fehlerklasse -- ein veralteter Zustand wird faelschlich als gueltig/aktuell gemeldet --, "
        "nur in einer anderen Domaene (Rechtsnorm statt Hardwarestatus), keine Antwort auf die "
        "konkrete Stale-Status-Frage."),
    "L-44a838": ("DANEBEN",
        "„Wer Preise selbst macht, ist datenbankrechtlich schwach geschuetzt“ (§87a/§87b UrhG) "
        "und die beiden anderen Treffer beruehren weder LLM-Output noch ungefilterte "
        "Schreibpfade fuer sensible Daten."),
    "L-cdac52": ("TEILWEISE",
        "„TripLifecycleCoordinator: warum der Fahrt-Lebenszyklus einen Owner braucht“ behandelt "
        "dieselbe App (fahrtenbuch) und dieselbe Fehlerklasse Timing/Reihenfolge, trifft aber "
        "nicht den konkreten Navigator.of(context)-Fall auf ambientem Widget-Context."),
    "L-b91ed6": ("BRAUCHBAR_ANDERS",
        "L-b63633 („Die Einstufung 'vorbestehend rot' verdeckte, dass ein Produktivskript gar "
        "nicht mehr lauffaehig war“) beantwortet exakt dieselbe Lehre wie das Ziel -- rote Tests "
        "nicht pauschal als Umgebungszustand abtun, sondern die Fehlerausgabe lesen -- nur unter "
        "anderer Lehren-ID."),
    "L-bbd7fb": ("TEILWEISE",
        "L-528f0c („Ein Waechter prueft ein Feld, das den Sachverhalt gar nicht traegt“) trifft "
        "den Kern -- falsche Sicherheit aus einem Signal, das die Wirklichkeit nicht abbildet --, "
        "aber nicht den konkreten Fall fehlender Sensoren mit Rueckfall auf Standardwerte."),
    "L-503687": ("TEILWEISE",
        "L-528f0c trifft erneut den Kern (Pruefung nach Oberflaechenform statt Funktion "
        "unterscheidet nicht Organisations- von Datenverbindung), aber „wiring_check.py“ und "
        "„Warum eine Stichprobe keine Diagnose ist“ beantworten die mycel.py-Rollen-Heuristik "
        "nicht direkt."),
    "L-8c633e": ("DANEBEN",
        "„Fuenf Hausverwaltungen fuer den Buckeberg“, „Keine Entwicklerinformation in der "
        "Oberflaeche“ und die DRINGEND-openlehr-Notiz zu Belegen behandeln weder Bugfix-"
        "Vollstaendigkeit noch uebersehene Zwillingsbildschirme."),
    "L-606b63": ("TEILWEISE",
        "„Warum autoConnect bei BLE-Verbindungen abgelehnt wurde“ (ADR F-026) liegt in derselben "
        "BLE-Verbindungs-Domaene des fahrtenbuchs, beantwortet aber die Reentrancy-/Generation-"
        "Token-Frage nicht, sondern einen anderen BLE-Fehler (Berechtigungs-Vorlauf)."),
    "L-476602": ("DANEBEN",
        "Keiner der Treffer („Kontakt wird per KI vorgeschlagen“, „Knoepfe, die die KI technisch "
        "nicht klicken kann“, „Simulator und Signalstaerke“) spricht MCP tools/list-Profilierung "
        "oder Startlisten-Verkleinerung an."),
    "L-476602-DUP": ("SKIP", ""),  # Platzhalter entfernt unten
    "/methodik/arbeitsweise/10-verhaeltnismaessigkeit-ist-teil-der-antwort": ("TEILWEISE",
        "Der Knoten „Kalibrierbremse: verdrahten oder ausbauen“ klingt durch Titel und "
        "Wortfeld (verdrahten) nach derselben Jetzt-oder-spaeter-Frage, doch sein "
        "Zusammenfassungsfeld ist ein inhaltsleeres Formular („kurzer Plan, weil eine "
        "Entscheidung mit echten Alternativen ansteht“, im Volltext nachgelesen) -- er hilft "
        "der Anfrage nicht wirklich, obwohl das Thema angrenzt."),
    "/lessons/phase2-summary": ("TEILWEISE",
        "L-6c6661 („Eine Umgebungsvariable zum Umlenken des Datenbankpfads existiert, wird aber "
        "nur von einem Teil der Skripte geachtet“) beruehrt das Thema uneinheitlich befolgter "
        "Vorgaben, beantwortet aber nicht die Frage nach Werkzeug-Restrukturierung fuer "
        "verlaessliche Skripterzeugung."),
    "/testing/pytest": ("BRAUCHBAR_ANDERS",
        "Der ausgelieferte Elternknoten „/testing“ („Testen als Fachgebiet: Strategien, pytest "
        "und TDD-Muster ... Kennzahlen zur Testabdeckung (Coverage) sowie Entwicklungsmuster "
        "nach TDD“) deckt Fixtures/Szenarien/Coverage inhaltlich genauso ab wie das Zielobjekt "
        "/testing/pytest selbst."),
    "/brainlehr/inference-control-was-andere-faecher": ("TEILWEISE",
        "„Cafe Enigma Rotation 1: P1-Mechanismen und P2-Grenzen“ behandelt verwandte Schutz-/"
        "Isolationsmechanismen, aber nicht speziell das Verraten-durch-Abwesenheit-Problem, "
        "das die Anfrage beschreibt (plausible Antwort statt leerer Rueckgabe)."),
    "/openlehr/steuer/ui": ("TEILWEISE",
        "L-0dec26 („Backend-Validierung erzwingt Pflichtfelder, fuer die es kein UI-Feld gibt ... "
        "OpenLehr steuer: Rechnungs-Formular“) liegt im selben Teilsystem (OpenLehr-Steuer-UI), "
        "beantwortet aber nicht die Frage nach der Anzahl der Untermodule."),
    "/ops/buckeberg-anbieterabend-2026-08-05": ("TEILWEISE",
        "L-14d14c („Eine Uebergabedatei ueberlebte einen Richtungswechsel des Auftrags und "
        "beschrieb danach zuversichtlich den aufgegebenen Strang“) beruehrt die Frage, ob ein "
        "alter Text noch gueltig ist, beantwortet aber nicht, warum das unordentliche Protokoll "
        "bewusst als Entstehungsbeleg erhalten bleibt."),
    "/methodik/direktiven-hub-claude-md/modell-kaskade-v3-opus-hauptfaden": ("BRAUCHBAR_ANDERS",
        "„Warum unabhaengige Pruefung ein frisches Fenster braucht“ beantwortet exakt die "
        "gestellte Frage (wann ein separates Kontrollfenster fuer eine unabhaengige "
        "Zweitmeinung sinnvoll ist), nur unter einem anderen Knotennamen als das Ziel."),
    "/ops/verwalterwahl-weg-im-buckeberg-zum-2027/widerspruch-2-brennertausch-haus-22-vom": ("TEILWEISE",
        "„Den Betreiber korrigieren“ (Widerspruch ist Bringschuld) und L-349083 (Buckeberg-"
        "Modellfazit widerspricht dem Rechenkern bei der Anlagenzahl) liegen beide auf dem "
        "Widerspruchs-Thema im selben Buckeberg-Kontext, treffen aber nicht den konkreten "
        "Brennertausch-Haus-22-Fall."),
    "/methodik/adr-bestand-hub-docs-adr/adr-006-token-kompression-fuer-multi": ("DANEBEN",
        "„Warum Disziplin verrottet und Erzeugung nicht“ und die EILMELDUNG zu "
        "Rueckwirkungs-Meldern behandeln weder Token-Budget noch Kompression von Anweisungen "
        "fuer Multi-Agent-Verlaesslichkeit."),
}
del URTEIL["L-476602-DUP"]


def main() -> None:
    rows = json.loads(ROH.read_text(encoding="utf-8"))
    assert len(rows) == 20, len(rows)
    assert set(r["target_id"] for r in rows) == set(URTEIL), (
        set(r["target_id"] for r in rows) ^ set(URTEIL))

    faelle_out = []
    for r in rows:
        klasse, begruendung = URTEIL[r["target_id"]]
        top3 = ([f"{n['title']} ({n['path']})" for n in r["ausgeliefert_nodes"]]
                if r["target_kind"] == "node" else
                [f"{l['id']}: {(l['description'] or '')[:80]}" for l in r["ausgeliefert_lessons"]])
        # Immer beide Kanaele mit anzeigen, wenn beide etwas lieferten -- die
        # Klassifizierung oben beruecksichtigt beide, die Kurzliste zeigt drei
        # Eintraege aus dem fuer diese Zielart gefuehrten Kanal (Auftrag:
        # "die drei besten tatsaechlich ausgelieferten Titel").
        faelle_out.append({
            "target_id": r["target_id"],
            "task_gekuerzt": r["task"][:200],
            "target_label": r["target_label"],
            "top3_ausgeliefert": top3[:3],
            "klasse": klasse,
            "begruendung": begruendung,
            "bester_kosinus": r["bester_kosinus"],
        })

    klassen = ("BRAUCHBAR_ANDERS", "TEILWEISE", "DANEBEN", "ZIEL_STRITTIG")
    zaehlung = {}
    for k in klassen:
        b = rueckwirkung.zaehle(
            faelle_out, lambda f, k=k: f["klasse"] == k,
            beschreibe=lambda f: f"{f['target_id']}: {f['begruendung'][:100]}")
        zaehlung[k] = {"treffer": b.treffer, "nenner": 20, "beispiele": b.beispiele}
        rueckwirkung.bericht(
            f"Klasse {k}", b,
            rahmen="ueber die 20 BF_CF-Faelle aus schritt2_dritte_gruppe_bf_cf "
                   "(runs/kreuztabelle_bc_2026-08-20.json)")

    summe = sum(zaehlung[k]["treffer"] for k in klassen)
    assert summe == 20, summe

    verteilung_je_klasse = {}
    for k in klassen:
        werte = [f["bester_kosinus"] for f in faelle_out
                 if f["klasse"] == k and f["bester_kosinus"] is not None]
        if werte:
            verteilung_je_klasse[k] = {
                "n": len(werte), "min": round(min(werte), 4), "max": round(max(werte), 4),
                "median": round(statistics.median(werte), 4),
                "mittel": round(statistics.mean(werte), 4),
            }
        else:
            verteilung_je_klasse[k] = {"n": 0}

    ergebnis = {
        "grundlage": {
            "quelle": "runs/kreuztabelle_bc_2026-08-20.json::schritt2_dritte_gruppe_bf_cf "
                      "(NUR gelesen, nicht neu berechnet)",
            "rohmaterial": "runs/roh_bf_cf_2026-08-20.json (run_case() im Zustand "
                           "B_2Kanal_an_Pflicht_aus, tatsaechlich ausgelieferte Titel/"
                           "Zusammenfassungen)",
            "nenner": 20,
        },
        "faelle": faelle_out,
        "auszaehlung": zaehlung,
        "verteilung_bester_kosinus_je_klasse": verteilung_je_klasse,
        "abnahme_pruefung": {"summe_vier_klassen_ist_20": summe == 20},
    }
    OUT.write_text(json.dumps(ergebnis, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\ngeschrieben: {OUT}")
    print(json.dumps(verteilung_je_klasse, indent=2, ensure_ascii=False))


def demo() -> None:
    """Ponytail-Selbsttest: die Handzuordnung deckt alle 20 Rohdaten-Faelle
    ab, die vier Klassen sind gueltig, keine Klasse fehlt in URTEIL."""
    rows = json.loads(ROH.read_text(encoding="utf-8"))
    assert len(rows) == 20
    assert set(r["target_id"] for r in rows) == set(URTEIL)
    gueltig = {"BRAUCHBAR_ANDERS", "TEILWEISE", "DANEBEN", "ZIEL_STRITTIG"}
    for k, _ in URTEIL.values():
        assert k in gueltig, k
    print("demo ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        demo()
    else:
        main()
