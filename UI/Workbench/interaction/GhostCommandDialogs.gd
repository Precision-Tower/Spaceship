extends RefCounted
class_name GhostCommandDialogs

var controller
var shell

var pipe_command_dialog: AcceptDialog = null
var pipe_length_input: LineEdit = null
var pipe_od_input: LineEdit = null
var pending_pipe_center := Vector3.ZERO
var pending_pipe_from_port := false
var pending_pipe_start := Vector3.ZERO
var pending_pipe_direction := Vector3.RIGHT

var fitting_command_dialog: AcceptDialog = null
var fitting_roll_input: LineEdit = null
var pending_fitting_selection: Dictionary = {}
var pending_fitting_type := "elbow_90"

var trim_command_dialog: AcceptDialog = null
var trim_amount_input: LineEdit = null
var pending_trim_selection: Dictionary = {}
var pending_trim_sign: float = -1.0

var od_command_dialog: AcceptDialog = null
var od_value_input: LineEdit = null
var pending_od_selection: Dictionary = {}


func setup(owner_controller, owner_shell) -> void:
	controller = owner_controller
	shell = owner_shell


func _start_pipe_command(center_position: Vector3, default_od_m: float = 0.1, from_port: bool = false, pipe_direction: Vector3 = Vector3(1.0, 0.0, 0.0)) -> void:
	pending_pipe_center = center_position
	pending_pipe_start = center_position
	pending_pipe_from_port = from_port
	pending_pipe_direction = pipe_direction.normalized()

	if pipe_command_dialog == null:
		_build_pipe_command_dialog()

	pipe_length_input.text = "1.0"
	pipe_od_input.text = str(default_od_m)

	pipe_command_dialog.popup_centered(Vector2i(280, 160))


func _build_pipe_command_dialog() -> void:
	pipe_command_dialog = AcceptDialog.new()
	pipe_command_dialog.title = "Create Ghost Pipe"
	pipe_command_dialog.ok_button_text = "Create"

	var box := VBoxContainer.new()

	var length_label := Label.new()
	length_label.text = "Length (m)"
	box.add_child(length_label)

	pipe_length_input = LineEdit.new()
	pipe_length_input.text = "1.0"
	box.add_child(pipe_length_input)

	var od_label := Label.new()
	od_label.text = "OD (m)"
	box.add_child(od_label)

	pipe_od_input = LineEdit.new()
	pipe_od_input.text = "0.1"
	box.add_child(pipe_od_input)

	pipe_command_dialog.add_child(box)
	pipe_command_dialog.confirmed.connect(_on_pipe_command_confirmed)

	shell.add_child(pipe_command_dialog)


func _on_pipe_command_confirmed() -> void:
	var length_m: float = float(pipe_length_input.text)
	var od_m: float = float(pipe_od_input.text)

	if length_m <= 0.0 or od_m <= 0.0:
		return

	var center_position: Vector3 = pending_pipe_center

	if pending_pipe_from_port:
		center_position = pending_pipe_start + pending_pipe_direction * (length_m * 0.5)

	controller._create_dimensioned_pipe(center_position, length_m, od_m, pending_pipe_direction)

	pending_pipe_from_port = false
	pending_pipe_start = Vector3.ZERO
	pending_pipe_direction = Vector3(1.0, 0.0, 0.0)


func start_fitting_command(port_selection: Dictionary, fitting_type: String) -> void:
	if port_selection.is_empty():
		return

	pending_fitting_selection = port_selection.duplicate(true)
	pending_fitting_type = fitting_type

	if fitting_command_dialog == null:
		_build_fitting_command_dialog()

	fitting_roll_input.text = "0"
	fitting_command_dialog.title = "Create 90 Fitting"
	fitting_command_dialog.popup_centered(Vector2i(280, 120))


func _build_fitting_command_dialog() -> void:
	fitting_command_dialog = AcceptDialog.new()
	fitting_command_dialog.ok_button_text = "Create"

	var box := VBoxContainer.new()

	var label := Label.new()
	label.text = "Roll degrees: 0 up, 180 down"
	box.add_child(label)

	fitting_roll_input = LineEdit.new()
	fitting_roll_input.text = "0"
	box.add_child(fitting_roll_input)

	fitting_command_dialog.add_child(box)
	fitting_command_dialog.confirmed.connect(_on_fitting_command_confirmed)

	shell.add_child(fitting_command_dialog)


func _on_fitting_command_confirmed() -> void:
	var roll_degrees: float = float(fitting_roll_input.text)

	if controller == null:
		return

	controller.create_fitting_from_port(
		pending_fitting_selection,
		pending_fitting_type,
		roll_degrees
	)


func start_pipe_trim_command(port_selection: Dictionary, sign: float) -> void:
	if port_selection.is_empty():
		return

	var parent: Dictionary = port_selection.get("parent_object", {})
	if str(parent.get("object_type", "")) != "ghost_pipe":
		print("[WorkbenchGhostPipe] trim disabled: selected port is not a ghost pipe endpoint")
		return

	pending_trim_selection = port_selection.duplicate(true)
	pending_trim_sign = sign

	if trim_command_dialog == null:
		_build_trim_command_dialog()

	trim_amount_input.text = "0.1"
	trim_command_dialog.title = "Shorten Pipe" if sign < 0.0 else "Extend Pipe"
	trim_command_dialog.popup_centered(Vector2i(280, 120))


func _build_trim_command_dialog() -> void:
	trim_command_dialog = AcceptDialog.new()
	trim_command_dialog.ok_button_text = "Apply"

	var box := VBoxContainer.new()

	var label := Label.new()
	label.text = "Amount (m)"
	box.add_child(label)

	trim_amount_input = LineEdit.new()
	trim_amount_input.text = "0.1"
	box.add_child(trim_amount_input)

	trim_command_dialog.add_child(box)
	trim_command_dialog.confirmed.connect(_on_trim_command_confirmed)

	shell.add_child(trim_command_dialog)


func _on_trim_command_confirmed() -> void:
	var amount_m: float = float(trim_amount_input.text)
	if amount_m <= 0.0:
		print("[WorkbenchGhostPipe] invalid trim amount=%s" % trim_amount_input.text)
		return

	controller._apply_pipe_trim(pending_trim_selection, pending_trim_sign, amount_m)


func start_od_edit_command(port_selection: Dictionary) -> void:
	if port_selection.is_empty():
		return

	pending_od_selection = port_selection.duplicate(true)

	var parent: Dictionary = port_selection.get("parent_object", {})
	var current_od: float = float(parent.get("od_m", 0.1))

	if od_command_dialog == null:
		_build_od_command_dialog()

	od_value_input.text = str(current_od)
	od_command_dialog.title = "Edit Run OD"
	od_command_dialog.popup_centered(Vector2i(280, 120))


func _build_od_command_dialog() -> void:
	od_command_dialog = AcceptDialog.new()
	od_command_dialog.ok_button_text = "Apply"

	var box := VBoxContainer.new()

	var label := Label.new()
	label.text = "New OD (m)"
	box.add_child(label)

	od_value_input = LineEdit.new()
	od_value_input.text = "0.1"
	box.add_child(od_value_input)

	od_command_dialog.add_child(box)
	od_command_dialog.confirmed.connect(_on_od_command_confirmed)

	shell.add_child(od_command_dialog)


func _on_od_command_confirmed() -> void:
	var new_od_m: float = float(od_value_input.text)
	if new_od_m <= 0.0:
		print("[WorkbenchGhostPipe] invalid OD=%s" % od_value_input.text)
		return

	controller._apply_run_od_edit(pending_od_selection, new_od_m)
