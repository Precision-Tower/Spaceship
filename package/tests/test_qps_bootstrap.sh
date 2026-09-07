#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$PACKAGE_ROOT/.." && pwd)"
QPS="${QPS_BIN:-$HOME/.local/bin/qps}"

if [[ ! -x "$QPS" ]]; then
    QPS="$REPO_ROOT/qps/cpp/build-pixel/qps"
fi

[[ -x "$QPS" ]] || {
    echo 'FAIL qps validator unavailable' >&2
    exit 1
}

"$QPS" "$PACKAGE_ROOT/bootstrap/qps-components.qps" --check

PT_RUNTIME_TMP_ROOT="$REPO_ROOT/trash/tmp/package-runtime" \
    "$PACKAGE_ROOT/bootstrap/qps-bootstrap.sh" --check

grep -q '3fce3b5bb0236da2df6d99672afb8a719642eca7' \
    "$PACKAGE_ROOT/bootstrap/qps-components.qps"
grep -q 'bff0e5412db91410d759e2eefbbca3df80a1e672' \
    "$PACKAGE_ROOT/bootstrap/qps-components.qps"

if grep -Eq '/data/data/com\.termux/files/usr/bin/(rg|grep|sed|find|xargs|gawk|diff|patch|coreutils)' \
    "$PACKAGE_ROOT/bootstrap/qps-components.qps" \
    "$PACKAGE_ROOT/bootstrap/qps-bootstrap.sh"; then
    echo 'FAIL bootstrap authority depends on Termux native binaries' >&2
    exit 1
fi

echo 'QPS_BOOTSTRAP_TEST=PASS'
