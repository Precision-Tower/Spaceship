extends Node
class_name OperatorShellAuditController

const AUDIT_SCRIPT_PATH := "res://audit/operator-shell-audit.sh"
const STATE_PATH := "res://audit/output/operator_shell_state.json"

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
