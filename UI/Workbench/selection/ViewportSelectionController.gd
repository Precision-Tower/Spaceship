extends RefCounted
class_name ViewportSelectionController

var _shell
var _session
var _main
var _viewport_input_helper
var _ghost_command_controller

var selected_port_selection: Dictionary = {}

func setup(shell, session, main, viewport_input_helper, ghost_command_controller) -> void:
	_shell = shell
	_session = session
	_main = main
	_viewport_input_helper = viewport_input_helper
	_ghost_command_controller = ghost_command_controller

func handle_viewport_selection_input(event: InputEvent) -> bool:
	if _shell.selection_raycaster == null or _shell.viewport_camera == null or _shell.viewport_container == null:
		return false

	if not (event is InputEventMouseButton):
		return false

	var mouse_event = event as InputEventMouseButton
	if mouse_event.button_index != MOUSE_BUTTON_LEFT or not mouse_event.pressed:
		return false

	if not _shell.viewport_container.get_global_rect().has_point(mouse_event.position):
		return false

	var viewport_position = _viewport_input_helper.to_subviewport_position(mouse_event.position)

	var selection = _shell.selection_raycaster.get_selection_at(
		_shell.viewport_camera,
		viewport_position
	)

	var object_id = ""
	if not selection.is_empty():
		object_id = str(selection.get("object_id", selection.get("id", "")))

	if str(selection.get("node_kind", "")) == "port":
		if _shell.ghost_action_menu != null:
			_shell.ghost_action_menu.hide()
		if _shell.create_context_menu != null:
			_shell.create_context_menu.hide()

		_ghost_command_controller.selected_ghost_id = ""
		selected_port_selection = selection.duplicate(true)

		if _session != null:
			_session.select_item(selected_port_selection.duplicate(true))

		if _shell.port_action_menu != null:
			_shell.port_action_menu.reset_size()
			_shell.port_action_menu.popup_on_parent(
				Rect2i(Vector2i(mouse_event.position.round()), Vector2i.ZERO)
			)

		return true

	if object_id == "":
		if _shell.ghost_action_menu != null:
			_shell.ghost_action_menu.hide()
		var world_position = _viewport_input_helper.empty_viewport_world_position(viewport_position)
		if _shell.create_context_menu != null:
			_shell.create_context_menu.show_at(mouse_event.position, world_position)
		return true

	if _shell.create_context_menu != null:
		_shell.create_context_menu.hide()

	if _ghost_command_controller.is_ghost_object_id(object_id):
		return _ghost_command_controller.select_ghost_by_id(object_id, mouse_event.position)

	if _shell.ghost_action_menu != null:
		_shell.ghost_action_menu.hide()
	_ghost_command_controller.selected_ghost_id = ""

	return select_object_by_id(object_id)

func select_object_by_id(object_id: String) -> bool:
	if object_id == "":
		return false

	if _session == null:
		return false

	var object_data = _session.get_object(object_id)
	if object_data.is_empty():
		return false

	_session.select_object(object_id)
	return true

func highlight_viewport_object(object_id: String) -> void:
	var object_nodes_by_id = _main.viewport_object_renderer.object_nodes()
	var default_materials_by_id = _main.viewport_object_renderer.default_materials()

	for id in object_nodes_by_id.keys():
		var node = object_nodes_by_id[id] as MeshInstance3D
		if node == null:
			continue

		if str(id) == object_id:
			node.material_override = _highlight_material()
		else:
			node.material_override = default_materials_by_id.get(id, null)

var _highlight_material_cache: StandardMaterial3D = null
func _highlight_material() -> StandardMaterial3D:
	if _highlight_material_cache == null:
		_highlight_material_cache = StandardMaterial3D.new()
		_highlight_material_cache.albedo_color = Color(1.0, 0.82, 0.24, 1.0)
		_highlight_material_cache.emission_enabled = true
		_highlight_material_cache.emission = Color(1.0, 0.58, 0.08, 1.0)
		_highlight_material_cache.emission_energy_multiplier = 0.35

	return _highlight_material_cache
