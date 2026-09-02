extends Node

class_name SelectionRaycaster

const OBJECT_ID_META := "object_id"
const WORKBENCH_OBJECT_ID_META := "workbench_object_id"

const SELECTION_META := "selection"

func get_selection_at(
		camera: Camera3D,
		mouse_position: Vector2,
		ray_length: float = 1000.0
) -> Dictionary:
	if camera == null:
		return {}

	var result := _raycast(camera, mouse_position, ray_length)
	if result.is_empty():
		return {}

	var collider: Variant = result.get("collider", null)
	if not (collider is Node):
		return {}

	var selection := _selection_from_node(collider)
	if not selection.is_empty():
		selection["click_position"] = result.get("position", Vector3.ZERO)
		if collider is Node3D:
			selection["global_position"] = collider.global_position

	return selection

func get_object_id_at(
		camera: Camera3D,
		mouse_position: Vector2,
		ray_length: float = 1000.0
) -> String:

	if camera == null:
		return ""

	var result := _raycast(camera, mouse_position, ray_length)
	if result.is_empty():
		return ""

	var collider: Variant = result.get("collider", null)
	if not (collider is Node):
		return ""

	return _object_id_from_node(collider)


func try_select(
		camera: Camera3D,
		mouse_position: Vector2,
		registry,
		selection_manager
) -> void:

	if camera == null:
		return

	var result: Dictionary = _raycast(camera, mouse_position)

	if result.is_empty():
		return

	var collider: Variant = result["collider"]

	if collider == null:
		return

	selection_manager.select_node_from_registry(
		registry,
		collider
	)


func _raycast(
		camera: Camera3D,
		mouse_position: Vector2,
		ray_length: float = 1000.0
) -> Dictionary:
	var origin := camera.project_ray_origin(mouse_position)
	var direction := camera.project_ray_normal(mouse_position)
	var space_state := camera.get_world_3d().direct_space_state

	var query := PhysicsRayQueryParameters3D.create(
		origin,
		origin + direction * ray_length
	)

	return space_state.intersect_ray(query)


func _object_id_from_node(node: Node) -> String:
	var current: Node = node

	while current != null:
		if current.has_meta(WORKBENCH_OBJECT_ID_META):
			return str(current.get_meta(WORKBENCH_OBJECT_ID_META))

		if current.has_meta(OBJECT_ID_META):
			return str(current.get_meta(OBJECT_ID_META))

		current = current.get_parent()

	return ""

func _selection_from_node(node: Node) -> Dictionary:
	var current: Node = node

	while current != null:
		if current.has_meta(SELECTION_META):
			var selection = current.get_meta(SELECTION_META)
			if selection is Dictionary:
				return (selection as Dictionary).duplicate(true)

		if current.has_meta(WORKBENCH_OBJECT_ID_META):
			return {
				"node_kind": "object",
				"object_id": str(current.get_meta(WORKBENCH_OBJECT_ID_META)),
				"id": str(current.get_meta(WORKBENCH_OBJECT_ID_META)),
			}

		if current.has_meta(OBJECT_ID_META):
			return {
				"node_kind": "object",
				"object_id": str(current.get_meta(OBJECT_ID_META)),
				"id": str(current.get_meta(OBJECT_ID_META)),
			}

		current = current.get_parent()

	return {}