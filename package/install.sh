#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
source "$SCRIPT_DIR/lib/hardware.sh"
pt_initialize
PT_RUNTIME_TMP_ROOT="${PT_RUNTIME_TMP_ROOT:-$REPO_ROOT/trash/tmp/package-runtime}"
mkdir -p "$PT_RUNTIME_TMP_ROOT"

APPLY=false
for arg in "$@"; do
    case "$arg" in
        --apply) APPLY=true ;;
        --dry-run|--plan) APPLY=false ;;
        -h|--help) pt_print_line "usage: package/install.sh [--dry-run|--apply]"; exit 0 ;;
        *) pt_status_line "WARNING" "usage" "unknown argument: $arg"; exit 2 ;;
    esac
done

SUDO_CMD=()
CREATED_PATHS=()
CREATED_DIRS=()
ROLLBACK_ENABLED=false

rollback() {
    local status="$1"
    [[ "$APPLY" == true && "$ROLLBACK_ENABLED" == true && "$status" -ne 0 ]] || return 0
    pt_print_line
    pt_status_line "WARNING" "rollback" "install failed; removing paths created by this run"
    local i path
    for (( i=${#CREATED_PATHS[@]}-1; i>=0; i-- )); do
        path="${CREATED_PATHS[$i]}"
        if [[ -L "$path" || -f "$path" ]]; then
            "${SUDO_CMD[@]}" rm -f "$path" || true
            pt_status_line "REMOVED" "$path" "rollback"
        fi
    done
    for (( i=${#CREATED_DIRS[@]}-1; i>=0; i-- )); do
        path="${CREATED_DIRS[$i]}"
        "${SUDO_CMD[@]}" rmdir "$path" >/dev/null 2>&1 || true
    done
}
trap 'status=$?; rollback "$status"; exit "$status"' EXIT

usage_context() {
    pt_print_line "CE-OS Node package installer"
    [[ "$APPLY" == true ]] && pt_status_line "PASS" "mode" "apply" || pt_status_line "PASS" "mode" "dry-run"
    pt_status_line "PASS" "repository root" "$REPO_ROOT"
    pt_status_line "PASS" "wrapper destination" "$PRECISION_BIN_DIR"
    pt_status_line "PASS" "environment destination" "$PRECISION_ENV_FILE"
}

require_files() {
    local missing=0 relative command_name
    local required=(
        "Agency/Core/runtime/runtime_profiles.yaml"
        "Agency/Core/runtime/model_server_manager.py"
        "Agency/Core/runtime/terminal/pty_service.py"
        "package/install.sh"
        "package/uninstall.sh"
        "package/verify.sh"
        "package/lib/common.sh"
        "package/lib/hardware.sh"
        "package/config/package.yaml"
        "package/config/default.env.example"
        "package/config/firewall.rules"
        "package/config/hardware.env"
        "package/config/machines/_index.qps"
        "package/config/machines/precision-tower.env"
        "package/config/tty-map.conf"
        "package/manifests/packages.txt"
        "package/manifests/commands.txt"
        "package/packages/base.txt"
        "package/packages/desktop.txt"
        "package/packages/diagnostics.txt"
        "package/packages/wine.txt"
        "package/systemd/agency.service.unresolved"
        "package/systemd/agency-health.service"
        "package/systemd/agency-console@.service"
        "package/tests/run_all.sh"
        "package/tests/test_boot.sh"
        "package/tests/test_services.sh"
        "package/tests/test_remote_access.sh"
        "package/tests/test_hardware_readiness.sh"
        "package/tests/test_machine_profiles.sh"
        "package/tests/test_operator_commands.sh"
        "package/tests/test_installation.sh"
    )
    while IFS= read -r command_name; do required+=("package/commands/$command_name"); done < <(pt_operator_commands)
    pt_print_line
    pt_print_line "Repository contract files"
    for relative in "${required[@]}"; do
        if [[ -f "$REPO_ROOT/$relative" ]]; then
            pt_status_line "PASS" "$relative"
        else
            pt_status_line "MISSING" "$relative"
            missing=$((missing + 1))
        fi
    done
    [[ -f "$REPO_ROOT/Docs/PrecisionTowerNode.md" ]] && pt_status_line "PASS" "Docs/PrecisionTowerNode.md" || pt_status_line "WARNING" "Docs/PrecisionTowerNode.md" "not present in this checkout; package still references it as contract"
    (( missing == 0 ))
}

prepare_privilege() {
    [[ "$APPLY" == true ]] || return 0
    [[ "$EUID" -eq 0 ]] && return 0
    if pt_requires_privilege_for_install_destinations; then
        if sudo -n true >/dev/null 2>&1; then
            SUDO_CMD=(sudo)
            pt_status_line "PASS" "privilege" "sudo is available non-interactively"
        else
            pt_status_line "MISSING" "privilege" "--apply to $PRECISION_BIN_DIR and $PRECISION_ENV_DIR requires sudo; sudo -n is unavailable"
            return 1
        fi
    fi
}

wrapper_conflict_count() {
    local count=0 command_name dest src target
    while IFS= read -r command_name; do
        dest="$PRECISION_BIN_DIR/$command_name"
        src="$PACKAGE_COMMANDS/$command_name"
        if [[ -L "$dest" ]]; then
            target="$(readlink "$dest")"
            [[ "$target" == "$src" ]] || { pt_status_line "WARNING" "wrapper conflict" "$dest -> $target" >&2; count=$((count + 1)); }
        elif [[ -e "$dest" ]]; then
            pt_status_line "WARNING" "wrapper conflict" "$dest exists and is not a package symlink" >&2
            count=$((count + 1))
        fi
    done < <(pt_operator_commands)
    printf '%s\n' "$count"
}

env_conflict_count() {
    if [[ -e "$PRECISION_ENV_FILE" && ! -f "$PRECISION_ENV_FILE" ]]; then
        pt_status_line "WARNING" "env conflict" "$PRECISION_ENV_FILE exists and is not a regular file" >&2
        printf '1\n'
        return
    fi
    if [[ -f "$PRECISION_ENV_FILE" ]] && ! grep -q '^# Managed by Dashboard CE-OS package$' "$PRECISION_ENV_FILE"; then
        pt_status_line "WARNING" "env conflict" "$PRECISION_ENV_FILE exists but is not package-managed" >&2
        printf '1\n'
        return
    fi
    printf '0\n'
}

write_generated_env() {
    local output="$1" python_bin godot_path pty_host pty_port user_name user_home wine_prefix tailscale_key
    python_bin="$(pt_python || true)"
    godot_path="$(pt_godot_path || true)"
    pty_host="$(pt_launcher_env_value OPERATOR_PTY_HOST 127.0.0.1)"
    pty_port="$(pt_launcher_env_value OPERATOR_PTY_PORT 8765)"
    user_name="$(id -un)"
    user_home=""
    if pt_have_command getent; then
        user_home="$(getent passwd "$user_name" 2>/dev/null | cut -d: -f6 || true)"
    fi
    user_home="${user_home:-$HOME}"
    wine_prefix="$user_home/Applications/wine/operator"
    tailscale_key="$PRECISION_ENV_DIR/tailscale-auth.key"
    cat > "$output" <<EOF
# Managed by Dashboard CE-OS package
# Generated by package/install.sh. This file is machine-local and must not be committed.
DASHBOARD_ROOT=$REPO_ROOT
DASHBOARD_PYTHON=${python_bin:-UNRESOLVED}
AGENCY_COMMAND=UNRESOLVED
AGENCY_RUNTIME_STATUS=unresolved_no_persistent_repository_daemon
AGENCY_USER=$user_name
GODOT_PATH=${godot_path:-UNRESOLVED}
OPERATOR_PTY_HOST=${pty_host:-127.0.0.1}
OPERATOR_PTY_PORT=${pty_port:-8765}
HEALTH_INTERVAL_SECONDS=60
CONSOLE_REFRESH_SECONDS=10
TAILSCALE_AUTH_KEY_FILE=$tailscale_key
SSH_ADMIN_PUBLIC_KEY=UNRESOLVED
WINE_OPERATOR_PREFIX=$wine_prefix
EOF
}

preflight() {
    local conflicts=0
    pt_print_line
    pt_print_line "Agency runtime classification"
    pt_agency_runtime_status
    [[ -e "$PACKAGE_SYSTEMD/agency.service" ]] && { pt_status_line "WARNING" "agency.service" "installable agency.service exists even though AGENCY_COMMAND is unresolved"; conflicts=$((conflicts + 1)); } || pt_status_line "PASS" "agency.service" "no installable agency.service present"
    [[ -f "$PACKAGE_SYSTEMD/agency.service.unresolved" ]] && pt_status_line "PASS" "agency service draft" "$PACKAGE_SYSTEMD/agency.service.unresolved" || { pt_status_line "MISSING" "agency service draft" "$PACKAGE_SYSTEMD/agency.service.unresolved"; conflicts=$((conflicts + 1)); }
    pt_print_line
    pt_print_line "Destination preflight"
    conflicts=$((conflicts + $(wrapper_conflict_count) + $(env_conflict_count)))
    (( conflicts == 0 )) && pt_status_line "PASS" "preflight" "no destination conflicts" || { pt_status_line "WARNING" "preflight" "$conflicts conflict(s); no mutation will occur"; return 1; }
}

hardware_gate() {
    pt_print_line
    pt_print_line "Hardware readiness gate"
    if pt_hardware_acceptance_report; then
        return 0
    fi
    if [[ "$APPLY" == true ]]; then
        pt_status_line "BLOCKED" "hardware readiness" "host is not accepted as a CE-OS Node; no installation will occur"
        return 1
    fi
    pt_status_line "WARNING" "hardware readiness" "host is not accepted; --apply would be blocked until hardware readiness passes"
    return 0
}

install_wrappers() {
    local command_name dest src
    pt_print_line
    pt_print_line "Operator command wrappers"
    if [[ "$APPLY" != true ]]; then
        while IFS= read -r command_name; do
            dest="$PRECISION_BIN_DIR/$command_name"
            src="$PACKAGE_COMMANDS/$command_name"
            pt_status_line "DRY-RUN" "$dest" "would link to $src"
            [[ "$command_name" == "help" ]] && pt_status_line "WARNING" "help command" "Bash's help builtin may shadow /usr/local/bin/help in interactive shells."
        done < <(pt_operator_commands)
        return 0
    fi
    if [[ ! -d "$PRECISION_BIN_DIR" ]]; then
        "${SUDO_CMD[@]}" mkdir -p "$PRECISION_BIN_DIR"
        CREATED_DIRS+=("$PRECISION_BIN_DIR")
        pt_status_line "CREATED" "$PRECISION_BIN_DIR"
    else
        pt_status_line "PRESERVED" "$PRECISION_BIN_DIR"
    fi
    while IFS= read -r command_name; do
        dest="$PRECISION_BIN_DIR/$command_name"
        src="$PACKAGE_COMMANDS/$command_name"
        if [[ -L "$dest" && "$(readlink "$dest")" == "$src" ]]; then
            pt_status_line "PRESERVED" "$dest" "already points to $src"
        else
            "${SUDO_CMD[@]}" ln -s "$src" "$dest"
            CREATED_PATHS+=("$dest")
            pt_status_line "CREATED" "$dest" "-> $src"
        fi
        [[ "$command_name" == "help" ]] && pt_status_line "WARNING" "help command" "Bash's help builtin may shadow /usr/local/bin/help in interactive shells."
    done < <(pt_operator_commands)
    return 0
}

install_env_file() {
    local tmp
    pt_print_line
    pt_print_line "Machine-local environment"
    if [[ -f "$PRECISION_ENV_FILE" ]]; then
        pt_status_line "PRESERVED" "$PRECISION_ENV_FILE" "package-managed file already exists"
        return 0
    fi
    if [[ "$APPLY" != true ]]; then
        tmp="$(mktemp "$PT_RUNTIME_TMP_ROOT/tmp.XXXXXXXXXX")"
        write_generated_env "$tmp"
        pt_status_line "DRY-RUN" "$PRECISION_ENV_DIR" "would create if missing"
        pt_status_line "DRY-RUN" "$PRECISION_ENV_FILE" "would write generated environment"
        sed -n '1,40p' "$tmp"
        rm -f "$tmp"
        return 0
    fi
    if [[ ! -d "$PRECISION_ENV_DIR" ]]; then
        "${SUDO_CMD[@]}" mkdir -p "$PRECISION_ENV_DIR"
        CREATED_DIRS+=("$PRECISION_ENV_DIR")
        pt_status_line "CREATED" "$PRECISION_ENV_DIR"
    else
        pt_status_line "PRESERVED" "$PRECISION_ENV_DIR"
    fi
    tmp="$(mktemp "$PT_RUNTIME_TMP_ROOT/tmp.XXXXXXXXXX")"
    write_generated_env "$tmp"
    "${SUDO_CMD[@]}" install -m 0644 "$tmp" "$PRECISION_ENV_FILE"
    rm -f "$tmp"
    CREATED_PATHS+=("$PRECISION_ENV_FILE")
    pt_status_line "CREATED" "$PRECISION_ENV_FILE"
}

main() {
    usage_context
    pt_require_dashboard_root || exit 1
    [[ -f "$PACKAGE_CONFIG" ]] || { pt_status_line "MISSING" "package config" "$PACKAGE_CONFIG"; exit 1; }
    [[ -x "$PACKAGE_VERIFY" ]] || { pt_status_line "MISSING" "verify script" "$PACKAGE_VERIFY"; exit 1; }
    require_files
    preflight
    hardware_gate
    prepare_privilege
    pt_print_line
    pt_print_line "Running read-only verification"
    local verify_output verify_status
    verify_output="$(mktemp "$PT_RUNTIME_TMP_ROOT/tmp.XXXXXXXXXX")"
    if "$PACKAGE_VERIFY" >"$verify_output"; then
        pt_status_line "PASS" "verification" "package/verify.sh exited 0"
    else
        verify_status=$?
        rm -f "$verify_output"
        pt_status_line "MISSING" "verification" "package/verify.sh exited $verify_status"
        return "$verify_status"
    fi
    rm -f "$verify_output"
    ROLLBACK_ENABLED=true
    install_wrappers
    install_env_file
    ROLLBACK_ENABLED=false
    pt_print_line
    pt_status_line "SKIPPED" "package installation" "not part of this phase"
    pt_status_line "SKIPPED" "systemd units" "not installed, enabled, or started in this phase"
    pt_status_line "SKIPPED" "agency.service" "AGENCY_COMMAND is unresolved; no persistent Agency daemon was proven"
    pt_status_line "SKIPPED" "ssh/tailscale/ufw/tty/boot" "not changed in this phase"
    [[ "$APPLY" == true ]] && pt_status_line "PASS" "install" "apply completed" || pt_status_line "PASS" "install" "dry-run completed; re-run with --apply to mutate approved destinations"
}
main "$@"
