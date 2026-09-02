from __future__ import annotations

import json
from typing import Any


class YAMLError(ValueError):
    """Minimal fallback error compatible with the PyYAML name."""


def _read_text(stream: Any) -> str:
    if stream is None:
        return ""
    if hasattr(stream, "read"):
        return stream.read()
    return str(stream)


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"", "null", "None", "~"}:
        return None
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _yaml_lines(text: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        lines.append((indent, raw.strip()))
    return lines


def _parse_block(lines: list[tuple[int, str]], index: int, indent: int):
    if index >= len(lines):
        return None, index
    if lines[index][1].startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_mapping(lines, index, indent)


def _parse_mapping(lines: list[tuple[int, str]], index: int, indent: int):
    data: dict[str, Any] = {}
    while index < len(lines):
        line_indent, content = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise YAMLError(f"Unexpected indentation near: {content}")
        if content.startswith("- "):
            break

        key, separator, value = content.partition(":")
        if not separator:
            raise YAMLError(f"Expected key/value entry near: {content}")

        key = key.strip()
        value = value.strip()
        index += 1

        if value:
            data[key] = _parse_scalar(value)
            continue

        if index < len(lines) and lines[index][0] > line_indent:
            data[key], index = _parse_block(lines, index, lines[index][0])
        else:
            data[key] = None

    return data, index


def _parse_inline_mapping(item: str) -> dict[str, Any] | None:
    key, separator, value = item.partition(":")
    if not separator:
        return None
    return {key.strip(): _parse_scalar(value.strip()) if value.strip() else None}


def _parse_list(lines: list[tuple[int, str]], index: int, indent: int):
    data: list[Any] = []
    while index < len(lines):
        line_indent, content = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise YAMLError(f"Unexpected indentation near: {content}")
        if not content.startswith("- "):
            break

        item = content[2:].strip()
        index += 1

        if item:
            inline_mapping = _parse_inline_mapping(item)
            if inline_mapping is not None:
                if index < len(lines) and lines[index][0] > line_indent:
                    child, index = _parse_block(lines, index, lines[index][0])
                    if isinstance(child, dict):
                        inline_mapping.update(child)
                data.append(inline_mapping)
            else:
                data.append(_parse_scalar(item))
            continue

        if index < len(lines) and lines[index][0] > line_indent:
            child, index = _parse_block(lines, index, lines[index][0])
            data.append(child)
        else:
            data.append(None)

    return data, index


def safe_load(stream: Any) -> Any:
    text = _read_text(stream).strip()
    if not text:
        return None

    if text[0] in "[{":
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    lines = _yaml_lines(text)
    if not lines:
        return None

    data, index = _parse_block(lines, 0, lines[0][0])
    if index != len(lines):
        raise YAMLError("Could not parse complete YAML document.")
    return data


def _format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)

    text = str(value)
    if (
        text == ""
        or text.strip() != text
        or any(token in text for token in [": ", "#", "\n", "[", "]", "{", "}"])
        or text.lower() in {"null", "true", "false"}
    ):
        return json.dumps(text)
    return text


def _dump_lines(data: Any, indent: int, sort_keys: bool) -> list[str]:
    prefix = " " * indent
    if isinstance(data, dict):
        keys = sorted(data.keys()) if sort_keys else list(data.keys())
        lines: list[str] = []
        for key in keys:
            value = data[key]
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.extend(_dump_lines(value, indent + 2, sort_keys))
            else:
                lines.append(f"{prefix}{key}: {_format_scalar(value)}")
        return lines

    if isinstance(data, list):
        lines = []
        for value in data:
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}-")
                lines.extend(_dump_lines(value, indent + 2, sort_keys))
            else:
                lines.append(f"{prefix}- {_format_scalar(value)}")
        return lines

    return [f"{prefix}{_format_scalar(data)}"]


def safe_dump(
    data: Any,
    stream: Any = None,
    sort_keys: bool = True,
    default_flow_style: bool | None = None,
) -> str | None:
    del default_flow_style
    text = "\n".join(_dump_lines(data, 0, sort_keys)) + "\n"
    if stream is not None:
        stream.write(text)
        return None
    return text
