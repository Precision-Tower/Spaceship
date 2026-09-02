extends RefCounted
class_name GhostPrimitiveRenderer

const EVIDENCE_STATE := "ui_ghost_candidate"

var _counts_by_item: Dictionary = {}
var _material: StandardMaterial3D

func create_ghost_pipe_segment(object_id: String, start_position: Vector3, end_position: Vector3) -> Node3D:
	var root := Node3D.new()
	root.name = object_id
	root.set_meta("object_id", object_id)
	root.set_meta("workbench_object_id", object_id)
	root.set_meta("node_kind", "ghost_pipe")
	root.set_meta("evidence_state", EVIDENCE_STATE)
	root.set_meta("start_position", start_position)
	root.set_meta("end_position", end_position)

	var midpoint := (start_position + end_position) * 0.5
	var delta := end_position - start_position
	var length := delta.length()

	var segment := MeshInstance3D.new()
	segment.name = "SegmentMesh"

	var mesh := CylinderMesh.new()
	mesh.top_radius = 0.035
	mesh.bottom_radius = 0.035
	mesh.height = max(length, 0.001)
	segment.mesh = mesh
	segment.material_override = _ghost_material()

	segment.transform = _cylinder_transform_between(start_position, end_position)

	root.add_child(segment)

	root.add_child(_create_ghost_pipe_endpoint(object_id, "start", start_position))
	root.add_child(_create_ghost_pipe_endpoint(object_id, "end", end_position))

	return root

func create_ghost_fitting_node(object_id: String, position: Vector3, source_selection: Dictionary, od_m: float, run_id: String, material_hint: String, fitting_type: String = "elbow_90", primary_direction: Vector3 = Vector3(1.0, 0.0, 0.0), turn_direction: Vector3 = Vector3(0.0, 1.0, 0.0)) -> Node3D:
	var root := Node3D.new()
	root.name = object_id
	root.position = position

	root.set_meta("object_id", object_id)
	root.set_meta("workbench_object_id", object_id)
	root.set_meta("node_kind", "ghost_fitting")
	root.set_meta("evidence_state", EVIDENCE_STATE)
	root.set_meta("source_selection", source_selection)
	root.set_meta("od_m", od_m)
	root.set_meta("run_id", run_id)
	root.set_meta("material_hint", material_hint)
	root.set_meta("fitting_type", fitting_type)

	var primary: Vector3 = primary_direction.normalized()
	var turn: Vector3 = turn_direction.normalized()

	var leg_length: float = max(od_m * 2.5, 0.2)
	var b_local: Vector3 = (primary * leg_length) + (turn * leg_length)

	if fitting_type == "elbow_90":
		var visual := _create_elbow_90_visual(od_m, primary, turn)
		root.add_child(visual)
		root.add_child(_create_selectable_fitting_body(object_id, od_m, primary, turn))
	else:
		var marker: MeshInstance3D = MeshInstance3D.new()
		marker.name = "GhostFittingMarker"

		var sphere: SphereMesh = SphereMesh.new()
		sphere.radius = max(od_m * 0.75, 0.04)
		sphere.height = sphere.radius * 2.0
		marker.mesh = sphere
		marker.material_override = _ghost_material()
		root.add_child(marker)

	root.add_child(_create_ghost_fitting_port(
		object_id,
		"A",
		Vector3.ZERO,
		position,
		source_selection,
		od_m,
		run_id,
		material_hint,
		-primary
	))

	root.add_child(_create_ghost_fitting_port(
		object_id,
		"B",
		b_local,
		position + b_local,
		{},
		od_m,
		run_id,
		material_hint,
		turn
	))
	return root

func _create_selectable_fitting_body(object_id: String, od_m: float, primary: Vector3, turn: Vector3) -> StaticBody3D:
	var body: StaticBody3D = StaticBody3D.new()
	body.name = "FittingBody_%s" % object_id

	body.set_meta("object_id", object_id)
	body.set_meta("workbench_object_id", object_id)
	body.set_meta("selection", {
		"node_kind": "object",
		"object_id": object_id,
		"id": object_id,
		"authority": "ghost",
		"object_type": "ghost_fitting",
		"visible": true
	})

	var collision: CollisionShape3D = CollisionShape3D.new()
	var shape: BoxShape3D = BoxShape3D.new()

	var leg_length: float = max(od_m * 2.5, 0.2)

	shape.size = Vector3(
		max(od_m * 2.0, 0.18),
		max(od_m * 2.0, 0.18),
		max(od_m * 2.0, 0.18)
	)

	collision.position = primary.normalized() * leg_length
	collision.shape = shape
	body.add_child(collision)

	return body

func _create_elbow_90_visual(od_m: float, primary: Vector3, turn: Vector3) -> Node3D:
	var visual: Node3D = Node3D.new()
	visual.name = "Elbow90Visual"

	var radius: float = max(od_m * 0.5, 0.035)
	var leg_length: float = max(od_m * 2.5, 0.2)

	var corner: Vector3 = primary * leg_length
	var end: Vector3 = corner + turn * leg_length

	var leg_a: MeshInstance3D = _create_fitting_leg(Vector3.ZERO, corner, radius)
	visual.add_child(leg_a)

	var leg_b: MeshInstance3D = _create_fitting_leg(corner, end, radius)
	visual.add_child(leg_b)

	return visual

func _create_fitting_leg(start_local: Vector3, end_local: Vector3, radius: float) -> MeshInstance3D:
	var mesh_node: MeshInstance3D = MeshInstance3D.new()
	mesh_node.name = "FittingLeg"

	var delta: Vector3 = end_local - start_local
	var length: float = delta.length()

	var mesh: CylinderMesh = CylinderMesh.new()
	mesh.top_radius = radius
	mesh.bottom_radius = radius
	mesh.height = float(max(length, 0.001))

	mesh_node.mesh = mesh
	mesh_node.material_override = _ghost_material()
	mesh_node.transform = _cylinder_transform_between(start_local, end_local)

	return mesh_node

func _create_ghost_fitting_port(object_id: String, port_id: String, local_position: Vector3, world_position: Vector3, source_selection: Dictionary, od_m: float, run_id: String, material_hint: String, direction: Vector3) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.name = "Port_%s_%s" % [object_id, port_id]
	body.position = local_position

	body.set_meta("selection", {
		"node_kind": "port",
		"object_id": object_id,
		"port_id": port_id,
		"id": "%s.%s" % [object_id, port_id],
		"raw_data": {
			"port_id": port_id,
			"position_m": {
				"x": world_position.x,
				"y": world_position.y,
				"z": world_position.z
			},
			"direction": {
				"x": direction.x,
				"y": direction.y,
				"z": direction.z
			},
		},
		"parent_object": {
			"object_id": object_id,
			"object_type": "ghost_fitting",
			"od_m": od_m,
			"run_id": run_id,
			"material_hint": material_hint
		},
		"source_selection": source_selection,
		"visible": true
	})

	var marker := MeshInstance3D.new()
	marker.name = "GhostFittingPortMarker"

	var sphere := SphereMesh.new()
	sphere.radius = 0.045
	sphere.height = 0.09
	marker.mesh = sphere
	marker.material_override = _ghost_material()
	body.add_child(marker)

	var collision := CollisionShape3D.new()
	var shape := SphereShape3D.new()
	shape.radius = 0.07
	collision.shape = shape
	body.add_child(collision)

	return body

func create_dimensioned_ghost_pipe(object_id: String, center_position: Vector3, length_m: float, od_m: float, direction: Vector3 = Vector3.RIGHT) -> Node3D:
	var root := Node3D.new()
	root.name = object_id
	root.position = center_position

	root.set_meta("object_id", object_id)
	root.set_meta("workbench_object_id", object_id)
	root.set_meta("node_kind", "ghost_pipe")
	root.set_meta("evidence_state", EVIDENCE_STATE)
	root.set_meta("length_m", length_m)
	root.set_meta("od_m", od_m)
	root.set_meta("run_id", object_id)
	root.set_meta("od_m", od_m)
	root.set_meta("material_hint", "unspecified")

	var pipe_direction: Vector3 = direction.normalized()
	if pipe_direction.length() <= 0.001:
		pipe_direction = Vector3.RIGHT

	var start_world: Vector3 = center_position - pipe_direction * (length_m * 0.5)
	var end_world: Vector3 = center_position + pipe_direction * (length_m * 0.5)

	root.set_meta("start_world", start_world)
	root.set_meta("end_world", end_world)
	root.set_meta("direction", pipe_direction)

	var start_local: Vector3 = start_world - center_position
	var end_local: Vector3 = end_world - center_position

	var mesh_node := MeshInstance3D.new()
	mesh_node.name = "PipeMesh"

	var mesh := CylinderMesh.new()
	mesh.top_radius = od_m * 0.5
	mesh.bottom_radius = od_m * 0.5
	mesh.height = length_m
	mesh_node.mesh = mesh
	mesh_node.material_override = _ghost_material()

	mesh_node.transform = _cylinder_transform_between(start_local, end_local)
	root.add_child(mesh_node)
	var body := StaticBody3D.new()
	body.name = "PipeBody"

	body.set_meta("selection", {
		"node_kind": "object",
		"object_id": object_id,
		"id": object_id,
		"authority": "ghost",
		"object_type": "ghost_pipe",
		"visible": true
	})

	var collision := CollisionShape3D.new()

	var shape := CylinderShape3D.new()
	shape.radius = od_m * 0.5
	shape.height = length_m

	collision.shape = shape
	body.add_child(collision)

	body.transform = mesh_node.transform

	root.add_child(body)

	root.add_child(_create_pipe_endpoint(
		object_id,
		"A",
		start_local,
		start_world,
		od_m,
		object_id,
		"unspecified"
	))

	root.add_child(_create_pipe_endpoint(
		object_id,
		"B",
		end_local,
		end_world,
		od_m,
		object_id,
		"unspecified"
	))

	root.add_child(_create_pipe_center_marker(object_id))

	return root


func _create_pipe_endpoint(object_id: String, port_id: String, local_position: Vector3, world_position: Vector3, od_m: float, run_id: String, material_hint: String) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.name = "Port_%s_%s" % [object_id, port_id]
	body.position = local_position

	body.set_meta("selection", {
		"node_kind": "port",
		"object_id": object_id,
		"port_id": port_id,
		"id": "%s.%s" % [object_id, port_id],
		"raw_data": {
			"port_id": port_id,
			"position_m": {
				"x": world_position.x,
				"y": world_position.y,
				"z": world_position.z
			}
		},
		"parent_object": {
			"object_id": object_id,
			"object_type": "ghost_pipe",
			"od_m": od_m,
			"run_id": run_id,
			"material_hint": material_hint
		},
		"visible": true
	})

	var marker := MeshInstance3D.new()
	marker.name = "PipeEndpointMarker"

	var sphere := SphereMesh.new()
	sphere.radius = max(od_m * 0.3, 0.035)
	sphere.height = sphere.radius * 2.0
	marker.mesh = sphere
	marker.material_override = _ghost_material()
	body.add_child(marker)

	var collision := CollisionShape3D.new()
	collision.name = "EndpointCollision"

	var shape := SphereShape3D.new()
	shape.radius = max(od_m * 0.4, 0.06)
	collision.shape = shape
	body.add_child(collision)

	return body
	
func _create_pipe_center_marker(object_id: String) -> MeshInstance3D:
	var marker := MeshInstance3D.new()
	marker.name = "PipeCenter_%s" % object_id

	var sphere := SphereMesh.new()
	sphere.radius = 0.035
	sphere.height = 0.07
	marker.mesh = sphere
	marker.material_override = _ghost_material()

	return marker

func _cylinder_transform_between(start_position: Vector3, end_position: Vector3) -> Transform3D:
	var midpoint := (start_position + end_position) * 0.5
	var direction := end_position - start_position
	var length := direction.length()

	if length <= 0.001:
		return Transform3D(Basis(), midpoint)

	var y_axis := direction.normalized()
	var x_axis := Vector3.RIGHT

	if abs(y_axis.dot(x_axis)) > 0.95:
		x_axis = Vector3.FORWARD

	var z_axis := x_axis.cross(y_axis).normalized()
	x_axis = y_axis.cross(z_axis).normalized()

	var basis := Basis(x_axis, y_axis, z_axis)
	return Transform3D(basis, midpoint)

func _create_ghost_pipe_endpoint(object_id: String, port_id: String, position: Vector3) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.name = "Port_%s_%s" % [object_id, port_id]
	body.position = position

	body.set_meta("selection", {
		"node_kind": "port",
		"object_id": object_id,
		"port_id": port_id,
		"id": "%s.%s" % [object_id, port_id],
		"raw_data": {
			"port_id": port_id,
			"position_m": {
				"x": position.x,
				"y": position.y,
				"z": position.z
			}
		},
		"parent_object": {
			"object_id": object_id,
			"object_type": "ghost_pipe"
		},
		"visible": true
	})

	var marker := MeshInstance3D.new()
	marker.name = "GhostPipeEndpoint"

	var sphere := SphereMesh.new()
	sphere.radius = 0.055
	sphere.height = 0.11
	marker.mesh = sphere
	marker.material_override = _ghost_material()
	body.add_child(marker)

	var collision := CollisionShape3D.new()
	collision.name = "EndpointCollision"

	var shape := SphereShape3D.new()
	shape.radius = 0.08
	collision.shape = shape
	body.add_child(collision)

	return body

func create_ghost(category: String, item: String, world_position: Vector3) -> StaticBody3D:
	var shape := _shape_for(category, item)
	if shape == "":
		return null

	var mesh := _mesh_for_shape(shape)
	if mesh == null:
		return null

	var object_id := _next_object_id(item)

	var ghost := StaticBody3D.new()
	ghost.name = object_id
	ghost.position = world_position
	_apply_ghost_metadata(ghost, object_id, category, item, world_position)

	var mesh_node := MeshInstance3D.new()
	mesh_node.name = "Mesh"
	mesh_node.mesh = mesh
	mesh_node.material_override = _ghost_material()
	_apply_ghost_metadata(mesh_node, object_id, category, item, world_position)
	ghost.add_child(mesh_node)

	var collision := CollisionShape3D.new()
	collision.name = "CollisionShape3D"
	collision.shape = _collision_shape_for_shape(shape)
	_apply_ghost_metadata(collision, object_id, category, item, world_position)
	ghost.add_child(collision)

	return ghost


func _shape_for(category: String, item: String) -> String:
	if category == "Primitives":
		if item == "coupling":
			return "cylinder"
		return item

	if category == "Objects":
		match item:
			"barrel", "pipe":
				return "cylinder"

	return ""


func _mesh_for_shape(shape: String) -> Mesh:
	match shape:
		"sphere":
			var mesh := SphereMesh.new()
			mesh.radius = 0.35
			mesh.height = 0.7
			return mesh
		"box":
			var mesh := BoxMesh.new()
			mesh.size = Vector3(0.7, 0.7, 0.7)
			return mesh
		"cylinder":
			var mesh := CylinderMesh.new()
			mesh.top_radius = 0.3
			mesh.bottom_radius = 0.3
			mesh.height = 0.8
			return mesh
		"plane":
			var mesh := PlaneMesh.new()
			mesh.size = Vector2(1.0, 1.0)
			return mesh
		"cone":
			var mesh := CylinderMesh.new()
			mesh.top_radius = 0.0
			mesh.bottom_radius = 0.35
			mesh.height = 0.8
			return mesh
		"pipe_elbow_90", "torus":
			var mesh := TorusMesh.new()
			mesh.inner_radius = 0.18
			mesh.outer_radius = 0.35
			return mesh
		_:
			return null


func _collision_shape_for_shape(shape: String) -> Shape3D:
	match shape:
		"sphere":
			var shape_resource := SphereShape3D.new()
			shape_resource.radius = 0.35
			return shape_resource
		"box":
			var shape_resource := BoxShape3D.new()
			shape_resource.size = Vector3(0.7, 0.7, 0.7)
			return shape_resource
		"cylinder", "cone":
			var shape_resource := CylinderShape3D.new()
			shape_resource.radius = 0.35
			shape_resource.height = 0.8
			return shape_resource
		"plane":
			var shape_resource := BoxShape3D.new()
			shape_resource.size = Vector3(1.0, 0.02, 1.0)
			return shape_resource
		"torus":
			var shape_resource := SphereShape3D.new()
			shape_resource.radius = 0.35
			return shape_resource
		_:
			var shape_resource := SphereShape3D.new()
			shape_resource.radius = 0.35
			return shape_resource


func _next_object_id(item: String) -> String:
	var normalized_item := item.to_snake_case()
	var next_count := int(_counts_by_item.get(normalized_item, 0)) + 1
	_counts_by_item[normalized_item] = next_count
	return "ghost_%s_%03d" % [normalized_item, next_count]


func _ghost_material() -> StandardMaterial3D:
	if _material == null:
		_material = StandardMaterial3D.new()
		_material.albedo_color = Color(0.3, 0.8, 1.0, 0.34)
		_material.emission_enabled = true
		_material.emission = Color(0.18, 0.55, 0.8, 1.0)
		_material.emission_energy_multiplier = 0.18
		_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA

	return _material


func _apply_ghost_metadata(node: Node, object_id: String, category: String, item: String, world_position: Vector3) -> void:
	node.set_meta("object_id", object_id)
	node.set_meta("workbench_object_id", object_id)
	node.set_meta("category", category)
	node.set_meta("item", item)
	node.set_meta("node_kind", "ghost_object")
	node.set_meta("world_position", world_position)
	node.set_meta("evidence_state", EVIDENCE_STATE)
