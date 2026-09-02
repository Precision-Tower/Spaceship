# Inference Map

## Active Dashboard Path

- `python run.py agent ask <AgentName> "prompt"`
  - One-shot agent prompt surface.
  - Dispatches through `run.py` to `Agency/Core/runtime/model_service.py`.

- `python run.py agent <AgentName>`
  - Opens the agent REPL implemented by `Agency/Core/runtime/agent_shell.py`.
  - Free-text REPL prompts call the same `model_service.ask_agent()` path.
  - `/tool` commands route through `Agency/Core/cli/dashboard_cli.py` and its authority ledger.

- `python run.py model [status|ask|agent-ask]`
  - Model status and direct model prompting surface.
  - Uses the same shared runtime profile authority as the model server manager.

- `python -m Agency.Core.runtime.model_server_manager <status|start|stop|restart|reconcile>`
  - Owns the Dashboard llama-server lifecycle.
  - Uses `Agency/Core/runtime/runtime_profiles.yaml` through `runtime_config.load_model_server_config()`.
  - Verifies process identity by server path, model path, host, port, context size, and GPU layers.
  - `reconcile` replaces only pid-file-owned stale Dashboard llama-server processes; unrelated processes are reported, not killed.

## Runtime Configuration Authority

- `Agency/Core/runtime/runtime_profiles.yaml`
  - Active model profile authority.
  - Current local GPU profile selects `local/Qwen3-4B-Q4_K_M.gguf` on `127.0.0.1:8081` with `context_tokens: 2048` and `gpu_layers: 99`.

- `Agency/Core/runtime/runtime_config.py`
  - Shared resolver for model path, context, GPU layers, server path, pid path, and log path.

## Request Policy

- `Agency/Core/runtime/inference_policy.py`
  - Selects the explicit inference policy before low-level llama-server calls.
  - Determines route, model requirement, authoritative-state allowance, thinking mode, completion budget, output contract, and validation requirements.

- `Agency/Core/runtime/llama_server_client.py`
  - Serializes the explicit policy into llama-server request fields such as `chat_template_kwargs.enable_thinking`, `reasoning_effort`, `max_tokens`, and `temperature`.
  - Distinguishes transport success from usable visible output.
  - Reports malformed, empty, and length-truncated completions as failures.

## Authority Boundary

- Local GGUF model output is draft-only, not repository truth.
- Authoritative state answers are returned only for explicit state-intent requests.
- Rewrite/edit prompts containing runtime vocabulary still route to model inference.
- Runtime validates response usability before reporting success.
- Operator approval remains required for mutation.
