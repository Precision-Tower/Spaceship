# Editor → Core Migration Ledger

## Principle

If deleting `Agency/Agents/Editor` would permanently remove a capability,
that capability belongs in `Agency/Core`.

The Agent is disposable.
Core is authoritative.

---

## Already Core

- EditorTask contracts
- Task validation
- Persistence
- Repository inspection
- Patch proposal
- Patch authorization
- Patch application
- Verification
- Mission work packet integration

---

## Candidate migrations

- [ ] Operator CLI orchestration
- [ ] Help rendering
- [ ] Task command routing
- [ ] Implement command routing
- [ ] Status command adapter
- [ ] Tools command adapter
- [ ] Mission command adapter

---

## Definition of Done

The Editor agent becomes a thin shell that delegates to Core.
Factory-generated agents receive the same capabilities automatically.
