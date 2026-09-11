# CE-OS QPS terminal bridge.
#
# Ctrl+M is composed as:
#   private QPS Inline hook -> Readline Ctrl+J accept-line
#
# Ordinary commands survive the hook unchanged.
# Canonical [< ... ] commands are consumed by qps/bin/inline before Bash
# receives them as shell syntax.

_ceos_qps_inline_enter() {
    if [[ "$READLINE_LINE" != '[<'* ]]; then
        return 0
    fi

    local source="$READLINE_LINE"

    READLINE_LINE=
    READLINE_POINT=0

    printf '\n'
    "$HOME/ce-os/qps/bin/inline" "$source"
    local status=$?

    # Preserve QPS execution status as the shell's most recent command status.
    return "$status"
}

if [[ $- == *i* ]]; then
    bind -x '"\C-x\C-q":_ceos_qps_inline_enter'
    bind '"\C-m":"\C-x\C-q\C-j"'
fi
