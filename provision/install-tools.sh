#!/usr/bin/env bash
# Plate solver, Python libraries for the tools, and PHD2 on a virtual display.
# Run on the Pi after install-indi.sh and install-phd2.sh. Safe to run again.
# First run 2026-11-26 on Raspberry Pi OS trixie.
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)

sudo apt-get update
sudo apt-get install -y \
  astrometry.net \
  astrometry-data-tycho2-07-littleendian astrometry-data-tycho2-08-littleendian \
  astrometry-data-tycho2-09-littleendian astrometry-data-tycho2-10-19-littleendian \
  python3-astropy python3-numpy \
  xvfb x11vnc xdotool imagemagick

# The Tycho-2 index files above cover star patterns from 22' up, which suits
# both fields here: 2.36 x 1.78 deg on the main camera (1.82"/px) and about
# 1.7 x 1.3 deg on the guide camera (4.77"/px).

# PHD2's equipment profile, loaded only when PHD2 has no settings yet.
# (wxWidgets names the file ~/.PHDGuidingV2.)
if [ ! -e "$HOME/.PHDGuidingV2" ]; then
  xvfb-run -a phd2 --load="$here/config/phd2-profile.phd"
fi

for unit in xvfb phd2 x11vnc; do
  sudo install -m 644 "$here/systemd/$unit.service" /etc/systemd/system/
done
sudo systemctl daemon-reload
sudo systemctl enable --now xvfb.service phd2.service x11vnc.service
systemctl is-active xvfb phd2 x11vnc
