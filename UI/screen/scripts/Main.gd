extends Control

const Palette = preload("res://screen/scripts/widgets/Palette.gd")
const CliBridge = preload("res://screen/scripts/runtime/CliBridge.gd")
const OperatorObservation = preload("res://screen/scripts/runtime/OperatorObservation.gd")
const MissionReader = preload("res://screen/scripts/runtime/MissionReader.gd")
const CommandRouter = preload("res://screen/scripts/runtime/CommandRouter.gd")
const SurfaceRenderer = preload("res://screen/scripts/runtime/SurfaceRenderer.gd")
const DashboardLayout = preload("res://screen/scripts/layout/DashboardLayout.gd")

signal request_assist_wake

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
var terminal_input: LineEdit
var approve_button: Button
var last_proposal_intent: String = ""

var left_panel_collapsed := {
	"mission": false,
	"status": true,
	"observation": true,
	"awareness": true,
	"history": true,
	"boundaries": true
}

var left_panel_buttons := {}

var current_status := {
	"current_root": "Core",
	"dashboard_boot": "booted_not_refreshed",
	"latest_diff": "unknown",
	"packets_pending": "unknown",
	"git_dirty": "unknown",
	"last_command": "none",
	"next_required_action": "Refresh State"
}

var operator_observation := OperatorObservation.new()
var surface_renderer := SurfaceRenderer.new()
var command_router: CommandRouter
var dashboard_layout: DashboardLayout


func _ready() -> void:
	command_router = CommandRouter.new(CliBridge)
	dashboard_layout = DashboardLayout.new(self)

	_background()
	_build()
	_seed()

	request_assist_wake.connect(_on_request_assist_wake)


func _on_request_assist_wake() -> void:
	_open_screen("AI Assist")


func _background() -> void:
	var bg := ColorRect.new()
	bg.color = Palette.PLUM_BLACK
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)


func _build() -> void:
	var refs := dashboard_layout.build(self)

	state_label = refs.get("state_label")
	mission_label = refs.get("mission_label")
	current_status_label = refs.get("current_status_label")
	operator_observation_label = refs.get("operator_observation_label")
	awareness_label = refs.get("awareness_label")
	history_label = refs.get("history_label")
	workspace_tabs = refs.get("workspace_tabs")
	right_content = refs.get("right_content")
	directory_panel = refs.get("directory_panel")
	screens_panel = refs.get("screens_panel")
	commands_panel = refs.get("commands_panel")
	bottom_shell = refs.get("bottom_shell")
	bottom_tabs = refs.get("bottom_tabs")
	approve_button = refs.get("approve_button")
	terminal_input = refs.get("terminal_input")

	surface_renderer.bind_bottom_tabs(bottom_tabs)
	surface_renderer.bind_history_label(history_label)

	_set_right_mode("", false)


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
	operator_observation.observe_button(label)
	_render_operator_observation()


func _observe_surface(surface: String) -> void:
	operator_observation.observe_surface(surface)
	_render_operator_observation()


func _observe_chat_surface(name: String) -> void:
	operator_observation.observe_chat_surface(name)
	_render_operator_observation()


func _observe_panel_toggle(key: String, opened: bool) -> void:
	operator_observation.observe_panel_toggle(_left_section_title(key), opened)
	_render_operator_observation()


func _render_operator_observation() -> void:
	if operator_observation_label:
		operator_observation_label.text = _operator_observation_text()


func _operator_observation_text() -> String:
	return operator_observation.text(_panel_state_text())


func _panel_state_text() -> String:
	var parts: Array[String] = ["current_status=open"]

	for key in ["observation", "awareness", "history", "boundaries"]:
		var state := "closed" if bool(left_panel_collapsed.get(key, true)) else "open"
		parts.append(str(key) + "=" + state)

	return _join_strings(parts, ", ")


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
			var label = tab_node.get_child(1)

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
		dashboard_layout._button(right_mode_buttons[key], key == active_right_mode)

	_update_awareness_mode(active_right_mode)
	_render_current_status()

	if observed and active_right_mode != "":
		_observe_surface("right:" + active_right_mode)


func _seed() -> void:
	_set_status_value("current_root", command_router.core_root())
	_set_status_value("dashboard_boot", "rendered")
	_new_chat(false)
	_open_screen("Home", false)
	_log("Phase 4.5 loaded. Operator-triggered state refresh only.")
	_terminal("Path debug\n" + command_router.debug_paths())
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
	dashboard_layout._panel(card, Palette.PLUM_CARD, Palette.GOLD_DARK, 1, 14)
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
		text.text = "[color=#f3edf7]AI Operational Consultant[/color]\n\n[color=#b8aebe]status: operational_consultant[/color]\n\nAuthority: candidate_only\nMutation: prohibited\n\nUse the 'Gemini Analyze Core' command to generate an architectural gap analysis."
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


func _log(text: String) -> void:
	surface_renderer.log_line(text)


func _terminal(text: String) -> void:
	surface_renderer.terminal(text)


func _diff(text: String) -> void:
	surface_renderer.diff(text)


func _packets(text: String) -> void:
	surface_renderer.packets(text)


func _render_terminal(result: Dictionary) -> void:
	surface_renderer.render_terminal(result)


func _render_diff(result: Dictionary) -> void:
	surface_renderer.render_diff(result)


func _render_packets(result: Dictionary) -> void:
	surface_renderer.render_packets(result)


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

	surface_renderer.render_history(command_history)


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

	if status == "active" or status == "error":
		request_assist_wake.emit()

	_update_awareness_from_state(short)


func _update_awareness_mode(_mode: String) -> void:
	if awareness_label:
		awareness_label.text = _awareness_default()


func _update_awareness_from_state(_state_text: String) -> void:
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
	return MissionReader.read_mission(
		command_router.dashboard_root().path_join("UI/Mission.yaml")
	)


func _mission_text_from_data(data: Dictionary) -> String:
	return MissionReader.mission_text_from_data(data)


func _render_mission() -> void:
	if not mission_label:
		return

	mission_label.text = _mission_text_from_data(_read_mission())


func _refresh_state_command() -> void:
	_log("runtime-state requested")
	var r := command_router.runtime_state()
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
	var r := command_router.test_all()
	_render_terminal(r)
	_record_command("Test", r, "structured validation report generated")


func _scan_core() -> void:
	_log("scan-core requested")
	_terminal("Running scan-repo against Core...")
	var r := command_router.scan_core()
	_render_terminal(r)
	_record_command("Scan Core", r, "Core scan executed")


func _git_status() -> void:
	_log("git-status requested")
	_terminal("Running git-status against Core...")
	var r := command_router.git_status_core()
	_render_terminal(r)
	_record_command("Git Status", r, "Git status executed")


func _gemini_analyze_core() -> void:
	_log("gemini-analyze requested")
	_open_screen("AI Assist")
	_terminal("Requesting Gemini analysis: Gap Analysis (Mission vs Directory)...")

	var mission_data := _read_mission()
	var purpose := "Architectural Gap Analysis"
	var context_str := "Mission Goal: " + str(mission_data.get("goal", "unknown")) + "\n"
	context_str += "Current Status: " + _current_status_text()

	var r := command_router.gemini_analyze(purpose, context_str)
	_render_terminal(r)

	if r.get("ok", false):
		var ai_screen := -1

		for i in workspace_tabs.get_tab_count():
			if workspace_tabs.get_tab_title(i) == "AI Assist":
				ai_screen = i
				break

		if ai_screen != -1:
			var tab_node := workspace_tabs.get_child(ai_screen)
			var card = tab_node.get_child(1)
			var label = card.get_child(0)

			if label is RichTextLabel:
				label.text = "[color=#f1d58a]AI ANALYSIS CANDIDATE[/color]\n\n" + str(r.get("stdout", ""))

	_record_command("Gemini Analyze", r, "Architectural analysis generated")


func _cali_observe_directory() -> void:
	_log("cali-observe-directory requested")
	_terminal("Running cali-observe-directory --max-new-tokens 1 --timeout-seconds 120...")
	var r := command_router.cali_observe_directory()
	_render_terminal(r)
	_record_command("Cali Observe Directory", r, "Cali directory observation attempted")


func _propose_diff() -> void:
	_log("propose-directory-diff requested")
	_diff("Running propose-directory-diff against Core...")
	var r := command_router.propose_directory_diff_core()
	_render_diff(r)
	_record_command("Propose Directory Diff", r, "latest.diff proposal attempted")


func _view_latest_diff() -> void:
	_log("view-latest-diff requested")
	_diff("Viewing latest.diff...")
	var r := command_router.view_latest_diff()
	_render_diff(r)
	_record_command("View Latest Diff", r, "latest.diff display attempted")


func _review_latest_diff() -> void:
	_log("grant-review-latest-diff requested")
	_diff("Reviewing latest.diff...")
	var r := command_router.grant_review_latest_diff()
	_render_diff(r)
	_record_command("Review Latest Diff", r, "lexical review executed")


func _clear_latest_diff() -> void:
	_log("clear-latest-diff requested")
	_diff("Clearing latest.diff with archive tombstone...")
	var r := command_router.clear_latest_diff()
	_render_diff(r)
	_record_command("Clear Latest Diff", r, "latest.diff clear/archive attempted")


func _list_packets() -> void:
	_log("list-packets requested")
	_packets("Listing packet registry...")
	var r := command_router.list_packets()
	_render_packets(r)
	_record_command("List Packets", r, "packet listing executed")


func _create_packet_stub() -> void:
	_log("create-packet requested")
	_packets("Creating packet stub...")
	var r := command_router.create_packet_stub()
	_render_packets(r)
	_record_command("Create Packet Stub", r, "incoming packet stub attempted")


func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_ENTER or event.keycode == KEY_KP_ENTER:
			if terminal_input and terminal_input.has_focus() and terminal_input.text != "":
				_on_terminal_input_submitted(terminal_input.text)
				get_viewport().set_input_as_handled()


func _on_terminal_input_submitted(text: String) -> void:
	if text.strip_edges() == "":
		return

	terminal_input.clear()
	approve_button.visible = false

	_log("intent-bridge: " + text)
	_terminal("Proposing task packet for intent: " + text)

	var r := command_router.propose_task_packet(text)

	if r.get("ok", false) and r.has("stdout"):
		var out_raw = r.get("stdout", "")
		var start = out_raw.find("{")
		var end = out_raw.rfind("}")

		if start != -1 and end != -1:
			var json_str = out_raw.substr(start, end - start + 1)
			var json = JSON.parse_string(json_str)

			if json and json.has("proposal"):
				_render_task_proposal(json.get("proposal"), text)
				return

	_render_terminal(r)
	_record_command("Propose Task", r, "Intent processed")


func _render_task_proposal(proposal: Dictionary, intent: String) -> void:
	last_proposal_intent = intent
	command_router.last_proposal_intent = intent
	approve_button.visible = true
	surface_renderer.show_task_proposal(proposal)


func _on_approve_task_pressed() -> void:
	approve_button.visible = false
	_log("Approving task: " + last_proposal_intent)
	_terminal("Generating diff proposal for: " + last_proposal_intent)

	var r := command_router.approve_task("Dashboard/")
	_render_diff(r)
	_record_command("Approve Task", r, "Diff proposal generated")


func _toggle_bottom() -> void:
	bottom_expanded = !bottom_expanded

	if bottom_shell:
		bottom_shell.custom_minimum_size = Vector2(0, 710 if bottom_expanded else 245)
