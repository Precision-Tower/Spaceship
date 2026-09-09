from __future__ import annotations

import tempfile
from pathlib import Path

from qps.cipher.emit.qps_emitter import (
    emit_qps,
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
from qps.cipher.sources.yaml_source import (
    load_yaml,
)


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise AssertionError(message)


def require_source(
    output: str,
    path: str,
    family: str,
    extension: str,
) -> None:
    require(
        f'path- "{path}";'
        in output,
        output,
    )

    require(
        f'family- "{family}";'
        in output,
        output,
    )

    require(
        f'extension- "{extension}";'
        in output,
        output,
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        specimens = [
            (
                root / "sample.py",
                "value = 1\n",
                load_python,
                "Python",
                ".py",
            ),
            (
                root / "sample.json",
                '{"value": 1}\n',
                load_json,
                "JSON",
                ".json",
            ),
            (
                root / "sample.yaml",
                "value: 1\n",
                load_yaml,
                "YAML",
                ".yaml",
            ),
            (
                root / "sample.yml",
                "value: 1\n",
                load_yaml,
                "YAML",
                ".yml",
            ),
            (
                root / "sample.cpp",
                "int value = 1;\n",
                load_cpp,
                "C++",
                ".cpp",
            ),
            (
                root / "sample.hpp",
                "int value;\n",
                load_cpp,
                "C++",
                ".hpp",
            ),
        ]

        for (
            source,
            content,
            loader,
            family,
            extension,
        ) in specimens:
            source.write_text(
                content,
                encoding="utf-8",
            )

            document = loader(source)

            output = emit_qps(
                document,
                workspace_root=root,
            )

            require_source(
                output,
                source.name,
                family,
                extension,
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

        entry_output = emit_qps(
            load_python(entry),
            workspace_root=package,
        )

        helper_output = emit_qps(
            load_python(helper),
            workspace_root=package,
        )

        require_source(
            entry_output,
            "main.py",
            "Python",
            ".py",
        )

        require_source(
            helper_output,
            "helper.py",
            "Python",
            ".py",
        )

        require(
            'path- "helper.py";'
            not in entry_output,
            entry_output,
        )

        require(
            'path- "main.py";'
            not in helper_output,
            helper_output,
        )

    print(
        "CIPHER_EMITTED_PROVENANCE=PASS"
    )


if __name__ == "__main__":
    main()
