extends RefCounted
class_name PacketLink

var object_id: String = ""
var packet_type: String = ""
var packet_path: String = ""
var packet_role: String = ""


func _init(
		p_object_id: String = "",
		p_packet_type: String = "",
		p_packet_path: String = "",
		p_packet_role: String = ""
) -> void:
	object_id = p_object_id
	packet_type = p_packet_type
	packet_path = p_packet_path
	packet_role = p_packet_role


func to_dict() -> Dictionary:
	return {
		"object_id": object_id,
		"packet_type": packet_type,
		"packet_path": packet_path,
		"packet_role": packet_role
	}
