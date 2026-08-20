"""Die Antwort des Nachrangers wird geparst -- und der Parser war zu gierig.

DER BEFUND (2026-08-20): `modell()` zog mit `re.findall(r"\\d+", roh)` JEDE
Ziffernfolge aus dem Rohtext. Der Prompt bittet um "NUR die Nummern, durch
Komma getrennt, keine Erklaerung" -- kleine lokale Modelle halten sich daran
nicht zuverlaessig. Eine Vorrede wie "Hier sind die Top 5:" schiebt die 5 an
den ANFANG der Reihenfolge, und der Nachranger ordnet ab da nach einer Zahl
um, die nie ein Kandidat war.

Das faellt nirgends auf: Die Funktion liefert weiterhin eine gueltige
Reihenfolge ueber alle Kandidaten, nur die falsche. Kein Fehler, kein Log,
keine Ausnahme -- die Guete sinkt still.

Der Fix ist ein erzwungenes Ausgabeformat (JSON-Schema an Ollama), nicht ein
strengerer Prompt: Ein Prompt ist eine Bitte, ein Schema eine Sperre im
Dekodierer. Der Rueckfall auf die alte Regex bleibt trotzdem, weil aeltere
Ollama-Fassungen und andere Endpunkte kein Schema koennen.
"""
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent.parent / "kern"),
                str(Path(__file__).resolve().parent.parent)]
import nachrangung as n  # noqa: E402


def test_vorrede_mit_zahl_verfaelscht_die_reihenfolge_nicht():
    """DER FALL, DER DEN BAU AUSLOEST: eine hoefliche Vorrede mit Ziffer."""
    assert n._reihenfolge_aus('Hier sind die Top 5: 3, 1, 0', 4) == [3, 1, 0, 2]


def test_sauberes_json_wird_bevorzugt():
    """Mit Schemazwang kommt genau das zurueck -- kein Raten noetig."""
    assert n._reihenfolge_aus('{"reihenfolge": [2, 0, 1]}', 3) == [2, 0, 1]


def test_rueckfall_auf_zahlen_wenn_kein_json():
    """Ein Endpunkt ohne Schemafaehigkeit darf nicht schlechter dastehen als
    heute -- sonst waere der Einbau eine Verschlechterung fuer alle, die es
    nicht koennen."""
    assert n._reihenfolge_aus('2, 0, 1', 3) == [2, 0, 1]


def test_nichts_wird_weggeworfen():
    """Unveraendert wichtig: Wer beim Umordnen etwas verliert, kann hinterher
    nicht mehr messen, was er verloren hat."""
    assert sorted(n._reihenfolge_aus('{"reihenfolge": [1]}', 4)) == [0, 1, 2, 3]
    assert sorted(n._reihenfolge_aus('Quatsch ohne Zahlen', 3)) == [0, 1, 2]


def test_zahl_ausserhalb_des_bereichs_wird_verworfen():
    """NEGATIVFALL: Ein Modell, das eine 99 nennt, darf keinen Indexfehler
    ausloesen und die 99 nicht in die Reihenfolge bringen."""
    assert n._reihenfolge_aus('{"reihenfolge": [99, 1]}', 3) == [1, 0, 2]


def test_doppelte_nennung_zaehlt_einmal():
    assert n._reihenfolge_aus('{"reihenfolge": [1, 1, 0]}', 3) == [1, 0, 2]


def test_endpunkt_kommt_aus_der_umgebung():
    """Der Endpunkt darf nicht fest verdrahtet sein.

    GEMESSEN 2026-08-20 auf dem Rechner des Betreibers: Der Vorgabewert zeigt
    auf Ollama (Port 11434) -- dort lauscht NIEMAND. Was laeuft, ist LM Studio
    auf Port 1234. Der Nachranger faellt damit bei jedem Aufruf still auf die
    urspruengliche Reihenfolge zurueck: kein Fehler, kein Log, nur Wirkung
    null. Ein erzwungenes Ausgabeformat an einem toten Endpunkt ist keine
    Verbesserung, sondern zwei wirkungslose Dinge uebereinander."""
    import importlib
    import os
    alt = os.environ.get("BRAINLEHR_MODELL_ENDPUNKT")
    try:
        os.environ["BRAINLEHR_MODELL_ENDPUNKT"] = "http://127.0.0.1:1234/v1/chat/completions"
        importlib.reload(n)
        assert n.ENDPUNKT.endswith("/v1/chat/completions")
    finally:
        if alt is None:
            os.environ.pop("BRAINLEHR_MODELL_ENDPUNKT", None)
        else:
            os.environ["BRAINLEHR_MODELL_ENDPUNKT"] = alt
        importlib.reload(n)


def test_openai_form_wird_an_der_pfadform_erkannt():
    """LM Studio spricht OpenAI-kompatibel, Ollama nicht -- Nutzlast und
    Antwortform unterscheiden sich. Erkannt wird es am Pfad, nicht an einer
    zweiten Einstellung: zwei Schalter, die zusammenpassen muessen, gehen
    irgendwann auseinander."""
    assert n._ist_openai("http://127.0.0.1:1234/v1/chat/completions")
    assert not n._ist_openai("http://127.0.0.1:11434/api/generate")


def test_antwort_beider_formen_wird_gelesen():
    """Gegenprobe in beide Richtungen: Ollama legt den Text unter 'response',
    OpenAI unter choices[0].message.content."""
    assert n._text_aus({"response": '{"reihenfolge": [1]}'}) == '{"reihenfolge": [1]}'
    assert n._text_aus({"choices": [{"message": {"content": "2, 0"}}]}) == "2, 0"
    assert n._text_aus({"unbekannt": 1}) == ""


def test_denkfeld_wird_gelesen_wenn_der_inhalt_leer_bleibt():
    """GEMESSEN 2026-08-20 gegen LM Studio, qwen3.8-27b, und das Ergebnis war
    das GEGENTEIL der Erwartung:

        ohne Schemazwang, 285 s:  '{"reihenfolge": [2, 0, 1]}'  -- richtig
        mit  Schemazwang,  15 s:  ''                            -- Rueckfall

    Der Zwang wirkt, aber bei einem Reasoning-Modell landet die
    schemakonforme Ausgabe in `reasoning_content`, waehrend `content` leer
    bleibt. Wer nur `content` liest, macht aus einer richtigen Antwort einen
    stillen Rueckfall -- und das erzwungene Format, das die Guete heben
    sollte, senkt sie.

    Das Denkfeld wird NUR gelesen, wenn der Inhalt leer ist. Denktext ist
    sonst nicht die Antwort, und wer ihn immer nimmt, liest die Ueberlegung
    statt des Ergebnisses."""
    assert n._text_aus({"choices": [{"message": {
        "content": "", "reasoning_content": '{"reihenfolge": [2, 0, 1]}'}}]}) \
        == '{"reihenfolge": [2, 0, 1]}'


def test_inhalt_sticht_das_denkfeld():
    """NEGATIVFALL, und er traegt die halbe Regel: Ist beides da, gilt der
    Inhalt. Sonst liest man die Ueberlegung statt des Ergebnisses."""
    assert n._text_aus({"choices": [{"message": {
        "content": "2, 0, 1", "reasoning_content": "hmm, vielleicht 9?"}}]}) == "2, 0, 1"
