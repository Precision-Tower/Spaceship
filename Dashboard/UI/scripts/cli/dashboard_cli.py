import sys
from pathlib import Path

CLI_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = CLI_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import argparse
from commands import scan_repo, git_status, propose_directory_diff, grant_review, apply_patch

def build_parser():
    parser = argparse.ArgumentParser(prog="dashboard_cli", description="DashBoard CLI spine")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("scan-repo")
    p.add_argument("--root", default=None)
    p.set_defaults(func=scan_repo.run)

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

    return parser

def main():
    args = build_parser().parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
