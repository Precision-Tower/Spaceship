func _add_port_markers(parent_node: Node3D, object_data: Dictionary) -> void:
	var ports: Array = object_data.get("ports", [])
	if ports.is_empty():
		return

	for port in ports:
		if not port is Dictionary:
			continue

		var port_data := port as Dictionary
		var position := _vector3_from_dict(port_data.get("position_m", {}))
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

func _create_port_pipe_ghost(center: Vector3, rotation_degrees: Vector3, length_m: float) -> void:
	if ghost_renderer == null or ghost_root == null:
		print("[WorkbenchPortAction] Add Pipe failed: ghost renderer/root missing")
		return

	var ghost = ghost_renderer.create_ghost(
		"Objects",
		"pipe",
		center
	)

	if ghost == null:
		print("[WorkbenchPortAction] Add Pipe failed: ghost renderer returned null")
		return

	ghost.rotation_degrees = rotation_degrees
	ghost.scale = Vector3(1.0, length_m, 1.0)

	ghost_root.add_child(ghost)

	if ghost.has_meta("workbench_object_id"):
		ghost_nodes_by_id[str(ghost.get_meta("workbench_object_id"))] = ghost
	else:
		ghost_nodes_by_id[ghost.name] = ghost

	print("[WorkbenchPortAction] Added pipe ghost %s" % ghost.name)

func _add_pipe_from_selected_port() -> void:
	if selected_port_selection.is_empty():
		return

	var port: Dictionary = selected_port_selection.get("raw_data", {})
	var port_position := _vector3_from_dict(port.get("position_m", {}))
	var direction := _vector3_from_dict(port.get("direction", {})).normalized()

	if direction.length() <= 0.0:
		print("[WorkbenchPortAction] Add Pipe failed: missing direction")
		return

	var length_m := 1.0
	var center := port_position + direction * (length_m / 2.0)

	var rotation_degrees := Vector3.ZERO

	# Godot cylinder height axis is Y.
	# Pipe along X uses Z rotation -90 / +90.
	if abs(direction.x) >= abs(direction.y) and abs(direction.x) >= abs(direction.z):
		rotation_degrees = Vector3(0.0, 0.0, -90.0 if direction.x > 0.0 else 90.0)
	elif abs(direction.z) >= abs(direction.x) and abs(direction.z) >= abs(direction.y):
		rotation_degrees = Vector3(90.0 if direction.z > 0.0 else -90.0, 0.0, 0.0)
	else:
		rotation_degrees = Vector3.ZERO if direction.y > 0.0 else Vector3(180.0, 0.0, 0.0)

	print(
		"[WorkbenchPortAction] Add Pipe from %s.%s position=%s direction=%s center=%s rotation=%s"
		% [
			selected_port_selection.get("object_id", "missing"),
			selected_port_selection.get("port_id", "missing"),
			port_position,
			direction,
			center,
			rotation_degrees
		]
	)

	_create_port_pipe_ghost(center, rotation_degrees, length_m)

func _add_elbow_from_selected_port() -> void:
	if selected_port_selection.is_empty():
		return

	var port: Dictionary = selected_port_selection.get("raw_data", {})
	var parent: Dictionary = selected_port_selection.get("parent_object", {})

	if str(parent.get("object_type", "")) != "connector_pipe":
		print("[WorkbenchPortAction] Add 90 Elbow disabled: selected parent is not connector_pipe")
		return

	if str(port.get("state", "")) != "open":
		print("[WorkbenchPortAction] Add 90 Elbow disabled: port is not open")
		return

	var command := {
		"command_type": "attach_elbow_90_candidate",
		"target_object_id": selected_port_selection.get("object_id", "missing"),
		"target_port_id": selected_port_selection.get("port_id", "missing"),
		"fitting_port_id": "A",
		"roll_degrees": 0.0,
		"source_state": "workbench_port_action"
	}

	_append_workbench_candidate_command(command)

	print("[WorkbenchPortAction] attach_elbow_90_candidate " + str(command))
