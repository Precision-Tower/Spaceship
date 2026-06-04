from pathlib import Path

from UI.scripts.cli.commands.base import Command
from UI.scripts.runtime.model_runner import (
    generate_qwen_text,
    generate_qwen_text_with_timeout,
)
from UI.scripts.runtime.agent_registry import normalized_agent_registry
from UI.scripts.agents.core.paths import scan_files


class ScanRepoCommand(Command):
    name = "scan-repo"

    def run(self, args):
        root = self.resolver.resolve_target_root(getattr(args, "root", None))
        files = scan_files(root)

        print(f"SCAN_REPO\nroot: {root}\nfiles_detected: {len(files)}")
        for f in files[:200]:
            print(f)


class RuntimeStateCommand(Command):
    name = "runtime-state"

    def run(self, args):
        print("RUNTIME_STATE")
        print("status: importable")
        print(f"dashboard_root: {self.resolver.dashboard_root}")
        print(f"ui_root: {self.resolver.ui_root}")
        print(f"spaceship_root: {self.resolver.spaceship_root}")
        print(f"root_resolution: {self.resolver.root_resolution_method}")


class TestAllCommand(Command):
    name = "test-all"

    def run(self, args):
        print("TEST_ALL")
        print("status: placeholder_pass")


class CaliObserveCommand(Command):
    name = "cali-observe"

    CALI_AGENT_ID = "cali"

    def run(self, args):
        root = self.resolver.resolve_target_root(getattr(args, "root", None))

        model_path_arg = getattr(args, "model_path", None)
        model_path = (
            Path(model_path_arg).resolve()
            if model_path_arg
            else self._resolve_cali_model_path()
            or self.resolver.spaceship_root / "local" / "Qwen3-8b"
        )

        print("CALI_OBSERVE_DIRECTORY")
        print(f"root: {root}")
        print(f"model_path: {model_path}")

        if getattr(args, "dry_run_model_path", False):
            print("status: dry_run")
            return

        max_files = getattr(args, "max_files", 200)
        snapshot = self._build_snapshot(root, max_files)
        prompt = self._build_prompt(snapshot)

        max_new_tokens = getattr(args, "max_new_tokens", 512)
        result = self._generate(model_path, prompt, max_new_tokens, args)

        if not getattr(result, "ok", False):
            self._report_degraded(
                getattr(result, "status", "generation_failed"),
                getattr(result, "reason", "unknown"),
            )
            return

        print("status: observation_generated\n")
        print(result.text)

    def _build_snapshot(self, root: Path, max_files: int):
        files = scan_files(root)
        lines = [
            "DIRECTORY_SNAPSHOT",
            f"root: {root}",
            f"files_detected: {len(files)}",
            "",
            "files:",
        ]

        for file in files[:max_files]:
            lines.append(f"- {file}")

        return "\n".join(lines)

    def _build_prompt(self, snapshot: str):
        agent_prompt_path = (
            self.resolver.ui_root
            / "scripts"
            / "agents"
            / "cali.md"
        )

        if agent_prompt_path.exists():
            prompt_text = agent_prompt_path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        else:
            prompt_text = (
                "You are Cali. Preserve continuity, summarize structure, "
                "and do not promote observations into validation."
            )

        return (
            f"{prompt_text}\n\n"
            "Task:\nObserve the directory snapshot.\n\n"
            "Directory snapshot:\n```text\n"
            f"{snapshot}\n"
            "```"
        )

    def _resolve_cali_model_path(self):
        try:
            registry = normalized_agent_registry()
        except Exception:
            return None

        for agent in registry.get("agents", []):
            if agent.get("id") == self.CALI_AGENT_ID:
                path = agent.get("model", {}).get("path")
                if path:
                    return self.resolver.spaceship_root / path

        return None

    def _generate(self, model_path, prompt, max_new_tokens, args):
        timeout = getattr(args, "timeout_seconds", None)

        if timeout:
            return generate_qwen_text_with_timeout(
                model_path=model_path,
                prompt=prompt,
                max_new_tokens=max_new_tokens,
                timeout_seconds=timeout,
            )

        return generate_qwen_text(
            model_path=model_path,
            prompt=prompt,
            max_new_tokens=max_new_tokens,
        )

    def _report_degraded(self, status, reason):
        print(f"status: {status}")
        print("mode: degraded_no_model_generation")
        print(f"reason: {reason}")