class_name MissionReader

static func read_mission(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {"missing": true}

	var file: FileAccess = FileAccess.open(path, FileAccess.READ)
	if file == null:
		return {"missing": true}

	var text: String = file.get_as_text()
	file.close()

	var lines: PackedStringArray = text.split("\n")

	var normalized: PackedStringArray = []
	var saw_mission_root: bool = false
	var removed_root: bool = false

	for i in range(lines.size()):
		var raw_line: String = str(lines[i])
		var stripped_line: String = raw_line.strip_edges()

		if not saw_mission_root and stripped_line.ends_with(":") and stripped_line.to_lower().begins_with("mission"):
			saw_mission_root = true
			removed_root = true
			continue

		if saw_mission_root:
			if raw_line.begins_with("  "):
				normalized.append(raw_line.substr(2, raw_line.length() - 2))
			elif raw_line.begins_with(" "):
				normalized.append(raw_line.substr(1, raw_line.length() - 1))
			else:
				normalized.append(raw_line)
		else:
			normalized.append(raw_line)

	if removed_root:
		lines = normalized

	var data: Dictionary = {
		"missing": false,
		"name": "",
		"phase": "",
		"next_action": "",
		"tasks": [],
		"goal": "",
		"decision": "",
		"observed": "",
		"recommendation": ""
	}

	var in_tasks: bool = false
	var current_task: Dictionary = {}

	for l in lines:
		var line: String = str(l).strip_edges()

		if line == "" or line.begins_with("#"):
			continue

		if in_tasks:
			if line.begins_with("-"):
				var item: String = line.substr(1, line.length() - 1).strip_edges()
				current_task = {"text": "", "status": "pending"}

				if item.find(":") != -1:
					var item_key: String = item.substr(0, item.find(":")).strip_edges().to_lower()
					var item_val: String = item.substr(item.find(":") + 1, item.length() - item.find(":") - 1).strip_edges()

					if item_key == "status":
						current_task["status"] = item_val
					elif item_key == "label":
						current_task["text"] = item_val
					else:
						var status: String = "pending"
						var text_val: String = item

						if item.begins_with("[") and item.find("]") >= 2:
							var mark: String = item.substr(1, 1)
							text_val = item.substr(
								item.find("]") + 1,
								item.length() - (item.find("]") + 1)
							).strip_edges()

							if mark == "x" or mark == "X":
								status = "complete"
							elif mark == "~":
								status = "in_progress"
							elif mark == "!":
								status = "blocked"

						current_task["status"] = status
						current_task["text"] = text_val
				else:
					current_task["text"] = item

				data["tasks"].append(current_task)
				continue

			elif line.begins_with("status:") or line.begins_with("label:"):
				if data["tasks"].size() > 0:
					var current: Dictionary = data["tasks"][data["tasks"].size() - 1]
					var detail_key: String = line.substr(0, line.find(":")).strip_edges().to_lower()
					var detail_val: String = line.substr(
						line.find(":") + 1,
						line.length() - line.find(":") - 1
					).strip_edges()

					if detail_key == "status":
						current["status"] = detail_val
					elif detail_key == "label":
						current["text"] = detail_val
				continue
			else:
				in_tasks = false

		var colon: int = line.find(":")

		if colon != -1:
			var key: String = line.substr(0, colon).strip_edges().to_lower()
			var val: String = line.substr(colon + 1, line.length() - colon - 1).strip_edges()

			if key == "name" or key == "mission":
				data["name"] = val
			elif key == "phase" or key == "current_phase":
				data["phase"] = val
			elif key == "next_action" or key == "next-action" or key == "next action":
				data["next_action"] = val
			elif key == "goal":
				data["goal"] = val
			elif key == "decision":
				data["decision"] = val
			elif key == "observed" or key == "observation":
				data["observed"] = val
			elif key == "recommendation" or key == "recommend":
				data["recommendation"] = val
			elif key == "tasks":
				in_tasks = true

	return data


static func mission_text_from_data(data: Dictionary) -> String:
	if bool(data.get("missing", false)):
		return "[color=#f1d58a]MISSION[/color]\nMission file missing."

	var text: String = "[color=#f1d58a]MISSION[/color]\n\n"

	var goal: String = str(data.get("goal", "")).strip_edges()
	var name: String = str(data.get("name", "")).strip_edges()

	if goal != "":
		text += "Current Goal:\n" + goal + "\n\n"
	elif name != "":
		text += "Current Goal:\n" + name + "\n\n"

	var decision: String = str(data.get("decision", "")).strip_edges()
	if decision != "":
		text += "Current Decision:\n" + decision + "\n\n"

	var observed: String = str(data.get("observed", "")).strip_edges()
	if observed != "":
		text += "Observed:\n" + observed + "\n\n"

	var recommendation: String = str(data.get("recommendation", "")).strip_edges()
	if recommendation != "":
		text += "Recommendation:\n" + recommendation + "\n\n"

	var phase: String = str(data.get("phase", "")).strip_edges()
	var next_a: String = str(data.get("next_action", "")).strip_edges()

	if next_a != "":
		text += "Next:\n" + next_a + "\n\n"
	elif phase != "":
		text += "Phase:\n" + phase + "\n\n"

	text += "Top Tasks:\n"

	var tasks: Array = data.get("tasks", [])
	var limit: int = min(tasks.size(), 5)

	if limit == 0:
		text += "(no tasks)\n"
	else:
		for i in range(limit):
			var t: Dictionary = tasks[i]
			var mark: String = "[ ]"
			var status_str: String = str(t.get("status", ""))

			if status_str == "complete":
				mark = "[x]"
			elif status_str == "in_progress":
				mark = "[~]"
			elif status_str == "blocked":
				mark = "[!]"

			text += mark + " " + str(t.get("text", "")) + "\n"

	return text