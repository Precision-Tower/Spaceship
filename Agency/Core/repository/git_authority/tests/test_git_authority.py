from __future__ import annotations

import ast
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from Agency.Core.work.tasks.editor import persistence as editor_persistence
from Agency.Core.repository.git_authority import (
    DOMAIN_AUTHORITY,
    GitAuthorityError,
    GitObservation,
    RepositoryStatusView,
    get_blob_oid,
    get_head,
    get_status,
    normalize_repo_path,
    repository_ref,
)
from Agency.Core.repository.git_authority.commands import run_git_observation
from Agency.Core.repository.git_authority.operations import operations_status
from Agency.Core.repository.git_authority.persistence_guard import GitPersistencePolicyError, guard_ceos_persistence
from Agency.Core.repository.git_authority.policy import TEMPORARY_DIRECT_GIT_EXCEPTIONS


class TempGitRepo(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        subprocess.run(["git", "init"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "ce-os@example.invalid"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "CE OS"], cwd=self.repo, check=True, capture_output=True)
        (self.repo / "tracked.txt").write_text("alpha\n", encoding="utf-8")
        subprocess.run(["git", "add", "tracked.txt"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=self.repo, check=True, capture_output=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()


class GitAuthorityBoundaryTests(TempGitRepo):
    def test_status_is_live_query_and_not_persisted_view(self) -> None:
        repo = repository_ref(self.repo)
        first = get_status(repo)
        self.assertTrue(first.clean)
        (self.repo / "tracked.txt").write_text("alpha\nbeta\n", encoding="utf-8")
        second = get_status(repo)
        self.assertFalse(second.clean)
        self.assertIn("tracked.txt", second.unstaged_paths)
        with self.assertRaises(GitPersistencePolicyError):
            guard_ceos_persistence(second.to_dict(), record_name="status-view")

    def test_missing_and_non_git_repositories_are_deterministic_errors(self) -> None:
        with self.assertRaises(GitAuthorityError) as missing:
            repository_ref(self.repo / "missing")
        self.assertEqual(missing.exception.code, "repository_missing")
        with tempfile.TemporaryDirectory() as non_git_dir:
            with self.assertRaises(GitAuthorityError) as not_git:
                repository_ref(non_git_dir)
            self.assertEqual(not_git.exception.code, "not_git_repository")

    def test_paths_are_normalized_and_repository_bounded(self) -> None:
        repo = repository_ref(self.repo)
        self.assertEqual(normalize_repo_path(repo, "tracked.txt").path, "tracked.txt")
        with self.assertRaises(GitAuthorityError):
            normalize_repo_path(repo, "../outside.txt")

    def test_oid_references_are_allowed(self) -> None:
        repo = repository_ref(self.repo)
        head = get_head(repo)
        blob = get_blob_oid(repo, "tracked.txt")
        guard_ceos_persistence({
            "commit_oid": head.oid,
            "tree_oid": head.oid,
            "blob_oid": blob.oid,
            "baseline_oid": head.oid,
            "baseline_hashes": {"tracked.txt": "abc"},
            "before_hashes": {"tracked.txt": "abc"},
            "after_hashes": {"tracked.txt": "def"},
            "proposal_sha256": "123",
        })

    def test_historical_git_observation_is_allowed_and_time_bounded(self) -> None:
        repo = repository_ref(self.repo)
        observation = run_git_observation(repo, ["status", "--short"])
        payload = observation.to_dict()
        self.assertIn("observed_at", payload)
        self.assertIn("output_sha256", payload)
        guard_ceos_persistence({"verification_results": [payload]})

    def test_mutable_git_truth_fields_are_rejected_before_persistence(self) -> None:
        bad_payloads = [
            {"current_branch": "main"},
            {"current_head": "abc"},
            {"working_tree_clean": True},
            {"repository_clean": True},
            {"staged_files": []},
            {"unstaged_files": []},
            {"untracked_files": []},
            {"changed_files": []},
            {"current_diff": "diff --git ..."},
            {"commit_history": []},
            {"merge_base": "abc"},
            {"branch_topology": {}},
            {"repository_status": {}},
        ]
        for payload in bad_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(GitPersistencePolicyError):
                    guard_ceos_persistence(payload)

    def test_editor_store_rejects_repository_cleanliness_as_current_truth(self) -> None:
        with self.assertRaises(GitPersistencePolicyError):
            editor_persistence.atomic_json(self.repo / "bad-result.json", {"repository_clean": True})

    def test_git_command_timeout_is_reported(self) -> None:
        repo = repository_ref(self.repo)
        with mock.patch("Agency.Core.repository.git_authority.commands.subprocess.run", side_effect=subprocess.TimeoutExpired(["git", "status"], 1)):
            with self.assertRaises(GitAuthorityError) as caught:
                run_git_observation(repo, ["status", "--short"], timeout=1)
        self.assertEqual(caught.exception.code, "git_command_timeout")

    def test_operations_status_projection_uses_live_git_query(self) -> None:
        observation = GitObservation.build(
            repository_id="repo",
            observed_at="2026-01-01T00:00:00Z",
            git_command=("git", "status", "--porcelain=v1"),
            git_exit_code=0,
            stdout=" M tracked.txt\n",
            stderr="",
            head_oid="abc",
        )
        fake_status = RepositoryStatusView(
            repository_id="repo",
            head_oid="abc",
            branch="main",
            detached=False,
            staged_paths=(),
            unstaged_paths=("tracked.txt",),
            untracked_paths=(),
            conflicts=(),
            clean=False,
            observation=observation,
        )
        fake_packet = {
            "packet_id": "wp-1",
            "play_owner": "Gear",
            "ball_holder": "Gear",
            "next_decision_owner": "Gear",
            "steps": [{"step_id": "s1", "status": "selected", "operation": "inspect"}],
            "unresolveds": [],
        }
        with mock.patch("Agency.Core.repository.git_authority.operations.repository_ref", return_value=mock.Mock(repository_id="repo", root_path=str(self.repo))), \
             mock.patch("Agency.Core.repository.git_authority.operations.get_status", return_value=fake_status) as get_status_mock, \
             mock.patch("Agency.Core.repository.git_authority.operations._latest_work_packet", return_value=fake_packet):
            payload = operations_status()
        self.assertEqual(payload["git_state_source"], "live_git_query")
        self.assertEqual(payload["authority"]["play_owner"], "Gear")
        self.assertEqual(payload["authority"]["current_route"], "inspect")
        self.assertFalse(payload["git"]["clean"])
        get_status_mock.assert_called_once()

    def test_canonical_authority_declaration_is_importable(self) -> None:
        self.assertEqual(DOMAIN_AUTHORITY["repository_contents"], "Git")
        self.assertEqual(DOMAIN_AUTHORITY["repository_status"], "Git")
        self.assertEqual(DOMAIN_AUTHORITY["play_direction"], "Gear")


class ArchitectureScanTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[5]

    def _production_python_files(self) -> list[Path]:
        bases = [self.ROOT / "Agency" / "Core", self.ROOT / "Agency" / "Agents", self.ROOT / "run.py"]
        files: list[Path] = []
        for base in bases:
            candidates = [base] if base.is_file() else base.rglob("*.py")
            for path in candidates:
                rel = path.relative_to(self.ROOT).as_posix()
                if "/tests/" in rel or "__pycache__" in rel:
                    continue
                if rel.startswith("Agency/Core/repository/git_authority/"):
                    continue
                files.append(path)
        return files

    def _direct_git_calls(self) -> list[tuple[str, int, str]]:
        findings: list[tuple[str, int, str]] = []
        for path in self._production_python_files():
            rel = path.relative_to(self.ROOT).as_posix()
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [alias.name for alias in getattr(node, "names", [])]
                    module = getattr(node, "module", "") or ""
                    if module == "git" or "git" in names:
                        findings.append((rel, node.lineno, "git_import"))
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                func_name = ""
                if isinstance(func, ast.Attribute):
                    func_name = func.attr
                    owner = getattr(func.value, "id", "")
                    if owner not in {"subprocess", "os"}:
                        continue
                elif isinstance(func, ast.Name):
                    func_name = func.id
                if func_name not in {"run", "Popen", "call", "check_call", "check_output", "system"}:
                    continue
                if func_name == "system":
                    if node.args and isinstance(node.args[0], ast.Constant) and "git " in str(node.args[0].value):
                        findings.append((rel, node.lineno, "os.system git"))
                    continue
                if not node.args:
                    continue
                first = node.args[0]
                if isinstance(first, (ast.List, ast.Tuple)) and first.elts:
                    head = first.elts[0]
                    if isinstance(head, ast.Constant) and head.value == "git":
                        findings.append((rel, node.lineno, "subprocess git"))
                for keyword in node.keywords:
                    if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                        findings.append((rel, node.lineno, "shell=True"))
        return findings

    def test_direct_git_subprocess_calls_are_boundary_controlled(self) -> None:
        findings = self._direct_git_calls()
        unexpected = [
            finding for finding in findings
            if finding[0] not in TEMPORARY_DIRECT_GIT_EXCEPTIONS
        ]
        self.assertEqual([], unexpected)
        self.assertIn("Agency/Core/work/missions/pipeline/implementation/execution.py", TEMPORARY_DIRECT_GIT_EXCEPTIONS)
        self.assertIn("Agency/Core/work/missions/mission_runtime.py", TEMPORARY_DIRECT_GIT_EXCEPTIONS)
        self.assertIn("Agency/Core/capabilities/engineering/execution.py", TEMPORARY_DIRECT_GIT_EXCEPTIONS)

    def test_editor_apply_and_verify_use_git_authority_boundary(self) -> None:
        source = (self.ROOT / "Agency/Core/work/tasks/editor/execution.py").read_text(encoding="utf-8")
        self.assertIn("git_check_patch", source)
        self.assertIn("git_apply_patch", source)
        self.assertIn("git_diff_check", source)
        self.assertNotIn('subprocess.run(["git"', source)

    def test_no_commit_merge_push_or_deploy_boundary_command_is_introduced(self) -> None:
        source = (self.ROOT / "Agency/Core/repository/git_authority/commands.py").read_text(encoding="utf-8")
        forbidden = ['"commit"', '"merge"', '"push"', '"deploy"', '"reset", "--hard"']
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
