#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP_BASE="${PT_TEST_TMP_ROOT:-$ROOT/trash/tmp/package-tests}"
TMP="$TMP_BASE/machine-enrollment"
rm -rf "$TMP"
mkdir -p "$TMP"

OUT="$TMP/enrollment.json"

python3 "$ROOT/package/tools/enroll_host.py" \
  --root "$ROOT" \
  --machine-profile precision-tower \
  --output "$OUT" >/dev/null

python3 - "$ROOT" "$OUT" <<'PY'
import json, sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
p = Path(sys.argv[2])
d = json.loads(p.read_text())

assert d["identity"] == "package.machine_enrollment"
assert d["ce_os_root"] == str(root)
assert d["machine_profile"] == "precision-tower"
assert d["authorities"]["operator_shell"] == "UI/OperatorShell/_index.qps"
assert d["authorities"]["workbench"] == "UI/Workbench/_index.qps"
assert d["launch_surfaces"]["operator_shell"] == "UI/OperatorShell/project.godot"
assert d["service_policy"]["package_install_does_not_enable_services"] is True
assert d["service_policy"]["unresolved_agency_service_not_installable"] is True
assert d["git"]["commit"]
assert d["status"] in ("candidate", "enrolled")
PY

DRY="$TMP/dry.json"
python3 "$ROOT/package/tools/enroll_host.py" \
  --root "$ROOT" \
  --machine-profile precision-tower \
  --dry-run > "$DRY"

test ! -e "$TMP/dry-run-side-effect"

if python3 "$ROOT/package/tools/enroll_host.py" \
    --root "$ROOT" \
    --machine-profile definitely-not-a-profile \
    --output "$TMP/bad.json" >/dev/null 2>&1; then
    echo 'unknown machine profile unexpectedly accepted' >&2
    exit 1
fi

test ! -e "$TMP/bad.json"

echo 'MACHINE_ENROLLMENT_TEST=PASS'
