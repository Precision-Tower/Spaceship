from __future__ import annotations

from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    yaml = None

from Agency.Core.foundation.paths import DASHBOARD_ROOT, WORK_ROOT

ROOT = DASHBOARD_ROOT
TASK_ROOT = WORK_ROOT / "Tasks"
ACTIVE_DIR = TASK_ROOT / "active"
RESULTS_DIR = TASK_ROOT / "results"


def load_yaml(path: str | Path) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text) or {}
    return load_basic_yaml(text)


def write_yaml(path: str | Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if yaml is not None:
        text = yaml.safe_dump(data, sort_keys=False)
    else:
        text = dump_basic_yaml(data)
    path.write_text(text, encoding="utf-8")


def get_result_path(task_id: str) -> Path:
    return RESULTS_DIR / f"{task_id}_result.yaml"


def stable_relative_path(path: str | Path) -> str:
    return Path(path).relative_to(ROOT).as_posix()


def parse_basic_scalar(value: str):
    value = value.strip()
    if value == "":
        return ""
    if value in ("true", "false"):
        return value == "true"
    if value.isdigit():
        return int(value)
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in ("'", '"')
    ):
        return value[1:-1]
    return value


def load_basic_yaml(text: str) -> dict:
    rows = [
        (len(line) - len(line.lstrip(" ")), line.strip())
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    def parse_block(index: int, indent: int):
        if index >= len(rows):
            return {}, index

        if rows[index][1].startswith("- "):
            items = []
            while index < len(rows) and rows[index][0] == indent:
                items.append(parse_basic_scalar(rows[index][1][2:]))
                index += 1
            return items, index

        values = {}
        while index < len(rows) and rows[index][0] == indent:
            _, line = rows[index]
            key, sep, value = line.partition(":")
            if not sep:
                index += 1
                continue

            key = key.strip()
            value = value.strip()
            index += 1

            if value:
                values[key] = parse_basic_scalar(value)
            elif index < len(rows) and rows[index][0] > indent:
                values[key], index = parse_block(index, rows[index][0])
            else:
                values[key] = {}

        return values, index

    parsed, _ = parse_block(0, rows[0][0] if rows else 0)
    return parsed


def format_basic_scalar(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    text = str(value)
    if text == "":
        return "''"
    return text


def dump_basic_yaml(data, indent: int = 0) -> str:
    lines = []
    prefix = " " * indent

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict | list):
                lines.append(f"{prefix}{key}:")
                lines.append(dump_basic_yaml(value, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {format_basic_scalar(value)}")
    elif isinstance(data, list):
        for value in data:
            if isinstance(value, dict):
                lines.append(f"{prefix}-")
                lines.append(dump_basic_yaml(value, indent + 2))
            else:
                lines.append(f"{prefix}- {format_basic_scalar(value)}")

    return "\n".join(line for line in lines if line != "") + ("\n" if indent == 0 else "")
