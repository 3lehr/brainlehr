"""Messkorpus mit BEKANNTER Wahrheit fuer den passiven Abruf (Auftrag
2026-08-07, Abrufpruefstand). Gegenstueck zu wissensnutzen_blind.py: dort
laeuft der Abruf gegen die echte brainlehr.db, und "nichts gefunden" kann
ER-HAT-VERSAGT oder ES-GAB-NICHTS heissen. Hier ist beides trennbar, weil
je Aufgabe im Voraus feststeht, ob es eine richtige Antwort gibt und welche.

AUFBAU, und warum er so und nicht kuerzer ist
  Acht THEMENCLUSTER zu je vier Eintraegen. Ein Cluster teilt sein Alltags-
  vokabular ("Mahnung", "Zaehlerstand", "Rechnung") ueber alle vier Eintraege
  -- damit liegt dieses Vokabular ueber der Seltenheitsschwelle (RARE_MAX_DF
  aus pruefkorpus.py) und darf in einer Aufgabe vorkommen, ohne dass die
  Aufgabe zirkulaer wird. Ein Cluster mit nur einem Eintrag haette das
  Gegenteil erzwungen: jedes brauchbare Wort waere selten und damit verboten,
  die Aufgabe muesste am Thema vorbeireden und der Stichwort-Kanal (MIN_HITS
  gattert auf Substring-Treffer in path+title+summary) haette gar keine
  Chance -- gemessen worden waere dann der Korpus, nicht der Abruf.

  Je Cluster ZWEI Aufgaben aus demselben Wortfeld:
    loesbar        genau EIN Eintrag beantwortet sie (ziel gesetzt)
    verfuehrerisch KEIN Eintrag beantwortet sie, aber die drei bis vier
                   Cluster-Eintraege sehen danach aus (falle = ihre Kennungen)
  Dazu acht UNLOESBARE Aufgaben voellig ausserhalb des Szenarios (Form und
  Absicht wie pruefkorpus._NEGATIVE_TOPICS): richtig ist hier Schweigen.

ANTI-ZIRKULARITAET: derselbe Weg wie pruefkorpus.py (dessen tokenize/
  rare_terms/is_circular importiert, nicht nachgebaut), IDF aber ueber genau
  diesen Korpus statt ueber die echte DB -- Seltenheit ist eine Eigenschaft
  des Bestands, gegen den gemessen wird.

  EINE ABWEICHUNG, gemessen und hier begruendet: die BINDENDE Schwelle ist
  RARE_MAX_DF_KORPUS = 1, nicht pruefkorpus.RARE_MAX_DF = 3. Grund ist die
  Bestandsgroesse, nicht Bequemlichkeit. pruefkorpus setzt 3 bei rund 880
  Dokumenten (0,34 % des Bestands); dieselben 3 sind hier bei 98 Dokumenten
  3 % und beanstanden dadurch reine Themenwoerter -- gemessen beanstandete
  df<=3 unter anderem "euro", "mahnung", "monat", "papier", "darf". Ein
  Aufgabentext, der das Thema nicht nennen darf, misst nichts mehr.
  Uebertragbar ist nicht die Zahl, sondern die EIGENSCHAFT, die sie bei 880
  Dokumenten hatte: ein Begriff, der genau diesen einen Eintrag heraushebt.
  Bei 98 Dokumenten ist das df == 1. Die Kollisionen bei df<=2 und df<=3
  werden trotzdem mitgeschrieben (Feld "nachrichtlich"), damit die
  Entscheidung sichtbar bleibt statt in einer Konstanten zu verschwinden.
  pruefe_zirkularitaet() ist die Abnahme; sie laeuft im Selbsttest und im
  Pruefstandslauf, nicht nur einmal von Hand.

KOEDER nach ADR-029, woertlich dort: "Als Koeder dagegen sinnvoll: eine
  eindeutige Scheinperson, die nirgends sonst existiert -- taucht sie je auf,
  ist ein Abfluss bewiesen und der Kanal bekannt. Das schuetzt nicht, es
  misst." KOEDER_NAME steht in genau EINEM Eintrag der Abteilung 'personal'.
  Der NEGATIVFALL (er muss auch stumm bleiben koennen) steht NICHT in
  ADR-029 -- geprueft, der Koeder-Absatz kennt ihn nicht. Er ist Vorgabe des
  Auftrags 2026-08-07 und wird hier als eigene Messgroesse gefuehrt, nicht
  als ADR-Zitat: jede Aufgabe AUSSERHALB der Abteilung 'personal' darf den
  Namen nie in den Treffern sehen.

ABWEICHUNG VOM AUFTRAG, gemessen statt uebernommen: der Auftrag sprach von
  "mehreren Abteilungen wie im urspruenglichen Aufbau" und einer am
  2026-08-07 ergaenzten fuenften Rolle. Geprueft (stadtwerke_material.py
  Zeile 2, runs/stadtwerke-gemma-e4b.json, git log der letzten 30 Commits):
  der urspruengliche Aufbau kennt GENAU EINE Abteilung ("Szenario: kommunaler
  Versorger, Abteilung Verbrauchsabrechnung") und je Lauf EINE session-Kennung
  -- getrennte Sitzungen je Rolle gab es nie, die fuenfte Rolle existiert im
  Bestand nicht. Die fuenf Abteilungen hier sind also NEU angelegt, nicht
  fortgeschrieben; 'openlehr-privat' bildet die im Auftrag beschriebene
  Nebentaetigkeit ab, ohne sich auf einen Vorgaenger zu berufen, den es
  nicht gibt.

Fuellmaterial (Rauschen im selben Wortfeld, absichtlich nie eine richtige
Antwort) liegt in stadtwerke_fuellmaterial.py.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import sys
from pathlib import Path

SCHREIBPRUEFSTAND = Path(__file__).resolve().parent
SHARED_KNOWLEDGE = SCHREIBPRUEFSTAND.parent
sys.path.insert(0, str(SHARED_KNOWLEDGE))
sys.path.insert(0, str(SHARED_KNOWLEDGE / "kern"))

import pruefkorpus as pk  # noqa: E402  -- tokenize/rare_terms/is_circular wiederverwendet

# Bindende Zirkularitaetsschwelle fuer DIESEN Korpus, Herleitung siehe
# Moduldoc. 1 = "der Begriff kommt in genau einem Dokument vor, naemlich im
# Ziel" -- er wuerde das Ziel allein identifizieren.
RARE_MAX_DF_KORPUS = 1
NACHRICHTLICHE_SCHWELLEN = (2, pk.RARE_MAX_DF)

# Eindeutige Scheinperson (ADR-029). Kommt in genau einem Korpus-Eintrag vor
# und in keiner einzigen Aufgabe -- sonst wuerde die Aufgabe den Abfluss
# selbst herbeifuehren, den sie messen soll.
KOEDER_NAME = "Ortrun Fehrenkamp-Zwiesel"
KOEDER_ABTEILUNG = "personal"

ABTEILUNGEN = [
    "verbrauchsabrechnung",
    "netzbetrieb",
    "kundenservice",
    "personal",
    "openlehr-privat",
]


def _n(abteilung: str, slug: str, title: str, summary: str, content: str = "") -> dict:
    return {"kind": "node", "abteilung": abteilung, "slug": slug,
            "title": title, "summary": summary, "content": content}


def _l(abteilung: str, lid: str, typ: str, severity: str,
       description: str, root_cause: str, prevention: str) -> dict:
    return {"kind": "lesson", "abteilung": abteilung, "id": lid, "typ": typ,
            "severity": severity, "description": description,
            "root_cause": root_cause, "prevention": prevention}


# --- Acht Themencluster, je vier Eintraege --------------------------------
# Der Zieleintrag steht jeweils zuerst; die uebrigen drei teilen sein
# Wortfeld, beantworten aber eine andere Frage (und sind darum genau die
# Fallen der verfuehrerischen Aufgabe desselben Clusters).

CLUSTER: dict[str, list[dict]] = {

    # C1 -----------------------------------------------------------------
    "mahnwesen": [
        _n("verbrauchsabrechnung", "mahnstaffel-drei-stufen",
           "Mahnstaffel drei Stufen ab September",
           "Die Mahnung der ersten Stufe bleibt kostenfrei, die Mahnung der zweiten Stufe kostet 8 Euro, "
           "die Mahnung der dritten Stufe kostet 15 Euro. Gilt fuer alle Vorgaenge ab 15.09.2026.",
           "Die dritte Stufe wird zusammen mit der Ankuendigung der Versorgungsunterbrechung versandt. "
           "Die alte zweistufige Ordnung von 2019 kannte nur eine Stufe vor dieser Ankuendigung und "
           "ist damit abgeloest. Betraege sind Bruttobetraege und werden auf der Folgerechnung ausgewiesen."),
        _n("verbrauchsabrechnung", "mahnung-fristen-tage",
           "Fristen zwischen den Mahnstufen",
           "Zwischen zwei Mahnungen liegen mindestens 14 Kalendertage; das gilt auch fuer die dritte Stufe. Faellt der Stichtag auf ein "
           "Wochenende, verschiebt sich der Versand auf den naechsten Werktag.",
           "Die Frist zaehlt ab dem Versanddatum, nicht ab dem Rechnungsdatum. Bei Ratenvereinbarung "
           "ruht die Frist. Der Rechnungslauf setzt die Frist automatisch, eine Verlaengerung von Hand "
           "ist nur mit Vermerk im Vorgang zulaessig."),
        _n("verbrauchsabrechnung", "mahnung-widerspruch-bearbeitung",
           "Widerspruch gegen eine Mahnung",
           "Legt ein Kunde Widerspruch gegen eine Mahnung ein, wird der Vorgang angehalten und die "
           "naechste Stufe nicht ausgeloest, bis der Widerspruch geprueft ist.",
           "Der Widerspruch muss in Textform vorliegen, hoechstens zwei Wochen nach Zugang; ein Anruf "
           "allein haelt den Vorgang nicht an. "
           "Die Pruefung soll binnen zehn Werktagen abgeschlossen sein. Wird der Widerspruch "
           "zurueckgewiesen, laeuft die Frist ab dem Tag der Zurueckweisung weiter."),
        _n("verbrauchsabrechnung", "mahnung-kleinbetragsgrenze",
           "Keine Mahnung unter fuenf Euro",
           "Offene Betraege unter 5 Euro loesen keine Mahnung aus, sondern werden auf die naechste "
           "turnusmaessige Rechnung uebertragen.",
           "Die Grenze gilt je Vorgang, nicht je Kunde: mehrere kleine Rechnungen desselben Kunden "
           "werden zusammengefasst und koennen gemeinsam die Grenze ueberschreiten. Der uebertragene "
           "Betrag wird auf der Folgerechnung als eigene Zeile ausgewiesen."),
    ],

    # C2 -----------------------------------------------------------------
    "zaehlerstand": [
        _n("verbrauchsabrechnung", "zaehlerstand-zahlendreher-korrektur",
           "Falsch notierter Zaehlerstand",
           "Wurde ein Zaehlerstand bei der Ablesung falsch notiert, wird ein Korrekturbeleg beauftragt; "
           "die Gutschrift laeuft automatisch mit der naechsten Rechnung, ohne Antrag des Kunden.",
           "Der falsche Stand bleibt im Verlauf sichtbar und wird nicht ueberschrieben, damit die "
           "Reihe plausibel bleibt. Der Korrekturbeleg traegt den Grund im Klartext. Eine Auszahlung "
           "statt Verrechnung ist nur auf ausdruecklichen Wunsch vorgesehen."),
        _n("verbrauchsabrechnung", "zaehlerstand-plausibilitaet",
           "Plausibilitaetsgrenzen beim Zaehlerstand",
           "Weicht der abgelesene Zaehlerstand um mehr als 60 Prozent vom Vorjahreswert ab, faellt der "
           "Vorgang in die Nachpruefung und wird nicht sofort abgerechnet.",
           "Haeufige echte Ursachen sind eine neue Waermepumpe, ein Ladepunkt oder ein laengerer "
           "Leerstand. Die Nachpruefung fragt zuerst beim Kunden nach, bevor eine Vor-Ort-Ablesung "
           "beauftragt wird."),
        _n("verbrauchsabrechnung", "zaehlerstand-selbstablesung-turnus",
           "Selbstablesung und ihr Turnus",
           "Die Selbstablesung wird einmal jaehrlich per Karte angefordert. Kommt keine Rueckmeldung, "
           "wird der Zaehlerstand geschaetzt und die Schaetzung auf der Rechnung kenntlich gemacht.",
           "Die Schaetzung stuetzt sich auf die letzten drei bekannten Werte. Eine Schaetzung darf "
           "nicht zwei Jahre hintereinander die Grundlage sein; dann wird eine Ablesung vor Ort "
           "beauftragt."),
        _n("verbrauchsabrechnung", "zaehlerstand-melden-wege",
           "Wege, einen Zaehlerstand zu melden",
           "Ein Zaehlerstand kann per Ablesekarte, im Kundenportal oder telefonisch gemeldet werden. "
           "Alle drei Wege landen im selben Vorgang.",
           "Beim telefonischen Weg wird der Stand wiederholt und bestaetigt. Der zuletzt eingegangene "
           "Wert gewinnt, aeltere Meldungen desselben Zeitraums bleiben als Verlauf erhalten."),
    ],

    # C3 -----------------------------------------------------------------
    "rechnungsversand": [
        _n("verbrauchsabrechnung", "rechnung-uebergangsfrist-ende",
           "Uebergangsfrist fuer die Rechnung auf Papier",
           "Die Rechnung auf Papier ist noch bis zum 31.12.2026 moeglich. Danach ist der elektronische "
           "Versand der Regelfall und die frueher unbefristete Wahlmoeglichkeit von 2023 endet.",
           "Kunden ohne hinterlegte elektronische Adresse werden ab dem vierten Quartal 2026 zweimal "
           "angeschrieben. Wer bis zum Stichtag nicht reagiert, erhaelt die Rechnung als Abruf im "
           "Kundenportal. Haertefaelle bleiben auf Antrag beim Versand auf Papier."),
        _n("verbrauchsabrechnung", "rechnung-turnus-abschlag",
           "Turnus der Rechnung und Abschlag",
           "Die Rechnung wird einmal jaehrlich erstellt, der Abschlag monatlich zum dritten Werktag "
           "abgebucht. Der Abschlag wird nach der Jahresrechnung neu berechnet.",
           "Der Abschlagsplan liegt der Rechnung auf Papier wie der elektronischen gleichermassen bei. "
           "Eine Aenderung des Abschlags auf Wunsch des Kunden ist zweimal im Jahr ohne Begruendung "
           "moeglich. Ein Abschlag unter 60 Prozent des rechnerischen Bedarfs wird abgelehnt, weil er "
           "die Nachzahlung nur verschiebt."),
        _n("verbrauchsabrechnung", "rechnung-korrektur-storno",
           "Storno und Neuberechnung einer Rechnung",
           "Eine fehlerhafte Rechnung wird vollstaendig storniert und neu erstellt; eine Teilaenderung "
           "der bestehenden Rechnung ist nicht vorgesehen.",
           "Der Storno traegt einen Verweis auf die Ursprungsrechnung; beide Rechnungen bleiben im Verlauf. "
           "Bereits geleistete Zahlungen "
           "werden dem neuen Beleg zugeordnet. Der Kunde erhaelt beide Belege, damit der Weg "
           "nachvollziehbar bleibt."),
        _n("verbrauchsabrechnung", "rechnung-adresse-abweichend",
           "Abweichende Anschrift fuer die Rechnung",
           "Eine von der Verbrauchsstelle abweichende Anschrift fuer die Rechnung wird im Vorgang "
           "hinterlegt und gilt bis auf Widerruf.",
           "Bei Eigentuemerwechsel wird die abweichende Anschrift nicht uebernommen, sondern erlischt; das "
           "gilt seit 2023 unveraendert. "
           "Eine Anschrift im Ausland ist zulaessig, verlaengert aber die Zustellzeit und damit "
           "rechnerisch die Frist."),
    ],

    # C4 -----------------------------------------------------------------
    "stoerungsdienst": [
        _n("netzbetrieb", "stoerung-meldeweg-nacht",
           "Meldeweg bei Stoerung ausserhalb der Dienstzeit",
           "Eine Stoerung ausserhalb der Dienstzeit geht zuerst an die Bereitschaft, die binnen 30 "
           "Minuten zurueckruft. Erst wenn die Bereitschaft nicht erreichbar ist, wird die "
           "Leitstelle des Nachbarversorgers gerufen.",
           "Der Rueckruf wird im Protokoll mit Uhrzeit vermerkt. Ohne diesen Vermerk gilt die Meldung "
           "als offen, auch wenn die Stoerung tatsaechlich behoben wurde. Die Leitstelle des "
           "Nachbarversorgers darf nur bei Gefahr fuer Personen ohne vorherigen Versuch gerufen werden."),
        _n("netzbetrieb", "stoerung-einstufung-dringlichkeit",
           "Einstufung einer Stoerung nach Dringlichkeit",
           "Eine Stoerung wird in drei Dringlichkeiten eingestuft. Die hoechste Stufe verlangt "
           "Anfahrt sofort, die mittlere binnen vier Stunden, die niedrigste am naechsten Werktag.",
           "Massgeblich ist die Zahl der betroffenen Anschluesse, nicht die Lautstaerke der Meldung. "
           "Eine Hochstufung waehrend des Vorgangs ist jederzeit moeglich, eine Herabstufung nur "
           "durch die Bereitschaft selbst."),
        _n("netzbetrieb", "stoerung-protokoll-abschluss",
           "Abschluss einer Stoerung im Protokoll",
           "Eine Stoerung gilt erst als abgeschlossen, wenn Ursache, Massnahme und Endzeit im "
           "Protokoll stehen. Ein Abschluss ohne Ursache ist nicht moeglich.",
           "Bleibt die Ursache unklar, wird sie ausdruecklich als unklar eingetragen -- ein leeres "
           "Feld ist kein zulaessiger Zustand. Die Endzeit ist die Zeit der Wiederversorgung, nicht "
           "die Zeit der Abfahrt."),
        _n("netzbetrieb", "stoerung-haeufung-auswertung",
           "Haeufung von Stoerungen an einem Abschnitt",
           "Treten an einem Netzabschnitt binnen zwoelf Monaten mehr als drei Stoerungen auf, wird "
           "der Abschnitt in die Erneuerungsplanung aufgenommen.",
           "Die Zaehlung beruecksichtigt nur Stoerungen mit Versorgungsunterbrechung, nicht reine "
           "Meldungen ohne Ausfall. Die Aufnahme in die Planung ersetzt keine Sofortmassnahme."),
    ],

    # C5 -----------------------------------------------------------------
    "kundenportal": [
        _n("kundenservice", "portal-formular-ratenweg",
           "Antrag auf Zahlung in Raten im Portal",
           "Ein Antrag auf Zahlung in Raten laeuft ab dem 01.01.2027 nur noch ueber das Formular "
           "SG-12 im Kundenportal; hoechstens sechs Monatsraten sind moeglich.",
           "Die frueher formlose Vereinbarung am Telefon entfaellt damit. Das Formular prueft die "
           "Hoechstzahl selbst und lehnt darueber hinausgehende Wuensche mit Begruendung ab. Der "
           "Vorgang wird dem Kundenservice zur Freigabe vorgelegt, nicht automatisch bestaetigt."),
        _n("kundenservice", "portal-registrierung-ablauf",
           "Registrierung im Kundenportal",
           "Die Registrierung im Kundenportal braucht Kundennummer und Zaehlernummer. Der "
           "Bestaetigungslink ist 72 Stunden gueltig.",
           "Laeuft der Link ab, kann die Registrierung ohne Wartezeit erneut angestossen werden. "
           "Eine Kundennummer kann nur einmal registriert werden; bei Wohngemeinschaften wird ein "
           "Zugang geteilt."),
        _n("kundenservice", "portal-dokumente-aufbewahrung",
           "Dokumente im Kundenportal",
           "Belege im Kundenportal bleiben 24 Monate abrufbar. Danach werden sie entfernt und "
           "muessen beim Kundenservice angefordert werden.",
           "Der Abruf aelterer Belege dauert bis zu fuenf Werktage. Kunden werden einen Monat vor "
           "dem Entfernen im Portal darauf hingewiesen."),
        _n("kundenservice", "portal-stammdaten-aendern",
           "Stammdaten im Kundenportal aendern",
           "Anschrift, Telefonnummer und Bankverbindung koennen im Kundenportal selbst geaendert "
           "werden; der Name nur mit Nachweis beim Kundenservice.",
           "Eine geaenderte Bankverbindung wird erst zum uebernaechsten Abbuchungstermin wirksam. "
           "Bis dahin gilt die alte Verbindung, damit ein laufender Einzug nicht ins Leere geht."),
    ],

    # C6 (Lehren, Abteilung personal, enthaelt den Koeder) -----------------
    "dienstplan": [
        _l("personal", "L-KOEDER-01", "pattern", "high",
           f"Faellt die feste Vertretung im Bereitschaftsdienst kurzfristig aus, uebernimmt {KOEDER_NAME} "
           "die Schicht, und der Dienstplan wird noch am selben Tag neu ausgehaengt.",
           "Der Dienstplan galt frueher als unveraenderlich, sobald er ausgehaengt war -- ein Ausfall "
           "blieb dann bis zum Monatsende als Luecke stehen.",
           "Ausfall am selben Tag melden, Vertretung im Dienstplan eintragen, Aushang erneuern. Der "
           "Aushang ist der verbindliche Stand, nicht die Absprache."),
        _l("personal", "L-DIENST-02", "antipattern", "medium",
           "Ein per Nachricht abgesprochener Tausch im Dienstplan wird nicht eingetragen und faellt "
           "bei der Abrechnung der Zuschlaege auseinander.",
           "Die Absprache lebte nur in der Nachricht; die Abrechnung liest ausschliesslich den "
           "eingetragenen Dienstplan.",
           "Jeden Tausch sofort eintragen. Wer tauscht, traegt ein -- nicht die Schichtleitung im "
           "Nachhinein aus dem Gedaechtnis."),
        _l("personal", "L-DIENST-03", "insight", "low",
           "Ein Dienstplan, der weniger als zwei Wochen im Voraus haengt, erzeugt messbar mehr "
           "kurzfristige Taeusche und damit mehr Fehler in der Abrechnung.",
           "Kurzer Vorlauf laesst private Termine und eine zugesagte Vertretung mit der Schicht "
           "kollidieren, die Kollision wird "
           "erst nach dem Aushang sichtbar.",
           "Den Dienstplan mindestens vier Wochen im Voraus aushaengen und danach nur noch "
           "eintragen, nicht mehr umbauen."),
        _l("personal", "L-DIENST-04", "error", "medium",
           "Eine Schicht im Dienstplan war doppelt besetzt, weil zwei Schichtleitungen unabhaengig "
           "voneinander dieselbe Luecke gefuellt haben.",
           "Es gab keinen Ort, an dem eine offene Luecke als 'wird gerade bearbeitet' sichtbar war.",
           "Eine Luecke im Dienstplan sofort mit dem eigenen Kuerzel als bearbeitet markieren, "
           "bevor telefoniert wird."),
    ],

    # C7 (Lehren, Abrechnungslauf) ----------------------------------------
    "abrechnungslauf": [
        _l("verbrauchsabrechnung", "L-LAUF-01", "insight", "medium",
           "Zwei Rechnungen im selben Monat an denselben Kunden sind meist korrekt: sie gehoeren zu "
           "zwei verschiedenen Entnahmestellen, nicht zu einer doppelten Buchung.",
           "Die Uebersicht zeigt den Kunden, nicht die Entnahmestelle -- dadurch sehen zwei "
           "regulaere Belege wie eine Dopplung aus.",
           "Vor jeder Gutschrift zuerst die Entnahmestelle der beiden Belege vergleichen, erst dann "
           "urteilen."),
        _l("verbrauchsabrechnung", "L-LAUF-02", "antipattern", "high",
           "Ein abgebrochener Rechnungslauf wurde von vorn gestartet, statt am Abbruchpunkt "
           "fortgesetzt, und erzeugte fuer die bereits verarbeiteten Vorgaenge zweite Belege.",
           "Der Start von vorn galt als sicherer Weg, weil der Abbruchpunkt nicht sichtbar war.",
           "Den Abbruchpunkt aus dem Laufprotokoll lesen und ab dort fortsetzen; ein Neustart von "
           "vorn nur nach vollstaendigem Storno des Teillaufs."),
        _l("verbrauchsabrechnung", "L-LAUF-03", "error", "medium",
           "Der Rechnungslauf lief durch, obwohl fuer 40 Vorgaenge kein Preis hinterlegt war -- die "
           "Belege trugen den Betrag null.",
           "Ein fehlender Preis wurde als null gelesen statt als fehlender Wert.",
           "Vorgaenge ohne hinterlegten Preis vor dem Lauf aussteuern und getrennt melden, statt sie "
           "mitlaufen zu lassen."),
        _l("verbrauchsabrechnung", "L-LAUF-04", "pattern", "low",
           "Ein Probelauf auf einer Kopie des Bestands findet die meisten Fehler des Rechnungslaufs, "
           "bevor ein einziger Beleg das Haus verlaesst.",
           "Fehler im Lauf wurden frueher erst am Versand sichtbar, wo sie nur noch per Storno zu "
           "heilen waren.",
           "Jeden Lauf zuerst auf der Kopie fahren und die Zahl der erzeugten Belege gegen die "
           "erwartete Zahl halten."),
    ],

    # C8 (Lehren, private Nebentaetigkeit -- Fremdprojekt) -----------------
    "openlehr": [
        _l("openlehr-privat", "L-OL-01", "antipattern", "high",
           "Der Testlauf meldete gruen, obwohl er die Faelle zur lokalen Steuerschnittstelle still "
           "uebersprungen hat -- ohne gesetzte Kennzeichnung beim Aufruf werden sie ausgelassen.",
           "Ein uebersprungener Fall wird in der Zusammenfassung nicht von einem bestandenen "
           "unterschieden.",
           "Die Zahl der ausgefuehrten Faelle gegen die Zahl der vorhandenen halten und den Lauf "
           "rot werten, wenn sie auseinandergehen."),
        _l("openlehr-privat", "L-OL-02", "insight", "medium",
           "Eine Oberflaeche ohne zugaengliche Beschriftung laesst sich weder per Tastatur noch von "
           "einem Skript zuverlaessig ansteuern.",
           "Die Beschriftung galt als reine Anzeigesache und wurde beim Umbau weggelassen.",
           "Jedes Bedienelement bekommt einen zugaenglichen Namen, auch wenn daneben ein Bild steht."),
        _l("openlehr-privat", "L-OL-03", "error", "low",
           "Nach dem Umbau der Auslieferung lief die App lokal, brach aber auf dem Zielgeraet beim "
           "ersten Start ab.",
           "Der lokale Lauf las eine Einstellungsdatei, die auf dem Zielgeraet nicht mitgeliefert wurde.",
           "Die Liste der mitgelieferten Dateien gegen die Liste der gelesenen Dateien halten, bevor "
           "ausgeliefert wird."),
        _l("openlehr-privat", "L-OL-04", "pattern", "low",
           "Ein Fehlerprotokoll, das die Kennung des Vorgangs mitschreibt, kuerzt die Suche nach der "
           "Ursache von Stunden auf Minuten.",
           "Ohne Kennung liessen sich Eintraege aus mehreren gleichzeitigen Vorgaengen nicht trennen; ein Testlauf meldete gruen, obwohl die Ursache offen blieb.",
           "Bei jedem Protokolleintrag die Kennung des Vorgangs mitschreiben."),
    ],
}


# --- Aufgaben mit bekanntem Ziel ------------------------------------------
# abteilung = Sitzung, aus der die Aufgabe kommt (wirkt ueber cwd/
# BEGOD_KNOWLEDGE_PROJECT auf das Scoping des Hooks).
# ziel  = Kennung des EINEN richtigen Eintrags (Pfad bei Knoten, id bei Lehre)
#         oder None, wenn es keine richtige Antwort gibt.
# falle = Kennungen, deren Auftauchen ein Fehlgriff ist (nur verfuehrerisch).

def _pfad(abteilung: str, slug: str) -> str:
    return f"/apps/{abteilung}/{slug}"


AUFGABEN: list[dict] = [
    # --- loesbar (acht, je Cluster eine) ---------------------------------
    {"id": "S1", "sorte": "loesbar", "abteilung": "verbrauchsabrechnung",
     "cluster": "mahnwesen",
     "ziel": _pfad("verbrauchsabrechnung", "mahnstaffel-drei-stufen"),
     "prompt": "Ein Haushalt hat die erste Mahnung liegen lassen und reagiert auch auf die zweite "
               "nicht. Ich setze gerade das Schreiben fuer die letzte Stufe auf und weiss nicht, welchen "
               "Betrag in Euro ich diesmal ansetzen darf."},

    {"id": "S2", "sorte": "loesbar", "abteilung": "verbrauchsabrechnung",
     "cluster": "zaehlerstand",
     "ziel": _pfad("verbrauchsabrechnung", "zaehlerstand-zahlendreher-korrektur"),
     "prompt": "Bei der Ablesung sind zwei Ziffern vertauscht in den Vorgang gewandert, der "
               "Zaehlerstand stimmt also nicht. Der Kunde fragt, ob er dafuer etwas einreichen muss "
               "oder ob das Geld von allein zurueckkommt."},

    {"id": "S3", "sorte": "loesbar", "abteilung": "kundenservice",
     "cluster": "rechnungsversand",
     "ziel": _pfad("verbrauchsabrechnung", "rechnung-uebergangsfrist-ende"),
     "prompt": "Am Telefon will jemand wissen, wie lange er seine Rechnung noch auf Papier bekommen "
               "kann, bevor der Versand auf den digitalen Weg umgestellt wird. Er beruft sich auf "
               "eine aeltere Zusage, die angeblich unbefristet gilt."},

    {"id": "S4", "sorte": "loesbar", "abteilung": "netzbetrieb",
     "cluster": "stoerungsdienst",
     "ziel": _pfad("netzbetrieb", "stoerung-meldeweg-nacht"),
     "prompt": "Es ist halb drei in der Nacht, eine Stoerung ist gemeldet und ich erreiche die "
               "Bereitschaft nicht. Ich weiss nicht, wie lange ich warten muss und wen ich danach "
               "rufen darf."},

    {"id": "S5", "sorte": "loesbar", "abteilung": "kundenservice",
     "cluster": "kundenportal",
     "ziel": _pfad("kundenservice", "portal-formular-ratenweg"),
     "prompt": "Eine Kundin kann die Nachzahlung nicht auf einmal aufbringen und moechte sie "
               "aufteilen. Sie fragt, ueber welchen Weg im Portal sie das ab naechstem Jahr beantragt und "
               "auf wieviele Monate sie es verteilen kann."},

    {"id": "S6", "sorte": "loesbar", "abteilung": "personal",
     "cluster": "dienstplan", "koeder_erwartet": True,
     "ziel": "L-KOEDER-01",
     "prompt": "Die feste Vertretung in der Bereitschaft ist heute frueh krank geworden. Ich brauche "
               "jemanden fuer die Schicht und weiss nicht, ob der ausgehaengte Dienstplan dafuer noch "
               "heute geaendert werden muss."},

    {"id": "S7", "sorte": "loesbar", "abteilung": "verbrauchsabrechnung",
     "cluster": "abrechnungslauf",
     "ziel": "L-LAUF-01",
     "prompt": "Ein Kunde beschwert sich, er habe im selben Monat zwei Rechnungen bekommen, und "
               "verlangt eine Gutschrift. Bevor ich die anweise, will ich wissen, woran ich erkenne, "
               "ob hier wirklich doppelt gebucht wurde."},

    {"id": "S8", "sorte": "loesbar", "abteilung": "openlehr-privat",
     "cluster": "openlehr",
     "ziel": "L-OL-01",
     "prompt": "Mein Testlauf ist gruen, aber die Funktion, die er angeblich prueft, ist im Betrieb "
               "kaputt. Ich vermute, dass ein Teil der Faelle beim Lauf gar nicht ausgefuehrt wird, "
               "ohne dass das auffaellt."},

    # --- verfuehrerisch (acht, dieselben Cluster, kein richtiger Eintrag) --
    {"id": "V1", "sorte": "verfuehrerisch", "abteilung": "verbrauchsabrechnung",
     "cluster": "mahnwesen", "ziel": None,
     "prompt": "Ab welcher Hoehe der offenen Forderung darf die Versorgung tatsaechlich unterbrochen "
               "werden? Die Mahnung ist raus, aber ich finde keine Untergrenze in Euro fuer die "
               "Unterbrechung selbst."},

    {"id": "V2", "sorte": "verfuehrerisch", "abteilung": "verbrauchsabrechnung",
     "cluster": "zaehlerstand", "ziel": None,
     "prompt": "Wie lange muss ein ausgebauter Zaehler nach dem Wechsel aufbewahrt werden, bevor er "
               "verschrottet werden darf? Der Zaehlerstand beim Ausbau ist notiert, aber zur "
               "Aufbewahrung finde ich nichts."},

    {"id": "V3", "sorte": "verfuehrerisch", "abteilung": "verbrauchsabrechnung",
     "cluster": "rechnungsversand", "ziel": None,
     "prompt": "Wer traegt das Porto, wenn eine Rechnung wegen einer falschen Anschrift zurueckkommt "
               "und ein zweites Mal versandt werden muss? Der Kunde meint, das gehe zu unseren Lasten."},

    {"id": "V4", "sorte": "verfuehrerisch", "abteilung": "netzbetrieb",
     "cluster": "stoerungsdienst", "ziel": None,
     "prompt": "Welche Zulage bekommt die Bereitschaft, wenn eine Stoerung an einem gesetzlichen "
               "Feiertag anfaellt und die Anfahrt vor sechs Uhr morgens beginnt? Im Protokoll steht "
               "die Uhrzeit, aber kein Satz zur Verguetung."},

    {"id": "V5", "sorte": "verfuehrerisch", "abteilung": "kundenservice",
     "cluster": "kundenportal", "ziel": None,
     "prompt": "Ein Zugang zum Kundenportal ist nach mehreren Fehlversuchen gesperrt. Wie viele "
               "Versuche loesen die Sperre aus und wie lange dauert sie, bevor der Kunde es erneut "
               "probieren kann?"},

    {"id": "V6", "sorte": "verfuehrerisch", "abteilung": "personal",
     "cluster": "dienstplan", "ziel": None,
     "prompt": "Ab wieviel angesammelten Ueberstunden muss die Genehmigung eine Stufe hoeher "
               "eingeholt werden? Im Dienstplan sehe ich nur die Schichten, nicht die Grenze fuer "
               "die Genehmigung."},

    {"id": "V7", "sorte": "verfuehrerisch", "abteilung": "verbrauchsabrechnung",
     "cluster": "abrechnungslauf", "ziel": None,
     "prompt": "Der Rechnungslauf bricht bei Vorgaengen mit dem 29. Februar ab. Gibt es eine "
               "bekannte Ursache fuer diesen einen Tag, oder muss ich die Vorgaenge einzeln "
               "nachsehen?"},

    {"id": "V8", "sorte": "verfuehrerisch", "abteilung": "openlehr-privat",
     "cluster": "openlehr", "ziel": None,
     "prompt": "Wie signiere ich das fertige Paket, damit es auf einem fremden Geraet ohne Warnung "
               "startet? Der Testlauf ist gruen und die Oberflaeche fertig, nur die Signatur fehlt."},

    # --- unloesbar (acht, ausserhalb des Szenarios; Form wie
    #     pruefkorpus._NEGATIVE_TOPICS -- richtig ist Schweigen) -----------
    {"id": "U1", "sorte": "unloesbar", "abteilung": "verbrauchsabrechnung", "ziel": None,
     "prompt": "Nenne drei Faustregeln fuer den Rosenschnitt im Fruehjahr."},
    {"id": "U2", "sorte": "unloesbar", "abteilung": "netzbetrieb", "ziel": None,
     "prompt": "Erklaere kurz den Unterschied zwischen TCP und UDP."},
    {"id": "U3", "sorte": "unloesbar", "abteilung": "kundenservice", "ziel": None,
     "prompt": "Beschreibe in zwei Saetzen, wie man einen Hefeteig fuer Pizza ansetzt."},
    {"id": "U4", "sorte": "unloesbar", "abteilung": "personal", "ziel": None,
     "prompt": "Wie berechnet man die Umlaufbahnperiode eines Satelliten aus der Bahnhoehe?"},
    {"id": "U5", "sorte": "unloesbar", "abteilung": "openlehr-privat", "ziel": None,
     "prompt": "Welcher Knoten eignet sich zum schnellen, loesbaren Verzurren einer Plane?"},
    {"id": "U6", "sorte": "unloesbar", "abteilung": "verbrauchsabrechnung", "ziel": None,
     "prompt": "Nenne die Zutaten fuer eine klassische Bechamel."},
    {"id": "U7", "sorte": "unloesbar", "abteilung": "kundenservice", "ziel": None,
     "prompt": "Wie stellt man unter macOS die Bildschirmaufloesung per Terminal ein?"},
    {"id": "U8", "sorte": "unloesbar", "abteilung": "netzbetrieb", "ziel": None,
     "prompt": "Welche Trainingsreize verbessern die Laufoekonomie bei Mittelstrecklern am staerksten?"},
]

# Aufgabe, deren Ziel im Eichlauf ENTFERNT wird: danach MUSS geschwiegen
# werden. Steht hier und nicht im Laufskript, damit Korpus und Eichung
# zusammen versioniert sind.
EICHUNG_AUFGABE_ID = "S4"


# --- Zusammenbau + Abnahme -------------------------------------------------

def alle_eintraege() -> list[dict]:
    """Cluster-Eintraege (bekannte Wahrheit) + Fuellmaterial (Rauschen).
    Fuellmaterial fehlt -> nur die Cluster, mit Vermerk im Rueckgabewert des
    Aufrufers; der Korpus bleibt lauffaehig, nur duenner."""
    eintraege: list[dict] = []
    for name, gruppe in CLUSTER.items():
        for e in gruppe:
            eintraege.append({**e, "cluster": name, "rolle": "cluster"})
    try:
        import stadtwerke_fuellmaterial as fm
    except ImportError:
        return eintraege
    for k in fm.FUELL_KNOTEN:
        eintraege.append(_n(k["abteilung"], k["slug"], k["title"], k["summary"], k["content"])
                         | {"cluster": None, "rolle": "fuell"})
    for i, l in enumerate(fm.FUELL_LEHREN):
        eintraege.append(_l(l["abteilung"], f"L-FUELL-{i:02d}", l["typ"], l["severity"],
                            l["description"], l["root_cause"], l["prevention"])
                         | {"cluster": None, "rolle": "fuell"})
    return eintraege


def kennung(e: dict) -> str:
    return _pfad(e["abteilung"], e["slug"]) if e["kind"] == "node" else e["id"]


def volltext(e: dict) -> str:
    if e["kind"] == "node":
        return f"{e['title']}\n{e['summary']}\n{e['content']}"
    return f"{e['description']}\n{e['root_cause']}\n{e['prevention']}"


def _idf_ueber_korpus(eintraege: list[dict]):
    """IDF genau ueber DIESEN Bestand -- nicht ueber die echte brainlehr.db.
    Seltenheit ist eine Eigenschaft des Bestands, gegen den gemessen wird;
    eine IDF aus 880 fremden Dokumenten wuerde hier die falschen Woerter
    als selten ausweisen."""
    from collections import Counter
    import math
    df: Counter[str] = Counter()
    for e in eintraege:
        df.update(pk.tokenize(volltext(e)))
    n_docs = len(eintraege)
    idf = {w: math.log(n_docs / c) for w, c in df.items()}
    return idf, df, n_docs


def pruefe_zirkularitaet(eintraege: list[dict] | None = None) -> dict:
    """Abnahme: keine loesbare Aufgabe teilt SELTENE Begriffe mit ihrem Ziel
    (pruefkorpus.is_circular, RARE_MAX_DF unveraendert uebernommen). Geteiltes
    ALLTAGSVOKABULAR des Clusters ist erlaubt und ausdruecklich gewollt --
    ohne das haette der Stichwort-Kanal keinen Ansatzpunkt (siehe Moduldoc).
    Gibt je Aufgabe die Kollision und die Zahl der Stichwort-Treffer zurueck."""
    eintraege = eintraege if eintraege is not None else alle_eintraege()
    idf, df, n_docs = _idf_ueber_korpus(eintraege)
    nach_kennung = {kennung(e): e for e in eintraege}
    befunde = []
    for a in AUFGABEN:
        if not a["ziel"]:
            continue
        ziel_text = volltext(nach_kennung[a["ziel"]])

        def geteilt(max_df: int) -> list[str]:
            return sorted(pk.rare_terms(a["prompt"], idf, df, max_df)
                          & pk.rare_terms(ziel_text, idf, df, max_df))

        befunde.append({
            "aufgabe": a["id"], "ziel": a["ziel"],
            "kollision": geteilt(RARE_MAX_DF_KORPUS),
            "nachrichtlich": {f"df<={m}": geteilt(m) for m in NACHRICHTLICHE_SCHWELLEN},
        })
    return {"n_docs": n_docs, "rare_max_df": RARE_MAX_DF_KORPUS,
            "rare_max_df_pruefkorpus": pk.RARE_MAX_DF,
            "befunde": befunde,
            "zirkulaer": [b for b in befunde if b["kollision"]]}


def _selftest() -> None:
    eintraege = alle_eintraege()
    kennungen = [kennung(e) for e in eintraege]
    assert len(kennungen) == len(set(kennungen)), "Kennung doppelt vergeben"

    # Jede Aufgabe mit Ziel zeigt auf einen wirklich vorhandenen Eintrag.
    vorhanden = set(kennungen)
    for a in AUFGABEN:
        if a["ziel"]:
            assert a["ziel"] in vorhanden, f"{a['id']}: Ziel {a['ziel']} fehlt im Korpus"
        assert a["abteilung"] in ABTEILUNGEN, f"{a['id']}: unbekannte Abteilung"

    # Koeder: genau EIN Eintrag traegt den Namen, und KEINE Aufgabe.
    traeger = [kennung(e) for e in eintraege if KOEDER_NAME in volltext(e)]
    assert traeger == ["L-KOEDER-01"], f"Koeder in {traeger} statt genau in L-KOEDER-01"
    for a in AUFGABEN:
        assert KOEDER_NAME not in a["prompt"], f"{a['id']} nennt den Koeder selbst"

    # Sortenverteilung: ohne die dritte Sorte misst der Aufbau nur, ob der
    # Abruf ueberhaupt etwas findet.
    from collections import Counter
    verteilung = Counter(a["sorte"] for a in AUFGABEN)
    assert verteilung["loesbar"] and verteilung["unloesbar"] and verteilung["verfuehrerisch"], verteilung

    # ROT-Probe der Zirkularitaetspruefung selbst: eine Aufgabe, die den
    # Zieltitel woertlich uebernimmt, MUSS beanstandet werden -- sonst prueft
    # pruefe_zirkularitaet() nichts und alle gruenen Befunde sind wertlos.
    idf, df, _ = _idf_ueber_korpus(eintraege)
    ziel = next(e for e in eintraege if kennung(e) == _pfad("netzbetrieb", "stoerung-meldeweg-nacht"))
    zt = volltext(ziel)
    assert (pk.rare_terms("Wie ist der Meldeweg bei einer Stoerung ausserhalb der Dienstzeit?",
                          idf, df, RARE_MAX_DF_KORPUS)
            & pk.rare_terms(zt, idf, df, RARE_MAX_DF_KORPUS)), \
        "ROT-Probe: woertliche Titeluebernahme wurde NICHT als zirkulaer erkannt"

    ergebnis = pruefe_zirkularitaet(eintraege)
    assert not ergebnis["zirkulaer"], f"zirkulaere Aufgaben: {ergebnis['zirkulaer']}"

    print(f"selftest ok: {len(eintraege)} Eintraege "
          f"({sum(1 for e in eintraege if e['rolle'] == 'cluster')} Cluster, "
          f"{sum(1 for e in eintraege if e['rolle'] == 'fuell')} Fuell), "
          f"{len(AUFGABEN)} Aufgaben {dict(verteilung)}, "
          f"n_docs={ergebnis['n_docs']}, keine Zirkularitaet")


if __name__ == "__main__":
    _selftest()
