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

- [x] Extend operator-build from PCK generation into generated-template APK packaging.
- [ ] Patch generated Android package to load operatorshell.pck through GodotApp --main-pack.
- [x] Isolate Godot Android editor rotation workaround inside operator-build tooling.
- [x] Keep fallback PCK reuse guarded by source freshness while editor export-pack crash is investigated.
- [x] Enforce portrait orientation in OperatorShell project/export contract.
- [ ] Validate all Godot resources and scene references.
- [x] Establish Android export/build path for OperatorShell.
- [x] Define OperatorShell Android package identity.
- [x] Build first OperatorShell APK.
- [x] Install OperatorShell APK on Pixel.
- [x] Launch OperatorShell through scripted harness.
- [x] Capture first OperatorShell screenshot.
- [x] Capture Godot/runtime logs.
- [x] Close test application automatically.
- [x] Inspect first render and record defects.
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

## Cross-Platform OperatorShell

- [ ] Define shared OperatorShell platform-service interface.
- [ ] Inventory current runtime scripts for Linux/Termux assumptions.
- [ ] Separate Linux-specific behavior from shared UI code.
- [ ] Separate Android/Termux-specific behavior from shared UI code.
- [ ] Establish runtime/platform/linux adapters.
- [ ] Establish runtime/platform/android adapters.
- [ ] Keep scenes/layout/widgets platform-neutral.
- [ ] Ensure Pixel Android UI communicates with Termux through CE-OS bridge.
- [ ] Verify same Godot project remains runnable on Linux and Android.

## Godot Android Toolchain

- [x] Download official Godot 4.7.2 export-template package.
- [x] Verify export-template archive.
- [x] Locate Android debug template.
- [x] Locate Android release template.
- [x] Locate Android source template.
- [x] Determine noninteractive project packaging/PCK generation path.
- [x] Wire Godot Android resources into operator-build.

## OperatorShell Android Template

- [x] Inspect Godot 4.7.2 android_source.zip.
- [x] Confirm Gradle wrapper and Android template project exist.
- [x] Confirm debug/release Godot engine AARs exist.
- [x] Identify how exported project payload/PCK is injected.
- [x] Set OperatorShell package/application metadata.
- [x] Wire template build into operator-build.

## Confirmed Export Boundary

- [x] Godot Android Gradle template does not generate project payload.
- [x] src/main/assets is empty in the extracted template.
- [x] Prebuilt android_debug.apk contains no OperatorShell/project payload.
- [x] Reproduce Godot project export/packaging step noninteractively.
- [x] Populate Android template assets with generated Godot payload.
- [x] Build standalone OperatorShell APK from populated template.
