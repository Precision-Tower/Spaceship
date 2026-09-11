#!/usr/bin/env python3
import argparse
import re
import shlex
from pathlib import Path

def die(msg):
    raise SystemExit(f"ERROR: {msg}")

def load_env(path):
    values = {}
    lines = path.read_text().splitlines()
    i = 0
    while i < len(lines):
        lineno = i + 1
        line = lines[i].strip()
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

def required(v, key):
    x = v.get(key, "").strip()
    if not x or x == "UNRESOLVED":
        die(f"{key} is unresolved")
    return x

def boolean(v, key):
    x = required(v, key).lower()
    if x not in ("true", "false"):
        die(f"{key} must be true or false")
    return x == "true"

def yaml_single(value):
    return "'" + value.replace("'", "''") + "'"

ap = argparse.ArgumentParser()
ap.add_argument("--activation", required=True, type=Path)
ap.add_argument("--output", required=True, type=Path)
args = ap.parse_args()

v = load_env(args.activation)

hostname = required(v, "CEOS_HOSTNAME")
user = required(v, "CEOS_ADMIN_USER")
timezone = required(v, "CEOS_TIMEZONE")
password = required(v, "CEOS_PASSWORD_HASH")
ssh_key = required(v, "CEOS_ADMIN_SSH_PUBLIC_KEY")
storage = required(v, "CEOS_REVIEWED_STORAGE_CONFIGURATION")
wifi = boolean(v, "CEOS_WIFI_ENABLE")

if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", hostname):
    die("CEOS_HOSTNAME is invalid")
if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", user):
    die("CEOS_ADMIN_USER is invalid")
if not re.fullmatch(r"[A-Za-z0-9_+.-]+(?:/[A-Za-z0-9_+.-]+)*", timezone) or ".." in timezone.split("/"):
    die("CEOS_TIMEZONE is invalid")
if not password.startswith("$"):
    die("CEOS_PASSWORD_HASH must be a crypt-style password hash")
if not re.match(r"^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(?:256|384|521))\s+\S+", ssh_key):
    die("CEOS_ADMIN_SSH_PUBLIC_KEY is invalid")

lower_storage = storage.lower()
for forbidden in ("unresolved", "largest", "first-disk", "first_disk", "wildcard"):
    if forbidden in lower_storage:
        die(f"storage configuration contains forbidden selector: {forbidden}")

ssid = psk = None
if wifi:
    ssid = required(v, "CEOS_WIFI_SSID")
    psk = required(v, "CEOS_WIFI_PSK")
    if len(psk) < 8 or len(psk) > 63:
        die("CEOS_WIFI_PSK must be 8..63 characters for WPA-PSK")

if args.output.exists():
    die(f"output already exists: {args.output}")
args.output.mkdir(parents=True, mode=0o700)

wifi_late = ""
if wifi:
    # Configure the installed system, not the ephemeral installer environment.
    # NetworkManager owns the connection after first boot.
    wifi_late = f"""
    - curtin in-target --target=/target -- nmcli connection add type wifi ifname '*' con-name ce-os-network ssid {yaml_single(ssid)}
    - curtin in-target --target=/target -- nmcli connection modify ce-os-network wifi-sec.key-mgmt wpa-psk wifi-sec.psk {yaml_single(psk)} connection.autoconnect yes
"""

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
    password: {yaml_single(password)}

  ssh:
    install-server: true
    allow-pw: false
    authorized-keys:
      - {yaml_single(ssh_key)}

  storage:
    config:
{storage}

  packages:
    - openssh-server
    - network-manager
    - wpasupplicant
    - iproute2
    - iputils-ping
    - ca-certificates
    - curl

  late-commands:
    - curtin in-target --target=/target -- systemctl enable NetworkManager
    - curtin in-target --target=/target -- systemctl enable ssh
{wifi_late.rstrip()}
    - curtin in-target --target=/target -- mkdir -p /var/lib/ce-os
    - curtin in-target --target=/target -- sh -c 'printf "%s\\n" "profile=network-install" "network_manager=enabled" "ssh=enabled" > /var/lib/ce-os/network-install-state'

  user-data:
    disable_root: true
"""

meta_data = f"""instance-id: ce-os-network-install-{hostname}
local-hostname: {hostname}
"""

(args.output / "user-data").write_text(user_data)
(args.output / "meta-data").write_text(meta_data)
(args.output / "user-data").chmod(0o600)
(args.output / "meta-data").chmod(0o600)

print(f"RENDERED={args.output}")
print("PROFILE=NETWORK_INSTALL")
print("CE_OS_RECONSTRUCTION=NONE")
print("SSH=ENABLED")
print("NETWORK_MANAGER=ENABLED")
print("WPA_SUPPLICANT=INSTALLED")
print("WIFI_AUTOCONNECT=" + ("ENABLED" if wifi else "DISABLED"))
print("NOCLOUD_RENDER=PASS")
