extends RefCounted

class_name WorkbenchObject

var object_id: String
var object_type: String
var role: String = ""

var display_node: Node = null
var packet_links: Array[String] = []

func _init(
	p_object_id: String,
	p_object_type: String,
	p_role: String = ""
) -> void:
	object_id = p_object_id
	object_type = p_object_type
	role = p_role

func attach_display_node(node: Node) -> void:
	display_node = node

func add_packet_link(packet_id: String) -> void:
	if packet_id not in packet_links:
		packet_links.append(packet_id)

func to_dict() -> Dictionary:
	return {
		"object_id": object_id,
		"object_type": object_type,
		"role": role,
		"packet_links": packet_links
	}