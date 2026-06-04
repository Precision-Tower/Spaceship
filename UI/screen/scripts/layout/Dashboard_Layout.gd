class_name DashboardLayout

const Palette = preload("res://screen/scripts/widgets/Palette.gd")

var main: Control

func _init(main_ref: Control) -> void:
	main = main_ref

func build(root_parent: Control) -> Dictionary:
	var refs := {}

	var root := VBoxContainer.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_theme_constant_override("separation", 8)
	root_parent.add_child(root)

	var top_bar := build_top_bar()
	root.add_child(top_bar)

	var runtime_state_bar := build_runtime_state_bar()
	refs["state_label"] = runtime_state_bar.get("state_label")
	root.add_child(runtime_state_bar.get("node"))

	var v_split := VSplitContainer.new()
	v_split.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(v_split)

	var top_h_split := HSplitContainer.new()
	top_h_split.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v_split.add_child(top_h_split)

	var display_box := HBoxContainer.new()
	display_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	display_box.add_theme_constant_override("separation", 0)
	top_h_split.add_child(display_box)

	var left_awareness := build_left_awareness()
	refs.merge(left_awareness.get("refs", {}), true)
	display_box.add_child(left_awareness.get("node"))

	var workspace := build_workspace()
	refs["workspace_tabs"] = workspace.get("workspace_tabs")
	display_box.add_child(workspace.get("node"))

	var right_rail := build_right_control_rail()
	refs.merge(right_rail.get("refs", {}), true)
	top_h_split.add_child(right_rail.get("node"))

	var bottom := build_bottom()
	refs.merge(bottom.get("refs", {}), true)
	v_split.add_child(bottom.get("node"))

	return refs

func build_top_bar() -> Control:
	var p := PanelContainer.new()
	p.custom_minimum_size = Vector2(0, 50)
	_panel(p, Palette.PLUM_DEEP, Palette.GOLD_DARK, 1, 12)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	p.add_child(row)

	var title := Label.new()
	title.text = "DashBoard"
	title.add_theme_font_size_override("font_size", 26)
	title.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
	row.add_child(title)

	var sub := Label.new()
	sub.text = "operator cockpit — operator-triggered state refresh"
	sub.add_theme_color_override("font_color", Palette.TEXT_DIM)
	row.add_child(sub)

	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(spacer)

	var state := Label.new()
	state.text = "OBSERVATION_ONLY • REFRESH != VALIDATION"
	state.add_theme_color_override("font_color", Palette.GOLD)
	row.add_child(state)

	return p

func build_runtime_state_bar() -> Dictionary:
	var p := PanelContainer.new()
	p.custom_minimum_size = Vector2(0, 78)
	_panel(p, Palette.PLUM_CARD, Palette.GOLD_DARK, 1, 14)

	var state_label := Label.new()
	state_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	state_label.add_theme_color_override("font_color", Palette.TEXT)
	state_label.text = "Runtime State\nstatus: booted_not_refreshed | latest_diff: unknown | git_dirty: unknown | packets_pending: unknown\nboundary: runtime_state_reports_observation_only"
	p.add_child(state_label)

	return {
		"node": p,
		"state_label": state_label,
	}

func build_left_awareness() -> Dictionary:
	var refs := {}

	var shell := PanelContainer.new()
	shell.custom_minimum_size = Vector2(320, 0)
	_panel(shell, Palette.PLUM_DEEP, Palette.GOLD_DARK, 1, 16)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	shell.add_child(box)

	var mission_label := _left_text(180)
	mission_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	mission_label.text = main._mission_text_from_data(main._read_mission())
	refs["mission_label"] = mission_label

	var mission_scroll := ScrollContainer.new()
	mission_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	mission_scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var mission_section := _collapsible_left_section("mission", "Mission", mission_label)
	mission_section.size_flags_vertical = Control.SIZE_EXPAND_FILL
	mission_scroll.add_child(mission_section)
	box.add_child(mission_scroll)

	box.add_child(HSeparator.new())

	var bottom_stack := VBoxContainer.new()
	bottom_stack.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bottom_stack.size_flags_vertical = Control.SIZE_SHRINK_CENTER

	var current_status_label := _left_text(120)
	current_status_label.text = main._current_status_text()
	refs["current_status_label"] = current_status_label
	bottom_stack.add_child(_collapsible_left_section("status", "Current Status", current_status_label))

	var operator_observation_label := _left_text(210)
	operator_observation_label.text = main._operator_observation_text()
	refs["operator_observation_label"] = operator_observation_label
	bottom_stack.add_child(_collapsible_left_section("observation", "Operator Observation", operator_observation_label))

	var awareness_label := RichTextLabel.new()
	awareness_label.bbcode_enabled = true
	awareness_label.selection_enabled = true
	awareness_label.custom_minimum_size = Vector2(0, 285)
	awareness_label.text = main._awareness_default()
	refs["awareness_label"] = awareness_label
	bottom_stack.add_child(_collapsible_left_section("awareness", "Operational Awareness", awareness_label))

	var history_label := RichTextLabel.new()
	history_label.bbcode_enabled = true
	history_label.selection_enabled = true
	history_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	history_label.text = "[color=#f1d58a]Command History[/color]\n\n(no commands yet)\n\n[color=#b8aebe]history != evidence[/color]"
	refs["history_label"] = history_label
	bottom_stack.add_child(_collapsible_left_section("history", "Command History", history_label))

	var boundaries := _left_text(185)
	boundaries.text = main._boundaries_default()
	bottom_stack.add_child(_collapsible_left_section("boundaries", "Runtime Boundaries", boundaries))

	box.add_child(bottom_stack)

	return {
		"node": shell,
		"refs": refs,
	}

func _left_text(height: int) -> RichTextLabel:
	var r := RichTextLabel.new()
	r.bbcode_enabled = true
	r.selection_enabled = true
	r.custom_minimum_size = Vector2(280, height)
	r.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return r

func _collapsible_left_section(key: String, title: String, content: Control) -> VBoxContainer:
	var section := VBoxContainer.new()
	section.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	section.add_theme_constant_override("separation", 6)

	var collapsed := bool(main.left_panel_collapsed.get(key, true))

	var b := Button.new()
	b.text = main._collapse_label(title, collapsed)
	_button(b, false)
	b.pressed.connect(func(): main._toggle_left_section(key, content))

	section.add_child(b)
	content.visible = not collapsed
	section.add_child(content)

	main.left_panel_buttons[key] = b

	return section

func build_right_control_rail() -> Dictionary:
	var refs := {}

	var shell := PanelContainer.new()
	shell.custom_minimum_size = Vector2(340, 0)
	_panel(shell, Palette.PLUM_DEEP, Palette.GOLD_DARK, 1, 16)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	shell.add_child(box)

	var top := HBoxContainer.new()
	box.add_child(top)

	var title := Label.new()
	title.text = "Control"
	title.add_theme_font_size_override("font_size", 18)
	title.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
	top.add_child(title)

	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(spacer)

	var plus := Button.new()
	plus.text = "+"
	_button(plus, true)
	main._connect_observed_button(plus, "New Chat", main._new_chat)
	top.add_child(plus)

	var refresh := Button.new()
	refresh.text = "Refresh State"
	_button(refresh, true)
	main._connect_observed_button(refresh, "Refresh State", main._refresh_state_command)
	box.add_child(refresh)

	var test := Button.new()
	test.text = "Test"
	_button(test, true)
	main._connect_observed_button(test, "Test", main._test_all)
	box.add_child(test)

	for mode in ["directory", "screens", "commands"]:
		var b := Button.new()
		b.text = mode.capitalize()
		_button(b, mode == main.active_right_mode)
		main._connect_observed_button(b, mode.capitalize(), func(m = mode): main._set_right_mode(m))
		box.add_child(b)
		main.right_mode_buttons[mode] = b

	var right_content := VBoxContainer.new()
	right_content.size_flags_vertical = Control.SIZE_EXPAND_FILL
	right_content.add_theme_constant_override("separation", 8)
	box.add_child(right_content)
	refs["right_content"] = right_content

	var directory_panel := build_directory_panel()
	var screens_panel := build_screens_panel()
	var commands_panel := build_commands_panel()

	right_content.add_child(directory_panel)
	right_content.add_child(screens_panel)
	right_content.add_child(commands_panel)

	refs["directory_panel"] = directory_panel
	refs["screens_panel"] = screens_panel
	refs["commands_panel"] = commands_panel

	return {
		"node": shell,
		"refs": refs,
	}

func _make_tree(_title: String, height: int) -> Tree:
	var t := Tree.new()
	t.columns = 1
	t.hide_root = false
	t.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	t.size_flags_vertical = Control.SIZE_EXPAND_FILL
	t.custom_minimum_size = Vector2(300, height)
	return t

func _tree_root(tree: Tree, label: String) -> TreeItem:
	tree.clear()
	var root := tree.create_item()
	root.set_text(0, label)
	root.set_collapsed(false)
	return root

func _tree_child(parent: TreeItem, label: String, collapsed := false) -> TreeItem:
	var item := parent.create_child()
	item.set_text(0, label)
	item.set_collapsed(collapsed)
	return item

func build_directory_panel() -> Control:
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var label := Label.new()
	label.text = "Directory Map"
	label.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
	box.add_child(label)

	var tree := _make_tree("Directory", 430)
	tree.item_selected.connect(func(item): main._on_directory_item_selected(item))
	box.add_child(tree)

	var root := _tree_root(tree, "Core/")
	var dashboard := _tree_child(root, "Dashboard/", false)
	var models := _tree_child(dashboard, "Models/", false)
	_tree_child(models, "Cali/", true)
	_tree_child(models, "Elrich/", true)
	_tree_child(models, "Gear/", true)
	_tree_child(models, "Godot/", true)
	_tree_child(models, "Grant/", true)
	_tree_child(models, "Local/", true)
	_tree_child(models, "Shared/", false)
	_tree_child(dashboard, "Tools/", true)

	var ui := _tree_child(dashboard, "UI/", false)
	var screen := _tree_child(ui, "screen/", true)
	_tree_child(screen, "scenes/", true)
	var scripts := _tree_child(ui, "scripts/", true)
	_tree_child(scripts, "cli/", true)
	_tree_child(scripts, "runtime/", true)
	_tree_child(scripts, "patches/", true)
	_tree_child(ui, "Packets/", true)
	_tree_child(root, "Engineering/", true)
	_tree_child(root, "Schools/", true)

	var note := Label.new()
	note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	note.add_theme_color_override("font_color", Palette.TEXT_DIM)
	note.text = "tree_display != filesystem_authority"
	box.add_child(note)

	scroll.add_child(box)
	return scroll

func build_screens_panel() -> Control:
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var label := Label.new()
	label.text = "Screens Map"
	label.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
	box.add_child(label)

	for s in ["Home", "State", "Agents", "Packets", "Diffs", "Logs", "Settings", "AI Assist"]:
		var b := Button.new()
		b.text = s
		_button(b, false)
		main._connect_observed_button(b, s, func(name = s): main._open_screen(name))
		box.add_child(b)

	var tree := _make_tree("Screens", 230)
	box.add_child(tree)

	var root := _tree_root(tree, "Screens/")
	var workspace := _tree_child(root, "workspace tabs/", false)
	for s in ["Home", "State", "Agents", "Packets", "Diffs", "Logs", "Settings", "AI Assist"]:
		_tree_child(workspace, s + " surface", false)

	scroll.add_child(box)
	return scroll

func build_commands_panel() -> Control:
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var label := Label.new()
	label.text = "Commands Map"
	label.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
	box.add_child(label)

	_add_command_button(box, "Scan Core", false, main._scan_core)
	_add_command_button(box, "Git Status", false, main._git_status)
	_add_command_button(box, "Cali Observe Directory", false, main._cali_observe_directory)
	_add_command_button(box, "Propose Directory Diff", false, main._propose_diff)
	_add_command_button(box, "View Latest Diff", false, main._view_latest_diff)
	_add_command_button(box, "Review Latest Diff", false, main._review_latest_diff)
	_add_command_button(box, "Clear Latest Diff", false, main._clear_latest_diff)
	_add_command_button(box, "List Packets", false, main._list_packets)
	_add_command_button(box, "Create Packet Stub", false, main._create_packet_stub)
	_add_command_button(box, "Test State Update", false, main._test_all)
	_add_command_button(box, "Debug Paths", false, func(): main._terminal("Path debug\n" + main.command_router.debug_paths()))
	_add_command_button(box, "Gemini Analyze Core", false, main._gemini_analyze_core)

	var tree := _make_tree("Commands", 260)
	box.add_child(tree)

	var root := _tree_root(tree, "Command Surfaces/")
	var observe := _tree_child(root, "observe/read-only/", false)
	_tree_child(observe, "scan Core")
	_tree_child(observe, "git status")
	_tree_child(observe, "cali observe directory")
	_tree_child(observe, "list packets")

	var diff := _tree_child(root, "diff proposal/review/", false)
	_tree_child(diff, "propose latest.diff")
	_tree_child(diff, "view latest.diff")
	_tree_child(diff, "review latest.diff")
	_tree_child(diff, "clear latest.diff")

	var packet := _tree_child(root, "packet candidate/", false)
	_tree_child(packet, "create packet stub")

	var debug := _tree_child(root, "debug/", false)
	_tree_child(debug, "debug paths")

	scroll.add_child(box)
	return scroll

func _add_command_button(parent: VBoxContainer, label: String, primary: bool, callable: Callable) -> void:
	var b := Button.new()
	b.text = label
	_button(b, primary)
	main._connect_observed_button(b, label, callable)
	parent.add_child(b)

func build_workspace() -> Dictionary:
	var shell := PanelContainer.new()
	shell.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_panel(shell, Palette.PLUM_PANEL, Palette.GOLD_DARK, 1, 18)

	var workspace_tabs := TabContainer.new()
	workspace_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	shell.add_child(workspace_tabs)

	return {
		"node": shell,
		"workspace_tabs": workspace_tabs,
	}

func build_bottom() -> Dictionary:
	var refs := {}

	var bottom_shell := PanelContainer.new()
	bottom_shell.custom_minimum_size = Vector2(0, 245)
	_panel(bottom_shell, Palette.PLUM_DEEP, Palette.GOLD_DARK, 1, 16)
	refs["bottom_shell"] = bottom_shell

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
	main._connect_observed_button(exp, "Fullscreen Bottom", main._toggle_bottom)
	row.add_child(exp)

	var bottom_tabs := TabContainer.new()
	bottom_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	box.add_child(bottom_tabs)
	refs["bottom_tabs"] = bottom_tabs

	var approve_button := Button.new()
	approve_button.text = "Approve Proposal"
	approve_button.visible = false
	approve_button.pressed.connect(main._on_approve_task_pressed)
	_button(approve_button, true)
	box.add_child(approve_button)
	refs["approve_button"] = approve_button

	var terminal_input := LineEdit.new()
	terminal_input.placeholder_text = "Type operational intent (e.g., 'connect Gear to Dashboard')..."
	terminal_input.focus_mode = Control.FOCUS_ALL
	terminal_input.text_submitted.connect(main._on_terminal_input_submitted)
	box.add_child(terminal_input)
	refs["terminal_input"] = terminal_input

	_add_bottom(bottom_tabs, "Logs", "No CLI bridge output yet.")
	_add_bottom(bottom_tabs, "Diffs", "Diff proposal/review output will render here.\n\nviewed_diff != approved_diff")
	_add_bottom(bottom_tabs, "Packets", "Packet intake and registry output will render here.")
	_add_bottom(bottom_tabs, "Terminal", "CLI stdout/stderr will render here.")

	return {
		"node": bottom_shell,
		"refs": refs,
	}

func _add_bottom(bottom_tabs: TabContainer, name: String, content: String) -> void:
	var r := RichTextLabel.new()
	r.name = name
	r.bbcode_enabled = true
	r.selection_enabled = true
	r.text = "[color=#d6b15f]" + name + "[/color]\n\n" + content
	bottom_tabs.add_child(r)

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
