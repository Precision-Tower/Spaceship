extends RefCounted
class_name GhostCommandController

const WorkbenchPathsScript = preload("res://Workbench/config/WorkbenchPaths.gd")

const GHOST_ACTION_MOVE_ID := 1
const GHOST_ACTION_DELETE_ID := 2
const GHOST_ACTION_EXPORT_ID := 3
const GHOST_ACTION_ROTATE_ID := 4

const MODE_IDLE := 0
const MODE_DRAWING_PIPE := 1

var _shell
var _session
var _main

var ghost_mode := MODE_IDLE

var drawing_pipe_start := Vector3.ZERO
var drawing_pipe_start_connection := {}

var ghost_move_active := false
var ghost_move_last_mouse_position := Vector2.ZERO
var ghost_move_node = null
var ghost_move_start_position := Vector3.ZERO
var ghost_move_plane_y := 0.0
var ghost_move_axis_lock := ""

var ghost_rotate_active := false
var ghost_rotate_node = null
var ghost_rotate_start_basis := Basis()
var ghost_rotate_last_mouse_position := Vector2.ZERO
var ghost_rotate_axis_lock := ""
var ghost_rotate_accumulated_degrees := 0.0

var ghost_nodes_by_id := {}
var selected_ghost_id := ""

var pending_pipe_run_id := ""
var pending_pipe_material_hint := "unspecified"
var pending_pipe_start_connection: Dictionary = {}

var ghost_command_dialogs = null

func setup(shell, session, main) -> void:
	_shell = shell
	_session = session
	_main = main


func handle_ghost_move_input(event: InputEvent) -> bool:
	if ghost_mode == MODE_DRAWING_PIPE:
		return _handle_pipe_draw_input(event)

	if ghost_rotate_active:
		return _handle_ghost_rotate_input(event)

	if not ghost_move_active:
		if event is InputEventKey:
			var key_event = event as InputEventKey
			if key_event.pressed and not key_event.echo and key_event.keycode == KEY_R:
				_start_ghost_rotate()
				return _selected_ghost_node() != null

		return false

	if event is InputEventMouseMotion:
		var motion_event = event as InputEventMouseMotion
		ghost_move_last_mouse_position = motion_event.position
		_update_ghost_move_position(ghost_move_last_mouse_position)
		return true

	if event is InputEventMouseButton:
		var mouse_event = event as InputEventMouseButton
		ghost_move_last_mouse_position = mouse_event.position

		if mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_LEFT:
			_confirm_ghost_move()
		elif mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_RIGHT:
			_cancel_ghost_move()
		elif mouse_event.pressed:
			_update_ghost_move_position(ghost_move_last_mouse_position)

		return true

	if event is InputEventKey:
		var key_event = event as InputEventKey
		if not key_event.pressed or key_event.echo:
			return true

		match key_event.keycode:
			KEY_X:
				ghost_move_axis_lock = "x"
				_update_ghost_move_position(ghost_move_last_mouse_position)
			KEY_Y:
				ghost_move_axis_lock = "y"
				_update_ghost_move_position(ghost_move_last_mouse_position)
			KEY_Z:
				ghost_move_axis_lock = "z"
				_update_ghost_move_position(ghost_move_last_mouse_position)
			KEY_ESCAPE:
				_cancel_ghost_move()
			KEY_ENTER, KEY_KP_ENTER:
				_confirm_ghost_move()
			_:
				pass

		return true

	return false

func _start_pipe_command(center_position: Vector3, default_od_m: float = 0.1, from_port: bool = false, pipe_direction: Vector3 = Vector3(1.0, 0.0, 0.0)) -> void:
	if ghost_command_dialogs == null:
		return

	ghost_command_dialogs._start_pipe_command(center_position, default_od_m, from_port, pipe_direction)

func start_pipe_draw_from_port(port_selection: Dictionary) -> void:
	if port_selection.is_empty():
		return

	var port: Dictionary = port_selection.get("raw_data", {})
	var parent: Dictionary = port_selection.get("parent_object", {})

	var start_position: Vector3 = _vector3_from_value(port.get("position_m", Vector3.ZERO))
	var inherited_od_m: float = float(parent.get("od_m", 0.1))

	print("[WorkbenchGhostPipe] pipe command from port=%s inherited_od_m=%s" % [
		port_selection.get("id", "missing"),
		inherited_od_m
	])

	var direction: Vector3 = _vector3_from_value(port.get("direction", Vector3.RIGHT))

	if direction.length() <= 0.001:
		var port_id: String = str(port_selection.get("port_id", ""))
		if port_id == "A":
			direction = Vector3.LEFT
		else:
			direction = Vector3.RIGHT

	pending_pipe_start_connection = port_selection.duplicate(true)
	pending_pipe_run_id = str(parent.get("run_id", ""))
	pending_pipe_material_hint = str(parent.get("material_hint", "unspecified"))

	_start_pipe_command(start_position, inherited_od_m, true, direction.normalized())
	
func _handle_pipe_draw_input(event: InputEvent) -> bool:
	if event is InputEventMouseMotion:
		var mouse_event = event as InputEventMouseMotion
		var end_position := _mouse_world_position(mouse_event.position)
		print("[WorkbenchGhostPipe] preview start=%s end=%s" % [
			drawing_pipe_start,
			end_position
		])
		return true

	if event is InputEventMouseButton:
		var mouse_event = event as InputEventMouseButton

		if mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_LEFT:
			var end_position := _mouse_world_position(mouse_event.position)
			_commit_pipe_segment(drawing_pipe_start, end_position)
			_stop_pipe_draw()
			return true

		if mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_RIGHT:
			_cancel_pipe_draw()
			return true

	if event is InputEventKey:
		var key_event = event as InputEventKey
		if key_event.pressed and not key_event.echo and key_event.keycode == KEY_ESCAPE:
			_cancel_pipe_draw()
			return true

	return true


func _commit_pipe_segment(start_position: Vector3, end_position: Vector3) -> void:
	var length := start_position.distance_to(end_position)
	if length < 0.01:
		print("[WorkbenchGhostPipe] commit ignored: segment too short")
		return

	if _shell.ghost_renderer == null or _shell.ghost_root == null:
		return

	var object_id := _next_ghost_pipe_id()
	var ghost_pipe = _shell.ghost_renderer.create_ghost_pipe_segment(
		object_id,
		start_position,
		end_position
	)

	if ghost_pipe == null:
		return

	_shell.ghost_root.add_child(ghost_pipe)
	ghost_nodes_by_id[object_id] = ghost_pipe

	print("[WorkbenchGhostPipe] committed id=%s start=%s end=%s" % [
		object_id,
		start_position,
		end_position
	])

func _next_ghost_pipe_id() -> String:
	var index := 1
	while true:
		var object_id := "ghost_pipe_%03d" % index
		if not ghost_nodes_by_id.has(object_id):
			return object_id
		index += 1

	return "ghost_pipe_fallback"

func _cancel_pipe_draw() -> void:
	print("[WorkbenchGhostPipe] draw cancelled")
	_stop_pipe_draw()


func _stop_pipe_draw() -> void:
	ghost_mode = MODE_IDLE
	drawing_pipe_start = Vector3.ZERO
	drawing_pipe_start_connection = {}

func _create_default_dimensioned_pipe(center_position: Vector3) -> void:
	if _shell.ghost_renderer == null or _shell.ghost_root == null:
		return

	var object_id := _next_ghost_pipe_id()
	var length_m := 1.0
	var od_m := 0.1

	var ghost_pipe = _shell.ghost_renderer.create_dimensioned_ghost_pipe(
		object_id,
		center_position,
		length_m,
		od_m
	)

	if ghost_pipe == null:
		return

	_shell.ghost_root.add_child(ghost_pipe)
	ghost_nodes_by_id[object_id] = ghost_pipe

	print("[WorkbenchGhostPipe] created dimensioned pipe id=%s center=%s length_m=%s od_m=%s" % [
		object_id,
		center_position,
		length_m,
		od_m
	])

func on_create_command_requested(category: String, item: String, world_position: Vector3) -> void:
	print("[WorkbenchCreate] category=%s item=%s world_position=%s" % [
		category,
		item,
		world_position
	])

	if _shell.ghost_renderer == null or _shell.ghost_root == null:
		return

	if category != "Primitives" and category != "Objects":
		return

	if category == "Objects" and item == "pipe":
		_start_pipe_command(world_position)
		return

	var ghost = _shell.ghost_renderer.create_ghost(
		category,
		item,
		world_position
	)

	if ghost != null:
		_shell.ghost_root.add_child(ghost)
		ghost_nodes_by_id[ghost.name] = ghost

func _create_dimensioned_pipe(center_position: Vector3, length_m: float, od_m: float, direction: Vector3 = Vector3(1.0, 0.0, 0.0)) -> void:
	if _shell.ghost_renderer == null or _shell.ghost_root == null:
		return

	var pipe_direction: Vector3 = direction.normalized()
	if pipe_direction.length() <= 0.001:
		pipe_direction = Vector3(1.0, 0.0, 0.0)

	var object_id: String = _next_ghost_pipe_id()

	var ghost_pipe = _shell.ghost_renderer.create_dimensioned_ghost_pipe(
		object_id,
		center_position,
		length_m,
		od_m,
		pipe_direction
	)

	if ghost_pipe == null:
		return

	if pending_pipe_run_id != "":
		ghost_pipe.set_meta("run_id", pending_pipe_run_id)
		ghost_pipe.set_meta("material_hint", pending_pipe_material_hint)

	if not pending_pipe_start_connection.is_empty():
		ghost_pipe.set_meta("start_connection", {
			"object_id": pending_pipe_start_connection.get("object_id", ""),
			"port_id": pending_pipe_start_connection.get("port_id", "")
		})

	_shell.ghost_root.add_child(ghost_pipe)
	ghost_nodes_by_id[object_id] = ghost_pipe
	_register_ghost_in_session(object_id, "ghost_pipe", object_id, ghost_pipe)

	print("[WorkbenchGhostPipe] created dimensioned pipe id=%s center=%s length_m=%s od_m=%s direction=%s start_connection=%s" % [
		object_id,
		center_position,
		length_m,
		od_m,
		pipe_direction,
		ghost_pipe.get_meta("start_connection", {})
	])

	pending_pipe_start_connection = {}
	pending_pipe_run_id = ""
	pending_pipe_material_hint = "unspecified"

func on_ghost_action_menu_id_pressed(id: int) -> void:
	print("[WorkbenchGhostMenu] pressed id=", id)

	match id:
		GHOST_ACTION_MOVE_ID:
			print("[WorkbenchGhostMenu] Move")
			_start_ghost_move()
		GHOST_ACTION_ROTATE_ID:
			print("[WorkbenchGhostMenu] Rotate")
			_start_ghost_rotate()
		GHOST_ACTION_DELETE_ID:
			print("[WorkbenchGhostMenu] Delete")
			_delete_selected_ghost()
		GHOST_ACTION_EXPORT_ID:
			print("[WorkbenchGhostMenu] Export")
			_export_ghost_candidate_commands()
		_:
			print("[WorkbenchGhostMenu] Unknown id=", id)


func select_ghost_by_id(object_id: String, menu_position: Vector2) -> bool:
	var ghost = _ghost_node_by_id(object_id)
	if ghost == null:
		return false

	selected_ghost_id = object_id
	ghost_move_last_mouse_position = menu_position
	ghost_rotate_last_mouse_position = menu_position
	_main.viewport_selection_controller.highlight_viewport_object("")
	print("[WorkbenchGhost] selected %s" % object_id)

	if _shell.ghost_action_menu != null:
		_shell.ghost_action_menu.reset_size()
		_shell.ghost_action_menu.popup_on_parent(
			Rect2i(Vector2i(menu_position.round()), Vector2i.ZERO)
		)

	return true


func is_ghost_object_id(object_id: String) -> bool:
	return _ghost_node_by_id(object_id) != null


func _ghost_node_by_id(object_id: String) -> Node3D:
	var ghost = ghost_nodes_by_id.get(object_id, null)
	if ghost == null:
		return null

	if not is_instance_valid(ghost):
		ghost_nodes_by_id.erase(object_id)
		return null

	return ghost


func _selected_ghost_node() -> Node3D:
	if selected_ghost_id == "":
		return null

	return _ghost_node_by_id(selected_ghost_id)


func _start_ghost_move() -> void:
	var ghost = _selected_ghost_node()
	if ghost == null:
		return

	if _shell.ghost_action_menu != null:
		_shell.ghost_action_menu.hide()

	ghost_move_active = true
	ghost_move_node = ghost
	ghost_move_start_position = ghost.position
	ghost_move_plane_y = ghost.position.y
	ghost_move_axis_lock = ""
	_update_ghost_move_position(ghost_move_last_mouse_position)


func _handle_ghost_rotate_input(event: InputEvent) -> bool:
	if event is InputEventMouseMotion:
		var motion_event = event as InputEventMouseMotion
		_update_ghost_rotate(motion_event.position)
		return true

	if event is InputEventMouseButton:
		var mouse_event = event as InputEventMouseButton
		ghost_rotate_last_mouse_position = mouse_event.position

		if mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_LEFT:
			_confirm_ghost_rotate()
		elif mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_RIGHT:
			_cancel_ghost_rotate()
		elif mouse_event.pressed:
			_apply_ghost_rotation()

		return true

	if event is InputEventKey:
		var key_event = event as InputEventKey
		if not key_event.pressed or key_event.echo:
			return true

		match key_event.keycode:
			KEY_X:
				ghost_rotate_axis_lock = "x"
				_apply_ghost_rotation()
			KEY_Y:
				ghost_rotate_axis_lock = "y"
				_apply_ghost_rotation()
			KEY_Z:
				ghost_rotate_axis_lock = "z"
				_apply_ghost_rotation()
			KEY_ESCAPE:
				_cancel_ghost_rotate()
			KEY_ENTER, KEY_KP_ENTER:
				_confirm_ghost_rotate()
			_:
				pass

		return true

	return true


func _start_ghost_rotate() -> void:
	var ghost = _selected_ghost_node()
	if ghost == null:
		return

	if _shell.ghost_action_menu != null:
		_shell.ghost_action_menu.hide()

	ghost_rotate_active = true
	ghost_rotate_node = ghost
	ghost_rotate_start_basis = ghost.basis
	ghost_rotate_last_mouse_position = ghost_move_last_mouse_position
	if _main != null and _main.get_viewport() != null:
		ghost_rotate_last_mouse_position = _main.get_viewport().get_mouse_position()
	ghost_rotate_axis_lock = ""
	ghost_rotate_accumulated_degrees = 0.0

	print("[WorkbenchGhostRotate] start object_id=%s" % ghost.name)


func _update_ghost_rotate(mouse_position: Vector2) -> void:
	if ghost_rotate_node == null or not is_instance_valid(ghost_rotate_node):
		_stop_ghost_rotate()
		return

	var delta_x := mouse_position.x - ghost_rotate_last_mouse_position.x
	ghost_rotate_last_mouse_position = mouse_position
	ghost_rotate_accumulated_degrees += delta_x * 0.25
	_apply_ghost_rotation()


func _apply_ghost_rotation() -> void:
	if ghost_rotate_node == null or not is_instance_valid(ghost_rotate_node):
		_stop_ghost_rotate()
		return

	var axis := _rotation_axis()
	ghost_rotate_node.basis = ghost_rotate_start_basis.rotated(
		axis,
		deg_to_rad(ghost_rotate_accumulated_degrees)
	)
	ghost_rotate_node.set_meta("rotation_degrees", ghost_rotate_node.rotation_degrees)

	print("[WorkbenchGhostRotate] object_id=%s axis=%s degrees=%s" % [
		ghost_rotate_node.name,
		axis,
		ghost_rotate_accumulated_degrees
	])


func _confirm_ghost_rotate() -> void:
	_stop_ghost_rotate()


func _cancel_ghost_rotate() -> void:
	if ghost_rotate_node != null and is_instance_valid(ghost_rotate_node):
		ghost_rotate_node.basis = ghost_rotate_start_basis
		ghost_rotate_node.set_meta("rotation_degrees", ghost_rotate_node.rotation_degrees)

	_stop_ghost_rotate()


func _stop_ghost_rotate() -> void:
	ghost_rotate_active = false
	ghost_rotate_node = null
	ghost_rotate_start_basis = Basis()
	ghost_rotate_last_mouse_position = Vector2.ZERO
	ghost_rotate_axis_lock = ""
	ghost_rotate_accumulated_degrees = 0.0


func _rotation_axis() -> Vector3:
	match ghost_rotate_axis_lock:
		"x":
			return Vector3.RIGHT
		"y":
			return Vector3.UP
		"z":
			return Vector3.BACK
		_:
			return Vector3.UP


func _delete_selected_ghost() -> void:
	var ghost = _selected_ghost_node()
	if ghost == null:
		return

	var object_id = selected_ghost_id
	ghost_nodes_by_id.erase(object_id)
	if _session != null:
		_session.remove_object(object_id)

	if _shell.object_tree_controller != null:
		_shell.object_tree_controller.populate()
	selected_ghost_id = ""

	if ghost_move_node == ghost:
		_stop_ghost_move()

	if ghost_rotate_node == ghost:
		_stop_ghost_rotate()

	if _shell.ghost_action_menu != null:
		_shell.ghost_action_menu.hide()

	ghost.queue_free()


func _export_ghost_candidate_commands() -> void:
	if _shell.ghost_command_exporter == null:
		return

	var ghosts := _current_ghost_nodes()
	if ghosts.is_empty():
		return

	if _shell.ghost_action_menu != null:
		_shell.ghost_action_menu.hide()

	var export_path := WorkbenchPathsScript.ghost_command_export_path()
	var command_count = _shell.ghost_command_exporter.export_ghost_commands(
		ghosts,
		export_path
	)

	if command_count >= 0:
		print("[WorkbenchGhostExport] wrote %s commands=%d" % [
			export_path,
			command_count
		])


func _current_ghost_nodes() -> Array:
	var ghosts := []

	for object_id in ghost_nodes_by_id.keys():
		var ghost = _ghost_node_by_id(str(object_id))
		if ghost != null:
			ghosts.append(ghost)

	return ghosts


func _update_ghost_move_position(mouse_position: Vector2) -> void:
	if ghost_move_node == null or not is_instance_valid(ghost_move_node):
		_stop_ghost_move()
		return

	var next_position := _ghost_move_position_from_mouse(mouse_position)
	_set_ghost_position(ghost_move_node, next_position)

	print("[WorkbenchGhostMove] object_id=%s position=%s" % [
		ghost_move_node.name,
		next_position
	])


func _set_ghost_position(ghost: Node3D, next_position: Vector3) -> void:
	ghost.position = next_position
	ghost.set_meta("world_position", next_position)

	for child in ghost.get_children():
		child.set_meta("world_position", next_position)


func _cancel_ghost_move() -> void:
	if ghost_move_node != null and is_instance_valid(ghost_move_node):
		_set_ghost_position(ghost_move_node, ghost_move_start_position)

	_stop_ghost_move()


func _confirm_ghost_move() -> void:
	_stop_ghost_move()


func _stop_ghost_move() -> void:
	ghost_move_active = false
	ghost_move_node = null
	ghost_move_start_position = Vector3.ZERO
	ghost_move_plane_y = 0.0
	ghost_move_axis_lock = ""


func clear_ghosts() -> void:
	_stop_ghost_move()
	_stop_ghost_rotate()
	_stop_pipe_draw()
	selected_ghost_id = ""
	ghost_nodes_by_id.clear()

	if _shell.ghost_action_menu != null:
		_shell.ghost_action_menu.hide()

	if _shell.ghost_root == null:
		return

	for child in _shell.ghost_root.get_children():
		_shell.ghost_root.remove_child(child)
		child.queue_free()


func _mouse_world_position(mouse_position: Vector2) -> Vector3:
	if _shell.viewport_camera == null:
		return drawing_pipe_start

	var viewport_position = _main.viewport_input_helper.to_subviewport_position(mouse_position)
	var origin = _shell.viewport_camera.project_ray_origin(viewport_position)
	var direction = _shell.viewport_camera.project_ray_normal(viewport_position)

	var plane = Plane(Vector3.UP, drawing_pipe_start.y)
	var plane_hit = plane.intersects_ray(origin, direction)

	if plane_hit != null:
		return Vector3(plane_hit.x, drawing_pipe_start.y, plane_hit.z)

	return drawing_pipe_start


func _ghost_move_position_from_mouse(mouse_position: Vector2) -> Vector3:
	if _shell.viewport_camera == null:
		return ghost_move_node.position

	var viewport_position = _main.viewport_input_helper.to_subviewport_position(mouse_position)
	var origin = _shell.viewport_camera.project_ray_origin(viewport_position)
	var direction = _shell.viewport_camera.project_ray_normal(viewport_position)

	if ghost_move_axis_lock == "":
		var plane = Plane(Vector3.UP, ghost_move_plane_y)
		var plane_hit = plane.intersects_ray(origin, direction)
		if plane_hit != null:
			return Vector3(plane_hit.x, ghost_move_plane_y, plane_hit.z)

		return ghost_move_node.position

	var axis := Vector3.ZERO

	match ghost_move_axis_lock:
		"x":
			axis = Vector3.RIGHT
		"y":
			axis = Vector3.UP
		"z":
			axis = Vector3.BACK
		_:
			return ghost_move_node.position

	return _main.viewport_input_helper.closest_point_on_axis_to_ray(
		ghost_move_start_position,
		axis,
		origin,
		direction
	)


func _append_workbench_candidate_command(command: Dictionary) -> void:
	var export_path := WorkbenchPathsScript.ghost_command_export_path()
	var packet := {
		"packet_type": "workbench_candidate_commands",
		"evidence_state": "ui_ghost_candidate",
		"source": "UI/Workbench",
		"commands": [],
		"prohibited_interpretations": [
			"ghost_candidate_equals_engineering_object",
			"ui_position_equals_validated_geometry",
			"candidate_command_equals_packet_mutation",
			"visual_object_equals_physical_truth"
		]
	}

	var existing = FileAccess.open(export_path, FileAccess.READ)
	if existing != null:
		var parsed = JSON.parse_string(existing.get_as_text())
		if parsed is Dictionary:
			packet = parsed

	var commands: Array = packet.get("commands", [])
	commands.append(command)
	packet["commands"] = commands

	var out = FileAccess.open(export_path, FileAccess.WRITE)
	if out == null:
		push_warning("Could not write candidate commands: " + export_path)
		return

	out.store_string(JSON.stringify(packet, "\t"))
	out.close()

	print("[WorkbenchCandidateCommand] appended " + str(command.get("command_type", "missing")))


func _vector3_from_value(value) -> Vector3:
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

func _next_ghost_fitting_id() -> String:
	var index := 1
	while true:
		var object_id := "ghost_fitting_%03d" % index
		if not ghost_nodes_by_id.has(object_id):
			return object_id
		index += 1

	return "ghost_fitting_fallback"

func create_fitting_from_port(port_selection: Dictionary, fitting_type: String, roll_degrees: float = 0.0) -> void:
	if port_selection.is_empty():
		return

	if _shell.ghost_renderer == null or _shell.ghost_root == null:
		return

	var port: Dictionary = port_selection.get("raw_data", {})
	var parent: Dictionary = port_selection.get("parent_object", {})
	var port_position: Vector3 = _vector3_from_value(port.get("position_m", Vector3.ZERO))

	var primary_direction: Vector3 = _vector3_from_value(port.get("direction", Vector3(1.0, 0.0, 0.0))).normalized()

	if primary_direction.length() <= 0.001:
		var port_id: String = str(port_selection.get("port_id", ""))
		if port_id == "A":
			primary_direction = Vector3(-1.0, 0.0, 0.0)
		else:
			primary_direction = Vector3(1.0, 0.0, 0.0)

	var roll_rad: float = deg_to_rad(roll_degrees)

	var turn_direction: Vector3 = Vector3(
		0.0,
		cos(roll_rad),
		sin(roll_rad)
	).normalized()

	var fitting_id: String = _next_ghost_fitting_id()

	var inherited_od_m: float = float(parent.get("od_m", 0.1))
	var inherited_run_id: String = str(parent.get("run_id", parent.get("object_id", fitting_id)))
	var inherited_material_hint: String = str(parent.get("material_hint", "unspecified"))

	var fitting = _shell.ghost_renderer.create_ghost_fitting_node(
		fitting_id,
		port_position,
		port_selection.duplicate(true),
		inherited_od_m,
		inherited_run_id,
		inherited_material_hint,
		fitting_type,
		primary_direction,
		turn_direction
	)

	if fitting == null:
		return

	fitting.set_meta("fitting_type", fitting_type)

	_shell.ghost_root.add_child(fitting)
	ghost_nodes_by_id[fitting_id] = fitting
	_register_ghost_in_session(fitting_id, "ghost_fitting", fitting_id, fitting)

	if _shell.port_action_menu != null:
		_shell.port_action_menu.hide()

	fitting.set_meta("primary_direction", primary_direction)
	fitting.set_meta("turn_direction", turn_direction)
	fitting.set_meta("roll_degrees", roll_degrees)

	print("[WorkbenchGhostPipe] created fitting id=%s type=%s position=%s od_m=%s run_id=%s direction=%s" % [
		fitting_id,
		fitting_type,
		port_position,
		inherited_od_m,
		inherited_run_id,
		turn_direction
	])

func start_pipe_trim_command(port_selection: Dictionary, sign: float) -> void:
	if ghost_command_dialogs == null:
		return

	ghost_command_dialogs.start_pipe_trim_command(port_selection, sign)

func _apply_pipe_trim(port_selection: Dictionary, sign: float, amount_m: float) -> void:
	var parent: Dictionary = port_selection.get("parent_object", {})
	var object_id: String = str(parent.get("object_id", ""))

	var pipe = _ghost_node_by_id(object_id)
	if pipe == null:
		print("[WorkbenchGhostPipe] trim failed: pipe not found " + object_id)
		return

	var start_world: Vector3 = _vector3_from_value(pipe.get_meta("start_world", Vector3.ZERO))
	var end_world: Vector3 = _vector3_from_value(pipe.get_meta("end_world", Vector3.ZERO))
	var direction: Vector3 = _vector3_from_value(pipe.get_meta("direction", Vector3.RIGHT)).normalized()

	var port_id: String = str(port_selection.get("port_id", ""))

	if port_id == "A":
		start_world = start_world - direction * sign * amount_m
	elif port_id == "B":
		end_world = end_world + direction * sign * amount_m
	else:
		print("[WorkbenchGhostPipe] trim failed: unknown port " + port_id)
		return

	var new_length: float = start_world.distance_to(end_world)
	if new_length <= 0.01:
		print("[WorkbenchGhostPipe] trim rejected: length too small")
		return

	var od_m: float = float(pipe.get_meta("od_m", 0.1))
	var run_id: String = str(pipe.get_meta("run_id", object_id))
	var material_hint: String = str(pipe.get_meta("material_hint", "unspecified"))

	_rebuild_dimensioned_pipe(object_id, start_world, end_world, od_m, run_id, material_hint)

func _rebuild_dimensioned_pipe(object_id: String, start_world: Vector3, end_world: Vector3, od_m: float, run_id: String, material_hint: String) -> void:
	var old_pipe = _ghost_node_by_id(object_id)
	if old_pipe == null:
		return
	var start_connection: Dictionary = old_pipe.get_meta("start_connection", {})
	var end_connection: Dictionary = old_pipe.get_meta("end_connection", {})
	var center_position: Vector3 = (start_world + end_world) * 0.5
	var length_m: float = start_world.distance_to(end_world)
	var direction: Vector3 = (end_world - start_world).normalized()

	var new_pipe = _shell.ghost_renderer.create_dimensioned_ghost_pipe(
		object_id,
		center_position,
		length_m,
		od_m,
		direction
	)

	if new_pipe == null:
		return

	new_pipe.set_meta("run_id", run_id)
	new_pipe.set_meta("material_hint", material_hint)

	_shell.ghost_root.add_child(new_pipe)
	ghost_nodes_by_id[object_id] = new_pipe

	old_pipe.queue_free()
	if not start_connection.is_empty():
		new_pipe.set_meta("start_connection", start_connection)

	if not end_connection.is_empty():
		new_pipe.set_meta("end_connection", end_connection)
	print("[WorkbenchGhostPipe] rebuilt pipe id=%s length_m=%s od_m=%s" % [
		object_id,
		length_m,
		od_m
	])

func start_od_edit_command(port_selection: Dictionary) -> void:
	if ghost_command_dialogs == null:
		return

	ghost_command_dialogs.start_od_edit_command(port_selection)

func _apply_run_od_edit(port_selection: Dictionary, new_od_m: float) -> void:
	var parent: Dictionary = port_selection.get("parent_object", {})
	var run_id: String = str(parent.get("run_id", ""))

	if run_id == "":
		print("[WorkbenchGhostPipe] OD edit failed: missing run_id")
		return

	var ids := ghost_nodes_by_id.keys()

	for id in ids:
		var object_id: String = str(id)
		var ghost = _ghost_node_by_id(object_id)
		if ghost == null:
			continue

		if str(ghost.get_meta("run_id", "")) != run_id:
			continue

		var node_kind: String = str(ghost.get_meta("node_kind", ""))

		if node_kind == "ghost_pipe":
			var start_connection: Dictionary = ghost.get_meta("start_connection", {})
			if not start_connection.is_empty():
				continue

			var start_world: Vector3 = _vector3_from_value(ghost.get_meta("start_world", Vector3.ZERO))
			var end_world: Vector3 = _vector3_from_value(ghost.get_meta("end_world", Vector3.ZERO))
			var material_hint: String = str(ghost.get_meta("material_hint", "unspecified"))

			_rebuild_dimensioned_pipe(object_id, start_world, end_world, new_od_m, run_id, material_hint)

		elif node_kind == "ghost_fitting":
			var position: Vector3 = ghost.position
			var fitting_type: String = str(ghost.get_meta("fitting_type", "elbow_90"))
			var material_hint: String = str(ghost.get_meta("material_hint", "unspecified"))
			var source_selection: Dictionary = ghost.get_meta("source_selection", {})

			var primary_direction: Vector3 = _vector3_from_value(
				ghost.get_meta("primary_direction", Vector3(1.0, 0.0, 0.0))
			)

			var turn_direction: Vector3 = _vector3_from_value(
				ghost.get_meta(
					"turn_direction",
					ghost.get_meta("outlet_direction", Vector3(0.0, 1.0, 0.0))
				)
			)

			var roll_degrees: float = float(ghost.get_meta("roll_degrees", 0.0))

			_rebuild_fitting(
				object_id,
				position,
				source_selection,
				new_od_m,
				run_id,
				material_hint,
				fitting_type,
				primary_direction,
				turn_direction,
				roll_degrees
			)

	_realign_connected_pipes_for_run(run_id, new_od_m)

	print("[WorkbenchGhostPipe] edited run OD run_id=%s od_m=%s" % [
		run_id,
		new_od_m
	])

func _realign_connected_pipes_for_run(run_id: String, od_m: float) -> void:
	for id in ghost_nodes_by_id.keys():
		var object_id: String = str(id)
		var pipe = _ghost_node_by_id(object_id)
		if pipe == null:
			continue

		if str(pipe.get_meta("node_kind", "")) != "ghost_pipe":
			continue

		if str(pipe.get_meta("run_id", "")) != run_id:
			continue

		var start_connection: Dictionary = pipe.get_meta("start_connection", {})
		if start_connection.is_empty():
			continue

		var connected_object_id: String = str(start_connection.get("object_id", ""))
		var connected_port_id: String = str(start_connection.get("port_id", ""))

		var new_start: Vector3 = _port_world_position(connected_object_id, connected_port_id)
		if new_start == Vector3.ZERO:
			continue

		var length_m: float = float(pipe.get_meta("length_m", 0.0))
		var direction: Vector3 = _vector3_from_value(pipe.get_meta("direction", Vector3(1.0, 0.0, 0.0))).normalized()
		var material_hint: String = str(pipe.get_meta("material_hint", "unspecified"))

		var new_end: Vector3 = new_start + direction * length_m

		_rebuild_dimensioned_pipe(
			object_id,
			new_start,
			new_end,
			od_m,
			run_id,
			material_hint
		)

		print("[WorkbenchGhostPipe] realigning pipe=%s from %s.%s new_start=%s" % [
			object_id,
			connected_object_id,
			connected_port_id,
			new_start
		])

func _rebuild_fitting(
	object_id: String,
	position: Vector3,
	source_selection: Dictionary,
	od_m: float,
	run_id: String,
	material_hint: String,
	fitting_type: String,
	primary_direction: Vector3,
	turn_direction: Vector3,
	roll_degrees: float
) -> void:
	var old_fitting = _ghost_node_by_id(object_id)
	if old_fitting == null:
		return

	var new_fitting = _shell.ghost_renderer.create_ghost_fitting_node(
		object_id,
		position,
		source_selection,
		od_m,
		run_id,
		material_hint,
		fitting_type,
		primary_direction,
		turn_direction
	)

	if new_fitting == null:
		return

	new_fitting.set_meta("fitting_type", fitting_type)
	new_fitting.set_meta("primary_direction", primary_direction)
	new_fitting.set_meta("turn_direction", turn_direction)
	new_fitting.set_meta("outlet_direction", turn_direction)
	new_fitting.set_meta("roll_degrees", roll_degrees)

	_shell.ghost_root.add_child(new_fitting)
	ghost_nodes_by_id[object_id] = new_fitting
	old_fitting.queue_free()

	print("[WorkbenchGhostPipe] rebuilt fitting id=%s od_m=%s roll=%s" % [
		object_id,
		od_m,
		roll_degrees
	])

func _port_world_position(object_id: String, port_id: String) -> Vector3:
	var node = _ghost_node_by_id(object_id)
	if node == null:
		return Vector3.ZERO

	for child in node.get_children():
		if str(child.name).ends_with("_" + port_id):
			var selection: Dictionary = child.get_meta("selection", {})
			var raw: Dictionary = selection.get("raw_data", {})
			return _vector3_from_value(raw.get("position_m", Vector3.ZERO))

	return Vector3.ZERO

func start_fitting_command(port_selection: Dictionary, fitting_type: String) -> void:
	if ghost_command_dialogs == null:
		return

	ghost_command_dialogs.start_fitting_command(port_selection, fitting_type)

func _register_ghost_in_session(object_id: String, object_type: String, display_name: String, node: Node3D) -> void:
	if _session == null:
		return

	var object_data := {
		"object_id": object_id,
		"object_type": object_type,
		"display_name": display_name,
		"role": "ghost_intent",
		"assembly_group": "GhostLab",
		"subsystem": "Ghost Intent",
		"parent_group": "Objects",
		"position": node.position,
		"primitive": "box",
		"size": Vector3(1.0, 0.1, 0.1),
		"packet_links": []
	}

	if node.has_meta("length_m"):
		object_data["length_m"] = node.get_meta("length_m")

	if node.has_meta("od_m"):
		object_data["od_m"] = node.get_meta("od_m")

	if node.has_meta("run_id"):
		object_data["run_id"] = node.get_meta("run_id")

	if node.has_meta("material_hint"):
		object_data["material_hint"] = node.get_meta("material_hint")

	_session.register_object(object_data)

	if _shell.object_tree_controller != null:
		_shell.object_tree_controller.populate()
