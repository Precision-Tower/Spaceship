#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"
pt_initialize
fail() { pt_status_line "MISSING" "$1" "$2"; exit 1; }
pt_print_line "Precision Tower controlled installation test"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
bin_dir="$tmp/bin"
env_dir="$tmp/etc/precision-tower-node"
mock_bin="$tmp/mock-bin"
policy="$tmp/hardware.env"
mkdir -p "$mock_bin"
cat > "$policy" <<'EOF'
PT_REQUIRED_ARCHITECTURE="x86_64"
PT_TARGET_GPU_NAME_PATTERN="RTX 3060"
PT_MIN_VRAM_MIB="12288"
PT_REQUIRE_NVIDIA_SMI="true"
PT_REQUIRE_NVIDIA_DRIVER="true"
PT_REQUIRE_NVIDIA_KERNEL_MODULE="true"
PT_REQUIRE_CUDA_RUNTIME="true"
PT_REQUIRE_CUDA_TOOLKIT="true"
EOF
cat > "$mock_bin/nvidia-smi" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == *"--query-gpu="* ]]; then
    printf '0, NVIDIA GeForce RTX 3060, 12288, 580.173.02, 8.6\n'
    exit 0
fi
printf 'NVIDIA-SMI 580.173.02 Driver Version: 580.173.02 CUDA Version: 13.0\n'
EOF
cat > "$mock_bin/nvcc" <<'EOF'
#!/usr/bin/env bash
printf 'Cuda compilation tools, release 12.4, V12.4.131\n'
EOF
cat > "$mock_bin/lspci" <<'EOF'
#!/usr/bin/env bash
printf '01:00.0 VGA compatible controller: NVIDIA Corporation NVIDIA GeForce RTX 3060\n'
EOF
cat > "$mock_bin/lsmod" <<'EOF'
#!/usr/bin/env bash
printf 'nvidia 105357312 53\n'
EOF
chmod +x "$mock_bin/nvidia-smi" "$mock_bin/nvcc" "$mock_bin/lspci" "$mock_bin/lsmod"
PATH="$mock_bin:$PATH" PT_HARDWARE_POLICY_FILE="$policy" PRECISION_BIN_DIR="$bin_dir" PRECISION_ENV_DIR="$env_dir" "$PACKAGE_ROOT/install.sh" --dry-run >/tmp/precision-tower-install-dry-run.out
[[ ! -e "$bin_dir" ]] || fail "dry-run" "$bin_dir was created during dry-run"
[[ ! -e "$env_dir/default.env" ]] || fail "dry-run" "$env_dir/default.env was created during dry-run"
grep -q 'PASS       precision tower acceptance' /tmp/precision-tower-install-dry-run.out || fail "dry-run hardware gate" "accepted mock hardware was not reported"
pt_status_line "PASS" "dry-run" "no filesystem mutation in temporary destinations"
PATH="$mock_bin:$PATH" PT_HARDWARE_POLICY_FILE="$policy" PRECISION_BIN_DIR="$bin_dir" PRECISION_ENV_DIR="$env_dir" "$PACKAGE_ROOT/install.sh" --apply >/tmp/precision-tower-install-apply.out
while IFS= read -r command_name; do dest="$bin_dir/$command_name"; src="$PACKAGE_COMMANDS/$command_name"; [[ -L "$dest" ]] || fail "installed wrapper" "$dest is not a symlink"; [[ "$(readlink "$dest")" == "$src" ]] || fail "installed wrapper" "$dest does not point to $src"; done < <(pt_operator_commands)
pt_status_line "PASS" "wrapper install" "all operator wrappers installed as symlinks"
[[ -f "$env_dir/default.env" ]] || fail "env install" "$env_dir/default.env missing"
grep -q '^# Managed by Dashboard Precision Tower package$' "$env_dir/default.env" || fail "env marker" "managed marker missing"
grep -q "^DASHBOARD_ROOT=$REPO_ROOT$" "$env_dir/default.env" || fail "env root" "DASHBOARD_ROOT not derived"
grep -q '^AGENCY_COMMAND=UNRESOLVED$' "$env_dir/default.env" || fail "env agency command" "AGENCY_COMMAND should remain unresolved"
grep -q '^AGENCY_RUNTIME_STATUS=unresolved_no_persistent_repository_daemon$' "$env_dir/default.env" || fail "env agency runtime" "agency runtime status missing"
grep -q '^TAILSCALE_AUTH_KEY_FILE=' "$env_dir/default.env" || fail "env tailscale key path" "tailscale key path missing"
grep -q '^WINE_OPERATOR_PREFIX=' "$env_dir/default.env" || fail "env wine prefix" "wine prefix missing"
pt_status_line "PASS" "env install" "$env_dir/default.env"
[[ ! -e "$PACKAGE_SYSTEMD/agency.service" ]] || fail "agency.service" "installable agency.service exists"
[[ -f "$PACKAGE_SYSTEMD/agency.service.unresolved" ]] || fail "agency.service.unresolved" "non-installable Agency draft missing"
pt_status_line "PASS" "agency service classification" "no installable agency.service exists"
PRECISION_BIN_DIR="$bin_dir" PRECISION_ENV_DIR="$env_dir" "$PACKAGE_ROOT/uninstall.sh" --apply >/tmp/precision-tower-uninstall-apply.out
while IFS= read -r command_name; do [[ ! -e "$bin_dir/$command_name" && ! -L "$bin_dir/$command_name" ]] || fail "uninstalled wrapper" "$bin_dir/$command_name remains"; done < <(pt_operator_commands)
[[ ! -e "$env_dir/default.env" ]] || fail "uninstalled env" "$env_dir/default.env remains"
pt_status_line "PASS" "uninstall" "package-owned temporary destinations removed"
