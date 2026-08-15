"""Tests fuer den Aehnlichkeits-Hinweis in knowledge_add() (Auftrag 78/90).

Rot vor gruen am belegten Fall: die echten Knoten dd367fd1/b6305304/6e0f0395
im Live-Bestand tragen dieselbe Kernaussage (Vergleichbarkeit setzt eine
gemeinsame Achse voraus), unabhaengig voneinander dreimal geschrieben.
Gemessen 2026-08-13 (siehe _find_similar_knowledge_nodes-Docstring in
knowledge_mcp_server.py): weder Wort-Jaccard noch der Bedeutungskanal
(Embedding-Kosinus, cos(dd,6e)=0,612 -- UNTER der fuer KANTEN kalibrierten
Schwelle 0,65) allein trennt diesen Fall von Rauschen. Erst die Summe aus
TF-IDF-gewichtetem Wort-Kosinus und Embedding-Kosinus (Schwelle 0,70) faengt
ihn bei einer Handvoll Hinweisen je neuem Knoten.

Hier: Titel/Zusammenfassung/Inhalt der drei echten Knoten woertlich
nachgestellt (TF-IDF-Signal bleibt damit echt), embed_text() gemockt mit
Vektoren, deren paarweise Kosinuswerte exakt den am 2026-08-13 gemessenen
echten Werten entsprechen (0,7654 / 0,612 / 0,621) -- kein echtes Ollama im
Testlauf noetig (Walkthrough-Doktrin: mockbare Aussenwelt). Die drei Werte
selbst sind unten als Konstanten benannt, nicht als magische Zahlen im Text
versteckt.

Sieht der Code anders aus als hier beschrieben, halte dich an den Code und
melde die Abweichung.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import math
import sqlite3
import sys
import time
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    # jeder Test startet mit einem leeren IDF-Index -- sonst faerbt der
    # zuletzt gelaufene Test (anderer temp_db, andere Knoten-IDs) in den
    # naechsten hinein.
    kms._knowledge_hint_index_cache.update(built_at=0.0, tok={}, idf={}, norm={})
    return db_path


# ─── echte Texte, woertlich aus dem Live-Bestand (2026-08-13) ───────────────

DD_TITLE = "Warum die Rangordnung eine zweite Achse braucht: Sein, Sollen, Duerfen"
DD_SUMMARY = (
    "Das Feld norm_rang kennt nur eine Achse -- wie bindend ein Satz ist. Bei "
    "der Gegenueberstellung von Studien, Leitlinien und Gebuehrenordnungen "
    "versagt das: eine Studie steht weder ueber noch unter einer "
    "Gebuehrenordnung, sie konkurriert gar nicht mit ihr. Ein Widerspruch ist "
    "nur dann einer, wenn beide Saetze derselben Art angehoeren."
)
DD_CONTENT = (
    "DIE DREI ARTEN, die dabei aufeinandertreffen: eine Studie sagt, was IST "
    "('Verfahren X hat Erfolgsquote Y'); eine Leitlinie sagt, was SEIN SOLL "
    "('bei Befund A ist X indiziert'); eine Gebuehrenordnung sagt, was "
    "ABRECHENBAR IST. Unsere Rangordnung ordnet nach BINDUNGSKRAFT und wuerde "
    "diese drei damit auf eine Leiter stellen. Das ist sachlich falsch: eine "
    "Studie wird von einer Gebuehrenordnung nicht ueberstimmt, und umgekehrt "
    "auch nicht. WAS ZU AENDERN WAERE: zwei Achsen statt einer -- Rang (wie "
    "bindend) und Art (Sein, Sollen, Duerfen)."
)

B6_TITLE = "Normen ordnen sich nach drei unabhängigen Achsen, nicht nach einer Zahl"
B6_SUMMARY = (
    "Betreiberentscheidung: Rang (wer hat es erlassen), Art (Sein/Sollen/"
    "Duerfen) und Unabänderlichkeit (Naturgesetz -> Menschenrecht -> "
    "zwischenstaatlich -> Einzelfall) bilden DREI unabhängige Achsen. Zwei "
    "davon sind bereits gebaut, eine liegt bislang leer."
)
B6_CONTENT = (
    "DIE DREI ACHSEN. 1. RANG -- wer eine Norm erlassen hat. 2. ART -- welche "
    "Art von Satz ueberhaupt vorliegt: Sein (Studie, Messung), Sollen "
    "(Leitlinie, Direktive), Duerfen (Gebuehrenordnung, Lizenz): zwei Normen "
    "unterschiedlicher Art konkurrieren NICHT, gleich welchen Rang sie tragen. "
    "3. UNABAENDERLICHKEIT -- wie fest ein Satz gegen Widerruf steht. Diese "
    "Achse KREUZT die Art-Achse: ein Naturgesetz ist Sein, Menschenrecht und "
    "Urteil sind Sollen."
)

E6_TITLE = "Mehrere Einteilungen sind gleichzeitig gültig — Herkunft, Form, Umgebung, Verwundbarkeit"
E6_SUMMARY = (
    "Betreibereinwand am Beispiel Delfin und Hai: Für die Abstammung gehört "
    "der Delfin zur Katze, für die Strömungslehre zum Hai — und beide "
    "Einteilungen sind richtig, sie beantworten verschiedene Fragen. Daraus "
    "vier unabhängige Achsen statt der zuvor behaupteten zwei."
)
E6_CONTENT = (
    "Die Abstammung gewinnt für die Frage der VERWANDTSCHAFT. Für die "
    "Strömungslehre ist „stromlinienförmiger Schwimmer\" die zutreffende "
    "Klasse. Es gibt keine einzige wahre Einteilung; es gibt eine je Frage. "
    "VIER ACHSEN: HERKUNFT, FORM, UMGEBUNG, VERWUNDBARKEIT. DRITTE "
    "AUSPRAEGUNG DESSELBEN GEDANKENS im Bestand: fuer Normen sind Rang, Art "
    "und Unabaenderlichkeit drei unabhaengige Achsen, nicht eine Zahl."
)

# echte Kosinuswerte, gemessen 2026-08-13 gegen den Live-Bestand
_COS_DD_B6 = 0.7654
_COS_DD_E6 = 0.612
_COS_B6_E6 = 0.621

_sin_dd_b6 = math.sqrt(1 - _COS_DD_B6 ** 2)
_b = (_COS_B6_E6 - _COS_DD_B6 * _COS_DD_E6) / _sin_dd_b6
_c = math.sqrt(1 - _COS_DD_E6 ** 2 - _b ** 2)

VEC_DD = (1.0, 0.0, 0.0, 0.0)
VEC_B6 = (_COS_DD_B6, _sin_dd_b6, 0.0, 0.0)
VEC_E6 = (_COS_DD_E6, _b, _c, 0.0)
VEC_NEG = (0.0, 0.0, 0.0, 1.0)  # unrelated -- orthogonal zu allen drei


def _make_embed_mock():
    """Routet embed_text() ueber einen eindeutigen Textbaustein auf den
    passenden vorgerechneten Vektor -- text ist f'{node_path}\\n{title}\\n
    {summary}\\n{content}', ein Titelfragment genuegt zur Unterscheidung."""
    def _mock(text, **kw):
        if "Warum die Rangordnung" in text:
            return list(VEC_DD)
        if "Normen ordnen sich nach drei" in text:
            return list(VEC_B6)
        if "Mehrere Einteilungen sind gleichzeitig" in text:
            return list(VEC_E6)
        return list(VEC_NEG)
    return _mock


def test_belegter_fall_dd_b6_e6_erzeugt_hinweis(temp_db, monkeypatch):
    """Positivfall (Kriterium 1): dd- und b6-analoge Knoten zuerst anlegen,
    dann den e6-analogen -- VORHER (nach den ersten beiden) gibt es keinen
    Grund fuer einen Hinweis, NACHHER (beim dritten) MUSS die Antwort beide
    zuvor angelegten IDs als Hinweis enthalten."""
    monkeypatch.setattr(kms.embeddings, "embed_text", _make_embed_mock())

    res_dd = kms.knowledge_add("/", DD_TITLE, DD_SUMMARY, content=DD_CONTENT, source="test")
    assert "error" not in res_dd, res_dd
    # VORHER: der allererste Knoten hat noch keinen Vorgaenger im (leeren)
    # Bestand, folgerichtig keinen Hinweis.
    assert "similar_node_hint" not in res_dd

    res_b6 = kms.knowledge_add("/", B6_TITLE, B6_SUMMARY, content=B6_CONTENT, source="test")
    assert "error" not in res_b6, res_b6
    # b6 ist selbst schon inhaltlich nah an dd (cos=0,7654, deutlich ueber der
    # Schwelle) -- der Hinweis hier ist erwuenscht, nicht Teil des Negativfalls.
    assert res_dd["id"] in {h["id"] for h in res_b6.get("similar_node_hint", [])}, res_b6

    res_e6 = kms.knowledge_add("/", E6_TITLE, E6_SUMMARY, content=E6_CONTENT, source="test")
    assert "error" not in res_e6, res_e6

    hint_ids = {h["id"] for h in res_e6.get("similar_node_hint", [])}
    assert res_dd["id"] in hint_ids, res_e6
    assert res_b6["id"] in hint_ids, res_e6


def test_negativfall_echter_anderer_knoten_ohne_hinweis(temp_db, monkeypatch):
    """Negativfall (Kriterium 2, der wichtigere): ein inhaltlich neuer,
    thematisch fremder Knoten (Text-Kompressibilitaet, NASA-LLIS-Sprache)
    erzeugt KEINEN Hinweis -- weder gegen einen leeren Bestand noch neben
    den drei oben angelegten Achsen-Knoten."""
    monkeypatch.setattr(kms.embeddings, "embed_text", _make_embed_mock())

    kms.knowledge_add("/", DD_TITLE, DD_SUMMARY, content=DD_CONTENT, source="test")
    kms.knowledge_add("/", B6_TITLE, B6_SUMMARY, content=B6_CONTENT, source="test")
    kms.knowledge_add("/", E6_TITLE, E6_SUMMARY, content=E6_CONTENT, source="test")

    res_neg = kms.knowledge_add(
        "/", "Data Compressibility bei Telemetriedaten",
        "Messreihe zur verlustfreien Kompression von Sensordaten im Flug, "
        "unabhaengig von Normen, Achsen oder Rangordnungen.",
        content="Kompressionsverfahren X erreicht Faktor 3 auf Telemetriedaten "
                "aus Sensor Y, gemessen ueber 40 Missionen.",
        source="test",
    )
    assert "error" not in res_neg, res_neg
    assert res_neg.get("similar_node_hint", []) == []


def test_pruefung_liegt_vor_dem_schreiben(temp_db, monkeypatch):
    """Kriterium 4: ein abgelehnter Aufruf (hier: unbekannter parent_path
    ohne neuer_ast) hinterlaesst KEINE Zeile -- die Aehnlichkeitspruefung
    haengt am Schreibpfad, nicht danach."""
    monkeypatch.setattr(kms.embeddings, "embed_text", _make_embed_mock())
    res = kms.knowledge_add("/gibt/es/nicht", DD_TITLE, DD_SUMMARY, content=DD_CONTENT, source="test")
    assert "error" in res, res

    conn = sqlite3.connect(str(temp_db))
    n = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    conn.close()
    assert n == 0, "abgelehnter Aufruf haette keine Zeile schreiben duerfen"


def test_hinweis_gedeckelt_auf_cap(temp_db, monkeypatch):
    """Grenzwert (Kriterium 3, punktuell): auch wenn mehr als CAP Kandidaten
    ueber der Schwelle liegen, kommen nie mehr als _KNOWLEDGE_HINT_CAP
    Hinweise zurueck -- sonst waere aus dem Hinweis wieder Rauschen."""
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda text, **kw: list(VEC_DD))

    ids = []
    for i in range(6):
        res = kms.knowledge_add(
            "/", f"Variante {i} -- {DD_TITLE}", DD_SUMMARY, content=DD_CONTENT, source="test",
        )
        assert "error" not in res, res
        ids.append(res["id"])

    res_final = kms.knowledge_add(
        "/", f"Variante final -- {DD_TITLE}", DD_SUMMARY, content=DD_CONTENT, source="test",
    )
    hints = res_final.get("similar_node_hint", [])
    assert len(hints) <= kms._KNOWLEDGE_HINT_CAP, hints


def test_schreibdauer_hint_pruefung_nicht_spuerbar(temp_db, monkeypatch):
    """Performance-Beleg (Auftrags-Grenze): die Hinweispruefung selbst
    (TF-IDF-Kurzliste + Embedding-Vergleich der Kurzliste) darf den
    Schreibvorgang nicht spuerbar verlangsamen. Gemessen hier gegen einen
    kleinen, aber nicht leeren Bestand (20 Vorknoten) -- der grosse Teil der
    Kosten (IDF-Indexaufbau, ~150ms bei 2000+ Knoten im echten Bestand,
    separat gemessen) ist TTL-gecacht und faellt hier nur einmal an, nicht
    pro Aufruf."""
    monkeypatch.setattr(kms.embeddings, "embed_text", _make_embed_mock())

    for i in range(20):
        kms.knowledge_add("/", f"Vorknoten {i}", f"Zusammenfassung {i}", source="test")

    # Cache einmal warm laufen lassen (Indexaufbau ausserhalb der Messung).
    kms.knowledge_add("/", DD_TITLE, DD_SUMMARY, content=DD_CONTENT, source="test")

    t0 = time.time()
    res = kms.knowledge_add("/", B6_TITLE, B6_SUMMARY, content=B6_CONTENT, source="test")
    dauer_ms = (time.time() - t0) * 1000
    assert "error" not in res, res
    print(f"\nknowledge_add mit Hinweispruefung (Cache warm): {dauer_ms:.1f}ms")
    assert dauer_ms < 200.0, f"{dauer_ms:.1f}ms -- Hinweispruefung koennte spuerbar verlangsamen"


# ─── Grenzwerte (nachgetragen bei der Nachmessung dieses Auftrags) ─────────
#
# Rot vor gruen fuer den Titel-Fall: VOR der zugehoerigen Aenderung in
# knowledge_add() (Zeile um "if not slug:") legte ein leerer oder rein aus
# Sonderzeichen bestehender Titel eine Zeile mit path="/" an -- identisch mit
# dem Wurzelpfad, den jeder Aufruf mit parent_path="/" traegt. Nachgestellt:
# knowledge_add("/", "", ...) lieferte {"status": "created", ...} statt eines
# Fehlers, und knowledge_nodes enthielt danach eine Zeile mit path="/".

def test_leerer_titel_wird_abgelehnt(temp_db, monkeypatch):
    monkeypatch.setattr(kms.embeddings, "embed_text", _make_embed_mock())
    res = kms.knowledge_add("/", "", "leerer titel", source="test",
                            norm_entscheidung="keine_norm", norm_entschieden_grund="test")
    assert "error" in res, res

    conn = sqlite3.connect(str(temp_db))
    n = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    conn.close()
    assert n == 0, "abgelehnter leerer Titel haette keine Zeile schreiben duerfen"


def test_titel_nur_sonderzeichen_wird_abgelehnt(temp_db, monkeypatch):
    """Wie oben, aber ueber einen NICHT-leeren Titel, der trotzdem zu einem
    leeren Slug faltet ('???' -> '') -- derselbe Fehlerpfad, ein anderer
    Ausloeser."""
    monkeypatch.setattr(kms.embeddings, "embed_text", _make_embed_mock())
    res = kms.knowledge_add("/", "???", "titel ohne brauchbare zeichen", source="test",
                            norm_entscheidung="keine_norm", norm_entschieden_grund="test")
    assert "error" in res, res

    conn = sqlite3.connect(str(temp_db))
    n = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    conn.close()
    assert n == 0


def test_sehr_kurzer_titel_wird_angelegt(temp_db, monkeypatch):
    """Ein einzelnes brauchbares Zeichen ist ein gueltiger Titel (Grenzwert
    knapp UEBER der Ablehnung) -- kein Fehler, normaler Pfad."""
    monkeypatch.setattr(kms.embeddings, "embed_text", _make_embed_mock())
    res = kms.knowledge_add("/", "A", "kurzer titel", source="test",
                            norm_entscheidung="keine_norm", norm_entschieden_grund="test")
    assert "error" not in res, res
    assert res["path"] == "/a"


def test_identischer_titel_anderer_inhalt_gibt_hinweis_kein_fehler(temp_db, monkeypatch):
    """Gleicher Titel unter VERSCHIEDENEM Elternpfad (also verschiedener
    node_path, kein Pfad-Kollisionsfehler) mit abweichendem Inhalt: erwartet
    ist ein Hinweis, keine Ablehnung -- der Aufrufer entscheidet."""
    monkeypatch.setattr(kms.embeddings, "embed_text", _make_embed_mock())
    kms.knowledge_add("/", DD_TITLE, DD_SUMMARY, content=DD_CONTENT, source="test")
    res = kms.knowledge_add(
        "/andere-ecke", DD_TITLE,  # identischer Titel, ANDERER Elternpfad -> kein Pfadkonflikt
        "Voellig andere Zusammenfassung ueber Backuprotation und Plattenplatz.",
        content="Nichts mit Rangordnung, Sein/Sollen/Duerfen oder Achsen zu tun.",
        source="test", neuer_ast=True,
    )
    assert "error" not in res, res
    # Titelgleichheit allein treibt TF-IDF stark genug fuer einen Hinweis,
    # obwohl Zusammenfassung/Inhalt fremd sind.
    assert res.get("similar_node_hint", []) != []


def test_gleicher_inhalt_anderer_pfad_gibt_hinweis(temp_db, monkeypatch):
    """Wortgleicher Inhalt unter voellig anderem Titel/Pfad: der Hinweis
    haengt am Text, nicht am Pfad."""
    monkeypatch.setattr(kms.embeddings, "embed_text", _make_embed_mock())
    kms.knowledge_add("/", DD_TITLE, DD_SUMMARY, content=DD_CONTENT, source="test")
    res = kms.knowledge_add(
        "/woanders", "Ein komplett anderer Titel fuer denselben Gedanken",
        DD_SUMMARY, content=DD_CONTENT, source="test", neuer_ast=True,
    )
    assert "error" not in res, res
    assert res.get("similar_node_hint", []) != []
