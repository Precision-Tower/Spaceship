UI/state is the canonical state modeling layer.

Purpose:

Move Dashboard from:

goal
→ action
→ artifact

toward:

state
→ transition
→ state

Rules:

Memory is not state.
Artifacts are not state.
Retrieval is not state.
Model output is not state.

State exists only in explicit state objects.

All state changes should eventually be represented by TransitionEvents.