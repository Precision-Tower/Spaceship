import json
from pathlib import Path

from Engineering.py.cipher.emit.qps_emitter import emit_qps
from Engineering.py.cipher.sources.json_source import load_json


def test_json_to_qps(tmp_path: Path):
    source = tmp_path / "pipe.json"

    source.write_text(
        json.dumps({
            "pipe": {
                "outer_diameter": 50,
                "inner_diameter": 40,
                "material": "PVC",
            }
        }),
        encoding="utf-8",
    )

    document = load_json(source)
    qps = emit_qps(document)

    assert "pipe: (" in qps
    assert "outer_diameter- 50;" in qps
    assert "inner_diameter- 40;" in qps
    assert 'material- "PVC"/a;' in qps
