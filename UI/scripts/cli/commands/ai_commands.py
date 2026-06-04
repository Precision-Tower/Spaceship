# scripts/cli/commands/ai_commands.py
import json
from UI.scripts.cli.commands.base import Command

class GeminiAnalyzeCommand(Command):
    def run(self, args):
        """CLI command entry point for Gemini analysis requests."""
        # Using the runtime bridge
        from UI.scripts.Models.Online.cali_gemini_bridge import request_analysis
        from UI.scripts.paths import UI_ROOT

        mission_path = UI_ROOT / "Mission.yaml"
        mission_context = ""
        if mission_path.exists():
            mission_text = mission_path.read_text(encoding="utf-8", errors="replace")
            mission_context = f"AXIOMATIC MISSION SOURCE (Mission.yaml):\n{mission_text}\n\n"

        full_context = f"{mission_context}ANALYSIS CONTEXT:\n{args.context}"
        result = request_analysis(args.purpose, full_context)
        print(json.dumps(result, indent=2))

class GeminiListModelsCommand(Command):
    def run(self, args):
        """CLI command to list models available to the current API key."""
        from UI.scripts.Models.Online.gemini_client import list_available_models

        models = list_available_models()
        print(json.dumps({
            "available_models": models,
            "count": len(models)
        }, indent=2))