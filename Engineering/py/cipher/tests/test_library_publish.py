from __future__ import annotations

import os
import tempfile
from pathlib import Path

from Engineering.py.cipher.ir.nodes import (
    DependencyRef,
)
from Engineering.py.cipher.libs.population import (
    plan_python_library_symbol,
)
from Engineering.py.cipher.libs.publish import (
    publish_library_plan,
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    repo = Path(__file__).resolve().parents[4]

    os.environ["QPS_EXECUTABLE"] = str(
        repo / "qps/cpp/build-pixel/qps"
    )

    with tempfile.TemporaryDirectory(
        dir=os.environ.get("TMPDIR")
    ) as tmp:
        root = Path(tmp)

        python = (
            root
            / "qps/libs/Python"
        )

        python.mkdir(
            parents=True
        )

        original_index = '''Python.

surface: (
);
'''

        (
            python / "_index.qps"
        ).write_text(
            original_index,
            encoding="utf-8",
        )

        dependency = DependencyRef(
            package="demo",
            module="demo.geometry",
            symbol="Cylinder",
        )

        plan = plan_python_library_symbol(
            dependency,
            root,
            '''Cylinder.

identity- "construct.cylinder";
''',
        )

        # Prove rollback restores an updated parent index
        # as well as deleting newly-created files.
        try:
            publish_library_plan(
                plan,
                fail_after=2,
            )
        except RuntimeError as exc:
            require(
                "injected library publication failure"
                in str(exc),
                str(exc),
            )
        else:
            raise AssertionError(
                "Injected failure did not fire"
            )

        require(
            (
                python / "_index.qps"
            ).read_text(
                encoding="utf-8"
            )
            == original_index,
            "Parent index was not restored",
        )

        require(
            not (
                python / "demo"
            ).exists(),
            "Failed transaction left namespace files",
        )

        published = publish_library_plan(
            plan
        )

        require(
            published,
            "Successful plan published nothing",
        )

        require(
            (
                python
                / "demo/geometry/Cylinder.qps"
            ).exists(),
            "Symbol file missing after publication",
        )

    print(
        "CIPHER_LIBRARY_PUBLISH=PASS"
    )


if __name__ == "__main__":
    main()
