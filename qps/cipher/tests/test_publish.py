from __future__ import annotations

import os
import tempfile
from pathlib import Path

from qps.cipher.plan import build_conversion_plan
from qps.cipher.publish import publish_conversion




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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    repo = _repo_root()
    qps = repo / "qps/cpp/build-pixel/qps"

    os.environ["QPS_EXECUTABLE"] = str(qps)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        source = root / "source"
        output = root / "output"
        source.mkdir()

        (source / "a.py").write_text(
            "VALUE = 2\n",
            encoding="utf-8",
        )

        (source / "b.py").write_text(
            "def twice(x):\n"
            "    value = x * 2\n"
            "    return value\n",
            encoding="utf-8",
        )

        plan = build_conversion_plan(
            source,
            output,
            workspace_root=repo,
        )

        require(
            plan.ready,
            repr(plan.blockers),
        )

        require(
            not output.exists(),
            "planning mutated destination",
        )

        published = publish_conversion(
            plan,
        )

        require(
            len(published) == 2,
            repr(published),
        )

        require(
            (output / "a.qps").exists(),
            "a.qps missing",
        )

        require(
            (output / "b.qps").exists(),
            "b.qps missing",
        )

        # A blocked plan must publish nothing.
        bad_source = root / "bad_source"
        bad_output = root / "bad_output"
        bad_source.mkdir()

        (bad_source / "good.py").write_text(
            "VALUE = 42\n",
            encoding="utf-8",
        )

        (bad_source / "bad.py").write_text(
            "def broken(:\n",
            encoding="utf-8",
        )

        blocked = build_conversion_plan(
            bad_source,
            bad_output,
            workspace_root=repo,
        )

        require(
            not blocked.ready,
            "bad source unexpectedly ready",
        )

        try:
            publish_conversion(
                blocked,
            )
        except RuntimeError:
            pass
        else:
            raise AssertionError(
                "blocked plan unexpectedly published"
            )

        require(
            not bad_output.exists()
            or not any(bad_output.rglob("*.qps")),
            "blocked plan mutated destination",
        )

        # A failure after the first published file must roll back
        # every output created by this transaction.
        rollback_source = root / "rollback_source"
        rollback_output = root / "rollback_output"
        rollback_source.mkdir()

        (rollback_source / "one.py").write_text(
            "ONE = 1\n",
            encoding="utf-8",
        )

        (rollback_source / "two.py").write_text(
            "TWO = 2\n",
            encoding="utf-8",
        )

        rollback_plan = build_conversion_plan(
            rollback_source,
            rollback_output,
            workspace_root=repo,
        )

        require(
            rollback_plan.ready,
            repr(rollback_plan.blockers),
        )

        try:
            publish_conversion(
                rollback_plan,
                fail_after=1,
            )
        except RuntimeError as exc:
            require(
                "injected Cipher publication failure"
                in str(exc),
                str(exc),
            )
        else:
            raise AssertionError(
                "injected publication failure did not fire"
            )

        require(
            not (rollback_output / "one.qps").exists(),
            "first published output survived rollback",
        )

        require(
            not (rollback_output / "two.qps").exists(),
            "second output exists after rollback",
        )

        require(
            not rollback_output.exists()
            or not any(rollback_output.rglob("*.qps")),
            "rollback left published QPS files",
        )

    print("CIPHER_PUBLISH=PASS")


if __name__ == "__main__":
    main()
