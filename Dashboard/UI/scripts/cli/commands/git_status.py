from runtime.paths import resolve_target_root
from runtime.git_tools import run_git

def run(args):
    root = resolve_target_root(args.root)
    code, out, err = run_git(root, ["status", "--short"])
    print("GIT_STATUS")
    print(f"root: {root}")
    if code != 0:
        print("status: git_error")
        print(err.strip())
        return
    print("status: clean" if not out.strip() else "status: changes_present")
    print(out.strip() or "(no changes)")
