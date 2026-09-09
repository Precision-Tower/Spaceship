from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import subprocess


@dataclass(frozen=True)
class NativeBinaryCapability:
    identity: str
    state: str
    binary: Path | None
    architecture: str | None
    symbols: tuple[str, ...]
    detail: str = ""


def _llvm_readelf() -> Path:
    prefix = os.environ.get("PREFIX")

    candidates = []

    if prefix:
        candidates.append(
            Path(prefix) / "bin/llvm-readelf"
        )

    candidates.append(
        Path("/usr/bin/llvm-readelf")
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise RuntimeError(
        "llvm-readelf is required for native "
        "binary capability inspection"
    )


def _architecture(
    readelf: Path,
    binary: Path,
) -> str | None:
    result = subprocess.run(
        [
            str(readelf),
            "-h",
            str(binary),
        ],
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        return None

    for line in result.stdout.splitlines():
        line = line.strip()

        if line.startswith("Machine:"):
            return line.split(":", 1)[1].strip()

    return None


def _symbols(
    readelf: Path,
    binary: Path,
    needle: str,
) -> tuple[str, ...]:
    result = subprocess.run(
        [
            str(readelf),
            "--dyn-syms",
            "--demangle",
            str(binary),
        ],
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        return ()

    matches = []

    for line in result.stdout.splitlines():
        if needle in line:
            matches.append(
                line.split(None, 7)[-1]
                if len(line.split(None, 7)) >= 8
                else line.strip()
            )

    return tuple(matches)


def resolve_native_binary_capability(
    identity: str,
    symbol_name: str,
    search_roots: list[str | Path],
) -> NativeBinaryCapability:
    readelf = _llvm_readelf()

    candidates: list[Path] = []

    for root in search_roots:
        root = Path(root).resolve()

        if not root.exists():
            continue

        for path in root.rglob("*.so"):
            if path.is_file():
                candidates.append(path)

    for binary in sorted(set(candidates)):
        symbols = _symbols(
            readelf,
            binary,
            symbol_name,
        )

        if not symbols:
            continue

        return NativeBinaryCapability(
            identity=identity,
            state="resolved",
            binary=binary,
            architecture=_architecture(
                readelf,
                binary,
            ),
            symbols=symbols,
        )

    return NativeBinaryCapability(
        identity=identity,
        state="missing",
        binary=None,
        architecture=None,
        symbols=(),
        detail=(
            "No native binary in configured search roots "
            f"exports {symbol_name}"
        ),
    )
