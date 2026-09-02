from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Agency.Core.work.tasks.editor import contracts as editor_contracts
from Agency.Core.work.tasks.editor import execution as editor_execution
from Agency.Core.work.tasks.editor import persistence as editor_persistence
from Agency.Core.work.work_packets import execution, persistence
from Agency.Core.work.work_packets.proposal_contracts import (
    CreateFile,
    ProposalRequest,
    ProposalScope,
    ReplaceText,
)
from Agency.Core.work.work_packets.proposals import create_proposal
from Agency.Core.repository.context import builder


class CreateProposalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()

        subprocess.run(
            ["git", "init"],
            cwd=self.repo,
            check=True,
            capture_output=True,
        )

        self.agency_root = self.repo / "Agency"
        self.runtime = self.agency_root / "Core" / "runtime"
        self.runtime.mkdir(parents=True)

        self.target = self.runtime / "target.txt"
        self.target.write_text("alpha\n", encoding="utf-8")

        self.work_packets = (
            self.agency_root
            / "Agents"
            / "Editor"
            / "work"
            / "WorkPackets"
        )
        self.editor_tasks = (
            self.agency_root
            / "Agents"
            / "Editor"
            / "work"
            / "EditorTasks"
        )
        self.inspections = (
            self.agency_root
            / "Agents"
            / "Editor"
            / "work"
            / "Inspections"
        )

        patches = [
            patch.object(editor_contracts, "DASHBOARD_ROOT", self.repo),
            patch.object(editor_execution, "DASHBOARD_ROOT", self.repo),
            patch.object(execution, "DASHBOARD_ROOT", self.repo),
            patch.object(builder, "DASHBOARD_ROOT", self.repo),
            patch.object(builder, "AGENCY_ROOT", self.agency_root),
            patch.object(
                builder,
                "WORK_INSPECTIONS_ROOT",
                self.inspections,
            ),
            patch.object(
                editor_persistence,
                "EDITOR_TASKS_ROOT",
                self.editor_tasks,
            ),
            patch.object(
                persistence,
                "WORK_PACKETS_ROOT",
                self.work_packets,
            ),
        ]

        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def test_create_proposal_dispatches_supported_intent(self) -> None:
        request = ProposalRequest(
            intent=ReplaceText(
                path="Agency/Core/runtime/target.txt",
                old="alpha",
                new="gamma",
            ),
            scope=ProposalScope(
                include=("Agency/Core/runtime",),
            ),
        )

        payload = create_proposal(
            play_owner="Gear",
            request=request,
        )

        self.assertTrue(payload["ok"], payload)
        self.assertEqual("replace_text", payload["proposal_intent"])
        self.assertFalse(payload["repository_mutation_performed"])
        self.assertEqual(
            "alpha\n",
            self.target.read_text(encoding="utf-8"),
        )

        packet_id = payload["packet_id"]
        packet_dir = self.work_packets / packet_id

        self.assertTrue((packet_dir / "packet.json").is_file())
        self.assertTrue((packet_dir / "events.jsonl").is_file())

        result_path = Path(payload["editor_result_path"])
        self.assertTrue(result_path.is_file(), payload)

        result_reference = json.loads(
            result_path.read_text(encoding="utf-8")
        )
        result_data = result_reference.get(
            "result",
            result_reference,
        )
        patch_artifacts = result_data.get("patch_artifacts") or []
        self.assertTrue(patch_artifacts, result_reference)

        def patch_paths_from(value):
            found = []

            if isinstance(value, dict):
                for item in value.values():
                    found.extend(patch_paths_from(item))

            elif isinstance(value, list):
                for item in value:
                    found.extend(patch_paths_from(item))

            elif isinstance(value, str) and value.endswith(".patch"):
                found.append(Path(value))

            return found

        patch_paths = patch_paths_from(patch_artifacts)
        self.assertTrue(patch_paths, patch_artifacts)

        existing_patch_paths = [
            path for path in patch_paths if path.is_file()
        ]
        self.assertTrue(existing_patch_paths, patch_paths)

        patch_text = existing_patch_paths[0].read_text(
            encoding="utf-8"
        )
        self.assertIn("-alpha", patch_text)
        self.assertIn("+gamma", patch_text)

    def test_unsupported_intent_is_explicit_and_persists_nothing(self) -> None:
        request = ProposalRequest(
            intent=CreateFile(
                path="Agency/Core/runtime/new.txt",
                content="new\n",
            ),
            scope=ProposalScope(
                include=("Agency/Core/runtime",),
            ),
        )

        payload = create_proposal(
            play_owner="Gear",
            request=request,
        )

        self.assertFalse(payload["ok"])
        self.assertEqual(
            "unsupported_proposal_intent",
            payload["code"],
        )
        self.assertEqual("create_file", payload["intent"])
        self.assertFalse(self.work_packets.exists())


if __name__ == "__main__":
    unittest.main()
