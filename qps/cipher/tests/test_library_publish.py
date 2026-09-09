from __future__ import annotations

import os
import tempfile
from tempfile import TemporaryDirectory
from pathlib import Path

from qps.cipher.ir.nodes import (

    DependencyRef,
)
from qps.cipher.foreign.population import (
    plan_python_library_symbol,
)
from qps.cipher.foreign.publish import (
    publish_library_plan,
)



def _repo_root() -> Path:
    current = Path(__file__).resolve().parent

    for candidate in (current, *current.parents):
        if (
            (candidate / ".git").exists()
            and (candidate / "qps").is_dir()
            and (candidate / "Engineering").is_dir()
        ):
            return candidate

    raise RuntimeError("CE-OS repository root not found")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    repo = _repo_root()
    os.environ["QPS_EXECUTABLE"] = str(
        repo / "qps/cpp/build-pixel/qps"
    )

    with tempfile.TemporaryDirectory(
        dir=os.environ.get("TMPDIR")
    ) as tmp:
        root = Path(tmp)

        python = (
            root
            / "libs/Python"
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


def test_capability_materialization_does_not_promote_member_path_to_module():
    from qps.cipher.foreign.population import plan_python_library_capability
    from qps.cipher.ir.nodes import DependencyRef

    with TemporaryDirectory() as raw:
        root = Path(raw)
        python = root / "libs/Python"
        python.mkdir(parents=True)
        (python / "_index.qps").write_text(
            "Python.\n\nsurface: (\n);\n",
            encoding="utf-8",
        )
        dependency = DependencyRef(
            package="pkg",
            module="pkg.mod",
            symbol=None,
        )
        plan = plan_python_library_capability(
            dependency,
            root,
            ("ClassName", "method"),
            'identity- "pkg.mod.ClassName.method";\n',
        )
        paths = [write.path.relative_to(root).as_posix() for write in plan.writes]
        assert not any("/ClassName/_index.qps" in path for path in paths)
        assert any(
            path.endswith("/ClassName.method.qps")
            for path in paths
        )


def test_multiple_capabilities_publish_as_one_atomic_transaction():
    from qps.cipher.foreign.population import (
        merge_library_population_plans,
        plan_python_library_capability,
    )
    from qps.cipher.ir.nodes import DependencyRef

    with TemporaryDirectory() as raw:
        root = Path(raw)
        python = root / "libs/Python"
        python.mkdir(parents=True)
        original = 'Python.\n\nsurface: (\n);\n'
        (python / "_index.qps").write_text(original)

        dependency = DependencyRef(
            package="pkg",
            module="pkg.mod",
            symbol=None,
        )
        first = plan_python_library_capability(
            dependency, root, ("first",),
            'first.\nidentity- "pkg.mod.first";\n',
        )
        second = plan_python_library_capability(
            dependency, root, ("second",),
            'second.\nidentity- "pkg.mod.second";\n',
        )
        merged = merge_library_population_plans([first, second])

        try:
            publish_library_plan(merged, fail_after=3)
        except RuntimeError as exc:
            assert "injected library publication failure" in str(exc)
        else:
            raise AssertionError("transaction injection did not fire")

        assert (python / "_index.qps").read_text() == original
        assert not (python / "pkg").exists()

        publish_library_plan(merged)
        module = python / "pkg/mod"
        assert (module / "first.qps").exists()
        assert (module / "second.qps").exists()
        surface = (module / "_index.qps").read_text()
        assert 'first- "first.qps";' in surface
        assert 'second- "second.qps";' in surface

if __name__ == "__main__":
    main()
    test_capability_materialization_does_not_promote_member_path_to_module()
    test_multiple_capabilities_publish_as_one_atomic_transaction()
    print("CIPHER_CAPABILITY_LIBRARY_PUBLISH=PASS")
