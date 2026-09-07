#!/usr/bin/env python3

import subprocess
import sys
import tempfile
from pathlib import Path


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def run(*args):
    return subprocess.run(
        [str(qps), *map(str, args)],
        text=True,
        capture_output=True,
    )


def require_valid(path: Path):
    result = run(path, "--check")
    require(
        result.returncode == 0,
        f"{path} did not pass QPS check:\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}",
    )


if len(sys.argv) != 2:
    raise SystemExit("usage: cipher_cli_test.py <qps>")

qps = Path(sys.argv[1]).resolve()


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)

    # 1. Simple file -> sibling .qps
    source = root / "simple.py"
    source.write_text(
        "VALUE = 2\n"
        "\n"
        "def twice(x):\n"
        "    value = x * VALUE\n"
        "    return value\n",
        encoding="utf-8",
    )

    result = run("cipher", source)

    require(result.returncode == 0, result.stderr)

    sibling = source.with_suffix(".qps")
    require(
        sibling.exists(),
        "Sibling QPS file was not created",
    )
    require_valid(sibling)

    # 2. A genuinely unavailable foreign dependency blocks.
    foreign_source = root / "foreign_probe.py"
    foreign_source.write_text(
        "from ceos_definitely_missing_package "
        "import MissingThing\n"
        "\n"
        "def build(value):\n"
        "    return MissingThing(value)\n",
        encoding="utf-8",
    )

    foreign_output = root / "foreign_probe.qps"

    preflight = run(
        "cipher",
        "test",
        foreign_source,
        foreign_output,
    )

    require(
        preflight.returncode != 0,
        "Missing foreign preflight unexpectedly succeeded",
    )

    require(
        "CIPHER_FOREIGN "
        "ceos_definitely_missing_package.MissingThing"
        in preflight.stdout,
        preflight.stdout,
    )

    require(
        "ready=false"
        in preflight.stdout,
        preflight.stdout,
    )

    result = run(
        "cipher",
        foreign_source,
        foreign_output,
    )

    require(
        result.returncode != 0,
        "Missing foreign conversion unexpectedly succeeded",
    )

    require(
        not foreign_output.exists(),
        "Blocked foreign conversion wrote output",
    )

    # 3. Directory -> mirrored destination tree
    source_tree = root / "python"
    destination_tree = root / "converted"

    (source_tree / "Physics" / "Domains").mkdir(parents=True)

    (source_tree / "Physics" / "constants.py").write_text(
        "GRAVITY = 9.81\n",
        encoding="utf-8",
    )

    (source_tree / "Physics" / "Domains" / "motion.py").write_text(
        "def velocity(distance, time):\n"
        "    return distance / time\n",
        encoding="utf-8",
    )

    result = run(
        "cipher",
        source_tree,
        destination_tree,
    )

    require(result.returncode == 0, result.stderr)

    constants_qps = (
        destination_tree / "Physics" / "constants.qps"
    )
    motion_qps = (
        destination_tree / "Physics" / "Domains" / "motion.qps"
    )

    require(constants_qps.exists(), "Mirrored constants.qps missing")
    require(motion_qps.exists(), "Mirrored motion.qps missing")
    require_valid(constants_qps)
    require_valid(motion_qps)

    # 4. Existing output must not be overwritten.
    before = constants_qps.read_text(encoding="utf-8")

    result = run(
        "cipher",
        source_tree,
        destination_tree,
    )

    require(
        result.returncode != 0,
        "Collision run unexpectedly succeeded",
    )
    require(
        constants_qps.read_text(encoding="utf-8") == before,
        "Existing QPS output was overwritten",
    )

    # 5. Recursive run publishes nothing when any source is bad.
    mixed_source = root / "mixed"
    mixed_output = root / "mixed_qps"
    mixed_source.mkdir()

    (mixed_source / "good.py").write_text(
        "value = 42\n",
        encoding="utf-8",
    )

    (mixed_source / "bad.py").write_text(
        "def broken(:\n",
        encoding="utf-8",
    )

    result = run(
        "cipher",
        mixed_source,
        mixed_output,
    )

    require(
        result.returncode != 0,
        "Mixed recursive run should report failure",
    )

    require(
        not (mixed_output / "good.qps").exists(),
        "Atomic run published good sibling despite bad source",
    )

    require(
        not mixed_output.exists()
        or not any(mixed_output.rglob("*.qps")),
        "Atomic run left published QPS output after failure",
    )

# 6. Real source dependency closure.
repo_root = Path(__file__).resolve().parents[4]

motion_source = (
    repo_root
    / "Engineering/py/Physics/Domains/motion.py"
)

result = run(
    "cipher",
    motion_source,
    "--closure",
)

require(
    result.returncode == 0,
    result.stderr,
)

require(
    "Engineering/py/Physics/Domains/motion.py"
    in result.stdout,
    result.stdout,
)

require(
    "Engineering/py/Physics/constants.py"
    in result.stdout,
    result.stdout,
)

require(
    "Engineering/py/Physics/equations.py"
    in result.stdout,
    result.stdout,
)

require(
    "CIPHER_FOREIGN dataclasses.dataclass"
    in result.stdout,
    result.stdout,
)

require(
    "CIPHER_FOREIGN dataclasses.field"
    in result.stdout,
    result.stdout,
)

require(
    "CIPHER_FOREIGN typing.Any"
    in result.stdout,
    result.stdout,
)

print("qps cipher recursive CLI: PASS")

# Preflight must write nothing and report semantic blockers.
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)

    source = root / "partial.py"
    destination = root / "partial.qps"

    source.write_text(
        "from dataclasses import dataclass\n"
        "\n"
        "@dataclass\n"
        "class Result:\n"
        "    value: float\n"
        "\n"
        "def build(x):\n"
        "    return Result(value=x)\n",
        encoding="utf-8",
    )

    before = sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
    )

    result = run(
        "cipher",
        "test",
        source,
        destination,
    )

    require(
        result.returncode != 0,
        "partial preflight unexpectedly succeeded",
    )

    require(
        "CIPHER_PARTIAL"
        in result.stdout,
        result.stdout,
    )

    require(
        "CIPHER_BLOCKER"
        in result.stdout,
        result.stdout,
    )

    require(
        "ready=false"
        in result.stdout,
        result.stdout,
    )

    require(
        not destination.exists(),
        "cipher test wrote destination",
    )

    after = sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
    )

    require(
        before == after,
        "cipher test mutated source tree",
    )
