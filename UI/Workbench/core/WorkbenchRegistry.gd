extends Node

class_name WorkbenchRegistry

var objects_by_id: Dictionary = {}
var node_to_object_id: Dictionary = {}

var selected_object_id: String = ""

signal object_registered(object_id: String)
signal selection_changed(object_id: String)

func register_object(workbench_object) -> void:
        if workbench_object == null:
                return

        objects_by_id[workbench_object.object_id] = workbench_object

        if workbench_object.display_node != null:
                node_to_object_id[workbench_object.display_node] = workbench_object.object_id

        object_registered.emit(workbench_object.object_id)

func get_object(object_id: String):
        return objects_by_id.get(object_id, null)

func has_object(object_id: String) -> bool:
        return objects_by_id.has(object_id)

func get_object_id_for_node(node: Node) -> String:
        return node_to_object_id.get(node, "")

func select_object(object_id: String) -> void:
        if not objects_by_id.has(object_id):
                return

        selected_object_id = object_id
        selection_changed.emit(object_id)

func select_node(node: Node) -> void:
        var object_id = get_object_id_for_node(node)
        if object_id == "":
                return

        select_object(object_id)

func get_selected_object():
        if selected_object_id == "":
                return null

        return get_object(selected_object_id)

func clear() -> void:
        objects_by_id.clear()
        node_to_object_id.clear()
        selected_object_id = ""
