#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-$HOME/Core/Dashboard}"
AUDIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT="$AUDIT_ROOT/output"
HISTORY="$OUTPUT/history"
OBS="$AUDIT_ROOT/observations.json"

mkdir -p "$OUTPUT" "$HISTORY"

python3 - "$REPO_ROOT" "$AUDIT_ROOT" "$OUTPUT" "$HISTORY" "$OBS" <<'PY'
import json, sys
from datetime import datetime, timezone
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
audit = Path(sys.argv[2]).resolve()
output = Path(sys.argv[3]).resolve()
history = Path(sys.argv[4]).resolve()
obs_path = Path(sys.argv[5]).resolve()

def exists(p): return (repo / p).exists()
def text(p):
    f = repo / p
    return f.read_text(encoding="utf-8", errors="replace") if f.exists() else ""
def now(): return datetime.now(timezone.utc).isoformat()
def row(i, c, cap, level, status, evidence, proof):
    return {
        "id": i, "category": c, "capability": cap,
        "evidence_level": level, "status": status,
        "evidence": evidence, "next_proof": proof
    }

checks = []

def path_check(i, c, cap, p, proof):
    checks.append(row(
        i, c, cap,
        "PRESENT" if exists(p) else "NONE",
        "FOUND" if exists(p) else "NOT FOUND",
        p,
        proof
    ))

# Core surfaces
for args in [
    ("shell.scene","Runtime","OperatorShell main scene exists","UI/OperatorShell/scenes/Main.tscn","Launch through Dashboard Main."),
    ("shell.main","Runtime","OperatorShell main controller exists","UI/OperatorShell/Main.gd","Confirm startup without fatal errors."),
    ("layout.left","Layout","Left panel exists","UI/OperatorShell/layout/LeftPanel.gd","Render capability state here."),
    ("layout.top","Layout","Top bars exist","UI/OperatorShell/layout/TopBars.gd","Confirm visible controls."),
    ("layout.bottom","Layout","Bottom runtime dock exists","UI/OperatorShell/layout/BottomDock.gd","Open and test each tab."),
    ("layout.right","Layout","Right rail exists","UI/OperatorShell/layout/RightRail.gd","Confirm visible controls."),
    ("layout.workspace","Layout","Workspace surface exists","UI/OperatorShell/layout/WorkspaceSurface.gd","Enable and render workspace."),
    ("runtime.cli","Runtime Services","CLI bridge exists","UI/OperatorShell/runtime/CliBridge.gd","Run one read-only command."),
    ("runtime.actions","Runtime Services","Command actions exist","UI/OperatorShell/runtime/CommandActions.gd","Trigger one read-only action."),
    ("runtime.packet","Runtime Services","Command packet exists","UI/OperatorShell/runtime/CommandPacket.gd","Generate and inspect one packet."),
    ("runtime.mission","Runtime Services","Mission service exists","UI/OperatorShell/runtime/MissionService.gd","Render mission data."),
    ("runtime.observation","Runtime Services","Observation tracker exists","UI/OperatorShell/runtime/ObservationTracker.gd","Record one observation."),
    ("runtime.result","Runtime Services","Result renderer exists","UI/OperatorShell/runtime/ResultRenderer.gd","Render stdout and stderr."),
    ("runtime.status","Runtime Services","Status service exists","UI/OperatorShell/runtime/StatusService.gd","Refresh and display status."),
    ("runtime.modelserver.controller","Runtime Services","Model server controller exists","UI/OperatorShell/runtime/ModelServerController.gd","Render status and toggle the lifecycle manager."),
    ("runtime.modelserver.manager","Runtime Services","Model server lifecycle manager exists","Agency/Core/runtime/model_server_manager.py","Run status/start/stop smoke tests.")
]:
    path_check(*args)

project = text("UI/project.godot")
checks.append(row(
    "route.dashboard","Routing","Godot boots Dashboard Main",
    "WIRED" if 'run/main_scene="res://Main/Main.tscn"' in project else "NONE",
    "FOUND" if 'run/main_scene="res://Main/Main.tscn"' in project else "NOT FOUND",
    "UI/project.godot",
    "Launch and observe Dashboard Main."
))

cockpit = text("UI/Main/Main.gd")
operator_default = "DEFAULT_ROUTE := ROUTE_OPERATOR_SHELL" in cockpit
checks.append(row(
    "route.operator","Routing","Dashboard defaults to OperatorShell",
    "WIRED" if operator_default else "NONE",
    "FOUND" if operator_default else "NOT FOUND",
    "UI/Main/Main.gd",
    "Launch and observe OperatorShell."
))

main = text("UI/OperatorShell/Main.gd")
bottom = text("UI/OperatorShell/layout/BottomDock.gd")

for i, cap, needles, proof in [
    ("wire.cli","CLI bridge references exist",["CliBridge.","const CliBridge"],"Run a read-only command."),
    ("wire.intent","Intent input routing exists",["terminal_input","_on_terminal_input_submitted"],"Submit harmless text."),
    ("wire.workspace","Workspace construction exists",["WorkspaceSurface.new","workspace_tabs"],"Enable workspace."),
    ("wire.density","Density control exists",["_cycle_terminal_density","apply_terminal_density"],"Cycle modes."),
    ("wire.modelserver","Model-server control is wired",["ModelServerController","_build_model_server_control","MODEL SERVER"],"Observe the compact control at the top of the right rail."),
]:
    hit = any(n in main for n in needles)
    checks.append(row(i,"Wiring",cap,"WIRED" if hit else "NONE","FOUND" if hit else "NOT FOUND",", ".join(needles),proof))

for tab in ["Logs","Diffs","Packets","Terminal"]:
    hit = f'add_bottom("{tab}"' in bottom
    checks.append(row(
        f"tab.{tab.lower()}","Runtime Dock",f"{tab} tab is declared",
        "PRESENT" if hit else "NONE",
        "FOUND" if hit else "NOT FOUND",
        "UI/OperatorShell/layout/BottomDock.gd",
        f"Open the {tab} tab."
    ))

manual_defs = [
    ("shell.01","Launch OperatorShell","Dashboard Main opens OperatorShell without fatal parser/runtime errors."),
    ("shell.02","Host OperatorShell inside Dashboard Main","OperatorShell is visibly contained in the route host."),
    ("shell.03","Force kiosk window","Application occupies the full 1920x1080 display."),
    ("shell.04","Capture screenshot with Alt+S","A 1920x1080 PNG is written to ~/Core/Pictures."),
    ("shell.05","Open Terminal tab","Terminal becomes active."),
    ("shell.06","Open Logs tab","Logs becomes active."),
    ("shell.07","Open Diffs tab","Diffs becomes active."),
    ("shell.08","Open Packets tab","Packets becomes active."),
    ("shell.09","Submit intent text","Text is accepted and routed without crashing."),
    ("shell.10","Cycle terminal density","All configured density modes visibly change."),
    ("shell.11","Collapse and restore dock","Dock collapses and restores without losing state."),
    ("shell.12","Resolve CLI path","Expected dashboard CLI path is reported."),
    ("shell.13","Run read-only CLI command","Command executes and returns a result."),
    ("shell.14","Render stdout","stdout appears in a result surface."),
    ("shell.15","Render stderr","stderr appears distinctly."),
    ("shell.16","Expose exit status","Success/failure is visible."),
    ("shell.17","Enable workspace surface","Workspace tabs render above the dock."),
    ("shell.18","Host Workbench in workspace","Workbench loads without killing OperatorShell."),
    ("modelserver.01","Model-server control renders at top of right column","MODEL SERVER appears as the first control in the right-column stack."),
    ("modelserver.02","OFF starts llama-server","Clicking OFF starts the configured localhost llama-server."),
    ("modelserver.03","UI reports READY only after health succeeds","The UI reaches ON/ready only after the health endpoint succeeds."),
    ("modelserver.04","ON stops llama-server","Clicking ON stops the verified managed llama-server process."),
    ("modelserver.05","UI tracks lifecycle changes initiated through SSH","The UI poller notices SSH start/stop changes."),
    ("modelserver.06","Duplicate start is prevented","A second start does not create another llama-server process."),
    ("modelserver.07","Failed startup is surfaced without crashing OperatorShell","Startup failure is visible in the control and dashboard log."),
    ("modelserver.08","Server binds only to 127.0.0.1","The live listener is restricted to localhost."),
    ("modelserver.09","OperatorShell can close without forcing server shutdown","Closing OperatorShell leaves explicit model-server lifecycle control to the operator.")
]

if not obs_path.exists():
    obs_path.write_text(json.dumps({"schema_version":1,"updated_at":now(),"observations":{}}, indent=2))

obs = json.loads(obs_path.read_text(encoding="utf-8")).get("observations", {})
manual = []
for i, step, condition in manual_defs:
    rec = obs.get(i,{})
    evidence = "; ".join(
        x.get("observation","") if isinstance(x,dict) else str(x)
        for x in rec.get("evidence",[])
    )
    manual.append({
        "id":i,"step":step,"pass_condition":condition,
        "result":rec.get("result","UNTESTED"),
        "evidence":evidence,
        "unresolved":rec.get("unresolved",[])
    })

summary = {
    "NONE":sum(x["evidence_level"]=="NONE" for x in checks),
    "PRESENT":sum(x["evidence_level"]=="PRESENT" for x in checks),
    "WIRED":sum(x["evidence_level"]=="WIRED" for x in checks),
    "EXECUTABLE":sum(x["evidence_level"]=="EXECUTABLE" for x in checks),
    "PASS":sum(x["result"]=="PASS" for x in manual),
    "PARTIAL":sum(x["result"]=="PARTIAL" for x in manual),
    "FAIL":sum(x["result"]=="FAIL" for x in manual),
    "UNTESTED":sum(x["result"]=="UNTESTED" for x in manual),
}
current = next((x for x in manual if x["result"]!="PASS"), None)

report = {
    "schema_version":1,
    "repository_root":str(repo),
    "generated_at":now(),
    "rule":"Presence is not capability. Capability requires an observed end-to-end demonstration.",
    "summary":summary,
    "current_test":current,
    "checks":checks,
    "manual_demonstration":manual
}

stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
stable_json = output/"operator_shell_state.json"
stable_md = output/"operator_shell_state.md"
hist_json = history/f"operator_shell_audit_{stamp}.json"
hist_md = history/f"operator_shell_audit_{stamp}.md"

j = json.dumps(report, indent=2)
stable_json.write_text(j, encoding="utf-8")
hist_json.write_text(j, encoding="utf-8")

lines = [
    "# OperatorShell Capability Audit","",
    f"- Repository: `{repo}`",
    f"- Generated: {report['generated_at']}",
    f"- Governing rule: **{report['rule']}**","",
    "## Summary","",
    "| State | Count |","|---|---:|"
]
for k,v in summary.items():
    lines.append(f"| {k} | {v} |")
if current:
    lines += ["","## Current capability test","",
              f"- ID: **{current['id']}**",
              f"- Step: {current['step']}",
              f"- Pass condition: {current['pass_condition']}",
              f"- Result: **{current['result']}**"]
lines += ["","## Automated inventory","",
          "| ID | Category | Candidate capability | Evidence level | Status | Evidence | Next proof |",
          "|---|---|---|---|---|---|---|"]
for x in checks:
    lines.append(f"| {x['id']} | {x['category']} | {x['capability']} | {x['evidence_level']} | {x['status']} | {x['evidence']} | {x['next_proof']} |")
lines += ["","## Manual demonstration checklist","",
          "Manual results come from `UI/OperatorShell/audit/observations.json`.",
          "Nothing becomes PASS from code inspection alone.","",
          "| ID | Step | Pass condition | Result | Evidence |",
          "|---|---|---|---|---|"]
for x in manual:
    lines.append(f"| {x['id']} | {x['step']} | {x['pass_condition']} | {x['result']} | {x['evidence']} |")
lines += ["","## Defensible claim","",
          "> OperatorShell contains substantial candidate runtime, layout, routing, and command surfaces. Only manually observed steps may be claimed as working capabilities.","",
          "## Next development rule","",
          "Work on the first manual capability step that is not PASS. Do not add unrelated features until it passes or is explicitly blocked."]

m = "\n".join(lines)+"\n"
stable_md.write_text(m, encoding="utf-8")
hist_md.write_text(m, encoding="utf-8")

print()
print("OperatorShell audit complete.")
print(f"Stable JSON: {stable_json}")
print(f"Stable MD:   {stable_md}")
print(f"History JSON: {hist_json}")
print(f"History MD:   {hist_md}")
print()
if current:
    print("Current capability test:")
    print(f"  {current['id']}")
    print(f"  {current['step']}")
    print(f"  Result: {current['result']}")
    print()
print("Summary:")
for k,v in summary.items():
    print(f"  {k}: {v}")
PY
