extends RefCounted
class_name OperatorShellBottomDock

const Palette = preload("res://widgets/Palette.gd")
const TerminalSurface = preload("res://widgets/TerminalSurface.gd")

var host
var bottom_shell: PanelContainer
var tab_row: HBoxContainer
var tab_buttons: HBoxContainer
var content_host: Control
var terminal_input: LineEdit
var terminal_surface
var tab_order: Array[String] = []
var tab_data := {}
var current_tab_name := ""
var bottom_tabs

func _init(owner) -> void:
	host = owner

func build() -> Control:
	bottom_shell = PanelContainer.new()
	bottom_shell.custom_minimum_size = Vector2(0, 48)
	host._panel(bottom_shell, Palette.PLUM_DEEP, Palette.GOLD_DARK, 1, 4)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 0)
	box.clip_contents = true
	bottom_shell.add_child(box)

	# Tab row: [buttons ...] [spacer] [Dense]
	tab_row = HBoxContainer.new()
	tab_row.add_theme_constant_override("separation", 4)
	tab_row.size_flags_vertical = Control.SIZE_EXPAND_FILL
	box.add_child(tab_row)

	tab_buttons = HBoxContainer.new()
	tab_buttons.add_theme_constant_override("separation", 2)
	tab_buttons.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	tab_row.add_child(tab_buttons)

	var density := Button.new()
	density.text = "Dense"
	density.custom_minimum_size = Vector2(70, 24)
	host._button(density, true)
	host._connect_observed_button(density, "Cycle Density", host._cycle_terminal_density)
	tab_row.add_child(density)
	host.terminal_density_button = density
	host.terminal_toggle_button = null

	# Content host
	content_host = Control.new()
	content_host.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	content_host.size_flags_vertical = Control.SIZE_EXPAND_FILL
	content_host.custom_minimum_size = Vector2(0, 0)
	content_host.clip_contents = true
	box.add_child(content_host)

	# Approve (hidden)
	host.approve_button = Button.new()
	host.approve_button.text = "Approve Proposal"
	host.approve_button.visible = false
	host.approve_button.pressed.connect(host._on_approve_task_pressed)
	host._button(host.approve_button, true)
	box.add_child(host.approve_button)

	# Input line — hidden when collapsed to taskbar height
	terminal_input = LineEdit.new()
	terminal_input.placeholder_text = "Type operational intent..."
	terminal_input.focus_mode = Control.FOCUS_ALL
	terminal_input.custom_minimum_size = Vector2(0, 26)
	terminal_input.text_submitted.connect(host._on_terminal_input_submitted)
	box.add_child(terminal_input)
	host.terminal_input = terminal_input

	bottom_shell.resized.connect(_on_shell_resized)

	add_bottom("Logs", "No CLI bridge output yet.")
	add_bottom("Diffs", "Diff proposal/review output will render here.")
	add_bottom("Packets", "Packet intake and registry output will render here.")
	add_terminal_bottom()

	_select_tab("Logs")
	bottom_tabs = self
	return bottom_shell

func _on_shell_resized() -> void:
	var h := bottom_shell.size.y
	var show_input := h > 80.0
	if terminal_input != null and terminal_input.visible != show_input:
		terminal_input.visible = show_input
	# Content area is only useful when there is meaningful height to show it in
	var show_content := h > 80.0
	if content_host != null and content_host.visible != show_content:
		content_host.visible = show_content

func _make_tab_button(name: String) -> Button:
	var btn := Button.new()
	btn.text = name
	btn.toggle_mode = true
	btn.custom_minimum_size = Vector2(64, 24)
	btn.add_theme_font_size_override("font_size", 11)
	host._button(btn, false)
	btn.pressed.connect(_select_tab.bind(name))
	tab_buttons.add_child(btn)
	return btn

func add_bottom(name: String, content: String) -> void:
	var btn := _make_tab_button(name)

	var label := RichTextLabel.new()
	label.name = name
	label.bbcode_enabled = true
	label.selection_enabled = true
	label.text = "[color=#d6b15f]" + name + "[/color]\n\n" + content
	label.anchor_right = 1.0
	label.anchor_bottom = 1.0
	label.visible = false
	content_host.add_child(label)

	tab_data[name] = { "button": btn, "content": label }
	tab_order.append(name)

func add_terminal_bottom() -> void:
	terminal_surface = TerminalSurface.new(host)
	var terminal_control: Control = terminal_surface.build()
	terminal_control.name = "Terminal"
	terminal_control.anchor_right = 1.0
	terminal_control.anchor_bottom = 1.0
	terminal_control.visible = false
	content_host.add_child(terminal_control)

	var btn := _make_tab_button("Terminal")
	tab_data["Terminal"] = { "button": btn, "content": terminal_control }
	tab_order.append("Terminal")

func _select_tab(name: String) -> void:
	if not tab_data.has(name):
		return
	current_tab_name = name
	for n in tab_data.keys():
		tab_data[n].button.button_pressed = (n == name)
		tab_data[n].content.visible = (n == name)

func get_tab_count() -> int:
	return tab_order.size()

func get_tab_title(i: int) -> String:
	return tab_order[i] if i >= 0 and i < tab_order.size() else ""

func set_current_tab(i: int) -> void:
	if i >= 0 and i < tab_order.size():
		_select_tab(tab_order[i])

func get_current_tab() -> int:
	return tab_order.find(current_tab_name)

func bottom_text(name: String) -> RichTextLabel:
	if tab_data.has(name):
		var c = tab_data[name].content
		if c is RichTextLabel:
			return c
	return null

func set_bottom(name: String) -> void:
	_select_tab(name)

func log_line(text: String) -> void:
	var l := bottom_text("Logs")
	if l:
		l.append_text("\n[color=#d6b15f]" + Time.get_time_string_from_system() + "[/color] " + text)

func terminal(text: String) -> void:
	if terminal_surface and terminal_surface.has_method("append_system_text"):
		terminal_surface.append_system_text(text)
	_select_tab("Terminal")

func diff(text: String) -> void:
	var d := bottom_text("Diffs")
	if d:
		d.append_text("\n\n[color=#d6b15f]>[/color] " + text)
	_select_tab("Diffs")

func packets(text: String) -> void:
	var p := bottom_text("Packets")
	if p:
		p.append_text("\n\n[color=#d6b15f]>[/color] " + text)
	_select_tab("Packets")

func shutdown_terminals() -> void:
	if terminal_surface and terminal_surface.has_method("shutdown"):
		terminal_surface.shutdown()

func record_command(name: String, result: Dictionary, summary: String) -> void:
	var status := "success" if result.get("ok", false) else "failed"
	host.current_status["last_command"] = name + " (" + status + ")"
	host.current_status["next_required_action"] = "Review " + name + " output"
	host._render_current_status()
	host.command_history.push_front({
		"command": name,
		"status": status,
		"time": Time.get_time_string_from_system(),
		"summary": summary
	})
	if host.command_history.size() > 10:
		host.command_history.pop_back()
	render_history()

func render_history() -> void:
	if not host.history_label:
		return
	var text := "[color=#f1d58a]Command History[/color]\n"
	if host.command_history.is_empty():
		text += "\n(no commands yet)\n"
	else:
		for row in host.command_history:
			var status := str(row.get("status", "unknown"))
			var color := "#8fca7a" if status == "success" else "#e05f5f"
			text += "\n[color=" + color + "]status: " + status + "[/color]\n"
			text += "time: " + str(row.get("time", "--:--")) + "\n"
			text += "command: " + str(row.get("command", "unknown")) + "\n"
			text += "summary: " + str(row.get("summary", "")) + "\n"
	text += "\n[color=#b8aebe]history != evidence[/color]"
	host.history_label.text = text

func apply_terminal_density(mode: String) -> void:
	var font_size := 12
	var margin := 6
	match mode:
		"comfortable":
			font_size = 14
			margin = 12
		"compact":
			font_size = 12
			margin = 6
		"dense":
			font_size = 10
			margin = 2
	for name in ["Logs", "Diffs", "Packets"]:
		var label := bottom_text(name)
		if label:
			label.add_theme_font_size_override("normal_font_size", font_size)
			label.add_theme_constant_override("text_highlight_h_padding", margin)
			label.add_theme_constant_override("text_highlight_v_padding", margin)
	if terminal_surface and terminal_surface.has_method("apply_terminal_density"):
		terminal_surface.apply_terminal_density(mode)