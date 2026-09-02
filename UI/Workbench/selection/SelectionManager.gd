extends Node

class_name SelectionManager

var selected_object_id: String = ""
var selected_node: Node = null

signal selection_changed(object_id: String, node: Node)
signal selection_cleared

func select_object(object_id: String, node: Node = null) -> void:
        if object_id == "":
                clear_selection()
                return

        selected_object_id = object_id
        selected_node = node
        selection_changed.emit(object_id, node)

func select_from_registry(registry, object_id: String) -> void:
        if registry == null:
                return

        var obj = registry.get_object(object_id)
        if obj == null:
                return

        select_object(object_id, obj.display_node)

func select_node_from_registry(registry, node: Node) -> void:
        if registry == null or node == null:
                return

        var object_id = registry.get_object_id_for_node(node)
        if object_id == "":
                return

        select_from_registry(registry, object_id)

func get_selected_object_id() -> String:
        return selected_object_id

func get_selected_node() -> Node:
        return selected_node

func has_selection() -> bool:
        return selected_object_id != ""

func clear_selection() -> void:
        selected_object_id = ""
        selected_node = null
        selection_cleared.emit()
