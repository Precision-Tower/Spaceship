import sys
from pathlib import Path

from UI.scripts.cli.commands import apply_patch, cali_observe_directory, clear_latest_diff, create_packet, gemini_analyze, gemini_list_models, git_status, grant_review, grant_review_latest_diff, list_agents, list_packets, propose_diff, propose_directory_diff, runtime_state, scan_repo, test_all, update_state

CLI_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = CLI_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import argparse
from UI.scripts.cli.commands import (
    view_latest_diff,
)
from UI.scripts.cli.registry import propose_task_packet

class CommandValidator:
    """
    Enforces authority boundaries by cross-referencing CLI commands
    against the registered authority in commands.yaml.
    """
    REGISTRY_PATH = CLI_DIR / "registry" / "commands.yaml"

    @classmethod
    def is_authorized(cls, cli_name):
        try:
            import yaml
            with open(cls.REGISTRY_PATH, 'r') as f:
                config = yaml.safe_load(f)
            
            commands = config.get("commands", {})
            # Check if the command exists and has an authority assigned
            for cmd_info in commands.values():
                if cmd_info.get("cli_name") == cli_name:
                    authority = cmd_info.get("authority")
                    if authority in ["read_only", "propose_only", "review_only", "requires_approval"]:
                        return True, authority
            
            return False, "Unregistered or missing authority"
        except ImportError:
            # If yaml is missing, we fail-safe to read-only for known core commands
            # until the environment is stabilized.
            core_read_only = ["scan-repo", "git-status", "list-agents"]
            if cli_name in core_read_only:
                return True, "read_only (fallback)"
            return False, "Registry environment unavailable (PyYAML missing)"
        except Exception as e:
            return False, f"Registry error: {str(e)}"

    @classmethod
    def validate_and_dispatch(cls, args):
        authorized, authority_level = cls.is_authorized(args.command)
        
        if not authorized:
            print(f"CRITICAL: Unauthorized Command Attempt: '{args.command}'", file=sys.stderr)
            print(f"Reason: {authority_level}", file=sys.stderr)
            sys.exit(1)

        if authority_level == "requires_approval":
            # Enforcement Gate: Block dispatch if the approval flag is missing.
            # This prevents control from UI.scriptsching the command implementation (run)
            # without the prerequisite authorization artifact.
            if not getattr(args, "approved", False):
                print(f"CRITICAL: Command '{args.command}' requires explicit approval (--approved). Dispatch aborted.", file=sys.stderr)
                sys.exit(1)
            
        args.func(args)

def build_parser():
    parser = argparse.ArgumentParser(prog="dashboard_cli", description="DashBoard CLI spine")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("scan-repo")
    p.add_argument("--root", default=None)
    p.set_defaults(func=scan_repo.run)

    p = sub.add_parser("runtime-state")
    p.add_argument("--root", default=None)
    p.set_defaults(func=runtime_state.run)

    p = sub.add_parser("git-status")
    p.add_argument("--root", default=None)
    p.set_defaults(func=git_status.run)

    p = sub.add_parser("propose-directory-diff")
    p.add_argument("--root", default=None)
    p.set_defaults(func=propose_directory_diff.run)

    p = sub.add_parser("grant-review")
    p.add_argument("--diff", required=True)
    p.set_defaults(func=grant_review.run)

    p = sub.add_parser("apply-patch")
    p.add_argument("--root", default=None)
    p.add_argument("--diff", required=True)
    p.add_argument("--approved", action="store_true")
    p.set_defaults(func=apply_patch.run)

    p = sub.add_parser("view-latest-diff")
    p.set_defaults(func=view_latest_diff.run)

    p = sub.add_parser("grant-review-latest-diff")
    p.set_defaults(func=grant_review_latest_diff.run)

    p = sub.add_parser("clear-latest-diff")
    p.set_defaults(func=clear_latest_diff.run)

    p = sub.add_parser("list-packets")
    p.set_defaults(func=list_packets.run)

    p = sub.add_parser("create-packet")
    p.add_argument("--category", default=None)
    p.add_argument("--title", default=None)
    p.set_defaults(func=create_packet.run)

    p = sub.add_parser("test-all")
    p.add_argument("--root", default=None)
    p.set_defaults(func=test_all.run)

    p = sub.add_parser("cali-observe-directory")
    p.add_argument("--root", default=None)
    p.add_argument("--model-path", default=None)
    p.add_argument("--dry-run-model-path", action="store_true", help="Print resolved model path and exit without generation")
    p.add_argument("--max-files", type=int, default=350)
    p.add_argument("--max-new-tokens", type=int, default=900)
    p.add_argument("--timeout-seconds", type=int, default=None, help="Timeout in seconds for model generation")
    p.set_defaults(func=cali_observe_directory.run)

    p = sub.add_parser("list-agents")
    p.set_defaults(func=list_agents.run)

    p = sub.add_parser("propose-task-packet")
    p.add_argument("--intent", required=True)
    p.set_defaults(func=propose_task_packet.run)

    p = sub.add_parser("propose-diff")
    p.add_argument("--intent", required=True)
    p.add_argument("--scope", default="Dashboard/")
    p.set_defaults(func=propose_diff.run)

    p = sub.add_parser("gemini-analyze")
    p.add_argument("--purpose", required=True)
    p.add_argument("--context", required=True)
    p.set_defaults(func=gemini_analyze.run)

    p = sub.add_parser("gemini-list-models")
    p.set_defaults(func=gemini_list_models.run)

    p = sub.add_parser("update-state")
    p.add_argument("--key", choices=["status", "interaction"], required=True)
    p.add_argument("--value", required=True)
    p.add_argument("--purpose", default=None)
    p.add_argument("--lane", default="global")
    p.set_defaults(func=update_state.run)

    return parser

def main():
    args = build_parser().parse_args()
    CommandValidator.validate_and_dispatch(args)

if __name__ == "__main__":
    main()

