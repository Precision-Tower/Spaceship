#!/usr/bin/env python3
import argparse
import os
import re
import shlex
import sys
from pathlib import Path

REQUIRED = (
    "CEOS_HOSTNAME",
    "CEOS_ADMIN_USER",
    "CEOS_TIMEZONE",
    "CEOS_PASSWORD_HASH",
    "CEOS_ADMIN_SSH_PUBLIC_KEY",
    "CEOS_REVIEWED_STORAGE_CONFIGURATION",
)

def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(2)

def load_env(path):
    values = {}
    lines = path.read_text().splitlines()
    i = 0
    while i < len(lines):
        lineno = i + 1
        raw = lines[i]
        line = raw.strip()
        i += 1

        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            die(f"{path}:{lineno}: expected KEY=VALUE")

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            die(f"{path}:{lineno}: invalid key {key!r}")

        # Explicit heredoc-style values are used for reviewed multiline
        # structures such as Subiquity storage configuration.
        if value.startswith("<<"):
            tag = value[2:].strip()
            if not re.fullmatch(r"[A-Z][A-Z0-9_]*", tag):
                die(f"{path}:{lineno}: invalid multiline terminator")
            body = []
            while i < len(lines) and lines[i] != tag:
                body.append(lines[i])
                i += 1
            if i >= len(lines):
                die(f"{path}:{lineno}: missing multiline terminator {tag}")
            i += 1
            value = "\n".join(body)
        elif value and value[0] in "'\"":
            try:
                parsed = shlex.split(value, posix=True)
            except ValueError as exc:
                die(f"{path}:{lineno}: {exc}")
            if len(parsed) != 1:
                die(f"{path}:{lineno}: expected one shell-style value")
            value = parsed[0]

        values[key] = value

    return values

def yaml_single(value):
    return "'" + value.replace("'", "''") + "'"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--activation", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    if not args.activation.is_file():
        die(f"activation file not found: {args.activation}")

    v = load_env(args.activation)

    unresolved = []
    for key in REQUIRED:
        value = v.get(key, "")
        if not value or value == "UNRESOLVED":
            unresolved.append(key)
    if unresolved:
        die("required activation inputs unresolved: " + ", ".join(unresolved))

    hostname = v["CEOS_HOSTNAME"]
    user = v["CEOS_ADMIN_USER"]
    timezone = v["CEOS_TIMEZONE"]
    password_hash = v["CEOS_PASSWORD_HASH"]
    ssh_key = v["CEOS_ADMIN_SSH_PUBLIC_KEY"]
    storage = v["CEOS_REVIEWED_STORAGE_CONFIGURATION"]

    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", hostname):
        die("CEOS_HOSTNAME is not a conservative hostname")
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", user):
        die("CEOS_ADMIN_USER is not a conservative Linux username")
    # Rendering occurs on the Pixel/Termux provisioning authority, whose
    # zoneinfo tree is not the Ubuntu target's authority. Reject unsafe or
    # malformed values here; target availability is verified against the
    # accepted Ubuntu substrate separately.
    if (
        not re.fullmatch(r"[A-Za-z0-9_+.-]+(?:/[A-Za-z0-9_+.-]+)*", timezone)
        or timezone.startswith("/")
        or ".." in timezone.split("/")
    ):
        die("CEOS_TIMEZONE is not a conservative IANA-style timezone identifier")
    if not password_hash.startswith("$"):
        die("CEOS_PASSWORD_HASH does not look like a crypt password hash")
    if not re.match(r"^(ssh-(rsa|ed25519)|ecdsa-sha2-nistp(256|384|521))\s+\S+", ssh_key):
        die("CEOS_ADMIN_SSH_PUBLIC_KEY does not look like an SSH public key")

    # Storage is intentionally a reviewed YAML fragment, not inferred here.
    # Require a multi-line list item and reject known unresolved/wildcard shortcuts.
    if "\n" not in storage:
        die("CEOS_REVIEWED_STORAGE_CONFIGURATION must be an explicit multi-line YAML fragment")
    bad = ("UNRESOLVED", "largest", "first-disk", "first_disk", "wildcard")
    if any(x.lower() in storage.lower() for x in bad):
        die("CEOS_REVIEWED_STORAGE_CONFIGURATION contains a forbidden unresolved/implicit selector")

    wifi_enable = v.get("CEOS_WIFI_ENABLE", "false").lower() == "true"
    if wifi_enable:
        if v.get("CEOS_WIFI_SSID", "") in ("", "UNRESOLVED"):
            die("CEOS_WIFI_ENABLE=true but CEOS_WIFI_SSID is unresolved")
        if v.get("CEOS_WIFI_PSK", "") in ("", "UNRESOLVED"):
            die("CEOS_WIFI_ENABLE=true but CEOS_WIFI_PSK is unresolved")

    tailscale_enable = v.get("CEOS_TAILSCALE_ENABLE", "false").lower() == "true"
    if tailscale_enable and v.get("CEOS_TAILSCALE_AUTH_KEY", "") in ("", "UNRESOLVED"):
        die("CEOS_TAILSCALE_ENABLE=true but CEOS_TAILSCALE_AUTH_KEY is unresolved")

    user_data = f"""#cloud-config
autoinstall:
  version: 1
  locale: en_US.UTF-8
  keyboard:
    layout: us
  timezone: {yaml_single(timezone)}

  identity:
    hostname: {yaml_single(hostname)}
    username: {yaml_single(user)}
    password: {yaml_single(password_hash)}

  ssh:
    install-server: true
    allow-pw: false
    authorized-keys:
      - {yaml_single(ssh_key)}

  storage:
    config:
{storage}

  packages:
    - git
    - ca-certificates
    - curl
    - build-essential
    - cmake
    - ninja-build
    - python3
    - python3-venv
    - network-manager
    - wpasupplicant
    - openssh-server
    - iproute2
    - iputils-ping

  late-commands:
    # The boot-medium assembly contract places the verified portable seed at
    # /cdrom/ce-os/seed and this stage script at /cdrom/ce-os/install/.
    # Missing media, missing seed, failed verification, or failed
    # reconstruction makes curtin fail closed and prevents completion.
    - test -d /cdrom/ce-os/seed
    - test -x /cdrom/ce-os/install/ce-os-reconstruct
    - mkdir -p /target/home/{user}
    - /cdrom/ce-os/install/ce-os-reconstruct --apply --seed /cdrom/ce-os/seed --target /target/home/{user}/ce-os
    - test -f /target/home/{user}/ce-os/.ce-os-reconstruction/state
    - grep -q '^status=reconstructed_from_verified_seed$' /target/home/{user}/ce-os/.ce-os-reconstruction/state
    - curtin in-target --target=/target -- chown -R {user}:{user} /home/{user}/ce-os
    - curtin in-target --target=/target -- mkdir -p /var/lib/ce-os
    - curtin in-target --target=/target -- sh -c 'printf "%s\\n" "status=reconstructed_from_verified_seed" "seed=/cdrom/ce-os/seed" > /var/lib/ce-os/substrate-state'

  user-data:
    disable_root: true
"""

    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    os.chmod(out, 0o700)
    (out / "user-data").write_text(user_data)
    os.chmod(out / "user-data", 0o600)
    (out / "meta-data").write_text(
        f"instance-id: ce-os-full-package-{hostname}\n"
        f"local-hostname: {hostname}\n"
    )
    os.chmod(out / "meta-data", 0o600)

    print(f"RENDERED={out}")
    print("REQUIRED_INPUTS=RESOLVED")
    print("STORAGE_POLICY=EXPLICIT_FRAGMENT")
    print("NOCLOUD_RENDER=PASS")

if __name__ == "__main__":
    main()
