# CE-OS Agent Contract

Canonical repository:

    ~/ce-os

The Pixel repository is authoritative.

## Entry

Read:

    ~/ce-os/_index.qps

first.

Then follow the nearest `_index.qps` before working deeper.

`_index.qps` is the CE-OS semantic navigation surface. Do not recursively inspect
the repository when an index can identify the required subsystem, file, command,
or deeper door.

Read only as deeply as the task requires.

## Work

Preserve unrelated unfinished work.

Do not reset, clean, overwrite, stage, or commit unrelated changes.

Start with the smallest relevant surface and widen only when evidence requires it.

Current implementation and passing tests outrank stale documentation.

Validate the smallest affected surface first.

Before committing:

    git status --short
    git diff --check

Stage only the coherent proven transaction.

## Pixel

Normal interactive control:

    ssh pixel

Automated execution:

    ops exec <script>

Privileged execution:

    ops root <script>

Diagnostics:

    ops doctor

Do not SSH as root. Cross privilege explicitly through `ops root`.

Do not hard-code transient hotspot addresses or Android-assigned usernames.

Do not bypass CE-OS thermal or Android safety controls.

## QPS

QPS is the CE-OS semantic language and navigation system.

Canonical door:

    ~/ce-os/qps/_index.qps

Move orchestration and semantic authority into QPS when existing QPS primitives
can express and prove the behavior.

Keep native implementation only where runtime, host, backend, bootstrap, or
machine capability currently requires it.

Discover the irreducible kernel from evidence. Do not predefine its
implementation language.

## Evidence

The Pixel filesystem, Git state, tests, and runtime observations are evidence.

Do not claim a change from generated patches or narration alone.
