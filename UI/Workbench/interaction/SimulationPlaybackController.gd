extends RefCounted
class_name SimulationPlaybackController

var _shell
var _viewport_object_renderer
var _main

var simulation_frames_by_id := {}
var simulation_time_s := 0.0
var simulation_playing := true

func setup(shell, main) -> void:
	_shell = shell
	_main = main
	_viewport_object_renderer = main.viewport_object_renderer

func capture_simulation_frames(object_data: Dictionary, packet: Dictionary) -> void:
	var object_id := str(object_data.get("object_id", ""))
	if object_id == "" or packet.is_empty():
		return

	if packet.has("barrel"):
		var barrel: Dictionary = packet.get("barrel", {})
		if str(barrel.get("object_id", "")) != object_id:
			return

		var simulation: Dictionary = barrel.get("simulation", {})
		var frames: Array = simulation.get("frames", [])

		if frames.size() > 0:
			simulation_frames_by_id[object_id] = frames

func apply_simulation_frame(time_s: float) -> void:
	var object_nodes_by_id = _viewport_object_renderer.object_nodes()
	for object_id in simulation_frames_by_id.keys():
		if not object_nodes_by_id.has(object_id):
			continue

		var mesh_node: MeshInstance3D = object_nodes_by_id[object_id]
		var parent := mesh_node.get_parent()
		if parent == null:
			continue

		var frames: Array = simulation_frames_by_id[object_id]
		if frames.is_empty():
			continue

		var frame_index := int(time_s / 0.04) % frames.size()
		var frame: Dictionary = frames[frame_index]

		parent.position.y = float(frame.get("barrel_center_y_m", frame.get("barrel_center_z_m", parent.position.y)))
		parent.rotation_degrees.x = float(frame.get("rotation_x_deg", parent.rotation_degrees.x))

func clear_simulation() -> void:
	simulation_frames_by_id.clear()
	simulation_time_s = 0.0
