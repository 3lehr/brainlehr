#!/usr/bin/env python3
"""foederation.py -- B5: wer ist DIESE Instanz, und welcher fremden traut sie?

Plan: docs/PLAN_B5_FOEDERATION_2026-08-10.md · Entwurf: Knoten 7c8df4e7

DER BEFUND, der diesen Bau ausgeloest hat: `PRAGMA application_id` steht auf
1112689746, das ist ASCII "BRLR". Sie ist eine GATTUNGSkennung -- sie sagt
"diese Datei ist eine brainlehr-Datenbank", und jeder Klon traegt dieselbe. Eine
INSTANZkennung sagt "diese Datei ist DIESE Instanz", und genau die fehlte. Ohne
sie ist der Satz "ein Ausweis aus Instanz B" nicht formulierbar -- es gibt kein
B. (Im Quelltext kam application_id ausserdem an keiner einzigen Stelle vor.)

DREI REGELN, die diesen Bau bestimmen:

1. VERTRAUEN IST NICHT TRANSITIV. Traut A der Instanz B und B der Instanz C,
   dann traut A NICHT C. Sonst ist die schwaechste Instanz im Verbund der Zugang
   zu allen -- und niemand merkt es, weil jede einzelne Beziehung vernuenftig
   aussieht. Technisch: diese Datei kennt nur DIREKTE Eintraege und loest
   nichts ueber Dritte auf. Dieselbe Schranke wie die Weiterdelegation beim
   Mandat, eine Ebene hoeher.

2. ERREICHBARKEIT IST KEIN VERTRAUEN. Ein Eintrag entsteht nur durch
   ausdrueckliche Aufnahme, nie durch einen Kontakt.

3. DIE VERTRAUENSLISTE IST EINE OBERGRENZE, KEIN RECHTEVERLEIH. Der Eintrag
   sagt HOECHSTENS; was ein fremder Ausweis wirklich darf, ist der SCHNITT aus
   seinen eigenen Rollen und dieser Grenze. Eine Obergrenze kann nur wegnehmen
   -- wie der Zweck in der Zugriffskette und wie das Mandat.

WO DIE DINGE LIEGEN:
- Instanzkennung in knowledge_config: sie beschreibt DIESE Datenbank. Laege sie
  daneben, waeren Kopie und Kennung trennbar, und ein Backup hiesse ploetzlich
  anders als sein Original.
- Vertrauensliste neben der Ausweisdatei, NICHT in der Datenbank: wer die
  Datenbank oeffnen kann, aenderte sonst die Vertrauensliste (L-bd1562).
  Vertrauen ist eine Zugangsentscheidung und gehoert dorthin, wo der Zugang
  entschieden wird -- dieselbe Begruendung wie bei den Ausweisen (ADR-002).

DER KLON-FALL, ehrlich: Eine Kennung wandert beim Kopieren mit. Fuer ein BACKUP
ist das richtig (es IST dieselbe Instanz), fuer eine ABSPALTUNG falsch (eine
zweite Abteilung ist eine andere). Automatisch unterscheidbar ist das nicht --
die Datei sieht in beiden Faellen gleich aus. Darum der ausdrueckliche Befehl
--neue-instanz, der die Kennung neu wuerfelt und die alte im Protokoll vermerkt.

WAS DIESE DATEI NICHT TUT: Sie macht Foederation AUSSAGBAR, nicht BENUTZBAR.
Es gibt keinen Netzwerkverkehr; dafuer fehlt weiterhin ADR-001 (HTTP).

Aufruf:
    python3 foederation.py --wer-bin-ich
    python3 foederation.py --vertrauen <kennung> --name <name> --hoechstens leser
    python3 foederation.py --liste
    python3 foederation.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import argparse
import json
import os
import secrets
import sqlite3
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

import zeitmarke

sys.path.insert(0, str(_w.parent))
import ausweis  # noqa: E402

# knowledge_config.updated_at ist im Betriebsschema NOT NULL. Der Selbsttest
# baute die Tabelle zuerst von Hand ohne diese Spalte und war gruen, waehrend
# der erste echte Lauf mit IntegrityError abbrach -- genau die Fehlklasse aus
# L-7e0823 (Testschema weicht vom Betriebsschema ab). Seither zieht der
# Selbsttest die Definition aus schema.sql statt sie nachzubauen.
_EINFUEGEN = ("INSERT OR REPLACE INTO knowledge_config (key, value, updated_at) "
              "VALUES (?,?,?)")

SCHLUESSEL_KENNUNG = "instanz_kennung"
SCHLUESSEL_NAME = "instanz_name"
ENV_VERTRAUEN = "BRAINLEHR_VERTRAUEN"


def vertrauensdatei() -> Path:
    roh = os.environ.get(ENV_VERTRAUEN)
    if roh:
        return Path(roh)
    return ausweis.ausweisdatei().parent / "vertrauen.json"


# --- B5.1: wer bin ich -----------------------------------------------------

def _db(pfad=None, schreibend: bool = False) -> sqlite3.Connection:
    if pfad is None:
        import knowledge_mcp_server as kms
        pfad = kms.DB_PATH
    if schreibend:
        conn = sqlite3.connect(str(pfad))
    else:
        conn = sqlite3.connect(f"file:{pfad}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def kennung(pfad=None, *, erzeugen: bool = True) -> tuple[str, str]:
    """(kennung, name) dieser Instanz. Wird beim ersten Lauf erzeugt.

    Die Kennung ist Zufall, kein abgeleiteter Wert: ein Rechnername ist
    instabil (Rechner werden umbenannt, Instanzen wandern, zwei Instanzen auf
    einem Rechner kollidieren), und ein Hash ueber den Inhalt aenderte sich mit
    jedem Schreibvorgang."""
    conn = _db(pfad)
    try:
        vorhanden = {r["key"]: r["value"] for r in conn.execute(
            "SELECT key, value FROM knowledge_config WHERE key IN (?,?)",
            (SCHLUESSEL_KENNUNG, SCHLUESSEL_NAME))}
    finally:
        conn.close()
    if vorhanden.get(SCHLUESSEL_KENNUNG):
        return vorhanden[SCHLUESSEL_KENNUNG], vorhanden.get(SCHLUESSEL_NAME, "")
    if not erzeugen:
        return "", ""
    return _erzeuge(pfad, grund="erstanlage")


def _erzeuge(pfad, *, grund: str, name: str | None = None) -> tuple[str, str]:
    neu = secrets.token_hex(8)
    conn = _db(pfad, schreibend=True)
    try:
        alt = conn.execute("SELECT value FROM knowledge_config WHERE key=?",
                           (SCHLUESSEL_KENNUNG,)).fetchone()
        jetzt = zeitmarke.jetzt()
        conn.execute(_EINFUEGEN, (SCHLUESSEL_KENNUNG, neu, jetzt))
        if name is not None:
            conn.execute(_EINFUEGEN, (SCHLUESSEL_NAME, name, jetzt))
        # Die abgeloeste Kennung bleibt stehen -- sonst ist nach einer
        # Abspaltung nicht mehr feststellbar, wovon abgespalten wurde, und
        # uebernommenes Wissen verliert seine Herkunft.
        if alt and alt["value"]:
            conn.execute(
                _EINFUEGEN,
                (f"instanz_kennung_vorher_{datetime.now(timezone.utc):%Y%m%dT%H%M%S}",
                 f"{alt['value']} ({grund})", jetzt))
        conn.commit()
    finally:
        conn.close()
    return neu, (name or "")


def neue_instanz(pfad=None, name: str | None = None) -> tuple[str, str]:
    """Abspaltung: diese Kopie wird eine EIGENE Instanz.

    Nur ausdruecklich aufrufen. Ein Backup soll die Kennung behalten -- es ist
    dieselbe Instanz."""
    return _erzeuge(pfad, grund="abspaltung", name=name)


# --- B5.2: wem traue ich ---------------------------------------------------

def _lies_vertrauen(pfad: Path | None = None) -> list[dict]:
    pfad = pfad or vertrauensdatei()
    if not pfad.exists():
        return []
    modus = pfad.stat().st_mode
    if modus & (stat.S_IRWXG | stat.S_IRWXO):
        print(f"foederation: {pfad} ist fuer Gruppe/Andere zugaenglich "
              f"(0{modus & 0o777:o}) -- ignoriert. Beheben: chmod 600 {pfad}",
              file=sys.stderr)
        return []
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as fehler:
        print(f"foederation: {pfad} nicht lesbar ({fehler}) -- ignoriert.",
              file=sys.stderr)
        return []
    eintraege = daten.get("vertrauen") if isinstance(daten, dict) else None
    return eintraege if isinstance(eintraege, list) else []


def vertraue(fremde_kennung: str, *, name: str = "", hoechstens: str = "leser",
             pfad: Path | None = None, eigene: str | None = None) -> None:
    """Nimmt eine fremde Instanz in die Vertrauensliste auf.

    `hoechstens` ist eine OBERGRENZE, kein Verleih -- siehe Modulkopf, Regel 3."""
    if not fremde_kennung or not fremde_kennung.strip():
        raise ValueError("Instanzkennung darf nicht leer sein")
    if hoechstens not in ausweis.ROLLEN:
        raise ValueError(f"unbekannte Rolle {hoechstens!r}. "
                         f"Bekannt: {sorted(ausweis.ROLLEN)}")
    if eigene is None:
        try:
            eigene = kennung(erzeugen=False)[0]
        except Exception:  # noqa: BLE001 -- ohne DB gibt es keine eigene Kennung
            eigene = ""
    if eigene and fremde_kennung == eigene:
        raise ValueError(
            "Das ist die eigene Instanz. Man buergt nicht fuer sich selbst — "
            "ein Selbsteintrag wuerde die eigene Rechtevergabe an einer "
            "Obergrenze vorbeifuehren.")

    pfad = pfad or vertrauensdatei()
    eintraege = [e for e in _lies_vertrauen(pfad)
                 if e.get("kennung") != fremde_kennung]
    eintraege.append({"kennung": fremde_kennung, "name": name,
                      "hoechstens": hoechstens,
                      "seit": zeitmarke.jetzt()})
    pfad.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(pfad, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "vertrauen": eintraege}, f,
                  ensure_ascii=False, indent=2)
        f.write("\n")
    os.chmod(pfad, 0o600)


def obergrenze(fremde_kennung: str, pfad: Path | None = None) -> str | None:
    """Welche Rolle darf ein Ausweis dieser Instanz HOECHSTENS haben?

    None = kein Vertrauen. Vorgabe ist deny: eine Instanz, die nicht in der
    Liste steht, ist nicht anerkannt -- Nichteintrag IST die Ablehnung, darum
    braucht es keine Sperrliste.

    KEINE AUFLOESUNG UEBER DRITTE: die Liste wird direkt gelesen, es gibt
    keinen Weg, auf dem das Vertrauen einer fremden Instanz hier wirksam wird
    (Regel 1, Modulkopf)."""
    for e in _lies_vertrauen(pfad):
        if e.get("kennung") == fremde_kennung:
            rolle = e.get("hoechstens")
            return rolle if rolle in ausweis.ROLLEN else None
    return None


def _passt_unter(rolle: str, grenze: str) -> bool:
    """Bleibt `rolle` ganz innerhalb dessen, was `grenze` zulaesst?

    NICHT ueber Zeichenketten vergleichen -- das war der erste Versuch und der
    Selbsttest hat ihn sofort widerlegt: 'wissen:lesen:published' (gast) ist
    als Zeichenkette verschieden von 'wissen:lesen' (leser), obwohl es ENGER
    ist. Der Mengenvergleich liess den Gast deshalb durchfallen, und die
    Obergrenze verlieh ihm daraufhin ihre eigene, weitere Rolle -- also genau
    das Gegenteil einer Grenze.

    Richtig ist der Vergleich ueber die Bezugsweite, die ausweis.bezug_fuer()
    bereits kennt: fuer jedes Recht der Rolle muss die Grenze dasselbe Recht
    mindestens so weit gewaehren."""
    rechte = ausweis.ROLLEN.get(rolle, ())
    if not rechte:
        return False
    r_aus = ausweis.Ausweis(name="_r", rollen=(rolle,), beglaubigt=True)
    g_aus = ausweis.Ausweis(name="_g", rollen=(grenze,), beglaubigt=True)
    for recht in rechte:
        if recht == "*":
            return "*" in ausweis.ROLLEN.get(grenze, ())
        modul, _, rest = recht.partition(":")
        aktion = rest.partition(":")[0]
        eigen = ausweis.bezug_fuer(r_aus, f"{modul}:{aktion}")
        erlaubt = ausweis.bezug_fuer(g_aus, f"{modul}:{aktion}")
        if erlaubt is None:
            return False
        if ausweis._BEZUG_WEITE[erlaubt] < ausweis._BEZUG_WEITE[eigen]:
            return False
    return True


def wirksame_rollen(fremde_kennung: str, rollen_des_ausweises,
                    pfad: Path | None = None) -> tuple[str, ...]:
    """Der SCHNITT aus den Rollen des fremden Ausweises und der Obergrenze.

    Die Obergrenze verleiht nichts: steht dort 'schreiber' und der Ausweis
    traegt nur 'leser', bleibt es bei 'leser'. Und umgekehrt schneidet sie ab.
    Verglichen wird ueber die RECHTE, nicht ueber Rollennamen -- 'leser' als
    Obergrenze soll auch einen 'fachkundig'-Ausweis beschneiden, obwohl die
    Namen nichts miteinander zu tun haben."""
    grenze = obergrenze(fremde_kennung, pfad)
    if grenze is None:
        return ()
    behalten = [r for r in rollen_des_ausweises if _passt_unter(r, grenze)]
    # Traegt der Ausweis keine Rolle, die ganz unter die Grenze passt, gilt die
    # Grenze selbst -- sonst verloere ein 'fachkundig'-Ausweis unter der Grenze
    # 'leser' ALLE Rechte, obwohl Lesen ausdruecklich erlaubt ist.
    return tuple(sorted(behalten)) if behalten else (grenze,)


# --- Selbsttest ------------------------------------------------------------

def _config_ddl() -> str:
    """Die Tabellendefinition aus schema.sql -- nicht nachgebaut.

    Ein handgebautes Testschema ist gruen und der Betrieb bricht ab, sobald
    eine Spalte fehlt (hier: updated_at NOT NULL). Lieber die Quelle lesen."""
    # _w ist bereits die Wurzel (siehe Schleife oben, die genau bis zum
    # Ordner mit schema.sql hochlaeuft) -- _w.parent zeigte einen Ordner zu
    # hoch und brach den Selbsttest ausserhalb dieses Repos.
    text = (_w / "schema.sql").read_text(encoding="utf-8")
    start = text.index("CREATE TABLE IF NOT EXISTS knowledge_config")
    return text[start:text.index(");", start) + 2]


def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "k.db"
        conn = sqlite3.connect(str(db))
        conn.executescript(_config_ddl())
        conn.commit(); conn.close()
        vpfad = Path(tmp) / "vertrauen.json"

        # --- F2: Kennung wird erzeugt --------------------------------------
        k1, _ = kennung(db)
        assert k1 and len(k1) == 16, k1
        # --- F1: zweimal lesen -> dieselbe ---------------------------------
        assert kennung(db)[0] == k1
        # --- erzeugen=False liefert leer statt zu erzeugen ------------------
        leer = Path(tmp) / "leer.db"
        c = sqlite3.connect(str(leer))
        c.executescript(_config_ddl())
        c.commit(); c.close()
        assert kennung(leer, erzeugen=False) == ("", "")

        # --- F4: Abspaltung wuerfelt neu, alte bleibt auffindbar ------------
        k2, _ = neue_instanz(db, name="zweigstelle")
        assert k2 != k1
        c = _db(db)
        alte = [r["value"] for r in c.execute(
            "SELECT value FROM knowledge_config WHERE key LIKE 'instanz_kennung_vorher_%'")]
        c.close()
        assert any(k1 in a for a in alte), f"alte Kennung verloren: {alte}"

        # --- F5: Vorgabe deny ----------------------------------------------
        assert obergrenze("fremde-instanz", vpfad) is None
        assert wirksame_rollen("fremde-instanz", ["betreiber"], vpfad) == ()

        # --- F6: Obergrenze schneidet ab ------------------------------------
        vertraue("instanz-b", name="Abteilung B", hoechstens="leser",
                 pfad=vpfad, eigene=k2)
        assert obergrenze("instanz-b", vpfad) == "leser"
        assert wirksame_rollen("instanz-b", ["schreiber"], vpfad) == ("leser",), \
            "Obergrenze hat einen Schreiber nicht beschnitten"
        assert wirksame_rollen("instanz-b", ["leser"], vpfad) == ("leser",)

        # --- F7: die Grenze verleiht nichts ---------------------------------
        vertraue("instanz-c", hoechstens="schreiber", pfad=vpfad, eigene=k2)
        assert wirksame_rollen("instanz-c", ["gast"], vpfad) == ("gast",), \
            "Obergrenze hat Rechte VERLIEHEN statt nur zu begrenzen"

        # --- F8: nicht transitiv --------------------------------------------
        # instanz-b traut instanz-d (in IHRER Liste, die uns nicht vorliegt).
        # Hier darf daraus nichts folgen -- es gibt gar keinen Weg dorthin.
        assert obergrenze("instanz-d", vpfad) is None, \
            "Vertrauen wurde ueber eine dritte Instanz aufgeloest"

        # --- F9: man buergt nicht fuer sich selbst --------------------------
        try:
            vertraue(k2, pfad=vpfad, eigene=k2)
        except ValueError as f:
            assert "eigene Instanz" in str(f), f
        else:
            raise AssertionError("Selbsteintrag ging durch")

        # --- Grenzwerte ------------------------------------------------------
        for kaputt, kw in ((" ", {}), ("", {}), ("x", {"hoechstens": "gibtsnicht"})):
            try:
                vertraue(kaputt, pfad=vpfad, eigene=k2, **kw)
            except ValueError:
                pass
            else:
                raise AssertionError(f"haette abweisen muessen: {kaputt!r} {kw}")

        # --- F10: zu weite Rechte -> ignoriert ------------------------------
        assert obergrenze("instanz-b", vpfad) == "leser"
        os.chmod(vpfad, 0o644)
        assert obergrenze("instanz-b", vpfad) is None, \
            "weltlesbare Vertrauensliste wurde trotzdem verwendet"
        os.chmod(vpfad, 0o600)
        assert obergrenze("instanz-b", vpfad) == "leser"

        # --- kaputte Datei vertraut niemandem -------------------------------
        kaputt = Path(tmp) / "kaputt.json"
        fd = os.open(kaputt, os.O_WRONLY | os.O_CREAT, 0o600)
        os.write(fd, b"{nicht json"); os.close(fd)
        assert obergrenze("instanz-b", kaputt) is None

    print("foederation.py: Selbsttest gruen")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--wer-bin-ich", action="store_true")
    p.add_argument("--neue-instanz", action="store_true")
    p.add_argument("--name", default=None)
    p.add_argument("--vertrauen", metavar="KENNUNG")
    p.add_argument("--hoechstens", default="leser")
    p.add_argument("--liste", action="store_true")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return 0
    if a.neue_instanz:
        print("Diese Kopie wird eine EIGENE Instanz. Ein Backup braucht das "
              "NICHT — es ist dieselbe Instanz.", file=sys.stderr)
        k, n = neue_instanz(name=a.name)
        print(f"neue Kennung: {k}  Name: {n or '(keiner)'}")
        return 0
    if a.vertrauen:
        vertraue(a.vertrauen, name=a.name or "", hoechstens=a.hoechstens)
        print(f"Vertrauen eingetragen: {a.vertrauen} hoechstens '{a.hoechstens}' "
              f"in {vertrauensdatei()}")
        return 0
    if a.liste:
        eigene, name = kennung(erzeugen=False)
        print(f"Diese Instanz: {eigene or '(noch keine)'}  {name}")
        eintraege = _lies_vertrauen()
        if not eintraege:
            print("Keine fremde Instanz anerkannt (Vorgabe: kein Vertrauen).")
        for e in eintraege:
            print(f"  {e['kennung']}  hoechstens {e['hoechstens']:10s} "
                  f"{e.get('name','')}  seit {e.get('seit','?')[:10]}")
        return 0

    k, n = kennung()
    print(f"Diese Instanz: {k}  Name: {n or '(keiner)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
