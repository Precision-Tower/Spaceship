extends VBoxContainer
class_name OperatorShellCapabilityPanel

var current_test_label: RichTextLabel
var summary_label: Label
var details_button: Button
var details_label: RichTextLabel
var details_open := false

func _ready() -> void:
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	add_theme_constant_override("separation", 6)

	var title := Label.new()
	title.text = "CAPABILITY"
	title.add_theme_font_size_override("font_size", 15)
	add_child(title)

	current_test_label = RichTextLabel.new()
	current_test_label.bbcode_enabled = true
	current_test_label.fit_content = true
	current_test_label.scroll_active = false
	current_test_label.selection_enabled = true
	current_test_label.custom_minimum_size = Vector2(0, 86)
	add_child(current_test_label)

	summary_label = Label.new()
	summary_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	add_child(summary_label)

	var refresh := Label.new()
	refresh.text = "Ctrl+Shift+A  Refresh"
	add_child(refresh)

	details_button = Button.new()
	details_button.text = "+ Details"
	details_button.pressed.connect(_toggle_details)
	add_child(details_button)

	details_label = RichTextLabel.new()
	details_label.bbcode_enabled = true
	details_label.fit_content = true
	details_label.scroll_active = false
	details_label.selection_enabled = true
	details_label.visible = false
	details_label.custom_minimum_size = Vector2(0, 80)
	add_child(details_label)

	show_missing_state()

func show_missing_state() -> void:
	current_test_label.text = "[b]No audit state loaded[/b]\nRun Ctrl+Shift+A"
	summary_label.text = "No summary available"
	details_label.text = "operator_shell_state.json was not loaded."

func show_running() -> void:
	current_test_label.text = "[b]Running OperatorShell audit...[/b]"
	summary_label.text = "Inspecting current repository state"

func show_error(message: String) -> void:
	current_test_label.text = "[color=#e05f5f][b]AUDIT FAILED[/b][/color]"
	summary_label.text = message
	details_label.text = message

func load_state(state: Dictionary) -> void:
	if current_test_label == null or summary_label == null or details_label == null:
		return

	var current: Dictionary = state.get("current_test", {})
	var summary: Dictionary = state.get("summary", {})

	current_test_label.text = (
		"[color=#f1d58a][b]%s[/b][/color]\n%s\n[b]%s[/b]"
		% [
			str(current.get("id", "none")),
			str(current.get("step", "No active test")),
			str(current.get("result", "UNKNOWN"))
		]
	)

	summary_label.text = (
		"PASS %d  ·  PARTIAL %d  ·  FAIL %d  ·  UNTESTED %d"
		% [
			int(summary.get("PASS", 0)),
			int(summary.get("PARTIAL", 0)),
			int(summary.get("FAIL", 0)),
			int(summary.get("UNTESTED", 0))
		]
	)

	var evidence: String = str(current.get("evidence", ""))
	if evidence.is_empty():
		evidence = "No evidence recorded."

	var unresolved_value: Variant = current.get("unresolved", [])
	var unresolved: String = "None"
	if typeof(unresolved_value) == TYPE_ARRAY:
		var unresolved_array: Array = unresolved_value
		if not unresolved_array.is_empty():
			unresolved = "\n".join(PackedStringArray(unresolved_array))

	details_label.text = (
		"[b]Pass condition[/b]\n%s\n\n[b]Evidence[/b]\n%s\n\n[b]Unresolved[/b]\n%s"
		% [
			str(current.get("pass_condition", "")),
			evidence,
			unresolved
		]
	)

func _toggle_details() -> void:
	details_open = not details_open
	details_label.visible = details_open
	details_button.text = "- Details" if details_open else "+ Details"
