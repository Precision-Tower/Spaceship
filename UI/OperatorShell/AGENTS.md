# OperatorShell Agent Contract

Scope:

    ~/ce-os/UI/OperatorShell

OperatorShell is the primary CE-OS operator interface.

## Target

Pixel 6
portrait orientation
Android
Godot 4.x project format

Project root:

    project.godot

Main scene:

    res://scenes/Main.tscn

QPS document:

    _index.qps

## Rules

Do not reorganize the project tree unnecessarily.

Prefer editing:

    project.godot
    scenes/
    layout/
    widgets/
    runtime/
    resources/
    *.gd
    *.tscn
    *.tres

Keep res:// references project-root relative.

Never reintroduce:

    res://OperatorShell/

Do not rename _index.qps.

Do not use filenames containing Windows-invalid characters such as:

    < > : " / \ | ? *

## Visual iteration

Every UI iteration should eventually pass through:

    android/tools/operator-observe

The observation loop is the runtime truth.

A screenshot without corresponding source state is not sufficient evidence.
A successful build without visual observation is not sufficient for
layout work.

## Portrait

OperatorShell is portrait-first.

Do not design around the landscape orientation of the Godot Android editor.

The editor itself is tooling.
The exported OperatorShell application is the product.

## Cross-Platform Contract

OperatorShell is one shared Godot application targeting:

    Nitro -> Linux
    Pixel -> Android

The visual/UI layer must remain platform-neutral wherever practical.

Shared code includes:

    project.godot
    scenes/
    layout/
    widgets/
    resources/

Platform-specific operating-system behavior must be isolated behind
runtime adapters.

Do not scatter checks such as:

    OS.get_name() == "Android"

through UI/layout/widget code.

Do not hard-code Termux paths such as:

    /data/data/com.termux/files/home

inside shared OperatorShell UI code.

Termux is part of the Pixel CE-OS backend/control substrate.
It is not OperatorShell itself.

Preferred architecture:

    runtime/
      platform/
        Platform.gd
        linux/
        android/

Shared OperatorShell code should call abstract services such as:

    terminal
    filesystem
    process
    ce_os_status
    workbench
    model_service

Linux adapters may communicate directly with the Linux host.

Android adapters should communicate with CE-OS Android/Termux services
through a defined bridge/API.

The same OperatorShell project should remain usable on both Nitro and Pixel.

## Godot Android Export Resources

Official Godot 4.7.2 Android export resources are available at:

    ~/ce-os/Android/Godot/4.7.2.stable/

Contents:

    android_debug.apk
    android_release.apk
    android_source.zip
    version.txt

These are tooling inputs, not OperatorShell source.

The automated OperatorShell build pipeline should use these resources where
appropriate rather than requiring manual operation of the Godot Android editor.

Canonical OperatorShell source remains:

    ~/ce-os/UI/OperatorShell

## Confirmed Android Export Boundary

The extracted Godot Android Gradle template is packaging infrastructure only.

Its:

    src/main/assets/

directory is empty before export.

The Gradle template does not convert .gd/.tscn/.tres/project.godot into a
Godot runtime payload.

Therefore the immediate engineering task is NOT to redesign Gradle.

The missing step is to reproduce Godot's noninteractive project
export/packing stage so that the generated project payload is placed into
the Android template before Gradle packaging.

Do not attempt to make Gradle parse Godot project source directly.

## Pixel Portrait Interaction Contract

Pixel OperatorShell is a portrait-first, single-surface interface.

The default visible state is:

    WORKSPACE

The workspace should consume essentially the entire usable screen.

Controls, Files, and Terminal are transient surfaces rather than permanent
desktop sidebars.

Primary transient surfaces:

    CONTROLS
    FILES
    TERMINAL

Only one primary transient surface may be open at a time.

Opening:

    CONTROLS

must close:

    FILES
    TERMINAL

Opening:

    FILES

must close:

    CONTROLS
    TERMINAL

Opening:

    TERMINAL

must close:

    CONTROLS
    FILES

Closing the active transient surface returns to:

    WORKSPACE

All inactive surfaces must collapse completely out of the usable workspace.
Do not permanently reserve left/right rail width on Pixel.

Small edge handles, tabs, buttons, or compact navigation affordances may
remain visible to reopen hidden surfaces, but they must not materially reduce
the workspace area.

### Terminal Behavior

Terminal is a special transient surface.

It should behave like a portrait-native bottom sheet or vertically expandable
panel.

When Terminal opens:

    Controls closes.
    Files closes.

When the Android software keyboard opens:

    Terminal must remain upright.
    Terminal must resize or move upward with the keyboard.
    The active prompt/input region must remain visible.
    The application must not rotate sideways to accommodate the keyboard.

The user must be able to:

    open terminal
    type
    see the active command/input
    dismiss keyboard
    collapse terminal
    return to workspace

without changing device orientation.

### Portrait Orientation

Pixel OperatorShell remains portrait-oriented.

Do not rotate the application into landscape for:

    Terminal
    keyboard
    Controls
    Files
    dialogs
    normal OperatorShell interaction

### Mobile Composition Rule

Do not shrink the desktop OperatorShell layout until every desktop panel fits.

Instead, preserve the shared semantic components while giving Pixel a
mobile composition:

    one primary surface at a time
    full workspace when panels are closed
    mutually-exclusive transient panels
    keyboard-aware terminal
    portrait orientation

Linux/Nitro may use a persistent multi-panel desktop composition.

Pixel/Android may use the same shared widgets and services with a different
layout/composition strategy.

## Remote Visual Observation

Pixel screenshots may be temporarily published for visual inspection using:

    UI/OperatorShell/android/tools/operator-share

The helper publishes only:

    state/ui-observation/latest.png

and writes the resulting temporary HTTPS URL to:

    state/ui-observation/latest.url

Do not publish logs, filesystem contents, CE-OS state, tokens, or source code.

## Screenshot Contract

Canonical diagnostic/share image:

    ~/ce-os/state/ui-observation/latest.png

This image is intentionally reduced for AI and routine visual inspection.

Full-resolution evidence:

    ~/ce-os/state/ui-observation/latest-full.png

Do not use the full-resolution screenshot for routine AI/Codex inspection unless the reduced image cannot answer a specific visual question.
