extends RefCounted
class_name OperatorShellCommandActions

const CommandPacket = preload("res://OperatorShell/runtime/CommandPacket.gd")
const CliBridge = preload("res://OperatorShell/runtime/CliBridge.gd")

static func refresh_state() -> Dictionary:
	return CommandPacket.make(
		"runtime-state requested",
		"terminal",
		"",
		"Refresh State",
		"runtime state refreshed",
		"runtime state failed",
		CliBridge.runtime_state(),
		true
	)

static func test_all() -> Dictionary:
	return {
		"log": "test-all requested",
		"surface": "terminal",
		"preamble": "Running structured validation report. Copy/paste this output back to Gear.",
		"record_name": "Test",
		"summary_ok": "structured validation report generated",
		"summary_fail": "structured validation report failed",
		"result": CliBridge.test_all()
	}

static func scan_core() -> Dictionary:
	return {
		"log": "scan-core requested",
		"surface": "terminal",
		"preamble": "Running scan-repo against Core...",
		"record_name": "Scan Core",
		"summary_ok": "Core scan executed",
		"summary_fail": "Core scan failed",
		"result": CliBridge.scan_core()
	}

static func git_status() -> Dictionary:
	return {
		"log": "git-status requested",
		"surface": "terminal",
		"preamble": "Running git status against Core...",
		"record_name": "Git Status",
		"summary_ok": "git status executed",
		"summary_fail": "git status failed",
		"result": CliBridge.git_status_core()
	}

static func cali_observe_directory() -> Dictionary:
	return {
		"log": "cali-observe-directory requested",
		"surface": "terminal",
		"preamble": "Running cali-observe-directory --max-new-tokens 1 --timeout-seconds 120...",
		"record_name": "Cali Observe Directory",
		"summary_ok": "Cali directory observation attempted",
		"summary_fail": "Cali directory observation failed",
		"result": CliBridge.cali_observe_directory()
	}

static func propose_diff() -> Dictionary:
	return {
		"log": "propose-directory-diff requested",
		"surface": "diff",
		"preamble": "Running propose-directory-diff against Core...",
		"record_name": "Propose Directory Diff",
		"summary_ok": "latest.diff proposal attempted",
		"summary_fail": "latest.diff proposal failed",
		"result": CliBridge.propose_directory_diff_core()
	}

static func view_latest_diff() -> Dictionary:
	return {
		"log": "view-latest-diff requested",
		"surface": "diff",
		"preamble": "Viewing latest.diff...",
		"record_name": "View Latest Diff",
		"summary_ok": "latest.diff display attempted",
		"summary_fail": "latest.diff display failed",
		"result": CliBridge.view_latest_diff()
	}

static func review_latest_diff() -> Dictionary:
	return {
		"log": "grant-review-latest-diff requested",
		"surface": "diff",
		"preamble": "Reviewing latest.diff...",
		"record_name": "Review Latest Diff",
		"summary_ok": "lexical review executed",
		"summary_fail": "lexical review failed",
		"result": CliBridge.grant_review_latest_diff()
	}

static func clear_latest_diff() -> Dictionary:
	return {
		"log": "clear-latest-diff requested",
		"surface": "diff",
		"preamble": "Clearing latest.diff with archive tombstone...",
		"record_name": "Clear Latest Diff",
		"summary_ok": "latest.diff clear/archive attempted",
		"summary_fail": "latest.diff clear/archive failed",
		"result": CliBridge.clear_latest_diff()
	}

static func list_packets() -> Dictionary:
	return {
		"log": "list-packets requested",
		"surface": "packets",
		"preamble": "Listing packet registry...",
		"record_name": "List Packets",
		"summary_ok": "packet listing executed",
		"summary_fail": "packet listing failed",
		"result": CliBridge.list_packets()
	}

static func create_packet_stub() -> Dictionary:
	return {
		"log": "create-packet requested",
		"surface": "packets",
		"preamble": "Creating packet stub...",
		"record_name": "Create Packet Stub",
		"summary_ok": "incoming packet stub attempted",
		"summary_fail": "incoming packet stub failed",
		"result": CliBridge.create_packet_stub()
	}
