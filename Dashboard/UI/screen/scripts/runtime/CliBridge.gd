extends RefCounted
class_name CliBridge

static func ui_root() -> String:
	return ProjectSettings.globalize_path("res://").trim_suffix("/").trim_suffix("\\")

static func dashboard_root() -> String:
	return ui_root().get_base_dir()

static func core_root() -> String:
	return dashboard_root().get_base_dir()

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
	return "python"
