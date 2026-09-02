extends RefCounted
class_name OperatorShellLeftPanel

const Palette = preload("res://widgets/Palette.gd")
const CliBridge = preload("res://runtime/CliBridge.gd")
const MissionService = preload("res://runtime/MissionService.gd")
const CapabilityPanel = preload("res://audit/CapabilityPanel.gd")
const DocsPanel = preload("res://widgets/DocsPanel.gd")

var host
var missions_panel: Control
var docs_panel: Control

func _init(owner) -> void:
	host = owner

func build() -> Control:
	var shell := PanelContainer.new()
	shell.custom_minimum_size = Vector2(320, 0)
	host._panel(shell, Palette.PLUM_DEEP, Palette.GOLD_DARK, 1, 16)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	shell.add_child(box)

	var rail_bar := HBoxContainer.new()
	rail_bar.add_theme_constant_override("separation", 6)

	var missions_btn := Button.new()
	missions_btn.text = "Missions"
	host._button(missions_btn, host.active_left_mode == "missions")
	missions_btn.pressed.connect(func(): host.set_left_mode("missions"))
	rail_bar.add_child(missions_btn)
	host.left_mode_buttons["missions"] = missions_btn

	var docs_btn := Button.new()
	docs_btn.text = "Docs"
	host._button(docs_btn, host.active_left_mode == "docs")
	docs_btn.pressed.connect(func(): host.set_left_mode("docs"))
	rail_bar.add_child(docs_btn)
	host.left_mode_buttons["docs"] = docs_btn

	box.add_child(rail_bar)

	missions_panel = VBoxContainer.new()
	missions_panel.size_flags_vertical = Control.SIZE_EXPAND_FILL
	missions_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	host.capability_panel = CapabilityPanel.new()
	missions_panel.add_child(host.capability_panel)

	var capability_sep := HSeparator.new()
	missions_panel.add_child(capability_sep)
	host.mission_label = left_text(180)
	host.mission_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	host.mission_label.text = MissionService.render(CliBridge.dashboard_root().path_join("UI/Mission.yaml"))

	var mission_scroll := ScrollContainer.new()
	mission_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	mission_scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var mission_section := collapsible_section("mission", "Mission", host.mission_label)
	mission_section.size_flags_vertical = Control.SIZE_EXPAND_FILL
	mission_scroll.add_child(mission_section)
	missions_panel.add_child(mission_scroll)

	var status_sep := HSeparator.new()
	missions_panel.add_child(status_sep)

	var bottom_stack := VBoxContainer.new()
	bottom_stack.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bottom_stack.size_flags_vertical = Control.SIZE_SHRINK_CENTER

	host.current_status_label = left_text(120)
	host.current_status_label.text = host._current_status_text()
	bottom_stack.add_child(collapsible_section("status", "Current Status", host.current_status_label))

	host.operator_observation_label = left_text(210)
	host.operator_observation_label.text = host._operator_observation_text()
	bottom_stack.add_child(collapsible_section("observation", "Operator Observation", host.operator_observation_label))

	host.awareness_label = RichTextLabel.new()
	host.awareness_label.bbcode_enabled = true
	host.awareness_label.selection_enabled = true
	host.awareness_label.custom_minimum_size = Vector2(0, 285)
	host.awareness_label.text = host._awareness_default()
	bottom_stack.add_child(collapsible_section("awareness", "Operational Awareness", host.awareness_label))

	host.history_label = RichTextLabel.new()
	host.history_label.bbcode_enabled = true
	host.history_label.selection_enabled = true
	host.history_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	host.history_label.text = "[color=#f1d58a]Command History[/color]\n\n(no commands yet)\n\n[color=#b8aebe]history != evidence[/color]"
	bottom_stack.add_child(collapsible_section("history", "Command History", host.history_label))

	var boundaries := left_text(185)
	boundaries.text = host._boundaries_default()
	bottom_stack.add_child(collapsible_section("boundaries", "Runtime Boundaries", boundaries))

	missions_panel.add_child(bottom_stack)
	box.add_child(missions_panel)
	host.missions_panel_control = missions_panel

	host.docs_panel_widget = DocsPanel.new(host)
	docs_panel = host.docs_panel_widget.build()
	docs_panel.size_flags_vertical = Control.SIZE_EXPAND_FILL
	docs_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box.add_child(docs_panel)
	host.docs_panel_control = docs_panel

	host.set_left_mode(host.active_left_mode, false)

	return shell

func left_text(height: int) -> RichTextLabel:
	var r := RichTextLabel.new()
	r.bbcode_enabled = true
	r.selection_enabled = true
	r.custom_minimum_size = Vector2(280, height)
	r.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return r

func collapsible_section(key: String, title: String, content: Control) -> VBoxContainer:
	var section := VBoxContainer.new()
	section.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	section.add_theme_constant_override("separation", 6)

	var collapsed := bool(host.left_panel_collapsed.get(key, true))

	var b := Button.new()
	b.text = collapse_label(title, collapsed)
	host._button(b, false)
	b.pressed.connect(func(): toggle_section(key, content))

	section.add_child(b)
	content.visible = not collapsed
	section.add_child(content)

	host.left_panel_buttons[key] = b
	return section

func collapse_label(title: String, collapsed: bool) -> String:
	return "+ " + title if collapsed else "- " + title

func section_title(key: String) -> String:
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

func toggle_section(key: String, content: Control) -> void:
	var collapsed := not bool(host.left_panel_collapsed.get(key, true))
	host.left_panel_collapsed[key] = collapsed
	content.visible = not collapsed

	if host.left_panel_buttons.has(key):
		var b: Button = host.left_panel_buttons[key]
		b.text = collapse_label(section_title(key), collapsed)

	host._observe_panel_toggle(key, not collapsed)
