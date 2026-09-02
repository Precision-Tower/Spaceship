extends Node

signal audit_started
signal audit_finished(state: Dictionary)
signal audit_failed(message: String)

const AUDIT_SCRIPT_PATH_WINDOWS := "res://Workbench/audit/capability-audit.ps1"
const AUDIT_SCRIPT_PATH_POSIX := "res://Workbench/audit/capability-audit.sh"
const AUDIT_STATE_PATH := "res://Workbench/audit/output/capability_state.json"

var shell
var session
var main
var audit_running := false


func setup(next_shell, next_session, next_main) -> void:
	shell = next_shell
	session = next_session
	main = next_main

	var initial_state := load_capability_state()

	if initial_state.get("ok", false):
		_refresh_left_panel(initial_state)


func handle_input(event: InputEvent) -> bool:
	if event is InputEventKey:
		if (
			event.pressed
			and not event.echo
			and event.ctrl_pressed
			and event.shift_pressed
			and event.keycode == KEY_A
		):
			if audit_running:
				print("[AuditController] Audit already running.")
				return true

			run_capability_audit()
			return true

	return false


func run_capability_audit() -> void:
	audit_running = true
	audit_started.emit()
	print("[AuditController] Running capability audit...")

	var ui_root := ProjectSettings.globalize_path("res://")
	var repo_root := _resolve_repo_root(ui_root)

	if repo_root.is_empty():
		_fail("Could not resolve Dashboard root from: %s" % ui_root)
		return

	var command_and_args := _audit_command(repo_root)
	var command := str(command_and_args.get("command", ""))
	var args: PackedStringArray = command_and_args.get("args", PackedStringArray())
	var script_path := str(command_and_args.get("script_path", ""))

	if command.is_empty() or script_path.is_empty():
		_fail("Could not resolve audit command for this platform.")
		return

	if not FileAccess.file_exists(script_path):
		_fail("Capability audit script does not exist: %s" % script_path)
		return

	var output: Array = []
	var exit_code := OS.execute(command, args, output, true, false)
	var console_output := "\n".join(output)

	if exit_code != 0:
		_fail("Audit failed with exit code %d.\n%s" % [exit_code, console_output])
		return

	var state := load_capability_state()

	if not state.get("ok", false):
		_fail(str(state.get("error", "Unknown state-loading error.")))
		return

	audit_running = false
	_refresh_left_panel(state)
	audit_finished.emit(state)

	print("[AuditController] Audit complete.")
	print("[AuditController] Summary: ", state.get("summary", {}))
	print("[AuditController] Current test: ", state.get("current_test", {}))


func load_capability_state() -> Dictionary:
	var state_path := ProjectSettings.globalize_path(AUDIT_STATE_PATH)

	if not FileAccess.file_exists(state_path):
		return {
			"ok": false,
			"error": "Capability state file does not exist: %s" % state_path
		}

	var file := FileAccess.open(state_path, FileAccess.READ)

	if file == null:
		return {
			"ok": false,
			"error": "Could not open capability state file: %s" % state_path
		}

	var text := file.get_as_text()
	if not text.is_empty() and text.unicode_at(0) == 0xFEFF:
		text = text.substr(1)

	var parsed = JSON.parse_string(text)

	if typeof(parsed) != TYPE_DICTIONARY:
		return {
			"ok": false,
			"error": "Capability state JSON did not parse into a dictionary."
		}

	var state: Dictionary = parsed
	state["ok"] = true
	return state


func _audit_command(repo_root: String) -> Dictionary:
	if OS.get_name() == "Windows":
		var windows_script_path := ProjectSettings.globalize_path(AUDIT_SCRIPT_PATH_WINDOWS)
		return {
			"command": "powershell.exe",
			"script_path": windows_script_path,
			"args": PackedStringArray([
				"-NoProfile",
				"-ExecutionPolicy",
				"Bypass",
				"-File",
				windows_script_path,
				"-RepoRoot",
				repo_root
			])
		}

	var posix_script_path := ProjectSettings.globalize_path(AUDIT_SCRIPT_PATH_POSIX)
	return {
		"command": "/bin/bash",
		"script_path": posix_script_path,
		"args": PackedStringArray([posix_script_path, repo_root])
	}


func _refresh_left_panel(state: Dictionary) -> void:
	if shell == null:
		return

	if shell.left_panel == null:
		push_warning("[AuditController] Left panel is not available.")
		return

	if shell.left_panel.has_method("load_capability_state"):
		shell.left_panel.load_capability_state(state)


func _resolve_repo_root(ui_root: String) -> String:
	var normalized := ui_root.trim_suffix("/").trim_suffix("\\")
	var repo_candidate := normalized.get_base_dir()

	if FileAccess.file_exists(repo_candidate.path_join("run.py")):
		return repo_candidate

	var fallback_candidate := repo_candidate.get_base_dir()

	if FileAccess.file_exists(fallback_candidate.path_join("run.py")):
		return fallback_candidate

	return ""


func _fail(message: String) -> void:
	audit_running = false
	audit_failed.emit(message)
	push_error("[AuditController] %s" % message)
