extends RefCounted
class_name OperatorShellBottomDock

const Palette = preload("res://widgets/Palette.gd")

var host
var bottom_shell: PanelContainer
var bottom_tabs
var terminal_surface

func _init(owner) -> void:
	host = owner

func build() -> Control:
	bottom_shell = PanelContainer.new()
	bottom_shell.custom_minimum_size = Vector2(0, 48)
	host._panel(bottom_shell, Palette.PLUM_DEEP, Palette.GOLD_DARK, 1, 0)

	var strip := ColorRect.new()
	strip.color = Color(1.0, 0.0, 1.0, 1.0)  # bright magenta test
	strip.custom_minimum_size = Vector2(0, 40)
	strip.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	strip.size_flags_vertical = Control.SIZE_EXPAND_FILL
	bottom_shell.add_child(strip)

	bottom_tabs = self
	return bottom_shell

func set_bottom(_name: String) -> void: pass
func log_line(_t: String) -> void: pass
func terminal(_t: String) -> void: pass
func diff(_t: String) -> void: pass
func packets(_t: String) -> void: pass
func record_command(_a, _b, _c) -> void: pass
func render_history() -> void: pass
func shutdown_terminals() -> void: pass
func apply_terminal_density(_m: String) -> void: pass
func bottom_text(_n: String): return null
func get_tab_count() -> int: return 0
func get_tab_title(_i: int) -> String: return ""
func set_current_tab(_i: int) -> void: pass
func get_current_tab() -> int: return 0