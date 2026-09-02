# CE-OS Agent Contract

You are operating directly on the canonical CE-OS Pixel workspace.

Canonical root:

    ~/ce-os

This repository is the active CE-OS implementation.
Do not treat Nitro-era repositories as canonical history.

## Platform

Target node:

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

## Git

The Pixel repository is canonical.

Make focused commits.
Do not rewrite unrelated source.
Do not commit generated runtime state, build directories, secrets,
model binaries, caches, screenshots, or temporary observation data.

Before committing:

    git status --short
    git diff --check

## Working method

Maintain:

    ~/ce-os/CHECKLIST.md

The checklist is the authoritative task ledger for the current mission.

For each meaningful task:

1. Inspect existing implementation.
2. Record intended work in CHECKLIST.md.
3. Make the smallest coherent change.
4. Validate it.
5. Observe runtime behavior when relevant.
6. Record result in CHECKLIST.md.
7. Commit a stable checkpoint.

Do not mark an item complete merely because source compiles.
Runtime-facing work requires runtime observation.

## QPS

Canonical QPS implementation:

    ~/ce-os/cpp/qps/cpp

Current baseline:

    qps_core compiled once as a static library
    CTest suite must remain green

Validate QPS with:

    cmake --build ~/ce-os/cpp/qps/cpp/build-pixel -j1
    ctest --test-dir ~/ce-os/cpp/qps/cpp/build-pixel --output-on-failure

Avoid clean rebuilds unless required.

## OperatorShell

OperatorShell is a Godot project whose source is:

    ~/ce-os/UI/OperatorShell

Godot project root:

    ~/ce-os/UI/OperatorShell/project.godot

Main scene:

    res://scenes/Main.tscn

Canonical QPS surface:

    UI/OperatorShell/_index.qps

OperatorShell is portrait-first on Pixel 6.

The Godot Android editor is not the source-of-truth editing environment.
Edit project.godot, .tscn, .tres, .gd and supporting files directly.

Runtime iteration should be automated:

    edit
    validate
    build/export
    install
    launch
    wait
    screenshot
    collect logs
    inspect
    close
    correct
    repeat

Never leave a broken test application running.

The UI must reflect real CE-OS backend state.
Do not fabricate backend state to make screenshots look correct.
