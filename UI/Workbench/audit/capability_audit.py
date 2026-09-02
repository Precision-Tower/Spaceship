#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MANUAL_DEFINITIONS = [
    {"id": "demo.01", "step": "Launch the current Godot project", "pass_condition": "Workbench opens and remains usable; fatal parser or runtime errors are not present."},
    {"id": "demo.02", "step": "Create or load an empty room", "pass_condition": "Room is visibly present and has a traceable source."},
    {"id": "demo.03", "step": "Create one ghost primitive", "pass_condition": "Primitive appears in the viewport from an operator action."},
    {"id": "demo.04", "step": "Move, rotate, and scale the primitive", "pass_condition": "Transforms visibly change and persist in candidate state."},
    {"id": "demo.05", "step": "Export the ghost candidate to JSON", "pass_condition": "A new JSON file is written with identity and transforms."},
    {"id": "demo.06", "step": "Validate and inspect the JSON", "pass_condition": "JSON parses and fields match the viewport candidate."},
    {"id": "demo.07", "step": "Edit one JSON field outside Godot", "pass_condition": "The edit is deliberate, parseable, and recorded."},
    {"id": "demo.08", "step": "Reload the edited JSON", "pass_condition": "Workbench reflects the edited field."},
    {"id": "demo.09", "step": "Assign additional object detail", "pass_condition": "Material, type, or metadata can be added without losing base geometry."},
    {"id": "demo.10", "step": "Save and reopen the project state", "pass_condition": "The room and object reconstruct from files, not memory."},
    {"id": "demo.11", "step": "Trace provenance", "pass_condition": "The producing command, file, and code path can be identified."},
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def new_check(check_id: str, category: str, capability: str, level: str, status: str, evidence: str, next_proof: str) -> dict[str, Any]:
    return {
        "id": check_id,
        "category": category,
        "capability": capability,
        "evidence_level": level,
        "status": status,
        "evidence": evidence,
        "next_proof": next_proof,
    }


def path_check(root: Path, check_id: str, category: str, capability: str, paths: list[str], next_proof: str) -> dict[str, Any]:
    hits = [path for path in paths if (root / path).exists()]
    if hits:
        return new_check(check_id, category, capability, "PRESENT", "FOUND", ", ".join(hits), next_proof)
    return new_check(check_id, category, capability, "NONE", "NOT FOUND", "Checked: " + ", ".join(paths), next_proof)


def text_hit(root: Path, check_id: str, category: str, capability: str, path: str, pattern: str, next_proof: str) -> dict[str, Any]:
    full = root / path
    if full.exists() and pattern in read_text(full):
        return new_check(check_id, category, capability, "WIRED", "FOUND", f"{path}: {pattern}", next_proof)
    return new_check(check_id, category, capability, "NONE", "NOT FOUND", f"Checked {path} for {pattern}", next_proof)


def load_observations(path: Path) -> dict[str, Any]:
    if not path.exists():
        path.write_text(json.dumps({"observations": {}}, indent=2) + "\n", encoding="utf-8")
    return json.loads(read_text(path) or "{}")


def observation_record(document: dict[str, Any], definition: dict[str, str]) -> dict[str, Any]:
    record = document.get("observations", {}).get(definition["id"], {})
    evidence_items = record.get("evidence", [])
    if isinstance(evidence_items, str):
        evidence_items = [evidence_items]
    evidence_text: list[str] = []
    for item in evidence_items:
        if isinstance(item, dict) and item.get("observation"):
            evidence_text.append(str(item["observation"]))
        elif isinstance(item, str):
            evidence_text.append(item)
    unresolved = record.get("unresolved", [])
    if isinstance(unresolved, str):
        unresolved = [unresolved]
    return {
        "id": definition["id"],
        "step": definition["step"],
        "pass_condition": definition["pass_condition"],
        "result": str(record.get("result", "UNTESTED")),
        "evidence": "; ".join(evidence_text),
        "unresolved": unresolved if isinstance(unresolved, list) else [],
    }


def find_text_hits(root: Path, search_root: Path, patterns: list[str], limit: int = 30) -> list[str]:
    hits: list[str] = []
    if not search_root.exists():
        return hits
    for path in sorted(search_root.rglob("*.gd")):
        if ".godot" in path.parts or "__pycache__" in path.parts:
            continue
        text = read_text(path)
        for pattern in patterns:
            if pattern in text:
                hits.append(f"{path.resolve().relative_to(root.resolve()).as_posix()}: {pattern}")
                break
        if len(hits) >= limit:
            break
    return hits


def route_checks(root: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    project_file = root / "UI/project.godot"
    project_text = read_text(project_file) if project_file.exists() else ""
    main_scene_line = next((line.strip() for line in project_text.splitlines() if line.strip().startswith("run/main_scene")), "")
    if main_scene_line == 'run/main_scene="res://Main/Main.tscn"':
        checks.append(new_check("ui.main_scene", "UI", "Godot project boots through cockpit router", "WIRED", "FOUND", main_scene_line, "Launch the project and record the active route."))
    else:
        checks.append(new_check("ui.main_scene", "UI", "Godot project boots through cockpit router", "NONE", "STALE", main_scene_line or "run/main_scene missing", "Confirm the intended project entrypoint."))
    checks.append(text_hit(root, "workbench.route_constant", "UI", "Workbench route is declared in cockpit router", "UI/Main/Main.gd", 'ROUTE_WORKBENCH := "res://Workbench/Main/Main.tscn"', "Launch the Workbench route."))
    checks.append(text_hit(root, "workbench.default_route", "UI", "Cockpit default remains OperatorShell", "UI/Main/Main.gd", "DEFAULT_ROUTE := ROUTE_OPERATOR_SHELL", "Do not embed Workbench into OperatorShell yet."))
    return checks


def duplicate_checks(root: Path) -> list[dict[str, Any]]:
    present = [path for path in ["UI/Workbench/Workbench.gd", "UI/Workbench/WorkbenchShellBuilder.gd"] if (root / path).exists()]
    if present:
        return [new_check("workbench.root_duplicates", "Repository Hygiene", "Root-level duplicate Workbench scripts are absent", "PRESENT", "STALE", ", ".join(present), "Remove or justify each duplicate.")]
    return [new_check("workbench.root_duplicates", "Repository Hygiene", "Root-level duplicate Workbench scripts are absent", "NONE", "ABSENT", "No root-level duplicate scripts found.", "Keep canonical scripts under Main/scenes/layout.")]


def build_report(root: Path) -> dict[str, Any]:
    script_root = root / "UI/Workbench/audit"
    observations = load_observations(script_root / "observations.json")
    checks: list[dict[str, Any]] = [
        path_check(root, "repo.run_py", "Runtime", "Root runtime entrypoint exists", ["run.py"], "Run the entrypoint and capture actual output."),
        path_check(root, "agency.cli", "Runtime", "Agency CLI entrypoint exists", ["Agency/Core/cli/dashboard_cli.py"], "Run a read-only command and capture output."),
        path_check(root, "ui.project", "UI", "Godot project exists", ["UI/project.godot"], "Launch the project and record the actual scene."),
        path_check(root, "workbench.main", "UI", "Workbench boot scene exists", ["UI/Workbench/Main/Main.tscn"], "Launch the scene and verify it remains usable."),
        path_check(root, "workbench.main_script", "UI", "Workbench boot script exists", ["UI/Workbench/Main/Main.gd"], "Parse and launch the boot scene."),
        path_check(root, "workbench.shell_scene", "UI", "Workbench shell scene exists", ["UI/Workbench/scenes/Workbench.tscn"], "Instantiate it through the boot scene."),
        path_check(root, "workbench.shell_script", "UI", "Workbench shell script is canonical", ["UI/Workbench/scenes/Workbench.gd"], "Verify it owns shell layout creation."),
        path_check(root, "workbench.shell_builder", "UI", "Workbench shell builder is canonical", ["UI/Workbench/layout/WorkbenchShellBuilder.gd"], "Verify only this builder path is loaded."),
        path_check(root, "workbench.left_panel", "UI", "Workbench left audit panel exists", ["UI/Workbench/inspectors/LeftPanel.gd"], "Run audit and verify the panel reloads current state."),
        path_check(root, "shared.screenshot_controller", "Shared UI", "Shared screenshot controller exists", ["UI/shared/ScreenshotController.gd"], "Press Alt+S and verify output."),
        path_check(root, "audit.posix_runner", "Audit", "Linux audit runner exists", ["UI/Workbench/audit/capability-audit.sh", "UI/Workbench/audit/capability_audit.py"], "Run it on the black laptop."),
    ]
    checks.extend(route_checks(root))
    checks.extend(duplicate_checks(root))
    checks.extend([
        text_hit(root, "workbench.shell_scene_script", "UI", "Workbench shell scene uses canonical script", "UI/Workbench/scenes/Workbench.tscn", 'path="res://Workbench/scenes/Workbench.gd"', "Load the scene."),
        text_hit(root, "workbench.builder_reference", "UI", "Workbench shell uses canonical builder", "UI/Workbench/scenes/Workbench.gd", 'preload("res://Workbench/layout/WorkbenchShellBuilder.gd")', "Load the shell scene."),
        text_hit(root, "left_panel.audit_state", "Audit", "Left panel reads stable audit state", "UI/Workbench/inspectors/LeftPanel.gd", 'res://Workbench/audit/output/capability_state.json', "Run Ctrl+Shift+A and observe reload."),
        text_hit(root, "audit.hotkey", "Audit", "Ctrl+Shift+A audit hotkey remains wired", "UI/Workbench/audit/AuditController.gd", "event.ctrl_pressed", "Press Ctrl+Shift+A in Workbench."),
        text_hit(root, "audit.controller_posix", "Audit", "Audit controller can call Linux runner", "UI/Workbench/audit/AuditController.gd", "capability-audit.sh", "Press Ctrl+Shift+A on Linux."),
        text_hit(root, "shared.screenshot_main", "Shared UI", "Cockpit uses shared screenshot controller", "UI/Main/Main.gd", "res://shared/ScreenshotController.gd", "Press Alt+S in cockpit."),
        text_hit(root, "shared.screenshot_workbench", "Shared UI", "Workbench uses shared screenshot controller", "UI/Workbench/Main/Main.gd", "res://shared/ScreenshotController.gd", "Press Alt+S in Workbench."),
        path_check(root, "ghost.controller", "Ghost Workflow", "Ghost command controller exists", ["UI/Workbench/interaction/GhostCommandController.gd"], "Create one primitive from an operator action."),
        path_check(root, "ghost.dialogs", "Ghost Workflow", "Ghost authoring dialogs exist", ["UI/Workbench/interaction/GhostCommandDialogs.gd"], "Open the authoring UI and submit one command."),
        path_check(root, "ghost.renderer", "Ghost Workflow", "Ghost primitive renderer exists", ["UI/Workbench/rendering/GhostPrimitiveRenderer.gd"], "Observe a primitive rendered in the viewport."),
        path_check(root, "ghost.exporter", "Ghost Workflow", "Ghost JSON exporter exists", ["UI/Workbench/packet/GhostCommandExporter.gd"], "Export one primitive and validate the JSON."),
        path_check(root, "packet.loader", "Workbench", "Packet loader exists", ["UI/Workbench/packet/PacketLoader.gd"], "Load a known JSON packet in the running Workbench."),
        path_check(root, "packet.display", "Workbench", "Packet display resolver exists", ["UI/Workbench/packet/PacketDisplayResolver.gd"], "Select an object and verify packet details are shown."),
        path_check(root, "render.packet_geometry", "Workbench", "Packet geometry renderer exists", ["UI/Workbench/rendering/PacketGeometryRenderer.gd"], "Render geometry from a packet."),
        path_check(root, "selection.raycaster", "Workbench", "Viewport selection code exists", ["UI/Workbench/selection/SelectionRaycaster.gd"], "Click a rendered object and observe selection state."),
        path_check(root, "session", "Workbench", "Workbench session state exists", ["UI/Workbench/core/WorkbenchSession.gd"], "Load, modify, and reload without losing traceable state."),
        path_check(root, "engineering.boat_assembly", "Engineering", "Active boat assembly generator exists", ["Engineering/py/Projects/Float/Boat/boat_assembly.py"], "Run it successfully and verify generated packet fields."),
        path_check(root, "engineering.hull", "Engineering", "Active hull generation scripts exist", ["Engineering/py/Projects/Float/Boat/Hull/hull_inventory.py", "Engineering/py/Projects/Float/Boat/Hull/hull_frame.py"], "Run each generator and capture outputs and errors."),
        path_check(root, "engineering.motor", "Engineering", "Active motor and battery generators exist", ["Engineering/py/Projects/Float/Boat/Motor/battery.py", "Engineering/py/Projects/Float/Boat/Motor/motor.py"], "Run each generator and verify packet schema."),
    ])
    ghost_hits = find_text_hits(root, root / "UI/Workbench", ["GhostCommandExporter", "JSON.stringify", "store_string"])
    if ghost_hits:
        checks.append(new_check("ghost.export_wiring", "Ghost Workflow", "Workbench export references are present", "WIRED", "FOUND", ", ".join(ghost_hits[:30]), "Execute export and inspect the file."))
    else:
        checks.append(new_check("ghost.export_wiring", "Ghost Workflow", "Workbench export references are present", "NONE", "NOT FOUND", "No matching references found inside UI/Workbench.", "Locate or implement the export route."))

    manual = [observation_record(observations, item) for item in MANUAL_DEFINITIONS]
    summary = {level: sum(1 for check in checks if check["evidence_level"] == level) for level in ["NONE", "PRESENT", "WIRED", "EXECUTABLE"]}
    for result in ["PASS", "PARTIAL", "FAIL", "UNTESTED"]:
        summary[result] = sum(1 for item in manual if item["result"] == result)
    current_test = next((item for item in manual if item["result"] != "PASS"), None)
    return {
        "schema_version": 3,
        "repository_root": str(root),
        "script_root": str(script_root),
        "generated_at": now_iso(),
        "rule": "Presence is not capability. Capability requires an observed end-to-end demonstration.",
        "summary": summary,
        "current_test": current_test,
        "checks": checks,
        "smoke_tests": [],
        "manual_demonstration": manual,
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Workbench Capability Audit", "",
        f"- Repository: `{report['repository_root']}`",
        f"- Generated: `{report['generated_at']}`",
        "- Governing rule: **Presence is not capability. Capability requires an observed end-to-end demonstration.**",
        "", "## Summary", "", "| State | Count |", "|---|---:|",
    ]
    for key, value in report["summary"].items():
        lines.append(f"| {key} | {value} |")
    current = report.get("current_test")
    if current:
        lines.extend(["", "## Current capability test", "", f"- ID: **{current['id']}**", f"- Step: {current['step']}", f"- Pass condition: {current['pass_condition']}", f"- Current result: **{current['result']}**"])
        if current.get("unresolved"):
            lines.append(f"- Unresolved: {', '.join(map(str, current['unresolved']))}")
    lines.extend(["", "## Automated inventory", "", "| ID | Category | Candidate capability | Evidence level | Status | Evidence | Next proof |", "|---|---|---|---|---|---|---|"])
    for check in report["checks"]:
        evidence = str(check["evidence"]).replace("|", "/").replace("\n", " ")
        next_proof = str(check["next_proof"]).replace("|", "/").replace("\n", " ")
        lines.append(f"| {check['id']} | {check['category']} | {check['capability']} | {check['evidence_level']} | {check['status']} | {evidence} | {next_proof} |")
    lines.extend(["", "## Manual end-to-end demonstration", "", "Manual results are loaded from `UI/Workbench/audit/observations.json`.", "Nothing becomes PASS from code inspection alone.", "", "| ID | Step | Pass condition | Result | Evidence |", "|---|---|---|---|---|"])
    for item in report["manual_demonstration"]:
        evidence = str(item.get("evidence", "")).replace("|", "/").replace("\n", " ")
        lines.append(f"| {item['id']} | {item['step']} | {item['pass_condition']} | {item['result']} | {evidence} |")
    lines.extend(["", "## Capability conclusion", "", "> We have candidate Workbench surfaces. End-to-end capability advances only through observed audit evidence.", "", "## Next development rule", "", "Work on the first manual capability step that is not PASS. Do not add unrelated features until that step passes or is explicitly blocked."])
    return "\n".join(lines) + "\n"


def write_outputs(root: Path, report: dict[str, Any]) -> dict[str, str]:
    script_root = root / "UI/Workbench/audit"
    output = script_root / "output"
    history = output / "history"
    evidence = script_root / "evidence"
    output.mkdir(parents=True, exist_ok=True)
    history.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    report_json = json.dumps(report, indent=2) + "\n"
    report_md = markdown(report)
    stable_json = output / "capability_state.json"
    stable_md = output / "capability_state.md"
    history_json = history / f"capability_audit_{timestamp}.json"
    history_md = history / f"capability_audit_{timestamp}.md"
    inventory = evidence / "latest_audit_inventory.json"
    stable_json.write_text(report_json, encoding="utf-8")
    stable_md.write_text(report_md, encoding="utf-8")
    history_json.write_text(report_json, encoding="utf-8")
    history_md.write_text(report_md, encoding="utf-8")
    inventory.write_text(json.dumps({"generated_at": report["generated_at"], "checks": report["checks"]}, indent=2) + "\n", encoding="utf-8")
    return {"stable_json": stable_json.relative_to(root).as_posix(), "stable_md": stable_md.relative_to(root).as_posix(), "history_json": history_json.relative_to(root).as_posix(), "history_md": history_md.relative_to(root).as_posix(), "inventory": inventory.relative_to(root).as_posix()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo_root", nargs="?", default=str(Path(__file__).resolve().parents[3]))
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    report = build_report(root)
    paths = write_outputs(root, report)
    print("Audit complete.")
    print(f"Stable JSON: {paths['stable_json']}")
    print(f"Stable MD:   {paths['stable_md']}")
    print(f"History JSON: {paths['history_json']}")
    print(f"History MD:   {paths['history_md']}")
    current = report.get("current_test") or {}
    if current:
        print("Current capability test:")
        print(f"  {current.get('id')}")
        print(f"  {current.get('step')}")
        print(f"  Result: {current.get('result')}")
    print("Summary:")
    for key, value in report["summary"].items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
