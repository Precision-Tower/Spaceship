#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"
source "$SCRIPT_DIR/../lib/hardware.sh"
pt_initialize
fail() { pt_status_line "MISSING" "$1" "$2"; exit 1; }
pt_print_line "Precision Tower hardware readiness test"

tmp="$(mktemp -d "$PT_TEST_TMP_ROOT/tmp.XXXXXXXXXX")"
trap 'rm -rf "$tmp"' EXIT
policy="$tmp/hardware.env"
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

write_mock_tools() {
    local dir="$1" gpu_name="$2" vram="$3"
    mkdir -p "$dir"
    cat > "$dir/nvidia-smi" <<EOF
#!/usr/bin/env bash
if [[ "\$*" == *"--query-gpu="* ]]; then
    printf '0, %s, %s, 580.173.02, 8.6\\n' '$gpu_name' '$vram'
    exit 0
fi
printf 'NVIDIA-SMI 580.173.02 Driver Version: 580.173.02 CUDA Version: 13.0\\n'
EOF
    cat > "$dir/nvcc" <<'EOF'
#!/usr/bin/env bash
printf 'Cuda compilation tools, release 12.4, V12.4.131\n'
EOF
    cat > "$dir/lspci" <<EOF
#!/usr/bin/env bash
printf '01:00.0 VGA compatible controller: NVIDIA Corporation %s\\n' '$gpu_name'
EOF
    cat > "$dir/uname" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" ]]; then
    printf '%s\n' x86_64
else
    /data/data/com.termux/files/usr/bin/uname "$@"
fi
EOF
chmod +x "$dir/uname"

cat > "$dir/lsmod" <<'EOF'
#!/usr/bin/env bash
printf 'nvidia 105357312 53\n'
EOF
    chmod +x "$dir/nvidia-smi" "$dir/nvcc" "$dir/lspci" "$dir/lsmod" "$dir/uname"
}

pass_bin="$tmp/pass-bin"
write_mock_tools "$pass_bin" "NVIDIA GeForce RTX 3060" "12288"
if PATH="$pass_bin:$PATH" PT_HARDWARE_POLICY_FILE="$policy" pt_hardware_acceptance_report >"$tmp/pass.out" 2>&1; then
    grep -q 'PASS       precision tower acceptance' "$tmp/pass.out" || fail "hardware acceptance" "passing mock did not report acceptance"
    pt_status_line "PASS" "accepted hardware mock" "RTX 3060 12288 MiB passes"
else
    cat "$tmp/pass.out"
    fail "accepted hardware mock" "expected readiness pass"
fi

fail_bin="$tmp/fail-bin"
write_mock_tools "$fail_bin" "NVIDIA GeForce GTX 1050" "4096"
if PATH="$fail_bin:$PATH" PT_HARDWARE_POLICY_FILE="$policy" pt_hardware_acceptance_report >"$tmp/fail.out" 2>&1; then
    cat "$tmp/fail.out"
    fail "rejected hardware mock" "GTX 1050 should not satisfy RTX 3060 policy"
else
    grep -q 'BLOCKED    target gpu' "$tmp/fail.out" || fail "rejected hardware mock" "target GPU blocker was not reported"
    grep -q 'BLOCKED    precision tower acceptance' "$tmp/fail.out" || fail "rejected hardware mock" "acceptance blocker was not reported"
    pt_status_line "PASS" "rejected hardware mock" "non-target GPU blocks acceptance"
fi

pt_status_line "PASS" "hardware readiness" "deterministic acceptance and rejection verified"
