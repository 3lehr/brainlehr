#!/usr/bin/env python3
"""Klassifiziert jede Fundstelle aus absolute_pfade_rohfund.json in A/B/C und
schreibt runs/absolute_pfade_vorschlag.json. NUR LESEND auf die DB (fuer die
Kontrollzahlen); die Klassifikation selbst ist Handarbeit, hier nur codiert.

A -- rein technischer Pfad, wird relativ zum Verbund (Praefix entfernt).
B -- der Pfad selbst traegt die Aussage. NICHT anfassen.
C -- Pfad in ein fremdes Projekt (be_old, videoki, /Users/lehrmacbook). NICHT
     anfassen.

Reihenfolge im Rohfund (0-84) wie von absolute_pfade_suche.py erzeugt.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
ROH = WURZEL / "runs" / "absolute_pfade_rohfund.json"
AUS = WURZEL / "runs" / "absolute_pfade_vorschlag.json"

# Nur "/Volumes/daten" (den maschinenspezifischen Einhaengepunkt) streichen,
# "Begod2026" als Verbundname stehen lassen -- der wird im Fliesstext ohnehin
# schon oft bar verwendet ("Bootstrap von 'buckeberg'", "unter Begod2026").
# Ein komplettes Streichen des Praefixes liess bei leeren Resttexten
# doppelte Leerzeichen und kaputte Grammatik zurueck ("der Arbeitsbaum unter
#  (Quelle..." statt "unter Begod2026 (Quelle...") -- beim ersten Durchlauf
# gefunden und hier korrigiert.
PRAEFIX = re.compile(r"^/Volumes/daten/Begod2026")

# Index -> (Klasse, Begruendung fuer B/C; leer bei A)
# Begruendet je Zeile, wie im Auftrag verlangt ("Ausnahmeliste ohne
# Begruendung je Zeile ist keine").
KLASSEN: dict[int, tuple[str, str]] = {
    # b4e5dfe9
    0: ("A", ""),
    # 30e1e9ea -- Zeile 1 (Verzeichnisliste): rein deskriptiv -> A.
    1: ("A", ""),
    # 30e1e9ea -- Zeile 2: dokumentiert den @-Import-Schnipsel
    # `@/Volumes/daten/Begod2026/hub/CLAUDE.md`, den man in eine neue
    # App-CLAUDE.md kopiert. Der Import-Mechanismus braucht einen
    # funktionierenden Pfad (relativ waere `@../hub/CLAUDE.md`, nicht einfach
    # Praefix weg) -- ein simples Kuerzen macht die Kopiervorlage falsch.
    2: ("B", "Kopiervorlage fuer @-Import; Praefix-Streichen macht sie falsch, keine reine Umbenennung."),
    # ab4f443e -- wohlair jetzt unter Begod2026 -> A
    3: ("A", ""),
    # ab4f443e -- frueherer Ort unter be_old -> fremdes Projekt
    4: ("C", "be_old: fremdes/abgeschriebenes Repo ausserhalb Begod2026."),
    5: ("A", ""),
    6: ("A", ""),
    7: ("A", ""),
    8: ("C", "be_old: fremdes/abgeschriebenes Repo ausserhalb Begod2026."),
    # da662b05 -- FREIGEGEBEN (offen). Begod2026-Bezug rein strukturell -> A
    9: ("A", ""),
    # da662b05 -- be_old, FREIGEGEBEN. Bewusst nicht anfassen und melden.
    10: ("C", "be_old, FREIGEGEBEN (offen) -- Existenz/Sinn des Eintrags ist zu klaeren, nicht nur die Schreibweise."),
    11: ("A", ""),
    12: ("C", "be_old, FREIGEGEBEN (offen) -- Existenz/Sinn des Eintrags ist zu klaeren, nicht nur die Schreibweise."),
    13: ("A", ""),
    # 483acb56 -- videoki: fremdes Projekt
    14: ("C", "videoki: fremdes Projekt ausserhalb Begod2026."),
    15: ("A", ""),
    16: ("A", ""),
    17: ("A", ""),
    # 1f81a8eb -- die Lehre BESCHREIBT, wie ein Werkzeug einen Pfad AUFLOEST
    # (Bug: falsche/veraltete Skriptkopie ueber genau diese Aufloesung
    # gefunden). Der Pfad ist Teil des beschriebenen Mechanismus, nicht nur
    # ein Fundort -- im Zweifel B.
    18: ("B", "Beschreibt eine Pfadaufloesung als Teil des Bugs, nicht nur den Fundort."),
    19: ("B", "Beschreibt eine Pfadaufloesung als Teil des Bugs, nicht nur den Fundort."),
    # 0beacbfa -- Agentenregister. Explizit im Auftrag als Klasse-B-Beispiel
    # genannt: der absolute Pfad IST die Regel (nicht raten, erfragen; alter
    # /tmp-Ort existiert weiter und wird nicht mehr gelesen).
    20: ("B", "Agentenregister -- Ort ist bewusst absolut genannt (nicht raten, erfragen); alter /tmp-Ort besteht weiter. Explizites Beispiel aus dem Auftrag."),
    21: ("A", ""),
    # a13cd3f4 -- /Users/lehrmacbook: per Auftrag Klasse C.
    22: ("C", "/Users/lehrmacbook -- ausserhalb Begod2026, per Auftrag Klasse-C-Praefix."),
    23: ("C", "/Users/lehrmacbook -- ausserhalb Begod2026, per Auftrag Klasse-C-Praefix."),
    24: ("A", ""),
    25: ("A", ""),
    26: ("A", ""),
    27: ("A", ""),
}
# Die 21 Boilerplate-Knoten ("Verbund unter .../Begod2026 ist EIN Repository
# ... Arbeitsbaum ... Werkbank, nicht das Archiv") -- Zeilen 28..67, reine
# Strukturbeschreibung, Praefix restlos entbehrlich -> A.
for _i in range(28, 68):
    KLASSEN[_i] = ("A", "")
KLASSEN[68] = ("A", "")
# e5b68f3a -- Beleg-Pfad einer Agentendatei im Verbund, rein deskriptiv -> A.
KLASSEN[69] = ("A", "")

# --- Lessons ---
KLASSEN[70] = ("A", "")  # L-720a22
KLASSEN[71] = ("A", "")  # L-bce00d
# L-18bc8d -- pruefstelle zeigt auf ~/.claude/skills/... , ausserhalb
# Begod2026 -- /Users/lehrmacbook-Praefix -> C.
KLASSEN[72] = ("C", "/Users/lehrmacbook -- ausserhalb Begod2026, per Auftrag Klasse-C-Praefix (pruefstelle-Feld zeigt auf globalen Claude-Ort, kein Repo-Pfad).")
KLASSEN[73] = ("A", "")  # L-e3456a
KLASSEN[74] = ("A", "")  # L-86e92d
KLASSEN[75] = ("A", "")  # L-80fa5c
KLASSEN[76] = ("A", "")  # L-752ce6
# L-7a719d -- die Lehre ist WOERTLICH darueber, dass ein absoluter Pfad in
# einem Arbeitsbaum den Zweig-Schutz aushebelt. Praefix-Streichen entwertet
# die Aussage selbst.
KLASSEN[77] = ("B", "Lehre handelt explizit vom Effekt eines ABSOLUTEN Pfads im Arbeitsbaum; das ist der Fehler, nicht nur der Fundort.")
# L-76395d -- Agentenregister, wie 0beacbfa.
KLASSEN[78] = ("B", "Agentenregister -- Ort ist bewusst absolut genannt (nicht raten, erfragen); alter /tmp-Ort besteht weiter. Explizites Beispiel aus dem Auftrag.")
# L-8c2c2a -- die Lehre demonstriert die BEGOD_ROOT-Werte vorher/nachher als
# Beleg des Bugs (abgeleitete Wurzel aendert sich mit der Verschachtelung).
KLASSEN[79] = ("B", "Vorher/Nachher-Wert einer abgeleiteten Wurzelkonstante ist der Beleg des beschriebenen Bugs, kein beilaeufiger Fundort.")
# L-9f8816 -- zitiert woertlich den Auftragstext ("Repo: /Volumes/... "), der
# Fehler war GENAU, dass kein absoluter Pfad genannt wurde. Aendern des
# Zitats veraendert den Beleg.
KLASSEN[80] = ("B", "Woertliches Zitat eines Auftragstexts, dessen fehlende Eindeutigkeit der Kern der Lehre ist.")
KLASSEN[81] = ("A", "")  # L-02fb6a
# L-b3793c -- zwei Fundstellen IM SELBEN Feld, alphabetisch sortiert (Users
# vor Volumes): Index 82 ist der Desktop-Pfad (/Users/lehrmacbook) = C,
# Index 83 der Begod2026-Verweis = A. (Beim ersten Durchlauf vertauscht --
# hier korrigiert, siehe Kontrolle gegen die tatsaechlichen alter_wortlaut-
# Werte in absolute_pfade_vorschlag.json.)
KLASSEN[82] = ("C", "/Users/lehrmacbook -- ausserhalb Begod2026, per Auftrag Klasse-C-Praefix.")
KLASSEN[83] = ("A", "")
KLASSEN[84] = ("C", "/Users/lehrmacbook -- ausserhalb Begod2026, per Auftrag Klasse-C-Praefix.")


def relativieren(pfad: str) -> str:
    """A-Transform: nur den Einhaengepunkt /Volumes/daten streichen,
    "Begod2026" als lesbaren Verbundnamen behalten."""
    return PRAEFIX.sub("Begod2026", pfad)


def main() -> None:
    roh = json.loads(ROH.read_text(encoding="utf-8"))
    assert len(roh) == 85, f"Rohfund hat {len(roh)} Zeilen, erwartet 85 -- Skript neu abgleichen."

    vorschlag = []
    for i, e in enumerate(roh):
        klasse, begruendung = KLASSEN[i]
        eintrag = {
            "index": i,
            "tabelle": e["tabelle"],
            "id": e["id"],
            "feld": e["feld"],
            "freigabe": e["freigabe"],
            "klasse": klasse,
            "alter_wortlaut": e["pfad"],
            "kontext": e["kontext"],
        }
        if klasse == "A":
            eintrag["neuer_wortlaut"] = relativieren(e["pfad"])
            eintrag["begruendung"] = "rein technischer Pfad, Bedeutung bleibt erhalten"
        else:
            eintrag["neuer_wortlaut"] = None
            eintrag["begruendung"] = begruendung
        vorschlag.append(eintrag)

    a = [v for v in vorschlag if v["klasse"] == "A"]
    b = [v for v in vorschlag if v["klasse"] == "B"]
    c = [v for v in vorschlag if v["klasse"] == "C"]
    print(f"Fundstellen (Zeilen) gesamt: {len(vorschlag)}")
    print(f"Klasse A: {len(a)}  Klasse B: {len(b)}  Klasse C: {len(c)}")

    ids_a = {(v["tabelle"], v["id"]) for v in a}
    ids_b = {(v["tabelle"], v["id"]) for v in b}
    ids_c = {(v["tabelle"], v["id"]) for v in c}
    print(f"Eintraege (id) mit mind. einer A-Stelle: {len(ids_a)}")
    print(f"Eintraege (id) mit mind. einer B-Stelle: {len(ids_b)}")
    print(f"Eintraege (id) mit mind. einer C-Stelle: {len(ids_c)}")
    print(f"reine A-Eintraege (keine B/C-Stelle): {len(ids_a - ids_b - ids_c)}")

    freigegeben_c = [v for v in c if v["freigabe"] == "offen"]
    print(f"Klasse C, FREIGEGEBEN: {len(freigegeben_c)}")
    for v in freigegeben_c:
        print("  ", v["tabelle"], v["id"], v["feld"], "|", v["alter_wortlaut"])

    ausgabe = {
        "meta": {
            "erzeugt": "2026-08-15",
            "quelle": "kern.speicher.lesen() -- nur lesend, Muster: /Volumes/daten/Begod2026, "
                      "/Volumes/daten/be_old, /Volumes/daten/videoki, /Users/lehrmacbook",
            "abweichung_von_betreiberzahl": {
                "betreiber_gemessen": {"nodes": 41, "nodes_offen": 15, "lessons": 15, "lessons_offen": 1, "summe": 56},
                "hier_gemessen": {
                    "nodes": len({v['id'] for v in vorschlag if v['tabelle'] == 'knowledge_nodes'}),
                    "lessons": len({v['id'] for v in vorschlag if v['tabelle'] == 'lessons_learned'}),
                    "summe": len(ids_a | ids_b | ids_c),
                },
                "grund": (
                    "Betreiberzahl 41/15 stammt vermutlich aus Wortsuche (\"Begod2026\" als "
                    "Teilstring). Drei Treffer davon tragen KEINEN echten absoluten Pfad: "
                    "Knoten 02bb87a3 (Titel/Text nennen 'Begod2026' nur als Projektname, kein "
                    "Pfad), Knoten 13a425f3 und Lehre L-fd1221 (beide zitieren denselben "
                    "Code-Fund `re.search(r\"/Begod2026/([^/]+)\", cwd)` -- ein Regex-Literal "
                    "im Fliesstext, keine Datei- oder Verzeichnisangabe). Nach Abzug dieser "
                    "drei falschen Treffer bleiben 39 Knoten / 14 Lehren = 53 echte Fundstellen. "
                    "Diese Datei fuehrt 53, nicht 56 -- die Abweichung ist geprueft, kein "
                    "uebersehener Rest."
                ),
            },
            "reklassifizierung_a_nach_b": [
                {
                    "id": "knowledge_nodes/1f81a8eb",
                    "erster_blick": "A -- wirkt wie ein reiner Fundort (Projektpfad phoenix)",
                    "endgueltig": "B",
                    "warum": (
                        "Der Text beschreibt nicht nur EINEN Ort, sondern WIE ein Werkzeug "
                        "(begod_recommend_model) einen Pfad AUFLOEST und dabei eine veraltete "
                        "Skriptkopie findet -- der Pfad ist Teil des beschriebenen Fehlermechanismus, "
                        "nicht nur eine Adresse. Beim ersten Lesen als austauschbarer Fundort "
                        "eingestuft, bei genauerem Lesen zurueckgestuft."
                    ),
                },
                {
                    "id": "knowledge_nodes/30e1e9ea (Feld content, zweite Fundstelle)",
                    "erster_blick": "A -- gleiche Datei, erste Fundstelle (Verzeichnisliste) ist A",
                    "endgueltig": "B",
                    "warum": (
                        "Zweite Fundstelle ist ein woertlicher @-Import-Schnipsel "
                        "(`@/Volumes/daten/Begod2026/hub/CLAUDE.md`), der als Kopiervorlage fuer "
                        "neue App-CLAUDE.md dient. Praefix-Streichen ergaebe `@hub/CLAUDE.md` -- "
                        "syntaktisch etwas anderes als der dokumentierte, funktionierende Import. "
                        "Gleiche ID, gleiches Feld, unterschiedliche Fundstelle -- deshalb A und B "
                        "nebeneinander im selben Eintrag."
                    ),
                },
            ],
            "klasse_c_freigegeben_besonders_melden": [
                "knowledge_nodes/da662b05 (offen): zwei Fundstellen zeigen auf "
                "/Volumes/daten/be_old/... -- WohlAir/schimmel_guard_app, ein Repo ausserhalb "
                "Begod2026. Der Knoten selbst ist FREIGEGEBEN (offen). Nicht die Schreibweise "
                "ist hier die Frage, sondern ob eine Freigabe fuer einen Verweis auf ein "
                "fremdes/veraltetes Repo weiterhin sinnvoll ist.",
                "knowledge_nodes/a13cd3f4 (offen): zwei Fundstellen zeigen auf "
                "/Users/lehrmacbook/.codex/... (Codex-Konfiguration des Betreibers). FREIGEGEBEN.",
            ],
            "zaehlung": {
                "fundstellen_gesamt": len(vorschlag),
                "klasse_a": len(a),
                "klasse_b": len(b),
                "klasse_c": len(c),
                "eintraege_mit_a": len(ids_a),
                "eintraege_mit_b": len(ids_b),
                "eintraege_mit_c": len(ids_c),
                "reine_a_eintraege": len(ids_a - ids_b - ids_c),
                "klasse_c_freigegeben_fundstellen": len(freigegeben_c),
            },
        },
        "eintraege": vorschlag,
    }

    AUS.write_text(json.dumps(ausgabe, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"geschrieben: {AUS}")


if __name__ == "__main__":
    main()
