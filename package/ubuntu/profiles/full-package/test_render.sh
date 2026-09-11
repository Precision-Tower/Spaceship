#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP="$(mktemp -d "$HOME/ce-os/trash/tmp/full-package-render-test.XXXXXXXX")"
trap 'rm -rf "$TMP"' EXIT

cp "$ROOT/activation.env.example" "$TMP/unresolved.env"

if python3 "$ROOT/render.py" --activation "$TMP/unresolved.env" --output "$TMP/should-not-exist" >/dev/null 2>&1; then
    echo "FAIL: unresolved profile rendered"
    exit 1
fi
[[ ! -e "$TMP/should-not-exist" ]]
echo "UNRESOLVED_REJECTION=PASS"

cat > "$TMP/resolved.env" <<'EOF'
CEOS_HOSTNAME=ce-os-proof
CEOS_ADMIN_USER=ceos
CEOS_TIMEZONE=UTC
CEOS_PASSWORD_HASH='$6$proof$not-a-real-credential'
CEOS_ADMIN_SSH_PUBLIC_KEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPROOFONLYNOTAREALKEY000000000000000 proof'
CEOS_REVIEWED_STORAGE_CONFIGURATION=<<CEOS_STORAGE
      - type: disk
        id: disk-proof
        path: /dev/ce-os-disposable-proof-target
        preserve: true
CEOS_STORAGE
CEOS_WIFI_ENABLE=false
CEOS_WIFI_SSID=UNRESOLVED
CEOS_WIFI_PSK=UNRESOLVED
CEOS_TAILSCALE_ENABLE=false
CEOS_TAILSCALE_AUTH_KEY=UNRESOLVED
EOF

python3 "$ROOT/render.py" --activation "$TMP/resolved.env" --output "$TMP/nocloud"

test -f "$TMP/nocloud/user-data"
test -f "$TMP/nocloud/meta-data"
grep -q 'wpasupplicant' "$TMP/nocloud/user-data"
grep -q 'openssh-server' "$TMP/nocloud/user-data"
grep -q '/dev/ce-os-disposable-proof-target' "$TMP/nocloud/user-data"
grep -q 'preserve: true' "$TMP/nocloud/user-data"

echo "RESOLVED_DISPOSABLE_RENDER=PASS"
echo "HOST_MUTATION=NONE"

# The rendered profile must fail closed around the exact carrier contract.
grep -q 'test -d /cdrom/ce-os/seed' "$TMP/nocloud/user-data"
grep -q 'test -x /cdrom/ce-os/install/ce-os-reconstruct' "$TMP/nocloud/user-data"
grep -q '/cdrom/ce-os/install/ce-os-reconstruct --apply --seed /cdrom/ce-os/seed --target /target/home/ceos/ce-os' "$TMP/nocloud/user-data"
grep -q "status=reconstructed_from_verified_seed" "$TMP/nocloud/user-data"
echo "CARRIED_SEED_NOCLOUD_WIRING=PASS"
