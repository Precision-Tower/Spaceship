#!/usr/bin/env bash
set -Eeuo pipefail

DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WT="$(cd -P "$DIR/../../../.." && pwd)"
TMP="$(mktemp -d "$WT/trash/tmp/network-install-render-test.XXXXXXXX")"
trap 'rm -rf "$TMP"' EXIT

if python3 "$DIR/render.py" \
    --activation "$DIR/activation.env.example" \
    --output "$TMP/unresolved" >/dev/null 2>&1
then
    echo "FAIL: unresolved activation was accepted"
    exit 1
fi
[[ ! -e "$TMP/unresolved" ]]
echo "UNRESOLVED_REJECTION=PASS"

cat > "$TMP/resolved.env" <<'EOF'
CEOS_HOSTNAME=ce-os-network-proof
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
CEOS_WIFI_ENABLE=true
CEOS_WIFI_SSID=CEOS-PROOF-NETWORK
CEOS_WIFI_PSK=proof-only-password
EOF

python3 "$DIR/render.py" \
    --activation "$TMP/resolved.env" \
    --output "$TMP/nocloud"

UD="$TMP/nocloud/user-data"

grep -q -- '- openssh-server' "$UD"
grep -q -- '- network-manager' "$UD"
grep -q -- '- wpasupplicant' "$UD"
grep -q 'systemctl enable NetworkManager' "$UD"
grep -q 'systemctl enable ssh' "$UD"
grep -q 'nmcli connection add type wifi' "$UD"
grep -q 'ssid.*CEOS-PROOF-NETWORK' "$UD"
grep -q 'connection.autoconnect yes' "$UD"

if grep -q 'ce-os-reconstruct' "$UD"; then
    echo "FAIL: Network Install unexpectedly reconstructs CE-OS"
    exit 1
fi

echo "NETWORK_PACKAGES=PASS"
echo "WIFI_AUTOCONNECT_CONFIG=PASS"
echo "SSH_ENABLEMENT=PASS"
echo "CE_OS_RECONSTRUCTION_ABSENT=PASS"
echo "DISPOSABLE_RENDER=PASS"
