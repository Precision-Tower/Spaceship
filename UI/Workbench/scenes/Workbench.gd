extends Control
class_name WorkbenchShell

@export var project_script: Script

const WorkbenchShellBuilderScript = preload("res://Workbench/layout/WorkbenchShellBuilder.gd")

# Expose shell node references (exposes visual components)
var viewport
var viewport_container
var viewport_camera
var project_objects_root
var ghost_root
var object_tree
var left_panel
var right_panel_split
var object_inspector_panel
var create_context_menu
var ghost_action_menu
var port_action_menu

# Controllers/helpers populated by Main.gd (provided for TEMP_COMPAT)
var session
var shell_builder
var object_tree_controller
var viewport_object_renderer
var camera_controller
var selection_raycaster
var packet_loader
var ghost_command_exporter
var packet_inspector
var object_inspector
var geometry_renderer
var ghost_renderer

# Rendering / interaction state variables (provided for TEMP_COMPAT)
var object_nodes_by_id: Dictionary = {}
var default_materials_by_id: Dictionary = {}
var highlight_material: StandardMaterial3D
var environment_node: Node3D

# Simulation playback state variables (provided for TEMP_COMPAT)
var simulation_frames_by_id: Dictionary = {}
var simulation_time_s: float = 0.0
var simulation_playing: bool = true

# Signal suppression state variables
var suppress_tree_selection_signal := false
var suppress_tree_edit_signal := false

func _ready() -> void:
	print("[WorkbenchShell] Building layout...")
	shell_builder = WorkbenchShellBuilderScript.new()
	shell_builder.build(self)

# TEMP_COMPAT: Deferred reload callback routing back to main controller
func _select_object_after_reload(object_id: String) -> void:
	if has_meta("main"):
		var main = get_meta("main")
		if main.project_action_controller != null:
			main.project_action_controller._select_object_after_reload(object_id)
