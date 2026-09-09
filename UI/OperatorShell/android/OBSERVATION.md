# OperatorShell Visual Observation Contract

OperatorShell visual iteration on Pixel uses the following observation path:

    OperatorShell runtime
        ->
    screenshot
        ->
    ~/ce-os/state/ui-observation/latest.png
        ->
    operator-share
        ->
    temporary HTTPS URL
        ->
    visual inspection

The canonical local screenshot remains:

    ~/ce-os/state/ui-observation/latest.png

The latest temporary URL is written to:

    ~/ce-os/state/ui-observation/latest.url

Publish/capture with:

    qps screenshot

`operator-share` remains only as a compatibility surface for legacy callers
that explicitly provide an already-existing screenshot.

Only the screenshot image is uploaded.

Do not automatically upload:

    latest.log
    latest.xml
    CE-OS state
    source code
    tokens
    configuration
    filesystem contents

The temporary host is transport for visual observation only.
It is not part of CE-OS runtime architecture and must never be treated
as a trusted control plane.

A failed upload must not make an otherwise successful observation fail.
Local screenshot and log artifacts remain authoritative.


## Screenshot Contract

Canonical diagnostic/share image:

    ~/ce-os/state/ui-observation/latest.png

This image is intentionally reduced for AI and routine visual inspection.

Full-resolution evidence:

    ~/ce-os/state/ui-observation/latest-full.png

Do not use the full-resolution screenshot for routine AI/Codex inspection unless the reduced image cannot answer a specific visual question.
