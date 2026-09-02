Agency

Agency is the execution operating system for CE-OS.

Its responsibility is to transform authorized intent into bounded, reconstructable work while preserving authority, evidence, verification, and causal accountability.

The repository is intentionally organized so that its parent/child relationships communicate how the system operates. Directory structure is part of the architecture, not merely file storage.

Operating Model

Agency separates four concerns:

Identity — who is acting
Work — what level of coordination is required
Capability — what the system can do
Runtime — where and how execution occurs

An Agent provides identity, policy, memory, configuration, and operating behavior.

Core provides reusable implementation.

Agents consume Core. Core must not depend on a concrete Agent implementation.

Repository Structure
Agency/
├── Agents/
├── Core/
├── Datasets/
├── Documentation/
├── Archive/
├── audit/
├── README.md
└── unittest.py
Agents/

Installed Agent identities and their Agent-owned operational state.

An Agent may own:

policy
memory
autonomy configuration
runtime configuration
work artifacts
state and session records

Agents do not duplicate Core implementation.

The currently installed Agent is:

Agency/Agents/Editor/
Core/

The reusable execution operating system.

Core contains Agent-independent contracts, capabilities, orchestration, repository operations, runtime services, and state management.

A concrete Agent may invoke Core, but Core should not require knowledge of that Agent’s identity.

Datasets/

Reference material and source corpora used by Agency capabilities.

Datasets are not part of the production test surface unless explicitly integrated into Core behavior.

Documentation/

Current long-form architecture and design material.

Archive/

Historical material retained for reference but excluded from active architecture and runtime authority.

audit/

Operational checks and generated evidence describing whether Agency is behaving according to its contracts.

Work Hierarchy

Work is the umbrella concept for using Agents.

Agency separates work into progressively more autonomous execution structures.

Task

A primitive unit of bounded execution.

For repository engineering, the canonical primitive is an EditorTask.

An EditorTask may inspect, propose, apply an authorized patch, or verify a result.

WorkPacket

A supervised sequence of Tasks.

WorkPackets preserve:

ordered steps
dependency relationships
scope
authorization
task references
result references
evidence
unresolveds

WorkPackets are shared execution infrastructure and live under:

Agency/Core/work/work_packets/

They are not owned exclusively by Missions.

Mission

A higher-level orchestration structure with more room for inspection, planning, proposal generation, review, implementation, and verification.

Missions may compile approved implementation units into WorkPackets and delegate bounded execution to EditorTasks.

Mission-specific operational handlers live under:

Agency/Core/missions/operations/

These handlers are mission-scoped operations, not the primitive Task abstraction.

Adventure

The future full-autonomy layer.

An Adventure may coordinate Missions with broader delegated authority while preserving the same evidence and authorization rules.

The intended hierarchy is:

Task
  ↓
WorkPacket
  ↓
Mission
  ↓
Adventure

Each level adds coordination and autonomy. It does not erase the authority boundaries of the levels beneath it.

Execution Flow

For tightly supervised repository work:

Operator
  ↓
Agent
  ↓
EditorTask
  ↓
Core capability
  ↓
Repository evidence or bounded mutation

For sequenced work:

Operator
  ↓
Agent
  ↓
WorkPacket
  ↓
EditorTasks
  ↓
Evidence and verification

For broader orchestration:

Operator
  ↓
Agent
  ↓
Mission
  ↓
WorkPackets
  ↓
EditorTasks
  ↓
Evidence and verification

Execution flows downward.

Evidence, status, unresolveds, and control of the next decision flow upward.

Editor

Editor is the repository execution surface.

Editor exists so that higher-level reasoning does not require a human to repeatedly relay filesystem contents.

Editor can perform bounded repository operations such as:

inspection
evidence collection
proposal creation
authorized patch application
verification

Editor must stop before mutation when authorization is absent.

After authorization, Editor applies the exact approved proposal rather than regenerating or reinterpreting it.

Verification reports evidence. Verification is not acceptance or approval.

Core Ownership

Core is organized by responsibility.

agents/

Generic Agent discovery and Agent-independent contracts.

Concrete Agent packages remain under Agency/Agents/.

agent_tools/

Reusable tooling for creating and configuring Agents.

capabilities/

Bounded reusable abilities such as engineering and structured context refinement.

Capabilities describe what can be done. They do not invent authority.

cli/

Command-line surfaces and command registration.

editor/

EditorTask contracts, persistence, execution, and result handling.

memory/

Shared memory infrastructure.

Agent-owned memory remains under the relevant Agent directory.

missions/

Mission contracts, lifecycle, orchestration, pipelines, and mission-scoped operations.

planning/

Planning and proposal-generation logic used by orchestration layers.

reasoning/

Shared causal reasoning contracts, evidence selection, and reasoning context construction.

repository/

Repository inspection, repository context, and Git authority boundaries.

The repository is the source of truth for repository work.

Conversational memory and retrieval memory may provide context, but they are not repository authority.

runtime/

Shared runtime services, shell behavior, command construction, environment management, and terminal surfaces.

state/

Persistent state contracts and schemas.

work/

Shared execution structures that are not owned by one orchestration layer.

WorkPackets currently live here.

Authority

Authority is explicit and bounded.

Execution cannot expand its own permissions.

A mutation must be attributable to an authorization chain.

A typical supervised chain is:

Operator approval
  ↓
WorkPacket authorization
  ↓
EditorTask
  ↓
Exact authorized mutation
  ↓
Verification evidence

Inspection and proposal generation are non-mutating operations.

Mutation requires explicit authority.

Verification does not create approval.

Evidence and Reconstruction

Agency prefers reconstructability over convenience.

Whenever practical, execution records:

inputs
scope
assumptions
decisions
authorization
outputs
verification
unresolved questions
next action
who holds the ball

A mission or work unit is not progressing unless it produces at least one of:

a runtime artifact
repository evidence
an authorized mutation
a verification result
a precise execution failure

The objective is not perfect memory.

The objective is that another engineer can reconstruct what happened, why it happened, and what authority was used.

Memory

Agency distinguishes three different concepts.

Conversational memory

Recent interaction context used to preserve continuity in dialogue.

Retrieval memory

Historical information retrieved from long-term storage such as Chroma.

Repository operational state

WorkPackets, EditorTasks, Mission artifacts, inspection evidence, proposals, authorizations, and verification results.

For repository work, repository operational state is authoritative.

Memory can augment repository evidence. It cannot replace it.

Validation

Agency standardizes on Python’s built-in unittest framework.

The canonical repository validation command is:

python Agency/unittest.py

The validation entrypoint performs:

Python compilation
repository sanity checks
discovery and execution of the complete Core unittest suite
a final pass/fail result with the correct process exit code

The canonical validation surface intentionally excludes vendored dataset test suites and third-party source corpora.

There should be no need to remember a special discovery command.

Architectural Rules

The following rules govern future changes:

Parent directories must meaningfully own their children.
Shared infrastructure must not be nested under one of its consumers.
Siblings communicate through contracts rather than implementation leakage.
Agents provide identity and policy.
Core provides reusable implementation.
Core must not depend on concrete Agent packages.
Tasks remain bounded.
WorkPackets preserve supervision and sequence.
Missions add orchestration rather than replacing Tasks.
Adventures add autonomy rather than bypassing authority.
Mutation requires authorization.
Verification produces evidence, not approval.
Repository truth comes from repository operations.
Runtime commands must be generated from a canonical command surface.
Tests must describe the current architecture rather than preserve retired scaffolding.
If the import graph consistently contradicts the directory hierarchy, the hierarchy is wrong.
Architecture should be understandable from the repository tree.
Reading Order

A new contributor should approach Agency in this order:

Agency/README.md
  ↓
Agency/Agents/
  ↓
Agency/Core/work/
  ↓
Agency/Core/editor/
  ↓
Agency/Core/missions/
  ↓
Agency/Core/capabilities/
  ↓
Agency/Core/repository/
  ↓
Agency/Core/runtime/
  ↓
Agency/Core/state/

Start with the work hierarchy.

Then follow how Tasks are executed, how WorkPackets supervise them, how Missions orchestrate them, and how Core preserves authority and evidence.

Current Validation State

The current production Core suite is validated through:

python Agency/unittest.py

The repository uses unittest, not pytest, as its canonical testing framework.

The retired LocalOperator scaffold is not part of the active runtime architecture.

Editor is the installed repository execution Agent.

WorkPackets are shared work infrastructure.

Missions are orchestration, not the primitive execution layer.

The repository should continue to tell that story as the system evolves.
