# Inference Map

## Active Path

- `UI/scripts/agents/reasoners/gguf.py`
  - llama.cpp GGUF adapter
  - current local model interface

- `UI/scripts/runtime/serve.py`
  - loads GGUF model
  - accepts JSON lines over stdin
  - supports runtime output modes

- `UI/scripts/runtime/client.py`
  - current request client
  - currently cold-launches `serve.py` per request
  - target for persistent transport upgrade

## Legacy / Deprecated Candidates

- `UI/scripts/runtime/phi_engine.py`
  - old Transformers Phi-3 path
  - loads model per call
  - not current Weebo path

- `UI/scripts/runtime/model_runner.py`
  - old subprocess / conda runner
  - references missing `isolated_inference.py`
  - not current Weebo path

## Current Priority

Replace subprocess-per-request behavior in `client.py` with a persistent server transport.

## Authority Boundary

- model drafts text
- runtime validates response contracts
- operator approves mutation
- no autonomous edits without explicit approval