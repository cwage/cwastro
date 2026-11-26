#!/usr/bin/env bash
# Build and install INDI core and the drivers this rig needs. Run on the Pi.
# Safe to run again: sources are updated in place and rebuilt.
#
# First run 2026-11-22 on Raspberry Pi OS trixie (gcc 14.2). The package list
# resolves there. The core build takes roughly an hour on a Pi 4.
#
#   INDI_TAG=v2.2.5 provision/install-indi.sh
set -euo pipefail

TAG=${INDI_TAG:-v2.2.5}
SRC=${SRC:-$HOME/src}
JOBS=${JOBS:-$(nproc)}

sudo apt-get update
sudo apt-get install -y \
  git cmake build-essential pkg-config \
  libev-dev libgsl-dev libcfitsio-dev libnova-dev zlib1g-dev libjpeg-dev \
  libusb-1.0-0-dev libcurl4-gnutls-dev libtheora-dev libfftw3-dev \
  libtiff-dev libraw-dev libgps-dev libdc1394-dev libgphoto2-dev \
  libboost-dev libboost-regex-dev libftdi1-dev librtlsdr-dev libudev-dev \
  libpigpiod-if-dev libpigpiod-if2-1   # client side of pigpiod, for indi-asi-power

mkdir -p "$SRC"

fetch() {  # repo dir
  if [ -d "$SRC/$2/.git" ]; then
    # Already at the tag: nothing to fetch. Otherwise fetch that one tag only
    # (--tags would pull every release of indi-3rdparty's binary SDKs).
    if [ "$(git -C "$SRC/$2" describe --tags --exact-match 2>/dev/null)" != "$TAG" ]; then
      git -C "$SRC/$2" fetch --depth 1 --no-tags origin "refs/tags/$TAG:refs/tags/$TAG"
      git -C "$SRC/$2" checkout -q "$TAG"
    fi
  else
    git clone --depth 1 --branch "$TAG" "https://github.com/indilib/$1.git" "$SRC/$2"
  fi
}

build() {  # source-dir build-name
  local b="$SRC/build/$2"
  mkdir -p "$b"
  # FIX_WARNINGS=OFF: INDI turns warnings into errors by default, and gcc 14
  # on trixie raises one (stringop-overread in the astrotrac driver, v2.2.5)
  # that stops the build of a driver this rig does not even use.
  cmake -S "$1" -B "$b" -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Release \
    -DFIX_WARNINGS=OFF
  cmake --build "$b" -j "$JOBS"
  sudo cmake --install "$b"
}

fetch indi indi
fetch indi-3rdparty indi-3rdparty

build "$SRC/indi" indi-core

# Libraries first, then the drivers that link against them.
build "$SRC/indi-3rdparty/libasi" libasi          # ZWO's camera/EFW SDK and udev rules
build "$SRC/indi-3rdparty/indi-asi" indi-asi      # ASI cameras, EFW
build "$SRC/indi-3rdparty/indi-eqmod" indi-eqmod  # EQ6-R
build "$SRC/indi-3rdparty/libpigpiod" libpigpiod  # the pigpiod daemon and its service
build "$SRC/indi-3rdparty/indi-asi-power" indi-asi-power  # the ASIAIR's 12 V ports

sudo ldconfig
sudo udevadm control --reload-rules
# indi-3rdparty's own pigpiod.service is only installed when the systemd
# pkg-config file is present, which it is not here; use ours.
sudo install -m 644 "$(dirname "$0")/../systemd/pigpiod.service" /etc/systemd/system/pigpiod.service
sudo systemctl daemon-reload
sudo systemctl enable --now pigpiod.service
sudo install -m 644 "$(dirname "$0")/../systemd/indiserver.service" /etc/systemd/system/indiserver.service
sudo systemctl daemon-reload
sudo systemctl enable --now indiserver.service

indiserver --version 2>&1 | head -1 || true
ls /usr/bin/indi_asi_* /usr/bin/indi_eqmod_telescope 2>/dev/null
