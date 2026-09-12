extends Control
class_name OperatorShellSurfaceCanvas

var texture_rect: TextureRect
var background_path: String = "res://assets/background.jpg"
var anchors: Dictionary = {}

func _ready() -> void:
    size_flags_horizontal = Control.SIZE_EXPAND_FILL
    size_flags_vertical = Control.SIZE_EXPAND_FILL
    custom_minimum_size = Vector2(600, 400)

    texture_rect = TextureRect.new()
    texture_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
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
    resized.connect(_dump_state)
    call_deferred("_dump_state")

func _dump_state() -> void:
    if texture_rect == null:
        return
    print("[SurfaceCanvasState] self=", int(size.x), "x", int(size.y),
        " tex_rect=", int(texture_rect.size.x), "x", int(texture_rect.size.y))

func content_rect() -> Rect2:
    if not is_inside_tree():
        return Rect2()
    return get_global_rect()

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
