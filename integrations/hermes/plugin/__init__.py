"""brainlehr als MemoryProvider fuer Hermes.

Diese Datei ist der Einstiegspunkt, den Hermes sucht. Sie muss das Wort
MemoryProvider in den ersten 8192 Zeichen fuehren -- Hermes erkennt einen
Speicher-Anbieter per TEXTSCAN, nicht per Import
(plugins/memory/__init__.py::_is_memory_provider_dir).
"""
try:
    # Der Weg, den HERMES geht: das Verzeichnis wird als Paket geladen.
    from .brainlehr_provider import BrainlehrProvider  # noqa: F401
except ImportError:
    # Und der, den jedes andere Werkzeug geht -- pytest, ein Skript, ein
    # Direktaufruf: dann ist diese Datei ein Modul OHNE Elternpaket, und die
    # relative Einfuhr oben ist syntaktisch gueltig, aber nicht ausfuehrbar.
    # Ohne diesen Rueckfall bricht im eigenstaendigen Repo jeder Testlauf,
    # weil pytest die __init__.py der Wurzel immer mitimportiert (gemessen
    # 2026-08-23: 44 Fehler, keiner davon inhaltlich).
    from brainlehr_provider import BrainlehrProvider  # type: ignore  # noqa: F401

__all__ = ["BrainlehrProvider"]
