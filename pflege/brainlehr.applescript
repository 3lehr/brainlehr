-- brainlehr.app -- Ausweise, Einladungen und der Wissensraum, ohne Terminal.
--
-- WARUM SYSTEMDIALOGE UND KEINE EIGENE OBERFLAECHE: Die Dialoge von macOS sind
-- ab Werk mit VoiceOver bedienbar, vollstaendig tastaturerreichbar und folgen
-- Systemschrift, Systemkontrast und "Ohne Bewegung". Eine selbstgebaute
-- Oberflaeche muesste das alles nachbauen -- und WCAG 2.2 AA waere dann eine
-- Behauptung statt einer Eigenschaft.
--
-- WARUM DAS GEHEIMNIS UEBER EINE DATEI GEHT, nicht als Argument: Alles, was in
-- `do shell script` steht, ist fuer jeden Prozess desselben Nutzers in `ps`
-- lesbar. AppleScript schreibt die Datei deshalb SELBST (open for access), ohne
-- Shell -- so steht das Geheimnis in keiner Befehlszeile, in keiner Historie
-- und in keiner Prozessliste. mktemp legt sie mit Rechten 600 an; geloescht
-- wird sie in jedem Fall, auch nach einem Fehler.
--
-- Erzeugen:  osacompile -o ~/Desktop/brainlehr.app brainlehr.applescript

property kRepo : "/Volumes/daten/Begod2026/brainlehr"
property kStarter : "pflege/ausweis_start.sh"
property kWissensraumStarter : "pflege/wissensraum_start.sh"
property kOffeneArbeit : "melder/offene_arbeit.py"

on run
	repeat
		set wahl to waehleAktion()
		if wahl is missing value then exit repeat
		try
			if wahl starts with "Ausweis anlegen" then
				anlegenFluss()
			else if wahl starts with "Einladung" then
				einladenFluss()
			else if wahl starts with "Ausweise anzeigen" then
				listeZeigen()
			else if wahl starts with "Rollen erklaeren" then
				rollenZeigen()
			else if wahl starts with "Wissensraum" then
				wissensraumFluss()
			else if wahl starts with "Offene Arbeit" then
				offeneArbeitFluss()
			end if
		on error fehlertext number fehlernummer
			if fehlernummer is -128 then
				-- Abbruch durch den Nutzer ist kein Fehler.
			else
				display alert "Das hat nicht geklappt" message fehlertext as warning
			end if
		end try
	end repeat
end run

on waehleAktion()
	set auswahl to choose from list {¬
		"Ausweis anlegen — fuer einen Menschen oder ein Programm", ¬
		"Einladung erzeugen — PIN, damit sich jemand selbst anmeldet", ¬
		"Ausweise anzeigen — wer hat gerade Zugang", ¬
		"Rollen erklaeren — was jede Rolle darf", ¬
		"Wissensraum öffnen — Server starten, falls noetig, und im Browser zeigen", ¬
		"Offene Arbeit anzeigen — welche Sprints noch offen sind"} ¬
		with title "brainlehr" ¬
		with prompt "Was moechtest du tun?" ¬
		default items {"Einladung erzeugen — PIN, damit sich jemand selbst anmeldet"} ¬
		OK button name "Weiter" cancel button name "Beenden"
	if auswahl is false then return missing value
	return item 1 of auswahl
end run

-- ---------------------------------------------------------------- Abläufe --

on anlegenFluss()
	set derName to frageText("Wie soll der Ausweis heissen?", ¬
		"Ein kurzer Name ohne Leerzeichen, z. B. \"laptop-markus\" oder \"codex\".", "")
	set dieArt to frageArt()
	set dieRollen to frageRollen()
	set geheim to frageGeheimnis("Zum Anlegen brauchst du deinen eigenen Ausweis.")

	set antwort to helfer("anlegen " & q(derName) & " " & q(dieArt) & " " & q(dieRollen), geheim)
	set neuesGeheimnis to feld(antwort, "geheimnis")

	set the clipboard to neuesGeheimnis
	display alert "Ausweis \"" & derName & "\" ist angelegt" message ¬
		"Das Geheimnis liegt jetzt in der Zwischenablage. Es erscheint NUR DIESES EINE MAL — sichere es in deinem Passwortmanager, bevor du weitermachst." & return & return & ¬
		"Art: " & dieArt & "   Rollen: " & dieRollen & return & return & ¬
		"Beim Programm gehoert es in dessen Konfiguration, nicht in einen Chat." ¬
		buttons {"Habe ich gesichert"} default button 1
end run

on einladenFluss()
	set derName to frageText("Unter welchem Namen soll sich der Gast anmelden?", ¬
		"Zum Beispiel \"claude-code\" oder \"codex\".", "claude-code")
	set fuerWen to frageText("Wer verantwortet diese Einladung?", ¬
		"Dein eigener Ausweisname. Er bleibt an allem haengen, was der Gast schreibt.", "markus")
	set dieRollen to frageRollen()
	set geheim to frageGeheimnis("Zum Einladen brauchst du deinen eigenen Ausweis.")

	set antwort to helfer("einladen " & q(derName) & " " & q(fuerWen) & " " & q(dieRollen), geheim)
	set diePin to feld(antwort, "pin")
	set dieDauer to feld(antwort, "gueltig_minuten")

	set the clipboard to diePin
	display alert "PIN fuer \"" & derName & "\"" message ¬
		"PIN: " & diePin & return & return & ¬
		"Sie liegt in der Zwischenablage, gilt " & dieDauer & " Minuten und funktioniert GENAU EINMAL." & return & return & ¬
		"Gib sie ueber einen Weg weiter, den du selbst waehlst — Chat, Zuruf, Mail. Genau das ist der Sinn: Die Einloesung beweist, dass ein Mensch sie weitergegeben hat." ¬
		buttons {"Verstanden"} default button 1
end run

on listeZeigen()
	set antwort to helfer("liste", missing value)
	set zeilen to do shell script "/usr/bin/python3 -c " & q("
import json,sys
d=json.loads(sys.argv[1])
if not d.get('ausweise'):
    print('Noch kein Ausweis angelegt.')
for a in d.get('ausweise',[]):
    art='Mensch' if a.get('art')=='mensch' else 'Programm'
    print('%-18s %-9s %s' % (a['name'], art, ', '.join(a.get('rollen') or [])))
print()
print('Datei: '+d.get('datei',''))
") & " " & q(antwort)
	display alert "Wer hat Zugang" message zeilen buttons {"Schliessen"} default button 1
end run

on rollenZeigen()
	display alert "Was die Rollen duerfen" message ¬
		"betreiber — alles, auch neue Ausweise ausstellen. Nur fuer dich." & return & return & ¬
		"schreiber — Wissen und Lehren lesen und schreiben. Die richtige Wahl fuer ein Programm, das mitarbeitet." & return & return & ¬
		"fachkundig — darf lesen, aber nur AENDERN, was es selbst angelegt hat." & return & return & ¬
		"leser — darf alles lesen, nichts schreiben." & return & return & ¬
		"gast — sieht nur, was ausdruecklich freigegeben ist." & return & return & ¬
		"meldeamt — darf Ausweise ausstellen, sonst nichts. Sparsam vergeben." ¬
		buttons {"Schliessen"} default button 1
end run

-- Startet den Wissensraum-Server, falls er nicht schon laeuft, und oeffnet
-- ihn im Standardbrowser. Braucht kein Geheimnis -- der Server liest nur.
on wissensraumFluss()
	set dieUrl to do shell script "cd " & q(kRepo) & " && " & q(kRepo & "/" & kWissensraumStarter)
	open location dieUrl
end run

-- Liest docs/SPRINTS.md und zeigt den Stand. Reiner Lesevorgang, dauert
-- unter einer Sekunde, kein Geheimnis noetig.
on offeneArbeitFluss()
	set derText to do shell script "cd " & q(kRepo) & " && /usr/bin/python3 " & q(kOffeneArbeit)
	if derText is "" then set derText to "Zur Zeit nichts Offenes vermerkt."
	display alert "Offene Arbeit" message derText buttons {"Schliessen"} default button 1
end run

-- ------------------------------------------------------------- Bausteine --

on frageText(titel, hinweis, vorgabe)
	set antwort to display dialog hinweis with title titel ¬
		default answer vorgabe buttons {"Abbrechen", "Weiter"} default button 2 ¬
		cancel button 1
	set t to text returned of antwort
	if t is "" then error "Es wurde nichts eingegeben."
	return t
end run

on frageArt()
	set auswahl to choose from list {"Programm (Vorgabe)", "Mensch"} ¬
		with title "Wer bekommt den Ausweis?" ¬
		with prompt "Nur ein Ausweis fuer einen Menschen zaehlt als menschliche Entscheidung — etwa fuer Hausregeln. Ein Geheimnis, das in der Konfiguration eines Programms liegt, gehoert dem Programm, auch wenn es deinen Namen traegt." ¬
		default items {"Programm (Vorgabe)"} OK button name "Weiter" cancel button name "Abbrechen"
	if auswahl is false then error number -128
	if item 1 of auswahl is "Mensch" then return "mensch"
	return "maschine"
end run

on frageRollen()
	set auswahl to choose from list {"schreiber", "fachkundig", "leser", "gast", "meldeamt", "betreiber"} ¬
		with title "Was soll erlaubt sein?" ¬
		with prompt "Mehrfachauswahl moeglich. Im Zweifel \"schreiber\" — das reicht fuer ein Programm, das mitarbeitet, ohne Ausweise ausstellen zu duerfen." ¬
		default items {"schreiber"} with multiple selections allowed ¬
		OK button name "Weiter" cancel button name "Abbrechen"
	if auswahl is false then error number -128
	set AppleScript's text item delimiters to ","
	set r to auswahl as text
	set AppleScript's text item delimiters to ""
	return r
end run

on frageGeheimnis(warum)
	set antwort to display dialog ¬
		warum & return & return & "Dein Geheimnis (bleibt verdeckt):" ¬
		with title "Dein Ausweis" default answer "" with hidden answer ¬
		buttons {"Abbrechen", "Weiter"} default button 2 cancel button 1
	set g to text returned of antwort
	if g is "" then error "Ohne Geheimnis geht es nicht weiter."
	return g
end run

-- Ruft den Helfer. Das Geheimnis geht ueber eine temporaere Datei, die
-- AppleScript selbst schreibt -- nie ueber die Befehlszeile.
on helfer(befehlUndArgumente, geheim)
	set tmpPfad to missing value
	try
		set aufruf to "cd " & q(kRepo) & " && " & q(kRepo & "/" & kStarter) & " " & befehlUndArgumente
		if geheim is missing value then
			set roh to do shell script aufruf & " < /dev/null"
		else
			set tmpPfad to do shell script "/usr/bin/mktemp -t brainlehr-ausweis"
			set f to open for access (POSIX file tmpPfad) with write permission
			set eof f to 0
			write geheim to f as «class utf8»
			close access f
			set roh to do shell script aufruf & " < " & q(tmpPfad)
		end if
	on error fehlertext number fehlernummer
		if tmpPfad is not missing value then loescheStill(tmpPfad)
		-- Der Helfer meldet Fehler als JSON und beendet sich mit Code 1; do
		-- shell script macht daraus einen AppleScript-Fehler, dessen Text die
		-- Meldung enthaelt. Sie wird durchgereicht, nicht ersetzt.
		set derGrund to versucheFeld(fehlertext, "fehler")
		if derGrund is not missing value then error derGrund
		error fehlertext number fehlernummer
	end try
	if tmpPfad is not missing value then loescheStill(tmpPfad)

	set derFehler to versucheFeld(roh, "fehler")
	if derFehler is not missing value then error derFehler
	return roh
end run

on loescheStill(pfad)
	try
		do shell script "/bin/rm -f " & q(pfad)
	end try
end run

-- Nur JSON lesen, keine Kryptografie: dafuer reicht Apples
-- System-Python, und das ist auf jedem Mac vorhanden.
on feld(jsonText, name)
	return do shell script "/usr/bin/python3 -c " & ¬
		q("import json,sys; print(json.loads(sys.argv[1]).get(sys.argv[2],''))") & ¬
		" " & q(jsonText) & " " & q(name)
end run

on versucheFeld(text_, name)
	try
		set w to do shell script "/usr/bin/python3 -c " & ¬
			q("
import json,sys,re
t=sys.argv[1]
m=re.search(r'\\{.*\\}', t, re.S)
if not m: raise SystemExit(1)
v=json.loads(m.group(0)).get(sys.argv[2])
if not v: raise SystemExit(1)
print(v)
") & " " & q(text_) & " " & q(name)
		if w is "" then return missing value
		return w
	on error
		return missing value
	end try
end run

on q(s)
	return quoted form of (s as text)
end run
