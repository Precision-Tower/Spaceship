#!/usr/bin/env python3
"""
Build a minimal provisioning environment for the Pixel 6.
This script creates a RAM-only bootable image that can be loaded via 'fastboot boot'
to provision target hardware with Ubuntu LTS + CE-OS.
Safety: This script never flashes or modifies the Pixel's persistent storage.
"""
import os
import sys
import subprocess
import shutil
import tempfile
from pathlib import Path
def log(msg):
 print(f"[PROVISIONING_ENV] {msg}")
def check_dependencies():
 """Check for required tools."""
 required = ['mkbootfs', 'mkbootimg', 'busybox', 'gzip']
 missing = []
 for tool in required:
 if not shutil.which(tool):
 missing.append(tool)
1
2
3
4
if missing:
    log(f"ERROR: Missing required tools: {', '.join(missing)}")
    log("Please install: android-tools, busybox-static")
    sys.exit(1)
def extract_kernel_from_boot(boot_img_path, output_kernel_path):
 """Extract kernel from Pixel 6 boot image."""
 log(f"Extracting kernel from {boot_img_path}")
1
2
3
4
5
6
7
8
9
10
# Use unpackbootimg or manual extraction
# For now, we'll use a placeholder - in production, this would parse the boot image header
log("WARNING: Kernel extraction requires Pixel 6 stock boot image")
log("Placeholder: Creating empty kernel file")
# In production:
# subprocess.run(['unpackbootimg', '-i', boot_img_path, '-o', output_dir])
# shutil.copy(output_dir / 'boot.img-kernel', output_kernel_path)
Path(output_kernel_path).touch()
def build_initramfs(initramfs_dir, output_cpio_path):
 """Build initramfs from directory structure."""
 log(f"Building initramfs from {initramfs_dir}")
1
2
3
4
5
6
7
8
# Create cpio archive
subprocess.run(
    f"cd {initramfs_dir} && find . | cpio -H newc -o | gzip > {output_cpio_path}",
    shell=True,
    check=True
)
log(f"Initramfs created: {output_cpio_path}")
def create_initramfs_structure(base_dir, payload_dir):
 """Create the initramfs directory structure."""
 log(f"Creating initramfs structure in {base_dir}")
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
# Create base directories
dirs = [
    'bin', 'sbin', 'etc', 'proc', 'sys', 'dev', 'mnt', 'tmp',
    'var/run', 'usr/bin', 'usr/sbin', 'lib', 'lib64', 'root',
    'payload'
]
for d in dirs:
    (base_dir / d).mkdir(parents=True, exist_ok=True)
# Copy busybox
busybox_src = shutil.which('busybox')
if not busybox_src:
    # Try static busybox
    busybox_src = '/data/data/com.termux/files/usr/bin/busybox'
if busybox_src and Path(busybox_src).exists():
    shutil.copy(busybox_src, base_dir / 'bin' / 'busybox')
    (base_dir / 'bin' / 'busybox').chmod(0o755)
        # Create busybox symlinks
    log("Creating busybox symlinks")
    busybox_links = ['sh', 'mount', 'umount', 'mkdir', 'cat', 'echo', 'sleep',
                    'httpd', 'ifconfig', 'ip', 'udhcpc', 'ln', 'cp', 'mv', 'rm']
        for link in busybox_links:
        link_path = base_dir / 'bin' / link
        if not link_path.exists():
            link_path.symlink_to('busybox')
# Create init script
init_script = base_dir / 'init'
init_script.write_text('''#!/bin/sh
Mount essential filesystems
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
Create device nodes
mkdir -p /dev/pts
mount -t devpts devpts /dev/pts
Setup networking
ip link set lo up
Display banner
echo "========================================"
echo " CE-OS Provisioning Environment"
echo "========================================"
echo ""
echo "1. Start Provisioning (serve Ubuntu + CE-OS to target)"
echo "2. Reboot to Android"
echo ""
read -p "Select option: " choice
case "$choice" in
 1)
 echo "Starting provisioning service..."
 echo "Connect Pixel USB to target PC"
 echo "Target should boot from Network (PXE) or USB"
 echo ""
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
    # Configure USB gadget (placeholder - requires ConfigFS setup)
    # This would configure RNDIS/Ethernet gadget
        # Start HTTP server
    cd /payload
    httpd -p 8080 -h .
    echo "HTTP server running on port 8080"
    echo "Serving payload from /payload"
    echo ""
    echo "Press Enter to stop and reboot..."
    read
    ;;
2)
    echo "Rebooting..."
    ;;
*)
    echo "Invalid choice"
    ;;
esac
Reboot
reboot -f
''')
 init_script.chmod(0o755)
1
2
3
4
5
6
7
8
# Copy payload if provided
if payload_dir and Path(payload_dir).exists():
    log(f"Copying payload from {payload_dir}")
    # In production, this would copy the CE-OS seed and Ubuntu autoinstall files
    # For now, create placeholder
    (base_dir / 'payload' / 'README.txt').write_text(
        "Payload directory\n\nPlace CE-OS seed and Ubuntu autoinstall files here\n"
    )
def build_provisioning_image(output_dir, boot_img=None, payload_dir=None):
 """Main build function."""
 output_dir = Path(output_dir)
 output_dir.mkdir(parents=True, exist_ok=True)
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
51
52
53
54
55
56
57
58
59
60
61
log(f"Building provisioning environment in {output_dir}")
check_dependencies()
# Create temporary build directory
with tempfile.TemporaryDirectory() as tmpdir:
    tmpdir = Path(tmpdir)
        # Step 1: Extract or prepare kernel
    kernel_path = tmpdir / 'kernel'
    if boot_img and Path(boot_img).exists():
        extract_kernel_from_boot(boot_img, kernel_path)
    else:
        log("WARNING: No boot image provided, using placeholder kernel")
        kernel_path.touch()
        # Step 2: Build initramfs
    initramfs_dir = tmpdir / 'initramfs'
    initramfs_dir.mkdir()
    create_initramfs_structure(initramfs_dir, payload_dir)
        initramfs_cpio = tmpdir / 'initramfs.cpio.gz'
    build_initramfs(initramfs_dir, initramfs_cpio)
        # Step 3: Create bootable image
    # For 'fastboot boot', we need an Android boot image format
    # In production, this would use mkbootimg with proper parameters
    output_img = output_dir / 'provisioning.img'
        # Placeholder: concatenate kernel + initramfs
    # Real implementation would use: mkbootimg --kernel kernel --ramdisk initramfs.cpio.gz --output 
    log("Creating boot image (placeholder)")
    with open(output_img, 'wb') as f:
        f.write(kernel_path.read_bytes())
        f.write(initramfs_cpio.read_bytes())
        log(f"Provisioning image created: {output_img}")
    log(f"Size: {output_img.stat().st_size} bytes")
        # Create metadata
    metadata = {
        'kernel_source': str(boot_img) if boot_img else 'placeholder',
        'initramfs_size': initramfs_cpio.stat().st_size,
        'payload_dir': str(payload_dir) if payload_dir else None,
        'safety': 'RAM-only, no flash, instant rollback via reboot'
    }
        metadata_file = output_dir / 'provisioning-metadata.json'
    import json
    metadata_file.write_text(json.dumps(metadata, indent=2))
        log(f"Metadata written: {metadata_file}")
log("Build complete")
log("")
log("To boot on Pixel 6:")
log("  1. Connect Pixel to PC via USB")
log("  2. Boot Pixel into fastboot mode")
log("  3. Run: fastboot boot provisioning.img")
log("  4. Pixel will boot into provisioning environment (RAM-only)")
log("  5. To rollback: simply reboot the Pixel")
if name == 'main':
 import argparse
1
2
3
4
5
6
7
8
parser = argparse.ArgumentParser(description='Build Pixel 6 provisioning environment')
parser.add_argument('--output', required=True, help='Output directory for provisioning.img')
parser.add_argument('--boot-img', help='Pixel 6 stock boot image (for kernel extraction)')
parser.add_argument('--payload', help='Directory containing CE-OS seed and Ubuntu autoinstall files'
args = parser.parse_args()
build_provisioning_image(args.output, args.boot_img, args.payload)
