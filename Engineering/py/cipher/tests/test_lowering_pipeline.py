from __future__ import annotations

import tempfile
from pathlib import Path

from Engineering.py.cipher.cipher import (
    emit_prepared_document,
    prepare_document,
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
        root = Path(tmp)
        source = root / "cylinder.py"

        source.write_text(
            "from OCC.Core.BRepPrimAPI import "
            "BRepPrimAPI_MakeCylinder as Cylinder\n"
            "\n"
            "def build(radius, height):\n"
            "    body = Cylinder(radius, height)\n"
            "    return body\n",
            encoding="utf-8",
        )

        document = prepare_document(source)

        semantic = [
            node
            for root_node in document.children
            for node in walk(root_node)
            if node.kind == "semantic_call"
        ]

        require(
            len(semantic) == 1,
            repr(semantic),
        )

        require(
            semantic[0].name == "construct.cylinder",
            repr(semantic[0]),
        )

        # Preparation is independently inspectable. Emission still
        # rejects semantic_call until that backend representation is
        # explicitly implemented.
        rejected = False

        try:
            emit_prepared_document(
                document,
                converge=False,
                workspace_root=root,
            )
        except ValueError as exc:
            rejected = (
                "semantic_call"
                in str(exc)
            )

        require(
            rejected,
            "unimplemented semantic_call unexpectedly emitted",
        )

    print("CIPHER_LOWERING_PIPELINE=PASS")


if __name__ == "__main__":
    main()
