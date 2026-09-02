extends PopupMenu

signal create_command_requested(category: String, item: String, world_position: Vector3)

var _registry: Dictionary = {}
var _item_data_by_id: Dictionary = {}
var _next_item_id := 1
var _world_position := Vector3.ZERO


func _ready() -> void:
	allow_search = false
	id_pressed.connect(_on_id_pressed)


func load_registry(path: String) -> void:
	_registry = {}

	if not FileAccess.file_exists(path):
		_build_menu()
		return

	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		_build_menu()
		return

	var parsed = JSON.parse_string(file.get_as_text())
	file.close()

	if typeof(parsed) == TYPE_DICTIONARY:
		_registry = parsed as Dictionary

	_build_menu()


func show_at(menu_position: Vector2, world_position: Vector3) -> void:
	_world_position = world_position
	reset_size()
	popup_on_parent(Rect2i(Vector2i(menu_position.round()), Vector2i.ZERO))


func _build_menu() -> void:
	clear(true)
	_item_data_by_id.clear()
	_next_item_id = 1

	var added_group := false
	for category in _registry.keys():
		var items: Variant = _registry.get(category)
		if typeof(items) != TYPE_ARRAY:
			continue

		if added_group:
			add_separator()

		_add_group(str(category), items as Array)
		added_group = true


func _add_group(category: String, items: Array) -> void:
	add_item(category, _next_item_id)
	set_item_disabled(item_count - 1, true)
	_next_item_id += 1

	for item in items:
		if typeof(item) != TYPE_DICTIONARY:
			continue

		var item_data := item as Dictionary
		var label := str(item_data.get("label", item_data.get("id", "")))
		var command_item := str(item_data.get("id", label))
		if label == "" or command_item == "":
			continue

		var item_id := _next_item_id
		_next_item_id += 1
		_item_data_by_id[item_id] = {
			"category": category,
			"item": command_item,
		}
		add_item(label, item_id)


func _on_id_pressed(id: int) -> void:
	var item_data: Dictionary = _item_data_by_id.get(id, {})
	if item_data.is_empty():
		return

	create_command_requested.emit(
		str(item_data.get("category", "")),
		str(item_data.get("item", "")),
		_world_position
	)
