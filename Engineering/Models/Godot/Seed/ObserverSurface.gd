extends Control

@onready var packet_value: Label = $Panel/MarginContainer/VBox/PacketRow/PacketValue
@onready var dirty_value: Label = $Panel/MarginContainer/VBox/DirtyRow/DirtyValue
@onready var event_value: Label = $Panel/MarginContainer/VBox/EventBlock/EventValue
@onready var uncertainty_value: Label = $Panel/MarginContainer/VBox/UncertaintyBlock/UncertaintyValue
@onready var contamination_value: Label = $Panel/MarginContainer/VBox/ContaminationBlock/ContaminationValue
@onready var warning_value: Label = $Panel/MarginContainer/VBox/WarningRow/WarningValue
@onready var view_mode_value: Label = $Panel/MarginContainer/VBox/ViewRow/ViewModeValue
@onready var zoom_value: Label = $Panel/MarginContainer/VBox/ZoomRow/ZoomValue

func _ready() -> void:
	packet_value.text = "FloatPressure_001"
	dirty_value.text = "visual_hover_not_validated"
	event_value.text = "hover_reported_not_validated"
	uncertainty_value.text = "OBSERVED: visual hover behavior only\nhover_not_validation\nruntime_motion_not_physics_truth\nunresolveds_remain_active"
	contamination_value.text = "water_plane_is_context_not_evidence\nbarrel_visual_does_not_create_buoyancy_claim\nshadow_is_spatial_anchoring_only"
	warning_value.text = "true"
	view_mode_value.text = "angled_inspection"
	zoom_value.text = "7.20"

func set_runtime_event(value: String) -> void:
	if is_inside_tree():
		event_value.text = value

func set_view_mode(value: String) -> void:
	if is_inside_tree():
		view_mode_value.text = value

func set_zoom_value(value: float) -> void:
	if is_inside_tree():
		zoom_value.text = str(snapped(value, 0.01))
