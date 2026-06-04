from UI.scripts.agents.core.bridge import CaliBridge
from UI.scripts.agents.core.memory import WeeboMemory
from UI.scripts.agents.core.paths import PathResolver
from UI.scripts.agents.core.persona import build_weebo_persona
from UI.scripts.agents.core.tooling import (
    parse_tool_call,
    run_tool,
    tool_result_preview,
    write_authorized,
)
from UI.scripts.agents.reasoners import ReasonerFactory

from pathlib import Path

class WeeboAgent:
    def __init__(
        self,
        reasoner=None,
        bridge: CaliBridge | None = None,
        memory: WeeboMemory | None = None,
        model_path: str | None = None,
        backend: str = "gguf",
        max_turns: int = 3,
        debug_raw: bool = False,
        spaceship_root: Path | None = None,
    ):
        self.resolver = bridge.resolver if bridge else PathResolver(spaceship_root=spaceship_root)
        self.bridge = bridge or CaliBridge(self.resolver)
        self.memory = memory or WeeboMemory(self.resolver)
        self.max_turns = max_turns
        self.debug_raw = debug_raw

        if reasoner is not None:
            self.reasoner = reasoner
        elif model_path:
            self.reasoner = ReasonerFactory.get_reasoner(model_path, backend)
        else:
            self.reasoner = None

        self.persona = build_weebo_persona()

    def process_command(self, user_input: str) -> str:
        if self.reasoner is None:
            return "WEEBO_ENGINE_READY_NO_REASONER"

        forced_context = self._forced_file_context(user_input)
        current_prompt = self._wrap_user_prompt(user_input, forced_context)

        for _ in range(self.max_turns):
            if self._interrupted():
                return "[INTERRUPTED] WEEBO stopped by operator request."

            response = self._generate(current_prompt)

            if self.debug_raw:
                print("\n[MODEL RAW]\n" + response + "\n", flush=True)

            if self._memory_only_requested(user_input):
                return self._clean_response(response)

            tool_call = parse_tool_call(response)

            if tool_call is None:
                return self._clean_response(response)

            tool_name, args = tool_call

            if tool_name == "write_file" and not write_authorized(user_input):
                return (
                    "WRITE_BLOCKED: Operator did not explicitly authorize file edits.\n\n"
                    "MODEL_OUTPUT:\n"
                    f"{response}"
                )

            result = run_tool(self.bridge, tool_name, args)

            self.memory.log_event(
                "tool_call",
                {
                    "tool": tool_name,
                    "args": args,
                    "result_preview": tool_result_preview(result),
                },
            )

            current_prompt += (
                "\n\nTOOL OBSERVATION:\n"
                f"tool: {tool_name}\n"
                f"result:\n{result}\n\n"
                "Now answer the operator normally. "
                "Do not emit another tool call unless more inspection is required."
            )

        return "WEEBO reached maximum reasoning turns."

    def _wrap_user_prompt(self, user_input: str, forced_context: str = "") -> str:
        context = self.bridge.get_system_context()
        memory_context = self.memory.build_context(user_input)

        extra = (
            f"\n\nPRELOADED FILE CONTEXT:\n{forced_context}"
            if forced_context
            else ""
        )

        return (
            f"CURRENT SYSTEM CONTEXT:\n{context}\n\n"
            f"{memory_context}"
            f"{extra}\n\n"
            f"OPERATOR REQUEST:\n{user_input}"
        )

    def _forced_file_context(self, user_input: str) -> str:
        lowered = user_input.lower()

        known_files = {
            "run.py": "Run.py",
            "engine.py": "UI/scripts/agents/core/engine.py",
            "tooling.py": "UI/scripts/agents/core/tooling.py",
            "persona.py": "UI/scripts/agents/core/persona.py",
            "bridge.py": "UI/scripts/agents/core/bridge.py",
            "memory.py": "UI/scripts/agents/core/memory.py",
        }

        chunks = []

        for key, path in known_files.items():
            if key in lowered:
                content = self.bridge.read_file(path)
                chunks.append(
                    f"FILE: {path}\n"
                    f"```text\n"
                    f"{content[:8000]}\n"
                    f"```"
                )

        return "\n\n".join(chunks)

    def _generate(self, prompt: str) -> str:
        return self.reasoner.generate(
            system_context=self.persona,
            user_prompt=prompt,
            max_new_tokens=128,
        )

    def _memory_only_requested(self, user_input: str) -> bool:
        return "memory only" in user_input.lower()

    def _interrupted(self) -> bool:
        interrupt_flag = self.resolver.spaceship_root / "interrupt.flag"

        if interrupt_flag.exists():
            interrupt_flag.unlink(missing_ok=True)
            return True

        return False

    def _clean_response(self, response: str) -> str:
        return response.strip()

    def task(self, instruction: str) -> str:
        plan = self.process_command(instruction)

        patches_dir = (
            self.resolver.spaceship_root
            / "UI"
            / "scripts"
            / "patches"
        )
        patches_dir.mkdir(parents=True, exist_ok=True)

        proposal_path = patches_dir / "latest_agent_proposal.txt"
        proposal_path.write_text(
            f"INSTRUCTION:\n{instruction}\n\nRESULT:\n{plan}\n",
            encoding="utf-8",
        )

        return f"[PROPOSAL WRITTEN] {proposal_path}"