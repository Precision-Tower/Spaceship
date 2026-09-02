extends RefCounted
class_name OperatorShellBottomDock

const Palette = preload("res://OperatorShell/widgets/Palette.gd")
const TerminalSurface = preload("res://OperatorShell/widgets/TerminalSurface.gd")

var host
var bottom_shell: PanelContainer
var bottom_tabs: TabContainer
var terminal_surface

func _init(owner) -> void:
	host = owner

func build() -> Control:
	bottom_shell = PanelContainer.new()
	bottom_shell.custom_minimum_size = Vector2(0, 245)
	host._panel(bottom_shell, Palette.PLUM_DEEP, Palette.GOLD_DARK, 1, 16)

	var box := VBoxContainer.new()
	bottom_shell.add_child(box)

	var row := HBoxContainer.new()
	box.add_child(row)

	var title := Label.new()
	title.text = "Runtime Surfaces"
	title.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
	row.add_child(title)

	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(spacer)

	var density := Button.new()
	density.text = "Dense"
	host._button(density, true)
	host._connect_observed_button(density, "Cycle Density", host._cycle_terminal_density)
	row.add_child(density)

	var toggle := Button.new()
	toggle.text = "▼"
	host._button(toggle, true)
	host._connect_observed_button(toggle, "Toggle Terminal Dock", host._toggle_terminal_dock)
	row.add_child(toggle)

	host.terminal_density_button = density
	host.terminal_toggle_button = toggle

	bottom_tabs = TabContainer.new()
	bottom_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	box.add_child(bottom_tabs)

	host.approve_button = Button.new()
	host.approve_button.text = "Approve Proposal"
	host.approve_button.visible = false
	host.approve_button.pressed.connect(host._on_approve_task_pressed)
	host._button(host.approve_button, true)
	box.add_child(host.approve_button)

	host.terminal_input = LineEdit.new()
	host.terminal_input.placeholder_text = "Type operational intent (e.g., 'connect Gear to Dashboard')..."
	host.terminal_input.focus_mode = Control.FOCUS_ALL
	host.terminal_input.text_submitted.connect(host._on_terminal_input_submitted)
	box.add_child(host.terminal_input)

	add_bottom("Logs", "No CLI bridge output yet.")
	add_bottom("Diffs", "Diff proposal/review output will render here.\n\nviewed_diff != approved_diff")
	add_bottom("Packets", "Packet intake and registry output will render here.")
	add_terminal_bottom()

	return bottom_shell

func add_bottom(name: String, content: String) -> void:
	var r := RichTextLabel.new()
	r.name = name
	r.bbcode_enabled = true
	r.selection_enabled = true
	r.text = "[color=#d6b15f]" + name + "[/color]\n\n" + content
	bottom_tabs.add_child(r)

func add_terminal_bottom() -> void:
	terminal_surface = TerminalSurface.new(host)
	var terminal_control: Control = terminal_surface.build()
	terminal_control.name = "Terminal"
	bottom_tabs.add_child(terminal_control)

func bottom_text(name: String) -> RichTextLabel:
	for child in bottom_tabs.get_children():
		if child.name == name:
			return child
	return null

func set_bottom(name: String) -> void:
	for i in bottom_tabs.get_tab_count():
		if bottom_tabs.get_tab_title(i) == name:
			bottom_tabs.current_tab = i
			return

func log_line(text: String) -> void:
	var l := bottom_text("Logs")
	if l:
		l.append_text("\n[color=#d6b15f]" + Time.get_time_string_from_system() + "[/color] " + text)

func terminal(text: String) -> void:
	if terminal_surface and terminal_surface.has_method("append_system_text"):
		terminal_surface.append_system_text(text)
	set_bottom("Terminal")

func diff(text: String) -> void:
	var d := bottom_text("Diffs")
	if d:
		d.append_text("\n\n[color=#d6b15f]>[/color] " + text)
	set_bottom("Diffs")

func packets(text: String) -> void:
	var p := bottom_text("Packets")
	if p:
		p.append_text("\n\n[color=#d6b15f]>[/color] " + text)
	set_bottom("Packets")

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

func shutdown_terminals() -> void:
	if terminal_surface and terminal_surface.has_method("shutdown"):
		terminal_surface.shutdown()

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
