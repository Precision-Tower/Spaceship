# CE-OS QPS Cipher

Cipher ingests external representations and normalizes their meaning into an
intermediate representation that can be emitted as canonical QPS.

Initial sources:

- JSON
- YAML
- Python structural syntax

Later:

- constrained C++
- executable behavior after QPS general execution `{}` is stable

Cipher does not silently promote inference to fact.

Every translated element carries provenance and a translation state:

- direct
- mapped
- inferred
- unresolved
- unsupported

Architecture:

    source
      -> source adapter
      -> Cipher IR
      -> QPS emitter
      -> translation report

Phase 1 is structural only.
