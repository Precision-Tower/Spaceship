#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
source "$SCRIPT_DIR/lib/hardware.sh"
pt_initialize
PT_RUNTIME_TMP_ROOT="${PT_RUNTIME_TMP_ROOT:-$REPO_ROOT/trash/tmp/package-runtime}"
mkdir -p "$PT_RUNTIME_TMP_ROOT"
FATALS=0
fatal_line() { pt_status_line "$@"; FATALS=$((FATALS + 1)); }
version_line() { pt_have_command "$1" && pt_run_quick 5 "$@" 2>&1 | head -n 1 || true; }
active_service() { pt_have_command systemctl && pt_run_quick 5 systemctl is-active --quiet "$1" >/dev/null 2>&1; }
check_file() { local label="$1" path="$2"; [[ -f "$path" ]] && pt_status_line "PASS" "$label" "$path" || pt_status_line "MISSING" "$label" "$path"; }
check_executable() { local label="$1" path="$2"; if [[ -x "$path" ]]; then pt_status_line "PASS" "$label" "$path"; elif [[ -e "$path" ]]; then pt_status_line "WARNING" "$label" "$path exists but is not executable"; else pt_status_line "MISSING" "$label" "$path"; fi; }
check_os() {
    if [[ ! -r /etc/os-release ]]; then pt_status_line "WARNING" "operating system" "/etc/os-release is not readable"; return; fi
    source /etc/os-release
    if [[ "${ID:-}" == "ubuntu" && "${VERSION:-}" == *LTS* ]]; then pt_status_line "PASS" "operating system" "${PRETTY_NAME:-Ubuntu LTS}"; elif [[ "${ID:-}" == "ubuntu" ]]; then pt_status_line "WARNING" "operating system" "${PRETTY_NAME:-Ubuntu} (LTS status not proven)"; else pt_status_line "WARNING" "operating system" "${PRETTY_NAME:-unknown}; target expects Ubuntu LTS"; fi
}
check_host_commands() {
    local brave="" xfce=""
    pt_have_command python3 && pt_status_line "PASS" "python3" "$(version_line python3 --version)" || pt_status_line "MISSING" "python3" "python3 not found in PATH"
    pt_have_command git && pt_status_line "PASS" "git" "$(version_line git --version)" || pt_status_line "MISSING" "git" "git not found in PATH"
    brave="$(pt_brave_command || true)"; [[ -n "$brave" ]] && pt_status_line "PASS" "brave" "$brave" || pt_status_line "MISSING" "brave" "Brave executable not found in PATH"
    pt_have_command wine && pt_status_line "PASS" "wine" "$(version_line wine --version)" || pt_status_line "MISSING" "wine" "wine not found in PATH"
    xfce="$(pt_xfce_command || true)"; [[ -n "$xfce" ]] && pt_status_line "PASS" "xfce" "$xfce" || pt_status_line "MISSING" "xfce" "startxfce4 or xfce4-session not found in PATH"
}
check_remote_services() {
    if pt_have_command tailscale; then
        if active_service tailscaled || pt_run_quick 5 tailscale status >/dev/null 2>&1; then pt_status_line "PASS" "tailscale" "installed and status is reachable"; else pt_status_line "WARNING" "tailscale" "installed, but active-state verification did not complete"; fi
    else pt_status_line "MISSING" "tailscale" "tailscale not found in PATH"; fi
    if pt_have_command sshd || [[ -x /usr/sbin/sshd ]]; then
        if active_service ssh || active_service sshd; then pt_status_line "PASS" "ssh" "sshd found and service is active"; else pt_status_line "WARNING" "ssh" "sshd found, but running state is not proven"; fi
    else pt_status_line "MISSING" "openssh-server" "sshd not found"; fi
    if pt_have_command ufw; then
        local output=""; output="$(pt_run_quick 5 ufw status 2>&1 | head -n 1 || true)"
        if [[ "$output" == *"Status: active"* ]]; then pt_status_line "PASS" "ufw" "installed and active"; elif [[ "$output" == *"need to be root"* || "$output" == *"Need to be root"* ]]; then pt_status_line "WARNING" "ufw" "installed, but active-state verification requires elevated privileges"; else pt_status_line "WARNING" "ufw" "installed, but active state is not proven"; fi
    else pt_status_line "MISSING" "ufw" "ufw not found in PATH"; fi
    if pt_have_command systemctl; then
        local version=""; version="$(pt_run_quick 5 systemctl --version 2>/dev/null | head -n 1 || true)"
        [[ -d /run/systemd/system ]] && pt_status_line "PASS" "systemd" "${version:-systemctl available}; runtime directory present" || pt_status_line "WARNING" "systemd" "${version:-systemctl available}; /run/systemd/system not present"
    else pt_status_line "MISSING" "systemd" "systemctl not found in PATH"; fi
}
check_godot_path() { local path=""; path="$(pt_godot_path || true)"; if [[ -z "$path" ]]; then pt_status_line "UNRESOLVED" "godot path" "no repository Godot path reference detected"; elif [[ -e "$path" ]]; then pt_status_line "PASS" "godot path" "$path exists"; else pt_status_line "MISSING" "godot path" "$path does not exist"; fi; }
check_package_surface() {
    local item command_name
    check_file "package manifest" "$PACKAGE_MANIFESTS/packages.txt"
    check_file "command manifest" "$PACKAGE_MANIFESTS/commands.txt"
    for item in base desktop diagnostics wine; do check_file "package list $item" "$PACKAGE_PACKAGE_LISTS/$item.txt"; done
    for item in default.env.example firewall.rules hardware.env tty-map.conf; do check_file "config $item" "$PACKAGE_ROOT/config/$item"; done
    check_file "hardware helper" "$PACKAGE_ROOT/lib/hardware.sh"
    if [[ -e "$PACKAGE_SYSTEMD/agency.service" ]]; then pt_status_line "WARNING" "systemd agency.service" "installable agency.service exists despite unresolved AGENCY_COMMAND"; else pt_status_line "PASS" "systemd agency.service" "not present; Agency service is intentionally non-installable"; fi
    check_file "systemd unresolved agency draft" "$PACKAGE_SYSTEMD/agency.service.unresolved"
    check_file "systemd draft agency-health.service" "$PACKAGE_SYSTEMD/agency-health.service"
    check_file "systemd draft agency-console@.service" "$PACKAGE_SYSTEMD/agency-console@.service"
    while IFS= read -r command_name; do check_executable "$command_name wrapper" "$PACKAGE_COMMANDS/$command_name"; done < <(pt_operator_commands)
    for item in run_all.sh test_boot.sh test_services.sh test_remote_access.sh test_hardware_readiness.sh test_operator_commands.sh test_installation.sh; do check_executable "package test $item" "$PACKAGE_TESTS/$item"; done
}
check_installed_surface() {
    local command_name dest src target
    pt_print_line; pt_print_line "Installed wrapper/env state"
    while IFS= read -r command_name; do
        dest="$PRECISION_BIN_DIR/$command_name"; src="$PACKAGE_COMMANDS/$command_name"
        if [[ -L "$dest" ]]; then target="$(readlink "$dest")"; [[ "$target" == "$src" ]] && pt_status_line "PASS" "installed $command_name" "$dest -> $target" || pt_status_line "WARNING" "installed $command_name" "$dest points to $target, not package wrapper"; elif [[ -e "$dest" ]]; then pt_status_line "WARNING" "installed $command_name" "$dest exists and is not a package symlink"; else pt_status_line "WARNING" "installed $command_name" "$dest is not installed"; fi
    done < <(pt_operator_commands)
    if [[ -f "$PRECISION_ENV_FILE" ]] && grep -q '^# Managed by Dashboard CE-OS package$' "$PRECISION_ENV_FILE"; then pt_status_line "PASS" "machine env" "$PRECISION_ENV_FILE"; elif [[ -e "$PRECISION_ENV_FILE" ]]; then pt_status_line "WARNING" "machine env" "$PRECISION_ENV_FILE exists but is not package-managed"; else pt_status_line "WARNING" "machine env" "$PRECISION_ENV_FILE is not installed"; fi
}
print_unresolved() {
    pt_print_line; pt_print_line "Unresolved deployment inputs"
    pt_status_line "UNRESOLVED" "agency_service_entrypoint" "No persistent Agency service command has been selected or proven."
    pt_status_line "UNRESOLVED" "tailscale_enrollment_method" "No auth key, interactive enrollment, or machine-local secret path selected."
    pt_status_line "UNRESOLVED" "ssh_administrator_public_key" "No administrator public key path selected."
    pt_status_line "UNRESOLVED" "wine_application" "Windows application installer, architecture, dependencies, and license are unknown."
    pt_status_line "UNRESOLVED" "nvidia_driver_package" "Hardware detection is implemented; driver installation package policy is not selected."
    pt_status_line "UNRESOLVED" "cuda_installation_policy" "CUDA detection is implemented; package-managed CUDA installation is not implemented."
    pt_status_line "UNRESOLVED" "firewall_interface_policy" "Tailscale interface and any additional service openings must be verified on target hardware."
    pt_status_line "UNRESOLVED" "bios_restore_on_ac_power_loss" "Firmware setting cannot be proven from the repository."
    pt_status_line "UNRESOLVED" "durant_acceptance_test" "Requires real target hardware and external remote device."
}
main() {
    pt_print_line "CE-OS Node package verification"
    pt_require_dashboard_root && pt_status_line "PASS" "repository root" "$REPO_ROOT" || FATALS=$((FATALS + 1))
    [[ -f "$PACKAGE_CONFIG" ]] && pt_status_line "PASS" "package config" "$PACKAGE_CONFIG" || fatal_line "MISSING" "package config" "$PACKAGE_CONFIG"
    [[ -f "$REPO_ROOT/Docs/PrecisionTowerNode.md" ]] && pt_status_line "PASS" "contract doc" "$REPO_ROOT/Docs/PrecisionTowerNode.md" || pt_status_line "WARNING" "contract doc" "Docs/PrecisionTowerNode.md is not present in this checkout"
    pt_print_line; pt_print_line "Host capabilities"; check_os; check_host_commands; check_remote_services
    pt_print_line; pt_print_line "Hardware readiness"; pt_hardware_acceptance_report || true
    pt_print_line; pt_print_line "Repository runtime authorities"; check_file "runtime profiles" "$REPO_ROOT/Agency/Core/runtime/runtime_profiles.yaml"; check_file "model manager" "$REPO_ROOT/Agency/Core/runtime/model_server_manager.py"; check_file "pty service" "$REPO_ROOT/Agency/Core/runtime/terminal/pty_service.py"; check_file "path authority" "$REPO_ROOT/Agency/Core/paths.py"; [[ -d "$REPO_ROOT/local" ]] && pt_status_line "PASS" "machine-local state" "$REPO_ROOT/local" || pt_status_line "WARNING" "machine-local state" "$REPO_ROOT/local is not present"; check_godot_path
    pt_print_line; pt_print_line "Agency runtime classification"; pt_agency_runtime_status
    pt_print_line; pt_print_line "Deployment package surface"; check_package_surface; check_installed_surface; print_unresolved
    pt_print_line; (( FATALS > 0 )) && { pt_status_line "MISSING" "package operability" "$FATALS fatal condition(s)"; return 1; }
    pt_status_line "PASS" "package operability" "verification completed without fatal package defects"
}
main "$@"
