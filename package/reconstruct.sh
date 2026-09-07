#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
pt_initialize

MODE="dry-run"
SEED=""
TARGET=""

usage() {
    printf '%s\n' \
      "usage: package/reconstruct.sh [--dry-run|--apply] --seed <seed-root> --target <target-root>"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) MODE="dry-run"; shift ;;
        --apply) MODE="apply"; shift ;;
        --seed) SEED="${2:-}"; shift 2 ;;
        --target) TARGET="${2:-}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done

[[ -n "$SEED" ]] || { echo "missing --seed" >&2; exit 2; }
[[ -n "$TARGET" ]] || { echo "missing --target" >&2; exit 2; }

SEED="$(cd -P "$SEED" && pwd)"
TARGET_PARENT="$(cd -P "$(dirname "$TARGET")" && pwd)"
TARGET="$TARGET_PARENT/$(basename "$TARGET")"

python3 "$PACKAGE_ROOT/tools/verify_seed.py" --seed "$SEED"

if [[ -e "$TARGET" && -n "$(find "$TARGET" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
    echo "target must be absent or empty: $TARGET" >&2
    exit 1
fi

if [[ "$MODE" == "dry-run" ]]; then
    printf '%s\n' "DRY-RUN seed verified"
    printf '%s\n' "DRY-RUN would reconstruct payload into $TARGET"
    printf '%s\n' "DRY-RUN would record reconstruction metadata"
    exit 0
fi

mkdir -p "$TARGET"

rollback() {
    local rc=$?
    if [[ "$rc" -ne 0 ]]; then
        rm -rf "$TARGET"
    fi
    exit "$rc"
}
trap rollback EXIT

cp -a "$SEED/payload/." "$TARGET/"

mkdir -p "$TARGET/.ce-os-reconstruction"
cp "$SEED/metadata/identity.json" "$TARGET/.ce-os-reconstruction/seed-identity.json"
cp "$SEED/metadata/deferred.json" "$TARGET/.ce-os-reconstruction/deferred.json"

cat > "$TARGET/.ce-os-reconstruction/state" <<STATE
status=reconstructed_from_verified_seed
mode=apply
STATE

trap - EXIT

printf '%s\n' "APPLY reconstructed verified seed into $TARGET"
printf '%s\n' "APPLY deferred payload remains explicitly recorded"
