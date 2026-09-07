#!/usr/bin/env python3
import argparse
import json
import os
import platform
import socket
import subprocess
from pathlib import Path

def git(repo, *args):
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()

def main():
    ap = argparse.ArgumentParser(description="CE-OS host enrollment record generator")
    ap.add_argument("--root", required=True)
    ap.add_argument("--machine-profile", default="precision-tower")
    ap.add_argument("--output")
    ap.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args()

    root = Path(ns.root).resolve()
    if not (root / "_index.qps").is_file():
        raise SystemExit("CE-OS root authority missing")
    if not (root / "package" / "_index.qps").is_file():
        raise SystemExit("package authority missing")

    profile = root / "package" / "config" / "machines" / f"{ns.machine_profile}.env"
    legacy = root / "package" / "config" / "hardware.env"
    if not profile.is_file():
        if ns.machine_profile == "precision-tower" and legacy.is_file():
            profile = legacy
        else:
            raise SystemExit(f"machine profile not found: {ns.machine_profile}")

    dirty = bool(git(root, "status", "--porcelain"))
    record = {
        "schema": 1,
        "identity": "package.machine_enrollment",
        "ce_os_root": str(root),
        "git": {
            "commit": git(root, "rev-parse", "HEAD"),
            "branch": git(root, "branch", "--show-current"),
            "dirty": dirty,
        },
        "host": {
            "hostname": socket.gethostname(),
            "architecture": platform.machine(),
            "system": platform.system(),
            "release": platform.release(),
        },
        "machine_profile": ns.machine_profile,
        "machine_profile_authority": str(profile.relative_to(root)),
        "authorities": {
            "root": "_index.qps",
            "package": "package/_index.qps",
            "agency": "Agency/_index.qps",
            "engineering": "Engineering/_index.qps",
            "ui": "UI/_index.qps",
            "operator_shell": "UI/OperatorShell/_index.qps",
            "workbench": "UI/Workbench/_index.qps",
        },
        "launch_surfaces": {
            "operator_shell": "UI/OperatorShell/project.godot",
            "workbench": "UI/Workbench/project.godot",
        },
        "service_policy": {
            "activation": "separate_explicit_host_action",
            "package_install_does_not_enable_services": True,
            "unresolved_agency_service_not_installable": True,
        },
        "status": "candidate" if dirty else "enrolled",
    }

    text = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if ns.dry_run or not ns.output:
        print(text, end="")
        return

    out = Path(ns.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, out)
    print(out)

if __name__ == "__main__":
    main()
