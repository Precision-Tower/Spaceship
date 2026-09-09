from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from qps.cipher.plan import ConversionPlan


@dataclass(frozen=True)
class StagedUnit:
    source: Path
    destination: Path
    staged: Path


def _qps_executable() -> Path:
    configured = os.environ.get("QPS_EXECUTABLE")

    if configured:
        return Path(configured).resolve()

    candidate = (
        Path.cwd()
        / "qps/cpp/build-pixel/qps"
    ).resolve()

    if candidate.exists():
        return candidate

    raise RuntimeError(
        "QPS executable not found; set QPS_EXECUTABLE"
    )


def publish_conversion(
    plan: ConversionPlan,
    *,
    fail_after: int | None = None,
) -> list[Path]:
    if not plan.ready:
        raise RuntimeError(
            "conversion plan is not ready"
        )

    if not plan.units:
        raise RuntimeError(
            "conversion plan contains no units"
        )

    # A topology-preserving plan must never map two source units
    # onto the same authored QPS file. Reject the transaction before
    # staging or touching any destination.
    destinations = [
        unit.destination.resolve()
        for unit in plan.units
    ]

    if len(destinations) != len(set(destinations)):
        duplicates = sorted(
            {
                str(destination)
                for destination in destinations
                if destinations.count(destination) > 1
            }
        )

        raise RuntimeError(
            "conversion plan contains duplicate destinations: "
            + ", ".join(duplicates)
        )

    # Recheck immediately before staging. The plan may have been
    # created before another process populated a destination.
    for unit in plan.units:
        if unit.destination.exists():
            raise RuntimeError(
                "destination appeared after planning: "
                f"{unit.destination}"
            )

    with tempfile.TemporaryDirectory(
        prefix="ce-os-cipher-"
    ) as tmp:
        stage_root = Path(tmp)
        staged_units: list[StagedUnit] = []

        # Phase 1: emit everything into an isolated staging tree.
        for index, unit in enumerate(plan.units):
            staged = (
                stage_root
                / "outputs"
                / f"{index:08d}.qps"
            )

            staged.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            if unit.candidate is None:
                raise RuntimeError(
                    "ready conversion unit has no candidate: "
                    f"{unit.source}"
                )

            staged.write_text(
                unit.candidate,
                encoding="utf-8",
            )

            staged_units.append(
                StagedUnit(
                    source=unit.source,
                    destination=unit.destination,
                    staged=staged,
                )
            )

        # Candidates were already QPS-validated when the
        # ConversionPlan was created.

        # Recheck every destination after potentially expensive
        # translation/validation and immediately before publication.
        for unit in staged_units:
            if unit.destination.exists():
                raise RuntimeError(
                    "destination appeared before publication: "
                    f"{unit.destination}"
                )

        published: list[Path] = []

        try:
            # Phase 3: publication. No destination has been touched
            # before this point.
            for unit in staged_units:
                unit.destination.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                # Exclusive creation preserves Cipher's no-overwrite
                # contract even if a race occurs after the recheck.
                with unit.destination.open(
                    "x",
                    encoding="utf-8",
                ) as handle:
                    handle.write(
                        unit.staged.read_text(
                            encoding="utf-8"
                        )
                    )

                published.append(
                    unit.destination
                )

                if (
                    fail_after is not None
                    and len(published) >= fail_after
                ):
                    raise RuntimeError(
                        "injected Cipher publication failure"
                    )

        except Exception:
            # Roll back files created by this publication attempt.
            for destination in reversed(published):
                try:
                    destination.unlink()
                except FileNotFoundError:
                    pass

            # Remove empty directories created beneath destination
            # parents where possible. Never remove non-empty or
            # pre-existing content.
            for unit in reversed(staged_units):
                parent = unit.destination.parent

                while parent != parent.parent:
                    try:
                        parent.rmdir()
                    except OSError:
                        break

                    parent = parent.parent

            raise

        return published
