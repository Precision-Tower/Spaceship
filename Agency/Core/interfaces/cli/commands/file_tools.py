# scripts/cli/commands/file_tools.py
from pathlib import Path

from Agency.Core.interfaces.cli.commands.base import Command


def _resolve_inside_root(root: Path, file_text: str) -> Path:
    root = root.resolve()

    candidate = Path(file_text)

    if candidate.is_absolute():
        raise ValueError("absolute target paths are not allowed")

    if ".." in candidate.parts:
        raise ValueError("parent traversal is not allowed")

    target = (root / candidate).resolve()

    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            "target path outside of project root"
        ) from exc

    return target


class ApplyCodeCommand(Command):
    """
    Surgically updates one file after authority validation.

    This command does not own approval authority. The CLI dispatcher must
    reject execution unless --approved is present.
    """

    def run(self, args):
        root = self.resolver.resolve_target_root(
            getattr(args, "root", None)
        )

        try:
            target_path = _resolve_inside_root(
                root,
                args.file,
            )
        except ValueError as exc:
            return self._report(
                "denied",
                f"reason: {exc}",
            )

        code = args.code

        try:
            target_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            target_path.write_text(
                code,
                encoding="utf-8",
            )

            print("status: success")
            print(
                "target: "
                + target_path.relative_to(root.resolve()).as_posix()
            )
            print(f"bytes_written: {len(code)}")
            return 0

        except Exception as exc:
            return self._report(
                "apply_failed",
                str(exc),
            )


class ReadFileCommand(Command):
    """
    Reads one file located inside the declared project root.
    """

    def run(self, args):
        root = self.resolver.resolve_target_root(
            getattr(args, "root", None)
        )

        try:
            target_path = _resolve_inside_root(
                root,
                args.file,
            )
        except ValueError as exc:
            return self._report(
                "denied",
                f"reason: {exc}",
            )

        if not target_path.exists():
            return self._report(
                "missing",
                f"file {args.file} not found",
            )

        if not target_path.is_file():
            return self._report(
                "denied",
                "reason: target is not a file",
            )

        print("status: success")
        print(
            "content:\n"
            + target_path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )
        return 0
