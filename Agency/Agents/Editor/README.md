# Editor

```yaml
Editor:
  role: editor
  description: Repository engineering and implementation agent.
  status: scaffold
  authority: local_agent_memory_only_not_validation

  owns:
    - local_context
    - local_memory
    - role_specific_outputs

  does_not_own:
    - validation
    - source_authority
    - mission_authority_unless_explicitly_granted
    - hidden_truth

  memory:
    enabled: true
    vector_store: true
    sources: memory/sources.yaml
    short_term: memory/short_term.yaml
    chroma: memory/Chroma

  runtime:
    config: runtime.yaml
    model_route: Agency/Core/runtime/model_service.py
    backend: llama_server
    accelerator: cuda
    inference_route: local
    execution_mode: local_gpu
    model_authority: draft_generation_only_not_truth

  state:
    config: state/agent_state.yaml
    transition_log: state/transition_log.yaml
    authority: state_scaffold_only_not_runtime_authority
```
