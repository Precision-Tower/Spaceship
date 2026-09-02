extends RefCounted
class_name PacketDisplayResolver

var _shell
var _session

func setup(shell, session) -> void:
	_shell = shell
	_session = session

func show_inspectable_selection(selection: Dictionary) -> void:
	var display_selection := selection.duplicate(true)
	var node_kind := str(display_selection.get("node_kind", ""))

	if node_kind == "object":
		var object_id := str(display_selection.get("object_id", ""))
		var object_data: Dictionary = _session.get_object(object_id)
		if object_data.is_empty():
			show_no_selection()
			return

		var object_item := _tree_item_for_object_id(object_id)
		display_selection["visible"] = _tree_item_is_visible(object_item)
		display_selection["raw_data"] = object_data
		
		if _shell.get_meta("main") != null:
			_shell.get_meta("main").viewport_selection_controller.highlight_viewport_object(object_id)

		var object_text: String = _shell.object_inspector.render_selection(display_selection) if _shell.object_inspector != null else str(object_data)
		object_text += _packet_text_for_object(object_data)
		if _shell.object_inspector_panel != null:
			_shell.object_inspector_panel.show_selection(display_selection, object_text)
		return

	var selected_item := _tree_item_for_selection(display_selection)
	if selected_item != null:
		display_selection["visible"] = _tree_item_is_visible(selected_item)

	if _shell.get_meta("main") != null:
		_shell.get_meta("main").viewport_selection_controller.highlight_viewport_object("")

	var selection_text: String = _shell.object_inspector.render_selection(display_selection) if _shell.object_inspector != null else str(display_selection)
	if _shell.object_inspector_panel != null:
		_shell.object_inspector_panel.show_selection(display_selection, selection_text)

func show_no_selection() -> void:
	if _shell.get_meta("main") != null:
		_shell.get_meta("main").viewport_selection_controller.highlight_viewport_object("")

	if _shell.object_inspector_panel != null:
		_shell.object_inspector_panel.show_no_selection()

func _packet_text_for_object(object_data: Dictionary) -> String:
	if _shell.packet_loader == null or _shell.packet_inspector == null:
		return ""

	var raw_links: Variant = object_data.get("packet_links", [])
	if typeof(raw_links) != TYPE_ARRAY:
		return ""

	var links := raw_links as Array
	if links.is_empty():
		return ""

	var lines := PackedStringArray()
	for link_value: Variant in links:
		if typeof(link_value) != TYPE_DICTIONARY:
			continue

		var link := link_value as Dictionary
		var packet_path := str(link.get("packet_path", ""))
		var packet: Dictionary = _shell.packet_loader.load_packet(packet_path)
		lines.append(_shell.packet_inspector.render_packet(object_data, packet))

	if lines.is_empty():
		return ""

	return "\n" + "\n".join(lines)

func _tree_item_for_object_id(object_id: String) -> TreeItem:
	if _shell.object_tree_controller != null:
		return _shell.object_tree_controller._tree_item_for_object_id(object_id)
	return null

func _tree_item_for_selection(selection: Dictionary) -> TreeItem:
	if _shell.object_tree_controller != null:
		return _shell.object_tree_controller._tree_item_for_selection(selection)
	return null

func _tree_item_is_visible(item: TreeItem) -> bool:
	if item == null:
		return true

	var data: Variant = item.get_metadata(0)
	if typeof(data) == TYPE_DICTIONARY:
		return bool((data as Dictionary).get("visible", true))

	return true
