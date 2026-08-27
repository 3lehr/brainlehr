"""Shared source-only views for sealed retrieval ablations."""
from __future__ import annotations

import ast
import io
import tokenize


def docstring_lines(source: str) -> set[int]:
    """Return module/class/function docstrings; expression bodies are not lists."""
    lines: set[int] = set()
    for node in ast.walk(ast.parse(source)):
        body = getattr(node, "body", None)
        if (not isinstance(body, list) or not body or not isinstance(body[0], ast.Expr)
                or not isinstance(getattr(body[0], "value", None), ast.Constant)
                or not isinstance(body[0].value.value, str)):
            continue
        lines.update(range(body[0].lineno, body[0].end_lineno + 1))
    return lines


def view(source: str, arm: str) -> str:
    """Build deterministic stripped/comments-only/combined source views."""
    docstrings = docstring_lines(source)
    comments, code = [], []
    rows = source.splitlines()
    ignored = {tokenize.ENCODING, tokenize.ENDMARKER, tokenize.NL, tokenize.NEWLINE,
               tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT}
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT:
            comments.append(token.string)
        elif token.type not in ignored and token.start[0] not in docstrings:
            code.append(token.string)
    docs = [rows[number - 1] for number in sorted(docstrings)]
    if arm == "stripped":
        return " ".join(code)
    if arm == "comments_only":
        return "\n".join([*comments, *docs])
    if arm == "combined":
        return source
    raise ValueError("unknown arm")
