# Cipher Checklist

## Phase 1 — Structural Normalization

- [x] Define Cipher IR.
- [x] Preserve source language/path/location.
- [x] Preserve translation confidence/state.
- [x] Implement JSON reader.
- [ ] Implement YAML reader.
- [x] Implement deterministic QPS emitter.
- [x] Add translation report.
- [x] Add focused tests.
- [ ] Prove JSON and YAML normalize through the same IR.
- [ ] Prove emitted QPS is deterministic.

## Phase 2 — Python Structural Extraction

- [x] Parse Python AST.
- [x] Extract classes.
- [x] Extract assignments/constants.
- [x] Extract function signatures.
- [x] Preserve function-body execution structure as deferred until QPS general execution grammar stabilizes.
- [x] Run against Engineering Pipe sources with zero true information-loss gaps.

## Phase 3 — C++ Structural Extraction

- [ ] Define supported C++ subset.
- [ ] Extract structs/classes/functions/constants.
- [ ] Mark unsupported constructs explicitly.
- [ ] Do not attempt arbitrary C++ semantic equivalence.

## Phase 4 — Executable Translation

Blocked until QPS general execution `{}` is stable.

- [ ] Map control flow.
- [ ] Map function bodies.
- [ ] Map algorithmic expressions.
- [ ] Promote proven Cipher behavior into a native QPS library/tool.
