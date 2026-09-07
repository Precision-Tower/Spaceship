# Quick Parse Standard

Quick Parse Standard (QPS) is the CE-OS structural language used to express engineering and simulation information in compact `.qps` documents.

The active QPS implementation lives under `qps/cpp`.

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
    qps qry <selector> [path]
    qps probe <file> <line> [radius]
    qps probe <file.qps> <structural.path>
    qps scope <file.qps> <structural.path>
    qps scout <indexed-module-or-_index.qps> <authored-identity>

`probe`, `scope`, and `scout` are the proven source-navigation tool trio.

`probe` inspects an exact known target: either a physical source line/radius in an arbitrary file or a structural path in a QPS document.

`scope` inspects an exact QPS structural target plus its immediate authored structural members. It does not recurse through descendants, and an `Item` is a valid leaf.

`scout` discovers an exact authored identity inside one indexed QPS module. The module is identified by `_index.qps`; only immediate `qpsFiles` are searched, `_index.qps` itself is excluded, child modules are not descended, and the filesystem is not recursively traversed. Admitted parsed documents are inspected recursively by authored AST identity, not textual grep. Current recognized identities are `Key`, `Term`, `Item`, and named `ExecutionDefinition`.

All three source-navigation commands share this evidence form:

    path:start-end
    ln: source

## Validation

Canonical Pixel build and test baseline:

    cmake --build ~/ce-os/qps/cpp/build-pixel -j1
    ctest --test-dir ~/ce-os/qps/cpp/build-pixel --output-on-failure

The focused source-navigation/query checkpoint is `qps_structural_selection_test`, `qps_source_span_contract`, `qps_probe_cli`, `qps_scope_cli`, `qps_scout_cli`, and `qps_query_cli` passing.

The active Engineering corpus is itself a conformance surface and must remain parseable as the language evolves.

## Documentation Lifecycle

`qps/qps/checklist.qps` is the active authored QPS language/tooling implementation and work-control surface.

`qps/checklist.qps` owns native runtime, host-boundary, and future kernel continuation.

`docs/CHECKLIST.md` is supporting Markdown history and does not outrank current implementation, passing tests, or authored QPS authority.

As checklist work is completed and proven, durable language architecture and behavior are distilled into this README.

`docs/QPS.qps` remains the executable language specification and should evolve with the implementation and tests.

## Reference Semantics

QPS currently has two distinct reference representations.

`PathReferenceNode` is the legacy module-surface/document-path representation used by the active Engineering corpus. The active AST census records 120 path references, all 120 in `_index.qps` module surfaces and zero in non-index documents. The active surface-graph conformance test validates connected module delegation and terminal semantic resolution for this surface.

`SymbolReferenceNode` is the structural semantic-navigation representation. It preserves authored reference origin and supports current-file, current-folder-file, relative-module, and local-binding navigation. Structural resolution can terminate on a Key, Term, or explicitly selected Item value.

The structural resolver is runtime-tested for current-file navigation, sibling-file navigation, child and parent module traversal, local-binding rebasing, nested Term resolution, explicit Item-value selection, and workspace-root containment.

The active Engineering corpus currently contains zero `SymbolReferenceNode` instances. Structural references are therefore an implemented and tested runtime language capability, but are not yet an authored dependency of the active Engineering corpus.

## testSuite

`testSuite` is the canonical QPS-native testing library and execution-system target.

Its purpose is to combine the strongest ideas from systems such as `unittest` and `pytest` while remaining native to QPS structure, syntax, runtime semantics, and CE-OS development.

QPS tests are intended to be authored in `.qps` and eventually discovered, loaded, executed, asserted, filtered, and reported by the QPS runtime itself.

`testSuite` is also the concrete bootstrap target for the QPS general execution language.

Plain `{ ... }` is the general execution/control block family.

Specialized block families remain semantically distinct:

- `{ ... }` — general execution/control
- `{% ... }` — calculation
- `{@ ... }` — geometry
- `{$ ... }` — model
- `{! ... }` — causal

The general execution language may orchestrate or consume specialized block behavior, but the specialized languages are not aliases for plain `{}`.

Causal `{! ... }` definitions preserve authored Engineering topology. A side such as `Pump: (ME = FD)` means a component-domain transformation from `ME` to `FD`, not scalar equality. A relationship such as `Motor: (DC = ME) = Pump: (ME = FD)` preserves the `ME` output/input boundary between the two components. Runtime propagation validates that boundary before using the current provisional same-name semantic binding transfer.

QPS execution syntax should preserve normal structural ownership where practical:

    key.
    term: <executable behavior>;

Function, test, control-flow, binding, assertion, and related execution syntax are still under active design and must not be treated as canonical until implemented and proven.

Detailed execution-language design belongs in `docs/EXECUTION_DESIGN.md`.

The active authored implementation ledger belongs in `qps/qps/checklist.qps`; native runtime and kernel continuation belongs in `qps/checklist.qps`.

