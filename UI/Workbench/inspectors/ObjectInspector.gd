extends RefCounted

class_name ObjectInspector


func render_selection(selection: Dictionary) -> String:
	if selection.is_empty():
		return "[color=#949da6]No object selected[/color]"

	var node_kind := str(selection.get("node_kind", "object"))
	match node_kind:
		"object":
			return render_object(selection)
		"source_packet":
			return render_source_packet(selection)
		"project", "group":
			return render_group(selection)
		_:
			return render_group(selection)


func render_object(selection: Dictionary) -> String:
	var object_data: Dictionary = selection.get("raw_data", selection)
	var lines := PackedStringArray()

	var object_id: String = str(object_data.get("object_id", selection.get("object_id", "missing")))
	var object_type: String = str(object_data.get("object_type", "missing"))

	if object_type == "fluid_environment":
		return render_environment_object(selection)

	var role := str(object_data.get("role", ""))
	var assembly_group := str(object_data.get("assembly_group", ""))
	var subsystem := str(object_data.get("subsystem", ""))

	lines.append("[color=#ffffff][b]" + object_id + "[/b][/color]")

	var descriptor := object_type
	if role != "" and role != "missing":
		descriptor += " · " + role

	lines.append("[color=#949da6]" + descriptor + "[/color]")

	if assembly_group != "" or subsystem != "":
		lines.append(
			"[color=#7f8c99]" +
			assembly_group +
			" / " +
			subsystem +
			"[/color]"
		)

	_append_section(lines, "Placement")
	_append_field(lines, "position_m", object_data.get("position_m", "missing"))
	if object_data.has("render"):
		var render: Dictionary = object_data.get("render", {})
		if render.has("rotation_degrees"):
			_append_field(lines, "rotation_degrees", render.get("rotation_degrees"))

	_append_primitive_section(lines, object_data)

	_append_section(lines, "Engineering")
	_append_field(lines, "mass_kg", object_data.get("mass_kg", "missing"))
	_append_field(lines, "volume_m3", object_data.get("volume_m3", "missing"))
	_append_field(lines, "material", object_data.get("material", "missing"))
	_append_field(lines, "contributes_weight", object_data.get("contributes_weight", "missing"))
	_append_field(lines, "contributes_buoyancy", object_data.get("contributes_buoyancy", "missing"))

	_append_section(lines, "Render")
	_append_field(lines, "render", object_data.get("render", "missing"))

	_append_section(lines, "Packet Links")
	_append_field(lines, "packet_links", object_data.get("packet_links", []))

	return "\n\n".join(lines)

func render_environment_object(selection: Dictionary) -> String:
	var object_data: Dictionary = selection.get("raw_data", selection)
	var lines := PackedStringArray()

	var object_id: String = str(object_data.get("object_id", selection.get("object_id", "missing")))
	var object_type: String = str(object_data.get("object_type", "fluid_environment"))

	lines.append("[color=#ffffff][b]" + object_id + "[/b][/color]")
	lines.append("[color=#949da6]" + object_type + "[/color]")

	_append_section(lines, "Environment")
	_append_field(lines, "object_id", object_id)
	_append_field(lines, "object_type", object_type)
	_append_field(lines, "role", object_data.get("role", "missing"))
	_append_field(lines, "visibility", _visibility_label(selection.get("visible", true)))

	_append_section(lines, "Packet Links")
	_append_field(lines, "packet_links", object_data.get("packet_links", []))

	return "\n\n".join(lines)

func render_group(selection: Dictionary) -> String:
	var lines := PackedStringArray()
	var node_kind := str(selection.get("node_kind", "group"))
	var display_type := node_kind
	if node_kind == "project":
		display_type = "project"

	_append_field(lines, "id", selection.get("id", "missing"))
	_append_field(lines, "type", display_type)
	_append_field(lines, "visibility", _visibility_label(selection.get("visible", true)))
	_append_field(lines, "role", selection.get("role", "missing"))
	_append_field(lines, "parent_group", selection.get("parent_group", "missing"))
	_append_field(lines, "object_count", selection.get("object_count", 0))
	_append_field(lines, "total_mass_kg", selection.get("total_mass_kg", "missing"))
	_append_field(lines, "child groups", selection.get("child_groups", []))
	_append_field(lines, "child objects", selection.get("child_objects", []))

	return "\n\n".join(lines)


func render_source_packet(selection: Dictionary) -> String:
	var raw_data: Dictionary = selection.get("raw_data", {})
	var lines := PackedStringArray()

	_append_field(lines, "id", selection.get("id", "missing"))
	_append_field(lines, "type", "source_packet")
	_append_field(lines, "visibility", _visibility_label(selection.get("visible", true)))
	_append_field(lines, "role", selection.get("role", raw_data.get("packet_type", "missing")))
	_append_field(lines, "parent_group", selection.get("parent_group", "Source Packets"))
	_append_field(lines, "object_count", selection.get("object_count", _packet_object_count(raw_data)))
	_append_field(lines, "total_mass_kg", selection.get("total_mass_kg", _packet_total_mass(raw_data)))
	_append_field(lines, "packet_path", selection.get("packet_path", raw_data.get("packet_path", "missing")))
	_append_field(lines, "resolved_packet_path", selection.get("resolved_packet_path", raw_data.get("_resolved_packet_path", "missing")))
	_append_field(lines, "packet_type", raw_data.get("packet_type", selection.get("id", "missing")))
	_append_field(lines, "evidence_state", raw_data.get("evidence_state", "missing"))

	return "\n\n".join(lines)

func _append_primitive_section(lines: PackedStringArray, object_data: Dictionary) -> void:
	_append_section(lines, "Physical Primitive")

	var primitive := str(object_data.get("physical_primitive", "missing"))
	_append_field(lines, "primitive", primitive)

	match primitive:
		"barrel":
			var barrel: Dictionary = object_data.get("barrel", {})
			_append_field(lines, "radius_m", barrel.get("radius_m", "missing"))
			_append_field(lines, "height_m", barrel.get("height_m", "missing"))
			_append_field(lines, "sealed", barrel.get("sealed", "missing"))
			_append_field(lines, "fill_state", barrel.get("fill_state", "missing"))
			_append_field(lines, "external_volume_m3", barrel.get("external_volume_m3", "missing"))

		"pipe":
			var dimensions: Dictionary = object_data.get("dimensions_m", {})
			_append_field(lines, "length_m", dimensions.get("length", "missing"))
			_append_field(lines, "outer_radius_m", dimensions.get("outer_radius", dimensions.get("radius", "missing")))
			_append_field(lines, "inner_radius_m", dimensions.get("inner_radius", "missing"))
			_append_field(lines, "wall_thickness_m", dimensions.get("wall_thickness", "missing"))

			if object_data.has("pipe"):
				_append_field(lines, "pipe", object_data.get("pipe", {}))

		"block":
			var dimensions: Dictionary = object_data.get("dimensions_m", {})
			_append_field(lines, "x_m", dimensions.get("x", "missing"))
			_append_field(lines, "y_m", dimensions.get("y", "missing"))
			_append_field(lines, "z_m", dimensions.get("z", "missing"))

			if object_data.has("block"):
				_append_field(lines, "block", object_data.get("block", {}))

		"plate":
			var plate: Dictionary = object_data.get("plate", {})
			_append_field(lines, "length_m", plate.get("length_m", "missing"))
			_append_field(lines, "width_m", plate.get("width_m", "missing"))
			_append_field(lines, "thickness_m", plate.get("thickness_m", "missing"))

		_:
			_append_field(lines, "dimensions_m", object_data.get("dimensions_m", "missing"))

func _append_field(lines: PackedStringArray, label: String, value: Variant) -> void:
	lines.append(
		"[color=#e1e6eb]" +
		label +
		"[/color]: " +
		_format_value(value)
	)

func _append_section(lines: PackedStringArray, title: String) -> void:
	lines.append("[color=#7fb4ff][b]" + title + "[/b][/color]")

func _visibility_label(visible: Variant) -> String:
	return "visible" if bool(visible) else "hidden"


func _format_value(value: Variant) -> String:
	if value == null:
		return "null"

	if value is Vector3:
		return _format_vector3(value)

	match typeof(value):
		TYPE_BOOL:
			return "true" if bool(value) else "false"
		TYPE_INT, TYPE_FLOAT:
			return str(value)
		TYPE_STRING, TYPE_STRING_NAME, TYPE_NODE_PATH:
			var text := str(value)
			return "missing" if text == "" else text
		TYPE_DICTIONARY:
			return _format_dictionary(value as Dictionary)
		TYPE_ARRAY, TYPE_PACKED_STRING_ARRAY:
			return _format_array(value)
		_:
			return str(value)


func _format_vector3(value: Vector3) -> String:
	return "(%s, %s, %s)" % [value.x, value.y, value.z]


func _format_dictionary(value: Dictionary) -> String:
	if value.is_empty():
		return "{}"

	var parts := PackedStringArray()
	for key in value.keys():
		parts.append(str(key) + ": " + _format_value(value[key]))

	return "{ " + ", ".join(parts) + " }"


func _format_array(value: Variant) -> String:
	var array_value: Array = []
	if value is PackedStringArray:
		for entry in value:
			array_value.append(entry)
	elif value is Array:
		array_value = value

	if array_value.is_empty():
		return "none"

	var parts := PackedStringArray()
	for entry in array_value:
		parts.append("- " + _format_value(entry))

	return "\n".join(parts)


func _packet_object_count(packet: Dictionary) -> int:
	var assembly: Dictionary = packet.get("assembly", {})
	var objects: Array = assembly.get("objects", [])
	return objects.size()


func _packet_total_mass(packet: Dictionary) -> Variant:
	var assembly: Dictionary = packet.get("assembly", {})
	var summary: Dictionary = assembly.get("summary", {})
	if summary.has("total_mass_kg"):
		return summary.get("total_mass_kg")

	var total := 0.0
	var found_mass := false
	var objects: Array = assembly.get("objects", [])
	for object in objects:
		if object is Dictionary and object.has("mass_kg"):
			total += float(object.get("mass_kg", 0.0))
			found_mass = true

	return total if found_mass else "missing"
