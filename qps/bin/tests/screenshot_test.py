#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import struct
import subprocess
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
COMMAND = ROOT / "qps" / "bin" / "qps-screenshot"
QPS = ROOT / "qps" / "cpp" / "build-pixel" / "qps"
TMP = ROOT / "trash" / "tmp" / f"qps-screenshot-test-{os.getpid()}"


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def png(path: Path, width: int = 3, height: int = 2) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    raw = b"".join(b"\x00" + b"\x00\x00\x00" * width for _ in range(height))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def run(command: Path, control: Path, curl: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CEOS_ROOT"] = str(TMP)
    env["QPS_SCREENSHOT_CONTROL"] = str(control)
    env["QPS_SCREENSHOT_CURL"] = str(curl)
    return subprocess.run(
        [str(command), "screenshot"] if command == QPS else [str(command)],
        cwd=TMP,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def main() -> None:
    shutil.rmtree(TMP, ignore_errors=True)
    (TMP / "trash" / "tmp").mkdir(parents=True)
    (TMP / "_index.qps").write_text("ROOT.\n", encoding="utf-8")

    control = TMP / "control"
    curl = TMP / "curl"

    executable(
        control,
        """#!/data/data/com.termux/files/usr/bin/bash
set -e
[[ "$1" == "operator.screenshot" ]]
python3 - "$2" <<'INNER'
import sys
from pathlib import Path
exec(compile(Path(%r).read_text(), %r, "exec"))
INNER
""" % (str(Path(__file__).resolve()), str(Path(__file__).resolve())),
    )

    # Replace recursive fixture with a minimal PNG writer executable.
    executable(
        control,
        """#!/data/data/com.termux/files/usr/bin/python3
import struct, sys, zlib
from pathlib import Path
assert sys.argv[1] == "operator.screenshot"
p=Path(sys.argv[2]); p.parent.mkdir(parents=True, exist_ok=True)
def c(k,d):
    return struct.pack(">I",len(d))+k+d+struct.pack(">I",zlib.crc32(k+d)&0xffffffff)
w,h=3,2
raw=b"".join(b"\\x00"+b"\\x00\\x00\\x00"*w for _ in range(h))
p.write_bytes(b"\\x89PNG\\r\\n\\x1a\\n"+c(b"IHDR",struct.pack(">IIBBBBB",w,h,8,2,0,0,0))+c(b"IDAT",zlib.compress(raw))+c(b"IEND",b""))
""",
    )
    executable(
        curl,
        """#!/data/data/com.termux/files/usr/bin/python3
import json
print(json.dumps({"status":"success","data":{"url":"https://tmpfiles.org/abc123/test.png"}}))
""",
    )

    result = run(COMMAND, control, curl)
    require(result.returncode == 0, result.stdout + result.stderr)
    require("SCREENSHOT=PASS" in result.stdout, result.stdout)
    require("url=https://tmpfiles.org/dl/abc123/test.png" in result.stdout, result.stdout)
    require("width=3" in result.stdout and "height=2" in result.stdout, result.stdout)
    require("exposure=temporary-public-https" in result.stdout, result.stdout)
    require(not list((TMP / "trash" / "tmp").glob("qps-screenshot-*.png")), "local screenshot was not cleaned")

    result = run(QPS, control, curl)
    require(result.returncode == 0, result.stdout + result.stderr)
    require("SCREENSHOT=PASS" in result.stdout, result.stdout)

    executable(curl, "#!/data/data/com.termux/files/usr/bin/bash\nexit 22\n")
    result = run(COMMAND, control, curl)
    require(result.returncode != 0, "failed uploader unexpectedly passed")
    require("SCREENSHOT=FAIL" in result.stderr, result.stderr)
    require("publication failed" in result.stderr, result.stderr)
    require(not list((TMP / "trash" / "tmp").glob("qps-screenshot-*.png")), "failed publication left screenshot behind")

    executable(
        control,
        "#!/data/data/com.termux/files/usr/bin/bash\nprintf 'not-png' > \"$2\"\n",
    )
    result = run(COMMAND, control, curl)
    require(result.returncode != 0, "invalid PNG unexpectedly passed")
    require("valid PNG" in result.stderr, result.stderr)
    require(not list((TMP / "trash" / "tmp").glob("qps-screenshot-*.png")), "invalid capture left screenshot behind")

    shutil.rmtree(TMP, ignore_errors=True)
    print("PASS qps screenshot")


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
