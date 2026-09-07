from __future__ import annotations

import tempfile
from pathlib import Path

from Engineering.py.cipher.lower.semantic_calls import (
    lower_semantic_calls,
)
from Engineering.py.cipher.sources.python_source import (
    load_python,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "cylinder.py"

        source.write_text(
            "from OCC.Core.BRepPrimAPI import "
            "BRepPrimAPI_MakeCylinder as Cylinder\n"
            "\n"
            "def build(radius, height):\n"
            "    body = Cylinder(radius, height)\n"
            "    return body\n",
            encoding="utf-8",
        )

        original = load_python(source)
        lowered = lower_semantic_calls(original)

        original_calls = [
            node
            for root in original.children
            for node in walk(root)
            if node.kind == "call"
        ]

        semantic_calls = [
            node
            for root in lowered.children
            for node in walk(root)
            if node.kind == "semantic_call"
        ]

        require(
            len(original_calls) == 1,
            repr(original_calls),
        )
        require(
            original_calls[0].name == "Cylinder",
            repr(original_calls[0]),
        )

        require(
            len(semantic_calls) == 1,
            repr(semantic_calls),
        )

        call = semantic_calls[0]

        require(
            call.name == "construct.cylinder",
            repr(call),
        )

        require(
            len(call.children) == 2,
            repr(call.children),
        )

        arguments = [
            child.children[0]
            for child in call.children
        ]

        require(
            [argument.name for argument in arguments]
            == ["radius", "height"],
            repr(arguments),
        )

        function = next(
            node
            for node in lowered.children
            if node.kind == "function"
            and node.name == "build"
        )

        parameters = [
            child.name
            for child in function.children
            if child.kind == "parameter"
        ]

        require(
            parameters == ["radius", "height"],
            repr(parameters),
        )

        require(
            all(
                "BRepPrimAPI_MakeCylinder"
                not in (node.name or "")
                for root in lowered.children
                for node in walk(root)
                if node.kind == "semantic_call"
            ),
            "Implementation identity survived semantic call",
        )

    print("CIPHER_SEMANTIC_CALL_LOWERING=PASS")


if __name__ == "__main__":
    main()
