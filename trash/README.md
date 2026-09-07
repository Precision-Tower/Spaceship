# CE-OS Trash

`trash/` is the repository-local disposal boundary.

CE-OS owns its filesystem footprint. Repository work must not scatter
temporary files through the repository root, source directories, `$HOME`,
or host-global `/tmp`.

- `trash/tmp/` â€” disposable scratch, test sandboxes, temporary patches,
  transient scripts, probes, generated intermediates, and temporary files.
  Its contents may be deleted freely.
- `trash/retired/` â€” intentionally displaced material retained temporarily.
- `trash/recovered/` â€” orphaned or suspicious material awaiting ownership
  classification.

Nothing below `trash/` is authoritative source.

The repository root is expected to remain immaculate: only intentional
top-level subsystem and authority surfaces belong there.
