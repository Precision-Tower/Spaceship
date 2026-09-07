from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .population import (
    LibraryPopulationPlan,
    PlannedLibraryWrite,
)


@dataclass(frozen=True)
class PublishedLibraryWrite:
    path: Path
    kind: str


def _qps_executable() -> Path:
    configured = os.environ.get(
        "QPS_EXECUTABLE"
    )

    if configured:
        path = Path(configured).resolve()

        if path.exists():
            return path

    candidate = (
        Path.cwd()
        / "qps/cpp/build-pixel/qps"
    ).resolve()

    if candidate.exists():
        return candidate

    raise RuntimeError(
        "QPS executable not found; "
        "set QPS_EXECUTABLE"
    )


def _validate_candidate(
    qps: Path,
    candidate: Path,
) -> None:
    import subprocess

    result = subprocess.run(
        [
            str(qps),
            str(candidate),
            "--check",
        ],
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        detail = (
            result.stderr.strip()
            or result.stdout.strip()
            or "QPS validation failed"
        )

        raise RuntimeError(
            f"{candidate}: {detail}"
        )


def publish_library_plan(
    plan: LibraryPopulationPlan,
    *,
    fail_after: int | None = None,
) -> list[PublishedLibraryWrite]:
    if not plan.writes:
        return []

    paths = [
        write.path.resolve()
        for write in plan.writes
    ]

    if len(paths) != len(set(paths)):
        raise RuntimeError(
            "Library publication plan contains "
            "duplicate write paths."
        )

    qps = _qps_executable()

    tmp_root = os.environ.get("TMPDIR")

    with tempfile.TemporaryDirectory(
        prefix="ceos-lib-stage.",
        dir=tmp_root,
    ) as temporary:
        stage = Path(temporary)

        # Stage and validate every final candidate before
        # touching qps/libs.
        for index, write in enumerate(
            plan.writes
        ):
            candidate = (
                stage
                / f"{index:08d}.qps"
            )

            candidate.write_text(
                write.content,
                encoding="utf-8",
            )

            _validate_candidate(
                qps,
                candidate,
            )

        original: dict[
            Path,
            str | None,
        ] = {}

        published: list[
            PublishedLibraryWrite
        ] = []

        try:
            for write in plan.writes:
                target = write.path.resolve()

                if target in original:
                    raise RuntimeError(
                        "Duplicate target during "
                        f"publication: {target}"
                    )

                if target.exists():
                    original[target] = (
                        target.read_text(
                            encoding="utf-8"
                        )
                    )
                else:
                    original[target] = None

                target.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                target.write_text(
                    write.content,
                    encoding="utf-8",
                )

                published.append(
                    PublishedLibraryWrite(
                        path=target,
                        kind=write.kind,
                    )
                )

                if (
                    fail_after is not None
                    and len(published)
                    >= fail_after
                ):
                    raise RuntimeError(
                        "injected library "
                        "publication failure"
                    )

        except Exception:
            # Restore every file touched by this transaction.
            for target, previous in reversed(
                list(original.items())
            ):
                if previous is None:
                    try:
                        target.unlink()
                    except FileNotFoundError:
                        pass
                else:
                    target.write_text(
                        previous,
                        encoding="utf-8",
                    )

            # Remove only newly-created empty directories.
            for write in reversed(
                plan.writes
            ):
                parent = (
                    write.path.resolve().parent
                )

                while parent != parent.parent:
                    try:
                        parent.rmdir()
                    except OSError:
                        break

                    parent = parent.parent

            raise

        return published
