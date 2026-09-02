from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RETIRED_NAMESPACES = [
    "Agency.Core.editor",
    "Agency.Core.missions",
    "Agency.Core.planning",
    "Agency.Core.projects",
    "Agency.Core.agent_tools",
    "Agency.Core.cli",
    "Agency.Core.reasoning",
    "Agency.Core.memory",
]
RETIRED_IMPORT_RE = re.compile(
    r"^\s*(?:from|import)\s+(?:" + r"|".join(re.escape(ns) for ns in RETIRED_NAMESPACES) + r")(?:\b|\.)"
)


class CoreArchitectureRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        sys.path.insert(0, str(ROOT))

    def tearDown(self) -> None:
        if sys.path and sys.path[0] == str(ROOT):
            sys.path.pop(0)

    def test_root_path_authority(self) -> None:
        from Agency.Core.foundation.paths import (
            AGENCY_ROOT,
            AGENTS_ROOT,
            CORE_ROOT,
            DASHBOARD_ROOT,
        )

        self.assertEqual(DASHBOARD_ROOT, ROOT)
        self.assertEqual(AGENCY_ROOT, ROOT / "Agency")
        self.assertEqual(CORE_ROOT, ROOT / "Agency" / "Core")
        self.assertEqual(AGENTS_ROOT, ROOT / "Agency" / "Agents")

    def test_retired_paths_are_not_created(self) -> None:
        from Agency.Core.foundation import paths

        _ = paths.PathResolver()

        self.assertFalse((ROOT / "Agency" / "Agency").exists(), "Retired path exists: Agency/Agency")
        self.assertFalse((ROOT / "Agency" / "Core" / "memory").exists(), "Retired path exists: Agency/Core/memory")
        self.assertFalse((ROOT / "Agency" / "Core" / "projects").exists(), "Retired path exists: Agency/Core/projects")

    def test_direct_core_ownership_directories_exist(self) -> None:
        core_root = ROOT / "Agency" / "Core"
        for child in [
            "agents",
            "capabilities",
            "foundation",
            "interfaces",
            "knowledge",
            "repository",
            "runtime",
            "state",
            "work",
        ]:
            self.assertTrue(
                (core_root / child).is_dir(),
                f"Expected Core ownership directory not found: Agency/Core/{child}",
            )

    def test_active_work_packages_exist(self) -> None:
        work_root = ROOT / "Agency" / "Core" / "work"
        for child in ["tasks", "work_packets", "missions", "adventures"]:
            self.assertTrue(
                (work_root / child).is_dir(),
                f"Expected active work package not found: Agency/Core/work/{child}",
            )

    def test_retired_namespace_imports_are_absent(self) -> None:
        source_paths = list(self._iter_python_source())
        evidence: list[str] = []

        for path in source_paths:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                for line_number, line in enumerate(fh, start=1):
                    if RETIRED_IMPORT_RE.search(line):
                        evidence.append(f"{path.relative_to(ROOT)}:{line_number}: {line.rstrip()}")

        self.assertFalse(
            evidence,
            "Retired Core namespace imports found:\n" + "\n".join(evidence),
        )

    def _iter_python_source(self) -> list[Path]:
        paths: list[Path] = []
        root = ROOT / "Agency" / "Core"

        for path in root.rglob("*.py"):
            if any(part == "__pycache__" for part in path.parts):
                continue
            if any(part == "Archive" for part in path.parts):
                continue
            if ".bak" in path.name:
                continue
            paths.append(path)

        for path in [ROOT / "run.py"]:
            if path.exists():
                paths.append(path)

        return sorted(paths)


class CoreHelpSmokeTests(unittest.TestCase):
    def _run_help(self, args: list[str]) -> str:
        result = subprocess.run(
            [sys.executable, str(ROOT / "run.py")] + args,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"Command {' '.join(args)} failed with exit {result.returncode}: {result.stderr}",
        )
        return result.stdout

    def _assert_no_retired_namespaces(self, help_text: str) -> None:
        for ns in RETIRED_NAMESPACES:
            self.assertNotIn(ns, help_text, f"Retired namespace '{ns}' appeared in help output")

    def test_agent_help(self) -> None:
        help_text = self._run_help(["agent", "-h"])
        self.assertIn("usage: python run.py agent", help_text)
        self.assertIn("list", help_text)
        self.assertIn("<AgentName>", help_text)
        self.assertIn("Editor", help_text)
        self._assert_no_retired_namespaces(help_text)

    def test_editor_help(self) -> None:
        help_text = self._run_help(["agent", "Editor", "-h"])
        self.assertIn("Editor terminal commands:", help_text)
        self.assertIn("/status", help_text)
        self.assertIn("/tool", help_text)
        self._assert_no_retired_namespaces(help_text)

    def test_task_help(self) -> None:
        help_text = self._run_help(["task", "-h"])
        self.assertIn("usage: python run.py task", help_text)
        self.assertIn("submit", help_text)
        self.assertIn("inspect", help_text)
        self._assert_no_retired_namespaces(help_text)

    def test_work_packet_help(self) -> None:
        help_text = self._run_help(["work-packet", "-h"])
        self.assertIn("usage: python run.py work-packet", help_text)
        self.assertIn("create", help_text)
        self.assertIn("dispatch", help_text)
        self.assertIn("authorize", help_text)
        self._assert_no_retired_namespaces(help_text)

    def test_mission_help(self) -> None:
        help_text = self._run_help(["mission", "-h"])
        self.assertIn("usage: python run.py mission", help_text)
        self.assertIn("create", help_text)
        self.assertIn("inspect", help_text)
        self._assert_no_retired_namespaces(help_text)


if __name__ == "__main__":
    unittest.main()
