#!/usr/bin/env python3

import subprocess
import sys
import tempfile
from pathlib import Path


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(cv, cwd, target, *value):
    return subprocess.run(
        [str(cv), target, *value],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def fixture_text():
    return (
        "Fixture.\n"
        "\n"
        "settings: (\n"
        "mode- \"idle\";\n"
        "count- 1/n;\n"
        "enabled- false;\n"
        "ref- [>settings.mode-];\n"
        "calc- 1/n + 2/n;\n"
        "notes- \"mode- \\\"idle\\\" appears here\";\n"
        ");\n"
        "\n"
        "other: (\n"
        "mode- \"untouched\";\n"
        ");\n"
    )


def main():
    if len(sys.argv) > 2:
        raise SystemExit("usage: cv_test.py [cv]")

    cv = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) == 2
        else Path(__file__).resolve().parents[1] / "cv"
    )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "fixture.qps"
        write(source, fixture_text())

        result = run(cv, root, "fixture.settings.mode-", '"active"')
        require(result.returncode == 0, result.stderr)
        require("CV=PASS" in result.stdout, result.stdout)
        current = source.read_text(encoding="utf-8")
        require('mode- "active";' in current, current)
        require('mode- "untouched";' in current, current)
        require('notes- "mode- \\"idle\\" appears here";' in current, current)
        require('mode- "idle";' not in current.split("other:", 1)[0], current)

        nested = root / "nested" / "operator"
        nested.mkdir(parents=True)
        result = run(cv, nested, "../../fixture.settings.count-", "42/n")
        require(result.returncode == 0, result.stderr)
        require("fixture.qps" in result.stdout, result.stdout)
        current = source.read_text(encoding="utf-8")
        require("count- 42/n;" in current, current)

        result = run(cv, root, "fixture.settings.enabled-", "true")
        require(result.returncode == 0, result.stderr)
        current = source.read_text(encoding="utf-8")
        require("enabled- true;" in current, current)

        result = run(cv, root, "fixture.settings.ref-", "[>settings.count-]")
        require(result.returncode == 0, result.stderr)
        current = source.read_text(encoding="utf-8")
        require("ref- [>settings.count-];" in current, current)

        result = run(cv, root, "fixture.settings.calc-", "5/n", "+", "7/n")
        require(result.returncode == 0, result.stderr)
        current = source.read_text(encoding="utf-8")
        require("calc- 5/n + 7/n;" in current, current)

        before_invalid = source.read_text(encoding="utf-8")
        result = run(cv, root, "fixture.settings.mode-", '"unterminated')
        require(result.returncode != 0, "invalid replacement unexpectedly succeeded")
        require("CV=FAIL" in result.stderr, result.stderr)
        after_invalid = source.read_text(encoding="utf-8")
        require(before_invalid == after_invalid, "invalid replacement mutated source")

        result = run(cv, root, "fixture.settings-", '"not an item"')
        require(result.returncode != 0, "structural non-Item target unexpectedly succeeded")

    print("qps/bin cv: PASS")


if __name__ == "__main__":
    main()
