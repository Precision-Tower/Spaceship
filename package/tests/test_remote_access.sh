#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"
pt_initialize
fail() { pt_status_line "MISSING" "$1" "$2"; exit 1; }
pt_print_line "Precision Tower remote-access contract test"
output="$($PACKAGE_VERIFY 2>&1)" || fail "verify" "verify.sh exited nonzero"
printf '%s\n' "$output" | grep -qi "tailscale" || fail "tailscale verification" "verify output lacks tailscale status"
printf '%s\n' "$output" | grep -qi "ssh" || fail "ssh verification" "verify output lacks ssh status"
printf '%s\n' "$output" | grep -qi "ufw" || fail "ufw verification" "verify output lacks ufw status"
if printf '%s\n' "$output" | grep -qi "need to be root"; then fail "ufw output" "raw privileged-tool error leaked instead of operator meaning"; fi
grep -q "tailscale_private_network" "$PACKAGE_ROOT/config/firewall.rules" || fail "firewall policy" "tailscale private network not declared"
grep -q "public_internet_exposure=forbidden" "$PACKAGE_ROOT/config/firewall.rules" || fail "firewall policy" "public SSH exposure policy missing"
grep -q "router_port_forwarding=forbidden" "$PACKAGE_ROOT/config/firewall.rules" || fail "firewall policy" "router forwarding policy missing"
pt_status_line "PASS" "remote access policy" "verification and firewall template preserve private-network requirement"