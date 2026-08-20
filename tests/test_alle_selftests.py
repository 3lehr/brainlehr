"""Ruft jedes Modul auf, das ein eigenes --selftest traegt (Auftrag
2026-08-12, Knoten .../selbsttests-in-die-suite-aufnehmen).

Befund vor diesem Modul: 60 Module unter kern/, haken/ und melder/ hatten
eine --selftest-Funktion, aber nur 8 liefen ueberhaupt in einer Testdatei.
52 verrotteten unbeobachtet -- Beleg aus derselben Sitzung: der Selbsttest
von haken/suchpfad_abruf.py brach mit "Cannot operate on a closed database"
ab, kaputtgegangen durch einen Naht-Umbau, bemerkt hat es niemand, weil er
nirgends lief. (Zaehlung hier: 61 Module tragen tatsaechlich eine
--selftest-Fallunterscheidung, eines mehr als der urspruengliche Befund --
haken/mehrstufiger_abruf.py ERWAEHNT --selftest nur in einem Kommentar,
implementiert es nicht, zaehlt darum nicht mit.)

Aufruf per Subprocess mit `--selftest`, nicht in-process: die 61 Module
nutzen mindestens sechs verschiedene interne Namen fuer ihre
Selbsttest-Funktion (demo/selftest/_selftest, teils hinter main()/main(argv)
verpackt) -- der CLI-Flag ist der einzige stabile, dokumentierte Vertrag.
Subprocess isoliert ausserdem sauber gegen Modulzustand, den ein Selbsttest
beim Import hinterlaesst (globale Monkeypatches u.ae.), was bei 61
nacheinander im selben Prozess importierten Modulen sonst ein Risiko waere.
Kostet Prozessstart je Modul (~20s zusaetzlich fuer alle 61 zusammen,
gemessen) -- gegen die Alternative (61 Sonderfaelle nachbauen, die bei jeder
Umbenennung brechen) die billigere Wahl.

Isolation gegen die echte Datenbank: einige der 61 Module oeffnen
brainlehr.db beim Selbsttest -- die meisten NUR ueber "file:...?mode=ro"
(kein Nebeneffekt auf die echte Datei) oder ueber eine eigene Testkopie, die
sie selbst anlegen (hebb_kanten.py, normbestand.py). Drei Module (siehe
BRAUCHT_ISOLIERTE_DB) oeffnen die DB dagegen normal und legen dabei
-wal/-shm-Dateien NEBEN der echten Datei an -- gemessen ueber einen
Datei-Snapshot vor/nach jedem der 61 Laeufe. Nur diese drei bekommen
BRAINLEHR_DB auf eine eigens erzeugte Kopie umgebogen; eine pauschale
Umbiegung fuer alle 61 wurde gemessen und verworfen (siehe
BRAUCHT_ISOLIERTE_DB-Kommentar -- eine frische Kopie ohne warmen
Seiten-Cache lies mindestens ein Modul von 0,1 auf ueber 90 Sekunden
einbrechen).

xfail mit Grund (5 von 61, siehe XFAIL unten): kein xfail ohne Begruendung,
ein xfail ohne Grund ist ein verstecktes Rot. Repariert wurden die anderen 3
roten Faelle direkt im Modul (liefermenge.py, foederation.py,
wissensverlauf.py) -- echte, billige Codefehler, kein Testkosmetik.

1 von 61 laeuft absichtlich NICHT mit (siehe ZU_TEUER_FUER_DIE_SUITE unten,
Grund dort): messlauf_abrufguete.py braucht ueber 90 Sekunden und haette die
Suite beinahe verdoppelt."""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
ROOT = _w
sys.path[:0] = [str(ROOT)]

# Alle 61 Module mit einer echten --selftest-Fallunterscheidung (gemessen
# 2026-08-12 per grep+ast ueber kern/, haken/, melder/).
MODULE = [
    # 2026-08-19: Der Fall, der DIESE Datei ausgeloest hat (siehe Modulkopf),
    # war bis heute weder behoben noch gelistet -- sein Selbsttest brach an
    # einer geschlossenen Verbindung ab. Behoben und eingetragen, damit die
    # Reparatur bewacht ist statt nur vorgenommen.
    "haken/suchpfad_abruf.py",
    # 2026-08-19 von test_kein_modul_faellt_durch_die_liste gefunden --
    # darunter melder/kennungskollision.py, das ich am selben Tag selbst
    # angelegt und nicht eingetragen habe. Genau dafuer gibt es den Test.
    "haken/mehrstufiger_abruf.py",
    "melder/derivatfrische.py",
    "melder/kennungskollision.py",
    "haken/antwort_abruf.py",
    "haken/auftrag_recall_hook.py",
    "haken/knowledge_recall_hook.py",
    "kern/abrufguete.py",
    "kern/ankerverfahren.py",
    "kern/anmeldung.py",
    "kern/auditanker.py",
    "kern/ausweis.py",
    "kern/baustein.py",
    "kern/bereinigung.py",
    "kern/build_node_index.py",
    "kern/codekanten.py",
    "kern/dokument.py",
    "kern/designtokens_latex.py",
    "kern/dokumentdienst.py",
    "kern/driftwaechter.py",
    "kern/einschleusung.py",
    "kern/endgueltig_entfernen.py",
    "kern/fenstergroesse.py",
    "kern/fremdimport.py",
    "kern/fundstelle.py",
    "kern/hebb_kanten.py",
    "kern/herkunft_normentscheider.py",
    "kern/kanten_herkunft_rueckwirkend.py",
    "kern/kettenerklaerung.py",
    "kern/knowledge_lint.py",
    "kern/konfidenz.py",
    "kern/lehrenpaket.py",
    "kern/liefermenge.py",
    "kern/meisterschaft.py",
    "kern/messlauf_abrufguete.py",
    "kern/messparameter.py",
    "kern/migrate_normfelder.py",
    "kern/normachsen.py",
    "kern/normbestand.py",
    "kern/normbezug.py",
    "kern/normfundstelle.py",
    "kern/normkraft.py",
    "kern/normrang.py",
    "kern/planbindung.py",
    "kern/planentscheidung.py",
    "kern/planordnung.py",
    "kern/pruefkorpus.py",
    "kern/pruefkorpus_rivalen.py",
    "kern/pruefkorpus_v3.py",
    "kern/pruefspruch.py",
    "kern/rangfolge.py",
    "kern/raum_daten.py",
    "kern/regelpaket.py",
    "kern/reifegrad.py",
    "kern/satz.py",
    "kern/schema_nachzug.py",
    "kern/sicherung_s12.py",
    "kern/sortierregel.py",
    "kern/speicher.py",
    "kern/suche_postgres.py",
    "kern/teilnehmer.py",
    "kern/umschrift_pruefstein.py",
    "kern/umschrift_s12.py",
    "kern/werkzeugrechte.py",
    "kern/wissensnutzen.py",
    "kern/wissensnutzen_blind.py",
    "kern/zahlenbezug.py",
    "melder/agentendauer.py",
    "melder/arbeitsmelder.py",
    "melder/auftragsregister.py",
    "melder/ausloeserlos.py",
    "melder/dienstwache.py",
    "melder/eilmeldung_etikett.py",
    "melder/faehigkeiten.py",
    "melder/foederation.py",
    "melder/kantenstillstand.py",
    "melder/messregeln.py",
    "melder/offene_arbeit.py",
    "melder/plan_bestandsabgleich.py",
    "melder/pruefer.py",
    "melder/rasterblick.py",
    "melder/schemastand.py",
    "melder/spaltenabgleich.py",
    "melder/selbstbeschreibung.py",
    "melder/sichtbarkeit.py",
    "melder/speicherherkunft.py",
    "melder/vektorstand.py",
    "melder/vier_nenner.py",
    "melder/vorschlagsmelder.py",
    "melder/wissensverlauf.py",
    "melder/wirkkette.py",
    "melder/abrufwirkung.py",
    # 2026-08-18 nachgetragen: beide haben einen Selbsttest und liefen bis
    # hierher nie in der Suite mit. rueckfrageschleife.py ist der
    # Stop-Waechter gegen Rueckfrageschleifen und Ankuendigungen ohne
    # Ausfuehrung, gatestand.py haelt die Lastenkataloge gegen ihre eigenen
    # Produktgates und meldet Phantom-Gates.
    "melder/rueckfrageschleife.py",
    "melder/gatestand.py",
    # 2026-08-18, gefunden von test_kein_modul_faellt_durch_die_liste selbst:
    # acht Module mit --selftest, die nie in der Suite liefen. Drei davon sind
    # von heute (kern/abloesung.py BDW-P08, kern/gegenstand.py ADR-028,
    # kern/ausloeser.py Rundruf-Aktion), fuenf sind vorbestehend. Genau dafuer
    # ist dieser Test da -- ein Selbsttest, den niemand faehrt, ist kein Test.
    "haken/agentenanker_abruf.py",
    "haken/agentenanker_einspielung.py",
    "kern/abloesung.py",
    "kern/ausloeser.py",
    "kern/gegenstand.py",
    "kern/planstatus.py",
    "kern/schnappschuss.py",
    "melder/fremdrollen.py",
    # 2026-08-14 nachgetragen: diese zehn melden --selftest ueber sys.argv
    # statt ueber argparse und fielen deshalb durch die Ratsche unten --
    # sie lief nur auf add_argument("--selftest"). Alle zehn liefen
    # nirgends, alle zehn sind gruen. Darunter haken/worktree_identitaet.py,
    # dessen Feldfehler-Fall am selben Tag gebaut wurde.
    "haken/auftragshypothese_waechter.py",
    "haken/existenzpruefung.py",
    "haken/worktree_identitaet.py",
    "kern/anfrage_erweiterung.py",
    "kern/ausschreibekatalog.py",
    "kern/kanarienvogel.py",
    "kern/sicherungen.py",
    "kern/zeitfenster.py",
    "kern/zeitmarke.py",
    "melder/eilmeldung_faellig.py",
    # 2026-08-18, BDW-E09/E07 Crypto-Shredding: neu gebaut, direkt eingetragen.
    "kern/kundenschluessel.py",
    # Von test_kein_modul_faellt_durch_die_liste selbst gefunden
    # (2026-08-19). Alle drei waren committet, trugen --selftest und liefen
    # nie -- abgabepruefung.py und fremdstandsvergleich.py seit 6442ccfe bzw.
    # 833f3dac, bewegungsmelder.py seit f7684b74. Alle drei einzeln gefahren,
    # alle drei gruen; es war eine Luecke in der Liste, kein kaputtes Modul.
    "melder/abgabepruefung.py",
    "melder/bewegungsmelder.py",
    "melder/fremdstandsvergleich.py",
    "migrationen/migrate_sensible_knoten.py",  # ADR-031, 2026-08-19
    "kern/schluesselablage.py",  # ADR-031 Schritt 2, 2026-08-19
    "melder/vermutungswaechter.py",  # Betreiberidee 2026-08-20
    "haken/eilmeldung_frisch.py",  # Zustellung in laufende Sitzungen, 2026-08-20
    "melder/korrekturlehre.py",  # Betreiberidee 2026-08-20
    "haken/regelrouting.py",  # Systemprompt-Routing, 2026-08-20
    "melder/rotprobe.py",  # Belegpflicht am commit-msg, 2026-08-20
    "kern/rueckwirkung.py",  # gemeinsame Zaehler-Bauform, Norm 17b14a32
    "kern/eilmeldung.py",  # Sendekriterien als Pflichtfelder, 2026-08-20
    "melder/ohne_mechanismus.py",  # Arbeitsliste aus dem eigenen Bestand, 2026-08-20
    "melder/klassenausfall.py",  # Mechanismus zu L-0e0ab6 (11x), 2026-08-20
    "tool/faehigkeitskarte.py",  # erzeugte Faehigkeitskarte, 2026-08-20
    "kern/belegsprache.py",  # eine Wortliste fuer beide Waechter, 2026-08-20
    "kern/aufbewahrung.py",
]

# Rot, mit Grund -- je Fall geprueft am 2026-08-12, nicht geraten:
XFAIL = {
    # haken/mehrstufiger_abruf.py und haken/knowledge_recall_hook.py standen
    # hier vom 2026-08-19 (Eintragung) bis 2026-08-19 (Behebung) mit
    # derselben Wurzel: die betroffenen Selbsttest-Faelle liefen gegen die
    # ECHTE, wachsende brainlehr.db und benannten dabei feste Bestandszeilen
    # (L-606b63 bzw. eine Trefferwartung fuer "kennst du paperless-ngx
    # docs?") -- Bestandsdrift, keine Codeaenderung. Beide Module bauen sich
    # jetzt eine eigene Wegwerf-DB aus schema.sql (s. Kommentare in den
    # Modulen selbst) und biegen DB/knowledge_recall_hook.DB nur fuer die
    # Dauer des jeweiligen Testblocks um -- unabhaengig vom Bestandswachstum
    # richtig, per Rot-vor-Gruen und Gegenprobe belegt (Auftrag 2026-08-19).
    # melder/vier_nenner.py stand hier von 833e7ef4 bis 993a8e18 und ist RAUS:
    # der Grund war das Symptom, nicht die Ursache. Es gab ZWEI Module namens
    # `ausloeser`; der Import holte still kern/ statt messungen/, wodurch der
    # Melder bei JEDEM Aufruf abbrach. Ueber den Pfad geladen -- Selbsttest und
    # Produktivlauf gruen. Wird er erneut rot, ist das ein echtes Rot.
    # kern/abrufguete.py stand hier bis 2026-08-14 und ist RAUS, weil der Fall
    # seither gruen laeuft (XPASS(strict), zweimal reproduziert). Der Selbsttest
    # haengt am echten Bestand -- gegen die Suiten-Kopie besteht er, gegen eine
    # frische leere DB nicht (dreimal exit=1 gemessen). Bewusst NICHT wieder als
    # xfail eingetragen: wird er durch Bestandsdrift erneut rot, ist das ein
    # echtes Rot und soll auffallen, statt unter einer veralteten Ausnahme zu
    # verschwinden.
    "kern/knowledge_lint.py": (
        "kaputte Testfixtur: die Konfidenzverfall-Probe erwartet, dass ihre "
        "Quellenangabe (fixture_source) als beobachtbare Datei erkannt wird "
        "(kern/konfidenz.py::beobachtbare_datei -- braucht einen Pfad MIT "
        "Schraegstrich). Die Fixture traegt aber nur einen blossen "
        "Dateinamen ohne Pfad, matcht das Muster nicht mehr, faellt auf "
        "Regime 3 zurueck -- decay_paths bleibt leer. Reparatur nicht "
        "billig: der erwartete Zahlenwert (0.0992) haengt an der "
        "echten Git-Historie EINER bestimmten Datei; ein neuer Fixture-Pfad "
        "braucht neue, nachgerechnete Commit-Zahlen."
    ),
    "kern/migrate_normfelder.py": (
        "veralteter Selbsttest: die Alt-Schema-Simulation schneidet per "
        "Regex einen 'Normschicht (N2...)'-Block bis zum naechsten ');' aus "
        "schema.sql. Seit dem Normschicht-Folgeauftrag (2026-08-07/08) "
        "stehen zwischen diesem Block und dem echten ');' der Tabelle "
        "weitere Spalten (norm_art, norm_entscheidung, ...) -- der Regex "
        "findet sein Ende nicht mehr (Assertion 1). Selbst mit engerem "
        "Regex bleibt Assertion 2 rot: norm_rang/gilt_ab/gilt_bis tauchen "
        "seither auch in Trigger-Kommentaren AUSSERHALB der Tabelle auf, "
        "die die Probe faelschlich als 'Spalte noch da' liest. Keine billige "
        "Reparatur, der Testaufbau selbst muss auf die gewachsene Datei "
        "umgestellt werden."
    ),
    "kern/regelpaket.py": (
        "vorbestehend rot, gefunden 2026-08-14 beim Nachtragen der 12 "
        "durchgefallenen Module -- nicht durch diese Arbeit verursacht. "
        "Der Selbsttest bricht mit sqlite3.IntegrityError ab: "
        "'knowledge_nodes.norm_art fehlt fuer einen Satz fremder Herkunft'. "
        "Ein Trigger verlangt norm_art, das Testfixture liefert es nicht -- "
        "dieselbe Luecke, die der Startmelder als 'Normachse 2 ist stumm: "
        "84 von 84 Normen ohne Art' meldet. Reparatur gehoert zur Normachse, "
        "nicht in diese Datei: solange norm_art im ganzen Bestand leer ist, "
        "wuerde ein hier gesetzter Wert nur den Test gruen faerben."
    ),
}

assert set(XFAIL) <= set(MODULE)
assert len(MODULE) == 130, len(MODULE)  # + haken/suchpfad_abruf.py und 3 nachgetragene (2026-08-19)  # + kern/kundenschluessel.py (2026-08-18, BDW-E09/E07)  # 61 + kern/lehrenpaket.py (2026-08-12) + melder/eilmeldung_etikett.py (2026-08-13) + melder/vorschlagsmelder.py (Auftrag 84, 2026-08-13) + 12 nachgetragene (2026-08-14, gefunden von test_kein_modul_faellt_durch_die_liste -- 11 davon waren vorbestehend und liefen nie) + kern/satz.py (2026-08-15T06:20:00+0200, ebenfalls von diesem Test gefunden -- sein Selbsttest war seit dem Anlegen rot) + melder/spaltenabgleich.py (Linie J3, 2026-08-15) + melder/plan_bestandsabgleich.py (Soll/Wirklichkeit-Abgleich fuer Planzeilen, 2026-08-15) + kern/driftwaechter.py (F6, Drift-Waechter Darstellung/Blatt, schnelle Darstellung im selben Modul, 2026-08-15) + kern/designtokens_latex.py (LaTeX-Erzeuger fuer Gestaltungsvorrat, ADR-015, 2026-08-15) + melder/wirkkette.py (Linie J2, Haken- und Prozessabgleich, 2026-08-15) + melder/agentendauer.py (Agentendauer-Melder, 2026-08-15, nebenlaeufig eingetragen) + melder/abrufwirkung.py (dauerhafter Abrufwirkungs-Verlauf, 2026-08-15) -- Zahl bei Eintragung nebenlaeufig veraltet vorgefunden (97 statt der tatsaechlichen Listenlaenge), auf den echten Bestand korrigiert statt weitergezaehlt

# Nur diese 3 legen -wal/-shm NEBEN der echten Datenbank an, wenn sie
# BRAINLEHR_DB unbesetzt lassen -- gemessen 2026-08-12 per Datei-Snapshot
# vor/nach jedem der 61 Selbsttests (siehe Commit-Nachricht). Alle anderen
# oeffnen entweder gar keine DB oder ausschliesslich ueber
# "file:...?mode=ro" (kein WAL-Nebendateien-Nebeneffekt) oder verwalten ihre
# eigene Testkopie schon selbst (hebb_kanten.py, normbestand.py). Nur diese
# 3 bekommen BRAINLEHR_DB auf eine isolierte Kopie umgebogen -- eine
# pauschale Umbiegung fuer alle 61 wurde gemessen und verworfen: mindestens
# ein Modul (messlauf_abrufguete.py) braucht auf einer frischen Kopie ohne
# warmen Seiten-Cache ueber 90 Sekunden statt 0,1 -- ein einzelnes Modul haette
# die Laufzeit der ganzen Suite mehr als verdoppelt, fuer einen Nutzen, den
# das Modul (rein lesend, mode=ro) nicht braucht.
BRAUCHT_ISOLIERTE_DB = {
    "haken/antwort_abruf.py",
    "haken/knowledge_recall_hook.py",
    "kern/messparameter.py",
}
assert BRAUCHT_ISOLIERTE_DB <= set(MODULE)


# kern/anmeldung.py::_selftest() liest den ANGEMELDETEN Bestand
# (ausweis.ausweisdatei()) und prueft daran die Doppelanmeldung -- es braucht
# also mindestens EINEN vorhandenen Ausweis, sonst bricht die eigene Annahme
# "kein Ausweis im Bestand -- Selbsttest nicht aussagekraeftig" (kern/
# anmeldung.py) ab. Bis 2026-08-13 lief das nur zufaellig gruen, weil die
# echte ~/Desktop/brainlehr-ausweise/ausweise.json dieses Rechners bereits
# Eintraege trug -- derselbe Heimatverzeichnis-Fehler wie bei den 14 anderen
# Tests dieses Auftrags, nur unbemerkt, weil er hier zufaellig gruen ausging.
# Statt den Selbsttest von kern/anmeldung.py zu lockern (tabu, kern/ ist
# Grenze dieses Auftrags): eine EIGENE, isolierte ausweise.json mit genau
# einem Eintrag anlegen und nur fuer DIESEN Subprozess BRAINLEHR_AUSWEISE
# darauf umbiegen -- exakt dasselbe Muster wie BRAINLEHR_DB oben.
BRAUCHT_ISOLIERTEN_AUSWEIS = {"kern/anmeldung.py"}
assert BRAUCHT_ISOLIERTEN_AUSWEIS <= set(MODULE)


@pytest.fixture(scope="session")
def ausweis_kopie_mit_einem_eintrag(tmp_path_factory) -> Path:
    """Isolierter Ausweisordner mit genau einem beglaubigten Eintrag --
    braucht kern/anmeldung.py::_selftest() (siehe BRAUCHT_ISOLIERTEN_AUSWEIS),
    unabhaengig vom Bestand im Heimatverzeichnis des ausfuehrenden Rechners."""
    import ausweis  # noqa: PLC0415  # gleicher Suchpfad wie conftest.py legt ihn an

    ordner = tmp_path_factory.mktemp("selftest_ausweise")
    pfad = ordner / "ausweise.json"
    ausweis.anlegen("selftest-teilnehmer", ["leser"], pfad=pfad)
    return pfad


# kern/messlauf_abrufguete.py::demo() lief in dieser Sitzung IMMER ueber 90
# Sekunden (45 echte Retrieval-Faelle gegen den vollen Bestand, unabhaengig
# von Original oder Kopie -- geprueft, keine Kopie-Eigenart). Ein einzelnes
# Modul haette die 150s-Suite damit fast verdoppelt: bewusst NICHT
# aufgenommen, hier benannt statt verschwiegen (Auftrag: "dann lieber
# weniger aufnehmen und sagen, welche fehlen").
ZU_TEUER_FUER_DIE_SUITE = {
    "kern/messlauf_abrufguete.py": "demo() braucht >90s (45 echte "
        "Retrieval-Faelle gegen den vollen Bestand) -- haette die Suite "
        "beinahe verdoppelt. Weiter separat pruefbar: "
        "python3 kern/messlauf_abrufguete.py --selftest",
}
assert ZU_TEUER_FUER_DIE_SUITE.keys() <= set(MODULE)


@pytest.fixture(scope="session")
def brainlehr_db_kopie(tmp_path_factory) -> Path:
    """Eine konsistente Kopie der echten brainlehr.db, einmal pro
    Testsitzung erzeugt -- ueber die sqlite3-Backup-API, NICHT per
    Dateikopie: brainlehr.db wird von anderen Sitzungen gleichzeitig
    beschrieben (WAL-Modus), eine rohe Dateikopie kann dabei eine
    inkonsistente Momentaufnahme einfangen (in dieser Sitzung beobachtet:
    eine per shutil.copy2 gezogene Kopie liess denselben Selbsttest von
    0,1 auf über 90 Sekunden CPU-Zeit einbrechen -- vermutlich eine
    zerrissene Seite mitten in einer fremden Transaktion). Die Backup-API
    haelt waehrend des Kopierens eine Lesesperre und liefert einen
    garantiert konsistenten Stand.

    Nur fuer BRAUCHT_ISOLIERTE_DB gebraucht (siehe dort); jeder
    Selbsttest-Subprozess dieser drei Module bekommt BRAINLEHR_DB auf diese
    Kopie gesetzt (siehe echte_db_unangetastet fuer den Nachweis, dass die
    echte Datei dabei unangetastet bleibt)."""
    ziel = tmp_path_factory.mktemp("selftest_db") / "brainlehr.db"
    quelle = sqlite3.connect(f"file:{ROOT / 'brainlehr.db'}?mode=ro", uri=True)
    ziel_conn = sqlite3.connect(str(ziel))
    quelle.backup(ziel_conn)
    ziel_conn.close()
    quelle.close()
    return ziel


def _lauf(relpath: str, db_kopie: Path, ausweis_kopie: Path | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("BEGOD_KNOWLEDGE_DB", None)
    if relpath in BRAUCHT_ISOLIERTE_DB:
        env["BRAINLEHR_DB"] = str(db_kopie)
    if relpath in BRAUCHT_ISOLIERTEN_AUSWEIS:
        assert ausweis_kopie is not None
        env["BRAINLEHR_AUSWEISE"] = str(ausweis_kopie)
        env.pop("BRAINLEHR_GEHEIMNIS", None)
    return subprocess.run(
        [sys.executable, str(ROOT / relpath), "--selftest"],
        # 30 s waren zu knapp: kern/liefermenge.py braucht auf dieser Maschine
        # 32-41 s, je nach Last. Der Test schlug damit fehl, wenn nebenher
        # gearbeitet wurde, und bestand sonst -- ein Ergebnis, das von der
        # Auslastung abhaengt, ist kein Ergebnis. Gemessen 2026-08-12.
        # Wer hier weiter hochsetzen muss, hat einen langsamen Selbsttest und
        # kein Zeitproblem: dann gehoert der Selbsttest verkuerzt, nicht die
        # Grenze.
        cwd=str(ROOT), capture_output=True, text=True, timeout=120, env=env,
    )


def _mit_marker(relpath: str):
    if relpath in ZU_TEUER_FUER_DIE_SUITE:
        return pytest.param(relpath, marks=pytest.mark.skip(
            reason=ZU_TEUER_FUER_DIE_SUITE[relpath]))
    if relpath in XFAIL:
        return pytest.param(relpath, marks=pytest.mark.xfail(
            reason=XFAIL[relpath], strict=True))
    return pytest.param(relpath)


@pytest.fixture(scope="session", autouse=True)
def echte_db_unangetastet():
    """Nachweis zur Abnahme, um die gesamte Sitzung dieser Datei gespannt
    statt die 61 Laeufe ein zweites Mal zu wiederholen: die Dateigroesse der
    ECHTEN brainlehr.db vor/nach allen Selbsttests dieser Datei
    unveraendert -- nicht nur per Codelesen behauptet.

    NUR Groesse, nicht auch Aenderungszeit: brainlehr ist ein Mehr-Sitzungs-
    Betrieb, mehrere andere Agenten schreiben waehrend dieser Testsitzung
    parallel an derselben Datei (beobachtet 2026-08-12: access_log wuchs
    zwischen zwei Messungen ohne mein Zutun). Ein WAL-Checkpoint EINES
    fremden Schreibers hebt die mtime, OHNE die Groesse zu aendern, wenn er
    nur bestehende Seiten aktualisiert -- genau das wurde hier einmal
    beobachtet (Groesse exakt gleich, mtime verschoben). Ein
    mtime-Vergleich waere in diesem Betrieb strukturell flackrig und wuerde
    fuer fremde Arbeit rot werden; die Groesse bleibt der robuste Indikator
    dafuer, dass unser eigener Lauf keine Zeile hinzugefuegt/entfernt hat."""
    echte_db = ROOT / "brainlehr.db"
    vorher = echte_db.stat().st_size
    yield
    nachher = echte_db.stat().st_size
    assert vorher == nachher, (
        "ein Selbsttest hat die Groesse der echten brainlehr.db veraendert -- "
        "BRAINLEHR_DB-Isolierung geprueft, aber offenbar von einem Modul umgangen")


@pytest.mark.parametrize("relpath", [_mit_marker(m) for m in MODULE])
def test_modul_selftest(relpath, brainlehr_db_kopie, ausweis_kopie_mit_einem_eintrag):
    p = _lauf(relpath, brainlehr_db_kopie, ausweis_kopie_mit_einem_eintrag)
    assert p.returncode == 0, (p.stdout + p.stderr)[-3000:]


def test_kein_modul_faellt_durch_die_liste():
    """MODULE ist von Hand gepflegt -- also verrottet sie, sobald jemand baut.

    Genau die Fehlerklasse, gegen die diese Datei gebaut wurde: ein Selbsttest,
    den niemand aufruft, ist kein Selbsttest. Die Zaehlprobe oben (len(MODULE)
    == 64) faellt nur, wenn jemand die LISTE aendert -- nicht, wenn ein neues
    Modul entsteht. Belegt am 2026-08-14: kern/baustein.py wurde mit
    --selftest angelegt und lief nirgends, die Suite blieb gruen.

    Dieser Fall prueft die andere Richtung: jedes Modul unter kern/, haken/ und
    melder/, das ein `--selftest`-Argument anmeldet, muss in MODULE stehen.
    Erkannt wird die ANMELDUNG des Arguments, nicht das blosse Vorkommen des
    Wortes -- ein Modul, das --selftest nur im Kommentar erwaehnt, zaehlt nicht
    (haken/mehrstufiger_abruf.py, siehe Kopf dieser Datei).
    """
    gefunden = set()
    for ordner in ("kern", "haken", "melder"):
        for datei in sorted((ROOT / ordner).rglob("*.py")):
            if "__pycache__" in datei.parts:
                continue
            quelle = datei.read_text(encoding="utf-8", errors="replace")
            # BEIDE Anmeldeformen. Bis 2026-08-14 stand hier nur die
            # argparse-Form -- zehn Module melden --selftest ueber sys.argv
            # und fielen damit durch die Ratsche, die genau das verhindern
            # sollte. Eine Ratsche, die nur eine von zwei Schreibweisen
            # kennt, ist bei der anderen blind, und blind sieht aus wie gruen.
            if ('add_argument("--selftest"' in quelle
                    or "add_argument('--selftest'" in quelle
                    or '"--selftest" in sys.argv' in quelle
                    or "'--selftest' in sys.argv" in quelle):
                gefunden.add(str(datei.relative_to(ROOT)))

    fehlend = sorted(gefunden - set(MODULE))
    assert not fehlend, (
        "Modul(e) mit --selftest, die in MODULE fehlen und darum nie laufen: "
        + ", ".join(fehlend)
        + " -- eintragen und die Zaehlprobe oben nachziehen"
    )
