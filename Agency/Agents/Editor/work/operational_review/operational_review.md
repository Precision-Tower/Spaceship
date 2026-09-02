# Editor Operational Review

Generated: 2026-07-29
Branch: test/editor-agency-refresh
Baseline: 5f15920 Route operational storage to active agent-owned paths

## Lifecycle Trace

1. Operator entry points
   - python run.py agent ask Editor <prompt> routes through 
un.py:run_agent_command() into Agency.Core.runtime.model_service.ask_agent().
   - python run.py agent Editor ... resolves the filesystem-discovered Agency/Agents/Editor package and calls Agency.Agents.Editor.main(), which delegates to Agency.Core.runtime.agent_shell.main( Editor, argv).
   - python run.py editor ... routes to Agency.Core.editor.execution.main() for explicit EditorTask submit/show/result/inspect operations.

2. Agent selection
   - Agent identity is filesystem-authoritative under Agency/Agents through Agency.Core.agents.discovery.
   - Editor has an agent package and launcher at Agency/Agents/Editor/editor.py.

3. Runtime initialization and model interaction
   - Agency.Core.runtime.model_service.ask_agent() loads Agency/Agents/Editor/runtime.yaml, output_contract.yaml, autonomy, short-term memory, and state files.
   - Model execution uses the shared runtime route when the agent runtime resolves to llama-server.
   - Agency.Core.runtime.llama_server_client serializes an explicit inference policy into the OpenAI-compatible llama-server request.

4. Context construction
   - Authoritative state requests short-circuit through Agency.Core.runtime.authoritative_state when intent matches state questions.
   - Repository inspection requests route through Agency.Core.repository.context.builder.repository_inspection_payload() and persist evidence under Agency/Agents/Editor/work/Inspections.
   - Normal model prompts can load direct file context, workspace snapshots, and optionally vector memory.

5. Mission/task/work execution
   - Explicit Editor tasks are represented by EditorTask and executed by Agency.Core.editor.execution.execute_editor_task().
   - Work packets call Editor through Agency.Core.work.work_packets.execution.dispatch_step().
   - Supported Editor operations are currently inspect, propose_patch, apply_patch, and verify.

6. Patch and validation flow
   - Patch proposal is deterministic text replacement based on change_intent and repository evidence.
   - Patch application requires PatchAuthorization and uses the Git authority boundary.
   - Verification is evidence-only and currently allows git diff --check and git status --short.

7. Operational state
   - Editor task artifacts are written through EDITOR_TASKS_ROOT from Agency.Core.foundation.paths.
   - Repository inspection artifacts are written through INSPECTIONS_ROOT from Agency.Core.foundation.paths.
   - Runtime state, logs, sessions, memory, work packets, missions, proposals, and pinboard paths resolve under Agency/Agents/Editor through Agency.Core.foundation.paths.

## Findings

### Confirmed Healthy Surfaces

- Active source audits show no Jarvis or Weebo references in active surfaces outside ignored generated work/runtime directories.
- Active generated runtime-state paths no longer point into Agency/Core/runtime/state, work, logs, or sessions.
- The traced Editor Python files compile under the configured environment.
- Editor task persistence and repository-context persistence are agent-owned.

### Potential Operational Failures To Validate

1. 
un.py agent ask and python run.py model agent-ask currently print payloads and return success even when the payload reports ok: false.
   - Risk: model/runtime failures can be hidden from operators and scripts.
   - Relevant files: 
un.py, Agency/Core/runtime/model_service.py.

2. Patch-refinement failure text still names Cali even when the active routed agent is Editor.
   - Risk: misleading error attribution during Editor patch recommendation workflows.
   - Relevant file: Agency/Core/runtime/model_service.py.

3. Direct model identity cleanup contains a hard-coded Cali identity narrative.
   - Risk: if the model emits that stale identity phrase, the cleanup function can rewrite output into a different active identity than Editor.
   - Relevant file: Agency/Core/runtime/model_service.py.

4. AgentShell model prompts use shared sk_agent, but failure exit semantics need validation.
   - Risk: interactive and argv shells might display failure text without returning actionable status.
   - Relevant file: Agency/Core/runtime/agent_shell.py.

5. Editor patch proposal is intentionally narrow and deterministic.
   - Risk: broad implementation requests cannot become patches unless translated into the supported 
eplace old with new in <path> change intent or another authorized work-packet flow.
   - Relevant file: Agency/Core/editor/execution.py.

## Next Validation Targets

- Model manager status and single-process ownership.
- gent list and gent Editor status startup.
- Exact-response Editor model smoke.
- Rewrite prompt containing environment.
- Authoritative environment question.
- Explicit Editor inspect task creation under Agency/Agents/Editor/work/EditorTasks.
- Error-path exit codes for failed gent ask/model agent-ask requests.
