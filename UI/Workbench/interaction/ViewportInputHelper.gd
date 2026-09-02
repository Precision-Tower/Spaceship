extends RefCounted
class_name ViewportInputHelper

var _shell

func setup(shell) -> void:
	_shell = shell

func empty_viewport_world_position(viewport_position: Vector2) -> Vector3:
	if _shell == null or _shell.viewport_camera == null:
		return Vector3.ZERO

	var origin = _shell.viewport_camera.project_ray_origin(viewport_position)
	var direction = _shell.viewport_camera.project_ray_normal(viewport_position)
	var plane_y = 0.0

	if _shell.camera_controller != null:
		plane_y = _shell.camera_controller.target.y

	var plane = Plane(Vector3.UP, plane_y)
	var plane_hit = plane.intersects_ray(origin, direction)

	if plane_hit != null:
		return plane_hit

	if _shell.camera_controller != null:
		return _shell.camera_controller.target

	return Vector3(origin + direction * 10.0)

func to_subviewport_position(global_position: Vector2) -> Vector2:
	if _shell == null or _shell.viewport_container == null or _shell.viewport == null:
		return Vector2.ZERO
	var rect = _shell.viewport_container.get_global_rect()
	if rect.size.x <= 0.0 or rect.size.y <= 0.0:
		return Vector2.ZERO

	var local_position = global_position - rect.position
	var viewport_size = Vector2(float(_shell.viewport.size.x), float(_shell.viewport.size.y))

	if viewport_size.x <= 0.0 or viewport_size.y <= 0.0:
		viewport_size = rect.size

	return Vector2(
		local_position.x * viewport_size.x / rect.size.x,
		local_position.y * viewport_size.y / rect.size.y
	)

func closest_point_on_axis_to_ray(
		line_point: Vector3,
		axis: Vector3,
		ray_origin: Vector3,
		ray_direction: Vector3
) -> Vector3:
	var axis_direction = axis.normalized()
	var ray_direction_normalized = ray_direction.normalized()
	var offset = line_point - ray_origin
	var a = axis_direction.dot(axis_direction)
	var b = axis_direction.dot(ray_direction_normalized)
	var c = ray_direction_normalized.dot(ray_direction_normalized)
	var d = axis_direction.dot(offset)
	var e = ray_direction_normalized.dot(offset)
	var denominator = a * c - b * b

	if abs(denominator) < 0.00001:
		return line_point

	var line_distance = (b * e - c * d) / denominator
	return line_point + axis_direction * line_distance
