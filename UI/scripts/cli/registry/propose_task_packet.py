#!/usr/bin/env python3
import sys
import json
import argparse

def propose_task_packet(intent: str) -> dict:
    """
    Deterministic heuristic parser to transform operational intent into a task packet.
    """
    intent_lower = intent.lower()
    
    # Default placeholder values
    objective = f"Implement intent: '{intent}'"
    inspect = ["Dashboard/UI/"]
    allowed = ["Modify .py and .gd files"]
    forbidden = ["Do not bypass existing security boundaries", "Do not modify .godot files"]
    test = [f"Verify behavior of '{intent}' manually"]
    success = ["Behavior is observable and verified"]
    report = "Provide modified files and test output."

    # Heuristics
    if "connect" in intent_lower and "gear" in intent_lower:
        objective = "Establish a bridged operational connection between Gear and Dashboard cockpit."
        inspect = [
            "Dashboard/UI/screen/scripts/runtime/CliBridge.gd",
            "Dashboard/UI/scripts/cli/dashboard_cli.py"
        ]
        test = ["Execute a remote command from UI.scriptsr and capture output in Dashboard terminal."]
        success = ["Cali confirms Gear is linked and authority handoff is possible."]
    elif "observe" in intent_lower:
        objective = "Perform an automated directory observation to synchronize state."
        inspect = ["Dashboard/UI/scripts/cli/commands/cali_observe_directory.py"]
        test = ["Run cali-observe-directory --root ."]
        success = ["Observation report is generated and displayed in UI."]

    packet = {
        "ok": True,
        "status": "proposal_generated",
        "intent": intent,
        "proposal": {
            "OBJECTIVE": objective,
            "INSPECT": inspect,
            "ALLOWED": allowed,
            "FORBIDDEN": forbidden,
            "TEST": test,
            "SUCCESS": success,
            "REPORT": report
        }
    }
    return packet

def run(args):
    result = propose_task_packet(args.intent)
    print(json.dumps(result))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--intent", type=str, required=True)
    args = parser.parse_args()
    
    run(args)
