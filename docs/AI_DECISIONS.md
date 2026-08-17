# Öffentliche Entscheidungen

## 2026-08-17: Funktionsfähiger Export ohne gespeichertes Kontextwissen

Gewählt wurde ein portabler lokaler Speicher mit Knoten, Suche, Beziehungen und Lehren. Nicht übernommen wurden private Bestandsdaten oder kontextspezifische Implementierungsdetails. Verifiziert durch Privacy-Check und Smoke-Test.

## 2026-08-17: ChatGPT-Tunnel nutzt den bestehenden stdio-MCP

ChatGPT erhält den authentifizierten HTTPS-Transport über OpenAI Secure MCP Tunnel; Brainlehr bleibt lokal auf stdio. Das Tunnelprofil setzt `BRAINLEHR_TOOL_PROFILE=prompt-invariance` und ist damit auf zwei Werkzeuge begrenzt, während Claudes Standardprofil vollständig bleibt. Verworfen wurde ein eigener öffentlicher HTTP-/OAuth-Dienst: Der offizielle Tunnel unterstützt stdio direkt, und zusätzlicher Ingress würde ohne Funktionsgewinn eine zweite Authentifizierungs- und TLS-Grenze schaffen.

Evidenz: OpenAI Secure MCP Tunnel Guide; lokale Sicherheitsbasis `Anwenderkataloge/Mindeststandard-TLS/Entwurf-Mindeststandard-TLS-catalog.json` (Transportverschlüsselung und Authentifizierung). Das ist eine Architekturbegründung, keine BSI- oder Compliance-Zertifizierung.
