extends RefCounted
class_name OperatorShellMissionService

static func read_mission(path: String) -> Dictionary:
    var file: FileAccess = FileAccess.open(path, FileAccess.READ)
    if file == null:
        return {"missing": true, "name": "", "phase": "", "next_action": "", "tasks": [], "goal": "", "decision": "", "observed": "", "recommendation": ""}

    var text: String = file.get_as_text()
    var lines: PackedStringArray = text.split("\n")

    var data: Dictionary = {"missing": false, "name": "", "phase": "", "next_action": "", "tasks": [], "goal": "", "decision": "", "observed": "", "recommendation": ""}
    var in_tasks: bool = false

    for l in lines:
        var line: String = str(l).strip_edges()
        if line == "":
            continue

        if line.begins_with("tasks:"):
            in_tasks = true
            continue

        if in_tasks and line.begins_with("-"):
            var item: String = line.substr(1, line.length() - 1).strip_edges()
            var status: String = "pending"
            var text_val: String = item

            if item.begins_with("[") and item.length() > 3:
                var mark: String = item.substr(1, 1)
                status = "done" if mark.to_lower() == "x" else "pending"
                text_val = item.substr(3, item.length() - 3).strip_edges()

            data["tasks"].append({"status": status, "text": text_val})
            continue

        var colon: int = line.find(":")
        if colon > -1:
            var key: String = line.substr(0, colon).strip_edges().to_lower()
            var val: String = line.substr(colon + 1, line.length() - colon - 1).strip_edges()

            match key:
                "name":
                    data["name"] = val
                "phase":
                    data["phase"] = val
                "next_action":
                    data["next_action"] = val
                "goal":
                    data["goal"] = val
                "decision":
                    data["decision"] = val
                "observed":
                    data["observed"] = val
                "recommendation":
                    data["recommendation"] = val

    return data

static func mission_text_from_data(data: Dictionary) -> String:
    if bool(data.get("missing", false)):
        return "[color=#e05f5f]MISSION[/color]\n\nMission file missing."

    var text: String = "[color=#f1d58a]MISSION[/color]\n\n"

    var goal: String = str(data.get("goal", "")).strip_edges()
    var name: String = str(data.get("name", "")).strip_edges()
    if goal != "":
        text += "[b]Goal:[/b] " + goal + "\n"
    elif name != "":
        text += "[b]Name:[/b] " + name + "\n"

    var decision: String = str(data.get("decision", "")).strip_edges()
    if decision != "":
        text += "[b]Decision:[/b] " + decision + "\n"

    var observed: String = str(data.get("observed", "")).strip_edges()
    if observed != "":
        text += "[b]Observed:[/b] " + observed + "\n"

    var recommendation: String = str(data.get("recommendation", "")).strip_edges()
    if recommendation != "":
        text += "[b]Recommendation:[/b] " + recommendation + "\n"

    var phase: String = str(data.get("phase", "")).strip_edges()
    var next_a: String = str(data.get("next_action", "")).strip_edges()

    if phase != "":
        text += "[b]Phase:[/b] " + phase + "\n"
    if next_a != "":
        text += "[b]Next:[/b] " + next_a + "\n"

    var tasks: Array = data.get("tasks", [])
    if tasks.size() > 0:
        text += "\n[color=#f1d58a]Tasks[/color]\n"
        var limit: int = min(tasks.size(), 5)
        for i in range(limit):
            var t: Dictionary = tasks[i]
            var mark: String = "[ ]"
            var status_str: String = str(t.get("status", ""))
            if status_str == "done":
                mark = "[x]"
            text += mark + " " + str(t.get("text", "")) + "\n"

    text += "\n[color=#b8aebe]mission_display != mission_completion[/color]"
    return text

static func render(path: String) -> String:
    return mission_text_from_data(read_mission(path))
