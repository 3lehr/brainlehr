"""Domaenenpaket-Importer (PLAN_OPENLEHR_2026-08-14.md H8a).

Ein Paket ist eine JSON-Datei mit Regeln und ihren Quellen -- das Format ist
kern/belegvertrag.pruefe_regeln in Dateiform (siehe H8-Abschnitt des Plans):
{"domaene", "bezeichnung", "herkunft", "stand", "quellen", "regeln"}.

Ein Paket ist reine Daten. Es wird nie ausgefuehrt, nie als Code geladen --
importiere()/pruefe() lesen JSON und pruefen, sonst nichts.

Eine Regel ohne belegte Fundstelle wird abgewiesen, nicht stillschweigend
uebernommen (ADR-007). Der Grund ist ein Satz fuer den Menschen, der das
Paket ausgewaehlt hat -- keine Ausnahme, kein Dateiname, keine Zeilennummer.

HERKUNFT (Fund O3, docs/SICHERHEITSFUNDE_2026-08-14.md; ADR-018): der
Belegvertrag allein prueft nur Selbstkonsistenz -- Regel und Quelle kommen
aus demselben Paket. Eine Quelle, die sich per kern.belegvertrag.herkunftsart
als 'bestand:<id>' ausweist, behauptet, ein bereits VORHANDENER, von diesem
Paket unabhaengiger Knoten zu sein -- pruefe() sieht hier tatsaechlich in der
Datenbank nach (_pruefe_bestandsquellen unten): leer, nur Leerraum, ein
Selbstverweis auf einen Knoten, den DIESES Paket selbst erst anlegt, oder ein
Knoten, den es gar nicht gibt, werden abgewiesen. Der ueberwiegende, heutige
Fall ('mitgeliefert', kein '_herkunft'-Feld -- siehe pakete/steuer.domaene.json)
bleibt Selbstkonsistenz: ein eingefuegter Gesetzestext ist real, aber nicht
automatisch von einer erfundenen Behauptung zu unterscheiden. speichere()
schreibt die Art als Tag ("beleg:mitgeliefert"/"beleg:bestand") auf jeden
Quellknoten; herkunft_uebersicht() unten liest genau dieses Tag wieder, damit
ein Mensch VOR setze_in_kraft() sehen kann, ob eine Regel nur selbstkonsistent
oder unabhaengig verankert ist -- ohne diesen Leser waere die Art ein weiteres
blindes Feld wie abgeleitet_von/bedient_von im Bestand.

WIRKUNG NULL (ADR-018, Sperre in docs/PLAN_GESAMT_2026-08-13.md): speichere()
ist die erste Stelle in dieser Datei, die tatsaechlich in den Bestand
schreibt. Vorbild ist kern/regelpaket.py TEIL 3 -- genau dieselben zwei
Felder, genau derselbe Grund:
    norm_rang = NULL, norm_entscheidung = 'keine_norm'
Eine importierte Regel WIRKT NICHT STAERKER als jede andere Notiz
(rangfolge.norm_score(None) == 0.0) und darf nie hoeher als Rang 1/2 ohne
menschlichen Entscheider herein (schema.sql-Trigger
knowledge_nodes_normrang_herkunft_bi/_bu) -- diese Datei fuegt der
bestehenden Schranke nichts hinzu, sie geht ihr nur nicht aus dem Weg (kein
Rang-Feld aus dem Paket wird je gelesen, ganz gleich was darin steht).
Quellen (Belegtexte) bekommen NIE einen Rang -- ein Beleg ist keine Norm.
setze_in_kraft() ist der einzige Weg aus der Wirkung Null heraus: ein
ausdruecklicher, protokollierter Aufruf mit Menschenname und Grund, nie ein
Nebeneffekt von speichere() oder einem zweiten Import desselben Pakets.

EXPORT (H10, PLAN_OPENLEHR_2026-08-14.md): exportiere() ist der Zwilling von
importiere()/pruefe() -- baut aus dem Bestand wieder ein Paket im selben
Format. Gate ist freigabe='offen' je Quell-/Regelknoten, exakt der
Mechanismus, den kern/lehrenpaket.py fuer Lehren/Wissensknoten bereits nutzt
(schema.sql-Default ist 'intern' -- ein importierter Knoten reist NIE von
selbst weiter, das Oeffnen ist ein ausdruecklicher menschlicher Akt ausserhalb
dieser Datei, siehe knowledge_freigeben). norm_rang reist NIE mit: er steht
nur in der DB-Spalte der Zeile (gesetzt von setze_in_kraft()), nie im
JSON-'content', das exportiere() wieder ausliest -- dieselbe Wirkung-Null-
Grenze wie beim Import, nur von der anderen Seite betrachtet, und ohne dass
diese Datei dafuer etwas herausfiltern muss (das Feld war nie dort).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from kern import speicher, zeitmarke
from kern.belegvertrag import herkunftsart, pruefe_regeln

_PFLICHTSCHLUESSEL = ("contract_version", "domaene", "quellen", "regeln", "dienst", "oberflaeche")

# INT-VER-001 (docs/REQUIREMENTS_INTERFACE_KOMPAT.md, Teilkatalog zu BDW-F07):
# Die einzige heute unterstuetzte Major-Version des Paketformats. Fehlt sie
# oder ist sie unbekannt, wird abgewiesen -- nie geraten und nie teilweise
# importiert. Dieselbe Fail-closed-Regel wie die Contract Registry in
# OPENLEHR_KERNEL_UND_APP_VERTRAG_V1 §2 Nr. 1: der OpenLehr-Envelope traegt
# contract_version laengst, das Domaenenpaket war das letzte Stueck der
# Strecke ohne Version. Additive Aenderungen (neue optionale Felder) lassen
# die 1 stehen; ein entferntes oder umgedeutetes Pflichtfeld erhoeht sie.
_VERTRAG_VERSION = 1

# -- Die drei Teile einer Domaene (ADR-013) ------------------------------
# Das Format deckte bis zum 2026-08-16 nur *Wissen* ab. 'dienst' und
# 'oberflaeche' stehen hier, WEIL sie Pflicht sind: ein Format nachtraeglich um
# ein Pflichtfeld zu erweitern macht jedes bereits verteilte Repo ungueltig
# (ADR-013). Die Reihenfolge ist das Argument, nicht die Zahl der Pakete.

# Ein Startbefehl mit festem Pfad laeuft auf genau einem Rechner. Verglichen
# wurden die beiden Startbeschreibungen im Haus: de.brainlehr.dienst benutzt
# __REPO_PFAD__, die openlehr-Legacy-Fassung verdrahtet /Volumes/... fest
# (ADR-023 §3). Ein Pfad wie '/gesundheit' ist KEIN Dateipfad und bleibt frei.
_FREMDE_WURZELN = ("/Volumes/", "/Users/", "/home/", "/opt/", "/private/", "/Applications/")

# Die Oberflaeche sagt WAS, nie WIE (ADR-024). Ohne diese Schranke nimmt die
# Beschreibung die Form ihres ersten Lesers an -- und ein zweiter Zeichner
# (Web) muesste sie nachbauen statt lesen.
# ponytail: naive Wortsuche ueber den JSON-Text. Deckt die Bauformen ab, die
# heute vorkommen; eine Beschreibung, die eine Bauform UMSCHREIBT statt sie zu
# benennen, faellt nicht auf. Aufruesten, sobald der erste echte Bildschirm
# steht (B4) -- dann gegen eine Positivliste erlaubter Rollen statt gegen eine
# Sperrliste verbotener Bauformen.
_BAUFORMEN = (
    "nstableview", "nsoutlineview", "nsview", "uiview", "uikit", "appkit", "swiftui",
    "popover", "sidebar", "modal", "toolbar", "vstack", "hstack", "zstack",
    "scrollview", "navigationsplitview", "sheet", "div", "iframe", "css",
)
# Aussehen ist Sache des Zeichners, nie der Domaene -- geprueft an den
# SCHLUESSELN, weil ein Farbwert als reine Zeichenkette sonst durchrutscht.
_AUSSEHEN = ("farbe", "color", "font", "schrift", "_px", "pixel", "margin", "padding", "style")

# -- Wirkung Null: Ort und Kennung importierter Domaenenknoten -----------
PARENT_PREFIX = "/domaenen"
PROJECT_ID = "domaenenpaket-import"
_SUMMARY_MAXLEN = 400

# Identisches Muster wie kern/regelpaket.py INSERT_SQL (TEIL 3 dort): kein
# Rang-Feld in der Spaltenliste, kein Weg, ihn ueber ein Paket zu setzen.
_INSERT_SQL = """
INSERT OR IGNORE INTO knowledge_nodes
    (id, path, parent_path, project_id, title, summary, content, level, tags,
     source, confidence, created_at, updated_at, anlass, actor,
     norm_entscheidung, norm_entschieden_von, norm_entschieden_grund)
VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'keine_norm','skript:domaene.py',
        'Import aus Domaenenpaket -- Rang muss ein Mensch der Zielinstanz vergeben')
"""


def importiere(pfad: str | Path, db: str | Path | None = None) -> dict[str, Any]:
    """Liest und prueft ein Domaenenpaket. Liefert immer ein Ergebnis, wirft
    nie: {"angenommen": bool, "anzahl_regeln": int | None, "grund": str | None}.
    `db`: gegen welchen Bestand '_herkunft':'bestand:<id>'-Quellen geprueft
    werden (siehe pruefe()) -- Vorgabe ort.DB wie ueberall in diesem Haus."""
    try:
        rohtext = Path(pfad).read_text(encoding="utf-8")
    except OSError:
        return _abgelehnt("Die Paketdatei laesst sich nicht oeffnen.")

    try:
        paket = json.loads(rohtext)
    except json.JSONDecodeError:
        return _abgelehnt("Die Paketdatei ist beschaedigt und laesst sich nicht lesen.")

    return pruefe(paket, db=db)


def pruefe(paket: Any, db: str | Path | None = None) -> dict[str, Any]:
    """Dieselbe Pruefung fuer ein bereits gelesenes Paket. Das atelier waehlt
    die Datei aus und schickt ihren INHALT -- so muss der Dienst nie im
    Dateisystem des Nutzers lesen. Gleiche Rueckgabe wie importiere() -- die
    exakte Schluesselmenge ist ein gepruefter Vertrag mit dem atelier
    (test_vertrag_gegen_das_atelier_haelt), darum kommt hier KEIN neues
    Ergebnisfeld dazu; die Herkunftspruefung wirkt ueber 'angenommen'/'grund'."""
    if not isinstance(paket, dict):
        return _abgelehnt("Die Paketdatei enthaelt kein gueltiges Paket.")

    fehlend = [schluessel for schluessel in _PFLICHTSCHLUESSEL if schluessel not in paket]
    if fehlend:
        return _abgelehnt(f"Der Paketdatei fehlen Angaben: {', '.join(fehlend)}.")

    if paket["contract_version"] != _VERTRAG_VERSION:
        return _abgelehnt(
            f"Die Paketdatei gehoert zu einer anderen Fassung des Formats "
            f"(erwartet {_VERTRAG_VERSION}, gefunden {paket['contract_version']!r})."
        )

    regeln = paket["regeln"]
    quellen = paket["quellen"]
    if not isinstance(regeln, list) or not isinstance(quellen, dict):
        return _abgelehnt("Die Paketdatei ist falsch aufgebaut.")

    try:
        pruefe_regeln(regeln, quellen)
    except (ValueError, KeyError, TypeError):
        return _abgelehnt(_grund_fuer_ablehnung(regeln, quellen))

    fehler = _pruefe_bestandsquellen(paket["domaene"], quellen, regeln, db)
    if fehler:
        return _abgelehnt(fehler)

    for pruefung in (_pruefe_dienst(paket["dienst"]), _pruefe_oberflaeche(paket["oberflaeche"])):
        if pruefung:
            return _abgelehnt(pruefung)

    # Die Bezeichnung steht im Paket und wird dem Menschen gezeigt ("... gilt
    # jetzt"). Fehlt sie, traegt die Kennung -- nie ein leerer Name.
    bezeichnung = paket.get("bezeichnung") or paket.get("domaene")
    return {
        "angenommen": True,
        "anzahl_regeln": len(regeln),
        "bezeichnung": bezeichnung,
        "grund": None,
    }


def lies_oberflaeche(domaene_id: str, db: str | Path | None = None) -> dict[str, Any] | None:
    """Die Bildschirm-Beschreibung einer importierten Domaene -- oder None.

    WARUM DIESE FUNKTION EXISTIERT: Ohne sie ueberlebt die Oberflaeche den
    Import nicht, und das atelier muesste die Manifest-DATEI im Dateisystem
    suchen. Genau das tat `DomaenenSeite` als ausdrueckliche Bruecke. Damit
    waere der Importweg fuer die Oberflaeche wirkungslos gewesen: Ein Fremder,
    der nur das Paket bekommt (ADR-012: das Wissenspaket reist frei), haette
    das Wissen gehabt und keinen Bildschirm.

    DREI RUECKGABEN, und die Unterscheidung ist der Zweck:
      None            die Domaene ist hier nicht importiert
      bildschirme=[]  importiert, bringt aber keinen Bildschirm mit -- nach
                      ADR-013 ausdruecklich zulaessig (der Teil *Wissen*
                      "laeuft nirgends, es wird gelesen")
      bildschirme=[…] importiert, mit Beschreibung

    Zurueckgegeben wird, was die Domaene beschrieben hat -- unveraendert, ohne
    Vorgabewerte, ohne Ergaenzung. Sonst entschiede der Speicher ueber das
    Aussehen, und ADR-024 (die Domaene sagt WAS, das atelier entscheidet WIE)
    waere von der falschen Seite ausgehebelt."""
    with speicher.lesen(db) as conn:
        zeile = conn.execute(
            "SELECT content FROM knowledge_nodes WHERE id=?",
            (f"domaeneoberflaeche-{domaene_id}",),
        ).fetchone()
    if zeile is None:
        return None
    try:
        return json.loads(zeile["content"] or "{}")
    except json.JSONDecodeError:
        return None


def _texte(wert: Any) -> Iterator[str]:
    """Jede Zeichenkette im Baum -- SCHLUESSEL UND WERTE gleichermassen.
    Die Unterscheidung waere hier eine Falle: die Bauform steht meist im Wert
    ('popover'), das Aussehen dagegen im Schluessel ('breite_px', 'farbe'), und
    ein Farbwert wie '#2b7de9' ist fuer sich genommen nicht von einer
    Beschriftung zu unterscheiden. Wer nur eine Seite liest, uebersieht die
    andere Haelfte -- ein erster Anlauf tat das und liess zwei von fuenf
    Bauform-Faellen durch."""
    if isinstance(wert, dict):
        for schluessel, unterwert in wert.items():
            yield str(schluessel)
            yield from _texte(unterwert)
    elif isinstance(wert, (list, tuple)):
        for eintrag in wert:
            yield from _texte(eintrag)
    elif isinstance(wert, str):
        yield wert


def _pruefe_dienst(dienst: Any) -> str | None:
    """Kein fester Pfad im Startbefehl (ADR-023 §3). Der Grund nennt den
    gefundenen Pfad -- ein Mensch soll nicht suchen muessen, welcher gemeint
    ist."""
    if not isinstance(dienst, dict):
        return "Der Teil 'dienst' der Paketdatei ist falsch aufgebaut."

    for text in _texte(dienst):
        if text.startswith("~") or any(wurzel in text for wurzel in _FREMDE_WURZELN):
            return (
                f"Der Startbefehl enthaelt einen festen Pfad ({text}). "
                "Er wuerde nur auf diesem Rechner funktionieren -- setze dafuer "
                "den Platzhalter __REPO_PFAD__ ein."
            )
    return None


def _pruefe_oberflaeche(oberflaeche: Any) -> str | None:
    """Die Beschreibung sagt WAS, nie WIE (ADR-024)."""
    if not isinstance(oberflaeche, dict):
        return "Der Teil 'oberflaeche' der Paketdatei ist falsch aufgebaut."

    for text in _texte(oberflaeche):
        klein = text.lower()
        if any(bauform in klein for bauform in _BAUFORMEN):
            return (
                f"Die Oberflaechen-Beschreibung nennt eine Bauform ({text}). "
                "Beschrieben wird, WAS zu sehen sein soll -- wie es gezeichnet "
                "wird, entscheidet die Anwendung."
            )
        if any(wort in klein for wort in _AUSSEHEN):
            return (
                f"Die Oberflaechen-Beschreibung legt das Aussehen fest ({text}). "
                "Beschrieben wird, WAS zu sehen sein soll -- Farben, Groessen und "
                "Abstaende entscheidet die Anwendung."
            )
    return None


def _pruefe_bestandsquellen(
    domaene_id: str, quellen: dict[str, Any], regeln: list[dict[str, Any]],
    db: str | Path | None,
) -> str | None:
    """Fund O3: eine Quelle, die sich als '_herkunft':'bestand:<id>' ausgibt,
    behauptet einen von diesem Paket UNABHAENGIGEN Beleg -- das wird hier
    tatsaechlich geprueft, nicht nur geglaubt. Drei Faelle scheitern schon
    ohne DB-Zugriff (billig zuerst): leere/nur-Leerraum-Kennung, und eine
    Kennung, die auf einen Knoten zeigt, den DIESES Paket selbst gerade erst
    anlegen wuerde (Selbstverweis -- der 'unabhaengige' Anker waere das Paket
    selbst). Erst danach, nur falls noch etwas zu pruefen ist, wird die
    Datenbank einmal nur-lesend geoeffnet. Gibt None zurueck, wenn alles in
    Ordnung ist (auch wenn keine einzige Quelle 'bestand' behauptet)."""
    eigene_ids = {f"domaene-{domaene_id}"}
    eigene_ids.update(f"domaenenquelle-{domaene_id}-{qid}" for qid in quellen)
    eigene_ids.update(
        f"domaenenregel-{domaene_id}-{r['id']}" for r in regeln
        if isinstance(r, dict) and "id" in r
    )

    zu_pruefen: list[tuple[str, str]] = []
    for qid, quelle in quellen.items():
        art, bestand_id = herkunftsart(quelle)
        if art != "bestand":
            continue
        if not bestand_id:
            return f"Die Quelle '{qid}' nennt einen leeren Bestandsverweis."
        if bestand_id in eigene_ids:
            return (
                f"Die Quelle '{qid}' verweist auf einen Knoten, den dieses "
                "Paket selbst anlegt -- kein unabhaengiger Beleg."
            )
        zu_pruefen.append((qid, bestand_id))

    if not zu_pruefen:
        return None

    with speicher.lesen(db) as conn:
        for qid, bestand_id in zu_pruefen:
            treffer = conn.execute(
                "SELECT 1 FROM knowledge_nodes WHERE id = ?", (bestand_id,)
            ).fetchone()
            if treffer is None:
                return (
                    f"Die Quelle '{qid}' verweist auf den Bestandsknoten "
                    f"'{bestand_id}', der nicht existiert."
                )
    return None


def speichere(paket: Any, db: str | Path | None = None) -> dict[str, Any]:
    """Prueft das Paket (siehe pruefe()) und schreibt es NUR bei Annahme in
    den Bestand -- Wirkung Null (ADR-018): jede Zeile bekommt norm_rang=NULL,
    norm_entscheidung='keine_norm'. Ein "norm_rang"-Feld im Paket wird nie
    gelesen, ganz gleich ob es existiert -- dieselbe Entscheidung wie in
    kern/regelpaket.py: das Format traegt kein Rang-Feld, damit nichts zu
    ignorieren ist. Erst setze_in_kraft() macht eine Regel wirksam.

    Idempotent ueber die Primaerschluessel-id (INSERT OR IGNORE), und
    AKTUALISIEREND bei geaendertem Inhalt (INT-UPD-001): existiert die id
    schon, wird title/summary/content/tags/source/updated_at ueberschrieben
    -- aber NUR, wenn die Zeile noch 'keine_norm' traegt UND sich der Inhalt
    tatsaechlich unterscheidet. Eine bereits in Kraft gesetzte Regel
    (setze_in_kraft()) wird von einem Reimport nie angefasst, unveraenderter
    Inhalt zaehlt als 'uebersprungen', nicht als 'aktualisiert'.

    Rueckgabe: das Ergebnis von pruefe(), erweitert um 'gespeichert' (Anzahl
    neu angelegter Zeilen), 'aktualisiert' (Anzahl inhaltlich geaenderter,
    noch nicht in Kraft gesetzter Zeilen) und 'uebersprungen' (unveraendert
    oder bereits in Kraft, also nicht angefasst). Bei Ablehnung sind alle
    drei 0 -- ein abgelehntes Paket schreibt nichts."""
    # db durchreichen: die Bestandspruefung in pruefe() muss gegen DENSELBEN
    # Bestand laufen, in den gleich geschrieben wird -- sonst pruefte diese
    # Zeile (bei einer abweichenden Test- oder Zweit-DB) am falschen Ort und
    # ein 'bestand:'-Verweis waere blind bestanden oder blind durchgefallen.
    ergebnis = pruefe(paket, db=db)
    if not ergebnis["angenommen"]:
        return {**ergebnis, "gespeichert": 0, "aktualisiert": 0, "uebersprungen": 0}

    domaene_id = paket["domaene"]
    herkunft = paket.get("herkunft") or domaene_id
    bezeichnung = ergebnis["bezeichnung"]
    ts = zeitmarke.jetzt()
    zeilen = [_wurzel_zeile(domaene_id, bezeichnung, ts)]
    zeilen += [_quelle_zeile(domaene_id, herkunft, qid, q, ts) for qid, q in paket["quellen"].items()]
    zeilen += [_regel_zeile(domaene_id, herkunft, r, ts) for r in paket["regeln"]]
    # Die Oberflaeche reist mit -- sonst kommt beim Empfaenger das Wissen an
    # und kein Bildschirm (ADR-012/ADR-013).
    zeilen.append(_oberflaeche_zeile(domaene_id, herkunft, paket.get("oberflaeche"), ts))
    # INT-DNST-001: der Startbefehl reist mit -- ein leerer 'dienst' ({})
    # legt bewusst KEINE Zeile an, damit ein Paket ohne eigenen Dienst (die
    # heutigen Wissens-Pakete) keinen leeren Knoten erzeugt (analog dazu,
    # dass exportiere() 'dienst': {} liefert, ohne dass hier je etwas
    # geschrieben wurde). Wirkung Null wie jede andere Zeile -- der Dienst
    # wird dabei NIE gestartet, nur abgelegt.
    if paket["dienst"]:
        zeilen.append(_dienst_zeile(domaene_id, herkunft, paket["dienst"], ts))

    gespeichert = aktualisiert = uebersprungen = 0
    with speicher.schreiben(db) as conn:
        for z in zeilen:
            cur = conn.execute(_INSERT_SQL, z)
            if cur.rowcount:
                gespeichert += 1
            elif _aktualisiere_falls_geaendert(conn, z):
                aktualisiert += 1
            else:
                uebersprungen += 1
    return {**ergebnis, "gespeichert": gespeichert, "aktualisiert": aktualisiert, "uebersprungen": uebersprungen}


def _aktualisiere_falls_geaendert(conn, zeile: tuple) -> bool:
    """INT-UPD-001: die id existiert schon (INSERT OR IGNORE hat nichts
    angelegt) -- prueft, ob sie noch 'keine_norm' traegt und sich der
    Inhalt unterscheidet, und schreibt nur dann. Eine bereits in Kraft
    gesetzte Zeile (setze_in_kraft()) wird hier nie angefasst -- dieselbe
    Schranke wie in setze_in_kraft() selbst, nur von der anderen Seite."""
    id_, title, summary, content, tags, source, ts = (
        zeile[0], zeile[4], zeile[5], zeile[6], zeile[8], zeile[9], zeile[12],
    )
    bestand = conn.execute(
        "SELECT title, summary, content, tags, source, norm_entscheidung "
        "FROM knowledge_nodes WHERE id=?",
        (id_,),
    ).fetchone()
    if bestand is None or bestand["norm_entscheidung"] != "keine_norm":
        return False
    if (bestand["title"], bestand["summary"], bestand["content"], bestand["tags"], bestand["source"]) == (
        title, summary, content, tags, source,
    ):
        return False
    conn.execute(
        "UPDATE knowledge_nodes SET title=?, summary=?, content=?, tags=?, source=?, updated_at=? "
        "WHERE id=? AND norm_entscheidung='keine_norm'",
        (title, summary, content, tags, source, ts, id_),
    )
    return True


def setze_in_kraft(
    domaene_id: str,
    wer: str,
    grund: str,
    norm_rang: int,
    *,
    befristet_bis: str | None = None,
    db: str | Path | None = None,
) -> int:
    """Der einzige Weg aus der Wirkung Null heraus (ADR-018): ein
    ausdruecklicher Willensakt eines Menschen der Zielinstanz, protokolliert
    in genau den Feldern, die dafuer vorgesehen sind (norm_entschieden_von,
    norm_entschieden_grund). Betrifft NUR die Regel-Knoten dieser Domaene
    (Tag "art:regel"), nie die Quellen -- eine Quelle ist ein Beleg, keine
    Norm, und bekommt nie einen Rang.

    `norm_rang` ist PFLICHT (kein Vorgabewert): schema.sql verlangt bei
    norm_entscheidung IN ('norm_befristet','norm_unbefristet') einen
    gesetzten Rang (Trigger knowledge_nodes_norm_entscheidung_rang_bi/_bu) --
    ohne diese Pruefung hier wuerde die Datenbank denselben Fehler erst
    spaeter und unleserlicher melden.

    Nur Regeln, die noch 'keine_norm' tragen, werden angefasst -- eine
    bereits in Kraft gesetzte Regel wird von einem zweiten Aufruf nicht
    stillschweigend ueberschrieben (wer das will, aendert norm_rang direkt).
    Wirft nichts fuer eine Domaene ohne (passende) Regeln -- das ist ein
    leeres Ergebnis, kein Fehler. Gibt die Anzahl geaenderter Zeilen zurueck."""
    if norm_rang is None:
        raise ValueError("setze_in_kraft() braucht einen Rang -- keine_norm wird nie automatisch wirksam.")
    if not wer or not wer.strip():
        raise ValueError("setze_in_kraft() braucht einen Menschen, der entscheidet (wer).")
    if not grund or not grund.strip():
        raise ValueError("setze_in_kraft() braucht einen Grund.")

    ts = zeitmarke.jetzt()
    entscheidung = "norm_befristet" if befristet_bis else "norm_unbefristet"
    with speicher.schreiben(db) as conn:
        cur = conn.execute(
            "UPDATE knowledge_nodes SET norm_rang=?, gilt_ab=?, gilt_bis=?, "
            "norm_entscheidung=?, norm_entschieden_von=?, norm_entschieden_grund=?, "
            "updated_at=? WHERE parent_path=? AND norm_entscheidung='keine_norm' "
            "AND tags LIKE '%\"art:regel\"%'",
            (norm_rang, ts, befristet_bis, entscheidung, wer, grund, ts,
             f"{PARENT_PREFIX}/{domaene_id}"),
        )
    return cur.rowcount


def herkunft_uebersicht(domaene_id: str, db: str | Path | None = None) -> dict[str, str]:
    """Fuer den Menschen, der VOR setze_in_kraft() entscheidet (ADR-018,
    Fund O3): je Regel-id die Herkunftsart ihrer Quelle -- 'mitgeliefert'
    (Selbstkonsistenz, siehe kern/belegvertrag.herkunftsart) oder 'bestand'
    (bei pruefe() gegen die echte Datenbank verankert). Liest das 'beleg:'-
    Tag, das speichere() beim Schreiben der Quellknoten setzt -- der zweite,
    tatsaechliche Leser dieser Herkunftsangabe (der erste ist die
    Bestandspruefung in pruefe() selbst); ohne diesen hier waere die Art nur
    geschrieben, nie wieder gelesen. Leeres Ergebnis fuer eine unbekannte
    oder regellose Domaene -- kein Fehler, dieselbe Haltung wie
    setze_in_kraft()."""
    parent = f"{PARENT_PREFIX}/{domaene_id}"
    with speicher.lesen(db) as conn:
        quellen_art: dict[str, str] = {}
        for row in conn.execute(
            "SELECT id, tags FROM knowledge_nodes WHERE parent_path=? AND tags LIKE '%\"art:quelle\"%'",
            (parent,),
        ):
            for tag in json.loads(row["tags"] or "[]"):
                if tag.startswith("beleg:"):
                    quellen_art[row["id"]] = tag[len("beleg:"):]

        ergebnis: dict[str, str] = {}
        for row in conn.execute(
            "SELECT id, content FROM knowledge_nodes WHERE parent_path=? AND tags LIKE '%\"art:regel\"%'",
            (parent,),
        ):
            regel = json.loads(row["content"] or "{}")
            quelle_id = f"domaenenquelle-{domaene_id}-{regel.get('ziel_id')}"
            ergebnis[regel.get("id", row["id"])] = quellen_art.get(quelle_id, "mitgeliefert")
    return ergebnis


def exportiere(domaene_id: str, db: str | Path | None = None) -> dict[str, Any] | None:
    """Baut aus dem Bestand wieder ein Domaenenpaket -- der Zwilling von
    importiere()/pruefe(). Gate ist freigabe='offen' JE KNOTEN: eine Quelle
    oder Regel, die noch (Vorgabe) 'intern' oder 'gesperrt' traegt, wird
    NICHT exportiert -- sie muss vorher ausdruecklich geoeffnet werden. Eine
    Regel ohne ihre (ebenfalls offene) Quelle wird ebenfalls ausgelassen --
    sonst waere das Paket kein gueltiger Belegvertrag mehr am Zielort
    (pruefe_regeln braucht die genannte ziel_id in 'quellen').

    Gibt None zurueck, wenn die Domaene nicht existiert (kein Wurzelknoten).
    Eine existierende, aber leere oder vollstaendig ungeoeffnete Domaene
    liefert ein Paket mit quellen={} und regeln=[] -- das ist kein Fehler,
    dieselbe Haltung wie bei importiere()/setze_in_kraft()."""
    wurzel_id = f"domaene-{domaene_id}"
    parent = f"{PARENT_PREFIX}/{domaene_id}"
    praefix_quelle = f"domaenenquelle-{domaene_id}-"

    with speicher.lesen(db) as conn:
        wurzel = conn.execute(
            "SELECT title FROM knowledge_nodes WHERE id=?", (wurzel_id,)
        ).fetchone()
        if wurzel is None:
            return None

        quellen: dict[str, Any] = {}
        for row in conn.execute(
            "SELECT id, content FROM knowledge_nodes WHERE parent_path=? "
            "AND tags LIKE '%\"art:quelle\"%' AND freigabe='offen'",
            (parent,),
        ):
            qid = row["id"][len(praefix_quelle):]
            quellen[qid] = json.loads(row["content"] or "{}")

        regeln: list[dict[str, Any]] = []
        for row in conn.execute(
            "SELECT content FROM knowledge_nodes WHERE parent_path=? "
            "AND tags LIKE '%\"art:regel\"%' AND freigabe='offen'",
            (parent,),
        ):
            regel = json.loads(row["content"] or "{}")
            # norm_rang steckt nie in 'content' (siehe Moduldocstring EXPORT)
            # -- diese Zeile filtert nichts heraus, sie stellt nur sicher,
            # dass eine kuenftige Aenderung an speichere()/_regel_zeile()
            # nicht still ein Feld einschleust, das hier ungeprueft mitreist.
            regel.pop("norm_rang", None)
            if regel.get("ziel_id") in quellen:
                regeln.append(regel)

    return {
        # INT-VER-001: der Rundlauf export -> pruefe muss halten, sonst
        # erzeugt das Haus selbst Pakete, die sein eigener Pruefer abweist.
        "contract_version": _VERTRAG_VERSION,
        "domaene": domaene_id,
        "bezeichnung": wurzel["title"],
        "herkunft": f"export:{domaene_id}",
        "stand": zeitmarke.jetzt(),
        "quellen": quellen,
        "regeln": regeln,
        # Der Bestand haelt nur den Teil *Wissen* (die Knoten). Dienst und
        # Oberflaeche stehen deshalb LEER, aber DA -- Anwesenheit ist der
        # Vertrag, nicht Inhalt: ADR-013 verlangt die Felder "von Anfang an
        # ins Manifest, auch wenn sie zunaechst leer bleiben". Eine Domaene,
        # die nur Wissen mitbringt, ist ausdruecklich zulaessig (in ADR-013
        # laeuft der Teil Wissen "nirgends -- es wird gelesen").
        "dienst": {},
        "oberflaeche": {"fassung": 1, "bildschirme": []},
    }


def _kuerzen(text: str) -> str:
    text = text or ""
    return text if len(text) <= _SUMMARY_MAXLEN else text[:_SUMMARY_MAXLEN].rstrip() + " [...]"


def _zeile(
    id_: str, path: str, parent_path: str, title: str, summary: str,
    content: str, level: int, tags: list[str], source: str, ts: str,
) -> tuple:
    return (
        id_, path, parent_path, PROJECT_ID, title, summary or title, content,
        level, json.dumps(tags, ensure_ascii=False), source, 0.5, ts, ts,
        "skript", "domaene.py",
    )


def _wurzel_zeile(domaene_id: str, bezeichnung: str, ts: str) -> tuple:
    # parent_path=None statt PARENT_PREFIX: ein eigener globaler "/domaenen"-
    # Wurzelknoten existiert nicht (derselbe Grund wie bei den Blattknoten
    # oben -- ein Ordnerknoten fuer nichts als Hierarchie). NULL ist laut
    # Trigger immer zulaessig, "/" waere die einzige Alternative gewesen.
    return _zeile(
        id_=f"domaene-{domaene_id}",
        path=f"{PARENT_PREFIX}/{domaene_id}",
        parent_path=None,
        title=bezeichnung or domaene_id,
        summary=f"Importierte Domaene '{domaene_id}'.",
        content=None,
        level=0,
        tags=["domaenenpaket-import", f"domaene:{domaene_id}"],
        source=f"domaenenpaket:{domaene_id}",
        ts=ts,
    )


def _oberflaeche_zeile(domaene_id: str, herkunft: str, oberflaeche: Any, ts: str) -> tuple:
    """Die Bildschirm-Beschreibung als EIN Knoten, nicht als viele.

    Bewusst nicht je Bildschirm ein Knoten: Die Beschreibung ist ein
    zusammenhaengendes Ganzes mit einer Fassungsnummer, und sie wird immer
    komplett gelesen. Einzelknoten waeren nur Hierarchie ohne Leser -- derselbe
    Grund, aus dem _wurzel_zeile keinen Ordnerknoten anlegt.

    Sie traegt KEINEN Rang und keine Norm (Wirkung Null, ADR-018): eine
    Bildschirmbeschreibung ist Darstellung, nie eine Regel."""
    return _zeile(
        id_=f"domaeneoberflaeche-{domaene_id}",
        path=f"{PARENT_PREFIX}/{domaene_id}/oberflaeche",
        parent_path=f"{PARENT_PREFIX}/{domaene_id}",
        title=f"Bildschirme der Domaene '{domaene_id}'",
        summary=_kuerzen(
            f"Beschreibung von {len((oberflaeche or {}).get('bildschirme') or [])} "
            f"Bildschirm(en). Die Domaene sagt WAS, das atelier zeichnet."),
        content=json.dumps(oberflaeche or {}, ensure_ascii=False),
        level=1,
        tags=["domaenenpaket-import", f"domaene:{domaene_id}", "oberflaeche"],
        source=f"domaenenpaket:{domaene_id}",
        ts=ts,
    )


def _dienst_zeile(domaene_id: str, herkunft: str, dienst: dict[str, Any], ts: str) -> tuple:
    """INT-DNST-001: der Startbefehl als EIN Knoten, analog _oberflaeche_zeile.
    Nur fuer nicht-leeren 'dienst' aufgerufen (siehe speichere()) -- ein
    leeres Paket legt keine Zeile an. Traegt KEINEN Rang (Wirkung Null,
    ADR-018): der Dienst wird hier abgelegt, nie gestartet."""
    return _zeile(
        id_=f"domaenendienst-{domaene_id}",
        path=f"{PARENT_PREFIX}/{domaene_id}/dienst",
        parent_path=f"{PARENT_PREFIX}/{domaene_id}",
        title=f"Dienst der Domaene '{domaene_id}'",
        summary=_kuerzen(f"Startbeschreibung fuer den Dienst von '{domaene_id}'. Wird abgelegt, nie gestartet."),
        content=json.dumps(dienst, ensure_ascii=False),
        level=1,
        tags=["domaenenpaket-import", f"domaene:{domaene_id}", "art:dienst"],
        source=f"domaenenpaket:{domaene_id}",
        ts=ts,
    )


def _quelle_zeile(domaene_id: str, herkunft: str, quelle_id: str, quelle: Any, ts: str) -> tuple:
    # parent_path zeigt auf die Domaenen-Wurzel selbst, nicht auf einen
    # eigenen "quellen"-Ordnerknoten -- schema.sql verlangt (Trigger
    # knowledge_nodes_parent_check_bi/_bu), dass JEDER parent_path auf einen
    # VORHANDENEN Knoten zeigt. Ein Ordnerknoten je Domaene waere ein
    # weiterer Schreibvorgang fuer nichts als Hierarchie -- die Unterscheidung
    # Quelle/Regel traegt bereits das Tag "art:quelle"/"art:regel" (siehe
    # setze_in_kraft(), das genau danach filtert).
    bezeichnung = (quelle.get("bezeichnung") if isinstance(quelle, dict) else None) or quelle_id
    # "beleg:<art>" (Fund O3): haelt fest, ob diese Quelle selbstkonsistent
    # ("mitgeliefert") oder gegen den Bestand verankert ("bestand") in
    # pruefe() angenommen wurde -- gelesen von herkunft_uebersicht() unten,
    # NICHT nur geschrieben (sonst dasselbe blinde Feld wie abgeleitet_von).
    art, _ = herkunftsart(quelle)
    return _zeile(
        id_=f"domaenenquelle-{domaene_id}-{quelle_id}",
        path=f"{PARENT_PREFIX}/{domaene_id}/quellen/{quelle_id}",
        parent_path=f"{PARENT_PREFIX}/{domaene_id}",
        title=bezeichnung,
        summary=_kuerzen(bezeichnung),
        content=json.dumps(quelle, ensure_ascii=False, sort_keys=True),
        level=1,
        tags=["domaenenpaket-import", f"domaene:{domaene_id}", "art:quelle", f"beleg:{art}"],
        source=f"domaenenpaket:{herkunft}/{domaene_id}/quellen/{quelle_id}",
        ts=ts,
    )


def _regel_zeile(domaene_id: str, herkunft: str, regel: dict[str, Any], ts: str) -> tuple:
    rid = regel["id"]
    fundstelle = regel.get("fundstelle") or rid
    return _zeile(
        id_=f"domaenenregel-{domaene_id}-{rid}",
        path=f"{PARENT_PREFIX}/{domaene_id}/regeln/{rid}",
        parent_path=f"{PARENT_PREFIX}/{domaene_id}",
        title=rid,
        summary=_kuerzen(fundstelle),
        content=json.dumps(regel, ensure_ascii=False, sort_keys=True),
        level=1,
        tags=["domaenenpaket-import", f"domaene:{domaene_id}", "art:regel"],
        source=f"domaenenpaket:{herkunft}/{domaene_id}/regeln/{rid}",
        ts=ts,
    )


def _grund_fuer_ablehnung(regeln: list[dict[str, Any]], quellen: dict[str, Any]) -> str:
    """Findet die erste Regel, die alleine gegen den Vertrag scheitert, und
    benennt sie -- statt die Ausnahme von pruefe_regeln() weiterzureichen."""
    for regel in regeln:
        if not isinstance(regel, dict):
            return "Eine Regel im Paket ist falsch aufgebaut."
        try:
            pruefe_regeln([regel], quellen)
        except (ValueError, KeyError, TypeError):
            name = regel.get("id", "?")
            return f"Die Regel '{name}' nennt keine Quelle, die zu ihrer Fundstelle passt."
    return "Eine Regel im Paket nennt keine passende Quelle."


def _abgelehnt(grund: str) -> dict[str, Any]:
    return {"angenommen": False, "anzahl_regeln": None, "bezeichnung": None, "grund": grund}


__all__ = ["importiere", "pruefe", "speichere", "lies_oberflaeche", "setze_in_kraft", "herkunft_uebersicht", "exportiere"]
