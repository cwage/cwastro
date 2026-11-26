#!/usr/bin/env bash
# Build and install PHD2 (guiding) against the INDI already installed.
# Run on the Pi, after install-indi.sh. Debian trixie has no phd2 package.
#
# First run 2026-11-23 on Raspberry Pi OS trixie: about 19 minutes on the Pi 4,
# no changes needed. Installs /usr/bin/phd2 (a wrapper) and phd2.bin.
set -euo pipefail

TAG=${PHD2_TAG:-v2.6.14}
SRC=${SRC:-$HOME/src}
JOBS=${JOBS:-$(nproc)}

sudo apt-get install -y \
  git cmake build-essential pkg-config gettext \
  libwxgtk3.2-dev libwxgtk-webview3.2-dev wx-common wx3.2-i18n \
  libx11-dev libcurl4-gnutls-dev libcfitsio-dev libnova-dev zlib1g-dev \
  libusb-1.0-0-dev libeigen3-dev libgtest-dev libopencv-dev

if [ ! -d "$SRC/phd2/.git" ]; then
  git clone --depth 1 --branch "$TAG" https://github.com/OpenPHDGuiding/phd2.git "$SRC/phd2"
fi

b="$SRC/build/phd2"
mkdir -p "$b"
cmake -S "$SRC/phd2" -B "$b" -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Release \
  -DOPENSOURCE_ONLY=1 -DUSE_SYSTEM_LIBINDI=1 -DUSE_SYSTEM_CFITSIO=1 \
  -DUSE_SYSTEM_LIBUSB=1 -DUSE_SYSTEM_EIGEN3=1 -DUSE_SYSTEM_GTEST=1
cmake --build "$b" -j "$JOBS"
sudo cmake --install "$b"
ls -l /usr/bin/phd2
