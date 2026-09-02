extends RefCounted
class_name OperatorShellWorkspaceSurface

const Palette = preload("res://OperatorShell/widgets/Palette.gd")

var host
var workspace_tabs: TabContainer

func _init(owner) -> void:
	host = owner

func build() -> Control:
	var shell := PanelContainer.new()
	shell.size_flags_vertical = Control.SIZE_FILL
	shell.custom_minimum_size = Vector2(0, 0)
	host._panel(shell, Palette.PLUM_PANEL, Palette.GOLD_DARK, 1, 18)
	workspace_tabs = TabContainer.new()
	workspace_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
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

func add_or_focus_tab(name: String, node: Control) -> void:
	for i in workspace_tabs.get_tab_count():
		if workspace_tabs.get_tab_title(i) == name:
			workspace_tabs.current_tab = i
			return

	node.name = name
	workspace_tabs.add_child(node)
	workspace_tabs.set_tab_title(workspace_tabs.get_tab_count() - 1, name)
	workspace_tabs.current_tab = workspace_tabs.get_tab_count() - 1

