#!/usr/bin/env bash
set -euo pipefail

# Build a .deb package for meshtasticd from a completed native build.
# Run inside the native-builder container after `pio run -e native` succeeds.

VERSION=$(python3 bin/buildinfo.py short 2>/dev/null || echo "0.0.0-dev")
ARCH=$(dpkg --print-architecture 2>/dev/null || echo "$(uname -m)")
PKG_DIR="/tmp/meshtasticd-pkg"
BINARY=".pio/build/native/meshtasticd"

if [[ ! -f "$BINARY" ]]; then
    echo "ERROR: Compiled binary not found at $BINARY"
    echo "Run 'pio run -e native' first."
    exit 1
fi

echo "Packaging meshtasticd $VERSION ($ARCH)"

# Clean previous build
rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/usr/bin"
mkdir -p "$PKG_DIR/usr/lib/systemd/system"
mkdir -p "$PKG_DIR/etc/meshtasticd"
mkdir -p "$PKG_DIR/etc/meshtasticd/available.d"
mkdir -p "$PKG_DIR/etc/meshtasticd/ssl"
mkdir -p "$PKG_DIR/var/lib/meshtasticd"

# Binary
cp "$BINARY" "$PKG_DIR/usr/bin/meshtasticd"
chmod 755 "$PKG_DIR/usr/bin/meshtasticd"

# Startup script
cp bin/meshtasticd-start.sh "$PKG_DIR/usr/bin/meshtasticd-start.sh"
chmod 755 "$PKG_DIR/usr/bin/meshtasticd-start.sh"

# systemd unit
cp bin/meshtasticd.service "$PKG_DIR/usr/lib/systemd/system/meshtasticd.service"

# Default config
cp bin/config-dist.yaml "$PKG_DIR/etc/meshtasticd/config.yaml"

# Available config templates
if [[ -d bin/config.d ]]; then
    cp -r bin/config.d/* "$PKG_DIR/etc/meshtasticd/available.d/" 2>/dev/null || true
fi

# udev rules (if present)
if [[ -f bin/99-meshtasticd-udev.rules ]]; then
    mkdir -p "$PKG_DIR/etc/udev/rules.d"
    cp bin/99-meshtasticd-udev.rules "$PKG_DIR/etc/udev/rules.d/"
fi

# Create meshtasticd user via postinst
cat > "$PKG_DIR/DEBIAN/postinst" << 'POSTINST'
#!/bin/sh
set -e

# Create system user/group if they don't exist
if ! getent group meshtasticd >/dev/null 2>&1; then
    addgroup --system meshtasticd
fi
if ! getent passwd meshtasticd >/dev/null 2>&1; then
    adduser --system --ingroup meshtasticd --no-create-home \
        --home /var/lib/meshtasticd --shell /usr/sbin/nologin meshtasticd
fi

# Set ownership
chown -R meshtasticd:meshtasticd /var/lib/meshtasticd
chown -R meshtasticd:meshtasticd /etc/meshtasticd

# Reload systemd if running
if command -v systemctl >/dev/null 2>&1; then
    systemctl daemon-reload 2>/dev/null || true
fi

echo ""
echo "meshtasticd installed."
echo "  Config:  /etc/meshtasticd/config.yaml"
echo "  Data:    /var/lib/meshtasticd/"
echo "  Templates: /etc/meshtasticd/available.d/"
echo ""
echo "Edit the config, then:"
echo "  sudo systemctl enable --now meshtasticd"
echo ""
POSTINST
chmod 755 "$PKG_DIR/DEBIAN/postinst"

# prerm — stop the service before removal
cat > "$PKG_DIR/DEBIAN/prerm" << 'PRERM'
#!/bin/sh
set -e
if command -v systemctl >/dev/null 2>&1; then
    systemctl stop meshtasticd 2>/dev/null || true
fi
PRERM
chmod 755 "$PKG_DIR/DEBIAN/prerm"

# postrm — remove user only on purge, not upgrade
cat > "$PKG_DIR/DEBIAN/postrm" << 'POSTRM'
#!/bin/sh
set -e
if [ "$1" = "purge" ]; then
    if command -v systemctl >/dev/null 2>&1; then
        systemctl daemon-reload 2>/dev/null || true
    fi
    echo "To remove meshtasticd data: sudo rm -rf /var/lib/meshtasticd /etc/meshtasticd"
    echo "To remove the meshtasticd user: sudo deluser meshtasticd"
fi
POSTRM
chmod 755 "$PKG_DIR/DEBIAN/postrm"

# Control file — dependency list matched to the official OBS daily build for Debian 13.
# These are the correct Debian Trixie/13 package names (including the t64 transition suffixes).
# For Debian 12 (bookworm) or Armbian, some package names may differ slightly —
# in that case use `dpkg -i --force-depends` and install missing libs manually.
cat > "$PKG_DIR/DEBIAN/control" << CONTROL
Package: meshtasticd
Version: $VERSION
Architecture: $ARCH
Maintainer: Meshtastic <contact@meshtastic.org>
Section: net
Priority: optional
Installed-Size: $(du -sk "$PKG_DIR" | cut -f1)
Depends: adduser, libc6 (>= 2.38), libgcc-s1 (>= 3.0), libgpiod3 (>= 2.1), libi2c0 (>= 4.0), libinput10 (>= 0.15.0), libjsoncpp26 (>= 1.9.6), liborcania2.3 (>= 2.1.0), libsdl2-2.0-0 (>= 2.0.18), libssl3t64 (>= 3.0.0), libstdc++6 (>= 11), libulfius2.7t64 (>= 2.7.0), libusb-1.0-0 (>= 2:1.0.22), libuv1t64 (>= 1.4.2), libx11-6, libxkbcommon0 (>= 0.5.0), libyaml-cpp0.8 (>= 0.8.0+dfsg-7)
Recommends: systemd
Description: Meshtastic native daemon (meshtasticd)
 Native Linux port of the Meshtastic firmware, built for the
 portduino platform. Supports LoRa radio modules attached via
 SPI (SX1262, SX1268, SX1280, LR1110, LR1120, LR1121, LR2021,
 RF95, LLCC68) or CH341 USB-SPI bridge.
 .
 Includes systemd service, default config, and hardware
 config templates for common SBC radio hats.
CONTROL

# Build the .deb
OUTPUT="release/meshtasticd_${VERSION}_${ARCH}.deb"
mkdir -p release
dpkg-deb --build "$PKG_DIR" "$OUTPUT"
echo ""
echo "Built: $OUTPUT"
ls -lh "$OUTPUT"
