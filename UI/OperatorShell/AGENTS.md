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
