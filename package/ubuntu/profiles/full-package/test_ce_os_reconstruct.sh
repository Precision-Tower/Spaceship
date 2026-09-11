#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WT="$(cd -P "$ROOT/../../../.." && pwd)"
SEED="$WT/trash/tmp/package-seed-proof"
TMP="$(mktemp -d "$WT/trash/tmp/full-package-reconstruct-test.XXXXXXXX")"
trap 'rm -rf "$TMP"' EXIT

[[ -d "$SEED" ]] || {
    echo "ERROR: proof seed absent: $SEED"
    exit 1
}

"$ROOT/ce-os-reconstruct" \
    --dry-run \
    --seed "$SEED" \
    --target "$TMP/dry-run-target"

[[ ! -e "$TMP/dry-run-target" ]]
echo "DRY_RUN_ZERO_TARGET_MUTATION=PASS"

"$ROOT/ce-os-reconstruct" \
    --apply \
    --seed "$SEED" \
    --target "$TMP/reconstructed"

test -f "$TMP/reconstructed/.ce-os-reconstruction/state"
grep -q '^status=reconstructed_from_verified_seed$' \
    "$TMP/reconstructed/.ce-os-reconstruction/state"

echo "DISPOSABLE_RECONSTRUCTION_APPLY=PASS"

mkdir -p "$TMP/occupied"
printf 'preserve-me\n' > "$TMP/occupied/sentinel"
before="$(sha256sum "$TMP/occupied/sentinel" | awk '{print $1}')"

if "$ROOT/ce-os-reconstruct" \
    --apply \
    --seed "$SEED" \
    --target "$TMP/occupied" >/dev/null 2>&1
then
    echo "FAIL: occupied target was accepted"
    exit 1
fi

after="$(sha256sum "$TMP/occupied/sentinel" | awk '{print $1}')"
[[ "$before" == "$after" ]]
echo "OCCUPIED_TARGET_REJECTION=PASS"
echo "DISPOSABLE_ONLY=PASS"
