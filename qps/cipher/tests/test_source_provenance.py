from __future__ import annotations

import tempfile
from pathlib import Path

from qps.cipher.ir.document import (
    SourceArtifact,
)
from qps.cipher.sources.cpp_source import (
    load_cpp,
)
from qps.cipher.sources.json_source import (
    load_json,
)
from qps.cipher.sources.python_source import (
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

        entry_document = load_python(
            entry
        )

        helper_document = load_python(
            helper
        )

        require(
            len(entry_document.sources) == 1,
            repr(entry_document.sources),
        )

        require(
            len(helper_document.sources) == 1,
            repr(helper_document.sources),
        )

        entry_source = entry_document.sources[0]
        helper_source = helper_document.sources[0]

        require(
            Path(entry_source.path).resolve()
            == entry.resolve(),
            repr(entry_source),
        )

        require(
            Path(helper_source.path).resolve()
            == helper.resolve(),
            repr(helper_source),
        )

        require(
            entry_source.family == "Python",
            repr(entry_source),
        )

        require(
            helper_source.family == "Python",
            repr(helper_source),
        )

        require(
            entry_source.extension == ".py",
            repr(entry_source),
        )

        require(
            helper_source.extension == ".py",
            repr(helper_source),
        )

    print(
        "CIPHER_SOURCE_PROVENANCE=PASS"
    )


if __name__ == "__main__":
    main()
