from runtime.paths import resolve_target_root, scan_files

def run(args):
    root = resolve_target_root(args.root)
    files = scan_files(root)
    print("SCAN_REPO")
    print(f"root: {root}")
    print(f"files_detected: {len(files)}")
    for f in files[:250]:
        print(f"- {f}")
    if len(files) > 250:
        print(f"... truncated {len(files) - 250} more files")
