#!/usr/bin/env python3

from pathlib import Path
import re
import sys

ROOT = Path.home() / "ce-os"
OPS = ROOT / "UI" / "OperatorShell"
WORKBENCH = ROOT / "UI" / "Workbench"

failures: list[str] = []


def fail(message: str) -> None:
    failures.append(message)


def read(path: Path) -> str:
    if not path.is_file():
        fail(f"missing required file: {path.relative_to(ROOT)}")
        return ""
    return path.read_text()


# ---------------------------------------------------------------------
# Required project/runtime files
# ---------------------------------------------------------------------

required = [
    OPS / "project.godot",
    OPS / "scenes" / "Main.tscn",
    OPS / "_index.qps",
    OPS / "Main.gd",
    OPS / "runtime" / "OperatorControlServer.gd",
    ROOT / "bin" / "ops",
]

for path in required:
    if not path.exists():
        fail(f"missing required file: {path.relative_to(ROOT)}")


# ---------------------------------------------------------------------
# GDScript indentation invariant
# ---------------------------------------------------------------------

for source_root in [OPS, WORKBENCH]:
    for path in sorted(source_root.rglob("*.gd")):
        if any(part in {".godot", "build", ".git"} for part in path.parts):
            continue

        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            if not line.strip():
                continue

            prefix = line[: len(line) - len(line.lstrip(" \t"))]

            if prefix.startswith(" "):
                fail(
                    f"{path.relative_to(ROOT)}:{lineno}: "
                    "leading structural indentation begins with spaces"
                )

            if " " in prefix and "\t" in prefix:
                fail(
                    f"{path.relative_to(ROOT)}:{lineno}: "
                    "mixed tabs/spaces in leading indentation"
                )


# ---------------------------------------------------------------------
# No accidental editor/patch backup files
# ---------------------------------------------------------------------

for pattern in ("*.orig", "*.rej"):
    for path in OPS.rglob(pattern):
        if "build" not in path.parts:
            fail(f"backup artifact present: {path.relative_to(ROOT)}")


# ---------------------------------------------------------------------
# Main.gd Android mobile-shell contract
# ---------------------------------------------------------------------

main = read(OPS / "Main.gd")

required_main_fragments = [
    "enum MobileSurface",
    "FILES",
    "EDITOR",
    "TERMINAL",
    "CONTROLS",
    "func _configure_mobile_composition()",
    "func operator_control_surface(",
    "func operator_control_editor_focus(",
    "func operator_control_keyboard_show(",
    "func operator_control_files_refresh(",
    "func operator_control_status(",
    'res://runtime/OperatorControlServer.gd',
]

for fragment in required_main_fragments:
    if fragment not in main:
        fail(f"Main.gd missing mobile/control contract: {fragment}")


# ---------------------------------------------------------------------
# virtual_keyboard_show regression test
#
# We previously shipped:
#
# virtual_keyboard_show(text, caret_line, caret_column)
#
# which Godot rejects because argument 2 must be Rect2.
# ---------------------------------------------------------------------

keyboard_calls = list(
    re.finditer(r"DisplayServer\.virtual_keyboard_show\s*\(", main)
)

if len(keyboard_calls) != 1:
    fail(
        "Main.gd must contain exactly one canonical "
        f"virtual_keyboard_show() call; found {len(keyboard_calls)}"
    )

if "var editor_rect := mobile_editor.get_global_rect()" not in main:
    fail("keyboard control must derive editor_rect from mobile_editor.get_global_rect()")

canonical_keyboard = """DisplayServer.virtual_keyboard_show(
\t\tmobile_editor.text,
\t\teditor_rect,
\t\tDisplayServer.KEYBOARD_TYPE_DEFAULT,"""

if canonical_keyboard not in main:
    fail(
        "canonical virtual_keyboard_show() signature not found "
        "(argument 2 must be editor_rect / Rect2)"
    )

for forbidden in [
    """DisplayServer.virtual_keyboard_show(
\t\t\tmobile_editor.text,
\t\t\tmobile_editor.get_caret_line()""",
    """DisplayServer.virtual_keyboard_show(
\t\tmobile_editor.text,
\t\tmobile_editor.get_caret_line()""",
]:
    if forbidden in main:
        fail("stale invalid virtual_keyboard_show(text, caret_line, ...) call remains")


# ---------------------------------------------------------------------
# Focus callback must use the canonical keyboard path.
# ---------------------------------------------------------------------

focus_match = re.search(
    r"func _on_mobile_editor_focus_entered\(\) -> void:(.*?)(?=\nfunc |\Z)",
    main,
    re.S,
)

if not focus_match:
    fail("_on_mobile_editor_focus_entered() not found")
else:
    body = focus_match.group(1)

    if "operator_control_keyboard_show()" not in body:
        fail(
            "_on_mobile_editor_focus_entered() must delegate to "
            "operator_control_keyboard_show()"
        )

    if "DisplayServer.virtual_keyboard_show" in body:
        fail(
            "_on_mobile_editor_focus_entered() must not implement "
            "a second virtual_keyboard_show() call"
        )


# ---------------------------------------------------------------------
# Control-server contract
# ---------------------------------------------------------------------

server = read(OPS / "runtime" / "OperatorControlServer.gd")

required_server_fragments = [
    'const HOST := "127.0.0.1"',
    "const PORT := 8767",
    '"surface.files"',
    '"surface.editor"',
    '"surface.terminal"',
    '"surface.controls"',
    '"editor.focus"',
    '"keyboard.show"',
    '"keyboard.hide"',
    '"files.refresh"',
    '"status"',
]

for fragment in required_server_fragments:
    if fragment not in server:
        fail(f"OperatorControlServer missing contract: {fragment}")

required_server_types = [
    "var available: int = peer.get_available_bytes()",
    "var chunk: String = peer.get_utf8_string(available)",
    "var command: String = str(buffers[peer]).get_slice",
    "var response: String = _dispatch(command)",
]

for fragment in required_server_types:
    if fragment not in server:
        fail(
            "OperatorControlServer must use explicit types for Android/Godot "
            f"parser stability: {fragment}"
        )


# ---------------------------------------------------------------------
# ops CLI contract
# ---------------------------------------------------------------------

ops_cli = read(ROOT / "bin" / "ops")

required_ops_fragments = [
    'HOST="127.0.0.1"',
    'PORT="8767"',
    'send_ops "surface.files"',
    'send_ops "surface.editor"',
    'send_ops "surface.terminal"',
    'send_ops "surface.controls"',
    'send_ops "editor.focus"',
    'send_ops "keyboard.show"',
]

for fragment in required_ops_fragments:
    if fragment not in ops_cli:
        fail(f"bin/ops missing contract: {fragment}")



# ---------------------------------------------------------------------
# Android control-plane permission contract
# ---------------------------------------------------------------------

android_manifests = list(
    (OPS / "android" / "template").rglob("AndroidManifest.xml")
)

internet_manifests = [
    path for path in android_manifests
    if 'android.permission.INTERNET' in path.read_text()
]

if not internet_manifests:
    fail(
        "OperatorShell Android template must declare "
        "android.permission.INTERNET for the localhost ops control plane"
    )

# ---------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------

if failures:
    print("OPERATORSHELL SOURCE TESTS FAILED")
    print()

    for failure in failures:
        print("FAIL:", failure)

    print()
    print(f"{len(failures)} failure(s)")
    sys.exit(1)

print("OPERATORSHELL SOURCE TESTS OK")
