# scripts/cli/commands/observation_commands.py
from pathlib import Path
import datetime
from UI.scripts.cli.commands.base import Command

# Pointing to the actual location revealed by 'find'
from UI.scripts.runtime.model_runner import generate_qwen_text, generate_qwen_text_with_timeout
from UI.scripts.runtime.agent_registry import normalized_agent_registry
from UI.scripts.agents.core.paths import DASHBOARD_ROOT, UI_ROOT, scan_files

class CaliObserveCommand(Command):
    """
    Handles repository observation, snapshot generation, and 
    clerical recommendation via the Cali agent model.
    """
    CALI_AGENT_ID = "cali"
    DEFAULT_MODEL_PATH = DASHBOARD_ROOT / "Models" / "Qwen3-8b"
    AGENT_PROMPT_PATH = UI_ROOT / "scripts" / "agents" / "cali.md"

    def run(self, args):
        root = self.resolver.resolve_target_root(args.root)
        model_path = Path(args.model_path).resolve() if getattr(args, 'model_path', None) else self._resolve_cali_model_path() or self.DEFAULT_MODEL_PATH
        
        print("CALI_OBSERVE_DIRECTORY")
        print(f"root: {root}")
        print(f"model_path: {model_path}")
        
        if getattr(args, 'dry_run_model_path', False):
            print(f"status: dry_run\nresolved_model_path: {model_path}")
            return

        snapshot = self._build_snapshot(root, args.max_files)
        prompt = self._build_prompt(snapshot)

        # Execution
        result = self._generate(model_path, prompt, args)
        
        if not result.ok:
            self._report_degraded(result.status, result.reason)
        else:
            print("status: observation_generated\n")
            print(result.text)

    def _build_snapshot(self, root, max_files):
        files = scan_files(root)
        lines = ["DIRECTORY_SNAPSHOT", f"root: {root}", f"files_detected: {len(files)}"]
        # Include your existing helper methods here (e.g., _count_by_top_folder)
        # using 'root' as the base path for scans.
        return "\n".join(lines)

    def _build_prompt(self, snapshot):
        prompt_text = self.AGENT_PROMPT_PATH.read_text(encoding="utf-8", errors="replace")
        return f"{prompt_text}\n\nTask:\nObserve the Directory snapshot as Cali.\n\nDirectory snapshot:\n```text\n{snapshot}\n```"

    def _resolve_cali_model_path(self):
        registry = normalized_agent_registry()
        for agent in registry.get("agents", []):
            if agent.get("id") == self.CALI_AGENT_ID:
                path = agent.get("model", {}).get("path")
                return DASHBOARD_ROOT / path if path else None
        return None

    def _generate(self, model_path, prompt, args):
        timeout = getattr(args, 'timeout_seconds', None)
        if timeout:
            return generate_qwen_text_with_timeout(
                model_path=model_path, prompt=prompt, 
                max_new_tokens=args.max_new_tokens, timeout_seconds=timeout
            )
        return generate_qwen_text(model_path=model_path, prompt=prompt, max_new_tokens=args.max_new_tokens)

    def _report_degraded(self, status, reason):
        print(f"status: {status}\nmode: degraded_no_model_generation")
        print(f"reason: {reason}\n- Restore execution, then rerun cali-observe-directory.")