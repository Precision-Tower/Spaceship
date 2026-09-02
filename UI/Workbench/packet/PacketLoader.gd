extends RefCounted
class_name PacketLoader


func load_packet(packet_path: String) -> Dictionary:
	var resolved_path := _resolve_path(packet_path)

	if resolved_path == "":
		return _error("packet_path_empty", packet_path, "Packet path is empty.")

	if not FileAccess.file_exists(resolved_path):
		return _error(
			"packet_file_missing",
			packet_path,
			"Packet file not found: " + resolved_path
		)

	var file := FileAccess.open(resolved_path, FileAccess.READ)
	if file == null:
		return _error(
			"packet_file_unreadable",
			packet_path,
			"Packet file could not be opened: " + resolved_path
		)

	var text := file.get_as_text()
	file.close()

	var json := JSON.new()
	var parse_error := json.parse(text)
	if parse_error != OK:
		return _error(
			"packet_json_invalid",
			packet_path,
			"Packet JSON invalid at line " + str(json.get_error_line()) + ": " + json.get_error_message()
		)

	var data: Variant = json.data
	if typeof(data) != TYPE_DICTIONARY:
		return _error(
			"packet_json_not_dictionary",
			packet_path,
			"Packet JSON root must be an object."
		)

	var packet := data as Dictionary
	packet["_resolved_packet_path"] = resolved_path
	return packet


func _resolve_path(packet_path: String) -> String:
	var trimmed := packet_path.strip_edges()
	if trimmed == "":
		return ""

	if trimmed.begins_with("res://") or trimmed.begins_with("user://"):
		return ProjectSettings.globalize_path(trimmed)

	if trimmed.length() >= 3 and trimmed.substr(1, 1) == ":":
		return trimmed

	if trimmed.begins_with("/") or trimmed.begins_with("\\"):
		return trimmed

	return ProjectSettings.globalize_path("res://" + trimmed)


func _error(error_type: String, packet_path: String, message: String) -> Dictionary:
	return {
		"error": true,
		"error_type": error_type,
		"packet_path": packet_path,
		"message": message
	}
