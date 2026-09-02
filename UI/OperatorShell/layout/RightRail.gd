extends RefCounted
class_name OperatorShellRightRail

const Palette = preload("res://widgets/Palette.gd")
const CliBridge = preload("res://runtime/CliBridge.gd")
const ModelServerController = preload("res://runtime/ModelServerController.gd")
const LibraryPanel = preload("res://widgets/LibraryPanel.gd")

var host
var right_mode_buttons := {}
var right_content: VBoxContainer
var controls_panel: Control
var library_panel: Control
var directory_panel: Control
var screens_panel: Control
var commands_panel: Control
var model_server_controller
var model_server_button: Button
var model_server_status_label: Label
var model_server_last_status: Dictionary = {}

func _init(owner) -> void:
	host = owner

func build() -> Control:
	var shell := PanelContainer.new()
	shell.custom_minimum_size = Vector2(340, 0)
	host._panel(shell, Palette.PLUM_DEEP, Palette.GOLD_DARK, 1, 16)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	shell.add_child(box)

	var rail_bar := HBoxContainer.new()
	rail_bar.add_theme_constant_override("separation", 6)

	var controls_btn := Button.new()
	controls_btn.text = "Controls"
	host._button(controls_btn, host.active_right_mode == "controls")
	controls_btn.pressed.connect(func(): host.set_right_mode("controls"))
	rail_bar.add_child(controls_btn)
	host.right_mode_buttons["controls"] = controls_btn

	var library_btn := Button.new()
	library_btn.text = "Library"
	host._button(library_btn, host.active_right_mode == "library")
	library_btn.pressed.connect(func(): host.set_right_mode("library"))
	rail_bar.add_child(library_btn)
	host.right_mode_buttons["library"] = library_btn

	box.add_child(rail_bar)

	controls_panel = VBoxContainer.new()
	controls_panel.size_flags_vertical = Control.SIZE_EXPAND_FILL
	controls_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	controls_panel.add_theme_constant_override("separation", 8)

	controls_panel.add_child(_build_model_server_control())

	var top := HBoxContainer.new()
	controls_panel.add_child(top)

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
	host._button(plus, true)
	host._connect_observed_button(plus, "New Chat", host._new_chat)
	top.add_child(plus)

	var refresh := Button.new()
	refresh.text = "Refresh State"
	host._button(refresh, true)
	host._connect_observed_button(refresh, "Refresh State", host._refresh_state_command)
	controls_panel.add_child(refresh)

	var test := Button.new()
	test.text = "Test"
	host._button(test, true)
	host._connect_observed_button(test, "Test", host._test_all)
	controls_panel.add_child(test)

	for mode in ["directory", "screens", "commands"]:
		var b := Button.new()
		b.text = mode.capitalize()
		host._button(b, mode == host.active_right_sub_mode)
		host._connect_observed_button(b, mode.capitalize(), func(m = mode): set_sub_mode(m))
		controls_panel.add_child(b)
		right_mode_buttons[mode] = b

	right_content = VBoxContainer.new()
	right_content.size_flags_vertical = Control.SIZE_EXPAND_FILL
	right_content.add_theme_constant_override("separation", 8)
	controls_panel.add_child(right_content)

	directory_panel = _build_directory_panel()
	screens_panel = _build_screens_panel()
	commands_panel = _build_commands_panel()

	right_content.add_child(directory_panel)
	right_content.add_child(screens_panel)
	right_content.add_child(commands_panel)

	box.add_child(controls_panel)
	host.controls_panel_control = controls_panel

	host.library_panel_widget = LibraryPanel.new(host)
	library_panel = host.library_panel_widget.build()
	library_panel.size_flags_vertical = Control.SIZE_EXPAND_FILL
	library_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box.add_child(library_panel)
	host.library_panel_control = library_panel

	set_sub_mode("", false)
	host.set_right_mode(host.active_right_mode, false)
	return shell

func _build_model_server_control() -> Control:
	var box := VBoxContainer.new()
	box.name = "ModelServerControl"
	box.add_theme_constant_override("separation", 2)
	box.custom_minimum_size = Vector2(0, 48)

	var title := Label.new()
	title.text = "MODEL SERVER"
	title.add_theme_font_size_override("font_size", 10)
	title.add_theme_color_override("font_color", Palette.TEXT_DIM)
	box.add_child(title)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)

	model_server_button = Button.new()
	model_server_button.text = "OFF"
	host._button(model_server_button, false)
	model_server_button.pressed.connect(_on_model_server_button_pressed)
	row.add_child(model_server_button)

	model_server_status_label = Label.new()
	model_server_status_label.text = "configured"
	model_server_status_label.add_theme_font_size_override("font_size", 10)
	model_server_status_label.add_theme_color_override("font_color", Palette.TEXT_DIM)
	row.add_child(model_server_status_label)

	box.add_child(row)

	model_server_controller = ModelServerController.new()
	model_server_controller.status_changed.connect(_on_model_server_status_changed)
	_update_model_server_control({"status": "stopped", "reason": "status loading", "configured": true})
	model_server_controller.refresh_now()

	return box

func _on_model_server_button_pressed() -> void:
	if model_server_controller:
		model_server_controller.toggle()

func _on_model_server_status_changed(payload: Dictionary) -> void:
	_update_model_server_control(payload)

func _update_model_server_control(payload: Dictionary) -> void:
	model_server_last_status = payload
	if model_server_button == null or model_server_status_label == null:
		return

	var status := str(payload.get("status", "unknown"))
	var reason := str(payload.get("reason", ""))
	var configured := bool(payload.get("configured", false))

	match status:
		"running":
			model_server_button.text = "ON"
			host._button(model_server_button, true)
			model_server_status_label.text = "running"
			model_server_status_label.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
		"starting":
			model_server_button.text = "..."
			host._button(model_server_button, false)
			model_server_status_label.text = "starting"
			model_server_status_label.add_theme_color_override("font_color", Palette.GOLD_SOFT)
		"stopping":
			model_server_button.text = "..."
			host._button(model_server_button, false)
			model_server_status_label.text = "stopping"
			model_server_status_label.add_theme_color_override("font_color", Palette.GOLD_SOFT)
		"stopped":
			model_server_button.text = "OFF"
			host._button(model_server_button, false)
			model_server_status_label.text = "stopped"
			model_server_status_label.add_theme_color_override("font_color", Palette.TEXT_DIM)
		_:
			model_server_button.text = "ERR"
			host._button(model_server_button, false)
			model_server_status_label.text = status if reason == "" else status + ": " + reason
			model_server_status_label.add_theme_color_override("font_color", Palette.TEXT_DIM)

func _make_tree(name: String, height: int) -> Tree:
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

func _build_directory_panel() -> Control:
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
	tree.item_selected.connect(func(item): _on_directory_item_selected(item))
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

func _build_screens_panel() -> Control:
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
		host._button(b, false)
		host._connect_observed_button(b, s, func(name = s): host._open_screen(name))
		box.add_child(b)

	var tree := _make_tree("Screens", 230)
	box.add_child(tree)
	var root := _tree_root(tree, "Screens/")
	var workspace := _tree_child(root, "workspace tabs/", false)
	for s in ["Home", "State", "Agents", "Packets", "Diffs", "Logs", "Settings", "AI Assist"]:
		_tree_child(workspace, s + " surface", false)

	scroll.add_child(box)
	return scroll

func _build_commands_panel() -> Control:
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

	_add_command_button(box, "Scan Core", false, host._scan_core)
	_add_command_button(box, "Git Status", false, host._git_status)
	_add_command_button(box, "Cali Observe Directory", false, host._cali_observe_directory)
	_add_command_button(box, "Propose Directory Diff", false, host._propose_diff)
	_add_command_button(box, "View Latest Diff", false, host._view_latest_diff)
	_add_command_button(box, "Review Latest Diff", false, host._review_latest_diff)
	_add_command_button(box, "Clear Latest Diff", false, host._clear_latest_diff)
	_add_command_button(box, "List Packets", false, host._list_packets)
	_add_command_button(box, "Create Packet Stub", false, host._create_packet_stub)
	_add_command_button(box, "Test State Update", false, host._test_state_update)
	_add_command_button(box, "Debug Paths", false, func(): host._terminal("Path debug\n" + CliBridge.debug_paths()))
	_add_command_button(box, "Gemini Analyze Core", false, host._gemini_analyze_core)

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
	host._button(b, primary)
	host._connect_observed_button(b, label, callable)
	parent.add_child(b)

func _on_directory_item_selected(item: TreeItem) -> void:
	if item == null:
		return
	var path := _directory_item_path(item)
	if path == "":
		return
	_open_directory_surface(path)

func _directory_item_path(item: TreeItem) -> String:
	var parts := []
	var current := item
	while current:
		var text := str(current.get_text(0)).strip_edges()
		if text != "":
			if text.ends_with("/"):
				text = text.substr(0, text.length() - 1)
			parts.insert(0, text)
		current = current.get_parent()
	return "/".join(parts)

func _open_directory_surface(path: String) -> void:
	var name := "Directory"
	var existing := -1
	for i in host.workspace_tabs.get_tab_count():
		if host.workspace_tabs.get_tab_title(i) == name:
			existing = i
			break

	var content_text := "[color=#f3edf7]Directory Navigation[/color]\n\nSelected path:\n" + path + "\n\nRead-only navigation only."

	if existing != -1:
		var tab_node: Node = host.workspace_tabs.get_child(existing)
		if tab_node and tab_node.get_child_count() >= 2:
			var label: Node = tab_node.get_child(1)
			if label is RichTextLabel:
				label.text = content_text
		host.workspace_tabs.current_tab = existing
	else:
		var box := VBoxContainer.new()
		box.add_theme_constant_override("separation", 12)
		var title := Label.new()
		title.text = name
		title.add_theme_font_size_override("font_size", 24)
		title.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
		box.add_child(title)
		var text := RichTextLabel.new()
		text.bbcode_enabled = true
		text.selection_enabled = true
		text.text = content_text
		box.add_child(text)
		host._add_or_focus_tab(name, box)

	host.active_surface = name
	host._render_current_status()

func set_sub_mode(mode: String, observed := true) -> void:
	if mode == host.active_right_sub_mode:
		host.active_right_sub_mode = ""
	else:
		host.active_right_sub_mode = mode

	if directory_panel:
		directory_panel.visible = (host.active_right_sub_mode == "directory")
	if screens_panel:
		screens_panel.visible = (host.active_right_sub_mode == "screens")
	if commands_panel:
		commands_panel.visible = (host.active_right_sub_mode == "commands")

	for key in right_mode_buttons.keys():
		if right_mode_buttons.has(key):
			host._button(right_mode_buttons[key], key == host.active_right_sub_mode)

	host._update_awareness_mode(host.active_right_sub_mode)
	host._render_current_status()
	if observed and host.active_right_sub_mode != "":
		host._observe_surface("right:" + host.active_right_sub_mode)
