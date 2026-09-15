extends RefCounted
class_name OperatorShellWorkspaceSurface

const Palette = preload("res://widgets/Palette.gd")

var host
var workspace_tabs: TabContainer
var internet_surface: Control

func _init(owner) -> void:
	host = owner

func _make_tab_style(bg: Color) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.corner_radius_top_left = 4
	sb.corner_radius_top_right = 4
	sb.content_margin_left = 10
	sb.content_margin_right = 10
	sb.content_margin_top = 4
	sb.content_margin_bottom = 4
	return sb

func _apply_tab_theme() -> void:
	var dark_purple := Color("26143d")
	var light_purple := Color("4a2d63")
	var gold := Color("d6b15f")
	var pale_gold := Color("f1d58a")

	var bg_style := StyleBoxFlat.new()
	bg_style.bg_color = dark_purple

	workspace_tabs.add_theme_stylebox_override("tabbar_background", bg_style)
	workspace_tabs.add_theme_stylebox_override("tab_unselected", _make_tab_style(light_purple))
	workspace_tabs.add_theme_stylebox_override("tab_selected", _make_tab_style(gold))
	workspace_tabs.add_theme_stylebox_override("tab_hovered", _make_tab_style(pale_gold))
	workspace_tabs.add_theme_color_override("font_unselected_color", gold)
	workspace_tabs.add_theme_color_override("font_selected_color", dark_purple)
	workspace_tabs.add_theme_color_override("font_hovered_color", dark_purple)
	workspace_tabs.add_theme_font_size_override("font_size", 12)

func build() -> Control:
	var shell := PanelContainer.new()
	shell.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	shell.size_flags_vertical = Control.SIZE_EXPAND_FILL
	shell.custom_minimum_size = Vector2(0, 0)
	host._panel(shell, Palette.PLUM_PANEL, Palette.GOLD_DARK, 1, 18)

	workspace_tabs = TabContainer.new()
	workspace_tabs.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	workspace_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_apply_tab_theme()
	shell.add_child(workspace_tabs)
	return shell

func new_chat(observed := true) -> void:
	host.chat_count += 1
	var name: String = "Chat %02d" % host.chat_count
	open_chat(name, observed)

func open_chat(name: String, observed := true) -> void:
	host.active_surface = name
	host._render_current_status()
	if observed:
		host._observe_chat_surface(name)

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

	add_or_focus_tab(name, box)

func open_screen(name: String, observed := true) -> void:
	host.active_surface = name
	host._render_current_status()
	if observed:
		host._observe_surface(name)
	if name == "Home":
		var bg := ColorRect.new()
		bg.name = "HomeBackground"
		bg.color = Palette.PLUM_BLACK
		bg.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		bg.size_flags_vertical = Control.SIZE_EXPAND_FILL
		add_or_focus_tab(name, bg)
		return


	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 12)

	var title := Label.new()
	title.text = name
	title.add_theme_font_size_override("font_size", 24)
	title.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
	box.add_child(title)

	var card := PanelContainer.new()
	card.size_flags_vertical = Control.SIZE_EXPAND_FILL
	host._panel(card, Palette.PLUM_CARD, Palette.GOLD_DARK, 1, 14)
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
	add_or_focus_tab(name, box)

func open_workbench(name: String = "Workbench") -> void:
	host.active_surface = name
	host._render_current_status()
	var surface: Control = load("res://runtime/SurfaceCanvas.gd").new()
	surface.name = name
	surface.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	surface.size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_or_focus_tab(name, surface)
	host.surface_canvas = surface

func open_internet(observed := true) -> void:
	host.active_surface = "Internet"
	host._render_current_status()
	if observed:
		host._observe_surface("Internet")

	if internet_surface != null and is_instance_valid(internet_surface):
		for i in workspace_tabs.get_tab_count():
			if workspace_tabs.get_tab_title(i) == "Internet":
				workspace_tabs.current_tab = i
				return
		return

	var surface := Control.new()
	surface.name = "InternetSurface"
	surface.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	surface.size_flags_vertical = Control.SIZE_EXPAND_FILL
	internet_surface = surface
	workspace_tabs.add_child(surface)
	workspace_tabs.set_tab_title(workspace_tabs.get_tab_count() - 1, "Internet")
	workspace_tabs.current_tab = workspace_tabs.get_tab_count() - 1

func add_or_focus_tab(name: String, node: Control) -> void:
	for i in workspace_tabs.get_tab_count():
		if workspace_tabs.get_tab_title(i) == name:
			workspace_tabs.current_tab = i
			return

	node.name = name
	workspace_tabs.add_child(node)
	workspace_tabs.set_tab_title(workspace_tabs.get_tab_count() - 1, name)
	workspace_tabs.current_tab = workspace_tabs.get_tab_count() - 1