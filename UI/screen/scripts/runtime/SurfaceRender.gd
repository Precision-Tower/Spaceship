class_name SurfaceRenderer

var bottom_tabs: TabContainer
var history_label: RichTextLabel

func _init(bottom_tabs_ref: TabContainer = null, history_label_ref: RichTextLabel = null) -> void:
	bottom_tabs = bottom_tabs_ref
	history_label = history_label_ref

func bind_bottom_tabs(bottom_tabs_ref: TabContainer) -> void:
	bottom_tabs = bottom_tabs_ref

func bind_history_label(history_label_ref: RichTextLabel) -> void:
	history_label = history_label_ref

func add_bottom(name: String, content: String) -> void:
	if bottom_tabs == null:
		return

	var r := RichTextLabel.new()
	r.name = name
	r.bbcode_enabled = true
	r.selection_enabled = true
	r.text = "[color=#d6b15f]" + name + "[/color]\n\n" + content
	bottom_tabs.add_child(r)

func bottom_text(name: String) -> RichTextLabel:
	if bottom_tabs == null:
		return null

	for child in bottom_tabs.get_children():
		if child.name == name:
			return child

	return null

func set_bottom(name: String) -> void:
	if bottom_tabs == null:
		return

	for i in bottom_tabs.get_tab_count():
		if bottom_tabs.get_tab_title(i) == name:
			bottom_tabs.current_tab = i
			return

func log_line(text: String) -> void:
	var l := bottom_text("Logs")
	if l:
		l.append_text("\n[color=#d6b15f]" + Time.get_time_string_from_system() + "[/color] " + text)

func terminal(text: String) -> void:
	var t := bottom_text("Terminal")
	if t:
		t.append_text("\n\n[color=#d6b15f]>[/color] " + text)
	set_bottom("Terminal")

func diff(text: String) -> void:
	var d := bottom_text("Diffs")
	if d:
		d.append_text("\n\n[color=#d6b15f]>[/color] " + text)
	set_bottom("Diffs")

func packets(text: String) -> void:
	var p := bottom_text("Packets")
	if p:
		p.append_text("\n\n[color=#d6b15f]>[/color] " + text)
	set_bottom("Packets")

func format_result(result: Dictionary) -> String:
	var text := ""
	text += "command: " + str(result.get("command", "")) + "\n"
	text += "exit_code: " + str(result.get("exit_code", "")) + "\n"
	text += "python: " + str(result.get("python", "")) + "\n"
	text += "args: " + str(result.get("args", "")) + "\n"
	text += "debug_paths:\n" + str(result.get("debug_paths", "")) + "\n\n"
	text += str(result.get("stdout", ""))

	if result.get("ok", false):
		return "[color=#8fca7a]CLI command completed.[/color]\n" + text

	return "[color=#e05f5f]CLI command failed.[/color]\n" + text

func render_terminal(result: Dictionary) -> void:
	terminal(format_result(result))

func render_diff(result: Dictionary) -> void:
	diff(format_result(result))

func render_packets(result: Dictionary) -> void:
	packets(format_result(result))

func render_history(command_history: Array[Dictionary]) -> void:
	if history_label == null:
		return

	var text := "[color=#f1d58a]Command History[/color]\n"

	if command_history.is_empty():
		text += "\n(no commands yet)\n"
	else:
		for row in command_history:
			var status := str(row.get("status", "unknown"))
			var color := "#8fca7a" if status == "success" else "#e05f5f"
			text += "\n[color=" + color + "]status: " + status + "[/color]\n"
			text += "time: " + str(row.get("time", "--:--")) + "\n"
			text += "command: " + str(row.get("command", "unknown")) + "\n"
			text += "summary: " + str(row.get("summary", "")) + "\n"

	text += "\n[color=#b8aebe]history != evidence[/color]"
	history_label.text = text

func render_task_proposal(proposal: Dictionary) -> String:
	var t := "[color=#f1d58a]CALI PROPOSED TASK PACKET[/color]\n\n"
	t += "[color=#d6b15f]OBJECTIVE:[/color]\n" + str(proposal.get("OBJECTIVE", "")) + "\n\n"
	t += "[color=#d6b15f]INSPECT:[/color]\n" + str(proposal.get("INSPECT", [])) + "\n\n"
	t += "[color=#d6b15f]ALLOWED:[/color]\n" + str(proposal.get("ALLOWED", [])) + "\n\n"
	t += "[color=#d6b15f]FORBIDDEN:[/color]\n" + str(proposal.get("FORBIDDEN", [])) + "\n\n"
	t += "[color=#d6b15f]TEST:[/color]\n" + str(proposal.get("TEST", [])) + "\n\n"
	t += "[color=#d6b15f]SUCCESS:[/color]\n" + str(proposal.get("SUCCESS", [])) + "\n\n"
	t += "[color=#d6b15f]REPORT:[/color]\n" + str(proposal.get("REPORT", "")) + "\n\n"
	t += "[color=#b8aebe]APPROVAL BOUNDARY: review != authority • type 'confirm' to accept (placeholder)[/color]"
	return t

func show_task_proposal(proposal: Dictionary) -> void:
	terminal(render_task_proposal(proposal))
