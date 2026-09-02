from __future__ import annotations

from pathlib import Path

from Agency.Core.work.missions.operations.io import ROOT, stable_relative_path

PLAYGROUND_ROOT = ROOT / "UI" / "godot" / "playground"
BLOCKED_FILES = [
    "UI/godot/screen/",
    "existing .gd files outside UI/godot/playground/",
    "Agency/Agents/*/memory/Chroma/",
    "Agency/Agents/*/work/pressure_lab/",
]

PROJECT_GODOT = """; Engine configuration file.
; This sandbox is isolated from the main Godot runtime project.

config_version=5

[application]

config/name="Task Playground Sandbox"
run/main_scene="res://scenes/Main.tscn"
config/features=PackedStringArray("4.0")
config/icon=""
"""

TASK_011_SCENE = """[gd_scene load_steps=4 format=3 uid="uid://playground_sandbox_main"]

[ext_resource type="Script" path="res://scripts/Main.gd" id="1_main"]

[sub_resource type="BoxMesh" id="BoxMesh_playground"]
size = Vector3(1.5, 1.5, 1.5)

[sub_resource type="StandardMaterial3D" id="StandardMaterial3D_playground"]
albedo_color = Color(0.2, 0.62, 0.95, 1)
roughness = 0.42

[node name="Main" type="Node3D"]
script = ExtResource("1_main")

[node name="Cube" type="MeshInstance3D" parent="."]
mesh = SubResource("BoxMesh_playground")
surface_material_override/0 = SubResource("StandardMaterial3D_playground")

[node name="Camera3D" type="Camera3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 0.906308, 0.422618, 0, -0.422618, 0.906308, 0, 2.2, 5)
current = true

[node name="DirectionalLight3D" type="DirectionalLight3D" parent="."]
transform = Transform3D(0.707107, -0.353553, 0.612372, 0, 0.866025, 0.5, -0.707107, -0.353553, 0.612372, 0, 3, 2)
light_energy = 1.5

[node name="Overlay" type="CanvasLayer" parent="."]

[node name="Label" type="Label" parent="Overlay"]
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
offset_left = 24.0
offset_top = 24.0
offset_right = -24.0
offset_bottom = -24.0
theme_override_font_sizes/font_size = 26
text = "PLAYGROUND_SANDBOX\\ngenerated_by_task_runner\\ndisplay_not_validation"
vertical_alignment = 1
"""

TASK_011_SCRIPT = """extends Node3D

@onready var cube: MeshInstance3D = $Cube


func _process(delta: float) -> void:
    cube.rotate_y(delta * 0.7)
    cube.rotate_x(delta * 0.25)
"""

TASK_012_SCENE = """[gd_scene load_steps=5 format=3 uid="uid://playground_interaction_main"]

[ext_resource type="Script" path="res://scripts/Main.gd" id="1_main"]

[sub_resource type="BoxMesh" id="BoxMesh_playground"]
size = Vector3(1.5, 1.5, 1.5)

[sub_resource type="StandardMaterial3D" id="StandardMaterial3D_playground"]
albedo_color = Color(0.2, 0.62, 0.95, 1)
roughness = 0.42

[sub_resource type="BoxShape3D" id="BoxShape3D_playground"]
size = Vector3(1.5, 1.5, 1.5)

[node name="Main" type="Node3D"]
script = ExtResource("1_main")

[node name="Cube" type="StaticBody3D" parent="."]

[node name="Mesh" type="MeshInstance3D" parent="Cube"]
mesh = SubResource("BoxMesh_playground")
surface_material_override/0 = SubResource("StandardMaterial3D_playground")

[node name="CollisionShape3D" type="CollisionShape3D" parent="Cube"]
shape = SubResource("BoxShape3D_playground")

[node name="Camera3D" type="Camera3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 0.906308, 0.422618, 0, -0.422618, 0.906308, 0, 2.2, 5)
current = true

[node name="DirectionalLight3D" type="DirectionalLight3D" parent="."]
transform = Transform3D(0.707107, -0.353553, 0.612372, 0, 0.866025, 0.5, -0.707107, -0.353553, 0.612372, 0, 3, 2)
light_energy = 1.5

[node name="Overlay" type="CanvasLayer" parent="."]

[node name="Label" type="Label" parent="Overlay"]
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
offset_left = 24.0
offset_top = 24.0
offset_right = -24.0
offset_bottom = -24.0
theme_override_font_sizes/font_size = 26
text = "PLAYGROUND_INTERACTION_TEST\\nclick_cube_changes_color\\ndisplay_not_validation"
mouse_filter = 2
vertical_alignment = 1
"""

TASK_012_SCRIPT = """extends Node3D

const CUBE_COLORS: Array[Color] = [
    Color(0.2, 0.62, 0.95),
    Color(0.98, 0.42, 0.32),
    Color(0.38, 0.78, 0.45),
    Color(0.95, 0.75, 0.28),
]

@onready var cube: StaticBody3D = $Cube
@onready var cube_mesh: MeshInstance3D = $Cube/Mesh
@onready var camera: Camera3D = $Camera3D

var color_index := 0
var cube_material := StandardMaterial3D.new()


func _ready() -> void:
    var source_material := cube_mesh.get_surface_override_material(0)
    if source_material is StandardMaterial3D:
        cube_material = source_material.duplicate() as StandardMaterial3D
    cube_mesh.set_surface_override_material(0, cube_material)
    _apply_cube_color()


func _process(delta: float) -> void:
    cube.rotate_y(delta * 0.7)
    cube.rotate_x(delta * 0.25)


func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventMouseButton:
        var mouse_event := event as InputEventMouseButton
        if mouse_event.button_index == MOUSE_BUTTON_LEFT and mouse_event.pressed:
            if _screen_point_hits_cube(mouse_event.position):
                _cycle_cube_color()
                get_viewport().set_input_as_handled()


func _screen_point_hits_cube(screen_position: Vector2) -> bool:
    var from := camera.project_ray_origin(screen_position)
    var to := from + camera.project_ray_normal(screen_position) * 1000.0
    var query := PhysicsRayQueryParameters3D.create(from, to)
    query.collide_with_bodies = true
    query.collide_with_areas = false
    var hit := get_world_3d().direct_space_state.intersect_ray(query)
    return hit.get("collider") == cube


func _cycle_cube_color() -> void:
    color_index = (color_index + 1) % CUBE_COLORS.size()
    _apply_cube_color()


func _apply_cube_color() -> void:
    cube_material.albedo_color = CUBE_COLORS[color_index]
"""


def execute_task_011(task_packet: dict) -> dict:
    return build_playground(
        task_packet,
        scene=TASK_011_SCENE,
        script=TASK_011_SCRIPT,
        required_markers=[
            "PLAYGROUND_SANDBOX",
            "generated_by_task_runner",
            "display_not_validation",
        ],
        missing_reason="missing_visible_text",
    )


def execute_task_012(task_packet: dict) -> dict:
    return build_playground(
        task_packet,
        scene=TASK_012_SCENE,
        script=TASK_012_SCRIPT,
        required_markers=[
            "PLAYGROUND_INTERACTION_TEST",
            "click_cube_changes_color",
            "display_not_validation",
            "_unhandled_input",
            "intersect_ray",
            "albedo_color",
        ],
        missing_reason="missing_interaction_marker",
    )

TASK_013_SCENE = """[gd_scene load_steps=5 format=3 uid="uid://playground_spawn_main"]

[ext_resource type="Script" path="res://scripts/Main.gd" id="1_main"]

[sub_resource type="BoxMesh" id="BoxMesh_playground"]
size = Vector3(1.5, 1.5, 1.5)

[sub_resource type="StandardMaterial3D" id="StandardMaterial3D_playground"]
albedo_color = Color(0.2, 0.62, 0.95, 1)
roughness = 0.42

[sub_resource type="BoxShape3D" id="BoxShape3D_playground"]
size = Vector3(1.5, 1.5, 1.5)

[node name="Main" type="Node3D"]
script = ExtResource("1_main")

[node name="Cube" type="StaticBody3D" parent="."]

[node name="Mesh" type="MeshInstance3D" parent="Cube"]
mesh = SubResource("BoxMesh_playground")
surface_material_override/0 = SubResource("StandardMaterial3D_playground")

[node name="CollisionShape3D" type="CollisionShape3D" parent="Cube"]
shape = SubResource("BoxShape3D_playground")

[node name="SpawnRoot" type="Node3D" parent="."]

[node name="Camera3D" type="Camera3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 0.906308, 0.422618, 0, -0.422618, 0.906308, 0, 2.2, 5)
current = true

[node name="DirectionalLight3D" type="DirectionalLight3D" parent="."]
transform = Transform3D(0.707107, -0.353553, 0.612372, 0, 0.866025, 0.5, -0.707107, -0.353553, 0.612372, 0, 3, 2)
light_energy = 1.5

[node name="Overlay" type="CanvasLayer" parent="."]

[node name="Label" type="Label" parent="Overlay"]
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
offset_left = 24.0
offset_top = 24.0
offset_right = -24.0
offset_bottom = -24.0
theme_override_font_sizes/font_size = 26
text = "PLAYGROUND_SPAWN_TEST\\npress_space_to_spawn\\nspawn_count: 0\\ndisplay_not_validation"
mouse_filter = 2
vertical_alignment = 1
"""

TASK_013_SCRIPT = """extends Node3D

const SPAWN_COLORS: Array[Color] = [
    Color(0.98, 0.42, 0.32),
    Color(0.38, 0.78, 0.45),
    Color(0.95, 0.75, 0.28),
    Color(0.75, 0.45, 0.95),
]

@onready var cube: StaticBody3D = $Cube
@onready var spawn_root: Node3D = $SpawnRoot
@onready var label: Label = $Overlay/Label

var spawn_count := 0


func _ready() -> void:
    _update_label()


func _process(delta: float) -> void:
    cube.rotate_y(delta * 0.7)
    cube.rotate_x(delta * 0.25)

    for spawned in spawn_root.get_children():
        if spawned is Node3D:
            spawned.rotate_y(delta * 0.9)


func _unhandled_input(event: InputEvent) -> void:
    if event.is_action_pressed("ui_accept"):
        _spawn_object()
        get_viewport().set_input_as_handled()


func _spawn_object() -> void:
    spawn_count += 1

    var mesh_instance := MeshInstance3D.new()
    mesh_instance.name = "SpawnedCube_%03d" % spawn_count

    var mesh := BoxMesh.new()
    mesh.size = Vector3(0.6, 0.6, 0.6)
    mesh_instance.mesh = mesh

    var material := StandardMaterial3D.new()
    material.albedo_color = SPAWN_COLORS[(spawn_count - 1) % SPAWN_COLORS.size()]
    mesh_instance.set_surface_override_material(0, material)

    var column := (spawn_count - 1) % 5
    var row := int((spawn_count - 1) / 5)
    mesh_instance.position = Vector3(-2.0 + column, 0.0, -1.5 - row)

    spawn_root.add_child(mesh_instance)
    _update_label()


func _update_label() -> void:
    label.text = "PLAYGROUND_SPAWN_TEST\\npress_space_to_spawn\\nspawn_count: %d\\ndisplay_not_validation" % spawn_count
"""
def execute_task_013(task_packet: dict) -> dict:
    return build_playground(
        task_packet,
        scene=TASK_013_SCENE,
        script=TASK_013_SCRIPT,
        required_markers=[
            "PLAYGROUND_SPAWN_TEST",
            "press_space_to_spawn",
            "spawn_count",
            "display_not_validation",
            "_spawn_object",
            "add_child",
        ],
        missing_reason="missing_spawn_marker",
    )

def build_playground(
    task_packet: dict,
    scene: str,
    script: str,
    required_markers: list[str],
    missing_reason: str,
) -> dict:
    target_root = task_packet.get("target_root", "UI/godot/playground")
    sandbox_root = (ROOT / target_root).resolve()
    allowed_root = PLAYGROUND_ROOT.resolve()

    if sandbox_root != allowed_root:
        return {
            "status": "fail",
            "reason": "target_root_outside_playground",
            "files_written": [],
            "returncode": 2,
        }

    files = {
        sandbox_root / "project.godot": PROJECT_GODOT,
        sandbox_root / "scenes" / "Main.tscn": scene,
        sandbox_root / "scripts" / "Main.gd": script,
    }

    files_written = []
    for path, contents in files.items():
        if not is_inside(path, allowed_root):
            return {
                "status": "fail",
                "reason": f"blocked_write_outside_playground: {stable_relative_path(path)}",
                "files_written": files_written,
                "returncode": 3,
            }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
        files_written.append(stable_relative_path(path))

    combined_text = "\n".join(path.read_text(encoding="utf-8") for path in files)
    missing = [marker for marker in required_markers if marker not in combined_text]

    if missing:
        return {
            "status": "fail",
            "reason": f"{missing_reason}: {', '.join(missing)}",
            "files_written": files_written,
            "returncode": 4,
        }

    return {
        "status": "pass",
        "files_written": files_written,
        "returncode": 0,
    }


def is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False
