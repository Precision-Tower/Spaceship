extends RefCounted
class_name ProjectActionController

const WorkbenchPathsScript = preload("res://Workbench/config/WorkbenchPaths.gd")
const DEVELOPMENT_DEFAULT_PROJECT_PATH := "res://projects/Float/FloatProject.gd"

var _shell
var _session
var _object_tree_controller
var _viewport_object_renderer
var _main

var layout_overrides: Dictionary = {}

func setup(shell, session, object_tree_controller, viewport_object_renderer, main) -> void:
	_shell = shell
	_session = session
	_object_tree_controller = object_tree_controller
	_viewport_object_renderer = viewport_object_renderer
	_main = main

func on_reload_project_pressed() -> void:
	print("[Workbench] Reload Project requested")

	var selected_object_id = ""

	var selected_item = _selected_tree_item()
	if selected_item != null:
		var data = selected_item.get_metadata(0)
		if typeof(data) == TYPE_DICTIONARY:
			var metadata = data as Dictionary
			selected_object_id = str(
				metadata.get(
					"object_id",
					metadata.get("id", "")
				)
			)

	if _session == null:
		return

	var project = _session.current_project
	if project == null:
		return

	_main.load_project(project)

	if selected_object_id != "":
		_shell.call_deferred("_select_object_after_reload", selected_object_id)

func _select_object_after_reload(object_id: String) -> void:
	if _main.viewport_selection_controller.select_object_by_id(object_id):
		print("[Workbench] Reselected object_id=%s" % object_id)
	else:
		print("[Workbench] Previous selection unavailable")

func on_save_override_pressed() -> void:
	var output_path = WorkbenchPathsScript.float_ghostlab_working_state_path()

	if _session == null:
		return

	var saved_objects := []

	for object_data: Dictionary in _session.get_objects():
		var object_type := str(object_data.get("object_type", ""))

		if not object_type.begins_with("ghost_"):
			continue

		saved_objects.append(_json_safe_object(object_data))

	var packet = {
		"packet_type": "ghostlab_working_state",
		"evidence_state": "operator_intent",
		"project_id": "float_ghostlab",
		"objects": saved_objects,
		"connections": [],
		"prohibited_interpretations": [
			"ghost_object_equals_engineering_object",
			"ui_position_equals_validated_geometry",
			"working_state_equals_engineering_package"
		]
	}

	var file = FileAccess.open(output_path, FileAccess.WRITE)
	if file == null:
		push_warning("Could not write GhostLab working state: " + output_path)
		return

	file.store_string(JSON.stringify(packet, "\t"))
	file.close()

	print("[GhostLabSave] wrote %s objects=%d" % [output_path, saved_objects.size()])

func _json_safe_object(object_data: Dictionary) -> Dictionary:
	var result := {}

	for key in object_data.keys():
		var value = object_data[key]

		if value is Vector3:
			result[key] = {
				"x": value.x,
				"y": value.y,
				"z": value.z
			}
		else:
			result[key] = value

	return result

func on_regenerate_packets_pressed() -> void:
	var engineering_dir = _engineering_float_boat_dir()
	var generators = [
		{
			"label": "hull_inventory.py",
			"path": engineering_dir.path_join("Hull/hull_inventory.py"),
		},
		{
			"label": "hull_frame.py",
			"path": engineering_dir.path_join("Hull/hull_frame.py"),
		},
		{
			"label": "battery.py",
			"path": engineering_dir.path_join("Motor/battery.py"),
		},
		{
			"label": "motor.py",
			"path": engineering_dir.path_join("Motor/motor.py"),
		},
		{
			"label": "boat_assembly.py",
			"path": engineering_dir.path_join("boat_assembly.py"),
		},
	]

	for generator in generators:
		var label = str(generator.get("label", "generator"))
		var script_path = str(generator.get("path", ""))

		print("[Workbench] Running %s" % label)

		if not FileAccess.file_exists(script_path):
			print("[Workbench] Regeneration failed: %s missing path=%s" % [label, script_path])
			return

		var exit_code = OS.execute("python", PackedStringArray([script_path]))
		if exit_code != 0:
			print("[Workbench] Regeneration failed: %s exit_code=%d" % [label, exit_code])
			return

	print("[Workbench] Regeneration complete")

func on_position_apply_requested(
	object_id: String,
	new_position: Vector3
) -> void:
	var object_nodes_by_id = _viewport_object_renderer.object_nodes()
	var node = object_nodes_by_id.get(object_id, null)
	if node == null:
		push_warning("No display node for object: " + object_id)
		return

	var item = _object_tree_controller._tree_item_for_object_id(object_id)
	if item == null:
		return

	var metadata = item.get_metadata(0)
	var object_data = metadata.get("raw_data", {})

	var old_position = _dict_to_vector3(object_data.get("position_m", {}))
	var delta = new_position - old_position

	node.position += delta

	object_data["position_m"] = {
		"x": new_position.x,
		"y": new_position.y,
		"z": new_position.z,
	}

	layout_overrides[object_id] = {
		"position_m": object_data["position_m"]
	}

	if object_data.has("render"):
		var render = object_data.get("render", {})
		if render.has("display_position_m"):
			var display_position = _dict_to_vector3(render.get("display_position_m", {}))
			display_position += delta
			render["display_position_m"] = {
				"x": display_position.x,
				"y": display_position.y,
				"z": display_position.z,
			}
			object_data["render"] = render

	metadata["raw_data"] = object_data
	item.set_metadata(0, metadata)

	if _session != null:
		_session.select_item(metadata.duplicate(true))

	print("[Workbench] applied live position edit: %s -> %s" % [object_id, new_position])

func _engineering_float_boat_dir() -> String:
	return ProjectSettings.globalize_path(
		"res://../Engineering/py/Projects/Float/Boat"
	).simplify_path()

func load_project_from_script() -> void:
	var script_to_load = _shell.project_script

	if script_to_load == null:
		print("Workbench: loading default project: ", DEVELOPMENT_DEFAULT_PROJECT_PATH)
		var default_resource = load(DEVELOPMENT_DEFAULT_PROJECT_PATH)
		print("Workbench: default resource = ", default_resource)
		if default_resource is Script:
			script_to_load = default_resource

	if script_to_load == null:
		print("Workbench: no project script loaded")
		_object_tree_controller.populate()
		return

	var next_project = script_to_load.new()
	print(
		"[Workbench] project=%s"
		% next_project.project_id
	)
	_main.load_project(next_project)

func _selected_tree_item() -> TreeItem:
	if _shell.object_tree == null:
		return null
	return _shell.object_tree.get_selected()

func _dict_to_vector3(value: Dictionary) -> Vector3:
	return Vector3(
		float(value.get("x", 0.0)),
		float(value.get("y", 0.0)),
		float(value.get("z", 0.0))
	)
