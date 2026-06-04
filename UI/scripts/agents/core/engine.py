import re
from pathlib import Path
from datetime import datetime
# Note: These paths assume you are starting from the root 'Dashboard' directory
from UI.scripts.agents.core.bridge import CaliBridge
from UI.scripts.agents.core.memory import WeeboMemory
from UI.scripts.agents.reasoners import ReasonerFactory

# Define regex outside the class for performance
TOOL_CALL_RE = re.compile(
    r"(?:^|\n)Thought:\s*(?P<thought>.+?)\n"
    r"Action:\s*(?P<tool>execute|read_file|write_file|list_files)\((?P<args>.*)\)\s*$",
    re.DOTALL,
)

class WeeboAgent:
    def __init__(self, reasoner, bridge: CaliBridge, memory: WeeboMemory):
        self.reasoner = ReasonerFactory.get_reasoner(model_path)
        self.bridge = bridge
        self.memory = memory
        self.persona = (
            "You are WEEBO, a world-class software engineering partner. "
            "Your primary mission is to help the operator build JARVIS (Gear). "
            "You provide architectural insights, code quality reviews, and perform tasks. "
            "Preserve truth-state integrity and guard against semantic drift. "
            "Bias toward inspectability, recoverability, and bounded uncertainty.\n\n"
            "### MEMORY FACTS\n"
            "When memory facts are provided above, they are already visible to you. "
            "Memory facts are NOT files and are NOT tool targets. "
            "Answer memory questions directly from UI.scripts facts already provided.\n\n"
            "### AVAILABLE TOOLS\n"
            "1. execute(command): Runs a Dashboard CLI command.\n"
            "2. read_file(path): Reads repository files.\n"
            "3. write_file(path='...', content='...'): Writes to the jail.\n"
            "4. list_files(path='.'): Lists files in the jail.\n\n"
            "To use a tool, your response MUST end with:\n"
            "Thought: [reasoning]\nAction: tool_name(arg1='value1')"
        )

    def process_command(self, user_input):
        memory_only_mode = "memory only" in user_input.lower()
        max_turns = 3
        current_prompt = user_input
        
        for turn in range(max_turns):
            # Check for operator interrupt flag via bridge/path logic
            interrupt_flag = self.bridge.resolver.root / "interrupt.flag"
            if interrupt_flag.exists():
                interrupt_flag.unlink(missing_ok=True)
                return "[INTERRUPTED] WEEBO: Stopped operational task by operator request."

            context = self.bridge.get_system_context()
            memory_context = self.memory.build_context(current_prompt)
            
            response = self.reasoner.generate(
                system_context=(
                    f"{self.persona}\n\n"
                    f"CURRENT SYSTEM CONTEXT:\n{context}\n\n"
                    f"{memory_context}"
                ),
                user_prompt=current_prompt,
                max_new_tokens=512
            )
            
            if memory_only_mode:
                return self._clean_response_for_memory_only(response)
            
            action_match = TOOL_CALL_RE.search(response)
            if action_match:
                tool_name = action_match.group("tool")
                raw_args = action_match.group("args")
                args = {m.group(1): m.group(2) for m in re.finditer(r"(\w+)=['\"](.*?)['\"]", raw_args, re.DOTALL)}
                arg_val = list(args.values())[0] if args else raw_args.strip("'\" ")

                print(f"\n[*] WEEBO is using tool: {tool_name}({args if args else arg_val})")
                self.memory.log_event("tool_call", {"tool": tool_name, "args": args if args else arg_val})

                result = ""
                if tool_name == "execute":
                    result = self.bridge._exec(args.get('command', arg_val))
                elif tool_name == "read_file":
                    result = self.bridge.read_file(args.get('path', arg_val))
                elif tool_name == "write_file":
                    result = self.bridge.write_file(args.get('path', ''), args.get('content', ''))
                elif tool_name == "list_files":
                    result = self.bridge.list_files(args.get('path', arg_val))
                
                current_prompt += f"\n\nObservation from UI.scriptsol_name:\n{result}"
                continue
            
            return response
        return "WEEBO reached maximum reasoning turns."

    def _clean_response_for_memory_only(self, response: str) -> str:
        # Implementation of your memory-only cleaning logic
        cleaned = response.strip()
        # ... (rest of your cleaning implementation) ...
        return cleaned

    def task(self, instruction: str) -> str:
        # Implementation of your task diff proposal workflow
        try:
            plan = self.process_command(instruction)
            patches_dir = self.bridge.resolver.root / "patches"
            patches_dir.mkdir(exist_ok=True)
            
            diff_path = patches_dir / "latest.diff"
            diff_path.write_text(f"--- Proposal ---\n{plan}", encoding='utf-8')
            
            return f"[TASK COMPLETE] Plan: {plan[:50]}... Path: {diff_path}"
        except Exception as e:
            return f"[ERROR] {str(e)}"