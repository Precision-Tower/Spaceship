#!/usr/bin/env python3

import subprocess
import sys
import tempfile
from pathlib import Path


def run(qps, *args):
    return subprocess.run(
        [str(qps), *map(str, args)],
        text=True,
        capture_output=True,
    )


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: query_cli_test.py <qps>")

    qps = Path(sys.argv[1]).resolve()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        source = root / "probe.qps"
        source.write_text(
            "Probe.\n"
            "system: (\n"
            "shaft_torque- 10/n;\n"
            "nested: (\n"
            "speed- 20/n;\n"
            ");\n"
            ");\n"
        )

        second = root / "second.qps"
        second.write_text(
            "Second.\n"
            "shaft_torque- 30/n;\n"
        )

        items = run(qps, "qry", "item-", root)
        require(items.returncode == 0, items.stderr)
        item_lines = items.stdout.splitlines()

        require(
            len(item_lines) == 3,
            f"expected 3 Items, got {len(item_lines)}:\n{items.stdout}",
        )

        require(
            any(
                line.endswith("probe.qps.Probe.system.shaft_torque-:3")
                for line in item_lines
            ),
            f"missing canonical nested Item address:\n{items.stdout}",
        )

        require(
            any(
                line.endswith("probe.qps.Probe.system.nested.speed-:5")
                for line in item_lines
            ),
            f"missing transparent-container Item address:\n{items.stdout}",
        )

        torque = run(qps, "qry", "shaft_torque", root)
        require(torque.returncode == 0, torque.stderr)
        torque_lines = torque.stdout.splitlines()

        require(
            len(torque_lines) == 2,
            f"expected 2 shaft_torque matches:\n{torque.stdout}",
        )

        require(
            torque_lines == sorted(torque_lines),
            "qry output is not deterministic/sorted",
        )

        terms = run(qps, "qry", "term:", source)
        require(terms.returncode == 0, terms.stderr)
        require(
            any(
                line.endswith("probe.qps.Probe.system::2")
                for line in terms.stdout.splitlines()
            ),
            f"missing Term identity:\n{terms.stdout}",
        )

        keys = run(qps, "qry", "key.", source)
        require(keys.returncode == 0, keys.stderr)
        require(
            any(
                line.endswith("probe.qps.Probe.:1")
                for line in keys.stdout.splitlines()
            ),
            f"missing Key identity:\n{keys.stdout}",
        )

        executable = root / "executable.qps"
        executable.write_text(
            "-func leverage(\n"
            "f-/n;\n"
            "arm-/n;\n"
            "){\n"
            "%product: f * arm\n"
            "-return product;\n"
            "}\n"
            "\n"
            "{calculate:\n"
            "[>input]-\n"
            "%output: input * 2\n"
            "}\n"
            "\n"
            "{!drive:\n"
            "Motor: (DC = ME) = Pump: (ME = FD);\n"
            "}\n"
        )

        functions = run(qps, "qry", "-func", executable)
        require(functions.returncode == 0, functions.stderr)
        require(
            any(
                line.endswith("executable.qps.leverage:1")
                for line in functions.stdout.splitlines()
            ),
            f"missing function identity:\n{functions.stdout}",
        )

        product = run(qps, "qry", "product", executable)
        require(product.returncode == 0, product.stderr)
        require(
            any(
                line.endswith("executable.qps.leverage.product::5")
                for line in product.stdout.splitlines()
            ),
            f"missing function-body calculation:\n{product.stdout}",
        )

        output = run(qps, "qry", "output", executable)
        require(output.returncode == 0, output.stderr)
        require(
            any(
                line.endswith("executable.qps.calculate.output::11")
                for line in output.stdout.splitlines()
            ),
            f"missing execution-definition calculation:\n{output.stdout}",
        )

        supplied = run(qps, "qry", "input", executable)
        require(supplied.returncode == 0, supplied.stderr)
        require(
            any(
                line.endswith("executable.qps.calculate.input-:10")
                for line in supplied.stdout.splitlines()
            ),
            f"missing SymbolReference-target Item:\n{supplied.stdout}",
        )

        first = run(qps, "qry", "item-", root)
        second_run = run(qps, "qry", "item-", root)

        require(first.returncode == 0, first.stderr)
        require(second_run.returncode == 0, second_run.stderr)
        require(
            first.stdout == second_run.stdout,
            "repeated qry output changed",
        )

    print("qps qry CLI: PASS")


if __name__ == "__main__":
    main()
