extends RefCounted
class_name WorkbenchSession

signal project_loaded(project_id: String)
signal selection_changed(selection: Dictionary)

var current_project = null
var project_id: String = ""
var project_name: String = ""

var objects: Array[Dictionary] = []
var objects_by_id: Dictionary = {}

var selected_object_id: String = ""
var selected_item: Dictionary = {}


func load_project(project) -> void:
	current_project = project
	project_id = ""
	project_name = ""
	objects.clear()
	objects_by_id.clear()
	selected_object_id = ""
	selected_item.clear()

	if current_project != null:
		project_id = str(current_project.get("project_id"))
		project_name = str(current_project.get("project_name"))

		if current_project.has_method("get_objects"):
			for object: Dictionary in current_project.get_objects():
				objects.append(object)

				var object_id := str(object.get("object_id", ""))
				if object_id != "":
					objects_by_id[object_id] = object

	project_loaded.emit(project_id)


func get_objects() -> Array[Dictionary]:
	return objects


func get_object(object_id: String) -> Dictionary:
	if objects_by_id.has(object_id):
		return objects_by_id[object_id]

	return {}


func select_object(object_id: String) -> void:
	if object_id != "" and not objects_by_id.has(object_id):
		return

	if object_id == "":
		clear_selection()
		return

	select_item({
		"node_kind": "object",
		"id": object_id,
		"object_id": object_id,
		"group_id": str(objects_by_id[object_id].get("assembly_group", "")),
		"raw_data": objects_by_id[object_id]
	})


func select_item(item_data: Dictionary) -> void:
	selected_item = item_data.duplicate(true)
	selected_object_id = ""

	if str(selected_item.get("node_kind", "")) == "object":
		selected_object_id = str(selected_item.get("object_id", ""))

	selection_changed.emit(selected_item)


func clear_selection() -> void:
	selected_object_id = ""
	selected_item.clear()
	selection_changed.emit({})


func get_selected_object() -> Dictionary:
	if selected_object_id == "":
		return {}

	return get_object(selected_object_id)


func get_selected_item() -> Dictionary:
	return selected_item

func register_object(object_data: Dictionary) -> void:
	var object_id := str(object_data.get("object_id", ""))
	if object_id == "":
		return

	if not objects_by_id.has(object_id):
		objects.append(object_data)

	objects_by_id[object_id] = object_data


func remove_object(object_id: String) -> void:
	if object_id == "":
		return

	objects_by_id.erase(object_id)

	for i in range(objects.size() - 1, -1, -1):
		if str(objects[i].get("object_id", "")) == object_id:
			objects.remove_at(i)