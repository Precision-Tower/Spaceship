extends Control
const Palette = preload("res://screen/scripts/widgets/Palette.gd")
const CliBridge = preload("res://screen/scripts/runtime/CliBridge.gd")

var awareness_label: RichTextLabel
var history_label: RichTextLabel
var state_label: Label
var workspace_tabs: TabContainer
var bottom_tabs: TabContainer
var bottom_shell: PanelContainer

var right_mode_buttons := {}
var right_content: VBoxContainer
var directory_panel: VBoxContainer
var screens_panel: VBoxContainer
var commands_panel: VBoxContainer

var chat_count := 0
var bottom_expanded := false
var active_right_mode := "directory"
var command_history: Array[Dictionary] = []

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
	root.add_child(_runtime_state_bar())

	var main := HSplitContainer.new()
	main.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(main)

	main.add_child(_left_awareness())

	var center := VBoxContainer.new()
	center.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	main.add_child(center)
	center.add_child(_workspace())
	center.add_child(_bottom())

	main.add_child(_right_control_rail())

func _top_bar() -> Control:
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

func _runtime_state_bar() -> Control:
	var p := PanelContainer.new()
	p.custom_minimum_size = Vector2(0, 78)
	_panel(p, Palette.PLUM_CARD, Palette.GOLD_DARK, 1, 14)
	state_label = Label.new()
	state_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	state_label.add_theme_color_override("font_color", Palette.TEXT)
	state_label.text = "Runtime State\nstatus: booted_not_refreshed | latest_diff: unknown | git_dirty: unknown | packets_pending: unknown\nboundary: runtime_state_reports_observation_only"
	p.add_child(state_label)
	return p

func _left_awareness() -> Control:
	var shell := PanelContainer.new()
	shell.custom_minimum_size = Vector2(320, 0)
	_panel(shell, Palette.PLUM_DEEP, Palette.GOLD_DARK, 1, 16)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	shell.add_child(box)

	awareness_label = RichTextLabel.new()
	awareness_label.bbcode_enabled = true
	awareness_label.selection_enabled = true
	awareness_label.custom_minimum_size = Vector2(0, 285)
	awareness_label.text = _awareness_default()
	box.add_child(awareness_label)

	var sep := HSeparator.new()
	box.add_child(sep)

	history_label = RichTextLabel.new()
	history_label.bbcode_enabled = true
	history_label.selection_enabled = true
	history_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	history_label.text = "[color=#f1d58a]Command History[/color]\n\n(no commands yet)\n\n[color=#b8aebe]history != evidence[/color]"
	box.add_child(history_label)

	return shell

func _awareness_default() -> String:
	return "[color=#f1d58a]Operational Awareness[/color]\n\n" + \
		"[color=#d6b15f]Focus[/color]\n" + \
		"surface: Home\n" + \
		"tree: directory\n" + \
		"last_cmd: none\n" + \
		"packet: none | diff: none\n" + \
		"root: Core\n" + \
		"focus != authority\n\n" + \
		"[color=#d6b15f]Live State[/color]\n" + \
		"refresh required for current values\n" + \
		"latest_diff: unknown\n" + \
		"git_dirty: unknown\n" + \
		"packets_pending: unknown\n\n" + \
		"[color=#d6b15f]Copy/Paste[/color]\n" + \
		"Test report | Runtime state\n" + \
		"Latest diff | Packet listing\n\n" + \
		"[color=#d6b15f]Boundaries[/color]\n" + \
		"runtime_health != readiness\n" + \
		"green_status != safe\n" + \
		"display != authority\n" + \
		"history != evidence\n" + \
		"compact_display != completeness"

func _right_control_rail() -> Control:
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
	plus.pressed.connect(_new_chat)
	top.add_child(plus)

	var refresh := Button.new()
	refresh.text = "Refresh State"
	_button(refresh, true)
	refresh.pressed.connect(_refresh_state_command)
	box.add_child(refresh)

	var test := Button.new()
	test.text = "Test"
	_button(test, true)
	test.pressed.connect(_test_all)
	box.add_child(test)

	for mode in ["directory", "screens", "commands"]:
		var b := Button.new()
		b.text = mode.capitalize()
		_button(b, mode == active_right_mode)
		b.pressed.connect(func(m = mode): _set_right_mode(m))
		box.add_child(b)
		right_mode_buttons[mode] = b

	right_content = VBoxContainer.new()
	right_content.size_flags_vertical = Control.SIZE_EXPAND_FILL
	right_content.add_theme_constant_override("separation", 8)
	box.add_child(right_content)

	directory_panel = _build_directory_panel()
	screens_panel = _build_screens_panel()
	commands_panel = _build_commands_panel()

	right_content.add_child(directory_panel)
	right_content.add_child(screens_panel)
	right_content.add_child(commands_panel)

	_set_right_mode("directory")
	return shell

func _make_tree(title: String, height: int) -> Tree:
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

func _build_directory_panel() -> VBoxContainer:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	box.size_flags_vertical = Control.SIZE_EXPAND_FILL

	var label := Label.new()
	label.text = "Directory Map"
	label.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
	box.add_child(label)

	var tree := _make_tree("Directory", 430)
	box.add_child(tree)
	var root := _tree_root(tree, "Core/")
	var dashboard := _tree_child(root, "Dashboard/", false)
	_tree_child(dashboard, "Models/", true)
	_tree_child(dashboard, "Tools/", true)
	var ui := _tree_child(dashboard, "UI/", false)
	var screen := _tree_child(ui, "screen/", true)
	_tree_child(screen, "scenes/", true)
	_tree_child(screen, "scripts/", true)
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
	return box

func _build_screens_panel() -> VBoxContainer:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	box.size_flags_vertical = Control.SIZE_EXPAND_FILL

	var label := Label.new()
	label.text = "Screens Map"
	label.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
	box.add_child(label)

	var tree := _make_tree("Screens", 230)
	box.add_child(tree)
	var root := _tree_root(tree, "Screens/")
	var workspace := _tree_child(root, "workspace tabs/", false)
	for s in ["Home", "State", "Agents", "Packets", "Diffs", "Logs", "Settings"]:
		_tree_child(workspace, s + " surface", false)

	for s in ["Home", "State", "Agents", "Packets", "Diffs", "Logs", "Settings"]:
		var b := Button.new()
		b.text = s
		_button(b, false)
		b.pressed.connect(func(name = s): _open_screen(name))
		box.add_child(b)
	return box

func _build_commands_panel() -> VBoxContainer:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	box.size_flags_vertical = Control.SIZE_EXPAND_FILL

	var label := Label.new()
	label.text = "Commands Map"
	label.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
	box.add_child(label)

	var tree := _make_tree("Commands", 260)
	box.add_child(tree)
	var root := _tree_root(tree, "Command Surfaces/")
	var observe := _tree_child(root, "observe/read-only/", false)
	_tree_child(observe, "scan Core")
	_tree_child(observe, "git status")
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

	_add_command_button(box, "Scan Core", false, _scan_core)
	_add_command_button(box, "Git Status", false, _git_status)
	_add_command_button(box, "Propose Directory Diff", false, _propose_diff)
	_add_command_button(box, "View Latest Diff", false, _view_latest_diff)
	_add_command_button(box, "Review Latest Diff", false, _review_latest_diff)
	_add_command_button(box, "Clear Latest Diff", false, _clear_latest_diff)
	_add_command_button(box, "List Packets", false, _list_packets)
	_add_command_button(box, "Create Packet Stub", false, _create_packet_stub)
	_add_command_button(box, "Debug Paths", false, func(): _terminal("Path debug\n" + CliBridge.debug_paths()))

	return box

func _add_command_button(parent: VBoxContainer, label: String, primary: bool, callable: Callable) -> void:
	var b := Button.new()
	b.text = label
	_button(b, primary)
	b.pressed.connect(callable)
	parent.add_child(b)

func _set_right_mode(mode: String) -> void:
	active_right_mode = mode
	if directory_panel:
		directory_panel.visible = mode == "directory"
	if screens_panel:
		screens_panel.visible = mode == "screens"
	if commands_panel:
		commands_panel.visible = mode == "commands"

	for key in right_mode_buttons.keys():
		_button(right_mode_buttons[key], key == mode)

	_update_awareness_mode(mode)

func _workspace() -> Control:
	var shell := PanelContainer.new()
	shell.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_panel(shell, Palette.PLUM_PANEL, Palette.GOLD_DARK, 1, 18)
	workspace_tabs = TabContainer.new()
	workspace_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	shell.add_child(workspace_tabs)
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
	_add_bottom("Diffs", "Diff proposal/review output will render here.\n\nviewed_diff != approved_diff")
	_add_bottom("Packets", "Packet intake and registry output will render here.")
	_add_bottom("Terminal", "CLI stdout/stderr will render here.")
	return bottom_shell

func _seed() -> void:
	_new_chat()
	_open_screen("Home")
	_log("Phase 4.5 loaded. Operator-triggered state refresh only.")
	_terminal("Path debug\n" + CliBridge.debug_paths())

func _new_chat() -> void:
	chat_count += 1
	var name := "Chat %02d" % chat_count
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
	transcript.selection_enabled = true
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
	text.selection_enabled = true
	if name == "State":
		text.text = "[color=#f3edf7]Runtime State Surface[/color]\n\nPersistent state is observation only.\n\nRefresh State for current snapshot.\n\ngreen_status != safe\nruntime_health != readiness"
	elif name == "Packets":
		text.text = "[color=#f3edf7]Packet System Seed[/color]\n\nIncoming -> Reviewed -> Promoted -> Rejected\n\ncandidate_packet != canon\npromoted_packet != true"
	elif name == "Diffs":
		text.text = "[color=#f3edf7]Diff Review Surface[/color]\n\n1. Propose Directory Diff\n2. View Latest Diff\n3. Review Latest Diff\n4. Clear Latest Diff\n\nproposal != patch\nreview_button != governance_decision\napply_patch is intentionally absent"
	else:
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
	r.selection_enabled = true
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

func _diff(text: String) -> void:
	var d := _bottom_text("Diffs")
	if d:
		d.append_text("\n\n[color=#d6b15f]>[/color] " + text)
	_set_bottom("Diffs")

func _packets(text: String) -> void:
	var p := _bottom_text("Packets")
	if p:
		p.append_text("\n\n[color=#d6b15f]>[/color] " + text)
	_set_bottom("Packets")

func _record_command(name: String, result: Dictionary, summary: String) -> void:
	var status := "success" if result.get("ok", false) else "failed"
	command_history.push_front({
		"command": name,
		"status": status,
		"time": Time.get_time_string_from_system(),
		"summary": summary
	})
	if command_history.size() > 10:
		command_history.pop_back()
	_render_history()

func _render_history() -> void:
	if not history_label:
		return
	var text := "[color=#f1d58a]Command History[/color]\n"
	if command_history.is_empty():
		text += "\n(no commands yet)\n"
	else:
		for row in command_history:
			var status := str(row.get("status", "unknown"))
			var color := "#8fca7a" if status == "success" else "#e05f5f"
			text += "\n[color=" + color + "]status: " + status + "[/color]\n"
			text += "time: " + str(row.get("time", "--:--")) + "\n"
			text += "command: " + str(row.get("command", "unknown")) + "\n"
			text += "summary: " + str(row.get("summary", "")) + "\n"
	text += "\n[color=#b8aebe]history != evidence[/color]"
	history_label.text = text

func _refresh_state_from_output(output: String) -> void:
	var stamp := Time.get_time_string_from_system()
	var short := output.strip_edges()
	if short.length() > 600:
		short = short.substr(0, 600) + "\n..."
	state_label.text = "Runtime State\nlast_refreshed: " + stamp + "\n" + short + "\nboundary: refresh_is_observation_only_not_validation"
	_update_awareness_from_state(short)

func _update_awareness_mode(mode: String) -> void:
	if awareness_label:
		awareness_label.text = _awareness_default()

func _update_awareness_from_state(state_text: String) -> void:
	if awareness_label:
		awareness_label.text = "[color=#f1d58a]Operational Awareness[/color]\n\n" + \
			"[color=#d6b15f]Focus[/color]\n" + \
			"surface: Home\n" + \
			"tree: " + active_right_mode + "\n" + \
			"last_cmd: Refresh State\n" + \
			"packet: none | diff: see state\n" + \
			"root: Core\n" + \
			"focus != authority\n\n" + \
			"[color=#d6b15f]Live State[/color]\n" + \
			"last_refreshed: " + Time.get_time_string_from_system() + "\n" + \
			"source: operator-triggered Refresh State\n" + \
			"full report: Terminal\n" + \
			"refresh != validation\n\n" + \
			"[color=#d6b15f]Copy/Paste[/color]\n" + \
			"Test report | Runtime state\n" + \
			"Latest diff | Packet listing\n\n" + \
			"[color=#d6b15f]Boundaries[/color]\n" + \
			"runtime_health != readiness\n" + \
			"green_status != safe\n" + \
			"display != authority\n" + \
			"history != evidence"

func _refresh_state_command() -> void:
	_log("runtime-state requested")
	var r := CliBridge.runtime_state()
	_render_terminal(r)
	_refresh_state_from_output(str(r.get("stdout", "")))
	_record_command("Refresh State", r, "runtime state refreshed")

func _test_all() -> void:
	_log("test-all requested")
	_terminal("Running structured validation report. Copy/paste this output back to Gear.")
	var r := CliBridge.test_all()
	_render_terminal(r)
	_record_command("Test", r, "structured validation report generated")

func _scan_core() -> void:
	_log("scan-core requested")
	_terminal("Running scan-repo against Core...")
	var r := CliBridge.scan_core()
	_render_terminal(r)
	_record_command("Scan Core", r, "Core scan executed")

func _git_status() -> void:
	_log("git-status requested")
	_terminal("Running git-status against Core...")
	var r := CliBridge.git_status_core()
	_render_terminal(r)
	_record_command("Git Status", r, "Git status executed")

func _propose_diff() -> void:
	_log("propose-directory-diff requested")
	_diff("Running propose-directory-diff against Core...")
	var r := CliBridge.propose_directory_diff_core()
	_render_diff(r)
	_record_command("Propose Directory Diff", r, "latest.diff proposal attempted")

func _view_latest_diff() -> void:
	_log("view-latest-diff requested")
	_diff("Viewing latest.diff...")
	var r := CliBridge.view_latest_diff()
	_render_diff(r)
	_record_command("View Latest Diff", r, "latest.diff display attempted")

func _review_latest_diff() -> void:
	_log("grant-review-latest-diff requested")
	_diff("Reviewing latest.diff...")
	var r := CliBridge.grant_review_latest_diff()
	_render_diff(r)
	_record_command("Review Latest Diff", r, "lexical review executed")

func _clear_latest_diff() -> void:
	_log("clear-latest-diff requested")
	_diff("Clearing latest.diff with archive tombstone...")
	var r := CliBridge.clear_latest_diff()
	_render_diff(r)
	_record_command("Clear Latest Diff", r, "latest.diff clear/archive attempted")

func _list_packets() -> void:
	_log("list-packets requested")
	_packets("Listing packet registry...")
	var r := CliBridge.list_packets()
	_render_packets(r)
	_record_command("List Packets", r, "packet listing executed")

func _create_packet_stub() -> void:
	_log("create-packet requested")
	_packets("Creating packet stub...")
	var r := CliBridge.create_packet_stub()
	_render_packets(r)
	_record_command("Create Packet Stub", r, "incoming packet stub attempted")

func _format(result: Dictionary) -> String:
	var text := ""
	text += "command: " + str(result.get("command", "")) + "\n"
	text += "exit_code: " + str(result.get("exit_code", "")) + "\n"
	text += "python: " + str(result.get("python", "")) + "\n"
	text += "args: " + str(result.get("args", "")) + "\n"
	text += "debug_paths:\n" + str(result.get("debug_paths", "")) + "\n\n"
	text += str(result.get("stdout", ""))
	if result.get("ok", false):
		return "[color=#8fca7a]CLI command completed.[/color]\n" + text
	return "[color=#e05f5f]CLI command failed.[/color]\n" + text

func _render_terminal(result: Dictionary) -> void:
	_terminal(_format(result))

func _render_diff(result: Dictionary) -> void:
	_diff(_format(result))

func _render_packets(result: Dictionary) -> void:
	_packets(_format(result))

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
