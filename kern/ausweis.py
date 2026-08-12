#!/usr/bin/env python3
"""ausweis.py -- B4.1/B4.2: wer etwas tut, wird gemessen statt behauptet.

Plan: docs/PLAN_B4_AUSWEIS_2026-08-09.md

DIE FEHLKLASSE, die dieses Modul schliesst: `_identity()` in
knowledge_mcp_server.py loeste bis heute so auf --

    actor or os.environ.get("BEGOD_KNOWLEDGE_ACTOR") or UNBEKANNTER_SCHREIBER

Das ARGUMENT steht vor der Umgebung. Wer `actor="betreiber"` mitschickt, IST
Betreiber; es gibt kein if und kein Abweisen. Bauartgleich mit L-8487fb
(openlehr): ein Endpunkt liess die Kennung frei waehlen und stellte dafuer
einen Grant aus.

WARUM NICHT IM GESPRAECH GEFRAGT WIRD ("wer bist du?"): Das Geheimnis stuende
dann im Verlauf, im Transkript auf der Platte, in jedem Kontextfenster und in
jeder Verdichtung. Ein Modell koennte es weitertragen -- absichtlich oder durch
eingeschleusten Text (siehe einschleusung.py). Und vor allem: wer im Gespraech
antwortet, BEHAUPTET seine Identitaet. Das ist der heutige Zustand mit mehr
Zeremonie. Die Identitaet kommt darum von dort, wo das Modell nicht hinreicht:
aus dem Prozessstart (Umgebungsvariable, vom Klienten gesetzt) bzw. spaeter aus
dem Bearer-Token (ADR-001). Das Modell erfaehrt seinen NAMEN, nie sein
GEHEIMNIS.

KEIN ABWEISEN OHNE AUSWEIS -- bewusst. 3.998 Protokollzeilen, mehrere lokale
Skripte (normbestand.py, hebb_kanten.py) und der ChatGPT-Zugang schreiben heute
ohne Ausweis. Ein hartes Abweisen waere ein Bruch ohne Gegenwert, solange keine
Ausweise existieren. Stattdessen traegt ein unbeglaubigter Name das Praefix
`unbeglaubigt:` -- damit ist im Protokoll dauerhaft und rueckwirkend
unterscheidbar, ob eine Zuschreibung geprueft war oder nur behauptet. Sobald
ein Ausweis vorliegt, ist das Argument stumm.

SCRYPT STATT ARGON2/BCRYPT: Der BSI-Hardstop nennt bcrypt/argon2; beide sind
auf diesem Rechner nicht installiert. hashlib.scrypt ist Standardbibliothek,
ebenfalls memory-hard und in BSI TR-02102-1 als Passwort-Ableitung zugelassen.
Die Abweichung ist damit benannt, nicht stillschweigend.

FEHLKLASSE DIESES MODULS: eine Identitaet wird beglaubigt, die es nicht ist.
PREIS EINES FEHLALARMS: Ein gueltiger Ausweis wird nicht erkannt -> der
Aufrufer faellt auf `unbeglaubigt:` zurueck und verliert Rechte. Laut, nicht
still -- und nie andersherum.

Aufruf:
    python3 ausweis.py --anlegen hausmeister --rollen readonly
    python3 ausweis.py --liste
    python3 ausweis.py --selftest
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

import hashlib
import hmac
import json
import os
import secrets
import stat
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

# --- Ablageort -------------------------------------------------------------
# AUSSERHALB des Repos und ausserhalb jeder Datenbank: wer die knowledge.db
# oeffnen kann, koennte sonst die Rechtetabelle aendern (L-bd1562). Rechte
# gehoeren dorthin, wo der Zugang entschieden wird, nicht dorthin, wo er wirkt.
#
# SICHTBAR STATT VERSTECKT (Betreiber, 2026-08-09: "kannst du mir die ausweise
# auf den desktop legen, das ich sie auf jedenfall wieder finde"). Ein Ordner
# auf dem Schreibtisch statt ~/.brainlehr. Was das kostet und was nicht:
#   - In der Datei stehen NUR scrypt-Hashes, Namen und Rollen. Kein Geheimnis
#     im Klartext, an keiner Stelle. Wer die Datei sieht, kann nichts damit.
#   - Die Rechte (0600) tragen den Schutz, nicht die Verborgenheit. Ein
#     Punktordner im Heimatverzeichnis ist nicht sicherer, nur unauffindbarer.
#   - Bezahlt wird: liegt der Schreibtisch in einer Cloud-Synchronisierung,
#     wandern die Hashes mit. Bei 32 Byte Zufallsgeheimnis ist ein
#     scrypt-Hash nicht zurueckrechenbar -- aber es ist eine Kopie mehr.
# Uebersteuerbar bleibt der Ort ueber BRAINLEHR_AUSWEISE.
VORGABE_AUSWEISORDNER = Path.home() / "Desktop" / "brainlehr-ausweise"
VORGABE_AUSWEISDATEI = VORGABE_AUSWEISORDNER / "ausweise.json"

# Liegt neben der Datei, damit der Ordner sich selbst erklaert, wenn ihn
# jemand in einem halben Jahr wiederfindet.
LIESMICH = """brainlehr — Ausweise

Diese Datei sagt, WER jemand ist. Sie enthaelt KEINE Geheimnisse im Klartext,
nur deren Pruefsummen (scrypt) — wer sie liest, kann sich damit nicht anmelden.

Das eigene Geheimnis (das, mit dem SICH DIESER RECHNER ausweist) steht in
einer eigenen Datei daneben: mein-geheimnis.txt, Rechte 600, eine Zeile, kein
JSON, kein Kommentar drumherum -- damit sie nie "aus Versehen ganz gelesen"
wird, so wie es mit ~/.claude.json am 2026-08-12 passiert ist (ein Assistent
las die Konfigurationsdatei als Ganzes und sah dabei das Geheimnis im
Klartext). mein-geheimnis.txt hat GENAU EINEN Zweck und keinen Kontext, der
einen Assistenten dazu bringen wuerde, sie versehentlich vollstaendig
vorzulesen.

EINRICHTEN:
  1. echo -n "<dein Geheimnis>" > ~/Desktop/brainlehr-ausweise/mein-geheimnis.txt
  2. chmod 600 ~/Desktop/brainlehr-ausweise/mein-geheimnis.txt
  3. den Eintrag "BRAINLEHR_GEHEIMNIS" aus ~/.claude.json
     (mcpServers.knowledge.env) LOESCHEN -- die Datei hat ab jetzt Vorrang,
     ein doppelter Eintrag ist nur eine Kopie mehr, die kompromittiert werden
     kann. Das Loeschen tippt der Betreiber selbst.

Die Umgebungsvariable BRAINLEHR_GEHEIMNIS bleibt als Rueckfall gueltig, falls
die Datei fehlt (z.B. eine laufende Sitzung, bevor umgestellt wurde). Stehen
Datei UND Umgebungsvariable und sind sie verschieden, gewinnt die Datei, und
brainlehr meldet das auf stderr -- keine stille Bevorzugung.

Das Geheimnis steht sonst nur einmal: auf dem Bildschirm, als der Ausweis
angelegt wurde. Bewahre es in deinem Passwortmanager auf. Es wird nie
wiederhergestellt, sondern ersetzt:
  python3 ausweis.py --anlegen <name> --rollen <rollen>

Die Dateirechte sind 600 (nur du). Wird das aufgeweicht, ignoriert brainlehr
die Datei und beglaubigt niemanden mehr — lieber alle unbeglaubigt als falsch
beglaubigt. Das gilt fuer ausweise.json genauso wie fuer
mein-geheimnis.txt.

ART: 'maschine' ist die Vorgabe. Nur ein Ausweis mit art=mensch gilt als
menschlicher Entscheider (z.B. fuer Hausnormen im Rang 1/2). Ein Geheimnis,
das in einer Klientenkonfiguration liegt, gehoert einer Maschine — auch wenn
es deinen Namen traegt.

Ordner verlegen:  Umgebungsvariable BRAINLEHR_AUSWEISE auf den neuen Pfad
(mein-geheimnis.txt zieht automatisch mit, sie liegt immer daneben).
Alles rueckgaengig machen:  diesen Ordner loeschen und BRAINLEHR_GEHEIMNIS aus
der Klientenkonfiguration nehmen. Danach ist der Zustand wie vorher.
"""

# Umgebungsvariablen. GEHEIMNIS traegt das Geheimnis selbst -- es wird nie
# protokolliert, nie zurueckgegeben und nie in eine Fehlermeldung geschrieben.
ENV_GEHEIMNIS = "BRAINLEHR_GEHEIMNIS"
ENV_AUSWEISDATEI = "BRAINLEHR_AUSWEISE"

# Die Datei fuer das eigene Geheimnis (mein-geheimnis.txt, Vorrang vor
# ENV_GEHEIMNIS) lebt bewusst NICHT hier -- Monolith-Bremse bei 1500 Zeilen,
# neue Logik geht in ein eigenes Modul. Siehe kern/geheimnis.py.
from geheimnis import aufloesen_mit_datei  # noqa: E402

# --- Einladung per PIN (Betreiber, 2026-08-10) ----------------------------
# "hier erscheint eine tan/pin plus anmeldenamen, dann kann ich von hieraus die
# pin chatgpt geben und so kann sich chatgpt als gesteuert von mir ausweisen"
#
# Das ist ein OUT-OF-BAND-Verfahren: die PIN laeuft ueber einen anderen Kanal
# (den Menschen) als die Anmeldung (die Maschine). Die Einloesung ist damit der
# Beweis, dass ein Mensch sie weitergegeben hat -- und genau das ist die
# Zurechnung, die ein Modell sich sonst nur selbst zuschreiben koennte.
#
# WER ERZEUGT DIE PIN, ist die ganze Sicherheit: der MENSCH, nicht der
# Anmeldende. Ein Endpunkt, an dem sich jeder eine PIN ausstellen laesst, waere
# L-1feb37 (Token-Ausgabe ohne Schutz -- ein korrektes consume() ohne
# geschuetztes issue() ist wirkungslos) und L-8487fb (Onboarding, das die
# Kennung frei waehlen laesst).
#
# EINMALIG UND BEFRISTET: eine PIN wird beim Einloesen verbraucht (L-d66ab9:
# ein Bootstrap-Weg, der sich nach einer Nutzung selbst schliesst), und sie
# laeuft ab. 15 Minuten sind lang genug zum Kopieren und kurz genug, dass eine
# vergessene PIN nicht wochenlang gilt.
EINLADUNG_GUELTIG_MINUTEN = 15
PIN_LAENGE = 8

UNBEGLAUBIGT = "unbeglaubigt:"
UNBEKANNT = "unbekannt"

# scrypt-Parameter. n=2**14 ist der von RFC 7914 fuer interaktive Anmeldung
# genannte Wert; er kostet rund 16 MiB und einige Millisekunden je Pruefung.
SCRYPT_N = 2 ** 14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_LEN = 32

# --- Rollenmodell ----------------------------------------------------------
# Uebernommen aus AKA2026 (Knoten /brainlehr/was-brainlehr-fuer-b4-fehlt-liegt-in,
# belegt in konsil-akamy-webclient-2026-03-09.json). Muster: modul:aktion:bezug.
#
# Die DRITTE Stelle ist der Grund, warum dieses Modell und nicht ein eigenes:
# `own` und `published` machen Sichtbarkeit vom BEZUG zum Objekt abhaengig, nicht
# nur von der Rolle. Ohne sie gibt es nur ganz-oder-gar-nicht -- und genau daran
# scheitert jede Trennung innerhalb EINES gemeinsamen Bestands.
#
# Im Code statt in der Ausweisdatei: die Datei sagt, WER jemand ist. Was eine
# Rolle darf, ist eine Entscheidung und gehoert versioniert. Sonst kann, wer
# eine Ausweiszeile schreiben darf, sich auch Rechte erfinden.
# EINBUERGERUNG statt Selbsteintritt (Betreiber, 2026-08-10: "wir brauchen ein
# art einbuergerungsamt, das nicht jeder in brainlehr kommen kann").
#
# Die Unterscheidung, die dahintersteckt, ist die zwischen MELDEREGISTER und
# EINBUERGERUNG: das eine haelt fest, WER DA IST -- das leistet access_log
# bereits, fuer jeden Aufrufer, auch fuer unbeglaubigte. Das andere verleiht
# ZUGEHOERIGKEIT MIT RECHTEN, und die kann sich niemand selbst nehmen.
#
# Technisch: 'ausweis:ausstellen' ist ein eigenes Recht und steht in
# NICHT_DELEGIERBAR. Wer einbuergern darf, kann diese Befugnis nicht
# weiterreichen -- sonst waere die erste Einbuergerung die letzte Kontrolle.
#
# DAS HENNE-EI-PROBLEM und seine ehrliche Antwort: Der erste Ausweis kann nicht
# nach dieser Regel entstehen, denn es gibt noch niemanden, der ihn ausstellen
# duerfte. Dieser Gruendungsakt liegt AUSSERHALB des Systems -- so wie ein Staat
# sich nicht selbst per Formular gruendet. Bei uns ist das der Griff ins
# Dateisystem (siehe selbstbedienung_moeglich): solange der Ordner dem laufenden
# Prozess gehoert, ist der Gruendungsakt fuer jeden offen, auch fuer ein Modell.
# Erst `sudo chown root` macht ihn zu dem, was er sein soll -- ein Akt, der das
# Passwort des Betreibers verlangt.
ROLLEN: dict[str, tuple[str, ...]] = {
    # Nur der Betreiber buergert ein. '*' schliesst ausweis:ausstellen ein.
    "betreiber":   ("*",),
    # Eine eigene Rolle fuer das Einbuergerungsamt: sie darf Ausweise
    # ausstellen und sonst nichts. Damit laesst sich die Befugnis vergeben,
    # ohne gleich alles mitzugeben -- und sie bleibt trotzdem
    # nicht-delegierbar, kann also nicht weitergereicht werden.
    "meldeamt":    ("ausweis:ausstellen",),
    "schreiber":   ("wissen:lesen", "wissen:schreiben",
                    "lehre:lesen", "lehre:schreiben",
                    "kante:lesen", "kante:schreiben",
                    "annahme:lesen", "annahme:schreiben",
                    "verwaltung:lesen"),
    "fachkundig":  ("wissen:lesen", "wissen:schreiben:own",
                    "lehre:lesen", "lehre:schreiben:own",
                    "kante:lesen", "annahme:lesen", "annahme:schreiben:own"),
    "leser":       ("wissen:lesen", "lehre:lesen", "kante:lesen",
                    "annahme:lesen"),
    # Enger Serving-Zugang: Volltext bleibt gesperrt; knowledge_read liefert
    # nur die am Datensatz fuer Raumplanung freigegebene Nutzinformation.
    "raumplaner":  ("wissen:lesen",),
    "gast":        ("wissen:lesen:published", "lehre:lesen:published"),
}

# Bezugsstufen, absteigend nach Weite. Wird gebraucht, damit zwei Rollen mit
# unterschiedlichem Bezug auf dasselbe Recht die WEITERE gewinnen lassen --
# sonst haengt das Ergebnis an der Reihenfolge der Rollenliste.
_BEZUG_WEITE = {"alle": 3, "own": 2, "published": 1}


# Art des Ausweistraegers. VORGABE IST 'maschine', und das ist der Kern:
#
# Ein Ausweis wird brauchbar, indem sein Geheimnis in eine Klientenkonfiguration
# wandert (~/.claude.json). Wer das tut, gibt das Geheimnis einer MASCHINE --
# ab da handelt ein Modell unter diesem Namen. Hiesse der Ausweis dann
# 'betreiber', waere aus dem Modell per Konfigurationseintrag ein Mensch
# geworden.
#
# Das ist keine Theorie: der Trigger knowledge_nodes_normrang_herkunft_bi
# verweigert Hausnormen mit Rang 1/2, wenn norm_entschieden_von auf ein Modell
# zeigt (LIKE '%claude%', '%gpt%', ...) -- und norm_entschieden_von wird aus
# actor gesetzt. Ein menschlich benannter Maschinenausweis haette genau diese
# Sperre lautlos ausgehebelt. Gefunden beim Nachsehen auf die Frage des
# Betreibers "nicht dass wir uns nun selbst aussperren!" -- die Gefahr lag in
# der Gegenrichtung.
ARTEN = ("maschine", "mensch")

# Rechte, die ein Mandat NIE weitergeben kann -- nicht aus Misstrauen gegen den
# Delegierten, sondern wegen der Art der Frage. Das Vorbild ist die
# Urabstimmung: bei Grundsatzfragen entscheidet die Basis selbst, weil eine
# Stellvertretung den Sinn der Frage aufhebt.
# Ein Mandat, das eines davon zu uebertragen versucht, wird beim Anlegen
# abgewiesen statt stillschweigend beschnitten -- sonst entstuende ein Ausweis,
# der aussieht, als koennte er etwas.
NICHT_DELEGIERBAR = frozenset({"*", "verwaltung:schreiben", "norm:setzen",
                               "veto:sperren", "ausweis:ausstellen"})


@dataclass(frozen=True)
class Ausweis:
    """Aufgeloeste Identitaet. `beglaubigt` ist die einzige Angabe, die
    zaehlt -- `name` allein sagt nichts, weil ein unbeglaubigter Name frei
    gewaehlt sein kann."""
    name: str
    rollen: tuple[str, ...]
    beglaubigt: bool
    art: str = "maschine"
    # Wessen Vollmacht in `rollen` mit eingegangen ist -- None heisst: alles
    # daran ist eigenes Recht. Gehoert ins Protokoll, sonst ist hinterher nicht
    # unterscheidbar, ob jemand aus eigenem Recht oder als Delegierter handelte.
    mandat_von: str | None = None
    # Wer diesen Ausweis verantwortet -- gesetzt beim Einloesen einer Einladung,
    # also von einem Menschen. Ein Modell kann es sich nicht selbst geben.
    bedient_von: str = ""

    @property
    def ist_mensch(self) -> bool:
        """Nur ein beglaubigter, ausdruecklich menschlicher Ausweis. Ein
        unbeglaubigter Ausweis ist NIE ein Mensch, egal wie er heisst --
        sonst genuegte ein Argument, um einer zu werden."""
        return self.beglaubigt and self.art == "mensch"

    @property
    def protokollname(self) -> str:
        """Was in access_log.actor landet. Unbeglaubigte Namen tragen das
        Praefix dauerhaft mit -- die Unterscheidung geprueft/behauptet bleibt
        so rueckwirkend auswertbar.

        AUSNAHME 'unbekannt': dort gibt es keine Behauptung, die man als
        unbeglaubigt kennzeichnen koennte -- niemand hat etwas behauptet.
        'unbeglaubigt:unbekannt' waere nicht nur doppelt gemoppelt, es haette
        auch den bestehenden Wert UNBEKANNTER_SCHREIBER veraendert, auf den
        anderer Code vergleicht. Vom eigenen Test gefunden."""
        if self.beglaubigt or self.name == UNBEKANNT:
            return self.name
        return f"{UNBEGLAUBIGT}{self.name}"


# --- Ausweisdatei ----------------------------------------------------------

def ausweisdatei() -> Path:
    roh = os.environ.get(ENV_AUSWEISDATEI)
    return Path(roh) if roh else VORGABE_AUSWEISDATEI


def selbstbedienung_moeglich(pfad: Path | None = None) -> tuple[bool, str]:
    """Kann der laufende Prozess sich SELBST einen Ausweis ausstellen?

    Auf die Frage des Betreibers am 2026-08-10: "nun kann sich jeder aber selbst
    eine identitaet schaffen?" -- ja. `ausweis.py --anlegen chef --rollen
    betreiber --art mensch` steht jedem offen, der die Datei schreiben darf, und
    das schliesst ein Modell ein, das unter demselben Benutzer laeuft. Gemessen:
    der Ordner auf dem Schreibtisch gehoert dem angemeldeten Benutzer, und der
    Serverprozess laeuft unter demselben Konto.

    DAMIT IST art=mensch EIN MERKMAL, KEINE SPERRE. Es verhindert, dass ein
    Modell per Konfigurationszeile zum Menschen wird -- nicht, dass es sich per
    Kommandozeile einen Menschenausweis ausstellt. Dieselbe Unterscheidung wie
    beim Testdaten-Merkmal (Knoten /shared/arch/testdaten-kennzeichnen-sperre-ist):
    ein Merkmal traegt die Herkunft, die Sperre ist physische Trennung.

    DIE ECHTE SPERRE verlangt etwas, das ein Prozess nicht hat -- das Passwort
    des Betreibers. Zwei Wege, beide muss der Betreiber selbst gehen:
      chown root + chmod 644  ->  lesbar fuer alle, schreibbar nur mit sudo
      macOS-Keychain           ->  jeder Zugriff verlangt Touch ID/Passwort

    Diese Funktion loest nichts. Sie macht den Zustand sichtbar, statt ihn zu
    verschweigen -- und das ist der ehrliche Zwischenstand, solange die Trennung
    fehlt."""
    import os
    pfad = pfad or ausweisdatei()
    ziel = pfad if pfad.exists() else pfad.parent
    try:
        eigner = ziel.stat().st_uid
    except OSError:
        return True, "ausweisdatei_nicht_lesbar"
    if eigner == os.getuid():
        return True, (f"selbstbedienung: {ziel} gehoert dem laufenden Prozess "
                      f"(uid {eigner}) — jeder Aufruf kann sich einen Ausweis "
                      f"mit art=mensch ausstellen")
    if os.access(ziel, os.W_OK):
        return True, f"selbstbedienung: {ziel} ist fuer den Prozess schreibbar"
    return False, "getrennt: Anlegen verlangt fremde Rechte"


def _lies_datei(pfad: Path) -> list[dict]:
    """Leere Liste, wenn es keine Datei gibt -- das ist der Normalfall vor der
    Erstausstattung und kein Fehler.

    RECHTEPRUEFUNG: eine Ausweisdatei, die andere lesen duerfen, ist keine.
    Bei zu weiten Rechten wird sie ignoriert (mit Meldung nach stderr) statt
    stillschweigend verwendet -- lieber alle unbeglaubigt als falsch
    beglaubigt."""
    if not pfad.exists():
        return []
    modus = pfad.stat().st_mode
    if modus & (stat.S_IRWXG | stat.S_IRWXO):
        print(f"ausweis: {pfad} ist fuer Gruppe/Andere zugaenglich "
              f"(0{modus & 0o777:o}) -- ignoriert. Beheben: chmod 600 {pfad}",
              file=sys.stderr)
        return []
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as fehler:
        print(f"ausweis: {pfad} nicht lesbar ({fehler}) -- ignoriert.",
              file=sys.stderr)
        return []
    eintraege = daten.get("ausweise") if isinstance(daten, dict) else None
    return eintraege if isinstance(eintraege, list) else []


def _schreibe_datei(pfad: Path, eintraege: list[dict]) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    liesmich = pfad.parent / "LIESMICH.txt"
    if not liesmich.exists():
        liesmich.write_text(LIESMICH, encoding="utf-8")
    # Rechte VOR dem Schreiben setzen: zwischen open() und chmod() laege sonst
    # ein Fenster, in dem die Datei mit den Vorgaberechten der umask existiert.
    fd = os.open(pfad, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "ausweise": eintraege}, f,
                  ensure_ascii=False, indent=2)
        f.write("\n")
    os.chmod(pfad, 0o600)


def _ableiten(geheimnis: str, salz: bytes) -> bytes:
    return hashlib.scrypt(geheimnis.encode("utf-8"), salt=salz,
                          n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=SCRYPT_LEN)


def anlegen(name: str, rollen: list[str], *, geheimnis: str | None = None,
            art: str = "maschine", gilt_bis: str | None = None,
            mandat: dict | None = None, pfad: Path | None = None,
            aussteller: str | None = None) -> str:
    """Legt einen Ausweis an und gibt das Geheimnis EINMAL zurueck. Danach
    steht in der Datei nur noch sein Hash -- ein verlorenes Geheimnis wird
    ersetzt, nie wiederhergestellt.

    `mandat` = {"von": <name>, "rollen": [...], "gegenstand": [...],
                "gilt_bis": <iso>}. Der Gegenstand ist PFLICHT: ein Mandat
    ohne ihn waere ein freies Mandat, und ein freies Mandat fuer ein Modell
    heisst, es entscheidet im Namen eines Menschen ueber Dinge, die dieser nie
    gesehen hat (docs/DURCHSPIEL_BEZUGSGRUPPEN_2026-08-09.md, 8.1)."""
    unbekannte = [r for r in rollen if r not in ROLLEN]
    if unbekannte:
        raise ValueError(f"unbekannte Rolle(n): {unbekannte}. "
                         f"Bekannt: {sorted(ROLLEN)}")
    if not name or ":" in name:
        raise ValueError("Name darf nicht leer sein und keinen Doppelpunkt "
                         "tragen (das Praefix 'unbeglaubigt:' braucht ihn).")
    if art not in ARTEN:
        raise ValueError(f"art muss eine von {ARTEN} sein, nicht {art!r}")
    _pruefe_datum(gilt_bis, "gilt_bis")

    pfad = pfad or ausweisdatei()
    bestand = _lies_datei(pfad)
    _pruefe_einbuergerung(bestand, pfad, name, aussteller)
    return _anlegen_ohne_pruefung(name, rollen, geheimnis=geheimnis, art=art,
                                  gilt_bis=gilt_bis, mandat=mandat,
                                  aussteller_geheimnis=aussteller, pfad=pfad)


def _aussteller_name(aussteller_geheimnis: str | None, pfad: Path) -> str:
    """Wer stellt aus? Aufgeloest, nicht behauptet.

    Ist die Datei leer, ist es der Gruendungsakt -- und der wird als solcher
    vermerkt, samt der ehrlichen Angabe, dass ihn ein Prozess vollzogen hat,
    der sich nicht ausweisen konnte. Genau das ist beim ersten Ausweis dieser
    Instanz passiert (ein Modell fuehrte den Befehl aus, der Mensch wurde sein
    erster Buerger)."""
    if not _lies_datei(pfad):
        return "gruendungsakt (kein Aussteller vorhanden)"
    a = loese_auf(geheimnis=aussteller_geheimnis, pfad=pfad)
    return a.protokollname


def _anlegen_ohne_pruefung(name: str, rollen: list[str], *,
                           geheimnis: str | None = None, art: str = "maschine",
                           gilt_bis: str | None = None, mandat: dict | None = None,
                           bedient_von: str = "",
                           aussteller_geheimnis: str | None = None,
                           pfad: Path | None = None) -> str:
    """Der Kern von anlegen(), ohne die Einbuergerungspruefung.

    Getrennt, weil einloesen() bereits geprueft hat -- dort ist die PIN die
    Berechtigung, und sie wurde von jemandem ausgestellt, der einbuergern
    durfte. Zweimal pruefen hiesse, den Einloesenden nach einem Ausweis zu
    fragen, den er gerade erst holen will."""
    pfad = pfad or ausweisdatei()
    eintraege = [e for e in _lies_datei(pfad) if e.get("name") != name]

    if mandat is not None:
        mandat = _pruefe_mandat(mandat, eintraege)

    geheimnis = geheimnis or secrets.token_urlsafe(32)
    salz = secrets.token_bytes(16)
    # HERKUNFT AM AUSWEIS (Betreiberfrage 2026-08-10: "sind wir hier jetzt
    # gruender und gegruendet?"). Der erste Eintrag lautete
    # {'name':'markus','art':'mensch','rollen':['betreiber']} -- und sagte
    # nicht, WER ihn geschrieben hat. Bei Wissen erzwingt ein Trigger die
    # Herkunft ("ein Eintrag ohne nachpruefbare Herkunft ist eine Behauptung");
    # ausgerechnet dort, wo IDENTITAET entsteht, fehlte sie. Der Gruendungsakt
    # hinterliess keine Spur, obwohl er der folgenreichste Schreibvorgang
    # ueberhaupt ist.
    ausstellender = _aussteller_name(aussteller_geheimnis, pfad)
    eintrag = {
        "name": name,
        "art": art,
        "ausgestellt_von": ausstellender,
        "ausgestellt_am": _jetzt().isoformat(),
        "rollen": list(rollen),
        "salz": salz.hex(),
        "hash": _ableiten(geheimnis, salz).hex(),
        "kdf": {"art": "scrypt", "n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P},
    }
    if gilt_bis:
        eintrag["gilt_bis"] = gilt_bis
    if mandat:
        eintrag["mandat"] = mandat
    if bedient_von:
        # Wer diesen Ausweis verantwortet. Kommt aus der Einladung, also von
        # einem Menschen -- ein Modell kann es sich nicht selbst eintragen.
        eintrag["bedient_von"] = bedient_von
    eintraege.append(eintrag)
    _schreibe_datei(pfad, eintraege)
    return geheimnis


def _pruefe_einbuergerung(bestand: list[dict], pfad: Path, name: str,
                          aussteller: str | None = None) -> None:
    """Wer darf einbuergern? Nur, wer 'ausweis:ausstellen' traegt.

    DER GRUENDUNGSAKT ist die eine Ausnahme: ist die Datei leer, gibt es
    niemanden, der ausstellen koennte. Dieser erste Ausweis entsteht darum ohne
    Pruefung -- so wie ein Staat sich nicht selbst per Formular gruendet. Er
    sollte deshalb der des Betreibers sein, und er ist der einzige, bei dem die
    Reihenfolge zaehlt.

    WAS DIESE PRUEFUNG NICHT LEISTET, ausdruecklich: sie haelt gegen Versehen
    und gegen einen Aufrufer, der sich an Regeln haelt. Sie haelt NICHT gegen
    jemanden, der die JSON-Datei direkt schreibt -- und solange der Ordner dem
    laufenden Prozess gehoert, kann das jeder, auch ein Modell (siehe
    selbstbedienung_moeglich). Zwei Schichten, und nur die untere haelt gegen
    Absicht: `sudo chown root` am Ordner. Diese hier ist die obere.
    """
    if not bestand:
        return                                    # Gruendungsakt
    ausw = loese_auf(geheimnis=aussteller, pfad=pfad)
    if not ausw.beglaubigt:
        raise PermissionError(
            f"Einbuergerung verlangt einen Ausweis mit 'ausweis:ausstellen'. "
            f"Es liegt keiner vor ({ENV_GEHEIMNIS} nicht gesetzt oder unbekannt). "
            f"Der Bestand in {pfad} ist nicht leer — ein Gruendungsakt ist es "
            f"also nicht.")
    if bezug_fuer(ausw, "ausweis:ausstellen") is None:
        raise PermissionError(
            f"'{ausw.name}' darf keine Ausweise ausstellen "
            f"(Rollen: {','.join(ausw.rollen) or '-'}). Noetig ist eine "
            f"Rolle mit 'ausweis:ausstellen' — betreiber oder meldeamt.")



# --- Einladung: PIN erzeugen und einloesen ---------------------------------

def einladen(name: str, *, bedient_von: str, rollen: list[str] | None = None,
             art: str = "maschine", pfad: Path | None = None,
             aussteller: str | None = None, jetzt: datetime | None = None) -> str:
    """Erzeugt eine EINMALIGE, BEFRISTETE PIN. Gibt sie zurueck -- der Mensch
    reicht sie ueber seinen eigenen Kanal weiter.

    `bedient_von` ist der Mensch, der diese Einladung ausspricht. Er landet im
    spaeteren Ausweis und beantwortet damit die Frage, die ein Modell sich
    sonst selbst beantworten muesste: in wessen Auftrag handelt es.

    Wer einladen darf, muss `ausweis:ausstellen` tragen -- eine Einladung IST
    eine Einbuergerung, nur zeitversetzt. Ohne diese Pruefung waere sie der
    Umweg um das Meldeamt."""
    jetzt = jetzt or _jetzt()
    pfad = pfad or ausweisdatei()
    bestand = _lies_datei(pfad)
    _pruefe_einbuergerung(bestand, pfad, name, aussteller)
    if not bedient_von or not bedient_von.strip():
        raise ValueError(
            "bedient_von fehlt. Eine Einladung ohne Menschen dahinter ist eine "
            "Selbstbedienung mit Zwischenschritt.")

    # PERSON UND ZUGANG SIND ZWEIERLEI (Betreiber, 2026-08-10: "die erste
    # chatgpt anmeldung ist der gleiche mensch wie ich hier, ich melde mich als
    # ich ja nur ueber chatgpt an"). Ein Mensch hat mehrere Zugaenge -- Claude
    # Code, ChatGPT, ein zweites Geraet. Jeder bekommt einen EIGENEN Ausweis,
    # damit er einzeln gesperrt werden kann; aber sie gehoeren derselben
    # Person, und daraus folgt die Grenze:
    #
    #   EIN ZUGANG KANN NIE MEHR ALS SEINE PERSON.
    #
    # Ohne diese Pruefung waere `bedient_von` blosser Freitext, und man koennte
    # einem Zugang die Rolle 'betreiber' geben, obwohl die Person nur liest --
    # eine Rechteerweiterung ueber den Umweg "im Auftrag von".
    person = _finde(bestand, bedient_von.strip())
    if person is None:
        raise ValueError(
            f"'{bedient_von}' ist kein Ausweis in diesem Bestand. bedient_von "
            f"zeigt auf eine PERSON, nicht auf einen freien Namen — sonst ist "
            f"der Auftrag eine Behauptung.")
    if _art_von(person) != "mensch":
        raise ValueError(
            f"'{bedient_von}' ist kein Mensch (art={_art_von(person)}). Ein "
            f"Zugang wird von einem Menschen verantwortet, nicht von einer "
            f"weiteren Maschine — sonst entstuende eine Kette ohne Ende.")
    gewollt = set(rollen or ["leser"])
    zuviel = sorted(r for r in gewollt
                    if not _rolle_gedeckt(r, person.get("rollen", ())))
    if zuviel:
        raise ValueError(
            f"Der Zugang soll {zuviel} bekommen, aber '{bedient_von}' hat das "
            f"selbst nicht (Rollen: {person.get('rollen', [])}). Ein Zugang "
            f"kann nie mehr als seine Person.")
    if art not in ARTEN:
        raise ValueError(f"art muss eine von {ARTEN} sein, nicht {art!r}")

    pin = secrets.token_urlsafe(PIN_LAENGE)[:PIN_LAENGE].upper()
    salz = secrets.token_bytes(16)
    einladungen = [e for e in _lies_einladungen(pfad)
                   if e.get("name") != name
                   and not _abgelaufen(e.get("gilt_bis"), jetzt)]
    einladungen.append({
        "name": name,
        "bedient_von": bedient_von.strip(),
        "rollen": list(rollen or ["leser"]),
        "art": art,
        "salz": salz.hex(),
        "hash": _ableiten(pin, salz).hex(),
        "gilt_bis": (jetzt + timedelta(minutes=EINLADUNG_GUELTIG_MINUTEN)).isoformat(),
    })
    _schreibe_einladungen(pfad, einladungen)
    return pin


def einloesen(pin: str, *, pfad: Path | None = None,
              jetzt: datetime | None = None) -> dict:
    """Loest eine PIN ein und gibt {name, geheimnis, bedient_von, rollen}.

    Die PIN wird dabei VERBRAUCHT -- auch bei einem zweiten Versuch mit
    derselben. Und sie ist die einzige Berechtigung: dieser Weg ist bewusst
    ohne Ausweis aufrufbar, denn wer sich anmeldet, hat noch keinen.

    Rueckgabe enthaelt das Geheimnis GENAU EINMAL. Es wird nicht gespeichert,
    nur sein Hash."""
    jetzt = jetzt or _jetzt()
    pfad = pfad or ausweisdatei()
    offen = _lies_einladungen(pfad)
    for eintrag in offen:
        if _abgelaufen(eintrag.get("gilt_bis"), jetzt):
            continue
        try:
            salz = bytes.fromhex(eintrag["salz"])
            erwartet = bytes.fromhex(eintrag["hash"])
        except (KeyError, ValueError):
            continue
        if not hmac.compare_digest(_ableiten(pin, salz), erwartet):
            continue
        # Treffer: verbrauchen, BEVOR der Ausweis entsteht -- sonst koennte ein
        # Fehler beim Anlegen die PIN wiederverwendbar zuruecklassen.
        _schreibe_einladungen(pfad, [e for e in offen if e is not eintrag])
        geheimnis = _anlegen_ohne_pruefung(
            eintrag["name"], eintrag.get("rollen") or ["leser"],
            art=eintrag.get("art", "maschine"),
            bedient_von=eintrag.get("bedient_von", ""), pfad=pfad)
        return {"name": eintrag["name"], "geheimnis": geheimnis,
                "bedient_von": eintrag.get("bedient_von", ""),
                "rollen": eintrag.get("rollen") or ["leser"]}
    raise PermissionError(
        "PIN unbekannt, bereits verbraucht oder abgelaufen. Eine neue "
        "Einladung erzeugt der Mensch, der sie verantwortet.")


def zugaenge_derselben_person(ausw: "Ausweis", pfad: Path | None = None) -> frozenset:
    """Alle Namen, die derselben Person gehoeren wie dieser Ausweis.

    ANLASS (Betreiber, 2026-08-10): "aber chatgpt und claude hier wird ja beides
    von mir bedient, gerade wechsle ich zu chatgpt nur weil mir hier die tokens
    ausgehen." Genau richtig -- und es deckt einen Fehler auf: der Bezug `own`
    verglich bis dahin mit dem Namen des ZUGANGS. Zwei Zugaenge desselben
    Menschen haetten sich damit gegenseitig ausgesperrt: was ueber Claude Code
    entstand, waere fuer ChatGPT fremd gewesen, obwohl derselbe Mensch dahinter
    steht.

    'Eigen' heisst darum: von mir, von meiner Person, oder von einem anderen
    Zugang derselben Person. Ein Ausweis ohne bedient_von steht fuer sich --
    dort bleibt es beim Namen allein."""
    namen = {ausw.name}
    person = ausw.bedient_von or (ausw.name if ausw.art == "mensch" else "")
    if not person:
        return frozenset(namen)
    namen.add(person)
    for e in _lies_datei(pfad or ausweisdatei()):
        if e.get("bedient_von") == person or e.get("name") == person:
            namen.add(e.get("name", ""))
    return frozenset(n for n in namen if n)


def _rolle_gedeckt(rolle: str, person_rollen) -> bool:
    """Deckt eine der Rollen der Person diese Rolle ganz ab?

    Ueber die Bezugsweite verglichen, nicht ueber Rollennamen -- 'leser' deckt
    'gast' ab, obwohl die Namen nichts gemein haben. Derselbe Vergleich wie bei
    der Obergrenze in foederation.py, aus demselben Grund: ein
    Zeichenkettenvergleich haelt 'wissen:lesen:published' faelschlich fuer etwas
    anderes als 'wissen:lesen', obwohl es enger ist."""
    rechte = ROLLEN.get(rolle, ())
    if not rechte:
        return False
    p = Ausweis(name="_p", rollen=tuple(person_rollen), beglaubigt=True)
    r = Ausweis(name="_r", rollen=(rolle,), beglaubigt=True)
    for recht in rechte:
        if recht == "*":
            return any("*" in ROLLEN.get(x, ()) for x in person_rollen)
        modul, _, rest = recht.partition(":")
        aktion = rest.partition(":")[0]
        eigen = bezug_fuer(r, f"{modul}:{aktion}")
        erlaubt = bezug_fuer(p, f"{modul}:{aktion}")
        if erlaubt is None or _BEZUG_WEITE[erlaubt] < _BEZUG_WEITE[eigen]:
            return False
    return True


def _einladungsdatei(pfad: Path) -> Path:
    return pfad.parent / "einladungen.json"


def _lies_einladungen(pfad: Path) -> list[dict]:
    datei = _einladungsdatei(pfad)
    if not datei.exists():
        return []
    modus = datei.stat().st_mode
    if modus & (stat.S_IRWXG | stat.S_IRWXO):
        print(f"ausweis: {datei} ist fuer Gruppe/Andere zugaenglich -- "
              f"ignoriert. Beheben: chmod 600 {datei}", file=sys.stderr)
        return []
    try:
        daten = json.loads(datei.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    eintraege = daten.get("einladungen") if isinstance(daten, dict) else None
    return eintraege if isinstance(eintraege, list) else []


def _schreibe_einladungen(pfad: Path, eintraege: list[dict]) -> None:
    datei = _einladungsdatei(pfad)
    datei.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(datei, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "einladungen": eintraege}, f,
                  ensure_ascii=False, indent=2)
        f.write("\n")
    os.chmod(datei, 0o600)


def _pruefe_datum(wert: str | None, feld: str) -> None:
    if wert is None:
        return
    try:
        datetime.fromisoformat(wert)
    except ValueError:
        raise ValueError(f"{feld} muss ISO-8601 sein, nicht {wert!r}") from None


def _pruefe_mandat(mandat: dict, eintraege: list[dict]) -> dict:
    """Alle Schranken beim ANLEGEN, damit kein Ausweis entsteht, der aussieht,
    als koennte er etwas. Die Laufzeitpruefung in _mandatsrollen() bleibt
    trotzdem -- die Datei kann auch von Hand geschrieben werden."""
    if not isinstance(mandat, dict):
        raise ValueError("mandat muss ein Objekt sein")
    von = mandat.get("von")
    mandant = _finde(eintraege, von) if von else None
    if mandant is None:
        raise ValueError(f"mandat.von: kein Ausweis namens {von!r} vorhanden")
    # Keine Weiterdelegation: eine Kette ist nicht mehr pruefbar, und bei einem
    # Menschen als Mandant braucht sie niemand.
    if isinstance(mandant.get("mandat"), dict):
        raise ValueError(f"{von!r} handelt selbst im Mandat -- "
                         "Weiterdelegation ist nicht vorgesehen")
    gegenstand = mandat.get("gegenstand") or []
    if not gegenstand:
        raise ValueError(
            "mandat.gegenstand fehlt. Ein Mandat ohne Gegenstand ist ein "
            "FREIES Mandat -- der Traeger entschiede dann im Namen eines "
            "anderen ueber Dinge, die dieser nie gesehen hat.")
    gewollt = set(mandat.get("rollen") or ())
    if not gewollt:
        raise ValueError("mandat.rollen fehlt")
    unbekannte = sorted(gewollt - set(ROLLEN))
    if unbekannte:
        raise ValueError(f"mandat.rollen unbekannt: {unbekannte}")
    # Nicht-delegierbare Rechte: manche Befugnisse sind es nicht wegen
    # Misstrauen gegen den Delegierten, sondern wegen der Art der Frage
    # (Urabstimmung, 8.2). Abweisen statt stillschweigend beschneiden.
    verboten = sorted(r for r in gewollt
                      if any(x in NICHT_DELEGIERBAR for x in ROLLEN.get(r, ())))
    if verboten:
        raise ValueError(
            f"nicht delegierbar: {verboten} -- diese Rolle traegt ein Recht "
            f"aus {sorted(NICHT_DELEGIERBAR)}, das bei seinem Traeger bleibt.")
    zuviel = sorted(gewollt - set(mandant.get("rollen", ())))
    if zuviel:
        raise ValueError(
            f"{von!r} hat selbst nicht: {zuviel}. Ein Mandat kann nur eine "
            "Teilmenge weitergeben, nie mehr als der Mandant hat.")
    _pruefe_datum(mandat.get("gilt_bis"), "mandat.gilt_bis")
    return {"von": von, "rollen": sorted(gewollt),
            "gegenstand": sorted(gegenstand),
            **({"gilt_bis": mandat["gilt_bis"]} if mandat.get("gilt_bis") else {})}


# --- Aufloesung ------------------------------------------------------------

def _stand(pfad: Path) -> tuple[int, int, int, int]:
    """Fingerabdruck der Ausweisdatei fuer den Cache-Schluessel. Aendert sie
    sich, faellt der Cache von selbst.

    st_ctime_ns und st_mode gehoeren dazu, nicht nur mtime und Groesse: ein
    `chmod` aendert den Inhalt NICHT, aber sehr wohl, ob die Datei jemanden
    beglaubigen darf (_lies_datei weist zu weite Rechte ab). Ohne beide blieb
    eine reparierte Datei im Cache als 'ignoriert' stehen -- vom eigenen
    Selbsttest gefunden, nicht vermutet."""
    try:
        s = pfad.stat()
        return (s.st_mtime_ns, s.st_ctime_ns, s.st_size, s.st_mode)
    except OSError:
        return (0, 0, 0, 0)


@lru_cache(maxsize=8)
def _pruefe(geheimnis: str, pfad_str: str,
            _stand_schluessel: tuple[int, int, int, int]) -> str | None:
    """Gibt nur den NAMEN zurueck, nicht den Eintrag.

    scrypt kostet je Pruefung rund 16 MiB und einige Millisekunden. Das ist
    fuer eine Anmeldung richtig und fuer einen Protokolleintrag falsch --
    _identity() laeuft bei JEDEM log_access(). Darum einmal je (Geheimnis,
    Dateistand) rechnen. Der Dateistand im Schluessel sorgt dafuer, dass ein
    neu angelegter Ausweis sofort greift, ohne Neustart.

    Warum nur der Name: alles Weitere (Ablauf, Mandat) haengt an der ZEIT und
    darf darum nicht mitgecacht werden -- ein zwischenzeitlich abgelaufenes
    Mandat wuerde sonst weitergelten. Den Eintrag frisch nachzuschlagen kostet
    nichts; die teure Rechnung ist die scrypt-Ableitung, und die bleibt
    gecacht."""
    for eintrag in _lies_datei(Path(pfad_str)):
        try:
            salz = bytes.fromhex(eintrag["salz"])
            erwartet = bytes.fromhex(eintrag["hash"])
            kdf = eintrag.get("kdf", {})
            gerechnet = hashlib.scrypt(
                geheimnis.encode("utf-8"), salt=salz,
                n=kdf.get("n", SCRYPT_N), r=kdf.get("r", SCRYPT_R),
                p=kdf.get("p", SCRYPT_P), dklen=len(erwartet))
        except (KeyError, ValueError, TypeError):
            continue  # kaputter Eintrag beglaubigt niemanden
        # Zeitkonstant: sonst verraet die Laufzeit, wie weit ein geratenes
        # Geheimnis stimmte.
        if hmac.compare_digest(gerechnet, erwartet):
            return eintrag["name"]
    return None


# --- Ablauf und Mandat -----------------------------------------------------

def _jetzt() -> datetime:
    return datetime.now(timezone.utc)


def _abgelaufen(gilt_bis: str | None, jetzt: datetime) -> bool:
    """Ein unlesbares Datum gilt als abgelaufen, nicht als unbefristet. Ein
    Tippfehler im Ablaufdatum darf keinen unbegrenzten Zugang erzeugen."""
    if not gilt_bis:
        return False
    try:
        ende = datetime.fromisoformat(gilt_bis)
    except ValueError:
        return True
    if ende.tzinfo is None:
        ende = ende.replace(tzinfo=timezone.utc)
    return jetzt >= ende


def _art_von(eintrag: dict) -> str:
    """Fehlende Art -> 'maschine'. Ein Altbestand-Eintrag ohne Angabe wird nie
    zum Menschen befoerdert, nur weil das Feld fehlt."""
    art = eintrag.get("art", "maschine")
    return art if art in ARTEN else "maschine"


def _finde(eintraege: list[dict], name: str) -> dict | None:
    for e in eintraege:
        if e.get("name") == name:
            return e
    return None


def _mandatsrollen(eintrag: dict, eintraege: list[dict],
                   jetzt: datetime, gegenstand: str | None
                   ) -> tuple[tuple[str, ...], str | None]:
    """Der Schnitt wird ZUR LAUFZEIT gebildet, nicht beim Ausstellen.

    Delegation ist der klassische Weg zur Rechteausweitung: A darf X,
    delegiert an B, und B kann ploetzlich X+Y. Dagegen hilft nur, bei JEDEM
    Aufruf neu zu schneiden -- verliert der Mandant ein Recht, verliert es der
    Delegierte im selben Moment. Ein beim Ausstellen eingefrorener Schnitt
    ueberlebt den Mandanten.

    IMPERATIVES MANDAT (siehe docs/DURCHSPIEL_BEZUGSGRUPPEN_2026-08-09.md,
    8.1): Fuer ein Modell ist nur das weisungsgebundene Mandat zulaessig. Ein
    freies Mandat hiesse, es entscheidet im Namen eines Menschen ueber Dinge,
    die dieser nie gesehen hat. Darum ist der Gegenstand Pflicht, und
    ausserhalb davon faellt die Vollmacht weg -- ohne Abbruch, das ist das
    'zurueck in die Gruppe'.
    """
    mandat = eintrag.get("mandat")
    if not isinstance(mandat, dict):
        return (), None
    if _abgelaufen(mandat.get("gilt_bis"), jetzt):
        return (), None

    # Gegenstandsbindung: ausserhalb gilt die Vollmacht nicht. Kein Fehler --
    # der Delegierte behaelt seine eigenen Rechte und muss zurueckfragen.
    gegenstaende = mandat.get("gegenstand") or ()
    if gegenstand is None or gegenstand not in gegenstaende:
        return (), None

    mandant = _finde(eintraege, mandat.get("von", ""))
    if mandant is None or _abgelaufen(mandant.get("gilt_bis"), jetzt):
        return (), None
    # Keine Weiterdelegation: ein Mandat aus einem Mandat waere nicht mehr
    # pruefbar. anlegen() weist es bereits ab; hier steht die zweite Schranke,
    # weil die Datei auch von Hand geschrieben werden kann.
    if isinstance(mandant.get("mandat"), dict):
        return (), None

    hat_der_mandant = set(mandant.get("rollen", ()))
    gewollt = set(mandat.get("rollen", ()))
    return tuple(sorted(gewollt & hat_der_mandant)), mandat.get("von")


def loese_auf(argument: str | None = None, *,
              geheimnis: str | None = None,
              pfad: Path | None = None,
              gegenstand: str | None = None,
              jetzt: datetime | None = None) -> Ausweis:
    """DIE Umkehrung: Ausweis gewinnt, Argument ist danach stumm.

    `gegenstand` entscheidet, ob ein Mandat greift (imperatives Mandat, siehe
    _mandatsrollen). `jetzt` wird hereingereicht statt intern geholt -- ohne
    injizierbare Zeit laesst sich kein Ablauf pruefen, ohne die Uhr zu stellen.

    Reihenfolge, sofern `geheimnis` nicht als Parameter mitkommt (der gewinnt
    immer, vor allem fuer Tests):
      1. mein-geheimnis.txt neben der Ausweisdatei (kern/geheimnis.py) --
         VORRANG, damit das Geheimnis nie mehr als Ganzes aus ~/.claude.json
         gelesen werden muss.
      2. sonst BRAINLEHR_GEHEIMNIS aus der Umgebung -- Ruecktritt, damit eine
         laufende Sitzung nicht abbricht, waehrend noch keine Datei existiert.
      Stehen beide UND unterscheiden sie sich, gewinnt die Datei UND es wird
      auf stderr gemeldet -- ein Befund, keine stille Bevorzugung.
      3. Trifft das Geheimnis (aus Datei oder Umgebung oder Parameter) einen
         Eintrag -> beglaubigt.
      4. Sonst: Argument, dann BEGOD_KNOWLEDGE_ACTOR, dann 'unbekannt' --
         jeweils UNbeglaubigt.

    FEHLEN DATEI UND UMGEBUNG BEIDE: es wird NICHT stillschweigend mit
    Rechten weitergearbeitet. Der Aufrufer faellt auf denselben unbeglaubigten
    Zweig wie bei einem falschen Geheimnis -- ohne Rollen, und mit dem
    Praefix 'unbeglaubigt:' an JEDER Stelle, an der der Name spaeter im
    Protokoll auftaucht (protokollname). Das ist die bewusste Entscheidung
    dieser Datei: kein Fehler, kein Abbruch, aber auch keine Rechte ohne
    Nachweis und keine Spur, die das verschweigt.

    Ein Geheimnis, das keinen Eintrag trifft, fuehrt NICHT zu einem Fehler und
    NICHT zu einer stillen Beglaubigung: der Aufrufer faellt auf den
    unbeglaubigten Zweig zurueck. Ein falsches Geheimnis darf nie mehr Rechte
    ergeben als gar keines."""
    if geheimnis is None:
        geheimnis = aufloesen_mit_datei(os.environ.get(ENV_GEHEIMNIS),
                                        pfad or ausweisdatei())
    if not geheimnis and sys.stdin.isatty():
        # Verdeckt nachfragen, statt den Aufrufer auf die Umgebungsvariable zu
        # zwingen. Anlass 2026-08-10: BRAINLEHR_GEHEIMNIS=... im Befehl landet
        # in der Shell-Historie und ist fuer jeden Prozess auf dem Rechner
        # lesbar; die Umgehung per `read -s -p` ist bash-Syntax und scheitert
        # in zsh lautlos -- der Aufruf brach dreimal ab, ohne dass die leere
        # Einladungsdatei den Grund verriet.
        # isatty(), damit Haken, Dienste und Testlaeufe nicht blockieren: dort
        # gibt es niemanden, der tippen koennte, und der unbeglaubigte Zweig
        # ist die richtige Antwort.
        import getpass
        try:
            geheimnis = getpass.getpass("Geheimnis (bleibt verdeckt): ") or None
        except (EOFError, KeyboardInterrupt):
            geheimnis = None
    if geheimnis:
        datei = pfad or ausweisdatei()
        name = _pruefe(geheimnis, str(datei), _stand(datei))
        if name is not None:
            jetzt = jetzt or _jetzt()
            eintraege = _lies_datei(datei)
            eintrag = _finde(eintraege, name)
            # Ein abgelaufener Ausweis beglaubigt nicht mehr -- er wirft aber
            # auch keinen Fehler, sondern faellt in den unbeglaubigten Zweig.
            # Dieselbe Bauform wie beim falschen Geheimnis: nie mehr Rechte
            # als gar keiner, nie ein Abbruch, der Arbeit unmoeglich macht.
            if eintrag is not None and not _abgelaufen(eintrag.get("gilt_bis"), jetzt):
                geliehen, von = _mandatsrollen(eintrag, eintraege, jetzt, gegenstand)
                return Ausweis(
                    name=name,
                    rollen=tuple(sorted(set(eintrag.get("rollen", ())) | set(geliehen))),
                    beglaubigt=True,
                    # Ein Mandat hebt die Art NIE an: ein Maschinenausweis mit
                    # dem Mandat eines Menschen bleibt Maschine. Sonst waere
                    # das Mandat der Umweg zur Menschwerdung -- genau die
                    # Luecke, die `art` gerade geschlossen hat.
                    art=_art_von(eintrag),
                    mandat_von=von,
                    bedient_von=eintrag.get("bedient_von", ""),
                )

    name = argument or os.environ.get("BEGOD_KNOWLEDGE_ACTOR") or UNBEKANNT
    # Ein Argument, das das Praefix selbst mitbringt, darf es nicht doppelt
    # tragen -- und vor allem nicht so aussehen, als sei es echt geprueft.
    if name.startswith(UNBEGLAUBIGT):
        name = name[len(UNBEGLAUBIGT):] or UNBEKANNT
    return Ausweis(name=name, rollen=(), beglaubigt=False)


# --- Rechte ----------------------------------------------------------------

def bezug_fuer(ausweis: Ausweis, recht: str) -> str | None:
    """Gibt den Bezug zurueck, in dem `recht` gilt: 'alle', 'own',
    'published' -- oder None, wenn es gar nicht gilt.

    None statt False, weil der Aufrufer den Bezug BRAUCHT: 'darf lesen' ohne
    'welche' ist die halbe Antwort, und genau die Haelfte, an der ganz-oder-
    gar-nicht scheitert.

    Vorgabe ist DENY: wer keine Rolle hat, darf nichts. Ein unbeglaubigter
    Ausweis traegt nie Rollen."""
    modul, _, aktion = recht.partition(":")
    if not modul or not aktion:
        raise ValueError(f"Recht braucht die Form modul:aktion -- {recht!r}")
    bestes: str | None = None
    for rolle in ausweis.rollen:
        for eintrag in ROLLEN.get(rolle, ()):
            if eintrag == "*":
                gefunden = "alle"
            else:
                e_modul, _, rest = eintrag.partition(":")
                e_aktion, _, e_bezug = rest.partition(":")
                if e_modul != modul:
                    continue
                if e_aktion != "*" and e_aktion != aktion:
                    continue
                gefunden = e_bezug or "alle"
            if bestes is None or _BEZUG_WEITE[gefunden] > _BEZUG_WEITE[bestes]:
                bestes = gefunden
            if bestes == "alle":
                return "alle"
    return bestes


def darf(ausweis: Ausweis, recht: str) -> bool:
    """Kurzform fuer Faelle ohne Bezug (z.B. ein Werkzeug ganz sperren)."""
    return bezug_fuer(ausweis, recht) is not None


# --- Selbsttest ------------------------------------------------------------

def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "ausweise.json"
        # Gruendungsakt: der erste Ausweis entsteht ohne Aussteller. Alle
        # weiteren im Selbsttest gehen ueber ihn -- genau wie im Betrieb.
        G = anlegen("gruender", ["betreiber"], art="mensch", pfad=pfad)
        _a = lambda *ar, **kw: anlegen(*ar, aussteller=G, **kw)  # noqa: E731

        # --- P1: kein Ausweis -> Argument gilt, aber unbeglaubigt ----------
        a = loese_auf("betreiber", geheimnis=None, pfad=pfad)
        assert a.name == "betreiber" and not a.beglaubigt
        assert a.protokollname == "unbeglaubigt:betreiber"
        assert a.rollen == () and not darf(a, "wissen:schreiben"), \
            "unbeglaubigt darf nichts"

        # --- P2: DER Kern. Ausweis gewinnt, Argument ist stumm -------------
        g = _a("hausmeister", ["leser"], pfad=pfad)
        a = loese_auf("betreiber", geheimnis=g, pfad=pfad)
        assert a.name == "hausmeister", \
            f"Argument hat den Ausweis ueberstimmt: {a.name}"
        assert a.beglaubigt and a.protokollname == "hausmeister"

        # --- falsches Geheimnis gibt nie mehr als gar keines ---------------
        a = loese_auf("betreiber", geheimnis=g + "x", pfad=pfad)
        assert not a.beglaubigt and a.name == "betreiber"

        # --- Untergrabung: Praefix im Argument mitgeliefert -----------------
        a = loese_auf("unbeglaubigt:betreiber", geheimnis=None, pfad=pfad)
        assert a.protokollname == "unbeglaubigt:betreiber", a.protokollname
        a = loese_auf(UNBEGLAUBIGT, geheimnis=None, pfad=pfad)
        assert a.name == UNBEKANNT

        # --- Grenzwerte der Aufloesung -------------------------------------
        assert loese_auf(None, geheimnis=None, pfad=pfad).name == UNBEKANNT
        assert loese_auf("", geheimnis=None, pfad=pfad).name == UNBEKANNT
        # 'unbekannt' bekommt KEIN Praefix -- es gibt keine Behauptung, die
        # man als unbeglaubigt kennzeichnen koennte, und der Wert wird
        # anderswo verglichen (UNBEKANNTER_SCHREIBER).
        assert loese_auf(None, geheimnis=None, pfad=pfad).protokollname == UNBEKANNT
        assert loese_auf(UNBEKANNT, geheimnis=None, pfad=pfad).protokollname == UNBEKANNT
        assert loese_auf("x", geheimnis="", pfad=pfad).name == "x"

        # --- Env-Kette: Argument vor BEGOD_KNOWLEDGE_ACTOR, beide unbegl. ---
        alt = os.environ.get("BEGOD_KNOWLEDGE_ACTOR")
        os.environ["BEGOD_KNOWLEDGE_ACTOR"] = "aus-env"
        try:
            assert loese_auf(None, geheimnis=None, pfad=pfad).name == "aus-env"
            assert loese_auf("arg", geheimnis=None, pfad=pfad).name == "arg"
            # und auch die Env verliert gegen einen echten Ausweis
            assert loese_auf(None, geheimnis=g, pfad=pfad).name == "hausmeister"
        finally:
            if alt is None:
                del os.environ["BEGOD_KNOWLEDGE_ACTOR"]
            else:
                os.environ["BEGOD_KNOWLEDGE_ACTOR"] = alt

        # --- P4/P5/P6: Bezug ------------------------------------------------
        leser = loese_auf(geheimnis=g, pfad=pfad)
        assert bezug_fuer(leser, "wissen:lesen") == "alle"
        assert bezug_fuer(leser, "wissen:schreiben") is None, "Vorgabe ist deny"

        g2 = _a("gastnutzer", ["gast"], pfad=pfad)
        gast = loese_auf(geheimnis=g2, pfad=pfad)
        assert bezug_fuer(gast, "wissen:lesen") == "published"
        assert bezug_fuer(gast, "kante:lesen") is None

        g3 = _a("fachmann", ["fachkundig"], pfad=pfad)
        fach = loese_auf(geheimnis=g3, pfad=pfad)
        assert bezug_fuer(fach, "wissen:schreiben") == "own"
        assert bezug_fuer(fach, "wissen:lesen") == "alle"

        g4 = _a("chef", ["betreiber"], pfad=pfad)
        chef = loese_auf(geheimnis=g4, pfad=pfad)
        assert bezug_fuer(chef, "was:auch:immer".partition(":")[0] + ":lesen") == "alle"

        # --- Reihenfolge der Rollen darf das Ergebnis nicht aendern ---------
        g5 = _a("beides", ["gast", "leser"], pfad=pfad)
        g6 = _a("beides2", ["leser", "gast"], pfad=pfad)
        assert (bezug_fuer(loese_auf(geheimnis=g5, pfad=pfad), "wissen:lesen")
                == bezug_fuer(loese_auf(geheimnis=g6, pfad=pfad), "wissen:lesen")
                == "alle"), "weiterer Bezug muss gewinnen, unabhaengig von der Reihenfolge"

        # --- Art: Vorgabe maschine, Mensch nur ausdruecklich ---------------
        assert loese_auf(geheimnis=g, pfad=pfad).art == "maschine", \
            "Vorgabe muss maschine sein -- ein Ausweis landet in einer " \
            "Klientenkonfiguration, also bei einem Modell"
        assert not loese_auf(geheimnis=g, pfad=pfad).ist_mensch

        g7 = _a("markus", ["betreiber"], art="mensch", pfad=pfad)
        mensch = loese_auf(geheimnis=g7, pfad=pfad)
        assert mensch.ist_mensch and mensch.art == "mensch"

        # Ein UNbeglaubigter ist nie Mensch, egal wie er heisst -- sonst
        # genuegte ein Argument, um einer zu werden.
        assert not loese_auf("markus", geheimnis=None, pfad=pfad).ist_mensch

        # Altbestand ohne Feld 'art' wird nicht befoerdert.
        eintraege = _lies_datei(pfad)
        for e in eintraege:
            e.pop("art", None)
        _schreibe_datei(pfad, eintraege)
        assert loese_auf(geheimnis=g7, pfad=pfad).art == "maschine", \
            "fehlendes Feld darf niemanden zum Menschen machen"
        assert not loese_auf(geheimnis=g7, pfad=pfad).ist_mensch
        g7 = _a("markus", ["betreiber"], art="mensch", pfad=pfad)

        try:
            _a("x", ["leser"], art="halbgott", pfad=pfad)
        except ValueError:
            pass
        else:
            raise AssertionError("unbekannte Art haette abweisen muessen")

        # --- P7: Geheimnis steht nirgends im Klartext -----------------------
        roh = pfad.read_text(encoding="utf-8")
        for k in (g, g2, g3, g4):
            assert k not in roh, "Geheimnis im Klartext in der Ausweisdatei"

        # --- Dateirechte: zu weit -> ignoriert, nicht stillschweigend genutzt
        assert pfad.stat().st_mode & 0o777 == 0o600
        os.chmod(pfad, 0o644)
        assert not loese_auf(geheimnis=g, pfad=pfad).beglaubigt, \
            "weltlesbare Ausweisdatei darf niemanden beglaubigen"
        os.chmod(pfad, 0o600)
        assert loese_auf(geheimnis=g, pfad=pfad).beglaubigt

        # --- kaputte Datei beglaubigt niemanden -----------------------------
        kaputt = Path(tmp) / "kaputt.json"
        fd = os.open(kaputt, os.O_WRONLY | os.O_CREAT, 0o600)
        os.write(fd, b"{nicht json")
        os.close(fd)
        assert not loese_auf(geheimnis=g, pfad=kaputt).beglaubigt

        # --- fehlerhafte Anlage --------------------------------------------
        for name, rollen in (("x", ["gibtsnicht"]), ("", ["leser"]),
                             ("mit:doppelpunkt", ["leser"])):
            try:
                anlegen(name, rollen, pfad=pfad)
            except ValueError:
                pass
            else:
                raise AssertionError(f"haette abweisen muessen: {name} {rollen}")

        try:
            bezug_fuer(leser, "ohne-doppelpunkt")
        except ValueError:
            pass
        else:
            raise AssertionError("Recht ohne Aktion haette abweisen muessen")

    _selftest_mandat()
    _selftest_einbuergerung()
    _selftest_einladung()
    print("ausweis.py: Selbsttest gruen")


def _selftest_einladung() -> None:
    """PIN-Verfahren: der Mensch erzeugt, die Maschine loest ein."""
    import tempfile

    T0 = datetime(2026, 8, 10, 12, 0, 0, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "ausweise.json"
        G = anlegen("gruender", ["betreiber"], art="mensch", pfad=pfad)

        # --- der Mensch laedt ein, die Maschine loest ein -------------------
        pin = einladen("chatgpt", bedient_von="gruender", rollen=["leser"],
                       pfad=pfad, aussteller=G, jetzt=T0)
        assert len(pin) == PIN_LAENGE
        erg = einloesen(pin, pfad=pfad, jetzt=T0)
        assert erg["name"] == "chatgpt" and erg["bedient_von"] == "gruender"

        a = loese_auf(geheimnis=erg["geheimnis"], pfad=pfad)
        assert a.beglaubigt and a.name == "chatgpt"
        assert a.bedient_von == "gruender", a.bedient_von
        assert a.art == "maschine" and not a.ist_mensch, \
            "eine Einladung darf keine Maschine zum Menschen machen"
        assert bezug_fuer(a, "wissen:lesen") == "alle"
        assert bezug_fuer(a, "wissen:schreiben") is None

        # --- EINMALIG: dieselbe PIN ein zweites Mal ------------------------
        try:
            einloesen(pin, pfad=pfad, jetzt=T0)
        except PermissionError:
            pass
        else:
            raise AssertionError("PIN war mehrfach einloesbar")

        # --- BEFRISTET: Grenzwerte am Ablauf -------------------------------
        pin2 = einladen("bote", bedient_von="gruender", pfad=pfad,
                        aussteller=G, jetzt=T0)
        knapp = T0 + timedelta(minutes=EINLADUNG_GUELTIG_MINUTEN) - timedelta(seconds=1)
        genau = T0 + timedelta(minutes=EINLADUNG_GUELTIG_MINUTEN)
        assert einloesen(pin2, pfad=pfad, jetzt=knapp)["name"] == "bote"
        pin3 = einladen("bote2", bedient_von="gruender", pfad=pfad,
                        aussteller=G, jetzt=T0)
        for zeitpunkt in (genau, genau + timedelta(seconds=1)):
            try:
                einloesen(pin3, pfad=pfad, jetzt=zeitpunkt)
            except PermissionError:
                pass
            else:
                raise AssertionError(f"abgelaufene PIN galt bei {zeitpunkt}")

        # --- falsche PIN ---------------------------------------------------
        for falsch in ("", "XXXXXXXX", pin.lower()):
            try:
                einloesen(falsch, pfad=pfad, jetzt=T0)
            except PermissionError:
                pass
            else:
                raise AssertionError(f"falsche PIN ging durch: {falsch!r}")

        # --- Person und Zugang: der Zugang kann nie mehr als die Person ----
        anlegen("kleiner", ["leser"], art="mensch", pfad=pfad, aussteller=G)
        try:
            einladen("zuviel", bedient_von="kleiner", rollen=["betreiber"],
                     pfad=pfad, aussteller=G, jetzt=T0)
        except ValueError as f:
            assert "nie mehr als seine Person" in str(f), f
        else:
            raise AssertionError("Zugang bekam mehr Rechte als seine Person")
        # gedeckt: 'gast' liegt ganz unter 'leser'
        einladen("kleiner-gast", bedient_von="kleiner", rollen=["gast"],
                 pfad=pfad, aussteller=G, jetzt=T0)

        # --- bedient_von muss auf einen ECHTEN Menschen zeigen -------------
        for wer, wort in (("Erika Mustermann", "kein Ausweis"), ("chatgpt", "kein Mensch")):
            try:
                einladen("geist2", bedient_von=wer, pfad=pfad, aussteller=G,
                         jetzt=T0)
            except ValueError as f:
                assert wort in str(f), (wer, f)
            else:
                raise AssertionError(f"bedient_von={wer!r} ging durch")

        # --- wer einlaedt, muss einbuergern duerfen -------------------------
        g_les = anlegen("nurleser", ["leser"], pfad=pfad, aussteller=G)
        try:
            einladen("schmuggel", bedient_von="X", pfad=pfad, aussteller=g_les)
        except PermissionError as f:
            assert "darf keine Ausweise ausstellen" in str(f), f
        else:
            raise AssertionError("ein Leser konnte einladen")

        # --- ohne Menschen dahinter keine Einladung ------------------------
        for leer in ("", "   "):
            try:
                einladen("geist", bedient_von=leer, pfad=pfad, aussteller=G)
            except ValueError as f:
                assert "bedient_von" in str(f), f
            else:
                raise AssertionError("Einladung ohne Menschen ging durch")

        # --- die PIN steht nirgends im Klartext ----------------------------
        roh = (_einladungsdatei(pfad)).read_text(encoding="utf-8")
        assert pin not in roh and pin3 not in roh


def _selftest_einbuergerung() -> None:
    """Das Einbuergerungsamt: niemand tritt sich selbst bei."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "ausweise.json"

        # --- Gruendungsakt: der erste Ausweis geht ohne Aussteller ---------
        G = anlegen("gruender", ["betreiber"], art="mensch", pfad=pfad)
        assert loese_auf(geheimnis=G, pfad=pfad).beglaubigt

        # --- ab jetzt NICHT mehr: kein zweiter Selbsteintritt --------------
        try:
            anlegen("schlaubi", ["betreiber"], art="mensch", pfad=pfad)
        except PermissionError as f:
            assert "Gruendungsakt" in str(f), f
        else:
            raise AssertionError("Selbsteintritt nach der Gruendung ging durch")

        # --- HERKUNFT: jeder Eintrag sagt, wer ihn ausgestellt hat ---------
        eintraege = _lies_datei(pfad)
        gr = _finde(eintraege, "gruender")
        assert "gruendungsakt" in gr["ausgestellt_von"], gr.get("ausgestellt_von")
        assert gr.get("ausgestellt_am"), "kein Zeitpunkt am Gruendungsakt"

        # --- der Gruender darf einbuergern --------------------------------
        g_amt = anlegen("meldeamt1", ["meldeamt"], pfad=pfad, aussteller=G)
        g_les = anlegen("leser1", ["leser"], pfad=pfad, aussteller=G)

        # ... und ein spaeterer Eintrag nennt den Aussteller beim Namen
        nach = _finde(_lies_datei(pfad), "meldeamt1")
        assert nach["ausgestellt_von"] == "gruender", nach.get("ausgestellt_von")

        # --- das Meldeamt darf einbuergern, aber sonst nichts --------------
        anlegen("neubuerger", ["leser"], pfad=pfad, aussteller=g_amt)
        amt = loese_auf(geheimnis=g_amt, pfad=pfad)
        assert bezug_fuer(amt, "ausweis:ausstellen") == "alle"
        assert bezug_fuer(amt, "wissen:lesen") is None, \
            "Meldeamt darf nur einbuergern, nicht lesen"

        # --- ein Leser darf NICHT einbuergern ------------------------------
        try:
            anlegen("schwarzarbeiter", ["betreiber"], pfad=pfad, aussteller=g_les)
        except PermissionError as f:
            assert "darf keine Ausweise ausstellen" in str(f), f
        else:
            raise AssertionError("ein Leser konnte einbuergern")

        # --- ein FALSCHES Geheimnis buergert nicht ein ---------------------
        try:
            anlegen("geist", ["leser"], pfad=pfad, aussteller="erfunden")
        except PermissionError:
            pass
        else:
            raise AssertionError("falsches Geheimnis buergerte ein")

        # --- die Befugnis ist nicht weiterreichbar -------------------------
        try:
            anlegen("statthalter", ["leser"], pfad=pfad, aussteller=G,
                    mandat={"von": "meldeamt1", "rollen": ["meldeamt"],
                            "gegenstand": ["einbuergerung"]})
        except ValueError as f:
            assert "nicht delegierbar" in str(f), f
        else:
            raise AssertionError("ausweis:ausstellen war delegierbar")

        # --- die untere Schicht: haelt das Dateisystem ueberhaupt? ---------
        offen, grund = selbstbedienung_moeglich(pfad)
        assert offen, "im Test gehoert die Datei dem Prozess — das ist der Punkt"
        assert "selbstbedienung" in grund


def _selftest_mandat() -> None:
    """M1-M10 aus docs/DURCHSPIEL_BEZUGSGRUPPEN_2026-08-09.md, 8.6."""
    import tempfile

    T0 = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)
    iso = lambda d: d.isoformat()  # noqa: E731

    with tempfile.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "ausweise.json"
        # Gruendungsakt, dann buergert der Gruender ein -- wie im Betrieb.
        G = anlegen("gruender", ["betreiber"], art="mensch", pfad=pfad)
        _a = lambda *ar, **kw: anlegen(*ar, aussteller=G, **kw)  # noqa: E731

        g_chef = _a("chefin", ["schreiber"], art="mensch", pfad=pfad)
        g_bote = _a("bote", ["leser"], pfad=pfad,
                         mandat={"von": "chefin", "rollen": ["schreiber"],
                                 "gegenstand": ["abfallwirtschaft"]})

        # --- M5: ausserhalb des Gegenstands nur eigene Rechte, kein Abbruch --
        a = loese_auf(geheimnis=g_bote, pfad=pfad, jetzt=T0)
        assert a.rollen == ("leser",) and a.mandat_von is None
        assert bezug_fuer(a, "wissen:schreiben") is None

        # --- innerhalb: geliehenes Recht greift, Herkunft ist vermerkt -------
        a = loese_auf(geheimnis=g_bote, pfad=pfad, jetzt=T0,
                      gegenstand="abfallwirtschaft")
        assert set(a.rollen) == {"leser", "schreiber"}, a.rollen
        assert a.mandat_von == "chefin"
        assert bezug_fuer(a, "wissen:schreiben") == "alle"

        # --- M3: ein Mandat hebt die Art NIE an ------------------------------
        assert a.art == "maschine" and not a.ist_mensch, \
            "Mandat eines Menschen darf keine Maschine befoerdern"

        # --- M2: Mandant verliert das Recht -> Delegierter sofort auch -------
        _a("chefin", ["leser"], art="mensch", geheimnis=g_chef, pfad=pfad)
        a = loese_auf(geheimnis=g_bote, pfad=pfad, jetzt=T0,
                      gegenstand="abfallwirtschaft")
        assert a.rollen == ("leser",), \
            f"Schnitt wurde eingefroren statt zur Laufzeit gebildet: {a.rollen}"
        _a("chefin", ["schreiber"], art="mensch", geheimnis=g_chef, pfad=pfad)

        # --- M1: Mandat ueber ein Recht, das der Mandant nie hatte -----------
        try:
            _a("bote2", ["leser"], pfad=pfad,
                    mandat={"von": "chefin", "rollen": ["betreiber"],
                            "gegenstand": ["x"]})
        except ValueError as f:
            assert "nicht delegierbar" in str(f) or "hat selbst nicht" in str(f), f
        else:
            raise AssertionError("M1: haette abweisen muessen")

        # --- M4: Mandat ohne Gegenstand ist ein freies Mandat ----------------
        for kaputt in ({"von": "chefin", "rollen": ["schreiber"]},
                       {"von": "chefin", "rollen": ["schreiber"], "gegenstand": []}):
            try:
                _a("bote3", ["leser"], pfad=pfad, mandat=kaputt)
            except ValueError as f:
                assert "gegenstand" in str(f).lower(), f
            else:
                raise AssertionError("M4: freies Mandat haette abweisen muessen")

        # --- M8: nicht-delegierbares Recht ----------------------------------
        _a("gott", ["betreiber"], art="mensch", pfad=pfad)
        try:
            _a("statthalter", ["leser"], pfad=pfad,
                    mandat={"von": "gott", "rollen": ["betreiber"],
                            "gegenstand": ["alles"]})
        except ValueError as f:
            assert "nicht delegierbar" in str(f), f
        else:
            raise AssertionError("M8: haette abweisen muessen")

        # --- M9: Mandant gibt es gar nicht ----------------------------------
        try:
            _a("bote4", ["leser"], pfad=pfad,
                    mandat={"von": "niemand", "rollen": ["leser"],
                            "gegenstand": ["x"]})
        except ValueError as f:
            assert "kein Ausweis" in str(f), f
        else:
            raise AssertionError("M9: haette abweisen muessen")

        # --- M7: keine Weiterdelegation --------------------------------------
        try:
            _a("unterbote", ["leser"], pfad=pfad,
                    mandat={"von": "bote", "rollen": ["leser"],
                            "gegenstand": ["abfallwirtschaft"]})
        except ValueError as f:
            assert "Weiterdelegation" in str(f), f
        else:
            raise AssertionError("M7: haette abweisen muessen")

        # --- M6 + Grenzwerte am Ablauf ---------------------------------------
        ende = T0 + timedelta(hours=1)
        g_kurz = _a("zeitweise", ["leser"], pfad=pfad, gilt_bis=iso(ende))
        eine_sek = timedelta(seconds=1)
        assert loese_auf(geheimnis=g_kurz, pfad=pfad, jetzt=ende - eine_sek).beglaubigt
        # genau auf der Schwelle: abgelaufen. Ein Ablauf, der die Sekunde des
        # Endes noch gelten laesst, ist kein Ablauf, sondern eine Verlaengerung.
        assert not loese_auf(geheimnis=g_kurz, pfad=pfad, jetzt=ende).beglaubigt
        assert not loese_auf(geheimnis=g_kurz, pfad=pfad, jetzt=ende + eine_sek).beglaubigt
        # abgelaufen heisst unbeglaubigt, nicht Abbruch -- Arbeit bleibt moeglich
        a = loese_auf("zeitweise", geheimnis=g_kurz, pfad=pfad, jetzt=ende)
        assert a.protokollname == "unbeglaubigt:zeitweise" and a.rollen == ()

        # abgelaufenes MANDAT: Ausweis gilt weiter, Vollmacht nicht
        g_frist = _a("fristbote", ["leser"], pfad=pfad,
                          mandat={"von": "chefin", "rollen": ["schreiber"],
                                  "gegenstand": ["abfallwirtschaft"],
                                  "gilt_bis": iso(ende)})
        a = loese_auf(geheimnis=g_frist, pfad=pfad, jetzt=ende,
                      gegenstand="abfallwirtschaft")
        assert a.beglaubigt and a.rollen == ("leser",) and a.mandat_von is None

        # M9 zur Laufzeit: Mandant laeuft ab -> Vollmacht faellt mit ihm
        _a("chefin", ["schreiber"], art="mensch", geheimnis=g_chef,
                pfad=pfad, gilt_bis=iso(ende))
        a = loese_auf(geheimnis=g_bote, pfad=pfad, jetzt=ende,
                      gegenstand="abfallwirtschaft")
        assert a.rollen == ("leser",), \
            "abgelaufener Mandant darf keine Vollmacht mehr tragen"

        # kaputtes Datum gilt als abgelaufen, nicht als unbefristet
        eintraege = _lies_datei(pfad)
        _finde(eintraege, "zeitweise")["gilt_bis"] = "morgen frueh"
        _schreibe_datei(pfad, eintraege)
        assert not loese_auf(geheimnis=g_kurz, pfad=pfad, jetzt=T0).beglaubigt, \
            "unlesbares Ablaufdatum darf keinen unbegrenzten Zugang erzeugen"

        # --- M10: Rotation -- der alte Ausweis muss scheitern -----------------
        g_alt = _a("sprecher", ["schreiber"], pfad=pfad)
        g_neu = _a("sprecher", ["schreiber"], pfad=pfad)
        assert loese_auf(geheimnis=g_neu, pfad=pfad, jetzt=T0).beglaubigt
        assert not loese_auf(geheimnis=g_alt, pfad=pfad, jetzt=T0).beglaubigt, \
            "M10: nach der Rotation gilt das alte Geheimnis weiter"

        # --- von Hand geschriebene Datei: die Laufzeitschranke haelt ----------
        eintraege = _lies_datei(pfad)
        eintraege.append({**_finde(eintraege, "bote"), "name": "schlaubi",
                          "mandat": {"von": "chefin", "rollen": ["betreiber"],
                                     "gegenstand": ["abfallwirtschaft"]}})
        _schreibe_datei(pfad, eintraege)
        a = loese_auf(geheimnis=g_bote, pfad=pfad, jetzt=T0,
                      gegenstand="abfallwirtschaft")
        assert "betreiber" not in a.rollen, \
            "handgeschriebenes Mandat umging den Laufzeitschnitt"

        # ... und die KETTE von Hand. anlegen() weist sie ab, aber die Datei
        # kann jemand von Hand schreiben -- die Laufzeitschranke muss halten.
        #
        # WICHTIG fuer die Konstruktion dieser Probe: unterbote muss ein Recht
        # wollen, das bote SELBST hat ('leser'), nicht eines, das bote nur
        # geliehen hat ('schreiber'). Geliehenes faengt schon der Schnitt gegen
        # die eigenen Rollen des Mandanten ab -- eine Probe darauf ist blind
        # und war es auch: die erste Fassung blieb unter Mutation gruen
        # (Mutationsprobe 2026-08-09, einzige von sechs). Erst am eigenen Recht
        # des Delegierten wird die Kettenschranke ueberhaupt beobachtbar.
        eintraege = _lies_datei(pfad)
        g_unter = "geheimnis-unterbote"
        salz = secrets.token_bytes(16)
        eintraege.append({
            "name": "unterbote", "art": "maschine", "rollen": [],
            "salz": salz.hex(), "hash": _ableiten(g_unter, salz).hex(),
            "kdf": {"art": "scrypt", "n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P},
            "mandat": {"von": "bote", "rollen": ["leser"],
                       "gegenstand": ["abfallwirtschaft"]},
        })
        _schreibe_datei(pfad, eintraege)
        a = loese_auf(geheimnis=g_unter, pfad=pfad, jetzt=T0,
                      gegenstand="abfallwirtschaft")
        assert a.beglaubigt and a.rollen == (), \
            f"Weiterdelegation ueber zwei Stufen ging durch: {a.rollen}"


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--anlegen", metavar="NAME")
    p.add_argument("--art", default="maschine", choices=list(ARTEN),
                   help="mensch nur fuer echte Personen — siehe ARTEN")
    p.add_argument("--rollen", default="leser",
                   help=f"kommagetrennt, bekannt: {','.join(sorted(ROLLEN))}")
    p.add_argument("--einladen", metavar="NAME",
                   help="PIN fuer eine Anmeldung erzeugen (einmalig, befristet)")
    p.add_argument("--fuer", metavar="MENSCH",
                   help="wer diese Einladung verantwortet")
    p.add_argument("--liste", action="store_true")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--datei", type=Path, default=None)
    args = p.parse_args()

    if args.selftest:
        _selftest()
        return 0

    pfad = args.datei or ausweisdatei()

    if args.anlegen:
        offen, grund = selbstbedienung_moeglich(pfad)
        if offen and args.art == "mensch":
            # Kein Abbruch -- solange die Trennung fehlt, waere ein Verbot hier
            # nur Zeremonie (wer das Skript aendern kann, hebt es auf). Aber die
            # Zeile MUSS fallen: ein Menschenausweis, der ohne jede Huerde
            # entsteht, darf nicht so aussehen, als haette er eine genommen.
            print(f"WARNUNG: {grund}\n"
                  f"  Ein Ausweis mit art=mensch entsteht hier ohne Huerde. "
                  f"Solange das so ist, belegt 'mensch' die HERKUNFT, nicht die "
                  f"Eigenschaft.\n"
                  f"  Echte Trennung: sudo chown root {pfad} && sudo chmod 644 "
                  f"{pfad} — danach verlangt jedes Anlegen dein Passwort.\n",
                  file=sys.stderr)
        geheimnis = anlegen(args.anlegen, args.rollen.split(","),
                            art=args.art, pfad=pfad)
        print(f"Ausweis '{args.anlegen}' angelegt in {pfad} (Rechte 600).")
        print("\nDas Geheimnis steht genau EINMAL hier. Es wird nicht "
              "gespeichert, nur sein Hash:\n")
        print(f"    {geheimnis}\n")
        print("Eintragen beim Klienten, nicht im Gespraech -- in ~/.claude.json "
              "unter mcpServers.knowledge.env:")
        print(f'    "{ENV_GEHEIMNIS}": "{geheimnis}"')
        return 0

    if args.einladen:
        if not args.fuer:
            p.error("--einladen braucht --fuer \"<Name des Menschen>\"")
        pin = einladen(args.einladen, bedient_von=args.fuer,
                       rollen=args.rollen.split(","), art=args.art, pfad=pfad)
        print(f"\nEinladung fuer '{args.einladen}', verantwortet von {args.fuer}")
        print(f"Rollen: {args.rollen}   Art: {args.art}")
        print(f"gueltig {EINLADUNG_GUELTIG_MINUTEN} Minuten, EINMALIG\n")
        print(f"    Anmeldename: {args.einladen}")
        print(f"    PIN:         {pin}\n")
        print("Diese PIN weitergeben (Chat, E-Mail, Zuruf) — der Empfaenger "
              "loest sie mit dem Werkzeug knowledge_anmelden ein und erhaelt\n"
              "dabei sein Geheimnis. Danach ist die PIN verbraucht.")
        return 0

    if args.liste:
        eintraege = _lies_datei(pfad)
        if not eintraege:
            print(f"Keine Ausweise in {pfad}.")
        for e in eintraege:
            print(f"{e['name']:20s} {','.join(e.get('rollen', []))}")
        return 0

    aktuell = loese_auf()
    print(f"Aufgeloest: {aktuell.protokollname}  Rollen: "
          f"{','.join(aktuell.rollen) or '-'}  "
          f"beglaubigt: {'ja' if aktuell.beglaubigt else 'nein'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
