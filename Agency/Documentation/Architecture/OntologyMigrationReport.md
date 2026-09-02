# Ontology Migration Report

This report records the first ontology-driven directory migration.

Authoritative ontology:

```text
Agency/Documentation/Architecture/Ontology.md
```

## Moves Performed

| Original path | New path | Reason | Ontology rule |
| --- | --- | --- | --- |
| `Agency/Core/repository_context` | `Agency/Core/repository/context` | Repository context exists because the Repository system needs bounded repository evidence. | Repository System contains Repository Context. |
| `Agency/Core/inspection` | `Agency/Core/repository/inspection` | Inspection is repository understanding, not a top-level Core system. | Repository System contains Inspection. |
| `Agency/Core/git_authority` | `Agency/Core/repository/git_authority` | Git authority is repository state and history authority. | Repository System contains Git Authority. |
| `Agency/Core/review` | `Agency/Core/missions/pipeline/review` | Review consumes proposal artifacts and gates later mission stages. | Mission Pipeline is ordered mission lifecycle. |
| `Agency/Core/implementation` | `Agency/Core/missions/pipeline/implementation` | Implementation consumes reviewed mission artifacts and produces changes for verification. | Mission Pipeline is ordered mission lifecycle. |
| `Agency/Core/verification` | `Agency/Core/missions/pipeline/verification` | Verification consumes implementation output and produces evidence for mission state. | Mission Pipeline is ordered mission lifecycle. |
| `Agency/Core/tasks` | `Agency/Core/missions/tasks` | Tasks are reusable executable mission tasks. | Mission System contains Tasks. |
| `Agency/Core/work_packets` | `Agency/Core/missions/work_packets` | WorkPackets are delegated units of mission work. | Mission System contains Work Packets. |

## Parent-Child Justification

`Agency/Core/repository` exists because Core needs one repository system that
owns repository evidence, inspection, and Git authority.

`Agency/Core/missions/pipeline` exists because Mission needs an ordered
lifecycle. Review, implementation, and verification are not independent Core
systems; each stage consumes the previous stage's artifacts.

`Agency/Core/missions/tasks` exists because missions need reusable executable
tasks.

`Agency/Core/missions/work_packets` exists because missions need delegated units
of bounded work.

## Directories Left In Place

- `Agency/Core/planning`: The ontology names Planning as its own Core system,
  but also says proposal belongs in the Mission Pipeline. The current code
  contains mission planning and proposal generation. This boundary needs a
  sharper ontology rule before moving.
- `Agency/Core/runtime`: The ontology warns against generic runtime buckets, but
  this directory currently contains agent shell, model service, environment
  manifest, terminal service, sessions, and resourcefulness runtime. It is too
  broad to move safely without a richer ontology split.
- `Agency/Core/agent_tools`: This appears to be agent factory and memory tooling,
  but the ontology does not yet define an Agent Factory or Agent Provisioning
  system.
- `Agency/Core/editor`: EditorTask and EditorResult power the Observer to Editor
  handoff. It may belong under WorkPackets, but it also has a standalone CLI
  surface. The ontology does not yet define the Editor role as a directory
  parent or child.
- `Agency/Core/capabilities`: The ontology discourages generic capability
  buckets, but this area contains legacy engineering execution contracts. It
  needs a separate classification pass.
- `Agency/audit`: Top-level audit/evidence exists outside the documented first
  children of Agency. Its relationship to State or Repository evidence should be
  clarified before movement.
- `Agency/runtime`: Lowercase runtime contains historical mission test artifacts.
  It should not be moved until the ontology distinguishes active state,
  historical evidence, and test fixture storage.

## Naming Inconsistencies

- `repository_context` became `repository/context` to avoid repeating the parent
  name in the child.
- `git_authority` remains snake_case because it is a named authority boundary.
- `work_packets` remains plural because the system owns many packet records.
- `runtime` remains ambiguous and overloaded.
- `capabilities` remains a generic implementation bucket.
- `agent_tools` describes implementation tooling rather than an architectural
  ownership domain.

## Ontology Improvements Recommended

1. Define whether `proposal` belongs under Planning, Mission Pipeline, or both.
2. Define an Agent Provisioning or Agent Factory system if generated-agent
   creation remains a Core responsibility.
3. Split the current Runtime ontology into agent conversation runtime, model
   runtime, terminal runtime, environment identity, and mission runtime.
4. Define where the Observer to Editor handoff belongs relative to WorkPackets.
5. Define whether Audit is a top-level Agency domain or part of State.
6. Define storage rules for active operational state versus historical evidence
   versus test fixtures.

## Migration Notes

Imports, CLI routes, validation harness paths, and package exports were updated
to use the new ontology paths. No compatibility wrappers were introduced.
