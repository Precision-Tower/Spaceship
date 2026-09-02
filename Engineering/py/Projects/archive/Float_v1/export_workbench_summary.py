import json
from pathlib import Path
from workbench_summary import workbench_sections

OUT = Path(__file__).resolve().parent / "workbench_summary.json"

if __name__ == "__main__":
    OUT.write_text(
        json.dumps(workbench_sections(), indent=2),
        encoding="utf-8"
    )
    print(f"wrote {OUT}")