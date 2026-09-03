extends RefCounted

static func value(status: Dictionary, key: String) -> String:
	return str(status.get(key, "unknown"))

static func field(state_text: String, key: String, fallback: String) -> String:
	for line in state_text.split("\n"):
		var clean := str(line).strip_edges()
		var colon := clean.find(":")
		var equals := clean.find("=")
		var split_at := colon
		if split_at == -1 or (equals != -1 and equals < split_at):
			split_at = equals
		if split_at == -1:
			continue
		if clean.substr(0, split_at).strip_edges() == key:
			return clean.substr(split_at + 1, clean.length() - split_at - 1).strip_edges()
	return fallback

static func status_text(status: Dictionary, active_surface: String, active_right_mode: String) -> String:
	return "[color=#f1d58a]Current Status[/color]\n" + \
		"[color=#d6b15f]current_root[/color]=" + value(status, "current_root") + "\n" + \
		"[color=#d6b15f]dashboard_boot[/color]=" + value(status, "dashboard_boot") + "\n" + \
		"[color=#d6b15f]latest_diff[/color]=" + value(status, "latest_diff") + "\n" + \
		"[color=#d6b15f]packets_pending[/color]=" + value(status, "packets_pending") + "\n" + \
		"[color=#d6b15f]git_dirty[/color]=" + value(status, "git_dirty") + "\n" + \
		"[color=#d6b15f]last_command[/color]=" + value(status, "last_command") + "\n" + \
		"[color=#d6b15f]active_surface[/color]=" + active_surface + " / " + active_right_mode + "\n" + \
		"[color=#d6b15f]next_required_action[/color]=" + value(status, "next_required_action") + "\n" + \
		"[color=#b8aebe]status != validation[/color]"

static func update_from_state_text(status: Dictionary, state_text: String, ok := true) -> void:
	status["current_root"] = field(state_text, "current_root", value(status, "current_root"))
	status["dashboard_boot"] = field(state_text, "dashboard_boot", value(status, "dashboard_boot"))
	status["latest_diff"] = field(state_text, "latest_diff", value(status, "latest_diff"))
	status["packets_pending"] = field(state_text, "packets_pending", value(status, "packets_pending"))
	status["git_dirty"] = field(state_text, "git_dirty", value(status, "git_dirty"))
	status["next_required_action"] = "Review refreshed state" if ok else "Inspect Refresh State failure"
