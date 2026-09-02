# OperatorShell Capability Audit

- Repository: `/home/spaztic/Core/Dashboard`
- Generated: 2026-07-15T21:17:13.711846+00:00
- Governing rule: **Presence is not capability. Capability requires an observed end-to-end demonstration.**

## Summary

| State | Count |
|---|---:|
| NONE | 1 |
| PRESENT | 17 |
| WIRED | 6 |
| EXECUTABLE | 0 |
| PASS | 4 |
| PARTIAL | 0 |
| FAIL | 0 |
| UNTESTED | 14 |

## Current capability test

- ID: **shell.05**
- Step: Open Terminal tab
- Pass condition: Terminal becomes active.
- Result: **UNTESTED**

## Automated inventory

| ID | Category | Candidate capability | Evidence level | Status | Evidence | Next proof |
|---|---|---|---|---|---|---|
| shell.scene | Runtime | OperatorShell main scene exists | PRESENT | FOUND | UI/OperatorShell/scenes/Main.tscn | Launch through Dashboard Main. |
| shell.main | Runtime | OperatorShell main controller exists | PRESENT | FOUND | UI/OperatorShell/Main.gd | Confirm startup without fatal errors. |
| layout.left | Layout | Left panel exists | PRESENT | FOUND | UI/OperatorShell/layout/LeftPanel.gd | Render capability state here. |
| layout.top | Layout | Top bars exist | PRESENT | FOUND | UI/OperatorShell/layout/TopBars.gd | Confirm visible controls. |
| layout.bottom | Layout | Bottom runtime dock exists | PRESENT | FOUND | UI/OperatorShell/layout/BottomDock.gd | Open and test each tab. |
| layout.right | Layout | Right rail exists | PRESENT | FOUND | UI/OperatorShell/layout/RightRail.gd | Confirm visible controls. |
| layout.workspace | Layout | Workspace surface exists | PRESENT | FOUND | UI/OperatorShell/layout/WorkspaceSurface.gd | Enable and render workspace. |
| runtime.cli | Runtime Services | CLI bridge exists | PRESENT | FOUND | UI/OperatorShell/runtime/CliBridge.gd | Run one read-only command. |
| runtime.actions | Runtime Services | Command actions exist | PRESENT | FOUND | UI/OperatorShell/runtime/CommandActions.gd | Trigger one read-only action. |
| runtime.packet | Runtime Services | Command packet exists | PRESENT | FOUND | UI/OperatorShell/runtime/CommandPacket.gd | Generate and inspect one packet. |
| runtime.mission | Runtime Services | Mission service exists | PRESENT | FOUND | UI/OperatorShell/runtime/MissionService.gd | Render mission data. |
| runtime.observation | Runtime Services | Observation tracker exists | PRESENT | FOUND | UI/OperatorShell/runtime/ObservationTracker.gd | Record one observation. |
| runtime.result | Runtime Services | Result renderer exists | PRESENT | FOUND | UI/OperatorShell/runtime/ResultRenderer.gd | Render stdout and stderr. |
| runtime.status | Runtime Services | Status service exists | PRESENT | FOUND | UI/OperatorShell/runtime/StatusService.gd | Refresh and display status. |
| route.dashboard | Routing | Godot boots Dashboard Main | WIRED | FOUND | UI/project.godot | Launch and observe Dashboard Main. |
| route.operator | Routing | Dashboard defaults to OperatorShell | WIRED | FOUND | UI/Main/Main.gd | Launch and observe OperatorShell. |
| wire.cli | Wiring | CLI bridge references exist | WIRED | FOUND | CliBridge., const CliBridge | Run a read-only command. |
| wire.intent | Wiring | Intent input routing exists | WIRED | FOUND | terminal_input, _on_terminal_input_submitted | Submit harmless text. |
| wire.workspace | Wiring | Workspace construction exists | WIRED | FOUND | WorkspaceSurface.new, workspace_tabs | Enable workspace. |
| wire.density | Wiring | Density control exists | WIRED | FOUND | _cycle_terminal_density, apply_terminal_density | Cycle modes. |
| tab.logs | Runtime Dock | Logs tab is declared | PRESENT | FOUND | UI/OperatorShell/layout/BottomDock.gd | Open the Logs tab. |
| tab.diffs | Runtime Dock | Diffs tab is declared | PRESENT | FOUND | UI/OperatorShell/layout/BottomDock.gd | Open the Diffs tab. |
| tab.packets | Runtime Dock | Packets tab is declared | PRESENT | FOUND | UI/OperatorShell/layout/BottomDock.gd | Open the Packets tab. |
| tab.terminal | Runtime Dock | Terminal tab is declared | NONE | NOT FOUND | UI/OperatorShell/layout/BottomDock.gd | Open the Terminal tab. |

## Manual demonstration checklist

Manual results come from `UI/OperatorShell/audit/observations.json`.
Nothing becomes PASS from code inspection alone.

| ID | Step | Pass condition | Result | Evidence |
|---|---|---|---|---|
| shell.01 | Launch OperatorShell | Dashboard Main opens OperatorShell without fatal parser/runtime errors. | PASS | Dashboard Main launched OperatorShell without fatal parser or runtime errors. |
| shell.02 | Host OperatorShell inside Dashboard Main | OperatorShell is visibly contained in the route host. | PASS | OperatorShell visibly rendered inside Dashboard Main's route host. |
| shell.03 | Force kiosk window | Application occupies the full 1920x1080 display. | PASS | Dashboard Main occupied the full 1920x1080 black-laptop display. |
| shell.04 | Capture screenshot with Alt+S | A 1920x1080 PNG is written to ~/Core/Pictures. | PASS | Alt+S wrote a 1920x1080 PNG to /home/spaztic/Core/Pictures. |
| shell.05 | Open Terminal tab | Terminal becomes active. | UNTESTED |  |
| shell.06 | Open Logs tab | Logs becomes active. | UNTESTED |  |
| shell.07 | Open Diffs tab | Diffs becomes active. | UNTESTED |  |
| shell.08 | Open Packets tab | Packets becomes active. | UNTESTED |  |
| shell.09 | Submit intent text | Text is accepted and routed without crashing. | UNTESTED |  |
| shell.10 | Cycle terminal density | All configured density modes visibly change. | UNTESTED |  |
| shell.11 | Collapse and restore dock | Dock collapses and restores without losing state. | UNTESTED |  |
| shell.12 | Resolve CLI path | Expected dashboard CLI path is reported. | UNTESTED |  |
| shell.13 | Run read-only CLI command | Command executes and returns a result. | UNTESTED |  |
| shell.14 | Render stdout | stdout appears in a result surface. | UNTESTED |  |
| shell.15 | Render stderr | stderr appears distinctly. | UNTESTED |  |
| shell.16 | Expose exit status | Success/failure is visible. | UNTESTED |  |
| shell.17 | Enable workspace surface | Workspace tabs render above the dock. | UNTESTED |  |
| shell.18 | Host Workbench in workspace | Workbench loads without killing OperatorShell. | UNTESTED |  |

## Defensible claim

> OperatorShell contains substantial candidate runtime, layout, routing, and command surfaces. Only manually observed steps may be claimed as working capabilities.

## Next development rule

Work on the first manual capability step that is not PASS. Do not add unrelated features until it passes or is explicitly blocked.
