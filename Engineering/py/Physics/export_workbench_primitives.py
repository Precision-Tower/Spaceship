from __future__ import annotations

import json
import sys
from pathlib import Path


DASHBOARD_ROOT = Path(__file__).resolve().parents[2]

if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

from Engineering.py.Physics.primitive_registry import workbench_primitive_registry


OUTPUT_PATH = Path(__file__).resolve().with_name("workbench_primitives.json")


def export_workbench_primitives(output_path: Path = OUTPUT_PATH) -> Path:
    registry = workbench_primitive_registry()
    output_path.write_text(
        json.dumps(registry, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    output_path = export_workbench_primitives()
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
