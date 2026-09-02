extends RefCounted
class_name GhostCommandExporter

const EVIDENCE_STATE := "ui_ghost_candidate"
const SOURCE := "UI/Workbench"
const PROHIBITED_INTERPRETATIONS := [
	"ghost_candidate_equals_engineering_object",
	"ui_position_equals_validated_geometry",
	"candidate_command_equals_packet_mutation",
	"visual_object_equals_physical_truth",
]


func export_ghost_commands(ghosts: Array, output_path: String) -> int:
	var commands := []

	for ghost_value in ghosts:
		if not (ghost_value is Node3D):
			continue

		var ghost := ghost_value as Node3D
		if not is_instance_valid(ghost):
			continue

		commands.append(_command_for_ghost(ghost))

	var packet := {
		"packet_type": "workbench_candidate_commands",
		"evidence_state": EVIDENCE_STATE,
		"source": SOURCE,
		"commands": commands,
		"prohibited_interpretations": PROHIBITED_INTERPRETATIONS,
	}

	var file := FileAccess.open(output_path, FileAccess.WRITE)
	if file == null:
		push_warning("Could not write ghost candidate commands: " + output_path)
		return -1

	file.store_string(JSON.stringify(packet, "\t"))
	file.close()

	return commands.size()


func _command_for_ghost(ghost: Node3D) -> Dictionary:
	var category := str(ghost.get_meta("category", ""))
	var item := str(ghost.get_meta("item", ""))
	var position := _vector3_to_dict(ghost.position)
	var command := {
		"command_type": _command_type(category, item),
		"category": category,
		"item": item,
		"object_id": str(ghost.get_meta("object_id", ghost.name)),
		"position_m": position,
		"rotation_degrees": _vector3_to_dict(ghost.rotation_degrees),
		"scale_m": _vector3_to_dict(ghost.scale),
		"source_state": "workbench_ghost",
		"world_position": position,
		"evidence_state": EVIDENCE_STATE,
	}

	if category == "Primitives":
		command["primitive"] = item

	if category == "Objects":
		command["object_type"] = item

	var metadata_position = ghost.get_meta("world_position", null)
	if metadata_position is Vector3:
		command["world_position"] = _vector3_to_dict(metadata_position)

	return command


func _command_type(category: String, item: String) -> String:
	if category == "Primitives":
		return "create_primitive"

	if category == "Objects":
		match item:
			"pipe":
				return "create_pipe_candidate"
			"barrel":
				return "create_barrel_candidate"
			_:
				return "create_object"

	return "create_object"


func _vector3_to_dict(value: Vector3) -> Dictionary:
	return {
		"x": value.x,
		"y": value.y,
		"z": value.z,
	}
