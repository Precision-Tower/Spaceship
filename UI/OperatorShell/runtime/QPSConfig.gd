extends RefCounted
class_name OperatorShellQPSConfig

const QPS_EXECUTABLE := "qps/cpp/build/qps"
const OPERATOR_SHELL_DOCUMENT := "UI/OperatorShell/_index.qps"

var dashboard_root: String


func _init(root: String) -> void:
	dashboard_root = root.simplify_path()


func apply(config) -> bool:
	if config == null:
		push_warning("QPSConfig received null OperatorShell config")
		return false

	var density := get_value("terminal.density")

	if density == "":
		push_warning("OperatorShell.qps does not define terminal.density")
		return false

	if density not in ["comfortable", "compact", "dense"]:
		push_warning("Invalid OperatorShell QPS terminal density: " + density)
		return false

	config.terminal_density = density

	print(
		"[OperatorShell] QPS applied terminal.density = ",
		density
	)

	return true


func get_value(path: String) -> String:
	var executable := dashboard_root.path_join(QPS_EXECUTABLE)
	var document := dashboard_root.path_join(OPERATOR_SHELL_DOCUMENT)

	if not FileAccess.file_exists(executable):
		push_warning("QPS runtime missing: " + executable)
		return ""

	if not FileAccess.file_exists(document):
		push_warning("OperatorShell QPS document missing: " + document)
		return ""

	var output: Array = []

	var exit_code := OS.execute(
		executable,
		[
			document,
			"--get",
			path
		],
		output,
		true,
		false
	)

	if exit_code != 0:
		push_warning(
			"QPS query failed for " +
			path +
			":\n" +
			"\n".join(output)
		)
		return ""

	var value := ""

	for part in output:
		value += str(part)

	return value.strip_edges()
