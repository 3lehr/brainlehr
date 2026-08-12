"""Aufgabe 46 (PLAN_PARALLEL_2026-08-13): satzart() klassifizierte
Maschinentext (Task-Notifications u.ae.) als 'auftrag', BEVOR der
Maschinentext-Filter (_ist_echte_frage) ihn ausscheidet -- gemessen
2026-08-12, Commit faf9f64: der Rohbestand-Auftragszweig war dadurch um
2852 von 3806 Zeilen aufgeblaeht. echtkorpus.py selbst war nicht betroffen
(satzart() wird dort erst NACH dem Filter aufgerufen), aber
trichter_fragen.roh_nachrichten_je_satzart() ruft satzart() bewusst VOR dem
Filter auf (das ist der ganze Witz des Trichters) und uebernahm die
Fehlklassifikation direkt in die Rohzahl.

Rot-Probe (siehe Auftrag): vor der Korrektur klassifizierte satzart() eine
echte, mehrzeilige Task-Notification als 'auftrag' (mehrzeilig_mit_
ueberschrift bzw. langer_fliesstext griff frueher als der Maschinentext-
Check). test_echte_task_notification_ist_maschinentext_nicht_auftrag war
rot, bis MASCHINENTEXT.search() an den Anfang von satzart() wanderte.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "messungen", "melder")]

import echtkorpus as ek  # noqa: E402

# Wortlaut wie er tatsaechlich im recall_log auftaucht: mehrzeilig, mit
# ueberschriftartiger erster Zeile -- genau die Form, die die alte
# Reihenfolge als 'auftrag' durchliess.
ECHTE_TASK_NOTIFICATION = (
    "<task-notification>\n"
    "AUFGABE ABGESCHLOSSEN\n"
    "Der Agent hat die Migration fertiggestellt und alle Tests bestanden.\n"
    "</task-notification>")

# Negativfall: eine echte menschliche Nachricht, die zufaellig das Wort
# 'task' enthaelt -- darf NICHT als Maschinentext ausgeschieden werden, nur
# weil der Wortlaut oberflaechlich aehnlich klingt.
MENSCHLICHE_NACHRICHT_MIT_TASK_WORT = (
    "Kannst du die Task-Liste fuer heute kurz priorisieren? Ich habe drei "
    "Themen und weiss nicht, womit ich anfangen soll.")


def test_echte_task_notification_ist_maschinentext_nicht_auftrag():
    assert ek.satzart(ECHTE_TASK_NOTIFICATION) == "maschine", \
        "eine echte Task-Notification wurde als 'auftrag' statt als " \
        "Maschinentext klassifiziert"


def test_menschliche_nachricht_mit_wort_task_bleibt_erhalten():
    # Gegenprobe zur vorigen Pruefung: der Filter darf nicht auf das blosse
    # Wort 'task' anspringen, sonst waere er zu grob, um etwas zu pruefen.
    art = ek.satzart(MENSCHLICHE_NACHRICHT_MIT_TASK_WORT)
    assert art != "maschine", \
        "eine echte menschliche Nachricht wurde faelschlich als " \
        "Maschinentext ausgeschieden, nur weil sie das Wort 'task' enthaelt"
    assert ek._ist_echte_frage(MENSCHLICHE_NACHRICHT_MIT_TASK_WORT), \
        "eine echte menschliche Nachricht mit dem Wort 'task' wurde verworfen"
