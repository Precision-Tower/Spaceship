extends Control
const Palette = preload("res://widgets/Palette.gd")
const CliBridge = preload("res://runtime/CliBridge.gd")
const MissionService = preload("res://runtime/MissionService.gd")
const ObservationTracker = preload("res://runtime/ObservationTracker.gd")
const ResultRenderer = preload("res://runtime/ResultRenderer.gd")
const CommandActions = preload("res://runtime/CommandActions.gd")
const StatusService = preload("res://runtime/StatusService.gd")
const OperatorAuditController = preload("res://audit/OperatorAuditController.gd")
const RightRail = preload("res://layout/RightRail.gd")
const BottomDock = preload("res://layout/BottomDock.gd")
const WorkspaceSurface = preload("res://layout/WorkspaceSurface.gd")
const LeftPanel = preload("res://layout/LeftPanel.gd")
const TopBars = preload("res://layout/TopBars.gd")
const DashboardConfig = preload("res://resources/DashboardConfig.gd")
const QPSConfig = preload("res://runtime/QPSConfig.gd")

signal request_assist_wake

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

var main_v_split: VSplitContainer
var center_vbox: VBoxContainer
var left_dock_shell: VBoxContainer
var right_dock_shell: VBoxContainer
var left_reveal_button: Button
var right_reveal_button: Button
var left_dock_open := true
var right_dock_open := true
var terminal_collapsed := false
var terminal_density_modes := ["comfortable", "compact", "dense"]

var config: DashboardConfig
var left_panel_control: Control
var right_rail_control: Control
var directory_panel: Control
var screens_panel: Control
var commands_panel: Control
var top_bar_control: Control
var runtime_state_bar_control: Control
var workspace_control: Control

var terminal_density_button: Button
var terminal_toggle_button: Button

var ai_intent_input: LineEdit
var ai_output: RichTextLabel

var awareness_label: RichTextLabel
var history_label: RichTextLabel
var current_status_label: RichTextLabel
var mission_label: RichTextLabel
var operator_observation_label: RichTextLabel
var state_label: Label
var workspace_tabs: TabContainer
var workspace_surface
var bottom_tabs: TabContainer
var bottom_shell: PanelContainer
var bottom_dock

var right_mode_buttons := {}
var right_content: VBoxContainer
var right_rail

var chat_count := 0
var bottom_expanded := false
var active_right_mode := "controls"

var active_left_mode := "missions"
var left_mode_buttons := {}
var missions_panel_control: Control
var docs_panel_control: Control
var docs_panel_widget

var active_right_sub_mode := ""
var controls_panel_control: Control
var library_panel_control: Control
var library_panel_widget

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
var left_panel
var capability_panel
var audit_controller
var top_bars
var operator_click_counts := {}
var operator_panel_toggles := {}
var operator_surface_visits := {}
var operator_recent_routes: Array[String] = []
var operator_last_event := "none"
var observation_tracker
var current_status := {
	"current_root": "Core",
	"dashboard_boot": "booted_not_refreshed",
	"latest_diff": "unknown",
	"packets_pending": "unknown",
	"git_dirty": "unknown",
	"last_command": "none",
	"next_required_action": "Refresh State"
}

func _toggle_terminal_dock() -> void:
	terminal_collapsed = !terminal_collapsed

	if bottom_shell:
		if terminal_collapsed:
			bottom_shell.custom_minimum_size = Vector2(0, 42)
			if terminal_toggle_button:
				terminal_toggle_button.text = "▲"
		else:
			bottom_shell.custom_minimum_size = Vector2(0, config.bottom_height_expanded)
			if terminal_toggle_button:
				terminal_toggle_button.text = "▼"

func _cycle_terminal_density() -> void:
	var current := config.terminal_density
	var index := terminal_density_modes.find(current)
	if index == -1:
		index = 1

	index = (index + 1) % terminal_density_modes.size()
	config.terminal_density = terminal_density_modes[index]

	if bottom_dock:
		bottom_dock.apply_terminal_density(config.terminal_density)

	if terminal_density_button:
		terminal_density_button.text = config.terminal_density.capitalize()

func _ai_propose_task() -> void:
	var intent := ai_intent_input.text.strip_edges()
	if intent == "":
		_terminal("AI_ASSIST\nstatus: blocked\nreason: empty intent")
		return

	var result := CliBridge.propose_task_packet(intent)
	_terminal("AI_ASSIST_PROPOSE_TASK\n" + str(result))

	if ai_output:
		ai_output.text = "[color=#f1d58a]AI Assist Proposal[/color]\n\n" + str(result)

func _test_state_update() -> void:
	var result := CliBridge.update_state(
		"interaction",
		"Dashboard local state update test",
		"manual_dashboard_test",
		"dashboard"
	)
	_terminal("TEST_STATE_UPDATE\n" + str(result))

func _ready() -> void:
	print("[OperatorShell] ready")
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
	var screen_size := DisplayServer.screen_get_size()
	DisplayServer.window_set_size(screen_size)
	DisplayServer.window_set_position(Vector2i.ZERO)
	config = load("res://resources/dashboard_config.tres")
	var qps_config := QPSConfig.new(CliBridge.dashboard_root())
	qps_config.apply(config)
	_background()
	_build()
	audit_controller = OperatorAuditController.new()
	add_child(audit_controller)
	audit_controller.setup(capability_panel)
	_seed()
	request_assist_wake.connect(_on_request_assist_wake)

func _on_request_assist_wake() -> void:
	_open_screen("AI Assist")

func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_PREDELETE:
		_shutdown_terminals()

func _background() -> void:
	var bg := ColorRect.new()
	bg.color = Palette.PLUM_BLACK
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

func _build() -> void:
	var root := HBoxContainer.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_theme_constant_override("separation", 0)
	add_child(root)

	left_dock_shell = _build_left_dock_shell()
	root.add_child(left_dock_shell)

	center_vbox = VBoxContainer.new()
	center_vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	center_vbox.size_flags_vertical = Control.SIZE_EXPAND_FILL
	center_vbox.add_theme_constant_override("separation", 8)
	root.add_child(center_vbox)

	center_vbox.add_child(_top_bar())
	center_vbox.add_child(_runtime_state_bar())

	main_v_split = VSplitContainer.new()
	main_v_split.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	main_v_split.size_flags_vertical = Control.SIZE_EXPAND_FILL
	center_vbox.add_child(main_v_split)

	var workspace_host := HBoxContainer.new()
	workspace_host.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	workspace_host.size_flags_vertical = Control.SIZE_EXPAND_FILL
	workspace_host.add_theme_constant_override("separation", 0)
	workspace_host.add_child(_workspace())
	main_v_split.add_child(workspace_host)

	main_v_split.add_child(_bottom())

	right_dock_shell = _build_right_dock_shell()
	root.add_child(right_dock_shell)


func _build_left_dock_shell() -> VBoxContainer:
	var shell := VBoxContainer.new()
	shell.custom_minimum_size = Vector2(320, 0)
	shell.size_flags_vertical = Control.SIZE_EXPAND_FILL
	shell.add_theme_constant_override("separation", 4)

	var collapse := Button.new()
	collapse.text = "«"
	collapse.tooltip_text = "Collapse left dock"
	collapse.custom_minimum_size = Vector2(32, 28)
	collapse.pressed.connect(_toggle_left_dock)
	shell.add_child(collapse)

	left_panel_control = _left_awareness()
	left_panel_control.size_flags_vertical = Control.SIZE_EXPAND_FILL
	shell.add_child(left_panel_control)

	left_reveal_button = Button.new()
	left_reveal_button.text = "›"
	left_reveal_button.tooltip_text = "Open left dock"
	left_reveal_button.custom_minimum_size = Vector2(28, 0)
	left_reveal_button.size_flags_vertical = Control.SIZE_EXPAND_FILL
	left_reveal_button.visible = false
	left_reveal_button.pressed.connect(_toggle_left_dock)
	shell.add_child(left_reveal_button)

	return shell


func _build_right_dock_shell() -> VBoxContainer:
	var shell := VBoxContainer.new()
	shell.custom_minimum_size = Vector2(320, 0)
	shell.size_flags_vertical = Control.SIZE_EXPAND_FILL
	shell.add_theme_constant_override("separation", 4)

	var collapse := Button.new()
	collapse.text = "»"
	collapse.tooltip_text = "Collapse right dock"
	collapse.custom_minimum_size = Vector2(32, 28)
	collapse.pressed.connect(_toggle_right_dock)
	shell.add_child(collapse)

	right_rail_control = _right_control_rail()
	right_rail_control.size_flags_vertical = Control.SIZE_EXPAND_FILL
	shell.add_child(right_rail_control)

	right_reveal_button = Button.new()
	right_reveal_button.text = "‹"
	right_reveal_button.tooltip_text = "Open right dock"
	right_reveal_button.custom_minimum_size = Vector2(28, 0)
	right_reveal_button.size_flags_vertical = Control.SIZE_EXPAND_FILL
	right_reveal_button.visible = false
	right_reveal_button.pressed.connect(_toggle_right_dock)
	shell.add_child(right_reveal_button)

	return shell


func _toggle_left_dock() -> void:
	left_dock_open = not left_dock_open

	if left_panel_control:
		left_panel_control.visible = left_dock_open

	if left_reveal_button:
		left_reveal_button.visible = not left_dock_open

	if left_dock_shell:
		left_dock_shell.custom_minimum_size = Vector2(
			320 if left_dock_open else 28,
			0
		)


func _toggle_right_dock() -> void:
	right_dock_open = not right_dock_open

	if right_rail_control:
		right_rail_control.visible = right_dock_open

	if right_reveal_button:
		right_reveal_button.visible = not right_dock_open

	if right_dock_shell:
		right_dock_shell.custom_minimum_size = Vector2(
			320 if right_dock_open else 28,
			0
		)


func _top_bar() -> Control:
	if top_bars == null:
		top_bars = TopBars.new(self)
	top_bar_control = top_bars.top_bar()
	return top_bar_control

func _runtime_state_bar() -> Control:
	if top_bars == null:
		top_bars = TopBars.new(self)
	runtime_state_bar_control = top_bars.runtime_state_bar()
	return runtime_state_bar_control

func _left_awareness() -> Control:
	left_panel = LeftPanel.new(self)
	left_panel_control = left_panel.build()
	return left_panel_control

func _left_text(height: int) -> RichTextLabel:
	return left_panel.left_text(height)

func _collapsible_left_section(key: String, title: String, content: Control) -> VBoxContainer:
	return left_panel.collapsible_section(key, title, content)

func _collapse_label(title: String, collapsed: bool) -> String:
	return left_panel.collapse_label(title, collapsed)

func _left_section_title(key: String) -> String:
	if left_panel:
		return left_panel.section_title(key)
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
	left_panel.toggle_section(key, content)

func _current_status_text() -> String:
	return StatusService.status_text(current_status, active_surface, active_right_mode)

func _status_value(key: String) -> String:
	return StatusService.value(current_status, key)

func _set_status_value(key: String, value: String) -> void:
	current_status[key] = value
	_render_current_status()

func _render_current_status() -> void:
	if current_status_label:
		current_status_label.text = _current_status_text()

func _state_field(state_text: String, key: String, fallback: String) -> String:
	return StatusService.field(state_text, key, fallback)

func _update_status_from_state_text(state_text: String, ok := true) -> void:
	StatusService.update_from_state_text(current_status, state_text, ok)
	_render_current_status()

func _obs() -> ObservationTracker:
	if observation_tracker == null:
		observation_tracker = ObservationTracker.new(OBSERVATION_SURFACES)
	return observation_tracker

func _connect_observed_button(button: Button, label: String, callable: Callable) -> void:
	button.pressed.connect(func(): _observed_call(label, callable))

func _observed_call(label: String, callable: Callable) -> void:
	_observe_button(label)
	callable.call()

func _observe_button(label: String) -> void:
	_obs().observe_button(label)
	_render_operator_observation()

func _observe_surface(surface: String) -> void:
	active_surface = surface
	_obs().observe_surface(surface)
	_render_operator_observation()

func _observe_chat_surface(name: String) -> void:
	active_surface = "Chat"
	_obs().observe_chat_surface(name)
	_render_operator_observation()

func _observe_panel_toggle(key: String, opened: bool) -> void:
	_obs().observe_panel_toggle(key, opened, _left_section_title(key))
	_render_operator_observation()

func _observe_event(kind: String, detail: String) -> void:
	_obs().observe_event(kind, detail)
	_render_operator_observation()

func _increment_count(counts: Dictionary, key: String) -> void:
	counts[key] = int(counts.get(key, 0)) + 1

func _push_route(route: String) -> void:
	_obs()._push_route(route)

func _render_operator_observation() -> void:
	if operator_observation_label == null:
		return
	operator_observation_label.text = _operator_observation_text()

func _operator_observation_text() -> String:
	return _obs().observation_text(left_panel_collapsed, active_surface)

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
	right_rail = RightRail.new(self)
	right_rail_control = right_rail.build()
	return right_rail_control

func _workspace() -> Control:
	workspace_surface = WorkspaceSurface.new(self)
	workspace_control = workspace_surface.build()
	workspace_tabs = workspace_surface.workspace_tabs
	return workspace_control

func _new_chat(observed := true) -> void:
	workspace_surface.new_chat(observed)

func _open_chat(name: String, observed := true) -> void:
	workspace_surface.open_chat(name, observed)

func _open_screen(name: String, observed := true) -> void:
	workspace_surface.open_screen(name, observed)

func _add_or_focus_tab(name: String, node: Control) -> void:
	workspace_surface.add_or_focus_tab(name, node)

func _apply_config() -> void:
	if config == null:
		push_warning("Dashboard config missing; using built layout defaults.")
		return

	if bottom_dock:
		bottom_dock.apply_terminal_density(config.terminal_density)

	if top_bar_control:
		top_bar_control.visible = config.show_top_bar

	if runtime_state_bar_control:
		runtime_state_bar_control.visible = config.show_runtime_state_bar



	if workspace_control:
		workspace_control.visible = config.show_workspace

	if bottom_shell:
		bottom_expanded = config.default_bottom_expanded
		bottom_shell.custom_minimum_size = Vector2(
			0,
			config.bottom_height_expanded if bottom_expanded else config.bottom_height_collapsed
		)

		if bottom_dock:
			bottom_dock.apply_terminal_density(config.terminal_density)

func _bottom() -> Control:
	bottom_dock = BottomDock.new(self)
	bottom_shell = bottom_dock.build()
	bottom_tabs = bottom_dock.bottom_tabs
	return bottom_shell

func _seed() -> void:
	_apply_config()
	_set_status_value("current_root", CliBridge.core_root())
	_set_status_value("dashboard_boot", "rendered")
	_new_chat(false)
	_open_screen("Home", false)
	_log("Phase 4.5 loaded. Operator-triggered state refresh only.")
	_terminal("Path debug\n" + CliBridge.debug_paths())
	_render_mission()

func _add_bottom(name: String, content: String) -> void:
	bottom_dock.add_bottom(name, content)

func _bottom_text(name: String) -> RichTextLabel:
	return bottom_dock.bottom_text(name)

func _set_bottom(name: String) -> void:
	bottom_dock.set_bottom(name)

func _log(text: String) -> void:
	bottom_dock.log_line(text)

func _terminal(text: String) -> void:
	bottom_dock.terminal(text)

func _diff(text: String) -> void:
	bottom_dock.diff(text)

func _packets(text: String) -> void:
	bottom_dock.packets(text)

func _record_command(name: String, result: Dictionary, summary: String) -> void:
	bottom_dock.record_command(name, result, summary)

func _render_history() -> void:
	bottom_dock.render_history()

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


func _render_mission() -> void:
	if mission_label == null:
		return
	var path: String = CliBridge.dashboard_root().path_join("UI/Mission.yaml")
	mission_label.text = MissionService.render(path)

func _run_command_packet(packet: Dictionary) -> void:
	_log(str(packet.get("log", "")))

	var preamble := str(packet.get("preamble", ""))
	var surface := str(packet.get("surface", "terminal"))
	if preamble != "":
		match surface:
			"diff":
				_diff(preamble)
			"packets":
				_packets(preamble)
			_:
				_terminal(preamble)

	var r: Dictionary = packet.get("result", {})
	match surface:
		"diff":
			_render_diff(r)
		"packets":
			_render_packets(r)
		_:
			_render_terminal(r)

	var ok := bool(r.get("ok", false))
	if bool(packet.get("refresh_state_from_output", false)):
		_refresh_state_from_output(str(r.get("stdout", "")), ok)
		if not ok:
			current_status["next_required_action"] = "Inspect Refresh State failure"
			_render_current_status()

	var summary := str(packet.get("summary_ok", "command executed")) if ok else str(packet.get("summary_fail", "command failed"))
	_record_command(str(packet.get("record_name", "Command")), r, summary)

func _refresh_state_command() -> void:
	_run_command_packet(CommandActions.refresh_state())
func _test_all() -> void:
	_run_command_packet(CommandActions.test_all())
func _scan_core() -> void:
	_run_command_packet(CommandActions.scan_core())
func _git_status() -> void:
	_run_command_packet(CommandActions.git_status())
func _gemini_analyze_core() -> void:
	_log("gemini-analyze requested")
	_open_screen("AI Assist")
	_terminal("Requesting Gemini analysis: Gap Analysis (Mission vs Directory)...")
	
	var mission_data := MissionService.read_mission(CliBridge.dashboard_root().path_join("UI/Mission.yaml"))
	var purpose := "Architectural Gap Analysis"
	var context_str := "Mission Goal: " + str(mission_data.get("goal", "unknown")) + "\n"
	context_str += "Current Status: " + _current_status_text()
	
	var r := CliBridge.gemini_analyze(purpose, context_str)
	_render_terminal(r)
	
	if r.get("ok", false):
		var ai_screen := -1
		for i in workspace_tabs.get_tab_count():
			if workspace_tabs.get_tab_title(i) == "AI Assist":
				ai_screen = i
				break
		if ai_screen != -1:
			var tab_node := workspace_tabs.get_child(ai_screen)
			var card = tab_node.get_child(1) # PanelContainer
			var label = card.get_child(0) # RichTextLabel
			if label is RichTextLabel:
				label.text = "[color=#f1d58a]AI ANALYSIS CANDIDATE[/color]\n\n" + r.get("stdout", "")
	
	_record_command("Gemini Analyze", r, "Architectural analysis generated")

func _cali_observe_directory() -> void:
	_run_command_packet(CommandActions.cali_observe_directory())
func _propose_diff() -> void:
	_run_command_packet(CommandActions.propose_diff())
func _view_latest_diff() -> void:
	_run_command_packet(CommandActions.view_latest_diff())
func _review_latest_diff() -> void:
	_run_command_packet(CommandActions.review_latest_diff())
func _clear_latest_diff() -> void:
	_run_command_packet(CommandActions.clear_latest_diff())
func _list_packets() -> void:
	_run_command_packet(CommandActions.list_packets())
func _create_packet_stub() -> void:
	_run_command_packet(CommandActions.create_packet_stub())
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

	if text.begins_with("ps "):
		var command_text := text.substr(3).strip_edges()
		_log("ps: " + command_text)
		_terminal("[color=#d6b15f][PS][/color] " + command_text)
		var r := CliBridge.run_powershell(command_text)
		_render_terminal(r)
		_record_command("PowerShell", r, "PowerShell command executed")
		return

	_log("intent-bridge: " + text)
	_terminal("Proposing task packet for intent: " + text)
	
	var r := CliBridge.propose_task_packet(text)
	if r.get("ok", false) and r.has("stdout"):
		var out_raw = r.get("stdout", "")
		# Attempt to find JSON in stdout
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

func _format(result: Dictionary) -> String:
	return ResultRenderer.format_result(result)
func _render_terminal(result: Dictionary) -> void:
	_terminal(_format(result))
func _render_diff(result: Dictionary) -> void:
	_diff(_format(result))
func _render_packets(result: Dictionary) -> void:
	_packets(_format(result))
func _render_task_proposal(proposal: Dictionary, intent: String) -> void:
	_diff(ResultRenderer.task_proposal(proposal, intent))
func _on_approve_task_pressed() -> void:
	approve_button.visible = false
	_log("Approving task: " + last_proposal_intent)
	_terminal("Generating diff proposal for: " + last_proposal_intent)
	var r := CliBridge.propose_diff(last_proposal_intent, "Dashboard/")
	_render_diff(r)
	_record_command("Approve Task", r, "Diff proposal generated")

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

func _unhandled_input(event: InputEvent) -> void:
	if audit_controller != null and audit_controller.handle_input(event):
		get_viewport().set_input_as_handled()
		return

	if event.is_action_pressed("ui_cancel"):
		_operatorshell_quit_requested()

	if event is InputEventKey and event.pressed and event.ctrl_pressed and event.keycode == KEY_Q:
		_operatorshell_quit_requested()


func _shutdown_terminals() -> void:
	if bottom_dock and bottom_dock.has_method("shutdown_terminals"):
		bottom_dock.shutdown_terminals()

func _operatorshell_quit_requested() -> void:
	print("[OperatorShell] quit requested")
	_shutdown_terminals()
	get_tree().quit()



func set_left_mode(mode: String, observed := true) -> void:
	active_left_mode = mode
	if missions_panel_control:
		missions_panel_control.visible = (active_left_mode == "missions")
	if docs_panel_control:
		docs_panel_control.visible = (active_left_mode == "docs")

	for key in left_mode_buttons.keys():
		if left_mode_buttons.has(key):
			_button(left_mode_buttons[key], key == active_left_mode)

	if not left_dock_open:
		_toggle_left_dock()

	_render_current_status()
	if observed:
		_observe_surface("left:" + active_left_mode)

func set_right_mode(mode: String, observed := true) -> void:
	active_right_mode = mode
	if controls_panel_control:
		controls_panel_control.visible = (active_right_mode == "controls")
	if library_panel_control:
		library_panel_control.visible = (active_right_mode == "library")

	for key in right_mode_buttons.keys():
		if right_mode_buttons.has(key):
			_button(right_mode_buttons[key], key == active_right_mode)

	if not right_dock_open:
		_toggle_right_dock()

	_render_current_status()
	if observed:
		_observe_surface("right:" + active_right_mode)

func open_document_in_docs(file_path: String) -> void:
	if docs_panel_widget != null:
		docs_panel_widget.open_document(file_path)
	set_left_mode("docs")
	if not left_dock_open:
		_toggle_left_dock()
