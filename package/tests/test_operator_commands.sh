#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"
pt_initialize
fail() { pt_status_line "MISSING" "$1" "$2"; exit 1; }
pt_print_line "Precision Tower operator command test"
while IFS= read -r script; do bash -n "$script" || fail "bash syntax" "$script"; pt_status_line "PASS" "bash syntax" "$script"; done < <(find "$PACKAGE_ROOT" -type f \( -name '*.sh' -o -path "$PACKAGE_ROOT/commands/*" \) | sort)
while IFS= read -r command_name; do path="$PACKAGE_COMMANDS/$command_name"; [[ -x "$path" ]] || fail "$command_name wrapper" "$path is not executable"; grep -q "^$command_name$" "$PACKAGE_MANIFESTS/commands.txt" || fail "$command_name manifest" "command missing from manifest"; pt_status_line "PASS" "$command_name wrapper" "$path"; done < <(pt_operator_commands)
safe_invocations=("$PACKAGE_COMMANDS/help" "$PACKAGE_COMMANDS/status" "$PACKAGE_COMMANDS/doctor" "$PACKAGE_COMMANDS/logs" "$PACKAGE_COMMANDS/browser --check" "$PACKAGE_COMMANDS/desktop --check" "$PACKAGE_COMMANDS/dashboard --check" "$PACKAGE_COMMANDS/update --check" "$PACKAGE_COMMANDS/restart --check" "$PACKAGE_COMMANDS/shutdown --check")
for invocation in "${safe_invocations[@]}"; do if bash -lc "$invocation" >/tmp/precision-tower-command-test.out 2>&1; then pt_status_line "PASS" "command check" "$invocation"; else cat /tmp/precision-tower-command-test.out; fail "command check" "$invocation exited nonzero"; fi; done
rm -f /tmp/precision-tower-command-test.out
pt_status_line "PASS" "operator commands" "safe command checks completed"