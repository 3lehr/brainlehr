---
applyTo: "**"
---
# Auto-Generated Lessons Learned
# Generiert: 2026-08-28T20:08:00Z
# Quelle: lesson_recorder.py auto-rules (Threshold: 3x)

- Je Zweig einer Oder-Verkettung eine eigene Testzeile, die NUR diesen Zweig trifft -- eine Testzeile mit zwei Verdachtsformulierungen belegt nichts. Und bei Zeichenklassen mit Umlauten pruefen, ob die Klasse an der richtigen STELLE steht: [Ll][üu]cke, nicht [LlÜü]cke. Beides ist in Sekunden mit re.search gegen die echte Schreibweise pruefbar.
- Je Zweig einer Oder-Verkettung eine eigene Testzeile, die NUR diesen Zweig trifft -- eine Testzeile mit zwei Verdachtsformulierungen belegt nichts. Und bei Zeichenklassen mit Umlauten pruefen, ob die Klasse an der richtigen STELLE steht: [Ll][üu]cke, nicht [LlÜü]cke. Beides ist in Sekunden mit re.search gegen die echte Schreibweise pruefbar.
- Bei jedem Merkmal, das eine Berechtigung, ein Entitlement oder eine Capability braucht und im Test „einfach nicht passiert": pruefen, was im GEBAUTEN ARTEFAKT steht, nicht was in der Konfiguration steht. Unter iOS `codesign -d --entitlements :- <app>`, unter Android `aapt dump badging`/`dumpsys package`. Konfiguration und Binary koennen auseinanderfallen, und zwar systematisch: Debug- und Simulator-Builds signieren ad-hoc und lassen benutzerdefinierte Entitlements weg, waehrend Device- und Release-Builds sie tragen. Ein Merkmal, das nur im Release funktioniert, ist deshalb kein Zufall, sondern ein Hinweis auf genau diese Klasse. Und: Ein lautloser Fehlschlag ohne Fehlermeldung ist ein Hinweis auf eine fehlende Berechtigung, nicht auf eine fehlende Faehigkeit -- Berechtigungssysteme schweigen, kaputte Funktionen melden sich.
- Bei knowledge_update mit betreiber_weisung stets die bestehende oder neue norm_entscheidung und norm_entschieden_grund im selben Aufruf mitsenden.
- Bei Public-README-Review Landingpage und Policy-Dokumente getrennt prüfen; interne Ausschlusslisten gehören nicht in den Einstieg.
- After any Brainlehr project lifecycle/provenance call, inspect .brainlehr.json before handoff and restore it when the task declares it protected.
