#!/usr/bin/env python3
"""Ein Melder auf die BINDUNG zwischen Plan und Speicher -- S: Plandateien
(docs/PLAN_*.md), Beleg fuer diese eine: docs/PLAN_DESTILLE_2026-08-09.md.

Anlass: Der Plan legt in seinem eigenen Kopf fest, dass eine Entscheidung
erst bindend ist, wenn ihr Abschnitt eine Knotenkennung nennt -- fehlt sie,
ist die Entscheidung "noch nicht bindend abgelegt". Gemessen 2026-08-09:
nur 4 von 18 Abschnitten in PLAN_DESTILLE_2026-08-09.md nennen eine
Kennung. "Query-Rewriting" stand dreimal als bekannter Rueckstand im Plan,
ohne Knoten dazu -- der Speicher konnte nicht widersprechen, als dieselbe
Sache Stunden spaeter neu erfunden wurde. Ein Plan, der nur in einer Datei
steht, ist fuer das eigene System unsichtbar.

Zwei Fehlklassen, unterschiedlich schwer:

  1. FEHLENDE KENNUNG -- ein Abschnitt behauptet nichts, was der Speicher
     pruefen koennte. Leichter Befund: der Plan hat es (noch) nicht
     abgelegt, das ist der Normalfall vor der Bindung.
  2. PHANTOM-KENNUNG -- ein Abschnitt nennt eine Kennung, zu der KEIN
     Knoten existiert. Schwerer Befund: der Plan behauptet eine Ablage,
     die es nicht gibt -- das ist kein fehlender Schritt, sondern eine
     falsche Angabe.

Dieselben drei Auflagen wie `pruefer.py` und `arbeitsmelder.py`:

  1. MESSBAR aus dem Bestand: ein Abschnitt zaehlt als geprueft, wenn eine
     im Text stehende 8-stellige Hexfolge tatsaechlich als `id` in
     `knowledge_nodes` existiert (Abgleich per Praefix, `id LIKE
     '<kennung>%'`) -- keine Stimmung, ein SQL-Ergebnis.
  2. FEHLKLASSE benannt: "fehlende Kennung" (leicht) und "Phantom-Kennung"
     (schwer), siehe oben -- kein Befund ohne diese Zuordnung.
  3. PREIS EINES FEHLALARMS: fuer "fehlende Kennung" gering -- der
     Abschnitt wird zurecht so lange genannt, bis jemand die Kennung
     eintraegt, kein Handeln erzwungen. Fuer "Phantom-Kennung" hoeher --
     eine falsch gelesene Kennung (z.B. abgeschnittene Backtick-Markierung)
     erzeugt einen Befund, der nach geloeschtem Knoten aussieht, obwohl nur
     der Regex daneben lag. Darum wird die Kennung im Befund IMMER woertlich
     mitgenannt -- der Leser kann sie in Sekunden selbst nachschlagen.

Und er schweigt, wenn nichts anschlaegt.

Aufruf:
    python3 planbindung.py             # alle Plandateien, ausfuehrlich
    python3 planbindung.py --melder    # nur sprechen, wenn etwas anschlaegt
    python3 planbindung.py --selftest
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

import argparse
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

WURZEL = _w

# Abschnittskopf: am Material gemessen (2026-08-12) tragen die zwoelf
# Plandateien FUENF verschiedene Kennungsschemata, nicht nur "### S<n>":
#   S1, S1b, S2 ...           (PLAN_DESTILLE, PLAN_DREITEILUNG -- ## UND ###)
#   P1, P4, P11 ...           (PLAN_ABARBEITUNG)
#   B4.1, B4.4b ...           (PLAN_B4_AUSWEIS)
#   §0, §1 ... / 1., 5b. ...  (PLAN_FREMDLAGE/KLIENTENDOKU/WURZELORDNUNG bzw.
#                              PLAN_B4_AUSWEIS/PLAN_B5_FOEDERATION)
#   Linie A, Linie B, Linie C (PLAN_GESAMT)
# Der alte Regex sah nur "### S<n>" -- das traf 23 von 139 Ueberschriften,
# verteilt auf genau eine Datei (Befund 2026-08-12, Lehre L-65d33e). Zwei
# Aenderungen gegenueber vorher: (1) ## UND ### erlaubt (PLAN_DREITEILUNG
# nutzt "## S1 · ..." auf Ebene 2, nicht 3), (2) alle fuenf Schemata.
# Trenner bleibt optional wie zuvor -- manche Kopfzeilen ("§0 Gemessener
# Ist-Stand", "### S12 ist kein Forschungsschritt mehr, ...") haben keinen
# "·"/"—", nur ein Leerzeichen zwischen Kennung und Titel.
_HEADER_RE = re.compile(
    r"^#{2,3}\s+"
    r"(§\d+|S\d+[a-z]?|P\d+|B4\.\d+[a-z]?|Linie\s[A-Z]|\d+[a-z]?\.)"
    r"(?:\s*(?:·|—)\s*|\s+)(.*)$"
)

# Ueberschriften OHNE Kennungsschema (reine Prosa-Titel wie "## Was bewusst
# nicht getan wird") sind weiterhin gueltige ABSCHNITTSGRENZEN (s.u.
# _JEDE_UEBERSCHRIFT_RE), zaehlen aber nicht als pruefbarer Abschnitt -- sie
# behaupten keine S<n>-artige Einzelentscheidung, die eine Kennung tragen
# koennte. Eine Datei, in der KEINE einzige Ueberschrift dieses Schema
# benutzt, hat keine pruefbare Abschnittsstruktur (siehe DATEIEN_OHNE_STRUKTUR).

# Knotenkennung: 8-stellige Hexfolge. \b reicht als Grenze -- Lehren-IDs
# ("L-502be0") haben nur 6 Hexstellen nach dem Praefix und passen nicht,
# Commit-Hashes im Kurzformat ("577a774") haben 7.
_KENNUNG_RE = re.compile(r"\b[0-9a-fA-F]{8}\b")


@dataclass
class Abschnitt:
    datei: str
    kennung: str  # "S1", "S1b", ...
    titel: str
    text: str


@dataclass
class Befund:
    art: str  # "fehlende_kennung" | "phantom_kennung"
    datei: str
    abschnitt: str
    titel: str
    kennungen: list[str] = field(default_factory=list)


_JEDE_UEBERSCHRIFT_RE = re.compile(r"^#{2,3} ")


def _lies_zeilen(datei: Path) -> list[str] | None:
    """None statt Ausnahme -- der Aufrufer entscheidet, ob eine unlesbare
    Datei ein stiller Nenner-Abzug oder ein gemeldeter Befund ist. Ohne
    dieses Signal wuerde ein Encoding-Fehler die Datei genauso stumm
    uebergehen wie eine Datei ohne Abschnittscode, und genau die Verwechslung
    soll dieser Melder nicht mehr machen."""
    try:
        return datei.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None


def _abschnitte_aus_zeilen(datei_name: str, zeilen: list[str]) -> list[Abschnitt]:
    """Ein Abschnitt endet an der naechsten UEBERSCHRIFT jeder Art, nicht
    erst am naechsten Kopf mit erkannter Kennung. Sonst schluckt ein
    Abschnitt jede Zwischenueberschrift ohne Kennung (z.B. "### Einwand des
    Betreibers ...") samt ihres Texts -- gemessen an
    PLAN_DESTILLE_2026-08-09.md: ohne diese Grenze haengt `b6305304` aus
    einem sechs Abschnitte spaeter liegenden Unterkapitel faelschlich am
    zweiten "S12"-Kopf."""
    grenzen = [i for i, z in enumerate(zeilen) if _JEDE_UEBERSCHRIFT_RE.match(z)]
    treffer = [(i, m) for i in grenzen if (m := _HEADER_RE.match(zeilen[i]))]
    ergebnis = []
    for start, m in treffer:
        folgende = [g for g in grenzen if g > start]
        ende = folgende[0] if folgende else len(zeilen)
        text = "\n".join(zeilen[start:ende])
        ergebnis.append(Abschnitt(datei=datei_name, kennung=m.group(1),
                                   titel=m.group(2).strip(), text=text))
    return ergebnis


def _abschnitte(datei: Path) -> list[Abschnitt]:
    zeilen = _lies_zeilen(datei)
    return [] if zeilen is None else _abschnitte_aus_zeilen(datei.name, zeilen)


_AUSSCHLUSSGRUND = (
    "nur Prosa-Ueberschriften, kein Abschnittscode (S<n>/P<n>/B4.<n>/"
    "§<n>/Linie <X>/<n>.) -- kein pruefbarer Abschnitt"
)


@dataclass
class Erhebung:
    """Nenner UND Ausnahmen in einem Objekt, damit keine Ausgabefunktion
    eine Datei stillschweigend uebergehen kann, ohne dass es hier auffiele."""
    abschnitte: list[Abschnitt]
    ueberschriften_gesamt: int
    ausgeschlossen: list[tuple[str, str, int]]  # (datei, grund, ueberschriften_in_datei)
    nicht_lesbar: list[str]


def _erheben(plan_dateien: list[Path]) -> Erhebung:
    abschnitte: list[Abschnitt] = []
    ueberschriften_gesamt = 0
    ausgeschlossen: list[tuple[str, str, int]] = []
    nicht_lesbar: list[str] = []
    for datei in plan_dateien:
        zeilen = _lies_zeilen(datei)
        if zeilen is None:
            nicht_lesbar.append(datei.name)
            continue
        n_ueberschriften = sum(1 for z in zeilen if _JEDE_UEBERSCHRIFT_RE.match(z))
        ueberschriften_gesamt += n_ueberschriften
        ab = _abschnitte_aus_zeilen(datei.name, zeilen)
        abschnitte.extend(ab)
        if n_ueberschriften > 0 and not ab:
            ausgeschlossen.append((datei.name, _AUSSCHLUSSGRUND, n_ueberschriften))
    return Erhebung(abschnitte, ueberschriften_gesamt, ausgeschlossen, nicht_lesbar)


def _ausschluss_zeile(ausgeschlossen: list[tuple[str, str, int]]) -> str:
    """Eine Zeile fuer BEIDE Ausgabemodi -- Befund 2026-08-12: die erste
    Fassung nannte ausgeschlossene Dateien nur in --ausfuehrlich, nicht in
    --melder. Ein Leser der Startmeldung ("56 von 79") hielt 79 fuer die
    Gesamtzahl -- derselbe Mechanismus wie beim alten "### S<n>"-Regex,
    nur eine Ebene hoeher. Eine gemeinsame Zeile verhindert, dass die
    beiden Ausgaben wieder auseinanderlaufen."""
    n = len(ausgeschlossen)
    ueberschriften = sum(u for _, _, u in ausgeschlossen)
    namen = ", ".join(d for d, _, _ in ausgeschlossen)
    gruende = {g for _, g, _ in ausgeschlossen}
    grund = next(iter(gruende)) if len(gruende) == 1 else "siehe Einzelbegruendung unten"
    return (f"{n} Datei(en) mit {ueberschriften} Ueberschriften nicht pruefbar "
            f"({grund}): {namen}")


def _vorhandene_ids(conn: sqlite3.Connection) -> list[str]:
    return [r[0].lower() for r in conn.execute("SELECT id FROM knowledge_nodes").fetchall()]


def _existiert(kennung: str, ids: list[str]) -> bool:
    k = kennung.lower()
    return any(i.startswith(k) for i in ids)


def pruefen(abschnitte: list[Abschnitt], conn: sqlite3.Connection) -> list[Befund]:
    ids = _vorhandene_ids(conn)
    befunde: list[Befund] = []
    for ab in abschnitte:
        gefunden = list(dict.fromkeys(_KENNUNG_RE.findall(ab.text)))
        if not gefunden:
            befunde.append(Befund("fehlende_kennung", ab.datei, ab.kennung, ab.titel))
            continue
        phantome = [k for k in gefunden if not _existiert(k, ids)]
        if phantome:
            befunde.append(Befund("phantom_kennung", ab.datei, ab.kennung, ab.titel, phantome))
        # sonst: mindestens eine gueltige Kennung -> still (Pflichtfall a)
    return befunde


DECKEL = 5


def _melden(befunde: list[Befund], erhebung: Erhebung) -> None:
    # Uebergangene Dateien sind selbst ein Anschlag -- eine Datei, die
    # stillschweigend uebersprungen wird, ist derselbe Fehler wie ein
    # Abschnitt ohne Kennung, nur unbemerkter (Befund 2026-08-12: die
    # erste Fassung nannte ausgeschlossene Dateien nur in --ausfuehrlich,
    # ein --melder-Leser hielt "56 von 79" faelschlich fuer die
    # Gesamtzahl). Darum bricht jede der drei Ausnahmeklassen die Stille.
    if not befunde and not erhebung.nicht_lesbar and not erhebung.ausgeschlossen:
        return
    geprueft = len(erhebung.abschnitte)
    if befunde:
        # Phantom-Kennungen zuerst -- der schwerere Befund soll nicht vom
        # Deckel abgeschnitten werden, wenn es zu viele leichte gibt.
        schwer = [b for b in befunde if b.art == "phantom_kennung"]
        leicht = [b for b in befunde if b.art == "fehlende_kennung"]
        geordnet = schwer + leicht

        gesamt = len(geordnet)
        print(f"{gesamt} von {geprueft} Abschnitten ohne bindende Ablage "
              f"({erhebung.ueberschriften_gesamt} Ueberschriften insgesamt gesichtet):")
        gezeigt = geordnet[:DECKEL]
        for b in gezeigt:
            if b.art == "phantom_kennung":
                print(f"PHANTOM-KENNUNG  {b.datei} · {b.abschnitt} · {b.titel}  "
                      f"-- nennt {', '.join(b.kennungen)}, kein Knoten dazu")
            else:
                print(f"fehlende Kennung {b.datei} · {b.abschnitt} · {b.titel}")
        rest = gesamt - len(gezeigt)
        if rest > 0:
            print(f"... und {rest} weitere Abschnitt(e) ohne bindende Ablage")
    elif erhebung.nicht_lesbar or erhebung.ausgeschlossen:
        print(f"{geprueft} von {geprueft} geprueften Abschnitten mit gueltiger Kennung oder ohne Anspruch "
              f"({erhebung.ueberschriften_gesamt} Ueberschriften insgesamt gesichtet)")
    if erhebung.ausgeschlossen:
        print(_ausschluss_zeile(erhebung.ausgeschlossen))
    if erhebung.nicht_lesbar:
        print(f"{len(erhebung.nicht_lesbar)} Datei(en) nicht lesbar: {', '.join(erhebung.nicht_lesbar)}")


def _ausfuehrlich(befunde: list[Befund], erhebung: Erhebung) -> None:
    geprueft = len(erhebung.abschnitte)
    if not befunde:
        print(f"{geprueft} Abschnitte geprueft, alle mit gueltiger Kennung oder ohne Anspruch.")
    else:
        print(f"{len(befunde)} von {geprueft} Abschnitten ohne bindende Ablage:")
        for b in befunde:
            if b.art == "phantom_kennung":
                print(f"  PHANTOM  {b.datei} · {b.abschnitt} · {b.titel} -- "
                      f"nennt {', '.join(b.kennungen)}, kein Knoten dazu")
            else:
                print(f"  fehlt    {b.datei} · {b.abschnitt} · {b.titel}")
    print(f"({erhebung.ueberschriften_gesamt} Ueberschriften insgesamt gesichtet, "
          f"{geprueft} davon mit Abschnittscode pruefbar)")
    if erhebung.ausgeschlossen:
        print(_ausschluss_zeile(erhebung.ausgeschlossen) + ":")
        for name, grund, n_ueb in erhebung.ausgeschlossen:
            print(f"  {name} ({n_ueb} Ueberschriften) -- {grund}")
    if erhebung.nicht_lesbar:
        print(f"{len(erhebung.nicht_lesbar)} Datei(en) nicht lesbar: {', '.join(erhebung.nicht_lesbar)}")


def _connection(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _echte_db_pfad() -> Path:
    sys.path.insert(0, str(WURZEL / "haken"))
    import ort  # noqa: E402
    return ort.DB


# ---------------------------------------------------------------------------
# Selbsttest -- eigene Beispieldateien in einem temporaeren Verzeichnis,
# kein Zugriff auf den echten Plan, keine Schreibung in die echte DB.
# ---------------------------------------------------------------------------

def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        db_pfad = tmp / "test.db"
        conn_rw = sqlite3.connect(db_pfad)
        conn_rw.execute("CREATE TABLE knowledge_nodes (id TEXT PRIMARY KEY)")
        conn_rw.executemany(
            "INSERT INTO knowledge_nodes (id) VALUES (?)",
            [("aaaa1111",), ("bbbb2222",)],
        )
        conn_rw.commit()
        conn_rw.close()
        conn = _connection(db_pfad)

        plan = tmp / "PLAN_TEST.md"
        plan.write_text(
            "### S1 · hat gueltige Kennung\n"
            "Text mit Knoten `aaaa1111` belegt.\n\n"
            "### S2 · hat keine Kennung\n"
            "Nur Prosa, nichts abgelegt.\n\n"
            "### S3 · hat Phantom-Kennung\n"
            "Verweist auf `ffffffff`, den es nicht gibt.\n",
            encoding="utf-8",
        )

        # ROT: vor dem Bau existierte `pruefen` nicht -- der Aufruf haette
        # mit AttributeError/NameError abgebrochen. Hier woertlich als
        # Kommentar festgehalten, weil ein rot gelaufener Aufruf sich nicht
        # nachtraeglich reproduzieren laesst, ohne den Code zu entfernen:
        #   NameError: name 'pruefen' is not defined
        # Ab hier die GRUEN-Probe gegen den fertigen Code.
        erhebung = _erheben([plan])
        befunde = pruefen(erhebung.abschnitte, conn)

        arten = {(b.abschnitt, b.art) for b in befunde}
        assert ("S1", "fehlende_kennung") not in arten, "Pflichtfall (a) verletzt: S1 haette schweigen muessen"
        assert ("S1", "phantom_kennung") not in arten, "Pflichtfall (a) verletzt: S1 haette schweigen muessen"
        assert ("S2", "fehlende_kennung") in arten, "Pflichtfall (b) verletzt: S2 haette gemeldet werden muessen"
        assert ("S3", "phantom_kennung") in arten, "Pflichtfall (c) verletzt: S3 haette als Phantom gemeldet werden muessen"
        assert len(befunde) == 2, f"erwartet 2 Befunde (S2, S3), bekommen {len(befunde)}"
        print("Pflichtfaelle a/b/c: bestanden")

        # (d) Deckel: 6 fehlende Abschnitte -> 5 genannt, Rest ausgewiesen
        viele = "\n\n".join(f"### S{i} · Abschnitt {i}\nkein Beleg" for i in range(6))
        plan_deckel = tmp / "PLAN_DECKEL.md"
        plan_deckel.write_text(viele, encoding="utf-8")
        erhebung_deckel = _erheben([plan_deckel])
        befunde_deckel = pruefen(erhebung_deckel.abschnitte, conn)
        assert len(befunde_deckel) == 6, f"erwartet 6 fehlende Abschnitte, bekommen {len(befunde_deckel)}"

        import io
        from contextlib import redirect_stdout
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            _melden(befunde_deckel, erhebung_deckel)
        ausgabe = puffer.getvalue()
        gezeigte_zeilen = [z for z in ausgabe.splitlines() if z.startswith("fehlende Kennung")]
        assert len(gezeigte_zeilen) == 5, f"Deckel haette 5 zeigen sollen, zeigte {len(gezeigte_zeilen)}"
        assert "1 weitere" in ausgabe, f"Restzahl fehlt in Ausgabe: {ausgabe!r}"
        assert "6 von 6 Abschnitten" in ausgabe, f"Nenner fehlt im --melder-Kopf: {ausgabe!r}"
        print("Pflichtfall d (Deckel bei 6, Nenner im --melder-Kopf): bestanden")

        # (e) Negativfall: alle Abschnitte mit gueltiger Kennung -> keine Ausgabe
        plan_ok = tmp / "PLAN_OK.md"
        plan_ok.write_text(
            "### S1 · alles belegt\nSiehe `aaaa1111`.\n\n"
            "### S2 · auch belegt\nSiehe `bbbb2222`.\n",
            encoding="utf-8",
        )
        erhebung_ok = _erheben([plan_ok])
        befunde_ok = pruefen(erhebung_ok.abschnitte, conn)
        assert befunde_ok == [], f"Negativfall haette leer sein muessen, bekommen {befunde_ok}"
        puffer2 = io.StringIO()
        with redirect_stdout(puffer2):
            _melden(befunde_ok, erhebung_ok)
        assert puffer2.getvalue() == "", "Negativfall haette --melder stumm lassen muessen"
        print("Pflichtfall e (Negativfall): bestanden")

        # (f) Breite der Kennungsschemata: alle fuenf Formen aus dem
        # Material (S/P/B4./§/Linie/nummeriert) muessen als Abschnitt
        # erkannt werden, auf ## UND ### Ebene -- nicht nur "### S<n>".
        # ROT gegen den alten Code: der alte _HEADER_RE (nur "### S<n>")
        # haette hier 1 von 6 gesehen (S1), nicht 6 von 6.
        plan_formen = tmp / "PLAN_FORMEN.md"
        plan_formen.write_text(
            "## S1 · S-Form auf Ebene 2\nBeleg `aaaa1111`.\n\n"
            "### P4 · P-Form\nBeleg `aaaa1111`.\n\n"
            "### B4.2 — B4-Form\nBeleg `aaaa1111`.\n\n"
            "## §3 Paragraph-Form ohne Trenner\nBeleg `aaaa1111`.\n\n"
            "## Linie A · Linie-Form\nBeleg `aaaa1111`.\n\n"
            "## 5b. Nummerierte Form\nBeleg `aaaa1111`.\n",
            encoding="utf-8",
        )
        erhebung_formen = _erheben([plan_formen])
        kennungen_gesehen = {ab.kennung for ab in erhebung_formen.abschnitte}
        assert kennungen_gesehen == {"S1", "P4", "B4.2", "§3", "Linie A", "5b."}, (
            f"Formenbreite unvollstaendig, gesehen: {kennungen_gesehen}")
        assert len(erhebung_formen.abschnitte) == 6, (
            f"erwartet 6 erkannte Abschnitte ueber alle Formen, bekommen {len(erhebung_formen.abschnitte)}")
        print("Pflichtfall f (Formenbreite S/P/B4./§/Linie/nummeriert, ## und ###): bestanden")

        # (g) Datei ohne pruefbare Struktur -- explizit ausgeschlossen, nicht
        # stillschweigend uebergangen. Ueberschriften vorhanden, aber keine
        # traegt eine Kennung.
        plan_prosa = tmp / "PLAN_PROSA.md"
        plan_prosa.write_text(
            "## Gemessener Ist-Stand\nNur Prosa.\n\n"
            "## Was bewusst nicht getan wird\nAuch nur Prosa.\n",
            encoding="utf-8",
        )
        erhebung_prosa = _erheben([plan_prosa])
        assert erhebung_prosa.abschnitte == [], "Prosa-Datei haette keine Abschnitte liefern duerfen"
        assert erhebung_prosa.ausgeschlossen == [("PLAN_PROSA.md", _AUSSCHLUSSGRUND, 2)], (
            f"Prosa-Datei haette namentlich mit Ueberschriftenzahl ausgeschlossen werden muessen: "
            f"{erhebung_prosa.ausgeschlossen}")
        print("Pflichtfall g (Datei ohne pruefbare Struktur, explizit ausgeschlossen): bestanden")

        # (g2) ROT gegen den Stand vom 2026-08-12 (erste Fassung dieses
        # Melders): --melder nannte ausgeschlossene Dateien NICHT, weder
        # allein noch neben echten Befunden -- ein Leser von "N von M
        # Abschnitten" hielt M faelschlich fuer die Gesamtzahl. Zwei Faelle:
        # nur eine ausgeschlossene Datei (keine Befunde), und eine
        # ausgeschlossene Datei NEBEN einem echten Befund.
        puffer_nur_prosa = io.StringIO()
        with redirect_stdout(puffer_nur_prosa):
            _melden([], erhebung_prosa)
        ausgabe_nur_prosa = puffer_nur_prosa.getvalue()
        assert "PLAN_PROSA.md" in ausgabe_nur_prosa, (
            f"--melder haette die ausgeschlossene Datei nennen muessen (ohne Befunde): {ausgabe_nur_prosa!r}")
        assert "2 Ueberschriften" in ausgabe_nur_prosa, (
            f"--melder haette die Ueberschriftenzahl der ausgeschlossenen Datei nennen muessen: {ausgabe_nur_prosa!r}")

        plan_mix_befund = tmp / "PLAN_MIX.md"
        plan_mix_befund.write_text("### S1 · ohne Kennung\nNur Prosa.\n", encoding="utf-8")
        erhebung_mix = _erheben([plan_mix_befund, plan_prosa])
        befunde_mix = pruefen(erhebung_mix.abschnitte, conn)
        assert len(befunde_mix) == 1, f"erwartet 1 Befund (S1), bekommen {len(befunde_mix)}"
        puffer_mix = io.StringIO()
        with redirect_stdout(puffer_mix):
            _melden(befunde_mix, erhebung_mix)
        ausgabe_mix = puffer_mix.getvalue()
        assert "fehlende Kennung" in ausgabe_mix, f"Befund fehlt in Mix-Ausgabe: {ausgabe_mix!r}"
        assert "PLAN_PROSA.md" in ausgabe_mix, (
            f"ausgeschlossene Datei fehlt in --melder NEBEN einem echten Befund: {ausgabe_mix!r}")
        print("Pflichtfall g2 (ausgeschlossene Datei in --melder genannt, allein und neben Befund): bestanden")

        # (h) Datei nicht lesbar (kaputtes Encoding) -- gezaehlt, nicht
        # stillschweigend uebersprungen. Dieselbe Fehlklasse wie (g), nur
        # dass hier nicht mal die Ueberschriften lesbar sind.
        plan_kaputt = tmp / "PLAN_KAPUTT.md"
        plan_kaputt.write_bytes(b"\xff\xfe### S1 kaputtes Encoding\n")
        erhebung_kaputt = _erheben([plan_kaputt])
        assert erhebung_kaputt.nicht_lesbar == ["PLAN_KAPUTT.md"], (
            f"Kaputte Datei haette als nicht lesbar gezaehlt werden muessen: {erhebung_kaputt.nicht_lesbar}")
        assert erhebung_kaputt.abschnitte == [], "Kaputte Datei haette 0 Abschnitte liefern muessen"
        puffer3 = io.StringIO()
        with redirect_stdout(puffer3):
            _melden([], erhebung_kaputt)
        assert "1 Datei(en) nicht lesbar: PLAN_KAPUTT.md" in puffer3.getvalue(), (
            f"--melder haette die unlesbare Datei nennen muessen: {puffer3.getvalue()!r}")
        print("Pflichtfall h (unlesbare Datei gezaehlt und in --melder genannt): bestanden")

        conn.close()

    print("Selbsttest bestanden.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--melder", action="store_true", help="nur sprechen, wenn etwas anschlaegt")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--plan-dir", type=Path, default=WURZEL / "docs")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return 0

    # PLAN_*.md und SPRINTS.md -- die zwoelf Dateien, an denen die
    # Kennungsschemata gemessen wurden (Befund 2026-08-12). Kein
    # pauschales docs/*.md: die uebrigen Dokumente (AUFBAU.md, RUNBOOK_*,
    # PROMPT_*, ...) sind keine Plandateien im Sinne dieses Melders.
    plan_dateien = sorted(set(args.plan_dir.glob("PLAN_*.md")) | set(args.plan_dir.glob("SPRINTS.md")))
    if not plan_dateien:
        if not args.melder:
            print(f"keine Plandateien unter {args.plan_dir}")
        return 0

    conn = _connection(_echte_db_pfad())
    try:
        erhebung = _erheben(plan_dateien)
        befunde = pruefen(erhebung.abschnitte, conn)
    finally:
        conn.close()

    if args.melder:
        _melden(befunde, erhebung)
    else:
        _ausfuehrlich(befunde, erhebung)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
