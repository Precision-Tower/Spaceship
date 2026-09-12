extends RefCounted
class_name OperatorShellBottomDock

const Palette = preload("res://widgets/Palette.gd")
const TerminalSurface = preload("res://widgets/TerminalSurface.gd")

var host
var bottom_shell: PanelContainer
var bottom_tabs: TabContainer
var terminal_surface
var content_host: Control
var terminal_input: LineEdit
var tab_buttons := {}
var tab_contents := {}
var tab_order: Array[String] = []
var current_name := ""

func _init(owner) -> void:
	host = owner

func build() -> Control:
	bottom_shell = PanelContainer.new()
	bottom_shell.custom_minimum_size = Vector2(0, 48)
	host._panel(bottom_shell, Palette.PLUM_DEEP, Palette.GOLD_DARK, 1, 4)

	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", 0)
	root.clip_contents = true
	bottom_shell.add_child(root)

	# Tab strip
	var tab_strip := HBoxContainer.new()
	tab_strip.add_theme_constant_override("separation", 4)
	tab_strip.custom_minimum_size = Vector2(0, 26)
	root.add_child(tab_strip)

	var buttons_row := HBoxContainer.new()
	buttons_row.add_theme_constant_override("separation", 2)
	buttons_row.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	tab_strip.add_child(buttons_row)

	var density := Button.new()
	density.text = "Dense"
	density.custom_minimum_size = Vector2(70, 22)
	host._button(density, true)
	host._connect_observed_button(density, "Cycle Density", host._cycle_terminal_density)
	tab_strip.add_child(density)

	# Content host (hidden when collapsed)
	content_host = Control.new()
	content_host.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	content_host.size_flags_vertical = Control.SIZE_EXPAND_FILL
	content_host.clip_contents = true
	root.add_child(content_host)

	# Placeholder tab host so bottom_tabs var is valid
	bottom_tabs = TabContainer.new()
	bottom_tabs.visible = false
	content_host.add_child(bottom_tabs)

	# Input line (hidden until expanded)
	terminal_input = LineEdit.new()
	terminal_input.placeholder_text = "Type operational intent..."
	terminal_input.custom_minimum_size = Vector2(0, 26)
	terminal_input.visible = false
	terminal_input.text_submitted.connect(host._on_terminal_input_submitted)
	root.add_child(terminal_input)
	host.terminal_input = terminal_input

	# Build tabs
	for name in ["Logs", "Diffs", "Packets"]:
		_make_tab(name, "No output yet.")
	_make_terminal_tab()

	bottom_shell.resized.connect(_on_resized)
	_select_tab("Logs")
	return bottom_shell

func _make_tab(name: String, content: String) -> void:
	var btn := Button.new()
	btn.text = name
	btn.toggle_mode = true
	btn.custom_minimum_size = Vector2(64, 22)
	btn.add_theme_font_size_override("font_size", 11)
	host._button(btn, false)
	btn.pressed.connect(_select_tab.bind(name))
	tab_buttons[name] = btn
	btn.get_parent() # no-op
	# Add button to the buttons_row inside build (deferred)
	var strip := bottom_shell.get_child(0).get_child(0).get_child(0)
	strip.add_child(btn)

	var label := RichTextLabel.new()
	label.name = name
	label.bbcode_enabled = true
	label.selection_enabled = true
	label.text = "[color=#d6b15f]" + name + "[/color]\n\n" + content
	label.anchor_right = 1.0
	label.anchor_bottom = 1.0
	label.visible = false
	content_host.add_child(label)
	tab_contents[name] = label
	tab_order.append(name)

func _make_terminal_tab() -> void:
	terminal_surface = TerminalSurface.new(host)
	var term_control: Control = terminal_surface.build()
	term_control.name = "Terminal"
	term_control.anchor_right = 1.0
	term_control.anchor_bottom = 1.0
	term_control.visible = false
	content_host.add_child(term_control)

	var btn := Button.new()
	btn.text = "Terminal"
	btn.toggle_mode = true
	btn.custom_minimum_size = Vector2(74, 22)
	btn.add_theme_font_size_override("font_size", 11)
	host._button(btn, false)
	btn.pressed.connect(_select_tab.bind("Terminal"))
	tab_buttons["Terminal"] = btn
	var strip := bottom_shell.get_child(0).get_child(0).get_child(0)
	strip.add_child(btn)

	tab_contents["Terminal"] = term_control
	tab_order.append("Terminal")

func _select_tab(name: String) -> void:
	if not tab_contents.has(name):
		return
	current_name = name
	for n in tab_contents.keys():
		if tab_buttons.has(n):
			tab_buttons[n].button_pressed = (n == name)
		tab_contents[n].visible = (n == name)

func _on_resized() -> void:
	var h := bottom_shell.size.y
	var expanded := h > 80.0
	if terminal_input != null:
		terminal_input.visible = expanded
	if content_host != null:
		content_host.visible = expanded

func set_bottom(name: String) -> void:
	_select_tab(name)

func log_line(text: String) -> void:
	var l = tab_contents.get("Logs")
	if l is RichTextLabel:
		l.append_text("\n[color=#d6b15f]" + Time.get_time_string_from_system() + "[/color] " + text)

func terminal(text: String) -> void:
	if terminal_surface and terminal_surface.has_method("append_system_text"):
		terminal_surface.append_system_text(text)
	_select_tab("Terminal")

func diff(text: String) -> void:
	var d = tab_contents.get("Diffs")
	if d is RichTextLabel:
		d.append_text("\n\n[color=#d6b15f]>[/color] " + text)
	_select_tab("Diffs")

func packets(text: String) -> void:
	var p = tab_contents.get("Packets")
	if p is RichTextLabel:
		p.append_text("\n\n[color=#d6b15f]>[/color] " + text)
	_select_tab("Packets")

func record_command(name: String, result: Dictionary, summary: String) -> void:
	var status := "success" if result.get("ok", false) else "failed"
	host.current_status["last_command"] = name + " (" + status + ")"
	host._render_current_status()
	host.command_history.push_front({"command": name, "status": status, "time": Time.get_time_string_from_system(), "summary": summary})
	if host.command_history.size() > 10:
		host.command_history.pop_back()
	render_history()

func render_history() -> void:
	if not host.history_label:
		return
	var text := "[color=#f1d58a]Command History[/color]\n"
	for row in host.command_history:
		text += "\n" + str(row.get("command", "?")) + " -> " + str(row.get("status", "?")) + "\n"
	host.history_label.text = text

func shutdown_terminals() -> void:
	if terminal_surface and terminal_surface.has_method("shutdown"):
		terminal_surface.shutdown()

func apply_terminal_density(mode: String) -> void:
	if terminal_surface and terminal_surface.has_method("apply_terminal_density"):
		terminal_surface.apply_terminal_density(mode)

func bottom_text(name: String):
	return tab_contents.get(name)

func get_tab_count() -> int:
	return tab_order.size()

func get_tab_title(i: int) -> String:
	return tab_order[i] if i >= 0 and i < tab_order.size() else ""

func set_current_tab(i: int) -> void:
	if i >= 0 and i < tab_order.size():
		_select_tab(tab_order[i])

func get_current_tab() -> int:
	return tab_order.find(current_name)