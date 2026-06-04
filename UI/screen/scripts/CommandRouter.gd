class_name CommandRouter

var cli_bridge
var last_proposal_intent: String = ""

func _init(cli_bridge_ref) -> void:
	cli_bridge = cli_bridge_ref

func core_root() -> String:
	return cli_bridge.core_root()

func dashboard_root() -> String:
	return cli_bridge.dashboard_root()

func runtime_state() -> Dictionary:
	return cli_bridge.runtime_state()

func test_all() -> Dictionary:
	return cli_bridge.test_all()

func scan_core() -> Dictionary:
	return cli_bridge.scan_core()

func git_status_core() -> Dictionary:
	return cli_bridge.git_status_core()

func cali_observe_directory() -> Dictionary:
	return cli_bridge.cali_observe_directory()

func propose_directory_diff_core() -> Dictionary:
	return cli_bridge.propose_directory_diff_core()

func view_latest_diff() -> Dictionary:
	return cli_bridge.view_latest_diff()

func grant_review_latest_diff() -> Dictionary:
	return cli_bridge.grant_review_latest_diff()

func clear_latest_diff() -> Dictionary:
	return cli_bridge.clear_latest_diff()

func list_packets() -> Dictionary:
	return cli_bridge.list_packets()

func create_packet_stub() -> Dictionary:
	return cli_bridge.create_packet_stub()

func debug_paths() -> String:
	return cli_bridge.debug_paths()

func propose_task_packet(intent: String) -> Dictionary:
	last_proposal_intent = intent
	return cli_bridge.propose_task_packet(intent)

func approve_task(scope: String = "Dashboard/") -> Dictionary:
	return cli_bridge.propose_diff(last_proposal_intent, scope)

func gemini_analyze(purpose: String, context: String) -> Dictionary:
	return cli_bridge.gemini_analyze(purpose, context)
