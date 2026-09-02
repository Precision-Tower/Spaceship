extends Node3D
class_name CoordinateHelper

@export var axis_length := 2.0
@export var grid_size := 4
@export var grid_step := 0.25

func _ready() -> void:
	_build_axes()
	_build_grid()

func _build_axes() -> void:
	_add_line("X_axis", Vector3.ZERO, Vector3(axis_length, 0, 0), Color.RED)
	_add_line("Y_axis", Vector3.ZERO, Vector3(0, axis_length, 0), Color.GREEN)
	_add_line("Z_axis", Vector3.ZERO, Vector3(0, 0, axis_length), Color.BLUE)

func _build_grid() -> void:
	var half := grid_size * grid_step
	var count := int(grid_size * 2)

	for i in range(-grid_size, grid_size + 1):
		var p := i * grid_step
		_add_line("grid_x_%s" % i, Vector3(-half, 0, p), Vector3(half, 0, p), Color(0.35, 0.35, 0.35))
		_add_line("grid_z_%s" % i, Vector3(p, 0, -half), Vector3(p, 0, half), Color(0.35, 0.35, 0.35))

func _add_line(name_value: String, a: Vector3, b: Vector3, color: Color) -> void:
	var mesh := ImmediateMesh.new()
	mesh.surface_begin(Mesh.PRIMITIVE_LINES)
	mesh.surface_add_vertex(a)
	mesh.surface_add_vertex(b)
	mesh.surface_end()

	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.albedo_color = color

	var node := MeshInstance3D.new()
	node.name = name_value
	node.mesh = mesh
	node.material_override = material
	add_child(node)