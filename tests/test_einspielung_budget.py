"""Der Abruf lieferte vollstaendig -- und verlor 85,5 Prozent DANACH.

GEMESSEN 2026-08-13T23:05 an einer laufenden Sitzung: 11 Einspielungen
erzeugten 155749 Byte, angekommen sind 22528. Je Einspielung sichtbar: 2 von
14, 3 von 10, 6 von 15 Eintraegen. Am 2026-08-14 an drei echten Anfragen
nachgemessen und bestaetigt: 16754, 19701 und 20522 Byte je Einspielung.

DAS KAPPENDE GLIED MELDET IN DER FALSCHEN EINHEIT: "Output too large
(16.3KB). Full output saved to <pfad>. Preview (first 2KB)" -- Byte und ein
Dateipfad, aber keine Zahl des Gegenstands. Deshalb wurde die Meldung elfmal
als Formatierungshinweis gelesen statt als Verlustmeldung (L-e61d18).

DIE REPARATUR IST NICHT MEHR PLATZ, SONDERN EHRLICHKEIT. Der Haken kennt
seine Trefferzahl, bleibt innerhalb der Grenze und benennt, was er weglaesst.

Rot vor gruen: gegen den Stand davor gibt es weder _auf_budget_kuerzen() noch
eine Bilanzzeile, und der Block ueberschreitet das Budget um das Doppelte
bis Zweieinhalbfache.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import knowledge_recall_hook as hook  # noqa: E402


def _block(n_eintraege: int, laenge: int = 400) -> list[str]:
    """Kopfzeile, Rumpfzeilen, Schlusszeile -- die Form, die der Haken baut."""
    return (["<knowledge-recall>", "Aus dem Speicher, ungeprüft."]
            + [f"- [{i}] " + "x" * laenge for i in range(n_eintraege)]
            + ["</knowledge-recall>"])


def test_block_bleibt_im_budget():
    block, weggelassen = hook._auf_budget_kuerzen(_block(60))
    assert len(block.encode("utf-8")) <= hook.EINSPIELUNG_MAX_BYTES, (
        f"{len(block.encode('utf-8'))} Byte ueberschreiten das Budget von "
        f"{hook.EINSPIELUNG_MAX_BYTES} -- genau dann kappt der Weg dahinter "
        "und legt den Rest in eine Datei, die niemand oeffnet")
    assert weggelassen > 0


def test_bilanz_nennt_gefunden_eingespielt_weggelassen():
    block, weggelassen = hook._auf_budget_kuerzen(_block(60))
    eingespielt = sum(1 for z in block.splitlines() if z.startswith("- ["))
    assert f"(60 Treffer, {eingespielt} eingespielt, {weggelassen} aus Platzgruenden weggelassen)" in block
    assert eingespielt + weggelassen == 60, "Die drei Zahlen muessen aufgehen"


def test_bilanz_steht_auch_ohne_verlust():
    """Nur-bei-Verlust zu melden hiesse, dass Vollstaendigkeit unbelegt
    bleibt. Genau daran krankte der bisherige Zustand: niemand vermisst, was
    er nie gesehen hat."""
    block, weggelassen = hook._auf_budget_kuerzen(_block(2))
    assert weggelassen == 0
    assert "(2 Treffer, 2 eingespielt, 0 aus Platzgruenden weggelassen)" in block


def test_rahmen_bleibt_immer_stehen():
    """Auch wenn eine EINZIGE Zeile das Budget schon sprengt: ein Block ohne
    Rahmen waere unlesbar, und ohne Bilanz waere der Verlust wieder still."""
    block, weggelassen = hook._auf_budget_kuerzen(
        _block(3, laenge=hook.EINSPIELUNG_MAX_BYTES * 2))
    assert block.startswith("<knowledge-recall>")
    assert block.endswith("</knowledge-recall>")
    assert "(3 Treffer, 0 eingespielt, 3 aus Platzgruenden weggelassen)" in block


def test_gekuerzt_wird_von_hinten():
    """Die Reihenfolge IST die Rangfolge des Abrufs -- vorne steht das
    Staerkste. Wer von vorne kuerzt, wirft die besten Treffer weg und
    behaelt die schwaechsten."""
    block, _ = hook._auf_budget_kuerzen(_block(60))
    behalten = [z for z in block.splitlines() if z.startswith("- [")]
    assert behalten[0].startswith("- [0] "), "Der staerkste Treffer muss bleiben"
    nummern = [int(z.split("]")[0][3:]) for z in behalten]
    assert nummern == sorted(nummern) and nummern[0] == 0


def test_budget_ist_ueber_umgebung_aenderbar(monkeypatch):
    """8000 ist ein gemessener Korridor, keine bekannte Konstante des
    kappenden Glieds. Ein besserer Messwert darf keine Codeaenderung
    verlangen."""
    monkeypatch.setattr(hook, "EINSPIELUNG_MAX_BYTES", 1200)
    block, weggelassen = hook._auf_budget_kuerzen(_block(60))
    assert len(block.encode("utf-8")) <= 1200
    assert weggelassen > 50
