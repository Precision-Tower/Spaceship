#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
pt_initialize
PT_RUNTIME_TMP_ROOT="${PT_RUNTIME_TMP_ROOT:-$REPO_ROOT/trash/tmp/package-runtime}"
mkdir -p "$PT_RUNTIME_TMP_ROOT"
APPLY=false
for arg in "$@"; do case "$arg" in --apply) APPLY=true ;; --dry-run|--plan) APPLY=false ;; -h|--help) pt_print_line "usage: package/uninstall.sh [--dry-run|--apply]"; exit 0 ;; *) pt_status_line "WARNING" "usage" "unknown argument: $arg"; exit 2 ;; esac; done
SUDO_CMD=()
if [[ "$APPLY" == true && "$EUID" -ne 0 ]] && pt_requires_privilege_for_install_destinations; then if sudo -n true >/dev/null 2>&1; then SUDO_CMD=(sudo); else pt_status_line "MISSING" "privilege" "--apply to $PRECISION_BIN_DIR and $PRECISION_ENV_DIR requires sudo; sudo -n is unavailable"; exit 1; fi; fi
pt_print_line "Precision Tower Node package uninstaller"
[[ "$APPLY" == true ]] && pt_status_line "PASS" "mode" "apply" || pt_status_line "PASS" "mode" "dry-run"
pt_status_line "PASS" "wrapper destination" "$PRECISION_BIN_DIR"
pt_status_line "PASS" "environment destination" "$PRECISION_ENV_FILE"
pt_require_dashboard_root || exit 1
remove_wrapper() { local command_name="$1" dest="$PRECISION_BIN_DIR/$command_name" src="$PACKAGE_COMMANDS/$command_name"; if [[ -L "$dest" && "$(readlink "$dest")" == "$src" ]]; then if [[ "$APPLY" == true ]]; then "${SUDO_CMD[@]}" rm -f "$dest"; pt_status_line "REMOVED" "$dest"; else pt_status_line "DRY-RUN" "$dest" "would remove package symlink"; fi; elif [[ -e "$dest" || -L "$dest" ]]; then pt_status_line "PRESERVED" "$dest" "not a symlink to $src"; else pt_status_line "SKIPPED" "$dest" "not installed"; fi; }
pt_print_line; pt_print_line "Operator command wrappers"; while IFS= read -r command_name; do remove_wrapper "$command_name"; done < <(pt_operator_commands)
pt_print_line; pt_print_line "Machine-local environment"
if [[ -f "$PRECISION_ENV_FILE" ]] && grep -q '^# Managed by Dashboard Precision Tower package$' "$PRECISION_ENV_FILE"; then if [[ "$APPLY" == true ]]; then "${SUDO_CMD[@]}" rm -f "$PRECISION_ENV_FILE"; pt_status_line "REMOVED" "$PRECISION_ENV_FILE"; "${SUDO_CMD[@]}" rmdir "$PRECISION_ENV_DIR" >/dev/null 2>&1 || true; else pt_status_line "DRY-RUN" "$PRECISION_ENV_FILE" "would remove package-managed env file"; fi; elif [[ -e "$PRECISION_ENV_FILE" ]]; then pt_status_line "PRESERVED" "$PRECISION_ENV_FILE" "not package-managed"; else pt_status_line "SKIPPED" "$PRECISION_ENV_FILE" "not installed"; fi
pt_print_line; pt_status_line "SKIPPED" "systemd units" "current phase never installs or enables units"; [[ "$APPLY" == true ]] && pt_status_line "PASS" "uninstall" "apply completed" || pt_status_line "PASS" "uninstall" "dry-run completed; re-run with --apply to remove package-owned paths"