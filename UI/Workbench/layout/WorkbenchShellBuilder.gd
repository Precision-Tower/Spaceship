extends RefCounted
class_name WorkbenchShellBuilder

const WorkbenchPathsScript = preload("res://Workbench/config/WorkbenchPaths.gd")
const WorkbenchConstantsScript = preload("res://Workbench/config/WorkbenchConstants.gd")
const CreateContextMenuScript = preload("res://Workbench/interaction/CreateContextMenu.gd")
const GhostPrimitiveRendererScript = preload("res://Workbench/rendering/GhostPrimitiveRenderer.gd")
const CoordinateHelperScript = preload("res://Workbench/rendering/CoordinateHelper.gd")
const LeftPanelScript = preload("res://Workbench/inspectors/LeftPanel.gd")
const ObjectInspectorPanelScript = preload("res://Workbench/inspectors/ObjectInspectorPanel.gd")

var _shell


func build(shell) -> void:
	_shell = shell
	_shell.set_anchors_preset(Control.PRESET_FULL_RECT)

	var root := HSplitContainer.new()
	root.name = "WorkbenchRoot"
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.split_offset = 176
	root.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	root.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_shell.add_child(root)

	root.add_child(_left_status_rail())

	var work_split := HSplitContainer.new()
	work_split.name = "ViewportAndInspectorSplit"
	work_split.split_offset = 880
	work_split.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	work_split.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(work_split)

	work_split.add_child(_center_viewport_container())
	work_split.add_child(_right_panel())

	_create_context_menus()


func _center_viewport_container() -> Control:
	var frame := PanelContainer.new()
	frame.name = "Center3DViewportContainer"
	frame.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	frame.size_flags_vertical = Control.SIZE_EXPAND_FILL

	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.025, 0.028, 0.032, 1.0)
	style.border_color = WorkbenchConstantsScript.COLOR_LINE
	style.set_border_width_all(1)
	frame.add_theme_stylebox_override("panel", style)

	_shell.viewport_container = SubViewportContainer.new()
	_shell.viewport_container.name = "SubViewportContainer"
	_shell.viewport_container.stretch = true
	_shell.viewport_container.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_shell.viewport_container.size_flags_vertical = Control.SIZE_EXPAND_FILL
	frame.add_child(_shell.viewport_container)

	_shell.viewport = SubViewport.new()
	_shell.viewport.name = "WorkbenchViewport"
	_shell.viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	_shell.viewport_container.add_child(_shell.viewport)

	var world := Node3D.new()
	world.name = "WorldRoot"
	_shell.viewport.add_child(world)

	var coordinate_helper = CoordinateHelperScript.new()
	coordinate_helper.name = "CoordinateHelper"
	world.add_child(coordinate_helper)

	_shell.project_objects_root = Node3D.new()
	_shell.project_objects_root.name = "ProjectObjects"
	_shell.viewport.add_child(_shell.project_objects_root)

	_shell.ghost_root = Node3D.new()
	_shell.ghost_root.name = "GhostObjects"
	_shell.viewport.add_child(_shell.ghost_root)
	_shell.ghost_renderer = GhostPrimitiveRendererScript.new()

	_shell.viewport_camera = Camera3D.new()
	_shell.viewport_camera.name = "Camera3D"
	_shell.viewport_camera.current = true
	_shell.viewport_camera.transform = Transform3D(
		Basis(),
		Vector3(0.0, 3.0, 8.0)
	).looking_at(Vector3.ZERO, Vector3.UP)
	world.add_child(_shell.viewport_camera)

	var light := DirectionalLight3D.new()
	light.name = "DirectionalLight3D"
	light.rotation_degrees = Vector3(-45.0, 35.0, 0.0)
	world.add_child(light)

	return frame


func _left_status_rail() -> Control:
	var rail := PanelContainer.new()
	rail.name = "LeftStatusRail"
	rail.custom_minimum_size = Vector2(176, 0)
	rail.size_flags_vertical = Control.SIZE_EXPAND_FILL

	var style := StyleBoxFlat.new()
	style.bg_color = Color(0, 0, 0, 0)
	style.border_color = WorkbenchConstantsScript.COLOR_LINE
	style.border_width_right = 1
	style.content_margin_left = 14
	style.content_margin_right = 12
	style.content_margin_top = 14
	style.content_margin_bottom = 14
	rail.add_theme_stylebox_override("panel", style)

	var scroll := ScrollContainer.new()
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	rail.add_child(scroll)

	_shell.left_panel = LeftPanelScript.new()
	_shell.left_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_shell.left_panel.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.add_child(_shell.left_panel)
	return rail


func _right_panel() -> Control:
	_shell.right_panel_split = VSplitContainer.new()
	var split: VSplitContainer = _shell.right_panel_split
	split.name = "RightPanel"
	split.custom_minimum_size = Vector2(320, 0)
	split.size_flags_horizontal = Control.SIZE_FILL
	split.size_flags_vertical = Control.SIZE_EXPAND_FILL
	split.split_offset = 320

	split.add_child(_object_tree_placeholder())
	split.add_child(_selected_object_placeholder())
	call_deferred("_apply_right_panel_default_split")

	return split


func _object_tree_placeholder() -> Control:
	var panel := PanelContainer.new()
	panel.name = "ObjectTreePanel"
	panel.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_apply_panel_style(panel, WorkbenchConstantsScript.COLOR_PANEL)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	panel.add_child(box)

	var title := Label.new()
	title.text = "Object Tree"
	title.add_theme_color_override("font_color", WorkbenchConstantsScript.COLOR_TEXT)
	box.add_child(title)

	_shell.object_tree = Tree.new()
	_shell.object_tree.name = "ObjectTree"
	_shell.object_tree.hide_root = false
	_shell.object_tree.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_connect_if_available(_shell.object_tree.item_selected, "_on_object_tree_item_selected")
	_connect_if_available(_shell.object_tree.item_edited, "_on_object_tree_item_edited")

	var root: TreeItem = _shell.object_tree.create_item()
	root.set_text(0, "Objects")
	root.set_selectable(0, false)

	_call_if_available("_populate_object_tree")

	box.add_child(_shell.object_tree)

	return panel


func _selected_object_placeholder() -> Control:
	var panel := PanelContainer.new()
	panel.name = "SelectedObjectPanel"
	panel.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_apply_panel_style(panel, WorkbenchConstantsScript.COLOR_PANEL_SOFT)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	panel.add_child(box)

	var title := Label.new()
	title.text = "Selected Object"
	title.add_theme_color_override("font_color", WorkbenchConstantsScript.COLOR_TEXT)
	box.add_child(title)

	var scroll := ScrollContainer.new()
	scroll.name = "SelectedObjectScroll"
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box.add_child(scroll)

	_shell.object_inspector_panel = ObjectInspectorPanelScript.new()
	_shell.object_inspector_panel.name = "ObjectInspectorPanel"
	_shell.object_inspector_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_connect_if_available(_shell.object_inspector_panel.save_override_requested, "_on_save_override_pressed")
	_connect_if_available(_shell.object_inspector_panel.regenerate_packets_requested, "_on_regenerate_packets_pressed")
	_connect_if_available(_shell.object_inspector_panel.reload_project_requested, "_on_reload_project_pressed")
	_connect_if_available(_shell.object_inspector_panel.position_apply_requested, "_on_position_apply_requested")
	scroll.add_child(_shell.object_inspector_panel)

	return panel


func _create_context_menus() -> void:
	_shell.create_context_menu = CreateContextMenuScript.new()
	_connect_if_available(
		_shell.create_context_menu.create_command_requested,
		"_on_create_command_requested"
	)
	_shell.add_child(_shell.create_context_menu)
	_shell.create_context_menu.load_registry(WorkbenchPathsScript.create_context_menu_registry_path())

	_shell.ghost_action_menu = PopupMenu.new()
	_shell.ghost_action_menu.name = "GhostActionMenu"
	_shell.ghost_action_menu.add_item("Move", WorkbenchConstantsScript.GHOST_ACTION_MOVE_ID)
	_shell.ghost_action_menu.add_item("Rotate", WorkbenchConstantsScript.GHOST_ACTION_ROTATE_ID)
	_shell.ghost_action_menu.add_item("Delete", WorkbenchConstantsScript.GHOST_ACTION_DELETE_ID)
	_shell.ghost_action_menu.add_item(
		"Export Candidate Command",
		WorkbenchConstantsScript.GHOST_ACTION_EXPORT_ID
	)
	_connect_if_available(_shell.ghost_action_menu.id_pressed, "_on_ghost_action_menu_id_pressed")
	_shell.add_child(_shell.ghost_action_menu)

	_shell.port_action_menu = PopupMenu.new()
	_shell.port_action_menu.name = "PortActionMenu"
	_shell.port_action_menu.add_item("Add Pipe", 1)
	_shell.port_action_menu.add_item("Add 90 Elbow", 2)
	_shell.port_action_menu.add_item("Add Coupling", 3)
	_shell.port_action_menu.add_item("Shorten From This End", 4)
	_shell.port_action_menu.add_item("Extend From This End", 5)
	_shell.port_action_menu.add_item("Edit OD", 6)
	_connect_if_available(_shell.port_action_menu.id_pressed, "_on_port_action_selected")
	_shell.add_child(_shell.port_action_menu)


func _apply_panel_style(panel: PanelContainer, fill: Color) -> void:
	var style := StyleBoxFlat.new()
	style.bg_color = fill
	style.border_color = WorkbenchConstantsScript.COLOR_LINE
	style.set_border_width_all(1)
	style.content_margin_left = 12
	style.content_margin_right = 12
	style.content_margin_top = 12
	style.content_margin_bottom = 12
	panel.add_theme_stylebox_override("panel", style)


func _apply_right_panel_default_split() -> void:
	if _shell == null or _shell.right_panel_split == null:
		return

	var split: VSplitContainer = _shell.right_panel_split
	var height := split.size.y
	if height <= 0.0:
		return

	split.split_offset = int(height * 0.4)


func _connect_if_available(source_signal: Signal, method_name: String) -> void:
	if _shell != null and _shell.has_method(method_name):
		source_signal.connect(Callable(_shell, method_name))


func _call_if_available(method_name: String) -> void:
	if _shell != null and _shell.has_method(method_name):
		_shell.call(method_name)
