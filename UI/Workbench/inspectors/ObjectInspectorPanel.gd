extends VBoxContainer

class_name ObjectInspectorPanel

signal save_override_requested
signal regenerate_packets_requested
signal position_apply_requested(object_id: String, position: Vector3)
signal reload_project_requested

const COLOR_TEXT := Color(0.88, 0.9, 0.92, 1.0)
const NO_SELECTION_TEXT := "[color=#949da6]No object selected[/color]"

var controls_root: VBoxContainer
var controls_body: VBoxContainer
var controls_expanded := false

var placement_editor_root: VBoxContainer
var placement_editor_body: VBoxContainer
var placement_editor_expanded := false

var selected_object_label: RichTextLabel

var selected_object_root: VBoxContainer
var selected_object_body: VBoxContainer
var selected_object_expanded := true
var selected_object_text := NO_SELECTION_TEXT

var current_selection: Dictionary = {}


func _ready() -> void:
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	add_theme_constant_override("separation", 8)
	_build_panel()
	show_no_selection()

func _toggle_selected_object_panel() -> void:
	selected_object_expanded = not selected_object_expanded
	_render_selected_object_panel()

func show_selection(selection: Dictionary, text: String) -> void:
	current_selection = selection.duplicate(true)
	selected_object_text = text
	_render_selected_object_panel()
	_render_controls_panel()
	_render_placement_editor()

func show_no_selection() -> void:
	current_selection.clear()
	selected_object_text = NO_SELECTION_TEXT

	_render_selected_object_panel()
	_render_controls_panel()
	_render_placement_editor()

func _build_panel() -> void:
	selected_object_root = VBoxContainer.new()
	selected_object_root.name = "SelectedObjectRoot"
	selected_object_root.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	selected_object_root.add_theme_constant_override("separation", 6)
	add_child(selected_object_root)

	controls_root = VBoxContainer.new()
	controls_root.name = "ControlsRoot"
	controls_root.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	controls_root.add_theme_constant_override("separation", 6)
	add_child(controls_root)

	placement_editor_root = VBoxContainer.new()
	placement_editor_root.name = "PlacementEditorRoot"
	placement_editor_root.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	placement_editor_root.add_theme_constant_override("separation", 6)
	add_child(placement_editor_root)

func _render_selected_object_panel() -> void:
	if selected_object_root == null:
		selected_object_root = VBoxContainer.new()
		selected_object_root.name = "SelectedObjectRoot"
		selected_object_root.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		selected_object_root.add_theme_constant_override("separation", 6)
		add_child(selected_object_root)

	_clear_control_children(selected_object_root)

	var toggle := Button.new()
	toggle.text = ("▼ Selected Object" if selected_object_expanded else "▶ Selected Object")
	toggle.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	toggle.pressed.connect(_toggle_selected_object_panel)
	selected_object_root.add_child(toggle)

	selected_object_body = VBoxContainer.new()
	selected_object_body.name = "SelectedObjectBody"
	selected_object_body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	selected_object_body.visible = selected_object_expanded
	selected_object_root.add_child(selected_object_body)

	selected_object_label = RichTextLabel.new()
	selected_object_label.name = "SelectedObjectText"
	selected_object_label.bbcode_enabled = true
	selected_object_label.fit_content = true
	selected_object_label.selection_enabled = true
	selected_object_label.context_menu_enabled = true
	selected_object_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	selected_object_body.add_child(selected_object_label)

	if current_selection.is_empty():
		selected_object_label.text = NO_SELECTION_TEXT
	else:
		selected_object_label.text = selected_object_text

func _render_controls_panel() -> void:
	if controls_root == null:
		return

	_clear_control_children(controls_root)

	var toggle := Button.new()
	toggle.text = ("▼ Controls" if controls_expanded else "▶ Controls")
	toggle.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	toggle.pressed.connect(_toggle_controls_panel)
	controls_root.add_child(toggle)

	controls_body = VBoxContainer.new()
	controls_body.name = "ControlsBody"
	controls_body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	controls_body.add_theme_constant_override("separation", 6)
	controls_body.visible = controls_expanded
	controls_root.add_child(controls_body)

	var save_button := Button.new()
	save_button.text = "Save Override"
	save_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	save_button.pressed.connect(func(): save_override_requested.emit())
	controls_body.add_child(save_button)

	var regenerate_button := Button.new()
	regenerate_button.text = "Regenerate Packets"
	regenerate_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	regenerate_button.pressed.connect(func(): regenerate_packets_requested.emit())
	controls_body.add_child(regenerate_button)

	var reload_button := Button.new()
	reload_button.pressed.connect(
		func():
			reload_project_requested.emit()
	)
	reload_button.text = "Reload Project"
	reload_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	reload_button.disabled = false
	controls_body.add_child(reload_button)


func _toggle_controls_panel() -> void:
	controls_expanded = not controls_expanded
	_render_controls_panel()


func _render_placement_editor() -> void:
	if placement_editor_root == null:
		return

	_clear_control_children(placement_editor_root)

	if not _selection_supports_position_editor():
		placement_editor_root.visible = false
		return

	placement_editor_root.visible = true

	var object_data: Dictionary = current_selection.get("raw_data", current_selection)
	var object_id := str(object_data.get("object_id", ""))
	var position: Dictionary = object_data.get("position_m", {})

	var toggle := Button.new()
	toggle.text = ("▼ Placement Editor" if placement_editor_expanded else "▶ Placement Editor")
	toggle.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	toggle.pressed.connect(_toggle_placement_editor)
	placement_editor_root.add_child(toggle)

	placement_editor_body = VBoxContainer.new()
	placement_editor_body.name = "PlacementEditorBody"
	placement_editor_body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	placement_editor_body.add_theme_constant_override("separation", 6)
	placement_editor_body.visible = placement_editor_expanded
	placement_editor_root.add_child(placement_editor_body)

	var grid := GridContainer.new()
	grid.columns = 2
	grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	placement_editor_body.add_child(grid)

	var x_edit := _placement_line_edit(position.get("x", 0.0))
	var y_edit := _placement_line_edit(position.get("y", 0.0))
	var z_edit := _placement_line_edit(position.get("z", 0.0))

	_add_labeled_control(grid, "x", x_edit)
	_add_labeled_control(grid, "y", y_edit)
	_add_labeled_control(grid, "z", z_edit)

	var apply_button := Button.new()
	apply_button.text = "Apply Position"
	apply_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	apply_button.pressed.connect(_emit_position_apply.bind(object_id, x_edit, y_edit, z_edit))
	placement_editor_body.add_child(apply_button)


func _toggle_placement_editor() -> void:
	placement_editor_expanded = not placement_editor_expanded
	_render_placement_editor()


func _selection_supports_position_editor() -> bool:
	if str(current_selection.get("node_kind", "object")) != "object":
		return false

	var object_data: Dictionary = current_selection.get("raw_data", current_selection)
	return str(object_data.get("object_id", "")) != "" and object_data.has("position_m")


func _placement_line_edit(value: Variant) -> LineEdit:
	var edit := LineEdit.new()
	edit.text = str(value)
	edit.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return edit


func _add_labeled_control(parent: GridContainer, label_text: String, control: Control) -> void:
	var label := Label.new()
	label.text = label_text
	label.add_theme_color_override("font_color", COLOR_TEXT)
	parent.add_child(label)
	parent.add_child(control)


func _emit_position_apply(
	object_id: String,
	x_edit: LineEdit,
	y_edit: LineEdit,
	z_edit: LineEdit
) -> void:
	position_apply_requested.emit(
		object_id,
		Vector3(float(x_edit.text), float(y_edit.text), float(z_edit.text))
	)


func _clear_control_children(node: Control) -> void:
	for child in node.get_children():
		child.queue_free()
