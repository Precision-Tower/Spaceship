from pathlib import Path

from Engineering.py.cipher.sources.python_source import load_python
from Engineering.py.cipher.reports.inspect import unresolved


def test_python_list_comprehension(tmp_path: Path):
    source = tmp_path / "ports.py"

    source.write_text(
        '''
def get_open_ports(ports):
    return [
        port
        for port in ports
        if port["state"] == "open"
    ]
''',
        encoding="utf-8",
    )

    document = load_python(source)

    assert unresolved(document) == []
