extends Node

# Preload Scripts
const WorkbenchShellScript = preload("res://Workbench/scenes/Workbench.gd")
const WorkbenchSessionScript = preload("res://Workbench/core/WorkbenchSession.gd")

const CameraControllerScript = preload("res://Workbench/interaction/CameraController.gd")
const SelectionRaycasterScript = preload("res://Workbench/selection/SelectionRaycaster.gd")

const PacketLoaderScript = preload("res://Workbench/packet/PacketLoader.gd")
const GhostCommandExporterScript = preload("res://Workbench/packet/GhostCommandExporter.gd")
const PacketInspectorScript = preload("res://Workbench/inspectors/PacketInspector.gd")
const ObjectInspectorScript = preload("res://Workbench/inspectors/ObjectInspector.gd")
const PacketGeometryRendererScript = preload("res://Workbench/rendering/PacketGeometryRenderer.gd")

const ObjectTreeControllerScript = preload("res://Workbench/widgets/ObjectTreeController.gd")
const ViewportObjectRendererScript = preload("res://Workbench/rendering/ViewportObjectRenderer.gd")
const GhostCommandControllerScript = preload("res://Workbench/interaction/GhostCommandController.gd")
const GhostCommandDialogsScript = preload("res://Workbench/interaction/GhostCommandDialogs.gd")
const ViewportSelectionControllerScript = preload("res://Workbench/selection/ViewportSelectionController.gd")
const PacketDisplayResolverScript = preload("res://Workbench/packet/PacketDisplayResolver.gd")
const ProjectActionControllerScript = preload("res://Workbench/actions/ProjectActionController.gd")
const SimulationPlaybackControllerScript = preload("res://Workbench/interaction/SimulationPlaybackController.gd")
const ViewportInputHelperScript = preload("res://Workbench/interaction/ViewportInputHelper.gd")
const ObjectTreeVisibilityControllerScript = preload("res://Workbench/widgets/ObjectTreeVisibilityController.gd")
const AuditControllerScript = preload("res://Workbench/audit/AuditController.gd")

const ScreenshotControllerScript = preload("res://shared/ScreenshotController.gd")
# Member Variables
var shell
var session

# Controllers
var object_tree_controller
var viewport_object_renderer
var ghost_command_controller
var viewport_selection_controller
var packet_display_resolver
var project_action_controller
var simulation_playback_controller
var viewport_input_helper
var object_tree_visibility_controller
var audit_controller

var screenshot_controller
func _ready() -> void:
	call_deferred("_force_kiosk_window")
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
	print("[Main] Requested fullscreen mode.")
	print("[Main] Screen size: ", DisplayServer.screen_get_size())
	print("[Main] Window size: ", DisplayServer.window_get_size())
	print("[Main] Initializing app spine...")

	# 1. Create the session
	session = WorkbenchSessionScript.new()

	# 2. Instantiate and add the Workbench scene (the shell)
	var scene_res = load("res://Workbench/scenes/Workbench.tscn")
	shell = scene_res.instantiate()
	add_child(shell)

	# Pass main reference to the shell so controllers can query it
	shell.set_meta("main", self)

	# TEMP_COMPAT: Expose session and other objects on shell
	shell.session = session

	# 3. Instantiate helper scripts & renderers and assign them to shell (acting as references)
	shell.packet_loader = PacketLoaderScript.new()
	shell.ghost_command_exporter = GhostCommandExporterScript.new()
	shell.packet_inspector = PacketInspectorScript.new()
	shell.object_inspector = ObjectInspectorScript.new()
	shell.geometry_renderer = PacketGeometryRendererScript.new()

	# Camera controller & Selection raycaster need to be added to the scene tree
	var camera_controller = CameraControllerScript.new()
	shell.add_child(camera_controller)
	shell.camera_controller = camera_controller
	camera_controller.setup(shell.viewport_camera, shell.viewport_container, Vector3.ZERO)

	var selection_raycaster = SelectionRaycasterScript.new()
	shell.add_child(selection_raycaster)
	shell.selection_raycaster = selection_raycaster

	# 4. Instantiate and setup controllers
	viewport_input_helper = ViewportInputHelperScript.new()
	viewport_input_helper.setup(shell)

	object_tree_controller = ObjectTreeControllerScript.new()
	object_tree_controller.setup(shell)
	shell.object_tree_controller = object_tree_controller

	viewport_object_renderer = ViewportObjectRendererScript.new()
	viewport_object_renderer.setup(shell)
	shell.viewport_object_renderer = viewport_object_renderer

	ghost_command_controller = GhostCommandControllerScript.new()
	ghost_command_controller.setup(shell, session, self)

	var ghost_command_dialogs = GhostCommandDialogsScript.new()
	ghost_command_dialogs.setup(ghost_command_controller, shell)
	ghost_command_controller.ghost_command_dialogs = ghost_command_dialogs

	viewport_selection_controller = ViewportSelectionControllerScript.new()
	viewport_selection_controller.setup(shell, session, self, viewport_input_helper, ghost_command_controller)

	packet_display_resolver = PacketDisplayResolverScript.new()
	packet_display_resolver.setup(shell, session)

	project_action_controller = ProjectActionControllerScript.new()
	project_action_controller.setup(shell, session, object_tree_controller, viewport_object_renderer, self)

	simulation_playback_controller = SimulationPlaybackControllerScript.new()
	simulation_playback_controller.setup(shell, self)

	object_tree_visibility_controller = ObjectTreeVisibilityControllerScript.new()
	object_tree_visibility_controller.setup(shell, session, self)

	audit_controller = AuditControllerScript.new()
	audit_controller.setup(shell, session, self)


	screenshot_controller = ScreenshotControllerScript.new()
	add_child(screenshot_controller)
	# 5. Wire Signals
	session.project_loaded.connect(_on_session_project_loaded)
	session.selection_changed.connect(_on_session_selection_changed)

	# Wire visual shell panel & tree signals
	if shell.object_inspector_panel != null:
		shell.object_inspector_panel.save_override_requested.connect(project_action_controller.on_save_override_pressed)
		shell.object_inspector_panel.regenerate_packets_requested.connect(project_action_controller.on_regenerate_packets_pressed)
		shell.object_inspector_panel.reload_project_requested.connect(project_action_controller.on_reload_project_pressed)
		shell.object_inspector_panel.position_apply_requested.connect(project_action_controller.on_position_apply_requested)

	if shell.object_tree != null:
		shell.object_tree.item_selected.connect(object_tree_visibility_controller.on_object_tree_item_selected)
		shell.object_tree.item_edited.connect(object_tree_visibility_controller.on_object_tree_item_edited)

	if shell.create_context_menu != null:
		shell.create_context_menu.create_command_requested.connect(ghost_command_controller.on_create_command_requested)

	if shell.ghost_action_menu != null:
		shell.ghost_action_menu.id_pressed.connect(ghost_command_controller.on_ghost_action_menu_id_pressed)

	if shell.port_action_menu != null:
		shell.port_action_menu.id_pressed.connect(_on_port_action_selected)

	# 6. Load default project
	project_action_controller.load_project_from_script()

func _input(event: InputEvent) -> void:
	if screenshot_controller != null and screenshot_controller.handle_input(event):
		get_viewport().set_input_as_handled()
		return

	if audit_controller != null and audit_controller.handle_input(event):
		get_viewport().set_input_as_handled()
		return

	if ghost_command_controller != null and ghost_command_controller.handle_ghost_move_input(event):
		get_viewport().set_input_as_handled()
		return

	if object_tree_visibility_controller != null and object_tree_visibility_controller.handle_visibility_shortcut(event):
		get_viewport().set_input_as_handled()
		return

	if shell != null and shell.camera_controller != null:
		if shell.camera_controller.handle_input(event):
			get_viewport().set_input_as_handled()
			return

	if viewport_selection_controller != null and viewport_selection_controller.handle_viewport_selection_input(event):
		get_viewport().set_input_as_handled()

func _process(delta: float) -> void:
	if simulation_playback_controller == null or not simulation_playback_controller.simulation_playing:
		return

	simulation_playback_controller.simulation_time_s += delta
	simulation_playback_controller.apply_simulation_frame(simulation_playback_controller.simulation_time_s)

func load_project(next_project) -> void:
	if ghost_command_controller != null:
		ghost_command_controller.clear_ghosts()
	session.load_project(next_project)

func _on_session_project_loaded(_project_id: String) -> void:
	if object_tree_controller != null:
		object_tree_controller.populate()
	if viewport_object_renderer != null:
		viewport_object_renderer.render_project_objects()
	call_deferred("_select_startup_object")

func _on_session_selection_changed(selection: Dictionary) -> void:
	if selection.is_empty():
		packet_display_resolver.show_no_selection()
		return

	var node_kind := str(selection.get("node_kind", "unknown"))
	var selection_id := str(selection.get("id", selection.get("object_id", "missing")))
	print("[Main] selected node_kind=%s id=%s" % [node_kind, selection_id])

	if object_tree_controller != null:
		object_tree_controller.sync_selection(selection)
	packet_display_resolver.show_inspectable_selection(selection)

func _select_startup_object() -> void:
	if session == null or session.current_project == null:
		packet_display_resolver.show_no_selection()
		return

	var startup_object_id := ""
	if not session.get_object("water_environment_001").is_empty():
		startup_object_id = "water_environment_001"
	else:
		var objects: Array[Dictionary] = session.get_objects()
		if not objects.is_empty():
			startup_object_id = str(objects[0].get("object_id", ""))

	if startup_object_id == "":
		packet_display_resolver.show_no_selection()
		return

	if not viewport_selection_controller.select_object_by_id(startup_object_id):
		session.select_object(startup_object_id)

func _on_port_action_selected(id: int) -> void:
	var selection = viewport_selection_controller.selected_port_selection
	if selection.is_empty():
		return

	if id == 1:
		ghost_command_controller.start_pipe_draw_from_port(selection)
		return

	if id == 2:
		ghost_command_controller.start_fitting_command(selection, "elbow_90")
		return

	if id == 4:
		ghost_command_controller.start_pipe_trim_command(selection, -1.0)
		return

	if id == 5:
		ghost_command_controller.start_pipe_trim_command(selection, 1.0)
		return

	if id == 6:
		ghost_command_controller.start_od_edit_command(selection)
		return

	print("[WorkbenchGhostPipe] port action disabled id=%d" % id)

func _force_kiosk_window() -> void:
	await get_tree().process_frame
	await get_tree().process_frame

	var screen_size := DisplayServer.screen_get_size()

	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
	DisplayServer.window_set_flag(
		DisplayServer.WINDOW_FLAG_BORDERLESS,
		true
	)
	DisplayServer.window_set_position(Vector2i.ZERO)
	DisplayServer.window_set_size(screen_size)

	print("[Main] Forced kiosk window.")
	print("[Main] Screen size: ", screen_size)
	print("[Main] Window size: ", DisplayServer.window_get_size())
	print("[Main] Window position: ", DisplayServer.window_get_position())
