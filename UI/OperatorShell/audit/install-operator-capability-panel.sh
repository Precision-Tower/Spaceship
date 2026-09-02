#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-$HOME/Core/Dashboard}"
MAIN="$REPO_ROOT/UI/OperatorShell/Main.gd"
LEFT="$REPO_ROOT/UI/OperatorShell/layout/LeftPanel.gd"
AUDIT_DIR="$REPO_ROOT/UI/OperatorShell/audit"
PANEL="$AUDIT_DIR/CapabilityPanel.gd"
CONTROLLER="$AUDIT_DIR/OperatorAuditController.gd"

mkdir -p "$AUDIT_DIR/output/history"

for path in "$MAIN" "$LEFT" "$AUDIT_DIR/operator-shell-audit.sh"; do
  [[ -e "$path" ]] || { echo "Missing: $path" >&2; exit 1; }
done

STAMP="$(date +%Y%m%d_%H%M%S)"
cp "$MAIN" "$MAIN.bak_$STAMP"
cp "$LEFT" "$LEFT.bak_$STAMP"

cat > "$PANEL" <<'GDSCRIPT'
extends VBoxContainer
class_name OperatorShellCapabilityPanel

var current_test_label: RichTextLabel
var summary_label: Label
var details_button: Button
var details_label: RichTextLabel
var details_open := false

func _ready() -> void:
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	add_theme_constant_override("separation", 6)

	var title := Label.new()
	title.text = "CAPABILITY"
	title.add_theme_font_size_override("font_size", 15)
	add_child(title)

	current_test_label = RichTextLabel.new()
	current_test_label.bbcode_enabled = true
	current_test_label.fit_content = true
	current_test_label.scroll_active = false
	current_test_label.selection_enabled = true
	current_test_label.custom_minimum_size = Vector2(0, 86)
	add_child(current_test_label)

	summary_label = Label.new()
	summary_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	add_child(summary_label)

	var refresh := Label.new()
	refresh.text = "Ctrl+Shift+A  Refresh"
	add_child(refresh)

	details_button = Button.new()
	details_button.text = "+ Details"
	details_button.pressed.connect(_toggle_details)
	add_child(details_button)

	details_label = RichTextLabel.new()
	details_label.bbcode_enabled = true
	details_label.fit_content = true
	details_label.scroll_active = false
	details_label.selection_enabled = true
	details_label.visible = false
	details_label.custom_minimum_size = Vector2(0, 80)
	add_child(details_label)

	show_missing_state()

func show_missing_state() -> void:
	current_test_label.text = "[b]No audit state loaded[/b]\nRun Ctrl+Shift+A"
	summary_label.text = "No summary available"
	details_label.text = "operator_shell_state.json was not loaded."

func show_running() -> void:
	current_test_label.text = "[b]Running OperatorShell audit...[/b]"
	summary_label.text = "Inspecting current repository state"

func show_error(message: String) -> void:
	current_test_label.text = "[color=#e05f5f][b]AUDIT FAILED[/b][/color]"
	summary_label.text = message
	details_label.text = message

func load_state(state: Dictionary) -> void:
	var current: Dictionary = state.get("current_test", {})
	var summary: Dictionary = state.get("summary", {})

	current_test_label.text = (
		"[color=#f1d58a][b]%s[/b][/color]\n%s\n[b]%s[/b]"
		% [
			str(current.get("id", "none")),
			str(current.get("step", "No active test")),
			str(current.get("result", "UNKNOWN"))
		]
	)

	summary_label.text = (
		"PASS %d  ·  PARTIAL %d  ·  FAIL %d  ·  UNTESTED %d"
		% [
			int(summary.get("PASS", 0)),
			int(summary.get("PARTIAL", 0)),
			int(summary.get("FAIL", 0)),
			int(summary.get("UNTESTED", 0))
		]
	)

	var evidence := str(current.get("evidence", ""))
	if evidence.is_empty():
		evidence = "No evidence recorded."

	var unresolved_value = current.get("unresolved", [])
	var unresolved := "None"
	if unresolved_value is Array and not unresolved_value.is_empty():
		unresolved = "\n".join(PackedStringArray(unresolved_value))

	details_label.text = (
		"[b]Pass condition[/b]\n%s\n\n[b]Evidence[/b]\n%s\n\n[b]Unresolved[/b]\n%s"
		% [
			str(current.get("pass_condition", "")),
			evidence,
			unresolved
		]
	)

func _toggle_details() -> void:
	details_open = not details_open
	details_label.visible = details_open
	details_button.text = "- Details" if details_open else "+ Details"
GDSCRIPT

cat > "$CONTROLLER" <<'GDSCRIPT'
extends Node
class_name OperatorShellAuditController

const AUDIT_SCRIPT_PATH := "res://OperatorShell/audit/operator-shell-audit.sh"
const STATE_PATH := "res://OperatorShell/audit/output/operator_shell_state.json"

var panel
var audit_running := false

func setup(next_panel) -> void:
	panel = next_panel
	var state := load_state()
	if state.get("ok", false):
		_refresh_panel(state)

func handle_input(event: InputEvent) -> bool:
	if event is InputEventKey:
		if (
			event.pressed
			and not event.echo
			and event.ctrl_pressed
			and event.shift_pressed
			and event.keycode == KEY_A
		):
			if not audit_running:
				run_audit()
			return true
	return false

func run_audit() -> void:
	audit_running = true
	if panel != null and panel.has_method("show_running"):
		panel.show_running()

	var script_path := ProjectSettings.globalize_path(AUDIT_SCRIPT_PATH)
	var ui_root := ProjectSettings.globalize_path("res://")
	ui_root = ui_root.trim_suffix("/").trim_suffix("\\")
	var repo_root := ui_root.get_base_dir()
	var output: Array = []

	var exit_code := OS.execute(
		"bash",
		PackedStringArray([script_path, repo_root]),
		output,
		true,
		false
	)

	if exit_code != 0:
		_fail("Audit exited %d.\n%s" % [exit_code, "\n".join(output)])
		return

	var state := load_state()
	if not state.get("ok", false):
		_fail(str(state.get("error", "Unable to load audit state.")))
		return

	audit_running = false
	_refresh_panel(state)
	print("[OperatorAudit] complete")
	print("[OperatorAudit] summary: ", state.get("summary", {}))
	print("[OperatorAudit] current_test: ", state.get("current_test", {}))

func load_state() -> Dictionary:
	var state_path := ProjectSettings.globalize_path(STATE_PATH)
	if not FileAccess.file_exists(state_path):
		return {"ok": false, "error": "operator_shell_state.json does not exist"}

	var file := FileAccess.open(state_path, FileAccess.READ)
	if file == null:
		return {"ok": false, "error": "Could not open operator_shell_state.json"}

	var parsed = JSON.parse_string(file.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY:
		return {"ok": false, "error": "operator_shell_state.json did not parse as a dictionary"}

	var state: Dictionary = parsed
	state["ok"] = true
	return state

func _refresh_panel(state: Dictionary) -> void:
	if panel != null and panel.has_method("load_state"):
		panel.load_state(state)

func _fail(message: String) -> void:
	audit_running = false
	if panel != null and panel.has_method("show_error"):
		panel.show_error(message)
	push_error("[OperatorAudit] %s" % message)
GDSCRIPT

python3 - "$MAIN" "$LEFT" <<'PY'
from pathlib import Path
import re, sys

main_path = Path(sys.argv[1])
left_path = Path(sys.argv[2])
main = main_path.read_text(encoding="utf-8")
left = left_path.read_text(encoding="utf-8")

panel_preload = 'const CapabilityPanel = preload("res://OperatorShell/audit/CapabilityPanel.gd")'
if panel_preload not in left:
    anchor = 'const MissionService = preload("res://OperatorShell/runtime/MissionService.gd")'
    if anchor not in left:
        raise SystemExit("LeftPanel preload anchor not found")
    left = left.replace(anchor, anchor + "\n" + panel_preload, 1)

mount = (
    "        host.capability_panel = CapabilityPanel.new()\n"
    "        box.add_child(host.capability_panel)\n\n"
    "        var capability_sep := HSeparator.new()\n"
    "        box.add_child(capability_sep)\n\n"
)
if "host.capability_panel = CapabilityPanel.new()" not in left:
    anchor = "        shell.add_child(box)\n"
    if anchor not in left:
        raise SystemExit("LeftPanel mount anchor not found")
    left = left.replace(anchor, anchor + "\n" + mount, 1)

controller_preload = 'const OperatorAuditController = preload("res://OperatorShell/audit/OperatorAuditController.gd")'
if controller_preload not in main:
    anchor = 'const StatusService = preload("res://OperatorShell/runtime/StatusService.gd")'
    if anchor not in main:
        raise SystemExit("Main preload anchor not found")
    main = main.replace(anchor, anchor + "\n" + controller_preload, 1)

if not re.search(r'(?m)^var capability_panel\s*$', main):
    anchor = re.search(r'(?m)^var left_panel\s*$', main)
    if not anchor:
        raise SystemExit("Main left_panel variable anchor not found")
    replacement = anchor.group(0) + "\nvar capability_panel\nvar audit_controller"
    main = main[:anchor.start()] + replacement + main[anchor.end():]

if "audit_controller = OperatorAuditController.new()" not in main:
    anchor = "        _build()\n        _seed()\n"
    if anchor not in main:
        raise SystemExit("Main _ready anchor not found")
    replacement = (
        "        _build()\n"
        "        audit_controller = OperatorAuditController.new()\n"
        "        add_child(audit_controller)\n"
        "        audit_controller.setup(capability_panel)\n"
        "        _seed()\n"
    )
    main = main.replace(anchor, replacement, 1)

if "audit_controller.handle_input(event)" not in main:
    anchor = "func _unhandled_input(event: InputEvent) -> void:\n"
    if anchor not in main:
        raise SystemExit("Main _unhandled_input anchor not found")
    block = (
        anchor
        + "        if audit_controller != null and audit_controller.handle_input(event):\n"
        + "                get_viewport().set_input_as_handled()\n"
        + "                return\n\n"
    )
    main = main.replace(anchor, block, 1)

left_path.write_text(left, encoding="utf-8")
main_path.write_text(main, encoding="utf-8")
PY

echo
echo "OperatorShell capability panel installed."
echo "Created:"
echo "  $PANEL"
echo "  $CONTROLLER"
echo "Modified:"
echo "  $MAIN"
echo "  $LEFT"
echo "Backups:"
echo "  $MAIN.bak_$STAMP"
echo "  $LEFT.bak_$STAMP"
echo
grep -nE "OperatorAuditController|capability_panel|audit_controller" "$MAIN" || true
grep -nE "CapabilityPanel|capability_panel" "$LEFT" || true
