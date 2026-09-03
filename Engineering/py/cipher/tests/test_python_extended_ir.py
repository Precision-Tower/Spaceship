from pathlib import Path

from Engineering.py.cipher.sources.python_source import load_python
from Engineering.py.cipher.reports.inspect import unresolved


def test_extended_python_ir(tmp_path: Path):
    source = tmp_path / "sample.py"

    source.write_text(
        '''
import math

def sample(packet, value=None):
    x = packet["radius"]

    if value is None or x <= 0:
        x += 1
    else:
        raise ValueError("bad")

    result = x if x > 2 else 2
    return result
''',
        encoding="utf-8",
    )

    document = load_python(source)

    failures = unresolved(document)

    assert failures == []
