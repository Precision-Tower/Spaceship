#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"
pt_initialize

fail() {
    pt_status_line "MISSING" "$1" "$2"
    exit 1
}

seed="$REPO_ROOT/trash/tmp/package-seed-proof"
root="$PT_TEST_TMP_ROOT/reconstruction-contract"
target="$root/target"
bad="$root/bad-target"

rm -rf "$root"
mkdir -p "$root"

"$PACKAGE_ROOT/reconstruct.sh" \
    --dry-run \
    --seed "$seed" \
    --target "$target" \
    >"$root/dry-run.out"

[[ ! -e "$target" ]] ||
    fail "dry-run mutation" "$target was created"

grep -q 'DRY-RUN seed verified' "$root/dry-run.out" ||
    fail "dry-run verification" "verified-seed report absent"

"$PACKAGE_ROOT/reconstruct.sh" \
    --apply \
    --seed "$seed" \
    --target "$target" \
    >"$root/apply.out"

[[ -f "$target/_index.qps" ]] ||
    fail "reconstruction authority" "_index.qps missing"

[[ -f "$target/.ce-os-reconstruction/seed-identity.json" ]] ||
    fail "reconstruction metadata" "seed identity missing"

grep -q '^status=reconstructed_from_verified_seed$' \
    "$target/.ce-os-reconstruction/state" ||
    fail "reconstruction state" "accepted state missing"

mkdir -p "$bad"
printf 'occupied\n' > "$bad/existing"

set +e
"$PACKAGE_ROOT/reconstruct.sh" \
    --apply \
    --seed "$seed" \
    --target "$bad" \
    >"$root/bad.out" 2>&1
bad_rc=$?
set -e

[[ "$bad_rc" -ne 0 ]] ||
    fail "occupied target" "non-empty target unexpectedly accepted"

[[ "$(cat "$bad/existing")" == "occupied" ]] ||
    fail "failure integrity" "existing target content changed"

pt_status_line "PASS" "reconstruction dry-run" "verified seed causes no target mutation"
pt_status_line "PASS" "reconstruction apply" "verified seed reconstructs disposable CE-OS root"
pt_status_line "PASS" "failure integrity" "non-empty target is rejected without mutation"
