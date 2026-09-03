# CE-OS Agent Contract

You are operating directly on the canonical CE-OS Pixel workspace.

Canonical root:

    ~/ce-os

This repository is the active CE-OS implementation.
Do not treat Nitro-era repositories as canonical history.

## Platform

Target development node:

    Pixel 6 / oriole
    Android
    Termux control plane
    rooted through Magisk
    CE-OS guardian/runtime

SSH is the preserved control plane.

Heavy compute must respect CE-OS state:

    requested_mode
    effective_mode
    allow_compute
    thermal_state
    power_state
    platform_state

Before expensive work, inspect:

    ./Android/Termux/bin/ce-os --json status

Do not bypass thermal or Android safety controls.

## Architecture

CE-OS/
  Agency/
  Android/
  Engineering/
  UI/
    OperatorShell/
    Workbench/
  cpp/
    qps/
  state/

Runtime state belongs under:

    ~/ce-os/state

Android Termux source belongs under:

    ~/ce-os/Android/Termux

Privileged Android services belong under:

    ~/ce-os/Android/Privileged

Shared UI must remain platform-neutral where practical.

Platform-specific filesystem, process, privilege, and host integration must live behind CE-OS platform services or adapters.

Do not introduce host-specific paths or direct Termux/root assumptions into shared UI code.

Android Godot must not directly depend on access to the Termux or root filesystem.
Privileged operations must cross an explicit CE-OS service boundary.

## Git

The Pixel repository is canonical.

Make focused commits.
Do not rewrite unrelated source.
Do not commit generated runtime state, build directories, secrets,
model binaries, caches, screenshots, or temporary observation data.

Before committing:

    git status --short
    git diff --check

## Workspace Documentation

`~/ce-os/AGENTS.md` is the universal operating contract for all CE-OS workspaces.

Do not create per-workspace `AGENTS.md` files unless a future requirement cannot
be represented by the universal contract and explicitly requires an exception.

Every CE-OS owned workspace/module maintains:

    docs/README.md
    docs/CHECKLIST.md

`docs/README.md` records durable architectural truth for that workspace,
including its purpose, structure, interfaces, terminology, established behavior,
and proven design decisions.

`docs/CHECKLIST.md` is the active implementation and validation ledger for that
workspace. It records the proven baseline, active milestone, known gaps, future
work, validation requirements, and concise work history.

A checked checklist item means the behavior has been demonstrated by appropriate
evidence. Implementation alone is not sufficient when tests, integration, or
runtime observation are required.

As checklist milestones are completed and proven, distill durable architectural
information into `docs/README.md`. Preserve useful validation and milestone
history in `docs/CHECKLIST.md`; do not turn the README into a task log.

Parent workspace documentation should link to or summarize child workspaces at
the integration level rather than duplicating detailed child checklists.

Do not create documentation surfaces for incidental implementation directories,
generated output, build trees, caches, vendor dependencies, or runtime state.
The convention applies to CE-OS owned architectural workspaces/modules.

## Working Method

For each meaningful task:

1. Read `~/ce-os/AGENTS.md`.
2. Read the active workspace `docs/README.md`.
3. Read the active workspace `docs/CHECKLIST.md`.
4. Inspect the existing implementation.
5. Record or confirm the intended work in `docs/CHECKLIST.md`.
6. Make the smallest coherent change.
7. Validate it.
8. Observe runtime behavior when relevant.
9. Record proven results in `docs/CHECKLIST.md`.
10. Distill newly established architectural truth into `docs/README.md`.
11. Commit a stable, focused checkpoint.

Do not mark an item complete merely because source compiles.
Runtime-facing work requires runtime observation.

Mission-specific implementation details belong in workspace documentation,
not in `AGENTS.md`.

## QPS

Canonical QPS implementation:

    ~/ce-os/cpp/qps/cpp

The QPS CTest suite must remain green.

Validate QPS with:

    cmake --build ~/ce-os/cpp/qps/cpp/build-pixel -j1
    ctest --test-dir ~/ce-os/cpp/qps/cpp/build-pixel --output-on-failure

Avoid clean rebuilds unless required.

## OperatorShell

OperatorShell is the shared Godot operator interface:

    ~/ce-os/UI/OperatorShell

Godot project:

    ~/ce-os/UI/OperatorShell/project.godot

Main scene:

    res://scenes/Main.tscn

Canonical QPS surface:

    UI/OperatorShell/_index.qps

The same OperatorShell project targets Linux and Android.

Android uses a mobile/portrait interaction model.
Linux may use a desktop interaction model.

The Godot Android editor is not the source-of-truth editing environment.
Edit project.godot, .tscn, .tres, .gd, and supporting files directly.

Runtime iteration should be automated:

    edit
    validate
    build/export
    install
    launch
    observe
    inspect
    correct
    repeat

Never leave a broken test application running.

The UI must reflect real CE-OS backend state.
Do not fabricate backend state to make screenshots look correct.

## Remote Access

The canonical Pixel CE-OS node is reached from Windows with:

    ssh pixel

`pixel` is the CE-OS-facing SSH identity for the Pixel.

Do not use ADB as the normal control/development transport.
Do not substitute a hard-coded Pixel IP.
Do not modify the Windows SSH configuration unless the mission explicitly requires
transport maintenance.

Once connected and the prompt is already on PIXEL, execute commands locally.
Do not recursively run `ssh pixel` from inside the Pixel.

Normal development transport:

    Windows / Codex
          |
      ssh pixel
          |
          v
    Pixel ~/ce-os
          |
          +-- source editing
          +-- builds
          +-- Android control
          +-- runtime observation
          +-- screenshots/logs

ADB is optional Android maintenance/debugging only.
Fastboot is provisioning/recovery only.

## OperatorShell Headless Development Contract

OperatorShell development on Pixel is normally headless. The physical display
may remain asleep during development.

Use the canonical terminal control surface:

    ops cycle
    ops files
    ops editor
    ops terminal
    ops controls
    ops share

`ops cycle` must run the OperatorShell test suite before expensive Android
builds.

Normal Android builds must preserve the incremental Gradle workspace. Use a
clean build only when required:

    CEOS_OPERATOR_CLEAN_BUILD=1 ops cycle

Runtime-facing work is not complete until runtime observation succeeds.

The OperatorShell control plane must preserve SSH, hotspot connectivity,
the CE-OS thermal guardian, and Android safety controls. Never bypass CE-OS
thermal admission to force a build.

Shared Godot UI must not directly assume Termux or root filesystem access.
Filesystem, privilege, Android framework, and host-specific behavior must cross
explicit CE-OS platform-service boundaries.

The Pixel may temporarily wake for OperatorShell control or visual observation.
Headless operations should restore the display to its prior sleeping state.
