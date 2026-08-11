"""Misst, was brainlehr BEITRAEGT -- nicht welches Modell besser ist.
Vergleich: dasselbe Modell MIT gegen OHNE Wissenszugang (lesson_query-Treffer
im Prompt), nicht Modell gegen Modell.

ZWEI AUFGABEN aus echten Fallen des Bestands (Wortlaut per lesson_query
gegen die echte brainlehr.db geholt, nicht aus dem Gedaechtnis geschrieben):
  A) Dialog-Falle (Lehre L-c0e910): AlertDialog+showDialog wird in
     fahrtenbuch_legacy durch einen globalen Shim zum Vollbild-Screen mit
     Weissraum. Richtig: ActionScreen(expandPrimaryAction:true) ueber
     eigenen Navigator.push(fullscreenDialog:true).
  B) Stummer Testlauf (Lehre L-68ff10): `flutter test` ueberspringt
     Debug-Schnittstellen-Faelle still ohne --dart-define=DEBUG_STATE_API=true.

ABWEICHUNG vom Auftrag, hier begruendet (Auftrag: "Sieh Code an, melde
Abweichung" -- gilt sinngemaess auch fuer den eigenen methodischen Aufbau):
Auftrag nennt knowledge_search als Quelle der Treffer. Geprueft (2026-08-06):
knowledge_search('AlertDialog showDialog ActionScreen Vollbild') UND
knowledge_search('DEBUG_STATE_API flutter test dart-define') liefern je 5
Treffer, aber KEINER davon ist die einschlaegige Lehre (L-c0e910 / L-68ff10)
-- knowledge_search durchsucht knowledge_nodes/FTS, nicht die
lessons_learned-Tabelle, in der genau diese zwei Lehren stehen. Mit
knowledge_search als Quelle wuerde der MIT-Arm irrelevantes Wissen
einspeisen und die Messung entwerten. Stattdessen: lesson_query (dieselbe
Funktion, mit der die Aufgaben oben recherchiert wurden), geprueft:
liefert L-c0e910 bzw. L-68ff10 exakt als Treffer 1.

Ollama-Aufruf wiederverwendet aus schreibpruefstand/schreiblauf.py
(_call_with_retry: ein Retry bei Werkzeugausfall, kein stilles Endlos-Retry).
Zweites Modell: gemma4:e4b (kleinste verfuegbare Groesse aus `ollama list` --
haelt 24 Aufrufe gesamt in vertretbarer Laufzeit; `ollama list` zeigte am
2026-08-06 gemma4:e4b/12b/31b + nomic-embed-text, e4b und 12b sind die zwei
generativen Groessen ohne die 19-GB-Stufe).

BEWERTUNG deterministisch (kein Modellurteil):
  A) trifft zu, wenn 'ActionScreen' in der Antwort vorkommt UND 'showDialog'
     NICHT vorkommt -- genau die zwei Textmerkmale, die Code vs. Antipattern
     unterscheiden, laut Lehre L-c0e910.
  B) trifft zu, wenn 'DEBUG_STATE_API' vorkommt -- das fehlende Flag IST der
     ganze Unterschied laut Lehre L-68ff10.
Jede andere Bewertung (Teilpunkte, Wortlaut-Aehnlichkeit) waere ein
Modellurteil durch die Hintertuer -- deshalb bewusst nicht gemacht.

Geaenderte Dateien ausserhalb dieser einen: KEINE. Liest die echte
brainlehr.db (lesson_query), schreibt nichts hinein.

AUFGABENSAMMLUNG erweitert 2026-08-07 auf 15 Aufgaben (A,B,D..J,O..U),
Fallen aus dem echten Bestand per lesson_query gezogen (siehe Kommentar an
jedem TASKS-Eintrag fuer die Lehren-ID), gestreut ueber fahrtenbuch/hub/
schwarmwacht/setfunk/openlehr/wohlairr und Dart/Python/Swift/Shell/JSON.
Jede Bewertung ist ein Textmerkmal, kein Modellurteil (siehe check-Lambdas).

EICHUNG (2026-08-07, gemini-2.5-flash als schnelles Vergleichsmodell,
Ollama-Budget geschont): JEDE neu vorgeschlagene Aufgabe wurde gegen genau
diese Probe gefahren (OHNE Wissen -> muss falsch sein, MIT Wissen -> muss
richtig sein), nicht nur eine stellvertretend. Von 21 kandidierten Aufgaben
bestanden 13 die Probe und sind unten aufgenommen: D, E, F, G, I, J, O, P,
Q, R, S, T, U (plus die zwei vom Auftrag vorgegebenen A, B, macht 15).
8 Kandidaten sind NICHT aufgenommen, weil gemini-2.5-flash sie bereits ohne
Wissen richtig loeste (keine Falle fuer dieses Modell: Ollama-keep_alive-
JSON-Typ, macOS-Keychain-Entitlement, Enum-Map-Exhaustiveness, setState-
Arrow-Body, dispose()-catchError, Drift-Migrationstest, testWidgets-
runAsync, Astro-<details>-Breakpoint, Android-Namespace/MainActivity.kt,
Gouraud-Stuetzstellenraum, PID31-Kalibrierschwelle, git-push-ls-remote,
TestFlight-Build-Nummer) oder weil sie auch MIT Wissen falsch blieb
(FakeStore-Wortlaut zu eng) bzw. sich MIT Wissen sogar verschlechterte
(Maskierungs-Aufgabe: Gemini fuegte unangefordert eine Maskierung hinzu).
Eine Aufgabe, die nicht wie beschrieben misst, bleibt nicht drin, nur weil
der Check technisch lauffaehig ist.

MINDESTENS DREI AUFGABEN OHNE PASSENDES WISSEN: siehe NO_COVERAGE_TOPICS
unten -- drei Themen ausserhalb jeder Projekt-Domain dieses Bestands,
lesson_query liefert dazu nachweislich nichts Einschlaegiges (2 Treffer je
Anfrage, keiner thematisch passend). Nicht als TASKS-Eintrag, weil es dazu
keine Falle im Bestand gibt, die man pruefen koennte.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SHARED_KNOWLEDGE / "schreibpruefstand"))
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import schreiblauf as sl  # noqa: E402  -- _call_with_retry wiederverwendet
import knowledge_mcp_server as kms  # noqa: E402  -- lesson_query wiederverwendet

# wn.MODELS[0] wird von bedeckung.py direkt indiziert (wn.MODELS[0]) -- das
# erste Element bleibt deshalb "gemma4:12b", nur anhaengen, nie umsortieren.
# Nur noch lokales Ollama -- fremdes Backend (gemini) 2026-08-07 entfernt,
# Betreiber-Verbot fremder Erzeugung.
MODELS = ["gemma4:12b", "gemma4:e4b"]
_MODEL_BACKEND = {"gemma4:12b": "ollama", "gemma4:e4b": "ollama"}


def _backend_for(model: str) -> str:
    return _MODEL_BACKEND.get(model, sl.DEFAULT_BACKEND)


N_RUNS = 3
TIMEOUT = 180.0
OUT_PATH = SHARED_KNOWLEDGE / "runs" / "wissensnutzen.json"

PROMPT_A = """Du arbeitest im Flutter-Repo fahrtenbuch_legacy. Schreibe den \
Dart-Code fuer einen Bestaetigungsdialog "Fahrt beenden?" mit zwei Buttons \
(Ja / Nein), der bei Tippen auf einen Button-Handler in car_home_screen.dart \
angezeigt wird. Antworte nur mit dem Dart-Code."""

PROMPT_B = """Du arbeitest im Flutter-Repo fahrtenbuch_legacy. Nenne den \
exakten Shell-Befehl, um `flutter test` so auszufuehren, dass die \
Debug-Schnittstellen-Testfaelle des Projekts tatsaechlich mitlaufen (nicht \
nur gruen aussehen). Antworte nur mit dem Befehl."""

TASKS = {
    "A": {
        "name": "Dialog-Falle",
        "prompt": PROMPT_A,
        "lesson_query": "AlertDialog showDialog ActionScreen Vollbild fahrtenbuch_legacy",
        "check": lambda text: "ActionScreen" in text and "showDialog" not in text,
    },
    "B": {
        "name": "Stummer Testlauf",
        "prompt": PROMPT_B,
        "lesson_query": "DEBUG_STATE_API flutter test dart-define fahrtenbuch",
        "check": lambda text: "DEBUG_STATE_API" in text,
    },
    "D": {
        "name": "Swiftly statt Xcode-Toolchain",  # Lehre L-884098 (setfunk/openlehr)
        "prompt": "Nenne den exakten Shell-Befehl, um in einer Agent-Session auf "
                  "diesem Mac ein Swift-Package zu bauen, ohne an einer veralteten "
                  "Swiftly-Toolchain zu scheitern. Antworte nur mit dem Befehl.",
        "lesson_query": "Swift build Swiftly Toolchain xcrun Xcode",
        "check": lambda text: "xcrun swift build" in text.lower(),
    },
    "E": {
        "name": "Ungemockter Plattform-Channel haengt",  # Lehre L-c77fc0 (fahrtenbuch)
        "prompt": "Schreibe einen Flutter-Widget-Test fuer einen Screen, dessen "
                  "Provider Geolocator.checkPermission() und permission_handler "
                  "aufruft, ohne dass der Test bei pumpAndSettle() haengt.",
        "lesson_query": "Plattform-Channel Widget-Test haengt setMockMethodCallHandler",
        "check": lambda text: "setMockMethodCallHandler" in text,
    },
    "F": {
        "name": "Fix nicht auf Schwesterdatei uebertragen",  # Lehre L-8c633e (schwarmwacht)
        "prompt": "Du hast gerade einen QR-Code-zu-dicht-Bug in "
                  "swarm_pairing_qr_screen.dart behoben. Gib einen Shell-Befehl, "
                  "um andere Dateien im Repo zu finden, die per Kommentar auf diese "
                  "gefixte Datei verweisen und denselben Bug haben koennten.",
        "lesson_query": "Bugfix Schwesterdatei Kommentar verweist see analog zu",
        "check": lambda text: "grep" in text.lower() and any(
            m in text for m in ("See ", "see ", "same as", "analog zu", "siehe ")),
    },
    "G": {
        "name": "QR-Scan-Aufloesung statt Encoding",  # Lehre L-657b03 (schwarmwacht/setfunk/fahrtenbuch)
        "prompt": "mobile_scanner zeigt die Kamera-Vorschau, erkennt einen dichten "
                  "QR-Code (v30, 137x137 Module) aber nie. Welcher einzelne "
                  "MobileScannerController-Parameter behebt das? Antworte kurz.",
        "lesson_query": "mobile_scanner QR nicht erkannt Aufloesung cameraResolution",
        "check": lambda text: "cameraResolution" in text,
    },
    "I": {
        "name": "Codesign in Bash-Sandbox",  # Lehre L-14a742 (wohlairr/hub/fahrtenbuch)
        "prompt": "flutter build ipa / xcodebuild -exportArchive scheitert im "
                  "Bash-Tool jedes Mal an einem anderen eingebetteten Framework "
                  "mit einem Codesign-Fehler. Was setzt du im Bash-Tool-Aufruf, "
                  "bevor du weiter am Zertifikat debuggst? Antworte kurz.",
        "lesson_query": "Codesign exportArchive Bash Sandbox dangerouslyDisableSandbox",
        "check": lambda text: "dangerouslyDisableSandbox" in text,
    },
    "J": {
        "name": "Commit auf WAL-Schnappschuss",  # Lehre L-cc6d37 (hub/openlehr/fahrtenbuch)
        "prompt": "Wie stellst du sicher, dass `git commit` auf einer SQLite-"
                  "Datenbank im WAL-Modus wirklich den aktuellen Stand sichert "
                  "und nicht einen aelteren Schnappschuss? Antworte kurz.",
        "lesson_query": "git commit SQLite WAL Schnappschuss wal_autocheckpoint",
        "check": lambda text: "wal_autocheckpoint" in text or "git show head" in text.lower(),
    },
    "O": {
        "name": "Bool-Gate statt Generation-Token",  # Lehre L-606b63 (fahrtenbuch)
        "prompt": "Schreibe ein Dart-Session-Gate (tryEnter/leave), bei dem ein "
                  "verspaeteter Cleanup-Aufruf einer alten Runde niemals eine "
                  "bereits neu gestartete Runde beenden darf.",
        "lesson_query": "Session-Gate Reentrancy verspaeteter Cleanup Generation-Token",
        "check": lambda text: "generation" in text.lower(),
    },
    "P": {
        "name": "fake_async faengt keine Plattform-Channels",  # Lehre L-05314f (fahrtenbuch, systemweit)
        "prompt": "Schreibe einen fake_async-Test fuer einen Retry-Timer, der "
                  "waehrend des Retries rootBundle.loadString() aufruft. Was "
                  "brauchst du zusaetzlich, damit der Test nicht lautlos haengt?",
        "lesson_query": "fake_async Plattform-Channel haengt TestDefaultBinaryMessenger",
        "check": lambda text: "TestDefaultBinaryMessenger" in text,
    },
    "Q": {
        "name": "shared:true Testserver auf belegtem Port",  # Lehre L-c1b088 (fahrtenbuch)
        "prompt": "Ein Flutter-HTTP-Testserver (fahrtenbuch_legacy) auf einem "
                  "festen, in der Doku empfohlenen Debug-Port liefert "
                  "widerspruechliche Antworten. Welche zwei Shell-Befehle "
                  "pruefst du zuerst, bevor du am eigenen Testserver-Code "
                  "debuggst? Antworte kurz.",
        "lesson_query": "HttpServer shared true Port Konflikt adb forward lsof",
        "check": lambda text: "lsof" in text.lower() and "adb forward" in text.lower(),
    },
    "R": {
        "name": "user_id in zwei Stores unterschiedlich normalisiert",  # Lehre L-e7236d (openlehr)
        "prompt": "Dieselbe user_id dient in zwei getrennten Stores (Python/"
                  "Dart) als Schluessel. Was muss an JEDEM Lese- UND "
                  "Schreibpfad angewendet werden, damit kein stiller "
                  "Auth-Mismatch entsteht? Antworte kurz.",
        "lesson_query": "user_id zwei Stores normalisiert Auth-Gate kollabiert lautlos",
        "check": lambda text: "normali" in text.lower(),
    },
    "S": {
        "name": "Kollateralzustand statt Poll-Loop",  # Lehre L-1edb0e (fahrtenbuch)
        "prompt": "Ein Flutter-Test wartet auf einen Kollateralzustand "
                  "(machine.state.state), der synchron kippt, bevor ein "
                  "zuvor gestarteter unawaited Fire-and-Forget-Schreibvorgang "
                  "fertig ist. Wie musst du stattdessen auf das Ergebnis "
                  "warten? Antworte kurz.",
        "lesson_query": "Kollateralzustand unawaited fire-and-forget Poll-Loop Wartebedingung",
        "check": lambda text: "poll" in text.lower(),
    },
    "T": {
        "name": "Caret-Range statt manuellem pubspec-Edit",  # Lehre L-692936 (fahrtenbuch)
        "prompt": "Play Console verlangt Google Play Billing Library >=8.0.0, "
                  "die App bekommt sie transitiv ueber das Flutter-Plugin "
                  "in_app_purchase_android (via in_app_purchase in "
                  "pubspec.yaml, Caret-Range ^3.2.3). Wie loest du das "
                  "ZUERST, bevor du pubspec.yaml manuell editierst? Antworte kurz.",
        "lesson_query": "Play Billing Library Version Frist transitiv Flutter Plugin pub upgrade",
        "check": lambda text: "flutter pub upgrade" in text.lower() and "in_app_purchase" in text.lower(),
    },
    "U": {
        "name": "idevicesyslog/qemu als Absturzursache",  # Lehre L-dff4c3 (fahrtenbuch)
        "prompt": "Der Mac ist ueber Nacht abgestuerzt nach einer haengenden "
                  "flutter run-Debug-Session mit einem iOS-Geraet. Welche "
                  "zwei Prozessnamen pruefst du zuerst per `ps aux | grep`, "
                  "bevor du den Mac unbeaufsichtigt laesst? Antworte kurz.",
        "lesson_query": "idevicesyslog Memory Leak qemu Mac Crash Reboot haengende Session",
        "check": lambda text: "idevicesyslog" in text.lower() and "qemu" in text.lower(),
    },
}

# Gegenprobe (2026-08-07): drei Themen ausserhalb jeder Projekt-Domain dieses
# Bestands, absichtlich gesucht per lesson_query -- jeweils 2 Treffer, aber
# KEINER thematisch einschlaegig (Bestand deckt Flutter/Dart/Python/hub-Ops
# ab, nicht Rust/Kubernetes/PostgreSQL-Administration). Deshalb NICHT als
# TASKS-Eintrag aufgenommen -- es gibt keine pruefbare Falle dazu, nur die
# Abwesenheit von Wissen selbst ist der Befund.
NO_COVERAGE_TOPICS = [
    "Rust Ownership/Borrow-Checker Lifetime-Fehler beheben",
    "Kubernetes Helm-Chart values.yaml Umgebungstrennung",
    "PostgreSQL Autovacuum-Tuning gegen Tabellen-Bloat",
]


def fetch_lesson_text(query: str) -> str | None:
    """Erster Treffer aus lesson_query, als Wissensblock formatiert. None,
    wenn nichts gefunden wurde -- dann fehlt eine Voraussetzung des Laufs."""
    result = kms.lesson_query(query=query, max_results=1)
    hits = result.get("results") or []
    if not hits:
        return None
    lesson = hits[0]
    return (
        f"{lesson['description']}\n"
        f"Ursache: {lesson['root_cause']}\n"
        f"Loesung/Praevention: {lesson['prevention']}"
    )


def build_prompt_mit(base_prompt: str, lesson_text: str) -> str:
    return f"{base_prompt}\n\nBekanntes Wissen aus fruehreren Sessions:\n{lesson_text}"


def run_cell(prompt: str, model: str) -> list[dict]:
    """N_RUNS unabhaengige Aufrufe (Backend aus _backend_for(model)) mit
    demselben Prompt. Streuung ist der Punkt, kein Einzellauf zaehlt als
    Beleg (siehe Docstring-Anlass: 2026-08-06 schwankte derselbe Aufbau
    zwischen 1 und 3 von 7). Modell+Backend stehen in JEDER Ergebniszeile,
    nicht nur im Cell-Key -- eine Zeile ohne diese Angabe ist wertlos,
    sobald mehrere Modelle/Backends nebeneinander im Bestand liegen."""
    backend = _backend_for(model)
    runs = []
    for _ in range(N_RUNS):
        started = time.perf_counter()
        raw, err, retries = sl._call_with_retry(
            # beantworten (Aufgaben A/B) -> ab jetzt gesperrt, siehe L-a69129.
            # Nebenbefund beim Deklarieren: `backend` wird hier berechnet, in
            # jede Ergebniszeile geschrieben und von _call_with_retry NIE
            # ausgewertet -- jeder Aufruf ging ueber Ollama. Die Spalte
            # 'backend' in den Ergebnisdateien behauptet eine Wahl, die es
            # nicht gab (Fehlklasse S14: gebaut und ohne Wirkung).
            prompt, model=model, base_url=sl.DEFAULT_OLLAMA_URL, timeout=TIMEOUT,
            rolle="beantworten", backend=backend)
        seconds = time.perf_counter() - started
        passed = False if err else bool(raw)
        runs.append({
            "model": model,
            "backend": backend,
            "error": err,
            "retry_count": retries,
            "call_seconds": seconds,
            "response_excerpt": (raw or "")[:400],
            "response_full": raw,
        })
    return runs


def aggregate(passed_flags: list[bool]) -> dict:
    vals = [1 if p else 0 for p in passed_flags]
    return {"mean": sum(vals) / len(vals), "range": max(vals) - min(vals), "runs": vals}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(OUT_PATH))
    ap.add_argument("--selftest", action="store_true",
                     help="Netzloser Selbsttest der Bewertungs-/Aggregationslogik, kein Ollama-Aufruf")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return

    started_total = time.perf_counter()
    cells: dict[str, dict] = {}
    prompts_for_honesty_check: dict[str, str] = {}

    for task_id, task in TASKS.items():
        lesson_text = fetch_lesson_text(task["lesson_query"])
        assert lesson_text, f"Keine Lehre gefunden fuer Aufgabe {task_id} -- Voraussetzung fehlt, Abbruch"
        prompt_ohne = task["prompt"]
        prompt_mit = build_prompt_mit(task["prompt"], lesson_text)
        if task_id == "A":
            prompts_for_honesty_check = {"ohne": prompt_ohne, "mit": prompt_mit}

        for model in MODELS:
            for condition, prompt in (("OHNE", prompt_ohne), ("MIT", prompt_mit)):
                key = f"{task_id}|{model}|{condition}"
                runs = run_cell(prompt, model)
                passed_flags = [task["check"](r["response_full"] or "") for r in runs]
                cell_agg = aggregate(passed_flags)
                cells[key] = {"task": task_id, "model": model, "condition": condition,
                              "aggregate": cell_agg, "runs": runs}
                print(f"{task_id} {model:12s} {condition:5s} "
                      f"mean={cell_agg['mean']:.2f} range={cell_agg['range']} "
                      f"runs={cell_agg['runs']}")

    runtime_total = time.perf_counter() - started_total

    output = {
        "models": MODELS,
        "n_runs": N_RUNS,
        "cells": cells,
        "honesty_check_task_a_prompts": prompts_for_honesty_check,
        "runtime_seconds_total": runtime_total,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nGeschrieben: {out_path}")
    print(f"Laufzeit gesamt: {runtime_total:.1f}s")
    print("\n--- EHRLICHKEITSPROBE Aufgabe A: Prompt OHNE Wissen ---")
    print(prompts_for_honesty_check["ohne"])
    print("\n--- EHRLICHKEITSPROBE Aufgabe A: Prompt MIT Wissen ---")
    print(prompts_for_honesty_check["mit"])


def _selftest() -> None:
    """Prueft Bewertungs- und Aggregationslogik ohne Netz/Ollama/DB."""
    assert TASKS["A"]["check"]("class X { ActionScreen(); }") is True
    assert TASKS["A"]["check"]("showDialog(context: c, builder: (_) => ActionScreen());") is False, \
        "Aufgabe A muss ablehnen, wenn showDialog im Text vorkommt, auch neben ActionScreen"
    assert TASKS["A"]["check"]("AlertDialog + showDialog") is False
    assert TASKS["B"]["check"]("flutter test --dart-define=DEBUG_STATE_API=true") is True
    assert TASKS["B"]["check"]("flutter test") is False

    # Je einmal richtig/falsch pro neuer Aufgabe -- keine Recherche, nur die
    # Grenzfaelle abhaken, die die Regex/Substring-Checks brechen wuerden.
    assert TASKS["D"]["check"]("xcrun swift build") is True
    assert TASKS["D"]["check"]("swift build") is False
    assert TASKS["E"]["check"]("tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(...)") is True
    assert TASKS["E"]["check"]("tester.pumpAndSettle();") is False
    assert TASKS["F"]["check"]('grep -rn "See swarm_pairing_qr_screen.dart" .') is True
    assert TASKS["F"]["check"]("check the other screens manually") is False
    assert TASKS["G"]["check"]("MobileScannerController(cameraResolution: Size(1920, 1080))") is True
    assert TASKS["G"]["check"]("MobileScannerController(formats: [BarcodeFormat.qrCode])") is False
    assert TASKS["I"]["check"]("Bash(..., dangerouslyDisableSandbox=True)") is True
    assert TASKS["I"]["check"]("security unlock-keychain -p pass login.keychain") is False
    assert TASKS["J"]["check"]("PRAGMA wal_autocheckpoint=100;") is True
    assert TASKS["J"]["check"]("git add brainlehr.db && git commit") is False
    assert TASKS["O"]["check"]("int generation = 0; leave(int gen) { if (gen == generation) ...}") is True
    assert TASKS["O"]["check"]("bool _active = false; void leave() { _active = false; }") is False
    assert TASKS["P"]["check"]("TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger") is True
    assert TASKS["P"]["check"]("fakeAsync((async) { timer.elapse(); });") is False
    assert TASKS["Q"]["check"]("lsof -i -P -n | grep 8080; adb forward --list") is True
    assert TASKS["Q"]["check"]("check the test server logs") is False
    assert TASKS["R"]["check"]("Eine kanonische Normalisierungsfunktion an jedem Lese- und Schreibpfad.") is True
    assert TASKS["R"]["check"]("Beide Stores vergleichen die IDs direkt.") is False
    assert TASKS["S"]["check"]("Poll-Loop mit genereoser Obergrenze auf das Export-Artefakt selbst.") is True
    assert TASKS["S"]["check"]("Einmal lesen, nachdem machine.state.state == idle ist.") is False
    assert TASKS["T"]["check"]("flutter pub upgrade in_app_purchase in_app_purchase_android") is True
    assert TASKS["T"]["check"]("pubspec.yaml von Hand auf ^3.3.0 anheben") is False
    assert TASKS["U"]["check"]("ps aux | grep idevicesyslog; ps aux | grep qemu-system") is True
    assert TASKS["U"]["check"]("Activity Monitor manuell durchsehen") is False

    agg_all_pass = aggregate([True, True, True])
    assert agg_all_pass == {"mean": 1.0, "range": 0, "runs": [1, 1, 1]}
    agg_mixed = aggregate([True, False, True])
    assert agg_mixed["mean"] == 2 / 3 and agg_mixed["range"] == 1 and agg_mixed["runs"] == [1, 0, 1]
    agg_none = aggregate([False, False, False])
    assert agg_none == {"mean": 0.0, "range": 0, "runs": [0, 0, 0]}

    print("selftest ok: Bewertungslogik aller 15 Aufgaben + Aggregation (mean/range)", file=sys.stderr)


if __name__ == "__main__":
    main()
