extends Node
class_name OperatorShellModelServerController

signal status_changed(payload: Dictionary)
signal command_completed(action: String, payload: Dictionary)

const PYTHON := "/home/spaztic/miniconda3/envs/weebo_env/bin/python"
const MANAGER_RELATIVE := "Agency/Core/runtime/model_server_manager.py"
const POLL_INTERVAL_SECONDS := 2.0
const COMMAND_TIMEOUT_SECONDS := 130.0

var current_status: Dictionary = {}
var _thread: Thread
var _thread_action := ""
var _thread_started_msec := 0
var _poll_elapsed := 0.0
var _timeout_reported := false

func setup() -> void:
	set_process(true)
	_request_status(true)

func start_server() -> void:
	if _is_transitioning():
		return
	_emit_local_state("starting", "loading model")
	_begin_command("start")

func stop_server() -> void:
	if _is_transitioning():
		return
	_emit_local_state("stopping", "shutting down")
	_begin_command("stop")

func refresh_now() -> void:
	_request_status(true)

func can_toggle() -> bool:
	return not _is_transitioning()

func _process(delta: float) -> void:
	_complete_thread_if_ready()
	if _thread != null:
		_check_command_timeout()
		return
	_poll_elapsed += delta
	if _poll_elapsed >= POLL_INTERVAL_SECONDS:
		_request_status(false)

func _is_transitioning() -> bool:
	if _thread != null:
		return true
	var status := str(current_status.get("status", ""))
	return status == "starting" or status == "stopping"

func _request_status(force := false) -> void:
	if _thread != null:
		return
	if not force and _is_transitioning():
		return
	_begin_command("status")

func _begin_command(action: String) -> void:
	if _thread != null:
		return
	_poll_elapsed = 0.0
	_timeout_reported = false
	_thread_action = action
	_thread_started_msec = Time.get_ticks_msec()
	_thread = Thread.new()
	var err := _thread.start(Callable(self, "_run_manager_command").bind(action))
	if err != OK:
		_thread = null
		_emit_error("failed to start model-server manager thread: %s" % str(err))

func _run_manager_command(action: String) -> Dictionary:
	var output: Array = []
	var exit_code := OS.execute(
		PYTHON,
		PackedStringArray([_manager_script_path(), action]),
		output,
		true,
		false
	)
	return {
		"action": action,
		"exit_code": exit_code,
		"output": "\n".join(output)
	}

func _complete_thread_if_ready() -> void:
	if _thread == null:
		return
	if _thread.is_alive():
		return
	var result: Dictionary = _thread.wait_to_finish()
	_thread = null
	_timeout_reported = false
	var payload := _payload_from_result(result)
	current_status = payload
	status_changed.emit(payload)
	command_completed.emit(str(result.get("action", "")), payload)
	print("[ModelServer] action=%s exit=%s status=%s reason=%s" % [
		str(result.get("action", "")),
		str(result.get("exit_code", "")),
		str(payload.get("status", "unknown")),
		str(payload.get("reason", ""))
	])

func _payload_from_result(result: Dictionary) -> Dictionary:
	var raw := str(result.get("output", "")).strip_edges()
	var parsed = JSON.parse_string(raw)
	var payload: Dictionary = {}
	if typeof(parsed) == TYPE_DICTIONARY:
		payload = parsed
	else:
		payload = _default_payload()
		payload["status"] = "error"
		payload["reason"] = "manager did not return JSON: " + raw.left(500)
	payload["manager_exit_code"] = int(result.get("exit_code", -1))
	payload["manager_action"] = str(result.get("action", ""))
	if int(payload.get("manager_exit_code", 0)) != 0 and str(payload.get("status", "")) != "error":
		payload["status"] = "error"
		if str(payload.get("reason", "")).is_empty():
			payload["reason"] = "manager exited nonzero"
	return payload

func _check_command_timeout() -> void:
	if _timeout_reported:
		return
	var elapsed := float(Time.get_ticks_msec() - _thread_started_msec) / 1000.0
	if elapsed < COMMAND_TIMEOUT_SECONDS:
		return
	_timeout_reported = true
	_emit_error("model-server manager command timed out: %s" % _thread_action)

func _emit_local_state(status: String, reason: String) -> void:
	var payload := current_status.duplicate(true) if not current_status.is_empty() else _default_payload()
	payload["status"] = status
	payload["reason"] = reason
	current_status = payload
	status_changed.emit(payload)
	print("[ModelServer] %s" % reason)

func _emit_error(reason: String) -> void:
	var payload := current_status.duplicate(true) if not current_status.is_empty() else _default_payload()
	payload["status"] = "error"
	payload["reason"] = reason
	current_status = payload
	status_changed.emit(payload)
	push_error("[ModelServer] %s" % reason)

func _default_payload() -> Dictionary:
	return {
		"status": "stopped",
		"configured": false,
		"healthy": false,
		"pid": null,
		"endpoint": "http://127.0.0.1:8081",
		"model_filename": "Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf",
		"model_path": "/home/spaztic/Core/Dashboard/local/Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf",
		"server_path": "/home/spaztic/Core/tools/llama.cpp-cuda/build/bin/llama-server",
		"log_path": "/home/spaztic/Core/Dashboard/Agency/Agents/Editor/runtime/logs/llama-server.log",
		"reason": "status not loaded yet"
	}

func _manager_script_path() -> String:
	var ui_root := ProjectSettings.globalize_path("res://")
	ui_root = ui_root.trim_suffix("/").trim_suffix("\\")
	var repo_root := ui_root.get_base_dir()
	return repo_root.path_join(MANAGER_RELATIVE)
