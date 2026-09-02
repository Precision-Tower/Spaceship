from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Agency.Core.runtime import context_builder
from Agency.Core.runtime.context_builder import build_direct_file_context


class FileMentionTests(unittest.TestCase):
    def test_trailing_period_is_not_part_of_path(self) -> None:
        prompt = "Read Agency/Core/runtime/model_service.py."
        self.assertEqual(
            ["Agency/Core/runtime/model_service.py"],
            context_builder._extract_file_mentions(prompt),
        )

    def test_backticks_are_not_part_of_path(self) -> None:
        prompt = "Read `Agency/Agents/ExampleAgent/runtime.yaml`."
        self.assertEqual(
            ["Agency/Agents/ExampleAgent/runtime.yaml"],
            context_builder._extract_file_mentions(prompt),
        )

    def test_two_paths_are_extracted_in_order(self) -> None:
        prompt = (
            "Compare Agency/Agents/ExampleAgent/runtime.yaml and "
            "Agency/Core/runtime/model_service.py."
        )
        self.assertEqual(
            [
                "Agency/Agents/ExampleAgent/runtime.yaml",
                "Agency/Core/runtime/model_service.py",
            ],
            context_builder._extract_file_mentions(prompt),
        )


class DirectContextTests(unittest.TestCase):
    def test_missing_file_produces_no_context(self) -> None:
        prompt = "Read Agency/Agents/ExampleAgent/definitely_missing_7f93.yaml"
        self.assertEqual("", context_builder.build_direct_file_context(prompt))



class MissingFileDetectionTests(unittest.TestCase):
    def test_missing_named_file_is_reported(self):
        from Agency.Core.runtime.context_builder import (
            find_unresolved_file_mentions,
        )

        missing = "Agency/Agents/ExampleAgent/definitely_missing_file_7f93.yaml"
        self.assertEqual(
            find_unresolved_file_mentions(f"Read {missing} and report its owner."),
            [missing],
        )

    def test_existing_named_file_is_not_reported(self):
        from Agency.Core.runtime.context_builder import (
            find_unresolved_file_mentions,
        )

        self.assertEqual(
            find_unresolved_file_mentions(
                "Read Agency/Core/runtime/context_builder.py and report its owner."
            ),
            [],
        )


class PatchRecommendationModeTests(unittest.TestCase):
    def test_unified_diff_phrase_enables_patch_mode(self):
        source = Path(
            "Agency/Core/runtime/model_service.py"
        ).read_text(encoding="utf-8")

        self.assertIn(
            '"unified diff" in normalized_patch_prompt',
            source,
        )
        self.assertIn(
            "or explicit_unified_diff_request",
            source,
        )


class PatchOutputContractTests(unittest.TestCase):
    def test_patch_mode_requires_unified_diff_markers(self):
        source = Path(
            "Agency/Core/runtime/model_service.py"
        ).read_text(encoding="utf-8")

        self.assertIn("Patch formatting requirements:", source)
        self.assertIn("--- a/", source)
        self.assertIn("+++ b/", source)
        self.assertIn("@@ -", source)


class StructuredPatchContextTests(unittest.TestCase):
    def test_patch_request_prefers_python_definition_context(self):
        prompt = (
            "Read Agency/Core/runtime/context_builder.py and propose one small "
            "reversible unified diff. Do not apply it."
        )

        context = build_direct_file_context(prompt)

        self.assertIn(
            "authority: direct_python_structure_for_patch_not_truth",
            context,
        )
        self.assertIn("Python block:", context)
        self.assertIn("def build_direct_file_context", context)
        self.assertNotIn("Excerpt 1:", context)

    def test_non_patch_request_preserves_excerpt_context(self):
        context = build_direct_file_context(
            "What does Agency/Core/runtime/context_builder.py contain?"
        )

        self.assertNotIn(
            "authority: direct_python_structure_for_patch_not_truth",
            context,
        )



# BEGIN patch_008d_semantic_patch_validation_tests
class SemanticPatchValidationTests(unittest.TestCase):
    def test_accepts_requested_comment_only_change(self):
        import tempfile
        from pathlib import Path

        from Agency.Core.runtime.model_service import (
            _patch_008d_semantic_errors,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sample.py"
            target.write_text(
                "# old comment\nvalue = 1\n",
                encoding="utf-8",
            )

            draft = """```diff
--- a/sample.py
+++ b/sample.py
@@ -1,2 +1,2 @@
-# old comment
+# harmless revised comment
 value = 1
```"""

            errors = _patch_008d_semantic_errors(
                draft=draft,
                prompt=(
                    "Read sample.py and propose a unified diff changing "
                    "one harmless comment. Do not apply changes."
                ),
                repo_root=root,
            )

            self.assertEqual(errors, [])

    def test_rejects_behavior_change_for_comment_only_request(self):
        import tempfile
        from pathlib import Path

        from Agency.Core.runtime.model_service import (
            _patch_008d_semantic_errors,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sample.py"
            target.write_text(
                "# comment\nvalue = 1\n",
                encoding="utf-8",
            )

            draft = """```diff
--- a/sample.py
+++ b/sample.py
@@ -1,2 +1,2 @@
 # comment
-value = 1
+value = 2
```"""

            errors = _patch_008d_semantic_errors(
                draft=draft,
                prompt=(
                    "Read sample.py and propose a unified diff changing "
                    "one harmless comment. Do not apply changes."
                ),
                repo_root=root,
            )

            self.assertTrue(
                any("comment-only" in error for error in errors),
                errors,
            )

    def test_rejects_wrong_target_file(self):
        import tempfile
        from pathlib import Path

        from Agency.Core.runtime.model_service import (
            _patch_008d_semantic_errors,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "requested.py").write_text(
                "# requested\n",
                encoding="utf-8",
            )
            (root / "wrong.py").write_text(
                "# wrong\n",
                encoding="utf-8",
            )

            draft = """```diff
--- a/wrong.py
+++ b/wrong.py
@@ -1 +1 @@
-# wrong
+# changed
```"""

            errors = _patch_008d_semantic_errors(
                draft=draft,
                prompt=(
                    "Read requested.py and propose a unified diff changing "
                    "one harmless comment."
                ),
                repo_root=root,
            )

            self.assertTrue(
                any("explicitly requested" in error for error in errors),
                errors,
            )

    def test_rejects_missing_target_file(self):
        import tempfile
        from pathlib import Path

        from Agency.Core.runtime.model_service import (
            _patch_008d_semantic_errors,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            draft = """```diff
--- a/missing.py
+++ b/missing.py
@@ -1 +1 @@
-# old
+# new
```"""

            errors = _patch_008d_semantic_errors(
                draft=draft,
                prompt=(
                    "Read missing.py and propose a unified diff changing "
                    "one harmless comment."
                ),
                repo_root=root,
            )

            self.assertTrue(
                any("does not exist" in error for error in errors),
                errors,
            )

    def test_rejects_prose_outside_fenced_diff(self):
        import tempfile
        from pathlib import Path

        from Agency.Core.runtime.model_service import (
            _patch_008d_semantic_errors,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sample.py").write_text(
                "# old\n",
                encoding="utf-8",
            )

            draft = """Here is the patch:
```diff
--- a/sample.py
+++ b/sample.py
@@ -1 +1 @@
-# old
+# new
```"""

            errors = _patch_008d_semantic_errors(
                draft=draft,
                prompt=(
                    "Read sample.py and propose a unified diff changing "
                    "one harmless comment."
                ),
                repo_root=root,
            )

            self.assertTrue(
                any("no prose outside" in error for error in errors),
                errors,
            )
# END patch_008d_semantic_patch_validation_tests


# BEGIN patch_008e_fence_parser_test
class PatchFenceParserTests(unittest.TestCase):
    def test_extracts_one_bare_fenced_diff(self):
        from Agency.Core.runtime.model_service import (
            _patch_008e_fenced_blocks,
        )

        fence = "`" * 3

        draft = "\n".join(
            [
                "Before",
                fence,
                "--- a/sample.py",
                "+++ b/sample.py",
                "@@ -1 +1 @@",
                "-# old",
                "+# new",
                fence,
                "After",
            ]
        )

        blocks = _patch_008e_fenced_blocks(draft)

        self.assertEqual(
            blocks,
            [
                (
                    "",
                    "--- a/sample.py\n"
                    "+++ b/sample.py\n"
                    "@@ -1 +1 @@\n"
                    "-# old\n"
                    "+# new",
                )
            ],
        )
# END patch_008e_fence_parser_test



# BEGIN patch_008e_diff_normalizer_test
class PatchDiffNormalizerTests(unittest.TestCase):
    def test_extracts_one_diff_from_wrapper_prose(self):
        from Agency.Core.runtime.model_service import (
            _patch_008e_normalize_model_patch,
        )

        fence = "`" * 3

        draft = "\n".join(
            [
                "Observed problem: wrapper prose.",
                "",
                "Change:",
                fence,
                "--- a/sample.py",
                "+++ b/sample.py",
                "@@ -1 +1 @@",
                "-# old",
                "+# new",
                fence,
                "",
                "Reason: wrapper prose.",
            ]
        )

        normalized, changed, errors = (
            _patch_008e_normalize_model_patch(draft)
        )

        expected = "\n".join(
            [
                fence + "diff",
                "--- a/sample.py",
                "+++ b/sample.py",
                "@@ -1 +1 @@",
                "-# old",
                "+# new",
                fence,
            ]
        )

        self.assertEqual(errors, [])
        self.assertTrue(changed)
        self.assertEqual(normalized, expected)
# END patch_008e_diff_normalizer_test



# BEGIN patch_008e_candidate_validation_test
class PatchCandidateValidationTests(unittest.TestCase):
    def test_wrapper_prose_normalizes_and_passes_validation(self):
        import tempfile
        from pathlib import Path

        from Agency.Core.runtime.model_service import (
            _patch_008e_validate_candidate,
        )

        fence = "`" * 3

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            (root / "sample.py").write_text(
                "# old comment\nvalue = 1\n",
                encoding="utf-8",
            )

            draft = "\n".join(
                [
                    "Observed problem: wrapper prose.",
                    "",
                    "Change:",
                    fence,
                    "--- a/sample.py",
                    "+++ b/sample.py",
                    "@@ -1,2 +1,2 @@",
                    "-# old comment",
                    "+# revised harmless comment",
                    " value = 1",
                    fence,
                    "",
                    "Reason: wrapper prose.",
                ]
            )

            (
                normalized,
                changed,
                normalization_errors,
                format_violated,
                semantic_errors,
            ) = _patch_008e_validate_candidate(
                draft=draft,
                prompt=(
                    "Read sample.py and propose a unified diff "
                    "changing one harmless comment."
                ),
                repo_root=root,
            )

            self.assertTrue(changed)
            self.assertEqual(normalization_errors, [])
            self.assertFalse(format_violated)
            self.assertEqual(semantic_errors, [])
            self.assertTrue(
                normalized.startswith(fence + "diff\n")
            )
# END patch_008e_candidate_validation_test



# BEGIN patch_009c_initial_wiring_test
class PatchInitialWiringTests(unittest.TestCase):
    def test_initial_path_uses_candidate_validator(self):
        from pathlib import Path

        source = Path(
            "Agency/Core/runtime/model_service.py"
        ).read_text(encoding="utf-8")

        self.assertIn(
            ") = _patch_008e_validate_candidate(",
            source,
        )
        self.assertIn(
            'payload["patch_normalized_initially"]',
            source,
        )
        self.assertIn(
            'payload["patch_normalization_errors_initially"]',
            source,
        )
        self.assertIn(
            "bool(initial_normalization_errors)",
            source,
        )
# END patch_009c_initial_wiring_test



# BEGIN patch_009c_repair_telemetry_test
class PatchRepairTelemetryTests(unittest.TestCase):
    def test_successful_repair_preserves_initial_normalization_metadata(self):
        from pathlib import Path

        source = Path(
            "Agency/Core/runtime/model_service.py"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'payload["patch_normalized_initially"]',
            source,
        )
        self.assertIn(
            'payload["patch_normalization_errors_initially"]',
            source,
        )
        self.assertIn(
            'payload["patch_normalized_after_repair"]',
            source,
        )
        self.assertIn(
            'payload["patch_normalization_errors_after_repair"]',
            source,
        )
# END patch_009c_repair_telemetry_test



# BEGIN patch_009c_initial_draft_telemetry_test
class PatchInitialDraftTelemetryTests(unittest.TestCase):
    def test_successful_repair_preserves_initial_draft(self):
        from pathlib import Path

        source = Path(
            "Agency/Core/runtime/model_service.py"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'payload["patch_initial_draft"] = initial_patch_draft',
            source,
        )
# END patch_009c_initial_draft_telemetry_test



# BEGIN patch_009c_repair_wiring_test
class PatchRepairWiringTests(unittest.TestCase):
    def test_repair_path_uses_validated_candidate_flow(self):
        from pathlib import Path

        source = Path(
            "Agency/Core/runtime/model_service.py"
        ).read_text(encoding="utf-8")

        legacy_flow = (
            "repaired_draft = (" in source
            and ") = _patch_008e_validate_candidate(" in source
            and "bool(repaired_normalization_errors)" in source
        )

        refinement_flow = (
            "run_refinement(" in source
            and "_context_bites_validation_feedback(" in source
            and (
                "candidate_extractor="
                "lambda artifact: artifact.response"
            ) in source
        )

        self.assertTrue(
            legacy_flow or refinement_flow,
            "No recognized validated patch-repair flow found",
        )

        self.assertIn(
            'payload["patch_normalized_after_repair"]',
            source,
        )
        self.assertIn(
            'payload["patch_normalization_errors_after_repair"]',
            source,
        )
# END patch_009c_repair_wiring_test


# BEGIN patch_009a_context_bites_validation_adapter_tests
class ContextBitesValidationAdapterTests(unittest.TestCase):
    def test_valid_candidate_returns_valid_feedback(self):
        import tempfile
        from pathlib import Path

        from Agency.Core.runtime.model_service import (
            _context_bites_validation_feedback,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sample.py").write_text(
                "# old comment\nvalue = 1\n",
                encoding="utf-8",
            )

            draft = """```diff
--- a/sample.py
+++ b/sample.py
@@ -1,2 +1,2 @@
-# old comment
+# revised comment
 value = 1
```"""

            feedback = _context_bites_validation_feedback(
                draft=draft,
                prompt=(
                    "Read sample.py and propose a unified diff changing "
                    "one harmless comment. Do not apply changes."
                ),
                repo_root=root,
            )

            self.assertTrue(feedback.valid)
            self.assertEqual(feedback.errors, ())

    def test_wrapper_prose_is_normalized_before_validation(self):
        import tempfile
        from pathlib import Path

        from Agency.Core.runtime.model_service import (
            _context_bites_validation_feedback,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sample.py").write_text(
                "# old comment\nvalue = 1\n",
                encoding="utf-8",
            )

            draft = """Here is the patch:

```diff
--- a/sample.py
+++ b/sample.py
@@ -1,2 +1,2 @@
-# old comment
+# revised comment
 value = 1
```"""

            feedback = _context_bites_validation_feedback(
                draft=draft,
                prompt=(
                    "Read sample.py and propose a unified diff changing "
                    "one harmless comment. Do not apply changes."
                ),
                repo_root=root,
            )

            self.assertTrue(feedback.valid)
            self.assertEqual(feedback.errors, ())

    def test_semantic_errors_are_preserved(self):
        import tempfile
        from pathlib import Path

        from Agency.Core.runtime.model_service import (
            _context_bites_validation_feedback,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "requested.py").write_text(
                "# requested\n",
                encoding="utf-8",
            )
            (root / "wrong.py").write_text(
                "# wrong\n",
                encoding="utf-8",
            )

            draft = """```diff
--- a/wrong.py
+++ b/wrong.py
@@ -1 +1 @@
-# wrong
+# changed
```"""

            feedback = _context_bites_validation_feedback(
                draft=draft,
                prompt=(
                    "Read requested.py and propose a unified diff changing "
                    "one harmless comment."
                ),
                repo_root=root,
            )

            self.assertFalse(feedback.valid)
            self.assertTrue(
                any(
                    "explicitly requested" in error
                    for error in feedback.errors
                ),
                feedback.errors,
            )
# END patch_009a_context_bites_validation_adapter_tests

if __name__ == "__main__":
    unittest.main()
