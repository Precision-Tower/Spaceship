extends RefCounted
class_name OperatorShellTerminalSurface

const Palette = preload("res://widgets/Palette.gd")
const TerminalClient = preload("res://runtime/TerminalServiceClient.gd")

const SYSTEM_SESSION_ID := "system-log"
const SYSTEM_LOG_PATH := "/home/spaztic/Core/Dashboard/dashboard.log"
const SYSTEM_INITIAL_LINES := 200
const MAX_SCREEN_LINES := 5000
const RENDER_LINE_LIMIT := 5000

var host
var root: VBoxContainer
var tabs_holder: HBoxContainer
var body_host: VBoxContainer
var empty_state: VBoxContainer
var empty_label: RichTextLabel
var new_terminal_button: Button
var poll_timer: Timer
var sessions := {}
var selected_session_id := ""
var next_terminal_number := 2
var font_size := 10
var margin := 2
var shutting_down := false

func _init(owner) -> void:
	host = owner

func build() -> Control:
	root = VBoxContainer.new()
	root.name = "Terminal"
	root.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	root.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_theme_constant_override("separation", 4)
	root.tree_exiting.connect(shutdown)

	var strip := HBoxContainer.new()
	strip.add_theme_constant_override("separation", 4)
	root.add_child(strip)

	tabs_holder = HBoxContainer.new()
	tabs_holder.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	tabs_holder.add_theme_constant_override("separation", 4)
	strip.add_child(tabs_holder)

	new_terminal_button = Button.new()
	new_terminal_button.text = "+"
	new_terminal_button.tooltip_text = "New Terminal"
	new_terminal_button.custom_minimum_size = Vector2(30, 26)
	if host != null and host.has_method("_button"):
		host._button(new_terminal_button, true)
	new_terminal_button.pressed.connect(_create_session)
	strip.add_child(new_terminal_button)

	body_host = VBoxContainer.new()
	body_host.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body_host.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(body_host)

	_build_empty_state()

	poll_timer = Timer.new()
	poll_timer.wait_time = 0.08
	poll_timer.autostart = true
	poll_timer.timeout.connect(_poll_sessions)
	root.add_child(poll_timer)

	_create_system_console()
	return root

func apply_terminal_density(mode: String) -> void:
	match mode:
		"comfortable":
			font_size = 14
			margin = 12
		"compact":
			font_size = 12
			margin = 6
		"dense":
			font_size = 10
			margin = 2
		_:
			font_size = 10
			margin = 2

	for sid in sessions.keys():
		var label: RichTextLabel = sessions[sid].get("label")
		if label:
			label.add_theme_font_size_override("normal_font_size", font_size)
			label.add_theme_constant_override("text_highlight_h_padding", margin)
			label.add_theme_constant_override("text_highlight_v_padding", margin)
			_render_session(sid)

func append_system_text(text: String) -> void:
	if sessions.has(SYSTEM_SESSION_ID):
		_process_output(SYSTEM_SESSION_ID, "\r\n[OperatorShell] " + text + "\r\n")
		_select_session(SYSTEM_SESSION_ID)
		return
	_show_empty_message(text)

func shutdown() -> void:
	if shutting_down:
		return
	shutting_down = true
	if poll_timer:
		poll_timer.stop()
	var ids := sessions.keys()
	for sid in ids:
		var data: Dictionary = sessions.get(sid, {})
		if str(data.get("kind", "bash")) == "bash":
			TerminalClient.close_session(str(sid))
	sessions.clear()

func _build_empty_state() -> void:
	empty_state = VBoxContainer.new()
	empty_state.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	empty_state.size_flags_vertical = Control.SIZE_EXPAND_FILL
	empty_state.add_theme_constant_override("separation", 8)
	body_host.add_child(empty_state)

	empty_label = RichTextLabel.new()
	empty_label.bbcode_enabled = true
	empty_label.fit_content = false
	empty_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	empty_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	empty_label.text = "[color=#d6b15f]Terminal[/color]\n\nNo terminal sessions are open."
	empty_state.add_child(empty_label)

	var create := Button.new()
	create.text = "New Terminal"
	create.tooltip_text = "Open a Bash PTY session"
	if host != null and host.has_method("_button"):
		host._button(create, true)
	create.pressed.connect(_create_session)
	empty_state.add_child(create)

func _show_empty_message(message: String) -> void:
	if empty_label:
		empty_label.text = "[color=#d6b15f]Terminal[/color]\n\n" + _bbcode_escape(message)
	if empty_state:
		empty_state.visible = sessions.is_empty()

func _create_system_console() -> void:
	if sessions.has(SYSTEM_SESSION_ID):
		return
	var label := _create_terminal_label(SYSTEM_SESSION_ID)
	var tab_shell := _create_tab_button(SYSTEM_SESSION_ID, "T1 SYSTEM", false)
	sessions[SYSTEM_SESSION_ID] = {
		"id": SYSTEM_SESSION_ID,
		"kind": "system",
		"title": "T1 SYSTEM",
		"pid": -1,
		"state": "running",
		"cwd": SYSTEM_LOG_PATH,
		"label": label,
		"tab_shell": tab_shell,
		"tab_button": tab_shell.get_child(0),
		"lines": [[]],
		"cursor_col": 0,
		"fg": "",
		"exit_noted": false,
		"log_path": SYSTEM_LOG_PATH,
		"log_offset": 0,
		"log_error": "",
	}
	if empty_state:
		empty_state.visible = false
	_select_session(SYSTEM_SESSION_ID)
	_load_system_log_tail()
	_log_terminal("system console following " + SYSTEM_LOG_PATH)

func _load_system_log_tail() -> void:
	if not sessions.has(SYSTEM_SESSION_ID):
		return
	var data: Dictionary = sessions[SYSTEM_SESSION_ID]
	var path := str(data.get("log_path", SYSTEM_LOG_PATH))
	_reset_session_buffer(SYSTEM_SESSION_ID)
	if not FileAccess.file_exists(path):
		data = sessions[SYSTEM_SESSION_ID]
		data["log_offset"] = 0
		data["log_error"] = "missing"
		sessions[SYSTEM_SESSION_ID] = data
		_append_system_notice("waiting for " + path)
		return

	var file: FileAccess = FileAccess.open(path, FileAccess.READ)
	if file == null:
		_append_system_notice("failed to open " + path + ": " + str(FileAccess.get_open_error()))
		return
	var length: int = int(file.get_length())
	data = sessions[SYSTEM_SESSION_ID]
	data["log_offset"] = length
	data["log_error"] = ""
	sessions[SYSTEM_SESSION_ID] = data
	var tail_text: String = _read_log_tail(file, length, SYSTEM_INITIAL_LINES)
	if tail_text == "":
		_append_system_notice(path + " is empty; following new output.")
		return
	_process_output(SYSTEM_SESSION_ID, tail_text)

func _read_log_tail(file: FileAccess, length: int, max_lines: int) -> String:
	if length <= 0:
		return ""
	var read_size: int = int(min(length, 524288))
	var start: int = length - read_size
	file.seek(start)
	var bytes: PackedByteArray = file.get_buffer(read_size)
	var text_value: String = bytes.get_string_from_utf8()
	if start > 0:
		var first_newline: int = text_value.find("\n")
		if first_newline != -1:
			text_value = text_value.substr(first_newline + 1)
	return _last_lines(text_value, max_lines)

func _last_lines(text_value: String, max_lines: int) -> String:
	var split_lines: PackedStringArray = text_value.split("\n")
	var start_index: int = int(max(0, split_lines.size() - max_lines))
	var kept := PackedStringArray()
	for i in range(start_index, split_lines.size()):
		kept.append(split_lines[i])
	return "\n".join(kept)

func _poll_system_log() -> void:
	if not sessions.has(SYSTEM_SESSION_ID):
		return
	var data: Dictionary = sessions[SYSTEM_SESSION_ID]
	var path := str(data.get("log_path", SYSTEM_LOG_PATH))
	if not FileAccess.file_exists(path):
		if str(data.get("log_error", "")) != "missing":
			data["log_error"] = "missing"
			data["log_offset"] = 0
			sessions[SYSTEM_SESSION_ID] = data
			_append_system_notice("waiting for " + path)
		return

	var file: FileAccess = FileAccess.open(path, FileAccess.READ)
	if file == null:
		var error_text := "failed to open " + path + ": " + str(FileAccess.get_open_error())
		if str(data.get("log_error", "")) != error_text:
			data["log_error"] = error_text
			sessions[SYSTEM_SESSION_ID] = data
			_append_system_notice(error_text)
		return

	var length: int = int(file.get_length())
	var offset: int = int(data.get("log_offset", 0))
	if length < offset:
		_load_system_log_tail()
		_append_system_notice("dashboard.log was truncated; reloaded tail.")
		return
	if length == offset:
		return

	file.seek(offset)
	var bytes: PackedByteArray = file.get_buffer(length - offset)
	data["log_offset"] = length
	data["log_error"] = ""
	sessions[SYSTEM_SESSION_ID] = data
	var text_value: String = bytes.get_string_from_utf8()
	if text_value != "":
		_process_output(SYSTEM_SESSION_ID, text_value)

func _append_system_notice(message: String) -> void:
	if sessions.has(SYSTEM_SESSION_ID):
		_process_output(SYSTEM_SESSION_ID, "\r\n[system console] " + message + "\r\n")

func _reset_session_buffer(sid: String) -> void:
	if not sessions.has(sid):
		return
	var data: Dictionary = sessions[sid]
	data["lines"] = [[]]
	data["cursor_col"] = 0
	data["fg"] = ""
	sessions[sid] = data
	_render_session(sid)

func _is_system_session(sid: String) -> bool:
	if not sessions.has(sid):
		return false
	var data: Dictionary = sessions[sid]
	return str(data.get("kind", "bash")) == "system"

func _create_session() -> void:
	if shutting_down:
		return
	var dims := _terminal_dimensions()
	var response := TerminalClient.create_session(dims.x, dims.y)
	if not bool(response.get("ok", false)):
		var message := "Terminal failed: " + str(response.get("error", "unknown PTY error"))
		push_error(message)
		print("[OperatorTerminal] " + message)
		_show_empty_message(message)
		if host != null and host.has_method("_log"):
			host._log(message)
		return

	var sid := str(response.get("session_id", ""))
	if sid == "":
		_show_empty_message("Terminal failed: service returned no session_id")
		return

	var title := "T" + str(next_terminal_number) + " Bash"
	next_terminal_number += 1
	var label := _create_terminal_label(sid)
	var tab_shell := _create_tab_button(sid, title)

	sessions[sid] = {
		"id": sid,
		"kind": "bash",
		"title": title,
		"pid": int(response.get("pid", -1)),
		"state": str(response.get("state", "running")),
		"cwd": str(response.get("cwd", "")),
		"label": label,
		"tab_shell": tab_shell,
		"tab_button": tab_shell.get_child(0),
		"lines": [[]],
		"cursor_col": 0,
		"fg": "",
		"exit_noted": false,
	}

	if empty_state:
		empty_state.visible = false
	_select_session(sid)
	_log_terminal("created %s pid=%d" % [sid, int(response.get("pid", -1))])

func _create_tab_button(sid: String, title: String, closable: bool = true) -> HBoxContainer:
	var shell := HBoxContainer.new()
	shell.add_theme_constant_override("separation", 1)
	tabs_holder.add_child(shell)

	var select := Button.new()
	select.text = title
	select.toggle_mode = true
	select.tooltip_text = "Terminal " + title
	select.custom_minimum_size = Vector2(54, 24)
	if host != null and host.has_method("_button"):
		host._button(select, false)
	select.pressed.connect(_select_session.bind(sid))
	shell.add_child(select)

	if closable:
		var close := Button.new()
		close.text = "x"
		close.tooltip_text = "Close " + title
		close.custom_minimum_size = Vector2(24, 24)
		if host != null and host.has_method("_button"):
			host._button(close, false)
		close.pressed.connect(_close_session.bind(sid))
		shell.add_child(close)
	return shell

func _create_terminal_label(sid: String) -> RichTextLabel:
	var label := RichTextLabel.new()
	label.name = "Terminal_" + sid
	label.bbcode_enabled = true
	label.selection_enabled = true
	label.fit_content = false
	label.focus_mode = Control.FOCUS_ALL
	label.mouse_filter = Control.MOUSE_FILTER_STOP
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	label.add_theme_font_size_override("normal_font_size", font_size)
	label.add_theme_constant_override("text_highlight_h_padding", margin)
	label.add_theme_constant_override("text_highlight_v_padding", margin)
	label.gui_input.connect(_on_terminal_gui_input.bind(sid))
	label.resized.connect(_resize_session.bind(sid))
	label.visible = false
	body_host.add_child(label)
	return label

func _select_session(sid: String) -> void:
	if not sessions.has(sid):
		return
	selected_session_id = sid
	for key in sessions.keys():
		var data: Dictionary = sessions[key]
		var label: RichTextLabel = data.get("label")
		if label:
			label.visible = key == sid
		var button: Button = data.get("tab_button")
		if button:
			button.button_pressed = key == sid
	if empty_state:
		empty_state.visible = sessions.is_empty()
	var selected_label: RichTextLabel = sessions[sid].get("label")
	if selected_label and selected_label.is_inside_tree():
		selected_label.grab_focus()
	_resize_session(sid)

func _close_session(sid: String) -> void:
	if not sessions.has(sid):
		return
	if _is_system_session(sid):
		_select_session(SYSTEM_SESSION_ID)
		return
	var data: Dictionary = sessions[sid]
	TerminalClient.close_session(sid)
	var label: RichTextLabel = data.get("label")
	if label:
		label.queue_free()
	var tab_shell: Control = data.get("tab_shell")
	if tab_shell:
		tab_shell.queue_free()
	sessions.erase(sid)
	_log_terminal("closed " + sid)

	if selected_session_id == sid:
		selected_session_id = ""
		_select_session(SYSTEM_SESSION_ID)

func _poll_sessions() -> void:
	if shutting_down:
		return
	_poll_system_log()
	for sid in sessions.keys():
		if _is_system_session(str(sid)):
			continue
		var response := TerminalClient.read_output(str(sid))
		if not bool(response.get("ok", false)):
			_log_terminal("read failed for %s: %s" % [sid, str(response.get("error", "unknown"))])
			continue
		var data: Dictionary = sessions[sid]
		var output := str(response.get("output", ""))
		if output != "":
			_process_output(str(sid), output)
		var state := str(response.get("state", data.get("state", "running")))
		data["state"] = state
		if state != "running" and not bool(data.get("exit_noted", false)):
			data["exit_noted"] = true
			_mark_tab_exited(str(sid), int(response.get("exit_code", 0)))
		sessions[sid] = data

func _mark_tab_exited(sid: String, exit_code: int) -> void:
	if not sessions.has(sid):
		return
	var data: Dictionary = sessions[sid]
	var button: Button = data.get("tab_button")
	if button:
		button.text = str(data.get("title", "T")) + "*"
		button.tooltip_text = "Terminal exited with code " + str(exit_code)
	_log_terminal("session %s exited code=%d" % [sid, exit_code])

func _resize_session(sid: String = "") -> void:
	if sid == "":
		sid = selected_session_id
	if sid == "" or not sessions.has(sid) or _is_system_session(sid):
		return
	var dims := _terminal_dimensions(sid)
	TerminalClient.resize_session(sid, dims.x, dims.y)

func _terminal_dimensions(sid: String = "") -> Vector2i:
	var width := 900.0
	var height := 220.0
	if sid != "" and sessions.has(sid):
		var label: RichTextLabel = sessions[sid].get("label")
		if label:
			width = max(label.size.x, 200.0)
			height = max(label.size.y, 80.0)
	elif body_host:
		width = max(body_host.size.x, 200.0)
		height = max(body_host.size.y, 80.0)
	var cols := int(max(40.0, width / max(6.0, float(font_size) * 0.58)))
	var rows := int(max(8.0, height / max(10.0, float(font_size) * 1.35)))
	return Vector2i(cols, rows)

func _on_terminal_gui_input(event: InputEvent, sid: String) -> void:
	if sid != selected_session_id:
		return
	if event is InputEventMouseButton and event.pressed:
		var label: RichTextLabel = sessions[sid].get("label")
		if label and label.is_inside_tree():
			label.grab_focus()
		return
	if not (event is InputEventKey) or not event.pressed:
		return
	if _is_system_session(sid):
		if not _is_global_passthrough(event):
			root.get_viewport().set_input_as_handled()
		return
	var sequence := _event_to_sequence(event)
	if sequence == "":
		return
	var result := TerminalClient.write_input(sid, sequence)
	if not bool(result.get("ok", false)):
		_process_output(sid, "\r\n[terminal input failed: " + str(result.get("error", "unknown")) + "]\r\n")
	root.get_viewport().set_input_as_handled()

func _is_global_passthrough(event: InputEventKey) -> bool:
	if event.ctrl_pressed and event.shift_pressed and event.keycode == KEY_A:
		return true
	if event.alt_pressed and event.keycode == KEY_S:
		return true
	if event.ctrl_pressed and event.keycode == KEY_Q:
		return true
	return false

func _event_to_sequence(event: InputEventKey) -> String:
	if _is_global_passthrough(event):
		return ""
	if event.ctrl_pressed:
		if event.keycode >= KEY_A and event.keycode <= KEY_Z:
			return String.chr(event.keycode - KEY_A + 1)
		match event.keycode:
			KEY_SPACE:
				return String.chr(0)
			_:
				return ""
	match event.keycode:
		KEY_ENTER, KEY_KP_ENTER:
			# Readline accepts LF as submit. For Shift+Enter, send the
			# terminal Insert-key sequence first; in the current Bash/readline
			# stack that enters quoted-insert, so the following LF becomes a
			# literal newline in the editing buffer instead of accept-line.
			# Interactive PTY applications still receive raw terminal bytes.
			if event.shift_pressed:
				return String.chr(27) + "[2~\n"
			return "\n"
		KEY_BACKSPACE:
			return String.chr(127)
		KEY_TAB:
			return "\t"
		KEY_ESCAPE:
			return String.chr(27)
		KEY_UP:
			return String.chr(27) + "[A"
		KEY_DOWN:
			return String.chr(27) + "[B"
		KEY_RIGHT:
			return String.chr(27) + "[C"
		KEY_LEFT:
			return String.chr(27) + "[D"
		KEY_HOME:
			return String.chr(27) + "[H"
		KEY_END:
			return String.chr(27) + "[F"
		KEY_DELETE:
			return String.chr(27) + "[3~"
		_:
			if event.unicode > 0 and not event.alt_pressed and not event.meta_pressed:
				return String.chr(event.unicode)
	return ""

func _process_output(sid: String, text: String) -> void:
	if not sessions.has(sid):
		return
	var data: Dictionary = sessions[sid]
	var i := 0
	while i < text.length():
		var code := text.unicode_at(i)
		if code == 27:
			i = _consume_escape(data, text, i)
			continue
		match code:
			10:
				_newline(data)
			13:
				data["cursor_col"] = 0
			8, 127:
				data["cursor_col"] = max(0, int(data.get("cursor_col", 0)) - 1)
			_:
				if code >= 32 or code == 9:
					_put_char(data, String.chr(code))
		i += 1
	sessions[sid] = data
	_trim_lines(data)
	_render_session(sid)

func _consume_escape(data: Dictionary, text: String, index: int) -> int:
	if index + 1 >= text.length():
		return index + 1
	var next_code := text.unicode_at(index + 1)
	if next_code == 91:
		var end := index + 2
		while end < text.length():
			var c := text.unicode_at(end)
			if c >= 64 and c <= 126:
				var params := text.substr(index + 2, end - index - 2)
				_apply_csi(data, params, String.chr(c))
				return end + 1
			end += 1
		return text.length()
	if next_code == 93:
		var end_osc := index + 2
		while end_osc < text.length():
			var c2 := text.unicode_at(end_osc)
			if c2 == 7:
				return end_osc + 1
			if c2 == 27 and end_osc + 1 < text.length() and text.unicode_at(end_osc + 1) == 92:
				return end_osc + 2
			end_osc += 1
		return text.length()
	return index + 2

func _apply_csi(data: Dictionary, params: String, final_char: String) -> void:
	match final_char:
		"m":
			_apply_sgr(data, params)
		"K":
			_clear_line(data, params)
		_:
			pass

func _apply_sgr(data: Dictionary, params: String) -> void:
	var parts := params.split(";", false)
	if parts.is_empty():
		parts = ["0"]
	for raw in parts:
		var value := 0 if str(raw).strip_edges() == "" else int(raw)
		if value == 0 or value == 39:
			data["fg"] = ""
		elif _ansi_color(value) != "":
			data["fg"] = _ansi_color(value)

func _ansi_color(value: int) -> String:
	match value:
		30:
			return "#1f1b24"
		31:
			return "#e05f5f"
		32:
			return "#8fca7a"
		33:
			return "#d6b15f"
		34:
			return "#70a7d7"
		35:
			return "#c586c0"
		36:
			return "#64c7c7"
		37:
			return "#e5ddea"
		90:
			return "#6f6877"
		91:
			return "#ff7b7b"
		92:
			return "#a8e090"
		93:
			return "#f1d58a"
		94:
			return "#8ec5ff"
		95:
			return "#dfa0d8"
		96:
			return "#83e4e4"
		97:
			return "#ffffff"
		_:
			return ""

func _clear_line(data: Dictionary, params: String) -> void:
	var mode := 0 if params.strip_edges() == "" else int(params)
	var lines: Array = data.get("lines", [[]])
	var line: Array = lines[lines.size() - 1]
	var cursor := int(data.get("cursor_col", 0))
	match mode:
		0:
			while line.size() > cursor:
				line.pop_back()
		1:
			for i in range(0, min(cursor + 1, line.size())):
				line[i] = _cell(" ", str(data.get("fg", "")))
		2:
			line.clear()
			data["cursor_col"] = 0
	lines[lines.size() - 1] = line
	data["lines"] = lines

func _put_char(data: Dictionary, ch: String) -> void:
	var lines: Array = data.get("lines", [[]])
	if lines.is_empty():
		lines.append([])
	var line: Array = lines[lines.size() - 1]
	var cursor := int(data.get("cursor_col", 0))
	while line.size() < cursor:
		line.append(_cell(" ", str(data.get("fg", ""))))
	var cell := _cell(ch, str(data.get("fg", "")))
	if cursor < line.size():
		line[cursor] = cell
	else:
		line.append(cell)
	data["cursor_col"] = cursor + 1
	lines[lines.size() - 1] = line
	data["lines"] = lines

func _newline(data: Dictionary) -> void:
	var lines: Array = data.get("lines", [[]])
	lines.append([])
	data["lines"] = lines
	data["cursor_col"] = 0

func _trim_lines(data: Dictionary) -> void:
	var lines: Array = data.get("lines", [[]])
	while lines.size() > MAX_SCREEN_LINES:
		lines.pop_front()
	data["lines"] = lines

func _cell(ch: String, fg: String) -> Dictionary:
	return {"ch": ch, "fg": fg}

func _render_session(sid: String) -> void:
	if not sessions.has(sid):
		return
	var data: Dictionary = sessions[sid]
	var label: RichTextLabel = data.get("label")
	if label == null:
		return
	var lines: Array = data.get("lines", [[]])
	var start: int = int(max(0, lines.size() - RENDER_LINE_LIMIT))
	var output := ""
	for i in range(start, lines.size()):
		output += _render_line(lines[i])
		if i < lines.size() - 1:
			output += "\n"
	label.text = output

func _render_line(line: Array) -> String:
	var output := ""
	var active_fg := ""
	for cell in line:
		var fg := str(cell.get("fg", ""))
		if fg != active_fg:
			if active_fg != "":
				output += "[/color]"
			active_fg = fg
			if active_fg != "":
				output += "[color=" + active_fg + "]"
		output += _bbcode_escape(str(cell.get("ch", "")))
	if active_fg != "":
		output += "[/color]"
	return output

func _bbcode_escape(value: String) -> String:
	return value.replace("[", "[lb]").replace("]", "[rb]")

func _log_terminal(message: String) -> void:
	print("[OperatorTerminal] " + message)
	if host != null and host.has_method("_log"):
		host._log("terminal: " + message)
