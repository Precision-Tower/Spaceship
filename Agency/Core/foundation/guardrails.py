from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


EXCLUDED_JSON_PARTS = {".godot", "__pycache__", "local", "backup"}


def relative_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def run_cmd(label: str, cmd: list[str], cwd: Path) -> bool:
    print(f"\n=== {label} ===")
    print("cmd:", " ".join(cmd))
    try:
        result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=120)
    except FileNotFoundError:
        print("status: skipped_missing_command")
        return True
    except subprocess.TimeoutExpired:
        print("status: failed_timeout")
        return False

    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())

    print(f"return_code: {result.returncode}")
    return result.returncode == 0


def json_smoke(root: Path) -> bool:
    print("\n=== json-parse ===")
    ok = True
    for path in root.rglob("*.json"):
        if set(path.parts) & EXCLUDED_JSON_PARTS:
            continue
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            ok = False
            print(f"FAIL {relative_path(root, path)}: {exc}")
    print("status:", "passed" if ok else "failed")
    return ok


def yaml_contract_smoke(root: Path) -> bool:
    print("\n=== yaml-contract-parse ===")

    try:
        import yaml
    except ImportError:
        print("status: skipped_missing_pyyaml")
        return True

    ok = True
    targets = [
        root / "CE-OS/Gear/core",
        root / "UI/Workbench/contracts",
    ]

    for target in targets:
        if not target.exists():
            ok = False
            print(f"FAIL missing_directory: {relative_path(root, target)}")
            continue

        for path in sorted(target.glob("*.yaml")):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
            except Exception as exc:
                ok = False
                print(f"FAIL {relative_path(root, path)}: {exc}")
                continue

            if not isinstance(data, dict):
                ok = False
                print(f"FAIL {relative_path(root, path)}: expected top-level mapping")

    print("status:", "passed" if ok else "failed")
    return ok


def packet_shape_smoke(root: Path) -> bool:
    print("\n=== packet-shape ===")
    ok = True
    ghostlab_root = root / "Engineering/py/Projects/Float/GhostLab"
    boat_root = root / "Engineering/py/Projects/Float/Boat"

    ghostlab_requirements = {
        "project.json": {
            "fields": ["project_id", "project_name", "project_type", "evidence_state", "objects_path", "topology_path", "environment_path", "save_state_path"],
            "types": {},
        },
        "environment.json": {
            "fields": ["environment_id", "environment_type", "units", "floor", "walls"],
            "types": {"floor": dict, "walls": list},
        },
        "objects.json": {
            "fields": ["objects"],
            "types": {"objects": list},
        },
        "topology.json": {
            "fields": ["connections"],
            "types": {"connections": list},
        },
        "working_state.json": {
            "fields": ["objects", "connections"],
            "types": {"objects": list, "connections": list},
        },
    }

    for filename, requirement in ghostlab_requirements.items():
        path = ghostlab_root / filename
        data, path_ok = _load_json_object(root, path)
        ok = ok and path_ok
        if not path_ok:
            continue

        ok = _require_fields(root, path, data, requirement["fields"]) and ok
        ok = _require_types(root, path, data, requirement["types"]) and ok

    packet_paths = sorted(boat_root.glob("**/*_packet.json")) if boat_root.exists() else []
    if not packet_paths:
        ok = False
        print(f"FAIL {relative_path(root, boat_root)}: no *_packet.json files found")

    for path in packet_paths:
        data, path_ok = _load_json_object(root, path)
        ok = ok and path_ok
        if not path_ok:
            continue

        ok = _require_fields(
            root,
            path,
            data,
            ["packet_type", "created_at", "evidence_state", "assembly", "prohibited_interpretations"],
        ) and ok
        ok = _require_types(
            root,
            path,
            data,
            {"assembly": dict, "prohibited_interpretations": list},
        ) and ok

        assembly = data.get("assembly", {})
        if isinstance(assembly, dict):
            ok = _require_fields(
                root,
                path,
                assembly,
                ["assembly_id", "assembly_type", "hierarchy", "objects"],
                context="assembly",
            ) and ok
            ok = _require_types(
                root,
                path,
                assembly,
                {"hierarchy": dict, "objects": list},
                context="assembly",
            ) and ok

    print("status:", "passed" if ok else "failed")
    return ok


def _load_json_object(root: Path, path: Path) -> tuple[dict, bool]:
    if not path.exists():
        print(f"FAIL missing_file: {relative_path(root, path)}")
        return {}, False

    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print(f"FAIL {relative_path(root, path)}: {exc}")
        return {}, False

    if not isinstance(data, dict):
        print(f"FAIL {relative_path(root, path)}: expected top-level object")
        return {}, False

    return data, True


def _require_fields(
    root: Path,
    path: Path,
    data: dict,
    fields: list[str],
    context: str = "top-level",
) -> bool:
    ok = True
    for field in fields:
        if field not in data:
            ok = False
            print(f"FAIL {relative_path(root, path)}: missing {context} field '{field}'")
    return ok


def _require_types(
    root: Path,
    path: Path,
    data: dict,
    types: dict[str, type],
    context: str = "top-level",
) -> bool:
    ok = True
    for field, expected_type in types.items():
        if field in data and not isinstance(data[field], expected_type):
            ok = False
            print(
                f"FAIL {relative_path(root, path)}: {context} field '{field}' expected {expected_type.__name__}"
            )
    return ok


def godot_smoke(root: Path, skip: bool) -> bool:
    if skip:
        print("\n=== godot-smoke ===")
        print("status: skipped")
        return True

    godot = root / "local/godot/Godot_Linux/Godot_v4.2.2-stable_linux.x86_64"
    if not godot.exists():
        print("\n=== godot-smoke ===")
        print("status: skipped_missing_godot_binary")
        return True

    return run_cmd(
        "godot-smoke",
        [str(godot), "--headless", "--path", str(root / "UI"), "--quit"],
        root,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--skip-godot", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    checks = [
        json_smoke(root),
        yaml_contract_smoke(root),
        packet_shape_smoke(root),
        run_cmd("python-compile-agency", [sys.executable, "-m", "compileall", "-q", "Agency/Core"], root),
        run_cmd("python-compile-engineering", [sys.executable, "-m", "compileall", "-q", "Engineering"], root),
        godot_smoke(root, args.skip_godot),
    ]

    print("\nTEST_ALL")
    print("status:", "passed" if all(checks) else "failed")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
