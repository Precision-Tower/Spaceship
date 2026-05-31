#!/usr/bin/env python3
import json
import argparse
from pathlib import Path

def propose_diff(intent: str, scope: str) -> dict:
    """
    Simulates a diff proposal based on intent and scope.
    Enforces RISK_BOUNDARY_VIOLATION if Engineering/ is touched.
    """
    # Safety logic: Strictly restricted to Dashboard/
    # If scope or intent involves Engineering/, flag violation.
    
    # Normalize
    scope_clean = scope.replace("\\", "/").strip("/")
    intent_lower = intent.lower()
    
    # Boundary logic
    is_in_engineering = "engineering" in scope_clean.lower() or "engineering" in intent_lower
    is_in_dashboard = "dashboard" in scope_clean.lower() or "dashboard" in intent_lower
    
    risk_boundary = "SAFE_ZONE"
    status = "diff_generated"
    ok = True
    
    # The logic must strictly enforce that the file scope is restricted to Dashboard/.
    if is_in_engineering:
        risk_boundary = "RISK_BOUNDARY_VIOLATION"
        status = "blocked_by_safety_boundary"
        ok = False
    elif not is_in_dashboard and scope_clean not in [".", ""]:
        risk_boundary = "RISK_BOUNDARY_VIOLATION"
        status = "blocked_by_safety_boundary"
        ok = False

    # Simulate diff content (git diff --no-index style)
    diff_lines = []
    if ok:
        diff_lines = [
            f"--- a/{scope_clean}/simulation.py",
            f"+++ b/{scope_clean}/simulation.py",
            "@@ -1,1 +1,1 @@",
            "- # baseline_state",
            f"+ # applied_intent: {intent}"
        ]

    return {
        "ok": ok,
        "status": status,
        "intent": intent,
        "scope": scope,
        "RISK_BOUNDARY": risk_boundary,
        "diff": "\n".join(diff_lines),
        "files_touched": [f"{scope_clean}/simulation.py"] if ok else []
    }

def run(args):
    """Entry point for CLI spine."""
    result = propose_diff(args.intent, args.scope)
    print(json.dumps(result))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--intent", type=str, required=True)
    parser.add_argument("--scope", type=str, default="Dashboard/")
    args = parser.parse_args()
    run(args)