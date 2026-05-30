# Model Runtime Dependency Decision

Recorded: 2026-05-29

Scope:
- This note preserves the current local Qwen runtime dependency decision.
- It does not authorize installs, model validation, UI wiring, or command behavior changes.

Current environment:
- Active local Python discovered for Dashboard tooling is Python 3.14 only.
- Python 3.12 was not found.
- Python 3.13 was not found.
- `uv`, `conda`, `winget`, `choco`, and `scoop` were not found on PATH.
- The current workspace `.venv` is Python 3.14.5 and contains only `pip`.

Qwen3-8B model files:
- Local model path: `Bridge/Core/Dashboard/Tools/Models/Qwen3-8b/`
- Required Hugging Face/Transformers files are present, including:
  - `config.json`
  - `generation_config.json`
  - `tokenizer.json`
  - `tokenizer_config.json`
  - `vocab.json`
  - `merges.txt`
  - `model.safetensors.index.json`
  - five `model-0000x-of-00005.safetensors` shards
- The safetensor index references the present shard files and appears coherent.

Current Cali observer state:
- `cali-observe-directory` is wired through the Dashboard CLI.
- It currently reaches the model runner path and degrades cleanly when the model runtime is not available.
- Local Qwen runtime now verified in the separate `cali-model` conda environment.
- Observed runtime environment:
  - Python 3.12.13
  - torch 2.12.0+cpu
  - transformers 5.9.0
- Qwen3-8B loads successfully from local shard files in `Bridge/Core/Dashboard/Tools/Models/Qwen3-8b/`.
- Minimal one-token generation succeeded and produced the text: `Local`.
- Single-token generation on CPU took approximately `53.62 sec`.
- A 4-token generation test was too slow / effectively blocked by CPU latency.
- Current blocker is runtime performance, not model availability.

Phi-3-mini-4k-instruct local result:
- Local model path: `Bridge/Core/Dashboard/Tools/Models/Phi-3-mini-4k-instruct/`
- Model loads successfully from local shard files.
- Generated text: `Local Ph`
- Tokens generated: `4`
- Generation time: `21.65 sec`
- Speed: ~`5.41 sec/token`
- No load or generation errors were observed.
- Phi-3-mini-4k-instruct is significantly faster than Qwen3-8B CPU and is a practical local model candidate for Cali.

Dependency decision:
- Do not install Torch/model dependencies into the Dashboard tooling `.venv` unless explicitly approved.
- Keep Dashboard tooling dependencies separate from local model runtime dependencies.
- Recommended local model environment path:
  - `Bridge/Core/Dashboard/.venv-model`
- Preferred runtime Python for `.venv-model`:
  - Python 3.12, if installed later.

Future runtime direction:
- Keep the local Qwen path as proven-but-slow for now.
- Do not route interactive Cali through full Qwen3-8B CPU generation yet.
- Next research should evaluate smaller local models, quantization, llama.cpp/GGUF, GPU option, or remote fallback.
- Model-bearing commands may later call `.venv-model/Scripts/python.exe` by subprocess.
- That should be an explicit runtime integration step, not an implicit dependency mix-in.
- Until approved, the current CLI behavior should remain unchanged and continue to degrade clearly when model dependencies are unavailable.

Implementation note:
If timeout is difficult inside the model generation call, implement timeout by wrapping the generation path in a subprocess or report that true interruption is not currently safe. Do not fake timeout behavior.
