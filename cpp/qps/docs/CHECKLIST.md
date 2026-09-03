# QPS Checklist

Implementation and validation ledger for Quick Parse Standard.

A checked item means the behavior has been demonstrated by implementation, tests, corpus evidence, or runtime validation. It does not mean merely intended.

## Mission

Build QPS into the compact, deterministic structural language used by CE-OS Engineering and simulation systems while keeping the language executable, testable, portable, and grounded in real corpus usage.

## Proven Baseline

### Parser and Corpus

- [x] Active QPS C++ implementation established under `cpp/qps/cpp`.
- [x] QPS CLI supports document parsing.
- [x] QPS CLI supports `--check`.
- [x] QPS CLI supports `--get <path>`.
- [x] Active Engineering corpus is part of the conformance target.
- [x] Recursive active Engineering corpus conformance test established.
- [x] Archive is excluded from active corpus conformance.
- [x] 33/33 active Engineering QPS documents parse successfully.

### AST Conformance

- [x] Exhaustive AST visitor/profiler established for the active corpus.
- [x] 33 active documents produce 33 programs.
- [x] Active AST census recorded.
- [x] 131 keys observed.
- [x] 196 terms observed.
- [x] 504 items observed.
- [x] 73 containers observed.
- [x] 297 strings observed.
- [x] 24 numerics observed.
- [x] 3 booleans observed.
- [x] 120 path references observed.
- [x] `/p` distinguished as path/reference typing rather than a physical unit.
- [x] Active physical units include `ft`, `in`, and `m`.

### Portable Module Surfaces

- [x] `_index.qps` established as canonical module-surface filename.
- [x] Active Engineering module surfaces migrated to `_index.qps`.
- [x] Archived Engineering module surfaces migrated for filesystem portability.
- [x] Historical tracked `<index.qps` surfaces removed.
- [x] Path resolver recognizes `_index.qps` module surfaces.
- [x] Module surfaces are valid on Windows-compatible filesystems.

### Active Surface Graph

- [x] Active Engineering module-surface graph validation established.
- [x] Connected modules are enumerated from the Engineering QPS root.
- [x] Each connected `_index.qps` surface is parsed.
- [x] Module delegation graph is checked for cycles.
- [x] Every surfaced symbol is resolved.
- [x] Terminal surfaced targets must be semantic Keys.
- [x] Resolved document owner and target node are retained.
- [x] Resolved targets must remain inside the workspace.
- [x] Duplicate/ambiguous surface aliases are rejected.
- [x] Real duplicate alias collision in `Engineering/qps/defs/MC/_index.qps` was exposed and corrected.
- [x] Full QPS validation baseline reaches 14/14 tests.

## Current Corpus Census

    documents=33
    programs=33
    keys=131
    terms=196
    items=504
    containers=73
    dictionaries=0
    dictionary_entries=0
    strings=297
    numerics=24
    booleans=3
    nulls=0
    identifiers=504
    path_references=120
    symbol_references=0
    execution_definitions=0
    execution_calls=0
    execution_actions=0
    execution_blocks=0
    calculations=0
    functions=0
    classes=0
    causal_relationships=0
    units:
      ft=1
      in=2
      m=1

These counts describe the current active corpus. They are evidence, not permanent language requirements.

## Active Milestone — Reference Semantics

QPS currently has two distinct reference representations.

### Legacy Path References

`PathReferenceNode` is the active module-surface/document-path representation used by the current Engineering corpus.

Current measured corpus baseline:

- [x] 120 active `PathReferenceNode` instances observed.
- [x] Active `PathReferenceNode` instances are authored in `_index.qps` module surfaces.
- [x] Active module-surface resolution is validated by `qps_active_surface_graph_test`.
- [x] Module delegation is acyclic.
- [x] Duplicate surfaced aliases are rejected.
- [x] Surfaced targets resolve to terminal semantic Keys.
- [x] Resolved targets remain inside the connected workspace.

- [x] Record explicit census split for `_index.qps` versus non-index `PathReferenceNode` instances: 120 index, 0 non-index.
- [x] Require zero unintended non-index legacy path references in the active corpus unless deliberately introduced.

### Structural Symbol References

`SymbolReferenceNode` is the structural semantic-navigation representation used by `[>...]` and local-binding references.

The runtime supports these authored origins:

- `CURRENT_FILE`
- `CURRENT_FOLDER_FILE`
- `RELATIVE_MODULE`
- `LOCAL_BINDING`

The resolver supports these terminal semantic targets:

- `KEY_DECLARATION`
- `TERM_DECLARATION`
- `ITEM_VALUE`

Existing conformance already proves:

- [x] direct structural Key resolution
- [x] nested Term resolution
- [x] explicit Item-value selection
- [x] child-module structural traversal
- [x] one-parent traversal
- [x] two-parent traversal
- [x] workspace-root escape rejection

Current active Engineering corpus baseline:

- [x] 0 active `SymbolReferenceNode` instances observed.
- [x] Structural-reference runtime semantics are implemented independently of active corpus usage.

Remaining structural-reference proof:

- [x] Explicitly prove `CURRENT_FILE` origin.
- [x] Explicitly prove `CURRENT_FOLDER_FILE` origin.
- [x] Explicitly prove `LOCAL_BINDING` through `resolveFrom()`.
- [x] Preserve `RELATIVE_MODULE` traversal witnesses.
- [ ] Preserve duplicate semantic structure rejection.
- [ ] Preserve unresolved-target rejection.
- [ ] Preserve invalid-descent rejection.
- [ ] Record structural-reference runtime contract in `docs/README.md`.
- [ ] Update `docs/QPS.qps` where executable specification changes are required.

### Reference Conformance Checkpoint

- [x] Extend the active AST census to report index and non-index path-reference populations separately.
- [x] Run the full QPS CTest suite: 14/14 passing.
- [x] Record the resulting reference-semantics baseline: 120 index path references, 0 non-index path references, 0 active structural symbol references.
- [ ] Distill proven reference architecture into `docs/README.md`.

## Future Language Milestones

### `%` Calculation

- [ ] Audit implemented calculation grammar against current tests and corpus.
- [ ] Establish calculation semantic conformance.
- [ ] Add active Engineering use cases before expanding syntax unnecessarily.

### `@` Geometry

- [ ] Inventory current geometry grammar and AST support.
- [ ] Define canonical geometry semantics from CE-OS Engineering requirements.
- [ ] Establish geometry conformance tests.
- [ ] Define the QPS-to-Godot geometry boundary.

### `$` Model

- [ ] Inventory currently lexed model syntax.
- [ ] Define model semantics before claiming the feature active.
- [ ] Establish model AST/runtime behavior.
- [ ] Add executable specification and conformance tests.

### `!` Causal

- [ ] Define canonical causal semantics from CE-OS requirements.
- [ ] Avoid inheriting obsolete syntax solely from historical documentation.
- [ ] Establish causal AST/runtime representation.
- [ ] Add executable specification and conformance tests.

## Validation Contract

Before expensive work:

    ./Android/Termux/bin/ce-os --json status

Canonical QPS build:

    cmake --build ~/ce-os/cpp/qps/cpp/build-pixel -j1

Canonical QPS test:

    ctest --test-dir ~/ce-os/cpp/qps/cpp/build-pixel --output-on-failure

Before committing:

    git status --short
    git diff --check

## Do Not

- [ ] Do not treat historical or stale language documentation as higher authority than the active implementation, tests, executable specification, and corpus.
- [ ] Do not change working syntax merely to satisfy obsolete documentation.
- [ ] Do not weaken resolver invariants to accommodate ambiguous corpus data.
- [ ] Do not reintroduce filesystem-invalid module-surface filenames.
- [ ] Do not claim a language feature is active merely because its token is lexed.
- [ ] Do not turn incidental AST census counts into permanent grammar requirements.
- [ ] Do not rewrite QPS semantics while working on unrelated CE-OS subsystems.

## Work Log

- [x] Active Engineering corpus conformance established — `598e507`.
- [x] Active QPS corpus AST measurement established — `6f2a432`.
- [x] AST conformance baseline recorded — `deeacf4`.
- [x] Portable `_index.qps` module surfaces adopted — `923ae29`.
- [x] Active QPS module-surface graph validation established — `050abf9`.
