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

	match command:
		"ping":
			return "OK pong"

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
