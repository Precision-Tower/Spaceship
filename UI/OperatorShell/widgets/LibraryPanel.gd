extends RefCounted
class_name OperatorShellLibraryPanel

const Palette = preload("res://widgets/Palette.gd")
const CliBridge = preload("res://runtime/CliBridge.gd")

var host
var panel_container: VBoxContainer
var tree: Tree
var root_path: String

func _init(owner) -> void:
	host = owner
	root_path = CliBridge.dashboard_root()

func build() -> Control:
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	panel_container = VBoxContainer.new()
	panel_container.add_theme_constant_override("separation", 8)
	panel_container.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	panel_container.size_flags_vertical = Control.SIZE_EXPAND_FILL

	var header := HBoxContainer.new()
	var label := Label.new()
	label.text = "Library"
	label.add_theme_font_size_override("font_size", 16)
	label.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
	header.add_child(label)

	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(spacer)

	var refresh_btn := Button.new()
	refresh_btn.text = "Refresh"
	host._button(refresh_btn, false)
	refresh_btn.pressed.connect(refresh_tree)
	header.add_child(refresh_btn)

	panel_container.add_child(header)

	tree = Tree.new()
	tree.columns = 1
	tree.hide_root = false
	tree.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	tree.size_flags_vertical = Control.SIZE_EXPAND_FILL
	tree.custom_minimum_size = Vector2(280, 450)
	tree.item_selected.connect(_on_item_selected)
	tree.item_collapsed.connect(_on_item_collapsed)
	panel_container.add_child(tree)

	var note := Label.new()
	note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	note.add_theme_color_override("font_color", Palette.TEXT_DIM)
	note.text = "tree_display != filesystem_authority"
	panel_container.add_child(note)

	scroll.add_child(panel_container)
	refresh_tree()
	return scroll

func refresh_tree() -> void:
	if tree == null:
		return
	tree.clear()
	root_path = CliBridge.dashboard_root()
	var root_item := tree.create_item()
	var root_name := root_path.get_file()
	if root_name == "":
		root_name = root_path
	root_item.set_text(0, root_name + "/")
	root_item.set_tooltip_text(0, root_path)
	root_item.set_metadata(0, {
		"path": root_path,
		"relative_path": ".",
		"is_dir": true,
		"label": root_name,
		"populated": false
	})
	_populate_directory(root_item, root_path, ".")

func _populate_directory(parent_item: TreeItem, dir_path: String, rel_prefix: String) -> void:
	var dir := DirAccess.open(dir_path)
	if dir == null:
		return

	var directories: Array[String] = []
	var files: Array[String] = []

	dir.list_dir_begin()
	var item_name := dir.get_next()
	while item_name != "":
		if item_name != "." and item_name != ".." and item_name != ".git":
			if dir.current_is_dir():
				directories.append(item_name)
			else:
				files.append(item_name)
		item_name = dir.get_next()
	dir.list_dir_end()

	directories.sort()
	files.sort()

	for d_name in directories:
		var d_full := dir_path.path_join(d_name)
		var d_rel := rel_prefix.path_join(d_name) if rel_prefix != "." else d_name
		var d_item := parent_item.create_child()
		d_item.set_text(0, d_name + "/")
		d_item.set_tooltip_text(0, d_rel)
		d_item.set_collapsed(true)
		d_item.set_metadata(0, {
			"path": d_full,
			"relative_path": d_rel,
			"is_dir": true,
			"label": d_name,
			"populated": false
		})

	for f_name in files:
		var f_full := dir_path.path_join(f_name)
		var f_rel := rel_prefix.path_join(f_name) if rel_prefix != "." else f_name
		var f_item := parent_item.create_child()
		f_item.set_text(0, f_name)
		f_item.set_tooltip_text(0, f_rel)
		f_item.set_metadata(0, {
			"path": f_full,
			"relative_path": f_rel,
			"is_dir": false,
			"label": f_name
		})

	var meta: Dictionary = parent_item.get_metadata(0)
	meta["populated"] = true
	parent_item.set_metadata(0, meta)

func _on_item_collapsed(item: TreeItem) -> void:
	if item == null or item.is_collapsed():
		return
	var meta: Dictionary = item.get_metadata(0)
	if meta.get("is_dir", false) and not meta.get("populated", false):
		var path: String = meta.get("path", "")
		var rel: String = meta.get("relative_path", "")
		if path != "":
			_populate_directory(item, path, rel)

func _on_item_selected() -> void:
	if tree == null:
		return
	var selected := tree.get_selected()
	if selected == null:
		return
	var meta: Dictionary = selected.get_metadata(0)
	if not meta.get("is_dir", false):
		var path: String = meta.get("path", "")
		if path != "":
			host.open_document_in_docs(path)
