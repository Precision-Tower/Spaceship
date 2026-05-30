from argparse import Namespace
from pathlib import Path
from runtime.paths import PATCH_DIR
from commands import grant_review


def run(args):
    latest = PATCH_DIR / "latest.diff"
    print("GRANT_REVIEW_LATEST_DIFF")
    if not latest.exists():
        print("status: blocked")
        print("reason: latest.diff not found")
        return

    review_args = Namespace(diff=str(latest))
    grant_review.run(review_args)
