extends Node
class_name OperatorShellControlServer

const HOST := "127.0.0.1"
const PORT := 8767

var operator_shell
var server := TCPServer.new()
var clients: Array[StreamPeerTCP] = []
var buffers := {}

func _init(owner) -> void:
	operator_shell = owner


func _ready() -> void:
	var err := server.listen(PORT, HOST)
	if err != OK:
		push_warning(
			"Operator control server failed to listen on %s:%d: %s"
			% [HOST, PORT, error_string(err)]
		)
		return

	print("[OperatorShell] control server listening ", HOST, ":", PORT)


func _exit_tree() -> void:
	server.stop()


func _process(_delta: float) -> void:
	while server.is_connection_available():
		var peer := server.take_connection()
		if peer != null:
			clients.append(peer)
			buffers[peer] = ""

	for peer in clients.duplicate():
		if peer.get_status() != StreamPeerTCP.STATUS_CONNECTED:
			_drop_peer(peer)
			continue

		var available: int = peer.get_available_bytes()
		if available <= 0:
			continue

		var chunk: String = peer.get_utf8_string(available)
		buffers[peer] = str(buffers.get(peer, "")) + chunk

		if "\n" not in buffers[peer]:
			continue

		var command: String = str(buffers[peer]).get_slice("\n", 0).strip_edges()
		var response: String = _dispatch(command)

		peer.put_data((response + "\n").to_utf8_buffer())
		peer.disconnect_from_host()
		_drop_peer(peer)


func _drop_peer(peer: StreamPeerTCP) -> void:
	clients.erase(peer)
	buffers.erase(peer)


func _dispatch(command: String) -> String:
	print("[OperatorShell] ops ", command)

	var parts := command.split(" ", false)
	if parts.size() >= 2 and parts[0] in ["t", "lr", "rr"]:
		var region := parts[0]
		var arg := parts[1]
		if region == "t":
			if arg == "+":
				return _bool_result(operator_shell.operator_control_terminal_new(), "terminal created")
			if arg in ["l", "logs", "d", "diffs", "p", "packets", "t", "terminal"]:
				return _bool_result(operator_shell.operator_control_terminal_surface(arg), "terminal surface " + arg)
			if arg == "status":
				return "OK " + operator_shell.operator_control_terminal_status()
		else:
			if arg == "status":
				return "OK " + operator_shell.operator_control_region_status(region)
		return _bool_result(operator_shell.operator_control_region(region, arg), region + " " + arg)

	match command:
		"ping":
			return "OK pong"

		"home":
			return _workspace("Home")

		"workbench":
			return _workspace("Workbench")

		"internet":
			return _workspace("Internet")

		"chat":
			return _workspace("Chat 01")

		"next":
			return _cycle_workspace(1)

		"prev":
			return _cycle_workspace(-1)

		"surface.files":
			return _surface("files")

		"surface.editor":
			return _surface("editor")

		"surface.terminal":
			return _surface("terminal")

		"surface.controls":
			return _surface("controls")

		"editor.focus":
			return _bool_result(
				operator_shell.operator_control_editor_focus(),
				"editor focused"
			)

		"keyboard.show":
			return _bool_result(
				operator_shell.operator_control_keyboard_show(),
				"keyboard requested"
			)

		"keyboard.hide":
			DisplayServer.virtual_keyboard_hide()
			return "OK keyboard hidden"

		"files.refresh":
			return _bool_result(
				operator_shell.operator_control_files_refresh(),
				"files refreshed"
			)

		"status":
			return "OK " + operator_shell.operator_control_status()

		_:
			return "ERROR unsupported command: " + command


func _surface(name: String) -> String:
	return _bool_result(
		operator_shell.operator_control_surface(name),
		"surface " + name
	)


func _bool_result(ok: bool, message: String) -> String:
	return ("OK " if ok else "ERROR ") + message


func _workspace(name: String) -> String:
	return _bool_result(
		operator_shell.operator_control_workspace(name),
		"workspace " + name
	)


func _cycle_workspace(direction: int) -> String:
	return _bool_result(
		operator_shell.operator_control_workspace_cycle(direction),
		"workspace cycled"
	)
