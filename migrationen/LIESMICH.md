# Migrationen und Einmalläufe

Historische Skripte, die eine **gewachsene** Datenbank auf einen neueren Stand
gebracht haben. Sie werden von nichts importiert und sind für eine Neuanlage
**nicht nötig** — `schema.sql` erzeugt den vollständigen aktuellen Stand.

Sie liegen hier statt im Wurzelverzeichnis, weil sie dort wie Bestandteile des
Systems aussahen, obwohl sie Vergangenheit sind. Gelöscht werden sie nicht: sie
belegen, **wann welche Regel dazukam** — und genau das lässt sich aus dem
fertigen Schema nicht mehr ablesen.

Ein Lauf gegen eine bereits migrierte Datenbank ist wirkungslos (idempotent),
nicht schädlich.
