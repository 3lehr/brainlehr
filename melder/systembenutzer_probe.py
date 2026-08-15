#!/usr/bin/env python3
"""
systembenutzer_probe.py — belegt G5: gehoert der Bestand einer ANDEREN
Kennung als der angemeldeten, und kann der angemeldete Benutzer nicht mehr
schreiben?

Vorbereitung fuer den Schritt "eigener Systembenutzer", docs/PLAN_GESAMT
Abschnitt G5 und docs/SICHERHEITSFUNDE_2026-08-14.md Fund O4. Diese Probe
existiert VOR der Aenderung und ist heute rot -- das ist ihr Zweck: der
Beleg, dass sie wirklich etwas misst, statt nur einen Haken zu setzen.

Geprueft werden zwei Dateien, beide aus kern/ausweis.py bzw. kern/auditanker.py
uebernommen (Pfadermittlung dort, hier nur gelesen -- kein Import von kern/):
  - brainlehr.db   (Repo-Wurzel, an schema.sql erkannt)
  - ausweise.json  (~/Desktop/brainlehr-ausweise, override BRAINLEHR_AUSWEISE)

Kriterium "gehoert einer anderen Kennung": Dateieigner-UID != os.getuid().
Kriterium "kein Schreibzugriff": os.access(pfad, os.W_OK) ist False UND die
Gruppen-/Other-Schreibbits sind aus (0600 bzw. 0700 fuer den Ordner).

IMMER exit 0 als Skript (Melder-Konvention) -- der Zustand steht im JSON auf
stdout, nicht im Exit-Code. Fuer die Ratsche (tests/) gibt es die Funktion
pruefe(), die eine klare Antwort liefert statt einen Prozess zu starten.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path


def _repo_wurzel() -> Path:
    w = Path(__file__).resolve().parent
    while not (w / "schema.sql").exists() and w != w.parent:
        w = w.parent
    return w


def _ausweisordner() -> Path:
    override = os.environ.get("BRAINLEHR_AUSWEISE")
    if override:
        return Path(override)
    return Path.home() / "Desktop" / "brainlehr-ausweise"


def _pruefe_datei(pfad: Path, verlangte_bits: int) -> dict:
    """Ein Fund je Datei/Verzeichnis. verlangte_bits: die einzigen erlaubten
    Modus-Bits (z.B. 0600 fuer Dateien, 0700 fuer Verzeichnisse) -- alles
    darueber hinaus (Gruppe/Andere) gilt als zu offen."""
    if not pfad.exists():
        return {
            "pfad": str(pfad),
            "vorhanden": False,
            "fremder_eigner": None,
            "nicht_beschreibbar": None,
            "gilt": False,
            "grund": "Datei/Verzeichnis fehlt -- Probe kann nicht urteilen.",
        }
    st = pfad.stat()
    eigener_uid = os.getuid()
    fremder_eigner = st.st_uid != eigener_uid
    zu_offene_bits = stat.S_IMODE(st.st_mode) & ~verlangte_bits
    eng_genug = zu_offene_bits == 0
    nicht_schreibbar = not os.access(pfad, os.W_OK)
    # G5 gilt erst, wenn BEIDES zutrifft: fremder Eigner UND der angemeldete
    # Benutzer kann tatsaechlich nicht mehr schreiben. Enge Rechte (0600)
    # unter dem EIGENEN Konto reichen nicht -- genau das ist der O4-Befund:
    # 0600 unter der eigenen Kennung wirkt gegen andere lokale Benutzer,
    # nicht gegen den eigenen (der bleibt Eigner und kann jederzeit chmod).
    gilt = fremder_eigner and nicht_schreibbar
    return {
        "pfad": str(pfad),
        "vorhanden": True,
        "eigner_uid": st.st_uid,
        "angemeldeter_uid": eigener_uid,
        "fremder_eigner": fremder_eigner,
        "rechte_eng_genug": eng_genug,
        "nicht_beschreibbar": nicht_schreibbar,
        "gilt": gilt,
        "grund": (
            "Eigner ist ein anderer Systembenutzer, angemeldeter Benutzer kann "
            "nicht schreiben."
            if gilt
            else "Bestand gehoert noch der angemeldeten Kennung -- G5 offen."
        ),
    }


def pruefe() -> dict:
    db = _pruefe_datei(_repo_wurzel() / "brainlehr.db", 0o600)
    ordner = _pruefe_datei(_ausweisordner(), 0o700)
    gesamt = bool(db["gilt"]) and bool(ordner["gilt"])
    return {"g5_erfuellt": gesamt, "brainlehr_db": db, "ausweisordner": ordner}


def main() -> int:
    print(json.dumps(pruefe(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
