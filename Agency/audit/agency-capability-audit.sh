#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-$HOME/Core/Dashboard}"
PYTHON_RUNNER=("/home/spaztic/miniconda3/envs/weebo_env/bin/python")
AUDIT_ROOT="$REPO_ROOT/Agency/audit"
OUTPUT_ROOT="$AUDIT_ROOT/output"
HISTORY_ROOT="$OUTPUT_ROOT/history"
EVIDENCE_ROOT="$AUDIT_ROOT/evidence"
REGISTRY_PATH="$REPO_ROOT/Agency/Core/cli/registry/commands.yaml"
OBSERVATIONS_PATH="$AUDIT_ROOT/observations.json"

STAMP="$(date +%Y-%m-%d_%H-%M-%S)"
RUN_ROOT="$EVIDENCE_ROOT/$STAMP"
LATEST_LINK="$EVIDENCE_ROOT/latest"

mkdir -p \
  "$OUTPUT_ROOT" \
  "$HISTORY_ROOT" \
  "$RUN_ROOT"

if [[ ! -f "$REPO_ROOT/run.py" ]]; then
  echo "Missing run.py at $REPO_ROOT" >&2
  exit 1
fi

if [[ ! -f "$REGISTRY_PATH" ]]; then
  echo "Missing command registry: $REGISTRY_PATH" >&2
  exit 1
fi

MANIFEST="$RUN_ROOT/manifest.tsv"

printf \
  "id\tcommand\texpected\tactual\tduration_ms\tresult\tevidence\n" \
  > "$MANIFEST"

run_check() {
  local id="$1"
  local expected="$2"
  shift 2

  local evidence="$RUN_ROOT/$id.txt"
  local started
  local finished
  local duration
  local actual
  local result

  started="$("${PYTHON_RUNNER[@]}" -c 'import time; print(time.monotonic_ns())')"

  {
    echo "id: $id"
    echo "command: $*"
    echo "expected: $expected"
  } > "$evidence"

  set +e
  timeout 20s "$@" >> "$evidence" 2>&1
  actual=$?
  set -e

  finished="$("${PYTHON_RUNNER[@]}" -c 'import time; print(time.monotonic_ns())')"
  duration=$(( (finished - started) / 1000000 ))

  if [[ "$actual" -eq 124 ]]; then
    result="BLOCKED_TIMEOUT"
  elif [[ "$expected" == "zero" && "$actual" -eq 0 ]]; then
    result="PASS"
  elif [[ "$expected" == "nonzero" && "$actual" -ne 0 ]]; then
    result="PASS"
  else
    result="FAIL"
  fi

  {
    echo "actual_exit_code: $actual"
    echo "duration_ms: $duration"
    echo "result: $result"
  } >> "$evidence"

  printf \
    "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$id" \
    "$*" \
    "$expected" \
    "$actual" \
    "$duration" \
    "$result" \
    "$evidence" \
    >> "$MANIFEST"
}

cd "$REPO_ROOT"

run_check \
  "agency.status" \
  "zero" \
  "${PYTHON_RUNNER[@]}" run.py status

run_check \
  "agency.scope" \
  "zero" \
  "${PYTHON_RUNNER[@]}" run.py scope

run_check \
  "agency.runtime_state" \
  "zero" \
  "${PYTHON_RUNNER[@]}" run.py cmd runtime-state \
    --root "$REPO_ROOT"

run_check \
  "agency.git_status" \
  "zero" \
  "${PYTHON_RUNNER[@]}" run.py cmd git-status \
    --root "$REPO_ROOT"

run_check \
  "agency.list_agents" \
  "zero" \
  "${PYTHON_RUNNER[@]}" run.py cmd list-agents

run_check \
  "agency.list_packets" \
  "zero" \
  "${PYTHON_RUNNER[@]}" run.py cmd list-packets

run_check \
  "agency.refs_scoped" \
  "zero" \
  "${PYTHON_RUNNER[@]}" run.py cmd refs OperatorShell \
    --root UI/OperatorShell \
    --max-files 500 \
    --max-matches 80

run_check \
  "agency.tree_scoped" \
  "zero" \
  "${PYTHON_RUNNER[@]}" run.py cmd tree UI/OperatorShell

run_check \
  "agency.apply_code_gate" \
  "nonzero" \
  "${PYTHON_RUNNER[@]}" run.py cmd apply-code \
    --root "$REPO_ROOT" \
    --file "UI/OperatorShell/DO_NOT_CREATE.txt" \
    --code "approval gate test"

run_check \
  "agency.unregistered_gate" \
  "nonzero" \
  "${PYTHON_RUNNER[@]}" run.py cmd definitely-not-a-command

run_check \
  "agency.legacy_dependency_map" \
  "zero" \
  "${PYTHON_RUNNER[@]}" Agency/audit/agent_runtime_checks.py \
    legacy-dependency-map

run_check \
  "agency.archive_manifest" \
  "zero" \
  "${PYTHON_RUNNER[@]}" Agency/audit/agent_runtime_checks.py \
    archive-manifest

run_check \
  "agency.no_broken_legacy_refs" \
  "zero" \
  "${PYTHON_RUNNER[@]}" Agency/audit/agent_runtime_checks.py \
    no-broken-legacy-refs

run_check \
  "agency.operator_shell_status" \
  "zero" \
  "${PYTHON_RUNNER[@]}" run.py shell status

run_check \
  "agency.workbench_route" \
  "zero" \
  "${PYTHON_RUNNER[@]}" Agency/audit/agent_runtime_checks.py \
    workbench-route

run_check \
  "agency.editor_status" \
  "zero" \
  "${PYTHON_RUNNER[@]}" run.py agent local status

run_check \
  "agency.editor_pinboard_refresh" \
  "zero" \
  "${PYTHON_RUNNER[@]}" run.py agent local pinboard-refresh \
    --mission "Agency audit Editor refresh"

run_check \
  "agency.pinboard_current_audit" \
  "zero" \
  "${PYTHON_RUNNER[@]}" Agency/audit/agent_runtime_checks.py \
    pinboard-current-audit

run_check \
  "agency.editor_inspect_read_only" \
  "zero" \
  "${PYTHON_RUNNER[@]}" Agency/audit/agent_runtime_checks.py \
    inspect-read-only

run_check \
  "agency.agent_direct_mutation_blocked" \
  "zero" \
  "${PYTHON_RUNNER[@]}" Agency/audit/agent_runtime_checks.py \
    direct-mutation-blocked

if [[ -e "$REPO_ROOT/UI/OperatorShell/DO_NOT_CREATE.txt" ]]; then
  echo "Unauthorized write test created a file." \
    >> "$RUN_ROOT/agency.apply_code_gate.txt"

  rm -f "$REPO_ROOT/UI/OperatorShell/DO_NOT_CREATE.txt"

  sed -i \
    's/agency.apply_code_gate\t\(.*\)\tPASS\t/agency.apply_code_gate\t\1\tFAIL\t/' \
    "$MANIFEST" || true
fi

ln -sfn "$STAMP" "$LATEST_LINK"

"${PYTHON_RUNNER[@]}" - \
  "$REPO_ROOT" \
  "$REGISTRY_PATH" \
  "$OBSERVATIONS_PATH" \
  "$MANIFEST" \
  "$OUTPUT_ROOT" \
  "$HISTORY_ROOT" \
  "$STAMP" <<'PY'
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:
    raise SystemExit(
        "PyYAML is required for the Agency audit."
    ) from exc


repo_root = Path(sys.argv[1]).resolve()
registry_path = Path(sys.argv[2]).resolve()
observations_path = Path(sys.argv[3]).resolve()
manifest_path = Path(sys.argv[4]).resolve()
output_root = Path(sys.argv[5]).resolve()
history_root = Path(sys.argv[6]).resolve()
stamp = sys.argv[7]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


registry_doc = yaml.safe_load(
    registry_path.read_text(encoding="utf-8")
) or {}

registry_commands = registry_doc.get("commands", {})

with manifest_path.open(
    "r",
    encoding="utf-8",
    newline="",
) as handle:
    execution_rows = list(
        csv.DictReader(handle, delimiter="\t")
    )

execution_by_id = {
    row["id"]: row
    for row in execution_rows
}

manual_definitions = [
    (
        "agency.status",
        "Run Dashboard status",
        "run.py status exits successfully.",
    ),
    (
        "agency.scope",
        "Resolve Dashboard scope",
        "run.py scope exits successfully.",
    ),
    (
        "agency.runtime_state",
        "Read runtime state",
        "runtime-state completes within 20 seconds.",
    ),
    (
        "agency.git_status",
        "Read Git status",
        "git-status completes within 20 seconds.",
    ),
    (
        "agency.list_agents",
        "List registered agents",
        "list-agents completes within 20 seconds.",
    ),
    (
        "agency.list_packets",
        "List packets",
        "list-packets completes within 20 seconds.",
    ),
    (
        "agency.refs_scoped",
        "Run bounded reference search",
        "Scoped refs completes within 20 seconds.",
    ),
    (
        "agency.tree_scoped",
        "Inspect OperatorShell tree",
        "Scoped tree inspection completes successfully.",
    ),
    (
        "agency.apply_code_gate",
        "Block unapproved code mutation",
        "apply-code is rejected without --approved and writes nothing.",
    ),
    (
        "agency.unregistered_gate",
        "Block unregistered command",
        "An unregistered command is rejected.",
    ),
    (
        "agency.propose_task",
        "Generate a task proposal",
        "A non-mutating task proposal is produced.",
    ),
    (
        "agency.propose_diff",
        "Generate a reviewable diff proposal",
        "A diff artifact is produced without applying it.",
    ),
    (
        "agency.review_diff",
        "Review a proposed diff",
        "Review status is recorded without applying changes.",
    ),
    (
        "agency.approved_mutation",
        "Apply an approved disposable mutation",
        "An explicitly approved scoped change is applied and verified.",
    ),
    (
        "agency.verify_reconstruction",
        "Verify and reconstruct the approved change",
        "The change is observable, attributable, and reversible.",
    ),
    (
        "local.model_plan.01",
        "Accept bounded engineering scopes",
        "Valid UI engineering scopes are represented in the latest model-plan proposal.",
    ),
    (
        "local.model_plan.02",
        "Reject invalid model-plan scopes",
        "Invalid, traversal, outside, disallowed, and missing scopes are rejected.",
    ),
    (
        "local.model_plan.03",
        "Fail clearly when model server is stopped",
        "Stopped model server returns nonzero configured_but_server_unavailable.",
    ),
    (
        "local.model_plan.04",
        "Generate nonempty model plan with healthy server",
        "A healthy local model server produced a nonempty model_plan.md artifact.",
    ),
    (
        "local.model_plan.05",
        "Report required plan sections",
        "Required plan sections are present or missing sections are recorded.",
    ),
    (
        "local.model_plan.06",
        "Inspect only declared scopes",
        "Inspected engineering files stay within declared UI scopes.",
    ),
    (
        "local.model_plan.07",
        "Preserve source files",
        "Proposal generation records source_files_modified=false and source status is unchanged outside runtime artifacts.",
    ),
    (
        "local.model_plan.08",
        "Record model invocation evidence",
        "Proposal artifacts contain model server and model response evidence.",
    ),
    (
        "local.model_plan.09",
        "Pinboard points to active model plan",
        "Pinboard active_proposal points to the latest model-generated plan.",
    ),
]

if observations_path.exists():
    observation_doc = json.loads(
        observations_path.read_text(encoding="utf-8")
    )
else:
    observation_doc = {
        "schema_version": 1,
        "observations": {},
    }

manual_observations = observation_doc.get(
    "observations",
    {},
)

manual: list[dict[str, Any]] = []

for test_id, step, pass_condition in manual_definitions:
    execution = execution_by_id.get(test_id)
    observation = manual_observations.get(test_id, {})

    if execution is not None:
        result = execution["result"]

        evidence = (
            f"exit={execution['actual']}; "
            f"duration_ms={execution['duration_ms']}; "
            f"file={execution['evidence']}"
        )
    else:
        result = observation.get(
            "result",
            "UNTESTED",
        )

        evidence_items = observation.get(
            "evidence",
            [],
        )

        evidence = "; ".join(
            str(item.get("observation", item))
            if isinstance(item, dict)
            else str(item)
            for item in evidence_items
        )

    manual.append(
        {
            "id": test_id,
            "step": step,
            "pass_condition": pass_condition,
            "result": result,
            "evidence": evidence,
            "unresolved": observation.get(
                "unresolved",
                [],
            ),
        }
    )

safe_for_ai = {
    "read_only": "YES_BOUNDED",
    "propose_only": "YES_PROPOSAL_ONLY",
    "review_only": "YES_REVIEW_ONLY",
    "requires_approval": "NO_WITHOUT_OPERATOR_APPROVAL",
}

command_inventory: list[dict[str, Any]] = []

for command_id, command_data in registry_commands.items():
    authority = str(
        command_data.get(
            "authority",
            "unknown",
        )
    )

    cli_name = str(
        command_data.get(
            "cli_name",
            command_id,
        )
    )

    command_inventory.append(
        {
            "id": command_id,
            "cli_name": cli_name,
            "authority": authority,
            "default_agent": command_data.get(
                "default_agent",
                "unknown",
            ),
            "safe_for_ai": safe_for_ai.get(
                authority,
                "UNKNOWN",
            ),
            "observed": False,
            "notes": (
                "Declared authority only. "
                "Execution must be demonstrated separately."
            ),
        }
    )

summary = {
    "REGISTERED_COMMANDS": len(command_inventory),
    "PASS": sum(
        item["result"] == "PASS"
        for item in manual
    ),
    "FAIL": sum(
        item["result"] == "FAIL"
        for item in manual
    ),
    "BLOCKED_TIMEOUT": sum(
        item["result"] == "BLOCKED_TIMEOUT"
        for item in manual
    ),
    "UNTESTED": sum(
        item["result"] == "UNTESTED"
        for item in manual
    ),
}

current_test = next(
    (
        item
        for item in manual
        if item["result"] != "PASS"
    ),
    None,
)

report = {
    "schema_version": 1,
    "repository_root": str(repo_root),
    "generated_at": now_iso(),
    "rule": (
        "Declared authority is not demonstrated capability. "
        "Safe AI use requires bounded, observed execution."
    ),
    "summary": summary,
    "current_test": current_test,
    "command_inventory": command_inventory,
    "manual_demonstration": manual,
}

stable_json = output_root / "agency_state.json"
stable_md = output_root / "agency_state.md"

history_json = (
    history_root
    / f"agency_audit_{stamp}.json"
)

history_md = (
    history_root
    / f"agency_audit_{stamp}.md"
)

json_text = json.dumps(
    report,
    indent=2,
)

stable_json.write_text(
    json_text,
    encoding="utf-8",
)

history_json.write_text(
    json_text,
    encoding="utf-8",
)

lines = [
    "# Agency Capability Audit",
    "",
    f"- Repository: `{repo_root}`",
    f"- Generated: {report['generated_at']}",
    f"- Rule: **{report['rule']}**",
    "",
    "## Summary",
    "",
    "| State | Count |",
    "|---|---:|",
]

for key, value in summary.items():
    lines.append(
        f"| {key} | {value} |"
    )

if current_test:
    lines.extend(
        [
            "",
            "## Current capability test",
            "",
            f"- ID: **{current_test['id']}**",
            f"- Step: {current_test['step']}",
            f"- Result: **{current_test['result']}**",
            f"- Pass condition: {current_test['pass_condition']}",
        ]
    )

lines.extend(
    [
        "",
        "## AI command contract",
        "",
        "| Command | Authority | Safe for AI | Default agent |",
        "|---|---|---|---|",
    ]
)

for item in command_inventory:
    lines.append(
        f"| {item['cli_name']} | "
        f"{item['authority']} | "
        f"{item['safe_for_ai']} | "
        f"{item['default_agent']} |"
    )

lines.extend(
    [
        "",
        "## Demonstration checklist",
        "",
        "| ID | Capability | Result | Evidence |",
        "|---|---|---|---|",
    ]
)

for item in manual:
    evidence = str(
        item["evidence"]
    ).replace(
        "|",
        "/",
    ).replace(
        "\n",
        " ",
    )

    lines.append(
        f"| {item['id']} | "
        f"{item['step']} | "
        f"{item['result']} | "
        f"{evidence} |"
    )

lines.extend(
    [
        "",
        "## Operating rule",
        "",
        "> The AI may use bounded read-only commands and proposal-only commands. "
        "Review-only commands may record review state. "
        "Commands requiring approval must never execute without explicit operator approval.",
    ]
)

markdown = "\n".join(lines) + "\n"

stable_md.write_text(
    markdown,
    encoding="utf-8",
)

history_md.write_text(
    markdown,
    encoding="utf-8",
)

print()
print("Agency audit complete.")
print(f"Stable JSON: {stable_json}")
print(f"Stable MD:   {stable_md}")
print(f"History JSON: {history_json}")
print(f"History MD:   {history_md}")
print()

if current_test:
    print("Current capability test:")
    print(f"  {current_test['id']}")
    print(f"  {current_test['step']}")
    print(f"  Result: {current_test['result']}")
    print()

print("Summary:")
for key, value in summary.items():
    print(f"  {key}: {value}")
PY
