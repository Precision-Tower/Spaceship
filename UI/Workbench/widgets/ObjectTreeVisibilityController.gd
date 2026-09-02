extends RefCounted
class_name ObjectTreeVisibilityController

var _shell
var _session
var _main

func setup(shell, session, main) -> void:
	_shell = shell
	_session = session
	_main = main

func handle_visibility_shortcut(event: InputEvent) -> bool:
	if not (event is InputEventKey):
		return false

	var key_event = event as InputEventKey
	if not key_event.pressed or key_event.echo:
		return false

	if key_event.keycode != KEY_H:
		return false

	if key_event.shift_pressed:
		return _set_selected_tree_item_visibility(true)

	return _toggle_selected_tree_item_visibility()

func _toggle_selected_tree_item_visibility() -> bool:
	var item = _selected_tree_item()
	if item == null:
		return false

	return _set_tree_item_visibility(item, not _tree_item_is_visible(item), true)

func _set_selected_tree_item_visibility(visible: bool) -> bool:
	var item = _selected_tree_item()
	if item == null:
		return false

	return _set_tree_item_visibility(item, visible, true)

func _selected_tree_item() -> TreeItem:
	if _shell.object_tree == null:
		return null

	var item = _shell.object_tree.get_selected()
	if item == null:
		return null

	var data = item.get_metadata(0)
	if typeof(data) != TYPE_DICTIONARY:
		return null

	return item

func _set_tree_item_checked_state(item: TreeItem, visible: bool) -> void:
	if item == null:
		return

	var data = item.get_metadata(0)
	if typeof(data) != TYPE_DICTIONARY:
		return

	var metadata = data as Dictionary
	metadata["visible"] = visible
	item.set_metadata(0, metadata)
	item.set_checked(0, visible)

func _apply_tree_visibility_to_viewport() -> void:
	var object_nodes_by_id = _main.viewport_object_renderer.object_nodes()
	for object_id in object_nodes_by_id.keys():
		var node = object_nodes_by_id[object_id] as MeshInstance3D
		if node == null:
			continue

		var item = _shell.object_tree_controller._tree_item_for_object_id(str(object_id))
		node.visible = _tree_item_is_visible(item)

func _refresh_selected_item_after_visibility_change() -> void:
	if _shell.object_tree == null or _session == null:
		return

	var selected_item = _shell.object_tree.get_selected()
	if selected_item == null:
		return

	var data = selected_item.get_metadata(0)
	if typeof(data) != TYPE_DICTIONARY:
		return

	_session.select_item((data as Dictionary).duplicate(true))

func on_object_tree_item_selected() -> void:
	if _shell.object_tree_controller != null:
		if _shell.suppress_tree_selection_signal:
			return

	if _shell.object_tree == null or _shell.object_inspector_panel == null:
		return

	var item = _shell.object_tree.get_selected()
	if item == null:
		_main.packet_display_resolver.show_no_selection()
		return

	var data = item.get_metadata(0)
	if typeof(data) != TYPE_DICTIONARY:
		_main.packet_display_resolver.show_no_selection()
		return

	if _session == null:
		return

	_session.select_item((data as Dictionary).duplicate(true))

func on_object_tree_item_edited() -> void:
	if _shell.object_tree == null:
		return

	if _shell.object_tree.get_edited_column() != 0:
		return

	var item = _shell.object_tree.get_edited()
	if item == null:
		return

	_set_tree_item_visibility(item, item.is_checked(0), true)

func _tree_item_is_visible(item: TreeItem) -> bool:
	if item == null:
		return true

	var data = item.get_metadata(0)
	if typeof(data) == TYPE_DICTIONARY:
		return (data as Dictionary).get("visible", true)

	return true

func _set_tree_item_visibility(item: TreeItem, visible: bool, update_viewport: bool) -> bool:
	_set_tree_item_checked_state(item, visible)

	var data = item.get_metadata(0)
	if typeof(data) == TYPE_DICTIONARY:
		var metadata = data as Dictionary
		var child_objects = metadata.get("child_objects", [])
		for object_id in child_objects:
			var object_item = _shell.object_tree_controller._tree_item_for_object_id(str(object_id))
			if object_item != null:
				_set_tree_item_visibility(object_item, visible, false)

		var child_groups = metadata.get("child_groups", [])
		for group_id in child_groups:
			var group_item = _shell.object_tree_controller._find_tree_item_by_key(_shell.object_tree.get_root(), "group:" + str(group_id))
			if group_item != null:
				_set_tree_item_visibility(group_item, visible, false)

	if update_viewport:
		_apply_tree_visibility_to_viewport()
		_refresh_selected_item_after_visibility_change()

	return true
