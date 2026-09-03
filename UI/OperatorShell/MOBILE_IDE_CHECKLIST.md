# OperatorShell Mobile IDE Checklist

## Mission

Turn OperatorShell on Android into a usable full IDE for CE-OS development on the Pixel 6.

The Android UI must not be treated as a compressed desktop layout.
Use a mobile interaction model with one primary surface at a time.

Linux/Desktop behavior must remain intact unless a shared abstraction explicitly improves both platforms.

## Active Work Log

- 2026-09-03 Milestone 1 reconciliation: mobile composition, bottom navigation,
  editable TextEdit, dirty-state tracking, buffer Save interaction, Android IME,
  headless `ops` controls, and deterministic visual observation are implemented.
  Files remain placeholder-backed; real filesystem read/write authority is the
  Milestone 2 boundary.

- 2026-09-03 Milestone 1 scope: implement Android-only Files / Editor / Terminal / Controls
  bottom navigation, one primary surface at a time, a native Godot editable text surface,
  placeholder file entries, and visual validation through `operator-cycle`.

## Current Proven Baseline

- [x] CE-OS Android diagnostic control works through UID 2000 / `u:r:shell:s0`.
- [x] OperatorShell can be force-stopped deterministically.
- [x] OperatorShell can be cold-launched deterministically.
- [x] OperatorShell foreground ownership can be verified.
- [x] Screenshots and logs can be captured automatically.
- [x] Successful observation leaves OperatorShell visible.
- [x] Fresh OperatorShell source can be packaged directly into the Android APK.
- [x] Fresh APK installation works.
- [x] `Main.gd` parses.
- [x] `[OperatorShell] ready` is reached.
- [x] Full OperatorShell construction reaches `[OperatorShell] build complete`.
- [x] Android direct filesystem browsing is intentionally blocked behind a placeholder.

## Mobile Layout Contract

Android must use persistent bottom navigation:

    Files
    Editor
    Terminal
    Controls

Only one primary surface should be visible at a time.

- [x] Replace Android desktop left/right dock composition with mobile surfaces.
- [x] Keep desktop/Linux dock layout unchanged.
- [x] Keep bottom navigation visible and readable.
- [x] Make Editor the normal working surface.
- [x] Make Files a full-height file browser surface.
- [x] Make Terminal a full-height terminal surface.
- [x] Make Controls a full-height CE-OS control/status surface.
- [ ] Ensure surfaces fit Pixel 6 portrait dimensions.
- [ ] Avoid horizontal overflow and inaccessible side controls.
- [ ] Validate all surfaces visually on-device.

## Editor

The editor must use Android's native keyboard through Godot text-editing controls.

Do not implement a custom keyboard.

- [x] Add a primary editable text surface for files.
- [x] Use Godot text input controls compatible with Android IME.
- [x] Tapping editor text must summon the system keyboard.
- [x] Android Back should dismiss the keyboard before leaving the editor when appropriate.
- [x] Editor must resize or remain usable when the keyboard is visible.
- [ ] Keep bottom navigation usable with IME behavior.
- [x] Support open file state for current placeholder/mobile-buffer files.
- [x] Support modified/dirty state.
- [x] Support explicit buffer Save interaction. Real persistence remains Milestone 2.
- [ ] Preserve cursor/scroll state when practical.

## Files

Files must behave conceptually like the VS Code Explorer.

Godot Android must not directly browse Termux/root paths with `DirAccess`.

- [ ] Define CE-OS filesystem platform interface.
- [ ] Add Android filesystem adapter.
- [ ] Keep Linux filesystem adapter/direct host behavior separate.
- [x] Render placeholder directory hierarchy as a tree. Real filesystem population remains Milestone 2.
- [ ] Expand/collapse directories.
- [x] Select placeholder files.
- [x] Open selected placeholder file in Editor.
- [x] Refresh current mobile Files tree.
- [ ] Display inaccessible/error states without breaking shell construction.

Required backend operations:

    fs.list
    fs.read
    fs.write
    fs.mkdir
    fs.rename
    fs.delete

Root-capable filesystem authority must remain behind an explicit CE-OS privileged boundary.

Do not expose arbitrary shell execution to the Godot UI.

## Filesystem Authority

Primary development root:

    ~/ce-os

The Android UI should be able to navigate CE-OS-authorized filesystem roots,
including root-backed paths when explicitly allowed by the backend.

- [ ] Define allowlisted filesystem roots.
- [ ] Define path canonicalization and traversal protections.
- [ ] Prevent `..` escapes from authorized roots.
- [ ] Keep privilege escalation inside CE-OS backend services.
- [ ] Return structured errors to OperatorShell.
- [ ] Do not make the Godot process itself root.

## Platform Boundaries

Current shared OperatorShell code still contains historical desktop assumptions.

Known examples include:

    /home/spaztic/...
    direct DirAccess
    direct FileAccess
    direct OS.execute
    desktop-local model/server paths
    dashboard.log assumptions

These must migrate behind platform services over time.

- [ ] Inventory host-specific paths in shared OperatorShell code.
- [ ] Define shared platform-service interface.
- [ ] Establish Linux adapter.
- [ ] Establish Android adapter.
- [ ] Move filesystem access behind platform service.
- [ ] Move process execution behind platform service.
- [ ] Move terminal backend access behind platform service.
- [ ] Move model-server integration behind platform service.
- [ ] Keep scenes/layout/widgets platform-neutral where practical.

Do not refactor unrelated subsystems merely to satisfy this checklist.
Work in coherent milestones.

## GDScript Quality Gate

Canonical repository GDScript indentation should be consistent.

- [ ] Add `gdscript-lint` or equivalent preflight script.
- [ ] Reject mixed indentation before Android build.
- [ ] Run audit across OperatorShell and Workbench.
- [ ] Do not auto-rewrite ambiguous mixed indentation.
- [ ] Add GDScript validation to `operator-preflight`.
- [ ] Catch parse failures before Gradle whenever possible.

## Validation Loop

Use the existing Android development loop.

Expected lifecycle:

    preflight
    build
    install
    force-stop old runtime
    cold-launch current runtime
    verify process
    verify top-resumed activity
    capture screenshot
    capture logs
    inspect
    leave successful runtime visible

Primary commands:

    UI/OperatorShell/android/tools/operator-build
    UI/OperatorShell/android/tools/operator-install
    UI/OperatorShell/android/tools/operator-observe
    UI/OperatorShell/android/tools/operator-cycle

Before expensive builds:

    ./Android/Termux/bin/ce-os --json status

## Milestone 1 — Mobile Shell

Do this first.

- [x] Implement Files / Editor / Terminal / Controls bottom navigation.
- [x] Show one primary mobile surface at a time.
- [x] Preserve desktop/Linux layout.
- [x] Add Editor surface with editable text control.
- [x] Verify Android system keyboard appears.
- [x] Use placeholder/mock file entries for Milestone 1.
- [x] Validate visually through the automated OperatorShell observation/headless loop.
- [x] Complete Milestone 1 without introducing privileged filesystem authority into Godot.

Completion rule:

Milestone 1 is complete only when the Pixel visibly shows a usable mobile IDE shell,
the Editor accepts text through the Android keyboard, all four surfaces can be reached,
and desktop behavior has not been intentionally replaced.

## Milestone 2 — CE-OS Filesystem Service

Begin only after Milestone 1 is visually usable.

### Filesystem Service Contract

The Files and Editor UI already exist. Milestone 2 must connect them to real
filesystem state without moving privileged authority into Godot.

The logical `fs.*` contract must be shared between Android and Linux/Desktop.

- [ ] `fs.list` returns typed structured entries, not rendered terminal text.
- [ ] Directory entries distinguish file, directory, symlink, and inaccessible/error state.
- [ ] Filesystem responses include canonical path information.
- [ ] `fs.read` returns real file content through the CE-OS service boundary.
- [ ] `fs.read` identifies binary/non-text files before loading them into TextEdit.
- [ ] `fs.read` applies a safe file-size policy for the mobile editor.
- [ ] `fs.write` persists editor contents through the CE-OS service boundary.
- [ ] `fs.write` detects stale writes when a file changed after it was opened.
- [ ] Use atomic write/replace where practical.
- [ ] Symlink handling cannot bypass authorized-root policy.
- [ ] Canonicalize paths before enforcing authorized-root boundaries.
- [ ] Reject traversal that escapes an authorized root after canonicalization.
- [ ] Privileged authority is operation-scoped; do not expose arbitrary shell execution.
- [ ] Filesystem failures return stable machine-readable error codes.
- [ ] Linux and Android implement the same logical `fs.*` contract.
- [ ] Normal `~/ce-os` editing uses the least privilege necessary.
- [ ] Root-backed paths require explicit allowlisting and privileged backend authority.
- [ ] Determine whether `GodotLaunchBridge.godot.open-project` is still required by the current architecture.


- [ ] Design `fs.list`.
- [ ] Design `fs.read`.
- [ ] Design `fs.write`.
- [ ] Design `fs.mkdir`.
- [ ] Design `fs.rename`.
- [ ] Design `fs.delete`.
- [ ] Implement backend path allowlisting.
- [ ] Implement root-capable backend authority where required.
- [ ] Connect Files tree to backend.
- [ ] Connect Editor open/save to backend.
- [ ] Validate against real `~/ce-os` files.

## Do Not

- Do not use ADB as the normal Windows control plane.
- Do not disable SELinux.
- Do not make Godot root.
- Do not hard-code Pixel IP addresses.
- Do not add new `/home/spaztic` assumptions.
- Do not restore dependence on the Godot Android editor UI.
- Do not fabricate CE-OS backend state.
- Do not commit generated Android build trees or runtime observations.
- Do not mix unrelated existing WIP into focused commits.

## Headless OperatorShell Development Loop

- [x] Add OperatorShell pre-build test suite.
- [x] Reject GDScript indentation regressions before Gradle.
- [x] Reject known invalid virtual keyboard call signatures before Gradle.
- [x] Validate OperatorShell control-server source contract.
- [x] Validate Android INTERNET permission contract.
- [x] Preserve Gradle build workspace across normal development cycles.
- [x] Add explicit clean-build escape hatch.
- [x] Reduce Android build from full rebuild behavior to incremental reuse.
- [x] Prove incremental build with 28/35 Gradle tasks up-to-date.
- [x] Add post-launch runtime contract.
- [x] Require OperatorShell ready/build-complete runtime proof.
- [x] Require control-server startup proof.
- [x] Add terminal `ops` control surface.
- [x] Control Files / Editor / Terminal / Controls from SSH.
- [x] Wake OperatorShell temporarily for headless control commands.
- [x] Restore Pixel display to Dozing after headless commands.
- [x] Wake / foreground / capture / sleep for `ops share`.
- [x] Prove remote screenshots while Pixel normally remains asleep.
- [x] Preserve hotspot and SSH as required development control plane.
- [x] Keep CE-OS thermal guardian authoritative.
- [x] Prove thermally blocked builds abort before Gradle.
- [ ] Add thermal-margin admission below Android SEVERE threshold.
- [ ] Record compact thermal diagnostics as a CE-OS command.

## Mobile IDE Interaction

- [ ] Files surface displays canonical CE-OS root tree.
- [ ] Directory tree expands/collapses like VS Code explorer.
- [ ] File selection opens selected file in Editor.
- [ ] Editor loads real file contents through CE-OS platform service.
- [ ] Editor writes modified files through explicit CE-OS service boundary.
- [ ] Root-required filesystem operations use privileged CE-OS backend.
- [ ] Editor dirty state is visible and accurate.
- [ ] Save action is explicit and validated.
- [ ] Android keyboard opens when Editor receives focus.
- [ ] Keyboard layout does not hide active editor content.
- [ ] Terminal surface remains usable on portrait Pixel.
- [ ] Bottom navigation remains persistent and readable.
- [x] Files / Editor / Terminal / Controls remain remotely selectable via `ops`.
- [x] `ops share` captures the requested surface deterministically.
- [x] Runtime/source test suite covers current mobile shell and control contracts.
