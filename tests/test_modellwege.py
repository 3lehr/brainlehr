"""Ein toter Modell-Endpunkt meldet sich nicht von selbst.

ZWEIMAL AM 2026-08-20 passiert, beide Male unbemerkt:

1. kern/nachrangung.modell() zeigte fest auf Ollama (11434). Dort lauschte
   niemand -- der Betreiber arbeitet mit LM Studio (1234). Jeder Aufruf fiel
   in den Rueckfall "urspruengliche Reihenfolge". Kein Fehler, kein Log; der
   Aufrufer sieht es nur daran, dass sich nichts aendert.
2. knowledge_add schrieb 13 Eintraege ohne Vektor, weil der Einbettungsdienst
   nicht antwortete. Der Eintrag ist gueltig und ueber die Bedeutungssuche
   unauffindbar -- genau die Haelfte des Abrufs, um die es geht.

Beide Male war der Zustand ueber einen einzigen HTTP-Aufruf feststellbar. Es
fragte nur niemand. Dieser Melder fragt.
"""
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent.parent / "melder"),
                str(Path(__file__).resolve().parent.parent)]
import modellwege as mw  # noqa: E402


def test_erreichbarer_dienst_gilt_als_gesund():
    lage = mw.pruefe(pruefer=lambda url: True)
    assert all(w["erreichbar"] for w in lage["wege"])
    assert lage["tote"] == 0


def test_toter_dienst_wird_gemeldet():
    """DER FALL, um den es geht -- und er ist der Normalfall, nicht die
    Ausnahme: ein Dienst, den niemand gestartet hat."""
    lage = mw.pruefe(pruefer=lambda url: False)
    assert lage["tote"] == len(lage["wege"])
    text = mw.als_text(lage)
    assert "nicht erreichbar" in text


def test_meldung_nennt_die_FOLGE_nicht_nur_den_zustand():
    """Ein Melder, der nur 'Dienst weg' sagt, laesst den Leser raten, was das
    kostet. Beide Faelle von heute waren still -- die Folge ist die
    Information, nicht der Port."""
    text = mw.als_text(mw.pruefe(pruefer=lambda url: False))
    assert "Vektor" in text or "unauffindbar" in text
    assert "Reihenfolge" in text or "Nachrangung" in text


def test_schweigt_wenn_alles_laeuft():
    """NEGATIVFALL: Ein Melder, der immer etwas sagt, wird ueberlesen.
    Laeuft alles, gibt es nichts zu melden."""
    assert mw.als_text(mw.pruefe(pruefer=lambda url: True)) == ""


def test_endpunkte_kommen_aus_der_umgebung(monkeypatch):
    """Die Vorgabe darf nicht fest verdrahtet sein -- genau daran lag Fall 1."""
    monkeypatch.setenv("BRAINLEHR_MODELL_ENDPUNKT", "http://beispiel:9999/v1/chat/completions")
    lage = mw.pruefe(pruefer=lambda url: True)
    assert any("beispiel:9999" in w["url"] for w in lage["wege"])
