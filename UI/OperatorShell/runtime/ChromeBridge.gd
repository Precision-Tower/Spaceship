extends Node
class_name OperatorShellChromeBridge

# Syncs an X11 Chrome window's geometry to a Godot Control's rect.
# Chrome must already be reparented as a child of the Godot X window
# (done once at launch, see ~/.xinitrc). This bridge only keeps geometry
# in sync when the user collapses/expands panels.

var host
var target_control: Control
var chrome_window_id: int = 0
var last_rect: Rect2 = Rect2()
var poll_timer: Timer

func _init(owner) -> void:
    host = owner

func setup(control: Control) -> void:
    target_control = control
    if target_control == null:
        push_warning("[ChromeBridge] no target control")
        return
    target_control.resized.connect(_on_target_resized)
    poll_timer = Timer.new()
    poll_timer.wait_time = 1.0
    poll_timer.autostart = true
    poll_timer.timeout.connect(_tick)
    add_child(poll_timer)
    _tick()

func _tick() -> void:
    if chrome_window_id == 0:
        chrome_window_id = _discover()
        if chrome_window_id > 0:
            print("[ChromeBridge] attached window=", chrome_window_id)
    if chrome_window_id > 0:
        _sync_geometry(true)

func _on_target_resized() -> void:
    _sync_geometry(false)

func _discover() -> int:
    var out := []
    var rc := OS.execute("xdotool", ["search", "--class", "Google-chrome"], out, true)
    if rc != 0 or out.is_empty():
        return 0
    # out is a chunked array; each element may contain multiple newline-separated IDs.
    # The last ID in the entire output is the most recently created window.
    var last := 0
    for chunk in out:
        for line in str(chunk).split("\n", false):
            var trimmed := line.strip_edges()
            if trimmed == "":
                continue
            if trimmed.is_valid_int():
                var id := int(trimmed)
                if id > 0:
                    last = id
    return last

func _sync_geometry(force: bool) -> void:
    if chrome_window_id == 0 or target_control == null:
        return
    if not target_control.is_inside_tree():
        return
    var rect := target_control.get_global_rect()
    if rect.size.x < 10 or rect.size.y < 10:
        return
    if not force and rect == last_rect:
        return
    last_rect = rect
    var x := int(rect.position.x)
    var y := int(rect.position.y)
    var w := int(rect.size.x)
    var h := int(rect.size.y)
    OS.execute("xdotool", ["windowmove", str(chrome_window_id), str(x), str(y)], [], true)
    OS.execute("xdotool", ["windowsize", str(chrome_window_id), str(w), str(h)], [], true)
