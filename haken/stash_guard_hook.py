#!/usr/bin/env python3
"""PreToolUse-Guard (Bash): `git stash` in JEDER schreibenden Form verhindern.

Anlass (2026-08-15): `git stash` wirkt auf den GANZEN Arbeitsbaum -- in
einer Sitzung mit mehreren gleichzeitig schreibenden Agenten kann ein
Stapelvorgang fremde Arbeit einspielen oder wegnehmen (2026-07-31: fuenf
Dateien mit Konfliktmarkern). Ein Verbot in CLAUDE.md wurde heute FUENFMAL
gebrochen, zuletzt trotz Verbot+Ersatzweg im selben Satz wie die
Rot-Probe-Anforderung (11:2x). Eine Formulierung loest das nicht -- es
braucht eine Stelle, an der der Aufruf SCHEITERT.

Warum auch pop/apply blockiert, nicht nur push/save: die Gefahr ("fremde
Arbeit einspielen/wegnehmen") gilt fuer BEIDE Richtungen gleich -- push
nimmt der gemeinsamen Baustelle etwas weg, pop/apply spielt etwas hinein,
das ein anderer Agent inzwischen ueberschrieben hat. Da push/save hier
verhindert wird, entsteht in dieser Sitzung ohnehin kein neuer Stash zum
Zurueckholen; ein noch vorhandener alter Stash ist ein Sonderfall, den ein
Mensch bewusst und einzeln freigeben soll (Marker-Override), nicht ein
Agent automatisch.

Erlaubt bleiben reine Leseoperationen: `git stash list`, `git stash show`.
Das ist das Werkzeug, mit dem man einen bereits entstandenen Schaden
UEBERHAUPT ERST findet.

Ersatzweg, den die Ablehnung nennt:
  - Vorherigen Stand einer Datei retten: `git show HEAD:<datei> > /tmp/<name>.vorher`
  - Arbeitsbaum-Aenderung an EINER Datei verwerfen: `git checkout HEAD -- <pfad>`

Fail-open: fehlender/kaputter stdin, kein Bash-Aufruf, kein `git stash` in
irgendeiner Statement-Form -> immer durchlassen. Grenze wie beim
Commit-Guard: mehrzeilige Heredocs koennen zeilenweise falsch geschnitten
werden und wuerden dann NICHT erkannt (fail-open, keine Regression).

Einmal-Override (bewusster Mensch, nicht Agent-Automatik):
  touch /tmp/claude-stash-guard-allow
Dauerhaft aus: Umgebungsvariable STASH_GUARD=off (settings.json env).
"""
import json
import os
import shlex
import sys

MARKER = "/tmp/claude-stash-guard-allow"
SHELL_OPS = {"&&", "||", ";", "|"}
READ_SUBCOMMANDS = {"list", "show"}


def allow() -> None:
    sys.exit(0)


def _statements(command: str) -> list:
    """Grobe Shell-Gliederung: zeilenweise, dann &&/||/;/| als Trenner.
    shlex haelt zitierte Strings ('echo "git stash"') als EIN Token
    zusammen -- ein blosses Vorkommen der Zeichenfolge in Anfuehrungszeichen
    wird so NICHT als Aufruf erkannt."""
    out, cur = [], []
    for line in command.splitlines():
        try:
            lex = shlex.shlex(line, posix=True, punctuation_chars=True)
            lex.whitespace_split = True
            toks = list(lex)
        except ValueError:
            continue
        for t in toks:
            if t in SHELL_OPS:
                if cur:
                    out.append(cur)
                cur = []
            else:
                cur.append(t)
    if cur:
        out.append(cur)
    return out


def _is_git(token: str) -> bool:
    return token == "git" or token.endswith("/git")


def _find_offending(command: str):
    for tokens in _statements(command):
        for i, t in enumerate(tokens[:-1]):
            if not _is_git(t):
                continue
            if tokens[i + 1] != "stash":
                continue
            rest = tokens[i + 2:]
            sub = next((a for a in rest if not a.startswith("-")), None)
            if sub in READ_SUBCOMMANDS:
                continue  # list/show -- lesend, erlaubt
            return " ".join(tokens[i:])
    return None


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        allow()

    if data.get("tool_name") != "Bash":
        allow()

    command = str((data.get("tool_input") or {}).get("command") or "")
    if not command:
        allow()

    offending = _find_offending(command)
    if offending is None:
        allow()

    if os.environ.get("STASH_GUARD", "").lower() == "off":
        allow()

    if os.path.exists(MARKER):
        try:
            os.remove(MARKER)
        except OSError:
            pass
        allow()

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"'{offending}' wirkt auf den GANZEN Arbeitsbaum und kann in "
                "einer Sitzung mit mehreren schreibenden Agenten fremde "
                "Arbeit einspielen oder wegnehmen (Vorfall 2026-07-31, fuenf "
                "Dateien mit Konfliktmarkern). git stash ist in diesem Repo "
                "gesperrt -- auch pop/apply, weil sie dieselbe Gefahr in die "
                "andere Richtung tragen. Lesend erlaubt: `git stash list`, "
                "`git stash show`. Ersatzweg: eine Datei vor einer Aenderung "
                "sichern mit `git show HEAD:<datei> > /tmp/<name>.vorher`, "
                "eine Arbeitsbaum-Aenderung verwerfen mit "
                "`git checkout HEAD -- <pfad>`. Einmal-Ausnahme (nur der "
                "Mensch, nicht der Agent): `touch /tmp/claude-stash-guard-allow`."
            ),
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
