#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$PACKAGE_ROOT/.." && pwd)"
RUNTIME_TMP_ROOT="${PT_RUNTIME_TMP_ROOT:-$REPO_ROOT/trash/tmp/package-runtime}"
BUILD_ROOT="${QPS_BOOTSTRAP_BUILD_ROOT:-$RUNTIME_TMP_ROOT/qps-bootstrap}"
MODE="check"

usage() {
    cat <<USAGE
Usage: $0 [--check|--build-qps]

--check       Verify pinned QPS/native source reconstruction inputs without building.
--build-qps   Configure and build the QPS executable into repository-local scratch.
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --check) MODE="check" ;;
        --build-qps) MODE="build-qps" ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
    shift
done

declare -a COMPONENTS=(
    "coreutils:bff0e5412db91410d759e2eefbbca3df80a1e672"
    "diffutils:ba490bf17c1938e7cd0c2309a08d9a59b962bdff"
    "findutils:db41ebaf0486e9903745c46a59fed9ccc4d5938b"
    "gawk:6c7fd0eb2ee568f5f2a30646f0c91ccb4a65ecc4"
    "grep:e187ca53198c7aafb28da64da86d1bd59244c3cc"
    "patch:a2b192295d7046bafc18d54973436bb3faa659d7"
    "ripgrep:3fce3b5bb0236da2df6d99672afb8a719642eca7"
    "sed:0c1fe22ccacf4887e0be6c11deb4e9c83acc287d"
)

verify_component() {
    local name="$1"
    local expected="$2"
    local source="$REPO_ROOT/qps/bin/src/$name"
    local actual

    [[ -d "$source" ]] || {
        echo "BLOCKED source_missing component=$name path=$source" >&2
        return 1
    }

    [[ -d "$source/.git" ]] || {
        echo "BLOCKED git_identity_missing component=$name path=$source" >&2
        return 1
    }

    actual="$(git -C "$source" rev-parse HEAD 2>/dev/null)" || {
        echo "BLOCKED revision_unreadable component=$name" >&2
        return 1
    }

    if [[ "$actual" != "$expected" ]]; then
        echo "BLOCKED revision_mismatch component=$name expected=$expected actual=$actual" >&2
        return 1
    fi

    echo "PINNED_SOURCE=PASS component=$name revision=$actual"
}

verify_inputs() {
    [[ -f "$REPO_ROOT/qps/cpp/CMakeLists.txt" ]] || {
        echo "BLOCKED qps_cmake_authority_missing" >&2
        return 1
    }

    local entry name expected
    for entry in "${COMPONENTS[@]}"; do
        name="${entry%%:*}"
        expected="${entry#*:}"
        verify_component "$name" "$expected"
    done

    echo 'QPS_BOOTSTRAP_INPUTS=PASS'
}

build_qps() {
    command -v cmake >/dev/null 2>&1 || {
        echo 'BLOCKED dependency_missing=cmake' >&2
        return 1
    }

    mkdir -p "$BUILD_ROOT"
    cmake -S "$REPO_ROOT/qps/cpp" -B "$BUILD_ROOT"
    cmake --build "$BUILD_ROOT" --target qps

    [[ -x "$BUILD_ROOT/qps" ]] || {
        echo "BLOCKED qps_artifact_missing path=$BUILD_ROOT/qps" >&2
        return 1
    }

    "$BUILD_ROOT/qps" "$REPO_ROOT/package/bootstrap/qps-components.qps" --check
    echo "QPS_BUILD=PASS artifact=$BUILD_ROOT/qps"
}

verify_inputs

case "$MODE" in
    check)
        echo 'QPS_BOOTSTRAP_CHECK=PASS'
        ;;
    build-qps)
        build_qps
        echo 'QPS_BOOTSTRAP_BUILD=PASS'
        ;;
esac
