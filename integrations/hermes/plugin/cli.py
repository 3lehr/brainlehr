"""`hermes brainlehr ...` -- die Diagnose, die ein fremder Nutzer zuerst braucht.

WARUM AUSGERECHNET DAS ALS EINZIGER BEFEHL: Wenn brainlehr im Menue steht und
trotzdem nichts tut, gibt es vier Gruende, die sich fuer den Nutzer alle gleich
anfuehlen -- Bestand nicht gefunden, Server antwortet nicht, kein Ausweis,
Einbettungsdienst tot. `is_available()` kennt sie einzeln und nennt sie im Log.
Aber ein Log liest niemand, der gerade zum ersten Mal etwas einrichtet. Dieser
Befehl holt genau diesen Grund an die Oberflaeche. Alles andere kann brainlehr
bereits ueber seine MCP-Werkzeuge, und ein zweiter Weg dorthin waere Zierat.

WIE HERMES DAS FINDET (plugins/memory/__init__.py::discover_plugin_cli_commands):
* nur fuer den AKTIVEN Anbieter (`memory.provider` in config.yaml),
* `register_cli` als Name der Aufsetzfunktion,
* und der Handler wird ueber `getattr(cli_mod, f"{name}_command")` geholt --
  also `brainlehr_command`. Ein anders benannter Handler wird still nicht
  gefunden; der Befehl stuende dann ohne Wirkung im Menue.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _provider():
    """Den Provider aus der Nachbardatei laden -- per Pfad, nicht per
    Paketimport. Hermes laedt cli.py unter einem synthetischen Paketnamen
    (`_hermes_user_memory.brainlehr.cli`), unter dem ein `from . import`
    nur dann traegt, wenn Hermes die Elternhuelle vorher registriert hat.
    Ueber den Pfad geht es in beiden Faellen -- auch im Pruefstand ohne
    Hermes."""
    pfad = Path(__file__).resolve().parent / "brainlehr_provider.py"
    name = "_brainlehr_provider_cli"
    modul = sys.modules.get(name)
    if modul is None:
        spec = importlib.util.spec_from_file_location(name, str(pfad))
        modul = importlib.util.module_from_spec(spec)
        sys.modules[name] = modul
        spec.loader.exec_module(modul)
    return modul.BrainlehrProvider()


def register_cli(subparser) -> None:
    """Unterbefehle unter `hermes brainlehr` anmelden."""
    unter = subparser.add_subparsers(dest="brainlehr_befehl")
    unter.add_parser(
        "pruefen",
        help="Pruefen, ob brainlehrs MCP-Server erreichbar ist, und was er meldet",
    )


def brainlehr_command(args) -> int:
    """0 heisst einsatzbereit, 1 heisst nicht -- und der Grund steht dabei.

    Der Rueckgabewert ist der Teil, der in einem Skript zaehlt: eine Diagnose,
    die nur Text ausgibt, laesst sich nicht abfragen."""
    if getattr(args, "brainlehr_befehl", None) not in (None, "pruefen"):
        print(f"  Unbekannter Befehl: {args.brainlehr_befehl}")
        return 2

    p = _provider()
    grund = p._grund_fuer_unverfuegbar()
    try:
        if grund:
            print("\n  brainlehr: nicht einsatzbereit / not ready\n")
            print(f"  Grund / reason:\n    {grund}\n")
            return 1

        klient = p._verbindung()
        werkzeuge = klient.werkzeugnamen() or []
        stats = klient.ruf("knowledge_stats", {}) or {}
        print("\n  brainlehr: einsatzbereit / ready\n")
        print(f"    Datenbank / store:  {stats.get('db_path', '?')}")
        print(f"    Knoten / nodes:     {stats.get('nodes_total', '?')}")
        print(f"    Werkzeuge / tools:  {len(werkzeuge)}")
        print(f"    Mitschrift / sync:  "
              f"{'an / on' if p.mitschrift else 'aus / off (Vorgabe)'}\n")
        return 0
    finally:
        # Der Server ist ein eigener Prozess. Ein Diagnosebefehl, der einen
        # zurueckliesse, waere selbst das Problem, das er suchen soll.
        p.shutdown()
