from __future__ import annotations

import re
from pathlib import Path

from ..ir.document import CipherDocument
from ..ir.nodes import CipherNode, SourceRef, TranslationState


_FUNCTION_RE = re.compile(
    r"""
    (?P<prefix>
        (?:[A-Za-z_][A-Za-z0-9_:<>,*&\s]*?)
    )
    (?P<name>
        [A-Za-z_][A-Za-z0-9_:~]*
    )
    \s*
    \(
        (?P<params>[^;{}]*)
    \)
    \s*
    (?:
        const\s*
    )?
    \{
    """,
    re.VERBOSE | re.MULTILINE,
)

_INCLUDE_RE = re.compile(
    r'^\s*#include\s+(?P<target><[^>]+>|"[^"]+")',
    re.MULTILINE,
)

_CALL_RE = re.compile(
    r'(?<![\w:])'
    r'(?P<name>[A-Za-z_][A-Za-z0-9_:]*(?:::[A-Za-z_][A-Za-z0-9_]*)*)'
    r'\s*\('
)

_OPERATION_COMPARE_RE = re.compile(
    r'''
    (?P<lhs>
        [A-Za-z_][A-Za-z0-9_.>\-]*
        \.operation
    )
    \s*
    (?P<op>==|!=)
    \s*
    "(?P<value>[^"]+)"
    ''',
    re.VERBOSE,
)

_STRING_RE = re.compile(r'"(?:\\.|[^"\\])*"')


_CONTROL_NAMES = {
    "if",
    "for",
    "while",
    "switch",
    "return",
    "sizeof",
    "catch",
}


def _line_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _source(path: Path, text: str, offset: int) -> SourceRef:
    return SourceRef(
        language="cpp",
        path=str(path),
        line=_line_for_offset(text, offset),
        column=None,
    )


def _matching_brace(text: str, opening: int) -> int | None:
    depth = 0
    i = opening

    in_string = False
    in_char = False
    in_line_comment = False
    in_block_comment = False
    escape = False

    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if in_char:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "'":
                in_char = False
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue

        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue

        if ch == '"':
            in_string = True
            i += 1
            continue

        if ch == "'":
            in_char = True
            i += 1
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1

            if depth == 0:
                return i

        i += 1

    return None


def _parameters(
    path: Path,
    text: str,
    raw: str,
    offset: int,
) -> list[CipherNode]:
    raw = raw.strip()

    if not raw or raw == "void":
        return []

    result = []

    for parameter in raw.split(","):
        parameter = parameter.strip()

        if not parameter:
            continue

        # This is intentionally structural rather than a full C++ declarator
        # parser. Preserve the complete declaration as evidence.
        pieces = parameter.replace("&", " & ").replace("*", " * ").split()

        name = pieces[-1] if pieces else None

        result.append(
            CipherNode(
                kind="parameter",
                name=name,
                value=parameter,
                source=_source(path, text, offset),
                state=TranslationState.MAPPED,
                notes=[
                    "Constrained C++ parameter extraction; full declarator preserved as value."
                ],
            )
        )

    return result


def _body_structure(
    path: Path,
    full_text: str,
    body: str,
    body_offset: int,
) -> list[CipherNode]:
    children: list[CipherNode] = []

    for match in _OPERATION_COMPARE_RE.finditer(body):
        children.append(
            CipherNode(
                kind="comparison",
                name=match.group("op"),
                value=match.group("value"),
                children=[
                    CipherNode(
                        kind="reference",
                        name=match.group("lhs"),
                        source=_source(
                            path,
                            full_text,
                            body_offset + match.start(),
                        ),
                        state=TranslationState.MAPPED,
                    )
                ],
                source=_source(
                    path,
                    full_text,
                    body_offset + match.start(),
                ),
                state=TranslationState.MAPPED,
                notes=[
                    "C++ operation dispatch comparison."
                ],
            )
        )

    seen_calls: set[tuple[str, int]] = set()

    for match in _CALL_RE.finditer(body):
        name = match.group("name")

        if name in _CONTROL_NAMES:
            continue

        line = _line_for_offset(
            full_text,
            body_offset + match.start(),
        )

        key = (name, line)

        if key in seen_calls:
            continue

        seen_calls.add(key)

        children.append(
            CipherNode(
                kind="call",
                name=name,
                source=SourceRef(
                    language="cpp",
                    path=str(path),
                    line=line,
                    column=None,
                ),
                state=TranslationState.MAPPED,
            )
        )

    operation_strings = []

    for match in _STRING_RE.finditer(body):
        value = match.group(0)[1:-1]

        if value in {
            "cylinder",
            "bore",
            "cut",
            "fuse",
            "common",
            "radius",
            "width",
        }:
            operation_strings.append(
                CipherNode(
                    kind="literal",
                    value=value,
                    source=_source(
                        path,
                        full_text,
                        body_offset + match.start(),
                    ),
                    state=TranslationState.DIRECT,
                    notes=[
                        "Geometry-relevant C++ string literal."
                    ],
                )
            )

    if operation_strings:
        children.append(
            CipherNode(
                kind="geometry_vocabulary",
                children=operation_strings,
                source=_source(
                    path,
                    full_text,
                    body_offset,
                ),
                state=TranslationState.MAPPED,
            )
        )

    children.append(
        CipherNode(
            kind="raw_execution",
            name="body",
            value=body,
            source=_source(
                path,
                full_text,
                body_offset,
            ),
            state=TranslationState.DEFERRED,
            notes=[
                "C++ body retained verbatim as evidence; complete executable normalization is deferred."
            ],
        )
    )

    return children


def load_cpp(path: str | Path) -> CipherDocument:
    p = Path(path)
    text = p.read_text(encoding="utf-8")

    children: list[CipherNode] = []

    for match in _INCLUDE_RE.finditer(text):
        children.append(
            CipherNode(
                kind="include",
                value=match.group("target"),
                source=_source(p, text, match.start()),
                state=TranslationState.DIRECT,
            )
        )

    cursor = 0

    while True:
        match = _FUNCTION_RE.search(text, cursor)

        if match is None:
            break

        opening = text.find("{", match.start(), match.end())

        if opening == -1:
            cursor = match.end()
            continue

        closing = _matching_brace(text, opening)

        if closing is None:
            children.append(
                CipherNode(
                    kind="function",
                    name=match.group("name"),
                    source=_source(p, text, match.start()),
                    state=TranslationState.UNRESOLVED,
                    notes=[
                        "Unable to locate matching C++ function brace."
                    ],
                )
            )
            break

        body = text[opening + 1 : closing]

        captured_prefix = match.group("prefix").strip()
        captured_name = match.group("name")

        # The intentionally lightweight function regex may split the
        # first character from a qualified constructor because there
        # is no return type. Repair that constrained case without
        # pretending to be a complete C++ declarator parser.
        if (
            len(captured_prefix) == 1
            and captured_prefix.isalpha()
            and "::" in captured_name
        ):
            captured_name = captured_prefix + captured_name
            captured_prefix = ""

        function_children = _parameters(
            p,
            text,
            match.group("params"),
            match.start("params"),
        )

        function_children.append(
            CipherNode(
                kind="execution",
                name="body",
                children=_body_structure(
                    p,
                    text,
                    body,
                    opening + 1,
                ),
                source=_source(p, text, opening),
                state=TranslationState.DEFERRED,
                notes=[
                    "C++ execution structure partially normalized; full QPS emission deferred."
                ],
            )
        )

        children.append(
            CipherNode(
                kind="function",
                name=captured_name,
                value=captured_prefix,
                children=function_children,
                source=_source(p, text, match.start()),
                state=TranslationState.MAPPED,
            )
        )

        cursor = closing + 1

    return CipherDocument(children=children)
