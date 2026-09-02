extends Node
class_name CameraController

@export var min_distance := 1.25
@export var max_distance := 40.0
@export var zoom_step := 0.12
@export var orbit_sensitivity := 0.01
@export var pan_sensitivity := 0.0015

var camera: Camera3D
var input_region: Control
var target := Vector3.ZERO
var distance := 8.0
var yaw := 0.0
var pitch := 0.0
var orbiting := false
var panning := false


func setup(p_camera: Camera3D, p_input_region: Control = null, p_target: Vector3 = Vector3.ZERO) -> void:
	camera = p_camera
	input_region = p_input_region
	target = p_target

	if camera == null:
		return

	var offset := camera.global_position - target
	distance = clamp(offset.length(), min_distance, max_distance)

	if distance > 0.0:
		yaw = atan2(offset.x, offset.z)
		pitch = asin(clamp(offset.y / distance, -1.0, 1.0))

	_update_camera()


func handle_input(event: InputEvent) -> bool:
	if camera == null:
		return false

	if event is InputEventMouseButton:
		return _handle_mouse_button(event)

	if event is InputEventMouseMotion:
		return _handle_mouse_motion(event)

	return false


func _handle_mouse_button(event: InputEventMouseButton) -> bool:
	if event.button_index == MOUSE_BUTTON_MIDDLE:
		var was_orbiting := orbiting
		orbiting = event.pressed and _event_in_region(event)
		return orbiting or was_orbiting

	if event.button_index == MOUSE_BUTTON_RIGHT:
		var was_panning := panning
		panning = event.pressed and _event_in_region(event)
		return panning or was_panning

	if not event.pressed or not _event_in_region(event):
		return false

	if event.button_index == MOUSE_BUTTON_WHEEL_UP:
		_zoom_toward_mouse(event.position, 1.0 - zoom_step)
		return true

	if event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
		distance = clamp(distance * (1.0 + zoom_step), min_distance, max_distance)
		_update_camera()
		return true

	return false

func _zoom_toward_mouse(mouse_position: Vector2, zoom_factor: float) -> void:
	if camera == null:
		return

	var focus := _mouse_world_point(mouse_position)
	var target_blend := 0.25

	target = target.lerp(focus, target_blend)
	distance = clamp(distance * zoom_factor, min_distance, max_distance)

	_update_camera()

func _mouse_world_point(mouse_position: Vector2) -> Vector3:
	if camera == null:
		return target

	var origin := camera.project_ray_origin(mouse_position)
	var direction := camera.project_ray_normal(mouse_position)

	# Stable navigation plane through current target.
	# Avoids raycast hits jumping between water, barrels, frame, etc.
	var plane := Plane(Vector3.UP, target.y)
	var plane_hit = plane.intersects_ray(origin, direction)

	if plane_hit != null:
		return plane_hit

	return target

func _handle_mouse_motion(event: InputEventMouseMotion) -> bool:
	if orbiting:
		yaw -= event.relative.x * orbit_sensitivity
		pitch = clamp(
			pitch - event.relative.y * orbit_sensitivity,
			deg_to_rad(-80.0),
			deg_to_rad(80.0)
		)
		_update_camera()
		return true

	if panning:
		var basis := camera.global_transform.basis
		var pan_scale := distance * pan_sensitivity
		target += (-basis.x * event.relative.x + basis.y * event.relative.y) * pan_scale
		_update_camera()
		return true

	return false


func _update_camera() -> void:
	if camera == null:
		return

	var cos_pitch := cos(pitch)
	var offset := Vector3(
		sin(yaw) * cos_pitch,
		sin(pitch),
		cos(yaw) * cos_pitch
	) * distance

	camera.global_position = target + offset
	camera.look_at(target, Vector3.UP)


func _event_in_region(event: InputEvent) -> bool:
	if input_region == null:
		return true

	if not input_region.is_inside_tree():
		return true

	if event is InputEventMouseButton:
		return input_region.get_global_rect().has_point(event.position)

	if event is InputEventMouseMotion:
		return input_region.get_global_rect().has_point(event.position)

	return false
