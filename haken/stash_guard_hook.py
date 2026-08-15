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

Nachtrag 2026-08-15 (Fehlalarm behoben): Eine Commit-Nachricht, die den
Ausdruck "git stash" nur BESCHREIBT (Heredoc-Rumpf zu `git commit -F -`),
wurde bislang abgelehnt -- die alte Zeilen-fuer-Zeilen-Abtastung machte
keinen Unterschied zwischen Text und Aufruf. Die Grenze jetzt: Ein
Heredoc-Rumpf ist BEFEHL (wird abgetastet), wenn der EMPFANGENDE Befehl
selbst eine Shell/ein Interpreter ist (`sh`/`bash`/`zsh`/`dash`/`ksh`,
`eval`, `source`) -- dann liest diese Shell den Rumpf als Kommandozeilen
und fuehrt sie aus. Sonst (z.B. `cat`, `git commit -F -`, `tee`) ist der
Rumpf DATEN und wird nicht als Aufruf gewertet, AUSSER der Delimiter ist
unquotiert (`<<EOF` statt `<<'EOF'`) -- dann fuehrt die AEUSSERE Shell noch
Kommando-Substitution (`$(...)`, Backticks) im Rumpf aus, und genau die wird
weiter abgetastet. Gleiches Prinzip fuer `sh -c "..."`/`bash -c "..."`/
`eval "..."`: der String-Inhalt wird rekursiv abgetastet, weil er wirklich
ausgefuehrt wird -- anders als eine Commit-Nachricht in `-m`/`-F`.

Benannte Restluecke (siehe auch Docstring von `_find_offending`):
  - Mehrfach verschachtelte `$(...)` im Rumpf eines unquotierten Heredocs
    werden nur EINE Ebene tief erkannt (kein Klammer-Parser).
  - `eval`/`source` als Empfaenger eines Heredocs wird erkannt, ein
    Alias wie `. <<EOF` (Kurzform von `source`) NICHT -- ein einzelner
    Punkt ist von echten Pfaden (`./skript`) nicht sicher unterscheidbar,
    ohne Faelle wie `./skript.sh` faelschlich als Shell-Aufruf zu werten.
  - Statement-Trennung bleibt zeilenweise (siehe unten): eine per
    Backslash-Zeilenumbruch fortgesetzte physische Zeile wird wie zwei
    getrennte behandelt.

Fail-open: fehlender/kaputter stdin, kein Bash-Aufruf, kein `git stash` in
irgendeiner Statement-Form -> immer durchlassen. Grenze wie beim
Commit-Guard: eine per Backslash-Zeilenumbruch fortgesetzte Anweisung wird
zeilenweise falsch geschnitten und dann u.U. NICHT erkannt (fail-open,
keine Regression -- unveraendert gegenueber vorher).

Einmal-Override (bewusster Mensch, nicht Agent-Automatik):
  touch /tmp/claude-stash-guard-allow
Dauerhaft aus: Umgebungsvariable STASH_GUARD=off (settings.json env).
"""
import json
import os
import re
import shlex
import sys

MARKER = "/tmp/claude-stash-guard-allow"
SHELL_OPS = {"&&", "||", ";", "|"}
READ_SUBCOMMANDS = {"list", "show"}
SHELL_INTERPRETERS = {"sh", "bash", "zsh", "dash", "ksh"}
SHELL_EXEC_WORDS = {"eval", "source"}

# <<-?  optional '-' (Tabs im Rumpf/Delimiter werden ignoriert)
# dann entweder 'DELIM' / "DELIM" (Anfuehrung -> literaler Rumpf) /
# \DELIM (Backslash -> literaler Rumpf) / DELIM (unquotiert -> Rumpf wird
# noch auf Kommando-Substitution durchsucht).
HEREDOC_RE = re.compile(
    r"<<(-)?\s*(?:(['\"])(\w+)\2|(\\)(\w+)|(\w+))"
)
# Eine Ebene von $(...) bzw. `...` -- siehe Restluecke oben.
SUBST_RE = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")


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


def _basename(token: str) -> str:
    return token.rsplit("/", 1)[-1]


def _receiver_of(text: str) -> str | None:
    """Erstes Wort des LETZTEN Statements in `text` -- der Befehl, an den
    ein am Ende von `text` stehender Heredoc-Redirect gebunden ist."""
    stmts = _statements(text)
    if not stmts or not stmts[-1]:
        return None
    return _basename(stmts[-1][0])


def _check_tokens(tokens: list) -> str | None:
    """Prueft EIN Statement (bereits durch &&/||/;/| getrennte Tokenliste)
    auf `git stash <schreibend>` UND auf `sh|bash|zsh|dash|ksh -c "..."`
    bzw. `eval "..."`/`source "..."` -- deren String-Argument wird
    tatsaechlich ausgefuehrt und deshalb rekursiv abgetastet."""
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

    for i, t in enumerate(tokens):
        base = _basename(t)
        if base in SHELL_INTERPRETERS:
            if "-c" in tokens[i + 1:]:
                idx_c = tokens.index("-c", i + 1)
                if idx_c + 1 < len(tokens):
                    off = _find_offending(tokens[idx_c + 1])
                    if off:
                        return off
        elif base in SHELL_EXEC_WORDS and i + 1 < len(tokens):
            off = _find_offending(" ".join(tokens[i + 1:]))
            if off:
                return off
    return None


def _scan_text(text: str) -> str | None:
    """Wie `_find_offending`, aber OHNE Heredoc-Behandlung -- fuer Text, der
    bereits als Rumpf/Substitution isoliert wurde (Rekursionsbasis)."""
    for tokens in _statements(text):
        off = _check_tokens(tokens)
        if off:
            return off
    return None


def _scan_substitutions(text: str) -> str | None:
    """Kommando-Substitution `$(...)`/Backtick in einem Heredoc-Rumpf mit
    UNQUOTIERTEM Delimiter wird von der AEUSSEREN Shell trotzdem ausgefuehrt
    -- anders als der Rest des Rumpfs (der bleibt Daten fuer den Empfaenger).
    Nur eine Klammerebene, siehe Restluecke im Modulkopf."""
    for m in SUBST_RE.finditer(text):
        inner = m.group(1) if m.group(1) is not None else m.group(2)
        off = _find_offending(inner)
        if off:
            return off
    return None


def _find_offending(command: str):
    """Zeile fuer Zeile, mit Sonderbehandlung fuer Heredocs (`<<DELIM`):
    Der Rumpf ist nur dann ein AUFRUF (wird abgetastet), wenn der
    empfangende Befehl selbst eine Shell/ein Interpreter ist -- sonst ist
    der Rumpf DATEN (z.B. eine Commit-Nachricht) und wird nicht als `git
    stash` gewertet, selbst wenn der Text die Worte enthaelt."""
    lines = command.splitlines()
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        m = HEREDOC_RE.search(line)
        if m is None:
            off = _scan_text(line)
            if off:
                return off
            i += 1
            continue

        strip_tabs = m.group(1) == "-"
        literal = m.group(2) is not None or m.group(4) is not None
        delim = m.group(3) or m.group(5) or m.group(6)

        # Text VOR dem Redirect gehoert weiter zum normalen Statement
        # (z.B. `cd /tmp && sh <<'EOF'`).
        off = _scan_text(line[: m.start()])
        if off:
            return off
        receiver = _receiver_of(line[: m.start()])

        body_lines = []
        j = i + 1
        while j < n:
            body = lines[j]
            cmp_line = body.lstrip("\t") if strip_tabs else body
            if cmp_line.rstrip("\r") == delim:
                break
            body_lines.append(body)
            j += 1
        body_text = "\n".join(body_lines)

        if receiver in SHELL_INTERPRETERS or receiver in SHELL_EXEC_WORDS:
            # Rumpf geht an eine Shell -> wird von IHR als Befehle gelesen.
            off = _find_offending(body_text)
        elif not literal:
            # Unquotierter Delimiter -> Kommando-Substitution im Rumpf
            # wird von der AEUSSEREN Shell noch ausgefuehrt, der Rest bleibt
            # Daten.
            off = _scan_substitutions(body_text)
        else:
            # Quotierter/escapter Delimiter an einen Nicht-Shell-Empfaenger
            # (z.B. `git commit -F -`) -> reiner Text, keine Ausfuehrung.
            off = None
        if off:
            return off

        i = j + 1  # Delimiter-Zeile selbst ueberspringen
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
