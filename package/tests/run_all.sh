#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
failures=0
for test_script in test_boot.sh test_services.sh test_remote_access.sh test_hardware_readiness.sh test_machine_profiles.sh test_ubuntu_substrate.sh test_reconstruction.sh test_qps_bootstrap.sh test_operator_commands.sh test_installation.sh; do
    printf '\n== %s ==\n' "$test_script"
    if "$SCRIPT_DIR/$test_script"; then printf 'PASS %s\n' "$test_script"; else printf 'FAIL %s\n' "$test_script"; failures=$((failures + 1)); fi
done
printf '\nPackage tests complete: %s failure(s)\n' "$failures"
exit "$failures"
