extends RefCounted
class_name CliBridge

static func ui_root() -> String:
	return ProjectSettings.globalize_path("res://").trim_suffix("/").trim_suffix("\\")

static func dashboard_root() -> String:
	return ui_root().get_base_dir()

static func core_root() -> String:
	return dashboard_root().get_base_dir()

static func cali_observe_directory() -> Dictionary:
	return run_cli("cali-observe-directory", ["--max-new-tokens", "1", "--timeout-seconds", "120"])
	
static func propose_task_packet(intent: String) -> Dictionary:
	return run_cli("propose-task-packet", ["--intent", intent])

static func propose_diff(intent: String, scope: String) -> Dictionary:
	return run_cli("propose-diff", ["--intent", intent, "--scope", scope])

static func default_engineering_root() -> String:
	return core_root().path_join("Engineering")

static func cli_path() -> String:
	return ui_root().path_join("scripts/cli/dashboard_cli.py")

static func debug_paths() -> String:
	return "ui_root: " + ui_root() + "\n" + \
		"dashboard_root: " + dashboard_root() + "\n" + \
		"core_root: " + core_root() + "\n" + \
		"engineering_root: " + default_engineering_root() + "\n" + \
		"cli_path: " + cli_path()

static func with_root(root: String) -> Array[String]:
	return ["--root", root]

static func runtime_state() -> Dictionary:
	return run_cli("runtime-state", with_root(core_root()))

static func test_all() -> Dictionary:
	return run_cli("test-all", with_root(core_root()))

static func scan_core() -> Dictionary:
	return run_cli("scan-repo", with_root(core_root()))

static func git_status_core() -> Dictionary:
	return run_cli("git-status", with_root(core_root()))

static func propose_directory_diff_core() -> Dictionary:
	return run_cli("propose-directory-diff", with_root(core_root()))

static func view_latest_diff() -> Dictionary:
	return run_cli("view-latest-diff", [])

static func grant_review_latest_diff() -> Dictionary:
	return run_cli("grant-review-latest-diff", [])

static func clear_latest_diff() -> Dictionary:
	return run_cli("clear-latest-diff", [])

static func list_packets() -> Dictionary:
	return run_cli("list-packets", [])

static func create_packet_stub() -> Dictionary:
	return run_cli("create-packet", ["--category", "topology", "--title", "ui_packet_stub"])

static func run_cli(command: String, extra_args: Array[String] = []) -> Dictionary:
	var args: Array[String] = [cli_path(), command]
	for a in extra_args:
		args.append(a)
	var output: Array = []
	var exit_code := OS.execute(_python_command(), args, output, true, false)
	var stdout := ""
	for line in output:
		stdout += str(line)
	return {
		"ok": exit_code == 0,
		"exit_code": exit_code,
		"command": command,
		"python": _python_command(),
		"args": args,
		"stdout": stdout,
		"debug_paths": debug_paths()
	}

static func scan_repo(root: String = "") -> Dictionary:
	var args: Array[String] = []
	if root != "":
		args.append("--root")
		args.append(root)
	return run_cli("scan-repo", args)

static func git_status(root: String = "") -> Dictionary:
	var args: Array[String] = []
	if root != "":
		args.append("--root")
		args.append(root)
	return run_cli("git-status", args)

static func _python_command() -> String:
	if OS.has_environment("DASHBOARD_PYTHON"):
		var configured := OS.get_environment("DASHBOARD_PYTHON").strip_edges()
		if configured != "":
			return configured
	if OS.get_name() == "Windows":
		var user_profile := OS.get_environment("USERPROFILE").strip_edges()
		if user_profile != "":
			var cali_python := user_profile.path_join("miniconda3/envs/cali-model/python.exe")
			if FileAccess.file_exists(cali_python):
				return cali_python
	if OS.get_name() == "Windows":
		return "py"
	return "python3"
