#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"
source "$SCRIPT_DIR/../lib/hardware.sh"
pt_initialize

fail() {
    pt_status_line "MISSING" "$1" "$2"
    exit 1
}

pt_print_line "CE-OS package machine-profile test"

precision="$PACKAGE_ROOT/config/machines/precision-tower.env"
legacy="$PACKAGE_ROOT/config/hardware.env"

[[ -f "$precision" ]] || fail "precision profile" "$precision missing"
[[ -f "$legacy" ]] || fail "legacy policy" "$legacy missing"

cmp -s "$precision" "$legacy" ||
    fail "precision compatibility" "explicit Precision profile does not preserve legacy hardware policy"

resolved="$(PT_MACHINE_PROFILE=precision-tower PT_HARDWARE_POLICY_FILE= pt_hardware_policy_file)"
[[ "$resolved" == "$precision" ]] ||
    fail "profile resolution" "precision-tower resolved to $resolved"

override="$PT_TEST_TMP_ROOT/machine-profile-override.env"
printf 'PT_REQUIRED_ARCHITECTURE="fixture"\n' > "$override"
resolved="$(PT_MACHINE_PROFILE=does-not-exist PT_HARDWARE_POLICY_FILE="$override" pt_hardware_policy_file)"
[[ "$resolved" == "$override" ]] ||
    fail "explicit override" "PT_HARDWARE_POLICY_FILE did not remain authoritative"

resolved="$(PT_MACHINE_PROFILE=does-not-exist PT_HARDWARE_POLICY_FILE= pt_hardware_policy_file)"
[[ "$resolved" == "$legacy" ]] ||
    fail "compatibility fallback" "unknown profile did not fall back to legacy policy"

pt_status_line "PASS" "precision profile" "existing Precision hardware contract preserved exactly"
pt_status_line "PASS" "profile selection" "package-owned machine profile resolution verified"
pt_status_line "PASS" "compatibility override" "PT_HARDWARE_POLICY_FILE remains authoritative"
