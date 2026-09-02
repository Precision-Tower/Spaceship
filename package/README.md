# Precision Tower Deployment Package

This directory contains the deployment, verification, operator-command, and
service-definition surface for a Precision Tower Node.

## Current scope

The package can:

- verify repository, host, and hardware prerequisites
- install operator command wrappers
- install a package-managed environment file
- validate boot, service, remote-access, hardware-readiness, and operator-command contracts
- safely uninstall artifacts it owns

It does not currently install packages, configure firewall rules, enable
services, modify SSH or Tailscale, or select a persistent Agency daemon.

## Hardware readiness

`config/hardware.env` defines the package-owned target hardware policy.
`verify.sh` reports host inventory, NVIDIA detection, driver visibility, CUDA
runtime/toolkit visibility, VRAM, and Precision Tower acceptance.

`install.sh --dry-run` reports whether `--apply` would be blocked.
`install.sh --apply` refuses to mutate the installation destinations unless the
host satisfies the hardware policy.

## Agency service status

`systemd/agency.service.unresolved` is intentionally non-installable.

The repository does not yet expose a proven daemon-style Agency entry point.
The unresolved unit documents that state and prevents the installer from
inventing a persistent runtime command.

## Usage

Run read-only verification:

    package/verify.sh

Run the package tests:

    package/tests/run_all.sh

Preview installation:

    package/install.sh --dry-run

Apply the currently supported installation phase:

    package/install.sh --apply

Preview removal:

    package/uninstall.sh --dry-run

Remove package-managed artifacts:

    package/uninstall.sh --apply

## Installed artifacts

The current installation phase may create:

- operator command symlinks under `/usr/local/bin`
- `/etc/precision-tower-node/default.env`

The uninstaller removes only symlinks that still point to this package and
environment files carrying the package ownership marker.

## Layout

- `commands/` — operator command wrappers
- `config/` — package policy and configuration examples
- `lib/` — shared shell functions
- `manifests/` — command and package inventories
- `packages/` — grouped operating-system package lists
- `systemd/` — service definitions and unresolved service policy
- `tests/` — package contract tests
