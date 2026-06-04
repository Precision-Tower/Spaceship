import re
from typing import Optional


TOOL_CALL_RE = re.compile(
    r"(?:^|\n)Thought:\s*(?P<thought>[^\n]+)\n"
    r"Action:\s*(?P<tool>execute|read_file|write_file|list_files)\((?P<args>.*)\)\s*$",
    re.DOTALL,
)

ARG_RE = re.compile(r"(\w+)=['\"](.*?)['\"]", re.DOTALL)


def parse_tool_call(response: str) -> Optional[tuple[str, dict]]:
    cleaned = response.strip()
    match = TOOL_CALL_RE.search(cleaned)

    if not match:
        return None

    tool_name = match.group("tool")
    raw_args = match.group("args")

    args = {key: value for key, value in ARG_RE.findall(raw_args)}

    if not args and raw_args.strip():
        args = {"value": raw_args.strip().strip("'\"")}

    return tool_name, args


def write_authorized(user_input: str) -> bool:
    lowered = user_input.lower()

    return any(
        token in lowered
        for token in (
            "edit ",
            "write ",
            "replace ",
            "patch ",
            "apply ",
            "modify ",
            "update the file",
            "save the file",
        )
    )


def run_tool(bridge, tool_name: str, args: dict) -> str:
    try:
        if tool_name == "execute":
            return bridge._exec(args.get("command", args.get("value", "")))

        if tool_name == "read_file":
            return bridge.read_file(args.get("path", args.get("value", "")))

        if tool_name == "write_file":
            return bridge.write_file(
                args.get("path", ""),
                args.get("content", ""),
            )

        if tool_name == "list_files":
            return bridge.list_files(args.get("path", args.get("value", ".")))

        return f"UNKNOWN_TOOL: {tool_name}"

    except Exception as e:
        return f"TOOL_ERROR: {tool_name}: {e}"


def tool_result_preview(result: str, limit: int = 1000) -> str:
    return str(result)[:limit]