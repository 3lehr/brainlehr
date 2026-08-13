#!/usr/bin/env python3
"""Zwei Einbettungsmodelle auf dem eigenen Bestand vergleichen -- Trefferquote
je Modell gegen dieselben etikettierten Faelle (Aufgabe 93-Vorlauf).

BAUFORM nach messungen/okkultation.py: WURZEL per schema.sql-Suche, nur
lesender Zugriff auf brainlehr.db (speicher.lesen), Pruefsumme vor/nach als
Beleg statt Behauptung.

FALLBESTAND: runs/pruefkorpus_v2.json (kern/pruefkorpus.py, Lauf vom
2026-08-07T14:02, 45 Faelle). Genommen statt pruefkorpus.json (v1, gleiche
Fallzahl 45): v2 ist der SPAETERE der beiden gleich grossen Laeufe (v1
09:21, v2 14:02 desselben Tages) und alle 35 Ziele (20 Knoten + 15 Lehren)
loesen HEUTE noch im Bestand auf (geprueft vor dem Schreiben dieses Skripts).
pruefkorpus_v3.json faellt aus: 42 Zeilen sind bereits ein abgeschlossener
Modell-Antwortlauf (Rechenaufgaben ueber erfundene, project_id='pruefkorpus_v3'
gehaltene Knoten) -- kein Anfrage->Zielknoten-Paar auf dem ECHTEN Bestand.

KANDIDATENPOOL (Ponytail-Entscheidung, hier begruendet statt nur behauptet):
Trefferquote = Rang-1-Treffer unter den 35 tatsaechlichen Zielen selbst, NICHT
unter dem vollen Bestand (~2166 Knoten + 833 Lehren). Vollbestand waere ueber
6000 Einbettungen je Modell -- reisst den Zehn-Minuten-Deckel. 35 Kandidaten
ist der Fallbestand selbst: jede Anfrage muss ihr EIGENES Ziel unter 35
moeglichen Zielen erkennen, nicht raten zwischen zwei. Das ist kleiner als
ein Produktivabruf, aber ein Modell, das nicht einmal DAS trennt, trennt erst
recht nicht mehr.

POSITIVKONTROLLE -- NACHTRAG 2026-08-14T02:05:00+0200, WICHTIGER ALS ALLES
DARUNTER: Diese Kontrolle bildet die Messung vom 2026-08-07 NICHT nach, sie
bildet sie NEU. Anderer Fallbestand (35 Pruefkorpus-Faelle statt 8 fest
benannter Knoten), andere Fachfremd-Menge, anderes Anfrage-Design. Ein
Abweichen sagt damit nichts ueber dieses Werkzeug -- es vergleicht zwei
verschiedene Dinge (L-3bf6c7).

Die Kontrolle wurde daher am 2026-08-14 auf dem URSPRUNGSMATERIAL
nachgefahren: dieselben acht Knoten (008175fd, 00ee966c, 01878a1a, 0193bfaf,
024810d2, 02937ddb,02bb87a3, 06c6fb97, in hub/docs/PRUEFKORPORA_UND_SPRACHE_
2026-08-07.md woertlich genannt), dasselbe Design (eigener Titel als Anfrage
gegen Titel+Zusammenfassung, dagegen Alltagssaetze). Ergebnis: bge-m3
reproduziert (Median-Abstand 0,093 gegen 0,106 damals), nomic-embed-text NICHT
(0,064 gegen 0,004, und die Minimum-Inversion von damals tritt nicht auf).

DER GRUND IST BENENNBAR UND LIEGT NICHT AM WERKZEUG: Sieben der acht Knoten
wurden seit dem 2026-08-07 geaendert (zuletzt drei am 2026-08-13). Der Text,
gegen den damals gemessen wurde, existiert nicht mehr. Und die fachfremden
Saetze wurden nie woertlich festgehalten, nur als Stichworte in Klammern
("Kartoffeln pflanzen, Apfelkuchen, Wetter, Fussball, Yoga, Roemisches
Reich") -- sie mussten rekonstruiert werden.

DARAUS FOLGT FUER DIE ENTSCHEIDUNG, die an dieser Aufgabe haengt: Die
Trefferquoten unten sind gerechnet, aber sie tragen keinen Modellwechsel.
Solange keine Positivkontrolle steht, die auf konserviertem Material laeuft,
ist ein Vergleich zwischen einem bekannten und einem neuen Modell nicht
entscheidbar. Was fehlt, ist kein besseres Werkzeug, sondern ein
EINGEFRORENER Kontrollsatz -- Text UND Anfragen woertlich abgelegt.

Ursprungsbeschreibung des Autors (Stand vor dem Nachtrag): bildet die Messung
vom 2026-08-07 (Knoten /brainlehr/das-einbettungsmodell-trennt-auf) nach --
Median-Kosinus PASSEND (Anfrage vs. eigenes Ziel, 35 Paare) gegen
FACHFREMD (die 10 zielfreien 'negative'-Anfragen aus demselben Fallbestand
gegen alle 35 Ziele, 350 Paare). bge-m3 muss trennen (Median-Abstand deutlich
> 0), nomic-embed-text darf es laut Vorbefund nicht.

GRENZE: kein Zeilenschreiben in brainlehr.db. Vergleichsvektoren leben nur im
Prozessspeicher, nie in knowledge_embeddings (dort haette ein Trigger jeden
Fremdmodell-Namen ohnehin abgelehnt, schema.sql
knowledge_embeddings_model_check_bi) -- hier wird die Tabelle gar nicht erst
angefasst.

Aufruf:
    python3 messungen/modellvergleich.py --lauf runs/modellvergleich_<datum>.json
    python3 messungen/modellvergleich.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken", "messungen")]

import argparse
import json
import statistics
import time
from pathlib import Path

import build_embeddings as be  # noqa: E402 -- nur node_text/lesson_text/_checksum, nichts geschrieben
import codestand  # noqa: E402
import embeddings  # noqa: E402
import speicher  # noqa: E402

WURZEL = _w
DB = None  # ort.DB via speicher-Vorgabe, kein fest verdrahteter Pfad
FALLBESTAND = WURZEL / "runs" / "pruefkorpus_v2.json"
MODELLE = ["bge-m3", "nomic-embed-text"]
ZEITDECKEL_S = 540  # 9 von 10 Minuten, Rest fuer Schreiben/Auswerten


# ------------------------------------------------------------- Fallbestand
def lade_faelle() -> tuple[list[dict], list[dict]]:
    """Gibt (etikettiert, negativ) zurueck. etikettiert: Faelle mit target_id
    (35). negativ: die 10 zielfreien Eichfaelle (category 'negative')."""
    daten = json.loads(FALLBESTAND.read_text(encoding="utf-8"))
    faelle = daten["cases"]
    etikettiert = [f for f in faelle if f.get("target_id")]
    negativ = [f for f in faelle if not f.get("target_id")]
    return etikettiert, negativ


def ziel_text(conn, kind: str, ref_id: str) -> str | None:
    """Denselben Text bauen, den ein echter build_embeddings.py-Lauf erzeugen
    wuerde -- node_text()/lesson_text() sind dort EINMAL definiert, hier nur
    aufgerufen (Kommentar an Ort und Stelle: keine zweite Abschrift)."""
    if kind == "node":
        row = conn.execute(
            "SELECT path, title, summary, content FROM knowledge_nodes "
            "WHERE path = ? AND zurueckgezogen = 0", (ref_id,)).fetchone()
        return be.node_text(row) if row else None
    if kind == "lesson":
        row = conn.execute(
            "SELECT id, node_path, projects, description, root_cause, prevention "
            "FROM lessons_learned WHERE id = ?", (ref_id,)).fetchone()
        return be.lesson_text(row) if row else None
    return None


# ------------------------------------------------------------- Einbettung
def _model_id(modell: str) -> str:
    return embeddings.model_identity(modell)


def probe_erreichbar(modell: str) -> bool:
    """Wie build_embeddings.main(): ein Sondertext VOR dem eigentlichen Lauf.
    Liefert er None, ist der Dienst/das Modell weg -- das darf NICHT als
    '0 Treffer' in die Quote einfliessen (Abnahme 5)."""
    return embeddings.embed_text("Erreichbarkeitstest", model=_model_id(modell)) is not None


def embed_alle(texte: list[str], modell: str) -> list[list[float] | None]:
    mid = _model_id(modell)
    return [embeddings.embed_text(t, model=mid) for t in texte]


# ------------------------------------------------------------- Auswertung
def naechstes_ziel(query_vec: list[float] | None,
                    ziel_vecs: dict[str, list[float]]) -> str | None:
    """Rang-1 unter den vorhandenen Zielvektoren, per Kosinus. None, wenn die
    Anfrage selbst nicht eingebettet werden konnte."""
    if query_vec is None:
        return None
    beste_id, beste_sim = None, -2.0
    for zid, zvec in ziel_vecs.items():
        if zvec is None:
            continue
        sim = embeddings.cosine_similarity(query_vec, zvec)
        if sim > beste_sim:
            beste_sim, beste_id = sim, zid
    return beste_id


def modell_auswerten(modell: str, etikettiert: list[dict], negativ: list[dict],
                      conn) -> dict:
    if not probe_erreichbar(modell):
        return {"modell": modell, "erreichbar": False,
                "hinweis": "Dienst/Modell antwortet nicht -- keine Quote, "
                           "KEIN 0-Treffer-Ausweis (Abnahme 5)."}

    # Zieltexte + IDs, deterministische Reihenfolge.
    ziel_ids = sorted({f"{f['target_kind']}:{f['target_id']}" for f in etikettiert})
    ziel_texte: dict[str, str] = {}
    gekappte_ziele = []
    for zid in ziel_ids:
        kind, ref = zid.split(":", 1)
        text = ziel_text(conn, kind, ref)
        ziel_texte[zid] = text or ""
        if text and embeddings.wird_gekappt(text):
            gekappte_ziele.append(zid)

    ziel_vecs = dict(zip(ziel_ids, embed_alle([ziel_texte[z] for z in ziel_ids], modell)))

    query_texte = [f["prompt"] for f in etikettiert]
    query_vecs = embed_alle(query_texte, modell)
    gekappte_anfragen = [etikettiert[i]["target_id"] for i, t in enumerate(query_texte)
                          if embeddings.wird_gekappt(t)]

    treffer = 0
    n = 0
    fehler_embed = 0
    passende_kosinus = []
    einzelfaelle = []
    for fall, qvec in zip(etikettiert, query_vecs):
        zid = f"{fall['target_kind']}:{fall['target_id']}"
        zvec = ziel_vecs.get(zid)
        if qvec is None or zvec is None:
            fehler_embed += 1
            continue
        n += 1
        gefunden = naechstes_ziel(qvec, ziel_vecs)
        ist_treffer = gefunden == zid
        treffer += int(ist_treffer)
        passende_kosinus.append(embeddings.cosine_similarity(qvec, zvec))
        einzelfaelle.append({"kennung": fall["target_id"], "ziel": zid,
                              "gefunden": gefunden, "treffer": ist_treffer})

    # Positivkontrolle: fachfremde Anfragen (die 10 'negative'-Faelle) gegen
    # alle 35 Ziele -- 350 Paare, kein Ziel gehoert zu ihnen per Definition.
    neg_texte = [f["prompt"] for f in negativ]
    neg_vecs = embed_alle(neg_texte, modell)
    fachfremde_kosinus = []
    for nvec in neg_vecs:
        if nvec is None:
            continue
        for zid, zvec in ziel_vecs.items():
            if zvec is not None:
                fachfremde_kosinus.append(embeddings.cosine_similarity(nvec, zvec))

    return {
        "modell": modell, "erreichbar": True,
        "trefferquote": {"treffer": treffer, "n": n,
                          "anteil": (treffer / n) if n else None},
        "embed_fehlgeschlagen": fehler_embed,
        "gekappte_ziele": gekappte_ziele,
        "gekappte_anfragen": gekappte_anfragen,
        "positivkontrolle": {
            "passend_median": statistics.median(passende_kosinus) if passende_kosinus else None,
            "passend_n": len(passende_kosinus),
            "fachfremd_median": statistics.median(fachfremde_kosinus) if fachfremde_kosinus else None,
            "fachfremd_n": len(fachfremde_kosinus),
            "median_abstand": (
                statistics.median(passende_kosinus) - statistics.median(fachfremde_kosinus)
                if passende_kosinus and fachfremde_kosinus else None),
        },
        "einzelfaelle": einzelfaelle,
    }


def lauf(out_pfad: str) -> dict:
    t0 = time.monotonic()
    etikettiert, negativ = lade_faelle()

    with speicher.lesen() as conn:
        pruefsumme_vorher = be._checksum(conn)
        ergebnisse = []
        gekuerzt = False
        for modell in MODELLE:
            if time.monotonic() - t0 > ZEITDECKEL_S:
                gekuerzt = True
                break
            ergebnisse.append(modell_auswerten(modell, etikettiert, negativ, conn))
        pruefsumme_nachher = be._checksum(conn)

    # Abnahme 2, POSITIVKONTROLLE ueber BEIDE Modelle geprueft, nicht behauptet:
    bge = next((e for e in ergebnisse if e["modell"] == "bge-m3" and e.get("erreichbar")), None)
    nomic = next((e for e in ergebnisse if e["modell"] == "nomic-embed-text" and e.get("erreichbar")), None)
    positivkontrolle_bestanden = None
    positivkontrolle_begruendung = "nicht pruefbar -- mindestens ein Modell nicht erreichbar"
    if bge and nomic:
        bge_trennt = (bge["positivkontrolle"]["median_abstand"] or 0) > 0.03
        nomic_trennt_nicht = abs(nomic["positivkontrolle"]["median_abstand"] or 0) < 0.03
        positivkontrolle_bestanden = bool(bge_trennt and nomic_trennt_nicht)
        positivkontrolle_begruendung = (
            f"bge-m3 Median-Abstand {bge['positivkontrolle']['median_abstand']}, "
            f"nomic-embed-text Median-Abstand {nomic['positivkontrolle']['median_abstand']} -- "
            f"erwartet: bge-m3 trennt deutlich (>0.03), nomic praktisch nicht (<0.03 Betrag), "
            f"wie am 2026-08-07 gemessen (0,106 gegen ~0,004)."
        )

    ergebnis = {
        "erzeugt_am": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "codestand": codestand.ermitteln(WURZEL),
        "fallbestand": {"datei": str(FALLBESTAND.relative_to(WURZEL)),
                         "etikettiert_n": len(etikettiert), "negativ_n": len(negativ),
                         "quelle": "kern/pruefkorpus.py-Lauf 2026-08-07T14:02"},
        "kandidatenpool": "die 35 tatsaechlichen Ziele selbst (nicht der volle Bestand, "
                           "s. Modulkopf)",
        "pruefsumme_bestand_vorher": pruefsumme_vorher,
        "pruefsumme_bestand_nachher": pruefsumme_nachher,
        "bestand_unveraendert": pruefsumme_vorher == pruefsumme_nachher,
        "laufzeit_deckel_540s_gekuerzt": gekuerzt,
        "modelle": ergebnisse,
        "positivkontrolle_bestanden": positivkontrolle_bestanden,
        "positivkontrolle_begruendung": positivkontrolle_begruendung,
        # Abnahme 2, woertlich: zeigt der Lauf den bekannten Unterschied
        # nicht, ist das WERKZEUG untauglich -- unabhaengig von jeder
        # anderen Zahl. Kein Nachjustieren der Schwelle, nur Feststellen.
        "gesamturteil": (
            "WERKZEUG UNTAUGLICH -- Positivkontrolle nicht bestanden, "
            "Trefferquoten unten sind ohne Aussagekraft"
            if positivkontrolle_bestanden is False else
            "Positivkontrolle nicht pruefbar (Modell nicht erreichbar) -- "
            "keine Aussage moeglich"
            if positivkontrolle_bestanden is None else
            "Positivkontrolle bestanden -- Trefferquoten unten sind belastbar"
        ),
        "gesamtlaufzeit_s": round(time.monotonic() - t0, 1),
    }
    if out_pfad:
        p = Path(out_pfad)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
    return ergebnis


# --------------------------------------------------------------------- CLI
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lauf", metavar="DATEI", help="Vergleich fahren, Ergebnis schreiben")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return

    if args.lauf:
        erg = lauf(args.lauf)
        for m in erg["modelle"]:
            if not m.get("erreichbar"):
                print(f"{m['modell']}: NICHT ERREICHBAR -- {m['hinweis']}")
                continue
            q = m["trefferquote"]
            pk = m["positivkontrolle"]
            print(f"{m['modell']}: Trefferquote {q['treffer']}/{q['n']} "
                  f"({q['anteil']}), Median-Abstand passend/fachfremd "
                  f"{pk['median_abstand']}")
        print(f"Positivkontrolle bestanden: {erg['positivkontrolle_bestanden']}")
        print(f"Bestand unveraendert: {erg['bestand_unveraendert']} "
              f"({erg['pruefsumme_bestand_vorher']} -> {erg['pruefsumme_bestand_nachher']})")
        print(f"Geschrieben: {args.lauf}")
        return

    ap.print_help()


# ------------------------------------------------------------------- Tests
def _selftest() -> None:
    """Rot-vor-gruen, ohne Netz: Rang-1-Logik, Erreichbarkeits-Negativfall
    samt Gegenprobe, Kappungs-Erkennung."""
    # 1) naechstes_ziel(): findet das naeher liegende von zwei Zielen.
    ziel_vecs = {"node:/a": [1.0, 0.0], "node:/b": [0.0, 1.0]}
    assert naechstes_ziel([0.9, 0.1], ziel_vecs) == "node:/a"
    assert naechstes_ziel([0.1, 0.9], ziel_vecs) == "node:/b"
    # Fehlender Query-Vektor -> kein Rang-1, nicht "irgendein Ziel".
    assert naechstes_ziel(None, ziel_vecs) is None
    # Leerer Zielraum -> None statt Absturz.
    assert naechstes_ziel([1.0, 0.0], {}) is None

    # 2) Kappung ist erkennbar (Grenze aus embeddings.zeichengrenze()).
    grenze = embeddings.zeichengrenze()
    assert not embeddings.wird_gekappt("kurz")
    assert embeddings.wird_gekappt("x" * (grenze + 1))

    # 3) Negativfall Abnahme 5: ein nicht erreichbares Modell darf NIE als
    # 0-Treffer-Quote erscheinen -- probe_erreichbar() muss False liefern,
    # wenn embed_text() (hier durch einen erfundenen Modellnamen simuliert,
    # den Ollama nicht kennt) None zurueckgibt.
    class _Notiz:
        rufe = []

    def _fake_embed_none(text, *, model="", base_url="", timeout=None):
        _Notiz.rufe.append(model)
        return None

    orig = embeddings.embed_text
    embeddings.embed_text = _fake_embed_none
    try:
        assert probe_erreichbar("kein-solches-modell") is False
    finally:
        embeddings.embed_text = orig
    assert _Notiz.rufe, "probe_erreichbar hat embed_text nie aufgerufen"

    # Gegenprobe: ein Fake, der einen Vektor liefert, gilt als erreichbar --
    # sonst waere probe_erreichbar() nur eine Funktion, die immer False sagt.
    def _fake_embed_ok(text, *, model="", base_url="", timeout=None):
        return [0.1, 0.2]

    embeddings.embed_text = _fake_embed_ok
    try:
        assert probe_erreichbar("irgendein-modell") is True
    finally:
        embeddings.embed_text = orig

    # 4) Fallbestand: 35 etikettierte + 10 negative, wenn die Datei vorliegt.
    if FALLBESTAND.exists():
        etikettiert, negativ = lade_faelle()
        assert len(etikettiert) == 35, len(etikettiert)
        assert len(negativ) == 10, len(negativ)
        assert all(f.get("target_kind") in ("node", "lesson") for f in etikettiert)

    print("selftest ok: Rang-1-Logik, Kappungserkennung, "
          "Erreichbarkeits-Negativfall+Gegenprobe, Fallbestandsform",
          file=_sys.stderr)


if __name__ == "__main__":
    main()
