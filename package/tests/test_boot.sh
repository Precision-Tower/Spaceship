#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"
pt_initialize
fail() { pt_status_line "MISSING" "$1" "$2"; exit 1; }
require_contains() { local path="$1" pattern="$2" label="$3"; grep -q -- "$pattern" "$path" || fail "$label" "$path lacks $pattern"; pt_status_line "PASS" "$label" "$pattern"; }
pt_print_line "Precision Tower boot contract test"
require_contains "$PACKAGE_CONFIG" "target: non_graphical" "non-graphical target policy"
require_contains "$PACKAGE_CONFIG" "agency_requires_local_login: false" "no local login dependency policy"
require_contains "$PACKAGE_CONFIG" "desktop_starts_at_boot: false" "desktop on-demand policy"
require_contains "$PACKAGE_ROOT/config/tty-map.conf" "tty1=local_operator_console" "tty1 mapping"
require_contains "$PACKAGE_ROOT/config/tty-map.conf" "tty5=agency_status_console" "tty5 mapping"
require_contains "$PACKAGE_SYSTEMD/agency-console@.service" "TTYPath=/dev/%I" "console service tty binding"
require_contains "$PACKAGE_SYSTEMD/agency.service.unresolved" "AGENCY_COMMAND unresolved" "agency unresolved boot guard"
pt_status_line "PASS" "boot contract" "repository-local policy and unresolved service templates are present"