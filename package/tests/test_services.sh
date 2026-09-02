#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"
pt_initialize
fail() { pt_status_line "MISSING" "$1" "$2"; exit 1; }
require_file() { [[ -f "$1" ]] || fail "service file" "$1"; pt_status_line "PASS" "service file" "$1"; }
require_contains() { local path="$1" pattern="$2" label="$3"; grep -Fq -- "$pattern" "$path" || fail "$label" "$path lacks $pattern"; pt_status_line "PASS" "$label" "$pattern"; }
reject_contains() { local path="$1" pattern="$2" label="$3"; if grep -Eiq -- "$pattern" "$path"; then fail "$label" "$path contains forbidden pattern $pattern"; fi; pt_status_line "PASS" "$label" "absent"; }
pt_print_line "Precision Tower systemd template test"
[[ ! -e "$PACKAGE_SYSTEMD/agency.service" ]] || fail "agency.service" "installable agency.service must not exist while AGENCY_COMMAND is unresolved"
pt_status_line "PASS" "agency.service" "not installable"
for unit in agency.service.unresolved agency-health.service agency-console@.service; do
    path="$PACKAGE_SYSTEMD/$unit"
    require_file "$path"
    require_contains "$path" "[Unit]" "$unit unit section"
    require_contains "$path" "[Service]" "$unit service section"
    reject_contains "$path" "AUTH_KEY=|PASSWORD=|PRIVATE_KEY=|SECRET=" "$unit embedded secret check"
done
require_contains "$PACKAGE_SYSTEMD/agency.service.unresolved" "no persistent Agency runtime" "agency unresolved command guard"
require_contains "$PACKAGE_SYSTEMD/agency-health.service" "package/commands/doctor" "health uses doctor wrapper"
require_contains "$PACKAGE_SYSTEMD/agency-console@.service" "package/commands/status" "console uses status wrapper"
pt_status_line "PASS" "systemd templates" "Agency daemon unit is reclassified as unresolved and no unit is installed"