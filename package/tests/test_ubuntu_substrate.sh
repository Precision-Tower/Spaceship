#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"
pt_initialize

fail() {
    pt_status_line "MISSING" "$1" "$2"
    exit 1
}

index="$PACKAGE_ROOT/ubuntu/_index.qps"
user_data="$PACKAGE_ROOT/ubuntu/autoinstall/user-data.template"
meta_data="$PACKAGE_ROOT/ubuntu/autoinstall/meta-data"

[[ -f "$index" ]] || fail "ubuntu authority" "$index missing"
[[ -f "$user_data" ]] || fail "autoinstall template" "$user_data missing"
[[ -f "$meta_data" ]] || fail "autoinstall metadata" "$meta_data missing"

grep -q 'exact_release- "UNRESOLVED"' "$index" ||
    fail "ubuntu release gate" "exact Ubuntu release must remain unresolved until image verification"

grep -q '__CEOS_REVIEWED_STORAGE_CONFIGURATION__' "$user_data" ||
    fail "storage safety" "tracked template unexpectedly lost reviewed-storage gate"

grep -q '__CEOS_ADMIN_SSH_PUBLIC_KEY__' "$user_data" ||
    fail "credential injection" "tracked template unexpectedly lost SSH key injection gate"

if grep -Eq '/dev/(sd[a-z]|nvme[0-9])' "$user_data"; then
    fail "storage safety" "tracked autoinstall template selects a concrete disk"
fi

if grep -Eq 'BEGIN (OPENSSH|RSA|EC) PRIVATE KEY' "$user_data"; then
    fail "secret safety" "tracked autoinstall template contains a private key"
fi

pt_status_line "PASS" "Ubuntu substrate" "stable LTS substrate authority is explicit"
pt_status_line "PASS" "autoinstall safety" "credentials and destructive storage remain unresolved"
pt_status_line "PASS" "boot-media boundary" "package contains inputs only; no media writer is activated"
