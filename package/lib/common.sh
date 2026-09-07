#!/usr/bin/env bash

pt_print_line() {
    printf '%s\n' "$*"
}

pt_status_line() {
    local status="$1"
    local name="$2"
    local detail="${3:-}"
    if [[ -n "$detail" ]]; then
        printf '%-10s %s - %s\n' "$status" "$name" "$detail"
    else
        printf '%-10s %s\n' "$status" "$name"
    fi
}

pt_script_dir() {
    local source="${BASH_SOURCE[1]}"
    while [[ -L "$source" ]]; do
        local dir
        dir="$(cd -P "$(dirname "$source")" && pwd)"
        source="$(readlink "$source")"
        [[ "$source" == /* ]] || source="$dir/$source"
    done
    cd -P "$(dirname "$source")" && pwd
}

pt_resolve_layout() {
    local script_directory
    script_directory="$(pt_script_dir)"
    case "$(basename "$script_directory")" in
        commands|lib|config|manifests|packages|systemd|tests)
            PACKAGE_ROOT="$(cd "$script_directory/.." && pwd)"
            ;;
        package)
            PACKAGE_ROOT="$script_directory"
            ;;
        *)
            PACKAGE_ROOT="$(cd "$script_directory" && pwd)"
            ;;
    esac
    REPO_ROOT="$(cd "$PACKAGE_ROOT/.." && pwd)"
    PACKAGE_CONFIG="$PACKAGE_ROOT/config/package.yaml"
    PACKAGE_VERIFY="$PACKAGE_ROOT/verify.sh"
    PACKAGE_COMMANDS="$PACKAGE_ROOT/commands"
    PACKAGE_MANIFESTS="$PACKAGE_ROOT/manifests"
    PACKAGE_PACKAGE_LISTS="$PACKAGE_ROOT/packages"
    PACKAGE_SYSTEMD="$PACKAGE_ROOT/systemd"
    PACKAGE_TESTS="$PACKAGE_ROOT/tests"
    PRECISION_BIN_DIR="${PRECISION_BIN_DIR:-/usr/local/bin}"
    PRECISION_ENV_DIR="${PRECISION_ENV_DIR:-/etc/precision-tower-node}"
    PRECISION_ENV_FILE="$PRECISION_ENV_DIR/default.env"
}

pt_have_command() {
    command -v "$1" >/dev/null 2>&1
}

pt_first_command() {
    local candidate
    for candidate in "$@"; do
        if pt_have_command "$candidate"; then
            command -v "$candidate"
            return 0
        fi
    done
    return 1
}

pt_run_quick() {
    local seconds="$1"
    shift
    if pt_have_command timeout; then
        timeout "$seconds" "$@"
    else
        "$@"
    fi
}

pt_python() {
    if [[ -n "${DASHBOARD_PYTHON:-}" && -x "${DASHBOARD_PYTHON}" ]]; then
        printf '%s\n' "$DASHBOARD_PYTHON"
        return 0
    fi
    local launcher="${REPO_ROOT:-}/run-dashboard.sh"
    if [[ -f "$launcher" ]]; then
        local configured=""
        configured="$(grep '^DASHBOARD_PYTHON=' "$launcher" | head -n 1 | sed -n 's#.*:-\([^}]*\)}.*#\1#p' || true)"
        if [[ -n "$configured" ]]; then
            configured="${configured//'$'HOME/$HOME}"
            if [[ -x "$configured" ]]; then
                printf '%s\n' "$configured"
                return 0
            fi
        fi
    fi
    if pt_have_command python3; then
        command -v python3
        return 0
    fi
    if pt_have_command python; then
        command -v python
        return 0
    fi
    return 1
}

pt_require_dashboard_root() {
    if pt_is_repository_root "$REPO_ROOT"; then
        return 0
    fi
    pt_status_line "MISSING" "repository root" "$REPO_ROOT is not a CE-OS repository root"
    return 1
}

pt_run_repo_python() {
    local python_bin
    if ! python_bin="$(pt_python)"; then
        pt_status_line "MISSING" "python" "No Python executable found in PATH or DASHBOARD_PYTHON"
        return 127
    fi
    (cd "$REPO_ROOT" && pt_run_quick 20 "$python_bin" "$@")
}

pt_file_size() {
    local path="$1"
    if [[ ! -e "$path" ]]; then
        printf 'missing'
        return 0
    fi
    if pt_have_command stat; then
        stat -c '%s bytes' "$path" 2>/dev/null && return 0
    fi
    wc -c <"$path" | awk '{print $1 " bytes"}'
}

pt_current_tty() {
    tty 2>/dev/null || true
}

pt_has_launch_surface() {
    local display="${DISPLAY:-}"
    local tty_path
    tty_path="$(pt_current_tty)"
    [[ -n "$display" || "$tty_path" == /dev/tty* ]]
}

pt_brave_command() {
    pt_first_command brave-browser brave brave-browser-stable
}

pt_xfce_command() {
    pt_first_command startxfce4 xfce4-session
}

pt_operator_commands() {
    printf '%s\n' help browser desktop dashboard status doctor logs update restart shutdown
}

pt_godot_path() {
    local rel=""
    if [[ -f "$REPO_ROOT/run-dashboard.sh" ]]; then
        rel="$(grep -o 'local/godot/Godot_Linux/Godot_v[^" ]*' "$REPO_ROOT/run-dashboard.sh" | head -n 1 || true)"
    fi
    if [[ -z "$rel" && -f "$REPO_ROOT/run.py" ]]; then
        rel="$(grep -o 'local/godot/Godot_Linux/Godot_v[^" ]*' "$REPO_ROOT/run.py" | head -n 1 || true)"
    fi
    [[ -n "$rel" ]] && printf '%s\n' "$REPO_ROOT/$rel"
}

pt_launcher_env_value() {
    local key="$1"
    local fallback="${2:-}"
    local launcher="$REPO_ROOT/run-dashboard.sh"
    local value=""

    if [[ -f "$launcher" ]]; then
        case "$key" in
            OPERATOR_PTY_HOST)
                value="$(grep '^OPERATOR_PTY_HOST=' "$launcher" 2>/dev/null | head -n 1 | sed -n 's#.*:-\([^}]*\)}.*#\1#p' || true)"
                ;;
            OPERATOR_PTY_PORT)
                value="$(grep '^OPERATOR_PTY_PORT=' "$launcher" 2>/dev/null | head -n 1 | sed -n 's#.*:-\([^}]*\)}.*#\1#p' || true)"
                ;;
        esac
    fi

    printf '%s\n' "${value:-$fallback}"
}

pt_agency_runtime_status() {
    if [[ -f "$REPO_ROOT/run-dashboard.sh" ]] && grep -q 'pty_service' "$REPO_ROOT/run-dashboard.sh" && grep -q 'GODOT' "$REPO_ROOT/run-dashboard.sh"; then
        pt_status_line "UNRESOLVED" "Agency runtime" "run-dashboard.sh launches Dashboard/client surfaces, not a persistent Agency daemon."
    fi
    if [[ -f "$REPO_ROOT/run.py" ]] && grep -q 'run_local_operator' "$REPO_ROOT/run.py"; then
        pt_status_line "UNRESOLVED" "Agency runtime" "run.py exposes mission and LocalOperator CLI routes, not a persistent Agency daemon."
    fi
    pt_status_line "UNRESOLVED" "AGENCY_COMMAND" "No persistent repository Agency runtime command is proven; agency.service is non-installable."
}

pt_requires_privilege_for_install_destinations() {
    [[ "$PRECISION_BIN_DIR" == /usr/* || "$PRECISION_BIN_DIR" == /bin/* || "$PRECISION_ENV_DIR" == /etc/* ]]
}


pt_is_repository_root() {
    local root="${1:-$REPO_ROOT}"
    [[ -f "$root/_index.qps" ]] &&
    [[ -d "$root/package" ]] &&
    [[ -d "$root/qps" ]]
}


pt_initialize() {
    pt_resolve_layout
}