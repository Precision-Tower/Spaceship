#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-$HOME/Core/Dashboard}"
MAIN="$REPO_ROOT/UI/OperatorShell/Main.gd"

if [[ ! -f "$MAIN" ]]; then
  echo "Missing: $MAIN" >&2
  exit 1
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
cp "$MAIN" "$MAIN.bak_$STAMP"

python3 - "$MAIN" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

var_anchor = re.search(r'(?m)^var main_v_split:\s*VSplitContainer\s*$', text)
if not var_anchor:
    raise SystemExit("Could not find main_v_split variable anchor.")

new_vars = (
    "\nvar center_vbox: VBoxContainer"
    "\nvar left_dock_shell: VBoxContainer"
    "\nvar right_dock_shell: VBoxContainer"
    "\nvar left_reveal_button: Button"
    "\nvar right_reveal_button: Button"
    "\nvar left_dock_open := true"
    "\nvar right_dock_open := true"
)

if "var center_vbox: VBoxContainer" not in text:
    text = text[:var_anchor.end()] + new_vars + text[var_anchor.end():]

build_pattern = re.compile(
    r'(?ms)^func _build\(\) -> void:\n.*?(?=^func _top_bar\(\) -> Control:)',
)

new_build = '''func _build() -> void:
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


'''

if not build_pattern.search(text):
    raise SystemExit("Could not locate _build() block.")

text = build_pattern.sub(new_build, text, count=1)

text = re.sub(
    r'(?ms)\n[ \t]*if left_panel_control:\n[ \t]*left_panel_control\.visible = config\.show_left_panel\n',
    "\n",
    text,
    count=1,
)

text = re.sub(
    r'(?ms)\n[ \t]*if right_rail_control:\n[ \t]*right_rail_control\.visible = config\.show_right_rail\n',
    "\n",
    text,
    count=1,
)

path.write_text(text, encoding="utf-8")
print("OperatorShell shell geometry updated.")
PY

echo
echo "Modified: $MAIN"
echo "Backup:   $MAIN.bak_$STAMP"
echo
echo "Verification:"
grep -nE   "center_vbox|_build_left_dock_shell|_build_right_dock_shell|_toggle_left_dock|_toggle_right_dock"   "$MAIN" || true
