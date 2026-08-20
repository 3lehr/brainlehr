"""brainlehr als MemoryProvider fuer Hermes.

Diese Datei ist der Einstiegspunkt, den Hermes sucht. Sie muss das Wort
MemoryProvider in den ersten 8192 Zeichen fuehren -- Hermes erkennt einen
Speicher-Anbieter per TEXTSCAN, nicht per Import
(plugins/memory/__init__.py::_is_memory_provider_dir).
"""
from .brainlehr_provider import BrainlehrProvider  # noqa: F401

__all__ = ["BrainlehrProvider"]
