#!/usr/bin/env python3
"""Erzeugt eine lokale Beispieldatenbank und prüft die Suchfunktion."""

from knowledge_mcp_server import add_node, open_db, search


def main():
    db = open_db()
    if not search(db, "Beispiel"):
        add_node(db, "Beispielwissen", "Synthetischer Eintrag für den lokalen Schnellstart.")
    assert search(db, "Beispiel"), "Schnellstart konnte keinen Eintrag finden"
    print("Schnellstart erfolgreich.")


if __name__ == "__main__":
    main()
