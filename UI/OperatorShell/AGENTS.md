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
