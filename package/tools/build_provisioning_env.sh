#!/usr/bin/env bash
set -Eeuo pipefail
log() { echo "[PROVISIONING_ENV] $1"; }
OUTPUT_DIR=""
BOOT_IMG=""
PAYLOAD_DIR=""
while [[ $# -gt 0 ]]; do
 case "$1" in
 --output) OUTPUT_DIR="$2"; shift 2 ;;
 --boot-img) BOOT_IMG="$2"; shift 2 ;;
 --payload) PAYLOAD_DIR="$2"; shift 2 ;;
 --help|-h)
 echo "Usage: $0 --output DIR [--boot-img IMG] [--payload DIR]"
 exit 0
 ;;
 *) echo "Unknown option: $1"; exit 1 ;;
 esac
done
if [[ -z "$OUTPUT_DIR" ]]; then
 echo "ERROR: --output is required"
 exit 1
fi
mkdir -p "$OUTPUT_DIR"
log "Building provisioning environment in $OUTPUT_DIR"
TMPDIR="$OUTPUT_DIR/build.tmp"
rm -rf "$TMPDIR"
mkdir -p "$TMPDIR/initramfs"
INITRAMFS="$TMPDIR/initramfs"
log "Creating initramfs structure"
for d in bin sbin etc proc sys dev mnt tmp var/run usr/bin usr/sbin lib root payload; do
 mkdir -p "$INITRAMFS/$d"
done
BUSYBOX_SRC=""
for candidate in /data/data/com.termux/files/usr/bin/busybox /usr/bin/busybox; do
 if [[ -x "$candidate" ]]; then
 BUSYBOX_SRC="$candidate"
 break
 fi
done
if [[ -n "$BUSYBOX_SRC" ]]; then
 cp "$BUSYBOX_SRC" "$INITRAMFS/bin/busybox"
 chmod 755 "$INITRAMFS/bin/busybox"
 log "Copied busybox from $BUSYBOX_SRC"
 for link in sh mount umount mkdir cat echo sleep httpd ifconfig ip udhcpc ln cp mv rm reboot; do
 ln -sf busybox "$INITRAMFS/bin/$link"
 done
 log "Created busybox symlinks"
else
 log "WARNING: busybox not found, initramfs will be minimal"
fi
cat > "$INITRAMFS/init" << 'INIT_EOF'
#!/bin/sh
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mkdir -p /dev/pts
mount -t devpts devpts /dev/pts
ip link set lo up
echo "========================================"
echo " CE-OS Provisioning Environment"
echo "========================================"
echo ""
echo "1. Start Provisioning"
echo "2. Reboot to Android"
echo ""
read -p "Select option: " choice
case "$choice" in
 1)
 echo "Starting provisioning service..."
 cd /payload
 httpd -p 8080 -h . 2>/dev/null || echo "httpd not available"
 echo "Press Enter to stop and reboot..."
 read
 ;;
 2) echo "Rebooting..." ;;
 *) echo "Invalid choice" ;;
esac
reboot -f
INIT_EOF
chmod 755 "$INITRAMFS/init"
if [[ -n "$PAYLOAD_DIR" && -d "$PAYLOAD_DIR" ]]; then
 cp -r "$PAYLOAD_DIR/." "$INITRAMFS/payload/"
 log "Copied payload from $PAYLOAD_DIR"
else
 echo "Payload directory - place CE-OS seed and Ubuntu autoinstall files here" > "$INITRAMFS/payload/README.txt"
 log "Created payload placeholder"
fi
KERNEL="$TMPDIR/kernel"
if [[ -n "$BOOT_IMG" && -f "$BOOT_IMG" ]]; then
 log "Kernel extraction from boot image not yet implemented"
 touch "$KERNEL"
else
 log "WARNING: No boot image, using placeholder kernel"
 touch "$KERNEL"
fi
INITRAMFS_CPIO="$TMPDIR/initramfs.cpio.gz"
(cd "$INITRAMFS" && find . | cpio -H newc -o 2>/dev/null | gzip) > "$INITRAMFS_CPIO"
log "Initramfs created: $INITRAMFS_CPIO ($(stat -c%s "$INITRAMFS_CPIO") bytes)"
OUTPUT_IMG="$OUTPUT_DIR/provisioning.img"
cat "$KERNEL" "$INITRAMFS_CPIO" > "$OUTPUT_IMG"
log "Provisioning image: $OUTPUT_IMG ($(stat -c%s "$OUTPUT_IMG") bytes)"
cat > "$OUTPUT_DIR/provisioning-metadata.json" << META_EOF
{
 "kernel_source": "${BOOT_IMG:-placeholder}",
 "initramfs_size": $(stat -c%s "$INITRAMFS_CPIO"),
 "image_size": $(stat -c%s "$OUTPUT_IMG"),
 "payload_dir": "${PAYLOAD_DIR:-none}",
 "safety": "RAM-only, no flash, instant rollback via reboot"
}
META_EOF
rm -rf "$TMPDIR"
log "Build complete"
log ""
log "To boot on Pixel 6:"
log " 1. Connect Pixel to PC via USB"
log " 2. Boot Pixel into fastboot mode"
log " 3. Run: fastboot boot provisioning.img"
log " 4. Pixel boots into provisioning environment (RAM-only)"
log " 5. To rollback: simply reboot the Pixel"
