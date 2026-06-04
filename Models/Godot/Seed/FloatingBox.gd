extends Node3D

const HOVER_EVENT := "hover_reported_not_validated"
const CENTER := Vector3(0.0, 1.05, 0.0)

@onready var barrel: Node3D = $HoverSpace/FloatingBarrel
@onready var camera_pivot: Node3D = $CameraPivot
@onready var camera: Camera3D = $CameraPivot/Camera3D
@onready var observer_surface = $CanvasLayer/ObserverSurface

@onready var top_button: Button = $CanvasLayer/RightControls/Panel/MarginContainer/VBox/TopViewButton
@onready var left_button: Button = $CanvasLayer/RightControls/Panel/MarginContainer/VBox/OrbitRow/LeftOrbitButton
@onready var right_button: Button = $CanvasLayer/RightControls/Panel/MarginContainer/VBox/OrbitRow/RightOrbitButton
@onready var bottom_button: Button = $CanvasLayer/RightControls/Panel/MarginContainer/VBox/BottomViewButton

var yaw := -35.0
var pitch := -24.0
var camera_distance := 7.2
var drag_active := false
var drag_sensitivity := 0.22
var orbit_step := 22.5

func _ready() -> void:
	top_button.pressed.connect(_on_top_view_pressed)
	bottom_button.pressed.connect(_on_bottom_view_pressed)
	left_button.pressed.connect(_on_left_orbit_pressed)
	right_button.pressed.connect(_on_right_orbit_pressed)

	observer_surface.set_runtime_event(HOVER_EVENT)
	observer_surface.set_view_mode("angled_inspection")
	observer_surface.set_zoom_value(camera_distance)
	_apply_camera_transform()

func _process(delta: float) -> void:
	# Sustained hover remains visually stable, but slightly wrong by design:
	# small timing asymmetry and drifting phase prevent clean physical elegance.
	var t := Time.get_ticks_msec() / 1000.0
	var drift := sin(t * 0.71 + sin(t * 0.17) * 0.22) * 0.055
	var asym := sin(t * 1.94) * 0.018
	barrel.position = Vector3(0.0, 1.1 + drift + asym, 0.0)
	barrel.rotation_degrees.y = fmod(t * 9.0, 360.0)
	barrel.rotation_degrees.z = sin(t * 0.63) * 1.8

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP and event.pressed:
			_zoom(-0.45)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN and event.pressed:
			_zoom(0.45)
		elif event.button_index == MOUSE_BUTTON_MIDDLE:
			drag_active = event.pressed
			if drag_active:
				observer_surface.set_view_mode("middle_drag_orbit")
	elif event is InputEventMouseMotion and drag_active:
		yaw -= event.relative.x * drag_sensitivity
		pitch = clamp(pitch - event.relative.y * drag_sensitivity, -86.0, 86.0)
		observer_surface.set_view_mode("manual_orbit")
		_apply_camera_transform()

func _zoom(delta_distance: float) -> void:
	camera_distance = clamp(camera_distance + delta_distance, 3.2, 12.0)
	observer_surface.set_zoom_value(camera_distance)
	_apply_camera_transform()

func _on_top_view_pressed() -> void:
	yaw = 0.0
	pitch = -89.0
	observer_surface.set_view_mode("top_down_z_axis")
	_apply_camera_transform()

func _on_bottom_view_pressed() -> void:
	yaw = 0.0
	pitch = 89.0
	observer_surface.set_view_mode("bottom_up_z_axis")
	_apply_camera_transform()

func _on_left_orbit_pressed() -> void:
	yaw -= orbit_step
	observer_surface.set_view_mode("left_orbit")
	_apply_camera_transform()

func _on_right_orbit_pressed() -> void:
	yaw += orbit_step
	observer_surface.set_view_mode("right_orbit")
	_apply_camera_transform()

func _apply_camera_transform() -> void:
	camera_pivot.global_position = CENTER
	camera_pivot.rotation_degrees = Vector3(pitch, yaw, 0.0)
	camera.position = Vector3(0.0, 0.0, camera_distance)
	camera.look_at(camera_pivot.global_position, Vector3.UP)
