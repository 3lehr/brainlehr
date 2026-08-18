# Plan: die Vertragsnaht openlehr_X → Brainlehr → Atelier (BDW-F07)

**Stand** 2026-08-18T05:45:00+0200
**Nachgetragen.** Der Wächter `melder/ablaufpflicht.py` hat beim Push zu Recht
beanstandet, dass `cdef550b` sechs Quelldateien ändert, ohne einen Plan zu
nennen. Er hat recht: Es gab keinen. Dieses Dokument holt ihn nach und ist als
Nachtrag gekennzeichnet, nicht als Rekonstruktion einer angeblichen Vorplanung.

## Gemessener Ist-Stand (vor der Arbeit, 2026-08-18 früh)

- `kern/domaene.py` verlangte fünf Pflichtschlüssel, kein Versionsfeld.
- `speichere()` schrieb mit `INSERT OR IGNORE`; gleiche IDs nie aktualisiert.
- `dienst` wurde geprüft, nie persistiert, nie gestartet.
- Der OpenLehr-Gegentest rief `pytest.skip`, wenn Brainlehr fehlte.
- Reproduktionsmenge der Übergabe: 80 passed.

## Alternativen, und warum verworfen

- **Zweites Repo für die Domänenpakete.** Verworfen: der heutige Atelier-Befund
  (`L-51e6d8`) fiel nur, weil beide Seiten in einem Commit lagen. Siehe ADR-025.
- **`contract_version` optional, mit Vorgabewert 1.** Verworfen: ein Vorgabewert
  rät, und ein ratender Prüfer kann eine brechende Fassung nicht erkennen.
  Fail-closed wie die Contract Registry in `OPENLEHR_KERNEL_UND_APP_VERTRAG_V1` §2.
- **Reimport als Löschen und Neuschreiben.** Verworfen: das würde eine in Kraft
  gesetzte Regel still entwerten (ADR-018). Update nur bei `keine_norm`.
- **Nur Katalog schreiben, Gates später.** Verworfen: ein Katalog ohne Gate ist
  die Fehlerklasse, für die brainlehr existiert („gebaut, laufend, wirkungslos").

## Reihenfolge, und wo sie bindend ist

1. Katalog mit stabilen `INT-*`-IDs — **vor** jedem Produktcode, sonst hat die
   Änderung keine Adresse.
2. Rote Gates (`xfail(strict=True)`) — **vor** der Umsetzung. Bindend: ein Gate,
   das erst nach dem Bau entsteht, kann nie rot gewesen sein.
3. `contract_version` — **vor** allem anderen Produktcode, weil jede weitere
   Formatänderung sonst keine Fassung hat, an der sie hängt.
4. Reimport-Update und Dienst-Persistenz — parallel möglich, beide in derselben
   Datei, deshalb **ein** Agent, nicht zwei.
5. Konsumenten des geänderten Rückgabewerts prüfen — bindend **nach** 4 und
   ausdrücklich in den Schichten, die dem Agenten verboten waren.

## Was bewusst nicht getan wird, samt Preis

- **Keine Rücknahme eines Imports** (`INT-UPD-002`). Preis: ein falsch
  importiertes Paket ist nur von Hand aus dem Bestand zu schneiden, und niemand
  weiß danach, was dazugehörte. Sichtbar gehalten als `xfail(strict=True)`.
- **Keine Domänenregistry** (`INT-REG-001`), keine Snapshotgrenze
  (`INT-SNAP-001`). Preis: das Atelier bleibt auf `einzelunternehmer` festgelegt,
  und jede Suche liest den gegenwärtigen Bestand statt eines festen Standes.
- **Keine Änderung an fremden Commit-Nachrichten**, obwohl sechs davon die
  Belegfrage offenlassen. Preis: der Push trägt sie mit.

## Woran sich Erfolg misst

Nicht an grünen Tests, sondern an einer Frage: Kann eine korrigierte Fachregel
aus `openlehr_X` beim Empfänger ankommen und dort sichtbar werden? Vor dieser
Arbeit war die Antwort dreimal nein — kein Versionsfeld, kein Update, und die
Oberfläche hätte „enthielt nichts Neues" gemeldet.
