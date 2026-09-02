extends RefCounted
class_name OperatorShellTerminalServiceClient

const DEFAULT_HOST := "127.0.0.1"
const DEFAULT_PORT := 8765
const CONNECT_TIMEOUT_MS := 450
const RESPONSE_TIMEOUT_MS := 900

static func ping() -> Dictionary:
	return request({"action": "ping"})

static func create_session(cols: int, rows: int) -> Dictionary:
	return request({
		"action": "create_session",
		"cols": cols,
		"rows": rows
	})

static func write_input(session_id: String, text: String) -> Dictionary:
	return request({
		"action": "write_input",
		"session_id": session_id,
		"input": text
	})

static func read_output(session_id: String) -> Dictionary:
	return request({
		"action": "read_output",
		"session_id": session_id
	})

static func resize_session(session_id: String, cols: int, rows: int) -> Dictionary:
	return request({
		"action": "resize_session",
		"session_id": session_id,
		"cols": cols,
		"rows": rows
	})

static func close_session(session_id: String) -> Dictionary:
	return request({
		"action": "close_session",
		"session_id": session_id
	})

static func list_sessions() -> Dictionary:
	return request({"action": "list_sessions"})

static func request(payload: Dictionary) -> Dictionary:
	var peer := StreamPeerTCP.new()
	var err := peer.connect_to_host(_host(), _port())
	if err != OK:
		return _error("connect_to_host failed: %d" % err)

	var deadline := Time.get_ticks_msec() + CONNECT_TIMEOUT_MS
	while peer.get_status() == StreamPeerTCP.STATUS_CONNECTING and Time.get_ticks_msec() < deadline:
		peer.poll()
		OS.delay_msec(10)

	if peer.get_status() != StreamPeerTCP.STATUS_CONNECTED:
		var status := peer.get_status()
		peer.disconnect_from_host()
		return _error("PTY service unavailable at %s:%d (status %d)" % [_host(), _port(), status])

	var line := JSON.stringify(payload) + "\n"
	err = peer.put_data(line.to_utf8_buffer())
	if err != OK:
		peer.disconnect_from_host()
		return _error("PTY request write failed: %d" % err)

	var response := ""
	deadline = Time.get_ticks_msec() + RESPONSE_TIMEOUT_MS
	while Time.get_ticks_msec() < deadline:
		peer.poll()
		var available := peer.get_available_bytes()
		if available > 0:
			var read_result := peer.get_data(available)
			if int(read_result[0]) != OK:
				peer.disconnect_from_host()
				return _error("PTY response read failed: %d" % int(read_result[0]))
			response += read_result[1].get_string_from_utf8()
			if response.find("\n") != -1:
				break
		OS.delay_msec(10)

	peer.disconnect_from_host()
	if response == "":
		return _error("PTY service response timed out")

	var first_line := response.get_slice("\n", 0).strip_edges()
	var parsed = JSON.parse_string(first_line)
	if typeof(parsed) != TYPE_DICTIONARY:
		return _error("PTY service returned non-JSON response: " + first_line)
	return parsed

static func _host() -> String:
	if OS.has_environment("OPERATOR_PTY_HOST"):
		var configured := OS.get_environment("OPERATOR_PTY_HOST").strip_edges()
		if configured != "":
			return configured
	return DEFAULT_HOST

static func _port() -> int:
	if OS.has_environment("OPERATOR_PTY_PORT"):
		var configured := OS.get_environment("OPERATOR_PTY_PORT").strip_edges()
		if configured.is_valid_int():
			return int(configured)
	return DEFAULT_PORT

static func _error(message: String) -> Dictionary:
	return {
		"ok": false,
		"error": message
	}
