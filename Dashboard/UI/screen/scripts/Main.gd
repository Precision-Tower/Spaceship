extends Control
const Palette = preload("res://screen/scripts/widgets/Palette.gd")
const CliBridge = preload("res://screen/scripts/runtime/CliBridge.gd")

const OBSERVATION_MAX_LINES := 12
const OBSERVATION_ROUTE_MAX := 5
const OBSERVATION_NOT_OBSERVED_MAX := 4
const OBSERVATION_SURFACES := [
	"Home",
	"State",
	"Agents",
	"Packets",
	"Diffs",
	"Logs",
	"Settings",
	"Chat",
	"right:directory",
	"right:screens",
	"right:commands"
]

var awareness_label: RichTextLabel
var history_label: RichTextLabel
var current_status_label: RichTextLabel
var mission_label: RichTextLabel
var operator_observation_label: RichTextLabel
var state_label: Label
var workspace_tabs: TabContainer
var bottom_tabs: TabContainer
var bottom_shell: PanelContainer

var right_mode_buttons := {}
var right_content: VBoxContainer
var directory_panel: Control
var screens_panel: Control
var commands_panel: Control

var chat_count := 0
var bottom_expanded := false
var active_right_mode := ""
var active_surface := "Home"
var command_history: Array[Dictionary] = []
var left_panel_collapsed := {
	"mission": false,
	"status": true,
	"observation": true,
	"awareness": true,
	"history": true,
	"boundaries": true
}
var left_panel_buttons := {}
var operator_click_counts := {}
var operator_panel_toggles := {}
var operator_surface_visits := {}
var operator_recent_routes: Array[String] = []
var operator_last_event := "none"
var current_status := {
	"current_root": "Core",
	"dashboard_boot": "booted_not_refreshed",
	"latest_diff": "unknown",
	"packets_pending": "unknown",
	"git_dirty": "unknown",
	"last_command": "none",
	"next_required_action": "Refresh State"
}

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

	# Mission section (read-only) - top flex zone
	mission_label = _left_text(180)
	mission_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	mission_label.text = _mission_text_from_data(_read_mission())

	var mission_scroll := ScrollContainer.new()
	mission_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	mission_scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var mission_section := _collapsible_left_section("mission", "Mission", mission_label)
	mission_section.size_flags_vertical = Control.SIZE_EXPAND_FILL
	mission_scroll.add_child(mission_section)
	box.add_child(mission_scroll)

	var status_sep := HSeparator.new()
	box.add_child(status_sep)

	var bottom_stack := VBoxContainer.new()
	bottom_stack.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bottom_stack.size_flags_vertical = Control.SIZE_SHRINK_CENTER

	current_status_label = _left_text(120)
	current_status_label.text = _current_status_text()
	bottom_stack.add_child(_collapsible_left_section("status", "Current Status", current_status_label))

	operator_observation_label = _left_text(210)
	operator_observation_label.text = _operator_observation_text()
	bottom_stack.add_child(_collapsible_left_section("observation", "Operator Observation", operator_observation_label))

	awareness_label = RichTextLabel.new()
	awareness_label.bbcode_enabled = true
	awareness_label.selection_enabled = true
	awareness_label.custom_minimum_size = Vector2(0, 285)
	awareness_label.text = _awareness_default()
	bottom_stack.add_child(_collapsible_left_section("awareness", "Operational Awareness", awareness_label))

	history_label = RichTextLabel.new()
	history_label.bbcode_enabled = true
	history_label.selection_enabled = true
	history_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	history_label.text = "[color=#f1d58a]Command History[/color]\n\n(no commands yet)\n\n[color=#b8aebe]history != evidence[/color]"
	bottom_stack.add_child(_collapsible_left_section("history", "Command History", history_label))

	var boundaries := _left_text(185)
	boundaries.text = _boundaries_default()
	bottom_stack.add_child(_collapsible_left_section("boundaries", "Runtime Boundaries", boundaries))

	box.add_child(bottom_stack)
	return shell

func _left_text(height: int) -> RichTextLabel:
	var r := RichTextLabel.new()
	r.bbcode_enabled = true
	r.selection_enabled = true
	# Ensure the Mission text has enough horizontal space to avoid awkward wrapping
	# without changing overall layout. Set a sensible min width to fit content.
	r.custom_minimum_size = Vector2(280, height)
	r.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return r

func _collapsible_left_section(key: String, title: String, content: Control) -> VBoxContainer:
	var section := VBoxContainer.new()
	section.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	section.add_theme_constant_override("separation", 6)
	var collapsed := bool(left_panel_collapsed.get(key, true))
	var b := Button.new()
	b.text = _collapse_label(title, collapsed)
	_button(b, false)
	b.pressed.connect(func(): _toggle_left_section(key, content))
	section.add_child(b)
	content.visible = not collapsed
	section.add_child(content)
	left_panel_buttons[key] = b
	return section

func _collapse_label(title: String, collapsed: bool) -> String:
	return "+ " + title if collapsed else "- " + title

func _left_section_title(key: String) -> String:
	if key == "observation":
		return "Operator Observation"
	if key == "awareness":
		return "Operational Awareness"
	if key == "history":
		return "Command History"
	if key == "mission":
		return "Mission"
	if key == "status":
		return "Current Status"
	return "Runtime Boundaries"

func _toggle_left_section(key: String, content: Control) -> void:
	var collapsed := not bool(left_panel_collapsed.get(key, true))
	left_panel_collapsed[key] = collapsed
	content.visible = not collapsed
	if left_panel_buttons.has(key):
		var b: Button = left_panel_buttons[key]
		b.text = _collapse_label(_left_section_title(key), collapsed)
	_observe_panel_toggle(key, not collapsed)

func _current_status_text() -> String:
	return "[color=#f1d58a]Current Status[/color]\n" + \
		"[color=#d6b15f]current_root[/color]=" + _status_value("current_root") + "\n" + \
		"[color=#d6b15f]dashboard_boot[/color]=" + _status_value("dashboard_boot") + "\n" + \
		"[color=#d6b15f]latest_diff[/color]=" + _status_value("latest_diff") + "\n" + \
		"[color=#d6b15f]packets_pending[/color]=" + _status_value("packets_pending") + "\n" + \
		"[color=#d6b15f]git_dirty[/color]=" + _status_value("git_dirty") + "\n" + \
		"[color=#d6b15f]last_command[/color]=" + _status_value("last_command") + "\n" + \
		"[color=#d6b15f]active_surface[/color]=" + active_surface + " / " + active_right_mode + "\n" + \
		"[color=#d6b15f]next_required_action[/color]=" + _status_value("next_required_action") + "\n" + \
		"[color=#b8aebe]status != validation[/color]"

func _status_value(key: String) -> String:
	return str(current_status.get(key, "unknown"))

func _set_status_value(key: String, value: String) -> void:
	current_status[key] = value
	_render_current_status()

func _render_current_status() -> void:
	if current_status_label:
		current_status_label.text = _current_status_text()

func _state_field(state_text: String, key: String, fallback: String) -> String:
	for line in state_text.split("\n"):
		var clean := str(line).strip_edges()
		var colon := clean.find(":")
		var equals := clean.find("=")
		var split_at := colon
		if split_at == -1 or (equals != -1 and equals < split_at):
			split_at = equals
		if split_at == -1:
			continue
		if clean.substr(0, split_at).strip_edges() == key:
			return clean.substr(split_at + 1, clean.length() - split_at - 1).strip_edges()
	return fallback

func _update_status_from_state_text(state_text: String, ok := true) -> void:
	current_status["current_root"] = _state_field(state_text, "current_root", _status_value("current_root"))
	current_status["dashboard_boot"] = _state_field(state_text, "dashboard_boot", _status_value("dashboard_boot"))
	current_status["latest_diff"] = _state_field(state_text, "latest_diff", _status_value("latest_diff"))
	current_status["packets_pending"] = _state_field(state_text, "packets_pending", _status_value("packets_pending"))
	current_status["git_dirty"] = _state_field(state_text, "git_dirty", _status_value("git_dirty"))
	current_status["next_required_action"] = "Review refreshed state" if ok else "Inspect Refresh State failure"
	_render_current_status()

func _connect_observed_button(button: Button, label: String, callable: Callable) -> void:
	button.pressed.connect(func(): _observed_call(label, callable))

func _observed_call(label: String, callable: Callable) -> void:
	_observe_button(label)
	callable.call()

func _observe_button(label: String) -> void:
	_increment_count(operator_click_counts, label)
	_observe_event("button", label)

func _observe_surface(surface: String) -> void:
	_increment_count(operator_surface_visits, surface)
	_push_route(surface)
	_observe_event("surface", surface)

func _observe_chat_surface(name: String) -> void:
	_increment_count(operator_surface_visits, "Chat")
	_push_route(name)
	_observe_event("surface", name)

func _observe_panel_toggle(key: String, opened: bool) -> void:
	var state := "open" if opened else "closed"
	var label := _left_section_title(key)
	_increment_count(operator_panel_toggles, label)
	_observe_event("panel", label + "=" + state)

func _observe_event(kind: String, detail: String) -> void:
	operator_last_event = kind + ": " + detail
	_render_operator_observation()

func _increment_count(counts: Dictionary, key: String) -> void:
	counts[key] = int(counts.get(key, 0)) + 1

func _push_route(route: String) -> void:
	operator_recent_routes.append(route)
	while operator_recent_routes.size() > OBSERVATION_ROUTE_MAX:
		operator_recent_routes.pop_front()

func _render_operator_observation() -> void:
	if operator_observation_label:
		operator_observation_label.text = _operator_observation_text()

func _operator_observation_text() -> String:
	return _cap_observation_lines("[color=#f1d58a]Operator Observation[/color]\n" + \
		"observed_clicks: " + _compact_counts(operator_click_counts, 4) + "\n" + \
		"panel_state: " + _panel_state_text() + "\n" + \
		"panel_toggles: " + _compact_counts(operator_panel_toggles, 3) + "\n" + \
		"surface_visits: " + _compact_counts(operator_surface_visits, 4) + "\n" + \
		"recent_routes: " + _recent_routes_text() + "\n" + \
		"not_observed_this_session: " + _not_observed_text() + "\n" + \
		"last_operator_event: " + operator_last_event + "\n" + \
		"[color=#b8aebe]observation != interpretation[/color]")

func _compact_counts(counts: Dictionary, max_entries: int) -> String:
	if counts.is_empty():
		return "none"
	var keys := _count_keys_by_frequency(counts)
	var parts: Array[String] = []
	var limit = min(keys.size(), max_entries)
	for i in limit:
		var key := str(keys[i])
		parts.append(key + "=" + str(counts.get(key, 0)))
	if keys.size() > max_entries:
		parts.append("+" + str(keys.size() - max_entries))
	return _join_strings(parts, ", ")

func _count_keys_by_frequency(counts: Dictionary) -> Array:
	var keys := counts.keys()
	keys.sort_custom(func(a, b):
		var count_a := int(counts.get(str(a), 0))
		var count_b := int(counts.get(str(b), 0))
		if count_a == count_b:
			return str(a) < str(b)
		return count_a > count_b
	)
	return keys

func _panel_state_text() -> String:
	var parts: Array[String] = ["current_status=open"]
	for key in ["observation", "awareness", "history", "boundaries"]:
		var state := "closed" if bool(left_panel_collapsed.get(key, true)) else "open"
		parts.append(str(key) + "=" + state)
	return _join_strings(parts, ", ")

func _recent_routes_text() -> String:
	if operator_recent_routes.is_empty():
		return "none"
	return _join_strings(operator_recent_routes, " -> ")

func _not_observed_text() -> String:
	var missing: Array[String] = []
	for surface in OBSERVATION_SURFACES:
		if int(operator_surface_visits.get(str(surface), 0)) == 0:
			missing.append(str(surface))
		if missing.size() >= OBSERVATION_NOT_OBSERVED_MAX:
			break
	if missing.is_empty():
		return "none"
	return _join_strings(missing, ", ")

func _cap_observation_lines(text: String) -> String:
	var lines := text.split("\n")
	var capped: Array[String] = []
	var limit = min(lines.size(), OBSERVATION_MAX_LINES)
	for i in limit:
		capped.append(str(lines[i]))
	return _join_strings(capped, "\n")

func _join_strings(items: Array[String], separator: String) -> String:
	var text := ""
	for i in items.size():
		if i > 0:
			text += separator
		text += items[i]
	return text

func _boundaries_default() -> String:
	return "[color=#f1d58a]Runtime Boundaries[/color]\n\n" + \
		"status != validation\n" + \
		"history != evidence\n" + \
		"display != authority\n" + \
		"collapsed_panel != inactive_authority\n" + \
		"refresh != readiness\n" + \
		"proposal != patch"

func _awareness_default() -> String:
	return "[color=#f1d58a]Operational Awareness[/color]\n\n" + \
		"[color=#d6b15f]Focus[/color]\n" + \
		"surface: " + active_surface + "\n" + \
		"tree: " + active_right_mode + "\n" + \
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
	_connect_observed_button(plus, "New Chat", _new_chat)
	top.add_child(plus)

	var refresh := Button.new()
	refresh.text = "Refresh State"
	_button(refresh, true)
	_connect_observed_button(refresh, "Refresh State", _refresh_state_command)
	box.add_child(refresh)

	var test := Button.new()
	test.text = "Test"
	_button(test, true)
	_connect_observed_button(test, "Test", _test_all)
	box.add_child(test)

	for mode in ["directory", "screens", "commands"]:
		var b := Button.new()
		b.text = mode.capitalize()
		_button(b, mode == active_right_mode)
		_connect_observed_button(b, mode.capitalize(), func(m = mode): _set_right_mode(m))
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

	_set_right_mode("", false)
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
		_button(b, false)
		_connect_observed_button(b, s, func(name = s): _open_screen(name))
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

	_add_command_button(box, "Scan Core", false, _scan_core)
	_add_command_button(box, "Git Status", false, _git_status)
	_add_command_button(box, "Cali Observe Directory", false, _cali_observe_directory)
	_add_command_button(box, "Propose Directory Diff", false, _propose_diff)
	_add_command_button(box, "View Latest Diff", false, _view_latest_diff)
	_add_command_button(box, "Review Latest Diff", false, _review_latest_diff)
	_add_command_button(box, "Clear Latest Diff", false, _clear_latest_diff)
	_add_command_button(box, "List Packets", false, _list_packets)
	_add_command_button(box, "Create Packet Stub", false, _create_packet_stub)
	_add_command_button(box, "Debug Paths", false, func(): _terminal("Path debug\n" + CliBridge.debug_paths()))

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
	_connect_observed_button(b, label, callable)
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
	for i in workspace_tabs.get_tab_count():
		if workspace_tabs.get_tab_title(i) == name:
			existing = i
			break

	var content_text := "[color=#f3edf7]Directory Navigation[/color]\n\nSelected path:\n" + path + "\n\nRead-only navigation only."

	if existing != -1:
		var tab_node := workspace_tabs.get_child(existing)
		if tab_node and tab_node.get_child_count() >= 2:
			var label := tab_node.get_child(1)
			if label is RichTextLabel:
				label.text = content_text
		workspace_tabs.current_tab = existing
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
		_add_or_focus_tab(name, box)

	active_surface = name
	_render_current_status()

func _set_right_mode(mode: String, observed := true) -> void:
	if mode == active_right_mode:
		active_right_mode = ""
	else:
		active_right_mode = mode

	if directory_panel:
		directory_panel.visible = active_right_mode == "directory"
	if screens_panel:
		screens_panel.visible = active_right_mode == "screens"
	if commands_panel:
		commands_panel.visible = active_right_mode == "commands"

	for key in right_mode_buttons.keys():
		_button(right_mode_buttons[key], key == active_right_mode)

	_update_awareness_mode(active_right_mode)
	_render_current_status()
	if observed and active_right_mode != "":
		_observe_surface("right:" + active_right_mode)

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
	_connect_observed_button(exp, "Fullscreen Bottom", _toggle_bottom)
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
	_set_status_value("current_root", CliBridge.core_root())
	_set_status_value("dashboard_boot", "rendered")
	_new_chat(false)
	_open_screen("Home", false)
	_log("Phase 4.5 loaded. Operator-triggered state refresh only.")
	_terminal("Path debug\n" + CliBridge.debug_paths())
	# Render mission on seed
	_render_mission()

func _new_chat(observed := true) -> void:
	chat_count += 1
	var name := "Chat %02d" % chat_count
	_open_chat(name, observed)

func _open_chat(name: String, observed := true) -> void:
	active_surface = name
	_render_current_status()
	if observed:
		_observe_chat_surface(name)
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

func _open_screen(name: String, observed := true) -> void:
	active_surface = name
	_render_current_status()
	if observed:
		_observe_surface(name)
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
	elif name == "AI Assist":
		text.text = "[color=#f3edf7]AI Assist surface pending wiring[/color]\n\nnot connected\nno API calls\nmanual context only\nassist_output != authority\nmodel_status=unknown"
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
	current_status["last_command"] = name + " (" + status + ")"
	current_status["next_required_action"] = "Review " + name + " output"
	_render_current_status()
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

func _refresh_state_from_output(output: String, ok := true) -> void:
	var stamp := Time.get_time_string_from_system()
	var short := output.strip_edges()
	if short.length() > 600:
		short = short.substr(0, 600) + "\n..."
	var status := _state_field(short, "status", "observed" if ok else "refresh_failed")
	var latest_diff := _state_field(short, "latest_diff", _status_value("latest_diff"))
	var git_dirty := _state_field(short, "git_dirty", _status_value("git_dirty"))
	var packets_pending := _state_field(short, "packets_pending", _status_value("packets_pending"))
	state_label.text = "Runtime State\n" + \
		"status: " + status + " | latest_diff: " + latest_diff + " | git_dirty: " + git_dirty + " | packets_pending: " + packets_pending + "\n" + \
		"last_refreshed: " + stamp + " | details: Terminal\n" + \
		"boundary: refresh_is_observation_only_not_validation"
	_update_status_from_state_text(short, ok)
	_update_awareness_from_state(short)

func _update_awareness_mode(mode: String) -> void:
	if awareness_label:
		awareness_label.text = _awareness_default()

func _update_awareness_from_state(state_text: String) -> void:
	if awareness_label:
		awareness_label.text = "[color=#f1d58a]Operational Awareness[/color]\n\n" + \
			"[color=#d6b15f]Focus[/color]\n" + \
			"surface: " + active_surface + "\n" + \
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


func _read_mission() -> Dictionary:
	var path: String = CliBridge.dashboard_root().path_join("UI/Mission.yaml")
	if not FileAccess.file_exists(path):
		return {"missing": true}
	var file: FileAccess = FileAccess.open(path, FileAccess.READ)
	if file == null:
		return {"missing": true}
	var text: String = file.get_as_text()
	file.close()
	var lines: PackedStringArray = text.split("\n")
	# Normalize YAML that nests fields under a top-level 'Mission:' mapping.
	# If present, strip the top 'Mission:' line and remove one indent level from following lines.
	var normalized: PackedStringArray = []
	var saw_mission_root: bool = false
	var removed_root: bool = false
	for i in range(lines.size()):
		var raw_line: String = str(lines[i])
		var stripped_line: String = raw_line.strip_edges()
		if not saw_mission_root and stripped_line.ends_with(":") and stripped_line.to_lower().begins_with("mission"):
			saw_mission_root = true
			removed_root = true
			continue
		if saw_mission_root:
			# Remove two-space indent if present, else remove one leading space if present
			if raw_line.begins_with("  "):
				normalized.append(raw_line.substr(2, raw_line.length() - 2))
			elif raw_line.begins_with(" "):
				normalized.append(raw_line.substr(1, raw_line.length() - 1))
			else:
				normalized.append(raw_line)
		else:
			normalized.append(raw_line)
	if removed_root:
		lines = normalized
	var data: Dictionary = {"missing": false, "name": "", "phase": "", "next_action": "", "tasks": [], "goal": "", "decision": "", "observed": "", "recommendation": ""}
	var in_tasks: bool = false
	var current_task: Dictionary = {}
	for l in lines:
		var line: String = str(l).strip_edges()
		if line == "" or line.begins_with("#"):
			continue
		if in_tasks:
			if line.begins_with("-"):
				var item: String = line.substr(1, line.length() - 1).strip_edges()
				current_task = {"text": "", "status": "pending"}
				if item.find(":") != -1:
					var item_key: String = item.substr(0, item.find(":")).strip_edges().to_lower()
					var item_val: String = item.substr(item.find(":") + 1, item.length() - item.find(":") - 1).strip_edges()
					if item_key == "status":
						current_task["status"] = item_val
					elif item_key == "label":
						current_task["text"] = item_val
					else:
						var status: String = "pending"
						var text_val: String = item
						if item.begins_with("[") and item.find("]") >= 2:
							var mark: String = item.substr(1, 1)
							text_val = item.substr(item.find("]") + 1, item.length() - (item.find("]") + 1)).strip_edges()
							if mark == "x" or mark == "X":
								status = "complete"
							elif mark == "~":
								status = "in_progress"
							elif mark == "!":
								status = "blocked"
							else:
								status = "pending"
						current_task["status"] = status
						current_task["text"] = text_val
				else:
					current_task["text"] = item
				data["tasks"].append(current_task)
				continue
			elif line.begins_with("status:") or line.begins_with("label:"):
				if data["tasks"].size() > 0:
					var current: Dictionary = data["tasks"][data["tasks"].size() - 1]
					var detail_key: String = line.substr(0, line.find(":")).strip_edges().to_lower()
					var detail_val: String = line.substr(line.find(":") + 1, line.length() - line.find(":") - 1).strip_edges()
					if detail_key == "status":
						current["status"] = detail_val
					elif detail_key == "label":
						current["text"] = detail_val
				continue
			else:
				in_tasks = false
		var colon: int = line.find(":")
		if colon != -1:
			var key: String = line.substr(0, colon).strip_edges().to_lower()
			var val: String = line.substr(colon + 1, line.length() - colon - 1).strip_edges()
			if key == "name" or key == "mission":
				data["name"] = val
			elif key == "phase":
				data["phase"] = val
			elif key == "current_phase":
				data["phase"] = val
			elif key == "next_action" or key == "next-action" or key == "next action":
				data["next_action"] = val
			elif key == "goal":
				data["goal"] = val
			elif key == "decision":
				data["decision"] = val
			elif key == "observed" or key == "observation":
				data["observed"] = val
			elif key == "recommendation" or key == "recommend":
				data["recommendation"] = val
			elif key == "tasks":
				in_tasks = true

	return data

func _mission_text_from_data(data: Dictionary) -> String:
	if bool(data.get("missing", false)):
		return "[color=#f1d58a]MISSION[/color]\nMission file missing."
	var text: String = "[color=#f1d58a]MISSION[/color]\n\n"
	# Current Goal (preferred) or name fallback
	var goal: String = str(data.get("goal", "")).strip_edges()
	var name: String = str(data.get("name", "")).strip_edges()
	if goal != "":
		text += "Current Goal:\n" + goal + "\n\n"
	elif name != "":
		text += "Current Goal:\n" + name + "\n\n"

	# Current Decision
	var decision: String = str(data.get("decision", "")).strip_edges()
	if decision != "":
		text += "Current Decision:\n" + decision + "\n\n"

	# Observed
	var observed: String = str(data.get("observed", "")).strip_edges()
	if observed != "":
		text += "Observed:\n" + observed + "\n\n"

	# Recommendation
	var recommendation: String = str(data.get("recommendation", "")).strip_edges()
	if recommendation != "":
		text += "Recommendation:\n" + recommendation + "\n\n"

	# Next action / phase
	var phase: String = str(data.get("phase", "")).strip_edges()
	var next_a: String = str(data.get("next_action", "")).strip_edges()
	if next_a != "":
		text += "Next:\n" + next_a + "\n\n"
	elif phase != "":
		text += "Phase:\n" + phase + "\n\n"

	# Tasks fallback
	text += "Top Tasks:\n"
	var tasks: Array = data.get("tasks", [])
	var limit: int = min(tasks.size(), 5)
	if limit == 0:
		text += "(no tasks)\n"
	else:
		for i in range(limit):
			var t: Dictionary = tasks[i]
			var mark: String = "[ ]"
			var status_str: String = str(t.get("status", ""))
			if status_str == "complete":
				mark = "[x]"
			elif status_str == "in_progress":
				mark = "[~]"
			elif status_str == "blocked":
				mark = "[!]"
			text += mark + " " + str(t.get("text", "")) + "\n"
	return text

func _render_mission() -> void:
	if not mission_label:
		return
	mission_label.text = _mission_text_from_data(_read_mission())

func _refresh_state_command() -> void:
	_log("runtime-state requested")
	var r := CliBridge.runtime_state()
	_render_terminal(r)
	var ok := bool(r.get("ok", false))
	_refresh_state_from_output(str(r.get("stdout", "")), ok)
	_record_command("Refresh State", r, "runtime state refreshed" if ok else "runtime state failed")
	if not ok:
		current_status["next_required_action"] = "Inspect Refresh State failure"
		_render_current_status()

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

func _cali_observe_directory() -> void:
	_log("cali-observe-directory requested")
	_terminal("Running cali-observe-directory --max-new-tokens 1 --timeout-seconds 120...")
	var r := CliBridge.cali_observe_directory()
	_render_terminal(r)
	_record_command("Cali Observe Directory", r, "Cali directory observation attempted")

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
