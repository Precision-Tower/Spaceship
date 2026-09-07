# OperatorShell

OperatorShell is the shared Godot operator interface targeting Linux and Android. Android uses a portrait, one-surface-at-a-time composition with Files, Editor, Terminal, and Controls.

The external runtime control plane is `bin/ops` -> `runtime/OperatorControlServer.gd` -> `Main.gd` control methods. It owns surface switching, keyboard control, refresh commands, and status; it does not carry filesystem data.

The application data plane for the read-only Files -> Editor slice is `Main.gd` -> `runtime/CliBridge.gd` URL helpers -> the supervised CE-OS API at `http://127.0.0.1:8765`. The API service is installed as `ce-os-api` under Termux services and serves `/v1/fs/list?path=...` and `/v1/fs/read?path=...`.

UI state uses repo-relative virtual paths beginning with `/`. The Files UI hides `.git`; the backend preserves directories-first, case-insensitive sorting. Files are read through the CE-OS authorization boundary; the Godot UI does not traverse Termux or root paths directly. The current slice is read-only and reports backend errors, including binary rejection, as structured editor states.

`CliBridge.gd` still contains legacy command wrappers pointing at `Agency/Core/cli/dashboard_cli.py`; the modern CLI is under `Agency/Core/interfaces/cli`, but it is not used for this filesystem data path.
