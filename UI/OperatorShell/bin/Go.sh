#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="$HOME/.ce-os/codego"
STATUS_FILE="$STATE_DIR/status"
PID_FILE="$STATE_DIR/pid"
MISSION_FILE="$STATE_DIR/mission.txt"
CONTROL_FILE="$STATE_DIR/control"

mkdir -p "$STATE_DIR"

worker_pid() {
    [ -f "$PID_FILE" ] || return 1
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    [ -n "$pid" ] || return 1
    kill -0 "$pid" 2>/dev/null || return 1
    printf '%s\n' "$pid"
}

send_control() {
    local command="$1"
    local pid
    pid="$(worker_pid)" || {
        echo "[!] CodeGo is not running." >&2
        exit 1
    }
    printf '%s\n' "$command" > "$CONTROL_FILE"
    kill -USR1 "$pid"
}

case "${1:-}" in
    ds|DS)
        send_control "PROVIDER:1"
        echo "[*] DeepSeek selected."
        ;;

    Q|q)
        send_control "PROVIDER:2"
        echo "[*] Qwen selected."
        ;;

    G|g)
        send_control "PROVIDER:3"
        echo "[*] Gemini selected."
        ;;

    system)
        send_control "SYSTEM"
        echo "[*] Go system submitted."
        ;;

    go)
        shift
        [ "$#" -gt 0 ] || {
            echo 'Usage: Go go "mission"' >&2
            exit 2
        }

        pid="$(worker_pid)" || {
            echo "[!] CodeGo is not running." >&2
            exit 1
        }

        state="$(sed -n 's/^STATE=//p' "$STATUS_FILE" 2>/dev/null || true)"
        [ "$state" = "READY" ] || {
            echo "[!] CodeGo is not SYSTEM-ready. Run: Go system" >&2
            exit 1
        }

        mission="$*"
        [ -n "${mission//[[:space:]]/}" ] || {
            echo "[!] mission is empty." >&2
            exit 2
        }

        printf '%s\n' "$mission" > "$MISSION_FILE"
        printf '%s\n' "MISSION" > "$CONTROL_FILE"
        kill -USR1 "$pid"
        echo "[*] Mission submitted to CodeGo pid=$pid."
        ;;

    status)
        if ! worker_pid >/dev/null 2>&1; then
            echo "GO=OFF"
            echo "WORKER=CodeGo"
            echo "STATE=STOPPED"
            exit 0
        fi
        cat "$STATUS_FILE" 2>/dev/null || {
            echo "GO=ON"
            echo "WORKER=CodeGo"
            echo "STATE=UNKNOWN"
        }
        ;;

    off)
        rm -f "$MISSION_FILE" "$CONTROL_FILE" "$PID_FILE"
        dashboard off
        echo "GO=OFF"
        ;;

    help|-h|--help|"")
        echo 'Go ds'
        echo 'Go Q'
        echo 'Go G'
        echo 'Go system'
        echo 'Go go "mission"'
        echo 'Go status'
        echo 'Go off'
        ;;

    *)
        echo "Usage: Go {ds|Q|G|system|go|status|off}" >&2
        exit 2
        ;;
esac