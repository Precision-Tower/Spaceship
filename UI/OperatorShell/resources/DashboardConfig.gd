extends Resource
class_name OperatorShellDashboardConfig

@export_enum("comfortable", "compact", "dense")
var terminal_density := "compact"

@export var terminal_first := true
@export var show_left_panel := true
@export var show_right_rail := false
@export var show_workspace := false

@export var show_top_bar := false
@export var show_runtime_state_bar := false

@export var show_directory_panel := false
@export var show_screens_panel := false
@export var show_commands_panel := true

@export var default_bottom_expanded := true
@export var bottom_height_collapsed := 245
@export var bottom_height_expanded := 710

@export var mission_path := "UI/Mission.yaml"

@export var default_screens := PackedStringArray([
	"Terminal",
	"Home",
	"State"
])
