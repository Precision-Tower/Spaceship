from pathlib import Path

RISK_PATTERNS = ["validated", "operational_readiness", "safe", "evidence", "truth", "canon", "fixed", "updated", "completed", "stable"]

def run(args):
    diff_path = Path(args.diff).resolve()
    print("GRANT_REVIEW")
    print(f"diff: {diff_path}")
    if not diff_path.exists():
        print("Status: blocked")
        print("Reason: diff not found")
        return
    text = diff_path.read_text(encoding="utf-8", errors="replace")
    hits = sorted({p for p in RISK_PATTERNS if p.lower() in text.lower()})
    print("Status: admissible_with_warnings" if hits else "Status: admissible")
    print("Observed Risks:")
    if hits:
        for h in hits:
            print(f"- risk_pattern_detected: {h}")
    else:
        print("- none_detected_by_simple_scan")
    print("Authority Boundary:")
    print("- lexical review only; not full semantic governance")
    print("- no filesystem mutation claim made")
