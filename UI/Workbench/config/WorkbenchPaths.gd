extends RefCounted
class_name WorkbenchPaths

const DEVELOPMENT_DEFAULT_PROJECT_PATH := "res://projects/Float/FloatProject.gd"
const CREATE_CONTEXT_MENU_REGISTRY_RESOURCE_PATH := "res://../Engineering/py/Physics/workbench_primitives.json"
const FLOAT_GHOSTLAB_PROJECT_RESOURCE_PATH := "res://../Engineering/py/Projects/Float/GhostLab/project.json"
const FLOAT_GHOSTLAB_WORKING_STATE_RESOURCE_PATH := "res://../Engineering/py/Projects/Float/GhostLab/working_state.json"
const FLOAT_WORKBENCH_SUMMARY_RESOURCE_PATH := "res://../Engineering/py/Projects/Float/workbench_summary.json"
const GHOST_COMMAND_EXPORT_RESOURCE_PATH := "res://../Engineering/py/Projects/Float/workbench_candidate_commands.json"


static func globalize(resource_path: String) -> String:
	return ProjectSettings.globalize_path(resource_path).simplify_path()


static func create_context_menu_registry_path() -> String:
	return globalize(CREATE_CONTEXT_MENU_REGISTRY_RESOURCE_PATH)


static func float_ghostlab_project_path() -> String:
	return globalize(FLOAT_GHOSTLAB_PROJECT_RESOURCE_PATH)


static func float_ghostlab_working_state_path() -> String:
	return globalize(FLOAT_GHOSTLAB_WORKING_STATE_RESOURCE_PATH)


static func float_workbench_summary_path() -> String:
	return globalize(FLOAT_WORKBENCH_SUMMARY_RESOURCE_PATH)


static func ghost_command_export_path() -> String:
	return globalize(GHOST_COMMAND_EXPORT_RESOURCE_PATH)
