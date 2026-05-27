extends Control

const Palette = preload("res://screen/scripts/widgets/Palette.gd")
const CliBridge = preload("res://screen/scripts/runtime/CliBridge.gd")

var left_tabs: VBoxContainer
var workspace_tabs: TabContainer
var bottom_tabs: TabContainer
var bottom_shell: PanelContainer
var right_panel: PanelContainer
var right_restore: Button
var file_tree: Tree
var chat_count := 0
var bottom_expanded := false
var right_collapsed := false

func _ready() -> void:
	_background()
	_build()
	_seed()

func _background() -> void:
	var bg := ColorRect.new()
	bg.color = Palette.PLUM_BLACK
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

func _build() -> void:
	var root := VBoxContainer.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_theme_constant_override("separation", 8)
	add_child(root)

	root.add_child(_top_bar())

	var main := HSplitContainer.new()
	main.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(main)

	main.add_child(_left_nav())

	var center := VBoxContainer.new()
	center.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	main.add_child(center)

	center.add_child(_workspace())
	center.add_child(_bottom())

	right_panel = _right_files()
	main.add_child(right_panel)

	right_restore = Button.new()
	right_restore.text = "Files"
	right_restore.custom_minimum_size = Vector2(44, 0)
	right_restore.visible = false
	_button(right_restore, true)
	right_restore.pressed.connect(_toggle_right)
	main.add_child(right_restore)

func _top_bar() -> Control:
	var panel := PanelContainer.new()
	panel.custom_minimum_size = Vector2(0, 50)
	_panel(panel, Palette.PLUM_DEEP, Palette.GOLD_DARK, 1, 12)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	panel.add_child(row)

	var title := Label.new()
	title.text = "DashBoard"
	title.add_theme_font_size_override("font_size", 26)
	title.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
	row.add_child(title)

	var sub := Label.new()
	sub.text = "operator cockpit"
	sub.add_theme_color_override("font_color", Palette.TEXT_DIM)
	row.add_child(sub)

	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(spacer)

	var state := Label.new()
	state.text = "DISPLAY_ONLY  •  NO_PATCH_AUTHORITY"
	state.add_theme_color_override("font_color", Palette.GOLD)
	row.add_child(state)
	return panel

func _left_nav() -> Control:
	var shell := PanelContainer.new()
	shell.custom_minimum_size = Vector2(245, 0)
	_panel(shell, Palette.PLUM_DEEP, Palette.GOLD_DARK, 1, 16)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	shell.add_child(box)

	var row := HBoxContainer.new()
	box.add_child(row)
	var pages := Label.new()
	pages.text = "Pages"
	pages.add_theme_font_size_override("font_size", 18)
	pages.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
	row.add_child(pages)
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(spacer)
	var plus := Button.new()
	plus.text = "+"
	_button(plus, true)
	plus.pressed.connect(_new_chat)
	row.add_child(plus)

	left_tabs = VBoxContainer.new()
	left_tabs.add_theme_constant_override("separation", 6)
	box.add_child(left_tabs)

	box.add_child(HSeparator.new())

	var screens := Label.new()
	screens.text = "Screens"
	screens.add_theme_color_override("font_color", Palette.TEXT_DIM)
	box.add_child(screens)

	for s in ["Home", "Agents", "Diffs", "Logs", "Settings"]:
		var b := Button.new()
		b.text = s
		_button(b, false)
		b.pressed.connect(func(): _open_screen(s))
		box.add_child(b)

	box.add_child(HSeparator.new())

	var commands := Label.new()
	commands.text = "Commands"
	commands.add_theme_color_override("font_color", Palette.TEXT_DIM)
	box.add_child(commands)

	var scan := Button.new()
	scan.text = "Scan Repo"
	_button(scan, true)
	scan.pressed.connect(_scan_repo)
	box.add_child(scan)

	var git := Button.new()
	git.text = "Git Status"
	_button(git, false)
	git.pressed.connect(_git_status)
	box.add_child(git)

	var dbg := Button.new()
	dbg.text = "Debug Paths"
	_button(dbg, false)
	dbg.pressed.connect(func(): _terminal("[color=#d6b15f]Path debug[/color]\n" + CliBridge.debug_paths()))
	box.add_child(dbg)

	return shell

func _workspace() -> Control:
	var shell := PanelContainer.new()
	shell.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_panel(shell, Palette.PLUM_PANEL, Palette.GOLD_DARK, 1, 18)
	workspace_tabs = TabContainer.new()
	workspace_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	shell.add_child(workspace_tabs)
	return shell

func _right_files() -> PanelContainer:
	var shell := PanelContainer.new()
	shell.custom_minimum_size = Vector2(305, 0)
	_panel(shell, Palette.PLUM_DEEP, Palette.GOLD_DARK, 1, 16)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	shell.add_child(box)

	var row := HBoxContainer.new()
	box.add_child(row)
	var title := Label.new()
	title.text = "Files"
	title.add_theme_font_size_override("font_size", 18)
	title.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
	row.add_child(title)
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(spacer)
	var collapse := Button.new()
	collapse.text = "⟩"
	_button(collapse, true)
	collapse.pressed.connect(_toggle_right)
	row.add_child(collapse)

	file_tree = Tree.new()
	file_tree.size_flags_vertical = Control.SIZE_EXPAND_FILL
	box.add_child(file_tree)
	_seed_tree()
	return shell

func _bottom() -> Control:
	bottom_shell = PanelContainer.new()
	bottom_shell.custom_minimum_size = Vector2(0, 245)
	_panel(bottom_shell, Palette.PLUM_DEEP, Palette.GOLD_DARK, 1, 16)
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
	var exp := Button.new()
	exp.text = "Fullscreen Bottom"
	_button(exp, true)
	exp.pressed.connect(_toggle_bottom)
	row.add_child(exp)

	bottom_tabs = TabContainer.new()
	bottom_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	box.add_child(bottom_tabs)
	_add_bottom("Logs", "No CLI bridge output yet.")
	_add_bottom("Diffs", "Candidate diffs will render here.")
	_add_bottom("Packets", "Observation/runtime packets will render here.")
	_add_bottom("Terminal", "CLI stdout/stderr will render here.")
	return bottom_shell

func _seed() -> void:
	_new_chat()
	_open_screen("Home")
	_log("Phase 1.2 full replacement loaded.")
	_terminal("[color=#d6b15f]Path debug[/color]\n" + CliBridge.debug_paths())

func _new_chat() -> void:
	chat_count += 1
	var name := "Chat %02d" % chat_count
	var b := Button.new()
	b.text = name
	_button(b, false)
	b.pressed.connect(func(): _open_chat(name))
	left_tabs.add_child(b)
	left_tabs.move_child(b, 0)
	_open_chat(name)

func _open_chat(name: String) -> void:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 12)
	var h := Label.new()
	h.text = name
	h.add_theme_font_size_override("font_size", 24)
	h.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
	box.add_child(h)
	var transcript := RichTextLabel.new()
	transcript.bbcode_enabled = true
	transcript.size_flags_vertical = Control.SIZE_EXPAND_FILL
	transcript.text = "[color=#b8aebe]Fresh operational thread.[/color]\n\nBoundary: this chat is a workspace surface, not authority."
	box.add_child(transcript)
	var input := TextEdit.new()
	input.custom_minimum_size = Vector2(0, 115)
	input.placeholder_text = "Write task / command / thought here..."
	box.add_child(input)
	_add_or_focus_tab(name, box)

func _open_screen(name: String) -> void:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 12)
	var title := Label.new()
	title.text = name
	title.add_theme_font_size_override("font_size", 24)
	title.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
	box.add_child(title)
	var card := PanelContainer.new()
	card.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_panel(card, Palette.PLUM_CARD, Palette.GOLD_DARK, 1, 14)
	box.add_child(card)
	var text := RichTextLabel.new()
	text.bbcode_enabled = true
	text.text = "[color=#f3edf7]" + name + " surface pending wiring.[/color]\n\nThis space stays clean until it earns complexity."
	card.add_child(text)
	_add_or_focus_tab(name, box)

func _add_or_focus_tab(name: String, node: Control) -> void:
	for i in workspace_tabs.get_tab_count():
		if workspace_tabs.get_tab_title(i) == name:
			workspace_tabs.current_tab = i
			return
	node.name = name
	workspace_tabs.add_child(node)
	workspace_tabs.set_tab_title(workspace_tabs.get_tab_count() - 1, name)
	workspace_tabs.current_tab = workspace_tabs.get_tab_count() - 1

func _add_bottom(name: String, content: String) -> void:
	var r := RichTextLabel.new()
	r.name = name
	r.bbcode_enabled = true
	r.text = "[color=#d6b15f]" + name + "[/color]\n\n" + content
	bottom_tabs.add_child(r)

func _bottom_text(name: String) -> RichTextLabel:
	for child in bottom_tabs.get_children():
		if child.name == name:
			return child
	return null

func _set_bottom(name: String) -> void:
	for i in bottom_tabs.get_tab_count():
		if bottom_tabs.get_tab_title(i) == name:
			bottom_tabs.current_tab = i
			return

func _log(text: String) -> void:
	var l := _bottom_text("Logs")
	if l:
		l.append_text("\n[color=#d6b15f]" + Time.get_time_string_from_system() + "[/color] " + text)

func _terminal(text: String) -> void:
	var t := _bottom_text("Terminal")
	if t:
		t.append_text("\n\n[color=#d6b15f]>[/color] " + text)
	_set_bottom("Terminal")

func _scan_repo() -> void:
	_log("scan-repo requested")
	_terminal("Running scan-repo...")
	_render(CliBridge.scan_repo(CliBridge.default_engineering_root()))

func _git_status() -> void:
	_log("git-status requested")
	_terminal("Running git-status...")
	_render(CliBridge.git_status(CliBridge.default_engineering_root()))

func _render(result: Dictionary) -> void:
	var text := ""
	text += "command: " + str(result.get("command", "")) + "\n"
	text += "exit_code: " + str(result.get("exit_code", "")) + "\n"
	text += "python: " + str(result.get("python", "")) + "\n"
	text += "args: " + str(result.get("args", "")) + "\n"
	text += "debug_paths:\n" + str(result.get("debug_paths", "")) + "\n\n"
	text += str(result.get("stdout", ""))
	if result.get("ok", false):
		text = "[color=#8fca7a]CLI command completed.[/color]\n" + text
	else:
		text = "[color=#e05f5f]CLI command failed.[/color]\n" + text
	_terminal(text)

func _seed_tree() -> void:
	file_tree.clear()
	var root := file_tree.create_item()
	root.set_text(0, "Core")
	var dash := file_tree.create_item(root)
	dash.set_text(0, "DashBoard")
	var ui := file_tree.create_item(dash)
	ui.set_text(0, "UI")
	file_tree.create_item(ui).set_text(0, "screen/")
	file_tree.create_item(ui).set_text(0, "scripts/")
	file_tree.create_item(ui).set_text(0, "assets/")
	file_tree.create_item(root).set_text(0, "Engineering")
	file_tree.create_item(root).set_text(0, "MolecularScience")
	file_tree.create_item(root).set_text(0, "BioChemistry")

func _toggle_right() -> void:
	right_collapsed = !right_collapsed
	right_panel.visible = !right_collapsed
	right_restore.visible = right_collapsed

func _toggle_bottom() -> void:
	bottom_expanded = !bottom_expanded
	bottom_shell.custom_minimum_size = Vector2(0, 710 if bottom_expanded else 245)

func _panel(panel: PanelContainer, fill: Color, border: Color, width: int, radius: int) -> void:
	var s := StyleBoxFlat.new()
	s.bg_color = fill
	s.border_color = border
	s.set_border_width_all(width)
	s.set_corner_radius_all(radius)
	s.content_margin_left = 12
	s.content_margin_right = 12
	s.content_margin_top = 10
	s.content_margin_bottom = 10
	panel.add_theme_stylebox_override("panel", s)

func _button(button: Button, primary: bool) -> void:
	var normal := StyleBoxFlat.new()
	normal.bg_color = Palette.GOLD_SOFT if primary else Palette.PLUM_CARD
	normal.border_color = Palette.GOLD if primary else Palette.GOLD_DARK
	normal.set_border_width_all(1)
	normal.set_corner_radius_all(10)
	normal.content_margin_left = 12
	normal.content_margin_right = 12
	normal.content_margin_top = 7
	normal.content_margin_bottom = 7

	var hover := StyleBoxFlat.new()
	hover.bg_color = Palette.GOLD_BRIGHT if primary else Palette.PLUM_HOVER
	hover.border_color = Palette.GOLD_BRIGHT
	hover.set_border_width_all(1)
	hover.set_corner_radius_all(10)
	hover.content_margin_left = 12
	hover.content_margin_right = 12
	hover.content_margin_top = 7
	hover.content_margin_bottom = 7

	button.add_theme_stylebox_override("normal", normal)
	button.add_theme_stylebox_override("hover", hover)
	button.add_theme_color_override("font_color", Palette.PLUM_BLACK if primary else Palette.TEXT)
	button.add_theme_color_override("font_hover_color", Palette.PLUM_BLACK if primary else Palette.GOLD_BRIGHT)
