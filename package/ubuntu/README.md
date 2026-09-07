# CE-OS Ubuntu LTS Substrate

This directory defines installer inputs; it does not contain or write boot
media.

Before physical installation, the Operator must explicitly accept an exact
stable Ubuntu LTS image, architecture, source origin, filename, and SHA-256.

`autoinstall/user-data.template` intentionally retains unresolved placeholders
for host identity, password hash, SSH public key, and reviewed storage policy.
A tracked template must never silently choose a disk or embed credentials.

The future one-flow install sequence is:

Ubuntu LTS -> locate seed -> verify seed -> reconstruct CE-OS -> verify CE-OS.
