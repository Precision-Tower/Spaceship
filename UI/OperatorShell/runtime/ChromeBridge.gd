extends Node
class_name OperatorShellChromeBridge

# Positions an external X11 Chrome window to match a Godot Control's rect.
# Uses content_rect() if the target implements it, else get_global_rect().
# Clips to screen bounds so oversize Godot canvas rects never send Chrome off-screen.

var host
var target_control: Control
var chrome_window_id: int = 0
var last_rect: Rect2 = Rect2()
var poll_timer: Timer
var _visible := false

func _init(owner) -> void:
	host = owner

func setup(control: Control) -> void:
	target_control = control
	if target_control == null:
		push_warning("[ChromeBridge] no target control")
		return
	target_control.resized.connect(_on_target_resized)
	poll_timer = Timer.new()
	poll_timer.wait_time = 0.5
	poll_timer.autostart = true
	poll_timer.timeout.connect(_tick)
	add_child(poll_timer)
	_tick()

func _tick() -> void:
	if chrome_window_id == 0:
		chrome_window_id = _discover()
		if chrome_window_id > 0:
			print("[ChromeBridge] attached window=", chrome_window_id)
	if chrome_window_id > 0 and _visible:
		_sync_geometry(true)

func _on_target_resized() -> void:
	if _visible:
		_sync_geometry(false)

func _discover() -> int:
	var out := []
	var rc := OS.execute("xdotool", ["search", "--class", "Google-chrome"], out, true)
	if rc != 0 or out.is_empty():
		return 0
	var last := 0
	for chunk in out:
		for line in str(chunk).split("\n", false):
			var t := line.strip_edges()
			if t.is_valid_int():
				var id := int(t)
				if id > 0:
					last = id
	return last

func _sync_geometry(force: bool) -> void:
	if chrome_window_id == 0 or target_control == null:
		return
	if not target_control.is_inside_tree():
		return

	var rect: Rect2
	if target_control.has_method("content_rect"):
		rect = target_control.content_rect()
	else:
		rect = target_control.get_global_rect()
		var window_pos := DisplayServer.window_get_position()
		rect.position += Vector2(window_pos)

	# Inset Chrome so splitter boundaries stay grabbable.
	var inset := 8.0
	rect.position.x += inset
	rect.position.y += inset
	rect.size.x -= inset * 2.0
	rect.size.y -= inset * 2.0

	var screen_size := DisplayServer.screen_get_size()
	var max_w := float(screen_size.x) - rect.position.x
	var max_h := float(screen_size.y) - rect.position.y
	rect.size.x = min(rect.size.x, max_w)
	rect.size.y = min(rect.size.y, max_h)

	if rect.size.x < 20 or rect.size.y < 20:
		return
	if not force and rect == last_rect:
		return
	last_rect = rect

	OS.execute("xdotool", ["windowmove", str(chrome_window_id), str(int(rect.position.x)), str(int(rect.position.y))], [], true)
	OS.execute("xdotool", ["windowsize", str(chrome_window_id), str(int(rect.size.x)), str(int(rect.size.y))], [], true)
	OS.execute("xdotool", ["windowraise", str(chrome_window_id)], [], true)
	OS.execute("wmctrl", ["-i", "-r", str(chrome_window_id), "-b", "add,above"], [], true)
	print("[ChromeBridge] pos=", int(rect.position.x), ",", int(rect.position.y), " size=", int(rect.size.x), "x", int(rect.size.y))

func Show(control: Control) -> void:
	if control == null:
		return
	if target_control != control:
		if target_control != null and is_instance_valid(target_control) \
				and target_control.resized.is_connected(_on_target_resized):
			target_control.resized.disconnect(_on_target_resized)
		target_control = control
		if not target_control.resized.is_connected(_on_target_resized):
			target_control.resized.connect(_on_target_resized)
	_visible = true
	_sync_geometry(true)

func Hide() -> void:
	_visible = false
	if chrome_window_id == 0:
		return
	OS.execute("wmctrl", ["-i", "-r", str(chrome_window_id), "-b", "remove,above"], [], true)
	OS.execute("xdotool", ["windowmove", str(chrome_window_id), "-10000", "-10000"], [], true)

func IsVisible() -> bool:
	return _visible

func IsRunning() -> bool:
	var out := []
	var home := OS.get_environment("HOME")
	var profile := home + "/local/chrome-profile"
	var rc := OS.execute("pgrep", ["-f", "^/opt/google/chrome/chrome .*--user-data-dir=" + profile], out, true)
	return rc == 0

func Open() -> void:
	chrome_window_id = _discover()

func Close() -> void:
	_visible = false
	var home := OS.get_environment("HOME")
	var profile := home + "/local/chrome-profile"
	OS.execute("pkill", ["-f", "^/opt/google/chrome/chrome .*--user-data-dir=" + profile], [], true)
	chrome_window_id = 0
