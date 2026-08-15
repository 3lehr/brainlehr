"""Test fuer melder/plan_bestandsabgleich.py.

Grenzwert, Negativfall und der Attrappen-Selftest stehen im Modul selbst
(plan_bestandsabgleich._selftest, laeuft ueber test_alle_selftests.py als
Teil der vollen Suite). Diese Datei ist die eigentliche Abnahme: die
Positivkontrolle gegen den ECHTEN Plan und den ECHTEN Bestand
(Pruefstand-Regel 2026-08-15) -- genau die vier Faelle, die am 2026-08-15
zweimal falsch als offen beauftragt wurden, plus die fuenf bekannt offenen
als Negativfall. Reiner Lesezugriff, nichts wird geschrieben."""
from __future__ import annotations

import plan_bestandsabgleich as pba


def test_selftest():
    pba._selftest()


def test_positivkontrolle_die_vier_bekannten_faelle():
    """81 (Kanten, 5a4d65b), 85 (ausloeserlos.py, b3dfc6f), 84
    (vorschlagsmelder.py, 38bebd9), J1 (schemastand.py, 88aaf73/c90f932) --
    wurden am 2026-08-15 zweimal als 'offen' beauftragt, obwohl laengst
    gebaut. Findet der Melder sie nicht, ist er nutzlos."""
    plan_text = pba.STANDARD_PLAN.read_text(encoding="utf-8")
    commits = pba._git_commits(pba._W)
    gefunden = {k.kennung for k in pba.finde_kandidaten(plan_text, commits)}
    for erwartet in ("81", "85", "84", "J1"):
        assert erwartet in gefunden, f"Positivkontrolle verfehlt: {erwartet} nicht gefunden"


def test_negativfall_bekannt_offene_aufgaben():
    """H4, H5, H7, H10 sind laut Plan (Stand 2026-08-15) offen -- H6 wird
    im Plan nie als eigener Backtick-Ausdruck genannt (nur ueber die Kurz-
    form 'H2 bis H7'), zaehlt darum nicht als Extraktions-Negativfall."""
    plan_text = pba.STANDARD_PLAN.read_text(encoding="utf-8")
    commits = pba._git_commits(pba._W)
    gefunden = {k.kennung for k in pba.finde_kandidaten(plan_text, commits)}
    for offen in ("H4", "H5", "H7", "H10"):
        assert offen not in gefunden, f"Falschtreffer: {offen} ist laut Plan offen"


def test_grenzwert_plandatei_ohne_kennungen():
    assert pba.kennungen_im_plan("kein einziger Backtick-Ausdruck hier.") == []
    assert pba.finde_kandidaten("kein einziger Backtick-Ausdruck hier.", []) == []


def test_falschtrefferrate_am_echten_plan_unter_der_haelfte():
    """Schlaegt der Melder bei der Mehrheit der Planzeilen an, ist er eine
    Fehlkonstruktion (L-528f0c), keine Heuristik. Gemessen 2026-08-15:
    31 von 70 Kennungen (44 %)."""
    plan_text = pba.STANDARD_PLAN.read_text(encoding="utf-8")
    commits = pba._git_commits(pba._W)
    alle = pba.kennungen_im_plan(plan_text)
    gefunden = {k.kennung for k in pba.finde_kandidaten(plan_text, commits)}
    assert len(gefunden) < len(alle) / 2, (len(gefunden), len(alle))
