import subprocess
from pathlib import Path

def run_git(root: Path, args: list[str]):
    proc = subprocess.run(
        ["git", *args],
        cwd=str(root),
        text=True,
        capture_output=True,
        shell=False,
    )
    return proc.returncode, proc.stdout, proc.stderr
