import sys
from pathlib import Path

CLI_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = CLI_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import argparse
from commands import (
    scan_repo,
    git_status,
    propose_directory_diff,
    grant_review,
    apply_patch,
    runtime_state,
    view_latest_diff,
    grant_review_latest_diff,
    clear_latest_diff,
    list_packets,
    create_packet,
    test_all,
    cali_observe_directory,
    list_agents,
    propose_diff,
)
from registry import propose_task_packet

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

    return parser

def main():
    args = build_parser().parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
