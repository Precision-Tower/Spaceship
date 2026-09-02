# Agency Ontology

## Purpose

This document defines the architectural ontology of the Agency repository.

Its purpose is not to describe implementation details, but to explain **why each
system exists** and **why it belongs where it does**.

Directory structure is part of the architecture. It is the primary navigation
mechanism for both humans and AI agents.

---

# First Principle

A directory exists because its parent requires it.

The parent explains why the child exists.

The child should not require prior knowledge to understand.

If either question cannot be answered clearly, the ontology is incomplete.

---

# Classification Rules

When introducing a new directory:

1. Identify the system it belongs to.
2. The parent must explain the child's purpose.
3. Prefer domain concepts over implementation concepts.
4. Avoid generic buckets such as `capabilities`, `runtime`, or `utils` unless
   they represent a true architectural system.
5. If a directory name requires additional explanation to understand, its
   parent is probably wrong.

---

# Agency

Agency is the complete operating system.

Its immediate children represent major knowledge domains or operational systems,
not implementation details.

Examples include:

- Core
- Agents
- Documentation
- Datasets
- Archive

---

# Core

Core contains the operational systems that make the Agency function.

Each child of Core represents a distinct system with a well-defined
responsibility.

---

# Mission System

The Mission system defines, executes, and records work.

## Pipeline

The Pipeline represents the ordered lifecycle of a mission.

Proposal
→ Review
→ Implementation
→ Verification

Each stage consumes the artifacts of the previous stage and produces artifacts
required by the next.

Implemented path:

```text
Agency/Core/missions/pipeline/
```

Current children:

- `review`
- `implementation`
- `verification`

`proposal` is currently produced by the Planning system and mission runtime.
That boundary remains explicit until the ontology defines whether proposal is a
Planning responsibility, a Pipeline stage, or both.

## Runtime

Executes missions.

## Tasks

Reusable executable mission tasks.

Implemented path:

```text
Agency/Core/missions/tasks/
```

## Work Packets

Delegated units of mission work.

Implemented path:

```text
Agency/Core/missions/work_packets/
```

---

# Repository System

The Repository system understands and safely modifies repositories.

Examples include:

- Repository Context
- Inspection
- Git Authority

Implemented path:

```text
Agency/Core/repository/
```

Current children:

- `context`
- `inspection`
- `git_authority`

---

# Planning System

Responsible for planning missions and generating proposals.

---

# State System

Responsible for persistent operational state and replay.

---

# CLI

Provides human interaction with the Agency.

---

# Projects

Represents project-level abstractions and orchestration.

---

# Remote

Provides remote execution capabilities.

---

# Architecture Rule

Architecture follows causal ownership, not implementation technique.

Organize directories according to **what system owns the responsibility**, not
according to the language, framework, or implementation mechanism.

The directory tree should tell the story of the system without requiring the
reader to inspect the code.

Every directory should answer:

    "Why does my parent need me?"

Every parent should answer:

    "Why do I contain this child?"
