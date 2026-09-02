# CE-OS Active Checklist

## Current Mission

Make OperatorShell a portrait-first Godot Android interface that can be
developed and visually validated from the Pixel through an automated
edit/build/launch/observe loop.

## Baseline

- [x] Pixel is canonical CE-OS workspace.
- [x] Pixel Git repository established.
- [x] QPS builds on Pixel.
- [x] QPS test suite passes 11/11.
- [x] QPS core compiles once as qps_core.
- [x] CE-OS platform verification persists.
- [x] Runtime state uses ~/ce-os/state.
- [x] Node mode can become effective.
- [x] Godot Android editor installed.
- [x] OperatorShell has project.godot.
- [x] OperatorShell res:// paths normalized.
- [x] OperatorShell canonical QPS index is _index.qps.
- [x] Android API 36 SDK platform installed.
- [x] Pixel-native Android build toolchain proven.
- [x] CE-OS native Android control app builds on Pixel.

## OperatorShell Bring-Up

- [ ] Enforce portrait orientation in OperatorShell project/export contract.
- [ ] Validate all Godot resources and scene references.
- [ ] Establish Android export/build path for OperatorShell.
- [ ] Define OperatorShell Android package identity.
- [ ] Build first OperatorShell APK.
- [ ] Install OperatorShell APK on Pixel.
- [ ] Launch OperatorShell through scripted harness.
- [ ] Capture first OperatorShell screenshot.
- [ ] Capture Godot/runtime logs.
- [ ] Close test application automatically.
- [ ] Inspect first render and record defects.
- [ ] Iterate until initial shell renders correctly.

## UI Contract

- [ ] Portrait-first Pixel 6 layout.
- [ ] OperatorShell shell/navigation visible.
- [ ] Terminal surface usable.
- [ ] CE-OS backend status visible.
- [ ] Node/effective mode reflects actual backend state.
- [ ] Workbench launch surface defined.
- [ ] No dependence on Godot Android editor UI during normal iteration.

## Completion Rule

An item is complete only when validated by source inspection, build/test,
or runtime observation appropriate to the item.
