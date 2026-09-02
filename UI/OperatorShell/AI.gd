extends Control

const CliBridge = preload("res://runtime/CliBridge.gd")

var intent_input
var output

func _ready():
	_build()

func _build():
	var root = VBoxContainer.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_theme_constant_override("separation", 10)
	add_child(root)

	var title = Label.new()
	title.text = "AI Test Surface"
	title.add_theme_font_size_override("font_size", 24)
	root.add_child(title)

	intent_input = LineEdit.new()
	intent_input.placeholder_text = "Tell the assistant what you want..."
	root.add_child(intent_input)

	var row = HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	root.add_child(row)

	var propose = Button.new()
	propose.text = "Propose Task"
	propose.pressed.connect(_propose_task)
	row.add_child(propose)

	var refresh = Button.new()
	refresh.text = "Refresh State"
	refresh.pressed.connect(_refresh_state)
	row.add_child(refresh)

	var test = Button.new()
	test.text = "Test CLI"
	test.pressed.connect(_test_cli)
	row.add_child(test)

	output = RichTextLabel.new()
	output.bbcode_enabled = true
	output.selection_enabled = true
	output.size_flags_vertical = Control.SIZE_EXPAND_FILL
	output.text = "Terminal ready.\n"
	root.add_child(output)

func _write(text):
	if output == null:
		print(text)
		return
	output.text += "\n> " + str(text) + "\n"

func _show_result(label, result):
	_write(label)
	_write("ok: " + str(result.get("ok", false)))
	_write("exit_code: " + str(result.get("exit_code", "unknown")))
	_write(str(result.get("stdout", "")))

func _propose_task():
	var intent = intent_input.text.strip_edges()
	if intent == "":
		_write("blocked: empty intent")
		return

	var result = CliBridge.propose_task_packet(intent)
	_show_result("PROPOSE_TASK_PACKET", result)

func _refresh_state():
	var result = CliBridge.runtime_state()
	_show_result("RUNTIME_STATE", result)

func _test_cli():
	var result = CliBridge.test_all()
	_show_result("TEST_ALL", result)