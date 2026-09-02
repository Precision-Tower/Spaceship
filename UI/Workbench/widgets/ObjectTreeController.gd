extends RefCounted
class_name ObjectTreeController

var _shell


func setup(shell) -> void:
	_shell = shell


func populate() -> void:
	var object_tree := _object_tree()
	if object_tree == null:
		return

	object_tree.clear()

	var session = _session()
	if session == null or session.current_project == null:
		var root := object_tree.create_item()
		_configure_tree_item(root, "Objects", {
			"node_kind": "project",
			"id": "objects",
			"role": "project_root",
			"object_count": 0,
			"total_mass_kg": 0.0,
			"child_groups": [],
			"child_objects": [],
			"raw_data": {}
		})
		var empty := root.create_child()
		empty.set_text(0, "No project loaded")
		empty.set_selectable(0, false)
		print("[Workbench] Object tree built groups=0 objects=0")
		return

	var all_objects: Array[Dictionary] = session.get_objects()
	var objects := _tree_display_objects(all_objects)
	var hierarchy_packet := _first_hierarchy_packet(all_objects)
	var root_child_groups := []
	var hierarchy_groups: Dictionary = {}
	if not hierarchy_packet.is_empty():
		var assembly: Dictionary = hierarchy_packet.get("assembly", {})
		var hierarchy: Dictionary = assembly.get("hierarchy", {})
		hierarchy_groups = hierarchy.get("groups", {})
		var root_group := str(hierarchy.get("root_group", ""))
		if root_group != "":
			root_child_groups.append(root_group)

	var root := object_tree.create_item()
	_configure_tree_item(root, _project_tree_root_label(), _project_tree_metadata(objects, root_child_groups))

	var built_from_hierarchy := false
	if not hierarchy_packet.is_empty():
		built_from_hierarchy = _populate_hierarchy_object_tree(root, objects, hierarchy_packet)

	if not built_from_hierarchy:
		_populate_ghostlab_tree(root, objects)

	print(
		"[Workbench] Object tree built groups=%d objects=%d"
		% [hierarchy_groups.size() if built_from_hierarchy else 0, objects.size()]
	)

func _populate_ghostlab_tree(
		root: TreeItem,
		objects: Array[Dictionary]
) -> void:

	var environment_folder := root.create_child()
	environment_folder.set_text(0, "Environment")

	var objects_folder := root.create_child()
	objects_folder.set_text(0, "Objects")

	var topology_folder := root.create_child()
	topology_folder.set_text(0, "Topology")

	var state_folder := root.create_child()
	state_folder.set_text(0, "Working State")

	for object_data in objects:
		_add_object_tree_item(objects_folder, object_data)

func sync_selection(selection: Dictionary) -> void:
	var object_tree := _object_tree()
	if object_tree == null:
		return

	if _shell != null and bool(_shell.suppress_tree_selection_signal):
		return

	var item := _tree_item_for_selection(selection)
	if item == null or object_tree.get_selected() == item:
		return

	if _shell != null:
		_shell.suppress_tree_selection_signal = true
	item.select(0)
	if _shell != null:
		_shell.suppress_tree_selection_signal = false


func _populate_hierarchy_object_tree(
		root: TreeItem,
		objects: Array[Dictionary],
		packet: Dictionary
) -> bool:
	var assembly: Dictionary = packet.get("assembly", {})
	var hierarchy: Dictionary = assembly.get("hierarchy", {})
	var groups: Dictionary = hierarchy.get("groups", {})
	var root_group := str(hierarchy.get("root_group", ""))

	if groups.is_empty() or root_group == "":
		return false

	var group_children := _group_children_from_hierarchy(groups)
	var objects_by_group := _objects_by_assembly_group(objects)
	var group_items: Dictionary = {}
	_create_group_tree_item(root, root_group, groups, group_children, objects_by_group, group_items)

	for group_id in groups.keys():
		var normalized_group_id := str(group_id)
		if not group_items.has(normalized_group_id):
			_create_group_tree_item(
				root,
				normalized_group_id,
				groups,
				group_children,
				objects_by_group,
				group_items
			)

	for object: Dictionary in objects:
		var parent_item := _tree_parent_for_object(object, group_items, root)
		_add_object_tree_item(parent_item, object)

	var source_parent: TreeItem = group_items.get(root_group, root)
	_add_source_packet_tree_items(source_parent, packet)

	return true


func _add_source_packet_tree_items(parent: TreeItem, packet: Dictionary) -> void:
	var source_packets: Array = packet.get("source_packets", [])
	if source_packets.is_empty():
		return

	var parent_group_id := ""
	var parent_metadata: Variant = parent.get_metadata(0)
	if typeof(parent_metadata) == TYPE_DICTIONARY:
		parent_group_id = str((parent_metadata as Dictionary).get("group_id", ""))

	var folder := parent.create_child()
	_configure_tree_item(folder, "Source Packets", {
		"node_kind": "group",
		"id": "source_packets",
		"group_id": "source_packets",
		"role": "source_packet_collection",
		"parent_group": parent_group_id,
		"object_count": 0,
		"total_mass_kg": 0.0,
		"child_groups": [],
		"child_objects": [],
		"raw_data": {
			"source_packets": source_packets
		}
	})

	for source_packet in source_packets:
		if not source_packet is Dictionary:
			continue

		var source_data := source_packet as Dictionary
		var packet_type := str(source_data.get("packet_type", ""))
		var packet_path := str(source_data.get("packet_path", ""))
		var resolved_path := _resolve_source_packet_path(packet_path, packet)
		var raw_data: Dictionary = source_data.duplicate(true)
		var packet_loader = _packet_loader()
		if packet_loader != null and resolved_path != "":
			raw_data = packet_loader.load_packet(resolved_path)

		var packet_id := packet_type
		if packet_id == "":
			packet_id = packet_path.get_file().get_basename()
		if packet_id == "":
			packet_id = "source_packet"

		var item := folder.create_child()
		_configure_tree_item(item, packet_id, {
			"node_kind": "source_packet",
			"id": packet_id,
			"packet_path": packet_path,
			"resolved_packet_path": resolved_path,
			"role": packet_type,
			"parent_group": "Source Packets",
			"object_count": _packet_object_count(raw_data),
			"total_mass_kg": _packet_total_mass(raw_data),
			"raw_data": raw_data
		})


func _create_group_tree_item(
		parent: TreeItem,
		group_id: String,
		groups: Dictionary,
		group_children: Dictionary,
		objects_by_group: Dictionary,
		group_items: Dictionary
) -> void:
	if group_items.has(group_id):
		return

	var item := parent.create_child()
	var group_data: Dictionary = groups.get(group_id, {})
	_configure_tree_item(
		item,
		_group_display_label(group_id),
		_group_tree_metadata(group_id, group_data, group_children, objects_by_group)
	)
	group_items[group_id] = item

	var children: Array = group_children.get(group_id, [])
	for child_group_id in children:
		_create_group_tree_item(
			item,
			str(child_group_id),
			groups,
			group_children,
			objects_by_group,
			group_items
		)


func _group_tree_metadata(
		group_id: String,
		group_data: Dictionary,
		group_children: Dictionary,
		objects_by_group: Dictionary
) -> Dictionary:
	var recursive_objects := _objects_for_group_recursive(group_id, group_children, objects_by_group)
	var direct_objects: Array = objects_by_group.get(group_id, [])

	return {
		"node_kind": "group",
		"id": group_id,
		"group_id": group_id,
		"role": str(group_data.get("role", group_data.get("status", "group"))),
		"parent_group": _parent_group_id(group_data),
		"object_count": recursive_objects.size(),
		"total_mass_kg": _total_mass_for_objects(recursive_objects),
		"child_groups": group_children.get(group_id, []),
		"child_objects": _object_ids_for_objects(direct_objects),
		"raw_data": group_data
	}


func _tree_display_objects(objects: Array[Dictionary]) -> Array[Dictionary]:
	var display_objects: Array[Dictionary] = []

	for object_data: Dictionary in objects:
		if str(object_data.get("object_type", "")) == "fluid_environment":
			continue
		if str(object_data.get("object_id", "")) == "":
			continue

		display_objects.append(object_data)

	return display_objects


func _objects_by_assembly_group(objects: Array[Dictionary]) -> Dictionary:
	var objects_by_group: Dictionary = {}

	for object_data: Dictionary in objects:
		var group_id := str(object_data.get("assembly_group", ""))
		if group_id == "":
			group_id = str(object_data.get("parent_group", ""))
		if group_id == "":
			continue

		if not objects_by_group.has(group_id):
			objects_by_group[group_id] = []

		objects_by_group[group_id].append(object_data)

	return objects_by_group


func _objects_for_group_recursive(
		group_id: String,
		group_children: Dictionary,
		objects_by_group: Dictionary
) -> Array[Dictionary]:
	var results: Array[Dictionary] = []
	var visited: Dictionary = {}
	_append_objects_for_group(group_id, group_children, objects_by_group, results, visited)
	return results


func _append_objects_for_group(
		group_id: String,
		group_children: Dictionary,
		objects_by_group: Dictionary,
		results: Array[Dictionary],
		visited: Dictionary
) -> void:
	if visited.has(group_id):
		return

	visited[group_id] = true

	var direct_objects: Array = objects_by_group.get(group_id, [])
	for object_data: Dictionary in direct_objects:
		results.append(object_data)

	var children: Array = group_children.get(group_id, [])
	for child_group_id in children:
		_append_objects_for_group(str(child_group_id), group_children, objects_by_group, results, visited)


func _object_ids_for_objects(objects: Array) -> Array:
	var object_ids := []

	for object_data in objects:
		if object_data is Dictionary:
			var object_id := str(object_data.get("object_id", ""))
			if object_id != "":
				object_ids.append(object_id)

	return object_ids


func _total_mass_for_objects(objects: Array) -> float:
	var total := 0.0

	for object_data in objects:
		if object_data is Dictionary and object_data.has("mass_kg"):
			total += float(object_data.get("mass_kg", 0.0))

	return total


func _packet_object_count(packet: Dictionary) -> int:
	var assembly: Dictionary = packet.get("assembly", {})
	var objects: Array = assembly.get("objects", [])
	return objects.size()


func _packet_total_mass(packet: Dictionary) -> Variant:
	var assembly: Dictionary = packet.get("assembly", {})
	var summary: Dictionary = assembly.get("summary", {})
	if summary.has("total_mass_kg"):
		return summary.get("total_mass_kg")

	var objects: Array = assembly.get("objects", [])
	return _total_mass_for_objects(objects)


func _project_tree_root_label() -> String:
	var session = _session()
	if session != null and session.project_name != "":
		return session.project_name

	return "Objects"


func _group_display_label(group_id: String) -> String:
	match group_id:
		"boat_assembly":
			return "Boat"
		"hull":
			return "Hull"
		"subfloor":
			return "Subfloor"
		"deck":
			return "Deck"
		"motor_assembly":
			return "Motor"
		_:
			return group_id


func _tree_item_for_selection(selection: Dictionary) -> TreeItem:
	var object_tree := _object_tree()
	if object_tree == null:
		return null

	var node_kind := str(selection.get("node_kind", ""))
	if node_kind == "object":
		return _tree_item_for_object_id(str(selection.get("object_id", "")))

	var root: TreeItem = object_tree.get_root()
	if root == null:
		return null

	return _find_tree_item_by_key(root, _item_key_from_metadata(selection))


func _tree_item_for_object_id(object_id: String) -> TreeItem:
	var object_tree := _object_tree()
	if object_tree == null:
		return null

	var root: TreeItem = object_tree.get_root()
	if root == null:
		return null

	return _find_tree_item_for_object_id(root, object_id)


func _find_tree_item_for_object_id(parent: TreeItem, object_id: String) -> TreeItem:
	var item: TreeItem = parent.get_first_child()
	while item != null:
		var data: Variant = item.get_metadata(0)
		if typeof(data) == TYPE_DICTIONARY:
			var object_data := data as Dictionary
			if str(object_data.get("object_id", "")) == object_id:
				return item

		var child_match := _find_tree_item_for_object_id(item, object_id)
		if child_match != null:
			return child_match

		item = item.get_next()

	return null


func _find_tree_item_by_key(parent: TreeItem, item_key: String) -> TreeItem:
	if item_key == "":
		return null

	var data: Variant = parent.get_metadata(0)
	if typeof(data) == TYPE_DICTIONARY and _item_key_from_metadata(data as Dictionary) == item_key:
		return parent

	var item: TreeItem = parent.get_first_child()
	while item != null:
		var child_match := _find_tree_item_by_key(item, item_key)
		if child_match != null:
			return child_match

		item = item.get_next()

	return null


func _tree_parent_for_object(
		object_data: Dictionary,
		group_items: Dictionary,
		fallback_parent: TreeItem
) -> TreeItem:
	var candidate_keys := [
		str(object_data.get("assembly_group", "")),
		str(object_data.get("subsystem", "")),
		str(object_data.get("parent_group", ""))
	]

	for key in candidate_keys:
		if key != "" and group_items.has(key):
			return group_items[key]

	return fallback_parent


func _add_object_tree_item(parent: TreeItem, object_data: Dictionary) -> TreeItem:
	var item := parent.create_child()
	var object_id := str(object_data.get("object_id", "missing"))
	_configure_tree_item(item, object_id, {
		"node_kind": "object",
		"id": object_id,
		"object_id": object_id,
		"group_id": str(object_data.get("assembly_group", "")),
		"raw_data": object_data
	})
	return item


func _first_hierarchy_packet(objects: Array[Dictionary]) -> Dictionary:
	for object_data: Dictionary in objects:
		var packet := _first_packet_for_object(object_data)
		if packet.get("error", false):
			continue

		var assembly: Dictionary = packet.get("assembly", {})
		var hierarchy: Dictionary = assembly.get("hierarchy", {})
		if not hierarchy.is_empty():
			return packet

	return {}


func _populate_flat_object_tree(root: TreeItem, objects: Array[Dictionary]) -> void:
	if objects.is_empty():
		var empty := root.create_child()
		empty.set_text(0, "No objects")
		empty.set_selectable(0, false)
		return

	for object: Dictionary in objects:
		_add_object_tree_item(root, object)


func _group_children_from_hierarchy(groups: Dictionary) -> Dictionary:
	var group_children: Dictionary = {}

	for group_id in groups.keys():
		var group_data: Dictionary = groups.get(group_id, {})
		var parent_group := _parent_group_id(group_data)
		if not group_children.has(parent_group):
			group_children[parent_group] = []

		group_children[parent_group].append(str(group_id))

	return group_children


func _parent_group_id(group_data: Dictionary) -> String:
	var parent_group: Variant = group_data.get("parent_group", "")
	if parent_group == null:
		return ""

	return str(parent_group)


func _configure_tree_item(item: TreeItem, label: String, metadata: Dictionary, selectable := true) -> void:
	metadata["base_label"] = label
	if not metadata.has("visible"):
		metadata["visible"] = true

	item.set_metadata(0, metadata)
	item.set_cell_mode(0, TreeItem.CELL_MODE_CHECK)
	item.set_text(0, label)
	item.set_checked(0, bool(metadata.get("visible", true)))
	item.set_editable(0, true)
	item.set_selectable(0, selectable)


func _project_tree_metadata(objects: Array[Dictionary], child_groups: Array) -> Dictionary:
	var session = _session()
	return {
		"node_kind": "project",
		"id": session.project_id if session != null else "project",
		"role": "project_root",
		"parent_group": "",
		"object_count": objects.size(),
		"total_mass_kg": _total_mass_for_objects(objects),
		"child_groups": child_groups,
		"child_objects": _object_ids_for_objects(objects),
		"raw_data": {
			"project_id": session.project_id if session != null else "",
			"project_name": session.project_name if session != null else ""
		}
	}


func _first_packet_for_object(object_data: Dictionary) -> Dictionary:
	var packet_loader = _packet_loader()
	if packet_loader == null:
		return {}

	var links: Array = object_data.get("packet_links", [])

	for link in links:
		if not link is Dictionary:
			continue

		var packet_path := str(link.get("packet_path", ""))
		if packet_path == "":
			continue

		var packet: Dictionary = packet_loader.load_packet(packet_path)
		if not packet.is_empty():
			return packet

	return {}


func _resolve_source_packet_path(packet_path: String, containing_packet: Dictionary) -> String:
	var trimmed := packet_path.strip_edges()
	if trimmed == "":
		return ""

	if trimmed.begins_with("res://") or trimmed.begins_with("user://"):
		return trimmed

	if trimmed.length() >= 3 and trimmed.substr(1, 1) == ":":
		return trimmed

	if trimmed.begins_with("/") or trimmed.begins_with("\\"):
		return trimmed

	var containing_path := str(containing_packet.get("_resolved_packet_path", "")).replace("\\", "/")
	var base_dir := containing_path.get_base_dir()
	if base_dir == "":
		return trimmed

	return base_dir.path_join(trimmed.replace("\\", "/"))


func _item_key_from_metadata(metadata: Dictionary) -> String:
	var node_kind := str(metadata.get("node_kind", metadata.get("tree_item_type", "")))
	match node_kind:
		"object":
			return "object:" + str(metadata.get("object_id", metadata.get("id", "")))
		"group":
			return "group:" + str(metadata.get("group_id", metadata.get("id", "")))
		"source_packet":
			var packet_key := str(metadata.get("packet_path", ""))
			if packet_key == "":
				packet_key = str(metadata.get("id", ""))
			return "source_packet:" + packet_key
		"project":
			return "project:" + str(metadata.get("id", ""))
		_:
			var item_id := str(metadata.get("id", ""))
			if node_kind == "" or item_id == "":
				return ""
			return node_kind + ":" + item_id


func _object_tree() -> Tree:
	if _shell == null:
		return null

	return _shell.object_tree


func _session():
	if _shell == null:
		return null

	return _shell.session


func _packet_loader():
	if _shell == null:
		return null

	return _shell.packet_loader
