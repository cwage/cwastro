#!/usr/bin/env bash
# Copy the first-boot files onto a freshly written Raspberry Pi OS card.
# Usage: provision/write-bootfs.sh /media/$USER/bootfs
set -euo pipefail
boot=${1:?path to the mounted bootfs partition}
here=$(cd "$(dirname "$0")/.." && pwd)
[ -f "$here/cloud-init/user-data" ] || {
  echo "no cloud-init/user-data: copy user-data.example to it and add your SSH keys" >&2
  exit 1
}
[ -f "$boot/cmdline.txt" ] && [ -f "$boot/user-data" ] || {
  echo "$boot does not look like a Raspberry Pi OS boot partition with cloud-init" >&2
  exit 1
}
cp "$here/cloud-init/user-data" "$boot/user-data"
cp "$here/cloud-init/network-config" "$boot/network-config"
cp "$here/cloud-init/meta-data" "$boot/meta-data"
: > "$boot/ssh"   # the older switch for enabling sshd; harmless if unused
sync
echo "first-boot files written to $boot"
