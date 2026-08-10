## BSI Stand-der-Technik Compliance (P44, PFLICHT)

> Quelle: BSI-Bund/Stand-der-Technik-Bibliothek (CC-BY-SA 4.0)
> Profil: hub/shared-knowledge/bsi-dev-profile.json (926 dev-relevante Controls)
> Tools: bsi_sync_checker.py (sync|gate), bsi_code_review.py (scan|secrets|deps)

### Session-Gate
Bei Session-Start: `python3 hub/scripts/bsi_sync_checker.py gate` — falls `passed: false`:
- BSI CODE REVIEW NÖTIG → `python3 hub/scripts/bsi_sync_checker.py diff` prüfen
- BSI-Sync veraltet → `python3 hub/scripts/bsi_sync_checker.py sync` ausführen
- KEIN normaler Task vor BSI-Gate-Clearance.

### Hard-Stops (ABSOLUT — keine Ausnahme)
- **HS-U1:** Keine Credentials/Secrets im Quellcode (BSI DEV.2.5) → Nur Env-Vars/.env
- **HS-U2:** Keine Default-Credentials in Produktion (BSI KONF.2.3)
- **HS-U3:** Kein eval()/exec() mit User-Input (BSI DEV.2.6)

### Hard-Stops (STARK — Veto-Recht)
- **HS-U4:** Dependencies nur aus vertrauenswürdigen Quellen (BSI DEV.4.2)
- **HS-U5:** Keine sensiblen Daten in Fehlermeldungen (BSI DEV.3.3)
- **HS-U6:** Lock-Files committiert (BSI DEV.4.3)
- **HS-U7:** OWASP Top 10 Schutz (BSI DEV.2.6) — SQL-Injection, XSS, CSRF prüfen
- **HS-U8:** Passwörter nur bcrypt/argon2 (BSI DEV.3.4)
- **HS-U9:** WCAG 2.1 AA bei UI-Änderungen (P45)

### Bei Code-Review
`python3 hub/scripts/bsi_code_review.py scan [path]` — automatisierter BSI-Check.
ABSOLUT-Findings = Blocker. STARK-Findings = vor Commit fixen.
