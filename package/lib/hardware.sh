#!/usr/bin/env bash

_pt_hw_trim() {
    local value="$*"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    printf '%s' "$value"
}

_pt_hw_bool_true() {
    case "${1:-}" in
        true|TRUE|yes|YES|1|required|REQUIRED) return 0 ;;
        *) return 1 ;;
    esac
}

pt_hardware_policy_file() {
    if [[ -n "${PT_HARDWARE_POLICY_FILE:-}" ]]; then
        printf '%s\n' "$PT_HARDWARE_POLICY_FILE"
        return 0
    fi

    local profile="${PT_MACHINE_PROFILE:-precision-tower}"
    local profile_file="$PACKAGE_ROOT/config/machines/${profile}.env"

    if [[ -r "$profile_file" ]]; then
        printf '%s\n' "$profile_file"
        return 0
    fi

    printf '%s\n' "$PACKAGE_ROOT/config/hardware.env"
}

pt_hardware_load_policy() {
    local policy
    policy="$(pt_hardware_policy_file)"
    if [[ ! -r "$policy" ]]; then
        PT_HARDWARE_LAST_REASON="hardware policy $policy is not readable"
        return 1
    fi
    # shellcheck source=/dev/null
    source "$policy"
    PT_REQUIRED_ARCHITECTURE="${PT_REQUIRED_ARCHITECTURE:-x86_64}"
    PT_TARGET_GPU_NAME_PATTERN="${PT_TARGET_GPU_NAME_PATTERN:-RTX 3060}"
    PT_MIN_VRAM_MIB="${PT_MIN_VRAM_MIB:-12288}"
    PT_REQUIRE_NVIDIA_SMI="${PT_REQUIRE_NVIDIA_SMI:-true}"
    PT_REQUIRE_NVIDIA_DRIVER="${PT_REQUIRE_NVIDIA_DRIVER:-true}"
    PT_REQUIRE_NVIDIA_KERNEL_MODULE="${PT_REQUIRE_NVIDIA_KERNEL_MODULE:-true}"
    PT_REQUIRE_CUDA_RUNTIME="${PT_REQUIRE_CUDA_RUNTIME:-true}"
    PT_REQUIRE_CUDA_TOOLKIT="${PT_REQUIRE_CUDA_TOOLKIT:-true}"
}

_pt_hw_memory_total() {
    awk '/MemTotal:/ {printf "%d MiB", $2 / 1024}' /proc/meminfo 2>/dev/null || true
}

_pt_hw_cpu_model() {
    awk -F: '/model name/ {gsub(/^[ \t]+/, "", $2); print $2; exit}' /proc/cpuinfo 2>/dev/null || true
}

_pt_hw_cuda_runtime_version() {
    pt_have_command nvidia-smi || return 1
    pt_run_quick 8 nvidia-smi 2>/dev/null | sed -n 's/.*CUDA Version: *\([0-9.]*\).*/\1/p' | head -n 1 || true
}

_pt_hw_cuda_toolkit_version() {
    pt_have_command nvcc || return 1
    pt_run_quick 8 nvcc --version 2>/dev/null | sed -n 's/.*release *\([0-9.]*\).*/\1/p' | head -n 1 || true
}

pt_hardware_acceptance_report() {
    local failures=0 arch kernel cpu memory pci_lines query_output query_status
    local gpu_count=0 target_found=0 target_vram_ok=0 driver_seen=0 compute_seen=0
    local target_detail="" runtime_version toolkit_version

    if ! pt_hardware_load_policy; then
        pt_status_line "MISSING" "hardware policy" "${PT_HARDWARE_LAST_REASON:-policy unavailable}"
        return 1
    fi

    pt_status_line "PASS" "hardware policy" "$(pt_hardware_policy_file)"
    pt_status_line "PASS" "target gpu policy" "$PT_TARGET_GPU_NAME_PATTERN with at least ${PT_MIN_VRAM_MIB} MiB VRAM"

    arch="$(uname -m 2>/dev/null || true)"
    kernel="$(uname -r 2>/dev/null || true)"
    cpu="$(_pt_hw_cpu_model)"
    memory="$(_pt_hw_memory_total)"

    if [[ "$arch" == "$PT_REQUIRED_ARCHITECTURE" ]]; then
        pt_status_line "PASS" "architecture" "$arch"
    else
        pt_status_line "BLOCKED" "architecture" "expected $PT_REQUIRED_ARCHITECTURE, found ${arch:-unknown}"
        failures=$((failures + 1))
    fi
    [[ -n "$kernel" ]] && pt_status_line "PASS" "kernel" "$kernel" || pt_status_line "WARNING" "kernel" "uname did not report a kernel version"
    [[ -n "$cpu" ]] && pt_status_line "PASS" "cpu" "$cpu" || pt_status_line "WARNING" "cpu" "CPU model not available from /proc/cpuinfo"
    [[ -n "$memory" ]] && pt_status_line "PASS" "system memory" "$memory" || pt_status_line "WARNING" "system memory" "MemTotal not available from /proc/meminfo"

    if pt_have_command lspci; then
        pci_lines="$(pt_run_quick 5 lspci -nn 2>/dev/null | grep -Ei 'nvidia|vga|3d|display' || true)"
        if [[ -n "$pci_lines" ]]; then
            pt_status_line "PASS" "display adapters" "$(printf '%s\n' "$pci_lines" | head -n 1)"
            local extra_count
            extra_count="$(printf '%s\n' "$pci_lines" | sed '/^$/d' | wc -l | tr -d ' ')"
            if [[ "${extra_count:-0}" -gt 1 ]]; then
                pt_status_line "PASS" "display adapter count" "$extra_count relevant PCI device(s)"
            fi
        else
            pt_status_line "WARNING" "display adapters" "lspci found no NVIDIA/VGA/3D/display devices"
        fi
    else
        pt_status_line "WARNING" "lspci" "pciutils/lspci is not installed; PCI inventory is incomplete"
    fi

    if ! pt_have_command nvidia-smi; then
        if _pt_hw_bool_true "$PT_REQUIRE_NVIDIA_SMI"; then
            pt_status_line "MISSING" "nvidia-smi" "required NVIDIA management tool not found"
            failures=$((failures + 1))
        else
            pt_status_line "WARNING" "nvidia-smi" "not found"
        fi
    else
        pt_status_line "PASS" "nvidia-smi" "$(command -v nvidia-smi)"
        set +e
        query_output="$(pt_run_quick 8 nvidia-smi --query-gpu=index,name,memory.total,driver_version,compute_cap --format=csv,noheader,nounits 2>&1)"
        query_status=$?
        set -e
        if [[ "$query_status" -ne 0 ]]; then
            pt_status_line "MISSING" "nvidia inventory" "nvidia-smi query failed: $(printf '%s' "$query_output" | head -c 160)"
            failures=$((failures + 1))
        else
            local line index name memory_mib driver compute
            while IFS= read -r line; do
                [[ -n "$line" ]] || continue
                IFS=',' read -r index name memory_mib driver compute <<<"$line"
                index="$(_pt_hw_trim "$index")"
                name="$(_pt_hw_trim "$name")"
                memory_mib="$(_pt_hw_trim "$memory_mib")"
                memory_mib="${memory_mib//[^0-9]/}"
                driver="$(_pt_hw_trim "$driver")"
                compute="$(_pt_hw_trim "$compute")"
                gpu_count=$((gpu_count + 1))
                [[ -n "$driver" ]] && driver_seen=1
                [[ -n "$compute" ]] && compute_seen=1
                pt_status_line "PASS" "gpu ${index:-$gpu_count}" "$name; ${memory_mib:-unknown} MiB VRAM; driver ${driver:-unknown}; compute ${compute:-unknown}"
                if [[ "$name" == *"$PT_TARGET_GPU_NAME_PATTERN"* ]]; then
                    target_found=1
                    target_detail="$name (${memory_mib:-unknown} MiB VRAM)"
                    if [[ "${memory_mib:-0}" =~ ^[0-9]+$ ]] && (( memory_mib >= PT_MIN_VRAM_MIB )); then
                        target_vram_ok=1
                    fi
                fi
            done <<<"$query_output"
            if (( gpu_count == 0 )); then
                pt_status_line "MISSING" "gpu inventory" "nvidia-smi returned no GPU rows"
                failures=$((failures + 1))
            fi
            if (( target_found == 0 )); then
                pt_status_line "BLOCKED" "target gpu" "$PT_TARGET_GPU_NAME_PATTERN was not detected"
                failures=$((failures + 1))
            elif (( target_vram_ok == 0 )); then
                pt_status_line "BLOCKED" "target vram" "$target_detail is below ${PT_MIN_VRAM_MIB} MiB"
                failures=$((failures + 1))
            else
                pt_status_line "PASS" "target vram" "$target_detail satisfies ${PT_MIN_VRAM_MIB} MiB minimum"
            fi
        fi
    fi

    if _pt_hw_bool_true "$PT_REQUIRE_NVIDIA_DRIVER"; then
        if (( driver_seen == 1 )); then
            pt_status_line "PASS" "nvidia driver" "driver version reported by nvidia-smi"
        else
            pt_status_line "MISSING" "nvidia driver" "driver version was not proven"
            failures=$((failures + 1))
        fi
    fi
    if (( compute_seen == 1 )); then
        pt_status_line "PASS" "gpu capability" "compute capability reported by nvidia-smi"
    else
        pt_status_line "WARNING" "gpu capability" "compute capability was not reported"
    fi

    runtime_version="$(_pt_hw_cuda_runtime_version || true)"
    if _pt_hw_bool_true "$PT_REQUIRE_CUDA_RUNTIME"; then
        if [[ -n "$runtime_version" ]]; then
            pt_status_line "PASS" "cuda runtime" "CUDA Version $runtime_version reported by nvidia-smi"
        else
            pt_status_line "MISSING" "cuda runtime" "CUDA runtime version was not proven through nvidia-smi"
            failures=$((failures + 1))
        fi
    elif [[ -n "$runtime_version" ]]; then
        pt_status_line "PASS" "cuda runtime" "CUDA Version $runtime_version reported by nvidia-smi"
    fi

    toolkit_version="$(_pt_hw_cuda_toolkit_version || true)"
    if _pt_hw_bool_true "$PT_REQUIRE_CUDA_TOOLKIT"; then
        if [[ -n "$toolkit_version" ]]; then
            pt_status_line "PASS" "cuda toolkit" "nvcc release $toolkit_version"
        else
            pt_status_line "MISSING" "cuda toolkit" "nvcc was not found or did not report a release"
            failures=$((failures + 1))
        fi
    elif [[ -n "$toolkit_version" ]]; then
        pt_status_line "PASS" "cuda toolkit" "nvcc release $toolkit_version"
    fi

    if _pt_hw_bool_true "$PT_REQUIRE_NVIDIA_KERNEL_MODULE"; then
        if pt_have_command lsmod; then
            local module_lines
            module_lines="$(pt_run_quick 5 lsmod 2>/dev/null || true)"
            if grep -q '^nvidia' <<<"$module_lines"; then
                pt_status_line "PASS" "nvidia kernel module" "nvidia module is loaded"
            else
                pt_status_line "MISSING" "nvidia kernel module" "nvidia module is not loaded"
                failures=$((failures + 1))
            fi
        else
            pt_status_line "MISSING" "nvidia kernel module" "lsmod is not available"
            failures=$((failures + 1))
        fi
    fi

    if (( failures == 0 )); then
        PT_HARDWARE_LAST_REASON="host satisfies CE-OS hardware policy"
        pt_status_line "PASS" "precision tower acceptance" "$PT_HARDWARE_LAST_REASON"
        return 0
    fi
    PT_HARDWARE_LAST_REASON="$failures hardware readiness condition(s) not satisfied"
    pt_status_line "BLOCKED" "precision tower acceptance" "$PT_HARDWARE_LAST_REASON"
    return 1
}

pt_hardware_acceptance_check() {
    pt_hardware_acceptance_report >/dev/null
}
