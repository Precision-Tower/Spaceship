import difflib
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from Agency.Core.interfaces.cli.commands.base import Command
from Agency.Core.repository.git_authority import GitAuthorityError, apply_patch as git_apply_patch, repository_ref
from Agency.Core.foundation.paths import PROPOSALS_ROOT, stable_path


class ApplyPatchCommand(Command):
    def run(self, args):
        root = self.resolver.resolve_target_root(getattr(args, "root", None))
        diff_path = Path(args.diff).resolve()

        if not getattr(args, "approved", False):
            return self._report("blocked", "reason: --approved required")

        if not diff_path.exists():
            return self._report("blocked", "reason: diff not found")

        try:
            observation = git_apply_patch(repository_ref(root), diff_path)
        except GitAuthorityError as exc:
            return self._report("apply_failed", f"{exc.code}: {exc.message}")
        if observation.git_exit_code != 0:
            return self._report("apply_failed", observation.stderr.strip())

        print("status: patch_applied")
        print(f"root: {root}")
        print(f"diff: {diff_path}")


class ClearDiffCommand(Command):
    def run(self, args):
        patch_dir = self.resolver.ui_root / "scripts" / "patches"
        latest = patch_dir / "latest.diff"
        archive = patch_dir / "latest.diff.tombstone"

        patch_dir.mkdir(parents=True, exist_ok=True)

        if not latest.exists():
            return self._report("missing", "latest.diff not found")

        if archive.exists():
            archive.unlink()

        latest.replace(archive)

        print("status: archived")
        print(f"from: {latest}")
        print(f"to: {archive}")


class ViewDiffCommand(Command):
    def run(self, args):
        patch_dir = self.resolver.ui_root / "scripts" / "patches"
        latest = patch_dir / "latest.diff"

        if not latest.exists():
            return self._report("missing", "latest.diff not found")

        print("status: present")
        print(f"path: {latest}")
        print(f"diff:\n{latest.read_text(encoding='utf-8', errors='replace')}")



class ProposeDiffCommand(Command):
    _IGNORED_PARTS = {
        ".git",
        ".godot",
        "__pycache__",
        ".venv",
        "node_modules",
        "Archive",
        "archive",
    }
    _MAX_DIFF_LISTED_FILES = 50

    def run(self, args):
        repo_root = self.resolver.dashboard_root.resolve()
        intent = str(args.intent).strip()
        raw_scopes = list(getattr(args, "scope", None) or [])

        if not intent:
            self._reject("intent is required")
        if not raw_scopes:
            self._reject("at least one --scope is required")

        try:
            validated_scopes = self._validate_scopes(repo_root, raw_scopes)
        except ValueError as exc:
            self._reject(str(exc))

        inspected_files, skipped_files = self._inspect_scopes(repo_root, validated_scopes)

        created_at = datetime.now(timezone.utc)
        proposal_id = self._proposal_id(intent, validated_scopes, created_at)
        proposal_dir = PROPOSALS_ROOT / proposal_id
        proposal_dir.mkdir(parents=True, exist_ok=False)

        proposal_json_path = proposal_dir / "proposal.json"
        proposed_diff_path = proposal_dir / "proposed.diff"
        evidence_json_path = proposal_dir / "evidence.json"
        scratch_rel = stable_path(proposal_dir / "proposal_scratch.txt", repo_root)

        diff_text = self._build_placeholder_diff(
            proposal_id=proposal_id,
            intent=intent,
            scopes=validated_scopes,
            inspected_files=inspected_files,
            skipped_files=skipped_files,
            scratch_rel=scratch_rel,
            created_at=created_at,
        )
        diff_target_validation = self._validate_diff_targets(
            diff_text=diff_text,
            repo_root=repo_root,
            validated_scopes=validated_scopes,
            proposal_dir=proposal_dir,
        )

        if diff_target_validation["invalid_targets"]:
            self._reject(
                "proposal contains files outside declared scopes: "
                + ", ".join(diff_target_validation["invalid_targets"])
            )
        if diff_target_validation["source_targets"]:
            self._reject(
                "deterministic proposal may not target source files: "
                + ", ".join(diff_target_validation["source_targets"])
            )

        generated_artifacts = {
            "proposal_json": self._repo_rel(proposal_json_path, repo_root),
            "proposed_diff": self._repo_rel(proposed_diff_path, repo_root),
            "evidence_json": self._repo_rel(evidence_json_path, repo_root),
            "scratch_diff_target": scratch_rel,
        }

        proposal = {
            "proposal_id": proposal_id,
            "status": "proposal_generated",
            "intent": intent,
            "scopes": [scope["relative"] for scope in validated_scopes],
            "authority": "proposal_only",
            "source_files_modified": False,
            "diff_path": generated_artifacts["proposed_diff"],
            "created_at": self._iso_timestamp(created_at),
        }

        evidence = {
            "proposal_id": proposal_id,
            "inspected_files": inspected_files,
            "skipped_files": skipped_files,
            "validated_scopes": validated_scopes,
            "generated_artifacts": generated_artifacts,
            "diff_target_validation": diff_target_validation,
            "source_files_modified": False,
            "limitations": [
                "Deterministic placeholder generator only; no AI model was called.",
                "The generated diff targets only a proposal-owned scratch file.",
                "No apply behavior is implemented by this command.",
                "No application source file changes are proposed in this implementation.",
            ],
            "no_source_files_modified_statement": (
                "No source files were modified; this command wrote only proposal artifacts "
                "inside the proposal directory."
            ),
        }

        proposed_diff_path.write_text(diff_text, encoding="utf-8")
        proposal_json_path.write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")
        evidence_json_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

        print("status: proposal_generated")
        print(f"proposal_id: {proposal_id}")
        print(f"proposal_dir: {proposal_dir}")
        print(f"proposal_json: {proposal_json_path}")
        print(f"proposed_diff: {proposed_diff_path}")
        print(f"evidence_json: {evidence_json_path}")

    def _validate_scopes(self, repo_root, raw_scopes):
        validated = []
        seen = set()

        for raw_scope in raw_scopes:
            raw = str(raw_scope).strip()
            if not raw:
                raise ValueError("empty scope is not allowed")
            if self._has_parent_traversal(raw):
                raise ValueError(f"scope contains parent traversal: {raw}")

            candidate = Path(raw)
            if not candidate.is_absolute():
                candidate = repo_root / candidate

            resolved = candidate.resolve()
            if not self._is_relative_to(resolved, repo_root):
                raise ValueError(f"scope escapes repository root: {raw}")
            if not resolved.exists():
                raise ValueError(f"scope does not exist: {raw}")

            relative = self._repo_rel(resolved, repo_root)
            if relative not in seen:
                seen.add(relative)
                validated.append({
                    "input": raw,
                    "resolved": str(resolved),
                    "relative": relative,
                    "kind": "directory" if resolved.is_dir() else "file",
                })

        return validated

    def _inspect_scopes(self, repo_root, validated_scopes):
        inspected = []
        skipped = []
        inspected_set = set()
        skipped_set = set()
        scope_paths = [Path(scope["resolved"]) for scope in validated_scopes]

        for scope in validated_scopes:
            scope_path = Path(scope["resolved"])
            candidates = [scope_path] if scope_path.is_file() else sorted(scope_path.rglob("*"))

            for candidate in candidates:
                try:
                    resolved = candidate.resolve()
                except OSError as exc:
                    self._record_skip(skipped, skipped_set, candidate, repo_root, f"resolve_failed: {exc}")
                    continue

                if not candidate.is_file():
                    continue
                if not self._is_relative_to(resolved, repo_root):
                    self._record_skip(skipped, skipped_set, candidate, repo_root, "symlink_or_path_escape")
                    continue
                if not any(self._path_is_in_scope(resolved, scope_path) for scope_path in scope_paths):
                    self._record_skip(skipped, skipped_set, candidate, repo_root, "outside_declared_scopes")
                    continue
                if self._should_ignore(resolved, repo_root):
                    self._record_skip(skipped, skipped_set, resolved, repo_root, "ignored_path")
                    continue

                try:
                    data = resolved.read_bytes()
                except OSError as exc:
                    self._record_skip(skipped, skipped_set, resolved, repo_root, f"read_failed: {exc}")
                    continue

                if b"\x00" in data:
                    self._record_skip(skipped, skipped_set, resolved, repo_root, "binary_file")
                    continue

                try:
                    text = data.decode("utf-8")
                except UnicodeDecodeError:
                    self._record_skip(skipped, skipped_set, resolved, repo_root, "non_utf8_text")
                    continue

                relative = self._repo_rel(resolved, repo_root)
                if relative in inspected_set:
                    continue

                inspected_set.add(relative)
                inspected.append({
                    "path": relative,
                    "bytes": len(data),
                    "lines": len(text.splitlines()),
                })

        inspected.sort(key=lambda item: item["path"])
        skipped.sort(key=lambda item: item["path"])
        return inspected, skipped

    def _build_placeholder_diff(
        self,
        *,
        proposal_id,
        intent,
        scopes,
        inspected_files,
        skipped_files,
        scratch_rel,
        created_at,
    ):
        scratch_lines = [
            "Deterministic placeholder proposal",
            f"Proposal ID: {proposal_id}",
            f"Created at: {self._iso_timestamp(created_at)}",
            "Authority: proposal_only",
            "Source files modified: false",
            "",
            f"Intent: {intent}",
            "",
            "Validated scopes:",
        ]
        scratch_lines.extend(f"- {scope['relative']}" for scope in scopes)
        scratch_lines.extend([
            "",
            f"Inspected text files: {len(inspected_files)}",
            f"Skipped files: {len(skipped_files)}",
            "",
            "Inspected file sample:",
        ])

        if inspected_files:
            scratch_lines.extend(
                f"- {item['path']} ({item['bytes']} bytes, {item['lines']} lines)"
                for item in inspected_files[:self._MAX_DIFF_LISTED_FILES]
            )
        else:
            scratch_lines.append("- none")

        remaining = max(len(inspected_files) - self._MAX_DIFF_LISTED_FILES, 0)
        if remaining:
            scratch_lines.append(f"- ... {remaining} additional inspected files omitted from scratch summary")

        scratch_lines.extend([
            "",
            "Limitations:",
            "- Placeholder generator only; no AI model was called.",
            "- Diff target is proposal-owned scratch content only.",
            "- No real application source file targets are proposed in this implementation.",
        ])

        diff_lines = difflib.unified_diff(
            [],
            scratch_lines,
            fromfile="/dev/null",
            tofile=f"b/{scratch_rel}",
            lineterm="",
        )
        return "\n".join(diff_lines) + "\n"

    def _validate_diff_targets(self, *, diff_text, repo_root, validated_scopes, proposal_dir):
        targets = []
        invalid = []
        source_targets = []
        proposal_owned_targets = []
        scope_paths = [Path(scope["resolved"]) for scope in validated_scopes]

        for line in diff_text.splitlines():
            if not (line.startswith("--- ") or line.startswith("+++ ")):
                continue

            raw_target = line[4:].strip()
            if raw_target == "/dev/null":
                continue
            if raw_target.startswith(("a/", "b/")):
                raw_target = raw_target[2:]

            target_path = Path(raw_target)
            if not target_path.is_absolute():
                target_path = repo_root / target_path

            resolved = target_path.resolve()
            relative = self._repo_rel(resolved, repo_root)
            targets.append(relative)

            if self._is_relative_to(resolved, proposal_dir):
                proposal_owned_targets.append(relative)
                continue

            if any(self._path_is_in_scope(resolved, scope_path) for scope_path in scope_paths):
                source_targets.append(relative)
                continue

            invalid.append(relative)

        return {
            "status": "valid" if not invalid and not source_targets else "invalid",
            "targets": targets,
            "proposal_owned_targets": proposal_owned_targets,
            "source_targets": source_targets,
            "invalid_targets": invalid,
        }

    def _proposal_id(self, intent, validated_scopes, created_at):
        stamp = created_at.strftime("%Y%m%dT%H%M%S%fZ")
        scope_text = "|".join(scope["relative"] for scope in validated_scopes)
        digest = hashlib.sha256(f"{intent}|{scope_text}|{stamp}".encode("utf-8")).hexdigest()[:10]
        return f"proposal_{stamp}_{digest}"

    def _record_skip(self, skipped, skipped_set, path, repo_root, reason):
        relative = self._repo_rel(path, repo_root)
        key = (relative, reason)
        if key in skipped_set:
            return
        skipped_set.add(key)
        skipped.append({
            "path": relative,
            "reason": reason,
        })

    def _reject(self, message):
        print("status: rejected", file=sys.stderr)
        print(f"message: {message}", file=sys.stderr)
        raise SystemExit(2)

    def _should_ignore(self, path, repo_root):
        relative_parts = Path(self._repo_rel(path, repo_root)).parts
        if any(part in self._IGNORED_PARTS for part in relative_parts):
            return True
        return tuple(relative_parts[:6]) == ("Agency", "Core", "runtime", "state", "proposals")

    def _has_parent_traversal(self, value):
        parts = value.replace("\\", "/").split("/")
        return any(part == ".." for part in parts)

    def _path_is_in_scope(self, path, scope_path):
        if scope_path.is_file():
            return path == scope_path
        return path == scope_path or self._is_relative_to(path, scope_path)

    def _repo_rel(self, path, repo_root):
        resolved = Path(path).resolve()
        try:
            return resolved.relative_to(repo_root).as_posix()
        except ValueError:
            return str(resolved)

    def _is_relative_to(self, path, root):
        path = Path(path).resolve()
        root = Path(root).resolve()
        return path == root or root in path.parents

    def _iso_timestamp(self, value):
        return value.isoformat().replace("+00:00", "Z")


class GrantReviewCommand(Command):
    def run(self, args):
        diff_path = Path(args.diff).resolve()

        if not diff_path.exists():
            return self._report("missing", f"diff not found: {diff_path}")

        # Lexical review placeholder.
        # This is review surface only, not approval authority.
        print("status: admissible")
        print(f"diff: {diff_path}")

