from __future__ import annotations

import tempfile
from pathlib import Path

from Engineering.py.cipher.graph.merge import (
    merge_local_python,
)
from Engineering.py.cipher.ir.document import (
    SourceArtifact,
)
from Engineering.py.cipher.sources.cpp_source import (
    load_cpp,
)
from Engineering.py.cipher.sources.json_source import (
    load_json,
)
from Engineering.py.cipher.sources.python_source import (
    load_python,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_single(
    document,
    source: Path,
    family: str,
    extension: str,
) -> None:
    require(
        len(document.sources) == 1,
        repr(document.sources),
    )

    item = document.sources[0]

    require(
        item.path == str(source),
        repr(item),
    )

    require(
        item.family == family,
        repr(item),
    )

    require(
        item.extension == extension,
        repr(item),
    )


def check_artifact(
    path: Path,
    family: str,
    extension: str,
) -> None:
    item = SourceArtifact.from_path(
        path,
        family,
    )

    require(
        item.path == str(path),
        repr(item),
    )

    require(
        item.family == family,
        repr(item),
    )

    require(
        item.extension == extension,
        repr(item),
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        py = root / "sample.py"
        py.write_text(
            "value = 1\n",
            encoding="utf-8",
        )

        check_single(
            load_python(py),
            py,
            "Python",
            ".py",
        )

        js = root / "sample.json"
        js.write_text(
            '{"value": 1}\n',
            encoding="utf-8",
        )

        check_single(
            load_json(js),
            js,
            "JSON",
            ".json",
        )

        # Provenance must preserve exact YAML suffix independently
        # of whether this host currently has a YAML parser installed.
        yaml = root / "sample.yaml"
        check_artifact(
            yaml,
            "YAML",
            ".yaml",
        )

        yml = root / "sample.yml"
        check_artifact(
            yml,
            "YAML",
            ".yml",
        )

        cpp = root / "sample.cpp"
        cpp.write_text(
            "int value = 1;\n",
            encoding="utf-8",
        )

        check_single(
            load_cpp(cpp),
            cpp,
            "C++",
            ".cpp",
        )

        hpp = root / "sample.hpp"
        hpp.write_text(
            "int value;\n",
            encoding="utf-8",
        )

        check_single(
            load_cpp(hpp),
            hpp,
            "C++",
            ".hpp",
        )

        package = root / "package"
        package.mkdir()

        entry = package / "main.py"
        helper = package / "helper.py"

        entry.write_text(
            "from helper import value\n"
            "result = value\n",
            encoding="utf-8",
        )

        helper.write_text(
            "value = 42\n",
            encoding="utf-8",
        )

        merged = merge_local_python(
            entry,
            package,
        )

        provenance = [
            (
                Path(item.path).name,
                item.family,
                item.extension,
            )
            for item in merged.document.sources
        ]

        require(
            provenance
            == [
                (
                    "main.py",
                    "Python",
                    ".py",
                ),
                (
                    "helper.py",
                    "Python",
                    ".py",
                ),
            ],
            repr(provenance),
        )

    print(
        "CIPHER_SOURCE_PROVENANCE=PASS"
    )


if __name__ == "__main__":
    main()
