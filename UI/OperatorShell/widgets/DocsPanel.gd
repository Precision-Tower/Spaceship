extends RefCounted
class_name OperatorShellDocsPanel

const Palette = preload("res://widgets/Palette.gd")

var host
var shell_container: VBoxContainer
var doc_tabs: TabContainer
var dirty_close_dialog: PanelContainer
var pending_close_path := ""

var open_documents := {}

func _init(owner) -> void:
	host = owner

func build() -> Control:
	shell_container = VBoxContainer.new()
	shell_container.size_flags_vertical = Control.SIZE_EXPAND_FILL
	shell_container.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	shell_container.add_theme_constant_override("separation", 8)

	var header := HBoxContainer.new()
	var title := Label.new()
	title.text = "Docs"
	title.add_theme_font_size_override("font_size", 18)
	title.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
	header.add_child(title)

	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(spacer)

	shell_container.add_child(header)

	doc_tabs = TabContainer.new()
	doc_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	doc_tabs.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	doc_tabs.custom_minimum_size = Vector2(280, 450)
	doc_tabs.tab_changed.connect(_on_tab_changed)
	shell_container.add_child(doc_tabs)

	_build_empty_placeholder()
	_setup_confirmation_dialog()

	return shell_container

func _build_empty_placeholder() -> void:
	var empty_box := VBoxContainer.new()
	empty_box.name = "EmptyPlaceholder"
	empty_box.add_theme_constant_override("separation", 12)
	empty_box.size_flags_vertical = Control.SIZE_EXPAND_FILL
	empty_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var info := RichTextLabel.new()
	info.bbcode_enabled = true
	info.size_flags_vertical = Control.SIZE_EXPAND_FILL
	info.selection_enabled = true
	info.text = "[color=#f3edf7]No Document Open[/color]\n\nSelect a file from [color=#f1d58a]Library[/color] on the right rail to open and edit documents in [color=#f1d58a]Docs[/color]."
	empty_box.add_child(info)

	doc_tabs.add_child(empty_box)
	doc_tabs.set_tab_title(0, "Docs")

func open_document(file_path: String) -> void:
	file_path = file_path.simplify_path()

	for path in open_documents.keys():
		if path == file_path:
			var doc_info: Dictionary = open_documents[path]
			var idx: int = doc_info.get("tab_index", 0)
			doc_tabs.current_tab = idx
			return

	if doc_tabs.has_node("EmptyPlaceholder"):
		var placeholder := doc_tabs.get_node("EmptyPlaceholder")
		doc_tabs.remove_child(placeholder)
		placeholder.queue_free()

	var basename := file_path.get_file()
	var doc_box := VBoxContainer.new()
	doc_box.size_flags_vertical = Control.SIZE_EXPAND_FILL
	doc_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	doc_box.add_theme_constant_override("separation", 6)

	var toolbar := HBoxContainer.new()
	toolbar.add_theme_constant_override("separation", 6)

	var save_btn := Button.new()
	save_btn.text = "Save"
	host._button(save_btn, true)
	save_btn.pressed.connect(func(): save_document(file_path))
	toolbar.add_child(save_btn)

	var close_btn := Button.new()
	close_btn.text = "Close"
	host._button(close_btn, false)
	close_btn.pressed.connect(func(): close_document(file_path))
	toolbar.add_child(close_btn)

	var path_label := Label.new()
	path_label.text = basename
	path_label.tooltip_text = file_path
	path_label.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
	path_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	toolbar.add_child(path_label)

	var status_label := Label.new()
	status_label.text = "[Clean]"
	status_label.add_theme_color_override("font_color", Palette.TEXT_DIM)
	toolbar.add_child(status_label)

	doc_box.add_child(toolbar)

	if not FileAccess.file_exists(file_path):
		var err_label := RichTextLabel.new()
		err_label.text = "Error: File does not exist: " + file_path
		doc_box.add_child(err_label)
		_add_doc_tab(basename, file_path, doc_box, {}, false)
		return

	var file := FileAccess.open(file_path, FileAccess.READ)
	if file == null:
		var err_label := RichTextLabel.new()
		err_label.text = "Error opening file: " + file_path
		doc_box.add_child(err_label)
		_add_doc_tab(basename, file_path, doc_box, {}, false)
		return

	var buffer := file.get_buffer(file.get_length())
	file.close()

	var is_binary := _is_binary_buffer(buffer)
	var line_ending := "\n"
	var text_content := ""

	if is_binary:
		var bin_label := RichTextLabel.new()
		bin_label.bbcode_enabled = true
		bin_label.selection_enabled = true
		bin_label.text = "[color=#f1d58a]Binary File[/color]\n\nPath: " + file_path + "\nSize: " + str(buffer.size()) + " bytes\n\n[color=#b8aebe]Editing disabled for binary files to prevent corruption.[/color]"
		doc_box.add_child(bin_label)
		save_btn.disabled = true
	else:
		text_content = buffer.get_string_from_utf8()
		if "\r\n" in text_content:
			line_ending = "\r\n"

		var editor := TextEdit.new()
		editor.size_flags_vertical = Control.SIZE_EXPAND_FILL
		editor.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		editor.text = text_content
		editor.custom_minimum_size = Vector2(0, 350)
		editor.text_changed.connect(func(): _on_text_changed(file_path))
		doc_box.add_child(editor)

	_add_doc_tab(basename, file_path, doc_box, {
		"path": file_path,
		"basename": basename,
		"is_dirty": false,
		"line_ending": line_ending,
		"is_binary": is_binary,
		"status_label": status_label,
		"editor": doc_box.find_child("*TextEdit*", true, false) if not is_binary else null
	}, true)

func _is_binary_buffer(buffer: PackedByteArray) -> bool:
	var check_len: int = mini(1024, buffer.size())
	for i in range(check_len):
		if buffer[i] == 0:
			return true
	return false

func _add_doc_tab(title: String, file_path: String, container: Control, doc_info: Dictionary, valid: bool) -> void:
	container.name = title
	doc_tabs.add_child(container)
	var new_index := doc_tabs.get_tab_count() - 1
	doc_tabs.set_tab_title(new_index, title)
	doc_tabs.set_tab_tooltip(new_index, file_path)
	doc_tabs.current_tab = new_index

	if valid:
		doc_info["tab_index"] = new_index
		open_documents[file_path] = doc_info

func _on_text_changed(file_path: String) -> void:
	if not open_documents.has(file_path):
		return
	var doc_info: Dictionary = open_documents[file_path]
	if not doc_info.get("is_dirty", false):
		doc_info["is_dirty"] = true
		var idx: int = doc_info.get("tab_index", 0)
		var title: String = doc_info.get("basename", "") + " *"
		doc_tabs.set_tab_title(idx, title)
		var status_label: Label = doc_info.get("status_label", null)
		if status_label:
			status_label.text = "[Modified]"
			status_label.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)

func save_document(file_path: String) -> bool:
	if not open_documents.has(file_path):
		return false
	var doc_info: Dictionary = open_documents[file_path]
	if doc_info.get("is_binary", false):
		return false

	var editor: TextEdit = doc_info.get("editor", null)
	if editor == null:
		return false

	var text := editor.text
	var line_ending: String = doc_info.get("line_ending", "\n")
	if line_ending == "\r\n":
		text = text.replace("\r\n", "\n").replace("\n", "\r\n")

	var file := FileAccess.open(file_path, FileAccess.WRITE)
	if file == null:
		push_error("Failed to save file: " + file_path)
		return false

	file.store_string(text)
	file.close()

	doc_info["is_dirty"] = false
	var idx: int = doc_info.get("tab_index", 0)
	var title: String = doc_info.get("basename", "")
	doc_tabs.set_tab_title(idx, title)

	var status_label: Label = doc_info.get("status_label", null)
	if status_label:
		status_label.text = "[Saved]"
		status_label.add_theme_color_override("font_color", Palette.TEXT_DIM)

	return true

func close_document(file_path: String) -> void:
	if not open_documents.has(file_path):
		return
	var doc_info: Dictionary = open_documents[file_path]
	var is_dirty: bool = doc_info.get("is_dirty", false)
	if is_dirty:
		_prompt_dirty_close(file_path)
	else:
		_force_close_document(file_path)

func _force_close_document(file_path: String) -> void:
	if not open_documents.has(file_path):
		return
	var doc_info: Dictionary = open_documents[file_path]
	var idx: int = doc_info.get("tab_index", 0)

	if idx < doc_tabs.get_tab_count():
		var child := doc_tabs.get_child(idx)
		doc_tabs.remove_child(child)
		child.queue_free()

	open_documents.erase(file_path)
	_reindex_tabs()

	if open_documents.size() == 0:
		_build_empty_placeholder()

func _reindex_tabs() -> void:
	for path in open_documents.keys():
		var doc_info: Dictionary = open_documents[path]
		for i in doc_tabs.get_tab_count():
			var child := doc_tabs.get_child(i)
			if child.name == doc_info.get("basename", ""):
				doc_info["tab_index"] = i

func _setup_confirmation_dialog() -> void:
	dirty_close_dialog = PanelContainer.new()
	dirty_close_dialog.visible = false
	host._panel(dirty_close_dialog, Palette.PLUM_CARD, Palette.GOLD_BRIGHT, 2, 12)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)

	var lbl := Label.new()
	lbl.text = "Unsaved Changes"
	lbl.add_theme_color_override("font_color", Palette.GOLD_BRIGHT)
	box.add_child(lbl)

	var msg := Label.new()
	msg.text = "This document has unsaved changes. Save before closing?"
	msg.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	box.add_child(msg)

	var btn_row := HBoxContainer.new()
	btn_row.add_theme_constant_override("separation", 8)

	var save_close_btn := Button.new()
	save_close_btn.text = "Save & Close"
	host._button(save_close_btn, true)
	save_close_btn.pressed.connect(_on_confirm_save_close)
	btn_row.add_child(save_close_btn)

	var discard_btn := Button.new()
	discard_btn.text = "Discard"
	host._button(discard_btn, false)
	discard_btn.pressed.connect(_on_confirm_discard_close)
	btn_row.add_child(discard_btn)

	var cancel_btn := Button.new()
	cancel_btn.text = "Cancel"
	host._button(cancel_btn, false)
	cancel_btn.pressed.connect(_on_confirm_cancel_close)
	btn_row.add_child(cancel_btn)

	box.add_child(btn_row)
	dirty_close_dialog.add_child(box)
	shell_container.add_child(dirty_close_dialog)

func _prompt_dirty_close(file_path: String) -> void:
	pending_close_path = file_path
	dirty_close_dialog.visible = true

func _on_confirm_save_close() -> void:
	dirty_close_dialog.visible = false
	if pending_close_path != "":
		save_document(pending_close_path)
		_force_close_document(pending_close_path)
		pending_close_path = ""

func _on_confirm_discard_close() -> void:
	dirty_close_dialog.visible = false
	if pending_close_path != "":
		_force_close_document(pending_close_path)
		pending_close_path = ""

func _on_confirm_cancel_close() -> void:
	dirty_close_dialog.visible = false
	pending_close_path = ""

func _on_tab_changed(tab_idx: int) -> void:
	for path in open_documents.keys():
		var doc_info: Dictionary = open_documents[path]
		if doc_info.get("tab_index", -1) == tab_idx:
			host._render_current_status()
			break
