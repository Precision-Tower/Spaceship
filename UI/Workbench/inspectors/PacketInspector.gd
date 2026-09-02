extends RefCounted
class_name PacketInspector


func render_packet(selected_object: Dictionary, packet: Dictionary) -> String:
	if packet.get("error", false):
		return _render_error(packet)

	var packet_type := str(packet.get("packet_type", "unknown_packet"))

	match packet_type:
		"barrel_candidate_packet":
			return _render_barrel_candidate_packet(selected_object, packet)
		_:
			return _render_unknown_packet(packet)


func _render_barrel_candidate_packet(_selected_object: Dictionary, packet: Dictionary) -> String:
	var barrel: Dictionary = packet.get("barrel", {}) as Dictionary
	var material: Dictionary = barrel.get("material", {}) as Dictionary
	var geometry: Dictionary = barrel.get("geometry", {}) as Dictionary
	var volumes: Dictionary = barrel.get("volumes", {}) as Dictionary
	var mass: Dictionary = barrel.get("mass", {}) as Dictionary

	var lines := PackedStringArray()
	lines.append("")
	lines.append("[color=#e1e6eb]Engineering Packet[/color]")
	lines.append("packet_type: " + str(packet.get("packet_type", "missing")))
	lines.append("evidence_state: " + str(packet.get("evidence_state", "missing")))
	lines.append("")
	lines.append("[color=#e1e6eb]Material[/color]")
	_append_value(lines, material, "material_id")
	_append_value(lines, material, "density_kg_m3")
	lines.append("")
	lines.append("[color=#e1e6eb]Geometry[/color]")
	_append_value(lines, geometry, "shape")
	_append_value(lines, geometry, "outer_radius_m")
	_append_value(lines, geometry, "inner_radius_m")
	_append_value(lines, geometry, "height_m")
	_append_value(lines, geometry, "wall_thickness_m")
	lines.append("")
	lines.append("[color=#e1e6eb]Volumes[/color]")
	_append_value(lines, volumes, "external_volume_m3")
	_append_value(lines, volumes, "internal_volume_m3")
	_append_value(lines, volumes, "shell_volume_m3")
	_append_value(lines, volumes, "flooded_volume_m3")
	lines.append("")
	lines.append("[color=#e1e6eb]Mass[/color]")
	_append_value(lines, mass, "declared_mass_kg")
	_append_value(lines, mass, "estimated_shell_mass_kg")
	_append_value(lines, mass, "mass_difference_kg")
	_append_value(lines, mass, "mass_source")
	lines.append("")
	lines.append("[color=#e1e6eb]Unresolved Variables[/color]")
	_append_list(lines, barrel.get("unresolved_variables", []))
	lines.append("")
	lines.append("[color=#e1e6eb]Blocked Interpretations[/color]")
	_append_list(lines, barrel.get("blocked_interpretations", []))

	var prohibited: Variant = packet.get("prohibited_interpretations", [])
	if typeof(prohibited) == TYPE_ARRAY and not (prohibited as Array).is_empty():
		lines.append("")
		lines.append("[color=#e1e6eb]Packet Prohibited Interpretations[/color]")
		_append_list(lines, prohibited)

	return "\n".join(lines)


func _render_unknown_packet(packet: Dictionary) -> String:
	var lines := PackedStringArray()
	lines.append("")
	lines.append("[color=#e1e6eb]Engineering Packet[/color]")
	lines.append("packet_type: " + str(packet.get("packet_type", "unknown_packet")))
	lines.append("evidence_state: " + str(packet.get("evidence_state", "missing")))
	lines.append("status: no specialized inspector")
	return "\n".join(lines)


func _render_error(packet: Dictionary) -> String:
	var lines := PackedStringArray()
	lines.append("")
	lines.append("[color=#e1e6eb]Engineering Packet[/color]")
	lines.append("packet_error: " + str(packet.get("error_type", "packet_error")))
	lines.append(str(packet.get("message", "Packet could not be loaded.")))
	return "\n".join(lines)


func _append_value(lines: PackedStringArray, data: Dictionary, key: String) -> void:
	lines.append(key + ": " + str(data.get(key, "missing")))


func _append_list(lines: PackedStringArray, value: Variant) -> void:
	if typeof(value) != TYPE_ARRAY:
		lines.append("- missing")
		return

	var items := value as Array
	if items.is_empty():
		lines.append("- none")
		return

	for item: Variant in items:
		lines.append("- " + str(item))
