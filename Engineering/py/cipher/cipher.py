from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .emit.qps_emitter import emit_qps
from .emit.convergence_qps import emit_convergence_qps
from .reports.report import summarize
from .graph.dependency_closure import build_dependency_closure
from .plan import build_conversion_plan
from .publish import publish_conversion
from .lower.semantic_calls import lower_semantic_calls


SUPPORTED_SUFFIXES = {
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".cpp",
    ".cc",
    ".cxx",
    ".hpp",
    ".h",
}

IGNORED_PARTS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "build",
    "build-pixel",
}


def load_source(path: Path):
    suffix = path.suffix.lower()

    if suffix == ".json":
        from .sources.json_source import load_json
        return load_json(path)

    if suffix in {".yaml", ".yml"}:
        from .sources.yaml_source import load_yaml
        return load_yaml(path)

    if suffix == ".py":
        from .sources.python_source import load_python
        return load_python(path)

    if suffix in {".cpp", ".cc", ".cxx", ".hpp", ".h"}:
        from .sources.cpp_source import load_cpp
        return load_cpp(path)

    raise ValueError(
        f"Cipher source type not yet supported: {suffix}"
    )


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_SUFFIXES


def is_ignored(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        relative = path

    return any(part in IGNORED_PARTS for part in relative.parts)


def prepare_document(
    path: Path,
):
    document = load_source(path)
    return lower_semantic_calls(document)


def emit_prepared_document(
    document,
    converge: bool,
    *,
    workspace_root=None,
) -> str:
    if converge:
        return emit_convergence_qps(
            document,
            workspace_root=workspace_root,
        )

    return emit_qps(
        document,
        workspace_root=workspace_root,
    )


def emit_document(
    path: Path,
    converge: bool,
    *,
    workspace_root=None,
) -> tuple[str, object]:
    document = prepare_document(path)

    output = emit_prepared_document(
        document,
        converge,
        workspace_root=workspace_root,
    )

    return output, document


def write_candidate(
    source: Path,
    destination: Path,
    *,
    converge: bool,
    report: bool,
) -> bool:
    if destination.exists():
        print(
            f"CIPHER_SKIP existing destination: {destination}",
            file=sys.stderr,
        )
        return False

    try:
        output, document = emit_document(source, converge)
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Exclusive creation is intentional. Cipher never silently
        # replaces an authored or previously generated QPS document.
        with destination.open("x", encoding="utf-8") as handle:
            handle.write(output)

        print(f"CIPHER_WRITE {source} -> {destination}")

        if report:
            print(
                f"{source}: {summarize(document)}",
                file=sys.stderr,
            )

        return True

    except Exception as exc:
        print(
            f"CIPHER_FAIL {source}: {exc}",
            file=sys.stderr,
        )
        return False


def directory_sources(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and is_supported(path)
        and not is_ignored(path, root)
    )


def _print_plan_failure(plan) -> None:
    for unit in plan.units:
        if unit.status != "ready":
            print(
                f"CIPHER_{unit.status.upper()} "
                f"{unit.source} -> {unit.destination}",
                file=sys.stderr,
            )

            if unit.detail:
                print(
                    f"  {unit.detail}",
                    file=sys.stderr,
                )

    for blocker in plan.blockers:
        print(
            f"CIPHER_BLOCKER {blocker}",
            file=sys.stderr,
        )


def _run_conversion(
    source: Path,
    destination: Path | None,
    *,
    converge: bool,
    report: bool,
) -> int:
    plan = build_conversion_plan(
        source,
        destination,
        converge=converge,
        workspace_root=Path.cwd(),
    )

    if not plan.ready:
        _print_plan_failure(plan)

        print(
            "CIPHER_SUMMARY "
            f"sources={len(plan.units)} "
            "written=0 "
            f"failed={len(plan.blockers)}"
        )

        return 1

    try:
        published = publish_conversion(
            plan,
            converge=converge,
        )

    except Exception as exc:
        print(
            f"CIPHER_FAIL {exc}",
            file=sys.stderr,
        )

        print(
            "CIPHER_SUMMARY "
            f"sources={len(plan.units)} "
            "written=0 "
            "failed=1"
        )

        return 1

    for unit in plan.units:
        print(
            f"CIPHER_WRITE "
            f"{unit.source} -> {unit.destination}"
        )

        if report:
            try:
                _, document = emit_document(
                    unit.source,
                    converge,
                )

                print(
                    f"{unit.source}: "
                    f"{summarize(document)}",
                    file=sys.stderr,
                )

            except Exception as exc:
                # Reporting occurs only after successful publication
                # and must not invalidate the accepted conversion.
                print(
                    f"CIPHER_REPORT_FAIL "
                    f"{unit.source}: {exc}",
                    file=sys.stderr,
                )

    print(
        "CIPHER_SUMMARY "
        f"sources={len(plan.units)} "
        f"written={len(published)} "
        "failed=0"
    )

    return 0


def run_file(
    source: Path,
    destination: Path | None,
    *,
    converge: bool,
    report: bool,
) -> int:
    return _run_conversion(
        source,
        destination,
        converge=converge,
        report=report,
    )


def run_directory(
    source_root: Path,
    destination_root: Path | None,
    *,
    converge: bool,
    report: bool,
) -> int:
    return _run_conversion(
        source_root,
        destination_root,
        converge=converge,
        report=report,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode_or_source",
        help="source path or the literal 'test'",
    )
    parser.add_argument(
        "source_or_destination",
        nargs="?",
    )
    parser.add_argument(
        "destination",
        nargs="?",
    )
    parser.add_argument("--report", action="store_true")
    parser.add_argument(
        "--closure",
        action="store_true",
        help="report recursive local and foreign dependency closure",
    )
    parser.add_argument(
        "--converge",
        action="store_true",
        help="emit semantic convergence QPS",
    )
    args = parser.parse_args()

    preflight = args.mode_or_source == "test"

    if preflight:
        if args.source_or_destination is None:
            parser.error(
                "cipher test requires a source path"
            )

        source = Path(
            args.source_or_destination
        ).resolve()

        destination = (
            Path(args.destination).resolve()
            if args.destination is not None
            else None
        )
    else:
        source = Path(
            args.mode_or_source
        ).resolve()

        destination = (
            Path(
                args.source_or_destination
            ).resolve()
            if args.source_or_destination is not None
            else None
        )

        if args.destination is not None:
            parser.error(
                "too many positional arguments"
            )

    if preflight:
        plan = build_conversion_plan(
            source,
            destination,
            converge=args.converge,
            workspace_root=Path.cwd(),
        )

        print(
            "CIPHER_TEST "
            f"source={plan.source} "
            f"destination="
            f"{plan.destination if plan.destination else ''}"
        )

        for unit in plan.units:
            print(
                f"CIPHER_{unit.status.upper()} "
                f"{unit.source} -> {unit.destination}"
            )

            if unit.detail:
                print(
                    f"  {unit.detail}"
                )

        for dependency in plan.foreign:
            print(
                f"CIPHER_FOREIGN {dependency}"
            )

        for library in plan.libraries:
            print(
                f"CIPHER_LIBRARY_RESOLVED {library}"
            )

        for blocker in plan.blockers:
            print(
                f"CIPHER_BLOCKER {blocker}"
            )

        print(
            "CIPHER_TEST_SUMMARY "
            f"units={len(plan.units)} "
            f"foreign={len(plan.foreign)} "
            f"blockers={len(plan.blockers)} "
            f"ready={str(plan.ready).lower()}"
        )

        return 0 if plan.ready else 1

    if args.closure:
        workspace_root = Path.cwd().resolve()

        try:
            closure = build_dependency_closure(
                source,
                workspace_root,
            )
        except Exception as exc:
            print(
                f"CIPHER_CLOSURE_FAIL {source}: {exc}",
                file=sys.stderr,
            )
            return 1

        print(f"CIPHER_ENTRY {closure.entry}")

        for path in sorted(closure.units):
            print(f"CIPHER_LOCAL {path}")

        for dependency in sorted(
            closure.external,
            key=lambda item: (
                item.module,
                item.symbol or "",
                item.alias or "",
            ),
        ):
            symbol = dependency.symbol or "*"
            alias = (
                f" as {dependency.alias}"
                if dependency.alias
                else ""
            )

            print(
                "CIPHER_FOREIGN "
                f"{dependency.module}.{symbol}{alias}"
            )

        print(
            "CIPHER_CLOSURE_SUMMARY "
            f"local={len(closure.units)} "
            f"foreign={len(closure.external)}"
        )

        return 0

    if source.is_dir():
        return run_directory(
            source,
            destination,
            converge=args.converge,
            report=args.report,
        )

    return run_file(
        source,
        destination,
        converge=args.converge,
        report=args.report,
    )


if __name__ == "__main__":
    raise SystemExit(main())
