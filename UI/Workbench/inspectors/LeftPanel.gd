extends VBoxContainer

class_name LeftPanel

const CAPABILITY_STATE_PATH := "res://Workbench/audit/output/capability_state.json"

var sections: Dictionary = {}
var selected_section := "Current Test"
var expanded: Dictionary = {
	"Current Test": true,
	"Summary": false,
	"Evidence": false,
	"Unresolved": false,
	"Refresh": false
}


func _ready() -> void:
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	add_theme_constant_override("separation", 8)
	load_latest_capability_state()


func load_latest_capability_state() -> void:
	var state_path := ProjectSettings.globalize_path(CAPABILITY_STATE_PATH)

	if not FileAccess.file_exists(state_path):
		sections = {
			"Current Test": {
				"status": "capability_state.json not found",
				"path": state_path
			},
			"Refresh": {
				"hotkey": "Ctrl+Shift+A",
				"action": "Run capability audit"
			}
		}
		render()
		return

	var file := FileAccess.open(state_path, FileAccess.READ)

	if file == null:
		sections = {
			"Current Test": {
				"status": "unable to open capability_state.json",
				"path": state_path
			}
		}
		render()
		return

	var parsed = JSON.parse_string(file.get_as_text())

	if typeof(parsed) != TYPE_DICTIONARY:
		sections = {
			"Current Test": {
				"status": "failed to parse capability_state.json"
			}
		}
		render()
		return

	load_capability_state(parsed)


func load_capability_state(state: Dictionary) -> void:
	var current_test: Dictionary = state.get("current_test", {})
	var summary: Dictionary = state.get("summary", {})

	var evidence_text := str(current_test.get("evidence", ""))
	var unresolved_value = current_test.get("unresolved", [])

	sections = {
		"Current Test": {
			"id": current_test.get("id", "none"),
			"step": current_test.get("step", "No active test"),
			"pass_condition": current_test.get("pass_condition", ""),
			"result": current_test.get("result", "UNKNOWN")
		},
		"Summary": {
			"none": int(summary.get("NONE", 0)),
			"present": int(summary.get("PRESENT", 0)),
			"wired": int(summary.get("WIRED", 0)),
			"executable": int(summary.get("EXECUTABLE", 0)),
			"pass": int(summary.get("PASS", 0)),
			"partial": int(summary.get("PARTIAL", 0)),
			"fail": int(summary.get("FAIL", 0)),
			"untested": int(summary.get("UNTESTED", 0))
		},
		"Evidence": {
			"observed": evidence_text if not evidence_text.is_empty() else "No evidence recorded"
		},
		"Unresolved": unresolved_value,
		"Refresh": {
			"hotkey": "Ctrl+Shift+A",
			"action": "Run capability audit and reload this panel",
			"generated_at": state.get("generated_at", "unknown")
		}
	}

	render()


func render() -> void:
	_clear_children()

	var names := sections.keys()
	names.sort()

	if names.has(selected_section):
		names.erase(selected_section)
		_add_section(selected_section)

	for name in names:
		_add_section(str(name))


func _add_section(name: String) -> void:
	var is_open := bool(expanded.get(name, false))

	var button := Button.new()
	button.text = ("v " if is_open else "> ") + name
	button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	button.pressed.connect(_on_section_pressed.bind(name))
	add_child(button)

	if not is_open:
		return

	var label := RichTextLabel.new()
	label.bbcode_enabled = false
	label.fit_content = true
	label.selection_enabled = true
	label.context_menu_enabled = true
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	label.text = _format_value(sections.get(name, {}))
	add_child(label)


func _on_section_pressed(name: String) -> void:
	var was_open := bool(expanded.get(name, false))
	selected_section = name

	expanded.clear()
	expanded[name] = not was_open

	render()


func _format_value(value: Variant, indent := 0) -> String:
	var pad := ""

	for _i in indent:
		pad += "  "

	match typeof(value):
		TYPE_DICTIONARY:
			var lines := PackedStringArray()

			for key in value.keys():
				var child = value[key]

				if typeof(child) == TYPE_DICTIONARY or typeof(child) == TYPE_ARRAY:
					lines.append(pad + str(key) + ":")
					lines.append(_format_value(child, indent + 1))
				else:
					lines.append(pad + str(key) + ": " + str(child))

			return "\n".join(lines)

		TYPE_ARRAY:
			var lines := PackedStringArray()

			for item in value:
				if typeof(item) == TYPE_DICTIONARY:
					lines.append(pad + "-")
					lines.append(_format_value(item, indent + 1))
				else:
					lines.append(pad + "- " + str(item))

			return "\n".join(lines)

		_:
			return pad + str(value)


func _clear_children() -> void:
	for child in get_children():
		child.queue_free()
