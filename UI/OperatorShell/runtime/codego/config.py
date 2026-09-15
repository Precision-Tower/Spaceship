"""CodeGo configuration.

Central constants for the CodeGo relay that lives inside the CE-OS
OperatorShell runtime. Nothing here hardcodes a user or a machine --
every path is derived from $HOME so the same file works on voc, HP,
or any other node in the fleet.
"""

import os

# ---------------------------------------------------------------------------
# Repository / runtime layout
# ---------------------------------------------------------------------------

HOME = os.path.expanduser("~")
RUNTIME_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPTS_DIR = os.path.join(RUNTIME_DIR, "prompts")

# CodeGo owns its dedicated Chrome session. OperatorShell discovers that X11
# window and owns workspace geometry/visibility; Selenium attaches through
# this dedicated debug port.
CHROME_DEBUG_HOST = "127.0.0.1"
CHROME_DEBUG_PORT = 9222
CHROME_DEBUG_ADDRESS = "{}:{}".format(CHROME_DEBUG_HOST, CHROME_DEBUG_PORT)
CHROME_PROFILE_DIR = os.path.join(HOME, "local", "chrome-profile")

# ---------------------------------------------------------------------------
# Provider table
# ---------------------------------------------------------------------------
# Menu order is the order the operator sees. Keys are the strings the
# menu prompts for. Swap ordering here and the menu follows.
# ---------------------------------------------------------------------------

PROVIDERS = {
    "1": {
        "name": "DeepSeek",
        "url": "https://chat.deepseek.com",
    },
    "2": {
        "name": "Qwen",
        "url": "https://chat.qwen.ai",
    },
    "3": {
        "name": "Gemini",
        "url": "https://gemini.google.com/app",
    },
}

MENU_ORDER = ["1", "2", "3"]

# ---------------------------------------------------------------------------
# Relay markers
# ---------------------------------------------------------------------------
# Everything the model wants executed locally on VOC goes between two
# %%VOC%% markers. STOP_SYSTEM anywhere in the reply halts the loop and
# returns control to the operator.
# ---------------------------------------------------------------------------

VOC_MARKER = "%%VOC%%"
STOP_SYSTEM = "STOP_SYSTEM"

# Prefix the controller puts on bash output it pastes back to the model.
COMMAND_OUTPUT_HEADER = "COMMAND_OUTPUT:"

# ---------------------------------------------------------------------------
# Timeouts / cadence
# ---------------------------------------------------------------------------

BASH_TIMEOUT_SEC = 600
REPLY_TIMEOUT_SEC = 180
POLL_INTERVAL_SEC = 2
UI_SETTLE_TIMEOUT_SEC = 30

# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------

def load_prompt(name):
    """Return the contents of prompts/<name>, or "" if missing.

    `name` may be given with or without the .md suffix.
    """
    if not name.endswith(".md"):
        name = name + ".md"
    path = os.path.join(PROMPTS_DIR, name)
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()
