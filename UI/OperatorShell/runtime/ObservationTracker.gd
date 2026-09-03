extends RefCounted
class_name OperatorShellObservationTracker

const OBSERVATION_MAX_LINES := 12
const OBSERVATION_ROUTE_MAX := 5
const OBSERVATION_NOT_OBSERVED_MAX := 4

var observation_surfaces: Array = []
var click_counts := {}
var panel_toggles := {}
var surface_visits := {}
var recent_routes: Array[String] = []
var last_event := "none"

func _init(surfaces: Array = []) -> void:
	observation_surfaces = surfaces

func observe_button(label: String) -> void:
	_increment_count(click_counts, label)
	last_event = "button:" + label
	_push_route("button:" + label)

func observe_surface(surface: String) -> void:
	_increment_count(surface_visits, surface)
	last_event = "surface:" + surface
	_push_route("surface:" + surface)

func observe_chat_surface(name: String) -> void:
	_increment_count(surface_visits, "Chat")
	last_event = "chat:" + name
	_push_route("chat:" + name)

func observe_panel_toggle(key: String, opened: bool, label: String = "") -> void:
	var state := "open" if opened else "closed"
	var display := label if label != "" else key
	_increment_count(panel_toggles, display + ":" + state)
	last_event = "panel:" + display + ":" + state
	_push_route("panel:" + key + ":" + state)

func observe_event(kind: String, detail: String) -> void:
	last_event = kind + ":" + detail
	_push_route(last_event)

func observation_text(left_panel_collapsed: Dictionary, active_surface: String) -> String:
	var text := "[color=#f1d58a]OPERATOR OBSERVATION[/color]\n"
	text += "active_surface: " + active_surface + "\n"
	text += "last_event: " + last_event + "\n"
	text += "panels: " + panel_state_text(left_panel_collapsed) + "\n"
	text += "recent_routes: " + recent_routes_text() + "\n"
	text += "surface_visits: " + compact_counts(surface_visits, 4) + "\n"
	text += "button_counts: " + compact_counts(click_counts, 4) + "\n"
	text += "panel_toggles: " + compact_counts(panel_toggles, 3) + "\n"
	text += "not_observed: " + not_observed_text() + "\n"
	text += "[color=#b8aebe]observation != evidence[/color]"
	return cap_observation_lines(text)

func panel_state_text(left_panel_collapsed: Dictionary) -> String:
	var parts: Array[String] = ["current_status=open"]
	for key in left_panel_collapsed.keys():
		var state := "closed" if bool(left_panel_collapsed.get(key, true)) else "open"
		parts.append(str(key) + "=" + state)
	return join_strings(parts, ", ")

func recent_routes_text() -> String:
	if recent_routes.is_empty():
		return "none"
	return join_strings(recent_routes, " -> ")

func not_observed_text() -> String:
	var missing: Array[String] = []
	for surface in observation_surfaces:
		if int(surface_visits.get(surface, 0)) <= 0:
			missing.append(surface)
	if missing.is_empty():
		return "none"
	var capped: Array[String] = []
	var limit = min(missing.size(), OBSERVATION_NOT_OBSERVED_MAX)
	for i in range(limit):
		capped.append(missing[i])
	if missing.size() > limit:
		capped.append("+" + str(missing.size() - limit) + " more")
	return join_strings(capped, ", ")

func compact_counts(counts: Dictionary, max_entries: int) -> String:
	if counts.is_empty():
		return "none"
	var keys := count_keys_by_frequency(counts)
	var parts: Array[String] = []
	var limit = min(keys.size(), max_entries)
	for i in range(limit):
		var key := str(keys[i])
		parts.append(key + "=" + str(counts.get(key, 0)))
	if keys.size() > limit:
		parts.append("+" + str(keys.size() - limit) + " more")
	return join_strings(parts, ", ")

func count_keys_by_frequency(counts: Dictionary) -> Array:
	var keys := counts.keys()
	keys.sort_custom(func(a, b):
		var count_a := int(counts.get(str(a), 0))
		var count_b := int(counts.get(str(b), 0))
		if count_a == count_b:
			return str(a) < str(b)
		return count_a > count_b
	)
	return keys

func cap_observation_lines(text: String) -> String:
	var lines := text.split("\n")
	if lines.size() <= OBSERVATION_MAX_LINES:
		return text
	var capped: Array[String] = []
	var limit = min(lines.size(), OBSERVATION_MAX_LINES)
	for i in range(limit):
		capped.append(lines[i])
	capped.append("... observation capped; source state still tracked")
	return join_strings(capped, "\n")

func join_strings(items: Array[String], separator: String) -> String:
	var text := ""
	for i in range(items.size()):
		if i > 0:
			text += separator
		text += str(items[i])
	return text

func _increment_count(counts: Dictionary, key: String) -> void:
	counts[key] = int(counts.get(key, 0)) + 1

func _push_route(route: String) -> void:
	recent_routes.append(route)
	while recent_routes.size() > OBSERVATION_ROUTE_MAX:
		recent_routes.pop_front()


