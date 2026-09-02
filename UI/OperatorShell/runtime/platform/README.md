# OperatorShell Platform Runtime

OperatorShell uses one shared Godot UI with platform-specific runtime adapters.

## Shared

UI, scenes, layout, widgets, resources and service contracts remain shared.

## Linux

`linux/` implements direct Linux integration for Nitro-class CE-OS hosts.

Examples:

- local PTY
- local filesystem
- process launch
- CE-OS services

## Android

`android/` implements Pixel integration.

Android OperatorShell must not assume direct Termux filesystem access.
It communicates with the CE-OS Android/Termux backend through defined
service boundaries.

Termux is backend infrastructure, not the OperatorShell UI runtime.
