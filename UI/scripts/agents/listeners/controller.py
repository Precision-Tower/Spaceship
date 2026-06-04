import json
import threading
from UI.scripts.agents.core.engine import WeeboAgent
from UI.scripts.agents.core.bridge import CaliBridge

class WeeboController:
    def __init__(self, agent: WeeboAgent, bridge: CaliBridge, interrupt_path):
        self.agent = agent
        self.bridge = bridge
        self.interrupt_flag_path = interrupt_path
        self.worker_thread = None
        self.worker_result = None
        self.worker_error = None

    def trigger_wake(self):
        """Logic for when the wake word is detected."""
        print(f"\n[WOKE UP] WEEBO: Yes, operator?")
        
        # 1. Dashboard launch logic (Moved from UI.scriptstener)
        # Note: You can import your launch_dashboard function here or keep it in the listener
        from UI.scripts.listeners.weebo_wake import launch_dashboard
        launch_dashboard()
        
        # 2. UI bridge update
        try:
            self.bridge._exec("update-state --key status --value active")
        except Exception:
            pass

    def execute_command(self, command: str):
        """Starts a background thread to process the voice command."""
        print(f"\nOperator: {command}")
        
        if command in ["exit", "stop", "quit"]:
            return "EXIT"

        print(f"[*] WEEBO is processing...")
        self.worker_thread = threading.Thread(
            target=self._worker_target,
            args=(command,),
            daemon=True
        )
        self.worker_thread.start()
        return "PROCESSING"

    def _worker_target(self, command: str):
        try:
            self.worker_result = self.agent.process_command(command)
        except Exception as e:
            self.worker_error = e

    def trigger_interrupt(self):
        """Halts the current worker operation."""
        print(f"\n[INTERRUPTING] WEEBO: Halting current operation...")
        self.interrupt_flag_path.write_text("1")
        
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
            self.worker_thread = None
        
        print(f"WEEBO: Stopped task. What do you need me to work on?")

    def check_worker_status(self):
        """Returns the result if finished, otherwise None."""
        if self.worker_thread and not self.worker_thread.is_alive():
            result = self.worker_result
            error = self.worker_error
            # Reset
            self.worker_thread = None
            self.worker_result = None
            self.worker_error = None
            return {"result": result, "error": error}
        return None