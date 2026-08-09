# Selbsttest-Rundlauf 2026-08-09T20:55:00+0200

Anlass: L-136f2b (im hub waren 10 von 34 Selbsttests rot, alle vorbestehend, unbemerkt).
Ausgeloest durch einen eingespielten Recall-Treffer, nicht durch eigene Suche.

ERGEBNIS: 73 Selbsttests, 52 gruen, 21 ROT.

MESSFALLE, die zuerst zuschlug: ein erster Lauf meldete 0 von 73 gruen.
Ursache war nicht der Bestand, sondern das Kommando 'timeout', das es auf
macOS nicht gibt — jeder Aufruf scheiterte am Werkzeug statt am Test.
Dieselbe Falle war heute frueh schon einmal aufgetreten.

ROT (21):
  - abrufguete.py
  - deckelreihe.py
  - entscheidungen_server.py
  - fenstergroesse.py
  - liefermenge.py
  - messparameter.py
  - messlauf_abrufguete.py
  - migrate_anlass.py
  - migrate_normfelder.py
  - knowledge_recall_replay.py
  - knowledge_lint.py
  - messlauf_abrufguete_v2.py
  - migrate_auditkette.py
  - migrate_quellhash.py
  - trichter_gitter.py
  - normrang.py
  - normbestand.py
  - haken/mehrstufiger_abruf.py
  - pruefkorpus_v3.py
  - wissensverlauf.py
  - wiederherstellung.py

NICHT betroffen sind die vier Werkzeuge der Abnahmespalte:
  konfidenz.py, pruefer.py, arbeitsmelder.py, haken/antwort_abruf.py — alle gruen,
  und alle vier per Gegenprobe als rot-faehig belegt (Kernzusicherung entwertet -> rot).

ABER: abrufguete.py ist rot und traegt die Kriterien von S9 und S15.
Sein Selbsttest meldet ausdruecklich eine Bestandsaenderung ('L-a9ccd0 sollte
ein Fehlgriff sein, war aber ein Treffer') — also ein Waechter, der spricht,
kein stiller Defekt. Die uebrigen 20 sind NICHT eingeordnet.

OFFEN: je Datei unterscheiden zwischen (a) Waechter meldet echte Abweichung,
(b) einmaliges Migrationsskript ohne Gegenwart, (c) echter Defekt.
