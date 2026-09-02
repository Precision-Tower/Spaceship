# Workbench Capability Audit

- Repository: `/home/spaztic/Core/Dashboard`
- Generated: `2026-07-16T06:59:27.556236+00:00`
- Governing rule: **Presence is not capability. Capability requires an observed end-to-end demonstration.**

## Summary

| State | Count |
|---|---:|
| NONE | 1 |
| PRESENT | 23 |
| WIRED | 11 |
| EXECUTABLE | 0 |
| PASS | 0 |
| PARTIAL | 1 |
| FAIL | 0 |
| UNTESTED | 10 |

## Current capability test

- ID: **demo.01**
- Step: Launch the current Godot project
- Pass condition: Workbench opens and remains usable; fatal parser or runtime errors are not present.
- Current result: **PARTIAL**
- Unresolved: Console output was not captured, so absence of parser or runtime errors is not yet established.

## Automated inventory

| ID | Category | Candidate capability | Evidence level | Status | Evidence | Next proof |
|---|---|---|---|---|---|---|
| repo.run_py | Runtime | Root runtime entrypoint exists | PRESENT | FOUND | run.py | Run the entrypoint and capture actual output. |
| agency.cli | Runtime | Agency CLI entrypoint exists | PRESENT | FOUND | Agency/Core/cli/dashboard_cli.py | Run a read-only command and capture output. |
| ui.project | UI | Godot project exists | PRESENT | FOUND | UI/project.godot | Launch the project and record the actual scene. |
| workbench.main | UI | Workbench boot scene exists | PRESENT | FOUND | UI/Workbench/Main/Main.tscn | Launch the scene and verify it remains usable. |
| workbench.main_script | UI | Workbench boot script exists | PRESENT | FOUND | UI/Workbench/Main/Main.gd | Parse and launch the boot scene. |
| workbench.shell_scene | UI | Workbench shell scene exists | PRESENT | FOUND | UI/Workbench/scenes/Workbench.tscn | Instantiate it through the boot scene. |
| workbench.shell_script | UI | Workbench shell script is canonical | PRESENT | FOUND | UI/Workbench/scenes/Workbench.gd | Verify it owns shell layout creation. |
| workbench.shell_builder | UI | Workbench shell builder is canonical | PRESENT | FOUND | UI/Workbench/layout/WorkbenchShellBuilder.gd | Verify only this builder path is loaded. |
| workbench.left_panel | UI | Workbench left audit panel exists | PRESENT | FOUND | UI/Workbench/inspectors/LeftPanel.gd | Run audit and verify the panel reloads current state. |
| shared.screenshot_controller | Shared UI | Shared screenshot controller exists | PRESENT | FOUND | UI/shared/ScreenshotController.gd | Press Alt+S and verify output. |
| audit.posix_runner | Audit | Linux audit runner exists | PRESENT | FOUND | UI/Workbench/audit/capability-audit.sh, UI/Workbench/audit/capability_audit.py | Run it on the black laptop. |
| ui.main_scene | UI | Godot project boots through cockpit router | WIRED | FOUND | run/main_scene="res://Main/Main.tscn" | Launch the project and record the active route. |
| workbench.route_constant | UI | Workbench route is declared in cockpit router | WIRED | FOUND | UI/Main/Main.gd: ROUTE_WORKBENCH := "res://Workbench/Main/Main.tscn" | Launch the Workbench route. |
| workbench.default_route | UI | Cockpit default remains OperatorShell | WIRED | FOUND | UI/Main/Main.gd: DEFAULT_ROUTE := ROUTE_OPERATOR_SHELL | Do not embed Workbench into OperatorShell yet. |
| workbench.root_duplicates | Repository Hygiene | Root-level duplicate Workbench scripts are absent | NONE | ABSENT | No root-level duplicate scripts found. | Keep canonical scripts under Main/scenes/layout. |
| workbench.shell_scene_script | UI | Workbench shell scene uses canonical script | WIRED | FOUND | UI/Workbench/scenes/Workbench.tscn: path="res://Workbench/scenes/Workbench.gd" | Load the scene. |
| workbench.builder_reference | UI | Workbench shell uses canonical builder | WIRED | FOUND | UI/Workbench/scenes/Workbench.gd: preload("res://Workbench/layout/WorkbenchShellBuilder.gd") | Load the shell scene. |
| left_panel.audit_state | Audit | Left panel reads stable audit state | WIRED | FOUND | UI/Workbench/inspectors/LeftPanel.gd: res://Workbench/audit/output/capability_state.json | Run Ctrl+Shift+A and observe reload. |
| audit.hotkey | Audit | Ctrl+Shift+A audit hotkey remains wired | WIRED | FOUND | UI/Workbench/audit/AuditController.gd: event.ctrl_pressed | Press Ctrl+Shift+A in Workbench. |
| audit.controller_posix | Audit | Audit controller can call Linux runner | WIRED | FOUND | UI/Workbench/audit/AuditController.gd: capability-audit.sh | Press Ctrl+Shift+A on Linux. |
| shared.screenshot_main | Shared UI | Cockpit uses shared screenshot controller | WIRED | FOUND | UI/Main/Main.gd: res://shared/ScreenshotController.gd | Press Alt+S in cockpit. |
| shared.screenshot_workbench | Shared UI | Workbench uses shared screenshot controller | WIRED | FOUND | UI/Workbench/Main/Main.gd: res://shared/ScreenshotController.gd | Press Alt+S in Workbench. |
| ghost.controller | Ghost Workflow | Ghost command controller exists | PRESENT | FOUND | UI/Workbench/interaction/GhostCommandController.gd | Create one primitive from an operator action. |
| ghost.dialogs | Ghost Workflow | Ghost authoring dialogs exist | PRESENT | FOUND | UI/Workbench/interaction/GhostCommandDialogs.gd | Open the authoring UI and submit one command. |
| ghost.renderer | Ghost Workflow | Ghost primitive renderer exists | PRESENT | FOUND | UI/Workbench/rendering/GhostPrimitiveRenderer.gd | Observe a primitive rendered in the viewport. |
| ghost.exporter | Ghost Workflow | Ghost JSON exporter exists | PRESENT | FOUND | UI/Workbench/packet/GhostCommandExporter.gd | Export one primitive and validate the JSON. |
| packet.loader | Workbench | Packet loader exists | PRESENT | FOUND | UI/Workbench/packet/PacketLoader.gd | Load a known JSON packet in the running Workbench. |
| packet.display | Workbench | Packet display resolver exists | PRESENT | FOUND | UI/Workbench/packet/PacketDisplayResolver.gd | Select an object and verify packet details are shown. |
| render.packet_geometry | Workbench | Packet geometry renderer exists | PRESENT | FOUND | UI/Workbench/rendering/PacketGeometryRenderer.gd | Render geometry from a packet. |
| selection.raycaster | Workbench | Viewport selection code exists | PRESENT | FOUND | UI/Workbench/selection/SelectionRaycaster.gd | Click a rendered object and observe selection state. |
| session | Workbench | Workbench session state exists | PRESENT | FOUND | UI/Workbench/core/WorkbenchSession.gd | Load, modify, and reload without losing traceable state. |
| engineering.boat_assembly | Engineering | Active boat assembly generator exists | PRESENT | FOUND | Engineering/Projects/Float/Boat/boat_assembly.py | Run it successfully and verify generated packet fields. |
| engineering.hull | Engineering | Active hull generation scripts exist | PRESENT | FOUND | Engineering/Projects/Float/Boat/Hull/hull_inventory.py, Engineering/Projects/Float/Boat/Hull/hull_frame.py | Run each generator and capture outputs and errors. |
| engineering.motor | Engineering | Active motor and battery generators exist | PRESENT | FOUND | Engineering/Projects/Float/Boat/Motor/battery.py, Engineering/Projects/Float/Boat/Motor/motor.py | Run each generator and verify packet schema. |
| ghost.export_wiring | Ghost Workflow | Workbench export references are present | WIRED | FOUND | UI/Workbench/Main/Main.gd: GhostCommandExporter, UI/Workbench/actions/ProjectActionController.gd: JSON.stringify, UI/Workbench/interaction/GhostCommandController.gd: JSON.stringify, UI/Workbench/packet/GhostCommandExporter.gd: GhostCommandExporter | Execute export and inspect the file. |

## Manual end-to-end demonstration

Manual results are loaded from `UI/Workbench/audit/observations.json`.
Nothing becomes PASS from code inspection alone.

| ID | Step | Pass condition | Result | Evidence |
|---|---|---|---|---|
| demo.01 | Launch the current Godot project | Workbench opens and remains usable; fatal parser or runtime errors are not present. | PARTIAL | Godot launched and Workbench visibly rendered with the viewport, object tree, and left-side status panel. |
| demo.02 | Create or load an empty room | Room is visibly present and has a traceable source. | UNTESTED |  |
| demo.03 | Create one ghost primitive | Primitive appears in the viewport from an operator action. | UNTESTED |  |
| demo.04 | Move, rotate, and scale the primitive | Transforms visibly change and persist in candidate state. | UNTESTED |  |
| demo.05 | Export the ghost candidate to JSON | A new JSON file is written with identity and transforms. | UNTESTED |  |
| demo.06 | Validate and inspect the JSON | JSON parses and fields match the viewport candidate. | UNTESTED |  |
| demo.07 | Edit one JSON field outside Godot | The edit is deliberate, parseable, and recorded. | UNTESTED |  |
| demo.08 | Reload the edited JSON | Workbench reflects the edited field. | UNTESTED |  |
| demo.09 | Assign additional object detail | Material, type, or metadata can be added without losing base geometry. | UNTESTED |  |
| demo.10 | Save and reopen the project state | The room and object reconstruct from files, not memory. | UNTESTED |  |
| demo.11 | Trace provenance | The producing command, file, and code path can be identified. | UNTESTED |  |

## Capability conclusion

> We have candidate Workbench surfaces. End-to-end capability advances only through observed audit evidence.

## Next development rule

Work on the first manual capability step that is not PASS. Do not add unrelated features until that step passes or is explicitly blocked.
