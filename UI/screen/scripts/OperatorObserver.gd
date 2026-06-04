class_name OperatorObservation

const OBSERVATION_MAX_LINES := 12
const OBSERVATION_ROUTE_MAX := 5
const OBSERVATION_NOT_OBSERVED_MAX := 4

const OBSERVATION_SURFACES := [
	"Home",
	"State",
	"Agents",
	"Packets",
	"Diffs",
	"Logs",
	"Settings",
	"Chat",
	"right:directory",
	"right:screens",
	"right:commands"
]

var click_counts := {}
var panel_toggles := {}
var surface_visits := {}
var recent_routes: Array[String] = []
var last_event := "none"

func observe_button(label: String) -> void:
	_increment_count(click_counts, label)
	_observe_event("button", label)

func observe_surface(surface: String) -> void:
	_increment_count(surface_visits, surface)
	_push_route(surface)
	_observe_event("surface", surface)

func observe_chat_surface(name: String) -> void:
	_increment_count(surface_visits, "Chat")
	_push_route(name)
	_observe_event("surface", name)

func observe_panel_toggle(title: String, opened: bool) -> void:
	var state := "open" if opened else "closed"
	_increment_count(panel_toggles, title)
	_observe_event("panel", title + "=" + state)

func text(panel_state_text: String) -> String:
	return _cap_lines("[color=#f1d58a]Operator Observation[/color]\n" +
		"observed_clicks: " + _compact_counts(click_counts, 4) + "\n" +
		"panel_state: " + panel_state_text + "\n" +
		"panel_toggles: " + _compact_counts(panel_toggles, 3) + "\n" +
		"surface_visits: " + _compact_counts(surface_visits, 4) + "\n" +
		"recent_routes: " + _recent_routes_text() + "\n" +
		"not_observed_this_session: " + _not_observed_text() + "\n" +
		"last_operator_event: " + last_event + "\n" +
		"[color=#b8aebe]observation != interpretation[/color]")

func _observe_event(kind: String, detail: String) -> void:
	last_event = kind + ": " + detail

func _increment_count(counts: Dictionary, key: String) -> void:
	counts[key] = int(counts.get(key, 0)) + 1

func _push_route(route: String) -> void:
	recent_routes.append(route)
	while recent_routes.size() > OBSERVATION_ROUTE_MAX:
		recent_routes.pop_front()

func _compact_counts(counts: Dictionary, max_entries: int) -> String:
	if counts.is_empty():
		return "none"

	var keys := _count_keys_by_frequency(counts)
	var parts: Array[String] = []
	var limit = min(keys.size(), max_entries)

	for i in limit:
		var key := str(keys[i])
		parts.append(key + "=" + str(counts.get(key, 0)))

	if keys.size() > max_entries:
		parts.append("+" + str(keys.size() - max_entries))

	return _join_strings(parts, ", ")

func _count_keys_by_frequency(counts: Dictionary) -> Array:
	var keys := counts.keys()
	keys.sort_custom(func(a, b):
		var count_a := int(counts.get(str(a), 0))
		var count_b := int(counts.get(str(b), 0))
		if count_a == count_b:
			return str(a) < str(b)
		return count_a > count_b
	)
	return keys

func _recent_routes_text() -> String:
	if recent_routes.is_empty():
		return "none"
	return _join_strings(recent_routes, " -> ")

func _not_observed_text() -> String:
	var missing: Array[String] = []

	for surface in OBSERVATION_SURFACES:
		if int(surface_visits.get(str(surface), 0)) == 0:
			missing.append(str(surface))

		if missing.size() >= OBSERVATION_NOT_OBSERVED_MAX:
			break

	if missing.is_empty():
		return "none"

	return _join_strings(missing, ", ")

func _cap_lines(value: String) -> String:
	var lines := value.split("\n")
	var capped: Array[String] = []
	var limit = min(lines.size(), OBSERVATION_MAX_LINES)

	for i in limit:
		capped.append(str(lines[i]))

	return _join_strings(capped, "\n")

func _join_strings(items: Array[String], separator: String) -> String:
	var value := ""

	for i in items.size():
		if i > 0:
			value += separator
		value += items[i]

	return value