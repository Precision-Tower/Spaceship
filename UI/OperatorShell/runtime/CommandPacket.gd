extends RefCounted
class_name OperatorShellCommandPacket

static func make(
	log_text: String,
	surface: String,
	preamble: String,
	record_name: String,
	summary_ok: String,
	summary_fail: String,
	result: Dictionary,
	refresh_state_from_output := false
) -> Dictionary:
	return {
		"log": log_text,
		"surface": surface,
		"preamble": preamble,
		"record_name": record_name,
		"summary_ok": summary_ok,
		"summary_fail": summary_fail,
		"result": result,
		"refresh_state_from_output": refresh_state_from_output
	}
