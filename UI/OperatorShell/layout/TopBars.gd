extends RefCounted
class_name OperatorShellTopBars

const Palette = preload("res://widgets/Palette.gd")

var host

func _init(owner) -> void:
	host = owner

func top_bar() -> Control:
	var p := PanelContainer.new()
	p.custom_minimum_size = Vector2(0, 50)
	host._panel(p, Palette.PLUM_DEEP, Palette.GOLD_DARK, 1, 12)

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

func runtime_state_bar() -> Control:
	var p := PanelContainer.new()
	p.custom_minimum_size = Vector2(0, 78)
	host._panel(p, Palette.PLUM_CARD, Palette.GOLD_DARK, 1, 14)

	host.state_label = Label.new()
	host.state_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	host.state_label.add_theme_color_override("font_color", Palette.TEXT)
	host.state_label.text = "Runtime State\nstatus: booted_not_refreshed | latest_diff: unknown | git_dirty: unknown | packets_pending: unknown\nboundary: runtime_state_reports_observation_only"

	p.add_child(host.state_label)
	return p

