extends RefCounted
class_name ViewportObjectRenderer

var _shell
var _object_nodes_by_id: Dictionary = {}
var _default_materials_by_id: Dictionary = {}
var _highlight_material_cache: StandardMaterial3D


func setup(shell) -> void:
	_shell = shell


func render_project_objects() -> void:
	var root := _project_objects_root()
	if root == null:
		return

	for child: Node in root.get_children():
		root.remove_child(child)
		child.queue_free()

	_set_shell_environment_node(null)
	_object_nodes_by_id.clear()
	_default_materials_by_id.clear()
	_clear_shell_render_state()

	var session = _session()
	if session == null or session.current_project == null:
		_sync_shell_object_maps()
		return

	var all_objects: Array[Dictionary] = session.get_objects()

	var environment_packet := {}
	for object: Dictionary in all_objects:
		if str(object.get("object_type", "")) == "fluid_environment":
			var packet := _first_packet_for_object(object)
			if not packet.is_empty():
				environment_packet = packet
				break

	var geometry_renderer = _geometry_renderer()
	if geometry_renderer != null and not environment_packet.is_empty():
		var environment_node: Node3D = geometry_renderer.create_environment_node(environment_packet)
		_set_shell_environment_node(environment_node)
		if environment_node != null:
			root.add_child(environment_node)

	for object: Dictionary in all_objects:
		if str(object.get("object_type", "")) == "fluid_environment":
			continue

		var node := _create_viewport_node(object)
		if node == null:
			continue

		root.add_child(node)
		_add_port_markers(root, object)

	_sync_shell_object_maps()


func object_nodes() -> Dictionary:
	return _object_nodes_by_id


func default_materials() -> Dictionary:
	return _default_materials_by_id


func _create_viewport_node(object: Dictionary) -> Node3D:
	var geometry_renderer = _geometry_renderer()
	if geometry_renderer == null:
		return null

	var packet := _first_packet_for_object(object)
	_capture_simulation_frames(object, packet)

	var node: Node3D = geometry_renderer.create_node(object, packet)
	if node == null:
		return null

	var object_id := str(object.get("object_id", ""))
	if object_id != "":
		_object_nodes_by_id[object_id] = node

	if node is MeshInstance3D:
		_default_materials_by_id[object_id] = (node as MeshInstance3D).material_override

	return node


func _capture_simulation_frames(object_data: Dictionary, packet: Dictionary) -> void:
	if _shell != null and _shell.get_meta("main") != null:
		var main = _shell.get_meta("main")
		if main.simulation_playback_controller != null:
			main.simulation_playback_controller.capture_simulation_frames(object_data, packet)


func _add_port_markers(parent_node: Node3D, object_data: Dictionary) -> void:
	var ports: Array = object_data.get("ports", [])
	if ports.is_empty():
		return

	for port in ports:
		if not port is Dictionary:
			continue

		var port_data := port as Dictionary
		var position := _vector3_from_value(port_data.get("position_m", {}))
		var object_id := str(object_data.get("object_id", "missing"))
		var port_id := str(port_data.get("port_id", "missing"))

		var body := StaticBody3D.new()
		body.name = "Port_%s_%s" % [object_id, port_id]
		body.position = position

		body.set_meta("selection", {
			"node_kind": "port",
			"object_id": object_id,
			"port_id": port_id,
			"id": "%s.%s" % [object_id, port_id],
			"raw_data": port_data,
			"parent_object": object_data,
			"visible": true
		})

		var marker := MeshInstance3D.new()
		marker.name = "PortMarker"

		var sphere := SphereMesh.new()
		sphere.radius = 0.035
		sphere.height = 0.07
		marker.mesh = sphere

		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color(1.0, 0.8, 0.1, 0.85)
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		marker.material_override = mat

		body.add_child(marker)

		var collision := CollisionShape3D.new()
		collision.name = "PortCollision"

		var shape := SphereShape3D.new()
		shape.radius = 0.06
		collision.shape = shape

		body.add_child(collision)
		parent_node.add_child(body)


func _first_packet_for_object(object_data: Dictionary) -> Dictionary:
	var packet_loader = _packet_loader()
	if packet_loader == null:
		return {}

	var links: Array = object_data.get("packet_links", [])
	for link in links:
		if not link is Dictionary:
			continue

		var packet_path := str(link.get("packet_path", ""))
		if packet_path == "":
			continue

		var packet: Dictionary = packet_loader.load_packet(packet_path)
		if not packet.is_empty():
			return packet

	return {}


func _default_material_for(object: Dictionary) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()

	match str(object.get("object_type", "")):
		"boat_hull":
			material.albedo_color = Color(0.42, 0.28, 0.16, 1.0)
		"barrel":
			material.albedo_color = Color(0.12, 0.38, 0.78, 1.0)
		"payload":
			material.albedo_color = Color(0.75, 0.68, 0.22, 1.0)
		_:
			material.albedo_color = Color(0.45, 0.5, 0.55, 1.0)

	return material


func _highlight_material() -> StandardMaterial3D:
	if _highlight_material_cache == null:
		_highlight_material_cache = StandardMaterial3D.new()
		_highlight_material_cache.albedo_color = Color(1.0, 0.82, 0.24, 1.0)
		_highlight_material_cache.emission_enabled = true
		_highlight_material_cache.emission = Color(1.0, 0.58, 0.08, 1.0)
		_highlight_material_cache.emission_energy_multiplier = 0.35

	return _highlight_material_cache


func _clear_shell_render_state() -> void:
	_object_nodes_by_id.clear()
	_default_materials_by_id.clear()
	if _shell != null:
		if _shell.get_meta("main") != null:
			var main = _shell.get_meta("main")
			if main.simulation_playback_controller != null:
				main.simulation_playback_controller.clear_simulation()
		if "object_nodes_by_id" in _shell and _shell.object_nodes_by_id is Dictionary:
			_shell.object_nodes_by_id.clear()
		if "default_materials_by_id" in _shell and _shell.default_materials_by_id is Dictionary:
			_shell.default_materials_by_id.clear()


func _sync_shell_object_maps() -> void:
	if _shell == null:
		return

	_shell.object_nodes_by_id = _object_nodes_by_id
	_shell.default_materials_by_id = _default_materials_by_id


func _set_shell_environment_node(environment_node: Node3D) -> void:
	if _shell == null:
		return

	_shell.environment_node = environment_node


func _vector3_from_value(value: Variant) -> Vector3:
	if value is Vector3:
		return value

	if value is Array and value.size() >= 3:
		return Vector3(float(value[0]), float(value[1]), float(value[2]))

	if value is Dictionary:
		return Vector3(
			float(value.get("x", 0.0)),
			float(value.get("y", 0.0)),
			float(value.get("z", 0.0))
		)

	return Vector3.ZERO


func _project_objects_root() -> Node3D:
	if _shell == null:
		return null

	return _shell.project_objects_root


func _session():
	if _shell == null:
		return null

	return _shell.session


func _geometry_renderer():
	if _shell == null:
		return null

	return _shell.geometry_renderer


func _packet_loader():
	if _shell == null:
		return null

	return _shell.packet_loader
