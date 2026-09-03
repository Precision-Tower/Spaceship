extends RefCounted
class_name OperatorShellResultRenderer

static func format_result(result: Dictionary) -> String:
	var text := ""
	text += "[color=#f1d58a]ok[/color]: " + str(result.get("ok", false)) + "\n"
	text += "[color=#f1d58a]return_code[/color]: " + str(result.get("return_code", "")) + "\n\n"

	var stdout := str(result.get("stdout", "")).strip_edges()
	var stderr := str(result.get("stderr", "")).strip_edges()

	if stdout != "":
		text += "[color=#8fca7a]stdout[/color]\n" + stdout + "\n\n"
	if stderr != "":
		text += "[color=#e05f5f]stderr[/color]\n" + stderr + "\n\n"

	text += "[color=#b8aebe]command_output != validation[/color]"
	return text

static func task_proposal(proposal: Dictionary, intent: String) -> String:
	var t := "[color=#f1d58a]CALI PROPOSED TASK PACKET[/color]\n\n"
	t += "intent: " + intent + "\n"
	t += "title: " + str(proposal.get("title", "untitled")) + "\n"
	t += "lane: " + str(proposal.get("lane", "unknown")) + "\n"
	t += "risk: " + str(proposal.get("risk", "unknown")) + "\n\n"
	t += "summary:\n" + str(proposal.get("summary", "")) + "\n\n"
	t += "[color=#b8aebe]proposal != approved diff[/color]"
	return t
