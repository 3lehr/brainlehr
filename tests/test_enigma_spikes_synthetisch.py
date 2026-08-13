"""Wacht darüber, dass die beiden Enigma-Studien synthetisch BLEIBEN.

Beide Studien (`test_enigma_crypto_shredding_spike.py`, 125 Zeilen, und
`test_enigma_two_process_spike.py`, 564 Zeilen) sind grün und von guter
Bauform — sie widerlegen Abschwächungen, statt Machbarkeit zu behaupten. Sie
prüfen aber **keinen Produktivpfad**: die tragenden Begriffe ihres
Erlaubnismodells kamen am 2026-08-13 im Produktivcode null Mal vor.

Der Speicher führt ein anderes Modell — die Rolle legt Zweck und Feld fest,
der Ausweis den Empfänger (`knowledge_mcp_server.py`). Ein Rollenmodell kennt
keinen Ablauf und keinen Einzelwiderruf. „Verdrahten" wäre also kein
Anschließen, sondern der Bau des zweiten Modells; die Entscheidung dagegen
steht in `docs/PLAN_ENIGMA_SPIKES_2026-08-13.md`.

**Wozu diese Datei.** 689 Zeilen grüner Testcode ohne Produktivpfad sehen in
jeder Bilanz aus wie Absicherung. Diese Ratsche macht den Zustand prüfbar
statt behauptet: Taucht einer der Begriffe im Produktivcode auf, ist das
Erlaubnismodell im Bau — dann ist der Ausweis „synthetisch" überholt und die
Studien gehören daran gehängt. Der Test schlägt dann an und verlangt eine
Entscheidung, statt sie zu verschlafen.
"""
from __future__ import annotations

from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[1]

# Die tragenden Begriffe des Erlaubnismodells der Studien. Stand 2026-08-13
# alle null Mal im Produktivcode; `recipient` und `nonce` hatten je einen
# Treffer, beide in Kommentaren, und sind deshalb hier nicht aufgeführt --
# ein Kommentar ist kein Modell.
BEGRIFFE = ("grant_id", "expiry", "audience_policy", "protected_edge_reads")

STUDIEN = (
    "tests/test_enigma_crypto_shredding_spike.py",
    "tests/test_enigma_two_process_spike.py",
)


def _produktivdateien() -> list[Path]:
    """Produktivcode: kern/ und der Serverprozess. Nicht tests/, nicht docs/,
    nicht messungen/ -- dort dürfen die Begriffe vorkommen und tun es auch."""
    dateien = sorted((WURZEL / "kern").rglob("*.py"))
    server = WURZEL / "knowledge_mcp_server.py"
    if server.exists():
        dateien.append(server)
    return dateien


def _ist_kommentarzeile(zeile: str) -> bool:
    return zeile.lstrip().startswith("#")


def fundstellen() -> list[tuple[str, int, str]]:
    treffer = []
    for pfad in _produktivdateien():
        for nr, zeile in enumerate(pfad.read_text(encoding="utf-8").splitlines(), 1):
            if _ist_kommentarzeile(zeile):
                continue
            for begriff in BEGRIFFE:
                if begriff in zeile:
                    treffer.append((str(pfad.relative_to(WURZEL)), nr, begriff))
    return treffer


def test_erlaubnismodell_ist_nicht_im_produktivcode():
    """Solange dieser Test grün ist, sind die Studien zu Recht als synthetisch
    ausgewiesen. Wird er rot, ist das KEIN Fehler -- es heißt, jemand baut das
    Erlaubnismodell, und dann muss der Ausweis in beiden Studien fallen und
    ihre Annahmen gegen den echten Speicher geprüft werden."""
    treffer = fundstellen()
    assert not treffer, (
        f"{len(treffer)} Fundstelle(n) eines Erlaubnismodell-Begriffs im "
        "Produktivcode: "
        + ", ".join(f"{p}:{n} ({b})" for p, n, b in treffer)
        + " -- die beiden Enigma-Studien weisen sich als synthetisch aus "
        "(docs/PLAN_ENIGMA_SPIKES_2026-08-13.md). Wird das Modell gebaut, "
        "gehört der Ausweis entfernt und ihre Annahmen an den echten Speicher "
        "gehängt. Diesen Test dann anpassen, nicht überspringen."
    )


def test_kommentar_zaehlt_nicht_als_modell():
    """Gegenprobe zur Auswahl der Begriffe: `recipient` und `nonce` kamen am
    2026-08-13 je einmal vor, beide in Kommentaren. Wäre die Prüfung blind für
    Kommentare, hätte sie zwei falsche Treffer gemeldet und wäre nie grün
    gewesen -- also nie eingebaut worden."""
    assert _ist_kommentarzeile("    # recipient: the role fixes the purpose")
    assert not _ist_kommentarzeile("    recipient = ausweis.empfaenger")


@pytest.mark.parametrize("studie", STUDIEN)
def test_studie_weist_sich_selbst_als_synthetisch_aus(studie):
    """Der Ausweis steht im Kopf der Datei und muss dort bleiben -- sonst
    trägt der Zustand nur diese Ratsche, und wer die Studie öffnet, sieht ihn
    nicht."""
    kopf = (WURZEL / studie).read_text(encoding="utf-8")[:400].lower()
    assert "synthetic" in kopf or "synthetisch" in kopf, (
        f"{studie} weist sich im Kopf nicht mehr als synthetisch aus. Entweder "
        "wurde sie an den echten Speicher gehängt -- dann gehört der Ausweis "
        "raus UND dieser Test angepasst -- oder der Hinweis ist beim Umbauen "
        "verlorengegangen."
    )
