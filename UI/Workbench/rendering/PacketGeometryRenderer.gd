extends RefCounted
class_name PacketGeometryRenderer

func create_node(object: Dictionary, packet: Dictionary = {}) -> Node3D:
	var object_id := str(object.get("object_id", ""))
	if object_id == "":
		return null

	var body := StaticBody3D.new()
	body.name = object_id
	body.position = _to_vector3(object.get("position", Vector3.ZERO))
	body.rotation_degrees = _to_vector3(
		object.get("rotation_degrees", Vector3.ZERO)
	)

	if _has_float_center_z(object, packet):
		body.position.y = _float_center_z_for(object, packet)

	body.set_meta("object_id", object_id)
	body.set_meta("workbench_object_id", object_id)

	var mesh_node := MeshInstance3D.new()
	mesh_node.name = "Mesh"
	mesh_node.set_meta("object_id", object_id)
	mesh_node.set_meta("workbench_object_id", object_id)

	var collision := CollisionShape3D.new()
	collision.name = "CollisionShape3D"

	var render := _render_contract_for(object, packet)
	if render.is_empty():
		render = _fallback_render_contract(object)

	if render.is_empty():
		return null

	var primitive := str(render.get("primitive", ""))

	match primitive:
		"box":
			var size := _to_vector3(render.get("size", Vector3(1, 1, 1)))
			var mesh := BoxMesh.new()
			mesh.size = size
			mesh_node.mesh = mesh

			var shape := BoxShape3D.new()
			shape.size = size
			collision.shape = shape

		"cylinder":
			var radius := float(render.get("radius_m", render.get("radius", 0.5)))
			var height := float(render.get("height_m", render.get("height", 1.0)))

			var mesh := CylinderMesh.new()
			mesh.top_radius = radius
			mesh.bottom_radius = radius
			mesh.height = height
			mesh_node.mesh = mesh

			var shape := CylinderShape3D.new()
			shape.radius = radius
			shape.height = height
			collision.shape = shape
		"pipe_elbow_90":
			var outer_radius := float(render.get("outer_radius_m", render.get("radius_m", 0.05)))
			var bend_radius := float(render.get("bend_radius_m", 0.20))

			mesh_node.mesh = _create_pipe_elbow_90_mesh(outer_radius, bend_radius)

			var shape := BoxShape3D.new()
			shape.size = Vector3(
				bend_radius + outer_radius * 2.0,
				bend_radius + outer_radius * 2.0,
				outer_radius * 2.0
			)
			collision.shape = shape
		_:
			return null

	mesh_node.material_override = _material_for(object, packet)
	body.add_child(mesh_node)
	body.add_child(collision)

	return body

func _create_pipe_elbow_90_node(object: Dictionary, packet: Dictionary, render: Dictionary) -> Node3D:
	var object_id := str(object.get("object_id", "pipe_elbow_90"))

	var root := StaticBody3D.new()
	root.name = object_id
	root.position = _to_vector3(object.get("position_m", object.get("position", Vector3.ZERO)))
	root.rotation_degrees = _to_vector3(render.get("rotation_degrees", object.get("rotation_degrees", Vector3.ZERO)))
	root.set_meta("object_id", object_id)
	root.set_meta("workbench_object_id", object_id)

	var outer_radius := float(render.get("outer_radius_m", render.get("radius_m", 0.05)))
	var bend_radius := float(render.get("bend_radius_m", 0.20))

	var leg_a := _pipe_leg_mesh("LegA", outer_radius, bend_radius)
	leg_a.position = Vector3(0.0, -bend_radius / 2.0, 0.0)
	root.add_child(leg_a)

	var leg_b := _pipe_leg_mesh("LegB", outer_radius, bend_radius)
	leg_b.rotation_degrees = Vector3(0.0, 0.0, 90.0)
	leg_b.position = Vector3(bend_radius / 2.0, 0.0, 0.0)
	root.add_child(leg_b)

	var collision := CollisionShape3D.new()
	collision.name = "CollisionShape3D"
	var shape := BoxShape3D.new()
	shape.size = Vector3(bend_radius + outer_radius * 2.0, bend_radius + outer_radius * 2.0, outer_radius * 2.0)
	collision.shape = shape
	root.add_child(collision)

	return root

func _pipe_leg_mesh(name_value: String, radius: float, height: float) -> MeshInstance3D:
	var node := MeshInstance3D.new()
	node.name = name_value

	var mesh := CylinderMesh.new()
	mesh.top_radius = radius
	mesh.bottom_radius = radius
	mesh.height = height
	node.mesh = mesh
	node.material_override = StandardMaterial3D.new()
	node.material_override.albedo_color = Color(0.8, 0.8, 0.8, 1.0)

	return node

func _create_pipe_elbow_90_mesh(tube_radius: float, bend_radius: float) -> ArrayMesh:
	var radial_steps := 16
	var tube_steps := 12

	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	var indices := PackedInt32Array()

	for i in range(radial_steps + 1):
		var u := float(i) / float(radial_steps)
		var theta := u * PI * 0.5

		var center := Vector3(
			sin(theta) * bend_radius,
			(1.0 - cos(theta)) * bend_radius,
			0.0
		)

		var radial_dir := Vector3(cos(theta), sin(theta), 0.0)
		var binormal := Vector3(0.0, 0.0, 1.0)

		for j in range(tube_steps):
			var v := float(j) / float(tube_steps)
			var phi := v * TAU

			var normal := radial_dir * cos(phi) + binormal * sin(phi)
			var vertex := center + normal * tube_radius

			vertices.append(vertex)
			normals.append(normal.normalized())

	for i in range(radial_steps):
		for j in range(tube_steps):
			var a := i * tube_steps + j
			var b := i * tube_steps + ((j + 1) % tube_steps)
			var c := (i + 1) * tube_steps + j
			var d := (i + 1) * tube_steps + ((j + 1) % tube_steps)

			indices.append(a)
			indices.append(c)
			indices.append(b)

			indices.append(b)
			indices.append(c)
			indices.append(d)

	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_INDEX] = indices

	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh

func create_environment_node(packet: Dictionary) -> Node3D:
	if packet.is_empty():
		return null

	var environment: Dictionary = packet.get("environment", {})
	var render: Dictionary = environment.get("render", {})

	if render.is_empty():
		return null

	var primitive := str(render.get("primitive", ""))

	if primitive == "fluid_surface":
		return _create_fluid_surface_node(environment, render)

	if primitive == "fluid_volume":
		return _create_fluid_volume_node(environment, render)

	return null


func _create_fluid_surface_node(environment: Dictionary, render: Dictionary) -> Node3D:
	var node := MeshInstance3D.new()
	node.name = str(environment.get("environment_id", "FluidEnvironment"))

	var mesh := PlaneMesh.new()
	var size: Dictionary = render.get("size_m", {})
	mesh.size = Vector2(float(size.get("x", 6.0)), float(size.get("z", 6.0)))
	node.mesh = mesh
	node.position = Vector3(0.0, float(render.get("surface_z_m", 0.0)), 0.0)
	node.material_override = _fluid_material(render)

	return node


func _create_fluid_volume_node(environment: Dictionary, render: Dictionary) -> Node3D:
	var root := Node3D.new()
	root.name = str(environment.get("environment_id", "FluidEnvironment"))

	var size: Dictionary = render.get("size_m", {})
	var size_x := float(size.get("x", 6.0))
	var depth := float(render.get("depth_m", size.get("y", 0.5)))
	var size_z := float(size.get("z", 6.0))
	var surface_y := float(render.get("surface_z_m", 0.0))

	root.set_meta("object_id", root.name)
	root.set_meta("workbench_object_id", root.name)

	var volume := MeshInstance3D.new()
	volume.name = "FluidVolume"

	var volume_mesh := BoxMesh.new()
	volume_mesh.size = Vector3(size_x, depth, size_z)
	volume.mesh = volume_mesh
	volume.position = Vector3(0.0, surface_y - depth / 2.0, 0.0)
	volume.material_override = _fluid_material(render)
	root.add_child(volume)

	var surface := MeshInstance3D.new()
	surface.name = "WaterlineSurface"

	var surface_mesh := PlaneMesh.new()
	surface_mesh.size = Vector2(size_x, size_z)
	surface.mesh = surface_mesh
	surface.position = Vector3(0.0, surface_y + 0.002, 0.0)

	var surface_mat := StandardMaterial3D.new()
	surface_mat.albedo_color = Color(0.2, 0.55, 1.0, 0.55)
	surface_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	surface.material_override = surface_mat
	root.add_child(surface)

	return root


func _fluid_material(render: Dictionary) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	var material: Dictionary = render.get("material", {})
	var alpha := float(material.get("alpha", 0.25))

	mat.albedo_color = Color(0.1, 0.35, 0.8, alpha)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA

	return mat


func _has_float_center_z(object: Dictionary, packet: Dictionary) -> bool:
	if packet.is_empty():
		return false

	var object_id := str(object.get("object_id", ""))

	if packet.has("barrel"):
		var barrel: Dictionary = packet.get("barrel", {})
		if str(barrel.get("object_id", "")) == object_id:
			var float_state: Dictionary = barrel.get("float_state", {})
			return float_state.has("barrel_center_z_m") or float_state.has("equilibrium_barrel_center_z_m")

	return false


func _float_center_z_for(object: Dictionary, packet: Dictionary) -> float:
	var object_id := str(object.get("object_id", ""))

	if packet.has("barrel"):
		var barrel: Dictionary = packet.get("barrel", {})
		if str(barrel.get("object_id", "")) == object_id:
			var float_state: Dictionary = barrel.get("float_state", {})
			if float_state.has("barrel_center_z_m"):
				return float(float_state.get("barrel_center_z_m", 0.0))
			return float(float_state.get("equilibrium_barrel_center_z_m", 0.0))

	return 0.0


func _render_contract_for(object: Dictionary, packet: Dictionary) -> Dictionary:
	if object.has("render"):
		var render: Dictionary = object.get("render", {})
		if not render.is_empty():
			return render

	if packet.is_empty():
		return {}

	var object_id := str(object.get("object_id", ""))

	if packet.has("barrel"):
		var barrel: Dictionary = packet.get("barrel", {})
		if str(barrel.get("object_id", "")) == object_id:
			var geometry: Dictionary = barrel.get("geometry", {})
			var render: Dictionary = geometry.get("render", {})
			return render.get("outer", {})

	return {}

func _fallback_render_contract(object: Dictionary) -> Dictionary:
	var primitive := str(object.get("primitive", ""))

	match primitive:
		"box":
			return {
				"primitive": "box",
				"size": object.get("size", Vector3(1, 1, 1))
			}
		"cylinder":
			return {
				"primitive": "cylinder",
				"radius_m": object.get("radius_m", 0.5),
				"height_m": object.get("height_m", 1.0)
			}
		_:
			return {}


func _material_for(object: Dictionary, packet: Dictionary) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	var object_type := str(object.get("object_type", ""))

	if packet.has("barrel"):
		var barrel: Dictionary = packet.get("barrel", {})
		var material_id := str(barrel.get("material_id", ""))
		if material_id.contains("hdpe"):
			material.albedo_color = Color(0.12, 0.38, 0.78, 1.0)
			return material

	match object_type:
		"boat_hull":
			material.albedo_color = Color(0.42, 0.28, 0.16, 1.0)
		"barrel":
			material.albedo_color = Color(0.12, 0.38, 0.78, 1.0)
		"connector_pipe":
			material.albedo_color = Color(0.8, 0.8, 0.8, 1.0)
		"frame_beam":
			material.albedo_color = Color(0.95, 0.55, 0.18, 1.0)
		"battery":
			material.albedo_color = Color(0.18, 0.18, 0.18, 1.0)
		"electric_motor":
			material.albedo_color = Color(0.95, 0.78, 0.18, 1.0)
		"payload":
			material.albedo_color = Color(0.75, 0.68, 0.22, 1.0)
		_:
			material.albedo_color = Color(0.45, 0.5, 0.55, 1.0)

	return material


func _to_vector3(value: Variant) -> Vector3:
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
