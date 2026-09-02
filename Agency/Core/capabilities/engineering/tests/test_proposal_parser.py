from __future__ import annotations

import unittest

from Agency.Core.capabilities.engineering.parser import EngineeringParser
from Agency.Core.work.work_packets.proposal_contracts import (
    ApplyPatch,
    CreateFile,
    ReplaceText,
    WriteFile,
)


class EngineeringParserTests(unittest.TestCase):
    def test_replace_text(self) -> None:
        request = EngineeringParser.parse(
            'replace "alpha" with "gamma" '
            "in Agency/Core/runtime/target.txt"
        )

        self.assertIsInstance(request.intent, ReplaceText)
        self.assertEqual(
            "Agency/Core/runtime/target.txt",
            request.intent.path,
        )
        self.assertEqual("alpha", request.intent.old)
        self.assertEqual("gamma", request.intent.new)

    def test_create_file(self) -> None:
        request = EngineeringParser.parse(
            "create file Agency/Core/runtime/new.txt "
            "containing exactly hello"
        )

        self.assertIsInstance(request.intent, CreateFile)
        self.assertEqual("hello", request.intent.content)

    def test_write_file(self) -> None:
        request = EngineeringParser.parse(
            "write file Agency/Core/runtime/target.txt "
            "containing exactly updated"
        )

        self.assertIsInstance(request.intent, WriteFile)
        self.assertEqual("updated", request.intent.content)

    def test_apply_patch(self) -> None:
        request = EngineeringParser.parse(
            "propose patch from changes.patch"
        )

        self.assertIsInstance(request.intent, ApplyPatch)
        self.assertEqual("changes.patch", request.intent.patch_path)

    def test_unknown_syntax_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "unsupported_engineering_proposal_syntax",
        ):
            EngineeringParser.parse("do something clever")


if __name__ == "__main__":
    unittest.main()
