# Quick Parse Standard

Quick Parse Standard (QPS) is the CE-OS structural language used to express engineering and simulation information in compact `.qps` documents.

The active QPS implementation lives under `cpp/qps/cpp`.

`docs/QPS.qps`, the parser/runtime implementation, automated tests, and active Engineering corpus together define the executable language. Historical documentation does not override behavior established by the current implementation and proven corpus.

## Current Language Surface

The active corpus demonstrates structural QPS built from programs, keys, terms, items, containers, identifiers, path references, strings, numerics, booleans, and unit-bearing values.

Current measured active Engineering corpus:

- 33 QPS documents
- 33 programs
- 131 keys
- 196 terms
- 504 items
- 73 containers
- 120 path references
- 297 strings
- 24 numerics
- 3 booleans

Observed units include `ft`, `in`, and `m`.

The `/p` suffix is a path/reference type marker and is not a physical unit.

Features that are lexed, documented, experimental, or planned are not considered active merely because syntax exists for them.

## Module Surfaces

The canonical portable module-surface filename is `_index.qps`.

Historical module names such as `<index.qps` are not canonical and must not be reintroduced.

Active Engineering module surfaces form a validated delegation graph.

The current surface resolver requires:

- module delegation to remain acyclic
- surfaced symbols to resolve unambiguously
- terminal surfaced targets to resolve to semantic Keys
- resolved targets to remain within the connected workspace
- duplicate aliases to be rejected rather than silently selected

## CLI

The QPS command-line interface supports:

    qps <document.qps>
    qps <document.qps> --check
    qps <document.qps> --get <path>

## Validation

Canonical Pixel build and test baseline:

    cmake --build ~/ce-os/cpp/qps/cpp/build-pixel -j1
    ctest --test-dir ~/ce-os/cpp/qps/cpp/build-pixel --output-on-failure

The established checkpoint is 14/14 QPS tests passing.

The active Engineering corpus is itself a conformance surface and must remain parseable as the language evolves.

## Documentation Lifecycle

`docs/CHECKLIST.md` is the active implementation ledger.

As checklist work is completed and proven, durable language architecture and behavior are distilled into this README.

`docs/QPS.qps` remains the executable language specification and should evolve with the implementation and tests.

## Reference Semantics

QPS currently has two distinct reference representations.

`PathReferenceNode` is the legacy module-surface/document-path representation used by the active Engineering corpus. The active AST census records 120 path references, all 120 in `_index.qps` module surfaces and zero in non-index documents. The active surface-graph conformance test validates connected module delegation and terminal semantic resolution for this surface.

`SymbolReferenceNode` is the structural semantic-navigation representation. It preserves authored reference origin and supports current-file, current-folder-file, relative-module, and local-binding navigation. Structural resolution can terminate on a Key, Term, or explicitly selected Item value.

The structural resolver is runtime-tested for current-file navigation, sibling-file navigation, child and parent module traversal, local-binding rebasing, nested Term resolution, explicit Item-value selection, and workspace-root containment.

The active Engineering corpus currently contains zero `SymbolReferenceNode` instances. Structural references are therefore an implemented and tested runtime language capability, but are not yet an authored dependency of the active Engineering corpus.

