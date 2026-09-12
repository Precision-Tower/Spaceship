extends Control
class_name OperatorShellSurfaceCanvas

var texture_rect: TextureRect
var background_path: String = "res://assets/background.jpg"
var anchors: Dictionary = {}

func _ready() -> void:
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	size_flags_vertical = Control.SIZE_EXPAND_FILL

	texture_rect = TextureRect.new()
	texture_rect.anchor_left = 0
	texture_rect.anchor_right = 1
	texture_rect.anchor_top = 0
	texture_rect.anchor_bottom = 1
	texture_rect.offset_top = float(_tab_bar_height())
	texture_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	texture_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	texture_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE

	var abs_path := ProjectSettings.globalize_path(background_path)
	if FileAccess.file_exists(abs_path):
		var img := Image.new()
		var err := img.load(abs_path)
		if err == OK:
			texture_rect.texture = ImageTexture.create_from_image(img)
			print("[SurfaceCanvas] loaded ", abs_path)
		else:
			push_warning("[SurfaceCanvas] failed to load " + abs_path + " err=" + str(err))
	else:
		push_warning("[SurfaceCanvas] missing " + abs_path)
	add_child(texture_rect)
	call_deferred("_dump_state")

func _tab_bar_height() -> int:
	var p := get_parent()
	if p is TabContainer:
		var tc := p as TabContainer
		var tb: TabBar = tc.get_tab_bar()
		if tb:
			return int(tb.size.y)
	return 0

func _dump_state() -> void:
	print("[SurfaceCanvasState] self=", int(size.x), "x", int(size.y),
		" tab_bar_h=", _tab_bar_height(),
		" content_rect=", content_rect())

var cr := content_rect()
var ws := DisplayServer.window_get_size()
var ss := DisplayServer.screen_get_size()
print("[SurfaceCanvasScreen] window=", ws.x, "x", ws.y,
" screen=", ss.x, "x", ss.y,
" cr=", cr)

func content_rect() -> Rect2:
	if not is_inside_tree():
		return Rect2()
	var base := get_global_rect()
	var h := _tab_bar_height()
	base.position.y += float(h)
	base.size.y = max(1.0, base.size.y - float(h))
	return base

func add_anchor(name: String, normalized_rect: Rect2) -> void:
	anchors[name] = normalized_rect

func anchor_rect(name: String) -> Rect2:
	if not anchors.has(name):
		return Rect2()
	var base := content_rect()
	var rel: Rect2 = anchors[name]
	return Rect2(
		base.position.x + rel.position.x * base.size.x,
		base.position.y + rel.position.y * base.size.y,
		rel.size.x * base.size.x,
		rel.size.y * base.size.y
	)