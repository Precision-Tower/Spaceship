#!/bin/bash
cd ~/ce-os/trash/tmp/provisioning-build
[ -f provisioning.img ] || exit 1
SIZE=
(stat−c["SIZE" -gt 10000000 ] || exit 1
echo "Tests passed"
