#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/spaztic/Core/Dashboard").resolve()
PYTHON = Path("/home/spaztic/miniconda3/envs/weebo_env/bin/python")
LEGACY = [
    "Cali",
    "Grant",
    "Jarvis",
    "NewNew",
    "Online",
    "Probe",
    "Scout",
    "Weebo",
    "Weebo2_legacy_shell",
    "Weebo_legacy_pre_agency",
]
LEGACY_RE = re.compile(
    r"Agency\.Agents\.(Cali|Grant|Jarvis|NewNew|Online|Probe|Scout|Weebo|Weebo2_legacy_shell|Weebo_legacy_pre_agency)"
    r"|Agency/Agents/(Cali|Grant|Jarvis|NewNew|Online|Probe|Scout|Weebo|Weebo2_legacy_shell|Weebo_legacy_pre_agency)"
)
EXCLUDED_DIRS = {".git", "local", "datasets", "backup", "__pycache__"}

EXCLUDED_PREFIXES = (
    "Agency/Archive/",
    "Agency/audit/evidence/",
    "Agency/audit/output/history/",
    "Agency/audit/sandbox/",
    "Agency/runtime/proposals/",
    "CE-OS/Gear/archive/",
    "backup/",
    "datasets/",
    "local/",
)


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def ok(message: str) -> int:
    print(f"PASS: {message}")
    return 0


def run(argv: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        env={"PYTHONDONTWRITEBYTECODE": "1", **dict(os.environ)},
    )


def filtered_status() -> list[str]:
    proc = run(["git", "status", "--porcelain"])
    lines = []
    for line in proc.stdout.splitlines():
        path = line[3:] if len(line) > 3 else line
        if path.startswith("Agency/runtime/"):
            continue
        if path == "dashboard.log" or "__pycache__/" in path or path.endswith(".pyc"):
            continue
        lines.append(line)
    return lines


def newest_proposal() -> Path | None:
    root = ROOT / "Agency" / "runtime" / "proposals"
    if not root.exists():
        return None
    dirs = [p for p in root.iterdir() if p.is_dir()]
    if not dirs:
        return None
    return max(dirs, key=lambda p: p.stat().st_mtime)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def manager_status() -> dict:
    proc = run([str(PYTHON), "-m", "Agency.Core.runtime.model_server_manager", "status"], timeout=20)
    try:
        data = json.loads(proc.stdout or "{}")
    except Exception:
        data = {"status": "invalid_json", "stdout": proc.stdout, "stderr": proc.stderr}
    data["returncode"] = proc.returncode
    return data


def validate_latest_model_plan_artifact() -> tuple[bool, str]:
    proposal = newest_proposal()
    if proposal is None:
        return False, "no proposal directory exists"
    required = {"proposal.json", "evidence.json", "model_plan.md", "model_response.json"}
    existing = {path.name for path in proposal.iterdir() if path.is_file()}
    missing = sorted(required - existing)
    if missing:
        return False, f"latest proposal missing artifacts: {missing}"
    if "proposed.diff" in existing:
        return False, "planning-only proposal unexpectedly contains proposed.diff"
    proposal_json = load_json(proposal / "proposal.json")
    evidence = load_json(proposal / "evidence.json")
    response = load_json(proposal / "model_response.json")
    plan = (proposal / "model_plan.md").read_text(encoding="utf-8", errors="replace")
    if proposal_json.get("status") != "model_plan_generated":
        return False, f"unexpected proposal status: {proposal_json.get('status')}"
    if proposal_json.get("model_invoked") is not True:
        return False, "proposal.json does not record model_invoked=true"
    if proposal_json.get("source_files_modified") is not False or evidence.get("source_files_modified") is not False:
        return False, "proposal evidence does not preserve source_files_modified=false"
    if response.get("status") != "draft_generated" or not str(response.get("draft") or "").strip():
        return False, "model_response.json does not preserve a nonempty draft_generated response"
    if not plan.strip():
        return False, "model_plan.md is empty"
    inspected = [item.get("path", "") for item in evidence.get("inspected_files", [])]
    if not inspected:
        return False, "evidence has no inspected_files"
    if any(path.startswith("Agency/runtime/pinboard/history") for path in inspected):
        return False, "pinboard history was ingested"
    scopes = proposal_json.get("scopes", [])
    if not scopes or any(not str(scope).startswith(("UI/OperatorShell", "UI/Workbench", "UI/Main", "UI/shared")) for scope in scopes):
        return False, f"proposal scopes are outside allowed UI roots: {scopes}"
    pinboard = ROOT / "Agency" / "runtime" / "pinboard" / "current.json"
    if pinboard.exists():
        active = load_json(pinboard).get("active_proposal")
        if active != str(proposal.relative_to(ROOT)):
            return False, f"pinboard active_proposal does not point to latest proposal: {active}"
    return True, f"latest model plan artifact is bounded and reconstructable: {proposal.relative_to(ROOT)}"




def check_no_broken_legacy_refs() -> int:
    proc = run(["git", "ls-files", "-co", "--exclude-standard"], timeout=20)
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
        return fail("git ls-files failed during legacy reference scan")

    hits: list[str] = []
    for rel in proc.stdout.splitlines():
        if rel in {".gitignore", "Agency/audit/agent_runtime_checks.py"}:
            continue
        if rel.endswith(".pyc") or ".bak_" in rel or rel.endswith(".bak"):
            continue
        if any(rel.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
            continue
        if "/Chroma/" in rel or rel.startswith(".git/"):
            continue
        path = ROOT / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            if LEGACY_RE.search(line):
                hits.append(f"{rel}:{line_no}:{line[:200]}")
                break
        if len(hits) >= 20:
            break
    if hits:
        print("\n".join(hits))
        return fail("active legacy references remain outside archive/evidence/runtime exclusions")
    return ok("no active legacy Agent imports or direct paths remain")


def check_workbench_route() -> int:
    proc = run([str(PYTHON), "-B", "-c", "import run; s=run._workbench_status(None); raise SystemExit(0 if s['project_path'].exists() and s['scene_path'].exists() and s['godot_path'].exists() else 1)"])
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
        return fail("Workbench route paths are not intact")
    return ok("Workbench route paths remain intact")


def check_pinboard_reads_audit() -> int:
    pinboard = ROOT / "Agency" / "runtime" / "pinboard" / "current.json"
    audit = ROOT / "Agency" / "audit" / "output" / "agency_state.json"
    if not pinboard.exists() or not audit.exists():
        return fail("pinboard or agency audit state missing")
    pin = json.loads(pinboard.read_text(encoding="utf-8"))
    state = json.loads(audit.read_text(encoding="utf-8"))
    pin_generated = pin.get("current_capability", {}).get("audits", {}).get("agency", {}).get("generated_at")
    if pin_generated != state.get("generated_at"):
        return fail("pinboard agency audit timestamp does not match current agency_state.json")
    return ok("pinboard references current Agency audit state")


def check_inspect_read_only() -> int:
    before = filtered_status()
    proc = run([str(PYTHON), "-B", "run.py", "agent", "local", "inspect"], timeout=40)
    after = filtered_status()
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
        return fail("Editor inspect exited nonzero")
    if before != after:
        print("before:", before)
        print("after:", after)
        return fail("Editor inspect changed source git status")
    return ok("Editor inspect did not modify source status")


def check_proposal_artifacts_only() -> int:
    valid, message = validate_latest_model_plan_artifact()
    if not valid:
        return fail(message)
    return ok(message)


def check_model_plan_invalid_scopes() -> int:
    base = [str(PYTHON), "-B", "run.py", "agent", "local", "propose", "--intent", "scope rejection audit"]
    cases = [
        (base, "missing required --scope"),
        (base + ["--scope", "UI/OperatorShell/../Workbench"], "traversal scope"),
        (base + ["--scope", "/tmp"], "outside absolute scope"),
        (base + ["--scope", "Agency/Agents/Editor"], "disallowed Agency scope"),
        (base + ["--scope", "UI/DoesNotExist"], "missing scope"),
    ]
    failures: list[str] = []
    for argv, label in cases:
        proc = run(argv, timeout=30)
        if proc.returncode == 0:
            failures.append(f"{label} unexpectedly exited 0")
    if failures:
        print("\n".join(failures))
        return fail("one or more invalid model-plan scopes were accepted")
    return ok("invalid, traversal, outside, disallowed, and missing model-plan scopes are rejected")


def check_model_plan_stopped_server() -> int:
    status = manager_status()
    if status.get("status") == "ready":
        return fail("model server is ready; stopped-server behavior requires an already stopped server")
    proc = run([
        str(PYTHON), "-B", "run.py", "agent", "local", "propose",
        "--intent", "stopped model server audit",
        "--scope", "UI/OperatorShell",
    ], timeout=40)
    if proc.returncode == 0:
        print(proc.stdout)
        return fail("Editor propose succeeded while model server was unavailable")
    if "configured_but_server_unavailable" not in proc.stdout:
        print(proc.stdout)
        print(proc.stderr)
        return fail("stopped model server failure did not surface configured_but_server_unavailable")
    return ok("stopped model server returns nonzero with configured_but_server_unavailable")


def check_model_plan_latest_artifact() -> int:
    valid, message = validate_latest_model_plan_artifact()
    if not valid:
        return fail(message)
    return ok(message)


def check_direct_mutation_blocked() -> int:
    before = filtered_status()
    proc = run([str(PYTHON), "-B", "run.py", "agent", "action", "propose", "Editor", "write file run.py containing audit-gate-test"])
    after = filtered_status()
    if proc.returncode == 0:
        print(proc.stdout)
        return fail("direct agent mutation proposal unexpectedly succeeded")
    if before != after:
        print("before:", before)
        print("after:", after)
        return fail("blocked direct mutation changed source status")
    return ok("direct agent source mutation proposal is blocked")


CHECKS = {
    "no-broken-legacy-refs": check_no_broken_legacy_refs,
    "workbench-route": check_workbench_route,
    "pinboard-current-audit": check_pinboard_reads_audit,
    "inspect-read-only": check_inspect_read_only,
    "proposal-artifacts-only": check_proposal_artifacts_only,
    "model-plan-invalid-scopes": check_model_plan_invalid_scopes,
    "model-plan-stopped-server": check_model_plan_stopped_server,
    "model-plan-latest-artifact": check_model_plan_latest_artifact,
    "direct-mutation-blocked": check_direct_mutation_blocked,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("check", choices=sorted(CHECKS))
    args = parser.parse_args(argv)
    return CHECKS[args.check]()


if __name__ == "__main__":
    raise SystemExit(main())
